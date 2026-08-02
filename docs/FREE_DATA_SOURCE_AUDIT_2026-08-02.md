# Free Data Source Audit — Frontier-Market Alpha Discovery

*2026-08-02. Every source below was independently verified via live web
search/fetch on this date (not recalled from training data alone) — URLs,
free-tier status, and historical-depth claims are as found on 2026-08-02
and should be re-verified before any acquisition decision, since government
and exchange websites restructure without notice. Where verification was
partial or ambiguous, that is stated explicitly rather than smoothed over.
Datasets already inside the platform (3 validated price sources, NGX
corporate actions/disclosures, dividend closure calendar, NGX sector
classification, market cap panel, macro/event dates already used by
H-004/H-005) are excluded, and overlap with existing sources is flagged
wherever a candidate is a refinement of something already partially owned,
not a wholly new acquisition.*

## Headline finding (read this first)

**`src/ngxrot/metrics.py` currently uses `rf_annual_pct=0.0` as a disclosed
placeholder** ("Default 0.0 is WRONG for Nigeria... the metric name says
what was used" — its own docstring). Every Sharpe ratio this platform has
ever reported, including H-011's, is computed against a **zero** risk-free
rate, when real NGN T-bill rates have ranged roughly 4%–25%+ over the
sample period. **Three of the sources below (CBN, FMDQ, DMO) each provide a
free, official, dated Nigerian T-bill/bond yield series that would let this
placeholder be replaced with a real, point-in-time-correct risk-free rate
for the first time.** This is not a new hypothesis family — it is a fix to
a metric every single hypothesis test (H-001 through H-012, and everything
downstream) has already been silently using in its weakest form. Flagged
**Immediate** priority below, ahead of every genuinely new factor-discovery
source.

---

## A. Macroeconomic / Rates Data

### A1. Central Bank of Nigeria (CBN) — Statistical Data

1. **Official source**: cbn.gov.ng, discrete rate pages plus a "Statistics
   Database" at `statistics.cbn.gov.ng/shop` and periodic Statistical
   Bulletins (quarterly/annual).
2. **Truly free?**: The discrete rate pages, exchange rates, inflation,
   Money and Credit Statistics, and the published Statistical Bulletins
   are free. **Uncertain**: the "/shop" naming on the bulk statistics
   portal suggests some series there may sit behind a paid tier — this was
   not resolved in this pass and should be checked before assuming the
   entire bulk database is free.
3. **Historical depth**: Statistical Bulletins reference a "5-Year
   Financial Summary" and a separate "5-Year Financial Summary — Pre 1972"
   series, implying decades of historical macro/monetary data exist in
   principle; **exact machine-readable depth for MPR/T-bill series
   specifically was not confirmed** in this pass.
4. **Update frequency**: MPR — event-driven (each MPC meeting, ~6/year);
   T-bill/exchange rates — reported as available at higher frequency
   (daily/weekly) on discrete pages; Statistical Bulletins — quarterly/annual.
5. **Data quality**: **High** — primary central-bank source, the same
   institution whose MPC decisions this platform's own H-012 regime gate
   already keys off of (as event dates, not rate levels).
6. **Point-in-time suitability**: Good for rate *levels* as long as the
   announcement date (not a later "as of" date) is captured — MPR changes
   are discrete, dated events, low ambiguity. T-bill primary-market rates
   are auction-dated. Revision risk for Statistical-Bulletin-published
   series was not assessed.
7. **Acquisition method**: Mix of HTML tables (rate pages), Excel/CSV
   (Statistical Bulletin annexes), and PDF (bulletins). No REST API
   confirmed in this pass.
8. **Automation difficulty**: **5/10** — no API, but the data is
   structured (tables/Excel), not narrative PDF.
9. **Research value**: **Exceptional** for the risk-free-rate fix
   specifically (see Headline finding); **Medium** for money-supply/credit
   statistics as a macro-regime input (extends, rather than replaces, the
   existing event-based macro/regime infrastructure).
10. **Hypothesis families unlocked**: risk-free-rate correction (all
    existing and future Sharpe ratios); macro liquidity/credit-growth
    regime variables (a genuinely new regime-classification input,
    distinct from H-012's event-proximity rule).
11. **Consuming module**: `src/ngxrot/metrics.py` (`rf_annual_pct`
    input) directly; `regime_stable_dates()` in `backtest_xs.py` as an
    additional, continuous (not just event-date) regime signal if pursued
    later.
12. **Priority**: **Immediate** (risk-free rate correction) — this is an
    input-data fix to an already-disclosed, already-flagged platform gap,
    not new research.
13. **Market classification**: Frontier-market-specific in its concrete
    value here (Nigeria's T-bill/MPR series specifically), though the
    *technique* (using a country's own policy rate as the risk-free
    benchmark) is universal practice in any market's Sharpe-ratio
    computation.

### A2. FMDQ Group — NAFEX FX Fixing, T-Bill/Bond Market Data

1. **Official source**: fmdqgroup.com (exchange arm: fmdqgroup.com/exchange).
2. **Truly free?**: The daily NAFEX FX benchmark and market notices are
   published free; FMDQ also offers a paid "e-Markets" data-feed product
   for deeper historical/bulk access — **the free tier appears limited to
   current/recent published rates, not confirmed to include a bulk
   historical download**, so this should be treated as a daily-scrape
   target (accumulate going forward) rather than an instant historical
   backfill source until confirmed otherwise.
3. **Historical depth**: NAFEX itself dates to June 2017 (when NAFEM/NAFEX
   launched) — meaningfully shorter than this platform's ~2015-2026 sample
   window, so it cannot backfill the earliest years even if bulk history
   were free.
4. **Update frequency**: Daily (FX fixing published each business day).
5. **Data quality**: **High** — FMDQ is the official benchmark
   administrator for NAFEX, analogous in role to how LIBOR/SONIA
   administrators publish developed-market benchmark rates.
6. **Point-in-time suitability**: Good — a daily fixing published same-day
   has essentially no restatement risk.
7. **Acquisition method**: HTML (published rate pages/market notices); no
   confirmed free bulk API.
8. **Automation difficulty**: **6/10** — daily scraping of a published
   page is straightforward, but historical backfill before scraping began
   is the open question in item 2.
9. **Research value**: **High** for FX-regime and NGN-devaluation-event
   research specifically (this platform's own H-012 regime rule already
   treats "float_shock" as a named regime — FMDQ's FX series is the
   authoritative reference for exactly that variable, currently sourced
   from `events` table dates rather than a continuous rate series).
10. **Hypothesis families unlocked**: FX-regime-conditioned factor
    variants (a different regime *input* from H-012's event-proximity
    rule); carry/rate-differential research if paired with a foreign
    risk-free rate.
11. **Consuming module**: `events` table / `regime_stable_dates()` as an
    alternative or complementary continuous regime signal; `metrics.py`
    for T-bill-based risk-free rate cross-check against CBN's own series.
12. **Priority**: **Near-term** — valuable but CBN alone already covers
    the risk-free-rate fix; FMDQ's marginal value is a second, independent
    source for cross-validation and a continuous FX-regime variable.
13. **Market classification**: Frontier-market-specific (NAFEX exists
    specifically because of Nigeria's historically fragmented FX-market
    structure — developed markets have no equivalent multi-window FX
    fixing).

### A3. Debt Management Office (DMO) Nigeria — FGN Bond Auctions

1. **Official source**: dmo.gov.ng (`/fgn-bonds/bonds-auction-results`,
   `/debt-profile`).
2. **Truly free?**: Yes, confirmed — auction result circulars and debt
   profile pages are openly published.
3. **Historical depth**: Auction result pages exist per-month going back
   multiple years (confirmed pages for Feb 2025, Apr 2025, May 2026, Jul
   2026 in this pass); a full back-to-2015-or-earlier archive was not
   individually confirmed but the page structure (dated sub-pages per
   auction) suggests a long-run archive exists.
4. **Update frequency**: Per-auction (roughly monthly/bi-monthly FGN bond
   auctions).
5. **Data quality**: **High** — primary sovereign-debt-issuer source,
   includes allotment amounts, bid-to-cover, and stop rates (yields).
6. **Point-in-time suitability**: Good — each auction result is dated and
   published shortly after the auction; no material restatement risk.
7. **Acquisition method**: HTML/PDF circulars per auction.
8. **Automation difficulty**: **6/10** — no bulk API; requires scraping a
   paginated archive of per-auction pages.
9. **Research value**: **High** — a real Nigerian sovereign yield curve
   (multiple tenors from bond auction stop rates) is a genuinely new
   capability; combined with CBN's T-bill rates, this supports a proper
   term-structure risk-free benchmark rather than a single flat rate.
10. **Hypothesis families unlocked**: risk-free-rate/term-structure
    correction; duration/rate-sensitivity interaction factors (does the
    Size or Liquidity premium interact with the level or slope of NGN
    yields?) — a genuinely new interaction-factor family not yet
    considered in the platform's existing Interaction Factors program.
11. **Consuming module**: `metrics.py` risk-free input; a new, small
    reference table analogous to `data/reference/exdiv_closure_calendar.csv`
    for yield-curve data if pursued.
12. **Priority**: **Near-term** — pairs naturally with the CBN
    Immediate-priority fix; adds term-structure depth CBN's single MPR/
    T-bill series alone doesn't provide.
13. **Market classification**: Frontier-market-specific in the concrete
    series (NGN sovereign yields), universal in technique (using a
    sovereign yield curve as the risk-free term structure).

### A4. World Bank Open Data / World Development Indicators API

1. **Official source**: data.worldbank.org (country page: `/country/NG`);
   API documented at datahelpdesk.worldbank.org.
2. **Truly free?**: Yes, confirmed — explicitly free, no registration
   required for the API.
3. **Historical depth**: Confirmed — many WDI series extend 50+ years;
   for Nigeria specifically this generally means annual data from the
   1960s-1980s depending on the indicator.
4. **Update frequency**: Annual (most WDI indicators); some quarterly
   series exist for a subset of countries but Nigeria coverage for those
   was not individually confirmed.
5. **Data quality**: **High** for standardized cross-country comparability;
   **Medium** for timeliness (WDI data is often 1-2 years lagged relative
   to a country's own national statistics office).
6. **Point-in-time suitability**: **Weak** — World Bank indicators are
   frequently revised/rebased retroactively (a real, well-known limitation
   of using WDI for backtesting); using it for anything beyond broad
   multi-year context would need explicit vintage-tracking, which the
   API does not appear to provide by default.
7. **Acquisition method**: REST API (JSON/XML) or bulk CSV/Excel via
   DataBank.
8. **Automation difficulty**: **2/10** — genuine, well-documented public
   API, low effort.
9. **Research value**: **Low-Medium** — useful for broad country-level
   context (e.g., a cross-market expansion scoping exercise) but too
   low-frequency and revision-prone for tradeable signal construction at
   the individual-hypothesis level this platform currently operates at.
10. **Hypothesis families unlocked**: none directly tradeable; supports
    macro-regime context and any future cross-market (multi-African-country)
    expansion research design.
11. **Consuming module**: none currently — would be a new, small
    reference table if a cross-market expansion phase is ever authorized.
12. **Priority**: **Future** — genuinely low urgency given the platform's
    current single-market, single-hypothesis-at-a-time research mode.
13. **Market classification**: **Universal** — a generic, non-market-specific
    macro-data source used identically regardless of market classification.

### A5. National Bureau of Statistics (NBS) Nigeria — CPI/Inflation, GDP

1. **Official source**: nigerianstat.gov.ng; microdata portal
   microdata.nigerianstat.gov.ng.
2. **Truly free?**: Yes, confirmed — PDF summaries and Excel tables are
   openly published per release.
3. **Historical depth**: Confirmed — CPI historical series described as
   extending back to 2003, with a 2025 rebasing (weight reference 2023,
   price reference 2024) — a real, disclosed methodology break researchers
   must account for (pre- and post-rebasing series are not directly
   comparable without a splicing adjustment).
4. **Update frequency**: Monthly (CPI/inflation); quarterly (GDP).
5. **Data quality**: **High** — the official national statistics agency;
   the rebasing methodology break is a known, disclosed limitation, not a
   quality defect.
6. **Point-in-time suitability**: **Medium** — monthly CPI releases are
   dated and not usually revised, but the 2025 rebasing changed the
   *entire historical series' basis* — any point-in-time reconstruction
   must use the vintage of the series as it was published at each date,
   not today's rebased history, to avoid a real look-ahead problem
   (a rebased CPI figure reflects information not available to a market
   participant on the original publication date).
7. **Acquisition method**: PDF summary + downloadable Excel tables per
   release, plus a structured microdata catalog portal.
8. **Automation difficulty**: **4/10** — Excel tables are structured but
   require per-release scraping/parsing; the rebasing break requires
   explicit handling, not just download automation.
9. **Research value**: **Medium** — real macro-regime input (inflation
   regime, GDP-growth regime) distinct from anything currently in the
   platform's event-based regime infrastructure; lower urgency than the
   risk-free-rate fix.
10. **Hypothesis families unlocked**: inflation-regime-conditioned factor
    variants (a genuinely new regime-classification input, complementary
    to H-012's event-proximity rule and distinct from it — inflation
    regime is continuous/gradual, not discrete-event-driven).
11. **Consuming module**: new macro reference table; `regime_stable_dates()`
    as an additional regime dimension if a future hypothesis pursues it.
12. **Priority**: **Near-term** — real, disclosed research value, but
    behind the risk-free-rate fix in urgency.
13. **Market classification**: Frontier-market-specific (the concrete
    Nigerian CPI/GDP series), universal in technique (inflation/GDP-regime
    conditioning is standard practice in any market's macro research).

---

## B. Corporate / Governance Data

### B1. NGX X-Compliance Report

1. **Official source**: ngxgroup.com
   (`/exchange/trade/investor-protection-education/x-compliance-report/`);
   PDF at `doclib.ngxgroup.com/.../X-Compliance.pdf`.
2. **Truly free?**: Yes, confirmed — publicly published compliance report.
3. **Historical depth**: **Uncertain** — confirmed the report exists and
   is periodically republished; a full historical archive of past
   X-Compliance reports (versus only the current one) was not confirmed
   in this pass.
4. **Update frequency**: Appears to be a recurring (likely
   quarterly-or-more-frequent) report, per references to "quarterly
   disclosure reports" on compliance-plan progress in the search results.
5. **Data quality**: **High** — this is NGX's own official transparency
   mechanism, explicitly covering free-float adequacy (tied to the
   Listing Rules' minimum free-float requirement — 20% for Main/Premium
   Board per the confirmed search result) and other disclosure
   obligations.
6. **Point-in-time suitability**: Good if historical editions can be
   archived going forward — each report reflects compliance status as of
   its publish date.
7. **Acquisition method**: PDF.
8. **Automation difficulty**: **4/10** — a single, recurring, structured
   PDF (not thousands of scattered notices), meaningfully easier to
   extract than the ad hoc "free-float deficiency notice" PDFs already
   found scattered through the existing 11,500-document archive.
9. **Research value**: **High**, and directly relevant to a known platform
   gap: the earlier factor-availability audit found no structured
   shares-outstanding/free-float dataset anywhere in the platform (only
   unextracted raw PDF filenames). **This is a materially better,
   already-structured target for that same gap** — a recurring compliance
   scorecard rather than scattered one-off notices.
10. **Hypothesis families unlocked**: free-float-adjusted size (a real
    refinement of H-011's already-confirmed but full-issue-share-count
    size measure); free-float-deficiency as its own governance/liquidity
    signal.
11. **Consuming module**: FSI extraction pipeline (a new, narrow,
    well-scoped extraction target — one recurring report format, not
    11,500 heterogeneous filings); `data/reference/` as a new structured
    table analogous to `market_cap_panel.csv`.
12. **Priority**: **Near-term** — narrow, well-scoped, directly addresses
    a previously-identified real gap (free-float data absence).
13. **Market classification**: Frontier-market-specific (free-float
    compliance monitoring at this level of regulatory attention is a
    direct response to NGX's own thin-liquidity market structure).

### B2. UK Companies House API (for Seplat Energy Plc and any other UK-incorporated dual-listed NGX names)

1. **Official source**: developer.company-information.service.gov.uk.
2. **Truly free?**: Yes, confirmed, official UK government API, no fees.
3. **Historical depth**: Filing history depth varies by company; UK
   statutory filing requirements typically ensure a full incorporation-to-
   present filing history.
4. **Update frequency**: Event-driven (as filings are made) plus a
   confirmation-statement/annual-accounts cadence.
5. **Data quality**: **High** for company registration/officer/PSC data;
   **Medium-Low for financials specifically** — confirmed limitation: only
   ~40% of filed accounts across the whole UK register are available as
   structured data; the rest are PDF-only, so this does not reliably
   upgrade FSI's structured-fact extraction without additional PDF
   parsing work.
6. **Point-in-time suitability**: Good — filings are dated at submission.
7. **Acquisition method**: REST API (JSON) for company/officer/PSC data;
   Document API returns filed accounts as PDF.
8. **Automation difficulty**: **2/10** for the API itself (well-documented,
   600 requests/5min); **higher** if structured financials are the goal,
   since most accounts are PDF-only.
9. **Research value**: **Low** in universe-wide terms (applies to at most
   a handful of NGX names with UK incorporation/dual-listing — Seplat
   Energy Plc being the clearest confirmed case) but **Medium** for that
   specific name, since it is one of FSI's already-covered 10 tickers and
   this could genuinely deepen (not just broaden) coverage for it.
10. **Hypothesis families unlocked**: none new at universe scale; a
    narrow data-quality improvement for one existing ticker's statement
    coverage.
11. **Consuming module**: FSI extraction pipeline, scoped narrowly to
    dual-listed names.
12. **Priority**: **Future** — real but narrow value; the platform's FSI
    breadth problem (10 of ~100 tickers) is not solved by deepening one
    already-covered name.
13. **Market classification**: **Universal** technique (UK company-registry
    data), applied here to a frontier-market-listed company's dual-listing
    structure specifically.

### B3. London Stock Exchange RNS (via Investegate, a free aggregator)

1. **Official source**: RNS is the LSE's official news service; Investegate
   (investegate.co.uk) is a long-established free public aggregator of RNS
   announcements (confirmed Seplat Energy's dual-board disclosures appear
   there, including dividend, board, and interim-results announcements).
2. **Truly free?**: Investegate's announcement archive appears freely
   browsable; **uncertain** whether Investegate imposes terms of use
   restricting bulk scraping specifically (a redistribution/ToS question
   distinct from "is it viewable free," which this pass did not resolve) —
   flagged for legal review before any automated bulk scraping, consistent
   with "do not recommend datasets that cannot legally be obtained."
3. **Historical depth**: Confirmed multi-year archive for Seplat Energy
   specifically (results found spanning at least 2025-2026 in this pass;
   likely extends to its 2015 dual-listing given Investegate's stated
   longstanding aggregator role, not individually confirmed further back).
4. **Update frequency**: Event-driven, same-day as RNS publication.
5. **Data quality**: **High** — RNS is FCA-approved as a Primary
   Information Provider; this is a materially higher-disclosure-standard
   feed than most frontier-market-only news sources.
6. **Point-in-time suitability**: Excellent — RNS announcements are
   timestamped at release, effectively the gold standard for corporate-
   event point-in-time correctness.
7. **Acquisition method**: HTML (per-announcement pages); no confirmed
   free bulk API.
8. **Automation difficulty**: **5/10**, pending the ToS question in
   item 2.
9. **Research value**: **Medium** for the narrow set of dual-listed names
   — faster, more complete, better-timestamped disclosure than relying on
   NGX-side filings alone for those specific names.
10. **Hypothesis families unlocked**: event-study research restricted to
    dual-listed names (too narrow a universe to support a standalone
    cross-sectional factor test, per the platform's own breadth
    discipline).
11. **Consuming module**: document ingestion pipeline, scoped to
    dual-listed tickers only.
12. **Priority**: **Future** — same reasoning as B2 (real but narrow).
13. **Market classification**: **Universal** infrastructure (RNS/LSE),
    valuable here only because of a frontier-market company's specific
    dual-listing choice.

### B4. Corporate Affairs Commission (CAC) Nigeria — Public Search

1. **Official source**: search.cac.gov.ng.
2. **Truly free?**: Yes, confirmed free public search.
3. **Historical depth**: Point-in-time registration/director data as
   currently recorded; **no evidence found of historical/versioned
   snapshots** (i.e., it appears to show current status, not a dated
   history of past director changes) — a real limitation for point-in-time
   reconstruction.
4. **Update frequency**: Presumably updated as CAC processes filings;
   frequency not specified publicly.
5. **Data quality**: **Medium** — official registrar data, but confirmed
   only at the level of "verify registration status, directors" per
   individual company search; no confirmation of bulk/structured export.
6. **Point-in-time suitability**: **Weak** — appears to expose only
   current state, not a dated change history, per this pass's findings.
   Using it for backtesting director-change events would require the
   platform to itself start snapshotting it repeatedly going forward
   (it cannot backfill history).
7. **Acquisition method**: Per-company HTML search, one record at a time;
   no confirmed bulk API.
8. **Automation difficulty**: **7/10** — one-at-a-time lookups across
   ~100 IRU names is feasible in principle (a bounded, small N) but
   without a documented API, likely requires either manual lookup or
   scraping a search form (possible CAPTCHA/rate-limit friction, not
   confirmed either way in this pass).
9. **Research value**: **Low-Medium** — this is the closest free source
   found for the "directors/executives" and "board composition" categories
   requested, but its lack of historical snapshots is a real, disclosed
   constraint on backtestable research value; going forward (not
   retroactively) it could feed board-turnover-event research.
10. **Hypothesis families unlocked**: board-stability/governance-turnover
    signal (small-universe, forward-looking only given the snapshot
    limitation).
11. **Consuming module**: a new, small governance-events reference table,
    populated prospectively rather than backfilled.
12. **Priority**: **Future** — real gap-filler for a requested category,
    but low near-term research value given the point-in-time limitation.
13. **Market classification**: Frontier-market-specific (Nigeria's
    company registrar), though the general technique (registrar-sourced
    governance data) is universal.

### B5. Insider ownership / beneficial ownership / shareholder structure — **no adequate free source found**

Stated plainly, per the instruction not to invent sources: this audit did
not find a free, legally-obtainable, structured source of Nigerian listed-
company shareholder registers, beneficial ownership, or insider-dealing
disclosures analogous to a UK PSC register or a US Schedule 13D/Form 4
regime. CSCS (the registrar/depository) is the party that would hold this
data but no public free access point was found. This is a genuine,
disclosed gap — not filled with a weak substitute.

---

## C. Corporate Events / Regulatory (extraction task on already-owned data, not a new external source)

AGM dates, earnings-announcement dates, auditor changes, and some
regulatory notices very likely already exist **inside the platform's
existing 11,500-document corpus** as unstructured filing content, per the
same pattern already found for Share Issuance in the prior factor audit
(broad symbol coverage in the raw archive, but no structured event-type
classification). **This is not a new data-acquisition recommendation** —
it is a restatement that a classification/extraction pass on data already
owned is likely to be more productive here than seeking a new external
source, exactly as already scoped for Share Issuance. SEC Nigeria's own
enforcement/sanctions pages (sec.gov.ng) were found to exist but their
content depth and distinctness from NGX's own circulars was **not verified
in this pass** — flagged as uncertain rather than asserted as valuable.

---

## D. Alternative / Frontier-Specific Public Data

### D1. GDELT Project — Global Event/News Database

1. **Official source**: gdeltproject.org.
2. **Truly free?**: Yes, confirmed explicitly — "100% free and open,"
   downloadable raw files or queryable via Google BigQuery.
3. **Historical depth**: Confirmed — event archives from 1979 (with
   ongoing extension toward 1800 for a subset), updated every 15 minutes.
4. **Update frequency**: Near-real-time (15-minute updates).
5. **Data quality**: **Medium** for single-country (Nigeria) precision —
   GDELT is a global, automatically-coded, multilingual event database;
   its automated event-coding is known (in the broader literature on
   GDELT, not verified specifically here) to carry real noise/miscoding
   risk at the level of any single country or company, which must be
   filtered/validated before use, not taken as ground truth.
6. **Point-in-time suitability**: Good in principle — events are
   timestamped at (near) real-time capture — but media-coverage lag/
   selection effects (what gets reported, and when) are a real, distinct
   bias from look-ahead bias and should be separately considered.
7. **Acquisition method**: Bulk file download, or BigQuery (free tier
   limits apply to BigQuery specifically; the raw files themselves are
   unrestricted).
8. **Automation difficulty**: **7/10** — the data exists and is
   accessible, but isolating Nigeria/NGX-company-relevant signal from a
   global, multilingual, 300+-category event stream is real engineering
   and validation work, not a simple download.
9. **Research value**: **Medium-High, frontier-specific rationale** —
   in a market with NGX's own documented characteristics (10-ticker FSI
   statement coverage vs. a ~100-name universe, i.e., very thin analyst/
   fundamental coverage), a media/event-attention signal plausibly carries
   more incremental information than in a heavily-covered developed
   market, where such signals are already priced in via dense sell-side
   coverage. This is a real, citable rationale (information diffusion is
   slower where formal analyst coverage is sparse), not a generic "more
   data is good" claim.
10. **Hypothesis families unlocked**: media-attention/event-intensity
    factor (frontier-specific rationale); potentially a new regime
    variable (news-volume spikes as an alternative regime classifier to
    H-012's own event-severity rule).
11. **Consuming module**: a new ingestion pipeline (does not fit cleanly
    into the existing FSI/document-ingestion pipeline, which is built
    around structured NGX regulatory filings, not global news streams) —
    likely its own new module.
12. **Priority**: **Future** — real, frontier-specific rationale, but
    the engineering/validation cost (filtering a global stream to
    NGX-specific, low-noise signal) is high relative to the
    Immediate/Near-term items above.
13. **Market classification**: **Frontier-market-specific value**, even
    though the underlying data source itself is universal/global — the
    argument for its incremental value rests specifically on frontier
    markets' lower baseline analyst coverage.

### D2. Google Trends (via the unofficial `pytrends` library)

1. **Official source**: trends.google.com; `pytrends` is a third-party,
   unofficial Python wrapper (github.com/GeneralMills/pytrends and forks).
2. **Truly free?**: Yes for the underlying Google Trends data itself;
   `pytrends` is an **unofficial** scraper of Google's public web
   interface, not a sanctioned API — genuinely free today, but carries
   real risk of breaking without notice if Google changes its site
   (disclosed explicitly, not glossed over) and is subject to Google's own
   rate limits.
3. **Historical depth**: Google Trends' own interest-over-time data
   generally extends to 2004; confirmed via `pytrends`' documented
   "Historical Hourly Interest" and "Interest Over Time" functions.
4. **Update frequency**: Near-real-time for recent data; the platform
   would typically pull weekly/monthly indexed series.
5. **Data quality**: **Medium** — Google Trends returns *indexed* (0-100
   relative) search interest, not absolute search volume, and is itself a
   sampled estimate, not a full-population count — a real, disclosed
   precision limitation.
6. **Point-in-time suitability**: **Weak-Medium** — Google Trends'
   normalization is relative to the query window requested, meaning a
   value pulled today for a past date is not guaranteed identical to what
   would have been observed had the query been run on that past date
   itself — a genuine reproducibility concern for point-in-time backtesting
   that should be disclosed in any prereg using this source, not assumed
   away.
7. **Acquisition method**: Scraping (via `pytrends`, unofficial).
8. **Automation difficulty**: **6/10** — functionally straightforward but
   fragile (rate limits, no SLA, unofficial status).
9. **Research value**: **Medium, frontier-specific rationale** — real
   academic precedent exists for search-interest as a retail-attention
   proxy (Da, Engelberg & Gao, 2011, *Journal of Finance*, "In Search of
   Attention") — cited as a real, existing paper, not fabricated; its
   original application was to US retail-investor attention, so applying
   it to NGX-listed names is a genuinely new, unproven adaptation, not a
   confirmed frontier-market finding.
10. **Hypothesis families unlocked**: retail-attention proxy factor,
    plausibly complementary to (not overlapping with) the platform's
    existing, confirmed Size factor.
11. **Consuming module**: new, small alternative-data ingestion module;
    not a fit for the existing FSI/document pipeline.
12. **Priority**: **Future** — real, citable rationale, but unofficial-API
    fragility and point-in-time reproducibility concerns should be
    resolved (or explicitly accepted as limitations) before pre-registering
    any hypothesis on it.
13. **Market classification**: **Frontier-market-specific rationale**
    (same low-analyst-coverage argument as GDELT above) applied to a
    **universal** underlying data source.

### D3. NOAA/NASA VIIRS Nighttime Lights (satellite economic-activity proxy)

1. **Official source**: Distributed via NOAA/NASA; confirmed accessible
   free via Google Earth Engine (`NOAA_VIIRS_DNB_ANNUAL_V21` dataset) and
   AWS Open Data.
2. **Truly free?**: Yes, confirmed.
3. **Historical depth**: Confirmed monthly/annual composites from 2012
   to present; a separately-published simulated dataset extends back to
   1992 (a modeled reconstruction, not raw VIIRS sensor data before
   VIIRS's own 2012 launch — a real, disclosed methodological distinction
   between raw-sensor-era and reconstructed-era data).
4. **Update frequency**: Monthly/annual composites.
5. **Data quality**: **High** for what it actually measures (radiance-
   calibrated light emissions); **Medium** as an *economic-activity proxy*
   specifically — this is an inference layer on top of the raw
   measurement, with real, published academic support (Henderson,
   Storeygard & Weil, 2012, "Measuring Economic Growth from Outer Space,"
   *American Economic Review* — cited as a real, existing paper) but is
   not a direct measurement of GDP, revenue, or any company-specific
   metric.
6. **Point-in-time suitability**: Good — satellite composites are dated
   at capture, no revision risk in the way survey-based statistics have.
7. **Acquisition method**: Cloud-optimized GeoTIFF via AWS Open Data, or
   Google Earth Engine API.
8. **Automation difficulty**: **8/10** — genuinely more complex than the
   other sources here: requires geospatial processing (defining regions
   of interest around, e.g., Nigerian industrial/port/company-operation
   areas), not just a tabular download.
9. **Research value**: **Medium, frontier-specific rationale** — the
   academic case for using satellite nightlights (Henderson et al.) is
   specifically strongest in places where official statistics are weak or
   lagged, which is a real, citable argument for Nigeria/frontier markets
   relative to developed markets with dense official data. Its
   *application to individual listed-company research* (rather than
   regional/national GDP proxying) is a much larger inferential leap this
   audit does not have direct academic support for — stated as
   uncertain, not claimed.
10. **Hypothesis families unlocked**: regional-economic-activity proxy
    for regionally-concentrated business lines (e.g., a cement or oil
    company's plant-region activity) — a genuinely novel, unproven signal
    class for this platform.
11. **Consuming module**: new geospatial-data module — no existing
    platform component consumes anything like this today.
12. **Priority**: **Future** — real academic grounding for the macro use
    case, high engineering cost, and unproven applicability at the
    individual-company level this platform researches.
13. **Market classification**: **Frontier-market-specific rationale**
    (weak/lagged official statistics is the whole justification), applied
    to a **universal** satellite data source.

### D4. FAOSTAT — Agricultural Commodity Prices (palm oil, cocoa, etc.)

1. **Official source**: fao.org/faostat.
2. **Truly free?**: Yes, confirmed.
3. **Historical depth**: Confirmed — FAOSTAT production/price data
   generally from 1961 (production series) and 1991 onward (producer
   price series) for ~200 countries/products.
4. **Update frequency**: Annual (producer prices); the separate FAO Food
   Price Index is published monthly.
5. **Data quality**: **High** — official UN agency, standard reference
   for agricultural commodity research globally.
6. **Point-in-time suitability**: Good for annual producer-price series;
   monthly Food Price Index likely has minimal revision.
7. **Acquisition method**: Bulk CSV/API via FAOSTAT's own data portal.
8. **Automation difficulty**: **3/10** — structured, documented bulk
   access.
9. **Research value**: **Low-Medium, narrow-universe** — relevant
   specifically to NGX's agro-industrial names (e.g., palm-oil producers);
   too narrow a universe (a handful of tickers) to support a standalone
   cross-sectional factor test under this platform's own breadth
   discipline, but could support a sector-level commodity-exposure
   interaction study for those specific names.
10. **Hypothesis families unlocked**: commodity-exposure interaction
    factor, narrow-universe.
11. **Consuming module**: new small commodity-reference table.
12. **Priority**: **Future** — real but narrow.
13. **Market classification**: **Universal** data source, with
    frontier-market relevance specifically because several NGX-listed
    names are commodity producers whose revenue is directly linked to
    these world prices (a genuine, citable link, distinct from a generic
    "commodities matter everywhere" claim).

### D5. NEITI — Nigeria Extractive Industries Transparency Initiative

1. **Official source**: neiti.gov.ng.
2. **Truly free?**: Yes, confirmed — public audit reports.
3. **Historical depth**: Confirmed — oil and gas industry audit reports
   from 1999 to 2020 (per the confirmed search result); more recent
   audits (2020-2021 cycle) confirmed launched in 2023, suggesting a
   multi-year reporting lag is typical.
4. **Update frequency**: Irregular/multi-year audit cycles, not a regular
   calendar cadence — a real, disclosed limitation (this is not a
   timely, tradeable-frequency data source).
5. **Data quality**: **High** in content (independently audited
   government-industry revenue reconciliation) but **Low** in timeliness
   given the multi-year publication lag.
6. **Point-in-time suitability**: Genuinely awkward — a report published
   in 2023 covering 2020-2021 activity would, if naively dated to its
   *coverage* period rather than its *publication* date, create a real
   look-ahead violation; must be dated to publication, not coverage, if
   ever used.
7. **Acquisition method**: PDF reports.
8. **Automation difficulty**: **7/10** — PDF-only, likely narrative/
   tabular mixed content requiring real extraction work for a handful of
   reports (not thousands), similar in kind to the platform's own
   FSI hand-verification approach for a small n.
9. **Research value**: **Medium, genuinely frontier-specific** — this is
   the one source in this whole audit with **no developed-market
   analogue at all**: it exists specifically because Nigeria's oil/gas/
   mining revenue flows are opaque enough to warrant an independent,
   government-commissioned audit reconciliation. Its research value is
   as an **independent cross-check on company-reported figures** (does a
   company's reported production/revenue in its own filings match what
   NEITI's independent audit found?) — a genuinely novel "revenue-audit
   divergence" signal class unique to extractive-economy frontier markets,
   not a repackaging of any factor already tested.
10. **Hypothesis families unlocked**: revenue-integrity/audit-divergence
    signal (frontier/extractive-economy-specific; no analogue in the
    platform's existing 16-family list from the prior audit).
11. **Consuming module**: FSI extraction pipeline, as a small,
    hand-verified supplementary source for oil/gas-sector tickers only
    (Seplat and historically other majors) — same rigor already applied
    to the 137 hand-verified facts.
12. **Priority**: **Future** — small n (extractive-sector names only),
    multi-year lag, but a genuinely unique, uncrowded research angle
    worth scoping once core statistical/breadth priorities are addressed.
13. **Market classification**: **Frontier-market-specific**, and more
    specifically **extractive-economy-specific** — this data class simply
    does not exist for developed or most emerging markets in this form.

---

## E. Sources evaluated and explicitly NOT recommended

- **CEIC, TradingEconomics**: secondary aggregators of the same primary
  sources already listed above (CBN, NBS, World Bank); confirmed to appear
  prominently in search results, but they are not original sources, are
  commonly paywalled beyond limited free previews, and their terms of use
  for bulk redistribution were not confirmed — **not recommended**, use
  the primary sources (CBN/NBS/DMO/World Bank) directly instead.
- **AfricanFinancials.com** and similar annual-report aggregators:
  encountered in general knowledge of this space but **not independently
  re-verified in this pass**; terms of use for bulk scraping/redistribution
  are uncertain — **not recommended without further legal verification**,
  consistent with "do not recommend datasets that cannot legally be
  obtained."
- **SEC Nigeria bulk filings database**: the official site (sec.gov.ng)
  exists and has a filings-related page, but no evidence of a structured,
  bulk-downloadable filings archive (comparable to NGX's own disclosure
  portal) was found in this pass — **not recommended as a distinct
  near-term target**; flagged as uncertain rather than valuable.
- **Weather/shipping/port-throughput data**: no NGX-relevant, sufficiently
  granular, free structured source was identified in this pass (general
  global shipping-tracking and weather datasets exist, e.g. from NOAA, but
  their specific relevance and accessibility for Nigerian port/trade
  activity at a useful granularity was not established) — stated as an
  open uncertainty, not asserted as either available or unavailable.

---

## Summary priority table

| Priority | Dataset | One-line reason |
|---|---|---|
| **Immediate** | CBN rates (MPR/T-bill) | Fixes the platform's own disclosed `rf_annual_pct=0.0` placeholder used by every Sharpe ratio reported to date |
| Near-term | FMDQ NAFEX/T-bill/bond data | Independent cross-check + continuous FX-regime variable |
| Near-term | DMO bond auctions | Term-structure depth for the same risk-free-rate fix |
| Near-term | NBS CPI/GDP | New continuous macro-regime input, distinct from H-012's event-based rule |
| Near-term | NGX X-Compliance Report | Structured, recurring free-float source — better target than scattered raw PDFs already found |
| Future | World Bank WDI | Broad context only; revision-prone, low frequency |
| Future | UK Companies House | Real but narrow (≤1-2 dual-listed tickers) |
| Future | LSE RNS / Investegate | Real but narrow; ToS uncertainty flagged |
| Future | CAC public search | No historical snapshots — forward-only value |
| Future | GDELT | Frontier-specific rationale, high engineering/validation cost |
| Future | Google Trends | Frontier-specific rationale, unofficial-API fragility, PIT reproducibility concern |
| Future | NOAA VIIRS nightlights | Strong macro rationale, weak company-level rationale, high engineering cost |
| Future | FAOSTAT | Real but narrow (agro-sector tickers only) |
| Future | NEITI | Genuinely unique frontier/extractive angle, but small n and multi-year publication lag |
| Not worthwhile | CEIC/TradingEconomics | Secondary aggregators of sources already listed |
| Not recommended (unverified legality) | AfricanFinancials.com-style aggregators | ToS/legality not confirmed |
| Not found | Beneficial ownership / shareholder registers | No adequate free source identified — genuine gap, not filled with a weak substitute |

**Overall reading**: the single highest-leverage action available today
is not a new factor-discovery dataset at all — it is closing the
platform's own already-disclosed risk-free-rate placeholder using CBN's
(and optionally FMDQ's/DMO's) freely published T-bill/bond rates. Every
genuinely new frontier-specific factor-discovery angle found in this audit
(NEITI's revenue-audit divergence, GDELT/Google-Trends attention proxies
under a low-analyst-coverage rationale, NOAA nightlights) carries real,
disclosed engineering cost, uncertain applicability at the individual-
company level, or narrow universe reach — none rise to the "Immediate"
tier the risk-free-rate fix does.
