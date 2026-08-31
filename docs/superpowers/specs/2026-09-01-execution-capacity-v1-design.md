# Execution & Capacity Study v1 — Design

## Purpose and scope

This standalone, read-only research implementation study replays execution of the
frozen H-011 Size and H-013 high-liquidity Size target portfolios under fixed,
model-based NGX assumptions. It answers how much historical factor return could
plausibly have been captured at six specified capital levels. It is not a new
Alpha hypothesis, a strategy optimisation, an execution recommendation, or proof
of live executable performance.

The study must not modify H-011, H-013, H-016, H-022, H-024, canonical identity,
historical identity, evidence records, Research OS, FRE, Alpha Engine governance,
or Portfolio behaviour.

## Inputs and output boundary

Inputs are the original H-011 configuration and frozen comparison artifacts, and
the approved H-013 high-liquidity configuration/results. The study will hash each
input before replay and write a versioned frozen package under
`fixtures/frozen/execution_capacity_v1/`. It will never write to a production
SQLite database.

A new standalone execution-replay module will consume target weights and daily
market fields, producing an auditable order, execution, and portfolio path for
each strategy/AUM/scenario. Existing `execution_realism` remains unchanged because
it is a diagnostic rather than a multi-session order-state simulator.

## Frozen assumptions

Capital grid: NGN 10m, 50m, 100m, 250m, 500m, and 1bn.

| Scenario | Daily value-traded participation | Maximum horizon | One-way spread | Square-root impact k |
|---|---:|---:|---:|---:|
| Optimistic | 10% | 5 sessions | 25 bps | 0.10 |
| Base (primary) | 5% | 3 sessions | 50 bps | 0.25 |
| Conservative | 2.5% | 1 session | 100 bps | 0.50 |

The non-headline participation stress diagnostic is 1% participation, a three
session horizon, 50 bps one-way spread, and `k = 0.25`. The existing explicit fee
schedule is used unchanged. Spread and impact are labelled `MODEL-BASED V1 / NOT
NGX-CALIBRATED`; bid/ask, order-book depth, and broker calibration are not claimed
where absent.

For each fill, impact is frozen as:

`impact_raw = k × sigma20 × sqrt(participation)`

`impact_applied = min(impact_raw, 0.05)`

The 5% cap is per fill. Every fill records `impact_cap_hit`; the study reports cap
hit count, percentage of fills, associated notional, and responsible securities.
A cap hit is a severe-liquidity diagnostic, never acceptance evidence.

The replay uses observed daily close movement to measure execution-delay exposure.
Unfilled order opportunity cost is not separately deducted, preventing double
counting: residual cash and actual holdings alone determine portfolio return.

## Execution architecture

At each rebalance, each independent AUM path creates orders from the difference
between the new target position and the actually executed portfolio position.
Orders advance deterministically:

`TARGET → SUBMITTED → PARTIALLY_FILLED → FILLED | EXPIRED/CANCELLED`.

Daily fill notional cannot exceed participation × observed eligible trading value,
cannot fill on a zero-liquidity day, and ends at the fixed horizon. Expired or
unfilled quantities never roll automatically forward; the next rebalance evaluates
only the then-current target against actual holdings. The weighted execution price
separates explicit fees, modelled spread, and modelled impact. Delay is reported
from observed price movement but not applied as an additional cost deduction.
Cash, holdings, fills, and costs reconcile per path.

No portfolio is scaled from another capital level; each capital/scenario path has
its own orders, fills, cash, and holdings.

## Data classification and limitations

The implementation will produce a pre-result coverage inventory. Daily price,
volume, value traded, ADTV60, deals where available, and corporate-action flags
are classified as observed or derived from observed. Bid/ask, depth, and broker
impact calibration remain unavailable unless existing frozen inputs demonstrably
contain them. A calibration interface will accept future broker, shadow-book, and
live-execution observations without changing replay semantics.

Where an execution or holding interval intersects a corporate action that cannot be
correctly handled using the frozen H-011/H-013 methodology and available data, the
replay flags the intersection and reports handled versus unhandled counts and
materiality. Material unresolved intersections render that replay
`INSUFFICIENT_DATA`; the engine never invents price adjustments.

All final results are labelled **MODEL-BASED HISTORICAL EXECUTION REPLAY**, never
actual historical execution or live realised return. Every strategy/AUM/scenario
retains three distinct performance objects: (A) frozen target portfolio, (B)
executed gross portfolio, and (C) executed net portfolio. Their decomposition is
target → executed gross (fill, delay, and portfolio deviation) and executed gross
→ executed net (explicit fees, modelled spread, and modelled impact).

## Acceptance labels

The study will freeze objective implementation labels before results:

- `PASS`: all of net excess return > 0; alpha capture ≥50% where the historical
  gross-excess denominator is economically valid; target-notional completion
  ≥80%; executed Sharpe ≥70% of target-portfolio Sharpe; executed HHI ≤1.5× target
  HHI; median execution duration ≤3 sessions; and no accounting or implementation
  integrity failure.
- `MARGINAL`: all of net excess return > 0; alpha capture ≥25%; target-notional
  completion ≥60%; executed Sharpe ≥40% of target-portfolio Sharpe; no catastrophic
  concentration; and no accounting or implementation integrity failure.
- `FAIL`: a complete-data replay that fails MARGINAL.
- `INSUFFICIENT_DATA`: required observed execution input is unavailable or invalid
  to the extent that the predeclared replay cannot be meaningfully classified.

Target-notional completion is
`sum(abs(filled_notional)) / sum(abs(target_trade_notional))`, computed on unique
order requirements so sells, cash, expiry, and order replacement cannot double
count. Median order fill ratio, full-fill rate, partial-fill rate, and zero-fill
rate remain separate reported diagnostics; none substitutes for portfolio-level
completion.

These labels are implementation diagnostics, not Alpha governance verdicts or
investment eligibility decisions.

## Verification and reproducibility

The implementation will be test-driven. Dedicated tests will cover AUM-dependent
orders, partial/unfilled fills, caps and zero-liquidity days, horizon expiry, cost
and cash reconciliation, independent AUM paths, frozen inputs/configuration,
unchanged historical artifacts, H-024 isolation, and deterministic artifact
rebuilds. The complete canonical verification suite runs before and after the
study. The frozen package records source/config/protocol/output hashes, row counts,
coverage, scenario definitions, and repository commit.

## Out of scope

No execution assumption may be changed after results are generated. Any such
change requires a separately named `execution_capacity_v2` protocol and dataset.
The work performs no live orders, no shadow orders, no broker calibration, and no
identity or historical-data repair.
