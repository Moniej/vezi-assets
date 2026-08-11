# Stage 21C — Drift-Only Market-Relative Diagnostic

**Date:** 2026-08-09
**Status:** Measurement/diagnostic only. No H-021, no portfolio, no strategy return, no optimization of
horizon/threshold/universe. T0 reopening jump discarded per the hard decision already made. Reuses
`MIN_RUN`/`HORIZONS` imported directly from Stage 21B's frozen script (zero redefinition). Cost model
reuses `costs.side_rates()` against the live `cost_schedule` table unmodified. Benchmark: NGXASI index
level series (`index_levels`, 2012–2026) — the platform's EW-IRU benchmark itself requires running
portfolio-construction machinery (`simulate()`/`benchmark_targets()`), which would blur the "no portfolio"
line, so a real, already-computed index series was used instead; disclosed, not a dodge. Script:
`scripts/stage21c_drift_only_market_relative.py`. Raw output preserved at `data/staging/stage21c/`.

**Question:** after discarding the untradeable reopening jump, is there enough independent post-reopening
drift left to plausibly overcome NGX execution friction?

---

## 1. Drift-only measurement — usable episodes

| Horizon (traded sessions after T0) | Episodes usable | Control usable |
|---|---|---|
| 3 | 8,255 | 7,081 |
| 5 | 8,245 | 7,081 |
| 10 | 8,223 | 7,081 |
| 20 | 8,177 | 7,080 |

Essentially the full Stage 21B episode set carries through (T0 itself is dropped from the horizon, not
the episode).

## 2. Market-relative comparison (all four horizons reported, none cherry-picked)

| k | n | Raw drift | Bench return | Excess drift (mean) | Excess drift (median) | Excess t-stat* | % positive raw drift | Control raw | Control excess | Episode − control excess |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 8,255 | +0.55% | +0.21% | +0.34% | **-0.02%** | 5.71 | 26.2% | +0.27% | +0.05% | +0.29% |
| 5 | 8,245 | +0.95% | +0.39% | +0.56% | **+0.03%** | 6.39 | 34.0% | +0.50% | -0.01% | +0.56% |
| 10 | 8,223 | +2.32% | +0.90% | +1.42% | **+0.10%** | 9.34 | 42.6% | +1.43% | +0.46% | +0.96% |
| 20 | 8,177 | +4.72% | +1.95% | +2.78% | **+0.20%** | 11.10 | 48.2% | +2.67% | +0.68% | +2.10% |

*t-stats use a naive i.i.d. assumption and are almost certainly overstated — many episodes share the same
ticker and overlapping calendar periods, so the effective independent sample size is well below 8,223.
Reported for completeness, not treated as a rigorous significance claim.

**Reading this honestly, the mean/median gap is the central finding.** Mean excess drift looks
substantial and "significant" by horizon 20 (+2.78%, t≈11). But the **median** excess drift is
essentially zero at every horizon (-0.02% to +0.20%), and only 42.6%–48.2% of episodes even have a
*positive* raw drift (never crossing 50%, at any horizon). A mean that is large and positive while the
median sits at zero and fewer than half the observations are positive is the signature of a **right-skewed
distribution driven by a small number of extreme episodes**, not a broad-based, typical, repeatable
effect. The market-relative adjustment correctly strips out general index movement (bench return grows
from +0.21% to +1.95% across horizons, confirming a real chunk of Stage 21B's raw positive drift was
just market beta, exactly the confound flagged there) — but what remains is dominated by tail episodes,
not a consistent typical-case edge.

## 3. Magnitude vs. direction (k=10, representative — all horizons already shown above)

- % episodes with positive drift: **42.6%** (less than half)
- Mean |drift|: 7.59% vs. mean signed drift: 2.32% — the dispersion (std 13.9%) dwarfs the mean.
- **Conclusion:** this is much closer to "statistically indistinguishable from noise / volatility
  clustering" for the typical episode than to "consistently directional." Magnitude predictability
  (something notable tends to happen) is weakly present; directional predictability (it tends to happen
  in a specific, exploitable direction) is not — a plurality-not-majority of episodes even go the
  "positive" way.

## 4. H-011 independence — and the deeper question

| Variable | Spearman(drift_10, ·) |
|---|---|
| market_cap_nm | +0.038 |
| trading_freq | -0.028 |
| zero_return_freq | +0.057 |
| run_length | -0.024 |

All negligible. This confirms the drift-only signal, to the extent it exists, is not mechanically encoded
by `size_scores()`'s market-cap input, nor by simple liquidity/duration proxies — H-011 does not already
capture it. But independence from H-011 was never the binding constraint here; §5 is.

## 5. Cost and capacity gate — decisive

Round-trip transaction cost from the platform's own `cost_schedule` (via `costs.side_rates()`,
unmodified): **3.79%** (1.90% buy + 1.90% sell, brokerage + SEC/NGX fees + CSCS + stamp duty + VAT).

