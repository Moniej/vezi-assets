# Hypothesis Discovery Module — Design (planning document, not yet built)

*2026-07-16. Build trigger: when the database supports ≥3 scanner classes
with meaningful power (roughly: constituent price lists + dividend calendar
+ ≥200 events). Until then, hypothesis generation stays human, fed by the
post-verdict reviews and the family map.*

## Mission and hard boundary

Scan the accumulated database for statistically interesting relationships
that deserve to become formal hypotheses. **It validates nothing and
promotes nothing.** Its entire output is *candidates for human review*;
a candidate that survives review still enters the standard pipeline
(unique ID → pre-registration with success/failure criteria → untouched OOS
→ full validation gauntlet) before it can influence any investment decision.
There is no code path from this module to the Alpha Engine, by construction —
it writes only to a `discovery_candidates` table, which the engine never reads.

## Why the statistics must be harsher here than anywhere else

A scanner is a mass hypothesis-testing machine: scanning 8 sectors × 12
lags × 5 windows is 480 implicit tests per relationship type. Untreated,
it becomes an industrial producer of false discoveries — the exact failure
mode this platform exists to prevent. Therefore:

1. **Scan-wide multiplicity accounting**: every scan records its full test
   count (including configurations evaluated and discarded); candidate
   "interestingness" is reported as BH-adjusted q-values *within the scan*,
   never raw p-values.
2. **A candidate is a lead, not evidence.** Its scan statistics are
   quarantined: pre-registration of the resulting hypothesis must define
   fresh criteria on data windows the scan did NOT optimize over, and the
   scan's own window becomes tainted in-sample by definition.
3. **Seeded and registered**: every scan run gets an immutable record
   (scan config, RNG seed, data vintage, test count, candidates emitted) in
   the registry — reproducible like any experiment.
4. **Economic-plausibility gate**: each candidate must have a one-paragraph
   mechanism sketch attached at review time. No mechanism, no hypothesis —
   pure pattern-mining output is where data-snooping lives.

## Scanner classes (initial set, each a plug-in like providers/diagnostics)

| Scanner | Looks for | Data dependencies |
|---|---|---|
| lead_lag | persistent cross-correlations at investable lags (macro→sector, sector→sector) | index levels, macro_series |
| event_response | repeating post-event return/vol signatures by taxonomy category | events (≥~30 per class), index levels |
| regime_shift | structural breaks & regime-dependent behavior (variance/correlation regimes) | index levels, fx series |
| cross_sector | stable dependency networks / cointegration among sectors | index levels |
| liquidity | volume/value anomalies preceding returns; illiquidity premia | constituent price lists (blocked on data) |
| execution | systematic intraday/day-of-week execution anomalies | price lists w/ deals (blocked on data) |
| factor_interaction | interactions among validated-or-tested signals (e.g. momentum × liquidity) | ≥2 tested model families |

Each scanner implements `scan(ctx) -> list[CandidateFinding]` and registers
via decorator (the diagnostics-engine pattern, proven extensible).

## Candidate lifecycle

```
scan run (seeded, registered)
  └─ CandidateFinding { relationship, scan_q_value, test_count, data_vintage,
                        window, effect size, stability across sub-windows }
       └─ discovery_candidates table: status = proposed
            └─ HUMAN REVIEW (mechanism sketch required)
                 ├─ dismissed  (kept forever, with reason — negative
                 │              generation results are also findings)
                 └─ promoted → new hypothesis ID in the ledger (untested)
                               → family map entry → pre-registration → pipeline
```

Review cadence: batch review after each scan run; the hypothesis generation
rate metric counts only *promoted, evidence-based* candidates — a scanner
that spams candidates that never survive review shows up as a low
promotion rate, which is itself a scanner-quality signal.

## What it will NOT do (permanent)

- Never write to the ledger's hypothesis table directly (human promotes).
- Never touch holdout/OOS windows of any active hypothesis.
- Never rank candidates by backtest PnL — interestingness is statistical
  stability + mechanism plausibility, not simulated profit.
- Never run on synthetic/confidence-0 data.
