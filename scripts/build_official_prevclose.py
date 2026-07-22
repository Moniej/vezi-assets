"""Consolidate the official previous-close (PCLOSE) column from staged
pricelist CSVs into one lookup — PCLOSE is the exchange's OFFICIALLY
ADJUSTED base for the day (differs from the raw prior close exactly on
markdown/re-basing days), so close/pclose is the official within-band
return. Doubles as a per-day corporate-adjustment record.

  python -u scripts/build_official_prevclose.py

Output: data/reference/official_prev_close.csv
        (trade_date, symbol, pclose, close, pct_change)
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging" / "parsed_pricelists"
OUT = ROOT / "data" / "reference" / "official_prev_close.csv"

frames, skipped = [], 0
for f in sorted(STAGING.glob("2*.csv")):
    try:
        df = pd.read_csv(f, usecols=lambda c: c in
                         ("trade_date", "symbol", "pclose", "close",
                          "pct_change", "row_conf"))
    except (pd.errors.EmptyDataError, ValueError):
        skipped += 1
        continue
    if "pclose" not in df.columns:
        skipped += 1
        continue
    frames.append(df[df.get("row_conf", 1.0) >= 0.8])
allr = pd.concat(frames, ignore_index=True)
allr = allr.dropna(subset=["symbol", "close"]).drop_duplicates(
    subset=["trade_date", "symbol"])
allr[["trade_date", "symbol", "pclose", "close", "pct_change"]].to_csv(
    OUT, index=False)
print(f"files={len(frames)} skipped={skipped} rows={len(allr):,} "
      f"days={allr.trade_date.nunique():,}")
print(f"wrote {OUT.relative_to(ROOT)}")
