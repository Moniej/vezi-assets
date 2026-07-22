# Factor Registry — permanent knowledge base

Updated after EVERY completed experiment (program rule, 2026-07-22).
Status ∈ {Validated, Rejected, Under Research}. The hypothesis ledger and
experiment registry (`data/registry.sqlite`) remain the immutable
evidence store; this document is the curated institutional memory layered
on top — every claim here must cite ledger/experiment IDs.

The Validated section is EMPTY BY DESIGN and stays empty until evidence
promotes a factor through the unchanged gauntlet.

---

## Validated

### H-011 — Size (family: Size) — CONFIRMED 2026-07-22
**The platform's first validated factor.** Long the smallest-cap quintile
(top 20 by inverse market cap) within IRU v2, equal-weighted, quarterly
rebalance, vs the equal-weighted-IRU benchmark, net of retail costs.

- **Status**: Validated. Validation date: 2026-07-22.
  Memo: `reports/IC_memo_H-011_h011_size_2026-07-22.md`. Prereg:
  `docs/PREREG_H-011.md`. Config: `configs/h011_size.toml`.
- **Statistical evidence (all six pre-registered criteria met)**:
  placebo p=0.0099 (real Sharpe 2.244 exceeds even the MAXIMUM of 100
  shuffled draws, 1.918); net excess positive in development (+15.02%
  base cell, gross +20.94%) AND untouched OOS (+53.0%); plateau 6/6 grid
  cells positive (best-median gap 4.9%, a clean plateau not a spike);
  1/6 cells survives Holm (corrected p=0.049), 5/6 survive BH(FDR 0.10);
  no single regime carries >80% of positive excess (float_shock 46.8%,
  OOS 46.8%, pre_float 6.5%); zero signal-quality failure conditions
  triggered. Confidence rating **High (10/12)** — the highest in the
  program's history.
- **Holding horizon**: quarterly rebalance (base configuration; grid also
  tested semiannual — both cadences produced positive excess).
- **Turnover**: 1.13×/yr one-way (base cell, from the registry), cost
  drag 4.07%/yr, 35 decisions in the development window. Not the
  low-turnover story H-008 hoped for and didn't get either — size ranks
  are NOT dramatically stickier than momentum's on real NGX data — but
  the gross effect (+20.94%) is large enough that this turnover cost
  does not eliminate it, unlike H-007/H-005/H-006/H-003 where it did.
- **Capacity — the central, honestly-stated caveat**: median leg
  capacity ₦694,336 — roughly 10-15× WORSE than any other hypothesis
  tested on this platform (H-010: ₦9.6m; H-009: ₦11.8m; H-006: ₦9.1m).
  100% of trade legs rejected at ₦1bn AUM. This is NOT a contradiction
  of the signal — per governance, `capacity_below_minimum` is a
  scalability finding, evaluated separately from signal quality, and per
  the factor's OWN economic rationale (compensation for the exact
  liquidity friction this platform's capacity reports have documented in
  every prior hypothesis) severe illiquidity is the expected, not
  surprising, companion to this specific effect. **This is a real, valid,
  but SMALL-AUM strategy — not a broadly scalable one.**
- **Economic rationale**: capacity/liquidity-friction compensation, not
  an "undervalued small companies get discovered" narrative claim — the
  prereg was written and frozen to test specifically the friction
  version of the size story, and the capacity result is consistent with
  that framing, not in tension with it.
- **Practical implementation notes**: per-regime top contributors were
  consistently thin/illiquid names (LASACO in pre_float, MULTIVERSE in
  float_shock, NCR in OOS) — the effect is genuinely concentrated in the
  most illiquid tail of the universe, exactly where the economic
  rationale predicts it should be, and exactly where real-world
  implementation would be hardest.
- **Known limitations**: full-issue market cap, NOT float-adjusted (no
  shares-outstanding/free-float dataset exists yet — a stated
  construct-validity limitation: could partly proxy cross-holding
  structure rather than purely tradeable-float scarcity). Price-only
  returns (no dividend reinvestment). 177 single-source close-only days
  in the panel. Retail cost schedule 'assumed' confidence. rf=0%
  placeholder. Turnover unmeasured/unasserted in this writeup (see above).
- **Interaction with other validated factors**: none yet — this is the
  library's only entry. Expected (not yet measured) correlation with a
  future Momentum entry: low, per disjoint construction inputs. Expected
  HIGH correlation with any future Liquidity factor (small-cap and
  illiquidity are related by construction on NGX) — any future Liquidity
  prereg must address this overlap explicitly, not claim independence.
- **Confidence level**: High (10/12), per the platform's standard rating
  scale — the strongest-evidenced result in the program's 11-hypothesis
  history.
