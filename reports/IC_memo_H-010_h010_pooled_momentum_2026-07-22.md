# Investment Committee Memo — H-010

*Generated 2026-07-22 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: placebo_performs_similarly, single_regime_dependency.

## Hypothesis tested

Pooled overlapping-cohort 12-1 momentum (4 staggered annual cohorts), long-only top-N vs EW-IRU (docs/PREREG_H-010.md)

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 9,583,019 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- cost_drag_eliminates_excess [signal_quality]: gross excess +5.69%, net excess +2.26%
- oos_performance_collapses [signal_quality]: OOS Sharpe 3.47 vs IS 2.20 (retention floor 25%)

## Contradictory evidence

- placebo_performs_similarly [signal_quality]: placebo p=0.386 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- single_regime_dependency [signal_quality]: regime 'pre_float' contributes 100% of positive excess (limit 80%); per-regime excess: pre_float=+1.5%, float_shock=-10.0%, oos_2025_26=-6.6%
- placebo: real strategy indistinguishable from shuffled labels (p=0.3861)
- NO parameter cell survives Holm correction across 6 tests (raw significant: 0)

## Parameter robustness

100% of 6
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +0.1%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess +1.5%, Sharpe 1.044, top contributor n/a (+0.00 cum. gross); median capacity NGN 8,087,910
- **float_shock**: excess -10.0%, Sharpe 3.346, top contributor n/a (+0.00 cum. gross); median capacity NGN 24,475,468
- **oos_2025_26**: excess -6.6%, Sharpe 3.466, top contributor n/a (+0.00 cum. gross); median capacity NGN 148,154,114

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 9,583,019
  (worst: NGN 8,348 on n/a)
- Bottlenecks: {}
- 88.12499999999999% of trade legs rejected at configured AUM
  of NGN 1,000,000,000
- Capacity limits SCALE, not signal validity — kept separate from the
  signal-quality verdict above.

## Implementation risks

- single-session execution assumed at each rebalance leg
- brokerage (retail schedule, 'assumed' confidence) dominates cost drag and is negotiable — economics swing with the rate
- capacity distribution is ADTV-based; participation cap is reported, not enforced inside the simulation
- benchmark is the EW-IRU investable null computed by the same engine under the same costs (not an index)

## Confidence rating: **Moderate** (score 6/12)

- data: exchange-official grade (+2)
- sample: only 0 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.853 (+0)
- robustness: 100% of parameter space acceptable (+2)
- placebo: FAILED — indistinguishable from noise (+0)
