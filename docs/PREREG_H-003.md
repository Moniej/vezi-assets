# Pre-Registration — H-003: Catalyst-Driven Sector Rotation (family F1)

*Registered 2026-07-16, BEFORE any H-003 experiment was run. Executable form:
`configs/h003_catalyst_rotation.toml`. Changes after first results = new
hypothesis ID.*

## Hypothesis

Positioning on announced, slow-moving structural catalysts (regulatory
directives, recapitalisation cycles, sector policy changes) generates
positive excess return over NGX ASI after costs, out of sample.

## Evidence-driven design constraints (inherited, not chosen)

- **Quarterly holding minimum** (H-005: NGX switching costs ~4%/round trip
  make sub-monthly event strategies unviable; gross short-window MPC effect
  ≈ 0).
- **No price-momentum component** (H-001 rejected; frozen).
- **Slow catalysts only**: market-scope events (FX regime, MPC, BDC policy)
  are EXCLUDED from sector scoring — they do not differentiate sectors.
  Only sector-scoped structural events score.

## The no-hindsight direction rule

Event `direction` is `unknown` throughout the database by design. This
strategy therefore uses **no direction labels at all**:

- **Activity**: a sector is *catalyst-active* at date t if any sector-scoped
  event has announced_date ≤ t ≤ max(effective_date, announced_date + W
  months). Mechanism claim: structural catalysts force repricing and
  attention in a thin market, and the average drift of catalyst-active
  sectors is positive over quarterly horizons.
- **Impairment**: sectors with an active event carrying
  `structurally_impairing = 1` are excluded. That flag was assigned at
  data-entry time from stated mechanism (dilution risk from forced capital
  raising: the 2019 NAICOM and 2024 CBN recapitalisations), never from
  observed returns.
- Honest contamination note: these events are historical and famous; no 2026
  design is perfectly hindsight-free. Mitigations: direction-free scoring,
  entry-time impairment flags, the shuffled-assignment placebo (does WHICH
  sector had the catalyst matter?), and an OOS window whose events were not
  known when the taxonomy was designed.

## Exact signal specification

Universe: NGXBNK, NGXINS, NGXOILGAS (sectors with event coverage AND full
price history) + NGXASI as fallback. At each month-end t (rebalanced
quarterly, execution lag 1 day):

1. Score each sector 1.0 if catalyst-active and not impaired, else 0.0.
2. NGXASI scores 1.0 if no sector qualifies, else 0.0.
3. Weights ∝ scores (equal weight among qualifying sectors; 100% ASI when
   none qualify). Long-only, fully invested.

**Base configuration (PRIMARY): W = 12 months.**
Stability grid: W ∈ {6, 12, 18} (3 cells; W rides the config lookback field).

## Windows

Development 2016-06-01 → 2024-12-31; final OOS (untouched) 2025-01-02 →
2026-06-30; regimes pre2023 / shock_2023_24 / bull_2025_26.

## Statistical power, stated before results

Only ~10 sector-scoped events exist in the curated timeline (BNK 5, INS 3,
OILGAS 2). This is a small-sample study by construction; per the standing
gap-report warning, the confidence rating will be capped low regardless of
outcome, and a confirmation here mandates event-coverage expansion before
any Alpha Engine wiring decision (which goes to IC with the rating).

## OOS-uninformative clause (decided now, before seeing the window)

The 2024-03 recapitalisation impairs NGXBNK until 2026-03-31 and no later
sector-scoped events exist yet; the OOS window may therefore hold ASI
throughout. Pre-declared handling: **if the strategy takes zero active
sector positions in the OOS window, the OOS criterion is UNINFORMATIVE —
the run cannot confirm the hypothesis.** In that case H-003 remains
`testing` with the development-window results documented, and the verdict
waits for forward OOS accumulation (new events after 2026-07). OOS
uninformativeness is not a pass.

## Confirmation requires ALL of:

1. Placebo p ≤ 0.05 on the base configuration (100 seeded shuffles of
   sector-score assignment at identical dates/costs).
2. Base net excess vs ASI > 0 in development AND in an INFORMATIVE final
   OOS (see clause above).
3. No signal-quality failure condition triggered.
4. Plateau: ≥ 2 of 3 grid cells with positive development net excess.
5. ≥ 1 cell BH-significant at FDR 0.10.

## Rejection (any one suffices)

placebo p > 0.05 · informative-OOS net excess ≤ 0 · regime concentration
> 80% · cost drag eliminates gross excess.

## Machinery notes (pre-declared)

- `max_single_sector_share` disabled (small universe; concentration by
  construction when one sector qualifies) — as in H-004/H-005.
- Catalyst filter flag unused: impairment is handled inside the score rule.
- Scope limits C1 (index-level, no capacity), C2 (rf = 0%), C3 (June-2023
  data hole), C5 (0.5-confidence prices) carry over; events at 0.7–0.9.
