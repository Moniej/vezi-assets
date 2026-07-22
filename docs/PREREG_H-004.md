# Pre-Registration — H-004: Oil→Equity Lead-Lag (family F12)

*Registered 2026-07-15, BEFORE any H-004 experiment was run. The config
`configs/h004_oil_leadlag.toml` is the executable form of this document;
its hash enters every experiment record. Changes after first results =
new hypothesis ID.*

## Hypothesis

Lagged Brent crude moves predict NGX Oil & Gas sector relative returns over
investable horizons, net of costs, out of sample.

## Priority rationale (research efficiency, NOT expected success)

Highest-priority candidate because: near-zero acquisition cost (Brent
ingested from FRED at confidence 0.9), full reuse of already-validated NGX
index data, and the existing pipeline reaches a rigorous verdict quickly.
Nothing here implies an expectation that it validates.

## Exact signal specification

At each month-end signal date t (last trading day of month):
- R(t, L) = Brent(t) / Brent(t − L calendar months) − 1, using the PIT Brent
  series (values knowable at t; FRED publishes next-day — execution lag
  covers this, see caveat C4).
- If R > 0: hold NGXOILGAS at 100% of NAV. Else: hold NGXASI at 100%.
- Long-only, fully invested; execution 1 trading day after t; standard NGX
  cost schedule (assumed retail rates, as for H-001).

**Base configuration (the PRIMARY test):** L = 3 months, quarterly
rebalancing. Confirmation is judged on the base configuration — never on
the best grid cell.

**Stability grid:** L ∈ {1, 3, 6, 12} × {monthly, quarterly} = 8 cells.

## Windows (identical to platform standard)

- Development: 2016-06-01 → 2024-12-31.
- Final OOS (untouched until final_oos stage): 2025-01-02 → 2026-06-30.
- Regimes: pre2023 / shock_2023_24 / bull_2025_26 (walk-forward).

## Confirmation requires ALL of:

1. Placebo p ≤ 0.05 (100 seeded shuffled-label runs, seed 42) on the base
   configuration, development window.
2. Base-configuration net excess vs NGXASI > 0 in development AND final OOS.
3. No signal-quality failure condition triggered.
4. Plateau: ≥ 50% of the 8 grid cells with positive net excess.
5. Multiple testing: ≥ 1 cell significant under Benjamini–Hochberg at
   FDR 0.10 (grid n=8; Holm reported as well but BH is the criterion).

## Rejection (any one suffices):

placebo p > 0.05 · base OOS net excess ≤ 0 · regime concentration > 80% ·
cost drag eliminates gross excess.

## Pre-declared machinery adjustments (with rationale)

- `max_single_sector_share = 1.0` (condition disabled): a two-asset gate
  strategy is 100% concentrated by construction; the condition would fire
  as an artifact. Regime concentration (≤80%) remains fully active.
- `top_n = 1` fixed across the grid (the strategy holds exactly one asset).

## Scope limits & caveats (recorded now)

C1. Index-level (lite engine): assumes tradeable sector baskets; capacity
    not evaluable — same limitation as H-001, carried in all flags.
C2. rf = 0% placeholder: Sharpe overstated; excess-vs-benchmark is primary.
C3. NGXOILGAS June-2023 month excluded by data staging (documented hole).
C4. FRED Brent posts T+1; the month-end signal uses the value dated t, which
    is knowable before the t+1 execution — no lookahead, but a 1-day
    staleness vs live spot is possible; flagged, not modeled.
C5. Confirmation on 0.5-confidence index data caps the confidence rating
    at Moderate by the existing rubric.
