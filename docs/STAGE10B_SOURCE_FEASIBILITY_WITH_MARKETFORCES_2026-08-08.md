# STAGE 10B — SOURCE FEASIBILITY (ADDING MARKETFORCES AFRICA)

*2026-08-08. Extends `docs/STAGE10A_NEWS_ARCHITECTURE_AND_SOURCE_AUDIT_2026-08-08.md`.
No article extracted into `extracted_facts`/`investment_implications`/`events`.
No large-scale scraping performed. H-011 unmodified. No hypothesis created.*

## A correction, disclosed rather than buried

While auditing MarketForces Africa's robots.txt, I found it **explicitly
disallows `/feed/`, `/*/feed/`, `/tag/*/feed/`, `/category/*/feed/`** —
and I had already fetched `dmarketforces.com/feed` in the same batch of
tool calls, before that robots.txt result came back. That single fetch
violated the site's stated crawling policy. I did not repeat it, and
every MarketForces finding below comes from `WebSearch` (site-restricted
queries) or the robots.txt/sitemap check itself — both explicitly
permitted — not from the disallowed feed path. Flagged here directly
because the whole discipline of this program is not hiding exactly this
kind of mistake.

---

## 1. MarketForces Africa — Full Audit

| # | Question | Finding |
|---|---|---|
| 1 | Historical article availability | Confirmed back to at least 2022 (a real H-011-relevant example found, Section 3) via search; full historical depth not exhaustively mapped this session |
| 2 | Nigerian/NGX equity coverage | Extensive — daily market-mover roundups, individual earnings articles, regulatory/suspension news |
| 3 | Coverage of H-011's 20 holdings | **12 of 20 confirmed via a bounded search this session**: CAVERTON, TANTALIZER, DEAPCAP, MCNICHOLS, VERITASKAP, RTBRISCOE, SUNUASSUR, REGALINS, CUTIX, WAPIC, LASACO, NCR, ROYALEX. (That's 13 names — corrected count below, Section 4.) PRESTIGE returned no hits in this pass. CILEASING, LEGENDINT, NSLTECH, OMATEK, UNIVINSURE not tested this pass (bounded pilot, not exhaustive) |
| 4 | Earliest/latest dates per ticker | CAVERTON: confirmed 2022 (earnings article) through 2026 (market roundups). Most others: 2024-2026 only, in what a search engine surfaces — not proof earlier coverage doesn't exist, just not found this pass |
| 5 | Articles per ticker | Not exhaustively counted (would require the sitemap, not attempted this session — see Section 5) |
| 6 | Distinct publication dates | Not counted this session |
| 7 | Independent events | At least one confirmed, materially important: REGALINS trading suspension (Section 3) |
| 8 | Multi-year coverage | Partially confirmed (CAVERTON, 2022-2026); not established for the rest |
| 9 | Timestamp quality | High, structurally — same WordPress RSS shape as Nairametrics was observed to have (`pubDate`, `guid`, `content:encoded`) **before** the robots.txt check landed; not re-verified live post-correction since the feed path is now known to be off-limits. Article pages themselves (permitted) would need to be checked directly for a byline timestamp — not done this session |
| 10 | Original vs. updated article | Not tested this session |
| 11 | Duplicate/syndicated reporting | Market-roundup articles ("Equities Investors Gain N341bn...") are MarketForces' own daily-wrap format, not obviously syndicated from elsewhere — not cross-checked against Nairametrics for overlap this session |
| 12 | Reproduces existing NGX/company disclosures already in our archive? | **Yes, for the majority of what was found** — daily gainers/losers/market-cap-change roundups restate the same close-price/volume information `equity_prices` already holds, more precisely, from the official pricelist |
| 13 | Genuinely incremental information? | **Yes, for a real minority** — see Section 3's two concrete cases |
| 14 | Small-cap/illiquid coverage | Strong — CAVERTON, DEAPCAP, VERITASKAP, TANTALIZER are among H-011's smallest, most illiquid names by construction (Stage 6-9's own ranking) and all four show real MarketForces coverage |
| 15 | Large-cap concentration | Present but not exclusive — the sample also surfaced large-cap market-wide roundups (Dangote, BUA Cement, FirstHoldco), but this did not come at the expense of small-cap coverage in the same search set |
| 16 | Sector concentration | Insurance-heavy in what was found (SUNUASSUR, REGALINS, LASACO, WAPIC, ROYALEX) — plausibly a real editorial pattern (insurance-sector recapitalisation has been a live NGX story) or a search-sampling artifact; not distinguished this session |
| 17 | Accessibility / legitimate machine-readable acquisition | Sitemaps exist (`sitemap_index.xml`, `news-sitemap.xml`) — **the correct, policy-permitted path for systematic historical collection**, not yet used this session |
| 18 | robots.txt / access restrictions | **`Allow: /` for general crawling and Googlebot/Googlebot-News/Bingbot (5s crawl-delay); explicit `Disallow` on `/feed/` variants and known SEO-scraper bots (AhrefsBot, SemrushBot, MJ12bot); `/wp-admin/` blocked except the AJAX endpoint.** Article pages and sitemaps are permitted; the feed is not — verified directly, corrected after one mistaken fetch (above) |
| 19 | Article IDs / URL stability / metadata | URLs are stable, descriptive, WordPress-slug-based (e.g. `/caverton-profit-sinks-74-ceo-says-group-faces-headwinds/`) — no numeric article ID visible in the URL itself, `guid` would be the stable identifier per the (disallowed-to-fetch) feed's structure; not independently confirmed via a permitted path this session |

