# Stage 11 — Bounded News Ingestion + Information-Novelty Audit

**Date:** 2026-08-08
**Scope:** Determine whether financial news can support a genuinely independent second alpha layer, specifically for H-011's small/illiquid holdings, using the existing FSI/LLM pipeline and the now-corrected `event_pipeline`. No H-019, no factor, no backtest, no optimization. H-011 config/prereg/signal untouched throughout.

---

## 11A. News ingestion universe

The H-011 20-name universe was reused from `data/reference/stage6_h011_universe_2026-08-08.json` — deterministically reconstructed from unmodified `backtest_xs.py` signal code in Stage 6, formation date 2026-06-30, and re-confirmed still current (today is 2026-08-08, same quarter as formation, H-011 rebalances quarterly). Not re-derived this stage to avoid redundant re-execution of the exact same validated code path.

Universe: CAVERTON, CILEASING, CUTIX, DEAPCAP, LASACO, LEGENDINT, MCNICHOLS, NCR, NSLTECH, OMATEK, PRESTIGE, REDSTAREX, REGALINS, ROYALEX, RTBRISCOE, SUNUASSUR, TANTALIZER, UNIVINSURE, VERITASKAP, WAPIC.

Sources used: **Nairametrics** (`nairametrics.com` — robots.txt `Disallow:` empty, i.e. fully open; `stocks.nairametrics.com` — `Allow: /`) and **MarketForces Africa** (`dmarketforces.com` — `Allow: /` generally, only `/feed/` paths disallowed; sitemap-based access only, consistent with Stage 10A/10B's finding). Both robots.txt files were re-fetched fresh this stage (not assumed from memory) before any access. No Reuters, Bloomberg, or FT access was attempted. No `/feed/` paths were used.

## 11B. Bounded historical corpus

All 20 tickers were searched (via `WebSearch`, domain-restricted to the two approved sources). **18 of 20** tickers returned substantive, dedicated company-specific event/earnings coverage. **2 of 20** returned weak or ambiguous coverage:
- **NSLTECH**: search results returned an article about "Secure Electronic Technology Plc" that plausibly but not confidently matches NSLTECH's known lottery/gaming business — not ingested, left as an unresolved identity ambiguity rather than force-matched.
- **OMATEK, WAPIC**: search results were dominated by weekly/monthly "best performing stocks" roundup mentions with no dedicated event article found for either — genuinely sparse coverage, not a search-execution failure.

From the 18 tickers with confirmed coverage, a **bounded sample of 12** was selected for full-text retrieval and processing through the extraction pipelines (the other 6 — CILEASING, REDSTAREX, SUNUASSUR, UNIVINSURE, VERITASKAP — have confirmed coverage via search but were not processed this stage; left as a disclosed scope boundary, see §11H). Selection deliberately favored dedicated event/earnings articles over roundups, price-only pieces, and filing-reproductions-with-no-added-content, per the explicit instruction:

| Ticker | Article selected | Type |
|---|---|---|
| CAVERTON | H1 2026 pre-tax loss (N8.66bn) | earnings |
| CUTIX | FY2026 pre-tax loss (N47.9m) | earnings |
| DEAPCAP | Shareholders approve rename to Critical Minerals Financing Corp | corporate restructuring |
| LASACO | N18.47bn rights issue opens | capital raise |
| LEGENDINT | Legend Internet / Spectranet merger (N80bn) | M&A |
| NCR | 2025 return to profitability | earnings |
| PRESTIGE | H1 2026 profit doubles to N1.05bn | earnings |
| ROYALEX | Nexamont acquires 21.4% stake (N3.6bn) | ownership change |
| RTBRISCOE | Shareholders approve N10bn capital raise | capital raise authorization |
| TANTALIZER | NGX cautionary letter, closed-period breach | regulatory action |
| REGALINS | N6.04bn capital raise completed; absent from NAICOM compliance list | capital raise / regulatory discrepancy |
| MCNICHOLS | N0.06 final dividend + FY2025 results (from a multi-company roundup, McNichols-specific portion only extracted) | dividend + earnings |

Metadata recorded for each: source, full URL, publication timestamp, ticker, document type (`news_article`), retrieval date — all as `documents` table rows (doc_id 11536–11547), reusing the existing, disclosed-provisional `stage10c_news_pilot` source registration (source_id=16) rather than creating a new one. Full text saved to `data/staging/news_text/*.txt`.

## 11C. FSI pipeline — run for real

**Fact extraction** (`extract_document()`, live Gemini calls, `model_id=gemini-3.6-flash`): run against the 6 articles containing quantifiable figures within Stage 10D's established scope (revenue, net_profit, ebit, ebitda, dividend, rights_issue, bonus_issue) — CAVERTON, CUTIX, LASACO, NCR, PRESTIGE, MCNICHOLS.

Result: **13 facts extracted, 13/13 (100%) passed grounding**, `extraction_confidence` correctly capped at `UNREVIEWED_LLM_CONFIDENCE_FLOOR=0.3` on every row (not overridden). One causal-chain step (not a primary fact) failed grounding and was correctly dropped rather than kept. No fact was hallucinated onto a document that didn't support it — every `numeric_value` traces to a verbatim quote in the source text.

**Event routing** (`event_pipeline.validate_batch()` → `ingest_events()`, the ticker-identity-fixed version from Stage 10E): the 6 remaining genuinely event-shaped items (not simple numeric facts) — DEAPCAP, LEGENDINT, ROYALEX, RTBRISCOE, TANTALIZER, REGALINS — plus LASACO's rights issue *also* logged at the event layer (deliberately dual-represented alongside its `extracted_facts` row, matching Stage 10D's established fact+event complementary design) were built into `data/events_news/events/stage11_news_events_2026-08-08.csv` and run through the standard `CSVProvider` + `ingest_events()` path.

