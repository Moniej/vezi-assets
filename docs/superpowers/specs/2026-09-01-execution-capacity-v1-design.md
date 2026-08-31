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

The 1% participation case is retained as a non-headline stress diagnostic. The
existing explicit fee schedule is used unchanged. Spread and impact are labelled
`MODEL-BASED V1 / NOT NGX-CALIBRATED`; bid/ask, order-book depth, and broker
calibration are not claimed where absent.

The replay uses observed daily close movement to measure execution-delay exposure.
Unfilled order opportunity cost is not separately deducted, preventing double
counting: residual cash and actual holdings alone determine portfolio return.

## Execution architecture

At each rebalance, each independent AUM path creates orders from the difference
between target and actually executed weights. Orders advance deterministically:

`TARGET → SUBMITTED → PARTIALLY_FILLED → FILLED | EXPIRED/CANCELLED`.

Daily fill notional cannot exceed participation × observed eligible trading value,
cannot fill on a zero-liquidity day, and ends at the fixed horizon. The weighted
execution price separates explicit fees, modelled spread, and modelled impact.
Delay is reported from observed price movement but not applied as an additional
cost deduction. Cash, holdings, fills, and costs reconcile per path.

No portfolio is scaled from another capital level; each capital/scenario path has
its own orders, fills, cash, and holdings.

## Data classification and limitations

The implementation will produce a pre-result coverage inventory. Daily price,
volume, value traded, ADTV60, deals where available, and corporate-action flags
are classified as observed or derived from observed. Bid/ask, depth, and broker
impact calibration remain unavailable unless existing frozen inputs demonstrably
contain them. A calibration interface will accept future broker, shadow-book, and
live-execution observations without changing replay semantics.

All final results are labelled **MODEL-BASED HISTORICAL EXECUTION REPLAY**, never
actual historical execution or live realised return.

## Acceptance labels

The study will freeze objective implementation labels before results:

- `PASS`: net excess return > 0, target-weight completion ≥80%, median order fill
  ratio ≥80%, and alpha capture ≥50% where the historical gross-excess denominator
  is economically valid.
- `MARGINAL`: net excess return > 0, completion ≥50%, median fill ≥50%, and alpha
  capture ≥25%, but does not meet PASS.
- `FAIL`: a complete-data replay that fails MARGINAL.
- `INSUFFICIENT_DATA`: required observed execution input is unavailable or invalid
  for the predeclared replay.

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
