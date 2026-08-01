# FSI Phase 6 — Final Report

*Unified Point-in-Time Company Memory. Prepared per the owner's
instruction to document findings and freeze this phase as a baseline on
completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase6_implementation_log.md`; this report
summarizes outcomes.*

## Executive summary

FSI Phase 6 built `CompanyMemory360.as_of(ticker, date)` — a pure,
read-only composition layer combining FRE-3's `CompanyMemory.as_of()`
and FSI Phase 4's `pit_financial_memory.as_of()` into a single call.
Neither underlying module was modified. No new fact, schema, or
synthesized field of any kind was introduced. Output equivalence with
both underlying modules was proven exactly (0 discrepancies across 20
real ticker/date combinations), PIT leakage tests found 0 violations,
and database immutability was confirmed across all 29 tables. No
architectural blocker was encountered — the two independently-built PIT
mechanisms (each already gating on `documents.filing_date`) composed
cleanly on first attempt.

## Files created

- `src/ngxrot/fre/company_memory_360.py` — the single composition
  function and its `CompanyMemory360` dataclass.
- `scripts/fre/test_company_memory_360.py` — 7 assertions.
- `docs/fre_runs/fsi_phase6_implementation_log.md`,
  `fsi_phase6_final_report.md` (this document).

**No schema change.** **No modification to `company_memory.py` or
`pit_financial_memory.py`.**

## Requirement-by-requirement results

1. **Do not modify either underlying frozen module.** Confirmed — both
   are imported and called unmodified; git history shows no changes to
   either file in this phase.
2. **Do not create synthesized conclusions.** Confirmed —
   `CompanyMemory360`'s only fields are `ticker`, `as_of_date`,
   `corporate`, and `financial`; verified by direct dataclass-field
   introspection in the test suite.
3. **No health scores, rankings, thesis outputs, investment
   recommendations, or valuation outputs.** Confirmed by code review and
   the same field-introspection check — nothing beyond the two existing
   result objects is returned.
4. **Complete provenance preserved.** Both sub-results retain their own
   source IDs (`fact_id`/`doc_id`), filing dates, confidence
   information, and PIT cutoff exactly as their own modules already
   produce — inherited, not re-derived.
5. **Zero-write architecture.** No schema change, no migration, no fact
   mutation — confirmed by an all-29-table row-count diff showing zero
   change before/after the full test run.

## Validation results

- **Output equivalence**: for all 5 real tickers across 4 real/
  representative `as_of_date` values (20 combinations),
  `CompanyMemory360.as_of()`'s two sub-results are exactly equal to
  calling the two underlying functions directly — 0 discrepancies.
- **PIT leakage tests**: reusing the 15 real anchor documents' own
  filing dates, 0 violations in either the `corporate` or `financial`
  sub-result.
- **Database immutability**: all 29 tables' row counts, `integrity_
  check`, and `foreign_key_check` unchanged/clean before and after the
  full test run.
- **Full regression suite**: every prior FSI Phase 1-5 test file (12
  files, 165 assertions) plus the new 7-assertion test file, plus
  `check_db_safety.py`, `test_reasoning_pipeline.py`, and FRE-2 through
  FRE-6 (FRE-6 unchanged at 40/40). Phase 5's own validation harness
  (`fsi_phase5_validate_pipeline.py`) was re-run after Phase 6's
  implementation and still reports PASS on all three components,
  confirming Phase 6 introduced no regression into the golden snapshot
  or cross-phase consistency.

## Findings

The pre-registration's own research question — whether FRE-3 and Phase
4's independently-built PIT mechanisms would agree once composed — is
answered: **yes, completely**. Both already gated on the identical
`documents.filing_date <= as_of_date` rule; composing them required no
reconciliation logic, no edge-case handling, and no change to either
module. This is itself a meaningful confirmation that the PIT discipline
established independently in FRE-3 (2026-07-22) and FSI Phase 4
(2026-08-01) — five weeks and several phases apart — was applied
consistently across the codebase.

## Known limitations

- **`CompanyMemory360` is a thin composition, not a new capability** —
  it does not add anything a consumer couldn't already get by calling
  both underlying functions themselves; its value is convenience and a
  single, tested access point, not new information.
- **Inherits every limitation already disclosed in FRE-3 and Phase 4** —
  e.g. `management_history`/`major_event_history` remain empty (FRE-3's
  own disclosed, systemic gap), and Phase 4's zero-linked-fact fallback
  rules still apply unchanged.

## Recommendations for the next phase

1. If either underlying module (`company_memory.py` or
   `pit_financial_memory.py`) is ever legitimately modified in a future,
   separately-approved phase, `CompanyMemory360`'s own equivalence test
   should be re-run to confirm the composition still holds.
2. Continue the standing discipline: any future "investment reasoning
   layer" remains subject to the same exclusions restated across all six
   approvals — no alpha, ranking, scoring, or unsupported conclusion.

---

**FSI Phase 6 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
