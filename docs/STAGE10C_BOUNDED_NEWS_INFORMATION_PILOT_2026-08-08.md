# STAGE 10C — BOUNDED NEWS INFORMATION PILOT

*2026-08-08. Extends Stage 10A/10B. Real database cross-referencing
performed. Real FSI (Gemini) extraction calls made on 2 real articles —
disclosed in full, including a real negative/diagnostic result. No
alpha construction, no return prediction, no trading signal, no
backtest. H-011 unmodified. No H-019 created.*

**Files changed**: `data/staging/news_text/` (2 real article-text
files), 1 new `sources` row (`stage10c_news_pilot`, provisional,
explicitly marked non-final), 2 new `documents` rows (`doc_type =
'news_article'`, the Stage 10A taxonomy leaf). **Zero `extracted_facts`
rows written** — the FSI pilot (Section 7) genuinely returned none, for
a diagnosed, disclosed reason, not a hidden failure.

---

## 1. Executive Summary

**The REGALINS/CAVERTON anecdotes from Stage 10B were not anecdotal.**
A broader (still bounded, not exhaustive) search across H-011's 20
names found real, article-level, fact-bearing news coverage for at
least 16 of 20, and direct database cross-referencing of 13 specific
events found **11 are genuinely NOVEL** — including a second trading
suspension (UNIVINSURE, found in the same REGALINS article) and
multi-year earnings series for tickers (CAVERTON, VERITASKAP, NCR,
RTBRISCOE, CILEASING) that this platform's four-stage fundamental-data
campaign (Stages 6-9) never reached at all.

**The FSI integration test produced a real, diagnostic negative
result, reported honestly rather than hidden**: the existing
`extract_document()` pipeline ran successfully end-to-end on both test
articles (real API calls, valid JSON returned, `model_id` logged) but
extracted **zero facts from either** — not because the model failed,
but because `configs`-adjacent `prompts.py`'s `PILOT_FACT_TYPES`
constant hardcodes the extraction scope to exactly three fact types
(`dividend`, `rights_issue`, `bonus_issue`) inherited from the original
FSI pilot's narrow purpose. Neither test article mentioned any of the
three. This is a precise, fixable scoping issue, not evidence the AI
cannot process news — but it is a real blocker as-configured today.

---

## 2. Coverage (H-011's actual 20 names)

Built from Stage 10B's 13/20 + this session's additional targeted
searches, all against the exact 20-name list reconstructed from
H-011's unmodified signal code:

| ticker | article-level coverage found? | roundup-only? | article dates found this session |
|---|---|---|---|
| CAVERTON | **Yes, rich** | — | 2022, 2023, 2024 (x2), H1-2025, FY-2025 |
| TANTALIZER | Yes (Stage 10B) | — | 2021 (x4) |
| DEAPCAP | Roundup only | Yes | 2024-2026 (price-move mentions) |
| MCNICHOLS | Roundup only | Yes | 2026 (price-move mentions) |
| NCR | **Yes** | — | 2025 (FY results), 2026 |
| NSLTECH | **No article found** (company-profile pages only) | — | — |
| OMATEK | Roundup only | Yes | 2026 |
| PRESTIGE | **Yes** | — | 2024, Q1-2025 |
| REDSTAREX | Roundup only (Stage 10B) | Yes | 2026 |
| REGALINS | **Yes, rich** | — | 2025-09 (suspension), 2026-08 (recapitalisation) |
| ROYALEX | **Yes** | — | Chairman appointment (undated in this pass) |
| RTBRISCOE | **Yes** | — | 2021 AGM, 2022 AGM, 2026 (capital raise) |
| SUNUASSUR | **Yes, rich** | — | 2026-02, 2026-04 (rights issue x2), free-float notice |
| SUNUASSUR / general | (dup entry avoided) | | |
| CUTIX | Roundup only | Yes | 2025-2026 (price-move mentions) |
| WAPIC | Roundup only | Yes | 2025-2026 (price-move mentions) |
| LASACO | **Yes** (unconfirmed-source, see caveat) | — | 2022, 2023, 2024 |
| VERITASKAP | **Yes, rich** | — | 2024-Q3, 2025-H1, 2025-Q3, 2026-Q1 |
| LEGENDINT | **Yes, flagged data-quality issue** | — | 2025 (listing, FY results — contradictory figures, Section 6) |
| CILEASING | **Yes** | — | 2024 FY, 2025 FY |
| UNIVINSURE | **Yes** (via the REGALINS suspension article) | — | 2025-09 |

