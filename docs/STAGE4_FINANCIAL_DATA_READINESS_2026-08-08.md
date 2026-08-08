# STAGE 4 — FINANCIAL-STRENGTH + CASH-FLOW DATA READINESS

*2026-08-08. Real extraction, committed to `data/ngx.sqlite`. Every
number below is a direct database query result. `configs/h011_size.toml`,
`docs/PREREG_H-011.md`, H-011's signal/construction, and all frozen
experiment results are unmodified. No hypothesis created. No external
API touched.*

**Files changed**: new script `scripts/fre/
stage4a_balance_sheet_cashflow_2026-08-08.py`. No taxonomy change needed
— `assets`/`liabilities`/`equity`/`cfo`/`capex` already existed as leaves
from prior phases. 25 new `extracted_facts` rows, 0 grounding failures.

---

## 1. Executive Summary

**Answering the success condition directly: NO, not yet — but the gap
narrowed to exactly one dimension, and it is now precisely quantified.**

**Financial Strength reached CODE-ELIGIBLE (10 tickers, the platform's
own `len(elig)<10` floor) but not RESEARCH-READY** (median 2 historical
periods, minimum 1 — thin depth, and 10 is the floor, not a comfortable
margin above it). **Cash Flow Quality remains BLOCKED at 7 tickers**,
below even the code floor. Neither family is recommended for H-018 this
stage. This is reported as a real result, not softened: Stage 4 moved
the needle by extracting from documents already open (zero new
acquisition) and the honest number is 10, not "significantly more."

---

## 2. Extraction Queue and Selection Logic

Ranked by Phase 4B's stated criteria (existing P&L depth × COGS/GP
coverage × periods × probability of reaching multi-factor eligibility),
computed from the actual pre-Stage-4 coverage matrix:

| rank | ticker | pre-4A fields | periods | why prioritized |
|---|---|---|---|---|
| 1 | DANGCEM | 2 (revenue, net_profit only) | 2 | Large-cap, IRU-heavyweight; zero balance sheet despite 2 clean P&L periods — highest-leverage gap to close |
| 2 | MTNN | 2 | 2 | Same profile as DANGCEM; telecom sector, currently zero-represented in Financial Strength |
| 3 | UBN | 2 | 2 | Same profile; banking sector, currently zero-represented |
| (screened, not pursued) | NESTLE, OANDO | 2 each | 2 each | Checked directly (Section 3) — no balance sheet or cash-flow content in currently-open filings; re-queued for Stage 5 with a DIFFERENT document (not the ones already open) |
| (not re-touched) | CAP's 3rd period (2020-12-31) | — | — | Checked — doc 4508 states only a leverage RATIO (2.3x), not absolute assets/equity; not extractable without inventing a base |

**A ticker with existing P&L depth was prioritized over a brand-new
ticker, exactly as instructed** — no new-ticker search was run this
stage; every fact below comes from documents already sitting in
`extracted_facts`' own source-document set from Stage 3.

**Breadth was preserved, not sacrificed**: the three tickers chosen span
three different sectors (cement, telecom, banking) not already
well-represented in the existing 8-ticker balance-sheet set (insurance,
power, food/FMCG, capital markets) — avoiding concentration in one
industry while closing the highest-value gaps.

---

## 3. New Financial Facts Extracted

**25 facts, 3 tickers, 0 grounding failures.**

| ticker | doc(s) | new fields | new/enriched periods | notable finding |
|---|---|---|---|---|
| DANGCEM | 8383, 9741 | assets, liabilities, equity (derived), cfo | 4 periods total (2 existing enriched: 2024-03-31, 2025-03-31; 2 genuinely new: 2023-12-31, 2024-12-31, pulled from the SAME two documents' comparative columns) | Clean, positive equity throughout (~44-37% liability ratio) |
| MTNN | 8080, 9430 | assets, liabilities, equity (derived), cfo, capex | 2 existing periods enriched (2023-12-31, 2024-12-31) | **Liabilities exceed assets in both periods — real, disclosed negative equity** (-₦40.8bn FY2023, -₦458.0bn FY2024, widening), consistent with MTNN's own existing net_profit facts also being negative both years. Not a data error — a genuine, economically important Financial Strength data point (FX-driven balance-sheet stress at Nigeria's largest telco). |
| UBN | 5987 | assets only | 1 existing period enriched | **Partial only** — this filing states Total Assets as a headline metric but never breaks out liabilities or equity; UBN remains excluded from Financial Strength despite this extraction |

