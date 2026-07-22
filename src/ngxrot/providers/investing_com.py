"""InvestingComProvider: real NGX index histories from investing.com's
financialdata API (probed working 2026-07-15, no auth, no Cloudflare block).

Confidence 0.5 (aggregator): values match the exchange at verified anchor
dates, but corporate-action/rebase handling and gap policy are undocumented —
hence the mandatory staging validation before ingestion (see ngxrot.staging).

Raw API responses are archived under data/staging/investing_com/ so every
ingested row can be traced back to the exact payload it came from.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from .base import DataProvider, ProviderInfo

PKG_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PKG_ROOT / "data" / "staging" / "investing_com"

# instrument id on investing.com -> our index_code (probed 2026-07-15)
INSTRUMENTS = {
    "NGXASI":      (101796, "NGSEINDEX"),
    "NGX30":       (101797, "NGSE30"),
    "NGXINS":      (101798, "NGSEINS10"),
    "NGXOILGAS":   (101800, "NGSEOILG5"),
    "NGXBNK":      (101801, "NGSEBNK10"),
    "NGXCNSMRGDS": (1131167, "NGNSECG"),
    "NGXPENSION":  (1191875, "NGSEPENSION"),
    "NGXINDUSTR":  (1191876, "NGSEINDUS"),
    # NGXPREMIUM: not carried by investing.com — documented coverage gap
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
    "domain-id": "www",
}
_API = "https://api.investing.com/api/financialdata/historical/{id}"


EQUITY_IDS_PATH = PKG_ROOT / "data" / "reference" / "investing_equity_ids.csv"


class InvestingComProvider(DataProvider):
    def __init__(self, request_pause_s: float = 1.0):
        self.pause = request_pause_s
        self.info = ProviderInfo(
            name="investing_com", kind="vendor", reliability="secondary",
            base_confidence=0.5,
            url_template=_API,
            notes="aggregator; adjustment policy undocumented; staging "
                  "validation mandatory before ingest",
            capabilities=frozenset({"index_levels", "equity_prices"}),
        )

    def _fetch_chunk(self, inst_id: int, start: str, end: str,
                     retries: int = 3) -> list[dict]:
        for attempt in range(retries):
            r = requests.get(_API.format(id=inst_id),
                             params={"start-date": start, "end-date": end,
                                     "time-frame": "Daily",
                                     "add-missing-rows": "false"},
                             headers=_HEADERS, timeout=40)
            if r.status_code in (403, 429) and attempt < retries - 1:
                time.sleep(45 * (attempt + 1))   # rate-limit backoff
                continue
            r.raise_for_status()
            return r.json().get("data") or []
        return []

    def fetch_equity_prices(self, tickers, start, end) -> pd.DataFrame:
        """Per-stock daily bars using the resolved NGX-symbol -> instrument-id
        map (built by scripts/backfill_equities.py). value_traded left NULL —
        vendor provides volume only; naira turnover is NOT fabricated."""
        ids = pd.read_csv(EQUITY_IDS_PATH).set_index("symbol")
        frames = []
        years = pd.date_range(start, end, freq="3YS").strftime("%Y-%m-%d").tolist()
        bounds = list(zip([start] + years[1:], years[1:] + [end])) or [(start, end)]
        for t in (tickers or list(ids.index)):
            if t not in ids.index:
                continue
            rows: list[dict] = []
            for a, b in bounds:
                if a >= b:
                    continue
                rows.extend(self._fetch_chunk(int(ids.loc[t, "inst_id"]), a, b))
                time.sleep(self.pause)
            if not rows:
                continue
            frames.append(pd.DataFrame({
                "ticker": t,
                "trade_date": [r["rowDateTimestamp"][:10] for r in rows],
                "close": [float(r["last_closeRaw"]) for r in rows],
                "open": [float(r.get("last_openRaw") or 0) or None for r in rows],
                "high": [float(r.get("last_maxRaw") or 0) or None for r in rows],
                "low": [float(r.get("last_minRaw") or 0) or None for r in rows],
                "volume": [int(r.get("volumeRaw") or 0) for r in rows],
            }))
        if not frames:
            return pd.DataFrame(columns=["ticker", "trade_date", "close"])
        return (pd.concat(frames, ignore_index=True)
                .drop_duplicates(subset=["ticker", "trade_date"])
                .sort_values(["ticker", "trade_date"], ignore_index=True))

    def fetch_index_levels(self, index_codes, start, end) -> pd.DataFrame:
        codes = [c for c in (index_codes or list(INSTRUMENTS))
                 if c in INSTRUMENTS]
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        frames = []
        # chunk by ~3 years to stay under response-size limits
        years = pd.date_range(start, end, freq="3YS").strftime("%Y-%m-%d").tolist()
        bounds = list(zip([start] + years[1:], years[1:] + [end])) or [(start, end)]
        for code in codes:
            inst_id, symbol = INSTRUMENTS[code]
            rows: list[dict] = []
            for a, b in bounds:
                if a >= b:
                    continue
                rows.extend(self._fetch_chunk(inst_id, a, b))
                time.sleep(self.pause)
            (RAW_DIR / f"{code}_{date.today().isoformat()}.json").write_text(
                json.dumps(rows), encoding="utf-8")
            if not rows:
                continue
            df = pd.DataFrame({
                "index_code": code,
                "trade_date": [r["rowDateTimestamp"][:10] for r in rows],
                "close_value": [float(r["last_closeRaw"]) for r in rows],
            })
            frames.append(df)
        if not frames:
            return pd.DataFrame(columns=["index_code", "trade_date", "close_value"])
        out = (pd.concat(frames, ignore_index=True)
               .drop_duplicates(subset=["index_code", "trade_date"])
               .sort_values(["index_code", "trade_date"], ignore_index=True))
        return out[(out.trade_date >= start) & (out.trade_date <= end)]
