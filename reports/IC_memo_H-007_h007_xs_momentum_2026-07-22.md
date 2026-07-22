# Investment Committee Memo — H-007

*Generated 2026-07-22 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: cost_drag_eliminates_excess, placebo_performs_similarly.

## Hypothesis tested

Cross-sectional 12-1 momentum, long-only top-20 within IRU v2 vs the
equal-weighted-IRU investable benchmark, quarterly rebalance, net of retail
costs, out of sample (docs/PREREG_H-007.md).

*(Correction 2026-07-22: the memo generator had hardcoded H-001's sector
description here since H-003; fixed in ic_report.py. All quantitative
content traces to registry records and was unaffected.)*

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 7,098,686 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- single_sector_dependency [signal_quality]: CILEASING contributes 10% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 2.76 vs IS 1.47 (retention floor 25%)

## Contradictory evidence

- cost_drag_eliminates_excess [signal_quality]: gross excess +2.18%, net excess -6.26%
- placebo_performs_similarly [signal_quality]: placebo p=0.644 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- placebo: real strategy indistinguishable from shuffled labels (p=0.6436)
- NO parameter cell survives Holm correction across 6 tests (raw significant: 0)

## Parameter robustness

17% of 6
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +7.4%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess -4.9%, Sharpe 0.567, top contributor CILEASING (+0.29 cum. gross); median capacity NGN 5,436,948
- **float_shock**: excess -14.7%, Sharpe 2.37, top contributor CWG (+0.15 cum. gross); median capacity NGN 17,784,215
- **oos_2025_26**: excess -30.3%, Sharpe 2.758, top contributor EUNISELL (+0.13 cum. gross); median capacity NGN 108,375,763

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 7,098,686
  (worst: NGN 9,904 on 2022-10-04)
- Bottlenecks: {'CUTIX': 12, 'OKOMUOIL': 12, 'ETERNA': 11, 'SEPLAT': 11, 'FCMB': 10}
- 97.5% of trade legs rejected at configured AUM
  of NGN 1,000,000,000
- Capacity limits SCALE, not signal validity — kept separate from the
  signal-quality verdict above.

## Implementation risks

- single-session execution assumed at each rebalance leg
- brokerage (retail schedule, 'assumed' confidence) dominates cost drag and is negotiable — economics swing with the rate
- capacity distribution is ADTV-based; participation cap is reported, not enforced inside the simulation
- benchmark is the EW-IRU investable null computed by the same engine under the same costs (not an index)

## Confidence rating: **Low** (score 4/12)

- data: exchange-official grade (+2)
- sample: only 35 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.453 (+0)
- robustness: narrow/unknown plateau (+0)
- placebo: FAILED — indistinguishable from noise (+0)
