# Phase 29 — Regime-Conditional Research Framework: H-012 Result

*2026-08-02. Full pre-registration: `docs/PREREG_H-012.md` (frozen
before any performance data was viewed). Full IC memo:
`reports/IC_memo_H-012_h012_regime_vol_2026-08-02.md`. Ledger entry:
`docs/FACTOR_REGISTRY.md`. Do not assume success — this section
reports the real, mechanical verdict, whichever way it fell.*

## What was built

`src/ngxrot/backtest_xs.py` gained two new functions (additive only —
no existing function modified, mirroring exactly how H-010's pooled-
cohort machinery was added in the same file):

- `regime_stable_dates(con, formations, lookback_months)` — the
  pre-declared regime-classification rule, reading only
  `events.category`/`severity`/`announced_date`.
- `regime_gated_targets(...)` — applies the gate to TARGETS (which
  weight vector executes on a given rebalance), never to the score
  construction — `vol_scores()` itself runs completely unmodified.

Wired into `run_from_config()` and `placebo_stats()` as a new
`signal.method = "xs_vol_regime"`, alongside the existing `xs_rank`/
`xs_vol`/`xs_size`/`xs_event`/`xs_rank_pooled` methods — none touched.

**Regression check before running anything for real**: every existing
synthetic rehearsal script (`rehearse_xs_engine.py`,
`rehearse_xs_engine_v2.py`, `rehearse_xs_size.py`,
`rehearse_xs_pooled.py` — 12 checks, R1 through R12) still passes
cleanly after these additions.

## The regime-classification rule (pre-declared, no lookahead)

> A formation date is **STABLE** unless, in the trailing 6 months: (1)
> a `critical`-severity event occurred in the `macro`/`banking`/
> `commodity` category, OR (2) more than one `high`-severity
> `monetary` (MPC) event occurred.

**Look-ahead audit, run as its own pre-registered confirmation
criterion**: every one of the 36 real formation dates' classifications
was independently recomputed using ONLY events with
`announced_date <= f`, then diffed against the engine's own output.
**Zero mismatches.** The gating mechanism is mechanically sound —
this is true regardless of the factor verdict below.

## The result — REJECTED, decisively

| Check | Confirmation threshold | Real result |
|---|---|---|
| Placebo p-value | ≤ 0.05 | **0.9703** — real Sharpe (1.143) BELOW the placebo mean (1.432) |
| Plateau | ≥ 4/6 cells positive | **0/6** cells positive |
| BH significance | ≥ 1 cell | 6/6 (significant, but negative direction) |
| Regime concentration | no regime > 80% of excess | n/a — every regime negative or flat |
| Look-ahead audit | 0 violations | **0/36 — PASS** |

**pre_float** regime: excess −13.9%, t=−4.02, p=0.00006 (highly
significant NEGATIVE). **float_shock**: −0.1% (flat). **oos_2025_26**
(untouched, entirely STABLE-classified by this rule): −28.9%.

## Honest interpretation

Restricting to macro-event-shock-free periods did **not** rescue
H-008's low-volatility signal — if anything, the pre_float "stable"
subset shows a *larger*, more significant negative excess than H-008's
own unconditional full-window test. The most direct reading: NGX
low-volatility underperformance is not well-explained by proximity to
discrete macro-event shocks; some other mechanism (plausibly, general
bull/recovery-market dynamics rewarding high-beta names, which this
event-proximity rule does not detect) is more likely at work.

**This does not close the regime-conditioning methodology.** The
gating mechanism itself is now validated, reusable infrastructure —
look-ahead-audited, mechanically correct, available to any future
hypothesis that wants to condition on a pre-declared regime variable.
What failed is this specific pairing: event-proximity regime ×
low-volatility factor. A genuinely different regime variable (e.g., a
realized-volatility regime, or a trend/momentum regime, rather than
discrete event proximity) — or this same event-proximity gate applied
to a different factor — would each be their own new hypothesis ID,
not a rerun or a revision of H-012.

## Ledger status

H-012: `untested` → `testing` → **`rejected`**, 2026-08-02, full
conclusion recorded in `data/registry.sqlite`'s `hypotheses` table and
`docs/FACTOR_REGISTRY.md`. A failed hypothesis is a successful
research outcome — this is now permanent, disclosed program knowledge,
exactly like H-001 through H-010.
