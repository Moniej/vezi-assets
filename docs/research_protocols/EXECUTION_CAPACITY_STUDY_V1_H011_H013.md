# Execution & Capacity Study v1 — H-011 / H-013

## Status

This is a read-only implementation study, not an Alpha hypothesis or recommendation.
It replays the frozen H-011 Size and H-013 high-liquidity Size target portfolios.
H-011, H-013, H-016, H-022, H-024, identity, evidence, and all production database
state remain unchanged. Results are always **MODEL-BASED HISTORICAL EXECUTION
REPLAY**, never actual historical execution, empirically realised execution, or
live realised performance.

## Frozen scenarios and mechanics

The capital grid is NGN 10m, 50m, 100m, 250m, 500m, and 1bn. Headline scenarios
are optimistic (10% daily value-traded participation, five sessions, 25 bps
one-way spread, `k=0.10`), base (5%, three sessions, 50 bps, `k=0.25`), and
conservative (2.5%, one session, 100 bps, `k=0.50`). The 1%/three-session/50
bps/`k=0.25` case is a non-headline diagnostic stress test.

At each rebalance, `required trade = new target position − actual executed
portfolio position`. An order follows `TARGET → SUBMITTED → PARTIALLY_FILLED →
FILLED | EXPIRED/CANCELLED`. Fill notional is capped at participation × observed
eligible daily trading value; a zero-liquidity session fills zero. Expired amounts
never carry automatically: the next rebalance uses only its new target and actual
holdings. Every AUM/scenario path has independent orders, fills, cash, and holdings.

`sigma20_annualized` is trailing 20-session annualized realised volatility in
decimal units. Impact uses its daily-equivalent scale:

`impact_sigma_daily = sigma20_annualized / sqrt(252)`

`impact_raw = k × impact_sigma_daily × sqrt(participation)`

`impact_applied = min(impact_raw, 0.05)`

The 5% cap is per fill. Spread and impact are `MODEL-BASED V1 / NOT
NGX-CALIBRATED`. `one_way_spread_bps` is a one-way modeled execution penalty
relative to observed execution-session close, not a claim about historical quoted
bid/ask: buys use `reference_close × (1 + modeled_spread + modeled_impact)` and
sells use `reference_close × (1 - modeled_spread - modeled_impact)`. Explicit fees
are accounted for separately. Cap hits are severe-liquidity diagnostics and record
count, rate, notional, and security.

Eligible sells are processed before buys. Same-session sale proceeds, net of
applicable execution costs and fees, are available to buys. If cash cannot fund all
eligible buy fills, it is allocated pro-rata by eligible desired fill notional. Cash
never becomes negative and no leverage is allowed. These rules make replay outcomes
independent of ticker or Python iteration order.

## Accounting and data integrity

Each replay retains Frozen Target, Executed Gross, and Executed Net portfolios.
Target-to-gross captures fill, delay, and portfolio-deviation effects. Gross-to-net
captures explicit fees, modelled spread, and modelled impact. Observed close
movement measures delay; neither delay nor unfilled-order opportunity cost is
deducted twice because cash and actual holdings determine economics.

Corporate-action intersections are flagged and reported as handled or unhandled.
No price adjustment is invented. An unresolved intersection is material when its
instrument has a non-zero executed holding, non-zero target position, or active
execution order during the affected interval and the frozen H-011/H-013 data and
methodology cannot deterministically produce a valid treatment. A material
unresolved intersection produces `INSUFFICIENT_DATA` for that replay path.

The unchanged explicit fee input is frozen from
`fixtures/frozen/h011_liquidity_comparison.sqlite`, table `modeled_cost_schedule`,
version `h011_liquidity_comparison_fixture_v1`. Its row-level deterministic digest
and components are recorded in the frozen input manifest.

## Classification

Target-notional completion is the absolute filled notional divided by absolute
target-trade notional, based on unique order requirements. Median order fill ratio,
full-fill, partial-fill, and zero-fill rates are diagnostics only.

Headline return is annualized compounded return over the full registered evaluation
period. Historical gross excess is frozen target-portfolio annualized gross return
minus the same benchmark annualized return. Executed net excess is executed-net
annualized return minus that same benchmark return. Alpha capture is executed net
excess divided by historical gross excess. Sharpe retention is executed-net
full-period Sharpe divided by frozen-target full-period Sharpe, using the same
sampling frequency and convention as the frozen strategy.

If historical gross excess is non-positive, alpha capture is `N/A` and headline
classification is `FAIL`: there is no positive historical gross excess to capture.
If required data make historical gross excess unavailable or invalid, alpha capture
is `N/A` and classification is `INSUFFICIENT_DATA`.

Target HHI is median daily equity HHI of the frozen target portfolio; executed HHI
is median daily equity HHI of the executed portfolio over the same sessions; and
the multiple is executed divided by target. Cash is excluded from equity HHI and
reported separately. Mean, 95th-percentile, and maximum HHI are diagnostics only.

Each submitted order receives a duration: submission through final fill inclusive
if filled; submission through expiry if partly filled; and the frozen maximum
horizon if zero-fill expired. Headline median duration includes every submitted
order, including zero-fill expiries.

`PASS` requires positive net excess; economically valid alpha capture ≥50%;
completion ≥80%; Sharpe retention ≥70%; executed HHI ≤1.5× target HHI; median
execution duration ≤3 sessions; and no accounting or implementation-integrity
failure.

`MARGINAL` requires positive net excess; economically valid alpha capture ≥25%;
completion ≥60%; Sharpe retention ≥40%; executed HHI ≤2.0× target HHI; and no
accounting or implementation-integrity failure. A complete-data replay that fails
MARGINAL is `FAIL`. Required observed-input absence or invalidity that prevents
meaningful classification is `INSUFFICIENT_DATA`.

Classification uses the full registered evaluation period only. If its historical
gross-excess denominator is non-positive or economically invalid, alpha capture is
`N/A` under the frozen denominator treatment. Year/regime views are diagnostic only.

The machine-readable protocol is [execution_capacity_v1.toml](../../configs/execution_capacity_v1.toml).
After its first result artifact, any substantive change requires
`execution_capacity_v2`.
