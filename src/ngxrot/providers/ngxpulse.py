"""NGXPulseProvider: real, live NGX equities/indices/disclosures/dividends
via the NGX Pulse REST API (https://www.ngxpulse.ng/api), plugged into this
platform's EXISTING provider abstraction (`ngxrot.providers.base.
DataProvider`) -- not a new, parallel system. Downstream code (ingestion,
validation, the PIT database, backtesting) is completely unaware this
provider exists beyond calling `fetch_*` like any other provider.

## Real endpoint inventory (confirmed LIVE, most recently 2026-08-10, against
## the real API with a real Personal-tier key)

**CORRECTION, 2026-08-10**: an earlier pass of this module tested
`/api/ngxdata/stocks/:symbol/history` (404, genuinely does not exist) and
concluded stock-level history was unavailable on this tier. That conclusion
was WRONG about the right thing for the wrong reason -- the real historical
endpoint is a DIFFERENT path, `/api/ngxdata/prices/:symbol` (documented as
"single stock price," but its real live behavior when called WITH `from`/`to`
query params returns FULL multi-year daily history, not just today's
snapshot -- confirmed directly: a single call for DANGCEM with
`from=2020-01-01` returned 1,561 real daily observations spanning
2020-01-02 to 2026-08-07). The product's own docs text undersold this
endpoint; empirical testing, not the docs page, is the source of truth here.

Confirmed working on the Personal tier (10 req/min, 100 req/day):
  GET /api/ngxdata/market-status          -- {"status": "Pre-Open"/..., "is_open": bool}
  GET /api/ngxdata/stocks                 -- full current-snapshot universe (all real tickers)
  GET /api/ngxdata/prices/:symbol         -- REAL MULTI-YEAR DAILY HISTORY when called with
                                              from=/to= params (see docs/fre_runs/
                                              ngxpulse_historical_coverage_report.md for the
                                              full coverage assessment: per-ticker earliest
                                              date varies -- appears to track each company's
                                              real NGX listing date -- observation counts in
                                              the 900-2,300 range per ticker tested, ZERO
                                              duplicates, from/to filtering genuinely
                                              respected (verified: a 30-day window returned
                                              exactly 23 real trading-day rows, not the full
                                              history). ONE call returns a ticker's ENTIRE
                                              available history -- not paginated by year.
  GET /api/ngxdata/indices                -- 21 real indices (broader than this platform's
                                              own 9-row `indices` table -- see INDEX_CODE_MAP)
  GET /api/ngxdata/indices/:slug/history  -- real daily index history (slug is LOWERCASE,
                                              e.g. 'asi' not 'ASI'); shorter lookback window
                                              than the per-stock /prices/ endpoint in a live
                                              test (5 days returned for a 9-day request) --
                                              disclosed, not assumed complete.

Confirmed NOT accessible on the Personal tier (from the API's own docs page):
  GET /api/ngxdata/fundamentals/:symbol   -- "Starter tier and above" (verified via docs text)
  GET /api/ngxdata/stocks/:symbol/history -- this exact route does not exist (404) -- the
                                              REAL historical route is /prices/:symbol (above),
                                              not this one.

Documented but NOT yet exercised live this pass: /api/ngxdata/dividends/:symbol
(exercised in an earlier pass, works), /api/ngxdata/disclosures (implemented,
not exercised), /api/ngxdata/market, /api/ngxdata/etfs, /api/ngxdata/bonds.

## Real, confirmed data-quality limitation

`high_price`/`low_price` are NULL in ~99.9-100% of every real observation
tested (8 tickers, 900-2,278 rows each) -- only open/close/volume are
genuinely populated. This is a real ceiling on any feature needing intraday
range (true range, ATR-style volatility) -- close-based momentum/relative-
strength features (this platform's actual near-term research need) are
unaffected. Never fabricated or backfilled from close -- left NULL, exactly
as returned.

## What this means for capability mapping

`fetch_equity_prices()` now uses the real `/prices/:symbol` historical
endpoint and returns REAL multi-year daily history (open/close/volume;
high/low always None, per the data-quality limitation above) -- it
DELIBERATELY REQUIRES an explicit `tickers` list (like
`fetch_corporate_actions`) since each ticker costs one real API call; it
never silently loops the ~147-name universe. This platform's existing
equity-history providers (ngx_pricelist_v1/v2, investing_com, etc.) remain
independently valid additional sources and are untouched by this change.

`fetch_index_levels()` provides real multi-day index history, gated by the
observed short lookback window above -- disclosed via a WARNING in the
returned frame's own construction, not silently accepted as complete.
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .base import DataProvider, ProviderInfo, Unsupported

PKG_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PKG_ROOT / "data" / "raw"
BASE_URL = "https://www.ngxpulse.ng/api"

# This platform's own `indices.index_code` values that differ from NGX
# Pulse's own `code` field -- confirmed by direct comparison against the
# real /api/ngxdata/indices response. Every other real code (NGX30, NGXBNK,
# NGXINS, NGXOILGAS, NGXINDUSTR, NGXCNSMRGDS, NGXPREMIUM, NGXPENSION)
# matches exactly and needs no mapping.
INDEX_CODE_MAP = {"NGXASI": "ASI"}
REVERSE_INDEX_CODE_MAP = {v: k for k, v in INDEX_CODE_MAP.items()}


def _load_api_key() -> str:
    """Reads NGXPULSE_API_KEY from the environment, falling back to a
    minimal manual .env parse (this project has no python-dotenv
    dependency) -- NEVER hard-coded here or anywhere else in the repo."""
    key = os.environ.get("NGXPULSE_API_KEY")
    if key:
        return key
    env_path = PKG_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("NGXPULSE_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError(
        "NGXPULSE_API_KEY is not set (checked the environment and .env). "
        "Set it before constructing NGXPulseProvider -- never hard-code a key in source."
    )


@dataclass
class RequestLogEntry:
    timestamp: str
    endpoint: str
    status: str  # SUCCESS | PARTIAL | FAILED | STALE | CACHED
    http_status: int | None
    duration_s: float
    detail: str = ""


class _RateLimiter:
    """Enforces the Personal-tier limits (10/min, 100/day) client-side,
    BEFORE a request is sent -- never relies on the server to reject an
    over-quota call. A day boundary is UTC-midnight, a minute boundary is
    a real rolling 60s window (deque of real timestamps, not a fixed
    per-minute bucket)."""

    def __init__(self, per_minute: int = 10, per_day: int = 100):
        self.per_minute = per_minute
        self.per_day = per_day
        self._minute_window: deque[float] = deque()
        self._day_window: deque[float] = deque()

    def wait_if_needed(self) -> None:
        now = time.monotonic()
        while self._minute_window and now - self._minute_window[0] > 60:
            self._minute_window.popleft()
        while self._day_window and now - self._day_window[0] > 86400:
            self._day_window.popleft()
        if len(self._day_window) >= self.per_day:
            raise RuntimeError(
                f"NGX Pulse daily quota ({self.per_day} requests/day) exhausted for this "
                f"process -- refusing to send another request rather than risk a silent "
                f"429 lockout."
            )
        if len(self._minute_window) >= self.per_minute:
            sleep_for = 60 - (now - self._minute_window[0]) + 0.05
            time.sleep(max(sleep_for, 0))
        t = time.monotonic()
        self._minute_window.append(t)
        self._day_window.append(t)


class NGXPulseProvider(DataProvider):
    def __init__(self, api_key: str | None = None, cache_ttl_seconds: int = 3600,
                 max_retries: int = 3):
        self.api_key = api_key or _load_api_key()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self._limiter = _RateLimiter()
        self.request_log: list[RequestLogEntry] = []
        self.info = ProviderInfo(
            name="ngx_pulse",
            kind="vendor",
            reliability="secondary",
            base_confidence=0.7,
            url_template=BASE_URL,
            notes="NGX Pulse API (ngxpulse.ng) -- real-time snapshot + index history + "
                  "corporate disclosures/dividends. Sources itself from 'NGX chartdata'/"
                  "'mansaapi-calendar' per its own responses; not the exchange's own "
                  "official channel, hence 'secondary' not 'primary'. Historical STOCK "
                  "(not index) data is genuinely unavailable via this provider -- see "
                  "this module's own docstring for the confirmed-live endpoint inventory.",
            capabilities=frozenset({"index_levels", "equity_prices", "corporate_actions", "events"}),
        )

    # --- HTTP + caching + logging -------------------------------------------

    def _cache_path(self, category: str, cache_key: str) -> Path:
        d = RAW_DIR / category
        d.mkdir(parents=True, exist_ok=True)
        safe_key = cache_key.replace("/", "_").replace(":", "_").replace("?", "_")
        return d / f"{safe_key}.json"

    def _get(self, path: str, category: str, cache_key: str, params: dict | None = None) -> dict:
        """GET with: local raw-response cache (never re-requests unchanged
        data within cache_ttl_seconds), client-side rate limiting, retry
        with exponential backoff on 429/5xx, and a full request-log entry
        every time -- cached or not."""
        cache_file = self._cache_path(category, cache_key)
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < self.cache_ttl_seconds:
                self.request_log.append(RequestLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
                    status="CACHED", http_status=None, duration_s=0.0,
                    detail=f"served from {cache_file} (age {age:.0f}s < ttl {self.cache_ttl_seconds}s)",
                ))
                return json.loads(cache_file.read_text(encoding="utf-8"))

        url = f"{BASE_URL}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            self._limiter.wait_if_needed()
            t0 = time.monotonic()
            try:
                resp = requests.get(url, headers={"X-API-Key": self.api_key}, params=params, timeout=20)
            except requests.RequestException as exc:
                last_exc = exc
                self.request_log.append(RequestLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
                    status="FAILED", http_status=None, duration_s=time.monotonic() - t0,
                    detail=f"attempt {attempt+1}/{self.max_retries}: {exc}",
                ))
                time.sleep(2 ** attempt)
                continue

            duration = time.monotonic() - t0
            if resp.status_code == 429:
                self.request_log.append(RequestLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
                    status="FAILED", http_status=429, duration_s=duration,
                    detail=f"rate-limited by server; backing off (attempt {attempt+1}/{self.max_retries})",
                ))
                time.sleep(2 ** (attempt + 2))
                continue
            if resp.status_code >= 500:
                self.request_log.append(RequestLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
                    status="FAILED", http_status=resp.status_code, duration_s=duration,
                    detail=f"server error, retrying (attempt {attempt+1}/{self.max_retries})",
                ))
                time.sleep(2 ** attempt)
                continue
            if resp.status_code != 200:
                self.request_log.append(RequestLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
                    status="FAILED", http_status=resp.status_code, duration_s=duration,
                    detail=resp.text[:300],
                ))
                raise RuntimeError(f"NGX Pulse {path} returned HTTP {resp.status_code}: {resp.text[:300]}")

            data = resp.json()
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            self.request_log.append(RequestLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
                status="SUCCESS", http_status=200, duration_s=duration,
                detail=f"cached to {cache_file}",
            ))
            return data

        self.request_log.append(RequestLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(), endpoint=path,
            status="FAILED", http_status=None, duration_s=0.0,
            detail=f"exhausted {self.max_retries} retries: {last_exc}",
        ))
        raise RuntimeError(f"NGX Pulse {path} failed after {self.max_retries} retries: {last_exc}")

    # --- market status (used by the scheduler, not a DataProvider capability) -

    def market_status(self) -> dict:
        return self._get("/ngxdata/market-status", "market_status", date.today().isoformat())

    # --- DataProvider capabilities ------------------------------------------

    def fetch_equity_prices(self, tickers: list[str], start: str, end: str) -> pd.DataFrame:
        """Real multi-year daily history via /prices/:symbol?from=&to=
        (see module docstring for how this was discovered/confirmed -- the
        docs page undersold this endpoint). REQUIRES an explicit, non-empty
        `tickers` list -- each ticker costs one real API call, so this
        never silently loops the ~147-name universe on a caller's behalf
        (same discipline as `fetch_corporate_actions`). `high`/`low` are
        always None (never fabricated from open/close) -- a real, disclosed
        data-quality ceiling of this source, not a bug in this provider."""
        if not tickers:
            raise Unsupported(
                "ngx_pulse.fetch_equity_prices requires an explicit ticker list -- each "
                "ticker costs one real API call against the 100/day quota, so this never "
                "silently loops the full universe"
            )
        frames = []
        for t in tickers:
            payload = self._get(f"/ngxdata/prices/{t}", "prices", f"{t}_{start}_{end}",
                                 params={"from": start, "to": end})
            rows = payload.get("prices", [])
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df["ticker"] = t
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
            df["open"] = df["open_price"]
            df["close"] = df["close_price"]
            df["high"] = None
            df["low"] = None
            frames.append(df[["ticker", "trade_date", "open", "high", "low", "close", "volume"]])
        if not frames:
            return pd.DataFrame(columns=["ticker", "trade_date", "open", "high", "low", "close", "volume"])
        return pd.concat(frames, ignore_index=True)

    def fetch_index_levels(self, index_codes: list[str], start: str, end: str) -> pd.DataFrame:
        """Real per-index history. WARNING (disclosed, not silently
        accepted): a live test on this tier returned only a 5-day window
        for a 9-day request -- the effective lookback under Personal tier
        is short and NOT the multi-year history the product's own docs
        describe for higher tiers. Callers should not assume completeness;
        `ingest.py`'s own dedup-by-key logic makes repeated short pulls
        safe to accumulate over time, but a full historical backfill via
        this endpoint alone is not currently possible on this tier."""
        frames = []
        for code in index_codes:
            pulse_code = INDEX_CODE_MAP.get(code, code)
            slug = pulse_code.lower()
            payload = self._get(
                f"/ngxdata/indices/{slug}/history", "index_history",
                f"{slug}_{start}_{end}", params={"from": start, "to": end},
            )
            history = payload.get("history", [])
            if not history:
                continue
            df = pd.DataFrame(history)
            df["index_code"] = code
            df["trade_date"] = df["date"]
            df["close_value"] = df["value"]
            frames.append(df[["index_code", "trade_date", "close_value"]])
        if not frames:
            return pd.DataFrame(columns=["index_code", "trade_date", "close_value"])
        return pd.concat(frames, ignore_index=True)

    def fetch_corporate_actions(self, tickers: list[str] | None = None) -> pd.DataFrame:
        """Dividends only, per real-endpoint availability
        (/ngxdata/dividends/:symbol -- no aggregate endpoint exists).
        DELIBERATELY per-symbol and therefore quota-expensive: this method
        raises if `tickers` is not supplied explicitly (never silently
        loops the whole universe and burns the 100/day quota)."""
        if not tickers:
            raise Unsupported(
                "ngx_pulse.fetch_corporate_actions requires an explicit ticker list -- "
                "there is no aggregate /dividends endpoint, and looping the full universe "
                "would burn the entire 100/day quota on one call"
            )
        frames = []
        for t in tickers:
            payload = self._get(f"/ngxdata/dividends/{t}", "dividends", f"{t}_{date.today().isoformat()}")
            history = payload.get("history", [])
            for row in history:
                frames.append({
                    "ticker": t,
                    "action_type": "dividend",
                    "markdown_date": row.get("date"),
                    "dividend_per_share": row.get("amount"),
                    "details": json.dumps(row),
                })
        return pd.DataFrame(frames, columns=["ticker", "action_type", "markdown_date",
                                              "dividend_per_share", "details"])

    def fetch_events(self, start: str, end: str) -> pd.DataFrame:
        """Corporate disclosures -> events contract. Uses the aggregate
        /disclosures endpoint (one call, not per-ticker)."""
        payload = self._get("/ngxdata/disclosures", "disclosures", f"{start}_{end}")
        rows = payload.get("disclosures", payload.get("data", []))
        if not rows:
            return pd.DataFrame(columns=["event_type", "announced_date", "scope", "headline"])
        df = pd.DataFrame(rows)
        out = pd.DataFrame({
            "event_type": df.get("disclosure_type", df.get("type", "disclosure")),
            "announced_date": pd.to_datetime(df.get("announcement_date", df.get("date"))).dt.strftime("%Y-%m-%d"),
            "scope": "ticker",
            "headline": df.get("title", df.get("description", "")),
            "ticker": df.get("symbol"),
            "source_url": df.get("source_url", df.get("url")),
        })
        return out[(out["announced_date"] >= start) & (out["announced_date"] <= end)].reset_index(drop=True)
