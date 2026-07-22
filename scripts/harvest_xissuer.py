"""Harvest the NGX X-Issuer corporate-actions CALENDAR from doclib SharePoint.

  python scripts/harvest_xissuer.py

Stage 1 of the dividend/earnings acquisition (core dataset #4):
  - pages the XFinancial_News list (exchange-official, discovered 2026-07-16)
    for Corporate Action(s) filings 2014-07 -> today, quarter by quarter;
  - archives every raw page (raw-first rule) under data/staging/xissuer/;
  - writes a combined calendar CSV: announcement timestamp (Created),
    symbol, ISIN, company, document URL;
  - also archives the DelistedCompanies list (survivorship dataset).

Stage 2 (separate task): parse linked documents for dividend amounts,
qualification/payment dates -> corporate_actions table rows.

PIT caveat recorded: items Created on 2014-07-11 are a batch-migration
artifact (announcement time unknown, not equal to Created). Real-time
Created stamps begin after the migration date.
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging" / "xissuer"
STAGING.mkdir(parents=True, exist_ok=True)

BASE = "https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('XFinancial_News')/items/"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Accept": "application/json;odata=verbose"}
SELECT = ("Id,Created,Modified,CompanyName,CompanySymbol,InternationSecIN,"
          "Type_of_Submission,URL")
TYPES = ["Corporate Actions ", "Corporate Action"]

windows = pd.date_range("2014-07-01", "2026-10-01", freq="QS")
rows, failures = [], []
for a, b in zip(windows[:-1], windows[1:]):
    flt = (f"(Type_of_Submission eq '{TYPES[0]}' or "
           f"Type_of_Submission eq '{TYPES[1]}') and "
           f"Created ge datetime'{a:%Y-%m-%d}T00:00:00' and "
           f"Created lt datetime'{b:%Y-%m-%d}T00:00:00'")
    try:
        r = requests.get(BASE, params={"$select": SELECT, "$filter": flt,
                                       "$orderby": "Created asc",
                                       "$top": "1000"},
                         headers=H, timeout=90)
        r.raise_for_status()
        items = r.json()["d"]["results"]
        (STAGING / f"corpactions_{a:%Y%m%d}.json").write_text(
            json.dumps(items), encoding="utf-8")
        if len(items) == 1000:
            failures.append(f"{a:%Y-%m}: page cap hit (1000) — window needs "
                            f"splitting, counts beyond cap NOT captured")
        for it in items:
            rows.append(dict(
                created=it["Created"], symbol=it.get("CompanySymbol"),
                isin=it.get("InternationSecIN"),
                company=it.get("CompanyName"),
                submission_type=it.get("Type_of_Submission", "").strip(),
                url=(it.get("URL") or {}).get("Url")
                    if isinstance(it.get("URL"), dict) else it.get("URL"),
                sp_id=it.get("Id")))
    except Exception as e:  # noqa: BLE001 — log & continue per window
        failures.append(f"{a:%Y-%m}: {type(e).__name__} {str(e)[:90]}")
    time.sleep(0.6)

df = pd.DataFrame(rows).drop_duplicates(subset=["sp_id"])
df["created_date"] = df.created.str[:10]
df["migration_batch"] = df.created_date == "2014-07-11"  # PIT-unknown flag
out = STAGING / "corporate_actions_calendar.csv"
df.to_csv(out, index=False)

print(f"harvested {len(df):,} corporate-action filings "
      f"({df.created_date.min()} .. {df.created_date.max()})")
print(f"distinct symbols: {df.symbol.nunique()} | with document URL: "
      f"{df.url.notna().mean():.0%} | migration-batch (PIT-unknown): "
      f"{int(df.migration_batch.sum()):,}")
print("\nfilings per year:")
print(df.created_date.str[:4].value_counts().sort_index().to_string())
if failures:
    print("\nwindow issues:")
    for f in failures:
        print("  ", f)
print(f"\ncalendar: {out}")

# --- DelistedCompanies (survivorship) ---------------------------------------
try:
    r = requests.get(
        "https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('DelistedCompanies')/items/",
        params={"$top": "500"}, headers=H, timeout=60)
    items = r.json()["d"]["results"]
    (STAGING / "delisted_companies.json").write_text(json.dumps(items),
                                                     encoding="utf-8")
    print(f"\nDelistedCompanies archived: {len(items)} items "
          f"-> {STAGING / 'delisted_companies.json'}")
except Exception as e:  # noqa: BLE001
    print(f"\nDelistedCompanies fetch failed: {type(e).__name__} {e}")

sys.exit(0 if len(df) else 1)