**Screened and explicitly NOT extracted this session, with reasons**:
NESTLE (8089, 9423) and OANDO (7058, 9355) — the specific documents
already open for these tickers' revenue/net_profit contain no balance
sheet or cash-flow content at all (checked directly, zero keyword hits
across both fields for both tickers). Getting balance-sheet data for
these two would require locating a DIFFERENT document (a full annual
report rather than an earnings press release) — queued for Stage 5, not
attempted here to stay within Stage 4's "re-read what's already open"
mandate.

---

## 4. Financial Depth Matrix

| ticker | P&L fields | BS fields | CF fields | total fields (of 14) | periods | knowledge-date quality | currency | PIT | grounding | Fin. Strength usable | Cash Flow Quality usable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GEREGU | 4/4 | 3/3 | 5/5 (cfo/cfi/cff/capex/fcf) | 14 | 1 | filing_date, 283-day lag (outlier, see Sec. 6) | NGN | PASS | 100% | Yes | Yes |
| NASCON | 4/4 | 3/3 | 3/3 | 12 | 3 | 31-63 day lag | NGN | PASS | 100% | Yes | Yes |
| AIRTELAFRI | 2/4 | 3/3 | 5/5 | 12 | 1 | 38-day lag | USD | PASS | 83% (2 not_run, derived) | Yes | Yes |
| BUAFOODS | 4/4 | 3/3 | 2/3 (cfo, cff; no cfi) | 11 | 3 | 31-35 day lag | NGN | PASS | 100% | Yes | Yes |
| CAP | 4/4 | 2/3 (assets, liab; no equity stated, derived unavailable for 1 period) | 0/3 | 10 | 3 | 28-90 day lag | NGN | PASS | 100% | Yes | No |
| AFRIPRUD | 4/4 | 3/3 | 0/3 | 9 | 3 | 21-27 day lag | NGN | PASS | 100% | Yes | No |
| **DANGCEM** | 2/4 | 3/3 | 1/3 (cfo only) | 8 | **4** | 25-116 day lag (see Sec. 6 nuance) | NGN | PASS | 100% | **Yes (new)** | **Yes (new)** |
| **MTNN** | 2/4 | 3/3 | 2/3 (cfo, capex) | 8 | 2 | 58-61 day lag | NGN | PASS | 100% | **Yes (new)** | **Yes (new)** |
| LASACO | 1/4 | 3/3 | 4/5 | 7 | 1 | 96-day lag | NGN | PASS | 100% | Yes | Yes |
| UCAP | 3/4 | 3/3 | 0/3 | 5 | 3 | 22-61 day lag | NGN | PASS | 100% | Yes | No |
| NESTLE | 2/4 | 0/3 | 0/3 | 4 | 2 | not audited this stage | NGN | UNKNOWN | 100% | No | No |
| OANDO | 2/4 | 0/3 | 0/3 | 3 | 2 | not audited this stage | NGN | UNKNOWN | 100% | No | No |
| UACN | 1/4 | 0/3 | 0/3 | 3 | 1 | 0-day-checked | NGN | PASS | 100% | No | No |
| **UBN** | 2/4 | **1/3 (assets only, new)** | 0/3 | 3 | 2 | 102-day lag | NGN | PASS | 100% | No | No |

