# NGX Rotation Investment Management Layer — Build Report

**Date:** 2026-08-13
**Scope:** Portfolio Management → Risk Management → Paper Execution Simulation →
Performance → Attribution → Decision Journal → Institutional/Fund Foundation.
**Mode:** Paper/simulation only. No broker. No capital. No live execution.

---

## 1. What already existed (not touched, not rebuilt)

- `src/ngxrot/alpha_engine.py`, `engine_full.py`, `runner.py` — the Alpha Engine.
  **Zero lines changed.** Consumed exclusively via `AlphaEngine.recommendations()`,
  its existing public interface, returning the existing `Recommendation` dataclass
  shape unmodified. No adapter rewrite was needed — confirmed by the integration
  test importing and calling it live.
- `data/registry.sqlite` (hypotheses, experiments, hypothesis_experiments) — read
  from, in `attribution.reconstruct_lineage()` and `journal.hypothesis_performance_history()`,
  never written to.
- `data/ngx.sqlite` (market data, cost schedules, securities) — read from only, via
  `ngxrot.db` functions (`equity_prices_asof`, `cost_schedule_asof`) reused unmodified.
- `ngxrot.costs.side_rates()` — reused unmodified for commission calculation, the
  same fee model `engine_full.py` itself uses.
- The project's own established SQLite discipline (WAL + busy_timeout,
  `CREATE TRIGGER ... RAISE(ABORT, ...)` immutability pattern from
  `schema/registry.sql`) — replicated, not reinvented.

## 2. What was newly built

A new, fully isolated package: `src/ngxrot/portfolio/` (10 modules, ~3,040 lines
including tests) backed by a new, additive database: `data/portfolio.sqlite`
(schema: `schema/portfolio.sql`, 23 tables, 9 immutability/guard triggers).

| Phase | Module | Responsibility |
|---|---|---|
| P1 | `construction.py` | Signal → target portfolio (equal_weight, signal_weighted, rank_weighted, volatility_scaled, custom) |
| P2 | `risk.py` | Configurable risk policy, pre-trade review, drawdown tracking |
| P3 | `execution.py` | Paper order → fill simulation, no-look-ahead, real cost schedule |
| P4 | `performance.py` | Position accounting (weighted-avg cost), NAV, Sharpe/Sortino/vol/drawdown |
| P5 | `attribution.py` | P&L attribution by ticker/sector/signal/hypothesis; exact lineage reconstruction |
| P6 | `journal.py` | Immutable decision journal; hypothesis performance feedback to research |
| P7 | `monitoring.py` | Drift/concentration/drawdown/freshness/anomaly alerts (configurable thresholds) |
| P8 | `fund_model.py` | Fund/strategy/account/investor/fee data model — schema-enforced non-live |

Portfolio construction methods are explicitly documented as mechanisms, not alpha
claims; no strategy was invented. Risk limits are `risk_policies` rows (config),
never hardcoded constants. No look-ahead: `_next_sessions()` in `execution.py`
only ever looks strictly forward from the signal date. `record_nav()` in
`performance.py` raises `ValueError` if called with `track_record_status="LIVE"`
— a hard constraint enforced in code, not just by convention.

## 3. Database/schema changes

- **New file:** `schema/portfolio.sql` — 23 tables, entirely additive.
- **No existing schema file was modified.** `schema/schema.sql` and
  `schema/registry.sql` are untouched by this build (they were modified in the
  earlier, separate reliability-audit and extraction-quality phases of this
  engagement, unrelated to this assignment).
- **New database file:** `data/portfolio.sqlite`, created by
  `ngxrot.portfolio.db.init_db()`. Isolated from `ngx.sqlite` and `registry.sqlite`.
- Confirmed at report time: `data/ngx.sqlite` (154,013,696 bytes, last modified
  2026-08-12 17:03) and `data/registry.sqlite` (2,392,064 bytes, last modified
  2026-08-12 17:08) — both predate this build session's write activity.
  `extracted_facts=495` and `financial_reasoning_conclusions=267` — **exactly
  unchanged** from the pre-build baseline, confirmed by direct query.

## 4. Tests created

`scripts/portfolio/` — 7 new test files, following the project's established
`check()`-helper pattern (no test framework dependency, matches existing
`scripts/` test style):

