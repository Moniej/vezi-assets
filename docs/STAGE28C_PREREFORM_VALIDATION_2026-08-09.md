# Stage 28C — Pre-Reform Protocol/Data-Validation Exercise

**Date:** 2026-08-09. **No post-2026-08-17 data used, inspected, or referenced anywhere in this
document.** No hypothesis registered, no DB write, no backtest, no parameter tuning. The frozen Stage 28B
protocol (`docs/STAGE28B_FROZEN_DID_PROTOCOL_VOLUME_THRESHOLD_REFORM_2026-08-09.md`) is unmodified — this
document identifies gaps in it and in the underlying data, it does not fix or amend either. Script:
`scripts/stage28b_prereform_validation.py`. Raw output: `data/staging/stage28b/`.

**Purpose, restated**: this is a protocol/data-validation exercise, not an alpha test. Every number below
uses only data through 2026-07-21, which is entirely pre-reform (reform effective 2026-08-17).

---

## Headline: the platform's price feed is itself stale — a separate, real operational risk

`equity_prices` currently ends **2026-07-21**. Today is 2026-08-09. That is a **19-day gap already**,
before the reform's own 27-day runway is even considered. If the daily price feed is not being actively
maintained, the October re-run (which needs data through roughly mid-to-late October) has no guarantee of
existing on schedule. **This must be fixed independently of the reform diagnostic** — flagged now,
explicitly, per the instruction to surface structural problems before October rather than after.

## PASS/FAIL by prerequisite

| # | Prerequisite | Result | Detail |
|---|---|---|---|
| 1 | Treatment/control universe is unambiguously constructible from the frozen protocol text | **FAIL — ambiguity found, not resolved** | See below |
| 2 | Zero-return outcome definition behaves correctly on real data | **PASS** | See below |
| 3 | Suspended-security handling (absence, not imputation) is supported by real data | **PASS** | 2,132 ticker-sessions across 171 tickers show genuine gaps in `trade_date` — the "absence, don't impute" rule is exercised heavily, not an edge case |
| 4 | Newly-listed handling via `securities.listing_date` | **FAIL — primary field unusable** | `listing_date` is **0/320 non-null** — entirely empty, same gap pattern as `delisting_date` (Stage 19 §5, Stage 23 §8). The frozen protocol's fallback ("or first `equity_prices` row, whichever is later") is the only viable path and must be adopted explicitly, not left as an alternative |
| 5 | Minimum-observation gate (≥30/40 sessions) is achievable for the treatment group | **PASS, narrowly** | See below — passes cleanly under one reading of the ambiguity in #1, fails badly under the other |
| 6 | Total session depth supports two non-overlapping 40-before/40-after placebo windows | **PASS** | 3,111 total sessions in the dataset — far more than the ≥160 structurally required |
| 7 | Pre-trend parallel-trends assumption (rehearsal) | **PASS, conditionally** | Stable under the cleaner interpretation of #1; unstable and noisy under the other — another point in favor of resolving #1 correctly |

---

## 1. Treatment/control universe construction — the central finding

The frozen protocol defines treatment by "closing price on the last trading session strictly before
2026-08-17" but does not specify what happens to a ticker with **no row exactly on that reference
session** — a real, common case (only 139/320 tickers, 43%, have a row on the current latest date at
all). Two readings were tested on real data, both fully mechanically executable but producing sharply
different, non-interchangeable results:

| | Interpretation A (strict same-day) | Interpretation B (look-back, most recent close as-of) |
|---|---|---|
| Treated (≥₦1,000) | **7 tickers** | 16 tickers |
| Mid-band (₦500–999.99) | 6 tickers | 8 tickers |
| Control (<₦500) | 126 tickers | 296 tickers |
| Median staleness of the reference price | 0 days (by construction) | 21 days (but max = **4,401 days**, ~12 years) |

**Interpretation B is disqualifying as written.** Its look-back has no bound, so it happily assigns
treatment/control status based on a ticker's *last ever recorded price*, however old. The consequence
shows up immediately in the observation-count check: under Interpretation B, the treated group's **median
sessions-present in the most recent 40-session window is 25 (with a minimum of 0)**, and the control
group's median is **0** — meaning the majority of "control" tickers under this reading are names that
haven't traded meaningfully in years, dead in all but a stale database row. Interpretation A, by contrast,
gives every treated/control ticker a clean 37-of-40 median session presence.

**This is reported as a finding, not resolved as a decision** — but the data leaves little ambiguity about
which reading is usable: **Interpretation A (strict same-day match, or at minimum a tightly bounded
look-back of a few sessions) is the only version of the rule that produces a defensible universe.** The
frozen protocol must be explicitly amended to say so before October — this is exactly the kind of
structural problem the instruction asked to be surfaced now.

A second, related structural fact worth flagging plainly: **only 139 of the 320 tickers in `securities`
(43%) are "live" enough to have a row on any given recent session at all.** Whatever the final treatment
rule, the addressable universe for this entire natural experiment is a minority of the platform's nominal
security list — expected and consistent with everything found in Stages 20-27, but worth restating here
since it directly bounds how large the treatment group can ever be (§5 shows the honest number is 7, not
16).

