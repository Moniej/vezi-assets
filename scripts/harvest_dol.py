"""Archive the NGX Daily Official List (Equities) PDF archive — permanently.

  python -u scripts/harvest_dol.py

Idempotent + resume-safe: skips files already on disk with plausible size.
Raw-first: no parsing here. Failures are logged and retried on next run.
Source: doclib.ngxgroup.com/DownloadsContent/<Title>.pdf (verified 2026-07-17;
catalog inventory at data/staging/sharepoint_probe/downloads_content_inventory.csv).
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive" / "dol_equities"
ARCHIVE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
FAIL_LOG = ARCHIVE / "_download_failures.csv"

inv = pd.read_csv(ROOT / "data/staging/sharepoint_probe/downloads_content_inventory.csv")
eq = inv[inv.FolderNameId == 10].dropna(subset=["Title"]).copy()
eq["content_date"] = pd.to_datetime(
    eq.Title.str.extract(r"(\d{2}-\d{2}-\d{4})")[0], format="%d-%m-%Y",
    errors="coerce")
eq = eq.dropna(subset=["content_date"]).sort_values("content_date")
print(f"catalog: {len(eq)} DOL(EQUITIES) files "
      f"({eq.content_date.min():%Y-%m-%d} .. {eq.content_date.max():%Y-%m-%d})",
      flush=True)


def fname(row) -> str:
    return f"{row.content_date:%Y-%m-%d}_{int(row.Id)}.pdf"


todo = [r for _, r in eq.iterrows()
        if not ((ARCHIVE / fname(r)).exists()
                and (ARCHIVE / fname(r)).stat().st_size > 20000)]
print(f"to download: {len(todo)} (already archived: {len(eq) - len(todo)})",
      flush=True)

ok = fail = 0
failures = []
backoff = 1.0
for i, r in enumerate(todo, 1):
    url = f"https://doclib.ngxgroup.com/DownloadsContent/{r.Title}.pdf"
    try:
        resp = requests.get(url, headers=UA, timeout=90)
        if resp.ok and resp.content[:4] == b"%PDF" and len(resp.content) > 20000:
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
    time.sleep(0.7)

if failures:
    pd.DataFrame(failures).to_csv(FAIL_LOG, index=False)
n_archived = len(list(ARCHIVE.glob("*.pdf")))
print(f"\nDONE: archive now holds {n_archived} PDFs "
      f"(this run: {ok} downloaded, {fail} failed"
      f"{'; failures logged' if failures else ''})", flush=True)
