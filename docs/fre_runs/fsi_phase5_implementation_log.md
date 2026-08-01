# FSI Phase 5 — Implementation Log

*Live journal, appended to throughout implementation, not reconstructed
afterward. Per `docs/fre_runs/fsi_phase5_preregistration.md` (approved)
and the owner's implementation instruction. Append-only.*

## Entry 0 — Start

Implementation begins exactly per the approved pre-registration and the
owner's explicit objectives: (1) golden snapshot reproducibility, (2)
cross-phase consistency, (3) historical defect detection (3 named real
cases), plus the owner's additional requirement: database immutability
verification (row counts + integrity before/after every validation run).
No new reasoning capability, no new fact, no valuation, no ranking, no
alpha claim, no investment output, no modification of Phases 1-4's
frozen behavior. Builds on `fsi-phase4-baseline-2026-08-01` (106 facts,
177 conclusions).

## Entry 1 — Golden snapshot module and freeze (complete)

`src/ngxrot/fre/pipeline_validation.py`'s `compute_live_snapshot()`
produces a canonical, deterministically-ordered dict (sorted keys, every
list sorted, no reliance on SQLite's own row order) covering
`extracted_facts`' financial-fact count and per-fact-type breakdown, and
every one of `financial_reasoning_conclusions`' 177 rows in full detail
(value, status, confidence_tier, period). `compare_snapshots()` does a
plain dict equality check (already byte-level, since both sides are
canonically ordered) and additionally produces a human-readable diff
list for any deviation found.

`scripts/fre/fsi_phase5_freeze_golden_snapshot.py` froze
`data/reference/fsi_pipeline_golden_snapshot.json` from the real,
current, frozen state — confirmed exactly: 106 financial facts (assets
14, capex 1, cff 4, cfi 3, cfo 4, ebit 12, ebitda 9, equity 14, fcf 1,
liabilities 14, net_profit 15, revenue 15), 177 conclusions (75 ratio +
87 trend + 15 flag). Read-only against production; writes only to this
one repository reference file.

## Entry 2 — Cross-phase consistency (complete)

`verify_cross_phase_consistency()` checks, for all 5 real tickers: (a)
`pit_financial_memory.as_of(ticker, <ticker's own latest real filing
date>)` returns EXACTLY that ticker's full, unfiltered conclusion set
(0 violations, confirmed for all 5 — this had only been informally
verified for NASCON alone in Phase 4's own tests); (b) monotonicity —
the knowable set at each successive real filing-date boundary is always
a superset of the prior one, for every ticker (0 violations) — a
property that was true by construction in Phase 4 but had never been
formalized as its own permanent, re-runnable regression guard until now.

## Entry 3 — Historical defect detection (complete)

`scripts/fre/test_historical_defect_detection.py` reproduces three real
defects, each on a disposable scratch copy or via a locally-defined
broken function that is never imported by any real pipeline module:

1. **The Phase 2 restatement false-positive** (Entry 4/5 of
   `fsi_phase2_implementation_log.md`): the historical, pre-fix
   overlap-only rule is reproduced verbatim and confirmed to STILL
   falsely flag NASCON's real FY2024 assets as restating its own real H1
   2024 assets — proving this is a real, reproducible defect, not a
   hypothetical. The CURRENT, corrected `find_restatement_conflicts()`
   is confirmed NOT to reproduce it on the same real data — meaning
   `test_restatement_detection.py`'s existing NASCON anchor would fail
   immediately if this historical bug were ever reintroduced.
2. **Confidence-tier corruption**: on a scratch copy, one real
   `NULL`-tier conclusion's `confidence_tier` is corrupted to
   `direct_reported`; `compare_snapshots()` against the golden snapshot
   correctly detects and names the exact `conclusion_id` affected.
3. **A `periods_overlap()` boundary confusion**: a deliberately-broken
   variant that checks for an EXACT period match (mixing up the
   restatement-detection fix's "equivalent reporting spans" rule with
   the DIFFERENT range-overlap rule trend classification actually
   needs — a genuinely plausible mistake given how closely related the
   two concepts are) is confirmed to misclassify NASCON's real H1-2024-
   vs-FY2024 pair as non-overlapping (the opposite of the current,
   correct answer). The golden snapshot's real, frozen trend count (1
   NASCON revenue trend pair, not 2) is confirmed as the artifact that
   would catch this deviation if the defective function were ever used
   in the real module.

All defect injection happened only on disposable scratch copies or via
functions that exist solely inside this one test file — confirmed by
direct query that production was never touched.

## Entry 4 — Database immutability verification and main harness runner (complete)

`snapshot_all_table_counts()`/`diff_table_counts()` check row counts
across ALL 29 real tables in the database, not just the ones Phase 5's
own logic happens to read. `scripts/fre/fsi_phase5_validate_pipeline.py`
is the single entry point tying all three components together — run
directly against production: **PASS** on every component (golden
snapshot byte-identical; 0 cross-phase consistency violations; all 29
tables' row counts, `integrity_check`, and `foreign_key_check`
unchanged/clean before and after the run).

## Entry 5 — Full regression and integrity verification (complete)

Full suite: `check_db_safety.py` PASS, `test_reasoning_pipeline.py` ALL
CHECKS PASSED, every prior FSI Phase 1-4 test file unchanged and
passing (`test_period_normalization.py` 23/23, `test_periods_
overlap.py` 6/6, `test_terminology_mapping.py` 8/8, `test_restatement_
detection.py` 9/9, `test_confidence_propagation.py` 9/9, `test_financial_
ratios.py` 12/12, `test_trend_classification.py` 8/8, `test_financial_
health_flags.py` 11/11, `test_reasoning_context.py` 11/11, `test_pit_
financial_memory.py` 15/15), plus the 2 new Phase 5 test files
(`test_pipeline_validation.py` 8/8, `test_historical_defect_
detection.py` 8/8), FRE-2 29/29, FRE-3 16/16, FRE-4 16/16, FRE-5 21/21,
FRE-6 40/40 (unchanged — Phase 5 has no write path to production at
all, confirmed directly).

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents` (11,533),
`extracted_facts` (267), and `financial_reasoning_conclusions` (177) row
counts all unchanged.

**No detected failure modes in the real, current pipeline** — all three
historical defects, when deliberately reintroduced on scratch copies or
via isolated test-only functions, were correctly detected; the harness
found 0 real deviations in the actual frozen Phase 1-4 output.

**FSI Phase 5 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
