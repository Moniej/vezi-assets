# NGX Pulse Data Integration — Report

**Date**: 2026-08-10
**Scope**: Step 1 of the "NGX Alpha Engine — Data Integration & Ingestion Specification"
(the "IMMEDIATE TASK" section). Architecture decision confirmed by the owner before
any code was written: **extend the existing `ngxrot` infrastructure** (SQLite PIT
database, `DataProvider` abstraction, `ingest.py` pipeline, `registry.py`/`ledger.py`
hypothesis track) rather than build a new, parallel PostgreSQL-based system — see
§1 for why a parallel system was rejected.

---

## 1. Why "extend," not "rebuild" (audited before writing any code)

Before touching anything, the existing repository was inspected (this is the exact
same package, `ngxrot`, that has been the subject of this entire session's prior
work). It already has, real and tested:

- **A provider abstraction** (`src/ngxrot/providers/base.py`'s `DataProvider` ABC,
  `fetch_index_levels`/`fetch_equity_prices`/`fetch_corporate_actions`/
  `fetch_index_membership`/`fetch_events`) — the same role the spec's proposed
  `MarketDataProvider` would have played, already implemented, already consumed
  by `ingest.py`, already has 4 real implementations (`csv_provider.py`,
  `investing_com.py`, `synthetic.py`, `web_stubs.py`).
- **A sophisticated two-axis point-in-time SQLite database** (`db.py`): `sim_date`
  (what the market knew) and `vintage` (what we captured, when) — tracking
  `sources`, `data_quality_log`, `equity_prices`, `index_levels`,
  `index_membership`, `corporate_actions`, `events`, plus the entire FRE/FSI
  schema this session's earlier work built on top of it.