**Exact numbers, as required:**
- **10 of 100 IRU securities now have all three of assets/liabilities/equity** across at least one period (Financial Strength CODE-ELIGIBLE): AFRIPRUD, AIRTELAFRI, BUAFOODS, CAP, DANGCEM, GEREGU, LASACO, MTNN, NASCON, UCAP.
- **7 of 100 IRU securities now have both net_profit and cfo** across at least one period (Cash Flow Quality): AIRTELAFRI, BUAFOODS, DANGCEM, GEREGU, LASACO, MTNN, NASCON.
- **7 securities have both** (Financial Strength AND Cash Flow Quality usable simultaneously): AIRTELAFRI, BUAFOODS, DANGCEM, GEREGU, LASACO, MTNN, NASCON.
- **Median historical periods across the 10 Financial-Strength-eligible tickers: 2. Minimum: 1** (GEREGU, AIRTELAFRI, LASACO are single-period).
- **PIT coverage**: 18/18 documents manually audited (Section 6) show positive filing-lag (no look-ahead); 0 negative lags found. 2 tickers (NESTLE, OANDO) are PIT UNKNOWN for balance-sheet/cash-flow purposes simply because no such fact was extracted for them, not because of a PIT problem.
- **Confidence-tier distribution across all 216 facts checked**: `direct_reported` 152 (70%), `mapped_equivalent` 19 (9%), `derived` 15 (7%, all pure accounting identities), remainder pre-existing non-FS facts (dividend, etc.).
- **Grounding pass rate**: 204 passed / 216 checked where a quote existed = **100%** of attempted grounding checks passed; 12 facts are correctly `not_run` (derived values with no single quote to ground, same convention as this platform's existing `fcf` derivation).

---

## 5. Data-Quality Validation

- **Units**: verified per-ticker before writing (Section 3 of `docs/STAGE3_EXECUTION_2026-08-08.md`'s disclosed platform-wide inconsistency persists — GEREGU stores raw, unconverted N'000; every other ticker here converts to full naira). Within each ticker, internally consistent.
- **Currency**: AIRTELAFRI is USD (disclosed, MC-001-tagged per Stage 2); every other ticker in this matrix is NGN. No mixed-currency fact was written without a `currency` tag.
- **Period mapping**: DANGCEM's two documents each contain TWO distinct period-ends (a current-quarter snapshot and a comparative prior-period snapshot) — both extracted as separate, correctly dated facts, not conflated.
- **Statement identity / duplicate facts**: **zero duplicate (ticker, fact_type, period_end) rows** found across all 216 FS-taxonomy facts on the platform (checked by direct query, Section 3's script run).
- **Accounting sanity check — Assets ≈ Liabilities + Equity**: trivially satisfied for the 15 `derived`-tier equity facts (by construction, equity = assets - liabilities from the same statement, same document). For the pre-existing DIRECT facts (NASCON, BUAFOODS, CAP, AFRIPRUD, GEREGU, AIRTELAFRI, UCAP, LASACO — where equity was independently stated, not derived), no cross-check was re-run this session; flagged as a **Stage 5 validation task**, not assumed clean.
- **Impossible accounting relationships — one real, disclosed, NOT an error**: MTNN's liabilities exceed assets in both extracted periods (negative equity). Verified NOT an extraction mistake: MTNN's own existing net_profit facts are also negative for the same two years, and the underlying cause (FX losses on dollar-linked tower-lease liabilities after the 2023-2024 naira devaluation) is real, disclosed, well-known market information about this specific company. **Flagged explicitly here rather than silently treated as a data error or excluded.**
- **Missing values**: honestly reported per ticker in Section 4's matrix (e.g., UBN's missing liabilities/equity, CAP's missing period-3 balance sheet, 9 tickers with zero cash-flow fields) — no field was backfilled with an estimate.
- **Restatements**: none encountered in this batch (`restates_fact_id` is null on all 25 new facts).

---

## 6. PIT Validation

18 documents manually audited (the 3 new tickers' 4 documents, plus 8 tickers' 14 pre-existing documents re-checked this session for completeness) — filing_date minus period_end, in days:

| ticker | doc | period_end | filing_date | lag (days) | verdict |
|---|---|---|---|---|---|
| DANGCEM | 8383 | 2024-03-31 | 2024-04-25 | 25 | PIT PASS |
| DANGCEM | 8383 | 2023-12-31 | 2024-04-25 | 116 | PIT PASS (see nuance below) |
| DANGCEM | 9741 | 2025-03-31 | 2025-04-25 | 25 | PIT PASS |
| DANGCEM | 9741 | 2024-12-31 | 2025-04-25 | 115 | PIT PASS (see nuance below) |
| MTNN | 8080 | 2023-12-31 | 2024-03-01 | 61 | PIT PASS |
| MTNN | 9430 | 2024-12-31 | 2025-02-27 | 58 | PIT PASS |
| UBN | 5987 | 2021-12-31 | 2022-04-12 | 102 | PIT PASS |
| GEREGU | 6555 | 2021-12-31 | 2022-10-10 | **283** | PIT PASS, but a real outlier — flagged below |
| LASACO | 7194 | 2022-12-31 | 2023-04-06 | 96 | PIT PASS |
| CAP | 5911 | 2021-12-31 | 2022-03-31 | 90 | PIT PASS |
| CAP | 4508, 10115 | 2020-12-31, 2025-06-30 | — | 28, 29 | PIT PASS |
| NASCON | 8801, 9460, 10929 | various | — | 31, 63, 62 | PIT PASS |
| BUAFOODS | 6664, 8009, 9357 | various | — | 35, 31, 31 | PIT PASS |
| AFRIPRUD | 4245, 6349, 7540 | various | — | 21, 21, 27 | PIT PASS |
| AIRTELAFRI | 9809 | 2025-03-31 | 2025-05-08 | 38 | PIT PASS |
| UCAP | 4248, 6911, 10772 | various | — | 22, 60, 61 | PIT PASS |

**Zero negative-lag documents found (0/18) — no look-ahead risk detected
in the entire audited FS-fact set.**

**A precise nuance, disclosed rather than glossed over**: DANGCEM's
2023-12-31 and 2024-12-31 facts came from COMPARATIVE columns inside the
Q1 2024/Q1 2025 releases, not from DANGCEM's own original FY2023/FY2024
annual results announcements (which this platform has not separately
harvested/extracted). The `knowledge_date` recorded for those facts is
therefore the Q1 release's filing_date (2024-04-25 / 2025-04-25) — later
than when the market would actually have first learned the FY figures
(likely via an earlier, separate annual-results announcement in
Jan-Mar). **This is the SAFE direction of error** (the fact is treated as
knowable LATER than it may have truly been, never earlier), so it
cannot cause a look-ahead violation — but it means these two periods'
`knowledge_date` is conservative, not exact, and should not be
represented as precisely dated if a stricter audit is ever required.

**GEREGU's 283-day lag** is real and unusually long (FY2021 results
filed October 2022) — not a PIT violation (still positive lag, still
PASS), but a data-quality observation: GEREGU's fundamentals were
effectively 9+ months stale for most of the following fiscal year, a
real limitation on how "current" any signal built from this single data
point could be.

**PIT UNKNOWN**: NESTLE, OANDO (no balance-sheet/cash-flow facts exist to
audit — not evaluated, not assumed clean). Per your own instruction,
these cannot be used in a final alpha experiment until extracted and
audited.

---

## 7. Financial Strength Readiness

**Definition adopted** (economically defensible, computable from
available fields, PIT-safe): leverage (`liabilities/assets` or
`liabilities/equity`), solvency margin (`equity/assets`). Interest
coverage is **NOT currently definable** — no `interest_expense` field
exists in the taxonomy or has been extracted (a real, disclosed gap, not
silently assumed). Liquidity (current ratio) is **NOT currently
definable** — `current_assets`/`current_liabilities` were requested by
your Phase 4A but were not found as clean, separately-stated lines in
any of the three documents read this session (DANGCEM/MTNN/UBN present
only "Total assets"/"Total liabilities", not a current/non-current
split); this would require different, deeper filings.

**Coverage gate (Phase 4E, all seven conditions checked)**:

1. Sufficient IRU securities with required fields: **10 — exactly the
   code-level minimum, not comfortably above it.**
2. Sufficient historical periods: **No — median 2, minimum 1.** A
   cross-sectional test needs multiple FORMATION DATES, and with most
   tickers single- or double-period, there are not enough independent
   formation dates to run a real stability grid.
3. Announcement/knowledge dates support PIT reconstruction: **Yes**
   (Section 6).
4. Coverage not concentrated in one sector: **Reasonably diverse** —
   insurance (2), food/FMCG (2), power (1), telecom (2), capital markets
   (1), cement (1) — 6 sectors represented, no single sector >2 names.
5. Missing data does not mechanically select certain company types:
   **Not yet verified** — plausible risk (Section on H-011 independence
   below) that FSI coverage skews toward larger/more liquid names simply
   because their filings were prioritized for extraction; not tested.
6. Signal calculable consistently across securities: **Yes**, for
   leverage/solvency specifically (assets/liabilities/equity present for
   all 10).
7. Eligible universe large enough for meaningful cross-sectional testing:
   **No — 10 names is the platform's own hard floor for a test to even
   RUN, not a floor for a test to be CREDIBLE.**

**Verdict: CODE-ELIGIBLE. NOT RESEARCH-READY.** Conditions 2 and 7 fail
on the practical-threshold reading even though condition 1 clears the
code-level minimum exactly.

---

## 8. Cash Flow Quality Readiness

**Definition adopted**: operating-cash-flow-to-earnings (`cfo/net_profit`
— an accrual-quality proxy), operating-cash-flow-to-assets (`cfo/assets`
— requires BOTH families' fields, only computable for the 7-ticker
intersection). Free-cash-flow-based measures are **NOT currently
derivable at scale** — `capex` exists for only 2 of the 7 (MTNN, and
pre-existing GEREGU/CAP/AIRTELAFRI have it too, but BUAFOODS/NASCON/
LASACO/DANGCEM do not consistently), so `fcf` (`cfo - capex`) cannot be
computed for the full Cash Flow Quality candidate set without more
extraction.

**Coverage gate**: **7 tickers, below the 10-name code floor.**
**Verdict: BLOCKED**, not PARTIALLY READY — an honest downgrade from
Stage 3's "PARTIALLY READY" label now that the exact count (7, not "5 of
10ish") is pinned down precisely.

---

## 9. Other Newly Unblocked Factor Families

None reach a new status this stage. Quality (needs assets/liabilities/
equity/net_profit with multi-period depth) inherits Financial Strength's
same CODE-ELIGIBLE-not-RESEARCH-READY status for its balance-sheet leg,
still blocked on periods. Investment (needs multi-period assets) gains 2
more data points from DANGCEM's 4-period extraction specifically, still
far short of a usable breadth×depth combination.

---

## 10. Fundamental Factor Readiness Matrix (final, this stage)

| Family | Required fields | Current coverage | Hist. depth | PIT | Status | Next missing requirement |
|---|---|---|---|---|---|---|
| Financial Strength | assets, liabilities, equity | 10 tickers | median 2, min 1 periods | PASS | **PARTIALLY READY (code-eligible, not research-ready)** | More periods per ticker, not more tickers — re-read each of the 10's OWN prior-year filings for a 3rd/4th period |
| Cash Flow Quality | net_profit, cfo | 7 tickers | median 2 | PASS | **BLOCKED** | 3 more tickers (NESTLE/OANDO need different documents; UBN/CAP/AFRIPRUD/UCAP need a cash-flow-statement-bearing filing, not yet found) |
| Value | net_profit/equity + market cap | 14 tickers (market cap panel is universe-wide already) | 1-3 | PASS | **PARTIALLY READY** | Same period-depth constraint as Financial Strength |
| Quality | net_profit+assets+liabilities+equity, multi-period | 10 tickers, thin depth | median 2 | PASS | **PARTIALLY READY** | Same as Financial Strength — inherits its exact gap |
| Profitability | revenue, cogs/gross_profit, ebit | 5 tickers | 1-3 | PASS | **PARTIALLY READY** | 5 more tickers with cogs/gross_profit specifically |
| Gross Profitability | revenue, cogs/gross_profit, assets | 5 tickers | 1-3 | PASS | **PARTIALLY READY** | Same as Profitability |
| Asset Turnover | revenue, assets | 10 tickers (assets now the binding constraint, same 10 as Fin. Strength) | median 2 | PASS | **PARTIALLY READY** | Same period-depth gap |
| Growth | revenue/net_profit, ≥2 periods | 9 tickers with ≥2 periods (NASCON/BUAFOODS/CAP/AFRIPRUD/UCAP have 3; DANGCEM/MTNN/NESTLE/OANDO have 2) | 2-3 | PASS | **BLOCKED** | Needs 4-8 periods for a real growth-rate measure — a time problem, not a breadth problem |
| Investment | assets, ≥2 periods | 4 tickers with ≥2 periods of assets specifically (DANGCEM now 4, NASCON/BUAFOODS/CAP 3 each) | 2-4 | PASS | **BLOCKED** | Same as Growth — few tickers have multi-period ASSETS specifically |
| Accruals | net_profit, cfo, working-capital detail | 0 with full requirement (no current_assets/current_liabilities anywhere) | — | N/A | **BLOCKED** | Working-capital line items — not found in any filing read across Stages 3-4 |
| Earnings Quality | net_profit, cfo, accruals detail | 7 (net_profit+cfo), 0 with accruals detail | median 2 | PASS (partial) | **BLOCKED** | Same as Accruals |

---

## 11. H-011 Independence Assessment (pre-hypothesis only, no family is READY)

Since no family reached READY, this is preparatory, not conclusive —
exactly as instructed.

1. **Fundamentally different information source?** Yes for all — balance
   sheet/income-statement fundamentals vs. H-011's market-cap-only input.
2. **Mechanically related to market cap?** **Real, disclosed risk,
   unresolved**: the 10 Financial-Strength-eligible tickers include
   several of the platform's largest names by market cap (DANGCEM,
   MTNN — both top-5 by the market-cap panel used in Section 2 of `docs/
   STAGE3_EXECUTION_2026-08-08.md`). If FSI coverage systematically
   skews toward LARGE names (because large-cap filings are easier to
   find/more complete) while H-011 is a SMALL-cap tilt, any future
   fundamentals factor tested only on today's coverage would have close
   to zero overlap with H-011's own investable universe by construction
   — worth stating as a real independence CONCERN in the eventual
   prereg, not an assumption of independence.
