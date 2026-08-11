"""Closes the one remaining sector_ngx gap identified in the 2026-08-10
cross-validation pass: MCNICHOLS had NULL securities.sector_ngx (absent
from the NGX Daily Official List PDF used by scripts/fre/
populate_sector_ngx.py -- most likely because it lists on NGX's Growth
Board, a section that PDF's transcription did not cover for this ticker).

This is a NULL -> value fill only. Per explicit instruction, existing
non-NULL sector_ngx values are NEVER overwritten -- this script refuses
to run if the target row is not already NULL. Source: NGX Pulse's own
real, live /ngxdata/stocks snapshot (already fetched and cached this
session at data/raw/stocks/2026-08-10.json, sector='CONSUMER GOODS',
market='Growth Board'), reusing the EXISTING sector_ngx_provenance table
(no new schema).

  PYTHONPATH=src python scripts/ngxpulse_fill_mcnichols_sector.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

TICKER = "MCNICHOLS"
CACHE_FILE = ROOT / "data" / "raw" / "stocks" / "2026-08-10.json"
SOURCE_DOCUMENT = "NGX Pulse API /ngxdata/stocks snapshot"
SOURCE_URL = "https://www.ngxpulse.ng/api/ngxdata/stocks"
RETRIEVAL_DATE = "2026-08-10"


def main() -> int:
    payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    stocks = payload.get("stocks") or payload.get("data") or payload
    row = next((s for s in stocks if s.get("symbol") == TICKER), None)
    if row is None:
        print(f"ERROR: {TICKER} not found in {CACHE_FILE}")
        return 1
    sector_ngx = row["sector"]
    board_section = row.get("market")
    print(f"{TICKER}: sector={sector_ngx!r} board_section={board_section!r} (from live NGX Pulse snapshot)")

    con = db.connect()
    current = con.execute("SELECT sector_ngx FROM securities WHERE ticker = ?", (TICKER,)).fetchone()
    if current is None:
        print(f"ERROR: {TICKER} not found in securities -- refusing to insert a new security row here.")
        return 1
    if current[0] is not None:
        print(f"REFUSING: securities.sector_ngx for {TICKER} is already {current[0]!r} (not NULL) -- "
              f"this script only fills NULLs, never overwrites existing metadata.")
        return 1

    con.execute("UPDATE securities SET sector_ngx = ? WHERE ticker = ?", (sector_ngx, TICKER))
    con.execute(
        "INSERT INTO sector_ngx_provenance (ticker, sector_ngx, sub_industry, board_section, "
        "source_document, source_url, retrieval_date) VALUES (?,?,?,?,?,?,?)",
        (TICKER, sector_ngx, None, board_section, SOURCE_DOCUMENT, SOURCE_URL, RETRIEVAL_DATE),
    )
    con.commit()

    verify = con.execute("SELECT sector_ngx FROM securities WHERE ticker = ?", (TICKER,)).fetchone()
    print(f"Done. securities.sector_ngx for {TICKER} is now {verify[0]!r}.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
