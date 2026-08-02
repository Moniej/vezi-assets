# METH-002 — CBN Risk-Free Rate Fix: Implementation Log + Final Report

*2026-08-02. Design record: `docs/PREREG_METH-002_risk_free_rate.md`. This
closes the **Immediate**-priority item from
`docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`'s headline finding: every
Sharpe ratio this platform has reported through H-012 used a disclosed,
flat `rf_annual_pct=0.0` placeholder.*

## What was built

- `data/reference/cbn_mpr_history.csv` — 50 real, individually-verified
  CBN Monetary Policy Rate decisions, 2015-07-23 to 2026-07-21, each row
  carrying `source`, `source_url`, `retrieved_date`, `confidence`.
- `src/ngxrot/riskfree.py` — new module: `load_mpr_history()`,
  `mpr_asof_series()` (point-in-time as-of lookup, `NaN` before verified
  coverage begins, no look-ahead by construction), `coverage_status()`.
- `src/ngxrot/metrics.py::compute()` — new optional `rf_series` parameter
  (additive; `None` by default reproduces prior behavior exactly). When
  given, computes `sharpe_vs_real_rf` from real daily excess returns
  (portfolio return minus that day's compounding-consistent MPR-implied
  daily rate), reported alongside the existing `sharpe_vs_rf`, never
  replacing it. Reports `real_rf_ann_pct_mean` and `real_rf_coverage_gap`
  (0 if the whole window has verified coverage; otherwise the Sharpe is
  `None`, never a value computed over a partially-fabricated series).
- `src/ngxrot/runner.py` — new opt-in `validation.use_real_risk_free_rate`
  config flag (default `False`); a small `_rf_series_if_enabled()` helper
  wired into all three `metrics.compute()` call sites (`cross_sectional`,
  `full`, and `lite` engines). `risk_free_rate_is_placeholder` now
  correctly reads `False` only when the real rate was requested AND fully
  covered the window — never on the strength of the flag alone.
- `scripts/rehearse_riskfree.py` — 11 synthetic/structural checks (T1–T6).
- `scripts/compute_real_rf_evidence.py` — read-only application to every
  resolved hypothesis's frozen final-evaluation config (same
  registry-bypassing rerun pattern as METH-001's DSR evidence script, for
  the same reason: avoids the frozen-hypothesis SQL trigger on H-001 and
  avoids ledger noise for a pure metrics-recomputation task).
- `experiments/real_rf_evidence_2026-08-02.json` — the permanent,
  git-tracked evidence output.

## Data verification (before any design was frozen)

