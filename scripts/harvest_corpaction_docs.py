"""Archive ALL X-Issuer corporate-action filing PDFs (permanent, idempotent).

  python -u scripts/harvest_corpaction_docs.py

Feeds: (a) qualification-date extraction from text-based standardized
"Corporate Actions Announcement" PDFs -> jump explanations; (b) the OCR
track for scanned filings; (c) the permanent disclosure archive.
Resume-safe: skips existing plausible files; failures logged.
"""

import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive" / "xissuer_docs"
ARCHIVE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

cal = pd.read_csv(ROOT / "data/staging/xissuer/corporate_actions_calendar_classified.csv")
cal = cal.dropna(subset=["url"])
print(f"catalog: {len(cal)} filings", flush=True)


def fname(r) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_",
                  f"{int(r.sp_id)}_{str(r.url).rsplit('/', 1)[-1][:120]}")


todo = [r for _, r in cal.iterrows()
        if not ((ARCHIVE / fname(r)).exists()
                and (ARCHIVE / fname(r)).stat().st_size > 5000)]
print(f"to download: {len(todo)} (already archived: {len(cal) - len(todo)})",
      flush=True)

ok = fail = 0
failures = []
for i, r in enumerate(todo, 1):
    try:
        resp = requests.get(str(r.url), headers=UA, timeout=60)
        if resp.ok and resp.content[:4] == b"%PDF":
            (ARCHIVE / fname(r)).write_bytes(resp.content)
            ok += 1
        else:
            fail += 1
            failures.append(dict(sp_id=int(r.sp_id), status=resp.status_code))
    except Exception as e:  # noqa: BLE001
        fail += 1
        failures.append(dict(sp_id=int(r.sp_id), status=type(e).__name__))
        time.sleep(10)
    if i % 500 == 0:
        print(f"[{i}/{len(todo)}] ok={ok} fail={fail}", flush=True)
    time.sleep(0.5)

if failures:
    pd.DataFrame(failures).to_csv(ARCHIVE / "_download_failures.csv", index=False)
print(f"DONE: archive holds {len(list(ARCHIVE.glob('*.pdf')))} PDFs "
      f"(this run: {ok} ok, {fail} failed)", flush=True)
