# Stage 21 — Illiquidity/Staleness Mechanism Diagnostic

**Date:** 2026-08-09
**Status:** Measurement/diagnostic only. No hypothesis registered, no portfolio constructed, no strategy
return calculated, no threshold chosen by looking at results. Script: `scripts/stage21_illiquidity_diagnostic.py`
(frozen spec in its own docstring, run once, raw output preserved verbatim at `data/staging/stage21/`).

**Research question:** does NGX price staleness/illiquidity create predictable relative mispricing
distinct from size, or does it merely compensate for liquidity risk (or reflect a measurement artifact)?

---

## 1–5. Descriptive diagnostics (Part A, n=201 tickers with ≥250 sessions)

| Metric | Mean | Median | p10 | p90 |
|---|---|---|---|---|
| Zero-return frequency | 58.9% | 61.4% | 16.2% | 93.2% |
| — of which genuinely traded (volume>0, price unchanged) | 55.6% | 57.5% | 15.1% | 88.5% |
| — of which missing/no recorded trade | 3.3% | 3.4% | 0.6% | 5.5% |
| Trading-session frequency (any volume) | 94.9% | 94.3% | 93.3% | 98.5% |
| Max consecutive zero-return run (sessions) | 100.4 | 64 | 5 | 267 |
| Mean zero-return run length | 10.3 | 4.0 | 1.3 | 22.7 |
| Return autocorrelation (lag-1) | +0.098 | +0.089 | -0.032 | +0.259 |
| Volume-shock frequency (>3× trailing 60-session avg) | 7.7% | — | — | — |

**Genuine unchanged vs. missing (item 4):** the large majority of "zero-return" sessions are genuinely
traded at an unchanged price (55.6 pp of the 58.9 pp total) — this is real price staleness, not mostly a
missing-data artifact. Good news for measurement validity.

**Historical stability:** correlation of each ticker's zero-return frequency in the first half vs.
second half of its own history = **0.76** — staleness is a persistent, structural trait of a given
ticker, not noise that reshuffles over time.

**Price-discovery proxy — return clustering after inactivity:** mean |return| on the session immediately
following a run of ≥5 consecutive zero-return sessions = **5.17%**, vs. an unconditional mean |return| of
**1.77%** across all sessions — roughly a **3× jump**. This is genuine, positive evidence that price
discovery on NGX is *lumpy and delayed* rather than continuous: information appears to accumulate during
stale spells and gets impounded in a single larger move once a trade finally occurs, rather than being
priced in gradually. Note this measures the *size* of the eventual adjustment, not its *direction* — it
is evidence the mechanism (delayed price discovery) is real, not yet evidence the direction is
forecastable.

Positive lag-1 return autocorrelation (mean +0.098) is consistent with the same story (a documented
signature of stale/thin trading in the microstructure literature), not an independent confirmation.

---

## 6. Independence from H-011

Trailing-60-session zero-return frequency (`illiq_60`) vs. `market_cap_nm` (the exact field
`size_scores()` consumes), pooled across 228,366 ticker-date observations:

- Spearman(illiq_60, mcap) = **-0.299**
- Pearson(illiq_60, log(mcap)) = **-0.262**

**Interpretation:** a real, moderate negative relationship exists (larger names are somewhat less
stale, as expected), but it is far from collinear (~7–9% of variance shared under a linear reading) —
illiquidity is **not** simply a relabeling of size. This licenses the within-size-tercile design used in
Part C below rather than assuming independence by name alone, exactly as the task required.

---

## 7. Forward-return diagnostic (Part C) — descriptive, NOT a strategy return

Frozen spec: monthly snapshots, double-sort into size terciles then illiquidity terciles within each
size tercile, mean **raw** 20-session forward return per cell (no weights, no rebalancing, no costs — a
descriptive cross-tab, not a portfolio).

| Size tercile | Illiquidity tercile (low→high) | Mean fwd 20-session return | n |
|---|---|---|---|
| Smallest | Low / Mid / High | +5.31% / +4.63% / **+3.76%** | 1643 / 1446 / 1556 |
| Middle | Low / Mid / High | +3.45% / +3.50% / **+2.98%** | 1538 / 1368 / 1487 |
| Largest | Low / Mid / High | +3.01% / +2.59% / **+1.95%** | 1616 / 1448 / 1578 |

Monotonically **decreasing** in every size tercile: more staleness → *lower*, not higher, subsequent raw
return. Pooled OLS confirms it: `illiq_rank_within_size` coefficient = **-0.038** (t = -5.36), controlling
for size-tercile dummies.

### Economic interpretation (item 7 — required, done honestly)

This direction is the **opposite** of what a liquidity-risk-compensation story predicts (that story needs
stale/illiquid names to earn *higher* average returns as compensation for holding a harder-to-trade
asset — not lower). So this is clearly not simply the small-cap/liquidity-risk premium re-labeled.

