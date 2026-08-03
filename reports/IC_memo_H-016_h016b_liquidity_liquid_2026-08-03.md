# Investment Committee Memo — H-016

*Generated 2026-08-03 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: placebo_performs_similarly.

## Hypothesis tested

Liquidity: does a whole-universe cross-sectional sort on trailing 60-day ADTV carry a return premium, in either direction, independent of Size?

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 56,943,998 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- cost_drag_eliminates_excess [signal_quality]: gross excess -5.36%, net excess -10.29%
- single_sector_dependency [signal_quality]: TRANSCORP contributes 12% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 2.99 vs IS 1.43 (retention floor 25%)

## Contradictory evidence

- placebo_performs_similarly [signal_quality]: placebo p=1.000 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- placebo: real strategy indistinguishable from shuffled labels (p=1.0)
- NO parameter cell survives Holm correction across 6 tests (raw significant: 4)

## Parameter robustness

0% of 6
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +3.1%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess -8.5%, Sharpe 0.351, top contributor FIRSTHOLDCO (+0.11 cum. gross); median capacity NGN 48,277,192
- **float_shock**: excess -6.7%, Sharpe 2.5, top contributor OANDO (+0.21 cum. gross); median capacity NGN 208,216,080
- **oos_2025_26**: excess -34.5%, Sharpe 2.992, top contributor WAPCO (+0.08 cum. gross); median capacity NGN 522,000,579

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 56,943,998
  (worst: NGN 118,764 on 2023-10-03)
- Bottlenecks: {'UACN': 16, 'GUINNESS': 15, 'FCMB': 15, 'FIDELITYBK': 15, 'ETI': 14}
- 98.7% of trade legs rejected at configured AUM
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
- significance: corrected p=0.078 (+1)
- robustness: narrow/unknown plateau (+0)
- placebo: FAILED — indistinguishable from noise (+0)
