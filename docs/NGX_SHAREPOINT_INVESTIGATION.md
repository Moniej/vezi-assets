# NGX SharePoint Investigation — Historical Equity Source Decision

*2026-07-17. Read-only investigation per IC directive; no backfill executed.
All probe payloads archived under `data/staging/sharepoint_probe/`.*

## 1. What exists (enumerated)

**Catalog:** SharePoint list `DownloadsContent` (35,235 items inventoried,
IDs 36→35,490) is the file catalog for 14 categories (list `DownloadFolder`),
including: DAILY OFFICIAL LIST (EQUITIES) · GAINERS AND PRICELIST · SHARES
OUTSTANDING · MARKET CAPITALIZATION · DAILY SUMMARY STATISTICS · P.E RATIO ·
INDICES REPORTS · WEEKLY SUMMARY STATISTICS · DOL (BONDS/ETFS) · MEMORANDUM
QUOTATION · FOREIGN LISTINGS.

**Files:** served at `https://doclib.ngxgroup.com/DownloadsContent/<Title>.pdf`
(pattern recovered via Wayback CDX of the legacy nse.com.ng site and
**verified live** on both a 2015 and a 2026 file).

**Current-day REST:** `doclib.ngxgroup.com/REST/api/statistics/equities/`
returns the full daily cross-section as JSON: Symbol, Prev/Open/High/Low/
Close, Change, **Trades, Volume, Value (naira)**, Board, Sector, TradeDate.

## 2. Characterization — DAILY OFFICIAL LIST (EQUITIES)

| Question | Finding |
|---|---|
| Earliest | **2014-06-30** (feed's first item; catalog begins 2014-07-11 load) |
| Latest | **yesterday** (2026-07-16; new items land ~16:00 UTC daily) |
| Frequency | Daily — 2,846 files; 216–249/yr vs ~247 trading days (≈97% complete; exact gap list to be produced by the harvester) |
| Fields | Per-symbol tables by board/sector: Symbol, Security Name, Quotation Price + further columns (full inventory = parser step 1; the current-day REST confirms the exchange records OHLC/Trades/Volume/Value) |
| Format | **Text-based PDFs** (machine-generated, ~90–105KB, 27–35 pp) — pypdf extracts cleanly; **no OCR required** |
| Download method | Plain HTTPS GET by title; catalog paged via REST OData |
| Permanent or rolling? | **Permanent in practice**: items carry 30-day `Expiry_Date` metadata but 2014 files remain live 12 years on — expiry is unenforced. (Risk noted: policy could change; archive-first mitigates.) |
| Delisted companies | **Present by construction** — each file is a frozen as-published snapshot; the 2015 file inventories the full 2015 board incl. later-dead names. Survivorship-clean and PIT-exact. |
| Bonus datasets | SHARES OUTSTANDING (daily → market cap + float math), MARKET CAPITALIZATION (2012-11→), INDICES REPORTS (2012-10→ — extends index history 15 months before investing.com's 2012-01... overlap cross-check), Gainers/PriceList |

## 3. NGX vs investing.com

| Dimension | NGX DownloadsContent | investing.com |
|---|---|---|
| Coverage | 2014-06 → present, ~97% of trading days, ALL listed symbols incl. ASeM/small boards | 2012 → present but only symbols the vendor lists TODAY; resolution of 259 filing symbols unknown (rate-limited before completing) |
| Survivorship | **Clean by construction** (frozen snapshots) | Biased toward survivors; delisted names likely absent |
| PIT integrity | **Exact** — as-published documents with catalog timestamps | Vendor may restate/adjust silently; vintage unknown |
| Adjustment quality | Raw as-traded prices (unadjusted) + our own corporate-actions DB = we control adjustment, auditable | Unknown vendor adjustment policy (flagged since day 1) |
| Value traded / deals | **Yes** (Value, Trades — capacity machinery's missing input) | Volume only; no naira value, no deals |
| Confidence score | **0.9 (exchange-official)** | 0.5 (aggregator) |
| Engineering effort | Higher: ~2.8k PDF downloads + table parser (text-based; template stable-looking but 12 yrs of format drift to handle) | Lower per symbol, but currently hard rate-limited; ID resolution incomplete |
| Maintenance | Low: daily REST capture (JSON) going forward; PDFs only for history | Fragile: rate limits, ToU exposure, silent changes |
| History before 2014-06 | No (feed starts there) | 2012→ for indices; per-stock depth unknown |

## 4. Recommendation: **NGX becomes the primary source.**

The exchange archive dominates on every research-critical dimension:
survivorship, PIT integrity, value-traded/deals, confidence, and control over
adjustments. The only investing.com advantages — lower parsing effort and
possibly deeper pre-2014 history — do not outweigh a 0.9-vs-0.5 confidence
gap and structural survivorship cleanliness, especially when the vendor is
currently rate-limiting us.

**Retained hybrid elements (narrow, explicit):**
1. investing.com remains the source for **index levels** (already banked,
   anchor-verified) and a **cross-check** for per-stock closes on a sample
   of dates (two-source discipline).
2. If per-stock history before 2014-06 proves necessary, the vendor is the
   only free candidate — a separate decision, deferred.
3. Forward daily capture uses the NGX **REST JSON** (richer + easier than
   PDFs); the PDF archive is for history. Both are exchange-official.

## 5. Roadmap redesign (per directive)

- Task 1 re-scoped: harvest + archive all 2,846 DOL(EQUITIES) PDFs
  (raw-first, permanent) → build the price-sheet parser → ingest to
  equity_prices at confidence 0.9 → coverage dashboard regenerates → gate.
- SHARES OUTSTANDING harvest queued right behind (market-cap/float truth —
  upgrades weights, capacity, and F13 size factors).
- daily capture extended with the statistics/equities JSON endpoint
  (full cross-section incl. Value/Trades) — done as part of this
  investigation's mandate to keep capture uninterrupted.
- investing.com equity backfill: PARKED (not deleted) as fallback/cross-check.
- OCR (tesseract) decision: still pending for corporate-action scans —
  unaffected by this finding (those are scanned; price sheets are not).