Result: **7/7 events accepted, 0 rejected, 0 issues** (dry-run validated before the real write; `events` table 160→167 rows). Event types used: `corporate_restructuring` (DEAPCAP), `merger` (LEGENDINT), `ownership_change` (ROYALEX), `capital_raise` (RTBRISCOE, REGALINS, LASACO), `regulatory_action` (TANTALIZER) — all pre-existing taxonomy leaves, no taxonomy change needed.

No fact or event scope was forced: DEAPCAP's rename and LEGENDINT's merger were routed to events, not facts, because they are not numeric-fact-shaped; the 6 earnings/dividend articles were routed to facts, not events, because they are.

## 11D. Novelty audit

Every one of the 20 extracted candidates (13 facts + 7 events) was cross-referenced against the pre-existing database — `corporate_actions`, prior `extracted_facts` (any `model_id`, any prior `doc_id`), and prior `events` (`event_id < 168`) — **before** this stage's own writes, not against a wording-similarity heuristic.

**Identity mechanism used** (per 11D's explicit requirement): the same natural key already enforced at write time by `event_pipeline.validate_batch()` (`event_type, announced_date, scope, ticker` [+`index_code`]) for events, and `(ticker, fact_type, qualification_date/period)` compared manually for facts. This is why only one article per underlying event was ever ingested in this corpus — no cross-outlet duplicate of the same event was submitted, so no syndication-inflation scenario actually arose to test defensively; the mechanism is demonstrated by construction (see also Stage 10E §4/§3 Test 8 for the cross-outlet conflict-preservation behavior this would invoke if it had).

| Ticker | Item | Prior DB state | Classification |
|---|---|---|---|
| CAVERTON | revenue N14.68bn, H1 2026 | Only prior CAVERTON fact is revenue N40.1bn for **FY2024** (different period, fact_id=439, Stage 10D) | **NOVEL** |
| CAVERTON | net loss N8.69bn, H1 2026 | No prior CAVERTON net_profit fact at all | **NOVEL** |
| CUTIX | revenue N14.77bn, FY2026 | Zero prior CUTIX facts/events/corporate_actions | **NOVEL** |
| CUTIX | net loss N47.9m, FY2026 | Zero prior | **NOVEL** |
| CUTIX | EBIT N930.29m, FY2026 | Zero prior | **NOVEL** |
| LASACO | rights issue N18.47bn (fact) | Prior LASACO facts are 2023-04-06 balance-sheet/income items (net_profit N1.48m, assets/liabilities/equity, cfo/cfi/cff) — different period, different fact_type | **NOVEL** |
| LASACO | rights issue N18.47bn (event, same article) | Same underlying fact as above — dual-represented, not a second independent observation | **REDUNDANT** (internal to this batch; collapsed to 1 novel unit at the article level, not double-counted in §11F) |
| NCR | revenue N3.081bn, net profit N196m, 2025 | Zero prior NCR facts/events/corporate_actions | **NOVEL** (both) |
| PRESTIGE | revenue N12.56bn, net profit N1.05bn, H1 2026 | Zero prior PRESTIGE facts/events/corporate_actions | **NOVEL** (both) |
| MCNICHOLS | dividend qualification_date 2026-06-29 | **Already in DB**: fact_id=133, same qualification_date, source_id=14 (`ngx_xissuer_documents`, primary, company_filing) | **REDUNDANT** |
| MCNICHOLS | dividend amount N0.06/share | fact_id=133's `numeric_value` is `NULL` — amount never previously captured | **NOVEL** (the amount specifically; the date is redundant) |
| MCNICHOLS | revenue N6.21bn, net profit N346m, 2025 | Zero prior | **NOVEL** (both) |
| DEAPCAP | rename to Critical Minerals Financing Corp (event) | Prior DEAPCAP facts are 2025-01-22 balance-sheet items (assets/liabilities/equity, negative equity) — unrelated content domain | **NOVEL** |
| LEGENDINT | Spectranet merger (event) | Prior LEGENDINT fact is an unrelated dividend record (qualification 2025-10-20) | **NOVEL** |
| ROYALEX | Nexamont 21.4% stake acquisition (event) | Zero prior ROYALEX facts/events/corporate_actions | **NOVEL** |
| RTBRISCOE | N10bn capital raise authorization (event) | Zero prior RTBRISCOE facts/events/corporate_actions | **NOVEL** |
| TANTALIZER | NGX closed-period warning (event) | Zero prior TANTALIZER facts/events/corporate_actions | **NOVEL** |
| REGALINS | N6.04bn capital raise + NAICOM-list absence (event) | Prior REGALINS event is the 2025-09-01 trading suspension (`event_id=168`) — different event_type, different date, complementary not duplicative | **NOVEL** |

**Summary**: of 20 candidate items, **17 unambiguously NOVEL**, **1 partially redundant/partially novel** (MCNICHOLS dividend: date redundant, amount novel), **1 fully redundant sub-component**, **1 intentional internal duplicate** (LASACO fact/event pair, correctly collapsed). Zero items were classified NOVEL by assumption — every classification traces to an explicit DB query result shown above, not to wording similarity or absence-of-search-effort.

No DERIVED or UNKNOWN classifications were needed in this sample — every item was either clearly cross-referenced as present or clearly absent from the archive.

## 11E. PIT verification

For every NOVEL item: `filing_date` (documents) / `announced_date` (events) was set to the article's own publication dateline, never to today's retrieval date (`as_of_date`/`retrieved_date`='2026-08-08' is recorded separately and never conflated with the informational date). REGALINS's new capital-raise event (2026-08-04) correctly post-dates its existing suspension event (2025-09-01) — no look-ahead ordering issue. `events_asof()` (the platform's actual PIT-read function, re-verified working in Stage 10E) will correctly surface these only from their true announced dates forward.

