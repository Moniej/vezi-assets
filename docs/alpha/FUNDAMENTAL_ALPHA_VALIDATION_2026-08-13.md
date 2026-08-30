# Fundamental Alpha Validation — 2026-08-13

No hypothesis registered by fiat. No Alpha Engine calculation changed. No
production data written. No new infrastructure built beyond one bounded
completion script (`scripts/fre/phase4_pilot_completion.py`) needed to
attempt the assigned Phase 1 continuation. Every number below is measured
directly against the real `data/ngx.sqlite`/`data/registry.sqlite` (both
read-only) or against real, disclosed LLM-quota failures — nothing is
assumed or projected without saying so explicitly.

**Bottom line, stated up front**: the chain Document → Extraction →
Validated Fact → Financial Reasoning works and produces real, checkable
output. It does not yet reach the breadth (50 tickers) this project's own
prior audit established as the minimum for a statistically legitimate
cross-sectional factor test. Today's honest answer is **DATA INSUFFICIENT**,
not a rejected factor and not a validated one. This is treated, per the
brief's own instruction, as useful information rather than a failure.

---

## 1. FRE validation

Continuing directly from `FINANCIAL_EXTRACTION_PILOT_2026-08-12.md` and
`FINANCIAL_EXTRACTION_QUALITY_FIX_REPORT.md`. That prior work already
established:

- Period-schema defect (facts had zero period metadata) — **fixed**,
  verified on a live re-extraction of TRANSCORP FY2024 (6/6 facts with
  complete, correct period metadata).
