# Pre-Registration — H-007: Cross-Sectional Momentum (family: Momentum)

*Drafted 2026-07-22, BEFORE any H-007 experiment run. Executable form:
`configs/h007_xs_momentum.toml` (to be encoded when the cross-sectional
engine extension lands — see BLOCKER note in the readiness report; the
design below is frozen now and the config must encode it verbatim).
Changes after first results = new hypothesis ID.*

## Economic rationale and market intuition

Slow information diffusion plus underreaction sustains price trends;
cross-sectional momentum is the most replicated equity anomaly globally,
with strong evidence in frontier/EM markets. NGX-specific amplifiers:
no analyst coverage for most names, retail-dominated flow, no shorting
(overpricing corrects slowly; a long-only tilt harvests relative
underpricing), and a ±10% daily band that mechanically stretches large
repricings over multiple sessions (post-band-limit continuation).
Prior art in-house: H-001 (sector momentum) was rejected for breadth, not
mechanism — the pivot memo's core claim is that per-stock breadth makes
this the correctly-powered retest of the family.

## Research question / hypotheses

Does a long-only tilt toward trailing 12-1 winners within the investable
universe beat an equal-weighted investable benchmark net of retail costs,
out of sample?

- H0: net excess return of the momentum portfolio vs the EW-IRU benchmark
  is ≤ 0 (no exploitable cross-sectional momentum).
- H1: net excess > 0, robust across the pre-declared grid and OOS.

## Universe / data (frozen)

- IRU v2 members at each formation date (PIT, monthly recompute,
  rename-canonical). `iru_version = "v2"`.
- Data: equity_prices via `db.equity_prices_asof`, `min_confidence = 0.9`,
  **vintage = 2026-07-21** (`docs/DATA_FREEZE_2026-07-21.md`),
  `requires_coverage_gate = true`.
- Eligibility filter at formation (ex-ante): ≥120 valid close observations
  in the formation window AND a trade within the last 20 sessions (the
  IRU's own staleness rule; no additional discretion).

## Signal specification

- Formation: cumulative return from month-end t−12 to month-end t−1
  ("12-1": the most recent month is skipped — avoids short-term reversal
  and band-limited settling).
- Returns use raw closes (price-only; dividends are not in the panel —
  flagged limitation L1 below; markdown re-basings make price-only returns
  slightly UNDERSTATE winners' totals, a conservative bias for longs).
- Scores standardized cross-sectionally at each formation date.

## Portfolio construction

- **Base configuration (PRIMARY): long top 20 names by formation score,
  equal-weighted, quarterly rebalance, execution lag 1 trading day.**
- Long-only, fully invested. No leverage, no shorts.
- Liquidity: ADTV participation cap 10% (existing platform default),
  60-day ADTV from value_traded.
- Stability grid (6 cells + base): formation ∈ {6-1, 12-1} ×
  top_n ∈ {10, 20, 30}, rebalance fixed quarterly.

## Benchmark (ex-ante)

Equal-weighted portfolio of ALL IRU-eligible names, same quarterly
rebalance, same cost model (the investable null strategy). ASI reported
as context only, never the test benchmark. (Cap-weighted benchmark
becomes available only after the LIST2 market-cap layer validates — NOT
used here; changing benchmark = new hypothesis ID.)

## Costs / turnover / capacity

- Costs: platform cost schedule (retail, ~1.9%/side, 'assumed'
  confidence), the standard sweep over brokerage overrides in the grid is
  NOT used — single cost model, pre-declared.
- Expected turnover: ~30–40% of names replaced per quarter → one-way
  ~1.2–1.6×/yr → expected drag ~3–5%/yr. This is the binding hurdle and
  part of the claim: H1 asserts the effect survives it.
- Capacity: reported as the platform's full distribution at
  AUM ∈ {0.1bn, 1bn, 2bn NGN}; per charter, capacity limits cap AUM and
  never invalidate the signal.

## Windows

- Development: 2016-01-02 → 2024-12-31 (2015 reserved as formation
  warm-up; 2014 partial year unused).
- **Untouched OOS: 2025-01-02 → 2026-06-30** (`holdout_start=2025-01-02`;
  runner-enforced).
- Walk-forward regimes: pre_float (2016→2023-05), float_shock
  (2023-06→2024-12), OOS (2025-01→2026-06).

## Validation plan

Phase 4 unchanged: stability map (the 7 cells) → Holm/BH → seeded placebo
(100 iterations; within-date cross-sectional shuffle of scores — tests
selection skill at identical dates, costs, and construction) →
walk-forward over the 3 regimes → final OOS evaluation → IC memo.

## Confirmation requires ALL of

1. Placebo p ≤ 0.05 on the base configuration.
2. Base net excess vs EW-IRU > 0 in development AND in final OOS.
3. Plateau: ≥ 4 of 7 grid cells with positive net excess.
4. ≥ 1 cell significant under Benjamini–Hochberg at FDR 0.10.
5. No regime contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered.

## Rejection (any one suffices)

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates gross
excess · regime concentration > 80% · signal-quality failure condition.
If gross excess is positive but net is not, the verdict is REJECT as an
investable factor; the gross result is recorded in the Factor Registry as
knowledge (turnover-reduction successors need a new ID).

## Multiple-testing treatment

7 cells under BH within this hypothesis; the program-level ledger count
(hypotheses tested to date: 5 prior + this wave) is reported in the IC
memo per program rule #2.

## Expected Interaction with Existing Factors

- Family: **Momentum** (first per-stock entry; library currently empty).
- Expected correlations (priors, to be measured): moderate-to-high with
  any future industry-strength factor; mildly positive with liquidity
  (winners gain liquidity); low or negative with value (E/P) and
  low-volatility — the classic diversifying pair.
- Diversification: as the library's prospective first entry it defines the
  baseline; its role in construction is the cyclical return engine that a
  defensive factor (low-vol) would complement.
- Independence rationale: trend information is constructed purely from
  past relative returns; level-based (value) and risk-based (low-vol)
  sorts use disjoint inputs.

## Known limitations (pre-declared)

L1 price-only returns (no dividend reinvestment) — conservative for
winners; total-return retest becomes possible after the DOL dividend layer
lands (would be a new ID). L2 177 single-source close-only days
(documented in the freeze; ≤3% deviation risk on a subset). L3 retail
cost schedule is 'assumed' confidence. L4 rf = 0 placeholder affects
Sharpe labels, not excess-return verdicts.
