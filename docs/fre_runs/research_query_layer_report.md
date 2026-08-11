# Research Query Layer -- Phase 2 Report

**Date**: 2026-08-10
**Follows**: `docs/fre_runs/research_os_infrastructure_report.md` (Phase 1:
dataset access, data-quality visibility, reproducibility, generic
experiment framework -- all still in place, unmodified in logic).
**Explicitly out of scope, and none of it was done**: momentum signals,
relative-strength signals, sector-rotation signals, alpha factors,
portfolio construction, trading strategies, strategy optimization, alpha
backtests, predictive models.

---

## 0. Architectural assessment (performed before writing any code)

Inspected the full existing repository before implementing anything.
Summary (full detail in `docs/RESEARCH_OS_ARCHITECTURE.md`, still
current):

- **Providers**: `providers/base.py` (`DataProvider` ABC, `.fetch()`
  dispatch), `providers/ngxpulse.py` (`NGXPulseProvider`). Untouched.
- **Ingestion**: `ingest.py` remains the sole write path;
  `contracts.py` remains the sole schema-validation authority. Untouched.
- **SQLite PIT**: `db.py` -- two time axes (`sim_date`/market-knowledge,
  `vintage`/capture-knowledge), `*_asof` (single-date, backtest-safe) and
  Phase-1's `*_range` (date-window, research-facing) readers. Extended
  with no new axis or semantics.
- **Identity**: `instrument_identity.py` (Phase 1, entity-graph-based
  rename bridging) -- reused directly, not duplicated. Note:
  `universe.py` also has an older, separate CSV-based `rename_chain()`
  used internally for IRU liquidity aggregation; this remains a disclosed,
  unreconciled duplication from before this phase, not created by it.
- **Lineage**: `lineage.py` (Phase 1, `trace_equity_observation`) --
  reused directly for single-observation drill-down provenance.
- **Data-quality system**: `data_quality_log` (pre-existing) +
  `research_quality.py` (Phase 1) -- reused for corporate-action
  cross-referencing; not duplicated.
- **Universe/registry/ledger**: `universe.py` (rule-based, versioned
  IRU) reused directly for the `universe_history` query type;
  `registry.py` (`experiments`/`hypotheses`, alpha-backtest-shaped) left
  untouched; Phase 1's `dataset_snapshots`/`research_runs` (generic)
  available but not required by this layer -- this layer has its own
  lighter-weight `query_log` (Section 6 below) for automatic per-query
  reproducibility, distinct from the heavier explicit
  hypothesis-to-results recording Phase 1 built.
- **Existing research infra**: Phase 1's `research_dataset.py`/
  `research_quality.py`/`research_experiment.py` -- this layer sits
  directly on top, does not reimplement dataset access.
- **Existing backtest infra**: `backtest_lite.py`/`backtest_xs.py`/
  `engine_full.py`/`alpha_engine.py` -- inspected, confirmed untouched
  and unreferenced by anything built this phase.
- **Tests**: plain `scripts/test_*.py` scripts with an inline
  `check(name, condition)` runner (no pytest), invoked via
  `PYTHONPATH=src python scripts/test_*.py` -- followed exactly.

**Where the Research Query Layer plugs in**: as one new module,
`src/ngxrot/research_query.py`, sitting directly on top of the Phase-1
infrastructure and the pre-existing PIT/identity/universe layers. No
existing module was replaced; `db.py` gained two small helper functions
in Phase 1 and none in this phase.

## 1. What was built

### 1a. `src/ngxrot/research_query.py` (new)

- `QuerySpec`/`QueryResult`/`EntityResolution` dataclasses -- the
  structured contract requested.
- `validate_spec()`: date validity, `start<=end`, field-registry
  enforcement (rejects anything not actually in the schema -- confirmed
  `market_cap`/`dividend_yield` do not exist anywhere in this database
  and are excluded from `FIELD_REGISTRIES`, not faked), entity existence,
  look-ahead rejection (`end > as_of`), non-positive `limit` rejection,
  and an explicit historical-classification-unavailable warning for
  backward-looking sector queries (since `securities.sector_ngx` has no
  historical versioning anywhere in this schema).
- `resolve_entity()`: thin wrapper over `instrument_identity.
  resolve_ticker_history_symbols` -- confirmed no second
  ticker-resolution mechanism was introduced.
