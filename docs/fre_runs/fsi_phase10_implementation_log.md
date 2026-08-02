# FSI Phase 10 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase10_preregistration.md`
(approved, with the owner's added implementation-boundary constraints)
and the owner's implementation instruction. Append-only.*

## Entry 0 — Design decision before coding: PIT-gate entity existence itself

The pre-registration's own Section 5 described returning an entity's
`entity_id`/`canonical_name`/`first_seen_doc_id` "verbatim, no new
judgment." Before writing code, this is refined with one additional,
disclosed rule, consistent with (not an addition to) the platform's
existing PIT discipline: an entity is only visible as of a given date
if its own `first_seen_doc_id`'s `filing_date <= as_of_date` — the same
`documents.filing_date` gate every prior FSI phase (4, 6, 8) already
uses. This is not new reasoning; it is the same rule applied
consistently to a table (`entities`) that had never been read through
a PIT lens before. **Important, explicitly disclosed distinction**: a
`None` result means "no graph presence is yet KNOWN as of this date,"
never "this company did not exist" — absence of evidence is not
evidence of absence, stated explicitly in the module docstring, not
left implicit.

`entity_relationships` rows are filtered the same way using their own
`valid_from`/`valid_to` columns (`valid_from <= as_of_date AND
(valid_to IS NULL OR valid_to > as_of_date)`) — for all 4 real
`renamed_from` edges, `valid_to` is `NULL` (Phase 9's own confirmed
result), so this filter never excludes them once `valid_from` has
passed, and has no practical effect for any of the 5 FSI tickers today
(none of the 4 renames involves any of them, per Phase 9's own
disclosed finding) — but the module is built correctly regardless of
how little today's real data exercises it, matching this program's
own established precedent (e.g. Phase 4's zero-linked-fact fallback
rules).

## Entry 1 — Implementation (complete)

`src/ngxrot/fre/entity_context.py` implements `get_entity_context(con,
ticker, as_of_date) -> EntityContext` (the raw, PIT-gated reader) and
`as_of(con, ticker, as_of_date) -> CompanyMemory360Graph` (the
composition with Phase 6's `CompanyMemory360.as_of()`, called
unmodified). Every `RelationshipContext` retains `relation_type`,
`valid_from`/`valid_to`, `confidence`, and `source_evidence_id`
verbatim from `entity_relationships` — no field is dropped or
re-derived.

**Real sanity check before writing formal tests**: all 5 FSI tickers
correctly show zero relationships (exactly matching Phase 9's own
disclosed finding that none of the 4 verified renames involves any FSI
ticker). GTCO (not an FSI ticker, but a real, known rename case)
correctly surfaces its one real `renamed_from` edge, direction
`'subject'`, counterpart `'GUARANTY'` — confirming the mechanism itself
works correctly on the one real case available to test it against. The
PIT boundary case (UCAP the day before vs. exactly on its own real
`first_seen_doc_id` filing date) correctly flips from `None` to
populated.

## Entry 2 — Validation and full regression (complete)

`scripts/fre/test_entity_context.py` (13/13): output equivalence
against the raw `entities` table for all 5 FSI tickers; GTCO's real
`renamed_from` edge matches the raw `entity_relationships` row exactly
(same `relationship_id`, `valid_from`, `confidence`) with the correct
`direction`; all 5 FSI tickers confirmed to show zero relationships
(disclosed as expected, not a defect); every real `renamed_from` edge
confirmed to trace to a `verified`-status CSV row, never a `candidate`
row; the real `UBCAP→UCAP` candidate relationship confirmed absent
from UCAP's own context; the PIT boundary verified directly (`None`
the day before, populated exactly on the real filing date); composition
equivalence with `CompanyMemory360` confirmed exact for all 5 tickers;
no forbidden scoring/ranking/centrality/weighting/voting/recommendation
field exists in any of this module's 3 dataclasses (verified by direct
introspection); single-ticker-scope guardrail holds; zero database
writes, `integrity_check`/`foreign_key_check` clean before and after.

Full regression: `check_db_safety.py` PASS, `test_reasoning_
pipeline.py` ALL CHECKS PASSED, every prior FSI Phase 1-9 test file
unchanged and passing (15 files, 205 assertions), plus the new
`test_entity_context.py` (13/13), FRE-2 29/29, FRE-3 16/16, FRE-4
16/16, FRE-5 21/21, FRE-6 40/40 (unchanged). Phase 5's own
`fsi_phase5_validate_pipeline.py` harness re-run and still reports PASS
on all three components.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents`
(11,533), `extracted_facts` (267), `financial_reasoning_conclusions`
(177), `entities` (50), and `entity_relationships` (5) row counts all
unchanged — this phase, unlike Phase 9, has zero write path of any
kind.

**FSI Phase 10 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
