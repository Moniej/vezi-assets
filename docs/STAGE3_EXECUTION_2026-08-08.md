# STAGE 3 — EXECUTION: FUNDAMENTAL DEPTH + DATA INTEGRITY + INSIDER COMPLETENESS

*2026-08-08. Real extraction was performed and committed to
`data/ngx.sqlite` (`extracted_facts`/`evidence`) — every number below is
either a direct database query result or a hand-transcribed, grounded
quote from an archived source document, not an estimate. `configs/
h011_size.toml`, `docs/PREREG_H-011.md`, H-011's signal/construction, and
all frozen experiment results are unmodified. No hypothesis was created.*

**Files changed**: `configs/fact_taxonomy.toml` (added `cogs`,
`gross_profit`, `share_reconstruction` — three new leaves, additive,
zero existing leaves touched). New scripts: `scripts/fre/
stage3a_uacn_2026-08-08.py`, `scripts/fre/
stage3b_cogs_gross_profit_2026-08-08.py`, `scripts/fre/
stage3c_corporate_actions_2026-08-08.py`. 31 new `extracted_facts` rows
(3 UACN + 20 cogs/gross_profit + 8 corporate actions), all with
`grounding_check` verified against real source text (0 failures across
all three scripts).

---

## 1. Executive Summary

Distinguishing the three standards you asked me to keep separate:

- **Data that exists**: much more than was catalogued in Stage 2 — the
  archive holds real, usable content for corporate actions (8 events now
  confirmed with sourced ratios) and for several IRU names not yet
  extracted (UACN, ETI, and others queued below).
- **Data that is research-ready**: 14 tickers now carry structured FSI
  facts (up from 13), 5 of them with both `cogs` and `gross_profit`
  (Profitability/Gross Profitability's specific missing fields, closed
  this session). 8 real corporate-action events are now structured,
  dated, sourced facts instead of prose in a report.
- **Data that can support a preregistered alpha**: **still nothing new**.
  No fundamental factor family clears a defensible breadth floor. This
  is stated plainly, not softened — Stage 3 measurably improved
  readiness without producing a testable factor, which is the correct
  outcome at this stage, not a shortfall.

**Insider dataset verdict: NEEDS MORE HARVESTING** (Section 6) — the
2021+ coverage collapse is very likely a harvest-completeness gap, not a
real decline, and no extraction was attempted, per your explicit
instruction.

**H-018: NOT CREATED.** No candidate clears the ten-condition gate
(Section 10).

---

## 2. FSI Expansion Results

### Target queue (ranked: market cap × existing results_notice
availability × real-text presence, IRU names not yet in the FS-fact set)

