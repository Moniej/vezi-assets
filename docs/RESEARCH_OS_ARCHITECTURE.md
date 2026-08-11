# Research OS Architecture

**Status**: Data-foundation infrastructure. No alpha hypothesis has been
run through any part of this system. This document describes the
laboratory, not an experiment.

---

## 1. Pipeline (unchanged)

```
NGX Pulse (+ other providers)
    -> DataProvider (base.py) / NGXPulseProvider
    -> ingest.py (the ONLY write path; validates against contracts.py)
    -> SQLite PIT database (data/ngx.sqlite)
    -> validated data
    -> Research OS (this layer)
```

No provider, ingestion path, or database was added or replaced building
this layer. Everything below reads from `data/ngx.sqlite` (market/
research data) and `data/registry.sqlite` (reproducibility ledger) --
both pre-existing files.

## 2. Layers, bottom to top

| Layer | Module | What it does |
|---|---|---|
| PIT readers | `db.py` | `*_asof()` (single sim_date, backtest-safe) and `*_range()` (date-window, research-facing) queries. Two time axes: `sim_date`/window (market knowledge) and `vintage` (our capture date). |
| Universe | `universe.py` | `iru_members()` -- rule-based, versioned, point-in-time eligible-security list (`configs/iru.toml`). |
| Identity | `instrument_identity.py` | Bridges ticker-rename chains (e.g. GTCO<-GUARANTY) using the existing `entities`/`entity_relationships` graph. Note: `universe.py` also has its own, older, CSV-based rename resolver (`rename_chain()`/`data/reference/symbol_renames.csv`) used for IRU liquidity aggregation -- the two are not merged; disclosed, not reconciled, in this pass. |
| Lineage | `lineage.py` | `trace_equity_observation()` composes security -> source -> endpoint -> ingestion run -> validation status purely from existing columns. |
| Data quality | `research_quality.py` | Composes `data_quality_log`, `corporate_actions`, `extracted_facts`, and live source-agreement checks into one report per ticker set/window. |
| Dataset access | `research_dataset.py` | `get_equity_dataset()`/`get_index_dataset()` -- the clean, research-facing query surface. Every call returns a `ResearchDataset` (data + provenance + reproducibility manifest). |
| Reproducibility | `registry.py` (existing) + `research_dataset.py`/`research_experiment.py` (new tables) | Immutable, insert-only records in `data/registry.sqlite`. |
| Experiment framework | `research_experiment.py` | Generic `hypothesis -> dataset -> universe -> period -> transformations -> analysis -> results -> reproducibility` shape. Deliberately separate from `registry.record_experiment`, which is alpha-backtest-shaped (requires signal/portfolio/cost config) and remains untouched. |

## 3. Data contracts

Unchanged. `contracts.py` still defines the required/optional columns and
validators for every dataset `ingest.py` accepts (`index_levels`,
`equity_prices`, `corporate_actions`, `index_membership`, `events`).
Nothing in the Research OS layer bypasses or duplicates this -- it is a
read-only layer on top of already-validated rows.

## 4. Identity model

A security may have traded under more than one ticker symbol (renames:
GTCO<-GUARANTY 2021-06-24, ACCESSCORP<-ACCESS 2022-03-28, FIRSTHOLDCO<-
FBNH 2025-03-10). Neither underlying price source bridges this on its
own -- each symbol's history simply stops/starts at the rename date.
`instrument_identity.resolve_ticker_history_symbols(con, ticker)` walks
the existing `entity_relationships` `renamed_from` edges to recover the
full chain; `full_price_history_query()` returns ready-to-run SQL that
unions every era, tagging each row with both its `original_ticker`
(never relabeled) and a `canonical_ticker`.

## 5. Lineage model

`lineage.trace_equity_observation(con, ticker, trade_date)` answers,
for any one observation:

- **source/endpoint**: `equity_prices.source_id` -> `sources.name/kind/
  reliability/url_template`
- **ingestion run**: the composite `(source_id, as_of_date)` -- there is
  no separate `ingestion_runs` table by design (every row from one
  `ingest.py` invocation already shares both fields; a surrogate table
  would duplicate information already fully recoverable, which the "no
  second ingestion architecture" constraint on this project argues
  against)
- **validation status**: a live join against `data_quality_log` by
  `(entity_type='ticker', entity_code, trade_date)`, classified
  `no_flags_found` / `flagged_and_resolved` / `flagged_unresolved`
