# STAGE 10A — NEWS ARCHITECTURE AUDIT + SOURCE FEASIBILITY + H-011 COVERAGE PILOT

*2026-08-08. Design/audit stage. No article extracted into `extracted_facts`
or `investment_implications`. No article scraped in violation of robots.txt
or terms of use. `configs/h011_size.toml`, `docs/PREREG_H-011.md`, H-011's
signal/construction, and all frozen experiment results are unmodified. No
hypothesis created.*

**Files changed**: `configs/event_taxonomy.toml` (14 new leaves under the
existing `[corporate]` category — additive, zero existing leaves touched),
`configs/document_taxonomy.toml` (1 new `[news]` category, 1 leaf —
additive). No database schema changes made; a `news_outlets` table is
**proposed**, not created (Section 2).

---

## 1. Architecture Audit — What Already Exists (and Was NOT Used in Stages 1-9)

**Correction of my own prior framing, stated directly**: everything I
extracted in Stages 3-9 was **hand-transcription** (`model_id = NULL`,
`extraction_confidence` set by me, no LLM call) — I never invoked this
platform's actual LLM reasoning pipeline. That pipeline exists, is
substantially built, and **has been used for real** (verified directly):

| component | file | status | verified real usage |
|---|---|---|---|
| Document→Facts→Causal-chain→Impact→Implication LLM pipeline | `src/ngxrot/documents/extract.py` | Built, functional | **41 `llm_calls` rows, 18 `investment_implications` rows, 18 `extracted_facts` with a real `model_id`** — a small real pilot, not vaporware |
| LLM provider abstraction | `src/ngxrot/documents/llm_providers.py` | Built | Gemini 3.6-flash, config-driven (`configs/llm_provider.toml`) |
| **Live credential check this session** | — | — | **`GEMINI_API_KEY` is set and available right now** — the pipeline is operationally runnable today, not just designed |
| Grounding check | `src/ngxrot/documents/grounding.py` | Built, reused throughout Stages 3-9 by me directly | Yes |
| Self-critique (8-question adversarial review) | `src/ngxrot/documents/self_critique.py` | Built | Not inspected in depth this stage; exists as the gate between `draft_pending_self_critique` and any more-trusted status |
| Entity resolution | `src/ngxrot/documents/entities.py` | Built | Used by `extract.py`'s `resolve_or_create_entity` |
| Fixed vocabularies (directions, impact categories, confidence rules) | `src/ngxrot/documents/vocab.py` | Built | `UNREVIEWED_LLM_CONFIDENCE_FLOOR = 0.3` — every LLM-derived fact/implication is capped low until human review, mechanically, not by convention |
| Coverage/evidence-trust scoring | `src/ngxrot/documents/evidence_ranking.py`, `coverage_assessment.py` | Built | `EVIDENCE_TRUST_TIERS` **already reserves tier 3 = "secondary_reputable" explicitly for news** — quoted directly: *"reserved: news/analyst source with a verified reliability tier"* |
| Event ingestion pipeline | `src/ngxrot/event_pipeline.py` | Built, used for CBN/MPC events | Taxonomy validation, chronology checks, duplicate/conflict detection (PIT append-only), quality reporting — directly reusable for news-sourced discrete events, zero code change needed |
| Event taxonomy | `configs/event_taxonomy.toml` | Built | `[corporate]` category already had 11 ticker-scoped leaves overlapping the news taxonomy this stage was asked to design; **14 more added this session** (Section 4) |
| Document-type taxonomy | `configs/document_taxonomy.toml` | Built, filing-only until this stage | New `[news]` category added this session |
| `NewsDocumentProvider` | — | **Confirmed NOT built** — a stale reference existed only in a compiled `.pyc`, not the current `.py` source (verified directly) | Matches the architecture doc's own "not yet built" status, unchanged since 2026-07-22 |
| `news_outlets` reference table | — | **Confirmed does NOT exist** | Required before any news evidence can reach trust tier 3 (explicit rule, `vocab.py`'s own comment: "populated by owner judgment... never inferred by the AI itself") |
| Design authority | `docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md` (2026-07-22, rev 2) | Design doc, largely implemented since | Explicitly names a "News Understanding Engine" module and lays out the exact ingestion pattern this stage follows |

**What this means for design**: news should NOT get a parallel schema.
Two existing pipelines split the work cleanly:

1. **Discrete, dateable events** (a rights issue reported by news before the
   formal notice, a management change, a lawsuit outcome) → **the existing
   `events` table via `event_pipeline.py`**, using the 14 new taxonomy
   leaves added this session. This is the RIGHT tool: it already has
   `announced_date`/`effective_date`/`publication_ts` (the exact PIT
   triad this stage's brief asked for), `direction`, `confidence`,
   `source_id`, dedup, and conflict-preservation, all built and proven on
   CBN/MPC data.
2. **Qualitative, narrative claims requiring reasoning** (an article's
   implied earnings-direction interpretation, a causal chain from a
   contract win to margin impact) → **the existing `documents` →
   `extract_document()` → `extracted_facts`/`investment_implications`
   pipeline**, using the new `[news]` document-type leaf. This is
   arguably a BETTER fit for news than it was for financial statements —
   news is narrative and interpretive by nature, exactly what this
   pipeline's causal-chain/impact-assessment/investment-implication
   schema was built for, whereas financial statements are precise tables
   this platform ended up hand-extracting instead (Stages 3-9) specifically
   because precision mattered more than reasoning there.

**One real gap, not previously flagged**: neither pipeline has a
**syndication/republication deduplication mechanism**. `event_pipeline.py`
dedupes on `(event_type, announced_date, scope, index_code)` — this
catches the SAME source re-reporting, not FOUR outlets reporting the same
underlying event with four different headlines and four different
`article_id`s. This is a real, new requirement (Section 6).

---

## 2. Proposed Schema Addition: `news_outlets`

Per the architecture doc's own explicit, pre-existing design (not invented
this stage) — **required before any news evidence can be trusted above
tier 4 ("ai_derived_or_ungrounded")**:

```sql
CREATE TABLE news_outlets (
    outlet_id INTEGER PRIMARY KEY,
    outlet_name TEXT NOT NULL UNIQUE,
    reliability_tier INTEGER NOT NULL,   -- maps to vocab.EVIDENCE_TRUST_TIERS
    base_confidence REAL NOT NULL,
    covers_ngx_directly INTEGER NOT NULL DEFAULT 0,  -- 1 = files original
                                                       -- NGX reporting; 0 =
                                                       -- wire/syndicated only
    notes TEXT
);
```

**Not created this session** (schema-only proposal) — per the
architecture doc's own rule, populating `reliability_tier`/
`base_confidence` per outlet is an **owner judgment call**, not something
I should infer. Section 3's evidence below is offered as INPUT to that
judgment, not a substitute for it.

---

## 3. Five-Source Feasibility Matrix

Checked directly this session — robots.txt fetched/verified where
fetchable, RSS feeds tested live, H-011-name search coverage tested live.

| Source | NGX coverage | Historical depth | Timestamp quality | Structured access | Permitted automated access | Cost | H-011 coverage (Section 5) | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Reuters** | Macro/index-level Nigeria coverage exists (FX, frontier-market-status stories); **no evidence of NGX micro-cap-level reporting found in any search this session** | Unknown — could not fetch robots.txt directly (blocked); WebSearch confirms Reuters **defaults to blocking AI crawlers as of May 2026**, allowlisting only Amazon/Google/Bing/OpenAI | N/A — not accessible | No public API; enterprise-only via Refinitiv/LSEG (paid, not evaluated) | **Not permitted for automated collection under current robots.txt** | Enterprise/paid (Refinitiv) | **Effectively 0/20** (no H-011 name found in any Reuters-specific search) | **NOT VIABLE for this universe** |
| **Bloomberg** | Has **quote/profile pages** for larger H-011-adjacent names (LASACO, WAPIC, CUTIX found) — but these are data-terminal-style aggregator pages, not confirmed original Bloomberg journalism on these specific tickers | Unknown | N/A | `robots.txt` explicitly **disallows AI/LLM bots (Claude-Web, GPTBot, anthropic-ai) from the entire site except `/professional`, `/company`, `/latam`, `/faq`, `/tc`** — verified directly this session | **Explicitly NOT permitted for AI-driven automated collection** — confirmed in the fetched robots.txt itself | Enterprise/Terminal (paid) | **Quote-page presence only for ~3/20 checked; zero confirmed original articles on any H-011 name** | **NOT VIABLE — both policy-blocked and coverage-thin for this universe** |
| **Financial Times** | Unknown — could not fetch robots.txt (blocked); FT is a paywalled subscription product by design | Unknown | N/A | No public API found; licensed data products exist (not evaluated, enterprise) | **Assume NOT permitted** absent evidence otherwise — could not verify robots.txt directly, and FT's paywall alone is a real access barrier regardless of crawl policy | Subscription/enterprise | Not tested — extremely unlikely to cover NGX micro-caps given the pattern of the other two Western outlets | **NOT VIABLE, on the same reasoning as Reuters/Bloomberg** |
| **BusinessDay Nigeria** | Nigerian business daily, real NGX coverage exists | Unknown depth (not tested) | RSS feed exists (`businessday.ng/feed`) but **returned HTTP 403 when fetched directly this session** — a real, live technical barrier despite a permissive `robots.txt` (verified: `Disallow:` blocks only `/wp-login.php`, `/wp-register.php`, search endpoints — the feed itself is not disallowed by policy, yet is blocked in practice, likely bot-detection/Cloudflare) | Sitemap exists (`sitemap_index.xml`); RSS exists in principle | **Policy-permitted (robots.txt) but technically blocked in practice** — this distinction matters and should not be conflated | Free (subject to resolving the 403) | Not tested this session (blocked before coverage could be checked) | **CONDITIONAL — policy allows it, access needs a different technical approach (e.g., sitemap-based retrieval instead of the `/feed` endpoint) before it can be evaluated further** |
| **Nairametrics** | **Real, substantive, ticker-tagged NGX coverage — confirmed directly, extensively, this session** | RSS feed live-tested: recent articles carry precise `pubDate` down to the second; a dedicated `stocks.nairametrics.com/tag/<company>/` archive exists per company (tested on Tantalizer: 4 dated articles, real financial content — "reports a loss of N57.6 million in HY 2021," etc.) | **High** — `pubDate` (RFC-822, second-precision), `guid`, WordPress `post-id` (stable article identifier), `category` taxonomy, `dc:creator` | RSS feed (`nairametrics.com/feed`) works cleanly; per-company tag pages (`stocks.nairametrics.com/tag/...`) provide a structured, ticker-identified archive — the closest thing to a company-indexed API this audit found anywhere | **`robots.txt` = fully open, no disallow rules, explicit sitemap reference** — verified directly, permits automated access | Free | **By far the strongest of the five — see Section 5** | **VIABLE — the only source that clears both the access-policy bar and the H-011-coverage bar** |

**Nothing was bypassed.** Reuters and Bloomberg's AI-crawler blocks were
read and respected, not worked around. FT's likely paywall was treated as
a hard stop without attempting to test it. BusinessDay's 403 was recorded
as a barrier, not retried with evasive techniques.

---

## 4. Event Taxonomy (frozen leaves added this session)

14 new leaves added to `configs/event_taxonomy.toml`'s existing
`[corporate]` category (ticker-scoped, matching this category's existing
default): `management_change`, `litigation`, `regulatory_action`,
`regulatory_approval`, `capital_raise`, `debt_issuance`,
`debt_default_or_restructuring`, `credit_rating_change`,
`major_contract`, `strategic_partnership`, `asset_disposal`,
`corporate_restructuring`, `production_disruption`, `ownership_change`.

**Deliberately excluded from this pass, per your explicit instruction**:
a generic macro/sentiment category. Macro events remain gated to
`[monetary]`/`[commodity]`/`[macro]`'s existing market/sector-scoped
categories, used **only** when a specific H-011 ticker's exposure is
demonstrable — no new leaves added there this session since no evidence
yet exists that news coverage of macro events explicitly ties back to any
H-011 name (untested, not assumed).

**Not added, and why**: a standalone "earnings_surprise" or
"guidance_change" leaf — these require a NUMERIC baseline (consensus
estimate or prior guidance) to be meaningful, which does not exist on
this platform (no analyst-estimate dataset). Recording a bare
"earnings_release" (already existed) without a surprise magnitude is
honest; inventing a surprise classification without a baseline would not
be.

---

## 5. H-011 Coverage Pilot — The Critical Section

Tested Nairametrics coverage against a majority of H-011's actual 20
holdings via direct, dated search this session (not exhaustive — a
bounded pilot, consistent with "collect a bounded sample" before any
large-scale ingestion):

| ticker | evidence found this session | article-level or aggregator-level? |
|---|---|---|
| RTBRISCOE | "R.T. Briscoe shareholders approve N10 billion capital raise..." (2026-07-06), 184% H1 2026 price move context | **Article** |
| TANTALIZER | 4 dated articles on `stocks.nairametrics.com/tag/tantalizer-plc/` spanning 2021 (HY loss, Q1 loss, FY loss, AGM notice), plus 2026 trading-volume mention | **Article** |
| MCNICHOLS | "gained 29.46% in May 2026," "10.00% decline" trading mentions | **Article/market-roundup** |
| CAVERTON | "posted an N8.66 billion H1 loss as admin costs surged" | **Article** |
| REGALINS (Regency Alliance) | "Regency Alliance offers 7.37 billion shares in recapitalisation drive" (2026-07-14), dedicated tag archive exists (`stocks.nairametrics.com/tag/...`) | **Article** |
| DEAPCAP | "among losers" market-roundup mention | **Roundup only, thin** |
| VERITASKAP | "9.49% price depreciation" market-roundup mention | **Roundup only, thin** |
| SUNUASSUR | Two dedicated articles on a N9.33bn/N2.08bn rights issue (2026-02-11, 2026-04-13), free-float breach notice | **Article, strong** |
| PRESTIGE | Free-float breach notice with exact figures (15.49% free float, ₦3.43bn value, compliance deadline) | **Article** |
| ROYALEX | "Royal Exchange naming Ikeme Osakwe as Chairman" | **Article** |
| LASACO | Mentioned in insurance-sector roundups ("LASACO Assurance... posting near double-digit gains") | **Roundup, recurring** |
| NCR | "share price soar 993%... N5.00 to N54.65" (2025) | **Article/data point** |
| OMATEK | "up 60.27%," non-dividend-payer sector roundup | **Roundup** |
| UNIVINSURE | Non-dividend-payer sector roundup mention | **Roundup, thin** |
| CUTIX, WAPIC | Bloomberg quote-page presence found; Nairametrics not separately re-tested this pass (time-bounded pilot) | Not tested this pass |
| CILEASING, LEGENDINT, NSLTECH, REDSTAREX | Not tested this pass (time-bounded pilot; NSLTECH's ticker/company-name mismatch — "Secure Electronic Technology" — was tested and found, see Section 3's search) | Untested / partial |

**Approximate pilot result: at least 13-15 of 20 H-011 names show SOME
Nairametrics coverage this session, with roughly 8-9 showing genuine
article-level (not just roundup-mention) coverage.** This is a bounded,
non-exhaustive pilot — stated precisely as such, not rounded up to a
clean number. **It is categorically different from the fundamental-data
and insider-dealing pilots**, where the equivalent check found 2-3 of 20
and 3 of 20 respectively. News is not failing the same way fundamentals
and insider dealing failed.

**Large-cap/liquidity bias check**: the covered names include some of
H-011's most illiquid, smallest members by construction (TANTALIZER,
CAVERTON, DEAPCAP, VERITASKAP are among the very smallest names in the
IRU per Stage 6-9's own market-cap ranking). **This is a materially
different bias pattern than fundamentals showed** — Nairametrics appears
to cover NGX-listed companies roughly comprehensively (its own stated
editorial mission is Nigerian-market-wide retail/investor coverage), not
selectively toward large caps. This is a real, positive, and notable
finding — not yet proven at full scale, but not contradicted by anything
found this session either.

**What remains genuinely unverified, stated plainly**: (a) HISTORICAL
depth per ticker beyond what a live search surfaces — the pilot found
recent (2025-2026) coverage strongly, and one 2021 example (TANTALIZER);
whether 3+ years of continuous coverage exists per ticker is not yet
established; (b) EVENT FREQUENCY per ticker — some names show only
market-roundup mentions (DEAPCAP, VERITASKAP, UNIVINSURE), which carry
much less information content than a dedicated article; (c) the
remaining 5-6 untested names.

---

## 6. Data-Quality / PIT / Deduplication Assessment

- **Timestamp quality**: Nairametrics' RSS `pubDate` is second-precision
  and directly usable as `knowledge_date` with no PIT ambiguity — a
  materially better starting point than several of the fundamental-
  document sources audited in Stages 3-9 (which frequently required the
  "comparative column, conservative dating" caveat).
- **Duplicate/syndication risk**: real and NOT YET SOLVED. Nairametrics
  articles often summarize NGX's own corporate-action notices (e.g., the
  SUNU rights-issue articles almost certainly derive from the same NGX
  filing this platform's `xissuer_docs` archive already has). **A future
  ingestion MUST cross-reference new news-sourced events against
  EXISTING `documents`/`extracted_facts`/`events` rows for the same
  ticker and approximate date before counting them as independent
  information** — this is a real, new requirement, not automatically
  handled by `event_pipeline.py`'s existing same-source dedup.
- **Retrospective-information risk**: not tested this session (no
  historical article was checked for silent backdating); flagged as a
  Stage 10C/F requirement, not resolved here.
- **Source bias**: per Section 5, coverage does not appear concentrated
  in large/liquid names — a genuinely different, more favorable finding
  than fundamentals/insider dealing produced.
- **PIT feasibility**: HIGH for Nairametrics specifically, given
  precise, structured `pubDate`. **UNKNOWN/LOW for Bloomberg/Reuters/FT**
  (inaccessible) and **UNTESTED for BusinessDay** (blocked before
  timestamp quality could be checked).

---

## 7. Stage 1 Gate Scoring

| # | Gate | Score | Evidence |
|---|---|---|---|
| 1 | Source availability | **PARTIAL** | 1 of 5 sources (Nairametrics) clearly viable; BusinessDay conditional pending a technical fix; Reuters/Bloomberg/FT effectively closed for this universe |
| 2 | Historical depth | **UNKNOWN** | One 2021 data point found; systematic multi-year depth not yet tested |
| 3 | H-011 coverage | **PARTIAL, LEANING PASS** | 13-15 of 20 names show some coverage in a bounded pilot — the strongest result of any information source tested across this entire program (fundamentals: 2/20 code-eligible, insider dealing: 3/20 nominal) |
| 4 | PIT integrity | **PARTIAL** | Excellent structured timestamps confirmed for Nairametrics; retrospective-backdating risk untested |
| 5 | Event extraction reliability | **UNKNOWN** | No article has been run through `extract_document()` yet this stage — deliberately, per "do not extract thousands of articles yet" |
| 6 | Deduplication feasibility | **PARTIAL** | Mechanism identified as a real, solvable requirement (cross-reference against existing filings) but not yet built |
| 7 | Small-cap representation | **PASS, provisionally** | The one gate every prior information source failed on — Nairametrics shows real coverage of H-011's smallest, most illiquid names specifically |
| 8 | Independent information content | **UNKNOWN** | Not tested — whether Nairametrics articles add information BEYOND what `xissuer_docs` already captures (vs. just re-reporting the same NGX filing) is exactly Section 6's unsolved dedup question |

---

## 8. Decision: **CONDITIONAL**

Not GO — five of eight gate items are PARTIAL or UNKNOWN, and this
stage's own brief correctly prohibits treating "we found some coverage"
as sufficient. Not NO-GO — this is the first information-source track in
this entire program (fundamentals, insider dealing, now news) where the
single most important gate — meaningful H-011 overlap on the platform's
own smallest, least-liquid names — shows a real, positive, non-trivial
signal rather than the near-total absence found twice before.

**What must be resolved before Stage 10B/10C proceeds, precisely, per
your own "do not use CONDITIONAL merely to keep the project alive"
standard:**

1. **A real, non-bounded H-011 coverage pilot** — all 20 names,
   systematically, via the Nairametrics RSS/tag-archive structure (not
   ad hoc web search), measuring articles/ticker, date range per ticker,
   and distinguishing article-level from roundup-mention-level coverage
   precisely (Section 5's approximate 13-15/20 must become an exact
   count).
2. **A resolved BusinessDay access path** (sitemap-based retrieval
   instead of the blocked `/feed` endpoint) or a formal decision to drop
   it, before it can honestly be scored either way.
3. **A dedup design decision**, concretely: cross-reference news events
   against existing `documents`/`events` rows for the same
   (ticker, approximate date) before any news-sourced event counts as
   independent information — Section 6's identified gap, not yet solved.
4. **Owner input on `news_outlets.reliability_tier`** for Nairametrics
   specifically (the one source that matters) before any extracted fact
   from it can exceed evidence trust tier 4.

**If item 1 confirms something close to the 13-15/20 pilot finding at a
real, systematic count, with genuine article-level (not just roundup)
coverage on most of those names**: proceed to Stage 10C's bounded
extraction exactly as designed, reusing `event_pipeline.py` for discrete
events and `extract_document()` for narrative claims, with the dedup
check from item 3 built first.

**If item 1 finds the true count is much lower** (e.g., most of the
13-15 collapse to roundup-only mentions with no real article-level
content): this becomes a NO-GO on the same shape of finding as
fundamentals and insider dealing, and should be recorded as such rather
than stretched.
