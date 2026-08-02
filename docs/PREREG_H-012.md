# Pre-Registration — H-012: Regime-Conditional Low-Volatility Gate (family: Low Volatility, regime-conditional variant)

*Drafted 2026-08-02, BEFORE any H-012 experiment run, per the full
architectural gap audit (`docs/ARCHITECTURAL_GAP_AUDIT_2026-08-02.md`).
This is Wave 3's own candidate C2 (`docs/WAVE_3_RESEARCH_DIRECTIONS.
md`), explicitly queued as "the next wave after C1/C4" — both of which
have since run (H-010 rejected, H-011 confirmed). Not a rerun of
H-008: the signal construction is identical and unmodified, but the
population of formation dates it is evaluated over is a materially
different, pre-declared subset — per program convention, a changed
population under a pre-declared, non-performance-derived rule is a new
hypothesis ID, not a retest of the same one. Executable form to be
drafted as `configs/h012_regime_vol.toml` only after this document is
reviewed. Any change to the regime rule after first results = a new
hypothesis ID again.*

## Economic rationale and market intuition

H-008 found the classic low-volatility mechanism (leverage-constrained
investors overpaying for high-beta "lottery" names, so low-vol names
are structurally underpriced) robustly REJECTED — not merely absent,
a statistically significant negative tilt — across 2016-2026. Its own
memo's stated explanation: this window contained three violent NGX
regime transitions (2016 FX crisis, 2020 COVID crash/recovery, 2023
float/devaluation), and in each, risk-taking/recovery names were
rewarded, exactly the opposite of what the low-vol mechanism predicts.
The classic mechanism plausibly *does* operate in calmer conditions —
NGX simply hasn't offered a long calm stretch to test it in
unconditionally. This hypothesis asks a narrower, pre-declared
question: **does low-volatility outperform specifically when the
market is NOT in the midst of, or immediately following, a
macro-regime shock?** — not "does low-vol always win," which H-008
already answered (no).

This is also, independently, a test of a NEW piece of reusable
research infrastructure: a regime-classification gate that could, if
validated as a sound methodology, be offered to any future hypothesis
on this platform, not just this one. Both purposes are stated
up front — the factor claim and the infrastructure claim are
evaluated on separate criteria (see Validation plan).

## Research question / hypotheses

Restricted to formation dates classified STABLE by the pre-declared
rule below (holding the EW-IRU benchmark on all other dates), does the
long-only low-volatility tilt beat the equal-weighted-IRU benchmark,
net of retail costs, out of sample?

- H0: net excess of the regime-gated low-vol portfolio vs EW-IRU is ≤ 0.
- H1: net excess > 0, robust across grid and OOS.

A secondary, methodology-level question (evaluated separately, not
part of the confirmation gate): does the regime-gate mechanism itself
behave correctly and transparently (correct classification, no
look-ahead, honest reporting of the stable/unstable date split)?

## Regime-classification rule (pre-declared, fixed BEFORE any performance data was viewed)

A formation date is **STABLE** unless, in the trailing 6 months:

1. A `critical`-severity event occurred in the `macro`, `banking`, or
   `commodity` category of the `events` table (captures the two real
   FX-regime-change events, 2016-06-15 and 2023-06-14, plus the 2024
   bank-recapitalisation directive and the 2023 fuel-subsidy removal
   — each a real, structurally disruptive shock, not a routine
   announcement); OR
2. More than one `high`-severity `monetary` (MPC) event occurred
   (captures clusters of rapid-fire policy moves — e.g. 2020's two
   emergency cuts, 2023-24's aggressive hiking cycle — as a proxy for
   monetary-policy uncertainty, distinct from a single routine
   quarterly MPC decision).

This rule uses **only** `events.category`/`events.severity`/
`events.announced_date` — fields that already exist, are already
populated (confirmed directly: 81 monetary events, 8 critical events
across macro/banking/insurance/commodity categories, date range
2011-10-10 to 2026-05-20), and are already used by H-004/H-005. No
new data source, no new extraction.

**Feasibility, checked directly against real dates before drafting
this document (zero return/performance data touched):** across 42
quarterly formation dates spanning H-008's own development + OOS
window (2016 Q1 through 2026 Q2), **27 classify STABLE, 15 UNSTABLE**.
The OOS window (2025 Q1 – 2026 Q2, 6 formation dates) is entirely
STABLE under this rule — a real, checkable fact about the rule's own
behavior, not a convenient coincidence engineered by looking at
returns.

## Universe / data (frozen)

- IRU v2 members at each formation date (PIT, rename-canonical),
  identical to H-008.
- `equity_prices_asof`, `min_confidence = 0.9`, **vintage =
  2026-07-21**, `requires_coverage_gate = true` — identical to H-008.
- `events` table, read-only, filtered per the rule above at each
  formation date using only `announced_date` (never `effective_date`
  or any date the market could not yet have known) — a look-ahead
  discipline check is part of the validation plan.

## Signal specification

**Identical to H-008, unmodified**: score = negative standardized
trailing realized volatility (`vol_scores()`, called without
modification). The regime gate is applied AFTER scoring, not by
changing the signal itself — for any formation date classified
UNSTABLE, the portfolio holds the EW-IRU benchmark weights for that
rebalance instead of the low-vol tilt (i.e., the active bet is "off"
on unstable dates, never a distorted or blended version of it). This
keeps the signal-construction risk identical to H-008's own
already-scrutinized code path; the only new logic is the date-level
gate itself.

## Portfolio construction

- **Base configuration (PRIMARY)**: long the lowest-volatility 20
  names by trailing 12-month realized vol within the IRU,
  equal-weighted, quarterly rebalance, execution lag 1 trading day —
  identical to H-008's base cell — **applied only on formation dates
  classified STABLE**; EW-IRU benchmark weights on UNSTABLE dates.
- Long-only, fully invested, no leverage, no shorts.
- Liquidity: ADTV participation cap 10%, 60-day ADTV (platform
  default, unchanged).
- Stability grid (6 cells, identical to H-008's own grid): rebalance ∈
  {quarterly, semiannual} × top_n ∈ {15, 20, 30}.

## Benchmark (ex-ante) — identical to H-008 and every prior per-stock hypothesis

Equal-weighted IRU portfolio, quarterly rebalance, identical cost
model. (This benchmark is also what the portfolio itself reverts to on
UNSTABLE dates — the same series serves both roles, by design, so the
gate's "off" state is never a different, undisclosed default.)

## Costs / turnover / capacity

**Turnover is expected to be LOWER than H-008's base** (1.29×/yr),
since roughly a third of rebalance dates now simply hold the prior
benchmark position rather than re-tilting — but this is a prediction
to be measured and reported honestly, not asserted in advance, per
the same discipline H-008 itself established. Capacity is expected to
be similar to H-008's (₦9.4m median leg) on the dates the tilt is
actually active; unmeasured until run.

## Windows — identical to H-008

Development 2016-01-02 → 2024-12-31. **Untouched OOS: 2025-01-02 →
2026-06-30.** Same three regime labels for reporting purposes
(pre_float / float_shock / oos_2025_26) — note these are H-008's own
REPORTING regimes (used for the `max_single_regime_share` failure
check) and are distinct from this hypothesis's own STABLE/UNSTABLE
gate; both concepts are reported, never conflated.

## Validation plan

Phase 4 unchanged in structure: stability map (6 cells) → Holm/BH →
seeded placebo (100 iterations, same persistence-preserving design as
every prior `xs_*` hypothesis) → walk-forward → final OOS → IC memo.
**Additionally, before any performance result is computed**: a
standalone look-ahead audit confirming every regime classification at
formation date `f` used only events with `announced_date <= f`
(mirroring FSI Phase 4's own 30-point look-ahead audit discipline,
applied here to the regime gate) — this is a mechanical correctness
check on the METHODOLOGY, reported independently of the hypothesis's
own confirm/reject verdict.

## Confirmation requires ALL of

1. Placebo p ≤ 0.05 on the base configuration.
2. Base net excess vs EW-IRU > 0 in development AND final OOS.
3. Plateau: ≥ 4 of 6 grid cells with positive net excess.
4. ≥ 1 cell significant under Benjamini–Hochberg at FDR 0.10.
5. No regime (of H-008's own pre_float/float_shock/oos_2025_26
   reporting regimes) contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered.
7. **New, methodology-specific**: the look-ahead audit above finds
   zero violations. A violation here invalidates the run regardless of
   any performance result — the regime gate itself must be proven
   correct, not just lucky.

## Rejection (any one suffices)

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates
gross excess · regime concentration > 80% · signal-quality failure
condition · a look-ahead violation in the regime gate (rejects the
METHOD, independent of any performance number it produced).

## Multiple-testing treatment

6 cells under BH within this hypothesis. Program-level ledger count
(12 hypotheses through this wave, 1 still blocked-on-data at H-002)
reported in the IC memo. H-012 is this wave's only active hypothesis
(the platform's ≤2-active-hypotheses rule is not binding here since no
second candidate is proposed alongside it).

## Expected Interaction with Existing Factors

- Family: **Low Volatility** — a regime-conditional variant of H-008,
  not a new family. The Low Volatility family's unconditional entry
  (H-008) remains REJECTED and is not superseded by this hypothesis
  regardless of its outcome — a conditional retest validating does not
  retroactively validate the unconditional claim H-008 tested.
- Expected correlation with H-011 (Size, the library's only validated
  entry): LOW — disjoint construction inputs (trailing volatility vs.
  market-cap level), though both may show elevated co-movement during
  the exact `UNSTABLE` windows this hypothesis excludes (small, thin
  names are often also the most volatile) — a second-order check to
  perform once results exist, not assumed.
- Diversification if validated: would give the library its first
  entry whose defining feature is a REUSABLE regime-conditioning
  METHOD, independent of whether the underlying low-vol signal itself
  is the one that benefits — future hypotheses (any family) could
  request the same gate applied to their own signal, evaluated on
  their own merits, never inherited automatically.
- Portfolio construction value if validated: this would be a
  **partially-invested-in-the-tilt** sleeve (roughly two-thirds of
  formation dates active, one-third reverting to benchmark) — a
  materially different implementation shape from every prior fully-
  tilted hypothesis, worth flagging explicitly for any future
  portfolio-construction consumer.
- Independence rationale: input is trailing realized volatility,
  identical to the already-scrutinized H-008 construction; the only
  new input is `events.category`/`severity`/`announced_date`, already
  used (differently) by H-004/H-005, with no shared construction logic
  with any validated or rejected factor's own scoring.

## Known limitations (pre-declared)

L1 the regime rule's two specific thresholds (6-month lookback,
`>1` high-severity MPC events) are a considered but not empirically
tuned choice — chosen for economic plausibility (a shock's disruptive
effect on investor risk appetite plausibly persists for a couple of
quarters, not a single month or several years) and confirmed feasible
against real dates, but NOT swept or optimized against any outcome;
changing either threshold after seeing a result would require a new
hypothesis ID. L2 price-only returns (no dividend reinvestment),
identical to H-008. L3 the STABLE subset is a strict subset of H-008's
own window by construction — statistical power is lower than the
already-marginal H-008 test, a known, disclosed risk, not discovered
after the fact. L4 retail cost schedule 'assumed' confidence,
identical to H-008. L5 rf = 0 placeholder, identical to H-008. L6 this
hypothesis cannot rehabilitate H-008's own unconditional rejection
even if confirmed — the two remain separate, permanent ledger entries.
