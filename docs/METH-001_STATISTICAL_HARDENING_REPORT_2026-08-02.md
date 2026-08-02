# METH-001 — Cross-Hypothesis Statistical Hardening: Implementation Log + Final Report

*2026-08-02. Pre-registration frozen before any real value was computed:
`docs/PREREG_METH-001_statistical_hardening.md`. This is Phase R1 of
`docs/INSTITUTIONAL_AUDIT_WAVE2_2026-08-02.md`'s own roadmap — the highest-
priority item identified there. Not a factor hypothesis; a statistical-
inference infrastructure addition, reported with the same rigor as a
hypothesis per the platform's "additive-only, regression-tested,
documented, committed, tagged" convention.*

## What was built

Three new, additive functions in `src/ngxrot/stats.py` (nothing existing
modified):
- `newey_west_tstat(x, lag=None)` — HAC-corrected one-sample t-test
  (Newey & West, 1987), Bartlett kernel, automatic bandwidth
  `floor(4*(T/100)^(2/9))` (Newey & West, 1994) unless overridden.
- `probabilistic_sharpe_ratio(sr_hat, sr_benchmark, skew, kurtosis, n_obs)`
  — PSR (Bailey & López de Prado, 2012).
- `deflated_sharpe_ratio(trial_sharpes, focal_sharpe, focal_skew, focal_kurtosis, focal_n_obs)`
  — DSR (Bailey & López de Prado, 2014), returning both the deflated
  probability and the chance-benchmark Sharpe it was measured against
  (never just the final number).
- A supporting `_norm_ppf` (inverse normal CDF, Acklam's approximation)
  and `_norm_cdf` helper — no new third-party dependency added.

Supporting, non-`stats.py` additions:
- `scripts/compute_dsr_evidence.py` — read-only recomputation of the daily
  net-return series for every resolved hypothesis's frozen final-evaluation
  config (needed because the registry stores only annualized summary
  metrics, not the raw series or its higher moments). Deliberately bypasses
  `runner.run_resolved()`'s registry-write path (which would fail outright
  for H-001, already frozen, and would add ledger noise for the rest) by
  replicating only the read path directly against `backtest_lite.run` /
  `backtest_xs.run_from_config`.
- `experiments/dsr_evidence_2026-08-02.json` — the permanent, git-tracked
  output: per-hypothesis daily excess Sharpe, T, skewness, kurtosis, and an
  integrity check (recomputed vs. originally-stored annualized Sharpe).
- `scripts/rehearse_stats_hardening.py` — synthetic validation (S1-S5),
  mirroring the existing R1-R12 convention.

## Validation (synthetic, run before any real evidence was touched)

| Check | Result |
|---|---|
| S1: HAC(lag=0) matches i.i.d. t-stat on white noise | PASS |
| S2: HAC \|t\| < i.i.d. \|t\| under real AR(1) autocorrelation (ρ=0.6) | PASS (hac t=1.768 vs iid t=3.118, lag=9) |
| S3: DSR(N=1) reduces exactly to PSR(SR*=0) | PASS |
| S4: DSR non-increasing in N for fixed focal inputs | PASS (0.989→0.788→0.562→0.429→0.338 for N=2,5,10,20,40) |
| S5: DSR of a genuinely zero-mean strategy stays low across N | PASS (0.054, 0.001, 0.001 for N=5,15,30) |

5/5 passed. All are checks against known analytical/monotonicity properties
on synthetic data — not tuned against, or informed by, the real NGX
evidence applied afterward.

## Regression (existing suite, re-run after the additions)

R1-R12 (rehearse_xs_engine.py, rehearse_xs_engine_v2.py,
rehearse_xs_size.py, rehearse_xs_pooled.py) — all still pass. `stats.py`'s
existing functions (`excess_ttest`, `holm`, `benjamini_hochberg`,
`placebo_p_value`) were not modified; the new functions are additive only.

## Integrity check on the evidence-recomputation script

For all 11 resolved hypotheses, the annualized Sharpe recomputed from a
fresh, read-only rerun of the frozen final-evaluation config matched the
originally-stored registry value **exactly** (11/11) — confirming the
rerun faithfully reproduces history rather than silently drifting from it.