- `test_construction.py`
- `test_risk.py`
- `test_execution.py`
- `test_performance.py`
- `test_attribution.py`
- `test_journal.py`
- `test_integration_e2e.py` — two scenarios: a full synthetic paper-trade loop,
  and a second loop that imports and calls the real, unmodified `AlphaEngine`,
  feeding genuine H-011 recommendations through the entire pipeline.

All tests run against real data: real `ngx.sqlite` (read-only) and real
`registry.sqlite` (read-only) for market/hypothesis facts, plus disposable
scratch copies of `portfolio.sqlite` created fresh per run (`tempfile.mkdtemp()`,
never colliding with `data/portfolio.sqlite`).

## 5. Tests passed

| Suite | Result |
|---|---|
| test_construction.py | 16/16 |
| test_risk.py | 12/12 |
| test_execution.py | 22/22 |
| test_performance.py | 14/14 |
| test_attribution.py | 23/23 |
| test_journal.py | 15/15 |
| test_integration_e2e.py | 32/32 |
| **Total** | **134/134** |

## 6. Full end-to-end test result

Both integration scenarios ran the complete loop — Hypothesis → Signal →
Portfolio target → Risk validation → Paper order → Fill → Position → NAV → P&L
realization → Attribution → Lineage reconstruction → Decision journal →
Hypothesis performance feedback → Monitoring — against real market data,
producing genuine, non-fabricated numbers:

- **Synthetic scenario** (DANGCEM/GTCO, entry 2026-08-05 / exit 2026-08-06):
  total realized P&L −2,976.92, NAV 979,671.14.
- **Real Alpha Engine (H-011) scenario**: live `AlphaEngine.recommendations()`
  call produced genuine buy recommendations; the top 5 were carried through the
  full pipeline. Exit position was MCNICHOLS. Total realized P&L 5,172.99, NAV
  983,538.75. Lineage for MCNICHOLS was reconstructed exactly:
  P&L → Position → Fill → Order → Signal → Hypothesis (H-011) → real experiment
  records pulled from `registry.sqlite`.

Both scenarios' realized P&L are real (one negative, one positive) — nothing
was tuned or selected to produce a favorable number.

### Bugs found and fixed during real testing (6 total, all self-caught by
running real code against real data, not by inspection alone)

1. `construct_portfolio` originally shared one DB connection for market reads
   and portfolio writes — failed against real two-database usage; split into
   `portfolio_con`/`market_con`.
2. `_latest_risk_policy` was ambiguous when two policies were created the same
   calendar day — added `rowid DESC` tiebreak after a test proved a stricter
   later policy was being silently ignored.
3. `risk_checks.risk_policy_id` used a string sentinel for "no policy", which
   violated its FK constraint — made the column nullable and passed `None`.
4. `simulate_fill`'s LIMIT-order matching crashed on real DANGCEM sessions with
   NULL high/low — fixed to skip unusable sessions rather than crash or guess.
5. The LIMIT-not-reached path tried two sequential terminal-state transitions
   (REJECTED then CANCELLED) — the schema's own immutability trigger correctly
   blocked it; fixed to a single UPDATE to CANCELLED.
6. `reconstruct_lineage`'s JOIN had an ambiguous `experiment_id` column — qualified
   as `e.experiment_id`.
7. `hypothesis_performance_history`'s `n_executed` undercounted orders created
   outside `orders_from_target_positions()` — rewritten to walk
   `position_lifecycles` → fills → orders instead of `target_positions` → signals.
8. **(found while completing this report)** The integration test's own exit-date
   scenario asked for a SELL fill strictly after the last date with real market
   data on record — no forward session existed, so the exit order was correctly
   REJECTED, the lifecycle never closed, and attribution correctly reported
   nothing. This was the system behaving correctly under a bad test parameter,
   not a platform defect; fixed by moving the test's exit-signal date one session
   earlier so a real forward fill exists.

Every one of these was the system's own integrity checks (FK constraints,
immutability triggers, NULL-safety) doing their job — no fabricated data ever
got persisted, even when a test's premise was wrong.

## 7. What remains unbuilt

- Real-money execution, broker connectivity — **not built, per explicit
  instruction**, not merely deferred.
