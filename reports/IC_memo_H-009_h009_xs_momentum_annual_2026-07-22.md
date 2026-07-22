# Investment Committee Memo — H-009

*Generated 2026-07-22 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: placebo_performs_similarly.

## Hypothesis tested

Turnover-budgeted 12-1 momentum: same signal as H-007, annual/semiannual rebalance (docs/PREREG_H-009.md)

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 11,833,438 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- cost_drag_eliminates_excess [signal_quality]: gross excess +6.10%, net excess +2.66%
- single_sector_dependency [signal_quality]: SUNUASSUR contributes 7% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 3.30 vs IS 2.35 (retention floor 25%)
- single_regime_dependency [signal_quality]: regime 'float_shock' contributes 73% of positive excess (limit 80%); per-regime excess: pre_float=+0.6%, float_shock=+27.8%, oos_2025_26=+9.4%

## Contradictory evidence

- placebo_performs_similarly [signal_quality]: placebo p=0.069 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- placebo: real strategy indistinguishable from shuffled labels (p=0.0693)
- NO parameter cell survives Holm correction across 6 tests (raw significant: 0)

## Parameter robustness

100% of 6
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +1.9%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess +0.6%, Sharpe 0.901, top contributor CILEASING (+0.17 cum. gross); median capacity NGN 9,596,667
- **float_shock**: excess +27.8%, Sharpe 3.796, top contributor SUNUASSUR (+0.21 cum. gross); median capacity NGN 15,675,824
- **oos_2025_26**: excess +9.4%, Sharpe 3.298, top contributor EUNISELL (+0.41 cum. gross); median capacity NGN 82,834,470

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 11,833,438
  (worst: NGN 8,348 on 2020-07-01)
- Bottlenecks: {'DANGSUGAR': 7, 'NPFMCRFBK': 6, 'NEM': 6, 'MBENEFIT': 6, 'NAHCO': 5}
- 96.0% of trade legs rejected at configured AUM
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
- sample: only 9 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.572 (+0)
- robustness: 100% of parameter space acceptable (+2)
- placebo: FAILED — indistinguishable from noise (+0)