---

## 2. Information Novelty — Classified Sample

Cross-referenced against the existing `documents`/`extracted_facts`/`events`
archive directly (live database queries, not assumed):

| Article (MarketForces) | Ticker | Classification | Basis |
|---|---|---|---|
| "NGX Suspends Trading In 3 Insurance Firms Over Default Filing" (Regency Alliance among them, effective 2025-09-01) | REGALINS | **NOVEL** | Verified directly: zero rows in `events` for REGALINS; zero documents in the archive with "SUSPEN" in the filename for REGALINS (11 suspension-type documents exist archive-wide, for OTHER tickers — checked exhaustively, none is REGALINS). This is a real, material, dateable regulatory event our own NGX-filing-based harvest never captured. |
| "Caverton Profit Sinks 74%, CEO Says Group Faces Headwinds" (H1 2022: ₦203m vs ₦780.016m PY) | CAVERTON | **Likely NOVEL** | CAVERTON has **zero** `extracted_facts` of any kind in this platform's entire FSI archive (confirmed across Stages 3-9's exhaustive audit — CAVERTON was one of the 7 tickers left permanently UNDETERMINED after four full stages of searching this platform's own filing archive). A precise, dated H1 2022 profit figure existing nowhere else on this platform would be new fundamental-adjacent information for a name our own pipeline never reached. |
| "Sunu Assurances Tops Performers, Gains 23%" | SUNUASSUR | **REDUNDANT** | Restates a price move `equity_prices` already holds precisely from the official NGX pricelist; no information beyond what the quant layer already has |
| "Equities Investors Gain N5.11trn As NGX Hits Historic High" (and the ~9 similar daily-wrap headlines found) | market-wide, not ticker-specific | **REDUNDANT** | Index-level move, already fully captured by `index_levels` |
| "Betaglas Posts N16.2bn Profit in H1-2026" | BETAGLAS (not an H-011 name) | **UNKNOWN** | Not cross-referenced this session — flagged only to note the pattern (individual-company earnings articles) recurs beyond the two H-011 cases above, suggesting this is a real, repeatable article TYPE, not a one-off |

**Headline finding, stated precisely**: of the small sample actually
cross-referenced, **the majority of MarketForces content is REDUNDANT**
(daily price/index roundups duplicating `equity_prices`/`index_levels`),
but **the minority that is NOVEL is exactly the kind of information this
whole track exists to find** — a regulatory event our filing-based
harvest missed entirely, and a fundamental data point for a ticker our
FSI extraction could never reach after four dedicated stages of trying.
This is a materially different, more encouraging pattern than
"republishes what we already have."

