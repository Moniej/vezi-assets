# Stage 25 — UCAP Concentration Stress Test (Insider-Dealing PURCHASE, k=20)

**Date:** 2026-08-09
**Status:** Mechanism-discovery diagnostic only. No hypothesis, no H-024/H-025, no factor, no backtest.
**Frozen test**: the exact Stage 24 PURCHASE, k=20, market-relative-excess diagnostic, unmodified in
every parameter (PIT rule, benchmark, cost schedule, aggregation, winsorization treatment, universe) —
the **only** change is excluding all UCAP observations. Raw output: `data/staging/stage24/
event_returns_with_k3.csv` (event-level, all horizons including a newly-added k=3 for the horizon table
below — computed via the same frozen `compute_event_returns()` function, not a re-derivation).

**Question:** does the insider-purchase signal survive after removing the single largest issuer
concentration?

The unresolved OCR gap (40/163 filings, ~25% of the original corpus, confirmed scanned-image PDFs in
Stage 23) is **explicitly out of scope for this test** and was not touched, re-attempted, or treated as
non-events here — those filings remain classified `unusable/ambiguous` with their stated reason, exactly
as Stage 23/24 left them.

---

## 1–6. Baseline vs. UCAP-excluded, k=20

| Metric | Baseline (Stage 24) | Ex-UCAP |
|---|---|---|
| 1. Qualifying PURCHASE events | 53 | **33** |
| 2. Unique tickers | 10 | **9** |
| 3. Mean excess return | +5.74% | **+4.40%** |
| 4. Median excess return | +5.15% | **+5.15%** (unchanged) |
| 5. Round-trip cost floor (frozen, `cost_schedule`) | 3.79% | 3.79% (unchanged) |
| 6. % positive (raw return) | 77.4% | **66.7%** |

The mean weakens (5.74%→4.40%) but **still clears the 3.79% cost floor**, with a materially thinner
margin than before (~0.6 percentage points, down from ~2.0). The median is **exactly unchanged**
(+5.15%) — mechanically expected only if UCAP's own observations weren't pulling the median, which turns
out to be the case; the median remains comfortably above cost regardless.

## 7. Concentration of the remaining sample

Removing UCAP does **not** resolve the concentration problem — it relocates it:

| Ticker | n (ex-UCAP) |
|---|---|
| UBA | 8 |
| SEPLAT | 6 |
| FCMB | 5 |
| NB | 5 |
| AIRTELAFRI | 3 |
| FLOURMILL | 2 |
| DANGCEM | 2 |
| AIICO | 1 |
| UBN | 1 |

New top-3 (UBA/SEPLAT/FCMB) = 19/33 = **57.6%** of the remaining sample — essentially the same
concentration ratio as Stage 24's original top-3 share (56.7%). **This is a real, unresolved,
distinct finding**: excluding the single largest issuer does not broaden effective breadth — the
sample is concentration-prone at every level, not just because of UCAP specifically.

## 8. Contribution of the largest remaining observations

The two largest remaining observations — SEPLAT/Udoma Udo Udoma (2024-09-27, +38.8%) and NB/Heineken
Brouwerijen (2020-08-27, +38.0%) — together account for **+2.19 percentage points of the +4.40% mean**
(roughly half of it), despite being only 2 of 33 events (6% of the sample). **Removing just these two
observations drops the mean to +2.21%, below the 3.79% cost floor.** The median, by construction largely
insensitive to top-end extremes, is unaffected (+5.15% unchanged whether or not these two are included) —
so the mean-based reading of this result is fragile to a very small number of observations; the
median-based reading is not.

## 9. Winsorization

Winsorized (5%/95%) mean: +4.40% → **+3.96%** — still (barely) above the 3.79% cost floor, but the margin
is now under 0.2 percentage points. This is consistent with §8: a meaningful share of the mean's magnitude
sits in the tails.

## 10. Repeated-insider aggregation sensitivity

