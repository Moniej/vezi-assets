# Data Acquisition Plan — NGX Event Database (H-003 and successors)

*Prepared 2026-07-15. Status of every source claim: probed this date unless
marked otherwise. The event database is a long-term Fund Alpha asset — it is
built to outlive H-003.*

## Standing rules

1. **Primary sources first.** An event's announced_date comes from the
   issuing institution's own document wherever one exists. Never infer dates
   from later summaries; a date that cannot be established stays NULL.
2. **Two-source discipline.** Target one primary + one secondary
   verification source per event class. Where only secondary sources exist,
   confidence is capped at 0.6 and the gap is recorded.
3. **Append-only, point-in-time.** All ingestion runs through
   `event_pipeline.py` (taxonomy, chronology, duplicate, and cross-source
   conflict checks; quality report per batch). Conflicts are preserved and
   resolved by confidence, never by deletion.
4. **Direction is data, not doctrine.** `direction` defaults to `unknown`.
   Assigning bullish/bearish requires either an explicit pre-registered rule
   or leaving it unknown — H-003 must not smuggle conclusions in as inputs.

## Confidence vocabulary

0.9 issuing institution's own dated document · 0.7 manual entry verified
against a primary document · 0.6 reputable secondary only (press/aggregator)
· 0.4 manual, unverified · 0.0 synthetic.

---

## A. Macroeconomic events

### A1. CBN MPC decisions (MPR, CRR, liquidity ratio, asymmetric corridor)
| | |
|---|---|
| Purpose | Core monetary catalyst series; market-scope; the most systematic event class available |
| Required fields | meeting end date (=announced), communiqué number, MPR before/after, CRR before/after, vote split if published, outcome_text (hike/hold/cut + bps) |
| Primary source | cbn.gov.ng MPC decisions page + per-meeting communiqué PDFs (**probed: reachable**, HTML with JS-included fragments — parse fragments or fetch communiqué list directly) |
| Secondary | Reuters/Nairametrics same-day reports |
| Coverage | 2004→present (communiqués numbered continuously); need ≥2012 to match price data |
| Update frequency | ~6 meetings/year (bi-monthly) |
| Confidence | 0.9 |
| Licensing | Public central-bank publications; cite source URLs |
| Method | HTML parse of decisions listing + PDF text extraction for outcomes; manual spot-verification of 10% |

### A2. Inflation releases (NBS CPI)
Purpose: inflation-surprise catalysts. **The release date is the event date**,
not the reference month — historical *release* dates are the hard part.
Fields: release date (announced), reference month, headline/food/core YoY,
prior value. Primary: nigerianstat.gov.ng (**probed: reachable**; documents
library). Secondary: press reports of each release; tradingeconomics calendar
for release-date verification. Coverage: data 2009→; reliable release *dates*
likely only 2016→ (NBS portal history) — earlier months enter as
`effective`-only with NULL announced_date (unusable for PIT signals, kept for
context). Frequency: monthly (~day 15). Confidence: 0.8 (values) / 0.6
(pre-2016 release dates, if press-derived). Method: HTML/PDF parse + press
cross-check.

### A3. FX policy & regime changes
Purpose: the single most market-moving class in sample (June 2023 unification
coincided with the synchronized sector jumps our price-staging flagged).
Fields: standard + regime label. Primary: CBN circulars library (dated PDFs).
Secondary: TheCable/BusinessDay same-day reports. Coverage: sparse,
event-driven (~1–5/year). Confidence: 0.9 primary / 0.7 verified-manual.
Method: circulars-library crawl + manual curation (small N, high value).
Seed rows ingested 2026-07-15: FX unification 2023-06-14 (0.7).

### A4. GDP releases
As A2 (NBS, quarterly, release date = event date). Lower priority: slow,
heavily anticipated. Confidence 0.8.

### A5. Daily exchange-rate series (official/NAFEM, parallel if sourced)
Purpose: covariate for regime definition and FX-shock detection (not an
event list itself; `fx_rates` table already exists). Primary: CBN exchange
rates page; FMDQ (registration wall). Secondary: investing.com USD/NGN.
Coverage 2012→. Daily. Confidence 0.9/0.5. Method: HTML parse (CBN) or
investing.com provider extension (endpoint already proven for indices).

## B. Regulatory events

### B1. CBN banking circulars & directives (incl. recapitalisation)
Purpose: banking is the dispersion engine of NGX; recap cycles are H-003's
flagship catalyst. Fields: standard + circular ref number. Primary: CBN
circulars library (dated PDFs, e.g. `cbn.gov.ng/Out/2024/CCD/...`).
Secondary: law-firm client alerts, Nairametrics. Coverage: 2010→ online.
Frequency: irregular (dozens/year; filter to price-sensitive). Confidence
0.9. Method: crawl circulars index; classify manually into taxonomy (do NOT
auto-classify with keyword rules without review — misclassification poisons
the signal). Seed row ingested: 2024-03-28 recap directive (0.7, primary PDF
linked).

### B2. SEC Nigeria circulars/directives
Primary: sec.gov.ng (**probed: reachable**). Coverage 2013→ (site archive
depth TBC). Confidence 0.8. Method: HTML crawl + manual triage.

