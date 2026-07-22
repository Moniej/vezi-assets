# Pre-Registration — H-010: Pooled Overlapping-Cohort Momentum
(family: Momentum)

*Drafted 2026-07-22, BEFORE any H-010 experiment run. Executable form:
`configs/h010_pooled_momentum.toml`. This is a NEW hypothesis ID, not a
rerun of H-007 or H-009 — the signal construction is unchanged from both;
the change is EXECUTION (N staggered formation cohorts instead of one).
Changes after first results = new hypothesis ID.*

## Why this hypothesis exists (honest framing, not a hopeful retry)

H-007 (12-1 momentum, quarterly, single cohort) was REJECTED: gross
excess +2.18%/yr, net −6.26%/yr — turnover (1.83×/yr) ate the entire
effect. H-009 (same signal, annual, single cohort) was REJECTED but
diagnosed precisely: net excess flipped POSITIVE (+2.66%/yr), 6/6 grid
cells positive, positive in every regime including OOS — but placebo
p=0.069, a near-miss, with only ~9 independent decisions in the 9-year
dev window. The turnover fix WORKED; the sample was too small to prove
it. H-010 changes exactly that one variable: N=4 staggered annual
cohorts, entered 3 months apart, each running the IDENTICAL single-cohort
signal H-007/H-009 already used. This was rehearsed on synthetic data
before this prereg was written
(`scripts/rehearse_xs_pooled.py`, 3/3 pass) — including a direct
measurement (not an assumption) that offset cohorts decorrelate
meaningfully (~0.57 mean pairwise return correlation on a planted-
momentum synthetic panel).

## Research question / hypotheses

Does pooling 4 staggered annual 12-1 momentum cohorts beat the
equal-weighted-IRU benchmark net of retail costs, out of sample, with
enough statistical power to distinguish the result from chance?

- H0: net excess of the pooled portfolio vs EW-IRU is ≤ 0, OR
  indistinguishable from a persistence-preserving relabeling (placebo).
- H1: net excess > 0, placebo p ≤ 0.05, robust across grid and OOS.

## Universe / data (frozen) — identical to H-007/H-009

IRU v2 members at each formation date (PIT, rename-canonical).
`iru_version = "v2"`. Data: `equity_prices_asof`, `min_confidence = 0.9`,
**vintage = 2026-07-21**, `requires_coverage_gate = true`.

## Signal specification — identical to H-007/H-009 per cohort

Formation: cumulative return t−12 to t−1 months (12-1, skip-month),
cross-sectionally standardized at each formation date. NOT re-optimized
— reusing the exact prior signal isolates cohort-pooling as the only new
variable.

## Cohort construction (the new mechanism, stated precisely)

- **Base configuration (PRIMARY): 4 cohorts, each on its own ANNUAL
  formation calendar, offset 3 months from the next (`n_cohorts=4`,
  `signal.method = "xs_rank_pooled"` — implemented in
  `src/ngxrot/backtest_xs.py`).** Each cohort is an independent,
  equally-sized (1/4 of NAV) sub-portfolio running the UNCHANGED
  single-cohort momentum path (top 25 names, equal-weighted). The
  aggregate portfolio's return is the equal-weighted blend of the 4
  cohorts' own return series.
- Design decision (not the only option, stated so it can't be
  second-guessed after seeing results): blending happens at the RETURN
  level, not via a single unified target-weight vector with partial
  per-date rebalancing — the latter would require tracking live drifted
  state across arbitrary cross-cohort dates, a correctness trap. The
  chosen design reuses `simulate()` completely unchanged per cohort.
- Aggregate turnover is NOT n_cohorts times a single cohort's turnover —
  each cohort trades only its own 1/4 NAV slice, so the NAV-fraction
  turnover contributed by any one cohort's rebalance is already scaled by
  1/4. Expected aggregate turnover is comparable to H-009's single-cohort
  figure (~0.6-0.7×/yr), NOT 4× it. This is stated as a prediction to be
  checked against the real run, not asserted as fact — H-008 already
  taught this platform not to assert turnover-stickiness claims without
  measuring them.

## Portfolio construction

Long-only, fully invested, no leverage, no shorts. Liquidity: ADTV
participation cap 10%, 60-day ADTV (platform default).
Stability grid (6 cells): `n_cohorts` ∈ {2, 4} × `top_n` ∈ {20, 25, 30},
rebalance fixed "annual" for every cell (both cohort counts evenly divide
the 12-month step: n=2 → 6-month offset, n=4 → 3-month offset).

