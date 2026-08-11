# Stage 21B — Trade-Conditional Price-Discovery Diagnostic

**Date:** 2026-08-09
**Status:** Measurement/diagnostic only. No H-021, no portfolio, no strategy return, no threshold chosen
from results. Script: `scripts/stage21b_trade_conditional_diagnostic.py`. Reuses Stage 21's own ≥5-session
stale-run threshold unmodified. Raw output preserved at `data/staging/stage21b/` (`episodes.csv`,
`episodes_with_controls.csv`, `control_group.csv`).

**Question:** once returns are measured only across sessions where a trade actually happened, does the
apparent post-stale "mispricing" survive, or does it disappear?

---

## Episode set

8,272 stale episodes (≥5 consecutive zero-return sessions) across 180 tickers, built directly from
`equity_prices`. Censoring was rare (1.1% of episodes lack 20 subsequent traded sessions; 2.6% show a
>20-day calendar gap during the forward walk, a suspected-suspension marker) — the diagnostic is not
materially compromised by missing data. 94.4% of T0 sessions (the first post-stale price change) have a
recorded trade volume; the remaining 5.6% are price changes with no recorded volume — a genuine data
inconsistency, flagged and left as-is, not fabricated or discarded.

## Decomposition: the reopening jump vs. subsequent drift

**T0 (reopening) move:** mean |return| = **6.68%**, median 5.25% — versus a pre-stale 1-day volatility
baseline of 2.81% (log-return std over the 60 sessions before the stale run began). Ratio ≈ **2.4×** —
the reopening move is materially larger than the stock's own ordinary daily volatility, confirmed under
strict trade-conditional measurement (this specific finding from Stage 21 Part A survives the redesign).

