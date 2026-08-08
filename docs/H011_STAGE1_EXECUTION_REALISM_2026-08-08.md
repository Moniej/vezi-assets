# H-011 Stage 1 — Execution Realism, Concentration, and Corporate-Action Audit

*2026-08-08. Does not modify `configs/h011_size.toml`, `docs/PREREG_H-011.md`,
or H-011's signal/portfolio construction. New code: `src/ngxrot/
execution_realism.py`, `src/ngxrot/corporate_action_audit.py`, a
`single_name_dependency` addition to `failure_conditions.py`, an additive
one-line change in `runner.py`'s xs branch. New scripts:
`scripts/h011_stage1_execution_realism.py`,
`scripts/h011_stage1_a2_single_name.py`,
`scripts/test_corporate_action_exposure.py`.*

## A-1 — Participation-capped execution

Method: same targets H-011's own frozen `size_scores`/`targets_from_scores`
pipeline produces, run through a new `constrained_simulate` that caps every
leg's fill at `adtv_participation_cap_pct=10.0` of 60-day ADTV (H-011's own
already-frozen liquidity config, unmodified), with unfilled capital sitting
at explicit zero-return cash (never redeployed, never credited the
benchmark's return). Unconstrained reproduction matches the registered
H-011 numbers exactly (dev excess +15.02%, Sharpe 2.244; OOS excess
+52.98%, Sharpe 4.558) — confirms the pipeline is faithful before trusting
the constrained numbers.

| metric | dev unconstrained | dev constrained | OOS unconstrained | OOS constrained |
|---|---|---|---|---|
| gross ann. return | 48.01% | 0.92% | 145.68% | 5.31% |
| net ann. return | 42.09% | 0.89% | 134.98% | 4.99% |
| benchmark return | 27.07% | 27.07% | 82.00% | 82.00% |
| **net excess** | **+15.02%** | **-26.18%** | **+52.98%** | **-77.01%** |
| Sharpe | 2.244 | 1.168 | 4.558 | 1.437 |
| max drawdown | -32.81% | -2.47% | -24.20% | -4.39% |
| turnover (ann. one-way) | 1.131 | 0.007 | 1.535 | 0.121 |
| mean fill fraction | 100% (assumed) | 12.3% | 100% (assumed) | 18.3% |

At the platform's configured `aum_ngn=1e9`, **A-1's acceptance criterion
fails decisively**: realized net OOS excess is -77.01%, not positive. The
portfolio is so radically underinvested (87.7%/81.7% of desired weight
unfilled on average) that it cannot keep pace with the fully-invested
EW-IRU benchmark, even though its per-unit-invested return is still
strong.

**AUM sweep** (execution-side only; signal/top_n/rebalance untouched)
finds where constrained net excess crosses zero:

| window | crossover AUM | excess just above | excess just below |
|---|---|---|---|
| dev (9yr, 35 rebalances) | **≈ ₦25,000,000** | +0.79% (₦24M) | -0.50% (₦26M) |
| oos_2025_26 (18mo, 5 rebalances) | ≈ ₦60-70M (between +24.0% @50M and -11.7% @75M) | | |

The dev-window crossover (far more decisions, less sample-noise) is the
primary estimate: **≈ ₦25 million**. Below that, e.g. at ₦5M, constrained
excess is +20.6% (mean fill 46%) — genuinely positive, but ₦5-25M is a
single small retail account, not institutional or even small-fund capital.
**There is no AUM level combining meaningful capital with meaningful
edge**: by the point fills become reasonably complete, the excess has
already decayed to roughly zero.

## A-2 — Single-name concentration

New generic `single_name_dependency` check added to `failure_conditions.py`
(default threshold `max_single_name_share=0.25`, chosen before viewing any
hypothesis's own per-name numbers — 5x an equal-weighted 20-name book's
"fair share" of 5%). Runs via the unmodified `runner.run_resolved` path
against H-011's base config, so results are persisted as new experiment
rows under H-011's own `hypothesis_id` (exp `bbacd121…` dev,
`28ba2165…` OOS) — not a new or separate record type.

| window | top name | share | top-3 combined | verdict (25% cap) |
|---|---|---|---|---|
| dev | FTNCOCOA | 7.4% | 20.2% | **PASS** |
| oos_2025_26 | NCR | 17.4% | 33.0% | **PASS** |

Matches the IC memo's own disclosed "FTNCOCOA 7%" figure exactly —
cross-consistent. OOS concentration (17.4%, close-ish to the 25% cap in an
18-month/5-rebalance window) is worth watching but does not fail.

## A-3 — Bonus/scrip price adjustment

**Confirmed, not newly discovered**: `backtest_xs.py` (H-011's engine) has
no query against `corporate_actions` and no adjustment-factor logic
anywhere — re-confirmed here by direct grep and locked in by
`scripts/test_corporate_action_exposure.py`'s first assertion.
`corporate_actions` itself has zero real rows (31 synthetic
`SYNBNKA/B/C` fixtures only — `docs/METHODOLOGY_HARDENING_2026-08-04.md`).
**Status: DATA UNAVAILABLE, not implemented.** No real bonus/scrip event
anywhere on the platform has a verified ratio + clean ex-date to calibrate
a correct adjustment against — building one now would mean guessing a
ratio, which is fabrication, explicitly out of bounds.

What was newly done: a generic, reusable exposure-detection diagnostic
(`corporate_action_audit.py`) that cross-references ANY hypothesis's own
actual holding periods against real `unexplained_jump` diagnostic flags —
not hypothetical, not platform-wide, but "did THIS hypothesis's own return
series actually touch a suspect day." For H-011 (2016-01 to 2026-06):
**5 real overlaps**, all individually inspected against the raw price
series:

| ticker | date | move | pattern |
|---|---|---|---|
| CILEASING | 2024-01-05 | 5.13→3.38 (-34.1%), adjacent-day | sharp single-day drop, partial bounce next 2 days — unconfirmed either way |
| IMG | 2023-12-29 | 8.50→9.35→13.45 across a ~1wk thin-trading gap | thin-trading price-discovery pattern, not a clean corporate-action marker |
| LASACO | 2021-02-22 | 0.42→1.52 (+262%) after a genuine ~17-session **archive-confirmed absence** (checked the archived PRICES1 PDF directly for a mid-gap date: LASACO is not listed at all — a real trading gap, not a parser miss) | consistent with a trading halt/resumption re-rating, NOT the clean single-day signature of a bonus/scrip markdown |
| PRESTIGE | 2018-06-08 | 0.46→0.67 (+45.7%), adjacent-day | sharp single-day move, unconfirmed either way |
| PRESTIGE | 2018-11-28 | 0.85→0.77→0.55 (-35.3% over 2 days) | cascading 2-day decline, unconfirmed either way |

**None of the 5 shows the clean single-day, simple-fraction-ratio
signature typical of an unadjusted bonus/scrip event** (e.g. an exact
2/3, 3/4, 4/5 multiplier). LASACO and IMG are better explained by the
platform's own already-disclosed, separately-measured thin-trading/
stale-price risk category than by a corporate action. CILEASING and
PRESTIGE remain genuinely unconfirmed — could be real market moves in
illiquid penny-priced names, could be an unadjusted action; the archive
does not resolve it further without the specific-day PDFs and an X-Issuer
cross-check, which is future work, not fabricated here.

`test_corporate_action_exposure.py` locks the count (5) as a tripwire —
if a future data refresh changes it, the test fails and forces a re-audit
rather than silently drifting.

## A-4 — Deployment scorecard

| Category | Result |
|---|---|
| PIT integrity | **PASS** |
| Data confidence | **PASS** |
| OOS performance (unconstrained) | **PASS** |
| Top-N robustness | **PASS** |
| Rebalance robustness | **PASS** |
| Regime robustness | **PASS** |
| Placebo | **PASS*** (own-hypothesis p=0.0099; *program-level DSR=0.0071-0.130 materially weaker — pre-existing METH-001 finding, not re-litigated here) |
| Transaction costs | **PASS** |
| Participation-constrained execution | **FAIL** (OOS net excess -77.01% at configured ₦1bn AUM) |
| Single-name concentration | **PASS** (new check; 7.4%/17.4% vs 25% cap) |
| Sector concentration | **PASS** |
| Free-float validity | **UNRESOLVED** (full-issue cap only, pre-existing L1) |
| Statistical significance | **WEAK** (Holm p=0.049 own-hypothesis; DSR weak at program level) |
| Economic significance | **WEAK** (at the AUM where fills work, edge has decayed to ~0%) |
| Capacity | **LIMITED** (≈₦25M realistic ceiling, dev-window basis) |
| Corporate-action adjustment | **UNRESOLVED** (no adjustment mechanism; 5 exposure overlaps found, none confirmed as an actual unadjusted action) |

## Verdict: **DEPLOYABLE AT LIMITED CAPACITY**

Realistic maximum AUM ≈ **₦20-25 million** (dev-window crossover; the
shorter OOS window's own crossover, ≈₦60-70M, is directionally consistent
but too sample-thin to trust over the 9-year dev estimate). This is not a
euphemism for "small" — it is genuinely capital appropriate to a single
retail account, not a fund. Below that ceiling the edge is real and
survives participation-capped execution; at or above it, the edge and the
available capital do not overlap.
