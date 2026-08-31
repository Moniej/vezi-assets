# Execution & Capacity Study v1 — Final Protocol Design

## Purpose and isolation

This standalone, read-only research implementation study replays execution of the
frozen H-011 Size and H-013 high-liquidity Size target portfolios under fixed,
model-based NGX assumptions. It answers how much historical factor return could
plausibly have been captured at six specified capital levels. It is not a new
Alpha hypothesis, a factor search, an execution recommendation, or proof of live
executable performance.

The study must not modify H-011, H-013, H-016, H-022, H-024, canonical identity,
historical identity, evidence records, Research OS, FRE, Alpha Engine governance,
or Portfolio behaviour. It never writes to production SQLite databases.

## Inputs and output boundary

Inputs are the original H-011 configuration and frozen comparison artifacts, and
the approved H-013 high-liquidity configuration and results. Every input is hashed
before replay. Outputs are a versioned frozen package under
`fixtures/frozen/execution_capacity_v1/`.

A new standalone execution-replay module consumes target weights and daily market
fields, producing an auditable order, execution, and portfolio path for each
strategy, AUM, and scenario. Existing `execution_realism` remains unchanged because
it is a diagnostic rather than a multi-session order-state simulator.

## Frozen scenarios

Capital grid: NGN 10m, 50m, 100m, 250m, 500m, and 1bn.

| Scenario | Daily value-traded participation | Maximum horizon | One-way spread | Square-root impact k |
|---|---:|---:|---:|---:|
| Optimistic | 10% | 5 sessions | 25 bps | 0.10 |
| Base (primary) | 5% | 3 sessions | 50 bps | 0.25 |
| Conservative | 2.5% | 1 session | 100 bps | 0.50 |

The non-headline participation stress diagnostic uses:

- participation = 1%
- maximum horizon = 3 sessions
- one-way spread = 50 bps
- impact k = 0.25

It is diagnostic only and is not a fourth headline scenario. The existing explicit
fee schedule is used unchanged. Spread and impact assumptions are explicitly
labelled `MODEL-BASED V1 / NOT NGX-CALIBRATED`.

## Execution architecture

At each rebalance:

`required trade = new target position − actual executed portfolio position`

Orders then follow:

`TARGET → SUBMITTED → PARTIALLY_FILLED → FILLED | EXPIRED/CANCELLED`

Expired or unfilled quantities never automatically roll forward. At the next
rebalance, required orders are recomputed solely from the new target and actual
holdings.

The fill constraints are:

- daily fill notional ≤ participation × observed eligible trading value;
- zero-liquidity session → zero fill;
- execution stops at the frozen maximum horizon;
- no automatic order carry-forward; and
- each AUM/scenario has independent cash, holdings, orders, and fills.

## Costs, impact, and performance decomposition

Impact uses consistent decimal units:

`impact_raw = k × sigma20 × sqrt(participation)`

`impact_applied = min(impact_raw, 0.05)`

The 5% cap is per fill. Every fill records `impact_cap_hit = true/false`. The study
reports cap-hit count, cap-hit percentage, associated notional, and responsible
securities. Cap hits are severe-liquidity diagnostics.

Each strategy/AUM/scenario maintains three distinct performance objects:

- Frozen Target Portfolio
- Executed Gross Portfolio
- Executed Net Portfolio

The decomposition is:

`Target → Executed Gross = fill / delay / portfolio-deviation effect`

`Executed Gross → Executed Net = explicit fees + modelled spread + modelled impact`

Delay is measured from observed historical price movement but is not deducted again
as a separate accounting charge. Unfilled opportunity cost is not separately
deducted because residual cash and actual holdings already determine realised
portfolio economics.

## Data classification and corporate actions

The study produces a pre-result coverage inventory. Daily price, volume, value
traded, ADTV60, deals where available, and corporate-action flags are classified as
observed or derived from observed. Bid/ask, depth, and broker impact calibration
remain unavailable unless existing frozen inputs demonstrably contain them. A
calibration interface accepts future broker, shadow-book, and live-execution
observations without changing replay semantics.

Where an execution or holding interval intersects a corporate action that cannot be
correctly handled using the frozen H-011/H-013 methodology and available data, the
study flags the intersection, reports handled/unhandled counts and materiality, and
does not invent an adjustment. Material unresolved corporate-action contamination
sufficient to invalidate the replay results in `INSUFFICIENT_DATA`.

All final results are labelled **MODEL-BASED HISTORICAL EXECUTION REPLAY**. They
must never be described as actual historical execution, empirically realised
execution, or live realised performance.

## Completion and acceptance classification

Target-notional completion is:

`sum(abs(filled_notional)) / sum(abs(target_trade_notional))`

It is calculated on unique order requirements, so sells, cash, expiry, and order
replacement cannot double count. Report separately: target-notional completion,
median order fill ratio, full-fill rate, partial-fill rate, and zero-fill rate.
Median order fill ratio is diagnostic only.

Headline acceptance classification is based on the full registered evaluation
period for each strategy/AUM/scenario. If the historical gross-excess denominator
for that headline period is non-positive or otherwise fails the predeclared
economic-validity rule, do not manufacture an alpha-capture ratio: report
`alpha_capture = N/A` and apply the preregistered denominator-validity treatment.
Year and regime decompositions are diagnostics and do not independently change the
headline classification.

`PASS` — all must hold:

- net excess return > 0;
- alpha capture ≥50% where the historical gross-excess denominator is economically
  valid;
- target-notional completion ≥80%;
- executed Sharpe ≥70% of target-portfolio Sharpe;
- executed HHI ≤1.5× target-portfolio HHI;
- median execution duration ≤3 sessions; and
- no accounting or implementation-integrity failure.

`MARGINAL` — all must hold:

- net excess return > 0;
- alpha capture ≥25% where the historical gross-excess denominator is economically
  valid;
- target-notional completion ≥60%;
- executed Sharpe ≥40% of target-portfolio Sharpe;
- executed HHI ≤2.0× target-portfolio HHI; and
- no accounting or implementation-integrity failure.

`FAIL` is a complete-data replay that fails `MARGINAL`, including an executed HHI
greater than 2.0× target-portfolio HHI.

`INSUFFICIENT_DATA` applies only where required observed execution inputs are
unavailable or invalid to the extent that the preregistered replay cannot be
meaningfully classified.

These labels are implementation diagnostics, not Alpha governance verdicts or
investment eligibility decisions.

## Verification and reproducibility

The implementation is test-driven. Dedicated tests cover AUM-dependent orders,
partial and unfilled fills, participation caps and zero-liquidity days, horizon
expiry, cost and cash reconciliation, independent AUM paths, frozen inputs and
configuration, unchanged historical artifacts, H-024 isolation, and deterministic
artifact rebuilds. The complete canonical verification suite runs before and after
the study. The frozen package records source, configuration, protocol, and output
hashes; row counts; coverage; scenario definitions; freeze timestamp; and
repository commit.

No execution assumption may be changed after the first capacity result is
generated. Any material change requires a separately named `execution_capacity_v2`
protocol and dataset. The work performs no live orders, shadow orders, broker
calibration, or identity or historical-data repair.