- **What this unlocks**: per
  `docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md`'s Year-1 exit condition
  (≥1 validated factor), Company Intelligence Engine v0 scaffolding may
  now begin. Portfolio Construction remains correctly GATED — the
  charter milestone requires ≥2 validated INDEPENDENT factors, and only
  one exists. Next engineering step: wire a `ModelAdapter` for H-011 in
  `alpha_engine.py`'s `MODEL_ADAPTERS` registry so the engine's honest
  `no_position` shell finally has something real to say.

---

## Under Research

*(none — H-010 moved to Rejected and H-011 moved to Validated, 2026-07-22)*

---

## Rejected — per-stock era

### H-010 — Pooled Overlapping-Cohort Momentum (family: Momentum) — REJECTED 2026-07-22
- Verdict (mechanical, per PREREG_H-010): placebo p=0.386 — a clean
  failure, and notably WORSE than H-009's near-miss (0.069), not an
  improvement. Cleanest plateau of the entire program (6/6 cells
  positive, best-median gap 0.15%) but 0/6 survive Holm (corrected
  p=0.853). Net excess +2.26% (matches the pre-run smoke test exactly)
  but `single_regime_dependency` NOW triggers — pre_float alone carries
  100% of positive excess; float_shock −10.0%; **OOS −6.6%**, flipping
  the sign of H-009's OOS result (+9.4%). Confidence rating Moderate
  (6/12). Memo: `reports/IC_memo_H-010_h010_pooled_momentum_2026-07-22.md`.
- Evidence summary — the decisive number: **real-data cohort return
  correlation averaged ~0.75** (recovered post-hoc from
  `backtest_xs.pooled_rank_run`'s diagnostics, since `result.attribution`
  is not yet persisted to the registry — see Known weaknesses), far
  higher than the ~0.57 measured on the synthetic rehearsal panel
  (`scripts/rehearse_xs_pooled.py`). The "4 independent cohorts" claim
  overstated the true information gain substantially — 4 highly
  correlated copies of the same bet, not 4 separate ones.
- Interpretation, stated carefully: the OOS sign flip suggests H-009's
  near-significant, all-regime-positive result was likely **partly a
  calendar-alignment artifact** of its one specific annual formation date
  landing favorably in the 2025-26 window, not a robust property of
  low-turnover momentum in general. Pooling — designed specifically to
  average out exactly this kind of timing luck — did so, and the
  apparent edge did not survive averaging.
- What is now KNOWN (do not retest without a materially different
  design): **the "pool more cohorts" successor path for NGX momentum is
  closed.** Turnover-fixing (H-009) was real progress on the cost
  problem; pooling did not fix the power problem, because the added
  cohorts are not independent enough to add power. A genuinely different
  signal construction — not another turnover/power variant of 12-1
  momentum — would be required for any further Momentum-family
  hypothesis, and it should address calendar-alignment risk explicitly
  in its own design, not assume it away.
- Capacity: median leg capacity ₦9.6m; 88% legs rejected at ₦1bn.
- Known weaknesses of the test: `result.attribution` (cohort correlation,
  per-cohort turnover) is computed by the engine but not yet wired into
  the persisted registry metrics or the IC memo template — recovered
  here by re-running the base config directly. Tracked as a follow-up
  engineering task (extend `runner.py`'s xs branch to persist
  `result.attribution` when present). Confidence-rating's "sample" score
  read 0 decisions — `n_rebalances` is computed from `result.weights`,
  which is empty by construction for pooled results (see
  `backtest_xs.pooled_rank_run`); the rating undercounts pooled
  hypotheses' true decision count. Neither gap affected this verdict
  (both are reporting/wiring issues, not evidence issues) but both
  should be fixed before the NEXT `xs_rank_pooled`-based hypothesis.
- Interaction: n/a (library empty).

### H-009 — Turnover-Budgeted Momentum (family: Momentum) — REJECTED 2026-07-22
- Verdict (mechanical, per PREREG_H-009): placebo p=0.069 — a NEAR-MISS
  against the 0.05 threshold, not a comfortable margin either way; no
  threshold was relaxed. Confidence rating Moderate (6/12).
  Memo: `reports/IC_memo_H-009_h009_xs_momentum_annual_2026-07-22.md`.
- Evidence summary — the most nuanced result of this wave: turnover
  reduction worked exactly as H-007's post-mortem predicted. Net excess
  FLIPPED POSITIVE (gross +6.10%, net +2.66%; H-007 was gross +2.18%, net
  −6.26%). 6/6 grid cells positive (100% plateau, best-median gap only
  1.9% — a clean plateau, not a lucky spike). Positive in all 3 regimes
  including the untouched OOS (+9.4%). BUT: 0/6 cells survive Holm
  (corrected p=0.572) and float_shock alone carries 73% of positive
  excess (below the 80% trigger, but concentrated). Diagnosis: annual/
  semiannual cadence over a 9-year window yields only ~9 independent
  decisions — this is now a STATISTICAL POWER problem, not a sign or
  cost problem. The economic direction is consistent; the sample is too
  small to prove it with confidence.