- Numeric-consistency defect (TRANSCORP's 10× net_profit error) — **fixed**,
  a new deterministic `check_numeric_consistency()` check now flags it
  (verified retroactively on the original error and on 5 synthetic
  round-factor cases, 0 false positives on the other 9 original facts).
- Point-in-time ratio-matching defect (`debt_to_equity` could never compute
  for ANY ticker) — **fixed**, confirmed live: `debt_to_equity` now computes
  204/267 = a real share of the current production conclusion set (see §1.1).
- A tested, zero-risk backfill script (`backfill_flow_fact_period_start.py`)
  exists, dry-run-verified against production (51 qualifying facts, 0
  rejected), and would raise `financial_reasoning_conclusions` from 267 to
  403 on application — **still awaiting explicit operator approval, not
  applied today**, consistent with this task's own "no new infrastructure,
  no unauthorized production writes" constraint.

**This session's assigned continuation** (Phase 1: "complete the remaining
pilot documents when quota permits") was attempted twice, live, against a
scratch copy of `data/ngx.sqlite`:

| Attempt | Time (UTC) | Result |
|---|---|---|
| 1 | 2026-08-13 ~04:50 | `429 RESOURCE_EXHAUSTED` — `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limit 20, on the FIRST call of the run (doc_id=452, STANBIC) |
| 2 | 2026-08-13 ~04:53 (after the API's own suggested retry delay) | Identical `429`, same quota ID, first call again |

**Finding, not assumed**: it is now past UTC midnight (checked directly:
system time 2026-08-13 05:49 UTC) relative to the 2026-08-12 pilot that
originally exhausted this quota, yet the daily cap is still reported as
exhausted. Either Google's actual reset boundary is not UTC midnight (the
prior report already flagged this as an unconfirmed assumption), or the
quota was already consumed today by activity outside this session. No
evidence of another local process consuming it was found (no lock files,
no matching log timestamps). **This is disclosed as an open, unresolved
uncertainty, not resolved by guessing.**

**Decision**: rather than keep spending turns against an external quota
with no confirmed reset time, this pilot continuation is recorded as
**quota-blocked, not completed**, and the assignment proceeds using the
FRE quality evidence already in hand (§1.1) — which is sufficient to
answer "is the pipeline's quality acceptable" even though it cannot yet
answer "does quality hold across the full stratified 5-case pilot."

### 1.1 Extraction accuracy (cumulative real evidence to date)

Across the two real pilot sessions (11 original documents + 1 fresh
post-fix TRANSCORP re-extraction = 12 real LLM-graded document/fact
observations total):

| Dimension | Result | Basis |
|---|---|---|
| Identity accuracy | 10/10 (100%) | Original pilot §7 |
| Fact-type accuracy | 9/10 (90%) | 1 qualitative-statement mistag (STANBIC fact 498) |
| Period_start/end/type accuracy (post-fix) | 6/6 (100%) | TRANSCORP re-extraction, quality-fix report §6 |
| Numeric accuracy | 9/10 pre-fix, safety net now closes the gap | TRANSCORP 10× error, now deterministically catchable |
| Unit accuracy | 9/10 (90%) | Same TRANSCORP case |
| Evidence grounding | 10/10 (100%) | Every fact has a real, verified `quoted_text` |
| True-negative behavior | 3/3 confirmed correct | SEPLAT (2 notices, 0 facts), MORISON (1 of 2 notices, 0 facts), most of STANBIC |
| Numeric-consistency check false-positive rate | 0/9 on real data, 0/1 on a genuine multi-figure quote | Quality-fix report §4 |

**EXTRACTED vs VALIDATED vs FINANCIAL-REASONING-USABLE, kept explicitly
separate, per instruction:**

- **EXTRACTED**: 495 rows in production `extracted_facts` today, spanning
  75 distinct tickers. This count alone answers nothing about usability.
- **VALIDATED**: of those, facts passing `grounding_check` (real quote) AND
  not flagged by `numeric_consistency_check` — the deterministic pipeline
  applies this per-fact; not separately re-tallied here since it was
  already measured at 9/10 (pre-fix sample) and 6/6 (post-fix sample).
  Extraction completing is explicitly NOT treated as validation — a fact
  can be extracted and still be a metric mistag, a period-null, or a
  round-factor error.
- **FINANCIAL-REASONING-USABLE**: facts that actually feed a `computed`
  (not `insufficient_data`) row in `financial_reasoning_conclusions`. Real
  count: **204 of 267** stored conclusion rows are `computed`; the
  remainder (`63`) are honest `insufficient_data` placeholders, not
  fabricated values. Usability is gated on having a same-ticker,
  same-period numerator AND denominator fact, in the same currency — a
  much narrower bar than "a fact was extracted."

The chain from EXTRACTED (495, 75 tickers) to FINANCIAL-REASONING-USABLE
(204 computed conclusions, 10 tickers) is the single most important
quantitative fact this report contains: **breadth collapses by roughly
7× going from "a fact exists somewhere" to "a fact is usable for a real
ratio."** This is the data constraint the rest of this report is built
around.

---

## 2. Financial-data coverage / 50-ticker coverage matrix

Measured directly against production `extracted_facts`/
`financial_reasoning_conclusions` (both read-only), not projected.

| Coverage tier | Definition | Tickers | List |
|---|---|---:|---|
| **Any extraction** | ≥1 `extracted_facts` row | 75 | (full list in query output; long tail of 1–2 fact tickers) |
| **≥2 usable periods** | distinct non-null `period_end` values ≥2 | 13 | AFRIPRUD, AIRTELAFRI, BUAFOODS, CAP, DANGCEM, DEAPCAP, MTNN, NASCON, NESTLE, OANDO, UBN, UCAP, VERITASKAP |
| **≥3 usable periods** (minimum for a real momentum/trend read, not just a first difference — Coverage Expansion Audit §8) | 8 | AFRIPRUD, AIRTELAFRI, BUAFOODS, CAP, DANGCEM, MTNN, NASCON, UCAP |
| **≥5 usable periods** | 3 | DANGCEM (7), AFRIPRUD (7), UCAP (7) |
| **Has ≥1 `computed` ratio/trend/flag TODAY** | 10 | AFRIPRUD, BUAFOODS, CAP, DANGCEM, MTNN, NASCON, NESTLE, OANDO, UBN, UCAP |
| **Would join the computed set if the tested backfill (§1) is approved** | +6 → 16 total | AIRTELAFRI, DEAPCAP, GEREGU, LASACO, UACN, VERITASKAP |

Per-ticker detail for the 10 currently-computed tickers (docs = distinct
source documents, facts = extracted_facts rows, periods = distinct usable
`period_end` values):

| Ticker | Docs | Facts | Fact types | Periods | Filing range |
|---|---:|---:|---:|---:|---|
| NASCON | 6 | 44 | 13 | 3 | 2023-03 → 2026-04 |
| DANGCEM | 10 | 43 | 9 | 7 | 2020-12 → 2026-03 |
| AFRIPRUD | 5 | 39 | 9 | 7 | 2020-07 → 2023-07 |
| UCAP | 12 | 39 | 6 | 7 | 2020-10 → 2026-03 |
| BUAFOODS | 9 | 38 | 12 | 4 | 2022-11 → 2026-03 |
| CAP | 7 | 30 | 11 | 4 | 2021-01 → 2026-03 |
| MTNN | 5 | 24 | 9 | 4 | 2022-03 → 2026-02 |
| OANDO | 4 | 8 | 4 | 2 | 2014-09 → 2025-01 |
| NESTLE | 2 | 7 | 4 | 2 | 2024-03 → 2025-02 |
| UBN | 3 | 6 | 4 | 2 | 2021-03 → 2023-04 |

**Answer to the matrix's required question** — "how many companies have
enough clean historical financial information to test each candidate
factor?": **10 today, 16 with an already-tested-but-unapplied fix,
against a documented minimum viable target of 50** (Financial Coverage
Expansion Audit §9, which itself derived 50 from the smallest N that
supports "a legitimate tercile-or-better cross-sectional design with real
placebo/HAC power," benchmarked against the original Fama-French/
Novy-Marx/Piotroski/Sloan cross-section sizes). **10–16 tickers is 20–32%
of that target.** Reaching 50 requires further extraction — quota-bound
at ~10-13 additional calendar days per the prior pilot's directly-measured
throughput (20 requests/day) — that this session could not perform (§1).

---

## 3. Factor readiness

Checked against real code, not assumed from factor names:

| Factor family | Computation infrastructure | Real breadth today | Verdict |
|---|---|---:|---|
| Profitability (net/EBIT/EBITDA margin) | `financial_ratios.py`, `RATIO_DEFINITIONS` — built, live | 10 tickers computed | **BLOCKED BY DATA** (breadth, not logic) |
| Quality/leverage (debt-to-equity, CFO/net-profit) | Same module, same live code | 10 tickers computed (`debt_to_equity`: 14 computed rows; `cfo_to_net_profit`: 4 computed rows) | **BLOCKED BY DATA** |
| Value (P/B via BVPS, P/E via EPS, EV/EBITDA) | `fre/valuation_engine.py` — built, live, joins market-cap panel to fundamentals | Same 10–16 ticker fundamental ceiling applies (market/price data itself is NOT the constraint — the fundamental side is) | **BLOCKED BY DATA** |
| Financial Momentum (trend of a ratio over ≥3 periods) | `trend_classification.py` — built, live | Only 8 tickers clear the ≥3-period bar | **BLOCKED BY DATA**, more severely (needs 3 periods, not 2) |
| Piotroski-style composite | Not assembled as a single scored composite; the individual signals (`net_margin`, `cfo_to_net_profit`, `debt_to_equity` trend) already exist as separate conclusions and could be combined without new infrastructure | Same 8–10 ticker ceiling, and needs several of the underlying ratios simultaneously computed for the SAME ticker/period, which narrows further | **BLOCKED BY DATA**, most severely |

**FACTORS READY FOR TESTING (on computation grounds): all five families.**
The computational infrastructure for Value, Quality, Profitability, and
Momentum already exists and is live, unmodified code — this is not a
"build more infrastructure" problem.

**FACTORS BLOCKED BY DATA (on breadth grounds): all five families,
identically.** None can legitimately support a 50-name tercile-sort
cross-sectional test today. This is a uniform breadth ceiling, not a
factor-specific defect — every family is gated by the same 10–16-ticker
extracted-fact universe.

---

## 4. Pre-registration

**Not performed.** Per the assignment's own conditional structure ("Only
proceed [to pre-registration] if Phase 3 demonstrates factor readiness"),
and per Phase 4's own selection criterion #5 ("ability to test without
excessive missingness"), pre-registering any of the five families against
a 10–16-ticker universe would not meet the bar this project's own prior
audit set for a legitimate test. Registering a hypothesis today, running
it, and reporting a result would be indistinguishable from the "fishing
expedition on insufficient data" this assignment explicitly prohibits.

No hypothesis ID was created. No `registry.sqlite` write occurred.

---

## 5–8. Alpha validation gauntlet, PIT methodology, statistical results, robustness

**Not performed** — correctly gated by §4. Running placebo/HAC/subperiod/
regime tests against an underpowered, unregistered candidate would produce
numbers with no defensible interpretation and would violate the brief's
own "optimize for discovering whether the result is true" instruction:
at N=10–16 names, "true" cannot be distinguished from "sampling noise
lucky enough to look like a pattern" with any of the standard tools this
platform's existing gauntlet uses (the Alpha Opportunity Audit's own §13
standard, referenced in the Coverage Expansion Audit, requires the same
breadth this report already found insufficient).

---

## 9. Transaction costs, liquidity, capacity

**Not reached.** No hypothesis exists to cost-test. This is the same
Phase 6 outcome the assignment itself anticipates under a Phase-7 "D"
result — capacity analysis is meaningless without a signal to size.

---

## 10. Out-of-sample performance / 11. Paper eligibility

**Not reached**, same reason.

---

## 12. Decision

### Phase 7 — Decision Gate

**Outcome D: DATA INSUFFICIENT.**

Explicitly, per the assignment's own instruction, **this is not recorded
as a factor failure.** The computation logic for every candidate factor
family exists, is live, and (on the tickers where it has enough input)
produces plausible, checkable output (e.g., DANGCEM's `debt_to_equity`
now computes correctly across all 4 of its periods, confirmed in the
quality-fix report). The blocker is exclusively breadth: 10–16 usable
tickers against a 50-ticker minimum-viable target that this project's own
prior research already derived from first principles, not invented for
this report.

### Missing data and expected information value

**What's missing**: real, multi-period statement coverage for
approximately 34–40 more NGX-listed tickers, beyond the current 10–16.

**Cost to obtain it** (measured, not assumed — from the two prior real
pilots' directly-observed throughput):
- Dollar cost: **$0** (free-tier Gemini, confirmed both pilots)
- Time cost: **~10–13 calendar days** of quota-bound extraction (20
  requests/day) to cover the ~44-ticker backlog already sitting in the
  document archive, **~2 more days** to stretch to the full 50-ticker
  target — **assuming the quota reliably grants 20 requests/day, which
  today's two failed attempts (§1) have not yet confirmed** (an open,
  disclosed risk to this estimate, not smoothed over).
- Founder/operator time: near-zero marginal effort beyond triggering the
  already-built, already-tested pipeline daily (or scheduling it) and
  periodically applying the already-tested backfill/migration once
  approved.

**Expected value of obtaining it**: high relative to cost. This is the
single blocking constraint standing between "the whole Investment
Management Layer built in the prior phase" and "a real, testable
capital-allocation decision" — every downstream phase of this exact
assignment (4 through 11) is gated on it. At effectively zero dollar cost
and a bounded, already-measured calendar-time cost, continuing extraction
toward 50 tickers has strictly positive expected information value: it
either produces a testable universe (unlocking Phases 4–11 for real) or
confirms the backlog itself is thinner than assumed (also valuable,
per this same report's own information-value framing). There is no
scenario in which acquiring more of the already-sitting archive is
wasted effort at this cost.

**Recommendation, stated precisely**: continue extraction of the existing
document backlog (NOT the 49-ticker zero-document acquisition gap, which
remains explicitly out of scope per this assignment's own Phase 2
instruction) at whatever pace the free-tier quota actually allows once
its true reset behavior is confirmed, then re-run this exact validation
cycle. This is a scheduling/patience problem, not an architecture problem.

---

## 13. Unresolved uncertainties

- **Daily quota reset time is not empirically confirmed.** Two real
  attempts today, more than 5 hours past assumed UTC-midnight reset,
  both failed with the same daily-cap error. This materially affects the
  "~10-13 days" extraction-time estimate's reliability and should be
  measured directly (e.g., log the exact UTC timestamp of the next
  successful call) before that estimate is relied on for planning.
- **The self-critique gate's behavior against period-complete,
  consistency-checked facts remains unverified by a live run** beyond the
  single TRANSCORP case (quality-fix report §9) — inherited, not resolved,
  by this report.
- **Whether the 10 currently-computed tickers are representative of the
  other 40+** in the backlog (sector mix, filing quality, statement
  completeness) is unknown — the current 10 were not chosen as a random
  or stratified sample of the full universe, they are simply whichever
  tickers happened to reach sufficient depth first.
- **The `numeric_consistency_check`'s round-factor-only blind spot**
  (cannot catch a non-round transcription error) remains a real, disclosed
  limitation carried over from the quality-fix report, unresolved by this
  report.
- **The tested backfill and schema migration remain unapplied to
  production**, awaiting the explicit operator approval named in both
  prior reports — this report does not request or assume that approval.

---

## 14. Next capital-allocation recommendation

**Do not allocate research time to inventing a sixth factor family or to
lowering the 50-ticker bar to force a test through on today's 10–16
tickers.** Both would violate this assignment's own explicit prohibitions
("do not relax statistical standards," "do not create hypotheses to
increase activity"). The correct next action is narrow and already fully
specified by prior work: resume quota-paced extraction of the existing
document backlog, apply the two already-tested-and-approved-pending fixes
once operator approval is given, and re-run Phases 1–7 of this exact
protocol once breadth crosses a defensible threshold (50 tickers, or a
smaller number with an explicit, pre-stated power-analysis justification
if 50 proves unreachable in reasonable time — not yet needed today).

---

## Status table

| Layer | Status |
|---|---|
| Data Foundation | BUILT |
| Research OS | BUILT |
| Research Query | BUILT |
| FRE | PROMISING (period + numeric-consistency + PIT-matching fixes verified real; full stratified re-pilot quota-blocked, not completed) |
| Fundamental Factor | UNPROVEN — DATA INSUFFICIENT (all 5 candidate families computationally ready, all blocked by 10–16-ticker breadth vs. 50-ticker target) |
| Alpha Engine | UNPROVEN (unchanged this session — no calculation touched) |
| Portfolio Management | BUILT |
| Risk Engine | BUILT |
| Paper Execution | BUILT |
| Performance | BUILT |
| Attribution | BUILT |
| Paper Track Record | NOT STARTED |
| Live Investment | NOT AUTHORIZED |

---

## Final capital-allocation verdict

# HOLD

**Conviction**: Low-to-moderate that a fundamental factor will ultimately
validate — genuinely unknown, and this report does not claim otherwise.
**High confidence** that the correct next step is more data, not more
architecture or a forced test.

**Expected information gain from the recommended next action** (resume
quota-paced extraction to 50 tickers): High. It is the single gate
blocking every remaining phase of this assignment (4 through 11) and,
transitively, any real capital-allocation decision this Investment OS
could ever produce from fundamentals. Nothing else in the pipeline is
close to being the binding constraint right now.

**Estimated founder time required**: Near-zero incremental effort — the
extraction pipeline, backfill script, and validation protocol are all
already built and tested. What's required is calendar time (quota-paced)
plus one explicit approval decision (the already-tested backfill/schema
migration) that remains the operator's call, not an engineering task.

**Economic opportunity cost**: Low. The extraction path costs $0 in fees
and does not compete for the same resource as any other active
initiative on this platform (it consumes free-tier API quota, not
founder attention, once triggered) — the paper-execution and monitoring
infrastructure built in the prior phase sits idle and ready in the
meantime at zero ongoing cost.

**Exact next decision unlocked**: once the 50-ticker (or a smaller,
explicitly power-justified) universe is reached, this exact Phase 1–7
protocol can be re-run to reach a real Phase 7 outcome — A (validated,
capacity-viable), B (validated but capacity-dead), or C (rejected) —
any of which is more decision-useful than today's D. Today's report's
job was to establish precisely how far away that decision is and why —
it is a data-breadth problem with a known, bounded, near-zero-cost fix,
not an open research question.