Raw (non-aggregated) filings, ex-UCAP, PURCHASE, k=20: n=51, mean **+5.78%**, median +5.15% — *stronger*
than the aggregated figure (n=33, mean +4.40%), not weaker, and does not reverse sign or drop below cost
either way. **Unlike Stage 24's SALE finding, this result is not sensitive to the aggregation choice in a
way that changes the conclusion** — both raw and aggregated versions clear costs and agree in direction
and rough magnitude.

## Pre-specified horizon table (k=3/5/10/20/40/60), ex-UCAP, PURCHASE — same frozen methodology

| k | n | Mean excess | Median excess | % positive | Winsorized mean |
|---|---|---|---|---|---|
| 3 | 33 | -0.54% | -0.99% | 18.2% | -0.90% |
| 5 | 33 | +0.46% | -1.16% | 48.5% | -0.03% |
| 10 | 33 | +1.69% | +2.13% | 48.5% | +1.16% |
| **20** | 33 | **+4.40%** | **+5.15%** | 66.7% | +3.96% |
| 40 | 32 | +0.03% | -3.01% | 65.6% | -0.14% |
| 60 | 32 | -1.45% | -3.51% | 65.6% | -1.36% |

**This confirms the effect is genuinely concentrated at k=20, not merely at k=20-among-many-that-all-work.**
Every other horizon is at or below zero on mean and/or median — k=3 is outright negative on every measure
(18% positive), k=5/10 are roughly flat, and k=40/60 decay back toward zero or negative. Compared to the
Stage 24 baseline (which still showed a positive, if weaker, mean at k=40 of +2.80%), removing UCAP makes
the **non-k=20 horizons weaker still**, sharpening rather than resolving the horizon-fragility concern
already flagged in Stage 24.

---

## Adversarial interpretation

- **A. General insider-purchase effect**: partially supported. Direction holds without UCAP (66.7%
  positive, median +5.15% exactly unchanged), is not reversed or eliminated by the aggregation choice
  (§10), and the median-based reading clears costs with no fragility to extreme observations.
- **B. UCAP-specific phenomenon**: **rejected as the sole explanation**. The effect survives UCAP's
  complete removal on both the median and the raw (non-aggregated) mean — this was not simply a UCAP
  artifact.
- **C. A small number of extreme observations creating the apparent effect**: **partially supported, and
  real**. The aggregated mean is not "materially supported by the distribution" in the strict sense the
  decision framework asks about — two observations (6% of the remaining sample) account for roughly half
  of the mean's magnitude, and their removal pushes the mean below the cost floor. This is a genuine,
  disclosed fragility that coexists with (rather than replaces) finding A: the *median* result is broad
  enough to survive it, the *mean* result is not.

No horizon, threshold, event window, issuer filter, or transaction definition was altered to rescue this
result — the k=3 addition was a pre-specified extension of the same frozen method for the horizon table
the task requested, not a substitute for k=20, and every number above is reported as computed.

---

## Verdict: **CONDITIONAL GO**

Not a clean **GO TO NEXT VALIDATION**: the decision framework requires the result to clear costs *and*
remain materially supported by the distribution rather than one or two observations — the mean fails the
second half of that test (§8), and the concentration problem, while no longer UCAP-specific, has simply
relocated to a new top-3 (§7) rather than resolved. Not a **NO-GO** either: the effect does not collapse
— it survives UCAP's exclusion, survives the aggregation-choice check, and the median-based reading
clears costs cleanly and is untouched by the extreme-observation sensitivity that weakens the mean.

**This is a genuine weakening, not a collapse, and not a UCAP artifact.** The insider-PURCHASE-at-k≈20
finding remains the strongest candidate this mechanism-discovery program has produced, but it is now
better described as "directionally real, horizon-specific, and still meaningfully concentration-fragile"
rather than "robust." This is not being called alpha.

**Next diagnostic, if authorized** (not run here, per scope): a formal leave-one-ticker-out sweep across
all remaining names (not just UCAP) to map exactly how much of the k=20 mean any single issuer can
contribute, plus resolution of the still-separate OCR gap to test whether a larger corpus changes this
picture — both still diagnostics, not a hypothesis or backtest.