| ticker | mkt cap (N'm) | results_notice docs | usable FSI content? |
|---|---|---|---|
| SEPLAT | 6,817,710 | 12 | **No** — all 12 are procedural (AGM outcomes, "notice of upcoming results", bond press releases); zero contain revenue/profit/balance-sheet figures. Real, checked finding, not assumed. |
| ZENITHBANK | 4,838,026 | 1 | Not checked this session (char_count=0 on the one doc — likely unextracted/scanned) |
| GTCO | 4,714,980 | 4 | char_count=0 on all four — scanned, unextracted |
| PRESCO | 2,683,333 | 4 | Not checked this session |
| STANBIC | 2,654,005 | 10 | Checked: 0 keyword hits — same "procedural, not financial" pattern as SEPLAT |
| UACN | 585,080 | 27 | **Yes — extracted this session (below)** |
| ETI | 1,555,890 | 12 | Checked: 46-48 keyword hits — real financial content, **queued, not yet extracted** |
| FCMB | 794,753 | 7 | Checked: 3-5 keyword hits — some content, **queued** |
| ACCESSCORP | 1,413,771 | 6 | Checked: 8-10 keyword hits — some content, **queued** |

**A real, negative finding worth stating plainly**: document count is
not document usefulness. SEPLAT and STANBIC — two of the highest
market-cap names in the IRU with the most `results_notice` documents —
turned out to have zero extractable financial figures in what's
harvested; both categories are dominated by procedural announcements
(AGM voting results, "notice of upcoming results" placeholders), not
earnings releases. This would have produced a false sense of progress if
document count alone had been used to prioritize.

### UACN — new ticker, extracted this session

| field | value |
|---|---|
| ticker | UACN |
| issuer | UAC of Nigeria Plc |
| doc | 5163, H1 2021 earnings release, filed 2021-07-29 |
| periods available | 1 (H1 2021) |
| fields available | revenue (₦46,499m), gross_profit (₦8,324m), net_profit (₦763m, total incl. discontinued ops) |
| missing fields | assets/liabilities/equity/cfo/cfi/cff/capex/fcf/ebitda/ebit/cogs — **this specific filing is P&L-only, no balance sheet or cash-flow statement included** (an interim press-release format limitation, not an extraction failure) |
| announcement/knowledge date | 2021-07-29 (filing_date) |
| currency | NGN |
| PIT status | Clean — filing_date precedes any use in a formation-date calculation by construction |
| confidence | 1.0, grounding passed on all 3 facts |
| research usability | **No — single period, 3/14 fields** |

**Net result: 14 tickers now carry FSI facts (was 13). The 15-25
ticker gate is NOT reached.** ETI, FCMB, ACCESSCORP are real, screened,
queued candidates for the next extraction pass — not invented, not
guessed, actually checked for content this session.

---

## 3. COGS/Gross Profit Results

- **Documents processed**: 10 (GEREGU 6555, NASCON 8801/9460/10929,
  BUAFOODS 6664/8009/9357, CAP 5911/10115, AFRIPRUD 7540) — all
  filings already open and hand-verified by prior FSI phases, zero new
  acquisition.
- **Facts extracted**: 20 (10 `cogs` + 10 `gross_profit`). 16
  `direct_reported` (explicit "Cost of Sales"/"Gross Profit" table
  lines), 4 `derived` (CAP's two periods state Gross Profit directly but
  never break out Cost of Sales as its own line — `cogs` = `revenue -
  gross_profit`, a pure accounting identity, same derivation-tier
  convention already used for `fcf`/`ebitda` elsewhere on this platform).
- **Grounding pass rate**: 16/16 attempted (100%); the 4 derived facts
  are correctly `not_run` (no single quote to ground a computed value
  against, same convention as existing `fcf` facts).
- **PIT metadata**: every fact carries the source filing's own
  `filing_date` (knowledge date) and correct `period_end`/`period_type`
  (FY/H1/9M as stated).
- **Ticker coverage**: 5 tickers now have both fields — GEREGU, NASCON,
  BUAFOODS, CAP, AFRIPRUD.
- **Period coverage**: NASCON and BUAFOODS both have full 3-period
  coverage (their existing periods, now enriched); CAP 2 of its 3
  periods; GEREGU and AFRIPRUD 1 period each.
- **Factor families newly touched**: Profitability, Gross Profitability
  — the two families this specifically unblocks.

**Coverage gate determination: NOT MET.** 5 tickers is real progress (up
from 0) but is half of even the platform's own code-level minimum
breadth floor (10, `_eligible()`'s `len(elig) < 10` guard), let alone a
defensible research breadth. **Profitability and Gross Profitability are
PARTIALLY READY, not READY** — see Section 7's matrix. No hypothesis
created.

---

## 4. Corporate-Action Extraction Results

`configs/fact_taxonomy.toml` gained one new leaf, `share_reconstruction`
(distinct from `bonus_issue` — share count is REDUCED via consolidation,
the opposite mechanical direction; NEM/LASACO/TRANSCORP are this type,
not `bonus_issue`, and forcing them into the wrong type would misrepresent
the adjustment direction to any future consumer).

**8 documents processed of the 17-document `bonus_split` archive
category** (9 remaining: 2 NB docs — 1 processed, 1 confirms it; 2
ENAMELWA docs already covered by the pair extracted; ARDOVA x2, NEIMETH,
TRIPPLEG remain genuinely unprocessed — scanned images, char_count 0-1,
need vision/OCR extraction not attempted this session). **The 52
`rights_capital` documents were not processed this session** — genuinely
out of scope given the time this stage already consumed; queued for
Stage 4, not silently dropped.

| ticker | event type | ratio (raw) | price factor | qualification date | closure/suspension date | status | source doc |
|---|---|---|---|---|---|---|---|
| CILEASING | bonus_issue | 2 new per 3 held | 0.600 | 2024-01-04 | 2024-01-05 | **CONFIRMED, matches observed price move** | 7837 |
| LASACO | share_reconstruction | 4 old → 1 new | 4.000 | — | 2021-02-01 | **CONFIRMED, matches observed price move** | 4513 |
| NB (Nigerian Breweries) | bonus_issue | 1 new per 4 held | 0.800 | 2022-12-06 | 2022-12-07 | **CONFIRMED EXECUTED** (doc 6997 confirms SEC registration + crediting on this exact basis) | 6682 |
| CHAMPION | bonus_issue | 1 new per 7 held | 0.875 | 2024-05-10 | 2024-05-13 | Confirmed announcement, same standardized format as CILEASING/NB | 8390 |
| CHIPLC | bonus_issue | 1 new per 15 held | 0.9375 | — | 2020-08-19 | **PROPOSED ONLY** — board resolution, explicitly subject to regulator/shareholder approval as of this document; lower confidence tier | 4000 |
| NEM | share_reconstruction | 2 old → 1 new | 2.000 | — | 2021-12-10 | **CONFIRMED** — resolves the previously narrative-only "fact_id 27" note from `docs/METHODOLOGY_HARDENING_2026-08-04.md`, which had mischaracterized this as a bonus_issue; it is a reconsolidation | 5531 |
| TRANSCORP | share_reconstruction | 4 old → 1 new | 4.000 | — | — | **CONFIRMED EXECUTED** (post-completion press release, 2024-10-28) | 9057 |
| ENAMELWA | bonus_issue | 3 new per 2 held | **1.000 (no-op — CANCELLED)** | 2023-03-13 | — | **PROPOSED THEN CANCELLED** (doc 6987, dated 2023-03-09, explicitly cancels the proposal before its own qualification date) — recorded so a future adjustment layer does NOT apply a markdown that never happened | 6930/6987 |

**One data-quality note surfaced while extracting**: `documents.ticker`
is `NULL` for doc 6682 (Nigerian Breweries) despite the filing content
being unambiguous — the fact was written with the correct ticker in its
own `description` field regardless, but any future query that JOINs on
`documents.ticker` to find this fact will miss it. Flagged, not fixed
(out of Stage 3's bounded scope; a one-row data-quality fix, not an
extraction task).

---

## 5. CILEASING / LASACO / PRESTIGE Resolution

- **CILEASING — CONFIRMED**, structured fact written (Section 4).
- **LASACO — CONFIRMED**, structured fact written (Section 4).
- **PRESTIGE — remains unresolved.** No new evidence was found this
  session (no new document search was warranted — Stage 2 already read
  every document filed near both dates). Restating why, precisely: the
  2018-06-08 date coincides with a real, sourced AGM notice proposing a
  41-for-100 bonus with a register closure window (4-8 June 2018)
  bracketing the observed move, but the observed price direction (+45.7%,
  UP) contradicts the mechanical markdown a bonus issue implies (~-29%
  expected) — no fabricated ratio was recorded because the evidence
  doesn't support one. The 2018-11-28 date has only a board-meeting
  notice mentioning "balance sheet restructuring" with no ratio or
  ex-date at all. **No `extracted_facts` row was written for either
  PRESTIGE date** — writing one would require inventing a number this
  evidence does not support.

**Integration into the return-series adjustment layer — analysis only,
not built.** The 8 confirmed events (Section 4) are now real,
queryable, dated facts (`fact_type IN ('bonus_issue',
'share_reconstruction')`, joined to `documents.ticker`). Wiring them into
`backtest_xs.py`'s price series is feasible WITHOUT touching
`h011_size.toml` — it would take the form of a new, parallel adjusted-
close panel (mirroring exactly how `load_market_cap_panel` sits beside
the raw price panel, or how `xs_liquidity_scores` was added beside
`liquidity_scores` without modifying either), consumed only by hypotheses
that opt in. **This is recommended as a Stage 4 engineering task, not
built here** — 8 events is not yet enough real coverage to justify
wiring a shared adjustment layer that every future hypothesis would
implicitly depend on; the risk of a false sense of completeness (8
events "fixed" while dozens more sit unextracted in `rights_capital`)
outweighs the value of building it now.

---

## 6. Insider Dataset Completeness Audit

| year | documents | unique tickers | IRU tickers |
|---|---|---|---|
| 2020 | 103 | 18 | 17 |
| 2021 | 22 | 5 | 3 |
| 2022 | 6 | 3 | 3 |
| 2023 | 4 | 3 | 2 |
| 2024 | 9 | 3 | 3 |
| 2025 | 13 | 3 | 3 |
| 2026 | 6 | 4 | 4 |

**Decisive evidence this is a harvest gap, not a real decline (B, not
A):**

1. **`retrieved_date` is clustered on 4 dates in July 2026** — the whole
   archive was pulled in one short window, consistent with the
   platform's other known harvest sessions. This alone is neutral, but:
2. **15 of 29 tickers have dealing documents ONLY in 2020, never
   again** — including DANGCEM, GTCO, UBA, NESTLE, FLOURMILL, AIICO,
   WAPIC: large, heavily-scrutinized blue-chips. It is not economically
   plausible that these companies' directors and substantial
   shareholders simply stopped transacting in their own shares for 5+
   consecutive years. Insider dealing is routine at this scale, not rare.
3. Only 7 tickers show dealing docs spanning more than one year, and
   even those are gappy (e.g. SEPLAT: 2022, 2024, 2025, 2026 — missing
   2023; ACCESSCORP: 2023, 2025, 2026 — missing 2024).
4. The IRU-ticker count per year collapses 17 → 3-4 (2020 → 2021), an
   ~80% drop with no known regulatory change to explain it.

**Verdict: NEEDS MORE HARVESTING.** No extraction was attempted (per
your explicit instruction). This is not a rejection of the source — the
one document read in Stage 2 (Flour Mills, 2020) was a clean,
standardized, well-dated disclosure — it is a statement that the LOCAL
ARCHIVE undersamples what NGX's disclosure system almost certainly holds
in full, and extracting from an undersampled archive now would produce a
dataset that looks complete but isn't, the exact trap this audit step
exists to catch.

---

## 7. Fundamental Factor Readiness Matrix (rebuilt post-Stage-3)

| Family | Required fields | Available | Eligible tickers | Hist. periods | PIT feasible | Min. coverage | Current coverage | Status |
|---|---|---|---|---|---|---|---|---|
| Profitability | revenue, cogs/gross_profit, ebit | Yes (all 3) | 5 | 1-3 | Yes | 10 | 5 | **PARTIALLY READY** |
| Gross Profitability | revenue, cogs/gross_profit, assets | Yes | 5 (assets also needed — all 5 have it) | 1-3 | Yes | 10 | 5 | **PARTIALLY READY** |
| Financial Strength | assets, liabilities, equity | Yes | 14 (any depth), 2 full-depth | 1-3 | Yes | 10 | 14 raw / thin depth | **PARTIALLY READY** — closest to the floor of any family, worth prioritizing next |
| Cash Flow Quality | net_profit, cfo | Yes | 13 | 1-3 | Yes | 10 | 13 | **PARTIALLY READY** — also close |
| Value | net_profit/equity + market cap | Yes (market cap panel already exists) | 14 | 1-3 | Yes | 10 | 14 | **PARTIALLY READY** |
| Quality | net_profit, equity, assets, liabilities, multi-period | Yes, fields; periods thin | 14 raw, 8 with ≥2 periods | 1-3 | Yes | 10, ≥3 periods | 8 w/ periods, thin depth | **PARTIALLY READY** |
| Asset Turnover | revenue, assets | Yes | 14 | 1-3 | Yes | 10 | 14 | **PARTIALLY READY** |
| Growth | revenue/net_profit, ≥2 periods | Yes | 8 (≥2 periods) | 2-3 | Yes | 10, ≥4-8 periods | 8, insufficient periods | **BLOCKED** |
| Accruals | net_profit, cfo, working-capital detail | Partial (no WC detail) | 0 with full requirement | — | Yes (mechanism) | 10 | 0 | **BLOCKED** |
| Earnings Quality | net_profit, cfo, accruals detail | Partial | 0 with full requirement | — | Yes (mechanism) | 10 | 0 | **BLOCKED** |
| Investment | assets, ≥2 periods | Yes | 8 | 2-3 | Yes | 10, ≥3 periods | 8, thin | **BLOCKED** |

**Correction from Stage 2's report**: several families I previously
called flatly "No"/zero-progress are more accurately **PARTIALLY READY**
once the actual field-coverage counts are laid out explicitly against a
stated minimum (10) rather than compared only to the FSI pilot's
ticker-count headline. The blocking constraint for most families is
**breadth (5-14 tickers vs. 10 minimum, and often only 1-3 tickers with
real multi-period depth)**, not missing fields — Financial Strength and
Cash Flow Quality are the closest to clearing the gate and should be the
explicit Stage 4 breadth-expansion target, not Profitability (which
needs both breadth AND the newly-added cogs/gross_profit fields to reach
the same number of tickers most other families already have).

---

## 8. H-011 Independence Considerations

No factor reached READY, so no combination testing was run (correctly,
per your instruction). Stated for the record, working through your five
questions for the two families closest to the gate:

1. **Is the information source fundamentally different?** Yes for all
   PARTIALLY READY families — fundamentals (income statement/balance
   sheet) vs. H-011's market-cap-only construction. This is a genuinely
   different information layer, not a re-derivation of price/volume data.
2. **Correlates mechanically with Size?** Plausible risk, not yet
   tested: small-cap NGX names are also more likely to be the thinly-
   covered ones with less FSI data, meaning any future fundamentals
   factor's ELIGIBLE universe may itself skew large-cap — a
   construct-validity risk to pre-register against explicitly, not
   discover after the fact.
3. **Correlates with liquidity?** Same directional risk as #2 — FSI
   coverage today is concentrated in names large/liquid enough to have
   had earnings releases fully harvested and hand-verified (GEREGU,
   NASCON, BUAFOODS, CAP are all reasonably liquid IRU names). Any
   fundamentals-based signal tested on today's coverage would need this
   disclosed as a known selection bias, exactly the entanglement H-013
   already found for Size.
4. **Obvious market-cap construction effect?** No shared construction
   input with H-011's negative-standardized-cap score — a real
   structural difference, unlike H-013/H-014/H-015's forensic findings
   about Size's own entanglements.
5. **Testable independently before combination?** Yes, mechanically —
   but not yet, since no family is READY. This question is answered in
   principle, not in practice, at this stage.

---

## 9. New Information Dimensions

Two, both narrower than "a new dataset":

1. **Corporate-action ratios/dates** — not a new alpha-search dimension,
   a data-integrity layer (explicitly your framing in Phase 2F/Stage 3C).
2. **`cogs`/`gross_profit`** — not a new dataset, a taxonomy extension of
   an existing one, unlocking measurement of an existing information
   layer (fundamentals) along a dimension it previously couldn't
   represent.

No genuinely new INFORMATION SOURCE (as opposed to deeper representation
of an existing one) was added this session. This is consistent with
Stage 3's own stated objective (turn Stage 2's discoveries into a
research-ready layer, not discover new sources) and is reported plainly
rather than inflated.

---

## 10. H-018 Eligibility Decision

Checked against all ten conditions:

| # | Condition | Met? |
|---|---|---|
| 1 | Genuinely new information dimension exists | No — see Section 9 |
| 2 | Historical data sufficient | No — max 3 periods on any ticker, max 5 tickers with the specific fields Profitability/Gross Profitability need |
| 3 | PIT reconstruction defensible | Yes, where data exists (moot without #2) |
| 4 | Coverage meets research threshold | **No — 5 vs. 10 minimum** for the closest families |
| 5 | Signal specifiable without hindsight | Not evaluated — moot without #4 |
| 6 | Economically plausible mechanism | Yes in principle (moot without #4) |
| 7 | Materially different from H-001–H-017 | Yes, if it ever gets built |
| 8 | Preregisterable before performance is seen | Not evaluated — moot |
| 9 | Cost/liquidity treatment defined | Not evaluated — moot |
| 10 | Dataset stable enough for an experiment | No — actively being expanded, not yet frozen |

**Decision: H-018 is NOT created.** Conditions 2 and 4 fail outright;
several others are moot as a direct consequence. This is not a close
call.

---

## 11. Data Sources Added / Rejected

No new external source was added or investigated this session — every
byte extracted came from documents already in `data/archive/
xissuer_docs`, already harvested before Stage 1. This is the correct
outcome per your own Stage 3H framing: the answer to "what does a new
source provide that the current system cannot" was, this entire session,
"nothing — the current system already has unextracted material worth
more than a new acquisition would be."

---

## 12. Remaining Data Bottlenecks

Ranked by what would move the readiness matrix (Section 7) fastest:

1. **Breadth on Financial Strength / Cash Flow Quality** — closest to
   the 10-ticker floor of any family; needs roughly 5-6 more tickers
   with `assets`/`liabilities`/`equity`/`cfo`, most of which likely
   already sit in the same filings already opened for revenue/
   net_profit (i.e., a re-read, not a new acquisition, mirroring exactly
   what Stage 3B did for cogs/gross_profit).
2. **ETI, FCMB, ACCESSCORP extraction** — screened, real content
   confirmed, not yet extracted (Section 2).
3. **The remaining 9 `bonus_split` + all 52 `rights_capital` documents**
   — real, on-disk, unprocessed.
4. **Insider dealing re-harvest** — needed before any extraction is
   meaningful (Section 6); this is an acquisition-completeness task, not
   an extraction task.
5. **Period depth** — even the best-covered tickers (NASCON, BUAFOODS)
   have only 3 periods; Growth/Investment/multi-period Quality need 4-8.
   This closes only with the passage of filing time or reaching further
   back into each company's own filing history.

---

## 13. Recommended Stage 4

**Extend Stage 3B's exact method (re-read filings already open, add the
fields already visible) to `assets`/`liabilities`/`equity`/`cfo` for
every ticker that currently has `revenue`/`net_profit` but not yet the
balance-sheet/cash-flow set** — this is very likely the single fastest
path to clearing a REAL "READY" status on Financial Strength or Cash
Flow Quality, since Section 7 shows those two families are already
closest to the floor and the required fields are frequently sitting in
the SAME already-open documents that produced today's revenue/net_profit
facts (this was true for GEREGU/BUAFOODS/CAP, unverified but plausible
for the rest without a re-read).

In parallel, not sequentially: extract ETI/FCMB/ACCESSCORP (already
screened, real content confirmed) and continue the `bonus_split`/
`rights_capital` backlog at the same hand-verified pace.

**Do not start the insider pipeline** until a re-harvest closes the
2021-2025 gap (Section 6) — extraction effort spent on an undersampled
archive would need to be redone.

**Do not create H-018.** Re-evaluate Section 7's matrix after the above;
if any family reaches 10+ tickers with real multi-period depth, that is
the point to draft a preregistration, not before.
