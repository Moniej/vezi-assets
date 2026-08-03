# H-016 — Liquidity: Implementation Log + Final Report

*2026-08-03. Pre-registration frozen before any leg was run:
`docs/PREREG_H-016_liquidity.md` (includes the Economic Capacity
Validation section, added before implementation per explicit
instruction). This is a genuinely new, standalone factor test — not an
extension or forensic decomposition of H-011 (Size) — testing whether a
whole-universe cross-sectional sort on trailing 60-day ADTV carries a
return premium, in either pre-registered direction, against the
equal-weighted-IRU benchmark.*

## What was built

Additive-only, `src/ngxrot/backtest_xs.py` — no existing function
modified: `xs_liquidity_scores()`, supporting both pre-registered
directions (`direction="illiquid"`: negative standardized ADTV, the
classic Amihud & Mendelson 1986 leg; `direction="liquid"`: positive
standardized ADTV) and an optional `min_adtv_ngn` floor for the Economic
Capacity Validation ladder — wired into the existing `xs_rank`/`xs_vol`/
`xs_size` dispatch path (`scores_for_method`, `run_from_config`,
`placebo_stats`). Phase R2's own `liquidity_scores()` (frozen, used only
by `xs_size_interaction`) is untouched. Two configs
(`configs/h016a_liquidity_illiquid.toml`, `configs/h016b_liquidity_liquid.toml`),
full 6-cell grid and full 3-regime walk-forward with untouched OOS —
matching H-011's own bar exactly, per the prereg's explicit requirement
that this NOT reuse Phase R2's reduced scope (this is a fresh standalone
claim, not a diagnostic of an already-OOS-cleared hypothesis).

## Validation before real data

`scripts/rehearse_xs_liquidity.py` — 6 synthetic checks (L1-L6): planted-
premium recovery in both directions, correct direction-selects-different-
names behavior, null-panel-stays-null, and filter-ladder mechanics. All 6
passed before any real data was touched. Full existing regression suite
(R1-R12, I1-I5, S1-S5, T1-T6) re-run and confirmed passing after the
additive changes — no disturbance to any prior hypothesis's own code path.

## Real results — both legs, full gauntlet (`phase4.run_phase4_xs`)

### Leg A — Illiquid (classic Amihud & Mendelson direction)

| Cell | Excess | Sharpe | p_raw |
|---|---:|---:|---:|
| quarterly, top_n=15 | -3.15% | 1.380 | 0.714 |
| quarterly, top_n=20 (base) | -3.13% | 1.462 | 0.659 |
| quarterly, top_n=30 | +2.57% | 1.917 | 0.508 |
| semiannual, top_n=15 | +0.92% | 1.334 | 0.759 |
| semiannual, top_n=20 | -1.03% | 1.406 | 0.971 |
| semiannual, top_n=30 | +3.16% | 1.793 | 0.412 |

