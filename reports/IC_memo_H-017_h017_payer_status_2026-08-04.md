# Investment Committee Memo — H-017

*Generated 2026-08-04 by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **Reject**

Signal-quality failure condition(s) triggered: cost_drag_eliminates_excess, placebo_performs_similarly, single_regime_dependency.

## Hypothesis tested

Dividend Payer-Status: within the IRU, do firms with a trailing-12m dividend-paying track record (payer status, binary, not yield magnitude) exhibit different risk-adjusted returns than non-payers, independent of Size and Liquidity?

## Supporting evidence

- capacity_below_minimum [scalability]: median capacity 460,752,340 NGN vs mandate 0; signal validity unaffected — deployable AUM is capped near the median capacity figure
- single_sector_dependency [signal_quality]: TRANSCORP contributes 5% of positive return (limit 100%)
- oos_performance_collapses [signal_quality]: OOS Sharpe 5.04 vs IS 2.67 (retention floor 25%)

## Contradictory evidence

- cost_drag_eliminates_excess [signal_quality]: gross excess +0.02%, net excess -3.58%
- placebo_performs_similarly [signal_quality]: placebo p=0.366 (alpha=0.05): real strategy NOT distinguishable from shuffled sector labels
- single_regime_dependency [signal_quality]: regime 'float_shock' contributes 100% of positive excess (limit 80%); per-regime excess: pre_float=-3.4%, float_shock=+7.0%, oos_2025_26=-12.2%
- placebo: real strategy indistinguishable from shuffled labels (p=0.3663)
- NO parameter cell survives Holm correction across 4 tests (raw significant: 0)

## Parameter robustness

0% of 4
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: +0.6%
(a small gap means a plateau, not a lucky spike).

## Regime attribution

- **pre_float**: excess -3.4%, Sharpe 0.86, top contributor CUTIX (+0.09 cum. gross); median capacity NGN 249,777,604
- **float_shock**: excess +7.0%, Sharpe 4.489, top contributor TRANSCORP (+0.07 cum. gross); median capacity NGN 1,357,320,014
- **oos_2025_26**: excess -12.2%, Sharpe 5.045, top contributor BETAGLAS (+0.05 cum. gross); median capacity NGN 8,999,886,863

## Data limitations

- minimum data confidence used: 0.9
- price-only per-stock returns (no dividend reinvestment) — conservative for winner-tilted longs; total-return retest possible after the DOL dividend layer lands
- 177 single-source recovered days (close-only) in the panel — documented in docs/DATA_FREEZE_2026-07-21.md
- risk-free rate placeholder 0% — NGN T-bill yields would materially lower every Sharpe shown
- diagnostics at run time: errors=['unexplained_jump'], warnings=['duplicate_observation', 'extreme_index_return', 'liquidity_anomaly', 'missing_data', 'stale_price']

## Capacity limitations

- Median per-rebalance capacity: NGN 460,752,340
  (worst: NGN 7,434 on 2019-01-02)
- Bottlenecks: {'REDSTAREX': 24, 'MAYBAKER': 23, 'BERGER': 22, 'CONOIL': 22, 'NEM': 22}
- 59.5% of trade legs rejected at configured AUM
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
- sample: only 27 decisions (+0)
- regimes: 3 covered (+2)
- significance: corrected p=0.450 (+0)
- robustness: narrow/unknown plateau (+0)
- placebo: FAILED — indistinguishable from noise (+0)
