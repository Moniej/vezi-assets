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

*(none — 0 validated factors; that is the honest current state)*

---

## Under Research

*(none — H-008 and H-009 both moved to Rejected, 2026-07-22)*

---

## Rejected — per-stock era

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