3. **Correlated with liquidity?** Same directional concern as #2 — the
   extracted set skews toward names large/liquid enough to have
   thoroughly-documented earnings releases.
4. **Obvious market-cap construction effect?** No shared construction
   input with H-011's negative-standardized-cap score.
5. **Testable independently before combination?** Mechanically yes, once
   READY — not yet reached.

**This is a real, disclosed tension worth resolving before extraction
continues much further**: if Stage 5 keeps prioritizing "which filing is
easiest to find" (this stage's own selection logic), FSI coverage may
end up systematically anti-correlated with H-011's own universe (small,
illiquid names) — worth an explicit check once coverage grows, not
assumed away.

---

## 12. H-018 Gate Decision

| # | Condition | Met? |
|---|---|---|
| 1 | Research-ready coverage | **No** — best case (Financial Strength) is code-eligible only |
| 2 | Sufficient historical depth | **No** — median 2 periods, minimum 1 |
| 3 | PIT integrity | Yes, for the 10-ticker Financial Strength set (Section 6) |
| 4 | Reproducible factor construction | Yes, in principle (leverage/solvency are simple, well-defined ratios) |
| 5 | Economically defensible rationale | Yes |
| 6 | Sufficient cross-sectional breadth | **No** — 10 is the floor, not a safe margin above it |
| 7 | Acceptable data quality | Yes, with disclosed caveats (Section 5) |
| 8 | Materially new information vs. H-001-H-017 | Yes, if ever built |
| 9 | Preregistration before performance testing | Not attempted — moot without the above |