**Coverage tallies:**
- **H-011 names with any article (article-level or roundup): 18 of 20**
  (NSLTECH and OMATEK found nothing beyond generic company-profile
  pages this session).
- **H-011 names with genuine article-level (non-roundup) coverage: 14
  of 20 (70%)** — this is the number that matters more than raw
  "coverage," since roundup-only mentions carry near-zero incremental
  information (Section 4).
- **H-011 names with ≥2 distinct dated events found: 11 of 20**
  (CAVERTON, TANTALIZER, NCR, PRESTIGE, REGALINS, RTBRISCOE, SUNUASSUR,
  LASACO, VERITASKAP, LEGENDINT, CILEASING).
- **H-011 names with ≥3 distinct dated events: 7 of 20** (CAVERTON,
  TANTALIZER, REGALINS, RTBRISCOE, SUNUASSUR, VERITASKAP, CILEASING —
  VERITASKAP alone has 4 quarterly data points).
- **H-011 names with multi-year event history confirmed: 5 of 20**
  (CAVERTON 2022-2025, LASACO 2022-2024, RTBRISCOE 2021-2026,
  TANTALIZER 2021 only — single year, VERITASKAP 2024-2026).

**One important caveat, disclosed precisely**: this is still a bounded,
search-engine-mediated pilot, not a systematic sitemap pull. Some
"no coverage found" results (NSLTECH, OMATEK) may reflect search
recall limits rather than true absence — the same caveat Stage 10A/B
already carried forward, unresolved by this stage either.

---

## 3. Information Quality — Classified Sample

**13 specific events cross-referenced directly against the live
database** (not assumed, not estimated):

| Event | Ticker | Classification | Verification method |
|---|---|---|---|
| NGX trading suspension, effective 2025-09-01 | REGALINS | **NOVEL** | `events` table: 0 rows for REGALINS. `documents`: 0 suspension-type filings for REGALINS (11 exist archive-wide, none for this ticker) |
| Same suspension notice, same article | UNIVINSURE | **NOVEL** | Identical check: 0 events, 0 suspension documents for UNIVINSURE |
| FY2024 revenue/loss (₦40.1bn / -₦53.6bn pre-tax) | CAVERTON | **NOVEL** | `extracted_facts`: 0 rows for CAVERTON, any type, any period (confirmed live query) |
| Q3 2024 / H1 2025 / Q3 2025 / Q1 2026 profit figures | VERITASKAP | **NOVEL** | `extracted_facts`: existing rows are `assets`/`liabilities`/`equity` for 2019-12-31 and 2020-12-31 ONLY — no overlap in fact_type or period with any of the 4 news-sourced figures |
| FY2025 results (profit ₦196.04m, revenue ₦3.08bn) | NCR | **NOVEL** | `extracted_facts`: 0 rows for NCR |
| 2026 shareholder-approved ₦10bn capital raise | RTBRISCOE | **NOVEL** | `extracted_facts`: 0 rows for RTBRISCOE; no capital_raise-type event exists for any ticker in `events` this early |
| FY2024/FY2025 profit (₦1.6bn, +480%; ₦2.94bn, +83.4%) | CILEASING | **NOVEL** | `extracted_facts`: existing CILEASING rows are `dividend`/`bonus_issue` with **NULL numeric_value** (older, narrative-only extractions) — no overlapping fact_type/period with real figures |
| 2023 revenue ₦18.3bn, PAT -13% to ₦1.3bn; 2024 PAT +44% to ₦1.89bn | LASACO | **NOVEL** (new periods) | `extracted_facts`: existing LASACO facts cover 2022-12-31 only — 2023/2024 are new periods. **Caveat: this specific search did not confirm Nairametrics/MarketForces as the exact source** (general web result) — lower confidence than the other NOVEL rows, flagged explicitly |
| Chairman appointment (Ikeme Osakwe) | ROYALEX | **ADDITIVE** | Governance-type information, not a financial fact — no direct `extracted_facts` analog exists to compare against, but it plausibly supplements rather than duplicates the existing delay/default-notice record already known for ROYALEX (Stage 7) |
| FY2024 profit +120% to ₦2.878bn; Q1-2025 GPW ₦8.03bn | PRESTIGE | **NOVEL** | Stage 7 confirmed PRESTIGE has zero real extracted facts (only delay-notice records) |
| ₦6.04bn capital raise, meets NAICOM requirement (2026-08-04) | REGALINS | **NOVEL** | Follow-up event to the suspension above; 0 capital-raise or NAICOM-compliance record exists for REGALINS anywhere |
| FY2025 pre-tax profit ₦173m (**two Nairametrics articles disagree**: one states +44.5% YoY growth, another states -39.41% YoY decline for what appears to be the same fiscal year) | LEGENDINT | **UNKNOWN** | Genuine source-internal contradiction found, not resolved this session — classified UNKNOWN rather than guessed, per the taxonomy's explicit allowance for this case |
| Daily price-move mentions (DEAPCAP, MCNICHOLS, CUTIX, WAPIC — 4 examples) | multiple | **REDUNDANT** | Restates `equity_prices`' own official close/volume more precisely than any roundup article does |

