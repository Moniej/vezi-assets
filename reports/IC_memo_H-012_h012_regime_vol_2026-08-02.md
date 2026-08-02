# Investment Committee Memo — H-012

*Generated 2026-08-02 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: placebo_performs_similarly.

## Hypothesis tested

Regime-Conditional Low-Volatility Gate: long the lowest-volatility 20 IRU names, quarterly rebalance, ONLY on formation dates classified STABLE by a pre-declared macro-event rule (no critical macro/banking/commodity event, and at most one high-severity MPC event, in the trailing 6 months); EW-IRU benchmark weights held on UNSTABLE dates. Reuses H-008 vol_scores() unmodified.

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 145,590,256 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- cost_drag_eliminates_excess [signal_quality]: gross excess -6.35%, net excess -12.89%
- single_sector_dependency [signal_quality]: PRESCO contributes 4% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 5.02 vs IS 2.27 (retention floor 25%)
- 4/6 parameter cells significant after Holm correction

## Contradictory evidence

- placebo_performs_similarly [signal_quality]: placebo p=0.970 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- placebo: real strategy indistinguishable from shuffled labels (p=0.9703)

## Parameter robustness

0% of 6
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +2.4%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess -13.9%, Sharpe 0.047, top contributor PRESCO (+0.07 cum. gross); median capacity NGN 36,320,458
- **float_shock**: excess -0.1%, Sharpe 4.488, top contributor OANDO (+0.05 cum. gross); median capacity NGN 783,258,910
- **oos_2025_26**: excess -28.9%, Sharpe 5.023, top contributor BUACEMENT (+0.08 cum. gross); median capacity NGN 382,454,975

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 145,590,256
  (worst: NGN 4,914 on 2019-04-01)
- Bottlenecks: {'REDSTAREX': 16, 'LEARNAFRCA': 14, 'ACADEMY': 13, 'BETAGLAS': 13, 'MBENEFIT': 13}
- 67.5% of trade legs rejected at configured AUM
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
- sample: only 35 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.002 (+2)
- robustness: narrow/unknown plateau (+0)
- placebo: FAILED — indistinguishable from noise (+0)
