# Research Query Layer

**Status**: Infrastructure. No alpha hypothesis, signal, factor, ranking,
or predictive model has been implemented anywhere in this layer.

---

## 1. Architecture

```
Data Sources -> Providers -> DataProvider -> ingest.py -> SQLite PIT
    -> identity / lineage / quality (Phase 1: instrument_identity.py,
       lineage.py, research_quality.py, research_dataset.py, universe.py)
    ══════════════════════════════════════════════════════════════
                      RESEARCH QUERY LAYER (this doc)
    ══════════════════════════════════════════════════════════════
    -> Research Questions -> Structured Results -> Evidence/Provenance
```

`src/ngxrot/research_query.py` is the ONLY new module. It sits directly
on top of the Phase-1 Research OS infrastructure and the pre-existing
PIT/identity/universe layers -- it does not reimplement any of them.

```
Query Interface (CLI / Python API)
      |
Query Specification (QuerySpec)
      |
Query Planner / Validator (validate_spec: dates, fields, entities,
      |                     look-ahead, survivorship)
Data Access Layer (db.py's *_range/*_asof readers, universe.iru_members)
      |
PIT / Identity / Metadata (db.py two-axis PIT, instrument_identity.py,
      |                     securities table)
Result Builder (QueryResult)
      |
Provenance / Evidence (sources table + lineage.py)
```

No PostgreSQL, no second database, no second provider abstraction, no
second ingestion pipeline, no second identity system, no second lineage
system.

## 2. Query model

### `QuerySpec`

| field | meaning |
|---|---|
| `query_type` | `prices`\|`cross_section`\|`universe_history`\|`compare`\|`metadata`\|`entity_lookup` |
| `entities` | ticker(s), or an index code for `universe_history` |
| `entity_kind` | `ticker`\|`sector`\|`index` |
| `start`/`end` | observation date range |
| `as_of` | information-availability cutoff (see Section 3) |
| `fields` | must be in `FIELD_REGISTRIES` -- unknown fields (e.g. `market_cap`, which does not exist anywhere in this schema) are rejected, never fabricated |
| `filters` | e.g. `{"sector": "CONSUMER GOODS"}` |
| `group_by`/`sort_by`/`limit` | result shaping |
| `min_confidence`/`sources` | same semantics as the underlying `db.py` PIT readers |

### `QueryResult`

`query_id`, `query_type`, `parameters`, `entities_requested`,
`entities_resolved` (requested identity **and** resolved/canonical
identity, per-entity), `observations` (DataFrame), `row_count`,
`date_range`, `data_sources`, `warnings`, `provenance`,
`execution_metadata`. `.content_hash()` gives a deterministic hash for
reproducibility checks; `.to_json()`/`.to_csv()` for output.

## 3. PIT semantics -- `as_of` vs `vintage`

`db.py` already models two independent time axes (documented at the top
of that file): `sim_date` (what the **market** knew -- `trade_date <=
sim_date`) and `vintage` (what **we** captured -- `as_of_date <=
vintage`). `QuerySpec.as_of` maps to the **first** axis (`sim_date`):
"don't show me observations dated after this point." `vintage` is
deliberately left unrestricted by every query type in this layer -- a
researcher asking "what happened by 2023-06-30" wants the best-known,
most-corrected record of that period, not an artificially frozen capture
snapshot. Freezing capture vintage for strict point-in-time
reproducibility is a separate concern already served by Phase 1's
`research_dataset.ResearchDataset.record_snapshot()` (content-hash
based), and by this layer's own `query_log` (Section 9).

**A real bug found and fixed while building this**: an early draft
passed `as_of` into BOTH `sim_date` and `vintage` parameters. Since most
of this database's historical data was backfilled in 2026 (long after
the trade dates themselves), restricting `vintage` to a historical
`as_of` silently excluded almost everything -- a `cross_section` query
for `2025-01-01` returned **0 rows** instead of ~19. Fixed by never
passing `as_of` into `vintage`; caught by manual smoke-testing before any
automated test was written, then covered by
`scripts/test_research_query.py`.

**Look-ahead is rejected, not silently corrected**: if `end > as_of`,
`validate_spec` raises `QueryValidationError` outright. Truncating the
range instead would itself be an undisclosed transformation of the
request (Section 13 of the original spec).

## 4. Entity resolution

Delegates entirely to `instrument_identity.resolve_ticker_history_symbols`
(Phase 1). `resolve_entity()` never invents a second ticker-matching
mechanism. `EntityResolution` exposes both the **requested** identifier
and the **resolved/canonical** one plus the full rename chain -- e.g.
looking up `GTCO` returns `canonical='GTCO'`, `full_chain=['GUARANTY',
'GTCO']`; looking up `GUARANTY` directly also resolves (both symbols are
real rows in `securities`), with the same full chain. A nonexistent
ticker is reported `found=False`, never guessed from string similarity.

## 5. Core query types

