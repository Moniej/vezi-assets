"""Daily ephemeral-data capture (data-moat mechanism M1).

  python scripts/daily_capture.py

Snapshots every proven NGX-related endpoint into data/capture/<YYYY-MM-DD>/
as RAW timestamped payloads (rule: raw first, structured second — parsing can
always be redone later; capture cannot). Idempotent per calendar day.

MUST run every trading day. Each missed day is permanently lost history.
Current capture set (expands as endpoint discovery progresses):
  1. NGX doclib REST full ticker snapshot (every listed symbol, current value,
     %change, type) — the exchange-official cross-section for the day.
  2. investing.com current levels for all 8 mapped NGX indices.
Work items (not yet captured): NGX daily price list w/ volume/value/deals
(endpoint discovery), X-Issuer disclosure feed, FX rates page.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db  # noqa: E402
from ngxrot.providers.investing_com import INSTRUMENTS, _API, _HEADERS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
outdir = ROOT / "data" / "capture" / today
outdir.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": _HEADERS["User-Agent"], "Accept": "application/json"}
captured, failed = [], []


def save(name: str, payload) -> None:
    ts = datetime.now(timezone.utc).strftime("%H%M%SZ")
    path = outdir / f"{name}_{ts}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    captured.append(f"{name} ({path.stat().st_size:,} bytes)")


# 1. NGX official full-ticker snapshot
try:
    r = requests.get("https://doclib.ngxgroup.com/REST/api/statistics/ticker",
                     headers=UA, timeout=40)
    r.raise_for_status()
    save("ngx_ticker_snapshot", r.json())
except Exception as e:  # noqa: BLE001 — capture jobs log and continue
    failed.append(f"ngx_ticker_snapshot: {type(e).__name__} {e}")

# 1a2. NGX full equity price list (exchange-official cross-section incl.
#      OHLC, Trades, Volume, naira Value — discovered 2026-07-17)
try:
    r = requests.get("https://doclib.ngxgroup.com/REST/api/statistics/equities/",
                     params={"market": "", "sector": "", "orderby": "",
                             "pageSize": "400", "pageNo": "0"},
                     headers=UA, timeout=60)
    r.raise_for_status()
    save("ngx_equities_pricelist", r.json())
except Exception as e:  # noqa: BLE001
    failed.append(f"ngx_equities_pricelist: {type(e).__name__} {e}")

# 1b. NGX X-Issuer disclosure feed: last 3 days of ALL submission types
#     (exchange-official announcement timestamps; discovered 2026-07-16)
try:
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00")
    r = requests.get(
        "https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('XFinancial_News')/items/",
        params={"$select": "Id,Created,CompanyName,CompanySymbol,"
                           "InternationSecIN,Type_of_Submission,URL",
                "$filter": f"Created ge datetime'{since}'",
                "$orderby": "Created desc", "$top": "1000"},
        headers={**UA, "Accept": "application/json;odata=verbose"}, timeout=90)
    r.raise_for_status()
    save("xissuer_disclosures_3d", r.json()["d"]["results"])
except Exception as e:  # noqa: BLE001
    failed.append(f"xissuer_disclosures_3d: {type(e).__name__} {e}")

# 2. investing.com current index values (last 5 sessions per index, cheap)
try:
    idx_payload = {}
    import time
    for code, (inst_id, sym) in INSTRUMENTS.items():
        rr = requests.get(_API.format(id=inst_id),
                          params={"start-date": "2026-07-01", "end-date": today,
                                  "time-frame": "Daily", "add-missing-rows": "false"},
                          headers=_HEADERS, timeout=40)
        rr.raise_for_status()
        idx_payload[code] = rr.json().get("data")
        time.sleep(0.8)
    save("investing_index_recent", idx_payload)
except Exception as e:  # noqa: BLE001
    failed.append(f"investing_index_recent: {type(e).__name__} {e}")

con = db.connect()
con.execute(
    "INSERT INTO data_quality_log (check_name, entity_type, entity_code, trade_date, "
    "severity, detail) VALUES ('daily_capture','index','MARKET',?,?,?)",
    (today, "info" if not failed else "warn",
     f"captured: {len(captured)}; failed: {len(failed)} "
     f"{('| ' + '; '.join(failed)) if failed else ''}"[:290]))
con.commit()

print(f"capture {today} -> {outdir}")
for c in captured:
    print(f"  OK   {c}")
for f in failed:
    print(f"  FAIL {f}")
sys.exit(1 if failed and not captured else 0)