- Capacity: median leg capacity ₦11.8m (higher than H-007's, as the wider
  top_n=25 basket predicted); 96% legs rejected at ₦1bn.
- Known weaknesses: n=9 decisions in dev window is the binding limitation,
  not turnover or the underlying signal.
- What is now KNOWN: momentum's cost problem on NGX IS fixable by
  reducing turnover (confirmed, not just hypothesized) — but a single
  once-a-year snapshot doesn't generate enough independent bets to prove
  it statistically in a 9-year sample. Successor space (new ID required,
  NOT a rerun of this design): pool multiple momentum implementations
  (staggered formation windows) into one composite bet-count to raise
  power while keeping per-implementation turnover low; or a rolling
  overlapping-cohort implementation that preserves low turnover while
  generating more independent decision points than an annual snapshot.
  Do not simply rerun this exact design hoping for a different placebo
  draw — that is p-hacking, not research.
- Interaction: n/a (library empty). If a successor validates, expect high
  correlation with any other Momentum-family entry (same mechanism).

### H-008 — Low Volatility (family: Low Volatility) — REJECTED 2026-07-22
- Verdict (mechanical, per PREREG_H-008): placebo p=0.822 (worse than
  H-006's already-bad 0.842); 0/6 grid cells positive net excess (best
  −9.5%, median −11.3%); **GROSS excess itself negative (−8.70%)** —
  unlike H-006/H-007, this was not a real-effect-killed-by-costs story;
  6/6 cells significant after Holm (a statistically ROBUST negative tilt,
  not an absent effect); OOS excess −28.9%. Confidence rating Moderate
  (6/12 — the corrected significance and 3-regime coverage score points
  even in rejection). Memo:
  `reports/IC_memo_H-008_h008_low_vol_2026-07-22.md`.
- Evidence summary: long-only low-vol UNDERPERFORMED the EW-IRU benchmark
  robustly across all 3 regimes including OOS. Turnover was NOT
  dramatically lower than H-007's momentum (1.29×/yr vs 1.83×/yr, flagged
  honestly in the prereg before this run) — the cost-advantage premise
  partly held but is moot given the sign of the underlying effect.
- Capacity: median leg capacity ₦9.4m; 94% legs rejected at ₦1bn.
- Known weaknesses of the test: single, unconditional design spanning
  three violent NGX regime transitions (2016 FX crisis, 2020 COVID
  crash/recovery, 2023 float/devaluation) — plausible economic
  explanation below.
- What is now KNOWN (do not retest without a materially different
  design): the classic low-volatility mechanism (leverage-constrained
  investors overpaying for high-beta "lottery" names) appears to need a
  calmer macro backdrop than NGX has had 2016-2026; this window instead
  rewarded risk-taking/recovery names through repeated regime shocks.
  Successor space: a regime-CONDITIONAL retest (e.g. post-2023
  stabilization only, as its own hypothesis with its own OOS split) is
  legitimate; an unconditional retest of the same 2016-2026 design is not.
- Interaction: n/a (library empty).

### H-007 — Cross-Sectional Momentum (family: Momentum) — REJECTED 2026-07-22
- Verdict (mechanical, per PREREG_H-007): placebo p=0.644 — selection
  indistinguishable from persistence-preserving random relabelings; gross
  excess +2.18%/yr vs net −6.26%/yr (cost drag ~6.7%/yr at 1.83×/yr
  realized one-way turnover — above the 1.2–1.6× prior); plateau 1/6
  cells; 0 cells survive Holm; OOS net excess −30.3% (2025-26 bull:
  benchmark itself compounded fastest). Confidence rating Low. Memo:
  `reports/IC_memo_H-007_h007_xs_momentum_2026-07-22.md`.
- Evidence summary: a small positive GROSS momentum tilt exists (+2.2%/yr
  dev) but is (a) statistically indistinguishable from noise at this
  breadth and (b) ~3× smaller than its own transaction-cost bill.
- Capacity: median leg capacity ₦7.1m; 97.5% legs rejected at ₦1bn —
  even gross-viable successors are small-capital strategies.
- Implementation cost: ~6.7%/yr at retail rates; brokerage-negotiation
  sensitivity is real but would need rates ~3× lower to flip the sign.