- **transformation**: none is currently applied anywhere in this
  pipeline -- prices are raw/unadjusted end to end (see Section 6). This
  is itself part of the lineage answer, not an omission.

## 6. Data-quality visibility

`research_quality.quality_report(con, tickers, start, end)` composes,
per ticker set/window:

- **quality_flags** -- every relevant `data_quality_log` row (stale
  prices, unadjusted jumps, date-attribution drift, unresolved cases),
  unresolved first
- **missing_observations** -- trading days (per the NGXASI calendar)
  with no `equity_prices` row for that ticker
- **source_conflicts** -- (ticker, date) pairs where more than one
  source disagrees on close beyond a tolerance
- **identity_notes** -- rename-chain presence (reuses Section 4)
- **corporate_action_notes** -- real bonus/rights/dividend facts on
  file, from BOTH current representations (`corporate_actions`, quant
  layer -- currently synthetic-only fixture data; `extracted_facts`, FRE
  layer -- has real facts). These two tables are **not** synchronized;
  disclosed, not merged, in this pass (see `docs/fre_runs/
  ngxpulse_data_foundation_gaps_report.md` Section 1).

Confirmed this session: `ngx_pricelist_v2` and `ngx_pulse` both report
**raw, unadjusted** prices -- no split/bonus/rights adjustment is applied
anywhere in the pipeline. Any return calculation spanning a real
corporate action will show a spurious price jump unless the caller
consults `corporate_action_notes`/`quality_flags` first.

## 7. Reproducibility workflow

`data/registry.sqlite` now holds two independent reproducibility
mechanisms:

- **`experiments`/`hypotheses`** (pre-existing): immutable record of
  every completed alpha-backtest run, keyed to a `signal`/`portfolio`/
  `costs` config shape. Unchanged.
- **`dataset_snapshots`/`research_runs`** (new, this pass): generic,
  NOT alpha-shaped. `dataset_snapshots` pins the exact query params +
  a deterministic content hash of a `ResearchDataset`'s rows +
  `code_fingerprint` (existing `registry.code_fingerprint()`, SHA256
  over `src/`+`schema/`+`configs/`). `research_runs` pins a free-text
  research question, the `dataset_snapshot_ids` used, the universe
  version, and the results -- with no field assuming the question is a
  trading hypothesis.

Both new tables follow the exact immutability discipline already
established by `experiments`: `INSERT`-only, `UPDATE`/`DELETE` blocked by
trigger (`RAISE(ABORT, ...)`), verified live in `scripts/
test_research_os.py`.

**How a future researcher reproduces a result**: read the
`research_runs` row -> for each `dataset_snapshot_id`, read the
`dataset_snapshots` row -> re-run the exact `query_params` recorded
there (same `vintage`, same universe/tickers, same date range) -> compare
the new `content_hash` to the stored one. A match proves the underlying
data has not silently changed since the run; a mismatch is itself a
finding (a restatement, correction, or new ingestion touched that
window) and should be investigated before trusting the old result.

## 8. Worked example (descriptive, NOT alpha)

`scripts/test_research_os.py` exercises the full chain end to end with a
deliberately non-trading research question:

```python
ds = get_equity_dataset(con, "2024-01-01", "2024-01-10", tickers=["CILEASING"])
snap_id = ds.record_snapshot(reg, notes="...")
report = quality_report(con, ["CILEASING"], "2024-01-01", "2024-01-10")
spec = ExperimentSpec(
    research_question="What does the CILEASING data-quality profile look "
                      "like for 2024-01-01..2024-01-10?",
    dataset_snapshot_ids=[snap_id],
    transformations=[],  # none -- purely descriptive
    analysis_method="research_quality.quality_report composition",
)
run_id = record_research_run(reg, ExperimentResult(spec=spec, results=report))
```

This is the template a future alpha-research phase would extend --
adding real `transformations` (e.g. named feature-construction steps)
and a real `analysis_method` -- **not** something this pass populated
with any momentum/ranking/factor logic.

## 9. What this layer deliberately does NOT do

- Does not decide what counts as "interesting" in the data (no feature
  engineering, no signal construction, no scoring).
- Does not adjust prices for corporate actions (raw in, raw out;
  disclosed via `quality_report`, not silently corrected).
- Does not merge `corporate_actions` and `extracted_facts`.
- Does not replace or wrap `registry.record_experiment` -- that remains
  the alpha-backtest path, untouched.
- Does not introduce a new database, provider, or ingestion pipeline.