## Real evidence: daily excess Sharpe ratios (recomputed, all 11 resolved hypotheses)

| Hypothesis | Daily excess Sharpe (vs. benchmark) | Engine |
|---|---:|---|
| H-001 | -0.0032 | lite |
| H-003 | -0.0016 | lite |
| H-004 | +0.0223 | lite |
| H-005 | -0.1691 | lite |
| H-006 | -0.0941 | cross_sectional |
| H-007 | -0.0215 | cross_sectional |
| H-008 | -0.0706 | cross_sectional |
| H-009 | +0.0165 | cross_sectional |
| H-010 | +0.0173 | cross_sectional |
| **H-011** | **+0.0564 (highest of all 11)** | cross_sectional |
| H-012 | -0.0780 | cross_sectional |

## Application to H-011 (the only confirmed factor)

**HAC-corrected inference**: t=2.205, p=0.02744 (Newey-West, lag=7,
automatic bandwidth), versus the existing i.i.d. t=2.646, p=0.00815 — still
below the conventional 0.05 bar, but visibly weaker once daily
autocorrelation is accounted for.

**Deflated Sharpe Ratio**, two trial-pool definitions (both reported, not
just the more favorable one):

| Trial pool | N | Chance-benchmark Sharpe (sr_star) | DSR |
|---|---:|---:|---:|
| All 11 resolved hypotheses | 11 | 0.1071 | **0.0071** |
| Cross-sectional-engine hypotheses only (H-006–H-012) | 7 | 0.0797 | **0.1304** |

**Honest interpretation**: H-011's own daily excess Sharpe (0.0564) is the
highest of any hypothesis this platform has tested — a genuinely
noteworthy fact on its own. But under either trial-pool definition, the
Deflated Sharpe Ratio is far below what its per-hypothesis Holm-corrected
p-value (0.049) or placebo p-value (0.0099) would suggest in isolation.
Under the full 11-trial pool, the chance-benchmark Sharpe (0.107) actually
*exceeds* H-011's own Sharpe — meaning that, adjusted for having run 11
independent trials against the same NGX history, H-011's result does not
clearly stand out from what the best of 11 random strategies would be
expected to produce by chance alone.

**Why the two trial-pool numbers differ so much (disclosed, not
smoothed over)**: H-005's daily excess Sharpe (-0.1691) is a large outlier
relative to the other 10 — it is also structurally the most different
strategy in the pool (an event-window "lite"-engine design with many
near-zero-exposure days between MPC announcements, unlike the other 10
which are continuously invested). Including it inflates the cross-trial
variance substantially, which inflates the chance-benchmark Sharpe under
the extreme-value approximation. This is exactly the "trials should be
comparable" concern flagged as a pre-declared limitation in the
pre-registration — pooling structurally different strategy designs into
one variance estimate is a real methodological question, not a settled
one, and the sensitivity shown here (0.007 vs 0.130) is the honest way to
surface that rather than pick whichever pool produces the preferred
number.

**What this does and does not change**: H-011's ledger status remains
`confirmed` — the pre-existing per-hypothesis validation criteria that
earned that status have not changed and are not retroactively altered.
What changes is the *interpretive confidence* attached to that
confirmation once viewed through a program-wide, multiple-testing-aware
lens: materially weaker than the per-hypothesis number alone suggests,
under every reasonable trial-pool definition tested. This is recorded
permanently in `docs/FACTOR_REGISTRY.md`'s H-011 entry, not filed away
separately from the headline result.

## Benchmarking (mandatory, per the new directive)

**Frontier Market Assessment**
- *Current adoption*: no evidence found of DSR/PBO/HAC-style
  multiple-testing correction in published frontier-market (NGX or
  broader African) factor research in this audit's literature review —
  this is stated as an absence of evidence, not evidence of absence; a
  systematic literature search was not performed as part of this pass.
- *Practicality*: directly practical here — the platform already has a
  permanent, queryable trial ledger (`data/registry.sqlite`), which is the
  one precondition DSR needs and which most frontier-market research
  shops, publishing one paper at a time, typically lack.
- *Strengths*: uses only data already collected; no new vendor, no new
  cost.
