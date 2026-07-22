"""Harvest the structured earnings-event calendar from X-Issuer filings.

  python -u scripts/harvest_earnings_calendar.py

No OCR/no documents needed: the filing's Created timestamp + type IS the
event. Types: 'Financial Statements' (results submissions) and Board Meeting
variants (results-approval meetings = earnings-adjacent notices).
Output: data/staging/xissuer/earnings_calendar.csv (raw pages archived).
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging" / "xissuer"
RAW = STAGING / "earnings_raw"
RAW.mkdir(parents=True, exist_ok=True)

BASE = "https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('XFinancial_News')/items/"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Accept": "application/json;odata=verbose"}
SELECT = ("Id,Created,CompanyName,CompanySymbol,InternationSecIN,"
          "Type_of_Submission,URL")
TYPES = ["Financial Statements", "Board Meeting (BM)", "Board Meeting"]

windows = pd.date_range("2014-07-01", "2026-10-01", freq="QS")
rows, issues = [], []
type_filter = " or ".join(f"Type_of_Submission eq '{t}'" for t in TYPES)
for a, b in zip(windows[:-1], windows[1:]):
    flt = (f"({type_filter}) and "
           f"Created ge datetime'{a:%Y-%m-%d}T00:00:00' and "
           f"Created lt datetime'{b:%Y-%m-%d}T00:00:00'")
    last_id = 0
    for page in range(8):
        try:
            r = requests.get(BASE, params={
                "$select": SELECT,
                "$filter": flt + f" and Id gt {last_id}",
                "$orderby": "Id asc", "$top": "1000"},
                headers=H, timeout=90)
            r.raise_for_status()
            items = r.json()["d"]["results"]
            if not items:
                break
            (RAW / f"{a:%Y%m%d}_p{page}.json").write_text(json.dumps(items),
                                                          encoding="utf-8")
            for it in items:
                rows.append(dict(
                    created=it["Created"], symbol=it.get("CompanySymbol"),
                    isin=it.get("InternationSecIN"),
                    company=it.get("CompanyName"),
                    submission_type=(it.get("Type_of_Submission") or "").strip(),
                    url=(it.get("URL") or {}).get("Url")
                        if isinstance(it.get("URL"), dict) else it.get("URL"),
                    sp_id=it.get("Id")))
            last_id = items[-1]["Id"]
            if len(items) < 1000:
                break
        except Exception as e:  # noqa: BLE001
            issues.append(f"{a:%Y-%m} p{page}: {type(e).__name__}")
            time.sleep(10)
    time.sleep(0.6)

df = pd.DataFrame(rows).drop_duplicates(subset=["sp_id"])
df["created_date"] = df.created.str[:10]
df.to_csv(STAGING / "earnings_calendar.csv", index=False)
print(f"harvested {len(df):,} filings "
      f"({df.created_date.min()}..{df.created_date.max()}) | "
      f"symbols: {df.symbol.nunique()}", flush=True)
print(df.submission_type.value_counts().to_string(), flush=True)
if issues:
    print("issues:", issues[:10], flush=True)
