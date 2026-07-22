# Pre-Registration — H-011: Size (family: Size, new family)

*Drafted 2026-07-22, BEFORE any H-011 experiment run. Executable form:
`configs/h011_size.toml`. First entry in the Size family. Changes after
first results = new hypothesis ID.*

## Economic rationale and market intuition

The classic size premium's most defensible explanation on a market like
NGX is compensation for bearing capacity/liquidity constraints —
compensation for a friction, not a mispricing. Every prior hypothesis's
capacity report on this platform has shown 90%+ of trade legs rejected
at ₦1bn AUM; a size tilt deliberately selects the names where that
friction binds hardest, so if a premium exists at all, this is the
cleanest place on NGX to look for it. This is explicitly NOT a
"undervalued small companies get discovered" narrative claim — it is a
friction-compensation claim, and the prereg is written to test that
specific version.

## Research question / hypotheses

Does a long-only tilt toward the smallest-market-cap names within the
investable universe beat the equal-weighted-IRU investable benchmark,
net of retail costs, out of sample?

- H0: net excess of the small-cap portfolio vs EW-IRU is ≤ 0.
- H1: net excess > 0, robust across grid and OOS.

## Universe / data (frozen)

- IRU v2 members at each formation date (PIT, rename-canonical).
  `iru_version = "v2"`.
- Data: `equity_prices_asof`, `min_confidence = 0.9`,
  **vintage = 2026-07-21**, `requires_coverage_gate = true`.
- Market cap: `data/reference/market_cap_panel.csv` (validated
  2026-07-22, 328,023 rows, 0.39% implied-share-count jump rate).
  **Full-issue cap, NOT float-adjusted** — no shares-outstanding/
  free-float dataset exists on this platform yet. This is a stated
  construct-validity limitation, not an oversight: full-issue cap could
  proxy for cross-holding/ownership structure rather than genuine
  tradeable-float scarcity. A float-adjusted successor is backlog item
  E12, gated on a future shares-outstanding harvest.
- Eligibility at formation: ≥120 valid observations in the trailing
  12-month window (same discipline as every prior xs_* hypothesis), plus
  a valid market-cap observation at the formation date (implied-share-
  count forward-filled from the LIST2-derived panel onto the dense close
  panel — see `backtest_xs.load_market_cap_panel` docstring for exactly
  how, and why that method was chosen over naively freezing the cap
  level).

## Signal specification

Score = negative standardized market cap at the formation date (smaller
cap → higher score, standard SMB convention). Cross-sectionally
standardized at each formation date. No lookback window is needed for
the signal itself (cap is observed, not a trailing statistic) — the
12-month window referenced above is solely the ELIGIBILITY filter, same
role it plays in every prior hypothesis.

## Portfolio construction

- **Base configuration (PRIMARY): long the smallest 20 names by market
  cap within the IRU, equal-weighted, quarterly rebalance, execution lag
  1 trading day.**
- Long-only, fully invested, no leverage, no shorts.
- Liquidity: ADTV participation cap 10%, 60-day ADTV (platform default).
- Stability grid (6 cells): rebalance ∈ {quarterly, semiannual} ×
  top_n ∈ {15, 20, 30}.

## Benchmark (ex-ante) — identical to every prior per-stock hypothesis

Equal-weighted IRU portfolio, quarterly rebalance, identical cost model.

## Costs / turnover / capacity — the central, honestly-stated risk

**Turnover is UNMEASURED on real data as of this writing** (the
synthetic rehearsal, `scripts/rehearse_xs_size.py`, validated the
SELECTION LOGIC and placebo behavior only, not real-data turnover). H-008
already taught this platform not to assert rank-stickiness without
measuring it — the same discipline applies here: no turnover claim is
made in advance beyond "will be measured and reported honestly."
**Capacity is EXPECTED to be the worst of any hypothesis tested on this
platform, BY THE FACTOR'S OWN ECONOMIC LOGIC** — it deliberately selects
the most capacity-constrained names in the universe (that constraint IS
the proposed source of the premium, per the Economic Rationale section).
This is disclosed as part of the hypothesis's own claim, not discovered
after the fact, and per platform governance a capacity finding is
tracked SEPARATELY from the signal-quality verdict (`failure_conditions`
splits `capacity_below_minimum` [scalability] from
`cost_drag_eliminates_excess` [signal_quality] — a severe capacity
constraint does not by itself reject the signal).