Plateau: 3/6 cells positive (50%). 0/6 significant even before correction
(Holm 0/6, BH 0/6). Placebo: real Sharpe 1.462 vs. placebo mean 1.292,
**p=0.168** (fails the ≤0.05 bar). Walk-forward: pre_float excess -5.75%,
float_shock +16.69%, **untouched OOS +28.17%** (t=1.252, p=0.211 — not
significant despite the positive point estimate). HAC (Newey-West,
lag=7): t=-0.366, **p=0.714**. `cost_drag_eliminates_excess` triggered
(gross +5.42% → net -3.13%) and `placebo_performs_similarly` triggered —
both signal-quality failure conditions. Real-rf daily excess Sharpe
0.0344; DSR context against the existing 11-hypothesis real-rf pool:
**0.0123**. Median leg capacity **₦712,992** — strikingly close to
H-011's own **₦694,336**, direct numerical confirmation of the expected
Size/Liquidity entanglement (the illiquid tail of the universe is
substantially the same names H-011's own size tilt selects).

**Leg A does not confirm.** Multiple independent criteria fail
(placebo, plateau, multiple-testing correction, cost-drag), not a single
marginal miss.

### Leg B — Liquid (the direction Phase R2's own H-013 evidence hinted at)

| Cell | Excess | Sharpe | p_raw |
|---|---:|---:|---:|
| quarterly, top_n=15 | -14.65% | 0.633 | 0.018 |
| quarterly, top_n=20 (base) | -10.30% | 0.889 | 0.078 |
| quarterly, top_n=30 | -8.34% | 1.100 | 0.070 |
| semiannual, top_n=15 | -13.33% | 0.660 | 0.023 |
| semiannual, top_n=20 | -12.59% | 0.729 | 0.015 |
| semiannual, top_n=30 | -8.75% | 1.021 | 0.047 |

Plateau: **0/6 cells positive** — uniformly negative across the entire
stability grid. 4/6 cells nominally significant at raw p<0.05, **all in
the wrong (negative) direction**; 3/6 survive BH correction — for
underperformance, not outperformance. Placebo: real Sharpe 0.889 sits
**below the placebo mean (1.399)**, **p=1.000** — the real strategy is
statistically indistinguishable from, and nominally worse than, a
shuffled null. Walk-forward: **every single regime shows negative
excess** — pre_float -8.53%, float_shock -6.66%, **untouched OOS -34.48%**
(t=-1.813, p=0.070). HAC (Newey-West, lag=7): t=-1.703, **p=0.088**.
`placebo_performs_similarly` triggered. Real-rf daily excess Sharpe
0.0114; DSR context **0.0005**. Median leg capacity **₦56,943,998** —
far more favorable than either H-011 or Leg A, as expected for a
liquid-name portfolio, but irrelevant given the signal itself does not
exist.

**Leg B does not confirm — and does so more decisively than Leg A.** A
strategy whose real result sits below its own null distribution's mean
(placebo p=1.0) and shows negative excess in every regime including the
untouched OOS window is not a marginal or ambiguous result.

## Economic Capacity Validation (prereg Section 10)

**Not run.** Per the prereg's own conditional framing, the filter ladder
is "applied to whichever leg (A or B) meets the §8 confirmation bar."
Neither leg met it. Running a capacity ladder on a signal that does not
exist would produce numbers with no research meaning — the ladder is a
tool for characterizing a confirmed signal's deployable scale, not a
substitute analysis for a rejected one. This is stated explicitly, not
silently skipped.

## Verdict

**H-016 (Liquidity) is REJECTED IN FULL.** Neither pre-registered
direction — illiquid (classic Amihud & Mendelson) nor liquid (the
direction Phase R2's own evidence hinted at) — produces a statistically
or economically credible standalone premium against the whole-universe
benchmark. This was explicitly recognized in advance (prereg §4, §9) as
at least as likely an outcome as confirmation, given Phase R2's own
evidence was a real prior against a clean, one-directional effect
existing at all — and the real data confirms that caution was warranted.

## Interpretation — reconciling this with Phase R2's H-013 finding

This result is **not in conflict** with H-013's own finding (Size premium
concentrated in the liquid half of a Size×Liquidity double sort), though
the two might appear superficially related. They ask genuinely different
questions:

- **H-013** asked: within a Size-selected tilt, does controlling for
  Liquidity change the result? Answer: yes — the Size premium is
  concentrated in the liquid half of the universe, and vanishes in the
  illiquid half.
- **H-016** asked: independent of Size, does a whole-universe Liquidity
  sort against the whole-universe benchmark carry its own premium in
  either direction? Answer: no, in neither direction.

A bucket-conditioned Size tilt performing well specifically within the
liquid half of the universe does not imply that an unconditioned
long-liquid tilt (with no Size selection at all) should itself outperform
the whole universe — and the real data shows it clearly does not (Leg B
was the more decisively rejected of the two legs, not the confirmed one).
**The economically meaningful liquidity-related effect on this platform
remains H-011's own Size premium, concentrated in liquid names — not a
standalone Liquidity factor.** This sharpens, rather than contradicts,
the platform's cumulative understanding: Liquidity appears to matter only
as a CONDITIONING characteristic on top of Size, not as an independent
source of return.

## What this does and does not change

- H-011's own `Validated` status and Phase R2's H-013/014/015 findings
  are unchanged by this result.
- `docs/FACTOR_CANDIDATE_REGISTRY.md`'s Liquidity entry (A1) moves from
  "Available, not yet Pre-Registered" to resolved (Rejected, both
  directions) — the standalone factor question this platform has left
  open since 2026-08-02 is now closed, with a real, informative,
  disclosed answer.
- No standalone Liquidity factor claim is made or should be inferred from
  any other result on this platform.

## Regression / integrity

Full existing suite (R1-R12, I1-I5, S1-S5, T1-T6) confirmed passing
before the real run. H-016's own real-data experiments are recorded
permanently in `data/registry.sqlite` (stability grid, placebo, and
walk-forward runs for both legs, plus one supplementary HAC/DSR-basis run
per leg). Ledger: H-016 `untested → testing → rejected`, full written
conclusion on record.
