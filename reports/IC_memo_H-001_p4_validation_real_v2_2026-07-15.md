# Investment Committee Memo — H-001

*Generated 2026-07-15 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: cost_drag_eliminates_excess, placebo_performs_similarly, single_regime_dependency.

## Hypothesis tested

Cross-sectional 3–6 month momentum across NGX sector indices, long-only
top-N rotation, outperforms the NGX All-Share Index after realistic
transaction costs and liquidity constraints, out of sample.

## Supporting evidence

- capacity_below_minimum [scalability]: no capacity records
- single_sector_dependency [signal_quality]: NGXBNK contributes 39% of positive return (limit 80%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 2.42 vs IS 1.51 (retention floor 25%)

## Contradictory evidence

- cost_drag_eliminates_excess [signal_quality]: gross excess +7.45%, net excess -3.43%
- placebo_performs_similarly [signal_quality]: placebo p=0.554 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- single_regime_dependency [signal_quality]: regime 'shock_2023_24' contributes 100% of positive excess (limit 80%); per-regime excess: pre2023=-27.5%, shock_2023_24=+18.8%, bull_2025_26=-15.4%
- placebo: real strategy indistinguishable from shuffled labels (p=0.5545)
- NO parameter cell survives Holm correction across 20 tests (raw significant: 0)

## Parameter robustness

40% of 20
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +15.6%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre2023**: excess -27.5%, Sharpe 0.333, top contributor NGXBNK (+0.20 cum. gross); median capacity NGN 0
- **shock_2023_24**: excess +18.8%, Sharpe 2.696, top contributor NGXOILGAS (+0.53 cum. gross); median capacity NGN 0
- **bull_2025_26**: excess -15.4%, Sharpe 2.419, top contributor NGXINDUSTR (+0.43 cum. gross); median capacity NGN 0

## Data limitations

- minimum data confidence used: 0.5
- within-sector weights are a trailing-ADTV proxy, not float-adjusted index weights (flatters capacity)
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=[], warnings=[]

## Capacity limitations

- Median per-rebalance capacity: NGN 0
  (worst: NGN 0 on n/a)
- Bottlenecks: {}
- 0% of trade legs rejected at configured AUM
  of NGN 0
- Capacity limits SCALE, not signal validity — kept separate from the
  signal-quality verdict above.

## Implementation risks

- single-session execution assumed: real multi-day execution raises capacity roughly linearly with horizon but adds timing risk
- slippage (30bps) and sqrt-impact coefficient (15bps) are assumed, not estimated from NGX fill data
- brokerage is the dominant cost line (~60% of drag) and is negotiable — economics swing materially with the negotiated rate
- thin sectors (insurance) are persistent capacity bottlenecks; index membership churn risk not yet stress-tested

## Confidence rating: **Low** (score 4/12)

- data: aggregator/manual grade (+1)
- sample: only 16 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.978 (+0)
- robustness: 40% plateau (+1)
- placebo: FAILED — indistinguishable from noise (+0)
