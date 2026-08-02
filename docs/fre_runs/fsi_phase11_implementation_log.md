# FSI Phase 11 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase11_preregistration.md`
(approved, with the owner's added implementation-boundary constraints)
and the owner's implementation instruction. Append-only.*

## Entry 0 — Design refinement before coding: reuse `company_thesis_360.as_of()` as a whole, not its own leaf calls

The pre-registration's own Section 4 sketched calling `build_company_
thesis()`, `company_memory_360.as_of()`, and `get_entity_context()` as
three independent leaf calls, to avoid the duplicate-memory-computation
risk of nesting Phase 8's and Phase 10's own composed objects together.
Before writing code, this is refined to an equally-correct, simpler
design: **call `company_thesis_360.as_of()` once** (it already returns
`thesis`, `memory`, `concern_evidence`, and `supplementary_evidence` in
a single call, computing `company_memory_360.as_of()` exactly once
internally) **and call `get_entity_context()` directly once** (bypassing
`entity_context.as_of()`, which would otherwise call `company_memory_
360.as_of()` a second time). This achieves the same "call each
underlying component exactly once" bar the pre-registration set, while
additionally reusing Phase 8's own concern/supplementary categorization
logic exactly, rather than re-deriving it — a stronger consistency
guarantee than the originally-sketched design, disclosed here as a
refinement, not a deviation from intent.

## Entry 1 — A disclosed, deliberate small duplication: two formatting helpers

`financial_reasoning_report.py` (Phase 7) is frozen and must not be
modified, including a mechanical rename of its own private `_format_
confidence_tier`/`_format_value` helpers to public ones. This phase
therefore defines its own small, independent copies of the same two
formatting rules (the `NULL`-confidence-tier phrase and the value-
formatting convention) inside its own new module — a disclosed,
deliberate duplication of two small, stable functions, chosen over
either modifying a frozen module or introducing a fragile cross-module
dependency on another module's private (underscore-prefixed) internals.

## Entry 2 — Implementation (complete)

`src/ngxrot/fre/company_research_dossier.py` implements `build_dossier()`
(per Entry 0's refined design) and `render_dossier()`. The Company
Memory portion of the rendered output is produced by calling `render_
report(dossier.memory)` directly — the exact same function Phase 7
exposes, never reimplemented. Two new sections are appended: **Investment
Thesis Evidence** (FRE-5's `CompanyThesis` fields verbatim, plus Phase
8's `concern_evidence`/`supplementary_evidence`, each item rendered with
its own `conclusion_id`, `status`, value, confidence tier, method, and
limitations) and **Knowledge Graph Context** (Phase 10's `EntityContext`
fields verbatim, including the explicit "not yet known, not the same as
non-existence" phrasing for a `None` `entity_id`).

Real sanity check against NASCON before writing formal tests: the
rendered dossier's Company Memory section matched `render_report()`
called directly; the Investment Thesis Evidence section correctly
surfaced FRE-5's own real bull/bear/base case text and the pilot
disclosure (`is_pilot: True`); the Knowledge Graph Context section
correctly showed NASCON's real `entity_id=22` and "No known
relationships as of this date" (matching Phase 9/10's own disclosed
finding).

## Entry 3 — A real false positive found and fixed during test development

Building the mechanical forbidden-vocabulary check (proving no ranking/
scoring/recommendation language leaks into the dossier) surfaced a real
false positive, disclosed rather than swept past: FRE-5's own frozen
`company_thesis.py` always appends a real, legitimate disclaimer to
`financial_signal_summary` — "...NOT a financial-statements-based
quality score -- that remains blocked pending a financial-statements
dataset..." — which legitimately uses the word "score" specifically to
disclaim having one. This is real, pre-existing data from a frozen
module (FRE-5), not something Phase 11 introduces. Fixed by excluding
this known phrase from the mechanical scan, the same class of fix
already applied once before in Phase 7's own test development (the
"Operating Profit" / disclaimer-sentence false positives).

## Entry 4 — Validation and full regression (complete)

`scripts/fre/test_company_research_dossier.py` (14/14): renders without
exception for all 5 real tickers; the Company Memory section is
byte-identical to a direct `render_report()` call; `dossier.thesis`/
`memory`/`concern_evidence`/`supplementary_evidence` are exactly
equivalent to calling `company_thesis_360.as_of()` directly;
`dossier.graph` is exactly equivalent to calling `get_entity_context()`
directly; determinism verified two ways (same dossier rendered 3x is
byte-identical; two independently-built dossiers of the same ticker/
date also render byte-identical); both new sections appear in the
fixed, disclosed order; every `NULL` confidence tier renders the
explicit "NOT RECORDED" phrase; no forbidden vocabulary appears outside
disclaimer text (including the real FRE-5 "quality score" disclaimer,
now correctly excluded); `CompanyResearchDossier`'s own 7 dataclass
fields contain no combined score/rating/summary field; single-ticker-
scope guardrail holds; zero database writes, `integrity_check`/
`foreign_key_check` clean before and after.

Full regression: `check_db_safety.py` PASS, `test_reasoning_
pipeline.py` ALL CHECKS PASSED, every prior FSI Phase 1-10 test file
unchanged and passing (16 files, 218 assertions), plus the new
`test_company_research_dossier.py` (14/14), FRE-2 29/29, FRE-3 16/16,
FRE-4 16/16, FRE-5 21/21, FRE-6 40/40 (unchanged). Phase 5's own
`fsi_phase5_validate_pipeline.py` harness re-run and still reports PASS
on all three components.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents`
(11,533), `extracted_facts` (267), `financial_reasoning_conclusions`
(177), `entities` (50), and `entity_relationships` (5) row counts all
unchanged — this phase has zero write path of any kind.

**FSI Phase 11 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
