# Stage 19B — Suspension-Lift Post-Reopening Persistence & Executability Diagnostic

**Date:** 2026-08-08
**Status:** Diagnostic only. No portfolio constructed, no backtest run, no hypothesis registered.
**Script:** `scripts/stage19b_suspension_lift_diagnostic.py` (frozen spec, run once, output below is verbatim
and unmodified after the fact).

## Frozen spec (fixed before execution, not altered after seeing results)

- Baseline = close at **T+2** sessions after reopening (excludes first 2 sessions to strip the
  auction/reopening shock).
- Persistence windows: cumulative raw return from T+2 to **T+7 / T+12 / T+22** (i.e. 5/10/20 sessions
  forward from baseline). Truncated windows (re-suspension or data end) reported as truncated, never
  extrapolated.
- Liquidity: daily volume and total turnover over the T+2→window-end span, compared against a
  pre-suspension 60-session ADTV baseline and against H-011's existing 10%-of-ADTV capacity rule. No
  bid/ask data exists on this platform — turnover is the sole liquidity proxy (disclosed limitation).
- Events: the four suspension-lifts identified in Stage 19 with recoverable price data — MBENEFIT
  (2025-03-20), INTENEGINS (2025-10-07), ASOSAVINGS (2025-10-21), ZICHIS (2026-03-23).

## Raw results (verbatim script output)

```
=== MBENEFIT  lift=2025-03-20  sessions_available=325 ===
  T+2 baseline: 2025-03-25 close=0.8
  [5-session fwd]  +21.25%
  [10-session fwd] +17.50%
  [20-session fwd] +7.50%
  post-lift avg daily volume vs pre-suspension ADTV ratio = 6.62x

=== INTENEGINS  lift=2025-10-07  sessions_available=194 ===
  T+2 baseline: 2025-10-09 close=2.9
  [5-session fwd]  +2.76%
  [10-session fwd] +0.00%
  [20-session fwd] -6.90%
  post-lift avg daily volume vs pre-suspension ADTV ratio = 0.53x

=== ASOSAVINGS  lift=2025-10-21  sessions_available=20 ===
  T+2 baseline: 2025-10-24 close=0.66
  [5-session fwd]  +56.06%
  [10-session fwd] +36.36%
  [20-session fwd] TRUNCATED — only 17 of 20 sessions available (re-suspended 2025-11-22)
  post-lift avg daily volume vs pre-suspension ADTV ratio = 50.02x

=== ZICHIS  lift=2026-03-23  sessions_available=79 ===
  T+2 baseline: 2026-03-25 close=11.4
  [5-session fwd]  +13.77%
  [10-session fwd] +10.09%
  [20-session fwd] +49.04%
  post-lift avg daily volume vs pre-suspension ADTV ratio = 0.66x
```

Full liquidity detail (avg daily volume, pre-suspension ADTV, implied 10% cap) is in the raw script
output preserved in `scripts/stage19b_suspension_lift_diagnostic.py`'s run log above each event block.

## Interpretation

### 1. Persistence diagnostic — does NOT survive

Across the 4 events, the post-shock (T+2-onward) return pattern is **not consistent**:

- MBENEFIT: positive at all 3 horizons but **monotonically decaying** (21.25% → 17.50% → 7.50%) — the
  move is front-loaded and fading, not building.
- INTENEGINS: decays through zero and **flips negative** by T+22 (+2.76% → 0.00% → **-6.90%**) — a
  direct sign reversal, the clearest evidence against persistence in the set.
- ASOSAVINGS: large but also decaying in relative terms across the two available horizons (56.06% →
  36.36%), and the 20-session window is **unobservable** — the name was re-suspended before it could be
  measured, which is itself informative (see liquidity section) but means this event cannot support a
  persistence claim past 10 sessions.
- ZICHIS: non-monotonic (13.77% → 10.09% → **49.04%**) — a late, large jump inconsistent with either a
  simple decay or simple persistence story; more consistent with a second, unrelated catalyst inside the
  20-session window than with the suspension-lift information itself continuing to be absorbed.

No shared pattern survives across events: one flips sign, one is censored by a second suspension, one
decays steadily toward zero, one jumps unpredictably late in the window. This is not the signature of a
persistent, information-driven drift — it is more consistent with idiosyncratic, event-specific noise
layered on top of the reopening shock. **Diagnostic 1 does not survive.**

### 2. Liquidity/executability diagnostic — does NOT survive either

- MBENEFIT: 6.62x pre-suspension ADTV — genuinely elevated, executable.
- INTENEGINS: **0.53x** pre-suspension ADTV — *below* its own pre-suspension baseline; harder to trade
  at scale after the lift than before the company was ever suspended.
- ASOSAVINGS: 50.02x pre-suspension ADTV — but this reflects reopening-frenzy volume over only 18
  sessions before the position would have been forcibly stuck, unable to exit, at the 2025-11-22
  re-suspension (last recorded price 2025-11-18, 4 sessions before the halt).
- ZICHIS: **0.66x** pre-suspension ADTV — also below baseline.

Two of four events (INTENEGINS, ZICHIS) show sub-baseline post-lift liquidity — the reopening does not
reliably create a liquidity window at all, let alone one that supports meaningful size. The one event
with by far the largest apparent return (ASOSAVINGS) is also the one with concrete, realized exit-lockup
risk from a second suspension inside the measurement window. **Diagnostic 2 does not survive.**

## Verdict: KILL the suspension-lift persistence track

Per the pre-agreed decision rule ("if either diagnostic kills the effect, kill the track"): both
diagnostics fail independently. The apparent post-reopening returns documented in Stage 19 §6 do not
show a persistent, information-driven pattern once the first 2 sessions are excluded — one event
reverses sign, one is censored by a second suspension, and the two that stay positive either decay
toward zero or jump unpredictably late. Liquidity is inconsistent and, in the one case with the
strongest apparent return, was cut off entirely by a second regulatory halt before a full window could
even be observed.

**This closes the regulatory state-transition track.** Combined with Stage 19's own findings
(suspension-imposed and final-delisting sub-types already NO-GO, corpus-depth DATA GAP), no sub-type of
regulatory state transition now has surviving evidence of tradable mispricing. No preregistration is
warranted — per the user's explicit rule, preregistration was conditional on both diagnostics surviving,
and neither did.
