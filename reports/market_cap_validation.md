# Market-Cap Panel Validation — 2026-07-22

Source: PRICES_LIST2 sector-format price list, 2,843 archived
pricelist zips scanned (657 had no LIST2-format member — mostly
early-era zips with a single combined PDF). Name->ticker resolution via
one per-calendar-year map built from a mid-year DOL (12 maps, not 2,800 —
runtime tradeoff; unmatched names logged, not fatal). Full-issue market
cap as printed (NOT float-adjusted — no shares-outstanding/free-float
dataset exists yet; that remains a separate backlog item).

- rows: 328,023 | symbols: 218 | days: 2,182
- unmatched name instances (not fatal, excluded): 25,488
- date range: 2016-03-16 .. 2026-07-21

## Implied-share-count stability check

market_cap / close = implied share count, which should be near-constant
between corporate actions. Day-over-day jumps > 2%: 1,274
(0.388% of rows).
Of those jumps, occurring within ±10 days of a corporate-actions filing
for that symbol: 29.6%

This is informational (Size-factor input quality), not a gate — it does
not touch equity_prices or the Coverage Gate.
