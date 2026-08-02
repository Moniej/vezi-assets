# FSI Phase 11 — Final Report

*Complete Institutional Research Dossier. Prepared per the owner's
instruction on completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase11_implementation_log.md`; this report
summarizes outcomes.*

## Executive summary

FSI Phase 11 built `CompanyResearchDossier`/`render_dossier()`, closing
the reporting gap identified in its own pre-registration: Phase 8's
Investment Thesis Evidence and Phase 10's Knowledge Graph Context are
now rendered into the same human-readable document as Phase 6's
Company Memory (Phase 7's own `render_report()`, reused verbatim, not
reimplemented). No modification to any of the five frozen modules this
phase draws from. No new reasoning, no synthesis across sections, no
combined score/rating/recommendation of any kind.

## Files created (deliverables)

- **CompanyResearchDossier**: `src/ngxrot/fre/company_research_
  dossier.py` — the composition dataclass and `build_dossier()`.
- **render_dossier()**: same file — the rendering function.
- **Tests**: `scripts/fre/test_company_research_dossier.py` (14
  assertions).
- **Documentation**: this report plus the implementation log.
- **Implementation log**: `docs/fre_runs/fsi_phase11_implementation_log.md`.

**No schema change. No modification to `render_report()`,
`company_thesis_360.py`, `entity_context.py`, `company_memory_360.py`,
or `company_thesis.py`.**

## Implementation-requirement results

- **Pure composition layer**: confirmed — `build_dossier()` calls
  `company_thesis_360.as_of()` once and `get_entity_context()` once;
  no new query beyond those two calls.
- **All five existing modules remain unchanged**: confirmed by code
  review; `company_thesis_360.as_of()` and `render_report()` are
  called exactly as their own modules already expose them.
- **`render_report()` behaves identically for existing functionality**:
  confirmed directly — the Company Memory portion of every rendered
  dossier is byte-identical to calling `render_report()` on the same
  `CompanyMemory360` snapshot directly.
- **New sections are append-only**: confirmed — Investment Thesis
  Evidence and Knowledge Graph Context are appended after the reused
  Company Memory section, in a fixed order, never interleaved or
  replacing existing content.
- **Each underlying component called exactly once**: confirmed — see
  the design refinement below.
- **PIT behavior preserved**: confirmed — `company_thesis_360.as_of()`
  and `get_entity_context()` are both PIT-safe by construction; this
  phase does not alter that.
- **Deterministic rendering, byte-identical for identical inputs**:
  confirmed two ways — same dossier rendered 3 times is byte-identical;
  two independently-built dossiers of the same ticker/date also render
  byte-identical.
- **Citations, provenance, confidence tiers, filing dates, and
  limitations preserved exactly; `NULL` confidence never upgraded**:
  confirmed — every FSI evidence item's `method`/`limitations`/
  `confidence_tier` is rendered verbatim, and the explicit "NOT
  RECORDED" phrase appears for every `NULL`-tier item.
- **No synthesized conclusions across sections, no summarization of
  multiple evidence items into new claims, no scores/rankings/
  recommendations/valuations/portfolio suggestions/health metrics/
  hidden aggregation**: confirmed by direct dataclass-field
  introspection (`CompanyResearchDossier`'s 7 fields contain no such
  field) and by a mechanical forbidden-vocabulary scan across all 5
  real rendered dossiers.

## A design refinement, made during implementation, disclosed

The pre-registration sketched calling three leaf functions (`build_
company_thesis`, `company_memory_360.as_of`, `get_entity_context`)
independently. During implementation this was refined to calling
`company_thesis_360.as_of()` as a whole (which already returns
`thesis`, `memory`, `concern_evidence`, and `supplementary_evidence`
from a single internal memory computation) plus `get_entity_context()`
directly (bypassing `entity_context.as_of()`'s own redundant memory
call). This achieves the same "exactly once" bar with a stronger
consistency guarantee: Phase 8's own concern/supplementary
categorization logic is reused exactly, never re-derived.

## A real false positive found and fixed during test development

Building the forbidden-vocabulary check surfaced a real false positive:
FRE-5's own frozen `company_thesis.py` always appends a genuine
disclaimer to `financial_signal_summary` — "...NOT a financial-
statements-based quality score -- that remains blocked pending a
financial-statements dataset..." — which legitimately uses the word
"score" to disclaim having one. This is real, pre-existing FRE-5 data,
not something this phase introduces. Fixed by excluding the known
phrase from the mechanical scan, the same class of fix already applied
once in Phase 7's own test development.

## Validation results

- **Section equivalence**: Company Memory section byte-identical to a
  direct `render_report()` call, for all 5 tickers.
- **Thesis/evidence equivalence**: `dossier.thesis`/`memory`/`concern_
  evidence`/`supplementary_evidence` exactly equal to a direct
  `company_thesis_360.as_of()` call, for all 5 tickers.
- **Graph equivalence**: `dossier.graph` exactly equal to a direct
  `get_entity_context()` call, for all 5 tickers.
- **Determinism**: verified two ways, as described above.
- **Database immutability**: all 29 tables' row counts, `integrity_
  check`, and `foreign_key_check` unchanged/clean before and after.
- **Full regression suite**: all 16 prior FSI Phase 1-10 test files
  (218 assertions) plus the new 14-assertion test file, plus
  `check_db_safety.py`, `test_reasoning_pipeline.py`, and FRE-2 through
  FRE-6 (all unchanged, FRE-6 still 40/40).
- **Phase 5 validation harness re-run after implementation**: still
  reports PASS on all three components.

## Known limitations

- **Low graph-context yield remains true here too, as in Phase 10**: 4
  of 5 tickers show "No known relationships as of this date" —
  correct, not a defect, and disclosed explicitly in the rendered
  output.
- **Markdown only, single-ticker only** — no PDF/HTML output, no
  cross-ticker section, by design, matching Phase 7's own scope.
- **Inherits every limitation already disclosed in Phases 6-10** — no
  new gap is introduced by this phase; none of the underlying data's
  own disclosed limitations are hidden or smoothed over by the new
  presentation layer.

## Recommendations for the next phase

1. If a future phase adds a new composition layer over the FSI track's
   data, extend `CompanyResearchDossier`/`render_dossier()` the same
   way this phase extended Phase 7's own report — a new, additive
   section, never a rewrite of the existing ones.
2. Continue the standing discipline: any future capability remains
   subject to the same exclusions restated across all eleven approvals
   — no alpha, ranking, scoring, valuation, or unsupported conclusion.

---

**FSI Phase 11 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
