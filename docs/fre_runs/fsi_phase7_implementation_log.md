# FSI Phase 7 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase7_preregistration.md`
(approved, with the owner's added presentation-layer-only constraint)
and the owner's implementation instruction. Append-only.*

## Entry 0 — Implementation (complete)

`src/ngxrot/fre/financial_reasoning_report.py` implements a single
function, `render_report(snapshot: CompanyMemory360) -> str`, that
renders a Phase 6 snapshot into Markdown. No reasoning, inference,
scoring, ranking, summarization, health assessment, or investment
interpretation of any kind — confirmed by design and, separately, by a
mechanical forbidden-vocabulary test (Entry 1 below). No LLM call
anywhere. Neither `company_memory.py`, `pit_financial_memory.py`, nor
`company_memory_360.py` was modified — the renderer only calls
`CompanyMemory360.as_of()`'s already-built output.

**Ordering discipline (owner's requirement 8)**: corporate-memory
sections (filings, dividends, corporate actions) are rendered in the
exact order `company_memory.py`'s own queries already return them in
(chronological, `ORDER BY filing_date` — that ordering already exists
in the source, so it is preserved, not re-derived). Financial-reasoning
conclusions (ratios/trends/flags) have no inherent order of their own,
so exactly one neutral, disclosed rule is imposed: alphabetical by
`metric`, then chronological by `period_end` — never by value, status,
or whether a flag fired.

**Missing-data discipline (owner's requirement 7)**: every
`insufficient_data` conclusion is rendered in the same list as
`computed` ones, with its own `limitations` text stated in full — never
filtered out. Every `NULL` `confidence_tier` is rendered as an explicit
"confidence tier NOT RECORDED" phrase, never silently omitted or
presented as equivalent to a recorded tier.

## Entry 1 — Validation (complete)

`scripts/fre/test_financial_reasoning_report.py` (13/13):

1. Renders without exception for all 5 real tickers at their own latest
   real filing date.
2. **Determinism**: byte-identical output across 3 renders of the same
   snapshot object, AND byte-identical output for two independently-
   built snapshots of the same `(ticker, as_of_date)` — full-pipeline
   determinism, not just the renderer in isolation.
3. The explicit `NULL`-confidence-tier phrase appears in at least one
   real report (Phase 1's legacy revenue/net_profit facts).
4. Every `insufficient_data` conclusion in each snapshot appears exactly
   once in its own report — a direct count-match check, not a spot
   check.
5. **Sentence-to-field traceability**: every conclusion's own `method`
   and `limitations` text appears VERBATIM in its ticker's report —
   proving every statement maps directly to stored data, per the
   owner's own validation requirement.
6. **Field coverage**: every real filing (`doc_id`) and every real
   dividend/corporate-action fact (`fact_id`) across all 5 snapshots
   appears in its own rendered report.
7. **Ordering discipline verified mechanically**: `_sorted_conclusions()`
   orders strictly by `(metric, period_end)`, confirmed against Python's
   own `sorted()` on the same key — not merely inspected by eye.
8. **Single-ticker-scope guardrail**, same style as Phases 3-6: every
   public function accepts at most one `ticker`-named parameter.
9. **Forbidden-vocabulary check**: no ranking/scoring/recommendation
   word (buy, sell, recommend, target price, expected return,
   undervalued, overvalued, and whole-word rank/score/rating) appears
   anywhere in any of the 5 real reports OUTSIDE the module's own fixed
   disclaimer sentence (which legitimately names these excluded
   categories to state what the report does not do). **A real false
   positive was found and fixed during test development**: a
   substring-only check flagged "rating" inside the real financial term
   "Operating Profit" and flagged "rank"/"score" inside the disclaimer's
   own required text ("no ranking", "no health score") — fixed by
   excluding the disclaimer sentence from the scan and using whole-word
   matching for the three ambiguous terms, disclosed here as a real
   test-development finding, not swept past.
10. Database immutability: all 29 tables' row counts, `integrity_
    check`, and `foreign_key_check` unchanged/clean before and after
    the full test run.

## Entry 2 — Full regression and integrity verification (complete)

Full suite: `check_db_safety.py` PASS, `test_reasoning_pipeline.py` ALL
CHECKS PASSED, every prior FSI Phase 1-6 test file unchanged and
passing (12 files, 165 assertions), plus the new `test_financial_
reasoning_report.py` (13/13), FRE-2 29/29, FRE-3 16/16, FRE-4 16/16,
FRE-5 21/21, FRE-6 40/40 (unchanged). Phase 5's own
`fsi_phase5_validate_pipeline.py` harness re-run and still reports PASS
on all three components.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents` (11,533),
`extracted_facts` (267), and `financial_reasoning_conclusions` (177) row
counts all unchanged. This module has zero write path of any kind.

**FSI Phase 7 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.