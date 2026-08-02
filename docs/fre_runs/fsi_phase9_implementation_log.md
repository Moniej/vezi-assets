# FSI Phase 9 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase9_preregistration.md`
(approved) and the owner's implementation instruction. Append-only.*

## Entry 0 — Correction found before writing any code: `configs/relation_taxonomy.toml` already exists

The pre-registration proposed creating "a new, minimally-scoped
`configs/relation_taxonomy.toml`... seeded with only the
`[corporate_structure]` family and only the `renamed_from` type."
Before writing code, direct inspection found this file **already
exists**, committed as part of `fre-architecture-baseline-2026-08-01`
(commit `f6f4034`, FRE-1) — with the FULL taxonomy from Part 2's
design already seeded (`corporate_structure`, `commercial`,
`governance`, `macro_exposure`, `graph_provenance`), including
`renamed_from` already listed. This is a real, disclosed correction to
the pre-registration's own assumption, not a silent adjustment: **no
new config file is created in this phase** — the existing, already-
frozen file already contains everything this phase needs. This phase
only ever READS `relation_taxonomy.toml` (to validate the `relation_
type` string it writes), never modifies it.

## Entry 1 — Real data gathered before writing the population script

Direct query against real production data, before any write:

- **Entities today**: exactly 2 real `company` rows exist —
  `NASCON` (entity_id=22) and `GTCO` (entity_id=1). Of the FSI track's
  5 tickers, only NASCON has one. Of the 4 verified renames' 8 symbols
  (4 old + 4 new), only `GTCO` (the new side of `GUARANTY→GTCO`) has
  one.
- **Missing FSI-ticker entities needed**: UCAP, BUAFOODS, AFRIPRUD, CAP
  (4 new rows) — `first_seen_doc_id` set to each ticker's own earliest
  real document (UCAP: doc 363, 2016-03-18; BUAFOODS: doc 5910,
  2022-03-31; AFRIPRUD: doc 36, 2014-07-11; CAP: doc 13, 2014-07-11).
- **Missing rename-lineage entities needed**: `FO`, `ARDOVA`,
  `GUARANTY`, `ACCESS`, `ACCESSCORP`, `FBNH`, `FIRSTHOLDCO` (7 new rows
  — `GTCO` already exists and is reused, not recreated).
  `first_seen_doc_id` set using `documents.raw_symbol` (the AS-
  DISCLOSED name a filing actually used), not `documents.ticker` (which
  Phase A already resolved to the post-rename ticker retroactively) —
  a real, disclosed methodology correction found while gathering this
  data: an initial query using `ticker` for the new-symbol side
  returned the SAME earliest doc_id as the old symbol's own query (285
  for both `FO` and `ARDOVA`), because Phase A's ticker-resolution
  back-fills the new ticker onto pre-rename filings. Re-querying by
  `raw_symbol` instead correctly separates "first disclosed under the
  old name" from "first disclosed under the new name," and the
  resulting dates line up exactly with each rename's own effective
  window in `symbol_renames.csv` (e.g. `ARDOVA` first disclosed
  2020-02-25, immediately after the 2020-02-21/24 rename window).
- **`entity_relationships` direction**: per Part 2's own worked example
  (`entity(company, "Access Holdings Plc") --[renamed_from]-->
  entity(company, "Access Bank Plc")`), `subject_entity_id` = the NEW
  (post-rename) entity, `object_entity_id` = the OLD (pre-rename)
  entity. `valid_from` = `symbol_renames.csv`'s own `new_first` column
  (the date the new ticker became effective). `confidence` = 1.0 (this
  is deterministic, owner-verified data, not a probabilistic
  extraction — the first entity_relationships row this platform has
  ever written with a non-inferred confidence value).

## Entry 2 — Implementation (complete)

`scripts/fre/fsi_phase9_populate_knowledge_graph.py` (dry-run then
`--apply`, matching the established convention from every prior FSI
extraction/population script): validates `'renamed_from'` against the
existing `relation_taxonomy.toml` before writing anything; creates
`entities` rows only where one doesn't already exist (checked by
`canonical_name`, never duplicated); creates `entity_relationships`
rows only for the 4 `verified`-status CSV rows.

**Dry-run matched expectations exactly** before any write: 11 new
`entities` rows (4 FSI tickers + 7 rename-lineage symbols; NASCON and
GTCO correctly skipped as already existing), 4 new
`entity_relationships` rows. Applied for real (backup:
`data/ngx.sqlite.pre_fsi_phase9_kg_backup_2026-08-02`): `entities` 39 →
50, `entity_relationships` 1 → 5, `documents`/`extracted_facts`
unchanged, `foreign_key_check` clean.

## Entry 3 — Validation and full regression (complete)

`scripts/fre/test_phase9_knowledge_graph.py` (14/14): all 5 FSI tickers
now have exactly one `entities` row each; NASCON's pre-existing row is
byte-for-byte untouched; exactly 4 real `renamed_from` edges exist,
each matching its own verified CSV row's `(old_symbol, new_symbol,
valid_from)` exactly; zero edges trace to any `candidate`-status row
(explicitly checked against the real `UBCAP→UCAP` candidate row,
which involves one of this program's own 5 FSI tickers and is
correctly excluded); `'renamed_from'` confirmed declared in the
existing, unmodified `relation_taxonomy.toml`; every new relationship
row has `confidence=1.0` and `valid_to=NULL`; the original
`affects_order_1` row is untouched; every new entity's
`first_seen_doc_id` points at a real, existing document.

Full regression: `check_db_safety.py` PASS, `test_reasoning_
pipeline.py` ALL CHECKS PASSED, every prior FSI Phase 1-8 test file
unchanged and passing (14 files, 191 assertions), plus the new
`test_phase9_knowledge_graph.py` (14/14), FRE-2 29/29, FRE-3 16/16,
FRE-4 16/16, FRE-5 21/21, FRE-6 40/40 (unchanged — this phase touches
`entities`/`entity_relationships` only, never `extracted_facts` or
`financial_reasoning_conclusions`, so no stale-assertion update was
needed anywhere). Phase 5's own `fsi_phase5_validate_pipeline.py`
harness re-run and still reports PASS on all three components (its own
golden snapshot does not cover `entities`/`entity_relationships`, so no
deviation was expected or found).

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents`
(11,533), `extracted_facts` (267), and `financial_reasoning_
conclusions` (177) row counts all unchanged; `entities` 39→50,
`entity_relationships` 1→5 — the two intentional, disclosed, additive
changes this phase makes.

**FSI Phase 9 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
