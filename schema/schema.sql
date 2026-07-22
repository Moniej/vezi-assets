-- ============================================================================
-- NGX Sector Rotation — Data Schema (Phase 1)
-- Engine: SQLite (single-file, portable; trivially portable to Postgres later)
--
-- Design principles:
--   1. Point-in-time (PIT) correctness: every observational row carries
--      (source_id, as_of_date). as_of_date = the date we KNEW this value.
--      Restatements/corrections APPEND a new row with a later as_of_date;
--      nothing is ever overwritten. Backtest queries must filter
--      as_of_date <= knowledge_date and take the latest surviving row.
--   2. Lineage: no row without a source. Sources are a registry table.
--   3. Announcement vs effective dates are separate columns everywhere it
--      matters (events, reconstitutions, corporate actions). The backtest
--      may only act on information whose announcement date <= trade date.
--   3b. Confidence scoring: every observation carries confidence in [0,1],
--      defaulted from its source's base_confidence, overridable per row
--      (e.g. upgraded after cross-source verification). Scale convention:
--        1.0 exchange-official, cross-verified   0.9 exchange-official, single
--        0.7 reputable vendor                     0.5 aggregator (investing.com/TV)
--        0.4 manual/unverified                    0.3 web-archive reconstruction
--        0.0 SYNTHETIC/TEST — must never contribute to research conclusions.
--      Robustness tests re-run the backtest at rising min_confidence floors.
--   4. Honest limitation (do not paper over this): if history is
--      RECONSTRUCTED after the fact (e.g., constituent lists scraped from
--      web archives in 2026), as_of_date reflects when WE captured it, not
--      when the market knew it. PIT filtering on as_of_date protects against
--      future revisions; it cannot repair a wrong reconstruction. The
--      announced_date / effective_date columns are the real survivorship
--      defense and must be populated from period-appropriate documents.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 0. Source registry (data lineage)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id     INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,        -- e.g. 'ngx_website_daily_pricelist'
    kind          TEXT NOT NULL CHECK (kind IN
                    ('exchange_official','vendor','regulator','company_filing',
                     'web_archive','manual_entry','derived')),
    url_template  TEXT,                        -- where it came from, if applicable
    reliability   TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (reliability IN ('primary','secondary','unverified','synthetic')),
    base_confidence REAL NOT NULL DEFAULT 0.4
                    CHECK (base_confidence >= 0.0 AND base_confidence <= 1.0),
    notes         TEXT
);

