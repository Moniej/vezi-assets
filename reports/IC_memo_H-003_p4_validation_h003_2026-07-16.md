# Investment Committee Memo — H-003

*Generated 2026-07-16 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: cost_drag_eliminates_excess, placebo_performs_similarly.

## Hypothesis tested

Cross-sectional 3–6 month momentum across NGX sector indices, long-only
top-N rotation, outperforms the NGX All-Share Index after realistic
transaction costs and liquidity constraints, out of sample.

## Supporting evidence

- capacity_below_minimum [scalability]: no capacity records
- single_sector_dependency [signal_quality]: NGXOILGAS contributes 49% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 5.75 vs IS 0.91 (retention floor 25%)

## Contradictory evidence

- cost_drag_eliminates_excess [signal_quality]: gross excess +2.83%, net excess -2.29%
- placebo_performs_similarly [signal_quality]: placebo p=0.198 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- placebo: real strategy indistinguishable from shuffled labels (p=0.198)
- NO parameter cell survives Holm correction across 3 tests (raw significant: 0)

## Parameter robustness

33% of 3
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +5.5%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre2023**: excess -3.7%, Sharpe 0.23, top contributor NGXOILGAS (+0.38 cum. gross); median capacity NGN 0
- **shock_2023_24**: excess -12.2%, Sharpe 1.588, top contributor NGXOILGAS (+0.34 cum. gross); median capacity NGN 0
- **bull_2025_26**: excess -2.5%, Sharpe 5.75, top contributor NGXASI (+0.80 cum. gross); median capacity NGN 0

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

## Confidence rating: **Low** (score 3/12)

- data: aggregator/manual grade (+1)
- sample: only 34 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.943 (+0)
- robustness: narrow/unknown plateau (+0)
- placebo: FAILED — indistinguishable from noise (+0)
