# Phase R2 — Size Interaction Forensics: Implementation Log + Final Report

*2026-08-03. Pre-registration frozen before any bucket was run:
`docs/PREREG_H013-015_size_interactions.md`. This is a forensic
decomposition of H-011 (Size), not a new standalone factor search — see
that document's Section 0 for why. All three verdicts below are honest,
including where the pre-registered a priori expectation was wrong.*

## What was built

Additive-only, `src/ngxrot/backtest_xs.py` — no existing function
modified:
- `liquidity_scores()` — new scoring dimension, reuses `panel["adtv60"]`
  (already computed by `load_panel()` for capacity reporting; no new
  data). Score = negative standardized trailing ADTV.
- `interaction_dimension_scores()`, `interaction_bucket_members()`,
  `targets_from_bucketed_size()`, `benchmark_targets_bucket()` — the
  double-sort machinery: median-split by the interacting factor, then
  H-011's own size-selection rule applied within each bucket, benchmarked
  against an equal-weight portfolio of that same bucket (isolating "is
  being small better than being an average member of this bucket," not
  "is this bucket better than the whole market").
- `xs_size_interaction` branches in `run_from_config()` and
  `placebo_stats()` — the latter applies ONE joint ticker permutation per
  iteration to both the size and interacting-factor score series
  together, preserving each real ticker's own persistent joint
  size/liquidity/momentum/vol relationship while randomizing which return
  series is attached to that identity.
- 6 new configs (`configs/h01{3,4,5}_size_x_*_{high,low}.toml`).
- `scripts/rehearse_xs_size_interaction.py` — 9 synthetic checks (I1-I5),
  run and passed before any real data was touched.
- `scripts/run_size_interaction_phase.py` — orchestration (stability grid
  → Holm/BH → placebo → final run → HAC → DSR context), reusing
  `phase4.stability_map_xs` / `phase4.placebo_test_xs` unchanged.

## Validation before real data

9/9 synthetic checks passed (median-split correctness, cross-bucket
selection isolation, bucket-scoped benchmark weighting, liquidity sign
convention). Existing R1-R12 rehearsal suite re-run after the additions —
still passes in full, confirmed twice (once after the initial code
addition, once again after two real-data-driven bug fixes described
below).

## Two real bugs caught by smoke-testing before the expensive run

1. `liquidity_scores()`'s eligibility check used a 60-calendar-day window
   with the default `min_obs_formation=120` — mathematically impossible
   (120 observed days cannot occur in a 60-day window), silently
   producing zero formation dates on real data. Caught by a smoke test
   before the full run, not discovered after. Fixed to use the same
   12-month eligibility window `size_scores()`/`vol_scores()` already
   use, decoupled from the ADTV rolling-window length itself.