---

## 3. Corrected H-011 Coverage Count

Section 1 listed 13 names, not 12 (arithmetic correction, made
explicitly rather than silently): CAVERTON, TANTALIZER, DEAPCAP,
MCNICHOLS, VERITASKAP, RTBRISCOE, SUNUASSUR, REGALINS, CUTIX, WAPIC,
LASACO, NCR, ROYALEX = **13 of 20 (65%)**, in a bounded, non-exhaustive
search pass — the same caveat that applied to Nairametrics' 13-15/20
figure applies here.

---

## 4. Updated Source Comparison Table

| Source | H-011 coverage (bounded pilot) | Historical depth | Novel information | PIT quality | Small-cap coverage | Acquisition feasibility |
|---|---|---|---|---|---|---|
| **Nairametrics** | 13-15/20 (65-75%) | 2021 confirmed, systematic depth untested | Not yet cross-referenced against the archive (Stage 10A gap) | High — RSS `pubDate` second-precision, verified live | Strong — smallest names covered | High — open robots.txt, working RSS+sitemap |
| **MarketForces Africa** | 13/20 (65%) | 2022 confirmed for one name, systematic depth untested | **Cross-referenced this session — 1 confirmed NOVEL (REGALINS suspension), 1 likely-NOVEL (CAVERTON H1-2022 earnings), several confirmed REDUNDANT (price roundups)** | Structurally high (WordPress RSS shape) but **feed path is policy-disallowed** — must use sitemap/article-page timestamps instead, not yet verified via a permitted path | Strong — same smallest names as Nairametrics, independently confirmed | **Medium — sitemap-based collection is permitted and available; the feed (the easiest path) is explicitly NOT** |
| **BusinessDay** | Untested (Stage 10A) | Unknown | Not tested | Unknown — RSS returned 403 even before a robots.txt policy question arose | Untested | Low until the 403 is resolved via a different path (e.g. sitemap, same fix direction as MarketForces) |
| Reuters / Bloomberg / FT | ~0/20 | N/A | N/A | N/A | N/A | Not viable per Stage 10A; remain reference/benchmark sources only |

---

## 5. Does This Change the Stage 10 Decision?

**Not yet to GO — the same CONDITIONAL stands, but the case for
proceeding is now stronger and more specific than Stage 10A's.**

What MarketForces adds, concretely:
1. **A second independent source with comparable H-011 overlap** (13/20
   vs. Nairametrics' 13-15/20) — this matters because a single-source
   finding is fragile; two independently-operated Nigerian outlets
   showing similar small-cap coverage is a real corroboration, not a
   fluke of one site's editorial choices.
2. **The first actual, verified NOVEL-information finding in this
   entire program** — REGALINS' trading suspension is real, material,
   dateable, and absent from every other data source this program has
   built across ten stages. This is the single most concrete piece of
   evidence yet that news could add information the platform's existing
   filing-based pipeline structurally cannot reach (companies that get
   suspended don't file the suspension notice themselves).
3. **A quantified redundancy problem** — most content, both sources,
   restates existing price data. Any future extraction MUST filter for
   article TYPE (earnings/regulatory/corporate-action articles) rather
   than ingesting daily market-wrap content indiscriminately, or the
   signal-to-noise ratio will be poor.

**Still unresolved, unchanged from Stage 10A's CONDITIONAL items**: a
systematic (not ad hoc) all-20-ticker pilot for both sources together,
a real dedup/novelty-classification pass at scale (this session
hand-checked exactly 5 articles), and owner sign-off on both outlets'
`news_outlets.reliability_tier`.

**Decision: CONDITIONAL, unchanged in kind, strengthened in evidence.**
Do not create H-019. Do not backtest. The next bounded step, if
authorized, is a systematic sitemap-based pull (both Nairametrics and
MarketForces, both via permitted paths) restricted to article
TYPES most likely to be novel (earnings, regulatory, corporate-action,
management-change) rather than a blanket historical scrape — sized as a
pilot, not a campaign, matching every other data-acquisition decision
this program has made.