- Six query types: `query_prices`, `query_cross_section`,
  `query_universe_history`, `query_compare`, `query_metadata`,
  `query_entity_lookup`, dispatched via `execute()`.
- Descriptive (non-alpha) calculations: `abs_change`, `pct_change`,
  `rolling_stats`, `drawdown`, `observation_counts`.
- Provenance: batch summary per query (source name/kind/reliability, row
  counts, date ranges) plus direct pass-through to `lineage.
  trace_equity_observation()` for single-observation drill-down.
- `_log_query()`: automatic, lightweight logging of every executed
  query to the new `query_log` table.

### 1b. `schema/registry.sql` (modified, additive)

New `query_log` table + 2 immutability triggers, in the **existing**
`data/registry.sqlite` (no new database). Same insert-only discipline as
every other table in this file.

**Real, separate bug found and fixed**: `hypothesis_experiments` was
referenced by the `no_experiments_on_frozen` trigger ~30 lines before
its own `CREATE TABLE` -- this predates this phase (found while building
Phase 1, actually; re-verified still fine here) -- no new instance of
this class of bug was introduced.

### 1c. `scripts/ngxrot_research.py` (new) -- CLI

Six subcommands (`prices`, `sector`, `compare`, `universe`, `lookup`,
`metadata`), `--format table|json|csv`, `--no-log`. Follows the existing
`scripts/*.py` argparse convention (e.g. `ngxpulse_ingest.py`) rather
than introducing a packaged console-script framework.

### 1d. Python API

`from ngxrot.research_query import QuerySpec, execute` -- documented
with a worked example in `docs/research_query_layer.md` Section 11.

### 1e. Documentation

`docs/research_query_layer.md` -- architecture, query model, PIT
semantics, entity resolution, all 6 query types, descriptive
calculations, provenance, guardrails, reproducibility, CLI, Python API,
output formats, SQL-access hierarchy, measured performance, disclosed
limitations, examples, testing.

## 2. Real bugs found and fixed during development

1. **`as_of`/`vintage` conflation** (query_prices, query_cross_section,
   query_universe_history): an early draft passed the researcher's
   `as_of` into the underlying reader's `vintage` parameter as well as
   the trade-date cutoff. Since most historical data in this database
   was captured (backfilled) in 2026 regardless of trade date,
   restricting `vintage` to a historical `as_of` silently excluded
   nearly all data -- a CONSUMER GOODS sector query for `2025-01-01`
   returned **0 rows** instead of ~19. Fixed by leaving `vintage`
   unrestricted in all three query types; `as_of` now correctly maps
   only to the trade-date/observation-availability axis. Caught by
   manual smoke-testing before any automated test existed, then
   permanently covered by `scripts/test_research_query.py`.
2. **`content_hash()` crash on list-valued cells**: `entity_lookup`
   results include a `full_chain` list column, which pandas cannot sort
   directly (`TypeError: unhashable type: 'list'`). Fixed by
   stringifying all cells purely for the hash computation (the returned
   `observations` DataFrame itself is never mutated).
3. **`cross_section` returning full history, not a snapshot**: the first
   implementation called `db.equity_prices_asof()` (correct for a
   backtest's day-by-day walk, which needs the *entire* PIT-filtered
   history up to `sim_date`) and expected one row per ticker back. It
   actually returned **37,040 rows** for a 19-ticker sector query (every
   historical observation up to the cutoff, for every ticker) instead of
   19. Fixed with a dedicated two-step SQL reduction (`_latest_snapshot_
   per_ticker`) that resolves directly to the latest observation per
   ticker at/before `as_of` -- this also fixed a real performance problem
   (Section 3).

All three were caught by hands-on smoke-testing against real data before
being written into `scripts/test_research_query.py`'s guardrail/
correctness checks, so they cannot silently regress.

## 3. Performance (measured)

| query | time |
|---|---|
| entity lookup | ~19ms |
| single-stock history, 2yr | ~37ms |
| multi-stock history, 10 tickers, 2yr | ~763ms |
| sector cross-section (19 tickers), before fix | ~4,180ms |
| sector cross-section (19 tickers), after fix | ~599ms (7x) |
| large date-range (single ticker, 10yr) | ~42ms |
| PIT universe query (IRU) | ~298ms |

All comfortably interactive. **No PostgreSQL migration is justified** --
documented per the spec's explicit instruction rather than solved for
hypothetically.

