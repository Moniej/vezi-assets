# FSI Phase 5 — Final Report

*Regression & Consistency Validation Harness. Prepared per the owner's
instruction to document detected and prevented failure modes and freeze
this phase as a baseline on completion. Full narrative and validation
detail is in `docs/fre_runs/fsi_phase5_implementation_log.md`; this
report summarizes outcomes.*

## Executive summary

FSI Phase 5 built a mechanical validation harness over the frozen FSI
Phase 1-4 pipeline (`fsi-phase4-baseline-2026-08-01`) — golden-snapshot
reproducibility, cross-phase consistency between Phase 3 and Phase 4,
and a database immutability check across all 29 tables — plus three
historical-defect-injection tests proving the harness would catch each
of three real defects drawn from this program's own incident history if
any were ever reintroduced. This phase adds **no new reasoning
capability, no new fact, no valuation, no ranking, no scoring, no alpha
claim, and no investment output** — it validates the existing pipeline
against itself, and modifies nothing in Phases 1-4.

**Result: the current, real, frozen pipeline shows zero detected
deviations.** All three historical defects, when deliberately
reintroduced on disposable scratch copies or via test-only isolated
functions, were correctly caught by the harness — confirming it is not
a rubber stamp.

## Files created

- `src/ngxrot/fre/pipeline_validation.py` — `compute_live_snapshot()`,
  `compare_snapshots()`, `verify_cross_phase_consistency()`,
  `snapshot_all_table_counts()`, `diff_table_counts()`.
- `data/reference/fsi_pipeline_golden_snapshot.json` — the frozen
  golden snapshot (106 facts, 177 conclusions, full per-conclusion
  detail).
- `scripts/fre/fsi_phase5_freeze_golden_snapshot.py` — the one-time
  freeze script.
- `scripts/fre/fsi_phase5_validate_pipeline.py` — the main harness
  entry point (run this to validate the pipeline at any future time).
- `scripts/fre/test_pipeline_validation.py` — 8 assertions (golden
  snapshot + cross-phase consistency + immutability).
- `scripts/fre/test_historical_defect_detection.py` — 8 assertions (3
  historical defects, each reproduced and shown to be detectable).
- `docs/fre_runs/fsi_phase5_implementation_log.md`,
  `fsi_phase5_final_report.md` (this document).

**No schema change was made in this phase.** No file in Phases 1-4 was
modified.

## Objective-by-objective results

### 1. Golden-snapshot reproducibility

`compute_live_snapshot()` produces a canonical, deterministically-
ordered dict (sorted keys, sorted lists) covering `extracted_facts`'
financial-fact breakdown and every one of the 177 conclusions' full
detail. `compare_snapshots()` performs a genuine byte-level comparison
(both sides canonically ordered, so dict equality IS byte-level
equality) and produces a human-readable diff on any deviation.
**Result: the live pipeline reproduces the frozen golden snapshot
exactly — 0 deviations.**

### 2. Cross-phase consistency

`verify_cross_phase_consistency()` confirms, for all 5 real tickers,
that Phase 4's `as_of()` at each ticker's own latest real filing date
returns exactly that ticker's full, unfiltered Phase 3 conclusion set,
and that the knowable set only grows (never shrinks) across every real
filing-date boundary — formalizing, as a permanent regression guard, a
property that was previously only informally verified for NASCON alone
in Phase 4's own tests. **Result: 0 violations across all 5 tickers.**

### 3. Historical defect detection

Three real defects from this program's own incident history, each
reproduced and confirmed detectable:

| Defect | Reproduced? | Detected? |
|---|---|---|
| Phase 2 restatement false-positive (overlap-only rule) | Yes — falsely flags NASCON's real FY2024 assets against its own real H1 2024 assets | Yes — the existing, corrected `find_restatement_conflicts()` does not reproduce it; the existing NASCON regression anchor would fail if the historical bug returned |
| `confidence_tier` corruption | Yes — one real conclusion's tier silently upgraded on a scratch copy | Yes — `compare_snapshots()` names the exact `conclusion_id` affected |
| `periods_overlap()` boundary confusion (equality vs. range overlap) | Yes — misclassifies NASCON's real H1-2024-vs-FY2024 pair as non-overlapping | Yes — the golden snapshot's real trend count (1 NASCON revenue trend pair, not 2) is the artifact that would catch this |

**All 3 of 3 candidate defects detected** — the pre-registered success
criterion (Phase 5's own success bar was ≥2/3), met in full.

### 4. Database immutability verification (owner's additional requirement)

`snapshot_all_table_counts()` covers all 29 real tables, not a
hardcoded subset. The main harness run
(`fsi_phase5_validate_pipeline.py`) confirms every table's row count,
`PRAGMA integrity_check`, and `PRAGMA foreign_key_check` are identical
before and after the entire validation run — this harness has no write
path to production at all.

## Regression and integrity results

Full suite passes: every prior FSI Phase 1-4 test file (11 files, 157
assertions) plus the 2 new Phase 5 test files (16 assertions), plus
`check_db_safety.py`, `test_reasoning_pipeline.py`, and all of FRE-2
through FRE-6 (FRE-6 unchanged at 40/40 — Phase 5 writes nothing to
`extracted_facts`). `PRAGMA integrity_check` → `ok`; `PRAGMA
foreign_key_check` → clean; `documents` (11,533), `extracted_facts`
(267), `financial_reasoning_conclusions` (177) all unchanged.

## Detected and prevented failure modes

**Detected in the real, current pipeline: none.** The pipeline's real
output matches its own golden snapshot exactly, and cross-phase
consistency holds for all 5 tickers.

**Prevented (would be caught if reintroduced)**: the three historical
defects above. This is the harness's core value — not that it found a
new problem today, but that it now exists as a permanent safeguard
against three specific, real ways this pipeline has previously gone
wrong (and, for the `periods_overlap()` case, a specific, realistic way
a future change could plausibly reintroduce a related but distinct
mistake).

## Known limitations

- **Only 3 candidate defects are covered**, all drawn from this
  program's own real incident history (or, for `periods_overlap()`, a
  closely related plausible confusion) — a defect of a genuinely
  different shape might not be caught. Disclosed as a real limitation,
  not overstated as comprehensive coverage.
- **The golden snapshot must be deliberately re-frozen** if a future,
  owner-approved phase legitimately changes Phase 1-4's output (e.g. a
  disclosed bug fix) — re-freezing is a manual, explicit act, never
  automatic, so a silent, unauthorized change is exactly what this
  harness is built to catch, not something it could be tricked into
  accepting.
- **Cross-phase consistency currently covers only Phase 3 ↔ Phase 4** —
  a future phase's own outputs would need this harness extended to
  cover it, not assumed compatible by default.

## Recommendations for the next phase

1. Re-run `scripts/fre/fsi_phase5_validate_pipeline.py` after any future
   change to Phases 1-4 (even an approved bug fix) — a deviation from
   the golden snapshot is expected in that case and should be reviewed
   and then deliberately re-frozen, never silently ignored.
2. If a future phase adds new reasoning capability, extend this
   harness's cross-phase consistency check to cover it, following the
   same pattern established here.
3. Continue the standing discipline: any future "investment reasoning
   layer" (the owner's own phrase) remains subject to the same
   exclusions restated across the last four approvals — no alpha,
   ranking, scoring, or unsupported conclusion — and should be
   pre-registered with the same rigor as every phase in this program.

---

**FSI Phase 5 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