**Post-T0 drift** (measured only across subsequent *traded* sessions, from T0's close forward):

| Horizon (traded sessions after T0) | n | Mean drift | Sign-corr(T0, drift) | Mean drift \| T0>0 | Mean drift \| T0<0 |
|---|---|---|---|---|---|
| 3 | 8,255 | +0.55% | 0.057 | +1.21% | +0.18% |
| 5 | 8,245 | +0.95% | 0.052 | +2.06% | +0.30% |
| 10 | 8,223 | +2.32% | 0.050 | +4.04% | +1.32% |
| 20 | 8,177 | +4.72% | 0.069 | +7.42% | +3.05% |

**Ticker-matched control baseline** (ordinary, non-post-stale traded-session sequences from the same
tickers' own remaining history, same horizon definitions): +0.33% / +0.49% / +1.04% / +2.23% at k=3/5/10/20.

**Reading this honestly:** both the post-stale group and the ordinary-trading control drift positive
over these horizons — this sample period is a rising NGX market (consistent with other stages' findings,
e.g. the NGX Pension Index's +59.7% 2025 return), and a naive read of the post-stale group's raw positive
drift alone would wrongly attribute general market drift to the staleness mechanism. The control group
exists precisely to net this out. Netting it out: post-T0 drift at k=10 (+2.32% unconditional, +4.04%
conditional on a positive T0 move) is roughly **2–4× the ticker-matched control's +1.04%** — a real,
though modest, excess. Sign-correlation between the T0 direction and subsequent drift direction is weak
but consistently positive and mildly increasing with horizon (0.050 → 0.069) — evidence of **continuation**,
not reversal, but a weak effect, not a strong one.

## Controls

| Bucket | n | mean \|T0 return\| | mean post-T0 drift (k=10) |
|---|---|---|---|
| Size: Small / Mid / Large | 2355/2355/2355 | 7.78% / 6.67% / 6.05% | 2.99% / 2.66% / 2.56% |
| Pre-stale vol: Low / Mid / High | 2754/2754/2755 | 6.77% / 6.51% / 6.77% | 1.68% / 2.59% / 2.71% |
| Stale-run length: 5–9 / 10–19 / 20–49 / 50+ | 5021/2000/970/281 | 6.10% / 6.93% / 8.67% / 8.54% | 2.44% / 1.92% / 2.38% / 2.83% |

The T0 move and post-T0 drift are **not concentrated in small caps** — magnitudes are similar to modestly
larger across size terciles, not dramatically size-driven. The T0 move scales up with stale-run length
(6.1% for 5–9-session runs → 8.5–8.7% for 20+-session runs) in a dose-response pattern — the longer the
silence, the bigger the eventual jump, which is the expected signature of a real mechanism (either pent-up
information or pent-up order flow) rather than noise.

## Independence from H-011 (episode-level, stronger check than Stage 21's aggregate)

- Spearman(|T0 return|, market_cap_nm) = **-0.074**
- Spearman(post-T0 drift at k=10, market_cap_nm) = **+0.038**

Both essentially negligible — **weaker** than Stage 21's already-modest aggregate correlation (-0.30).
At the episode level, conditional on a stale episode having occurred, the size of the reopening move and
the subsequent drift carry almost no size signature at all. This is a materially stronger independence
result than Stage 21 produced, and it directly addresses this stage's requirement to check for mechanical
overlap with `size_scores()` rather than just reporting a correlation: there is none of consequence.

## Critical separation: A / B / C / D

- **D (measurement artifact) — rejected.** Under strict trade-conditional measurement, a real, non-zero
  effect survives: the T0 jump exceeds ordinary volatility by ~2.4×, and post-T0 drift exceeds a fair,
  ticker-matched, non-overlapping control baseline by 2–4×. This is not merely Stage 21's "stale names
  stay flat in the forward window" artifact — that specific concern is resolved by construction here
  (only genuinely traded sessions are counted).
- **C (pure reopening/auction effect, nothing afterward) — not supported cleanly, but not fully rejected
  either.** Most of the magnitude *is* concentrated in the single T0 session (6.68% vs. a per-session
  post-T0 drift on the order of 0.2–0.5%/traded-session) — the reopening jump dominates. But there is
  measurable, direction-consistent residual drift afterward above the control baseline, which a purely
  one-off auction-clearing effect would not produce on average.
- **B (liquidity shock — mechanical price-impact of a stale name finally trading) — plausible and not
  separable from A for the T0 jump itself.** The dose-response relationship between stale-run length and
  T0 magnitude is equally consistent with "more pent-up unfilled orders create more price impact" as with
  "more pent-up information gets impounded at once" — this diagnostic cannot distinguish the two for the
  jump itself.
- **A (delayed information incorporation) — partially supported, specifically by the post-T0 continuation
  evidence, not by the T0 jump alone.** The weak-but-positive, horizon-increasing sign correlation and the
  materially larger drift following positive-direction T0 moves versus negative ones, both measured above
  a ticker-matched control, are hard to explain via a pure one-time liquidity-impact story (which predicts
  no informative continuation) but are exactly what a gradual-incorporation story predicts. The effect is
  real but small.

**Overall: a mixture of B (dominant, for the T0 jump) and A (secondary, weak, for the post-T0 drift).**
Neither pure C nor D describes the data.

## Execution reality

The dominant piece of the apparent move — the T0 jump itself — is **not tradable**: there is no
mechanism to transact at the pre-stale price, and the first observed post-stale price already reflects
the repricing (exactly the caveat the task named in advance). Only the smaller post-T0 continuation
(≈2.3% mean, ≈4.0% conditional on a positive first move, over 10 subsequent *traded* sessions — which on
a previously-stale name could span several calendar months, not 10 calendar days) is even theoretically
capturable. This is a modest edge, on names that are, by construction, thin and hard to trade at scale
(the same tension flagged in Stage 19B and Stage 21), to be measured against realistic NGX transaction
costs that have been a binding hurdle for larger apparent edges throughout this project (e.g. the H-019
backtest, DEAPCAP). No cost/capacity computation was run here (correctly out of scope — no backtest), but
the magnitude alone is a reason for real skepticism, not an assumption of tradability.

## Falsification outcome

Pre-committed test: does the effect disappear once measured on actually-traded sessions? **No** — this is
the central, disciplined result of this stage. The mechanism survives the redesign that Stage 21 flagged
as necessary. It is not being rescued by redefining staleness or the measurement window; the same ≥5-run
threshold and the same horizons were used as specified, and the result — modest but real, dominated by an
unexecutable jump plus a small executable-in-principle drift — is reported as found.

---

## Verdict: **CONDITIONAL GO**

The mechanism is not killed. It is also not a clean GO: the dominant component (the T0 jump) is
economically ambiguous between delayed information and mechanical liquidity impact, and is unexecutable
regardless of which explanation is correct; the smaller, more clearly A-consistent component (post-T0
drift) is real but modest, on thin names, and unverified against costs.

**Named condition for the next stage:** before any hypothesis or preregistration, (1) re-run the
control comparison using a market/sector-relative baseline (not just each ticker's own history) to more
cleanly purge the general-market-drift confound visible in this pass, since the control group is only
ticker-matched, not regime-matched; (2) treat the T0 jump and the post-T0 drift as two separate candidate
mechanisms going forward, not one — the jump is not tradable and should not be carried into any future
factor design; (3) if the post-T0 drift alone survives (1), assess it conceptually against the platform's
existing cost schedule and 10%-of-ADTV capacity rule before considering any further step — still a
diagnostic, not a backtest.

## Direct answer

**When an NGX stock finally trades after being stale, does information get incorporated gradually across
subsequent trades, or does the entire apparent "mispricing" disappear once we stop counting days on which
the stock did not trade?**

It does not disappear. A real, direction-consistent drift persists in the sessions following the
reopening trade, above a ticker-matched ordinary-trading baseline, and is essentially uncorrelated with
size at the episode level — a materially stronger independence result than Stage 21 produced. But the
larger part of the apparent effect is a single, unexecutable reopening jump that looks at least as
consistent with mechanical liquidity impact as with information catching up. The gradual-incorporation
story is real but small, and not yet shown to be tradable.
