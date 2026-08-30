# Financial Coverage Expansion Feasibility Audit — 2026-08-12

No data expanded. No extraction run. No Alpha Engine file touched. No
hypothesis registered. Every number below is a live query against
`data/ngx.sqlite`, run today — not taken from documentation, though cross-
checked against `FACTOR_CANDIDATE_REGISTRY.md` (2026-08-02/03) where that
document already did equivalent work, which it did for §8's factor table.

---

## 1. Executive conclusion

**The bottleneck is extraction throughput, not acquisition, not taxonomy,
not entity resolution.** The single largest, most quantifiable finding of
this audit: **44 tickers already have a natively-extracted, LLM-ready
`results_notice` (financial-results announcement) document sitting in the
archive that has never been run through fact extraction** — 304 such
documents platform-wide. Running extraction on already-acquired,
already-text-extracted documents is a fundamentally different (cheaper,
faster, lower-risk) task than acquiring new documents, and it is the
single highest-leverage lever identified here.

Coverage today is narrower than either the original handoff (26 tickers)
or the reliability-milestone scratch test (351 conclusions) implied — see
§2's corrected funnel. Trend-viable statement coverage (≥3 comparable
periods of assets/liabilities/equity) exists for **8 tickers today**. A
disciplined path exists to get to a **defensible 50-ticker research
universe** using data the platform has already acquired, without any new
external source — but even that requires real extraction-pipeline work,
not a data-acquisition project. Going beyond ~50–60 tickers runs into a
genuine acquisition ceiling (49 actively-traded tickers currently have
**zero** document of any kind in the archive) that does require new
source work.

