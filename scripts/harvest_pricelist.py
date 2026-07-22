"""Archive NGX 'Gainers and Price List' daily ZIPs (contains PRICES1.pdf =
full daily OHLCV + Trades + naira Value per company).

  python -u scripts/harvest_pricelist.py

Idempotent + resume-safe (skips existing plausible files). Raw-first: zips
stored as-downloaded; extraction happens at parse time.
"""

import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive" / "pricelist_zips"
ARCHIVE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

inv = pd.read_csv(ROOT / "data/staging/sharepoint_probe/downloads_content_inventory.csv")
pl = inv[inv.FolderNameId == 5].dropna(subset=["Title"]).copy()
pl["content_date"] = pd.to_datetime(
    pl.Title.str.extract(r"(\d{2}-\d{2}-\d{4})")[0], format="%d-%m-%Y",
    errors="coerce")
pl = pl.dropna(subset=["content_date"]).sort_values("content_date")
print(f"catalog: {len(pl)} pricelist zips "
      f"({pl.content_date.min():%Y-%m-%d} .. {pl.content_date.max():%Y-%m-%d})",
      flush=True)


def fname(row) -> str:
    return f"{row.content_date:%Y-%m-%d}_{int(row.Id)}.zip"


todo = [r for _, r in pl.iterrows()
        if not ((ARCHIVE / fname(r)).exists()
                and (ARCHIVE / fname(r)).stat().st_size > 10000)]
print(f"to download: {len(todo)} (already archived: {len(pl) - len(todo)})",
      flush=True)

ok = fail = 0
failures = []
backoff = 1.0
for i, r in enumerate(todo, 1):
    url = f"https://doclib.ngxgroup.com/DownloadsContent/{r.Title}.zip"
    try:
        resp = requests.get(url, headers=UA, timeout=90)
        if resp.ok and resp.content[:2] == b"PK" and len(resp.content) > 10000:
            (ARCHIVE / fname(r)).write_bytes(resp.content)
            ok += 1
            backoff = 1.0
        else:
            fail += 1
            failures.append(dict(id=int(r.Id), date=str(r.content_date.date()),
                                 status=resp.status_code, size=len(resp.content)))
    except Exception as e:  # noqa: BLE001
        fail += 1
        failures.append(dict(id=int(r.Id), date=str(r.content_date.date()),
                             status=type(e).__name__, size=0))
        backoff = min(backoff * 2, 60)
        time.sleep(backoff)
    if i % 100 == 0:
        print(f"[{i}/{len(todo)}] ok={ok} fail={fail}", flush=True)
    time.sleep(1.0)

if failures:
    pd.DataFrame(failures).to_csv(ARCHIVE / "_download_failures.csv", index=False)
print(f"\nDONE: archive holds {len(list(ARCHIVE.glob('*.zip')))} zips "
      f"(this run: {ok} ok, {fail} failed)", flush=True)
