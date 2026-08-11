# Stage 26 — Statistical-Independence and Clustering Diagnostic (Insider-PURCHASE, k=20)

**Date:** 2026-08-09
**Status:** Mechanism-validation diagnostic only. No hypothesis, no H-024/H-025/H-026, no factor, no
backtest. Frozen dataset and methodology: Stage 24/25's PURCHASE, k=20 event set
(`data/staging/stage24/event_returns_with_k3.csv`), unmodified signal definition, PIT rule, benchmark,
cost floor (3.79%), and aggregation rules. Script: `scripts/stage26_clustering_diagnostic.py`. Raw
output preserved at `data/staging/stage26/ticker_cluster_means.csv`.

**Core question:** are these 53 observations genuinely independent enough to support a repeatable k≈20
effect, or did repeated issuers/insiders create the illusion of sample size?

---

## 1. Dependence structure

| Dimension | Count |
|---|---|
| Unique tickers | 10 |
| Unique insiders | 43 |
| Insiders appearing more than once | 9 / 43 |
| Insider × ticker combinations | 43 (9 with >1 observation) |
| Largest ticker cluster | UCAP, n=20 (38% of the sample) |
| Largest same-disclosure-date cluster | **8 events, all on 2020-09-23** |

**A genuine same-information-episode cluster was found and is worth stating plainly**: all 8 events
dated 2020-09-23 are UBA filings by eight different members of the Elumelu family (Awele, Nneka,
Ogechukwu, Ogochukwu, Onyinye, Toby Onyemaechi, Tony Onyekachukwu, Ugochukwu Elumelu), and **all eight
carry the identical excess_ret_20 value (+5.1458%)** — because they share the same ticker and the same
eligible-from/end dates, they are not eight independent informational draws, they are eight insiders
reacting to (or party to) one underlying corporate/family transaction. This is exactly the kind of
non-independence the task asked to identify explicitly, and it sits entirely inside the UBA ticker
cluster — which is precisely why ticker-level clustering (§2) is the right unit of analysis here, not an
overly conservative choice.

## 2. Cluster-robust inference

| Method | Point est. | SE | t | df / G | p | 95% CI |
|---|---|---|---|---|---|---|
| Naive (i.i.d.) | +5.74% | 1.45% | 3.97 | df=52 | 0.0002 | — |
| **Ticker-clustered** | +5.74% | **1.19%** | 4.84 | G=10 | 0.0009 | **[+3.06%, +8.43%]** |
| Insider-clustered | +5.74% | 1.18% | 4.85 | G=43 | 0.0000 | [+3.35%, +8.13%] |
| Two-way (ticker × insider-ticker) | +5.74% | 1.13% | 5.10 | min(G)=10 | 0.0006 | — |

Insider-clustering is, as expected, close to the naive result — 34/43 insiders are singleton clusters by
construction, so this check is not materially informative on its own (disclosed, not hidden). **Ticker
clustering is the meaningful test here**, given §1's finding, and the cluster-robust SE is *smaller* than
naive, not larger (driven by low within-cluster dispersion in several small clusters, e.g. UBA's eight
identical values) — an outcome that can happen with CR1 estimators and small G, not an error.

**G=10 ticker clusters is below the conventional G≥30–40 comfort threshold** for trusting cluster-robust
asymptotics at face value — stated explicitly, not glossed over. An **exact randomization test** was run
as the more defensible alternative: enumerate all 2¹⁰=1,024 sign-flip patterns on the 10 ticker-level
cluster means and compute the exact two-sided p-value under a symmetric-around-zero null.

**Exact permutation p-value: 0.0156.** Weaker than the parametric cluster-robust p-values (as expected —
this is the more conservative, small-G-appropriate test), but still comfortably below conventional
significance thresholds.

## 3. Cluster-aware equal-weighted aggregation

Collapsing to one observation per ticker (mean excess return within each of the 10 tickers, then
averaging across tickers with **equal weight regardless of n**) — the single most direct test of whether
UCAP's 20 observations are "masquerading" as more independent evidence than they are:

| Ticker | n | Mean excess (k=20) |
|---|---|---|
| UCAP | 20 | +7.96% |
| UBN | 1 | +24.08% |
| DANGCEM | 2 | +8.77% |
| SEPLAT | 6 | +5.94% |
| AIICO | 1 | -2.38% |
| FLOURMILL | 2 | +5.64% |
| UBA | 8 | +5.15% |
| FCMB | 5 | +1.55% |
| NB | 5 | +3.20% |
| AIRTELAFRI | 3 | -1.95% |

**Equal-weighted mean-of-means: +5.79%** — essentially identical to the observation-weighted mean
(+5.74%), and comfortably clears the 3.79% cost floor. **This is the strongest single piece of evidence
against the "illusion of sample size" concern**: if UCAP's 20 observations were inflating the apparent
effect by sheer count, forcing equal weight per ticker would have moved the result substantially. It did
not.