## 4. Tests

`scripts/test_research_query.py`, **29/29 passing**: all six query
types against real data, PIT correctness (as-of, look-ahead rejection,
historical identity via GTCO/GUARANTY, real NGX index membership),
guardrails (invalid dates, unsupported field, unknown entity,
non-positive limit), descriptive-calculation correctness, provenance
population, reproducibility (identical query -> identical content hash),
`query_log` population and immutability (trigger-verified), and an
explicit assertion that the NGX Pulse API key never appears in any
logged query parameters.

`scripts/research_query_integration_test.py` (Section 22 of the spec):
genuine end-to-end run of "show historical price observations for a
representative set of NGX companies... preserving source lineage" through
validation -> entity resolution -> PIT query -> SQLite -> lineage ->
`QueryResult` -> reproduction -> `query_log`. **PASSED** -- 2,896
observations across 6 real tickers, multi-source lineage correctly
resolved and disclosed (`ngx_dol_v1`/`ngx_list2_v1`/`ngx_pricelist_v2`/
`ngx_pulse` contributing different date ranges per ticker), single-
observation drill-down demonstrated, identical content hash on re-run.

**Regression** (all prior suites re-run, unaffected):

| Suite | Result |
|---|---|
| `scripts/test_instrument_identity.py` | 20/20 |
| `scripts/test_lineage.py` | 10/10 |
| `scripts/test_ngxpulse_provider.py` | 31/31 |
| `scripts/test_research_os.py` | 19/19 |
| `scripts/test_research_query.py` (new) | 29/29 |
| **Total** | **109/109** |

## 5. Files changed

New:
- `src/ngxrot/research_query.py`
- `scripts/ngxrot_research.py`
- `scripts/test_research_query.py`
- `scripts/research_query_integration_test.py`
- `docs/research_query_layer.md`
- `docs/fre_runs/research_query_layer_report.md` (this file)

Modified:
- `schema/registry.sql` (one new table + two triggers, additive)

No existing provider, ingestion path, identity system, lineage system,
or backtest module was modified.

## 6. Architectural decisions worth flagging

- **`query_log` vs Phase 1's `research_runs`**: deliberately separate.
  `query_log` is automatic and lightweight (every `execute()` call, no
  explicit researcher effort); `research_runs` is explicit and heavier
  (a researcher deliberately records a question + results). Both are
  useful; neither replaces the other.
- **Batch, not per-row, provenance**: chosen for performance -- a
  per-row `lineage.trace_equity_observation()` call for a multi-thousand-
  row result would be prohibitively slow. Full per-observation detail
  remains one function call away when actually needed.
- **`as_of` maps to `sim_date`, never `vintage`**: a deliberate choice,
  documented in Section 3 of `docs/research_query_layer.md`, distinct
  from strict capture-vintage freezing (served separately by Phase 1's
  snapshot mechanism).

## 7. Known limitations (disclosed, not resolved this pass)

- No historical sector versioning exists in the schema -- every
  backward-looking sector query warns about this; it cannot be fixed
  without new source data, which is out of scope.
- `corporate_actions`/`extracted_facts` desynchronization (Phase 1
  finding) is unaffected.
- `instrument_identity.py`'s entity-graph resolution and `universe.py`'s
  separate CSV-based rename resolver remain two independent, unmerged
  mechanisms (also a Phase 1 finding, unchanged).
- Field support is intentionally narrow -- anything genuinely absent
  from the schema (market cap, dividend yield, etc.) is rejected, not
  approximated.

## 8. Example of a successful research query (from the integration test)

```
prices(entities=["GTCO","ZENITHBANK","DANGCEM","MTNN","BUAFOODS","SEPLAT"],
       start="2023-01-01", end="2024-12-31", fields=["close","volume"])
-> 2,896 observations, 4 distinct sources correctly attributed per
   ticker/date-range, content_hash reproducible on re-run,
   GTCO's pre-2021 GUARANTY-era identity correctly surfaced in
   entities_resolved even though GTCO itself was the only requested symbol.
```

---

## STOP

This closes the requested Research Query Layer. **No alpha research was
started** -- no momentum, relative-strength, sector-ranking, factor,
portfolio-construction, strategy, or predictive-modelling code exists
anywhere in this codebase as a result of this phase. The next phase
should only begin after an explicit decision to proceed.