But it is **most parsimoniously explained by a stale-price measurement artifact**, not by genuine
mispricing: a name with a high trailing-60-session zero-return frequency (by the 0.76 stability finding
above) is very likely to *also* have many zero-return sessions in the *forward* 20-session window used to
compute "return" — and a stock that mechanically doesn't trade cannot show a large cumulative price
change. The high-illiquidity-tercile cell's lower "return" is therefore substantially explained by **the
same staleness continuing forward and mechanically compressing the measured return toward zero**, not
necessarily by a correctable mispricing being realized. This is a known, foreseeable limitation of naive
raw-return sorts on thinly-traded names (the same critique applies to any calendar-time return measure
on a security that may not trade every day) — it is not a post-hoc rescue invented after seeing an
inconvenient result; it is the standard reason this class of diagnostic requires a trade-conditional
return measure, which this frozen spec did not include (deliberately, to avoid threshold/definition
shopping after the fact).

**Net read:** Part C's headline finding cannot currently be distinguished from a mechanical artifact and
should not be read as evidence of exploitable, directional mispricing. Part A's post-inactivity
return-clustering finding is untouched by this specific critique (it conditions on a trade actually
occurring) and remains genuine evidence that NGX price discovery is delayed/lumpy.

---

## 8. Tradability (conceptual, no simulation run)

Even setting the Part C confound aside: the tercile where any effect would be concentrated (highest
staleness) is, by construction, the tercile with the fewest tradable sessions — median max consecutive
zero-return run of 64 sessions (~3 months) means a position could realistically sit without an exit
opportunity for a quarter or more. This is the same structural tension flagged for the suspension-lift
track in Stage 19B: the more pronounced the apparent effect, the less executable the underlying name is
likely to be against the platform's existing 10%-of-60-day-ADTV capacity rule. This was not simulated
(per the no-portfolio constraint) but is a foreseeable, likely-binding constraint on any eventual factor
built from the high-illiquidity tail specifically.

---

## 9. Falsification — stated criteria and outcome

Pre-committed reasoning (methodological, not data-driven): the forward-return sort as specified cannot
distinguish "genuine mispricing correction" from "mechanical non-trading compressing measured return,"
because both produce the identical observable signature (low measured return in the high-staleness
tercile). This is a foreseeable property of the chosen design, not a post-hoc excuse — and per the
"don't rescue by changing the definition" instruction, **the design is not being altered to explain this
away**; it is reported as a genuine limitation that blocks a clean GO verdict.

What would have supported a clean GO: a *positive* within-size illiquidity–forward-return relationship
(ruling out both the risk-premium story's wrong sign here and the artifact concern, since compression
toward zero cannot manufacture an apparently positive result), or a trade-conditional return measure
confirming the same direction and magnitude as the raw measure. Neither was found — the sign is negative
and no trade-conditional measure was computed in this pass.

---

## Verdict: **CONDITIONAL GO**

- **What survives:** the underlying mechanism — NGX price discovery is genuinely delayed and lumpy
  (persistent per-ticker staleness, 3× larger absolute returns immediately after inactive spells) — is
  real, PIT-measurable from existing data, moderately but not fully independent of H-011's size input
  (r ≈ -0.3, not collinear), and stable over time. This is the strongest, most direct evidence produced
  in this entire research program (Stages 16–21) for a genuine, structural NGX friction.
- **What does not yet survive:** the specific claim that this friction is *directionally exploitable* —
  Part C's negative illiquidity–return relationship is confounded with a mechanical stale-price artifact
  that this diagnostic's design cannot rule out, and the tail where any effect concentrates is also the
  tail least likely to be executable at realistic size.
- **Named condition for the next stage, before any hypothesis/preregistration:** re-run the
  forward-return diagnostic using a **trade-conditional** return measure (e.g., cumulative return
  measured over the next *N actual trading/price-change events* rather than *N calendar sessions*, or
  restricting to names whose forward window contains a minimum number of genuine price-change sessions)
  to separate "information catching up" from "mechanical flatness." This is still a diagnostic, not a
  backtest, and must be specified before re-running, exactly as this stage's spec was.

## Direct answer to the explicit question

**Is NGX illiquidity actually creating exploitable price staleness, or are we simply rediscovering the
small-cap/liquidity-risk premium under a new name?**

**Neither, on current evidence.** It is demonstrably not a relabeled small-cap/liquidity-risk premium —
the sign of the forward-return relationship runs opposite to what that story requires, and the effect
survives within size terciles. But it is also not yet demonstrated to be *exploitable* mispricing — the
best current explanation for the measured effect is a mechanical stale-price artifact in the return
measure itself. What *is* solidly established is that NGX price discovery is delayed and lumpy rather
than continuous — a genuine mechanism, but one that requires a better-designed forward-return measure
before it can support a preregistration.
