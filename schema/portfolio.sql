-- Investment Management Layer schema (2026-08-12, BUILD ASSIGNMENT — NGX
-- Rotation Investment Management Layer). Lives in its own database
-- (data/portfolio.sqlite), completely separate from data/ngx.sqlite
-- (market/document/FRE data) and data/registry.sqlite (immutable
-- experiment/hypothesis ledger) -- zero schema changes to either existing
-- database, zero risk to production Alpha/research data. This mirrors the
-- project's own established pattern of one database per concern.
--
-- PAPER/SIMULATION ONLY. No table here represents real money, a real
-- broker connection, or real investor capital. See fund_model tables'
-- own header comment for the explicit NOT LIVE / NOT REGULATED marking.
--
-- Immutability discipline, matching schema/registry.sql's own trigger
-- pattern exactly: signals, allocation_decisions, orders, fills, and
-- decision_journal are INSERT-only (UPDATE/DELETE blocked by trigger) --
-- "the goal is to create institutional memory," per the build assignment.
-- Tables that legitimately mutate (positions, portfolio_snapshots'
-- current-state view, portfolio_alerts' acknowledgement) are NOT
-- immutable, matching the same distinction ngx.sqlite's own
-- monitoring_runs/alerts (immutable) vs positions-would-be (mutable, if
-- it existed there) already draws.

-- ============================================================
-- PHASE 1: PORTFOLIO
-- ============================================================

CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id     TEXT PRIMARY KEY,          -- e.g. 'NGX_ROTATION_PAPER'
    name             TEXT NOT NULL,
    base_currency    TEXT NOT NULL DEFAULT 'NGN' CHECK (base_currency GLOB '[A-Z][A-Z][A-Z]'),
    initial_capital  REAL NOT NULL CHECK (initial_capital > 0),
    strategy_id      TEXT,                      -- references strategies.strategy_id (Phase 11), nullable early on
    inception_date   TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'paper'
                       CHECK (status IN ('paper', 'paused', 'archived')),
                       -- 'live' is intentionally NOT a legal value here --
                       -- per the hard constraint "do not connect real
                       -- money" -- promoting a portfolio to live status
                       -- requires a schema change made deliberately later,
                       -- not a value this build makes reachable.
    created_at       TEXT NOT NULL
);