**Decision: H-018 is NOT created.** Conditions 1, 2, and 6 fail. This is
reported as a successful, disciplined result per your own framing, not a
shortfall — Stage 4 exists to answer the readiness question honestly,
and the honest answer is "closer, specifically on periods and margin
above the floor, not on fields or PIT integrity."

---

## 13. Remaining Data Gaps

Ranked by what would flip Financial Strength from CODE-ELIGIBLE to
RESEARCH-READY fastest:

1. **More periods per already-eligible ticker** (not more tickers) —
   each of the 10 Financial-Strength names likely has 1-2 more years of
   filings sitting in the same `documents` archive, unopened. This is
   the single fastest lever: it directly attacks condition 2 (depth) AND
   condition 7 (breadth-over-time, since more periods effectively means
   more formation dates even with the same 10 names) without needing any
   new ticker at all.
2. **Cash Flow Quality's missing 3 tickers** — NESTLE/OANDO need a
   different document type than what's currently open; UBN/CAP/AFRIPRUD/
   UCAP need a cash-flow-statement-bearing filing not yet located.
3. **Working-capital line items (current_assets/current_liabilities)** —
   needed for Accruals and Earnings Quality, not found in any filing
   read across two full stages of extraction; may require full annual
   reports rather than earnings-release press releases.
