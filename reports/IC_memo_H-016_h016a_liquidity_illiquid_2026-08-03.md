# Investment Committee Memo — H-016

*Generated 2026-08-03 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: cost_drag_eliminates_excess, placebo_performs_similarly.

## Hypothesis tested

Liquidity: does a whole-universe cross-sectional sort on trailing 60-day ADTV carry a return premium, in either direction, independent of Size?

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 712,992 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- single_sector_dependency [signal_quality]: RTBRISCOE contributes 11% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 4.46 vs IS 2.04 (retention floor 25%)
- single_regime_dependency [signal_quality]: regime 'oos_2025_26' contributes 63% of positive excess (limit 80%); per-regime excess: pre_float=-5.8%, float_shock=+16.7%, oos_2025_26=+28.2%

## Contradictory evidence

- cost_drag_eliminates_excess [signal_quality]: gross excess +5.42%, net excess -3.13%
- placebo_performs_similarly [signal_quality]: placebo p=0.168 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- placebo: real strategy indistinguishable from shuffled labels (p=0.1683)
- NO parameter cell survives Holm correction across 6 tests (raw significant: 0)

## Parameter robustness

50% of 6
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +3.2%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess -5.8%, Sharpe 0.656, top contributor MAYBAKER (+0.13 cum. gross); median capacity NGN 559,521
- **float_shock**: excess +16.7%, Sharpe 3.422, top contributor MULTIVERSE (+0.21 cum. gross); median capacity NGN 2,120,999
- **oos_2025_26**: excess +28.2%, Sharpe 4.463, top contributor MECURE (+0.12 cum. gross); median capacity NGN 17,396,792

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 712,992
  (worst: NGN 4,914 on 2019-04-01)
- Bottlenecks: {'REGALINS': 16, 'LEARNAFRCA': 14, 'BERGER': 14, 'TRANSCOHOT': 14, 'MCNICHOLS': 13}
- 100.0% of trade legs rejected at configured AUM
  of NGN 1,000,000,000
- Capacity limits SCALE, not signal validity — kept separate from the
  signal-quality verdict above.

## Implementation risks

- single-session execution assumed at each rebalance leg
- brokerage (retail schedule, 'assumed' confidence) dominates cost drag and is negotiable — economics swing with the rate
- capacity distribution is ADTV-based; participation cap is reported, not enforced inside the simulation
- benchmark is the EW-IRU investable null computed by the same engine under the same costs (not an index)

## Confidence rating: **Moderate** (score 5/12)

- data: exchange-official grade (+2)
- sample: only 35 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.971 (+0)
- robustness: 50% plateau (+1)
- placebo: FAILED — indistinguishable from noise (+0)
