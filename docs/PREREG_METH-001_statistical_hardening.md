# Pre-Registration — METH-001: Cross-Hypothesis Statistical Hardening (Deflated Sharpe Ratio + HAC-corrected inference)

*Drafted 2026-08-02, before any DSR/HAC value is computed against real
platform evidence. This is not a factor hypothesis (no new market signal is
being tested); it is a methodology/infrastructure change to the Quant
Engine's statistical-inference layer, triggered by a real, cited gap found
in `docs/INSTITUTIONAL_AUDIT_WAVE2_2026-08-02.md` Sections 1, 3, 5, 9, and
scheduled there as Phase R1 — the highest-priority item in that audit's own
roadmap. Per the new mandatory benchmarking requirement, this document
includes the required Frontier/Emerging/Developed Market Assessments and
Statistical Robustness review BEFORE implementation.*

## 1. Research gap (per the 15-step methodology)

`src/ngxrot/stats.py::excess_ttest` computes a plain i.i.d. two-sided
t-test on **daily** net excess returns, with the docstring's own honest
admission that this "understates fat-tail risk — treat as the OPTIMISTIC
bound," which is why the placebo (permutation) test is already the primary
criterion. Two concrete gaps remain even with that mitigation:

1. **No correction for return autocorrelation** within a hypothesis's own
   test — daily returns of a monthly/quarterly-rebalanced strategy are not
   independent observations; `n_obs` in the thousands overstates the
   effective sample size.
