# FSI Phase 6 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase6_preregistration.md`
(approved) and the owner's implementation instruction. Append-only.*

## Entry 0 — Start and implementation (complete)

`src/ngxrot/fre/company_memory_360.py` implements exactly the design:
a single function, `as_of(con, ticker, as_of_date) -> CompanyMemory360`,
that calls FRE-3's `build_company_memory()` and FSI Phase 4's
`pit_financial_memory.as_of()` for the same `(ticker, as_of_date)` and
returns both results in one dataclass, unmodified. Neither underlying
module's source file was touched. No new table, no new column, no new
fact, no synthesized field (explicitly: no health score, no rating, no
combined summary of any kind — the two source objects are returned
side by side, exactly as their own modules produce them).

This is the smallest possible implementation consistent with the
approved scope — a 6-line composition function — deliberately, since
any additional logic would risk reintroducing exactly the kind of
"combined signal" the pre-registration's Alternative 4 explicitly
rejected.

## Entry 1 — Validation (complete)

`scripts/fre/test_company_memory_360.py` (7/7):

1. **Output equivalence**: for all 5 real tickers across 4 real/
   representative `as_of_date` values (20 combinations), `CompanyMemory360
   .as_of()`'s two sub-results are exactly (`==`) equal to calling
   `build_company_memory()` and `pit_financial_memory.as_of()` directly —
   0 discrepancies. This directly answers the pre-registration's own
   research question: the two independently-built PIT mechanisms agree
   completely once composed, no reconciliation logic was needed.
2. **PIT leakage**: reusing the 15 real anchor documents' own filing
   dates (the same real date set Phase 4's own audit used), 0
   violations in EITHER sub-result — `corporate.filing_history` and
   every `financial` conclusion's own source facts.
3. **Mechanical guardrails**: every public function accepts at most one
   `ticker`-named parameter; `CompanyMemory360`'s own dataclass fields
   are exactly `{ticker, as_of_date, corporate, financial}` — confirmed
   by direct introspection that no synthesized score/rating/summary/
   recommendation field exists anywhere in this module.
4. **Database immutability**: all 29 tables' row counts, `integrity_
   check`, and `foreign_key_check` unchanged/clean before and after the
   full test run — this module has no write path of any kind.

No architectural blocker was encountered — the two underlying modules'
independently-built PIT mechanisms turned out to be fully compatible on
first composition, requiring no reconciliation logic and no change to
either frozen module.

## Entry 2 — Full regression and integrity verification (complete)

Full suite: `check_db_safety.py` PASS, `test_reasoning_pipeline.py` ALL
CHECKS PASSED, every prior FSI Phase 1-5 test file unchanged and
passing (period_normalization 23/23, periods_overlap 6/6, terminology_
mapping 8/8, restatement_detection 9/9, confidence_propagation 9/9,
financial_ratios 12/12, trend_classification 8/8, financial_health_
flags 11/11, reasoning_context 11/11, pit_financial_memory 15/15,
pipeline_validation 8/8, historical_defect_detection 8/8), plus the new
`test_company_memory_360.py` (7/7), FRE-2 29/29, FRE-3 16/16, FRE-4
16/16, FRE-5 21/21, FRE-6 40/40 (unchanged). Phase 5's own
`fsi_phase5_validate_pipeline.py` harness re-run and still reports PASS
on all three components — confirming Phase 6 did not disturb the
golden snapshot or cross-phase consistency in any way.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents` (11,533),
`extracted_facts` (267), and `financial_reasoning_conclusions` (177)
row counts all unchanged.

**FSI Phase 6 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
