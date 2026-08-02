# FSI Phase 9 — Final Report

*Knowledge Graph Completeness: Verified Entities and Rename Lineage.
Prepared per the owner's instruction on completion. Full narrative and
validation detail is in `docs/fre_runs/fsi_phase9_implementation_log.
md`; this report summarizes outcomes.*

## Executive summary

FSI Phase 9 closed two real, previously-disclosed gaps in the
knowledge graph using only data this platform already possesses and
already trusts: (1) all 5 FSI tickers now have a real `entities` row
(up from 1 of 5 — only NASCON — before this phase); (2) `entity_
relationships` now has 4 real, typed `renamed_from` edges (up from 0
real ones — the table's only prior row was an `effect_chains` artifact,
not a genuine relationship), sourced exclusively from the 4 rows marked
`verified` in `data/reference/symbol_renames.csv`. Zero new extraction,
zero LLM call, zero subjective inference of any kind — every new row
traces to data already collected and already owner-reviewed.

## Files created

- `scripts/fre/fsi_phase9_populate_knowledge_graph.py` — dry-run/
  `--apply` population script.
- `scripts/fre/test_phase9_knowledge_graph.py` — 14 assertions.
- `docs/fre_runs/fsi_phase9_implementation_log.md`,
  `fsi_phase9_final_report.md` (this document).

**No new config file** — `configs/relation_taxonomy.toml` was found,
during implementation, to already exist in full (committed as part of
`fre-architecture-baseline-2026-08-01`, FRE-1) with the `renamed_from`
type already declared; this phase only reads it. **No schema change.**

## A pre-registration assumption corrected during implementation, disclosed

The pre-registration proposed creating a new, minimally-scoped
`relation_taxonomy.toml`. Direct inspection before writing code found
this file already exists in full. No new config was created; the
existing one was used as-is. This is exactly the kind of assumption-
correction this program's discipline calls for disclosing rather than
silently absorbing.

## Results

| Item | Before | After |
|---|---|---|
| FSI tickers with a real `entities` row | 1 of 5 (NASCON only) | 5 of 5 |
| Real, typed `entity_relationships` rows | 0 (1 row total, an `effect_chains` artifact) | 4 (`renamed_from`), plus the 1 original artifact row untouched |
| New `entities` rows | — | 11 (4 FSI tickers + 7 rename-lineage symbols; NASCON and GTCO correctly reused, not duplicated) |

**Rename edges populated** (all `verified`-status only): `FO→ARDOVA`
(2020-02-24), `GUARANTY→GTCO` (2021-06-24), `ACCESS→ACCESSCORP`
(2022-03-28), `FBNH→FIRSTHOLDCO` (2025-03-10) — each `valid_from`
matching `symbol_renames.csv`'s own `new_first` column exactly.

**A real methodology correction found while gathering data, disclosed
rather than silently fixed**: an initial approach to finding each
"new symbol's" first appearance used `documents.ticker`, which Phase A
had already retroactively resolved to the post-rename ticker on
pre-rename filings — producing an identical, wrong "first seen" doc_id
for both the old and new symbol. Corrected by querying `documents.
raw_symbol` (the as-disclosed name) instead, which correctly separates
"first disclosed under the old name" from "first disclosed under the
new name" and produces dates that line up exactly with each rename's
own effective window.

## Requirement-by-requirement results

- **Zero new extraction, zero LLM call**: confirmed by code review —
  the population script only reads `symbol_renames.csv` and existing
  `documents` rows.
- **Only `verified`-status rows used**: confirmed directly — the real
  `UBCAP→UCAP` candidate row (involving one of this program's own 5
  FSI tickers) is correctly excluded; all 4 populated edges trace to
  `verified` rows only.
- **No modification to any frozen module or existing row**: confirmed —
  NASCON's and GTCO's pre-existing `entities` rows are byte-for-byte
  untouched; the original `affects_order_1` relationship row is
  untouched; `relation_taxonomy.toml` was not modified.
- **No expansion into Part 2's LLM-dependent scope** (ownership
  extraction, competitor/supplier classification, merger/demerger
  detection, governance/macro-exposure edges): confirmed by code
  review — none of these were touched.

## Validation results

`test_phase9_knowledge_graph.py` (14/14): all 5 FSI tickers have
exactly one entity row; NASCON's row is untouched; exactly 4 real
`renamed_from` edges exist, each matching its source CSV row exactly;
zero edges trace to a `candidate`-status row; `renamed_from` confirmed
declared in the existing taxonomy config; every new relationship has
`confidence=1.0`/`valid_to=NULL`; the original artifact row is
untouched; every new entity's `first_seen_doc_id` resolves to a real
document. Full regression suite: all 14 prior FSI Phase 1-8 test files
(191 assertions) plus the new 14-assertion test file, plus
`check_db_safety.py`, `test_reasoning_pipeline.py`, and FRE-2 through
FRE-6 (all unchanged, FRE-6 still 40/40). Phase 5's own validation
harness re-run after implementation and still reports PASS on all
three components.

## Known limitations

- **None of the 4 verified renames involve any of the FSI track's own 5
  tickers** — disclosed already in the pre-registration and confirmed
  here; only the 4 new FSI-ticker `entities` rows directly benefit the
  FSI track. The rename-lineage edges are a general knowledge-graph
  improvement, not FSI-specific.
- **`entity_relationships` remains otherwise almost entirely
  unpopulated** — this phase adds 4 real edges to a graph that
  otherwise still has only 1 (the pre-existing artifact); Part 2's
  LLM-dependent relation types (competitor_of, supplier_of, executive_
  of, major_shareholder_of, etc.) remain entirely unbuilt, by design,
  in this phase.
- **The `commodity`/`macro_variable`/`subsidiary`/`index` entity types**
  (added to the schema's CHECK constraint by FRE-1) still have zero
  populated rows after this phase — populating them was explicitly out
  of scope.

## Recommendations for the next phase

1. If a future phase performs LLM-based relation classification
   (competitor_of, supplier_of, etc.), it should build on this phase's
   now-real `entities` rows for all 5 FSI tickers rather than needing
   to create them again.
2. If new ticker renames are ever verified and added to `symbol_
   renames.csv` with `status='verified'`, re-running this phase's
   population script (idempotent by design — it skips any entity that
   already exists) would pick them up without any code change.
3. Continue the standing discipline: any future capability remains
   subject to the same exclusions restated across all nine approvals —
   no alpha, ranking, scoring, valuation, or unsupported conclusion.

---

**FSI Phase 9 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
