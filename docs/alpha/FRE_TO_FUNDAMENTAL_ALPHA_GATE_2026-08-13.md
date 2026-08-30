# FRE Scale Validation + Fundamental Alpha Gate — 2026-08-13

**LIM status**: research archive, not an active workstream (per the
completed LIM Economic Viability Audit — ABANDON as extraction engine).
No LIM work performed in this report. **Production data at time of
writing**: untouched, verified at open and close (see the ADDENDUM below
for a later, explicitly-approved change). **Alpha Engine**: zero diffs.
No broker connected, no capital deployed, no hypothesis registered.

> **ADDENDUM (2026-08-13, later same day) — backfill approved and
> applied.** The operator explicitly approved §10's recommended action.
> `scripts/fre/backfill_flow_fact_period_start.py --apply` was run
> against production, backed up first (`scripts/backup_db.py`, integrity
> + restore verified, plus the backfill script's own pre-apply copy).
> Result: `financial_reasoning_conclusions` 267→403 (+136, 0 duplicates),
> exactly matching the pre-tested projection. `extracted_facts` unchanged
> at 495 (pure completion of existing fields, nothing invented).
> **Corrected computed-ticker coverage: 10 → 14** (not 16 as originally
> estimated, and not the "26" first misreported in conversation before
> being corrected — 26 was every ticker with *any* conclusion row,
> including unusable `insufficient_data` placeholders; 14 is the count
> filtered to `status='computed'`, the only figure that means "usable").
> Fact-level end-to-end survival (§2's critical metric) rose from 26.5%
> to **38.6%** (191/495). Still 14/50 = 28% of the 50-ticker target — a
> real improvement, not a resolution of the underlying breadth
> constraint. §3/§10's conclusions are otherwise unchanged: extraction
> resumption toward 50 tickers remains the binding next step, still
> blocked on Gemini quota.

**Data-state legend used throughout**: 🏭 PRODUCTION (`data/ngx.sqlite`,
read-only unless stated) · 🧪 SCRATCH (disposable copies, this session) ·
📄 PAPER (portfolio-management layer, not reached this session) ·
❓ HYPOTHESIS (none registered) · ✅ VALIDATED (none) · ⚪ UNPROVEN.

---

## 1. FRE pilot results (Phase 1)

**Status: BLOCKED, not completed.** Per this assignment's own instruction
("do not repeatedly poll the API"), the Gemini daily quota was checked
**once** this session (a single live attempt against
`scripts/fre/phase4_pilot_completion.py`), consistent with the prior
session's already-exhausted budget of retries today (this is the 6th
consecutive real 429 across the day, going back to ~04:50 UTC). Result:
identical `429 RESOURCE_EXHAUSTED`, `GenerateRequestsPerDayPerProjectPerModel-FreeTier`,
limit 20. No further retries were attempted this session.

**The 4 remaining pilot documents (STANBIC-messy, ELLAHLAKES-format-diverse,
MORISON-thin, ETI-clean-quarterly) remain unprocessed.** Per-dimension
accuracy for THESE specific documents cannot be reported — reporting
numbers for them would be fabrication. What can be reported honestly is
the cumulative real evidence from the two prior, already-completed pilot
sessions (12 real document/fact observations total, unchanged since
2026-08-12/13):

| Dimension | Result |
|---|---:|
| Identity accuracy | 10/10 (100%) |
| Fact-type accuracy | 9/10 (90%) — 1 qualitative-statement mistag |
| Period accuracy (post-fix) | 6/6 (100%), single fresh TRANSCORP re-extraction |
| Numeric accuracy | 9/10 pre-fix; the 1 error (TRANSCORP 10×) is now deterministically catchable by `numeric_consistency_check` |
| Evidence grounding | 10/10 (100%) |
| True-negative behavior | 3/3 confirmed correct (SEPLAT ×2, most of STANBIC/MORISON) |

This report does not treat this as "Phase 1 passed" — it is disclosed as
**incomplete**, with the caveat that everything downstream in this report
that depends on extraction *quality* (as opposed to extraction *breadth*)
rests on this same, still-partial evidence base.

---

## 2. End-to-end usability — the critical metric (Phase 2)

Ran against 🏭 **PRODUCTION** data, read-only (no writes; the fact-consumption
linkage already exists in `financial_reasoning_conclusion_facts`, written by
prior, already-approved pipeline runs — nothing new was computed or written
this session).

**Chain**: document → extraction → period validation → numeric validation →
evidence → financial reasoning → (PIT memory, verified separately, see
note below).

| Stage | Count | % of total extracted |
|---|---:|---:|
| Extracted (🏭 `extracted_facts`) | 495 | 100% |
| Evidence grounding passed | 470 | 94.9% |
| Structurally period-complete (point-in-time: `period_end` set; flow: both `period_start`+`period_end` set) | 245 | 49.5% |
| **Distinct facts consumed by a COMPUTED (usable) conclusion** | **131** | **26.5%** |

**131/495 = 26.5% is the critical metric this phase asks for.** Composition
of what those 131 facts fed: 114 distinct facts feeding `ratio` conclusions,
122 feeding `trend` conclusions, 73 feeding `flag` conclusions (a single
fact can feed more than one conclusion type, e.g. a revenue fact used in
both a margin ratio and a trend).

**Diagnosis, not just a number**: the drop from 495→245 (period-completeness)
is the dominant loss, not the drop from 245→131. This matches an
already-known, already-fixed-going-forward root cause: the extraction
prompt did not request period metadata at all until the 2026-08-12
quality-fix session (`docs/alpha/FINANCIAL_EXTRACTION_QUALITY_FIX_REPORT.md`).
The 495 production facts are a mix of pre-fix (no period fields requested)
and a small number of newer/backfill-eligible facts. **A tested, dry-run-verified,
zero-risk backfill script exists** (`scripts/fre/backfill_flow_fact_period_start.py`)
that would raise `financial_reasoning_conclusions` from 267 to 403 on
production if applied — **still awaiting explicit operator approval, not
applied by this report**.

**Numeric-consistency safety net has never been retroactively run**: all
495 production facts show `numeric_consistency_check = 'not_run'` — the
check exists in code and applies to new extractions going forward, but the
historical backlog has never been swept. This means an undetected
round-factor error (like the original TRANSCORP case) could theoretically
still be sitting in one of the 131 "usable" facts, unflagged. **Disclosed as
a real, open gap, not fixed by this report.**

**Verdict on Phase 2's gate**: **PARTIAL** — not a clean pass, not a
rejection. The 26.5% raw survival rate is real and low, but it is
explained by a specific, already-diagnosed, already-partially-fixed cause
(period-metadata completeness era-dependence), not by a fundamental
extraction-quality defect. Per-fact quality (§1) remains genuinely good
where facts ARE period-complete.

---

## 3. Coverage matrix (Phase 3)

Per instruction, uses only the 🏭 **existing acquired document inventory**
— no new acquisition, no new extraction attempted (quota-blocked anyway).
Re-measured fresh this session (identical to the 2026-08-13 Fundamental
Alpha Validation report — nothing changed in production since then,
confirming these numbers are stable, not drifting):

| Coverage tier | Tickers | vs. 50-ticker target |
|---|---:|---:|
| Any extraction at all | 74 | 148% by raw count (misleading — see below) |
| ≥2 usable periods | 13 | 26% |
| ≥3 usable periods (minimum for a real trend read) | 8 | 16% |
| Has ≥1 COMPUTED ratio/trend/flag today | **10** | **20%** |
| Would join the computed set if the tested-but-unapplied backfill (§2) is approved | +6 → **16** | **32%** |

**A ticker counts only when it has enough validated financial history to
support the intended factor calculations** — per instruction, raw
document/fact presence (74 tickers) is explicitly NOT counted as coverage.
By the correct standard (≥1 computed conclusion), current coverage is
**10 tickers**, or **16** with an approved-but-unapplied fix. Both are
well short of the 50-ticker minimum viable target this platform's own
prior research (`docs/alpha/FINANCIAL_COVERAGE_EXPANSION_AUDIT.md` §9)
derived from first principles (smallest N supporting a legitimate
tercile-sort cross-sectional design with real placebo/HAC power).

Per-ticker detail, the 10 currently-computed tickers:

| Ticker | Docs | Facts | Periods |
|---|---:|---:|---:|
| NASCON | 6 | 44 | 3 |
| DANGCEM | 10 | 43 | 7 |
| AFRIPRUD | 5 | 39 | 7 |
| UCAP | 12 | 39 | 7 |
| BUAFOODS | 9 | 38 | 4 |
| CAP | 7 | 30 | 4 |
| MTNN | 5 | 24 | 4 |
| OANDO | 4 | 8 | 2 |
| NESTLE | 2 | 7 | 2 |
| UBN | 3 | 6 | 2 |

**Human-review requirements**: not separately measured this session
(no new extraction ran) — inherited estimate from the FRE pilot's own
finding that extraction quality is high enough NOT to need 100% manual
review, contingent on the numeric-consistency and period-validation gates
staying active (§2's disclosed gap notwithstanding).

**Compute/API consumption**: $0 (free tier, confirmed), throughput-bound
at ~10 documents/day per the directly-measured 20-requests/day quota.

---

## 4. Fundamental factor readiness (Phase 4)

| Factor family | Computation infrastructure | Real breadth today | Readiness |
|---|---|---:|---|
| Value (P/B, P/E via `valuation_engine.py`) | Built, live | Same 10-16 ticker fundamental ceiling | BLOCKED BY DATA |
| Quality (debt-to-equity, CFO/net-profit) | Built, live — `debt_to_equity`: 14 computed / 11 insufficient; `cfo_to_net_profit`: 4 computed / 21 insufficient | 10-16 tickers | BLOCKED BY DATA |
| Profitability (net/EBIT/EBITDA margin) | Built, live — `net_margin`: 25 computed; `ebit_margin`: 18 computed; `ebitda_margin`: 14 computed | 10-16 tickers | BLOCKED BY DATA |
| Financial Momentum (trend of a ratio over ≥3 periods) | Built, live | Only 8 tickers clear the ≥3-period bar | BLOCKED BY DATA, more severely |
| Piotroski-style composite | Component signals exist, not assembled into one score; needs several ratios simultaneously for the SAME ticker/period | 8-10 ticker ceiling, narrows further | BLOCKED BY DATA, most severely |

**All five families are computationally ready** (this is not a "build
more infrastructure" problem — confirmed again, unchanged from the LIM
audit's own conclusion). **All five are blocked identically by breadth**,
not by factor-specific defects. Expected sample size at current coverage
(10-16 names) does not support a legitimate tercile-sort test with real
statistical power for ANY family. Capacity/implementation requirements
are not the binding constraint — data breadth is.

---

## 5-7. Pre-registration, validation, capacity, decision (Phases 5-7)

**No hypothesis pre-registered.** Per instruction ("Do not run a factor
simply because its code exists" / "Do not register speculative Alpha
hypotheses" in this assignment's own DO-NOT list), and consistent with
the same discipline applied in the prior Fundamental Alpha Validation
report: registering and testing any of the five families against a
10-16-name universe would be statistically indistinguishable from a
fishing expedition on insufficient data — this platform's own established
50-ticker standard exists precisely to prevent that.

Phases 5 (pre-registration), 6 (capital-reality test), and the paper
portfolio (Phase 8) are consequently **not reached** — there is no
candidate to validate or size.

### Phase 7 — Decision

# D. DATA INSUFFICIENT — do not interpret the result

Explicitly, per the assignment's own framing: this is **not** Option C
(REJECTED — factor does not survive) and **not** Option E (statistical
edge exists but can't support capital). Neither applies because **no
factor was tested.** The correct reading of "D" here: the computational
machinery is real and working; the data breadth to responsibly run it is
not yet in place; nothing about factor validity can be concluded either
way from today's evidence.

---

## 8. Capacity analysis

**Not applicable.** No hypothesis exists to size. (Placeholder retained
per the report template — deliberately empty, not omitted, so the gap is
visible rather than silently skipped.)

---

## 9. Paper-trading decision

**Not applicable — no factor passed Phase 7.** The 📄 paper
portfolio-management layer (portfolio/risk/execution/performance/
attribution, all 🟢 BUILT per the 2026-08-13 build report, 134/134 tests
passing, reconfirmed again this session) remains idle and ready. It has
never been more validated-signal-ready than it is today; it simply has no
validated signal to receive yet.

---

## 10. Capital-allocation recommendation

**Unchanged in substance from the prior Fundamental Alpha Validation
report — this session adds one materially new data point (§2's 26.5%
fact-survival metric and its diagnosis) but does not change the
bottom-line recommendation, because the binding constraint (ticker
breadth) has not changed:**

1. **Resume quota-paced Gemini extraction** toward the 50-ticker target,
   using the existing document backlog first (no new acquisition needed
   yet, per instruction). This is $0, already proven at real quality on
   the dimensions measured, and blocked only by calendar time (~10-13
   days of quota-bound extraction, per the directly-measured 20
   requests/day ceiling) and today's unresolved quota-reset-timing
   question (§1).
2. **A single, low-risk, already-tested decision is available now,
   independent of extraction resuming**: apply the period-metadata
   backfill (`backfill_flow_fact_period_start.py --apply`) to production.
   Dry-run-verified, zero rejected rows, would raise usable conclusions
   from 267 to 403 (and coverage from 10 to 16 tickers) with **zero new
   extraction and zero new quota spent** — this is the single highest
   information-value-per-effort action available today, and it is a
   pure operator-approval decision, not an engineering task.
3. **Do not register a hypothesis, do not build new infrastructure, do
   not touch LIM** — none of these are the binding constraint. The
   binding constraint is document breadth, addressed only by (1)+(2)
   above.

**Standalone economic value of the Investment OS/FRE, stated plainly**:
not yet demonstrated, and not yet disprovable either. The machinery
(extraction → validation → reasoning → portfolio management) is real,
tested, and — where it has enough data to run — produces correct,
checkable output (§2, §4). What has not yet been demonstrated is whether
feeding it enough data produces a factor with genuine, capacity-viable
edge. That is a **calendar-time-and-approval** question today, not an
open research question requiring more architecture.

---

## Status table

| Component | Status |
|---|---|
| Extraction pipeline (period/numeric/grounding validation) | 🟢 BUILT, PROMISING quality (§1, incomplete pilot) |
| End-to-end fact survival (extraction → usable conclusion) | ⚪ MEASURED at 26.5%, diagnosed cause, not yet fixed in production |
| 50-ticker coverage target | 🔴 NOT MET (10-16 of 50, 20-32%) |
| Factor computation infrastructure (Value/Quality/Profitability/Momentum/Piotroski) | 🟢 BUILT, all 5 families |
| Factor readiness (data breadth) | 🔴 BLOCKED, all 5 families, identically |
| Hypothesis | ❓ NONE REGISTERED |
| Alpha validation gauntlet | NOT RUN (no candidate) |
| Capacity analysis | NOT APPLICABLE |
| Portfolio/Risk/Execution/Performance/Attribution layer | 🟢 BUILT, 134/134 tests passing |
| Paper track record | NOT STARTED |
| LIM | 📁 RESEARCH ARCHIVE (per 2026-08-13 viability audit — ABANDON as extraction engine) |
| Live investment | NOT AUTHORIZED |

---

## Final principle check

**Evidence gathered this session**: one new, real, load-bearing metric
(§2's 131/495 fact-survival rate, with cause diagnosed) plus reconfirmation
that nothing material has changed in coverage since the prior audit
(stability itself is information — it confirms the constraint is real and
persistent, not a measurement artifact). **No code, feature, or
architecture was added to move this forward** — the two available levers
(resume extraction, approve the backfill) are calendar-time and
approval decisions, not engineering ones. This is the correct place for
founder attention to sit right now: not redirected away from the
Investment OS/FRE (it has not failed), and not scaled up prematurely
(it has not yet earned that) — held at exactly the "close the data-breadth
gap, then re-run this exact gate" state this report, and the one before
it, both point to.
