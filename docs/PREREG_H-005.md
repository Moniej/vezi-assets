# Pre-Registration — H-005: MPC Announcement-Window Effects (family F11)

*Registered 2026-07-16, BEFORE any H-005 experiment was run. Executable form:
`configs/h005_mpc_window.toml`. Changes after first results = new hypothesis ID.*

## Hypothesis

NGX sector returns show exploitable patterns in windows following CBN MPC
decision announcements, net of costs, out of sample.

## Priority rationale (research efficiency, not expected success)

The sole data dependency (80-meeting MPC history, confidence 0.9, primary
source) landed yesterday; infrastructure is complete; a rigorous verdict is
cheap and fast. Nothing here implies an expectation that it validates.

## Exact signal specification

- Event set: all `mpc_decision` events (announced_date), confidence ≥ 0.4,
  unconditional on decision direction (single pre-registered choice — no
  hike/cut conditioning, to avoid forking paths).
- On each announcement date t: enter NGXBNK at 100% of NAV (execution 1
  trading day after t, platform standard). Hold for K trading days, then
  revert to NGXASI. Overlapping windows extend (re-entry supersedes exit).
- Mechanism sketch: rate decisions reprice bank net-interest-margin
  expectations; under thin analyst coverage the repricing may extend over
  days rather than minutes. Banking is the pre-registered target (the
  rate-sensitivity mechanism); no other sector will be tested under this ID.
- **Base configuration (PRIMARY): K = 10 trading days.**
- Stability grid: K ∈ {5, 10, 21} (3 cells; encoded via the config's
  lookback field, rebalance fixed "monthly" = use-all-signal-dates,
  top_n fixed 1).

## Windows (platform standard)

Development 2016-06-01→2024-12-31 (~47 MPC events); final OOS (untouched)
2025-01-02→2026-06-30 (~8 events); regimes pre2023 / shock_2023_24 /
bull_2025_26.

## Confirmation requires ALL of:

1. Placebo p ≤ 0.05 on the base configuration (100 seeded shuffles). Note:
   the platform placebo shuffles asset assignment at identical switch dates
   — it tests whether the *direction* of the allocation beats random at the
   same timing and cost structure.
2. Base-configuration net excess vs NGXASI > 0 in development AND final OOS.
3. No signal-quality failure condition triggered.
4. Plateau: ≥ 2 of 3 grid cells with positive net excess.
5. ≥ 1 cell significant under Benjamini–Hochberg at FDR 0.10.

## Rejection (any one suffices)

placebo p > 0.05 · base OOS net excess ≤ 0 · regime concentration > 80% ·
cost drag eliminates gross excess.

## Cost realism, stated up front

~5.5 events/year × two full-NAV switches per window ≈ 11 switches/year at
~1.9% per side is a very large cost hurdle (order of 20–40%/yr at
retail-max brokerage). This is deliberate: the hypothesis claims
*exploitable* patterns, and cost-viability is part of the claim. If the
gross effect exists but costs eliminate it, the pre-declared
`cost_drag_eliminates_excess` condition will record exactly that — a
scientifically useful outcome, not a technicality.

## Pre-declared machinery notes

- `max_single_sector_share = 1.0` (disabled): two-asset strategy, 100%
  concentrated by construction (same rationale as H-004).
- Capacity not evaluable (index-level, lite engine) — scope limit C1 as in
  prior preregs; rf = 0% placeholder (C2); NGXBNK June-2023 data hole (C3);
  0.5-confidence index data caps the confidence rating at Moderate (C5).