## 2. Zero-return outcome definition — stress test

- 353,043 total price rows; 320 excluded as each ticker's unmatchable first observation (correct, expected
  behavior, one per ticker).
- 53.5% of all remaining rows are zero-return under the frozen strict-equality definition — of which
  177,833 are genuinely traded-but-unchanged and 10,986 have no recorded volume. The genuine-trade
  component dominates by a wide margin, confirming the metric is measuring real price stickiness, not
  mostly a missing-data artifact.
- A tolerance-band alternative (|return| < 0.1%) would reclassify only 1,972 rows (0.6% of all rows)
  differently from the frozen strict-equality rule — the definition is not fragile to this specific edge
  case, and the frozen choice (strict equality) is confirmed unambiguous in practice, not just in theory.

## 3. Minimum-observation feasibility (§5 of the protocol)

Under Interpretation A: **treated group 7/7 tickers pass** the ≥30-of-40 rule (median 37, min 37).
Mid-band: 5/6 pass. Control: 117/126 pass. **The treated group — the group the entire experiment depends
on — clears this bar with no exceptions**, which is a genuinely reassuring result given how small it is.

Under Interpretation B, the same gate collapses the usable sample dramatically (only 7/16 treated, 117/296
control survive) — the same evidence pointing back to §1's conclusion.

## 4. Pre-trend check (rehearsal — not the real pre-period, which doesn't exist yet)

Using the last 40 available sessions (2026-05-27 to 2026-07-21) split into two 20-session halves, under
Interpretation A:

- Treated: 89.3% → 88.7% zero-return frequency (stable, essentially flat).
- Control: 51.8% → 54.9% (stable, small upward drift shared by both groups' general direction — not a
  concerning divergence).

No material pre-trend incompatibility in this rehearsal window. This is not a substitute for the real
pre-trend check (which must use the actual pre-period ending at the real reference date), but it is a
reasonable early signal that the design is not obviously broken.

**Baseline level worth flagging on its own**: the treated group's zero-return frequency is already
extremely high pre-reform (~85-90%). These are large, expensive, thinly-traded-by-count blue chips. If the
reform works as the mechanism predicts, this baseline should drop materially post-reform — a big, visible
number to watch for, not a subtle one.

## 5. Placebo-date checks — run using old-regime data only (Interpretation A groups)

Two placebo "reform dates" were tested, both entirely within the old regime (no rule change occurred at
either), using the same DiD construction as the frozen protocol:

| Placebo | Pre window | Post window | Treated Δ | Control Δ | Placebo DiD |
|---|---|---|---|---|---|
| 1 | 2026-03-31 to 2026-05-25 | 2026-05-26 to 2026-07-21 | +6.1pp | +9.1pp | **-3.0pp** |
| 2 | 2025-12-09 to 2026-02-02 | 2026-02-03 to 2026-03-30 | -11.8pp | -1.2pp | **-10.6pp** |

**This is an important, honest finding, not a null result to wave away.** With only 7 treated tickers,
period-to-period noise alone produces placebo DiD estimates ranging at least from -3pp to -11pp under
conditions where the true effect is known to be zero (no rule changed at either placebo date). **The real
October DiD result must be judged against this noise floor, not against zero.** A real effect smaller than
roughly 10-11 percentage points would not be distinguishable from what this small-sample design already
produces by chance. This directly reinforces the frozen protocol's own instruction to rely on the exact
sign-permutation test rather than trusting a parametric p-value at face value (Stage 28B §3) — confirmed
necessary by this rehearsal, not just a theoretical caution.

---

## Does the frozen Stage 28B experiment remain executable as designed?

**Yes, but not without one required amendment.** Every mechanical piece of the protocol — the outcome
definition, the suspension-handling rule, the minimum-observation gate, the clustering/permutation
approach, the placebo-window construction — checks out against real data and is either already correct or
straightforwardly executable. The one load-bearing gap is the treatment-assignment ambiguity in §1, which
must be closed with an explicit rule (recommended, based on this evidence: strict same-day match, or a
tightly bounded look-back of no more than a few sessions) before the October run, or the experiment risks
silently running on a badly contaminated universe (Interpretation B).

## What must be fixed before the first post-reform run

1. **Amend Stage 28B §1** to specify exactly how a ticker with no row on the reference session is handled
   — this document's evidence favors strict same-day matching (or a narrow bounded look-back), not an
   unbounded one.
2. **Amend Stage 28B §2's newly-listed clause** to rely solely on the first-`equity_prices`-row fallback —
   `securities.listing_date` is confirmed 100% unusable, not merely incomplete.
3. **Resolve the price-feed staleness issue independently** — the platform's daily data is already 19 days
   behind "today," unrelated to the reform; without fixing this, there is no guarantee the October window
   will have data available on schedule.
4. **Treatment-group size expectation should be set now, honestly**: under the only defensible reading of
   §1, the treatment group is **7 tickers**. Any eventual result must be interpreted with that sample size
   in mind from the start — not discovered as a disappointing surprise in October.