-- Signals: a persisted record of what alpha_engine.Recommendation said,
-- at the moment it was consumed -- NOT a copy of alpha_engine.py's logic,
-- a durable snapshot of its OUTPUT for lineage. alpha_engine.py itself is
-- never modified; this table is written by portfolio/construction.py's
-- adapter only.
CREATE TABLE IF NOT EXISTS signals (
    signal_id            TEXT PRIMARY KEY,       -- 'S-' + uuid4
    as_of                TEXT NOT NULL,
    instrument           TEXT NOT NULL,
    action               TEXT NOT NULL CHECK (action IN ('buy','sell','hold','avoid','no_position')),
    size_pct_nav         REAL,
    horizon              TEXT,
    expected_excess_ann  REAL,
    expected_max_drawdown REAL,
    confidence_rating    TEXT NOT NULL,
    rationale            TEXT NOT NULL,
    hypothesis_id        TEXT,                   -- references registry.sqlite hypotheses.hypothesis_id
                                                  -- (cross-database reference, not an FK -- registry.sqlite
                                                  -- is a separate file; recorded for lineage traceability only)
    experiment_ids_json  TEXT,                   -- JSON array, from Recommendation.experiment_ids
    caveats_json         TEXT,                   -- JSON array, from Recommendation.caveats
    recorded_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_signals_asof ON signals (as_of);
CREATE INDEX IF NOT EXISTS ix_signals_hypothesis ON signals (hypothesis_id);

CREATE TRIGGER IF NOT EXISTS signals_no_update
BEFORE UPDATE ON signals
BEGIN SELECT RAISE(ABORT, 'signals are immutable -- a corrected signal is a new row, referencing this one in rationale'); END;
CREATE TRIGGER IF NOT EXISTS signals_no_delete
BEFORE DELETE ON signals
BEGIN SELECT RAISE(ABORT, 'signals are immutable -- never deleted'); END;

-- Target positions: output of portfolio construction (Phase 1), before
-- risk review. One row per (allocation_decision, ticker).
CREATE TABLE IF NOT EXISTS target_positions (
    target_position_id  TEXT PRIMARY KEY,        -- 'TP-' + uuid4
    allocation_decision_id TEXT NOT NULL,         -- references allocation_decisions
    portfolio_id         TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    ticker               TEXT NOT NULL,
    target_weight        REAL NOT NULL,
    target_notional       REAL,                   -- NULL until portfolio NAV at construction time is known
    signal_id            TEXT REFERENCES signals(signal_id),
    signal_timestamp     TEXT,
    hypothesis_id        TEXT,
    confidence           TEXT,                    -- carried from the signal's confidence_rating, if any
    reason               TEXT NOT NULL,
    construction_method  TEXT NOT NULL CHECK (construction_method IN
                           ('equal_weight','signal_weighted','rank_weighted','volatility_scaled','custom')),
    created_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_target_positions_decision ON target_positions (allocation_decision_id);

-- Allocation decisions: the unit of "the construction layer proposed THIS
-- portfolio at THIS moment" -- what target_positions belong to, and what
-- risk_checks evaluate.
CREATE TABLE IF NOT EXISTS allocation_decisions (
    allocation_decision_id TEXT PRIMARY KEY,      -- 'AD-' + uuid4
    portfolio_id            TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    as_of                   TEXT NOT NULL,
    construction_method     TEXT NOT NULL,
    rationale                TEXT NOT NULL,
    n_target_positions       INTEGER NOT NULL,
    risk_status              TEXT NOT NULL DEFAULT 'pending'
                              CHECK (risk_status IN ('pending','APPROVED','APPROVED_WITH_WARNINGS','REJECTED')),
    created_at               TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_allocation_decisions_portfolio ON allocation_decisions (portfolio_id, as_of);

CREATE TRIGGER IF NOT EXISTS target_positions_no_update
BEFORE UPDATE ON target_positions
BEGIN SELECT RAISE(ABORT, 'target_positions are immutable -- a revised proposal is a new allocation_decision'); END;
CREATE TRIGGER IF NOT EXISTS target_positions_no_delete
BEFORE DELETE ON target_positions
BEGIN SELECT RAISE(ABORT, 'target_positions are immutable'); END;

-- ============================================================
-- PHASE 2: RISK ENGINE
-- ============================================================

-- Risk policy parameters -- CONFIGURATION, not discovered alpha, per the
-- build assignment's explicit instruction. One active row per
-- portfolio_id (versioned by effective_from, never overwritten).
CREATE TABLE IF NOT EXISTS risk_policies (
    risk_policy_id        TEXT PRIMARY KEY,       -- 'RP-' + uuid4
    portfolio_id           TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    max_position_weight    REAL NOT NULL,
    max_position_notional  REAL,
    max_gross_exposure     REAL NOT NULL,
    max_net_exposure       REAL NOT NULL,
    max_sector_exposure    REAL,
    max_single_name_exposure REAL,
    max_participation_rate REAL NOT NULL,         -- position / ADTV ceiling
    max_drawdown_limit     REAL,                  -- portfolio-level circuit-breaker threshold
    effective_from         TEXT NOT NULL,
    notes                  TEXT NOT NULL           -- REQUIRED: "these are risk-policy parameters, not discovered alpha"
);

CREATE TABLE IF NOT EXISTS risk_checks (
    risk_check_id         TEXT PRIMARY KEY,        -- 'RC-' + uuid4
    allocation_decision_id TEXT NOT NULL REFERENCES allocation_decisions(allocation_decision_id),
    risk_policy_id         TEXT REFERENCES risk_policies(risk_policy_id),  -- NULL = no policy was
                                                                           -- configured at review time
                                                                           -- (itself a REJECTED-by-
                                                                           -- construction finding, see risk.py)
    ticker                 TEXT,                   -- NULL for a portfolio-level check
    check_type             TEXT NOT NULL CHECK (check_type IN
                             ('position_limit','gross_exposure','net_exposure','sector_exposure',
                              'single_name_exposure','liquidity','drawdown')),
    status                 TEXT NOT NULL CHECK (status IN ('pass','warning','fail')),
    measured_value          REAL,
    threshold_value          REAL,
    reason                  TEXT NOT NULL,
    checked_at               TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_risk_checks_decision ON risk_checks (allocation_decision_id);

CREATE TABLE IF NOT EXISTS drawdown_tracking (
    portfolio_id   TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    as_of          TEXT NOT NULL,
    equity         REAL NOT NULL,
    peak_equity    REAL NOT NULL,
    drawdown       REAL NOT NULL,          -- (equity - peak_equity) / peak_equity, <= 0
    max_drawdown_to_date REAL NOT NULL,    -- min(drawdown) over all history up to and including as_of
    PRIMARY KEY (portfolio_id, as_of)
);

-- ============================================================
-- PHASE 3: PAPER EXECUTION
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id              TEXT PRIMARY KEY,        -- 'O-' + uuid4
    portfolio_id            TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    allocation_decision_id  TEXT REFERENCES allocation_decisions(allocation_decision_id),
    target_position_id      TEXT REFERENCES target_positions(target_position_id),
    ticker                  TEXT NOT NULL,
    side                    TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    order_type              TEXT NOT NULL CHECK (order_type IN ('MARKET','LIMIT')),
    quantity                 REAL NOT NULL CHECK (quantity > 0),
    limit_price               REAL,                 -- NULL for MARKET
    signal_timestamp          TEXT NOT NULL,         -- when the signal that generated this order was as_of
    status                    TEXT NOT NULL DEFAULT 'CREATED'
                               CHECK (status IN ('CREATED','SUBMITTED','PARTIALLY_FILLED','FILLED','CANCELLED','REJECTED')),
    rejection_reason           TEXT,
    created_at                 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_orders_portfolio ON orders (portfolio_id, ticker);

CREATE TABLE IF NOT EXISTS fills (
    fill_id            TEXT PRIMARY KEY,          -- 'F-' + uuid4
    order_id            TEXT NOT NULL REFERENCES orders(order_id),
    fill_date            TEXT NOT NULL,             -- the executable trade_date used (next available after signal_timestamp)
    fill_price            REAL NOT NULL,
    quantity              REAL NOT NULL CHECK (quantity > 0),
    commission             REAL NOT NULL DEFAULT 0,
    slippage_bps            REAL NOT NULL DEFAULT 0,  -- applied slippage, in basis points of fill_price
    market_impact_bps        REAL NOT NULL DEFAULT 0,
    transaction_cost_total    REAL NOT NULL,          -- commission + (slippage_bps + market_impact_bps)/1e4 * price * qty
    pricing_source_confidence  REAL,                  -- confidence of the underlying equity_prices row used
    assumptions_note            TEXT NOT NULL,          -- REQUIRED: e.g. "next-session close; commission from cost_schedule_asof;
                                                        -- slippage/impact are configured assumptions, not measured"
    created_at                   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fills_order ON fills (order_id);

CREATE TRIGGER IF NOT EXISTS orders_no_update_terminal
BEFORE UPDATE ON orders
WHEN OLD.status IN ('FILLED','CANCELLED','REJECTED')
BEGIN SELECT RAISE(ABORT, 'a terminal order is immutable -- corrections are a new order'); END;
CREATE TRIGGER IF NOT EXISTS fills_no_update
BEFORE UPDATE ON fills
BEGIN SELECT RAISE(ABORT, 'fills are immutable historical execution records'); END;
CREATE TRIGGER IF NOT EXISTS fills_no_delete
BEFORE DELETE ON fills
BEGIN SELECT RAISE(ABORT, 'fills are immutable historical execution records'); END;

-- Live position state -- the one legitimately-mutable table in the
-- execution chain (a position's quantity/average_cost/market_value change
-- as fills accumulate and prices move; the FILLS that produced it are
-- immutable, this is a derived, recomputable materialization of them).
CREATE TABLE IF NOT EXISTS positions (
    portfolio_id     TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    ticker            TEXT NOT NULL,
    as_of             TEXT NOT NULL,
    quantity           REAL NOT NULL,
    average_cost        REAL NOT NULL,
    market_value          REAL NOT NULL,
    weight                 REAL NOT NULL,
    unrealized_pnl          REAL NOT NULL,
    realized_pnl              REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (portfolio_id, ticker, as_of)
);
CREATE INDEX IF NOT EXISTS ix_positions_portfolio_asof ON positions (portfolio_id, as_of);

-- ============================================================
-- PHASE 4: PERFORMANCE / NAV
-- ============================================================

CREATE TABLE IF NOT EXISTS nav_snapshots (
    portfolio_id       TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    as_of               TEXT NOT NULL,
    cash                 REAL NOT NULL,
    positions_value        REAL NOT NULL,
    nav                      REAL NOT NULL,          -- cash + positions_value
    track_record_status       TEXT NOT NULL CHECK (track_record_status IN
                               ('BACKTEST_ONLY','PAPER','LIVE')),
                               -- 'LIVE' is a legal ENUM value (the column
                               -- must be able to represent reality later)
                               -- but nothing in this build ever WRITES
                               -- 'LIVE' -- see performance.py's own guard.
    PRIMARY KEY (portfolio_id, as_of)
);

CREATE TABLE IF NOT EXISTS performance_records (
    portfolio_id        TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    as_of                 TEXT NOT NULL,
    track_record_status     TEXT NOT NULL CHECK (track_record_status IN ('BACKTEST_ONLY','PAPER','LIVE')),
    daily_return              REAL,
    cumulative_return           REAL,
    cagr                          REAL,
    volatility_ann                 REAL,
    max_drawdown                     REAL,
    sharpe                             REAL,
    sortino                              REAL,
    turnover                              REAL,
    transaction_costs_cum                   REAL,
    number_of_trades_cum                      INTEGER,
    win_rate                                    REAL,
    benchmark_id                                  TEXT,     -- e.g. 'NGXASI' -- must be explicitly configured, never invented
    benchmark_cumulative_return                     REAL,
    PRIMARY KEY (portfolio_id, as_of)
);

-- ============================================================
-- PHASE 5: ATTRIBUTION + LINEAGE
-- ============================================================

CREATE TABLE IF NOT EXISTS attribution_records (
    attribution_id     TEXT PRIMARY KEY,          -- 'ATTR-' + uuid4
    portfolio_id         TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    period_start           TEXT NOT NULL,
    period_end               TEXT NOT NULL,
    dimension                  TEXT NOT NULL CHECK (dimension IN
                                ('ticker','sector','signal','strategy','hypothesis','trade')),
    dimension_value               TEXT NOT NULL,
    pnl                             REAL NOT NULL,
    contribution_pct                 REAL,          -- share of total portfolio P&L over the period, if computable
    created_at                        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_attribution_portfolio_period ON attribution_records (portfolio_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS ix_attribution_dimension ON attribution_records (dimension, dimension_value);

-- Per-position lifecycle record (entry thesis -> exit -> P&L -> cost ->
-- contribution) -- the concrete unit Phase 5 asks for "for each position."
CREATE TABLE IF NOT EXISTS position_lifecycles (
    position_lifecycle_id  TEXT PRIMARY KEY,       -- 'PL-' + uuid4
    portfolio_id             TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    ticker                     TEXT NOT NULL,
    signal_id                    TEXT REFERENCES signals(signal_id),
    hypothesis_id                  TEXT,
    entry_fill_id                    TEXT REFERENCES fills(fill_id),
    exit_fill_id                       TEXT REFERENCES fills(fill_id),
    entry_date                           TEXT NOT NULL,
    exit_date                              TEXT,
    holding_period_days                      INTEGER,
    realized_pnl                               REAL,
    total_cost                                   REAL,
    contribution_to_portfolio                      REAL
);
CREATE INDEX IF NOT EXISTS ix_position_lifecycles_portfolio ON position_lifecycles (portfolio_id, ticker);

-- ============================================================
-- PHASE 6: DECISION JOURNAL
-- ============================================================

CREATE TABLE IF NOT EXISTS decision_journal (
    decision_id       TEXT PRIMARY KEY,           -- 'DJ-' + uuid4
    timestamp           TEXT NOT NULL,
    portfolio_id           TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    strategy_id               TEXT,
    hypothesis_id               TEXT,
    signal_id                     TEXT REFERENCES signals(signal_id),
    portfolio_state_json            TEXT NOT NULL,  -- snapshot of NAV/positions/exposure at decision time
    decision                          TEXT NOT NULL, -- e.g. 'ALLOCATE', 'REJECT_RISK', 'REBALANCE', 'NO_ACTION'
    rationale                           TEXT NOT NULL,
    risk_state_json                       TEXT NOT NULL,
    expected_return                         REAL,
    expected_risk                             REAL,
    actual_outcome_pnl                          REAL,    -- filled in later by attribution, once known -- see note below
    postmortem                                    TEXT
);
-- actual_outcome_pnl/postmortem are the ONLY columns ever updated after
-- insert (by attribution.py, once an outcome is known) -- everything else
-- about a decision is permanent from the moment it's recorded. Enforced
-- by application discipline (portfolio/journal.py), not a trigger,
-- because SQLite triggers cannot express "these two columns only" at the
-- row level without a BEFORE UPDATE trigger comparing OLD/NEW on every
-- other column -- implemented that way instead, see journal.py.
CREATE TRIGGER IF NOT EXISTS decision_journal_no_delete
BEFORE DELETE ON decision_journal
BEGIN SELECT RAISE(ABORT, 'decision_journal is permanent institutional memory -- never deleted'); END;
CREATE TRIGGER IF NOT EXISTS decision_journal_guard_immutable_fields
BEFORE UPDATE ON decision_journal
WHEN OLD.timestamp != NEW.timestamp OR OLD.portfolio_id != NEW.portfolio_id
  OR OLD.decision != NEW.decision OR OLD.rationale != NEW.rationale
  OR OLD.portfolio_state_json != NEW.portfolio_state_json
  OR OLD.risk_state_json != NEW.risk_state_json
BEGIN SELECT RAISE(ABORT, 'only actual_outcome_pnl/postmortem may ever be updated on a decision_journal row'); END;

-- ============================================================
-- PHASE 9: MONITORING (portfolio-layer alerts -- analogous to, not
-- merged with, ngx.sqlite's ticker-scoped monitoring_runs/alerts, since
-- a portfolio-level alert (drawdown breach, risk violation) is not
-- ticker-scoped the same way; same PATTERN, separate table, deliberately
-- not a schema change to the existing monitoring tables)
-- ============================================================

CREATE TABLE IF NOT EXISTS portfolio_alerts (
    alert_id       TEXT PRIMARY KEY,              -- 'PA-' + uuid4
    portfolio_id     TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    as_of              TEXT NOT NULL,
    alert_type           TEXT NOT NULL CHECK (alert_type IN
                          ('data_freshness','signal_generation','portfolio_drift','risk_violation',
                           'execution_failure','position_concentration','drawdown','strategy_status','pnl_anomaly')),
    severity                TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
    message                    TEXT NOT NULL,
    details_json                  TEXT,
    acknowledged_at                 TEXT,
    acknowledged_by                   TEXT,
    generated_at                        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_portfolio_alerts_portfolio ON portfolio_alerts (portfolio_id, as_of);

-- ============================================================
-- PHASE 11: INSTITUTIONAL / FUND FOUNDATION
-- Data model ONLY. NOT LIVE. NOT REGULATED. NOT INVESTOR-READY.
-- NOT CONNECTED TO EXTERNAL CAPITAL. No row in these tables represents
-- a real fund, a real investor, or real money. This exists so that IF a
-- capacity-viable strategy is eventually validated, the data model to
-- represent a real fund already exists and does not require another
-- schema migration -- it does not itself constitute fund infrastructure.
-- ============================================================

CREATE TABLE IF NOT EXISTS funds (
    fund_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'CONCEPTUAL'
                       CHECK (status IN ('CONCEPTUAL')),   -- the ONLY legal value this build allows --
                                                           -- widening this CHECK is itself the explicit,
                                                           -- deliberate future act of going live, never
                                                           -- silently reachable from here
    base_currency      TEXT NOT NULL DEFAULT 'NGN',
    created_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategies (
    strategy_id    TEXT PRIMARY KEY,
    fund_id          TEXT REFERENCES funds(fund_id),
    name               TEXT NOT NULL,
    hypothesis_ids_json  TEXT,                      -- JSON array of registry.sqlite hypothesis_id references
    status                 TEXT NOT NULL DEFAULT 'RESEARCH'
                            CHECK (status IN ('RESEARCH','PAPER')),  -- 'LIVE' deliberately not a legal value yet
    created_at                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id     TEXT PRIMARY KEY,
    fund_id          TEXT REFERENCES funds(fund_id),
    portfolio_id       TEXT REFERENCES portfolios(portfolio_id),
    account_type          TEXT NOT NULL DEFAULT 'SIMULATED'
                           CHECK (account_type IN ('SIMULATED')),  -- only legal value
    created_at                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investors (
    investor_id    TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'PLACEHOLDER'
                        CHECK (status IN ('PLACEHOLDER')),  -- explicitly not a real onboarded investor
    created_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capital_allocations (
    capital_allocation_id  TEXT PRIMARY KEY,
    investor_id              TEXT REFERENCES investors(investor_id),
    account_id                 TEXT REFERENCES accounts(account_id),
    amount                        REAL NOT NULL,
    currency                        TEXT NOT NULL DEFAULT 'NGN',
    status                            TEXT NOT NULL DEFAULT 'SIMULATED'
                                       CHECK (status IN ('SIMULATED')),
    effective_date                       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance_periods (
    performance_period_id  TEXT PRIMARY KEY,
    portfolio_id              TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    period_start                TEXT NOT NULL,
    period_end                     TEXT NOT NULL,
    period_return                     REAL,
    track_record_status                 TEXT NOT NULL CHECK (track_record_status IN ('BACKTEST_ONLY','PAPER','LIVE'))
);

CREATE TABLE IF NOT EXISTS fee_schedules (
    fee_schedule_id  TEXT PRIMARY KEY,
    fund_id             TEXT REFERENCES funds(fund_id),
    management_fee_pct     REAL NOT NULL DEFAULT 0,
    performance_fee_pct       REAL NOT NULL DEFAULT 0,
    high_water_mark              INTEGER NOT NULL DEFAULT 1,
    status                          TEXT NOT NULL DEFAULT 'CONCEPTUAL'
                                     CHECK (status IN ('CONCEPTUAL')),
    notes                              TEXT NOT NULL DEFAULT
                                       'NOT LIVE. NOT REGULATED. NOT INVESTOR-READY. NOT CONNECTED TO EXTERNAL CAPITAL.'
);