2. **No correction across hypotheses.** 11 hypotheses have now been run and
   resolved (H-001, H-003–H-012) against the same ~10-year NGX return
   history. Each was corrected internally (Holm/Benjamini-Hochberg across
   its own stability-grid cells), but nothing today adjusts H-011's
   headline confirmation for the fact that it is (by real ledger count) the
   11th independent idea tested against this data. Harvey, Liu & Zhu (2016,
   *Review of Financial Studies*, "…and the Cross-Section of Expected
   Returns") document this "factor zoo" problem directly and argue for a
   materially higher significance bar as the number of tested factors
   grows.

## 2. Literature review

- **Bailey, D.H. & López de Prado, M. (2014). "The Deflated Sharpe Ratio:
  Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."
  *Journal of Portfolio Management*, 40(5).** Provides a closed-form
  correction: given N independent trials, the expected maximum Sharpe ratio
  achievable purely by chance (under a true-zero-Sharpe null) is estimated
  via an extreme-value approximation using the cross-sectional variance of
  the trials' own Sharpe estimates; the focal trial's Sharpe is then tested
  against that chance-derived benchmark using the Probabilistic Sharpe
  Ratio (PSR) framework (Bailey & López de Prado, 2012, "The Sharpe Ratio
  Efficient Frontier"), which itself corrects for the focal return series'
  own skewness and kurtosis and finite sample size.
- **Newey, W.K. & West, K.D. (1987). "A Simple, Positive Semi-Definite,
  Heteroskedasticity and Autocorrelation Consistent Covariance Matrix."
  *Econometrica*, 55(3).** Standard HAC standard-error correction; applied
  here to the daily excess-return series with a Bartlett kernel and a
  pre-declared lag length (not tuned after seeing the result — see
  Section 4).
- **Harvey, C.R., Liu, Y. & Zhu, H. (2016).** Motivates *why* a
  cross-hypothesis correction matters at all, independent of any
  within-hypothesis fix — cited above as the research gap's own source.
- **Bailey, D.H., Borwein, J., López de Prado, M. & Zhu, Q.J. (2014). "The
  Probability of Backtest Overfitting." *Journal of Computational
  Finance*.** Reviewed for completeness. **Not implemented in this phase**
  — see Section 6 (explicitly deferred, not silently dropped).
- **White, H. (2000). "A Reality Check for Data Snooping." *Econometrica*,
  68(5)**, and **Hansen, P.R. (2005). "A Test for Superior Predictive
  Ability." *Journal of Business & Economic Statistics*.** Reviewed.
  **Not implemented in this phase** — both require a bootstrap over the
  full universe of *considered* strategies (including ones that were never
  formally pre-registered, e.g. discarded stability-grid cells across every
  hypothesis), which this platform's ledger does not currently track at
  that granularity. Implementing White/Hansen honestly would require first
  extending the registry schema to record every considered-but-discarded
  configuration, not just pre-registered hypotheses — a separate,
  larger infrastructure decision, named here as a real dependency rather
  than skipped silently.

## 3. Data availability audit

All required data already exists; no new data source, vendor, or owner
decision is needed.

- The registry (`data/registry.sqlite`) already records each hypothesis's
  canonical "final evaluation" experiment (stage=`walk_forward`,
  notes containing "final evaluation") with `config_json` fully preserved
  — sufficient to deterministically regenerate the daily net-return series
  for every resolved hypothesis (frozen data, frozen seed, frozen code
  fingerprint at time of the original run).
- The daily return series itself (`XSResult.net_returns` /
  `BacktestResult.net_returns`, depending on engine) is **not** persisted in
  the registry's summarized `metrics` JSON (only annualized derived
  statistics are) — obtaining skewness, kurtosis, and daily-frequency
  Sharpe requires regenerating it from the frozen config, read-only,
  without writing new registry rows (a frozen hypothesis, H-001, would
  reject any new experiment insertion under its ID by SQL trigger design —
  correctly so; this recomputation must not attempt to bypass that).
- Real trial count N: **11** — the number of hypotheses actually executed
  and resolved (H-001, H-003 through H-012). H-002 (registered, never
  executed — blocked on data) is excluded from N, since DSR's N counts
  trials that actually looked at performance data; a hypothesis that was
  never run contributes no selection-bias risk.

## 4. Method specification (pre-declared, before any real value is computed)

**HAC-corrected inference** (additive alongside, not replacing,
`excess_ttest`):
- Applied to the same daily net-excess-return series `excess_ttest` already
  uses.
- Newey-West standard error with lag length `L = floor(4 * (T/100)^(2/9))`
  (Newey & West's own automatic bandwidth rule, not hand-picked after
  seeing results) using a Bartlett kernel.
- Reported alongside, never replacing, the existing i.i.d. t-test — both
  numbers shown, consistent with the platform's existing practice of
  showing the parametric test next to the (primary) placebo test.

**Deflated Sharpe Ratio**, computed entirely at **daily** frequency (both
the focal hypothesis's own SR_hat/skew/kurtosis/T, and the cross-trial
variance V[{SR_n}] used to derive the chance benchmark, all at daily
frequency — units must match throughout the PSR formula, per Bailey &
López de Prado's own specification):
1. For each of the 11 resolved hypotheses, recompute the daily excess
   return series (`net_returns - benchmark_returns`) from its frozen final-
   evaluation config; compute daily SR_n = mean/std of that series.
2. V[{SR_n}] = the empirical (real, not assumed) variance of those 11
   daily Sharpe ratios.
3. SR* (expected max Sharpe under N=11 trials, true Sharpe = 0) =
   `sqrt(V[{SR_n}]) * ((1-γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/(N·e)))`,
   γ = Euler-Mascheroni constant ≈ 0.5772156649.
4. DSR = PSR(SR*) for the focal hypothesis, using its own daily SR_hat,
   skewness, kurtosis, and T (real observation count), via:
   `PSR(SR*) = Φ[ (SR_hat − SR*) · sqrt(T−1) / sqrt(1 − γ₃·SR_hat + ((γ₄−1)/4)·SR_hat²) ]`
   where γ₃ = sample skewness, γ₄ = sample kurtosis (regular, normal = 3).

**Pre-declared limitation, stated up front, not discovered after the
fact**: the extreme-value approximation underlying SR* assumes the N
trials are *independent*. These 11 hypotheses are not fully independent —
several share underlying signal ingredients (e.g. H-007/H-009/H-010 are all
momentum variants; H-008/H-012 share the volatility signal) and all draw
from the same NGX return history over overlapping windows. This makes
SR* a **conservative-leaning but imperfect** proxy — treated here as
informative, not as a rigorously exact correction. This limitation is
disclosed in every report that cites a DSR value from this point forward,
not buried in this pre-registration alone.

## 5. What will NOT be considered evidence of success or failure

This is infrastructure, not a hypothesis — there is no accept/reject
criterion for "the DSR" itself. Instead:
- **Implementation correctness** is validated against synthetic data with
  known analytical properties (Section "Validation plan" below), matching
  the platform's existing rehearsal-script convention (R1-R12).
- **Application to real evidence** (Section 7) reports whatever DSR value
  results for H-011 plainly — a lower post-correction confidence is exactly
  as valid an outcome as a confirming one, and does not retroactively
  change H-011's `confirmed` ledger status (that status reflects the
  platform's pre-existing per-hypothesis confirmation criteria, which have
  not changed; DSR is reported as an *additional*, more conservative lens,
  layered alongside the existing record, not a replacement for it).

## 6. Explicitly deferred (named, not silently dropped)

- **Probability of Backtest Overfitting (PBO)** — requires Combinatorial
  Purged Cross-Validation over multiple data partitions per hypothesis;
  the current stability grids (6 cells) are a plausible starting partition
  set but a correct CPCV implementation needs its own dedicated
  design/validation pass (its own METH-00X). Deferred, not implemented as
  an approximation, because a mislabeled or approximate "PBO" would itself
  violate the "no fabricated confidence" guardrail.
- **White's Reality Check / Hansen's SPA test** — requires tracking every
  *considered*, not just every *pre-registered*, configuration (including
  discarded grid cells across all hypotheses) via a registry-schema
  extension. Deferred pending that schema decision.

## 7. Validation plan

Synthetic checks (new `scripts/rehearse_stats_hardening.py`, mirroring the
existing R1-R12 convention):
- HAC standard error reduces to the ordinary i.i.d. standard error when the
  return series has zero true autocorrelation (verified against a
  synthetic i.i.d. normal series).
- HAC standard error is strictly larger than the i.i.d. estimate for a
  synthetic AR(1) series with known positive ρ (autocorrelation inflates
  the effective-sample-size correction as expected).
- DSR(SR_hat, N=1) reduces exactly to PSR(SR_hat, SR*=0) (the N=1 case has
  no multiple-testing correction to apply).
- DSR is monotonically non-increasing in N for fixed SR_hat/skew/kurt/T
  (more trials → higher chance-benchmark → harder to clear).
- DSR of a genuinely zero-mean synthetic series stays low (< 0.5) even
  across a range of N (a null check, analogous to the existing R6/R9/R11
  "null panel stays null" checks).

Only after every synthetic check passes does Section 8 apply the method to
real platform evidence.

## 8. Application (results reported honestly, whatever they show)

Applied to H-011 (the only confirmed factor) as the first real use of this
methodology, in a separate implementation log — this pre-registration is
frozen before that number is computed.