Three independent fetches of CBN's official MPC decisions page, cross-
checked against each other's stated meeting-sequence numbers. This caught
a real extraction error: an initial wide-range pull mislabeled the 302nd
meeting (a real **2025-09-22/23** decision) as "September 22-23, **2023**"
— corrected via the meeting-number cross-check before it could enter the
reference table. The one real, disclosed gap (no MPC meeting held between
Jul 2023 and Feb 2024, during CBN's leadership transition) is a historical
fact, not a scraping omission — see `docs/PREREG_METH-002_risk_free_rate.md`
Section 1.

## Validation (synthetic, before any real evidence was touched)

| Check | Result |
|---|---|
| T1: no look-ahead across a known MPR change (2016-07-26, 12%→14%) | PASS (day before: 12%, decision day and after: 14%) |
| T2: pre-coverage date (2010) returns NaN, not a filled value | PASS |
| T3: `coverage_status()` distinguishes covered vs. gapped ranges | PASS |
| T4: `metrics.compute()` byte-for-byte identical when `rf_series` omitted | PASS |
| T5: real-rf Sharpe materially differs from flat-rf Sharpe on a synthetic 2018+ window | PASS |
| T6: pre-coverage window returns `sharpe_vs_real_rf=None`, not a fabricated number | PASS |

11/11 checks passed (T1/T4 have sub-checks). Existing R1–R12 rehearsal
suite re-run afterward — all still pass; no regression.

## Real evidence: every resolved hypothesis, before/after

Integrity check: for all 11 hypotheses, the flat-0.0 Sharpe recomputed via
a fresh read-only rerun of the frozen final-evaluation config matched the
originally-stored registry value **exactly** (11/11) — the rerun path is
faithful.

| Hypothesis | Flat-0.0 Sharpe (as reported through today) | Real CBN-MPR Sharpe | Mean real rate over window | Coverage |
|---|---:|---:|---:|---|
| H-001 | 1.554 | 0.753 | 16.68% | full |
| H-003 | 0.624 | 0.067 | 15.20% | full |
| H-004 | 1.093 | 0.416 | 15.20% | full |
| H-005 | -1.108 | -1.840 | 15.17% | full |
| H-006 | 0.134 | **None** | — | **gap (14 days precede 2015-07-23)** |
| H-007 | 1.136 | 0.365 | 14.95% | full |
| H-008 | 1.164 | -0.099 | 14.95% | full |
| H-009 | 1.624 | 0.708 | 14.95% | full |
| H-010 | 1.721 | 0.728 | 14.95% | full |
| **H-011** | **2.244** | **1.228** | 14.95% | full |
| H-012 | 1.143 | 0.013 | 14.95% | full |

## Honest interpretation

Every single hypothesis's Sharpe ratio falls substantially once measured
against a real ~15–17% Nigerian policy rate instead of a flat 0%. This is
economically unsurprising, not an artifact: these are long-only equity
strategies, and NGN T-bill-equivalent rates over this sample were high in
both nominal and real terms — a strategy earning, say, 20% gross when cash
alone earned 15% has created much less "excess return per unit of risk"
than a naive 0%-rf Sharpe suggests. **H-011 remains the highest of the 10
hypotheses with full coverage (1.228)**, consistent with it being the
platform's only confirmed factor, though its own real-rf Sharpe is now
materially lower than its previously-reported 2.244. H-008 and H-012 (both
already-rejected volatility variants) turn slightly negative under the
real rate, reinforcing rather than reversing their rejections. **H-006's
`None` result is itself the correct, disclosed behavior** — its
final-evaluation window begins 14 days before verified MPR coverage starts
(2015-07-23), and the honest answer is "not yet computable," not a value
estimated from an incomplete series.

**What this does and does not change**: no hypothesis's ledger status
changes. This is a new, more correct metric reported *alongside* the
existing one, exactly as METH-001's DSR was — not a silent replacement,
and not grounds by itself to reopen any `rejected`/`confirmed` status
(those were resolved against pre-registered, per-hypothesis criteria that
did not include this metric at the time).

## Interaction with METH-001 (disclosed, not performed here)

METH-001's Deflated Sharpe Ratio used each hypothesis's flat-0.0-rf,
excess-*vs-benchmark* daily Sharpe — a different quantity from this
phase's excess-*vs-real-risk-free* Sharpe. Recomputing DSR against real-rf
Sharpe ratios is a distinct next exercise, not conflated with this report.

## Regression / ledger impact

No registry writes; no hypothesis status changed. `data/registry.sqlite`
was not touched — `compute_real_rf_evidence.py` deliberately bypasses
`registry.record_experiment`, identical in rationale to METH-001's
evidence script.

## Next steps (named, not performed here)

1. Recompute METH-001's DSR using real-rf Sharpe ratios as the trial-pool
   input, for a fully rate-corrected confidence view of H-011.
2. Consider FMDQ/DMO actual T-bill stop rates (METH-002's own Section 2
   names this as the rejected-for-now alternative) as a future refinement
   — the lookup interface built here (`riskfree.py`) is rate-source-
   agnostic and would not need to change shape to accept a different
   source.
3. Extend `use_real_risk_free_rate` to any future hypothesis's config as
   the new default expectation going forward, while leaving all frozen
   historical configs (H-001–H-012) exactly as originally recorded.