## Benchmark (ex-ante) — identical to H-007/H-009

Equal-weighted IRU portfolio, quarterly rebalance, identical cost model.

## Costs / turnover / capacity

Same retail cost schedule as every prior hypothesis (single model, not
swept). Expected turnover per the Cohort Construction section above —
measured, not assumed, against the real run. Capacity: reported at the
standard AUM grid, computed PER COHORT at its own 1/4-NAV allocation
(unifying capacity across cohorts into one target vector would corrupt
the delta-based capacity calculation the same way a unified rebalance
vector would corrupt turnover accounting — see
`backtest_xs.pooled_rank_run`'s docstring) and aggregated as median-of-
medians / worst-of-worsts, reported per-cohort in full for transparency.

## Windows — identical to H-007/H-009

Development 2016-01-02 → 2024-12-31. **Untouched OOS: 2025-01-02 →
2026-06-30.** Same three regimes (pre_float / float_shock / oos_2025_26).

## Validation plan

Phase 4 unchanged: stability map (6 cells) → Holm/BH → seeded placebo
(100 iterations; **ONE fixed ticker relabeling applied to EVERY cohort
simultaneously per iteration** — tests aggregate pooled selection skill
under the null; a per-cohort-independent relabeling would test a
different, wrong question — see `backtest_xs._placebo_pooled`) →
walk-forward → final OOS → IC memo.

## Confirmation requires ALL of

1. Placebo p ≤ 0.05 on the base configuration.
2. Base net excess vs EW-IRU > 0 in development AND final OOS.
3. Plateau: ≥ 4 of 6 grid cells with positive net excess.
4. ≥ 1 cell significant under Benjamini–Hochberg at FDR 0.10.
5. No regime contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered.

## Rejection (any one suffices) — with pre-declared diagnosis paths

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates gross
excess · regime concentration > 80% · signal-quality failure condition.
**Pre-declared diagnosis, so the verdict cannot be spun after the fact:**
if net excess is positive and the plateau/regime checks pass but placebo
STILL fails, the correct reading is "cohorts are too correlated to add
real independent information beyond H-009's single cohort" — NOT
"the effect doesn't exist." If net excess itself is flat or negative
despite more decisions, the correct reading is "H-009's near-miss was
itself noise, not a real effect obscured by low power" — closing the
low-turnover-momentum successor space entirely, not just this design.

## Multiple-testing treatment

6 cells under BH within this hypothesis. Program-level ledger count (10
hypotheses through this wave) reported in the IC memo. H-010 and H-011
are this wave's only two active hypotheses.

## Expected Interaction with Existing Factors

- Family: **Momentum** — same family and same underlying signal as
  H-007/H-009 (both rejected). This is explicitly a cost/power
  engineering retest of the same mechanism, not a diversification play.
- If validated, expected HIGH correlation with any future Momentum-family
  entry (same signal); expected LOW correlation with H-011 (Size, a
  risk-based/structural sort with a disjoint construction input) and with
  any future Low-Volatility retry.
- Diversification: if BOTH H-010 and H-011 validate, the library's first
  two entries would be a cyclical return driver (momentum) and a
  structural/capacity-premium candidate (size) — a reasonable starting
  pair, to be confirmed by MEASURED correlation, not assumed from this
  paragraph.
- Portfolio construction value if validated: a slow-turnover core return
  driver; complements a low-turnover risk factor without compounding
  trading costs against it.
- Independence rationale: trend information from past relative RETURNS
  only, identical construction basis to H-007/H-009 by design.

## Known limitations (pre-declared)

L1 price-only returns (no dividend reinvestment) — conservative for
winner-tilted longs. L2 177 single-source close-only days in the panel
(documented in the freeze). L3 retail cost schedule 'assumed'
confidence. L4 rf = 0 placeholder. L5 cohort correlation is a property
of the REAL NGX data, not guaranteed to match the ~0.57 figure measured
on the synthetic rehearsal panel — will be measured and reported
explicitly in the IC memo, not inferred from the rehearsal. L6 fewer
independent decision points than H-007 despite the pooling (still
annual-cadence per cohort) — this hypothesis tests whether pooling closes
enough of that gap, not whether it closes all of it.
