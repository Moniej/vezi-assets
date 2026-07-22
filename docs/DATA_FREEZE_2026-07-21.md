# Data Freeze — 2026-07-21 (Coverage Gate v2 PASS)

The Coverage Gate passed on 2026-07-21 with **12 ready years (2015–2026)**,
no threshold changes. This document freezes the research dataset state.

## Freeze mechanism

The bitemporal PIT store is the freeze: research readers
(`db.equity_prices_asof` et al.) pin `vintage = '2026-07-21'`.
H-006 / H-007 pre-registrations MUST set:

- `data.vintage_date = "2026-07-21"`
- `data.requires_coverage_gate = true`
- `universe.iru_version = "v2"`

Later captures/restatements land under later `as_of_date`s and are invisible
at this vintage. Nothing is deleted; nothing needs to be.

## Frozen state (conf >= 0.9)

| source | rows | days | note |
|---|---|---|---|
| ngx_pricelist_v1 | 301,511 | 2,763 | OHLCV+value+deals; PDF-vs-REST 100% (V3) |
| ngx_dol_v1 | 17,947 | 170 | close-only gap recovery; 99.44% validated; volume/value NULL by design |
| ngx_list2_v1 | 753 | 7 | close/volume/deals; 100%/99.9% validated |
| **total** | **320,159** | **2,933 distinct** | 308 tickers, 2014-06-30 → 2026-07-21 |

Gate detail: `data/coverage_gate.json` + `reports/data_coverage_dashboard.md`
(day-completeness 95.1–100% every full year 2015–2026; IRU jump rate ≤ 2%
every ready year).

## Reference calendars produced by the remediation (frozen alongside)

- `data/reference/exdiv_closure_calendar.csv` — 1,044 closure-of-register
  events, 217 symbols (DOL ex-div band, char-level parser).
- `data/reference/gainers_transitions.csv` — 138,001 official mover rows /
  2,801 transitions incl. 5,338 officially adjusted bases (markdown ledger).
- `data/reference/official_prev_close.csv` — PCLOSE (officially adjusted
  base) per symbol-day for 2,763 pricelist days.
- `data/staging/xissuer/earnings_calendar.csv` — 10,690 filings, 245 symbols.

## Jump-scan evidence hierarchy (final)

A session-adjacent |move| > 12% is UNEXPLAINED only if none of:
(a) it spans a verified market day our panel lacks (index value-change
calendar); (b) NGX's own records certify a within-band move off an
officially adjusted base (Gainers/Losers report OR PRICES1 PCLOSE);
(c) closure-of-register or earnings filing within ±3 business days.
Residual unexplained: 116 flags, ALL in non-equities (ETFs/sukuk — outside
the equity band's premise and outside the IRU). Equity residue: 3 flags in
12 years (CILEASING, IMG, LASACO — single occurrences).

## Known, documented limitations at this vintage

1. **Single-source days**: the 177 recovered days have no second NGX
   publication; flagged per-day in `data_quality_log`
   (`single_source_day`). Intraday-print risk ≈ 1.7% of DOL days with
   ≤ ~3% close deviation on a subset of symbols (observed 2022-03-16, an
   overlap day NOT in the ingest set).
2. DOL-sourced days carry close only (volume NULL) — DOL 'Qty' is the last
   trade's size, not daily volume; it was never ingested.
3. 2017-07-25 is unrecoverable (gainers-only zip, no DOL) — 2017 passes
   without it. 2014 is a partial year (coverage starts 2014-06-30).
4. `vwap_inconsistent` (D4b, warn): 469 rows where value/volume is far from
   close — informational backlog, not a gate input.
5. 49 candidate symbol renames remain unverified/unapplied
   (`data/reference/symbol_renames.csv`).