## 4. Distributional robustness

| Metric | Value |
|---|---|
| Mean | +5.74% |
| Median | +5.15% |
| Winsorized mean (5%/95%, Stage 24's frozen treatment) | +5.28% |
| % positive | 77.4% |
| Top-1 observation's share of the mean | 12.7% |
| Top-3 observations' share of the mean | 33.1% |

No single observation or small handful dominates at the full-sample level (contrast with Stage 25's
finding that the *UCAP-excluded subsample*'s mean was much more fragile to its top-2 observations — that
finding stands for that specific subsample and is not contradicted here; the full 53-observation set is
better distributed).

## 5. Horizon check — observation-weighted vs. equal-ticker-weighted

| k | n | Obs-weighted mean | Equal-ticker-weighted mean |
|---|---|---|---|
| 3 | 53 | +0.50% | -0.39% |
| 5 | 53 | +1.23% | +1.03% |
| 10 | 53 | +1.90% | +2.20% |
| **20** | 53 | **+5.74%** | **+5.79%** |
| 40 | 52 | +2.80% | +1.95% |
| 60 | 52 | +1.68% | -0.49% |

**Both weighting schemes peak sharply at k=20 and agree closely there**, while diverging more at the
edges (k=3 and k=60 flip sign under equal-ticker weighting). This confirms the k=20 concentration is a
genuine feature of the data, not an artifact of how observations are weighted.

## 6. OCR gap — quantified, not assumed away

| | Count | % of original 163 |
|---|---|---|
| Original filings | 163 | 100% |
| Genuine (native-text) transactions | 109 | 66.9% |
| Unusable/ambiguous (includes 40 scanned-image/OCR-blocked) | 48 | 29.4% |
| — of which confirmed scanned-image PDFs (Stage 23) | 40 | **24.5%** |

The tickers, directions, and dates of these 40 filings are **unknown** without OCR, which was not run in
this stage (no separate authorization exists). **Their distribution cannot be assumed random.** If they
are concentrated in a systematically different type of filer (e.g. smaller issuers still using
paper-native disclosure workflows, or a specific compliance officer/law firm template that happens to be
scan-only), the true concentration profile — and potentially the true effect size — could shift in either
direction. This is reported as an open, material **DATA GAP**, not treated as benign by default.

---

## Hard interpretation

**A — Genuine distributed mechanism: supported.** The effect survives ticker-clustered inference
(t=4.84, p=0.0009), survives the more conservative exact small-G permutation test (p=0.0156), and —
decisively — survives being recomputed with equal weight per ticker cluster (+5.79% vs. +5.74%
observation-weighted, no material change). The k=20 horizon-specificity holds under both weighting
schemes. No single cluster (ticker, insider, or same-date information episode) explains the result; the
one clear same-episode cluster found (UBA, 2020-09-23) is correctly absorbed by ticker-level clustering
and does not distort the equal-weighted result.

**B — Concentration/dependence artifact: not supported.** This was the leading concern after Stage 25,
and this stage's direct tests (equal-weighting, cluster-robust SEs, exact permutation) do not bear it
out. The apparent sample size was not, in fact, an illusion at the ticker-cluster level.

**C — Data uncertainty: partially applies, narrowly.** Not because the clustering/independence question
is unresolved — it isn't, per A — but because the OCR gap (§6) means the *complete* corpus's true
concentration and effect profile remain genuinely unknown. This is a narrower, more specific uncertainty
than a full "cannot judge" verdict.

---

## Verdict: **CONDITIONAL GO**

Not **ADVANCE TO PREREGISTRATION REVIEW**, despite the clustering/independence analysis coming back
clean: the OCR gap is real, material (24.5% of the original corpus), and — per instruction — not to be
assumed random or resolved in this stage. That single, already-named, pre-existing limitation is what
keeps this from full advancement, not any new concern raised here.

Not **NO-GO**: clustering did not destroy the effect — if anything, this is the strongest evidence this
entire mechanism-discovery program has produced that the insider-PURCHASE, k≈20 signal reflects a
genuine, distributed pattern across issuers rather than a statistical illusion created by a few dominant
tickers or repeat filers.

Not **DATA GAP** as the primary verdict: inference *could* be responsibly performed here (economic
significance and dependence-robust statistical significance are both established), and was. The data gap
that remains is bounded and specifically named (§6), not a blanket inability to judge.

**Net progression across Stages 24→25→26**: the concentration and dependence concerns that motivated
Stages 25 and 26 have now been substantially addressed — UCAP's exclusion doesn't collapse the effect
(Stage 25), no other single ticker is load-bearing (Stage 25's sweep), and equal-weighting by ticker
cluster reproduces the observation-weighted result almost exactly (this stage). **The remaining blocker
to advancing this track is the OCR gap alone**, which is a data-completeness problem, not a
mechanism-validity problem. This is still not alpha, and still not a hypothesis — but it is the cleanest,
most thoroughly stress-tested finding in the program to date.
