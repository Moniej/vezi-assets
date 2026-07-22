"""One-command daily update — schedule THIS (Windows Task Scheduler).

  python -u scripts/daily_update.py

1. Refreshes the DownloadsContent catalog delta (new item IDs since last
   inventory) so the harvesters can see new days' files.
2. Runs the daily REST capture (ticker snapshot, full price list, X-Issuer
   3-day disclosure delta).
3. Runs the idempotent DOL + pricelist harvesters (grab any new/missed
   files; skip everything already archived).
All steps are safe to re-run; failures in one step don't block the next.
"""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/staging/sharepoint_probe/downloads_content_inventory.csv"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Accept": "application/json;odata=verbose"}

# ---- 1. catalog delta ------------------------------------------------------
try:
    inv = pd.read_csv(INV)
    last_id = int(inv.Id.max())
    rows = []
    while True:
        r = requests.get(
            "https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('DownloadsContent')/items/",
            params={"$select": "Id,Title,Created,FolderNameId",
                    "$filter": f"Id gt {last_id}",
                    "$orderby": "Id asc", "$top": "1000"},
            headers=H, timeout=90)
        r.raise_for_status()
        items = r.json()["d"]["results"]
        if not items:
            break
        rows.extend(items)
        last_id = items[-1]["Id"]
    if rows:
        add = pd.DataFrame(rows)
        add["content_date"] = pd.to_datetime(
            add.Title.str.extract(r"(\d{2}-\d{2}-\d{4})")[0],
            format="%d-%m-%Y", errors="coerce")
        pd.concat([inv, add], ignore_index=True).drop_duplicates("Id").to_csv(
            INV, index=False)
    print(f"[1/3] catalog delta: +{len(rows)} items", flush=True)
except Exception as e:  # noqa: BLE001
    print(f"[1/3] catalog delta FAILED: {type(e).__name__} {e}", flush=True)

# ---- 2 & 3. capture + harvesters ------------------------------------------
for i, script in enumerate(("daily_capture.py", "harvest_pricelist.py",
                            "harvest_dol.py"), start=2):
    try:
        out = subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / script)],
                             capture_output=True, text=True, timeout=1800,
                             cwd=ROOT)
        tail = (out.stdout or "").strip().splitlines()[-1:] or ["(no output)"]
        print(f"[{i}/3+] {script}: exit {out.returncode} | {tail[0][:100]}",
              flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[{i}/3+] {script} FAILED: {type(e).__name__}", flush=True)
