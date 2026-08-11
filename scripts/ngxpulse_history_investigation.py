"""One-shot, deliberate live investigation of /api/ngxdata/prices/:symbol as
a HISTORICAL endpoint (with from/to query params) -- NOT the same endpoint
this session's prior report tested (that was /api/ngxdata/stocks/:symbol/
history, confirmed 404/nonexistent; this is a DIFFERENT, real, working path).

Bounded, pre-declared test plan (frozen before any call was made, to avoid
open-ended quota burn on a 10/min, 100/day key):
  - 1 ticker per real economic sector (per economic_peer_taxonomy's own
    level1 groups, reusing the SAME representative tickers Phase 19's
    pipeline assessment already used, for continuity): BUAFOODS (Consumer),
    OANDO (Energy), GTCO (Financials -- a real bank, not AFRIPRUD, since
    AFRIPRUD's own sub_industry is a thin "Other Financial Services" proxy
    and GTCO is NGX's most liquid, best-covered bank), MTNN (ICT/Telecom),
    CAP (Industrials), GEREGU (Utilities).
  - For ONE of those tickers (DANGCEM, already probed ad hoc before this
    script ran -- 1 call spent), a wide from=2015-01-01 request to find the
    genuine earliest available date.
  - For ONE ticker, a narrow 30-day request, to confirm the API actually
    respects from/to rather than always returning full history regardless.
  - A duplicate/missing-day/OHLCV-completeness pass over every response
    already fetched -- no extra calls.

  PYTHONPATH=src python scripts/ngxpulse_history_investigation.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import requests  # noqa: E402

from ngxrot.providers.ngxpulse import _load_api_key  # noqa: E402

BASE_URL = "https://www.ngxpulse.ng/api"
API_KEY = _load_api_key()

SECTOR_TICKERS = {
    "Consumer": "BUAFOODS", "Energy": "OANDO", "Financials": "GTCO",
    "ICT/Telecom": "MTNN", "Industrials": "CAP", "Utilities": "GEREGU",
}

# NGX trading holidays are not independently modeled here -- "missing
# trading days" below is measured against a plain Mon-Fri business-day
# calendar, a deliberate over-count (public holidays will show as
# "missing" too) -- disclosed, not corrected, since this platform's real
# NGX holiday calendar was not cross-referenced this pass.


def call(symbol: str, from_date: str | None, to_date: str | None) -> dict:
    params = {}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    t0 = time.monotonic()
    resp = requests.get(f"{BASE_URL}/ngxdata/prices/{symbol}", headers={"X-API-Key": API_KEY},
                         params=params, timeout=30)
    dt = time.monotonic() - t0
    print(f"  GET /prices/{symbol} params={params} -> HTTP {resp.status_code} in {dt:.1f}s")
    resp.raise_for_status()
    return resp.json()


def analyze(symbol: str, payload: dict) -> dict:
    prices = payload.get("prices", [])
    if not prices:
        return {"symbol": symbol, "n_obs": 0}
    df = pd.DataFrame(prices)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    n = len(df)
    dup = df.duplicated(subset=["trade_date"]).sum()
    biz_days = pd.bdate_range(df["trade_date"].min(), df["trade_date"].max())
    missing = len(biz_days) - df["trade_date"].nunique()
    null_high = df["high_price"].isna().sum()
    null_low = df["low_price"].isna().sum()
    null_open = df["open_price"].isna().sum()
    null_close = df["close_price"].isna().sum()
    null_vol = df["volume"].isna().sum()
    return {
        "symbol": symbol, "n_obs": n, "min_date": str(df["trade_date"].min().date()),
        "max_date": str(df["trade_date"].max().date()), "duplicates": int(dup),
        "expected_bdays_in_range": len(biz_days), "missing_bdays_vs_calendar": int(missing),
        "pct_high_null": null_high / n, "pct_low_null": null_low / n,
        "pct_open_null": null_open / n, "pct_close_null": null_close / n,
        "pct_volume_null": null_vol / n,
    }


def main() -> int:
    results = []
    print("=" * 100)
    print("1 ticker per sector, wide request (2015-01-01 to today) -- probes earliest "
          "history + full recent coverage in one call each")
    print("=" * 100)
    for sector, ticker in SECTOR_TICKERS.items():
        try:
            payload = call(ticker, "2015-01-01", "2026-08-09")
        except requests.HTTPError as exc:
            print(f"  FAILED for {ticker}: {exc}")
            results.append({"symbol": ticker, "sector": sector, "n_obs": 0, "error": str(exc)})
            continue
        stats = analyze(ticker, payload)
        stats["sector"] = sector
        results.append(stats)
        print(f"  {ticker} ({sector}): {stats}")

    print()
    print("=" * 100)
    print("Narrow-window test: does from/to actually filter, or is full history always "
          "returned regardless? (BUAFOODS, 30-day window)")
    print("=" * 100)
    narrow = call("BUAFOODS", "2026-07-01", "2026-08-01")
    narrow_stats = analyze("BUAFOODS", narrow)
    print(f"  narrow request stats: {narrow_stats}")
    wide_buafoods = next(r for r in results if r["symbol"] == "BUAFOODS")
    print(f"  wide request (already fetched above) n_obs={wide_buafoods['n_obs']} vs "
          f"narrow n_obs={narrow_stats['n_obs']}")
    date_filter_respected = narrow_stats["n_obs"] < wide_buafoods["n_obs"]
    print(f"  CONCLUSION: from/to date filtering is {'RESPECTED' if date_filter_respected else 'IGNORED (returns full history regardless)'}")

    print()
    print("=" * 100)
    print("Missing-security probe: a ticker with NO real facts on this platform at all "
          "(MCNICHOLS, per Phase 19's own unclassified pilot ticker)")
    print("=" * 100)
    try:
        mc = call("MCNICHOLS", "2015-01-01", "2026-08-09")
        mc_stats = analyze("MCNICHOLS", mc)
        print(f"  MCNICHOLS: {mc_stats}")
    except requests.HTTPError as exc:
        print(f"  MCNICHOLS FAILED: {exc}")

    out_path = ROOT / "data" / "raw" / "history_investigation_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print()
    print(f"Results written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