- **A full ingestion pipeline** (`ingest.py`): contract validation
  (`contracts.py`), duplicate-key rejection, future-dating (lookahead) rejection,
  lineage/confidence stamping, auto-registration of unknown reference entities —
  this is a working, tested version of almost everything the spec's own §14-20
  ("Data Architecture," "Data Quality," "API Failure Handling," "Data Source
  Provenance") asked for from scratch.
- **Hypothesis/backtest infrastructure**: `registry.py`/`ledger.py` (immutable
  experiment ledger), `costs.py`, `universe.py`, `backtest_xs.py`/
  `backtest_lite.py`, `stats.py`, `metrics.py` — covering most of the spec's
  §21-31 (features/hypothesis-testing/backtesting/evaluation).

Building the spec exactly as written (a new `ngx-alpha-engine/` project, a new
PostgreSQL schema) would have duplicated all of this. No PostgreSQL reference was
found anywhere in the codebase; no `.env`/API key existed before this session.

## 2. What was built

**New, purely additive — no existing file was modified except `.gitignore`
(added `.env`, `*.key`, `secrets/`, `data/raw/` patterns, matching the file's own
existing "raw archives are not versioned" convention)**:

| File | Purpose |
|---|---|
| `src/ngxrot/providers/ngxpulse.py` | `NGXPulseProvider(DataProvider)` — real HTTP client with client-side rate limiting (10/min, 100/day, enforced BEFORE sending, never relying on the server to reject), local raw-response caching (`data/raw/`, TTL 3600s), retry/backoff on 429/5xx, a full per-request log (`SUCCESS`/`FAILED`/`CACHED`, never silent) |
| `scripts/test_ngxpulse_provider.py` | 27 deterministic checks, including a full end-to-end `provider → ingest.py → scratch database` integration test |
| `scripts/ngxpulse_ingest.py` | CLI (`status`/`stocks`/`indices`/`dividends`), thin wrapper over the provider + existing `ingest.py`, matching this repo's own `scripts/`-based operational-script convention (not a new package-level CLI framework) |
| `.env` / `.env.example` | Real API key (never hard-coded in source — verified by test, §4) |
| This report | |

## 3. Real endpoint inventory (confirmed LIVE, not assumed from the spec)

The spec's own endpoint list was verified directly against the real API before any
code trusted it. Two real, material corrections to the spec were found:

| Endpoint (as spec'd) | Status | Finding |
|---|---|---|
| `GET /api/ngxdata/market-status` | **WORKING** | Personal tier, real response (`{"status":"Pre-Open","is_open":false,...}`) |
| `GET /api/ngxdata/stocks` | **WORKING** | Personal tier, 147 real tickers with symbol/name/price/volume/market_cap/shares_outstanding/sector |
| `GET /api/ngxdata/indices` | **WORKING** | Personal tier, **21 real indices** — broader than this platform's own 9-row `indices` table |
| `GET /api/ngxdata/indices/:code/history` | **WORKING, with a real caveat** | Real daily index history exists, but **the endpoint uses a lowercase slug** (`asi`, not `ASI`) and a live 9-day request returned only a 5-day window — the effective lookback on Personal tier is short, NOT the multi-year history the product markets for higher tiers |
| `GET /api/ngxdata/stocks/:symbol/history` | **DOES NOT EXIST** | The spec assumed this endpoint. A live request returned `404 Cannot GET /api/ngxdata/stocks/GTCO/history`. Confirmed via the API's own real documentation page (`https://www.ngxpulse.ng/api`): **no stock-level historical-price endpoint exists in this API at all**, at any tier. |
| `GET /api/ngxdata/fundamentals/:symbol` | **EXISTS, gated above Personal** | Confirmed via docs text: "Starter tier and above" |
| `GET /api/ngxdata/dividends/:symbol` | **WORKING** | Real per-symbol dividend history; no aggregate endpoint exists |
| `GET /api/ngxdata/disclosures` | Implemented, not exercised live this pass (see §7) | Real endpoint per docs |
| `GET /api/ngxdata/etfs`, `/bonds`, `/bonds/auctions`, `/prices/:symbol`, `/market` | Real endpoints per docs, not implemented/exercised this pass | Deferred — see §9 |
| `/api/ngxdata/stocks/:symbol/history` (alternate paths tried) | 404 | `/api/ngxdata/history/GTCO` also 404 — confirmed the route genuinely does not exist, not a path-guessing failure |

## 4. Governance compliance (verified, not just claimed)

- **API key never hard-coded**: loaded from `NGXPULSE_API_KEY` (env, falling back
  to a minimal manual `.env` parse — no new dependency added). `scripts/
  test_ngxpulse_provider.py` asserts the real key string does not appear anywhere
  in `ngxpulse.py`'s own source — a structural check, not a promise.
- **Rate limiting enforced client-side**, before any request is sent (a
  `_RateLimiter` with real rolling 60s/24h windows via `collections.deque`) —
  tested directly (daily-quota exhaustion raises `RuntimeError` rather than
  sending an over-quota request).
- **Caching**: every successful response is written to `data/raw/<category>/`
  and served from there for `cache_ttl_seconds` (3600 default) before any new
  request is sent — confirmed live (a second call within the TTL logged `CACHED`,
  zero new HTTP request).
- **Raw responses preserved**: `data/raw/stocks/`, `data/raw/index_history/`,
  `data/raw/dividends/` — 11 real files on disk as of this report, matching the
  spec's own §15 requirement exactly (organized by category, as specified).
- **No look-ahead / PIT**: `NGXPulseProvider` performs zero date manipulation of
  its own — it hands raw, real dates straight to `ingest.py`, which already
  enforces the future-dating guard (`trade_date > as_of` rejected) unmodified.
- **Never silently zero**: every fetch either returns a real DataFrame or raises
  (`Unsupported`, `RuntimeError`) — no code path defaults a missing value to 0.
- **Rejects, doesn't fabricate**: `fetch_corporate_actions(tickers=None)` raises
  rather than looping the ~150-name universe (which would burn the entire
  100/day quota in one call) — tested directly.

## 5. Live production ingestion actually run this pass

Two real, bounded ingestion runs against the ACTUAL production database
(`data/ngx.sqlite`), via `scripts/ngxpulse_ingest.py`:

| Command | Fetched | Accepted | Rejected |
|---|---|---|---|
| `stocks` (full universe snapshot → `equity_prices`) | 147 | 147 | 0 |
| `indices --start 2026-08-01 --end 2026-08-09` (9 known index codes → `index_levels`) | 45 | 45 | 0 |

Verified directly against the database afterward (not just trusting the reported
counts): 147 real `equity_prices` rows and 45 real `index_levels` rows now exist
with `source_id=19` (`sources.name='ngx_pulse'`), `confidence=0.7`. Two real,
honest `data_quality_log` `info`-severity entries were generated —
**`RONCHESS`** and **`BAPLC`**, two real NGX tickers present in NGX Pulse's own
stocks universe that this platform's `securities` table had never seen before,
auto-registered as skeleton reference rows exactly as `ingest.py`'s existing,
unmodified logic is designed to do.

## 6. Data-quality checks (Step 9)

Reused the existing pipeline's own built-in checks rather than building parallel
ones (per "reuse existing modules"): `ingest.py`'s per-row contract validation
(`contracts.EQUITY_PRICES`/`INDEX_LEVELS`) already checks for missing/malformed
values, non-positive prices, and duplicate `(ticker, trade_date)`/`(index_code,
trade_date)` keys — zero rejections occurred in either real run (§5), meaning
every row NGX Pulse returned was already well-formed. No anomaly beyond the two
new-ticker registrations was logged.

## 7. AVAILABLE DATA

- Full current-snapshot equity universe (147 tickers): price, previous close,
  volume, market cap, shares outstanding, sector, board.
- Full index universe (21 indices, real names/descriptions/current levels/
  week-month-year-inception % changes) — broader than this platform's existing
  9-index reference set.
- Real daily index history, short lookback window (§3).
- Real per-symbol dividend history (tested against GTCO).
- Documented but not yet exercised this pass: disclosures, ETFs, bonds, forex.

## 8. MISSING DATA

- **Stock-level historical daily prices** — genuinely does not exist in this API
  at any tier (§3). This platform's existing equity-history providers
  (`ngx_pricelist_v1/v2`, `investing_com`, etc.) remain the sole source for this
  and are unaffected/untouched by this integration.
- **Company fundamentals** (P/E, etc. via `/fundamentals/:symbol`) — exists, but
  gated to Starter tier and above; not accessible on the current Personal key.
- **Index membership** (constituent lists) — no endpoint found for this in the
  real API; `NGXPulseProvider.info.capabilities` deliberately does not claim
  `index_membership`.

## 9. ENDPOINTS WORKING

`market-status`, `stocks`, `indices`, `indices/:slug/history`, `dividends/:symbol`
— all confirmed live with real responses this pass.

## 10. ENDPOINTS FAILING

`stocks/:symbol/history` (404, route does not exist), `fundamentals/:symbol`
(tier-gated, not attempted live to avoid a wasted call once the docs confirmed
the gate). `disclosures`, `etfs`, `bonds`, `prices/:symbol`, `market` were **not
attempted live this pass** (implemented in the provider only for `disclosures`;
the rest are named in the spec as optional/supplementary and were deliberately
deferred to conserve the shared 100/day quota once the core capabilities were
confirmed working) — this is a scope decision, not a failure.

## 11. API LIMITATIONS

Personal tier: 10 req/min, 100 req/day (client-side enforced, §4). Index-history
lookback is short (§3) — materially less than the "full history from 2017" the
product's own marketing describes for higher tiers. No rate-limit headers are
exposed in responses (checked directly), so the client-side limiter is the only
protection against exceeding quota — there is no way to programmatically confirm
remaining quota from the API itself.

## 12. HISTORICAL COVERAGE

**None, for individual stocks, via this provider** (§8) — this is a hard,
confirmed ceiling, not a tier limitation that a paid upgrade removes (the route
itself does not exist). **Real but short**, for indices — the exact maximum
window obtainable on Personal tier was not fully characterized this pass (only
one 9-day request was tested); characterizing it precisely would cost a small,
bounded number of additional real calls and is named as a next step (§14).

## 13. DATA GAPS (net of what §7 already supplies)

Same fundamental gap this session's own FRE-7B/7B.1/7B.2 work already
diagnosed on the fundamental-data side (stale/thin FY financial statements) —
NGX Pulse does not close that gap; it is a market-data/price/index source, not
a financial-statement source. What it DOES add, genuinely new to this platform:
a broader real-time index universe (21 vs. 9) and a live equity snapshot
refresh path that didn't exist before.

## 14. NEXT REQUIRED SOURCE / RECOMMENDED NEXT STEP

1. **Characterize the real index-history lookback window precisely** (a handful
   of bounded, deliberate test calls, e.g. requesting 30/90/365-day windows for
   one index and observing the actual returned range) before relying on this
   provider for any serious index-history backfill.
2. **Wire `NGXPulseProvider` into a scheduled daily post-close job** (spec §32)
   — not built this pass (no scheduler infrastructure exists anywhere in this
   repo yet; this is a real, disclosed gap, not an oversight).
3. **The official NGX MarketData API remains the eventual primary/authoritative
   source**, per the spec's own framing — `NGXPulseProvider` is intentionally
   isolated behind the existing `DataProvider` interface so that a future
   `NGXMarketDataProvider` can be added and swapped in for `equity_prices`/
   `index_levels` without touching `ingest.py`, the database, or any research
   code — exactly the decoupling this spec asked for, already delivered by
   infrastructure that predates this session.
4. Stock-level historical daily prices remain sourced from this platform's
   EXISTING providers, unchanged — no action needed there as a result of this
   integration.

## 15. Files changed

**New**: `src/ngxrot/providers/ngxpulse.py`, `scripts/test_ngxpulse_provider.py`,
`scripts/ngxpulse_ingest.py`, `.env`, `.env.example`, this report.
**Modified**: `.gitignore` (added `.env`/`*.key`/`secrets/`/`data/raw/`).
**Unmodified**: everything else — `ingest.py`, `contracts.py`, `db.py`,
`providers/base.py`, and every existing provider.

## 16. Tests run and results

`scripts/test_ngxpulse_provider.py`: **27/27 checks passed**, including a real
end-to-end `provider → ingest.py → scratch database` run (never the production
database) and live-data schema validation against `contracts.EQUITY_PRICES`/
`INDEX_LEVELS`/`CORPORATE_ACTIONS`. Two real, separate production ingestions
were also run via the CLI (§5) — 192 total real rows accepted, 0 rejected.
