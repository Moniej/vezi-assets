"""Consolidate the per-day DOL ex-div staging CSVs into one closure-date
calendar (remediation step 3; feeds the jump re-match in equity diagnostics).

  python -u scripts/build_exdiv_calendar.py

Each DOL carries, per symbol, the LAST closure-of-register date (ex_div band,
char-level parser validated 2026-07-18). A distinct (symbol, ex_div) pair is
therefore one closure event; first_seen = earliest DOL file that shows it
(PIT: the event was public knowledge no later than first_seen).
Output: data/reference/exdiv_closure_calendar.csv
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging" / "dol_exdiv"
OUT = ROOT / "data" / "reference" / "exdiv_closure_calendar.csv"

frames = []
skipped = 0
for f in sorted(STAGING.glob("2*.csv")):
    try:
        df = pd.read_csv(f)
    except pd.errors.EmptyDataError:
        skipped += 1
        continue
    if "ex_div" not in df.columns:  # days where no row had a date band
        skipped += 1
        continue
    frames.append(df[["symbol", "file_date", "ex_div"]].dropna(subset=["ex_div"]))
all_rows = pd.concat(frames, ignore_index=True)

# guard against parser noise: keep plausible ISO dates only
d = pd.to_datetime(all_rows.ex_div, format="%Y-%m-%d", errors="coerce")
bad = all_rows[d.isna() | (d < "1990-01-01") | (d > "2027-12-31")]
all_rows = all_rows[~all_rows.index.isin(bad.index)]

cal = (all_rows.groupby(["symbol", "ex_div"], as_index=False)
       .agg(first_seen=("file_date", "min"), last_seen=("file_date", "max"),
            n_files=("file_date", "size"))
       .rename(columns={"ex_div": "closure_date"})
       .sort_values(["symbol", "closure_date"]))
OUT.parent.mkdir(parents=True, exist_ok=True)
cal.to_csv(OUT, index=False)

in_cov = cal[(cal.closure_date >= "2014-06-01")]
print(f"files={len(frames)} skipped={skipped} "
      f"raw_rows={len(all_rows):,} dropped={len(bad)}")
print(f"events={len(cal):,} symbols={cal.symbol.nunique()} | "
      f"in price coverage (>=2014-06): {len(in_cov):,} "
      f"({in_cov.symbol.nunique()} symbols)")
print(f"wrote {OUT.relative_to(ROOT)}")