-- ----------------------------------------------------------------------------
-- 1. Reference: indices and securities
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indices (
    index_code    TEXT PRIMARY KEY,            -- 'NGXASI','NGXBNK','NGXINS','NGXOILGAS',
                                               -- 'NGXINDUSTR','NGXCNSMRGDS','NGXPREMIUM',
                                               -- 'NGXPENSION','NGX30'
    name          TEXT NOT NULL,
    weighting     TEXT NOT NULL CHECK (weighting IN
                    ('full_mcap','float_adjusted_mcap','capped_float_mcap','price','equal')),
    cap_pct       REAL,                        -- single-stock cap if capped (e.g. NGX30)
    base_date     TEXT,                        -- ISO date; also = earliest possible history
    base_value    REAL,
    is_total_return INTEGER NOT NULL DEFAULT 0, -- 1 if the published series reinvests divs
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS securities (
    ticker        TEXT PRIMARY KEY,            -- NGX symbol, e.g. 'ZENITHBANK'
    isin          TEXT,
    name          TEXT NOT NULL,
    board         TEXT CHECK (board IN ('main','premium','growth','asem','delisted_unknown')),
    listing_date  TEXT,
    delisting_date TEXT,                       -- NULL if still listed. NEVER delete delisted
                                               -- rows: they are the survivorship-bias defense.
    delisting_reason TEXT,                     -- 'voluntary','regulatory','merger','nationalised',...
    sector_ngx    TEXT,                        -- NGX's own sector classification label
    notes         TEXT
);

-- ----------------------------------------------------------------------------
-- 2. Index level data (daily closes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS index_levels (
    index_code    TEXT NOT NULL REFERENCES indices(index_code),
    trade_date    TEXT NOT NULL,               -- ISO 'YYYY-MM-DD'
    close_value   REAL NOT NULL CHECK (close_value > 0),
    currency      TEXT NOT NULL DEFAULT 'NGN',
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,               -- when this value was captured/known by us
    inserted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (index_code, trade_date, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_index_levels_lookup
    ON index_levels (index_code, trade_date, as_of_date);

-- ----------------------------------------------------------------------------
-- 3. Constituent-level daily prices (what we can actually trade)
--    value_traded is the critical field: it drives ADTV-based capacity
--    constraints in Phase 3.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equity_prices (
    ticker        TEXT NOT NULL REFERENCES securities(ticker),
    trade_date    TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL NOT NULL CHECK (close > 0),
    volume        INTEGER,                     -- shares
    value_traded  REAL,                        -- NGN turnover that day (for ADTV)
    deals         INTEGER,                     -- number of trades (thin-market diagnostic)
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,
    inserted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (ticker, trade_date, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_equity_prices_lookup
    ON equity_prices (ticker, trade_date, as_of_date);

-- ----------------------------------------------------------------------------
-- 4. Index membership (intervals) and periodic weight snapshots
--    Membership = which stocks were in which index and WHEN (reconstitution
--    history). Weights drift daily with prices, so exact weights are stored
--    as dated snapshots (NGX publishes at reviews); daily weights between
--    snapshots are DERIVED (mcap-proportional) and marked as such via source.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS index_membership (
    index_code     TEXT NOT NULL REFERENCES indices(index_code),
    ticker         TEXT NOT NULL REFERENCES securities(ticker),
    effective_from TEXT NOT NULL,              -- date membership took effect
    effective_to   TEXT,                       -- NULL = still a member
    announced_date TEXT,                       -- when the review result was PUBLIC.
                                               -- Backtest may not use membership
                                               -- before this date. NULL = unknown
                                               -- (treated as effective_from).
    reason_in      TEXT,                       -- 'index_launch','review_add','ipo',...
    reason_out     TEXT,                       -- 'review_drop','delisting','merger',...
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL,
    PRIMARY KEY (index_code, ticker, effective_from, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_membership_lookup
    ON index_membership (index_code, effective_from, effective_to);

CREATE TABLE IF NOT EXISTS constituent_weights (
    index_code     TEXT NOT NULL REFERENCES indices(index_code),
    ticker         TEXT NOT NULL REFERENCES securities(ticker),
    snapshot_date  TEXT NOT NULL,              -- date the weight applies to
    weight         REAL NOT NULL CHECK (weight >= 0 AND weight <= 1),
    free_float_pct REAL,                       -- float factor if known
    is_derived     INTEGER NOT NULL DEFAULT 0, -- 1 = we computed it, not published
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL,
    PRIMARY KEY (index_code, ticker, snapshot_date, source_id, as_of_date)
);

-- ----------------------------------------------------------------------------
-- 5. Corporate actions
--    NGX mechanics: price is marked down on the QUALIFICATION date (NGX's
--    ex-date analogue). Total-return adjustment keys off markdown_date.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id      INTEGER PRIMARY KEY,
    ticker         TEXT NOT NULL REFERENCES securities(ticker),
    action_type    TEXT NOT NULL CHECK (action_type IN
                     ('dividend_cash','dividend_interim','dividend_scrip','bonus',
                      'stock_split','reverse_split','rights_issue','public_offer',
                      'private_placement','share_reconstruction','delisting',
                      'suspension','resumption','merger','capital_return')),
    declared_date  TEXT,                       -- announcement (PIT anchor)
    qualification_date TEXT,                   -- NGX qualification/closure-of-register
    markdown_date  TEXT,                       -- date price adjusts on the board
    payment_date   TEXT,
    dividend_per_share REAL,                   -- NGN, for dividend_*
    ratio_new      REAL,                       -- for bonus/split/rights: new shares...
    ratio_old      REAL,                       -- ...per old shares (e.g. bonus 1-for-4)
    rights_price   REAL,                       -- subscription price for rights
    currency       TEXT NOT NULL DEFAULT 'NGN',
    withholding_tax_pct REAL DEFAULT 10.0,     -- NGN dividend WHT (confirm rate/applicability)
    details        TEXT,
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_corp_actions_ticker
    ON corporate_actions (ticker, markdown_date);

-- ----------------------------------------------------------------------------
-- 6. Regulatory / macro event calendar
--    announced_date vs effective_date is the whole point of this table:
--    e.g. CBN recapitalisation circular announced 2024-03-28, deadline
--    2026-03-31. A catalyst filter may react on 2024-03-28, not before.
-- ----------------------------------------------------------------------------
-- Event types are validated against configs/event_taxonomy.toml by the event
-- pipeline (ngxrot/event_pipeline.py), NOT by a CHECK constraint — the
-- taxonomy is configurable per the H-003 research design. Chronology,
-- duplicate, and cross-source-conflict checks also live in the pipeline.
CREATE TABLE IF NOT EXISTS events (
    event_id       INTEGER PRIMARY KEY,
    event_type     TEXT NOT NULL,             -- taxonomy leaf (pipeline-validated)
    event_uid      TEXT,                      -- stable source-assigned ID (e.g.
                                              -- 'CBN-MPC-295'). Restatements share
                                              -- the uid; PIT reads keep the latest
                                              -- as_of per uid. NULL = no uid known.
    category       TEXT,                      -- taxonomy branch: monetary/banking/...
    announced_date TEXT NOT NULL,             -- when the market learned of it
    effective_date TEXT,                      -- when it takes/took effect (NULL = unknown)
    publication_ts TEXT,                      -- exact publication timestamp if knowable
    scope          TEXT NOT NULL CHECK (scope IN ('market','sector','ticker')),
    index_code     TEXT REFERENCES indices(index_code),   -- if sector-scoped
    ticker         TEXT REFERENCES securities(ticker),    -- if ticker-scoped
    headline       TEXT NOT NULL,
    outcome_numeric REAL,                     -- e.g. MPR level after MPC (27.50)
    outcome_text   TEXT,                      -- e.g. 'hold', 'hike +50bps'
    severity       TEXT CHECK (severity IN ('low','medium','high','critical')),
    direction      TEXT NOT NULL DEFAULT 'unknown'
                     CHECK (direction IN ('bullish','bearish','neutral','unknown')),
    structurally_impairing INTEGER NOT NULL DEFAULT 0,
    source_url     TEXT,                      -- primary document URL where possible
    notes          TEXT,                      -- supporting notes incl. verification trail
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_dates ON events (announced_date, event_type);

-- ----------------------------------------------------------------------------
-- 7. FX rates (regime definition + real-return sanity checks)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fx_rates (
    trade_date    TEXT NOT NULL,
    rate_type     TEXT NOT NULL CHECK (rate_type IN ('official','nafem','parallel')),
    ngn_per_usd   REAL NOT NULL CHECK (ngn_per_usd > 0),
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,
    PRIMARY KEY (trade_date, rate_type, source_id, as_of_date)
);

-- ----------------------------------------------------------------------------
-- 7b. Generic macro/commodity daily series (Brent, T-bills, CPI level, ...)
--     Reusable home for any external daily/periodic series feeding models.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS macro_series (
    series_code   TEXT NOT NULL,               -- 'BRENT', 'NGN_TBILL_91D', ...
    trade_date    TEXT NOT NULL,
    value         REAL NOT NULL,
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,
    PRIMARY KEY (series_code, trade_date, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_macro_series ON macro_series (series_code, trade_date);

-- ----------------------------------------------------------------------------
-- 8. Transaction cost schedule (effective-dated, overridable — Phase 3 input)
--    Seeded with ASSUMED NGX retail fee stack; every rate must be confirmed
--    against a real broker contract note before results are trusted.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cost_schedule (
    fee_name       TEXT NOT NULL,              -- 'brokerage','sec_fee','ngx_fee',
                                               -- 'cscs_fee','stamp_duty','vat'
    side           TEXT NOT NULL CHECK (side IN ('buy','sell','both')),
    rate_pct       REAL NOT NULL,              -- % of trade value (VAT: % of fees)
    applies_to     TEXT NOT NULL DEFAULT 'trade_value'
                     CHECK (applies_to IN ('trade_value','commission_and_fees')),
    effective_from TEXT NOT NULL,
    effective_to   TEXT,
    confidence     TEXT NOT NULL DEFAULT 'assumed'
                     CHECK (confidence IN ('confirmed','assumed')),
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    notes          TEXT,
    PRIMARY KEY (fee_name, side, effective_from)
);

-- ----------------------------------------------------------------------------
-- 9. Data quality log (Phase 3 diagnostics write here)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_quality_log (
    check_name    TEXT NOT NULL,               -- 'unadjusted_jump','stale_series',
                                               -- 'missing_days','weight_sum_error',...
    entity_type   TEXT NOT NULL CHECK (entity_type IN ('index','ticker')),
    entity_code   TEXT NOT NULL,
    trade_date    TEXT,
    severity      TEXT NOT NULL CHECK (severity IN ('info','warn','error')),
    detail        TEXT,
    resolved      INTEGER NOT NULL DEFAULT 0,
    logged_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- Point-in-time views: latest as_of per (entity, trade_date).
-- The Python layer exposes as-of-a-knowledge-date variants of these.
-- ----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_index_levels_latest AS
SELECT il.*
FROM index_levels il
JOIN (
    SELECT index_code, trade_date, MAX(as_of_date) AS max_asof
    FROM index_levels GROUP BY index_code, trade_date
) m ON il.index_code = m.index_code
   AND il.trade_date = m.trade_date
   AND il.as_of_date = m.max_asof;

CREATE VIEW IF NOT EXISTS v_equity_prices_latest AS
SELECT ep.*
FROM equity_prices ep
JOIN (
    SELECT ticker, trade_date, MAX(as_of_date) AS max_asof
    FROM equity_prices GROUP BY ticker, trade_date
) m ON ep.ticker = m.ticker
   AND ep.trade_date = m.trade_date
   AND ep.as_of_date = m.max_asof;