### ★ BREAKTHROUGH (2026-07-16): NGX doclib SharePoint REST discovered

`doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('<list>')/items` — open OData
access to exchange-official lists, including **XFinancial_News (70k+ X-Issuer
disclosure items, 2014-07 → live today)** with company symbol, ISIN,
submission type, announcement timestamp, and document URL; plus
NoticeToIssuers (546), DelistedCompanies, Daily Summary, MarketDataDownloads,
PE Ratio, MarketCap, CompanyDirectory. This single discovery re-scopes
datasets C4, B3, and the disclosure archive from "endpoint discovery needed"
to "harvestable now".

**Harvested 2026-07-16 (stage 1):** 11,546 corporate-action filings
(2014-2026, 259 symbols, 100% with document URLs) →
`data/staging/xissuer/corporate_actions_calendar.csv`. PIT caveat: 95 items
from the 2014-07-11 migration batch carry load-time, not announcement-time,
stamps. **Stage 2 (next): parse linked documents for dividend amounts,
qualification/payment dates → corporate_actions table (unblocks H-002).**
Daily forward capture of the full disclosure feed (all submission types)
added to `daily_capture.py`.

### B3. NGX market notices: circulars, index reviews, suspensions,
### listings/delistings
Purpose: dual use — event catalysts AND the `index_membership.announced_date`
fix that makes constituent work survivorship-proof. Primary: NGX
(ngxgroup.com media/market-notices; the doclib REST API exists —
`/statistics/ticker` responds — but disclosure/circular endpoint names 404'd
on guessed paths; **work item: discover real endpoint names from the site's
network traffic via browser dev tools**). Secondary: press. Coverage: TBC
(likely 2015→ online). Confidence 0.9 (exchange-official). Method: REST if
discovered, else HTML parse of notices pages.

## C. Company events (corporate actions & calendar)

### C4. Earnings announcements, dividends (declared/qualification/payment),
### rights, bonus, splits, M&A, delistings
Purpose: corporate catalyst class for H-003; the dividend fields
simultaneously unblock H-002 (total-return momentum) — highest reuse value of
any dataset here. Fields: the full `corporate_actions` schema (already
built), plus announcement rows in `events`. Primary: NGX X-Issuer company
disclosures; company IR pages; registrar notices (Africa Prudential, GTL).
Secondary: Nairametrics corporate round-ups. Coverage: strong 2018→ online;
patchy 2012–2017 (disclosure portal depth TBC). Frequency: continuous.
Confidence: 0.8 (portal) / 0.6 (press-only). Method: disclosure-portal crawl
per top-20 ticker (covers ~90% of sector-index weight), manual for the rest.
**Scope control:** limit to constituents of the five investible sector
indices.

## D. Sector-specific events

### D1. Oil price series & shock events (Brent)
Purpose: commodity catalyst for NGXOILGAS; shocks derived from the daily
series by a pre-registered rule (e.g. |20-day move| > threshold), so the
series is the dataset, the events are computed and marked `is_derived`.
Primary: FRED `DCOILBRENTEU` CSV (**probe timed out — retry**; EIA API as
alternate). Secondary: stooq. Coverage 1987→. Daily. Confidence 0.9.
Method: CSV download. Trivial effort.

### D2. Energy policy (PIA, subsidy changes, gas policy)
Primary: government gazettes, NNPC/NMDPRA releases; press for dates.
Sparse, manual curation. Confidence 0.6–0.7. Method: manual entry with
verification trail (like the seed batch).

### D3. NAICOM insurance regulation (recapitalisation, directives)
Primary: naicom.gov.ng. Insurance recap history (2019–2021 attempted, court-
stalled) is a natural experiment for H-003. Confidence 0.8. Manual + crawl.

### D4. PenCom reforms | D5. Fiscal/tax policy (budgets, VAT changes)
Primary: pencom.gov.ng / Budget Office, FIRS. Sparse; manual. Confidence
0.6–0.8.

---

## Pipeline (built and demonstrated 2026-07-15)

- Schema: `events` table extended (category, severity, direction,
  publication_ts, source_url, notes); type CHECK replaced by the configurable
  taxonomy `configs/event_taxonomy.toml` (8 categories, 40+ types; add a
  type = edit the TOML, no code).
- `src/ngxrot/event_pipeline.py`: taxonomy/vocabulary validation, chronology
  checks (effective<announced flagged; future-dated rejected;
  publication_ts≠announced flagged), batch and cross-source duplicate
  detection, conflict preservation + logging, per-batch quality report.
- Demonstrated: 3-row seed batch → 2 verified events accepted (0.7), 1
  invalid type rejected with reason; legacy rows preserved through the
  table migration (63+2 = 65).

## Completeness reporting

`reports/event_quality_<date>.md` after every batch (ingestion stats,
issues, category counts). A cross-dataset completeness view (coverage per
event class per year vs. the acquisition targets above) becomes meaningful
once the first systematic class (MPC) is loaded — deliverable of the next
acquisition sprint, same format as the price-data completeness report.
