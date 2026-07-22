"""Bulk-parse all archived pricelist ZIPs to staged per-file CSVs.

  python -u scripts/parse_pricelists.py

Parallel (6 workers), resume-safe (skips already-parsed files). Failures
logged to _parse_failures.csv, never fatal. Output: data/staging/parsed_pricelists/
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
ARCHIVE = ROOT / "data" / "archive" / "pricelist_zips"
OUT = ROOT / "data" / "staging" / "parsed_pricelists"
OUT.mkdir(parents=True, exist_ok=True)


def work(zp: str):
    from ngxrot.pricelist_parser import parse_pricelist_zip
    p = Path(zp)
    df, issues = parse_pricelist_zip(p)
    if len(df):
        df.to_csv(OUT / (p.stem + ".csv"), index=False)
    return p.name, len(df), issues


if __name__ == "__main__":
    zips = sorted(ARCHIVE.glob("*.zip"))
    todo = [z for z in zips if not (OUT / (z.stem + ".csv")).exists()]
    print(f"zips: {len(zips)} | to parse: {len(todo)}", flush=True)
    fails, n_rows = [], 0
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(work, str(z)): z for z in todo}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                name, n, issues = f.result()
                n_rows += n
                if n == 0:
                    fails.append(dict(file=name, issue="; ".join(issues)[:200]))
            except Exception as e:  # noqa: BLE001
                fails.append(dict(file=futs[f].name,
                                  issue=f"{type(e).__name__}: {str(e)[:150]}"))
            if i % 200 == 0:
                print(f"[{i}/{len(todo)}] rows so far: {n_rows:,} "
                      f"fails: {len(fails)}", flush=True)
    if fails:
        pd.DataFrame(fails).to_csv(OUT / "_parse_failures.csv", index=False)
    print(f"DONE: parsed files now {len(list(OUT.glob('*.csv')))} | "
          f"rows this run: {n_rows:,} | failures: {len(fails)}", flush=True)