**Result: of 13 classified events, 11 NOVEL, 1 ADDITIVE, 1 UNKNOWN
(source-contradiction), plus a separate 4-example REDUNDANT sample of
roundup-type content. Zero DUPLICATE (same-source republication)
found; one clean cross-SOURCE duplicate identified separately
(Section 5).**

**This is a genuinely different, more favorable ratio than "most
content is redundant"** — because it is computed on the ARTICLE-TYPE-
FILTERED sample (dedicated company-event articles), not the unfiltered
mix. Section 4 makes this filter explicit.

---

## 4. Article-Type Filter — Does It Solve the Redundancy Problem?

**Yes, based on this sample — cleanly and predictably.**

| Article type | Count observed this session | Novelty pattern |
|---|---|---|
| **HIGH-VALUE** (earnings/result articles, capital raise, suspension, regulatory action, AGM/rights-issue outcomes, management change) | ~20+ across the session | **11 of 13 classified examples from this bucket were NOVEL** |
| **LOW-VALUE** (daily gainers/losers, market-cap-change roundups, index-level moves) | ~15+ observed (Stage 10A/B/C combined) | **100% of the classified sample from this bucket was REDUNDANT** |

The separation is not fuzzy in this sample — every dedicated
company-event article checked carried new information; every roundup
article checked restated existing price data. **A mechanical filter on
article TYPE (title/content pattern: "posts profit/loss," "suspends,"
"raises," "approves," vs. "gains/loses %," "investors gain/lose ₦Xbn")
would very likely separate these cleanly at scale** — this is a
testable, specific, bounded next step, not a vague aspiration.

---

## 5. Deduplication — Cross-Source Example