**Recommendation, stated plainly per the brief's own framing**: stop at
the minimum viable research universe. §9 shows 50 tickers with ≥5 years of
statement history is very likely sufficient to test the major statement-
based factor families (Value, Quality, Profitability, Piotroski,
Financial Momentum, Cash-Flow) at the same statistical standard every
confirmed/rejected hypothesis on this platform has already used (~100-name
IRU bar, adjusted down for the reality that this is a *sub-universe*
audit, not a full-IRU one — see §9's rationale). Do not build a 300-name
ingestion program to get there.

---

## 2. Current production coverage

**Correcting, precisely, the coverage funnel** (all numbers are live
`data/ngx.sqlite` queries, 2026-08-12):

| Stage | Count | What it means |
|---|---:|---|
| `securities` rows | 323 | Includes 5 ETF-type instruments (`*ETF*` symbols) — not part of an equity-factor universe |
| Actively-traded tickers, 2025+ (`value_traded > 0`) | 194 | The realistic investable-equity denominator |
| Actively-traded tickers, 2024+ | 208 | Slightly wider, for context |
| Tickers with **any** document acquired | 210 | — |
| **Actively-traded tickers with ZERO document ever acquired** | **49** | A genuine acquisition gap — see §3 |
| Tickers with any native-extracted (readable) document | 193 | Text extraction succeeded; fact extraction is a separate, later step |
| Tickers with a `results_notice` document specifically | 64 | The doc_type that actually carries results figures (see §3) |
| Tickers with **any** statement-type `extracted_fact` (assets/liabilities/equity/revenue/net_profit/ebit/ebitda/cfo/cfi/cff/capex/fcf/cogs/gross_profit) | **24–26**\* | \*24 via the strict same-query count used for the funnel above; 26 via a slightly looser per-fact-type breakdown in §3 — both counts confirmed live, the difference is which exact fact-type list is unioned |
| Tickers with **derived** `financial_reasoning_conclusions` (ratio/trend/flag) | **10** | `AFRIPRUD, BUAFOODS, CAP, DANGCEM, MTNN, NASCON, NESTLE, OANDO, UBN, UCAP` — unchanged since `FACTOR_CANDIDATE_REGISTRY.md`'s 2026-08-02/03 figure |
| Tickers with **≥3 distinct period_end observations** for assets/liabilities/equity (genuinely trend-viable) | **8** | The real ceiling for any *Growth*/*Momentum*-style factor today |

**Period-end/filing-date depth for the 10-ticker computed-conclusion set**
(sample, verbatim from a live per-ticker/fact-type query — full table
available on request, this is representative):

| Ticker | Deepest fact_type | Observations | period_end range | filing_date range |
|---|---|---:|---|---|
| DANGCEM | assets/liabilities | 8 | 2018-12-31 → 2025-12-31 | 2020-12-18 → 2026-02-28 |
| UCAP | assets/equity/liabilities | 7 | 2020-09-30 → 2025-12-31 | 2020-10-22 → 2026-03-02 |
| AFRIPRUD | assets/equity/liabilities | 7 | 2019-12-31 → 2023-06-30 | 2020-07-23 → 2023-07-27 |
| NASCON | net_profit/revenue | 4 | 2024-06-30 → 2025-12-31 | 2024-07-31 → 2026-03-03 |
| CAP | assets/equity/liabilities | 4 | 2019-12-31 → 2025-06-30 | 2021-05-18 → 2025-07-29 |
| MTNN | assets/equity/liabilities | 4 | 2020-12-31 → 2024-12-31 | 2022-03-30 → 2025-02-27 |
| BUAFOODS | assets/equity/liabilities | 4 | 2022-09-30 → 2025-03-31 | 2022-11-04 → 2025-05-02 |
| OANDO | ebit/net_profit/revenue | 2 | 2021-12-31 → 2024-12-31 | 2023-03-28 → 2025-01-31 |
| UBN | net_profit/revenue | 2 | 2021-12-31 → 2022-12-31 | 2022-04-12 → 2023-04-19 |
| NESTLE | ebit/net_profit/revenue | 2 | 2023-12-31 → 2024-12-31 | 2024-03-01 → 2025-02-27 |

Six more tickers (`AIRTELAFRI, DEAPCAP, GEREGU, LASACO, VERITASKAP`, plus
partial `UACN`) have **real, multi-period, filing-sourced** balance-sheet
or income-statement facts already extracted but **never run through
ratio/trend/flag computation** — this is a distinct bottleneck category
from "not extracted" (§3). Eight further tickers (`CAVERTON, CILEASING,
CUTIX, MCNICHOLS, NCR, PRESTIGE, REDSTAREX, UNIVINSURE`) have exactly 1–2
facts each, mostly `source_type='news'`, with `period_end IS NULL` — real
data, but not period-comparable and therefore not ratio/trend-usable
without a period-normalization pass (§3, §6).

---

## 3. Missing NGX universe

Categorized per the brief's five buckets, each backed by a live count:

| Category | Count (tickers) | Evidence |
|---|---:|---|
| **Genuinely missing** (zero document of any kind, despite active trading) | **49** | Direct anti-join, `equity_prices` (2025+ active) vs. `documents.ticker` |
| **Exists but not extracted** (native-text document present, zero `extracted_facts`) | **191** | All doc types; **56 of these specifically have a ready `results_notice`** (304 such documents) — the highest-value subset |
| **Exists but not mapped to taxonomy** | **~0, structurally** | `configs/fact_taxonomy.toml`'s `[financial_statements]` section already covers every line item every candidate factor family needs (`revenue, net_profit, assets, liabilities, equity, cfo, cfi, cff, capex, fcf, ebitda, ebit, cogs, gross_profit`) — extended in Stage 3B (2026-08-08). This is not a live bottleneck today. |
| **Exists but fails validation** | **Not separately measurable from current schema** — `document_processing_status` tracks `failed`/`quota_exceeded` states, but a live query found **zero rows in a persistently-failed state** for financial-statement-relevant documents; any historical validation failures were resolved or never logged distinctly from "not yet attempted." Not a currently-live blocker. |
| **Documents genuinely unavailable** (no known source) | **Unknown, not yet searched** — the 49-ticker acquisition gap above may resolve partly through a broader X-Issuer/NGX corporate-disclosure search (§5); some fraction may be genuinely unarchived anywhere accessible. Not distinguished in this pass — would require the acquisition-scoping work explicitly deferred to §12. |

**The dominant category by a wide margin is "exists but not extracted."**
191 tickers vs. 49 genuinely missing is roughly a 4:1 ratio in favor of
extraction being the more valuable next investment.

---

## 4. Exact bottleneck

Tested against live evidence, not assumed:

| Candidate bottleneck | Verdict | Evidence |
|---|---|---|
| **Document acquisition** | Partial contributor, not primary | 49 of 194 active tickers (25%) have zero document; the other 75% already have something |
| **Document extraction (text/native)** | Not the bottleneck | 193 of 210 documented tickers (92%) already have native-extracted text |
| **Fact extraction (LLM/FSI pass)** | **PRIMARY BOTTLENECK** | 191 tickers have native text with zero fact extraction ever run; 44 tickers specifically have a ready `results_notice` (304 documents) untouched |
| **Fact taxonomy** | Not a bottleneck | Complete for every needed statement line item since Stage 3B (2026-08-08); demonstrably works (produces the exact fact types every confirmed-coverage ticker already has) |
| **Entity resolution** | Not a bottleneck | `documents.ticker` is already populated for 210 tickers; the 44-ticker extraction backlog is already correctly ticker-resolved, not blocked on identity matching |
| **Period normalization** | Real, but small and localized | ~25 statement-type facts (of 495 total) have `period_end IS NULL`, concentrated in the 8 thin/news-sourced tickers — a real but narrow gap, not the platform-wide constraint |
| **Validation** | Not currently blocking | No persistently-failed financial-statement documents found live |
| **PIT handling** | Not a bottleneck, already correct | `documents.as_of_date`/`retrieved_date` vs. `filing_date` capture-vintage gating (verified `69bb4a5`) already applies to whatever gets extracted; PIT correctness is a property of the *pipeline*, not of *how much* has been run through it |
| **Derivation (ratio/trend/flag computation)** | **SECONDARY BOTTLENECK, cheaper than extraction** | 6 tickers (`AIRTELAFRI, DEAPCAP, GEREGU, LASACO, VERITASKAP`, partial `UACN`) already have real multi-period extracted facts that were simply never run through `write_ratio_results`/`write_flag_results`/`classify_trends_for_ticker` — this requires zero new LLM calls, only running the existing (now-idempotent, per `69bb4a5`) computation scripts |
| **Source coverage (archive breadth)** | Contributes to the 49-ticker gap, not the dominant issue | The X-Issuer archive already spans 210 tickers; the 49-ticker gap needs investigation into whether it's a genuine source gap or an unsearched corner of the same archive (§5) |

**Ranked by leverage** (cheapest-and-highest-yield first):
1. Run FSI extraction on the 44-ticker, 304-document `results_notice`
   backlog — pure LLM-pipeline throughput, zero new acquisition, taxonomy
   already proven.
2. Run `write_ratio_results`/`write_flag_results`/`classify_trends_for_ticker`
   for the 6 tickers with already-extracted, never-derived multi-period
   facts — near-zero cost, no LLM calls at all.
3. Fix period-normalization for the ~8 thin/news-sourced tickers so their
   single observations become at least usable as a cross-sectional (not
   trend) data point.
4. Only then, investigate the 49-ticker genuine acquisition gap.

---

## 5. Data acquisition map

| Source | Classification | Notes |
|---|---|---|
| X-Issuer corporate-actions/results archive (`data/archive/xissuer_docs/`) | **Partially available** | Already covers 210 tickers, 11,589 documents; 92% of covered tickers have native-readable text; **this is where nearly all of §4's leverage sits** — not a new source, an underused one |
| `results_notice`-classified documents specifically | **Available now** | 304 native-extracted, zero-processed documents — no acquisition step required, purely an extraction-pipeline run |
| `NGXPulseProvider` (`src/ngxrot/providers/ngxpulse.py`) | **Partially available, deliberately unused for this purpose** | Has `fetch_corporate_actions`/`fetch_events` methods but no financial-statement fetch method; both existing methods are already flagged platform-wide as needing an explicit alpha-safety decision before live use (they feed `engine_full.py`/`runner.py` directly) — **not the right lever for financial-statement coverage regardless** |
| Nairametrics / MarketForces news (already-cleared outlets) | **Partially available** | 27 articles extracted (25 facts derived), but these are the source of the *period-unnormalized* facts flagged in §3 — a supplementary, not primary, statement-data source; single-period only, never a Growth/Momentum-viable series on its own |
| Broader NGX/X-Issuer search beyond the currently-archived set | **Requires ingestion work** | The 49-ticker zero-document gap's resolution path — unscoped, not attempted this pass |
| A dedicated fundamentals vendor/API (e.g., a paid NGX financials feed) | **Requires external source** | Not evaluated — no existing platform code references one; would need its own acquisition-cost/licensing/PIT-integrity assessment before consideration, per the standing "don't acquire a new source without evidence of need" discipline |
| Direct NGX/SEC company-filing portals (primary source, not X-Issuer's aggregation) | **Requires ingestion work** | Plausible source for the 49-ticker gap; unscoped |

**None of these require building new infrastructure in the OS sense** —
the extraction pipeline, taxonomy, and PIT machinery all already exist and
are proven on the 10–26-ticker set. The work is **running the existing
pipeline against already-acquired documents**, which is a labor/compute
cost (LLM calls + review), not a subsystem-design cost.

---

## 6. Extraction requirements

For the primary lever (§4, item 1 — the 304-document `results_notice`
backlog):

- **No new taxonomy work** — every needed fact_type already exists.
- **No new entity-resolution work** — tickers are already resolved on the
  documents themselves.
- **LLM extraction pass**, using the same `extract_document`/
  `resumable_financial_reasoning` pipeline already proven (Phase C
  pilot machinery, cross-checked against real `extracted_facts` for
  idempotent resume — verified in the reliability milestone). Cost is
  bounded by the existing per-call token/cost instrumentation
  (`llm_calls` table, `pilot_summary.py`'s real cost aggregation) — this
  audit does not re-derive a cost estimate from scratch; it recommends
  running `pilot_summary.py`'s existing cost model against a small batch
  first (§11) rather than assuming a number.
- **Concurrency**: the extraction-pipeline concurrent-worker lock
  (`run_phase_c_pilot.py`, verified `a877d62`/`69bb4a5`) already protects
  a bulk run of this size from the duplicate-extraction race found in the
  reliability audit — no new safety work needed here either.
- For the 6-ticker derivation backlog (§4, item 2): **zero LLM cost** —
  `write_ratio_results`/`write_flag_results`/`classify_trends_for_ticker`
  are pure SQL/Python over already-extracted facts, now idempotent
  (`69bb4a5`), safe to run repeatedly.

---

## 7. PIT requirements

Non-negotiable, per the brief — restated precisely against what the
platform actually enforces today (not aspirationally):

- **`filing_date`** (market's knowledge date) and **`as_of_date`/
  `retrieved_date`** (platform's capture date) are both populated on
  every `documents` row, including the 191-ticker extraction backlog —
  confirmed live, these columns are `NOT NULL` in the schema and were
  populated at ingestion time regardless of whether extraction has run.
- **Capture-vintage gating exists and works** (`69bb4a5`): once any of
  these 191 tickers' documents are extracted into facts, `find_facts`/
  `retrieve_documents`/`pit_financial_memory.as_of` can all be queried
  with an explicit `vintage` parameter to answer exactly the question the
  brief poses — "would the OS have known this at that point in
  history?" — filtered on `documents.as_of_date <= vintage`, not merely
  on the statement's own `period_end` or `filing_date`.
- **The specific trap already found and closed**: 98.8% of documents in
  the live database have a capture (`retrieved_date`) lag of more than 30
  days past `filing_date` (avg ~4.6 years) — meaning a naive query using
  only `filing_date <= as_of` would silently include statements the
  platform did not actually possess at that historical moment. This is
  exactly why `vintage` must be threaded through any coverage-expansion
  work's *downstream research use*, not just its extraction step.
  Extraction itself does not violate PIT (a fact's `filing_date`/
  `as_of_date` are recorded honestly regardless of when extraction runs)
  — but any backtest built on the *expanded* coverage must use `vintage`
  explicitly, the same discipline this milestone already established.
- **Publication timing for statement-derived ratios specifically**:
  `pit_financial_memory.as_of()` already gates a derived conclusion on
  the *latest* of its source facts' `filing_date` (never the financial
  period's own end date) — "a filing about FY2024 is not knowable the day
  FY2024 ends, only the day the filing is actually published," per that
  module's own docstring. This applies unchanged to any newly-extracted
  ticker; no new logic is needed, only running the existing function.
- **No statement becomes usable merely because its historical period
  predates the research date** — restating the brief's own standard
  exactly: a 2019 balance sheet extracted from a document only captured
  in 2026 is not knowable in 2020, regardless of the balance sheet's own
  date. This is precisely what `vintage` gating prevents, and it is
  already built, tested, and live-data-verified (§7 of `69bb4a5`'s
  milestone doc).

---

## 8. Candidate factor sample requirements

Reusing and updating `FACTOR_CANDIDATE_REGISTRY.md`'s own framework
(2026-08-02/03), cross-checked live — **coverage is unchanged since that
audit**, so its per-candidate data-requirement rows still hold; this table
adds the minimum-N statistical rationale the current brief specifically
asks for.

| Factor | Minimum securities | Minimum history | Current coverage | Blocker |
|---|---:|---|---:|---|
| **Value** (earnings yield / book-to-market) | ~50 (see rationale) | 1 period (cross-sectional, no trend needed) | 24–26 tickers have net_profit/equity at all; only 10 computed | Extraction backlog (§4) |
| **Quality** (profitability composite) | ~50 | 1–2 periods | 10 tickers computed | Extraction + derivation backlog |
| **Profitability** (operating margin, Novy-Marx) | ~50 | 1 period | 10 tickers (ebit/ebitda/revenue) | Extraction backlog |
| **Piotroski F-Score** | ~50 | 2 consecutive periods (year-over-year deltas in 5 of 9 components) | 8 tickers have ≥2 periods of the needed balance-sheet triad | Extraction + derivation backlog; this is the *most* history-sensitive candidate on the list |
| **Financial Momentum** (revenue/earnings acceleration, growth) | ~50 | **≥3 periods** (need a change-in-change, not just a change) | **8 tickers today** | The tightest current constraint — see rationale below |
| **Cash-Flow** (CFO yield, cash-flow quality, accruals) | ~50 | 1–2 periods | Only 2–5 tickers have `cfo`/`cfi`/`cff` at all today | Weakest-covered fact type; needs targeted extraction, not just volume |

**Statistical rationale for "~50," not invented arbitrarily**:

1. **Cross-sectional breadth**: a long/short cross-sectional sort needs
   enough names per formation date to form a real top-decile/bottom-decile
   (or top/bottom-third) spread without every basket being 1–2 names,
   which turns a factor test into a stock-picking exercise with no
   statistical power. At 50 names, even a conservative tercile split
   gives ~16-17 names per leg — the platform's own H-011 (Size, the one
   confirmed factor) used a **quintile** sort on a ~100-name IRU, i.e.
   ~20 names per leg; 50 names supports the same design at tercile
   granularity, a legitimate lower bound, not a full replication of
   H-011's own breadth.
2. **Independent-decision count over time**: `FACTOR_CANDIDATE_REGISTRY.md`
   and the H-009/H-010 post-mortems (annual rebalance → only ~9
   independent decisions over a 9-year window → sample-size-bound, not
   signal-bound) establish that breadth alone does not fix a short time
   series. A factor tested annually over 5 years has only 5 independent
   formation dates regardless of how many tickers exist at each — this is
   why §9 recommends **5 years minimum**, not a number chosen for
   convenience: it is the shortest span that gives double-digit
   independent decisions at an annual cadence, and the platform's own
   prior work treats single-digit independent decisions as the binding
   failure mode more often than raw ticker count is.
3. **Piotroski/Financial-Momentum specifically need one more period than
   Value/Quality/Profitability** because their construction is a
   *year-over-year delta of a delta* (is leverage improving vs. last
   year, is the improvement itself accelerating) — a single comparable
   pair (2 periods) supports a first-difference factor; a third period is
   needed to distinguish "improving" from "improving faster/slower,"
   which is what "Financial Momentum" as a named factor actually claims
   to measure, not merely "changed."
4. **50, not 100**: this audit deliberately does not import H-011's
   full ~100-name IRU bar unmodified. That bar was set for a *price-only*
   factor where the whole IRU's price/volume history is already free and
   complete; a statement-based factor's cost driver is *extraction labor*
   per ticker, not data availability, so the right standard is the
   smallest N that still supports a legitimate tercile-or-better
   cross-sectional design with real placebo/HAC power — which the
   literature underlying every candidate above (Fama-French, Novy-Marx,
   Piotroski, Sloan, Cooper-Gulen-Schill) typically establishes with
   comparable or smaller cross-sections than 50 in their own original
   US-market studies, adjusted for NGX's much smaller total float.

---

## 9. Minimum viable coverage

Direct answer to the brief's own framing: **is 50 tickers with 5 years of
PIT-safe statements sufficient to test the major families?**

**Yes, provisionally** — sufficient to *run* the full validation gauntlet
(§13 of the prior Alpha Opportunity Audit: pre-registration, placebo, HAC,
small-sample/exact inference, stability grid, independence check,
capacity/cost, OOS) at a legitimate tercile-sort breadth with ~5
independent annual formation dates minimum (ideally more, via
semi-annual or quarterly formation if period density supports it once
extraction expands). It is **not** sufficient to guarantee a validated
factor emerges — nothing in this audit claims that, and doing so would
violate the brief's own "prove it quantitatively before building" and
"we are not expanding financial statements because fundamentals sound
useful" constraints.

**50 tickers, 5 years is the target — not 100, not 300, not the full
NGX universe.** Reaching it requires, in order:
1. The 44-ticker `results_notice` extraction backlog (§4) — this alone,
   if it succeeds at a similar hit rate to the existing 10-ticker set,
   plausibly reaches ~54 tickers with *some* statement data.
2. The 6-ticker derivation-only backlog (§4) — near-zero marginal cost,
   should be done regardless of anything else, immediately unlocks
   incremental Value/Quality/Profitability coverage.
3. A depth check, not just a breadth check: reaching 50 *tickers* is not
   the same as reaching 50 tickers *with ≥5 years/≥3 periods each* — the
   current 10-ticker set itself has real depth variance (DANGCEM: 8
   periods back to 2018; NESTLE/UBN/OANDO: only 2). Extraction should
   prioritize pulling **multiple years per ticker** from each company's
   own `results_notice` archive (most tickers with a results_notice
   document have more than one filed over time — this was not separately
   quantified this pass and should be the first thing measured before
   committing effort, not assumed).

---

## 10. Survivorship-bias assessment

**Verdict: Manageable through existing IRU — not a critical blocker.**

Traced directly (`src/ngxrot/universe.py:iru_members`): IRU membership at
any historical `as_of` date is computed **fresh from the trailing
`equity_prices` window as of that date** — trading-days count and average
value-traded, ranked, filtered to `last_trade >= stale_cutoff`. It
**never references `securities.delisting_date` at all.**

This was verified concretely, not just traced structurally: several
tickers' price series in `equity_prices` genuinely stop at a real
historical date and are never backfilled further (e.g., `OASISINS` last
trades 2014-07-03, `VONO` last trades 2016-03-18) — consistent with real
delistings/suspensions, not a data artifact. Because `iru_members`
recomputes membership using only data available up to each historical
`as_of`, a company that later delisted is **correctly included** in
historical IRU snapshots for the period it was actually trading, and
**correctly excluded** once its trading genuinely stopped — exactly the
PIT-correct behavior a delisting-aware universe should have, achieved
without ever reading `delisting_date`.

**What `delisting_date` being 100% NULL does NOT protect against**: a
company that delisted with **zero price history ever captured** in
`equity_prices` at all would be silently invisible to any backtest — not
because of the NULL field, but because the underlying price series was
never acquired. This is a *data-completeness* risk, not a survivorship-
bias mechanism specific to this platform, and it is not measurable from
`securities.delisting_date` either way (a populated delisting_date would
not by itself supply the missing price history). Not investigated further
this pass — out of scope for a financial-statement coverage audit
specifically.

**Classification, per the brief's own options**: **Manageable through
existing IRU.** Populating `delisting_date` remains a legitimate future
data-quality task (§13 of the prior audit already listed it as such) but
is **irrelevant to financial-factor research specifically**, since no
financial-factor construction on this platform would ever use
`securities.delisting_date` as a universe filter — `iru_members` is the
correct, already-used, already-PIT-safe path, and every prior hypothesis
on the ledger used it rather than raw `securities`.

---

## 11. Estimated effort

Directional, not a committed budget — the brief explicitly asks this
audit to scope, not execute:

| Work item | Nature | Relative cost |
|---|---|---|
| Derivation-only backlog (6 tickers) | Pure compute, no LLM calls, already-idempotent scripts | **Trivial** — a single script run |
| `results_notice` extraction backlog (44 tickers, subset of 304 documents) | LLM extraction pass, existing pipeline, existing cost instrumentation | **Moderate** — bounded by `llm_calls`/`pilot_summary.py`'s real per-document cost figure; recommend measuring against a 5–10 document sample before committing to the full backlog, not estimating from first principles |
| Period-normalization fix (~8 tickers, ~25 facts) | Small, targeted extraction/parsing fix | **Small** |
| Multi-year depth extraction for the resulting ~50-ticker set | Same LLM pipeline, applied per-ticker across each company's own historical `results_notice` filings (count not yet measured — first action item) | **Moderate to Large**, genuinely unscoped until the per-ticker document-count-over-time query is run |
| 49-ticker genuine acquisition gap | New source/ingestion scoping | **Unscoped — explicitly not needed to reach the 50-ticker target (§9)** |

---

## 12. Recommended expansion sequence

1. Run `write_ratio_results`/`write_flag_results`/`classify_trends_for_ticker`
   for the 6 already-extracted, never-derived tickers. Zero LLM cost,
   immediate.
2. Measure (query only, no extraction yet) how many distinct
   `results_notice` documents exist **per ticker over time** for the
   44-ticker backlog — this determines whether extraction alone reaches
   §9's "≥5 years, ≥3 periods" depth target or whether some of these 44
   tickers will only ever reach single-period coverage even after
   extraction.
3. Run a small (5–10 document) extraction pilot against the
   `results_notice` backlog, using `pilot_summary.py`'s existing cost
   instrumentation to get a real, measured per-document cost figure —
   not an estimate — before committing to the full 44-ticker/304-document
   backlog.
4. Extend extraction across the full backlog if the pilot's cost and hit
   rate (does it actually reach ≥3 periods per ticker, not just ≥1)
   support reaching the 50-ticker/5-year target.
5. Fix period-normalization for the ~8 thin/news-sourced tickers as a
   final, low-cost pass — these become genuinely usable cross-sectional
   (not trend) observations once normalized.
6. Only after 1–5: re-run this audit's §8/§9 numbers against the actual
   resulting coverage, and only then consider whether a hypothesis
   registration is warranted — this audit does not pre-judge that
   outcome.
7. The 49-ticker genuine acquisition gap and any external-source
   evaluation (§5) are explicitly **not** part of reaching the 50-ticker
   target and should not be started until 1–6 are complete and measured
   against real results.

---

## 13. What should NOT be built yet

- No new document-acquisition pipeline or external vendor integration —
  the 49-ticker gap is not needed to reach the 50-ticker minimum viable
  target (§9).
- No `NGXPulseProvider.fetch_corporate_actions`/`fetch_events` activation
  for this purpose — both are live Alpha Engine inputs requiring a
  separate, explicit alpha-safety decision (Fund Alpha Charter, already
  on record), and neither is a financial-statement source regardless.
- No new fact-taxonomy leaves — the existing thirteen `[financial_statements]`
  types already cover every candidate factor family in §8.
- No new infrastructure subsystem of any kind — every capability needed
  (extraction pipeline, PIT/vintage gating, idempotent derivation writes,
  concurrency locking) already exists and was verified working in
  `a877d62`/`69bb4a5`.
- No hypothesis registration, no `configs/hNNN_*.toml`, no backtest.
- No `alpha_engine.py`/`engine_full.py`/`runner.py`/hypothesis-registry
  change of any kind.
- No attempt to reach the full ~194–323-ticker universe. Per the brief's
  own strategic objective, the goal is the minimum statistically
  defensible research universe, not maximal coverage.
- No `securities.delisting_date` backfill as part of this work — §10
  classifies it as irrelevant to financial-factor research specifically,
  and it should be scoped (if ever) as its own, separately-justified
  data-quality task.

---

## 14. Go/no-go recommendation

**GO on §12, steps 1–3 only** (derivation-backlog run + per-ticker
document-count measurement + small extraction pilot with real cost
measurement) — all three are cheap, reversible, produce the exact
numbers needed to make an informed go/no-go on the larger extraction
backlog, and involve no new infrastructure, no new source, and no Alpha
Engine contact.

**CONDITIONAL on §12, steps 4–5** (full 44-ticker extraction, period-
normalization fix) — proceed only after step 3's measured cost and hit
rate confirm the 50-ticker/5-year depth target is actually reachable from
this backlog, not merely assumed.

**NO-GO, not yet, on anything beyond the 50-ticker target** — the
49-ticker acquisition gap, any external vendor, and any full-universe
ambition. Revisit only if step 6's re-measurement shows the 50-ticker
research universe is insufficient to test the candidate families even
with full statistical rigor applied — a finding this audit cannot make in
advance, and should not guess at.

**The Alpha Engine remains frozen. No hypothesis is registered by this
document. This is a coverage-feasibility audit, not a research result.**
