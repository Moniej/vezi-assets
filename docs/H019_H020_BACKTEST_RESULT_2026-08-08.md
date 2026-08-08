# H-019/H-020 — Backtest Result (Expanded Dataset)

**Date:** 2026-08-08
**Status: FIRST LOOK, NOT CONFIRMATION-ELIGIBLE.** This report supersedes the earlier n=6 version. The H-019 event dataset was expanded to n=11 qualifying events before this update, per the frozen specifications (`docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md`, `docs/PREREG_H-019.md`, `docs/PREREG_H-020_PORTFOLIO_CONSTRUCTION_2026-08-08.md`). **The executable (tradable) set did not grow** — still exactly 2 events — for reasons disclosed in §1 below. This does not resolve H-019 to confirmed or rejected. No portfolio-construction parameter was changed after seeing any return data, at any point across the original or expanded run.

**Read this whole document before the numbers below, not instead of them**: six original qualifying events was already stated as extremely small. Eleven is still extremely small. Even a spectacular result at this sample size would be evidence a hypothesis is worth investigating further — never proof of alpha. Nothing in this report should be read as overriding that standard, regardless of which way any individual number points.

---

## 1. Dataset expansion (n=6 → n=11)

Five additional articles, spanning event types already cleared for H-019 (governance/management-change and corporate-identity-restructuring), were fetched, registered as `documents` rows (learning from the Stage 14 Round 4 provenance gap — registered *before* building the events batch this time, not after), and ingested through the standard, Stage-10E-fixed `event_pipeline`:

| Ticker | Event | Type | Direction (applied per frozen §14C rule table) |
|---|---|---|---|
| ROYALEX | New Group Chairman (Ikeme Osakwe, succeeding a retiring 28-year incumbent) | management_change | **neutral** — routine appointment, no stated controversy |
| TANTALIZER | Majority stake acquired by Food Specialties/Banklink Africa via ₦1.07bn private placement | ownership_change | **unknown** — see finding below |
| TANTALIZER | Board appointment (Tade Ogidan) | management_change | **neutral** — routine appointment |
| REDSTAREX | Wholly-owned logistics subsidiary absorbed into parent | corporate_restructuring | **unknown** — see finding below |
| CILEASING | Three executive appointments (COO + 2) | management_change | **neutral** — routine appointments |

**A genuine finding, not smoothed over**: applying §14C's frozen direction rule *literally* to these 5 new events surfaced **two real gaps in the rule table's coverage**, not two convenient NEUTRAL calls:
- **TANTALIZER's ownership_change** doesn't fit any defined row. Row 3 (NEUTRAL) requires "no accompanying capital-raise/injection" — but this transaction explicitly *did* include one (the ₦1.07bn private placement that created the stake). Row 2 (POSITIVE, capital injection) is scoped specifically to rename/pivot events, not ownership changes. No row covers "ownership change with an accompanying injection."
- **REDSTAREX's corporate_restructuring** doesn't fit any defined row either. It's an internal reorganization (a subsidiary absorbed into its own parent), not a merger between independent parties (row 1), not a rename/pivot with capital injection (row 2), not an external stake acquisition (row 3), and not disclosed as distress-driven (row 4). The article's strong accompanying profit figures are earnings-adjacent content, explicitly out of scope for CIR direction input — they were **not** used to lean this toward positive.

Both fall to §14C's own explicit catch-all (row 5: "cannot be objectively determined → UNKNOWN") rather than being stretched into a convenient answer. This is disclosed here as a real limitation of the frozen rule table discovered by actually using it on new data — not a defect to quietly patch by loosening the rule (that would reopen §14C, explicitly out of scope for this stage) or to quietly reinterpret in whichever direction happens to change the tradable count.

**Consequence**: of 11 qualifying events, 2 are `positive`, 7 are `neutral`, 2 are `unknown`. Only `positive`-direction events are long-only-executable under PREREG_H-020 §3/§6 — so **the executable set is still exactly 2** (DEAPCAP, LEGENDINT, unchanged from the original n=6 run). The backtest numbers below are therefore numerically identical to the original run for every metric that depends only on the executable set — expansion added real dataset breadth (and a real, disclosed rule-coverage finding) without adding a single new tradable observation.

All 11 rows: `PIT_status=PIT-SAFE` (11/11), `duplicate_status=primary` (11/11, no cross-outlet ambiguity). Document-linkage guard (`scripts/test_event_document_provenance.py`) re-run clean after expansion: 18/18 news events linked, 0 orphans this time (unlike the original 6-event round, which required a separate remediation stage).

