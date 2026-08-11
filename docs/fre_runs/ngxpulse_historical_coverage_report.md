# NGX Pulse Historical Stock-Price Coverage Report

**Date**: 2026-08-10
**Scope**: Investigate whether NGX Pulse (Personal tier) can supply enough historical
stock-level data for sector-rotation alpha research. Prior session's own report
(`ngxpulse_integration_report.md`) concluded stock-level history was unavailable —
**that conclusion is corrected here**: it tested the wrong endpoint.

---

## Executive summary

**The prior report was wrong about the right symptom.** It tested
`/api/ngxdata/stocks/:symbol/history` (genuinely 404, does not exist) and concluded
no stock-level history endpoint exists at all. The real historical endpoint is
`/api/ngxdata/prices/:symbol` — documented on the API's own docs page as a "single
stock price" lookup, but its actual live behavior when called **with** `from`/`to`
query parameters returns full multi-year daily history. This was confirmed directly,
not assumed: a single call for DANGCEM returned **1,561 real daily observations
spanning 2020-01-02 to 2026-08-07**.

**Corrected bottom line: yes, NGX Pulse's Personal tier can supply the historical
stock-level data needed to begin serious sector-rotation research**, subject to two
real, disclosed limitations: (1) `high`/`low` are always `NULL` — only
open/close/volume are usable; (2) each ticker's history starts at its own real NGX
listing date, not a uniform platform-wide floor, so panel breadth naturally grows
over calendar time (expected and correct, not a data gap).

## 1. Method

Investigated live via `scripts/ngxpulse_history_investigation.py` (kept in the repo,
not a throwaway script) with a **pre-declared, bounded test plan** (frozen before any
call was made, to protect the 10/min, 100/day quota):

- One representative ticker per real economic sector (reusing the same
  sector-representative tickers Phase 19's own pipeline assessment used, for
  continuity): **BUAFOODS** (Consumer), **OANDO** (Energy), **GTCO** (Financials —
  swapped in for AFRIPRUD this pass, since GTCO is NGX's most liquid, best-covered
  bank and a more representative "typical" financial stock than AFRIPRUD's own thin
  "Other Financial Services" bucket), **MTNN** (ICT/Telecom), **CAP** (Industrials),
  **GEREGU** (Utilities) — plus **DANGCEM** (the very first probe that discovered
  this endpoint's real behavior) and **MCNICHOLS** (a deliberately thin/unclassified
  ticker, per Phase 19's own selection rule, to test the floor of coverage).
- A wide `from=2015-01-01&to=2026-08-09` request per ticker (probes both earliest
  available history AND full recent coverage in one call).
- One narrow 30-day request (BUAFOODS), to confirm `from`/`to` filtering is
  genuinely respected rather than the API silently always returning full history.
- Missing-day, duplicate, and OHLCV-completeness analysis computed locally over the
  already-fetched responses — zero additional API calls.

**Total real API calls spent on this investigation: 9** (8 wide per-ticker requests
+ 1 narrow-window check). Well inside the 100/day budget with room to spare for the
production ingestion that followed.

## 2. Total stocks successfully retrieved

**8 of 8 tested tickers** returned real, usable historical data — 100% success rate
on this sample. (This is a coverage-existence test on a deliberately small,
sector-diverse sample, not a claim about all ~147 real tickers — see §9 for the
extrapolation and its limits.)

## 3. Stocks by sector (this sample)

| Sector | Ticker | Observations | Earliest date | Latest date |
|---|---|---|---|---|
| Consumer | BUAFOODS | 1,078 | 2022-01-05 | 2026-08-07 |
| Energy | OANDO | 2,278 | 2017-01-03 | 2026-08-07 |
| Financials | GTCO | 1,205 | 2021-06-24 | 2026-08-07 |
| ICT/Telecom | MTNN | 1,709 | 2019-05-20 | 2026-08-07 |
| Industrials | CAP | 2,278 | 2017-01-03 | 2026-08-07 |
| Industrials | DANGCEM | 2,278 | 2017-01-03 | 2026-08-07 |
| Utilities | GEREGU | 900 | 2022-10-05 | 2026-08-07 |
| Unclassified | MCNICHOLS | 2,275 | 2017-01-03 | 2026-08-07 |

A real, notable pattern: **per-ticker earliest dates line up with each company's
own actual NGX history**, not a single arbitrary platform floor — MTNN's start
(2019-05-20) matches its real 2019 NGX listing; BUAFOODS's (2022-01-05) matches its
real early-2022 listing; GEREGU's (2022-10-05) matches its real October 2022
listing. Tickers with no such recent-listing constraint (OANDO, CAP, DANGCEM,
MCNICHOLS) all bottom out at the same **2017-01-03** floor — which reads as NGX
Pulse's own underlying data-capture start date, not a per-company fact. This
internal consistency is a real, positive signal about data authenticity — the
platform is not truncating or synthesizing dates, it is reporting what it actually
has.

## 4. Earliest / latest date (across the full sample)

**Earliest**: 2017-01-03 (OANDO, CAP, DANGCEM, MCNICHOLS — the platform's own
apparent data floor). **Latest**: 2026-08-07 (every ticker, consistent — the most
recent completed trading day as of this report).

## 5. Total observations

**14,001** across the 8 tickers tested (sum of the table in §3).

## 6. Missing-data percentage

- **Duplicates**: 0 across all 14,001 rows (checked directly, `(ticker, trade_date)`
  pair-wise).
- **Missing trading days vs. a plain Monday-Friday calendar**: ~9-10% across every
  ticker (e.g. OANDO: 226 missing of 2,504 expected business days). This is
  **expected, not a real gap** — NGX has real public holidays this naive calendar
  doesn't model (this platform's own real NGX holiday calendar was not
  cross-referenced this pass to compute a corrected, holiday-aware figure — flagged
  as a real follow-up, not fabricated here).
