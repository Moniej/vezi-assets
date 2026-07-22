# NGX Price-Data Pipeline — Completion Report (2026-07-17)

## Totals

| Stage | Result |
|---|---|
| DOL(EQUITIES) PDFs archived | **2,827 / 2,846** (99.3%; failures logged: 1×404, 18 truncated, 9 network — retried once) |
| Pricelist ZIPs archived | **2,840 / 2,854** (99.5%) |
| Days parsed | **2,765** (76 parse failures = 2.7%, logged with reasons) |
| Rows extracted | **304,282** across 2,759 trading days (2014-06-30 → 2026-07-16), 335 symbols |
| Rows ingested @ confidence 0.9 | **300,926 / 308 tickers** (excl. 2,096 low-confidence rows, 815 zero-close rows, dups) |
| Parsing success (row level) | 99.3% of rows at extraction confidence ≥ 0.9; OHLC-sanity flags 0.69% |

## Validation (full detail: reports/pricelist_validation.md)

- **V3 independent implementation** (parsed PDF vs NGX REST JSON, same day,
  134 symbols): close **100%**, trades **100%**, volume/value **99.25%**.
- **V2 continuity** (adjacency-clean): exact match 98.24%,
  markdown-consistent down-gaps 1.06%, suspicious up-gaps **0.70%** (rule ≤1%).
  Methodology audit trail: two pre-ingestion refinements documented (markdown
  decomposition; exclusion of archive-gap-spanning transitions after
  diagnosis showed 28–64% mismatch on gap-spanning vs 1.5% adjacent).
- Pending: investing.com spot-check when vendor rate-limit lifts.

## Coverage by year (symbols with ≥150 obs / any obs)

2016: 71/186 (median 86 obs) · 2020: 87/161 (median 177) · 2025: 127/170
(median 228). Full table: reports/data_coverage_dashboard.md.

## THE GATE DECISION NOW REQUIRED (thresholds may not be loosened unilaterally)

The coverage gate **FAILS** under the pre-set rule (≥70% of filing-active
symbols with ≥150 obs/yr) — and the diagnosis says the rule, not the data,
encodes the wrong question. The archive is near-complete and
validation-clean; what the dashboard revealed is the **market's structure**:
most NGX-listed companies genuinely trade <100 days/year (2016 median: 86).
Those are not missing observations — the exchange's own price list records
only actual trades. A gate demanding 70% of *all filers* trade 150 days/yr
would fail this market forever, regardless of data quality.

**Recommendation to IC** (explicit approval required to change thresholds):
redefine year-readiness around research breadth, which is what the gate
exists to protect (per the pivot memo arithmetic: ~40 effective independent
names): a year is ready when **≥60 symbols have ≥150 observations** and the
unexplained-jump cap holds; overall gate unchanged otherwise (≥6 ready
years incl. 2 most recent). Under that rule 2016 (71), 2020 (87) and 2025
(127) pass on current data. Additionally the filing-universe denominator
should exclude non-equity filers (funds/REITs) — a defect, not a threshold
change.

## Known limitations

1. ~90 trading days absent (catalog gaps + failed downloads + parse
   failures) — listed in `_download_failures.csv` / `_parse_failures.csv`;
   partially recoverable from DOL PDFs (secondary path).
2. Prices are raw as-traded: corporate-action adjustment is OURS to apply
   (by design) — the DOL dividend/ex-date layer (2,827 PDFs, parsed next)
   plus the corporate-actions calendar feed that adjustment layer.
3. Symbol renames (GUARANTY→GTCO, ACCESS→ACCESSCORP…) not yet mapped —
   required before H-006/H-007 universe construction.
4. Thin names have sparse rows because they rarely trade — a market fact
   recorded faithfully, but momentum/PEAD designs must handle it explicitly
   (staleness rules fixed in prereg).
5. 815 zero-close rows excluded (memorandum quotations etc.); 2,096 rows
   below extraction-confidence floor.

## Recommended next actions

1. IC decision on the gate redefinition (above).
2. Symbol-rename mapping table (from filing calendar + DOL names).
3. Parse DOL PDFs for the daily dividend/EPS/ex-date layer (archive already
   complete; text-based).
4. Shares Outstanding harvest (same method) → market-cap/float truth.
5. Then: H-006/H-007 pre-registration — still blocked until the gate passes.