## 2. Selections (executable, long-only, per PREREG_H-020 §3/§6)

| ticker | entry (`eligible_from`) | exit (60 sessions later) | direction |
|---|---|---|---|
| DEAPCAP | 2026-03-18 | 2026-06-22 | positive |
| LEGENDINT | 2026-03-25 | 2026-06-25 | positive |

## 3. A construction bug found and fixed before interpreting anything (unchanged from the original run)

The first attempt used `sim_start=2015-07-01` (by analogy to H-006). This left the H-019 book with **zero** targets — true 0% return, not benchmark-tracking — for the ~10.7-year pre-event stretch, since the platform's `event_targets()`/`simulate()` combination only sets a weight row on selection *change* dates. This crushed the annualized-return math and compared the book to the benchmark over incomparable exposure periods. **Fixed by bounding `sim_start` to 2026-01-01** — done before examining whether that changed the result's favorability. The buggy run is preserved in the immutable experiment registry, not deleted (`experiment_id d897a1cb...`).

## 4. Result — raw, net-of-cost, and benchmark-relative, separated explicitly

135-day window (2026-01-01 to 2026-07-21). Cost model = live `cost_schedule` table (brokerage/SEC/NGX/CSCS/stamp duty/VAT). Liquidity = platform-standard 10%/60-day ADTV cap. Benchmark = EW-IRU. All exactly per PREREG_H-020, none chosen after seeing this result.

| Metric | Value |
|---|---|
| **Gross annualized return** (before costs) | **+3.90%** |
| **Net annualized return** (after costs) | **-0.77%** |
| Cost drag (annualized) | -4.56% |
| **Benchmark (EW-IRU) annualized return, same window** | **+9.23%** |
| **Excess return, net of costs, vs. benchmark (ann.)** | **-10.0%** |
| Annualized volatility | 11.29% |
| Sharpe (rf=0%) | -0.068 |
| Maximum drawdown | -14.49% |
| Hit rate vs. benchmark (execution-window level) | 25% (1 of 4 entry/exit windows) |

**Cost drag alone (4.56% annualized) very nearly exceeds the entire gross return (3.90%)** — this is a direct, visible consequence of §14D/§14G/PREREG_H-020's own turnover profile (60-session holds, only 2 positions total, each requiring a full round-trip) rather than a surprising new finding; it is the same capacity/cost sensitivity pattern H-011 already disclosed for this universe.

## 5. Event/trade counts

- **Qualifying events (all types, all directions)**: 11
- **Executable trades**: 2 (100% long, 0% short — no `negative`-direction event exists in the dataset; PREREG_H-020 §6 would not execute one anyway, long-only being the platform-wide convention)
- **Non-executable events**: 9 (7 neutral-by-rule, 2 unknown-by-rule-coverage-gap)
- **Rebalance events** (entries + exits): 4

## 6. Exposure and turnover

- Trading days in simulation window: 135
- Days with ≥1 active non-benchmark position: 63 (46.7% of the window) — the book is at least partially event-exposed for under half the analyzed window, benchmark (EW-IRU residual sleeve) for the rest, by construction (PREREG_H-020 §9).
- One-way turnover: 28.6% of NAV per rebalance event on average; 213.7% annualized one-way — very high, mechanically, because there are only 2 positions total and 60-session holds concentrate all turnover into 4 discrete dates rather than spreading it across a periodic rebalance calendar the way H-011's quarterly cadence does.

## 7. Maximum drawdown

**-14.49%**, over the 135-day window. With only 2 underlying positions, this drawdown is not diversified across multiple independent bets — it substantially reflects the realized path of these 2 specific names during their specific holding windows, not a general property of the strategy.

## 8. Win/loss characteristics

| ticker | raw price return | net-of-costs return | EW-IRU return over the same window | excess | result |
|---|---|---|---|---|---|
| DEAPCAP | -31.63% | -34.20% | +3.87% | -38.06% | **LOSS** |
| LEGENDINT | -17.36% | -20.46% | +2.46% | -22.92% | **LOSS** |

**Win rate: 0/2 (0%).** Stated explicitly: with n=2, a win rate is a coin-flip-uninformative statistic — 0/2 is not distinguishable from bad luck, and would not become distinguishable even if it had gone the other way (2/2 would have been equally uninformative as "evidence"). Both `positive`-classified events lost substantial value in absolute terms and underperformed the benchmark by a wide margin over their own holding windows.

## 9. Event-level contribution