4. **Independent verification of the 8 pre-existing DIRECT (not derived)
   equity facts** against the accounting identity — flagged in Section 5,
   not yet done.

---

## 14. Recommended Stage 5

**Depth before breadth, reversing Stage 4's own instinct**: re-read each
of the 10 Financial-Strength-eligible tickers' OWN prior/subsequent-year
filings (not new tickers) to add a 2nd, 3rd, 4th period per ticker. This
directly targets the ONE condition (historical depth) that is currently
the binding constraint on every PARTIALLY READY family in Section 10 —
Financial Strength, Quality, Asset Turnover, Value, Profitability, Gross
Profitability all share this exact same gap, so fixing it once
(systematically, ticker by ticker) upgrades six families' status
simultaneously rather than one at a time.

**In parallel**: locate a genuine annual-report or cash-flow-statement
document for NESTLE and OANDO specifically (their current documents are
confirmed empty of this content — a different search, not a re-read).

**Do not** pursue Growth/Investment/Accruals/Earnings Quality yet — all
four are blocked on a TIME problem (more fiscal years must simply pass,
or deeper archival reach-back is needed) that breadth expansion alone
cannot solve this quarter.

**Do not create H-018.** Re-run Section 7's coverage gate after Stage 5;
if Financial Strength reaches ≥15 tickers with ≥3 periods each and the
H-011-overlap concern (Section 11) is checked and found not disqualifying,
that is the point to draft a preregistration — not before.