## Windows — identical to every prior per-stock hypothesis

Development 2016-01-02 → 2024-12-31. **Untouched OOS: 2025-01-02 →
2026-06-30.** Same three regimes (pre_float / float_shock / oos_2025_26).

## Validation plan

Phase 4 unchanged: stability map (6 cells) → Holm/BH → seeded placebo
(100 iterations; fixed persistent ticker relabeling — the same
persistence-preserving design validated for xs_rank/xs_vol, reused
unchanged since xs_size produces the identical {formation_date: score}
structure) → walk-forward → final OOS → IC memo.

## Confirmation requires ALL of

1. Placebo p ≤ 0.05 on the base configuration.
2. Base net excess vs EW-IRU > 0 in development AND final OOS.
3. Plateau: ≥ 4 of 6 grid cells with positive net excess.
4. ≥ 1 cell significant under Benjamini–Hochberg at FDR 0.10.
5. No regime contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered (capacity findings
   evaluated separately, per the Costs section above).

## Rejection (any one suffices)

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates gross
excess · regime concentration > 80% · signal-quality failure condition.
A severe `capacity_below_minimum` finding ALONE does not constitute
rejection — per governance, it is recorded as a scalability finding
(bounding deployable AUM) separate from whether the signal is real.

## Multiple-testing treatment

6 cells under BH within this hypothesis. Program-level ledger count (11
hypotheses through this wave) reported in the IC memo. H-010 and H-011
are this wave's only two active hypotheses.

## Expected Interaction with Existing Factors

- Family: **Size** — first entry in this family; the library is
  currently empty (0/9 validated).
- Expected correlation with H-010 (Momentum, this wave's other
  candidate): LOW — disjoint construction inputs (trailing return vs.
  a cap level), though small-cap names may mechanically show HIGHER
  momentum volatility, a second-order effect to check, not assume, once
  both hypotheses have results.
- Expected correlation with liquidity/ADTV-based measures: HIGH by
  construction (small cap and illiquidity are strongly related on NGX) —
  if a future Liquidity hypothesis is proposed, its Expected Interaction
  section must explicitly address this overlap rather than claim
  independence from Size.
- Diversification: if validated, this would give the library its first
  entry whose economic story is EXPLICITLY about market friction/
  capacity rather than information or trend — valuable regardless of
  verdict as the first candidate input to a future Risk Engine (size is
  a standard risk-model factor even independent of whether it earns a
  premium — see `docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md` Phase 6).
- Portfolio construction value if validated: a genuinely capacity-
  constrained sleeve — any future portfolio combining this with other
  factors must size it conservatively relative to its OWN measured
  capacity, not treated as freely scalable like a large-cap tilt would be.
- Independence rationale: input is cross-sectional market
  capitalization, structurally orthogonal to trailing return (momentum),
  realized volatility (low-vol, rejected), and discrete-event reactions
  (PEAD, rejected) — no shared construction input with any hypothesis
  tested so far, EXCEPT the disclosed liquidity/ADTV overlap above.

## Known limitations (pre-declared)

L1 full-issue, not float-adjusted, market cap (construct-validity risk,
see Universe/data section). L2 price-only returns (no dividend
reinvestment). L3 177 single-source close-only days in the panel. L4
retail cost schedule 'assumed' confidence. L5 rf = 0 placeholder. L6
turnover and capacity are UNMEASURED on real data until this run — both
are the run's own measurement objective, not a pre-asserted property.
