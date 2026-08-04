# FSI Coverage Expansion — Institutional Decision Audit

*2026-08-03. Owner-decision audit only — no extraction, no implementation,
no schema change, no database write, no new hypothesis was performed or
proposed as part of this document. Every figure below was re-verified
directly against `data/ngx.sqlite` and the real document archive today,
not reused from prior documentation without re-checking (two read-only
scripts were run: `scripts/fre/fsi_scope_candidates.py`, confirmed
`PRAGMA query_only = ON`; and three existing regression suites, run
unmodified). Written for review by a Quant Research Director, Data
Engineering Lead, Portfolio Manager, and Research Committee. The
objective of this document is to determine, from evidence, whether FSI
expansion is the highest-return next investment — not to justify it.*

---

## 1. Current Platform State (re-verified today, not assumed)

### 1.1 Ticker and filing coverage

| Metric | Value | Source |
|---|---|---|
| Total securities tracked | 320 | `SELECT COUNT(*) FROM securities` |
| Distinct tickers with price history | 320 | `equity_prices` |
| Current IRU v2 membership (2026-06-30 formation) | 100 | `universe.iru_members()`, live query |
| Total documents in archive | 11,533 | `documents` |
| Distinct tickers with ANY document | 210 | `documents` |
| Native-text documents (`source_confidence>=0.8`) | 7,399 | `documents` |
| OCR-pending / low-confidence documents | 4,134 (36% of archive) | `documents` |
| Distinct tickers appearing ONLY among OCR-pending docs | 184 | `documents` |
| Securities with a known `sector_ngx` | 136 / 320 (42.5%) | `securities` |

### 1.2 Financial-statement fact counts (re-verified, unchanged from the 2026-08-02 audit)

| `fact_type` | Distinct tickers | Rows |
|---|---:|---:|
| dividend | 60 | 158 |
| net_profit | 10 | 25 |
| revenue | 10 | 25 |
| ebit | 7 | 18 |
| ebitda | 6 | 14 |
| assets | 5 | 14 |
| equity | 5 | 14 |
| liabilities | 5 | 14 |
| cff | 2 | 4 |
| cfo | 2 | 4 |
| cfi | 1 | 3 |
| capex | 1 | 1 |
| fcf | 1 | 1 |
| bonus_issue | 1 | 1 |
| rights_issue | 1 | 2 |

**No `gross_profit`/`cogs`/`cost_of_sales` fact_type exists at all** — confirmed by direct enumeration of every distinct `fact_type` value; this is unchanged from every prior audit.

**The real, verified number that matters most for research purposes**: of the current **100-member Investable Research Universe**, only **9 members** have any financial-statement fact at all (net_profit/revenue level) — **9%**, not the "10 tickers" figure usually quoted, because one of the 10 platform-wide FSI tickers (UBN) is not currently an IRU member. Dividend facts (an event/corporate-action fact, not a fundamental) reach 51/100 IRU members — a materially broader but economically different data class.

### 1.3 Reasoning-conclusion counts (re-verified)

`financial_reasoning_conclusions`: 267 rows, 10 distinct tickers, split `ratio`=125, `trend`=112, `flag`=30. Re-confirmed the specific claim carried in every prior audit since Revision 1: **`cfo`/`cfi`/`cff` trend conclusions = exactly 1 ticker each; `fcf` trend conclusions = 0.** Unchanged.

### 1.4 Validation and regression status (spot-checked today)

- `scripts/test_reasoning_pipeline.py` — **PASS** (full run, all checks).
- `scripts/fre/test_financial_ratios.py` — **12/12 PASS**.
- `scripts/fre/test_financial_health_flags.py` — **11/11 PASS**.
- These three were run as a targeted spot-check of the FSI fact-consuming layer, not an exhaustive re-run of all ~30+ `scripts/fre/test_*.py` files — stated honestly rather than implying full coverage was re-verified.

### 1.5 Every research capability currently blocked by the 10-ticker ceiling

Directly from `docs/FACTOR_CANDIDATE_REGISTRY.md` (re-verified, unchanged): Value (earnings yield/book-to-market), Quality (profitability composite), Growth (revenue/earnings acceleration), Profitability (operating margin), Gross Profitability (no fact_type exists at all — worse than the others), Investment/Asset Growth, Earnings Quality (accrual gap), Cash Flow Quality, Financial Strength (Piotroski-style F-Score), Accruals, Asset Turnover. **11 of 16 named candidate factor families share this single root blocker.**

---

## 2. Opportunity Analysis

### 2.1 The hard ceiling that matters: the already-scoped candidate pool

Re-running `scripts/fre/fsi_scope_candidates.py` today (read-only, `PRAGMA query_only=ON`) against the CURRENT database returns **349 candidate documents, 50 distinct tickers** (30 additional documents have no resolved ticker — an "UNRESOLVED" attribution gap, a real, disclosed data-quality issue, not previously flagged this precisely). This is close to, but not identical to, the "49 tickers" figure the 2026-08-01 Phase 1 pre-registration originally reported — a small drift, stated honestly rather than silently reused. All 10 currently-extracted tickers fall inside this pool (consistent).

**Overlap with the current 100-member IRU, computed directly**:
- 44 of the 50 candidate-pool tickers are current IRU members.
- Of the 40 remaining (never-extracted) candidates, **35 are current IRU members**.
- **Ceiling finding**: even if every single one of the 50 already-scoped, already-archived, native-text candidate tickers were hand-extracted, IRU coverage would rise from the current 9/100 (9%) to at most **44/100 (44%)** — not to 50%, not to 100 tickers, and nowhere near the full 320-security universe.

Reaching beyond ~44/100 IRU coverage requires resolving the OCR-engine/vendor decision (unlocking the 4,134 OCR-pending documents, 36% of the archive, spanning 184 tickers not otherwise covered) — a **separate, distinct owner decision** from "allocate more hand-extraction labor," per `docs/fre_runs/FUTURE_EXPANSION_ROADMAP_2026-08-02.md`'s own Chain A/Chain B distinction.