| type | function | example |
|---|---|---|
| entity lookup | `query_entity_lookup` | resolve `GTCO`/`GUARANTY`/sector/index identifiers |
| time-series | `query_prices` | GTCO close/volume, 2020-2025 |
| cross-sectional | `query_cross_section` | all CONSUMER GOODS companies as of 2025-01-01 (one row per ticker -- the **latest** observation at/before `as_of`, resolved directly in SQL, not by materializing full history and trimming in Python -- a real 7x performance fix, see Section 8) |
| historical universe | `query_universe_history` | IRU membership (`filters={"universe": "iru"}`) or a real NGX index's constituents (`entity_kind="index"`, e.g. `NGXBNK`) as of a date |
| comparison | `query_compare` | GTCO vs ZENITHBANK vs ACCESSCORP, 2023-2025 -- adds a **descriptive** per-ticker summary (n_observations, first/last value, total_pct_change); no ranking, no score |
| metadata | `query_metadata` | sector, board, listing date, rename chain for one or more tickers |

Event/corporate-action queries (spec item F) are served by the existing
Phase-1 `research_quality.corporate_action_notes`/`quality_flags`, not
duplicated here -- call those directly for that purpose.

## 6. Descriptive (non-alpha) calculations

`abs_change`, `pct_change`, `rolling_stats` (mean/median/min/max/std),
`drawdown`, `observation_counts`. Pure, generic, appliable to any
series -- **not** momentum factors, alpha scores, or trading signals.
`query_compare`'s summary uses `total_pct_change` as a descriptive
statistic only.

## 7. Provenance

Two levels, both reusing Phase-1's `lineage.py` (no second provenance
framework):

- **Batch summary** (`QueryResult.provenance`): one entry per (ticker,
  source_id) actually present in the result -- source name/kind/
  reliability, row count, date range. Computed once per query, not once
  per row (would be O(n) against `lineage.trace_equity_observation` for
  a large result set).
- **Single-observation drill-down**: call
  `lineage.trace_equity_observation(con, ticker, trade_date)` directly
  for the full chain (ingestion run, validation status/flags) on any one
  observation. `scripts/research_query_integration_test.py` demonstrates
  both levels together.

## 8. Guardrails (validated, not assumed)

- invalid/malformed dates, `start > end` -- rejected
- unknown ticker/sector/index -- rejected with a specific message
- unsupported field (anything not in `FIELD_REGISTRIES`, e.g.
  `market_cap`/`dividend_yield` -- absent from this schema) -- rejected,
  never silently dropped
- look-ahead (`end > as_of`) -- rejected
- non-positive `limit` -- rejected
- historical sector/cross-section query -- **warned**, not rejected:
  `securities.sector_ngx` carries no historical versioning anywhere in
  this schema (`sector_ngx_provenance` records only where the *current*
  value came from), so any `as_of` in the past triggers an explicit
  warning rather than silently assuming today's classification applied
  historically

All covered by `scripts/test_research_query.py`'s guardrail checks.

## 9. Reproducibility / query logging