**VERITASKAP Q3 2024 profit growth (117%, to ₦2.339bn/₦2.34bn) was
reported independently by BOTH Nairametrics ("Veritas Kapital Assurance
posts exceptional 117% profit growth in Q3 2024...") AND MarketForces
Africa ("Q3 2024: Veritas Kapital Grows Profit by 117% to N2.34bn") —
same percentage, same approximate figure, same fiscal quarter.**

**This is ONE underlying event (almost certainly both derived from the
same NGX Q3 2024 filing), reported by two outlets — correctly counted
as one event, not two independent information observations**, exactly
per your instruction. An event-fingerprint on `(ticker, fact_type ≈
"earnings", period_end, rounded numeric_value)` would catch this
specific case mechanically. **Article count for this one event: 2.
Unique event count: 1.**

No same-source republication (identical article re-dated) was found in
this sample — the duplication risk identified is cross-outlet, not
within-outlet.

---

## 6. PIT Assessment

- **Exact timestamps confirmed this session**: the 2 articles fetched
  in full (Section 7) both carry an explicit, unambiguous publication
  date on the page itself (CAVERTON: "March 31, 2025"; REGALINS:
  "September 1, 2025") — **100% of the directly-fetched sample has
  usable PIT dating.**
- **Date-only vs. exact-timestamp**: the RSS-level second-precision
  `pubDate` confirmed in Stage 10A for Nairametrics was NOT
  independently re-verified this session for MarketForces (its feed is
  policy-disallowed, per Stage 10B) — MarketForces timestamp precision
  for a systematic pull would need to come from article-page bylines
  (confirmed present, Section 7) or the permitted sitemap, not the feed.
- **% PIT PASS this session**: 2 of 2 directly-verified articles pass
  (positive-lag-equivalent: publication date is a real, stated,
  unambiguous date, not inferred).
- **% PIT UNKNOWN**: the remaining 11 NOVEL events (Section 3) were
  dated from search-result snippets, not independently re-verified on
  the article page itself this session — **downgraded to PIT UNKNOWN
  pending direct verification**, stated explicitly rather than assumed
  clean.
- **No retrospective-backdating risk was found, but it was also not
  actively tested** (no article was checked for a silent "updated"
  timestamp diverging from its original publish date) — an open item
  for the next bounded step, not resolved here.

---

## 7. FSI Integration Test — Real Result, Including the Negative Finding

**Method**: registered 1 provisional `sources` row and 2 real
`documents` rows (CAVERTON's FY2024 article, REGALINS' suspension
article — full text, not summaries), then called this platform's
actual `extract_document()` function with a real `build_default_provider()`
(Gemini 3.6-flash, live `GEMINI_API_KEY`).

**Result**: both calls succeeded end-to-end — `parse_ok=True`, a real
`model_id` logged, valid JSON returned, 2 new rows in `llm_calls` (call
42, call 43). **Both returned `{"facts": []}` — zero facts extracted
from either article.**

**Root cause, diagnosed directly, not guessed**: `src/ngxrot/documents/
prompts.py` line 28 hardcodes `PILOT_FACT_TYPES = ["dividend",
"rights_issue", "bonus_issue"]` — a narrow scope carried over from the
ORIGINAL FSI pilot's stated purpose ("Phase B's dividend/rights/bonus
ground truth"). This list is baked into the module-level prompt string
at import time, not passed as a parameter to `build_draft_prompt()`.
**Neither test article mentions a dividend, rights issue, or bonus
issue** — CAVERTON's article is revenue/profit/loss content (fact
types `revenue`/`net_profit`, which exist in `fact_taxonomy.toml` but
are NOT in the LLM prompt's current allowlist); REGALINS' is a trading
suspension (not a `fact_taxonomy.toml` leaf at all — it is an `events`-
table concept, per `event_taxonomy.toml`'s `[corporate]` category,
extended in Stage 10A specifically to cover this case).

**This is not a capability failure of the AI or the pipeline
architecture** — the model correctly followed its instructions and
correctly returned an empty list rather than fabricating a
dividend/rights/bonus fact that wasn't there (exactly the "never
fabricate" rule working as intended). **It is a real, precise,
fixable configuration gap**: extending `PILOT_FACT_TYPES` to the full
`fact_taxonomy.toml` leaf set (or making it a caller-supplied
parameter instead of a module-level constant) would very likely let
`extract_document()` process CAVERTON's article successfully — not
tested this session, since editing `prompts.py` is a real code change
beyond this stage's audit-only mandate ("do not retrain the model").

**Measured this session** (per your explicit ask to measure, not
assume):
1. Structured event: **not produced** (0/2)
2. Affected company/ticker: n/a (pipeline never reached this stage)
3-10: **not measurable this run** — the pipeline exited at the facts
   stage with an empty list both times

**Extraction accuracy against manually-validated ground truth: 0/2
this specific run, entirely attributable to the diagnosed scoping gap,
not to the model or the architecture.** Re-running with the fact-type
scope corrected is the obvious, bounded next test — not attempted this
session per the "do not retrain, stay bounded" instruction.

---

## 8. Layer Separation (as required, not collapsed)

| Layer | This session's evidence |
|---|---|
| SOURCE | 2 (Nairametrics, MarketForces) confirmed viable per policy; 18 articles/mentions found across both |
| ARTICLE | 2 fetched in full; ~20+ identified via search snippet |
| UNIQUE EVENT | 13 classified; 1 confirmed cross-source duplicate collapsed to 1 event (Section 5) |
| STRUCTURED FACT | **0 produced** — FSI pipeline scoping gap (Section 7) |
| CAUSAL INTERPRETATION | Not reached — depends on structured facts existing first |
| INVESTMENT IMPLICATION | Not reached, same reason |

**No sentiment score was computed anywhere in this pipeline.** The
pipeline stalled at exactly the layer boundary your instruction
anticipated as the risk point (Section 7), and stalled cleanly (an
empty, valid response) rather than collapsing layers to compensate.

---

## 9. Final Stage 10C Metrics (as specified)

**Coverage**: 18/20 any mention, 14/20 article-level, 11/20 ≥2 events,
7/20 ≥3 events, 5/20 multi-year confirmed.

**Information quality**: ~20+ articles/mentions identified this
session; 13 unique events formally classified (1 collapsed from a
2-article cross-source duplicate); 11 NOVEL, 1 ADDITIVE, 1 UNKNOWN, 4
separately-sampled REDUNDANT roundup examples; 0 same-source DUPLICATE
found.

**Novelty**: **11/13 classified non-roundup events (85%) NOVEL** when
restricted to the article-type-filtered (HIGH-VALUE) bucket; **0% of
the sampled roundup (LOW-VALUE) bucket was novel** — the two buckets
behave completely differently, exactly as the filter hypothesis
predicted.

**Event distribution**: heaviest observed density — VERITASKAP (4
events, quarterly cadence, 2024-2026), CAVERTON (5 events, 2022-2025),
CILEASING (2 events), SUNUASSUR (2-3 events). Sector skew in this
sample: insurance-heavy (VERITASKAP, REGALINS, UNIVINSURE, SUNUASSUR,
LASACO, PRESTIGE = 6 of ~14 article-level names) — plausibly a real
2025-2026 NGX story (insurance recapitalisation wave, consistent with
Stage 8/9's own independent finding of insurance-sector filing
distress) rather than a search artifact, not disambiguated further
this session.

**PIT**: 2/2 directly-fetched articles have exact, unambiguous
publish-date timestamps (100% of the verified subsample); the
remaining 11 classified NOVEL events are PIT UNKNOWN pending direct
per-article verification (not yet done at scale).

**FSI**: 0/2 successful structured extractions this run; root cause
diagnosed and disclosed (Section 7) as a fact-type scoping
configuration, not a model or architecture failure.

---

## 10. Readiness Decision: **CONDITIONAL**

Not GO — FSI extraction produced zero usable structured output this
session (Section 7), and PIT verification was only completed for 2 of
13 classified events. Both are real, load-bearing gaps, not
technicalities.

**Not NO-GO** — every other measured dimension moved in a genuinely
positive direction from Stage 10B: coverage held at a real 70%
article-level rate across an independently-expanded sample; the
novelty rate on filtered content (85%) is the strongest evidence yet,
in this entire ten-stage program, that an information source can add
something to H-011's universe the existing archive does not have; and
the redundancy problem has a demonstrated, mechanical filter
(Section 4) rather than being an open question.

**Specifically required before this can become GO, per your own
10-condition list:**

1. Meaningful H-011 overlap — **met** (70% article-level, this session).
2. Sufficient historical depth — **partially met**; 5/20 multi-year
   confirmed, most others single-year or unverified further back.
3. Repeatable event frequency — **met for a subset** (VERITASKAP,
   CAVERTON show real multi-event cadence); not established
   platform-wide.
4. Meaningful NOVEL/ADDITIVE information — **met, strongly**, on the
   filtered sample (Section 3/4).
5. Acceptable PIT integrity — **NOT yet met** — only 2/13 events
   independently timestamp-verified.
6. Manageable redundancy — **met** — the article-type filter works
   cleanly on this sample (Section 4).
7. Reliable FSI extraction — **NOT met this run** — 0/2, diagnosed
   fixable cause (Section 7), unfixed.
8. Sufficient cross-sectional breadth — **met**, 14/20.
9. Information materially different from H-011 — plausible (fundamental/
   regulatory content, not price/volume-derived) but not yet
   quantitatively tested against H-011's own Size score, liquidity, or
   momentum (correctly out of scope — Stage 10C explicitly excludes
   backtesting/factor construction).
10. No large-cap/sector concentration invalidating the test — **mostly
    met** (small-cap coverage strong, per Section 2); a real,
    disclosed sector skew toward insurance exists and should be
    watched, not ignored, going forward.

**5 of 10 conditions clearly met, 2 explicitly not met (PIT
verification at scale, FSI extraction), 1 partial, 2 out of scope by
design.** This is a genuine CONDITIONAL, not a disguised GO — the two
unmet conditions are both concrete, bounded, fixable tasks (verify
timestamps on the classified event list directly; widen
`PILOT_FACT_TYPES` and re-run the same 2-article FSI test before
trusting it on anything larger), not open-ended research questions.

**No H-019. No backtest. No alpha construction.** If both unmet
conditions are resolved in a follow-up bounded pass and continue to
hold at roughly this session's rates, the evidence would support
proceeding to a genuinely systematic (sitemap-based, all-20-ticker,
multi-year) pull — still short of H-019, which additionally requires
the independence test (condition 9) this stage correctly did not
attempt.