- *Weaknesses*: frontier markets' short histories (NGX: ~10 years) mean
  T is small relative to developed-market applications of DSR (which
  often use decades of data) — the PSR term's `sqrt(T-1)` scaling means
  this platform's version of the test has less power to begin with,
  compounding the multiple-testing penalty rather than offsetting it.

**Emerging Market Assessment**
- *Adoption*: DSR/PBO are used in developed-market quant research and
  increasingly cited in EM-focused practitioner literature (e.g., AQR and
  Research Affiliates publications extending factor research to EM
  universes), but this audit found no specific evidence of their
  application to Nigerian or African frontier equities specifically —
  again, absence of evidence in this review, not a claim of absence in
  the literature at large.
- *Academic support*: the underlying papers (Bailey & López de Prado 2012,
  2014; Newey & West 1987, 1994) are general-purpose statistical results,
  not market-specific — they apply to any return series regardless of
  market classification.
- *Known failures*: none documented in this pass; this is a new
  application, not a retest of a known-failed technique.
- *Required adjustments*: none beyond what is already disclosed (trial
  independence assumption, trial-pool comparability).

**Developed Market Assessment**
- *Institutional usage*: DSR and PBO are cited by López de Prado's own
  publicly-documented work at Guggenheim Partners/AQR-adjacent research
  and taught in *Advances in Financial Machine Learning* (Wiley, 2018) as
  standard practice for controlling backtest-selection bias; treated as
  a serious, real institutional technique, not experimental, in developed
  quant research.
- *Evidence quality*: strong — closed-form, peer-reviewed, widely cited.
- *Implementation complexity*: moderate — the formula itself is simple
  (as implemented here, ~40 lines), but correctly sourcing its inputs
  (comparable trial pool, consistent frequency) is where real judgment is
  required, as this report's own trial-pool sensitivity analysis shows.

**Statistical Robustness** (per the new mandatory checklist)
- HAC/Newey-West usage: **implemented this phase** (`newey_west_tstat`).
- Multiple hypothesis correction: **implemented at two levels now** —
  within-hypothesis (pre-existing Holm/BH) and, as of this phase,
  cross-hypothesis (DSR).
- Deflated Sharpe Ratio: **implemented this phase.**
- Probability of Backtest Overfitting: **still missing** — explicitly
  deferred per the pre-registration (Section 6), pending a
  Combinatorial-Purged-CV design pass. Not approximated here.
- White's Reality Check / SPA test: **still missing** — deferred pending
  a registry-schema extension to track discarded (not just pre-registered)
  configurations. Not approximated here.
- Sample independence: **addressed for daily autocorrelation** (HAC);
  **not addressed for cross-hypothesis independence** (DSR's own
  limitation, disclosed above and in the pre-registration).
- Survivorship bias: **not addressed by this phase** — remains the
  separate, open item flagged in the institutional audit (Phase R5 there).
- Selection bias: **directly what DSR targets** — this phase's core
  contribution.
- Look-ahead bias: **not in scope for this phase** — already separately
  audited per-hypothesis (e.g. H-012's independent re-derivation).
- Data snooping risk: **DSR is the direct mitigation implemented here**;
  residual risk from trial-pool composition choices is disclosed above,
  not hidden.

## Ledger / registry impact

None. `data/registry.sqlite` was not written to by this phase — the
evidence-recomputation script deliberately bypasses `registry.record_experiment`
(see script docstring). No hypothesis status changed. H-011 remains
`confirmed`; all rejected hypotheses remain `rejected`. The new,
permanent artifact is `experiments/dsr_evidence_2026-08-02.json`
(git-tracked) plus this report and the `FACTOR_REGISTRY.md` update.

## Next gap analysis (per step 15 of the methodology)

With METH-001 complete, the audit's Phase R2 (H-011 interaction forensics
— Size×Volatility, Size×Momentum, Size×Liquidity) should now be read under
this hardened lens from the outset: any future confirmation should report
its DSR against the now-12-trial pool (once R2 itself becomes trial #12),
not just its own per-hypothesis correction. PBO and White/SPA remain
correctly deferred, named dependencies (Combinatorial Purged CV design;
registry schema extension for discarded configurations) rather than
something to approximate under time pressure.
