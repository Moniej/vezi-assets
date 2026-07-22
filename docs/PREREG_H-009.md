# Pre-Registration — H-009: Turnover-Budgeted Cross-Sectional Momentum
(family: Momentum)

*Drafted 2026-07-22, BEFORE any H-009 experiment run. Executable form:
`configs/h009_xs_momentum_annual.toml`. This is a NEW hypothesis ID, not a
rerun of H-007 — H-007's signal, universe, and cost model are unchanged;
the ONLY change is rebalance cadence (the specific mechanism H-007's own
verdict identified as the point of failure: 1.83×/yr realized turnover
against a 2.2%/yr gross effect). Changes after first results = new
hypothesis ID.*

## Why this hypothesis exists (honest framing)

H-007 (12-1 momentum, quarterly rebalance) was REJECTED 2026-07-21:
placebo p=0.644, net excess −6.26%/yr against a gross excess of +2.18%/yr
— the entire loss was cost drag from 1.83×/yr one-way turnover, roughly
3× the pre-registered estimate. This is the single most direct,
cheaply-testable successor: hold the SAME signal and universe, cut
turnover by rebalancing less often. If a real, if modest, gross momentum
effect exists on NGX (H-007's dev-window gross excess was positive, even
though not statistically distinguishable from noise), a large-enough cost
reduction could flip the net sign. If it does NOT — if net excess remains
negative or the effect vanishes entirely at low turnover — that is
equally informative: it would indicate the gross effect itself decays
faster than a year (inconsistent with genuine 12-month momentum
persistence), closing off the entire quarterly-or-slower momentum
successor space in one test.

## Research question / hypotheses

Does 12-1 cross-sectional momentum, rebalanced at MOST annually, beat the
equal-weighted-IRU benchmark net of retail costs, out of sample?

- H0: net excess ≤ 0 at every tested rebalance cadence.
- H1: net excess > 0 at annual or semi-annual cadence, robust across grid
  and OOS.

## Universe / data (frozen) — identical to H-007

IRU v2, `equity_prices_asof`, min_confidence 0.9, **vintage 2026-07-21**,
`requires_coverage_gate = true`. Eligibility: ≥120 valid observations in
the formation window, IRU staleness rule.

## Signal specification — identical to H-007

Formation: cumulative return t−12 to t−1 months (skip-month, standard
12-1). Cross-sectionally standardized at each formation date. NOT
re-optimized — reusing H-007's exact signal isolates rebalance cadence as
the only new variable, consistent with "no discretionary changes after
seeing results" (the cadence choice is pre-registered here, before this
hypothesis's own results exist, even though H-007's results motivated it).

## Portfolio construction

- **Base configuration (PRIMARY): long top 25 names by formation score,
  equal-weighted, ANNUAL rebalance, execution lag 1 trading day.**
  (top_n widened from H-007's 20 to 25 — a larger basket further damps
  per-rebalance turnover, a second independent lever on the same cost
  problem, tested jointly with cadence in the grid below.)
- Long-only, fully invested, no leverage, no shorts.
- Liquidity: ADTV participation cap 10%, 60-day ADTV.
- Stability grid (6 cells): rebalance ∈ {semiannual, annual} × top_n ∈
  {20, 25, 30} — engine capability (semiannual/annual cadence) validated
  in `scripts/rehearse_xs_engine_v2.py` (R7) before this prereg was
  written.

## Benchmark (ex-ante) — identical to H-007

Equal-weighted IRU, quarterly rebalance, identical cost model.

## Costs / turnover / capacity

H-007 realized 1.83×/yr one-way turnover at quarterly cadence. The
synthetic rehearsal (R7) showed annual cadence cutting turnover by >30%
relative to quarterly on a matched signal (exact NGX magnitude will differ
and is what this hypothesis measures, not assumes). Expected drag:
proportionally lower than H-007's realized 6.7%/yr, but NOT assumed to
scale linearly with rebalance count — annual reconstitution trades bigger
per-event position changes, a real cost-structure difference this design
exists specifically to measure. Capacity: standard AUM grid; a wider
top_n (25 vs 20) should also mechanically raise capacity by spreading
into more, generally smaller, positions.

## Windows — identical to H-007

Development 2016-01-02 → 2024-12-31. **Untouched OOS: 2025-01-02 →
2026-06-30.** Same three regimes as H-007/H-008.

## Validation plan

Phase 4 unchanged: stability map (6 cells) → Holm/BH → seeded placebo (100
iterations, fixed persistent ticker relabeling — H-007's validated
design) → walk-forward → final OOS → IC memo.

## Confirmation requires ALL of

1. Placebo p ≤ 0.05 on the base configuration.
2. Base net excess vs EW-IRU > 0 in development AND final OOS.
3. Plateau: ≥ 4 of 6 grid cells with positive net excess.
4. ≥ 1 cell significant under Benjamini–Hochberg at FDR 0.10.
5. No regime contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered.

## Rejection (any one suffices)

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates gross
excess · regime concentration > 80% · signal-quality failure condition.
If net excess is positive but fails placebo/BH (the specific way H-007
failed), the verdict is REJECT and the program conclusion becomes: NO
turnover-reduction design rescues NGX cross-sectional momentum — closing
the family pending a materially different signal construction (not just a
slower cadence of the same one), which is itself decisive, useful
knowledge.

## Multiple-testing treatment

6 cells under BH within this hypothesis. Program-level ledger count (9
hypotheses through this wave) reported in the IC memo. H-008 and H-009
are this wave's only two active hypotheses.

## Expected Interaction with Existing Factors

- Family: **Momentum** — same family as H-007 (rejected). This is
  explicitly NOT a diversification play; it is a cost-engineering retest
  of the same economic mechanism. If validated, its correlation to any
  future momentum-family entry would be expected HIGH (same signal); its
  correlation to H-008 (Low Volatility, if validated) is expected LOW —
  the standard cyclical/defensive split.
- Diversification: if H-009 validates and H-008 also validates, the two
  together would give the library its first cyclical+defensive pair —
  the textbook starting point for a multi-factor combination, per the
  platform's stated goal that a factor's value includes what it adds to
  the library, not just standalone validity.
- Portfolio construction value if validated: a slow-turnover return
  driver — complements a low-turnover risk reducer (H-008) without
  compounding trading costs, since neither is designed to trade against
  the other. If H-009 fails, the honest conclusion feeds directly back
  into `docs/FACTOR_REGISTRY.md`'s Momentum-family entry, closing that
  line of research rather than leaving it open-ended.
- Independence rationale: trend information from past relative RETURNS
  only — same construction basis as H-007 by design (this hypothesis
  varies execution, not signal construction).

## Known limitations (pre-declared)

L1 price-only returns (no dividend reinvestment) — same as H-007;
conservative for winner-tilted longs. L2 177 single-source days
(documented in the freeze). L3 retail cost schedule 'assumed'. L4 rf = 0
placeholder. L5 annual/semiannual cadence means FEWER independent
decision points than H-007 (6-9 rebalances in dev window vs H-007's ~35),
which lowers statistical power for the same span — a real tradeoff
against the turnover benefit, reported honestly in the confidence rating
rather than treated as a free win.
