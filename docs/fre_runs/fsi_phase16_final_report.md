# FSI Phase 16 — Final Report

*Composition-Layer Ticker Coverage Fix. Full narrative in
`docs/fre_runs/fsi_phase16_implementation_log.md`.*

## Executive summary

FSI Phase 16 found and fixed a real, demonstrated piece of validation
debt: every dedicated per-phase test file for Phase 6, 7, 8, 10, 11, 12
had hardcoded the original 5-ticker list and was NEVER updated after
Phase 13 grew the real roster to 10 — meaning every regression run since
Phase 13 silently tested only half the real tickers while its own
assertion text still claimed "for all 5 tickers." Fixed by switching all
6 files to dynamic ticker discovery (`financial_ratios.list_tickers()`,
the same function every production module already uses), closing the
root cause rather than just re-hardcoding a new number that would go
stale again at the next expansion. Also added a 4th component to Phase
5's validation harness — a coarse, cross-ticker smoke check across the
whole composition chain — as the platform-level mechanism that would
catch this exact class of gap automatically in the future.

## Files modified

- `scripts/fre/test_company_memory_360.py`, `test_financial_reasoning_
  report.py`, `test_company_thesis_360.py`, `test_entity_context.py`,
  `test_company_research_dossier.py`, `test_generate_research_dossier.py`
  — ticker-list source changed from hardcoded to dynamic.
- `scripts/fre/fsi_phase5_validate_pipeline.py` — new Component 4
  (composition-layer smoke coverage); Component 3's ordering adjusted so
  the immutability check correctly spans the entire run.

**No modification to any production module's own logic.**

## Two real fixes found beyond a mechanical find-and-replace

1. `test_company_thesis_360.py`'s ground-truth `EXPECTED_FIRED_CONCERNS`
   map needed 5 new real entries (obtained via direct SQL query, not
   assumed): MTNN/OANDO/NESTLE fire `margin_compression`; DANGCEM/UBN
   fire nothing.
2. `test_entity_context.py`'s equivalence check incorrectly required a
   non-NULL `entities` row to count as a match — wrong for the 5
   Phase-13 tickers, none of which has one yet (a disclosed, deferred
   gap). Fixed so "both sides empty" correctly counts as equivalence.

## Validation results

All 6 fixed test files pass in full (69 assertions total, now covering
10 tickers instead of 5, zero regression in any existing ticker-specific
assertion). Phase 5 harness: all 4 components PASS. Full regression: 26
test files, all green. `check_db_safety.py` PASS. `test_reasoning_
pipeline.py` ALL CHECKS PASSED.

## Recommendations for the next phase

The root-cause fix (dynamic ticker discovery) means no future coverage-
expansion phase should need to touch these 6 test files again — Phase 5's
new Component 4 provides an additional, automatic backstop even if it
did. Per the owner's standing continuous-execution authorization,
proceeding to Phase 17 (Portfolio-memory cross-reference, Part 9's last
undone Tier-1 item).

---

**FSI Phase 16 is complete: fully implemented, validated, and
documented.**
