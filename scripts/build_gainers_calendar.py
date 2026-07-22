"""Parse every archived pricelist zip's Gainers-and-Losers PDF into one
transitions table — the exchange's own record of daily movers with their
OFFICIALLY ADJUSTED base prices (corporate-action re-basings).

  python -u scripts/build_gainers_calendar.py

Zip naming is unreliable (a zip dated D can hold D-1→D or D→D+1), so rows
key on the report's INTERNAL end date.
Output: data/reference/gainers_transitions.csv
        (end_date, symbol, prev, base, new, pct, adjusted, start_date)
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "data" / "reference" / "gainers_transitions.csv"


def work(zp: str):
    from ngxrot.gainers_parser import parse_gainers_zip
    g = parse_gainers_zip(zp)
    if g is None:
        return Path(zp).name, None
    return Path(zp).name, [
        dict(end_date=g["end"], symbol=s, start_date=g["start"], **r)
        for s, r in g["rows"].items()]


if __name__ == "__main__":
    zips = sorted((ROOT / "data/archive/pricelist_zips").glob("2*.zip"))
    print(f"zips: {len(zips)}", flush=True)
    rows, fails = [], 0
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, str(z)) for z in zips]
        for i, f in enumerate(as_completed(futs), 1):
            name, rs = f.result()
            if rs is None:
                fails += 1
            else:
                rows.extend(rs)
            if i % 300 == 0:
                print(f"[{i}/{len(zips)}] rows={len(rows):,} "
                      f"no-gainers={fails}", flush=True)
    df = (pd.DataFrame(rows)
          .drop_duplicates(subset=["end_date", "symbol"])
          .sort_values(["end_date", "symbol"]))
    df.to_csv(OUT, index=False)
    print(f"DONE: {len(df):,} mover rows / {df.end_date.nunique():,} "
          f"transitions | adjusted rows: {int(df.adjusted.sum()):,} | "
          f"zips without gainers: {fails}", flush=True)