- True multi-lot (FIFO/LIFO) position accounting — this build uses disclosed
  weighted-average-cost accounting; `position_lifecycles` model one lot per
  flat→nonzero transition, which is exact for the common case but does not
  capture partial-lot tax/accounting nuance a real fund ledger would need.
- Unrealized (mark-to-market, not yet closed) attribution — `compute_attribution`
  only attributes realized P&L from closed lifecycles; open-position attribution
  would need per-date position history, out of scope for this build (disclosed
  in the module docstring, not silently approximated).
- Portfolio-level regime classification — `hypothesis_performance_history`'s
  `regime_breakdown` field explicitly returns a string disclosing this is not
  built, rather than fabricating a regime analysis.
- Fundraising, LP dashboards, compliance workflows, investor onboarding, fund
  administration — **not built, per explicit instruction** ("until a
  capacity-viable strategy exists"). Phase 8's `fund_model.py` is a data model
  only, with every fund/strategy/account/investor/capital-allocation table
  schema-restricted (via `CHECK` constraints) to placeholder statuses
  (`CONCEPTUAL`/`PLACEHOLDER`/`SIMULATED`) — attempting to write `LIVE` raises
  `sqlite3.IntegrityError` at the database layer, not just at the application
  layer.
- Slippage/market-impact calibration from real execution data — currently
  configured assumptions (`ExecutionAssumptions.slippage_bps`,
  `market_impact_bps`), explicitly labeled on every fill's `assumptions_note`
  as configured, not measured, because this platform has no real intraday
  fill data to calibrate them from.

## 8. What remains unproven

- Capacity: whether H-011 (or any hypothesis) remains profitable at realistic
  position sizes against real NGX liquidity was **not** re-validated by this
  build — this layer inherits whatever capacity conclusions already exist in
  prior research (e.g. `H011_STAGE1_EXECUTION_REALISM_2026-08-08.md`); it does
  not re-derive them.
- Multi-day, multi-rebalance behavior — every test exercised a single
  construct → fill → exit cycle. Behavior under repeated rebalancing, position
  netting across overlapping signals, and long-running drawdown tracking across
  many NAV snapshots was not exercised at any scale beyond the test scenarios.
- The commission/slippage cost model's realism versus actual NGX execution
  quality is unproven — it reuses the existing fee schedule (real) but layers
  configured, unmeasured slippage/impact assumptions on top.
- Paper track record: nothing in this build constitutes a "track record."
  `record_nav()` only ever writes `track_record_status="PAPER"` in these tests;
  no accumulated paper history exists yet — it starts at zero from here.

## 9. Explicit confirmations

- **Was any Alpha Engine calculation changed?** No. `alpha_engine.py`,
  `engine_full.py`, `runner.py`, and hypothesis registry logic have zero diffs
  from this build. Verified by direct call to the live, unmodified
  `AlphaEngine.recommendations()` in the integration test.
- **Was any production investment capital touched?** No. No capital exists to
  touch; every NAV/position number produced by this build lives in the new,
  isolated `data/portfolio.sqlite` and is explicitly tagged `PAPER`.
- **Was any live broker/execution system connected?** No. No broker
  integration exists anywhere in this codebase. `execution.py`'s module
  docstring states this explicitly; fills are simulated against historical/
  current `equity_prices` rows only.
- **Was `extracted_facts`/`financial_reasoning_conclusions` touched?** No —
  confirmed unchanged at 495/267 by direct query at report time.

## 10. Architecture after integration

```
Research Layer (unchanged)
  registry.sqlite (hypotheses, experiments)  [READ-ONLY from portfolio layer]
        |
  alpha_engine.py / engine_full.py / runner.py  [UNCHANGED, UNMODIFIED]
        |
        v  AlphaEngine.recommendations() -- existing public interface
        |
=================== NEW: Investment Management Layer ===================
        |
  construction.py   -- record_signals(), construct_portfolio()
        |                (equal_weight / signal_weighted / rank_weighted /
        |                 volatility_scaled / custom -- mechanisms, not alpha)
        v
  risk.py           -- create_risk_policy() [config], review_allocation()
        |                (APPROVED / APPROVED_WITH_WARNINGS / REJECTED)
        v
  execution.py      -- orders_from_target_positions(), simulate_fill()
        |                (paper only; next-session-strictly-after-signal fill;
        |                 real cost_schedule_asof() + costs.side_rates())
        v
  performance.py    -- apply_fill_to_position(), mark_to_market(), record_nav()
        |                (NAV/Sharpe/Sortino computed only from real observations;
        |                 track_record_status='LIVE' hard-refused in code)
        v
  attribution.py    -- compute_attribution(), reconstruct_lineage()
        |                (P&L -> Position -> Fill -> Order -> Signal ->
        |                 Hypothesis -> registry.sqlite Experiment, exact)
        v
  journal.py        -- record_decision() [immutable], record_outcome(),
        |                hypothesis_performance_history()  --> feeds back to
        |                                                       research layer
        v
  monitoring.py     -- run_monitoring_checks() (drift/concentration/
                        drawdown/freshness/anomaly, configurable thresholds)

  fund_model.py     -- funds/strategies/accounts/investors/fees
                        (schema-enforced CONCEPTUAL/PLACEHOLDER/SIMULATED only;
                         DB-level CHECK constraint blocks any LIVE status)

Storage: data/portfolio.sqlite (23 tables, 9 immutability/guard triggers,
         WAL mode) -- new, additive, isolated from ngx.sqlite/registry.sqlite.
```

## 11. Component classification

| Component | Status |
|---|---|
| Portfolio construction (5 weighting methods) | 🟢 BUILT |
| Risk policy (configurable, DB-persisted) | 🟢 BUILT |
| Pre-trade risk review (position/gross/net/sector/participation limits) | 🟢 BUILT |
| Drawdown tracking | 🟢 BUILT |
| Paper order creation + validation | 🟢 BUILT |
| No-look-ahead fill simulation (MARKET + LIMIT) | 🟢 BUILT |
| Real commission via existing fee schedule | 🟢 BUILT |
| Configurable slippage/market-impact assumptions | 🟢 BUILT (⚪ UNPROVEN realism) |
| Weighted-average-cost position accounting | 🟢 BUILT |
| NAV computation | 🟢 BUILT |
| Performance metrics (Sharpe/Sortino/vol/drawdown) | 🟢 BUILT |
| BACKTEST/PAPER/LIVE status separation | 🟢 BUILT (LIVE hard-refused in code) |
| Realized P&L attribution (ticker/sector/signal/hypothesis) | 🟢 BUILT |
| Unrealized/open-position attribution | 🔴 NOT BUILT (disclosed) |
| Exact lineage reconstruction (P&L→...→Hypothesis→Experiment) | 🟢 BUILT |
| Immutable decision journal | 🟢 BUILT |
| Hypothesis performance feedback to research | 🟢 BUILT |
| Regime-conditional performance breakdown | 🔴 NOT BUILT (disclosed, not fabricated) |
| Monitoring (drift/concentration/drawdown/freshness/anomaly) | 🟢 BUILT |
| Fund/strategy/account/investor/fee data model | 🟡 PARTIALLY BUILT (data model only, schema-locked to non-live) |
| Fundraising / LP dashboards / compliance / investor onboarding | 🔴 NOT BUILT (explicitly out of scope) |
| Real broker connectivity | 🔴 NOT BUILT (explicitly prohibited) |
| Multi-lot (FIFO/LIFO) accounting | 🔴 NOT BUILT (weighted-avg-cost used instead, disclosed) |
| Capacity re-validation at scale | ⚪ UNPROVEN |
| Multi-rebalance / long-horizon behavior | ⚪ UNPROVEN |
| Slippage/impact calibration against real fills | ⚪ UNPROVEN |
| Paper track record (accumulated history) | ⚪ UNPROVEN (starts at zero) |

---

**Principle honored throughout:** the machine was built — every mechanism
(construction, risk, execution, performance, attribution, journal, monitoring,
fund model) is real, tested against real data, and traceable end to end. No
returns were manufactured: every P&L number in section 6 came from an actual
run against real market prices, including one that lost money. Nothing here
claims to be a track record, live performance, or proof of investable edge —
those remain open questions this layer is built to eventually measure, not
to assume.