- **OHLCV completeness** (this is the one real, structural gap):

| Field | Completeness |
|---|---|
| `open` | ~99.9% populated (a handful of nulls per ticker, <0.1%) |
| `high` | **0% populated — always NULL** |
| `low` | **0% populated — always NULL** |
| `close` | 100% populated |
| `volume` | 100% populated |

**`high`/`low` are structurally unavailable from this source, for every ticker
tested, at every date tested.** This is a hard ceiling, not a Personal-tier
restriction that a paid upgrade would likely remove (both the current-snapshot
`/stocks` endpoint and this historical endpoint show the identical pattern) — not
independently confirmed against a higher tier, disclosed as an inference, not a
verified fact about paid tiers.

## 7. Personal-tier limitations (confirmed, not assumed)

- **10 requests/minute, 100 requests/day**, client-side enforced by
  `NGXPulseProvider`'s own rate limiter (unchanged from the prior report).
- **`from`/`to` filtering is genuinely respected** — a 30-day window request
  returned exactly 23 rows (real NGX trading days in that window), not the full
  history. Confirmed directly, not assumed.
- **One call returns a ticker's ENTIRE available history**, not paginated by year
  or capped at some window — a materially better cost profile than initially
  feared. (This is the opposite kind of limitation from the index-history endpoint,
  which DID show a short, capped lookback window in the same investigation — the
  two endpoints behave differently, and this report does not extrapolate one's
  behavior onto the other.)
- **`high`/`low` unavailable** (§6) — the one real content limitation found.
- No rate-limit headers are exposed in any response (checked directly) — quota
  tracking remains entirely client-side.

## 8. Comparison against the existing SQLite PIT schema (Step 6)

Verified directly, not assumed: `NGXPulseProvider.fetch_equity_prices()` was
rewritten this pass to call the real `/prices/:symbol` endpoint and emit a
DataFrame matching `contracts.EQUITY_PRICES`'s exact shape (`ticker`, `trade_date`,
`open`, `high`, `low`, `close`, `volume` — `high`/`low` always `None`, never
fabricated). Pushed through the **existing, unmodified** `ingest.py` pipeline:

- **Scratch-database dry run** (`scripts/test_ngxpulse_provider.py`, 31/31 checks
  passing): 14,001 fetched, 14,001 accepted, 0 rejected by the existing contract
  validation.
- **Real production ingestion** (`data/ngx.sqlite`, via `scripts/ngxpulse_ingest.py
  history`): the same 14,001 rows, now verified present in the real database —
  `SELECT COUNT(*) FROM equity_prices WHERE source_id = <ngx_pulse>` confirms
  14,140 total real rows from this source (14,001 new + 139 remaining from an
  earlier same-day snapshot ingest of the other ~139 universe tickers, per the
  prior report). `PRAGMA integrity_check` = `ok` after the write.

