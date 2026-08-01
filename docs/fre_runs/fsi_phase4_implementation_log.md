# FSI Phase 4 — Implementation Log

*Live journal, appended to throughout implementation, not reconstructed
afterward. Per `docs/fre_runs/fsi_phase4_preregistration.md` (approved)
and the owner's implementation instruction. Append-only.*

## Entry 0 — Start

Implementation begins exactly per the approved pre-registration:
read-only `CompanyFinancialReasoningMemory.as_of(ticker, date)` over
Phase 3's frozen `fsi-phase3-baseline-2026-08-01` conclusions, gated by
`documents.filing_date` (public availability), never by financial
period dates. No new facts, no new extraction, no valuation, no
ranking, no scoring, no alpha claims, no portfolio outputs, no
recommendations. Phase 3 itself is not modified.

## Entry 1 — Design resolution: the zero-linked-fact edge case

Before writing code, a real edge case was found by direct query: 4 of
Phase 3's 24 `insufficient_data` conclusions have **zero** linked source
facts (`CAP`'s FY2020 `debt_to_equity`, and `AFRIPRUD`/`CAP`/`UCAP`'s
ticker-wide `cash_flow_earnings_divergence` flag, which has no
`period_start`/`period_end` at all since it is not about one period).
A conclusion with no source fact cannot be PIT-gated by "the latest of
its own facts' filing dates" (Area 1's primary rule), since there are no
facts to check. Two sub-cases were resolved differently, deliberately:

- **Period-specific, zero-fact** (CAP FY2020 `debt_to_equity`): the
  absence of balance-sheet data is a property of ONE specific filing
  (doc 4508, already disclosed in Phase 2 Stage 2's own notes: "only a
  leverage ratio, no absolute Naira amounts"). Gated by the EARLIEST
  filing_date among ALL of that ticker's real facts for that exact
  period — i.e. the date doc 4508 itself became public, since that is
  when the absence became knowable.
- **Ticker-wide, zero-fact, no period** (`cash_flow_earnings_divergence`
  for AFRIPRUD/CAP/UCAP): this is a claim about the COMPLETE set of a
  ticker's processed filings ("no cfo fact exists anywhere"), which is
  only true once every filing Phase 2 actually processed for that
  ticker has been seen. Gated by the LATEST filing_date among ALL of
  that ticker's real facts — the conservative choice, since claiming
  "no cfo ever" before all known filings are in would itself be a
  premature, unsupported claim.

Both rules are implemented as explicit, named fallback functions,
disclosed in the module docstring — never a silent default.

## Entry 2 — Module built: `src/ngxrot/fre/pit_financial_memory.py` (complete)

`as_of(con, ticker, as_of_date) -> CompanyFinancialReasoningSnapshot`
implements Area 1's gating rule exactly: a conclusion is knowable iff
`max(source fact filing_dates) <= as_of_date`, with the two disclosed
fallback rules (Entry 1) for the 4 zero-linked-fact conclusions.
`audit_no_lookahead(con, ticker, as_of_date)` independently re-checks
every returned conclusion's own per-fact filing dates against
`as_of_date` directly — not merely re-asserting `as_of()`'s own internal
computation, so a bug in the gating logic itself would still be caught.
**No write path exists anywhere in this module** — every function is a
pure read/filter over already-frozen Phase 3 data.

**Real sanity check against NASCON before writing formal tests**: `as_of`
at `2024-07-30` (day before NASCON's first real filing) → 0 knowable, 33
excluded. At `2024-07-31` (that filing's own date) → 5 knowable (exactly
the 5 ratios computable from that single filing's own facts — no trend
is possible yet, since NASCON's only valid trend pair needs its SECOND
and third filings). At `2025-03-04` (second filing) → 10 knowable. At
`2026-03-03` (NASCON's own last real filing) → all 33 of NASCON's real
conclusions knowable, 0 excluded — confirmed this equals NASCON's total
row count in `financial_reasoning_conclusions` exactly.

## Entry 3 — PIT leakage audit and restatement-preservation test (complete)

`scripts/fre/fsi_phase4_pit_audit.py` tests all 30 real points (one day
before + one on the filing_date, for each of the 15 anchor documents'
own filing_date) — **0 look-ahead violations found**, the pre-registered
success criterion for Area 3, met exactly.

`scripts/fre/test_pit_financial_memory.py` (15/15): the NASCON gating
sequence above, both zero-linked-fact fallback rules (CAP FY2020
`debt_to_equity` — period-specific, gated by doc 4508's own filing date;
UCAP's ticker-wide `cash_flow_earnings_divergence` — gated by UCAP's
LATEST real filing date), the mechanical single-ticker-scope guardrail
(same `inspect.signature` style audit as Phase 3's Area 7), and —
**requirement 2, historical corrections/restatements preserve the
original knowledge state** — a disposable scratch fixture (matching
`test_restatement_detection.py`'s own established precedent for testing
a mechanism the real dataset doesn't naturally exercise, since
`restates_fact_id` is 0 database-wide after Phase 2's Entry 5
correction): a synthetic conclusion tied to a real, pre-restatement fact
(CAP's real fact_id 181, doc 4508) remains knowable, unchanged, and
byte-identical in its own `value_numeric`/`method` both BEFORE and AFTER
a synthetic later "restating" document's own filing date — proving the
append-only architecture plus per-fact filing-date gating together
satisfy requirement 2 by construction, without any additional
restatement-chain-resolution logic being necessary.

## Entry 4 — Full regression and integrity verification (complete)

Full suite: `check_db_safety.py` PASS, `test_reasoning_pipeline.py` ALL
CHECKS PASSED, `test_period_normalization.py` 23/23, `test_periods_
overlap.py` 6/6, `test_terminology_mapping.py` 8/8, `test_restatement_
detection.py` 9/9, `test_confidence_propagation.py` 9/9, `test_financial_
ratios.py` 12/12, `test_trend_classification.py` 8/8, `test_financial_
health_flags.py` 11/11, `test_reasoning_context.py` 11/11, `test_pit_
financial_memory.py` 15/15, `fsi_phase4_pit_audit.py` 0 violations /30
points, FRE-2 29/29, FRE-3 16/16, FRE-4 16/16, FRE-5 21/21, FRE-6 40/40
(unchanged — Phase 4, like Phase 3, writes zero rows to
`extracted_facts` or `financial_reasoning_conclusions`, so no stale-
assertion update was needed).

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents` unchanged
at 11,533; `extracted_facts` unchanged at 267;
`financial_reasoning_conclusions` unchanged at 177 (Phase 4 has no
write path to this table at all — every conclusion it can ever return
was already written by Phase 3); no test-fixture leakage into
production (confirmed by direct query).

**FSI Phase 4 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
