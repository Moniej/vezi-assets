"""FSI Phase 25: Sector-Coverage View CLI (docs/fre_runs/
fsi_phase25_preregistration.md).

A thin, read-only command-line wrapper around Phase 24's
`sector_coverage.coverage_by_sector()`, called unmodified. No new
reasoning, no new data, no LLM call, no database write of any kind.

  PYTHONPATH=src python scripts/fre/screen_sector_coverage.py --as-of 2026-08-02
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.sector_coverage import coverage_by_sector  # noqa: E402


def _print_rows(rows) -> None:
    if not rows:
        print("No sectors found.")
        return
    for r in rows:
        print(f"{r.sector_ngx}: total={r.total_tickers} fsi_covered={r.fsi_covered_tickers} "
              f"watchlist={r.watchlist_tickers}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Show research/watchlist coverage aggregated by NGX sector, as of a "
                    "given point-in-time date. Read-only against the production database; "
                    "writes nothing to it. Three plain counts per sector -- never a "
                    "combined coverage score or ranking."
    )
    parser.add_argument("--as-of", required=True, dest="as_of_date",
                         help="Point-in-time cutoff date, YYYY-MM-DD, for the watchlist "
                              "count (total/fsi_covered counts are not date-sensitive).")
    args = parser.parse_args()

    try:
        date.fromisoformat(args.as_of_date)
    except ValueError:
        print(f"ERROR: --as-of {args.as_of_date!r} is not a valid date (expected YYYY-MM-DD).",
              file=sys.stderr)
        return 1

    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    rows = coverage_by_sector(con, args.as_of_date)
    con.close()

    _print_rows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