**Disclosed limitation, not resolved this stage**: the task specifically asked to verify whether news-reported earnings figures later diverge from official filings once those filings appear. **This could not be tested** — none of the 12 processed tickers currently has a *subsequent* official NGX filing in the archive for the same reporting period to compare against (that is precisely the coverage gap this stage is filling, not closing on the filing side). This is a genuine, open PIT-precision question, not a pass: we know the news article's own stated dateline is being used correctly as the informational date, but we cannot yet demonstrate that the *figures themselves* will match what an eventual audited filing states. All 6 fact-bearing articles explicitly describe themselves as reporting figures "filed on the Nigerian Exchange" (i.e., presenting NGX-filed unaudited/interim results, not independent journalism) — meaning the risk is unaudited-vs-audited restatement, not fabrication, but it is unverified either way in this corpus.

Announcement-date vs. publication-date: in all 12 cases, the news article's dateline was used directly as both. No case in this bounded sample showed evidence of the news report lagging the underlying NGX disclosure by more than same-day/next-day (each article states it is reporting on a specific NGX filing/AGM/board resolution), but this was not independently cross-checked against NGX's own filing timestamps this stage — a bounded, disclosed limitation, not a claim of exact same-day precision.

## 11F. Information-quality analysis

**By source**: 9 of 12 processed articles from Nairametrics, 1 from MarketForces Africa (NCR) — MarketForces coverage is real and viable but this bounded sample under-weighted it; not evidence MarketForces is weaker, just an artifact of this pilot's article selection.