2. The momentum and volatility interaction configs were missing
   `formation_months`/`skip_months` and `vol_lookback_months`
   respectively (copied from the Liquidity config template, which
   doesn't need them) — caught immediately on the first real run attempt
   (`KeyError`), fixed before any registry-writing run.

## An operational note on background execution (disclosed, not hidden)

Two earlier attempts to run this phase's compute in `run_in_background`
Bash calls were killed mid-execution by the tooling environment itself
(not a code defect) — confirmed by checking that all 6 concurrent jobs
died simultaneously regardless of explicit timeout settings, and that
registry rows already written were real, uncorrupted partial progress,
not duplicates (no duplicate registry rows resulted; the killed attempts
never reached a second write for the same cell). The work was completed
by running each bucket-config as a synchronous foreground call instead,
which completed reliably. This is recorded because full reproducibility
requires disclosing operational hiccups, not just final numbers.

## Real results — all 6 bucket-configs

| Interaction | Bucket | Excess (base cell) | Sharpe | i.i.d. p | HAC p | Placebo p | Plateau | Holm sig | BH sig | DSR context* |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Size×Liquidity | **High**-liquidity | +23.37% | 2.272 | 0.0043 | 0.0225 | **0.0099** | 4/4 | 1/4 | 1/4 | 0.438 |
| Size×Liquidity | **Low**-liquidity | -7.81% | 0.574 | 0.370 | 0.386 | **0.703** | 0/4 | 0/4 | 0/4 | 0.0001 |
| Size×Momentum | **High**-momentum | +4.61% | 1.236 | 0.442 | 0.445 | **0.0297** | 4/4 | 1/4 | 1/4 | 0.020 |
| Size×Momentum | **Low**-momentum | +28.53% | 1.922 | 0.0004 | 0.0064 | **0.0099** | 4/4 | 2/4 | 3/4 | 0.251 |
| Size×Volatility | **High**-volatility | +1.39% | 1.216 | 0.681 | 0.720 | **0.1287** | 3/4 | 0/4 | 0/4 | 0.005 |
| Size×Volatility | **Low**-volatility | +24.65% | 1.835 | 0.0141 | 0.0218 | **0.0099** | 4/4 | 0/4 | 0/4 | 0.240 |

*DSR context: this bucket's daily real-risk-free excess Sharpe evaluated
against the existing 11-hypothesis trial pool (not a new trial slot —
context only, per the pre-registration).

## Verdicts against the pre-registered criteria (Section 5)

**H-013 (Size × Liquidity): EXPLAINED AWAY.** The high-liquidity bucket
is strong and robust (placebo p=0.0099, HAC p=0.0225, DSR context 0.438).
The low-liquidity bucket's real Sharpe (0.574) sits BELOW its own
placebo-mean Sharpe (0.731) — placebo p=0.703, a clean null. Per the
pre-registered criteria, one bucket real-and-significant while the other
placebo-fails outright is "explained away": the Size premium is better
described as a premium specific to liquid small-caps, not small-caps
generally.

**This is the OPPOSITE direction from the a priori concern stated in the
pre-registration** — H-011's own capacity report found its top
contributors were consistently thin/illiquid names, which motivated
testing whether the premium was actually an illiquidity effect. The
double-sort result says no: the premium lives in the LIQUID half. This
apparent tension is disclosed, not resolved by assumption — a bucket-level
median split of the whole eligible universe by ADTV is a different cut
of the data from "which specific names happened to contribute most
within an already-tiny top-20 selection," and the two are not logically
required to agree. Both facts are now permanently on record.

**H-014 (Size × Momentum): PARTIALLY EXPLAINED.** Both buckets are
directionally positive (4/4 plateau in each) and both pass the primary
placebo criterion (0.0297 and 0.0099). But the high-momentum bucket fails
both parametric tests at its base cell (i.i.d. p=0.442, HAC p=0.445) and
only 1/4 grid cells reach conventional significance, while the
low-momentum bucket is comprehensively strong (i.i.d. p=0.0004, HAC
p=0.0064, 3/4 BH-significant cells). The premium is real in both but
materially concentrated among low-momentum ("laggard") small caps — not
independent of momentum, but not fully explained away either.

**H-015 (Size × Volatility): EXPLAINED AWAY.** The high-volatility
bucket is a clean null (placebo p=0.1287, i.i.d./HAC both >0.68, only
3/4 plateau with zero significant cells). The low-volatility bucket is
strong (placebo p=0.0099, HAC p=0.0218). The Size premium is concentrated
in the low-volatility half.

## Overall synthesis: where H-011's confirmed edge actually lives

Combining all three interactions, the picture is consistent and
specific: **H-011's Size premium is not a generic "buy small caps"
effect — it is concentrated among small caps that are simultaneously
liquid, low-volatility, and (to a lesser, partial degree) low-momentum.**
Every "high" bucket tested (illiquid, high-vol, and — more weakly —
high-momentum small caps) shows a materially weaker or entirely null
effect. This is a real, substantive refinement of institutional
knowledge about the platform's only confirmed factor: an investor
implementing H-011 broadly (any small-cap tilt) would be diluting a real
signal that is actually narrower and more specific than the original
confirmation alone would suggest.

## What this does and does not change

- **H-011's own `Validated` status is unchanged.** It was earned under
  its own, different, pre-registered criteria (whole-universe smallest-20
  tilt vs. the whole-universe benchmark), which have not been altered.
  This investigation adds a permanent, disclosed qualification to
  `FACTOR_REGISTRY.md`, not a retroactive edit.
- **H-013, H-014, H-015 are resolved `rejected`** in the ledger — the
  narrow claim each tested ("does the Size premium survive fully
  independently of this characteristic") did not hold cleanly for any of
  the three. This is recorded as real, valuable evidence (a rejected
  hypothesis is a successful research outcome, per the platform's own
  standing convention), not a failure of the investigation.
- **No standalone Liquidity, Momentum, or Volatility factor claim is
  made or implied.** `docs/FACTOR_CANDIDATE_REGISTRY.md`'s existing
  entries for these remain exactly as they were — untested as
  independent factors.

## Regression / integrity

Existing R1-R12 rehearsal suite: pass (re-confirmed after code additions
and again after the two bug fixes). New I1-I5 synthetic checks: pass. All
6 bucket-configs' registry experiments are real, immutable, permanently
recorded (`data/registry.sqlite`, cross-checked: no duplicate rows from
the killed background-execution attempts). H-013/H-014/H-015 ledger
entries: `untested → testing → rejected`, each with a full written
conclusion, per the same state-machine every other hypothesis on this
platform has used.

## Next gap analysis (per step 15 of the methodology)

This result raises a natural, narrower follow-on question — not
manufactured as a new phase, but named for the owner's future
consideration: would a triple-conditioned tilt (small AND liquid AND
low-vol, rather than small alone) show a materially different capacity
or turnover profile than H-011's own already-documented worst-in-program
capacity (₦694,336 median leg)? This is NOT pursued here — it would be a
new standalone hypothesis requiring its own full pre-registration and OOS
validation, not an extension of this forensic investigation's own
narrower scope.