| k | Mean excess drift | Round-trip cost | Survives (mean)? | Median excess drift | Survives (median)? |
|---|---|---|---|---|---|
| 3 | +0.34% | 3.79% | **NO** | -0.02% | **NO** |
| 5 | +0.56% | 3.79% | **NO** | +0.03% | **NO** |
| 10 | +1.42% | 3.79% | **NO** | +0.10% | **NO** |
| 20 | +2.78% | 3.79% | **NO** | +0.20% | **NO** |

**At every horizon tested — none selected after the fact — the gross excess drift fails to clear a
single round trip's transaction cost.** Even the most generous reading (the skew-inflated mean at the
longest horizon, +2.78%) falls short of +3.79%. The economically relevant median case isn't close: 0.02–
0.20% of "edge" against a 3.79% cost floor, before any allowance for the wider bid/ask-equivalent
slippage that thin, previously-stale names would realistically add on top of the schedule's stated rates.

Per the pre-committed rule: **if gross drift is smaller than realistic round-trip costs, the mechanism is
NO-GO regardless of statistical significance.** This condition is met at all four horizons.

## 6. Robustness splits (descriptive, not threshold-searched)

| Split | Bucket | Raw drift_10 | Excess drift_10 |
|---|---|---|---|
| Size | Small / Mid / Large | 2.99% / 2.66% / 2.56% | 1.89% / 1.71% / 1.20% |
| Activity | Less active / More active | 2.37% / 2.26% | 1.35% / 1.52% |
| Stale-run length | 5–9 / 10–19 / 20–49 / 50+ | 2.44% / 1.92% / 2.38% / 2.83% | 1.67% / 1.07% / 0.87% / 1.46% |

No split produces an excess-drift figure anywhere near the 3.79% cost floor — the largest cell (Small,
1.89% excess) is still under half the round-trip cost. Consistent with §5's conclusion across every
reasonable descriptive cut, not just the pooled figure.

## 7. Required decomposition

- **A — Genuine delayed information incorporation:** weakened relative to Stage 21B. The median
  episode shows ~zero market-relative drift; what Stage 21B read as mild continuation evidence is, once
  market-adjusted and viewed through the mean/median gap, more consistent with a skewed tail than a
  broad-based incorporation process.
- **B — Liquidity compensation:** not a good fit — a risk premium should show up as a consistent,
  majority-positive excess return; only 42.6–48.2% of episodes are even directionally positive.
- **C — Volatility clustering:** the best fit for the residual pattern — high dispersion (std 13.9% at
  k=10) relative to a near-zero median, with the mean pulled up by a skewed minority of large moves in
  both directions, is the classic signature of volatility clustering after an inactive spell, not
  directional drift.
- **D — Market-wide movement:** confirmed present and now correctly removed — bench return accounts for a
  meaningful share of Stage 21B's raw positive-drift reading (e.g. +1.95% of the +4.72% raw drift at
  k=20).
- **E — Data/measurement artifact:** plausible contributor to the mean/median divergence (a small number
  of episodes — possibly involving unusual filings, corporate actions, or data irregularities — can
  dominate a mean computed over thousands of episodes); not separately isolated in this pass, but
  consistent with what's observed.
- **F — Potential independent mispricing:** not supported. The one clean positive finding (near-zero
  correlation with size/liquidity/duration, §4) establishes that *if* something real were left, it would
  be independent of existing factors — but §5 shows there isn't enough of it to matter economically.

---

## Verdict: **NO-GO**

The cost/capacity gate is unambiguous and was checked at every pre-specified horizon, not the one that
looked best. Gross excess drift never clears a single round-trip transaction cost, the typical (median)
episode carries essentially no market-relative edge, and fewer than half of all episodes even move in the
"expected" direction. Per the standing instruction, this is not being rescued by adjusting the horizon,
threshold, universe, or cost assumptions — all were fixed in advance (imported directly from Stage 21B)
and the result is reported as found.

**This kills the entire staleness/illiquidity mechanism track**, closing the line of research opened in
Stage 20 and carried through Stages 21/21B: the underlying phenomenon (delayed, lumpy price discovery) is
real and reproducible (Stage 21B), but once isolated from the unexecutable reopening jump and measured
against the market and realistic NGX transaction costs, it does not constitute exploitable mispricing.

## Direct answer

**Once the untradeable reopening jump is discarded, is there enough independent post-reopening drift
left to plausibly overcome NGX execution friction? No.** The typical episode's market-relative drift is
close to zero; the positive mean is carried by a skewed minority of episodes rather than a systematic
effect; and even the most favorable horizon's mean figure falls short of a single round trip's cost. The
mechanism is killed, not conditionally — no further rescue via redefinition is warranted.