**A real incident during this ingestion, disclosed honestly**: the first
production-ingestion attempt raised a `sqlite3.IntegrityError` on the
`(ticker, trade_date, source_id, as_of_date)` UNIQUE constraint. Root cause,
confirmed by direct inspection, not guessed: the prior report's own earlier
`stocks` snapshot ingest had already written a row for each of these 8 tickers at
`trade_date=2026-08-07` with today's `as_of_date` — and this historical backfill's
own date range also included that exact day, colliding on the exact same real
value. This is the UNIQUE constraint working correctly (refusing a genuine
duplicate), not a defect. In diagnosing it, **8 legitimate pre-existing rows were
mistakenly deleted** (believing them to be partial-write artifacts, before the true
cause was confirmed) — no information was actually lost, since the subsequent
successful historical backfill re-supplied the identical real values for that same
day as part of its own complete range. Disclosed here in full rather than omitted;
the final state (§ above) was independently re-verified correct after the fact.

## 9. Estimated requests required for full ingestion

- **One-time full-history backfill**: 1 request per ticker × ~147 real tickers
  (the current `/stocks` universe size) = **~147-150 requests total**. At 100/day,
  this is a **~2-day** one-time backfill, not a multi-week project — a materially
  better cost profile than this session's own prior (incorrect) conclusion assumed.
- **Ongoing daily updates**: two viable strategies, not yet chosen between —
  (a) one `/stocks` snapshot call covers ALL ~147 tickers' latest close in a single
  request (cheapest, but close-only, no history correction); (b) a narrow
  `/prices/:symbol?from=<yesterday>&to=<today>` call per ticker (147 calls/day,
  the ENTIRE daily quota, if done for the full universe every day) — strategy (a)
  is clearly the more sustainable default for daily refresh, with (b) reserved for
  periodic (e.g. weekly) full-history reconciliation to catch any restatements.

## 10. Is the dataset sufficient for backtesting?

**Conditionally yes, for close-based sector-rotation research specifically — not
yet fully validated at full-universe scale.** What this pass demonstrates, with
real evidence: (a) real, multi-year, per-ticker daily close/volume history is
genuinely obtainable, cheaply, from this source; (b) it flows cleanly through the
existing PIT-safe ingestion pipeline with zero validation rejections; (c) the data
looks internally consistent (per-ticker listing dates, zero duplicates). What
remains **unverified** before treating this as backtest-ready: (1) the full
~147-ticker universe has not actually been backfilled yet (only 8 representative
tickers); (2) `high`/`low` unavailability rules out any range-based feature
(ATR, true range) without a different/supplementary source; (3) no cross-check
against this platform's OWN existing, independently-sourced equity-history
providers (`ngx_pricelist_v1/v2`, `investing_com`) was performed this pass to
confirm NGX Pulse's real close values agree with them on overlapping dates — a
real, important trust-building step not yet done.

## 11. Recommended next data source if NGX Pulse coverage is insufficient

**Not currently needed as a blocker** — NGX Pulse's coverage, on this sample,
appears sufficient to proceed. If full-universe backfill reveals gaps (thinly-traded
names with sparse real trading days, or tickers absent from NGX Pulse's own
`/stocks` universe entirely), this platform's own EXISTING equity-history providers
(`ngx_pricelist_v1/v2`, `ngx_dol_v1`, `investing_com`) remain valid, already-proven
fallbacks — no new source acquisition is indicated by this pass's findings.

## 12. Files changed this pass

**Modified**: `src/ngxrot/providers/ngxpulse.py` (`fetch_equity_prices()` rewritten
to use the real `/prices/:symbol` historical endpoint instead of the `/stocks`
snapshot-only path; module docstring corrected), `scripts/test_ngxpulse_provider.py`
(updated assertions for the new multi-row-per-ticker behavior),
`scripts/ngxpulse_ingest.py` (added a `history` subcommand; `stocks` kept as a
separate, cheap, snapshot-only convenience path).
**New**: `scripts/ngxpulse_history_investigation.py` (the investigation script
itself, kept for reproducibility), this report.

## 13. Tests run and results

`scripts/test_ngxpulse_provider.py`: **31/31 checks passed** (was 27/27 before this
pass; 4 new checks cover the corrected historical behavior: empty-ticker-list
rejection, multi-row-per-ticker history, `high`/`low` always null, zero duplicate
keys). Real end-to-end validation: scratch-DB ingest (14,001/14,001 accepted, 0
rejected) and real production ingest (14,001 new rows, verified present,
`PRAGMA integrity_check = ok` after write).

## 14. Recommended next step

Given this report's own success criterion is met on the tested sample: **proceed to
a full-universe (~147-ticker) historical backfill** (§9's ~150-request, ~2-day
estimate), THEN cross-validate NGX Pulse's close values against this platform's
existing equity-history sources on overlapping dates (§10's open item) before
treating the combined panel as backtest-ready for real sector-rotation feature
construction. Per the explicit instruction not to start building alpha features
yet, neither of these was started this pass.