Every `execute()` call (unless `log=False`) writes one row to
`query_log` (new table, `schema/registry.sql`, in the **existing**
`data/registry.sqlite` -- no new database): `query_id`, timestamp, code
fingerprint, the full `QuerySpec` as JSON, row count, date range,
sources used, warnings, and a deterministic content hash. It does
**not** store the observations themselves ("do not store enormous
duplicated result datasets unnecessarily"). Insert-only, `UPDATE`/
`DELETE` blocked by trigger -- same immutability discipline as every
other table Phase 1 added. Reproducing a past query: re-run the logged
`parameters_json` and compare `content_hash`.

## 10. CLI

`scripts/ngxrot_research.py` (argparse, following this repo's existing
`scripts/*.py` convention -- no new CLI framework):

```bash
PYTHONPATH=src python scripts/ngxrot_research.py prices --symbol GTCO --from 2023-01-01 --to 2025-01-01
PYTHONPATH=src python scripts/ngxrot_research.py sector --sector "CONSUMER GOODS" --as-of 2025-01-01
PYTHONPATH=src python scripts/ngxrot_research.py compare --symbols GTCO,ZENITHBANK,ACCESSCORP --from 2023-01-01 --to 2025-01-01
PYTHONPATH=src python scripts/ngxrot_research.py universe --as-of 2024-06-30
PYTHONPATH=src python scripts/ngxrot_research.py universe --index NGXBNK --as-of 2024-06-30
PYTHONPATH=src python scripts/ngxrot_research.py lookup --symbol GTCO --kind ticker
PYTHONPATH=src python scripts/ngxrot_research.py metadata --symbol GTCO
```

`--format table|json|csv` on every command; `--no-log` to skip
`query_log` (e.g. a rehearsal run); a rejected query prints
`QUERY REJECTED: <reason>` to stderr and exits 1.

## 11. Python API

```python
from ngxrot import db, registry
from ngxrot.research_query import QuerySpec, execute

con = db.connect()
reg = registry.connect_registry()
result = execute(con, QuerySpec(query_type="prices", entities=["GTCO"],
                                start="2023-01-01", end="2025-01-01",
                                fields=["close", "volume"]), reg=reg)
result.observations       # pandas DataFrame
result.provenance         # list[dict]
result.to_json()          # str
```

## 12. Output formats

`QueryResult.to_json()`, `.to_csv()`, and the raw `.observations`
pandas DataFrame (this project's existing dataframe convention
throughout `db.py`/`research_dataset.py` -- no new representation
introduced). The CLI's default `table` format is a terminal-friendly
rendering of the same DataFrame.

## 13. SQL access hierarchy

```
High-level Research API (research_query.py)
        |
Query Layer (validation, entity resolution, PIT dispatch)
        |
Validated SQL/data access (db.py's *_asof / *_range readers)
        |
SQLite PIT (data/ngx.sqlite)
```

Advanced researchers retain full direct SQL access to `data/ngx.sqlite`
(read-only recommended) for anything this layer does not yet cover --
nothing was removed or gated.

## 14. Performance (measured, not assumed)

Benchmarked against the real production `data/ngx.sqlite`:

| query | time | rows |
|---|---|---|
| entity lookup | ~19ms | 1 |
| single-stock history, 2yr | ~37ms | 486 |
| multi-stock history, 10 tickers, 2yr | ~763ms | 4,830 |
| sector cross-section (19 tickers) -- **before** the SQL-reduction fix | ~4,180ms | 19 |
| sector cross-section (19 tickers) -- **after** | ~599ms | 19 |
| large date-range (single ticker, 10yr) | ~42ms | 861 |
| PIT universe query (IRU) | ~298ms | 100 |

All well within interactive/notebook use. **No PostgreSQL migration is
justified by these numbers.** SQLite remains adequate at this data
volume; documented here rather than solved for hypothetically.

## 15. Limitations (disclosed, not silently worked around)

- Sector classification has no historical versioning -- disclosed via a
  warning on every backward-looking sector/cross-section query, never
  corrected or backfilled here.
- `corporate_actions`/`extracted_facts` desynchronization (Phase 1
  finding) is unaffected by this layer; `research_quality.
  corporate_action_notes` still surfaces both representations side by
  side.
- `fields` is intentionally restrictive -- if a researcher needs a field
  genuinely absent from the schema (e.g. market cap, dividend yield),
  the correct response is "not supported," not a fabricated value.
- Provenance's batch summary is per (ticker, source_id), not per row --
  drill into a specific observation via `lineage.
  trace_equity_observation()` directly when needed (Section 7).

## 16. Examples

See `scripts/research_query_integration_test.py` for a full worked
example (a genuine research question executed end to end, with
reproducibility verified), and `docs/fre_runs/
research_query_layer_report.md` for the summary run output.

## 17. Testing

`scripts/test_research_query.py` (29 checks): query correctness for all
six query types, PIT correctness (as-of, look-ahead rejection, historical
identity, historical universe), guardrails (invalid dates, unknown
entity/field, non-positive limit), descriptive-calculation correctness,
provenance population, reproducibility (identical query -> identical
content hash), `query_log` population/immutability, and an explicit
check that the NGX Pulse API key never appears in any logged query.

`scripts/research_query_integration_test.py`: the Section-22-style
end-to-end integration test.

## 18a. Document/evidence bridge (added 2026-08-11)

Four new `query_type`s, all thin `QueryResult` wrappers around the
existing, already-tested FRE retrieval primitives in
`src/ngxrot/documents/retrieval.py` and `documents/context.py` -- no new
fact/evidence-reading logic, matching every query type above:

| type | function | wraps |
|---|---|---|
| `facts` | `query_facts` | `documents.retrieval.find_facts` -- extracted facts (deterministic + LLM-sourced) for one or more tickers, `filters={"fact_type": ...}` |
| `events` | `query_events` | `documents.retrieval.find_events` -- PIT-correct events via the existing `db.events_asof`, `filters={"event_type": ...}` |
| `entity_relationships` | `query_entity_relationships` | `documents.retrieval.find_entity_relationships` |
| `document_context` | `query_document_context` | `documents.context.build_reasoning_context` -- ONE ticker per call (a full reasoning-context assembly, not a cheap index read); returns a one-row summary with document/fact/evidence/event/relationship counts plus `coverage_score`/`confidence_ceiling` |

Provenance for `facts`/`document_context` is resolved against
`documents`/`sources` directly (`_document_provenance_summary`), the
document-side counterpart to the existing `_provenance_summary` used by
the market-data query types. CLI: `scripts/ngxrot_research.py facts|
events|relationships|context`. Tests:
`scripts/test_research_query.py`'s facts/events/entity_relationships/
document_context section (12 checks, run against the real production DB).

This closes the gap `docs/INVESTMENT_OS_SPECIFICATION.md` flagged: the
query layer previously only covered price/security/universe data. It now
also covers the document/FRE side, without any change to the six
pre-existing query types or the underlying FRE modules.

## 18. Reproducibility, summarized

1. Run a query -> get a `QueryResult` with a `content_hash`.
2. `query_log` (or Phase 1's `dataset_snapshots`, if the caller also
   used `research_dataset.py`) preserves the exact parameters used.
3. Re-run the same parameters later -> compare `content_hash`. A match
   confirms the underlying data has not changed since; a mismatch is
   itself a finding to investigate (a restatement, correction, or new
   ingestion touched that window), not something to silently accept.