- Known weaknesses of the test: price-only returns (understates winners
  by missed dividends — a total-return retest after the DOL dividend
  layer is a legitimate NEW hypothesis); 35 quarterly decisions.
- What is now KNOWN (do not retest without a materially different design):
  quarterly-turnover per-stock momentum at retail costs is dead on NGX.
  Successor space: annual-rebalance / buy-and-hold momentum tilts,
  turnover-budgeted designs, or negotiated institutional cost schedules.
- Interaction: n/a (library empty).

### H-006 — PEAD, market-reaction proxy (family: Event) — REJECTED 2026-07-22
- Verdict (mechanical, per PREREG_H-006): placebo p=0.842 — reaction-rank
  selection indistinguishable from random relabeling WITHIN cohort, despite
  4/4 grid cells significant on raw excess (corrected p=0.000 — the gross
  EVENT-DRIVEN effect itself is real and large, the RANKING adds nothing).
  Gross excess +16.69%/yr vs net −20.49%/yr (~37pp/yr cost drag — the
  20-concurrent-slot book turns over far faster than a single-event
  round-trip estimate implied). OOS net excess −48.7%. Confidence rating
  **High** (score 8/12) — this is a high-confidence, well-powered (862
  decisions) rejection, not an ambiguous one. Memo:
  `reports/IC_memo_H-006_h006_pead_2026-07-22.md`.
- Evidence summary: earnings-adjacent stocks as a POOL show a strong,
  statistically robust gross return pattern; the pre-registered top-tercile
  REACTION ranking within that pool carries no incremental selection
  information (placebo shuffles which pool member you'd hold, not whether
  to hold one — and shuffled draws matched the real ranking's Sharpe).
- Capacity: median leg capacity ₦9.1m; 97.5% legs rejected at ₦1bn.
- Implementation cost: ~37pp/yr — an order of magnitude above the
  pre-registered ~3.8%/event estimate; the estimate assumed one round trip
  per event, but a capped 20-slot book with continuous entries/exits against
  a benchmark sleeve trades far more.
- Known weaknesses of the test: price-only returns; single fixed sizing
  rule (1/20 NAV) not swept; entry lag/hold grid was narrow (2×2).
- What is now KNOWN (do not retest without a materially different design):
  (1) reaction-magnitude ranking is NOT a valid selection signal on this
  event set — a successor should test EVENT MEMBERSHIP alone (any
  Financial-Statements filer, unranked) as a genuinely new hypothesis;
  (2) capped-slot event-book turnover costs must be modeled explicitly
  before any future design reuses this construction — the 37pp/yr figure
  is itself a reusable cost-engineering finding, independent of PEAD.
- Interaction: n/a (library empty).

## Rejected (sector-era hypotheses, retained as program knowledge)

| ID | family | verdict date | one-line lesson (full record: ledger + IC memos) |
|---|---|---|---|
| H-001 | Momentum (sector) | 2026-07-15 | Sector breadth (~8 bets/yr) cannot host detectable alpha; placebo p=0.55. Frozen. |
| H-004 | Macro (oil→sector) | 2026-07-16 | Placebo p=0.079, OOS −11.9%; oil lead-lag not exploitable at sector level. |
| H-005 | Macro/Event (MPC windows) | 2026-07-16 | Gross window effect ≈ 0; ~4%/round-trip costs dominate all sub-monthly designs — program-wide constraint. |
| H-003 | Event (catalyst rotation) | 2026-07-16 | Low-power operationalization (~10 events); OOS uninformative per pre-declared clause. Slow catalysts only, need orders more events. |

Cross-cutting constraints inherited by all future factors: nothing faster
than quarterly holding survives retail costs; regime attribution must be
evaluated at capacity-feasible AUM; capacity caps AUM but never validates/
invalidates signal.

---

## Dataset → factor leverage map (program rule: every acquisition answers
"which factors does this improve; which families does it enable?")

| dataset (state) | improves | enables |
|---|---|---|
| LIST2 market-cap layer — DONE 2026-07-22, validated | benchmarks (cap-weighted), capacity precision | Size |
| Corp-actions archive — DONE 2026-07-22 (11,187/11,546, 97%) | event hygiene for all | Corporate-Actions/Event-Driven (needs OCR decision) |
| DOL dividend/EPS layer — ATTEMPTED 2026-07-22, NOT VALIDATED (`reports/eps_pe_extraction_status.md`); deprioritized, needs per-era recalibration | H-007 & all: total-return construction | Value (E/P), Dividend Yield |
| Shares outstanding harvest (backlog) | capacity, float adjustment | Size (float-adjusted) |
| Fundamentals extraction/OCR (user-gated) | PEAD (true surprise) | Quality, Growth, Accruals, Earnings Revisions |
