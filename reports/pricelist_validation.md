# Pricelist Extraction Validation — 2026-07-21

Parser: v1 (word-position method). Source archive:
data/archive/pricelist_zips (2769 parsed days).

## V1 internal
- rows parsed: 534; row_conf >= 0.9: 99.8%
- rows excluded (<0.8 conf): 1
- OHLC-sanity flags: 0.19%

## V2 cross-day continuity (40 most-active symbols; adjacency-clean, markdown-aware)
- adjacency-clean checks (cal_gap 1 or 3): 80; exact match: 98.75%
- DOWN-gaps (markdown-consistent, ex-div/bonus — expected): 1.25%
- UP-gaps (suspicious): 0.00% (pass rule: <= 1%)
- excluded gap-spanning transitions (archive holes/holidays): 40
- Methodology audit trail (both refinements made BEFORE any ingestion):
  (1) raw 97%-match rule mis-scored legitimate ex-dividend markdowns as
  failures — replaced by up/down decomposition; (2) diagnosis showed 28–64%
  mismatch on transitions spanning missing archive days vs 1.5% on adjacent
  days — archive completeness is measured by the coverage dashboard, so V2
  now evaluates parser alignment on adjacency-clean transitions only.

## V3 independent implementation (PDF vs REST JSON, same day)
{
 "trade_date": "2026-07-21",
 "matched_symbols": 134,
 "close_match": 1.0,
 "volume_match": 1.0,
 "value_match": 1.0,
 "trades_match": 1.0
}

## Notes
- Price list contains only securities that TRADED each day (no stale rows).
- Symbols follow NGX conventions incl. renames (GUARANTY->GTCO etc.);
  symbol-mapping handled at research-universe level, not by rewriting rows.
- Pending: investing.com spot-check (vendor currently rate-limiting).