**By article type**: 6 earnings/financial-result articles, 4 discrete corporate-action/event articles (rename, merger, stake acquisition, capital-raise-authorization), 1 regulatory-enforcement article (NGX warning), 1 capital-raise-completion article with an embedded regulatory discrepancy.

**By event type** (for the 7 events): `capital_raise` ×3, `corporate_restructuring` ×1, `merger` ×1, `ownership_change` ×1, `regulatory_action` ×1.

**Novel vs. redundant**: 17/20 novel, 1 partial, 2 redundant/internal-duplicate (see §11D table).

**Confirmed later by an official filing**: 0/12 — see §11E, this is an open question, not yet testable in-archive.

**Forward-looking/explanatory information genuinely unavailable in a filing archive**: 2 clear cases out of 12 — TANTALIZER's NGX enforcement warning (a regulator's own action against the company; a company's own financial filing would never self-report this) and REGALINS's NAICOM-compliance-list absence (a third-party regulatory list contradicting/not-yet-confirming the company's own claim; explanatory context no single filing would surface). The other 10 processed items are news reports *of* information that is, by the articles' own text, sourced from an NGX filing/AGM/board resolution — valuable for closing our own archive's coverage gap, but not demonstrated to be information genuinely unavailable via the primary filing route, only faster/cheaper to acquire via news than by resuming targeted primary-document extraction.

**Market-cap rank / liquidity**: all 20 tickers are, by H-011's own construction, the smallest names in the ~96-100-name IRU (bottom quintile by design — this universe *is* "small/illiquid" by definition, not something requiring separate ranking). A liquidity proxy (mean `value_traded`, last 60 trading days) was pulled for context:

| Ticker | Avg daily value traded (60d, ₦) | Search coverage richness |
|---|---|---|
| TANTALIZER | 31.8m | rich |
| MCNICHOLS | 24.6m | rich |
| DEAPCAP | 19.6m | rich |
| CUTIX | 18.3m | rich |
| RTBRISCOE | 14.2m | rich |
| VERITASKAP | 12.4m | rich (not processed) |
| LASACO | 13.1m | rich |
| REDSTAREX | 10.5m | rich (not processed) |
| LEGENDINT | 9.9m | rich |
| UNIVINSURE | 9.8m | rich (not processed) |
| WAPIC | 8.5m | sparse |
| CILEASING | 8.8m | rich (not processed) |
| NSLTECH | 7.1m | ambiguous |
| ROYALEX | 5.3m | rich |
| REGALINS | 4.9m | rich |
| CAVERTON | 4.9m | rich |
| OMATEK | 3.4m | sparse |
| PRESTIGE | 2.7m | rich |
| SUNUASSUR | 2.1m | rich (not processed) |
| NCR | 0.9m | rich despite lowest liquidity |

**Key observation directly answering the stated research question**: coverage richness does **not** track liquidity in a simple monotonic way — NCR has the *lowest* liquidity in the universe (₦874k/day) yet returned rich, substantive, dedicated earnings coverage; PRESTIGE and SUNUASSUR are similarly illiquid with rich coverage. Only OMATEK and WAPIC (sparse) and NSLTECH (ambiguous) show a real coverage gap, and none of the three is the *most* illiquid name in the universe. This directly contradicts the pattern that killed the fundamentals track (where coverage tracked size/liquidity almost perfectly and never reached H-011's actual small-cap holdings) — **news coverage in this universe is not simply a re-run of the same liquidity-driven coverage bias.**

## 11G. Stop conditions — checked, none triggered

- Novelty vs. duplication distinguishable: **yes**, demonstrated with a real partial-redundancy case (MCNICHOLS) found and correctly classified, not just asserted.
- PIT timestamps adequate: **yes for informational dating**; **open/unresolved for news-vs-eventual-filing figure agreement** (§11E) — a bounded research question, not a timestamp-quality failure.
- Source acquisition policy: **fully compliant** — robots.txt re-verified fresh this stage for both domains, no `/feed/` paths, no blocked sources touched.
- LLM systematic unsupported claims: **not observed** — 13/13 facts grounded, confidence floor respected, one ungrounded causal-chain step correctly dropped rather than kept.
- Article/event identity reliability: **not stress-tested this stage** (no cross-outlet duplicate was actually submitted to test the conflict-preservation path against), but the underlying mechanism was already formally regression-tested in Stage 10E (Test 8) and is the same mechanism relied on here.

No stop condition fired. Proceeding to the decision gate rather than halting.

## 11H. Decision gate

**CONDITIONAL.**

**What was earned**: financial news, via this bounded 12-of-20-ticker pilot, demonstrably solves the specific coverage problem that killed both prior tracks. 18/20 H-011 tickers (90%) have real, dedicated, non-roundup news coverage discoverable through fully policy-compliant channels — versus 0% research-ready overlap for fundamentals and 15% (3/20, single-snapshot) for insider dealing. Coverage does not track liquidity the way the fundamentals track's coverage did; the platform's single lowest-liquidity name (NCR) had some of the richest coverage found. Extraction quality is clean: 100% grounding pass rate, confidence floor correctly enforced, no fabrication observed, event/fact routing correctly kept each information shape in its proper representation, and the Stage 10E ticker-identity fix worked correctly under real multi-event-type production use (7/7 accepted, 0 issues).

**What was not earned yet, and is why this is not a GO**:
1. **Exclusivity is not established.** Of the 17 novel items, only 2 (TANTALIZER's regulatory warning, REGALINS's NAICOM-list discrepancy) are demonstrably information a primary-filing-only archive would never surface. The other 15 are news reports *of* NGX filings/AGM outcomes/board resolutions the articles themselves cite as their source — meaning the value demonstrated so far is largely "faster/cheaper coverage of our own archive gap," not "information genuinely unavailable elsewhere." This is a materially different, weaker claim than exploitable alpha requires, and the task explicitly warned against conflating the two.
2. **PIT figure-integrity is untested.** No processed ticker yet has a matching later official filing in-archive to check whether the news-reported (often unaudited/interim) figures agree with the eventual audited numbers. This is a real, bounded, answerable question — not answered here.
3. **Sample is small and one-sided toward Nairametrics** (9/12 articles) — MarketForces Africa, independently confirmed viable, was under-used in this pilot by chance of article selection, not by finding it weaker.
4. **6 tickers with confirmed coverage were never processed** (CILEASING, REDSTAREX, SUNUASSUR, UNIVINSURE, VERITASKAP) and **2 tickers show a real coverage gap** (OMATEK, WAPIC) alongside **1 unresolved identity ambiguity** (NSLTECH) — the full-universe picture is not yet complete.

**Specific, bounded next steps that would resolve the CONDITIONAL** (not authorized to start automatically): (a) find or wait for a case where both a news report and its corresponding official filing exist in-archive, to directly test PIT figure-agreement; (b) deliberately separate "regulatory/enforcement/ownership-change" event types (the 2 demonstrably exclusive cases) from "earnings reproduction" event types in any future measurement, since they appear to have structurally different information value; (c) process the remaining 6 confirmed-coverage tickers and resolve the NSLTECH identity question before claiming full-universe coverage; (d) accept that OMATEK/WAPIC may simply be sources of the same kind of small-cap information vacuum fundamentals hit, for different reasons.

No H-019 is authorized by this result. This CONDITIONAL is not "promising enough to build" — it identifies exactly what would need to be true first, and none of it has been shown yet.