DEAPCAP: -1.667% of total book NAV over the full sim window. LEGENDINT: -0.739%. (These figures are diluted by the ~53% of the window the book spent outside these two positions — see §6 — so they are not the same as the per-position returns in §8, which are computed only over each position's own holding window.)

## 10. Concentration by ticker

Of the 11 qualifying events: ROYALEX and TANTALIZER each contributed 2 events (the only tickers with more than one), all others exactly 1. Of the 2 *executable* events: 1 each for DEAPCAP and LEGENDINT — perfectly diversified by construction at this sample size only because there happen to be exactly 2 tradable names; this is not evidence of genuine cross-sectional breadth, since the underlying tradable set is this small.

## 11. Performance across time periods

| Month | Net book return (compounded) | Trading days |
|---|---|---|
| 2026-01 | 0.00% | 21 |
| 2026-02 | 0.00% | 20 |
| 2026-03 | -3.41% | 20 |
| 2026-04 | +1.56% | 20 |
| 2026-05 | +8.43% | 18 |
| 2026-06 | -10.77% | 21 |
| 2026-07 | +4.92% | 15 |

January/February show 0.00% because the book was fully in cash/no-target state before the first entry (2026-03-18) — this is a real, disclosed artifact of the event-driven construction (§3, matching the original bug fix), not a data gap. June's large negative month coincides with both positions' exit windows (2026-06-22, 2026-06-25). **No meaningful sub-period stability analysis is possible with only 2 underlying events spanning one contiguous ~4-month active stretch** — this table is reported for transparency, not as a basis for any regime- or seasonality-based claim.

## 12. Periods with insufficient liquidity/execution capacity

**100% of trade legs would be rejected** under a ₦1bn AUM at the platform's standard 10%/60-day ADTV participation cap (median leg capacity ≈ ₦34m — roughly 3% of the configured AUM). Both DEAPCAP and LEGENDINT are the capacity bottleneck. This is not a new finding specific to H-019 — it mirrors H-011's own, independently-established prior finding that this 20-name universe is capacity-constrained by construction (it is deliberately the smallest/most illiquid tier of the IRU). It is stated here as a real, disclosed constraint on how any eventually-confirmed version of H-019 could be deployed at scale, not swept into the return numbers.

## 13. Statistical uncertainty — the central caveat, stated as plainly as possible

- **Underlying independent event count: n=2.** Not 135 (the number of daily return observations), not 11 (the number of qualifying dataset rows) — **2**, the number of genuinely independent real-world occurrences this backtest's return numbers are built from.
- The reported t-statistic (-1.581) and p-value (0.114) are computed over 135 *daily* excess-return observations, which are highly autocorrelated within each of only 2 independent underlying events. **The effective sample size for any claim about GMC/CIR events in general is 2, not 135.** No p-value, confidence interval, or significance test computed this way can distinguish a real effect from noise at this sample size — this is a hard mathematical limit on what can be concluded, not a caveat to read past before getting to "the real result."
- **Even a spectacular result at n=2 (or n=11 qualifying, 2 executable) would only be evidence that GMC/CIR events are worth investigating further with more data — never proof of alpha.** This result happens to be negative, which makes the caution easier to state honestly than it would be with a positive result, but the caution applies identically either way, and is stated here as the platform's standing epistemic standard, not as a post-hoc excuse for this particular outcome.

## What this does not authorize

No change to H-019's event dataset, direction rules, or PIT rules (§14A/§14C/§14E untouched — the two rule-coverage gaps found in §1 are disclosed, not silently patched). No change to H-020's portfolio-construction rules based on any result seen (per PREREG_H-020 §14, any parameter change requires a new hypothesis ID). No confirm/reject resolution of H-019 — ledger status remains `testing`, now with 3 logged experiments (the original buggy-window run, the corrected n=6 run, and this expanded n=11/n=2-executable run — all three preserved, none deleted). H-011 untouched throughout (file timestamps unchanged: 2026-07-22). No new source scraped — both new-article sources are Nairametrics, already approved. The platform's own standing confound check (§14J item 10, H-011 size/distress correlation) remains unrun and still gates any future claim that H-019 is independent of H-011.

## Natural next step (not begun here)

Stage 13 identified 51 independent novel events across the full 20-ticker search corpus; 11 now sit in the fully-processed, database-resident GMC/CIR set (up from 6). Further expansion, and — separately — resolving the two rule-coverage gaps found in §1 (which would require reopening §14C, a decision for whoever owns that document, not something to be done inside a backtest-reporting stage) are the two most direct paths to a dataset large enough to say anything with real statistical content. n=2 executable observations remains a pipeline test, not a research result, regardless of which direction the numbers point.