### 2.2 Milestone table (20 / 50 / 100 / full universe)

| Milestone | Feasible without new acquisition? | What it actually requires | IRU coverage reached |
|---|---|---|---|
| **~20 tickers** | Yes — well within the already-scoped 50-ticker pool | Hand-extraction labor only, same Phase 1/2/13 methodology, no new decision | ~18-20/100 (estimated proportionally from the pool's 44/50 IRU-overlap rate; not separately verified per-ticker) |
| **~50 tickers** | Yes — this IS approximately the full already-scoped pool (50 tickers found today) | Exhausts the entire currently-scoped, native-text candidate pool; hand-extraction labor only | **44/100 (44%), a hard ceiling** — verified exactly, not estimated |
| **~100 tickers** | **No** | Requires the OCR-engine/vendor decision (unresolved since 2026-07-16) to unlock the 4,134 OCR-pending documents, PLUS a fresh scoping pass over that newly-text-accessible set (untested — no one knows today how many of those documents would pass the same revenue/profit/monetary keyword filter) | Unknown — depends on OCR yield, not measured |
| **Full NGX universe (320 securities)** | **No** | OCR decision (above) AND likely additional document acquisition for the ~110 securities with no document at all in the archive (210 of 320 currently have any document) AND depends on how many of the 320 are even active, filing companies (some are bonds/ETFs/delisted — `documents`' own ticker-attribution gaps suggest this denominator itself needs cleaning) | Unknown |

**Which factor families become testable at each milestone** — this is the section where the evidence runs out and estimation must be labeled as such:

- **Technically testable** (some fact exists, code path could run) at ~44-ticker coverage: none of Value/Quality/Growth/Profitability/Investment/Financial Strength/Accruals reach a usable state at 44 tickers for MOST of their required fields, because — critically — **ticker breadth and fact-type depth are different axes, and the 40 remaining candidates have only been scoped for revenue/net_profit-level keyword presence, not for balance-sheet or cash-flow content.** Phase 2's own finding (per the Explore review below) is that a full 33% of hand-checked filings had NO cash-flow statement at all (many NGX results are "abridged"). There is **no evidence** that extracting the remaining 40 tickers would yield balance-sheet/cash-flow facts for anywhere near 40 names — this must be measured, not assumed, and is explicitly labeled **Unknown** rather than estimated, because even a rough proportional estimate has no basis in any documented finding.
- **Statistically credible**: no factor family reaches the platform's own established breadth precedent (~100-name tests, or at minimum the ~20-35 name range that has supported the weakest accepted cross-sectional designs, e.g., H-007's ~35-name breadth) at 44 tickers, UNLESS the family requires only revenue/net_profit (Growth, in its crudest single-metric form) — and even then, multi-period Growth needs the SAME ticker to have facts across ≥2 non-adjacent periods, which is a further, unmeasured constraint (see §7).
- **Suitable for production research**: none, at any milestone in this table, without first resolving the OCR/vendor decision AND running a fresh, dedicated depth-scoping pass (not yet done) to determine how many tickers would actually yield full balance-sheet + cash-flow data, not just revenue/net_profit.

### 2.3 Immediately buildable hypotheses (evidence-based, not assumed)

**None, at any milestone this section can verify.** The reasoning: every blocked factor family requires MULTIPLE fact_types (e.g., Financial Strength needs assets+liabilities+equity together; Quality needs net_profit+revenue+equity together), and the CURRENT ticker-level intersection of "has assets AND liabilities AND equity" is exactly 5 tickers (unchanged since Phase 2, per the Explore review's Q2 finding) — none of which is guaranteed to grow proportionally with ticker-count expansion, because the 40 remaining candidates were scoped on revenue/profit KEYWORDS ONLY, not balance-sheet presence. This is the single most important, previously-under-stated finding of this audit: **expanding ticker breadth (10→50) does not automatically expand the fact-type DEPTH (balance-sheet, cash-flow) needed for most of the blocked factor families** — the two have historically moved almost independently (Phase 13 explicitly deferred balance-sheet/cash-flow work when it added tickers 6-10).

---

## 3. Extraction Strategy Review

*Findings below combine direct reading of `docs/fre_runs/fsi_phase1_preregistration.md`, `fsi_phase1_results.md`, `reports/eps_pe_extraction_status.md`, `reports/DOL_PIPELINE_COMPLETION_REPORT.md`, and a targeted document-review pass across `docs/fre_runs/fsi_phase2_*` through `fsi_phase27_*` (final reports plus implementation logs where a final report was thin on a specific point).*

### 3.1 Deterministic / template-based extraction — the DOL price-list pipeline (a genuinely different, SUCCESSFUL precedent)

- **What it is**: fully automated parsing of the NGX Daily Official List and pricelist PDFs/ZIPs for price/volume data — 2,827 PDFs archived (99.3%), 304,282 rows extracted across 2,759 trading days, 335 symbols, validated against an independent NGX REST JSON source at 99.25-100% match.
- **Why it succeeded**: this document TYPE has a genuinely regular, repeating tabular structure (columns fixed in position/order across time), amenable to deterministic parsing.
- **Relevance to this audit**: proves the platform CAN scale fully-automated extraction to hundreds of thousands of rows when the source format is sufficiently regular — establishing that hand-verification for FSI was a deliberate methodological choice given the DIFFERENT (narrative, non-tabular, format-inconsistent) nature of financial-statement filings, not a default failure to attempt automation.

### 3.2 DOL EPS/P.E. parser — attempt #1 (naive last-two-tokens) and #2 (header-calibrated banding)

Both attempts targeted a DIFFERENT dataset (EPS/P.E. figures on the DOL, not raw financial-statement facts) but are the platform's clearest documented case of automated-parsing failure on NGX PDF content, directly relevant to judging whether automation could ever work for FSI:

- **Attempt #1** (naive: grab the last two numeric tokens per row): 58.5% pass rate at 6,003-row scale — failed because high-price names (DANGCEM, NESTLE, MTNN, SEPLAT) systematically have blank EPS/P.E. fields, and the naive rule silently grabbed the wrong column instead of returning nothing.
- **Attempt #2** (header-calibrated banding: locate the "P.E." header token, require candidates in tight x-bands): pass rate DROPPED to 34.3% — introduced a NEW failure mode (implausibly tiny values on low-price names) because column geometry drifts by era/section more than a single tolerance band can cover.
- **Verdict**: neither cleared the pre-declared 95%-pass/≥500-row bar. **Failure was architectural, not an implementation bug** — the underlying claim ("a single positional/geometric rule generalizes across NGX's DOL PDF corpus") was falsified twice, by two structurally different approaches. Retrying with a third geometric/positional rule is not obviously justified without first doing the per-format-era calibration work the report itself recommends (probe header x-positions on a stratified 2014-2026 sample BEFORE attempting bulk extraction again) — this has not been done.
- **Safest future architecture, per the report's own recommendation**: per-format-era calibration BEFORE any bulk attempt, not a universal rule — this is a real, actionable design note for the SAME class of problem, but has never been executed.

### 3.3 Financial-statement extraction — Phase 1 (hand-verified, native-text only)

- **What was attempted**: 5 tickers (UCAP, BUAFOODS, AFRIPRUD, CAP, NASCON), 15 filings, revenue+net_profit only, deterministic-parsing-first with LLM-assist only where deterministic parsing failed, every fact cross-checked against the SAME document's own second restatement (highlights vs. detailed table).
- **Result**: 30/30 facts (100%), decisively clearing the pre-registered 80% bar.
- **Why it succeeded, with real disclosed limits**: hand-verification with an internal same-document cross-check is a genuinely different, higher-assurance method than either DOL parser attempt — but it is **non-random, hand-picked for document-size manageability**, and **validated ONLY internally** (never against an independent external source, per explicit instruction). A 100% result on 15 hand-picked filings does not establish accuracy at scale.

### 3.4 Financial-statement extraction — Phase 2 (same 5 tickers, added balance-sheet + cash-flow + ebit/ebitda)

- **Result**: 76 new facts, same hand-verification methodology.
- **Real finding, not an extraction-technique failure**: 5 of 15 filings had NO cash-flow-statement section at all (abridged results announcements) — a **source-document disclosure gap**, not a parsing difficulty. This directly explains why cash-flow facts (`cfo`/`cff`=2 tickers, `cfi`/`capex`/`fcf`=1 ticker) lag so far behind revenue/net_profit (10 tickers) even for the ORIGINAL 5 tickers, and is the single most important risk factor for any expansion cost estimate (§4): **a meaningful, currently unquantified fraction of NGX filings structurally cannot yield cash-flow facts no matter how much labor is applied**, because the statement itself was never filed in abridged form.

### 3.5 Financial-statement extraction — Phase 13 (5 new tickers: DANGCEM, MTNN, UBN, OANDO, NESTLE)

- **Scope was deliberately narrowed back to Phase 1's revenue/net_profit/ebit/ebitda** — balance-sheet/cash-flow for these 5 tickers was **explicitly deferred, not rejected**, when the team chose to prioritize ticker BREADTH over per-ticker DEPTH for this phase.
- **Result**: 31/31 facts, same internal-only cross-check methodology, again on a hand-picked, non-random sample.
- **Real complications surfaced, generalizing beyond Phase 1's AFRIPRUD "Gross Earnings" finding**:
  - **Banks structurally lack an EBIT/EBITDA concept** (UCAP, and again UBN seven phases later) — a bank's income-statement structure has no equivalent line; this is not a labeling quirk, it is a genuine architectural gap that would recur for EVERY bank added in any future expansion (10 of the 100 IRU members are banks or bank-adjacent by ticker name inspection — a real, non-trivial fraction).
  - **Non-statutory "adjusted" headline figures** (MTNN, NESTLE) required deliberately recording the LOWER-profile statutory figure per the platform's no-fabrication rule, even where the company's own press release headlined a different, more favorable number.
  - **Unusually long reporting lag** (OANDO: FYE2021 results released 28 March 2023) — a real data-timeliness/point-in-time complication for any hypothesis eventually built on this data (see §5).
  - **Same-era label variance** (DANGCEM: "Total revenue" vs. "Total revenues" in different tables of the SAME filing; OANDO: two different hyphenation variants of "Profit-After-Tax" across its own two filings) — handled via a config-driven synonym table, not a structural blocker, but real, recurring, per-ticker engineering overhead.
- **No chronological format-era shift was found for financial-statement extraction specifically** (unlike the DOL EPS/P.E. parser's documented ~2015→2019 shift) — the complications found are same-era terminology variance and structural sector differences (banks vs. non-banks), not a time-based layout change.

### 3.6 No phase ever attempted extraction beyond the 49/50-ticker scoped pool

Verified false across every phase 2-27: Phase 13's own pre-registration explicitly rejected "a wholly new extraction methodology (OCR, vendor data, automated scraping at scale)" as an alternative, framing all coverage-expansion work as strictly "MORE of the same validated method, not a faster, less rigorous one." No phase ever used or piloted a fully-automated/LLM-only pipeline for financial-statement facts — every one of the three fact-writing phases (1, 2, 13) used hand-reading as the sole extraction method, with automation limited to downstream mechanical steps (period classification, terminology mapping, ratio computation) applied AFTER a human read the source text.

### 3.7 Summary judgment on extraction strategy

| Approach | Attempted for FSI? | Outcome | Retry justified? |
|---|---|---|---|
| Deterministic/template parsing (DOL price pipeline precedent) | Not for financial statements — proven only on price data | N/A (different document type) | Only if a per-format-era calibration effort were separately scoped; no evidence this would work on narrative statements |
| Deterministic parsing, naive (EPS/P.E., a related PDF-parsing case) | Yes | 58.5% pass — failed | Not without per-era calibration, never attempted |
| Deterministic parsing, header-calibrated (EPS/P.E.) | Yes | 34.3% pass — failed, worse | No — introduced a new failure mode |
| Hand-verified, internal-cross-check (Phases 1/2/13) | Yes, for all 10 current FSI tickers | 100% on every pilot, but small, non-random samples, never externally validated | Yes — this is the ONLY validated approach for financial statements; retrying means MORE of it, not a different method |
| Fully-automated/LLM-only extraction | Never attempted for FSI | N/A | Unknown — never piloted, no evidence either way |

---

## 4. Cost-Benefit Analysis

**Labeled per the instruction's own requirement: Measured / Estimated / Unknown, kept separate.**

### 4.1 Measured

- Phase 1: 5 tickers, 15 filings, 30 facts (2 metrics) — one documented unit of completed work.
- Phase 2: same 5 tickers, 76 additional facts (6 metrics) — a second documented unit.
- Phase 13: 5 NEW tickers, 10 filings, 31 facts (4 metrics, narrower scope than Phase 2) — a third documented unit.
- Real disclosure-gap rate (Phase 2): 5/15 filings (33%) had no cash-flow section at all.

### 4.2 Estimated (labeled as estimates, not facts)

- **No per-ticker or per-filing time/effort figure exists anywhere in the reviewed documentation** — confirmed absent by a targeted keyword search across every phase document and the four consolidated 2026-08-02 rollups. Any hours-per-ticker number quoted by anyone would be an invented estimate, not a platform fact.
- A rough, explicitly-labeled proportional estimate: if Phase 13's 5-ticker/10-filing/4-metric unit represents roughly one "session" of hand-extraction labor (an assumption, not measured), extracting the remaining 40 scoped tickers at the SAME narrow (revenue/net_profit/ebit/ebitda-only) scope would represent roughly 8 more such units. This is stated as a rough proportional inference from 3 data points, not a validated throughput model, and should not be relied upon for actual resource planning.
- Engineering effort for the extraction/storage/validation CODE PATH itself is low-to-none — the schema, `grounding.py`, and the write pattern are already built and reused unmodified across all three phases; the cost is essentially 100% human reading/verification labor, not software engineering.

### 4.3 Unknown (explicitly, not glossed over)

- Whether cash-flow/balance-sheet disclosure rates in the REMAINING 40 candidate filings resemble Phase 2's 67% (10/15) rate, are better, or are worse — never measured for this specific set.
- Whether the "UNRESOLVED" 30-document ticker-attribution gap in the scoping output represents additional usable candidates or noise — never investigated.
- The diminishing-return point — cannot be located without knowing the depth-yield rate above; stated as unknown rather than guessed.
- Maintenance burden of a larger fact set (restatement handling, confidence-tier propagation) at 10x the current scale — no phase has operated at that scale, so no empirical maintenance-cost data exists.
- Whether extraction throughput would degrade for less "convenient" filings than the ones selected so far (Phase 1's own explicit selection bias: "moderate document size... large enough to contain a full income statement, small enough to read directly" — the remaining 40 were never screened for this same convenience factor).

---

## 5. Risk Assessment

| Risk | Level | Evidence |
|---|---|---|
| Data quality (accuracy of extracted values) | **Low**, for the ALREADY-EXTRACTED facts specifically | 100% pass on every pilot (30/30, 76/76-equivalent, 31/31), each cross-checked internally; real errors that DID occur (BUAFOODS layout artifact, AFRIPRUD 3-line derived sum) were caught and resolved before writing, per the documented error-categorization tables |
| Data quality, GENERALIZED to future extraction | **Medium** | All validation to date is internal/same-document only, on hand-picked, non-random, size-convenient samples — real accuracy on a forced, unscreened expansion to 40 more (potentially larger, messier, less convenient) filings is unmeasured |
| Validation risk (methodology itself) | **Medium** | No independent/external cross-check has EVER been used for any FSI fact, by explicit design choice — a systematic, not random, gap in the validation approach; if the source documents themselves ever contain an error (not just an extraction error), nothing would catch it |
| Point-in-time integrity | **Low** | `period_start`/`period_end`/`qualification_date` fields exist and are populated per the same discipline as every other platform fact; OANDO's 15-month reporting lag (FYE2021 results, 2023-03-28) shows the platform's PIT discipline is already stress-tested by a real, extreme case and handled (filing_date, not coverage period, is what's used for dating) |
| Look-ahead risk | **Low** | Same PIT-safe pattern as every other fact type on this platform; no new mechanism introduced by more tickers |
| Regression risk | **Low** | Three spot-checked regression suites pass today; the FSI write pattern is unchanged/reused across all three phases, reducing the chance new tickers introduce a new code path |
| Operational complexity | **Medium** | Per-ticker/per-sector idiosyncrasy is real and recurring (bank EBIT/EBITDA gap, non-statutory headline figures, abridged filings, same-era label variance) — every new ticker is not a uniform, drop-in unit of work; sector composition of the remaining 40 matters and has not been characterized |
| Maintenance burden | **Medium-High, at scale — Unknown, at the current scale tested** | No phase has operated anywhere near the scale (40+ more tickers) needed to observe real maintenance cost; the existing `restates_fact_id`/confidence-tier machinery is designed for this but untested at volume |
| Long-term technical debt | **Low-Medium** | The extraction methodology itself (hand-verify, internal cross-check, additive schema) is consistent and disciplined across all three phases — no shortcut has been taken yet; the RISK is if future pressure to move faster (given the labor cost) leads to a lower-rigor approach being introduced later, which nothing in the current architecture would prevent by itself |

---

## 6. Research Impact — Field Mapping for Every Blocked Factor Family

Re-verified directly against `data/ngx.sqlite` and `docs/FACTOR_CANDIDATE_REGISTRY.md §B` today (unchanged from the 2026-08-02 audit for every field-count figure):

| Family | Required fields | Available (tickers) | Missing | Min. FSI coverage needed | Architecture already supports it once data exists? |
|---|---|---:|---|---|---|
| Value (earnings yield/B2M) | net_profit, equity | 10, 5 (joint: fewer) | equity for 5 more of the 10 net_profit tickers, at minimum | Joint coverage of both fields for a fair-breadth universe (§7) | Yes — `xs_rank`-style scoring generalizes directly, per Wave 3/A1's own precedent for Liquidity |
| Value (cash-flow yield) | cfo, fcf | 2, 1 | Nearly everything | Same | Yes, mechanically; data is the entire blocker |
| Quality (profitability composite) | net_profit, revenue, equity | 10, 10, 5 | equity breadth | Joint coverage | Yes |
| Growth (revenue/earnings acceleration) | revenue, net_profit, MULTI-PERIOD | 10, 10 | Whether each ticker has ≥2 non-adjacent periods — **not separately verified in this audit, a real gap** | Multi-period depth per ticker, not just ticker count | Yes, mechanically |
| Profitability (operating margin) | ebit/ebitda, revenue | 7/6, 10 | ebit/ebitda breadth | Joint coverage | Yes |
| Gross Profitability | gross_profit (fact_type does not exist) | 0 | Everything — no extraction has EVER targeted this line item | A new extraction target, not just more of the same tickers | Unknown — would need a new fact_type and extraction pass, not evaluated here |
| Investment/Asset Growth | assets, multi-period | 5 | Same joint/multi-period gap as Growth | Multi-period depth | Yes |
| Earnings Quality (accrual gap) | net_profit, cfo | 10, 2 | cfo is the binding constraint | cfo breadth specifically | Yes |
| Cash Flow Quality | cfo, cff, cfi | 2, 2, 1 | All three, jointly | All three jointly, hardest bar of any family | Yes, mechanically |
| Financial Strength (Piotroski) | assets, liabilities, equity | 5, 5, 5 (same 5 tickers, per Phase 2) | Breadth beyond these 5 | Joint coverage of all three | Yes — `financial_health_flags.py`'s rule pattern is directly extensible, confirmed in Owner Decision Backlog |
| Accruals | net_profit, cfo | 10, 2 | cfo | Same as Earnings Quality | Yes |
| Asset Turnover | revenue, assets | 10, 5 | assets breadth | Joint coverage | Yes |

**The universal finding across every row**: architecture is NOT the blocker for any of these families (every consuming module — `financial_health_flags.py`, `financial_ratios`, the eventual `backtest_xs.py` scoring pattern — already handles arbitrary coverage levels, confirmed in the Owner Decision Backlog and Future Expansion Roadmap). **The blocker is exclusively DATA, and specifically the JOINT availability of 2-3 fields per ticker, which is currently far narrower than any single field's own ticker count** — e.g., Financial Strength needs all three of assets/liabilities/equity for the SAME ticker, and that joint set has been stuck at exactly 5 since Phase 2 (2026-08-01), UNCHANGED through 25 subsequent phases and one ticker-breadth expansion (Phase 13) that deliberately did not touch these fields.

---

## 7. Minimum Viable Coverage (mandatory section)

**Technically testable** (code runs, produces a number, without regard to whether the number is trustworthy): as few as 10-15 tickers with the JOINT required fields, matching the platform's own `_eligible()` breadth guard (`len(elig) >= 10`) already enforced throughout `backtest_xs.py` — this is a verified, code-level minimum, not an estimate. **At CURRENT joint coverage (5 tickers for the assets/liabilities/equity triple), NO blocked family clears even this minimal code-level floor today.**

**Statistically credible**: **no precise, platform-derived threshold exists** — stated as uncertainty, not invented. The closest available anchor is the platform's own historical practice: every hypothesis tested to date (H-001 through H-016) has used the ~100-name IRU or a large, clearly-defined subset of it (the narrowest being H-003's ~10 sector-scoped events, which the platform's own retrospective explicitly named as an under-powered "breadth ceiling" failure — 5 of 13 rejections trace to exactly this problem, per `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`). This suggests, as a REASONED JUDGMENT rather than a derived figure, that **something in the 20-35 name range is a plausible practical floor** for a fundamentals-based cross-sectional sort to avoid repeating the platform's own most common failure mode — but no formal power analysis has ever been performed for this specific factor class, and this number should not be treated as validated.

**Suitable for production research**: **no threshold is stated or estimated here** — this platform has never operated ANY factor at "production" scale (Portfolio Construction Tier 2 remains gated on ≥2 validated factors, currently at 1), so there is no internal precedent to anchor this figure to, and inventing one would violate the instruction against unsupported values.

---

## 8. Alternatives — Is FSI Expansion Actually the Best Next Investment?

| Alternative | Case for priority | Case against priority |
|---|---|---|
| **H-017 (Dividend Payer Status)** | Zero new data acquisition; fully available today (`exdiv_closure_calendar.csv`, 217 symbols, 1,044 events); lowest engineering cost of any candidate in `docs/WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`; could produce the platform's SECOND validated factor (the single most consequential architectural gap per every audit since 2026-08-02) within one research cycle | Real, disclosed construct-validity risk (may simply proxy Size/Quality); modest research-value ceiling even if confirmed; does not address the FSI ceiling at all |
| **Additional technical-factor research** (beyond H-017) | Zero new data acquisition for MOST remaining ideas (e.g., a triple-conditioned Size∩Liquidity∩LowVol tilt, named but not pursued in Phase R2's report) | The platform's own ≤2-active-hypotheses rule limits how much of this can run in parallel with anything else; H-016's own result (this session) suggests the technical-factor space may be approaching diminishing returns given how many of the "free" candidates (A1 Liquidity, A3 Interactions) are now resolved-negative |
| **Statistical-method improvements** | Already substantially built (HAC, DSR, Holm/BH, real-rf) as of METH-001/002 — marginal remaining value is genuinely lower than when this program started | Not a large open item; no specific next statistical method is currently named as missing |
| **Portfolio-construction improvements** | N/A — explicitly, correctly GATED behind ≥2 validated factors per the charter; building this now would violate the platform's own standing guardrail | This is not a live alternative at all right now, not a competing priority |
| **Better document extraction (OCR/vendor decision)** | Would unlock the 4,134-document, 184-ticker OCR-pending set — the ONLY path to genuinely breaking the ~44/100 IRU ceiling this audit found for the hand-extraction-only path | This is a DIFFERENT decision from "more hand-extraction on the scoped-49/50 pool" — it is a vendor/cost decision open since 2026-07-16 with no new information in this audit changing that; not something this document can resolve |
| **New data-source acquisition** (e.g., NGX X-Compliance free-float report, per `docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`) | Addresses a DIFFERENT, real, disclosed gap (H-011's full-issue-cap limitation) with a narrower, better-scoped extraction target (one recurring report format, not 11,500 heterogeneous filings) | Narrower research value than a full fundamentals unlock; still requires new extraction work of its own |
| **Other roadmap items** (Evaluation Framework, LIM, news-source registry, corp-action classification) | Real, each already scoped | Every one requires its OWN separate owner decision or human-judgment input (gold-set authoring, OCR vendor, licensing) — none is a free next step either |

**Why FSI expansion (the hand-extraction path specifically) should NOT automatically be assumed the top priority**: this audit's central finding (§2.3, §6) is that expanding ticker BREADTH within the already-scoped 50-ticker pool does not reliably expand the JOINT field DEPTH (balance-sheet + cash-flow together) that most blocked factor families actually need — and that joint depth has been stuck at 5 tickers since Phase 2, unmoved by Phase 13's later 5-ticker breadth expansion. **A hand-extraction investment scoped the same way as Phases 1/2/13 (breadth-first) is not evidenced to unlock any NEW factor family test at fair breadth** — it would most likely just add MORE tickers to the already-testable-but-currently-underused revenue/net_profit/ebit/ebitda set (Growth, crudely), while leaving Value/Quality/Financial Strength/Cash Flow Quality/Accruals exactly as blocked as today, unless the labor is EXPLICITLY re-scoped to prioritize DEPTH (balance-sheet + cash-flow) on the existing or expanding ticker set instead of breadth — a design choice not yet made in any phase.

---

## 9. Decision Options

### Option A — Do nothing further on FSI; proceed with H-017 and/or other technical-factor research

- **Benefits**: zero new cost; H-017 could deliver the platform's second validated factor (its single largest architectural gap) fastest.
- **Risks**: the FSI ceiling remains exactly where it is; if H-017 also rejects (a live possibility, per its own disclosed construct-validity risk), the technical-factor pipeline may be running low on cheap candidates.
- **Dependencies**: none beyond what already exists.
- **Research unlocked**: none new on the fundamentals side.
- **Estimated effort**: zero (for this decision itself).
- **Unknowns**: whether H-017 confirms; whether any further technical-factor candidate exists beyond what Wave 4 already named.

### Option B — Depth-first hand-extraction expansion on the EXISTING 10 tickers (balance-sheet + cash-flow for the 5 tickers Phase 13 skipped, plus any gaps in the original 5)

- **Benefits**: directly targets the §6 finding that joint-field depth, not ticker count, is the binding constraint; could bring 10 tickers to full statement depth, enabling a genuine (if narrow, ~10-ticker) pilot test of Financial Strength/Cash Flow Quality/Accruals for the first time.
- **Risks**: 10 tickers is far below even the reasoned 20-35 floor named in §7 — any resulting hypothesis would likely repeat the platform's own most common failure mode (breadth ceiling).
- **Dependencies**: none beyond labor allocation; reuses Phase 1/2/13's methodology unmodified.
- **Research unlocked**: a pilot-only, likely-underpowered test — genuinely informative about EXTRACTION feasibility at depth, less clear about delivering a fairly-tested FACTOR.
- **Estimated effort**: unknown (§4.3) — smaller in ticker count than Option C but requires the SAME per-filing depth work Phase 2 already showed is harder (33% of filings lack cash-flow entirely).
- **Unknowns**: whether the existing 10 tickers' remaining filings even contain cash-flow sections (not yet checked for DANGCEM/MTNN/OANDO/NESTLE/UBN specifically).

### Option C — Breadth-first hand-extraction expansion to the remaining 40 scoped tickers, same narrow scope as Phase 13 (revenue/net_profit/ebit/ebitda only)

- **Benefits**: reaches the 44/100 IRU ceiling (§2.1) for a Growth-style (revenue/net_profit-based) factor test at close to the platform's own reasoned breadth floor.
- **Risks**: per §6/§8, does NOT unlock Value/Quality/Financial Strength/Cash Flow Quality/Accruals — repeats Phase 13's own choice to defer depth, this time at larger scale; real risk of investing significant labor for a narrower research payoff than Option B or D would give per unit of ticker.
- **Dependencies**: none beyond labor allocation.
- **Research unlocked**: a fair-breadth (~44-ticker) Growth-style hypothesis becomes buildable; nothing else.
- **Estimated effort**: roughly 8x Phase 13's own unit of work (§4.2's explicitly-labeled rough estimate).
- **Unknowns**: real depth-yield rate for these 40 filings (never measured); sector composition (bank/EBIT-gap exposure unknown).

### Option D — Combined depth-and-breadth expansion (extract ALL available metrics for AS MANY of the remaining 40 tickers as labor allows, prioritizing joint-field completeness over raw ticker count)

- **Benefits**: directly targets §6's actual finding — most likely path to genuinely unlocking Value/Quality/Financial Strength/Accruals at a broader-than-5-ticker breadth, if the underlying filings cooperate (unverified).
- **Risks**: highest total effort of any option (breadth AND depth together); still bounded by the SAME 33%-of-filings-lack-cash-flow real constraint found in Phase 2 — a hard ceiling on cash-flow-dependent families no matter how much labor is applied.
- **Dependencies**: a fresh depth-scoping pass (checking which of the 40 remaining candidates' filings actually CONTAIN balance-sheet/cash-flow sections) BEFORE committing extraction labor — not yet done, and per this program's own standing discipline ("audit data availability before forming a hypothesis"), should be done first, cheaply, before any large labor commitment.
- **Research unlocked**: potentially all 11 blocked families, at whatever breadth the depth-scoping pass reveals is achievable — genuinely unknown until that pass is run.
- **Estimated effort**: highest of the four options; genuinely unknown in absolute terms (§4.3).
- **Unknowns**: everything the depth-scoping pass would resolve — this option's own value cannot be bounded without it.

### Option E — Resolve the OCR/vendor decision first (Chain B), independent of any hand-extraction labor decision

- **Benefits**: the ONLY path that could exceed the 44/100 IRU ceiling this audit found; unlocks 184 additional tickers' worth of documents.
- **Risks**: a vendor/cost decision, open since 2026-07-16, with no new evidence in this audit to resolve it; even if resolved, still requires a FRESH scoping pass (unknown yield) before any extraction labor question is even reachable.
- **Dependencies**: owner selection of an OCR engine/vendor — outside this audit's scope to resolve.
- **Research unlocked**: unknown until the vendor decision is made and a scoping pass is run.
- **Estimated effort**: unknown; likely includes a real financial cost (vendor fees), distinct from the labor-only cost of Options B-D.
- **Unknowns**: everything about OCR yield and cost.

---

## 10. Final Recommendation

### Is FSI expansion justified?

**Partially, and only in a specific, narrower form than "expand to more tickers" — not justified in the breadth-first form every prior phase (1, 2, 13) has actually used.**

### Why

The evidence in this audit does not support the implicit assumption that more hand-extraction labor, applied the way it has been applied three times already, is the highest-return next investment. The single load-bearing finding is **§6/§8's discovery that ticker breadth and joint-field depth have moved almost independently across this program's history**, and that depth (not breadth) is what's actually gating 10 of the 11 blocked factor families. A fourth phase that repeats Phases 1/13's breadth-first choice would very likely reach 44/100 IRU coverage on revenue/net_profit (enabling, at best, a Growth-style hypothesis) while leaving Value, Quality, Financial Strength, Cash Flow Quality, and Accruals **exactly as blocked as they are today** — a real, evidenced risk, not a hypothetical one, since it is precisely what happened when Phase 13 added 5 tickers without touching balance-sheet/cash-flow.

### Evidence supporting a (narrower) expansion decision

- The extraction methodology itself is validated (100% pass on every pilot, though on hand-picked samples) and requires no new engineering — `financial_health_flags.py`, `financial_ratios`, and the eventual quant-side scoring pattern are all already built and ready to consume more data the moment it exists.
- A real, already-identified, already-archived candidate pool exists (50 tickers, 349 documents, 44 of them current IRU members) requiring no new document acquisition or vendor decision for at least a partial expansion.
- 11 of 16 named factor families share this single blocker — the highest-leverage single blocker on the entire research roadmap, if it can genuinely be resolved.

### Evidence arguing against an unscoped/breadth-first expansion

- No per-ticker or per-filing effort estimate exists anywhere — committing labor without first bounding its cost is exactly the kind of decision this platform's own discipline (audit before acting) exists to prevent.
- The 33%-filings-lack-cash-flow finding (Phase 2) means a meaningful, currently unquantified share of ANY expansion labor will hit a hard, unresolvable disclosure gap, not an extraction-skill gap — no amount of labor fixes an abridged filing that never reported cash flow.
- Sector-specific structural gaps (banks' missing EBIT/EBITDA concept) mean the remaining 40 candidates are not uniform, interchangeable units of labor — some fraction will yield systematically incomplete data regardless of effort.
- No statistically-credible breadth threshold has ever been derived for a fundamentals-based factor on this platform — committing to "50 tickers" as a target is not backed by a validated power analysis, only a reasoned analogy to the platform's own past breadth failures.

### What owner decisions remain

1. Whether to fund a **depth-scoping pass** (cheap: read-only, checks which of the 40 remaining candidates' filings actually contain balance-sheet/cash-flow sections) BEFORE any extraction-labor commitment — this is the single highest-leverage next action this audit can identify, and notably, it is NOT itself "FSI expansion" — it is a scoping step that would make any subsequent expansion decision evidence-based rather than a repeat of Phase 13's own untested assumption.
2. Whether to prioritize DEPTH (Option B/D) over BREADTH (Option C) for whatever labor is allocated, given §6/§8's finding.
3. Whether to pursue the OCR/vendor decision (Option E) in parallel, as a genuinely separate, larger-scope decision.
4. Whether H-017 (zero-cost, already-designed) should proceed in parallel regardless of the FSI decision — this audit finds no reason it should wait on FSI.

### What should happen immediately after approval (if expansion is approved in some form)

- Run the depth-scoping pass first (a read-only script analogous to `fsi_scope_candidates.py`, checking for balance-sheet/cash-flow section presence, not just revenue/profit keywords) across the 40 remaining candidates, BEFORE committing any hand-extraction labor.
- Re-scope the labor allocation decision using that pass's real findings, not this audit's own rough estimates.

### What should NOT happen immediately after approval

- Do not repeat Phase 13's breadth-first, depth-deferred pattern by default — that choice is exactly what produced the current joint-depth ceiling this audit identifies as the real blocker.
- Do not commit a large, unbounded labor allocation before the depth-scoping pass exists — doing so would be spending against an unmeasured cost and an unmeasured yield simultaneously.
- Do not treat a future ticker-count milestone (20/50/100) as a proxy for research readiness — §2.3 and §6 show ticker count alone does not imply joint-field usability for most blocked families.
- Do not delay H-017 pending any FSI decision — the two are independent, and H-017 is fully ready today.

---

## Institutional Adversarial Review

*Five reviewer perspectives, each required to find real weaknesses; each criticism answered directly below it, not deflected.*

### Quant Research Director

**Criticism**: "This audit spends a lot of effort quantifying the ceiling (44/100) but doesn't tell me what Sharpe ratio or research value I'd actually get. Without that, how do I compare this against H-017 on a like-for-like basis?"

**Response**: Correct, and this is a real limitation, not an oversight to paper over. No factor has ever been tested on FSI fundamentals data on this platform, so there is no realized Sharpe/DSR figure to cite — any such figure would be fabricated. The honest comparison this audit CAN make is qualitative: H-017 is fully ready today at zero incremental data cost with a KNOWN (if modest) research ceiling; FSI expansion, even in its best-case (Option D) form, requires an unscoped depth pass before its OWN research ceiling can be estimated at all. That asymmetry — one option's value is boundable today, the other's is not — is itself the decision-relevant fact, not a gap in this audit.

### Skeptical Portfolio Manager

**Criticism**: "You've told me 33% of filings lack cash-flow data. Have you checked whether that 33% is randomly distributed, or concentrated in a way that would bias any resulting factor (e.g., only smaller/weaker companies file abridged results, creating a survivorship-style bias in whichever names end up with full data)?"

**Response**: This was not checked, and should have been flagged more prominently — it is a real, undisclosed risk this audit missed until this review. Adding it explicitly: **if abridged (cash-flow-omitting) filings correlate with company characteristics (size, sector, financial distress) rather than being randomly missing, any future Cash Flow Quality/Accruals factor built only on the "lucky" subset with full disclosure would carry a real, undiagnosed selection bias** — economically weaker or more opaque companies might be systematically excluded, precisely the companies where an accruals/cash-flow-quality signal would be most informative. This must be checked (a straightforward query cross-referencing which tickers/sectors show the disclosure gap) as part of any future depth-scoping pass, not assumed away. This is now added as an explicit item any depth-scoping pass must check, not just section presence.

### Skeptical Statistician

**Criticism**: "Section 7's '20-35 name floor' is your own reasoned guess dressed up as a section heading. You're claiming to avoid inventing thresholds, but this number has no more rigor behind it than a made-up one — you're just citing precedent instead of stating a number outright. Isn't that the same problem with extra steps?"

**Response**: This is a fair challenge, and the distinction matters even if it's subtle: the number is not derived from a power calculation (which would require an assumed effect size and variance this platform has never estimated for a fundamentals factor, and inventing THOSE would be worse), but it is not arbitrary either — it is anchored to REAL, OBSERVED outcomes on THIS platform (5 of 13 rejections tracing to breadth ceilings, the narrowest at ~10 events). The distinction drawn in §7 — "reasoned judgment, not a derived figure" — is the correct level of honesty, but the statistician's challenge is right that this should not be read as anything stronger than an analogy-based heuristic, and the document is edited in spirit here to make sure that caveat is not skimmable-past: **no one should size an actual extraction labor budget off the number in §7.**

### Data Engineering Lead

**Criticism**: "You never actually looked at what fraction of the remaining 40 tickers are banks (the EBIT/EBITDA-gap sector). That's a concrete, checkable fact you had the data to verify and didn't. Also, the 'UNRESOLVED' 30-document ticker gap — did you check if fixing THAT (a data-quality bug, not new extraction) might itself add usable candidates for free?"

**Response**: Both are legitimate, checkable gaps this audit left as prose speculation ("10 of the 100 IRU members are banks or bank-adjacent by ticker name inspection") rather than a verified count, and the UNRESOLVED-ticker question was flagged but never investigated. Correcting the record: this audit does NOT have a verified bank-count among the 40 remaining candidates — that estimate should be treated as unverified and is flagged here as a specific, cheap, concrete follow-up (a direct `sector_ngx`/company-type join against the 40-ticker list) that should be part of any depth-scoping pass, not left as an inspection-based guess. Similarly, the 30 UNRESOLVED documents represent a genuine, cheap-to-investigate data-quality question (why does `documents.ticker` come back NULL for these) that could recover additional candidates or additional documents for ALREADY-covered tickers at zero incremental extraction cost — this should be the very first, cheapest step of any future work, ahead of even the depth-scoping pass, and this audit should have said so more directly rather than mentioning it once in passing.

### Software Architect

**Criticism**: "Every recommendation in Section 9/10 assumes the CURRENT hand-verification architecture is the right one to keep scaling. But you documented, in Section 3.1, that the platform successfully automated an entirely different document type (DOL price lists) at huge scale. Did you seriously evaluate whether a hybrid approach — deterministic first-pass extraction with human verification only on low-confidence extractions — could be built for FSI, rather than treating 'more of the same manual process' as the only validated path?"

**Response**: This is a real gap in the options considered. The audit correctly established that TWO fully-deterministic/naive automated attempts (the EPS/P.E. parser) failed outright, and that no phase has ever tried a genuine HYBRID (automated-first-pass-plus-human-verification-of-low-confidence-cases) approach for financial statements specifically — this is a real, third category of extraction strategy that Section 3's summary table should have included as its own row rather than only presenting "fully automated" and "fully manual" as the two poles. Stated honestly: **a hybrid deterministic-extraction-with-human-spot-check approach has never been attempted or evaluated for FSI, and this audit cannot say whether it would work** — it is neither validated nor refuted by any existing evidence, and should be named as a genuine sixth decision option (call it Option F: pilot a hybrid extraction approach on a small sample before committing to either a pure-labor expansion (Options B-D) or accepting the current fully-manual method as the only scalable path). This is a real, missed alternative, not a minor omission — a hybrid approach, if it worked even partially, could change the entire cost calculus in §4, and no evidence currently exists either way.

---

*This document makes no recommendation to proceed with implementation. Per its own scope, it identifies what is known, what is estimated, what is unknown, and what a responsible next (still non-extraction, non-implementation) step would be: a cheap, read-only depth-scoping pass and a bank/sector composition check on the 40 remaining candidates, plus an investigation of the 30 UNRESOLVED-ticker documents — all before any labor-allocation decision is made.*
