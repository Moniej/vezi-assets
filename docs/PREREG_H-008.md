# Pre-Registration — H-008: Low-Volatility (family: Low Volatility)

*Drafted 2026-07-22, BEFORE any H-008 experiment run. Executable form:
`configs/h008_low_vol.toml`. First entry in a NEW factor family — the
library is currently empty (0 validated / 6 rejected, all Momentum/Event/
Macro). Changes after first results = new hypothesis ID.*

## Economic rationale and market intuition

The low-volatility anomaly (low-vol/low-beta names earn risk-adjusted
returns that exceed what CAPM predicts) is best explained by
leverage-constrained and benchmark-relative investors who cannot lever up
safe assets, so they instead bid up high-vol/high-beta names in search of
return — overpricing risk and underpricing safety. NGX is close to a
textbook fit for this mechanism: retail dominates the tape (no
institutional leverage arbitraging the anomaly away), there is NO
shorting (nothing corrects the high-vol overpricing side, but nothing
stops us capturing the long-side underpricing either), and — distinct
from H-006/H-007 — this factor is naturally LOW TURNOVER: volatility
ranks are far stickier period-to-period than momentum or event ranks,
which directly targets the exact failure mode (cost drag) that killed
both prior hypotheses.

## Research question / hypotheses

Does a long-only tilt toward the lowest-trailing-volatility quintile
within the investable universe beat the equal-weighted-IRU investable
benchmark, net of retail costs, out of sample?

- H0: net excess return of the low-vol portfolio vs EW-IRU is ≤ 0.
- H1: net excess > 0, robust across the pre-declared grid and OOS.

## Universe / data (frozen)

- IRU v2 members at each formation date (PIT, monthly recompute,
  rename-canonical). `iru_version = "v2"`.
- Data: `equity_prices_asof`, `min_confidence = 0.9`,
  **vintage = 2026-07-21** (`docs/DATA_FREEZE_2026-07-21.md`),
  `requires_coverage_gate = true`.
- Eligibility at formation: ≥120 valid (actually-traded, not
  forward-filled) close observations in the volatility lookback window —
  identical discipline to H-007, plus one addition specific to this
  factor: **volatility is computed on actually-traded sessions only**
  (the ffilled panel used for NAV accounting would inject artificial
  zero-return days for stale names and mechanically understate their
  vol — engineering detail fixed in `backtest_xs.vol_scores` BEFORE any
  real run, verified in the synthetic rehearsal).

## Signal specification

- Trailing realized volatility: annualized std of daily returns
  (actually-traded sessions only) over a 12-month lookback (base case).
- Score = negative standardized volatility (so lower vol = higher score);
  standardized cross-sectionally at each formation date.

## Portfolio construction

- **Base configuration (PRIMARY): long the bottom-volatility quintile
  (lowest 20% by trailing vol) within the IRU, equal-weighted, quarterly
  rebalance, execution lag 1 trading day.**
- Long-only, fully invested, no leverage, no shorts.
- Liquidity: ADTV participation cap 10%, 60-day ADTV (platform default).
- Stability grid (6 cells): vol lookback ∈ {6, 12} months × selection
  width ∈ {top 15, top 20, top 30 by count} — a genuinely different axis
  from H-007's grid (holding-width and estimation-window robustness for a
  risk-based sort, not a momentum-formation sweep).

## Benchmark (ex-ante)

Equal-weighted IRU portfolio, quarterly rebalance, identical cost model —
same definition used for H-006/H-007, so results are directly comparable
across the program.

## Costs / turnover / capacity — the central claim of this hypothesis

Expected one-way turnover is meant to be materially lower than H-007's:
volatility ranks change slowly (a name doesn't flip from calm to volatile
overnight absent a regime shock), so quarterly reconstitution should
replace a small minority of holdings per rebalance. **Honesty check run
2026-07-22 (base-config smoke test, single dev-window pass, NOT the
validated verdict)**: realized turnover at quarterly cadence was
1.29×/yr — lower than H-007's 1.83×/yr, but not the large gap the
"volatility ranks are sticky" argument implied; gross excess in that same
smoke pass was negative (a defensive tilt underperforming during a bull
window is expected behavior, not necessarily a bad sign, but noted
without spin). This does NOT change the pre-registered design or grid —
it is disclosed here, before the real run, exactly so the eventual
verdict cannot be read as if the cost argument were confirmed in advance.
If the turnover advantage is smaller than expected, the grid's wider
top_n cells (25, 30) may show a cleaner effect (larger baskets swap fewer
names per rebalance) — that comparison is exactly what the stability map
is for. Capacity: reported at the standard AUM grid; low-vol tilts often
concentrate in large, liquid, defensive names (banks, consumer staples)
which should help capacity relative to H-007's mid-liquidity momentum
winners — a testable, not assumed, comparison.

## Windows

Development: 2016-01-02 → 2024-12-31. **Untouched OOS: 2025-01-02 →
2026-06-30** (runner-enforced). Walk-forward regimes: pre_float
(2016→2023-05), float_shock (2023-06→2024-12), OOS (2025-01→2026-06) —
identical regime definitions to H-006/H-007 for cross-hypothesis
comparability.

## Validation plan

Phase 4 unchanged: stability map (6 cells) → Holm/BH → seeded placebo (100
iterations; fixed persistent ticker relabeling per iteration — the same
persistence-preserving design validated for xs_rank, reused unchanged for
xs_vol since both produce a {formation_date: score} structure) →
walk-forward → final OOS → IC memo.

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

## Multiple-testing treatment

6 cells under BH within this hypothesis. Program-level ledger count (8
hypotheses tested through this wave) reported in the IC memo per program
rule. H-008 and H-009 are this wave's only two active hypotheses.

## Expected Interaction with Existing Factors

- Family: **Low Volatility** — first entry in this family; no validated
  factors exist yet in the library (0/6).
- Expected correlation with Momentum (H-007, rejected) and PEAD (H-006,
  rejected): LOW or NEGATIVE. This is the textbook diversifying pair —
  low-vol is a defensive, mean-reverting-adjacent tilt; momentum/event
  factors are cyclical/information-driven. Even though neither prior
  factor validated, the correlation structure itself is measurable
  against their SCORES (not just their rejected P&L) and will be reported
  for program record.
- Diversification: if validated, this would be the library's first
  DEFENSIVE-character entry, complementing any future cyclical factor
  rather than duplicating one.
- Portfolio construction value if validated: low-vol factors are
  typically combined as a RISK REDUCER / ballast sleeve rather than a
  standalone return driver — worth stating explicitly since its expected
  alpha may be modest even if statistically genuine; the construction
  value is as much about the covariance structure as the mean return.
- Independence rationale: input is trailing REALIZED VOLATILITY, a
  second-moment (risk) measure, structurally orthogonal to trailing
  RETURN (momentum), price-level ratios (value, not yet available), and
  discrete-event reactions (PEAD) — no shared construction inputs with
  any hypothesis tested so far.

## Known limitations (pre-declared)

L1 price-only returns (dividend-adjusted vol would differ slightly,
second-order effect — flagged, not expected to be material). L2 177
single-source close-only days in the panel (documented in the freeze).
L3 retail cost schedule 'assumed' confidence. L4 rf = 0 placeholder
affects Sharpe labels, not excess-return verdicts. L5 no float-adjusted
size control — a low-vol tilt could partially proxy for size/liquidity
until the market-cap panel (`data/reference/market_cap_panel.csv`,
validated 2026-07-22) is used to build an explicit orthogonality check in
a later wave.
