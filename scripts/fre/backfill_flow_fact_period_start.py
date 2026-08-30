"""Financial Extraction Quality Fix (2026-08-12), Fix 3: safe,
deterministic period_start backfill for FLOW-type extracted_facts.

Companion to scripts/fre/backfill_entity_relationship_recorded_at.py's own
dry-run/--apply/backup-first pattern.

QUALIFYING CRITERIA (a fact is backfilled iff ALL of the following hold --
anything that fails any one of these is left untouched, not guessed):
  1. fact_type is a FLOW type (spans a period), never a point-in-time type
     (assets/liabilities/equity -- ngxrot.documents.prompts.
     POINT_IN_TIME_FACT_TYPES) -- a snapshot has no "start" to backfill,
     full stop, regardless of what period_type it carries.
  2. period_start IS NULL (never overwrites an existing value, even a
     value from an older/different extraction convention).
  3. period_end IS NOT NULL (the anchor date the backfill derives FROM;
     with no anchor, there is nothing to compute).
  4. period_type IS NOT NULL and is one of the CHECK-constrained enum
     values with a well-defined, unambiguous FIXED duration (FY=1yr,
     H1/H2=6mo, Q1-Q4=3mo, 9M=9mo) -- every one of these implies an exact
     period_start once period_end is known; there is no "ambiguous but
     still enum-valid" case, so anything that reaches this script with a
     period_type outside this set (should be impossible given the schema
     CHECK constraint, checked defensively anyway) is rejected, not
     guessed.

DERIVATION METHOD: period_start = period_end minus the period_type's own
fixed duration, plus one day (e.g. FY ending 2024-12-31 -> period_start =
2024-01-01; H1 ending 2024-06-30 -> period_start = 2024-01-01). Pure date
arithmetic on values ALREADY recorded on the fact itself -- no new
information is invented, and no other fact/document is consulted.

PIT SEMANTICS: unaffected by construction. This backfill touches only
period_start (a description of what business period the figure covers,
period_type/period_end being the anchors it was derived from). It never
touches filing_date, retrieved_date, as_of_date, or any other capture-
vintage field -- a fact's actual knowability date (when the OS possessed
it) is completely unchanged by completing its own period description.

DUPLICATE DETECTION: after backfill, this script re-derives
financial_reasoning_conclusions for every newly-unblocked ticker via the
existing, already-idempotent write_ratio_results/write_flag_results/
classify_trends_for_ticker (2026-08-12, production-reliability audit,
`a877d62`) and reports before/after conclusion counts plus an explicit
duplicate-group check.

  python -u scripts/fre/backfill_flow_fact_period_start.py             # dry run, live DB read-only
  python -u scripts/fre/backfill_flow_fact_period_start.py --scratch   # apply to a fresh scratch copy only
  python -u scripts/fre/backfill_flow_fact_period_start.py --apply     # write to PRODUCTION -- requires
                                                                        # explicit operator approval, see
                                                                        # docs/alpha/FINANCIAL_EXTRACTION_
                                                                        # QUALITY_FIX_REPORT.md
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.prompts import POINT_IN_TIME_FACT_TYPES  # noqa: E402
from ngxrot.fre.financial_ratios import (  # noqa: E402
    compute_ratios_for_ticker, list_tickers, write_ratio_results)
from ngxrot.fre.financial_health_flags import compute_flags_for_ticker, write_flag_results  # noqa: E402
from ngxrot.fre.trend_classification import classify_trends_for_ticker, write_trend_results  # noqa: E402

_PERIOD_DURATIONS = {  # period_type -> (years, months) to subtract from period_end
    "FY": (1, 0), "9M": (0, 9), "H1": (0, 6), "H2": (0, 6),
    "Q1": (0, 3), "Q2": (0, 3), "Q3": (0, 3), "Q4": (0, 3),
}


def _derive_period_start(period_end: str, period_type: str) -> str | None:
    if period_type not in _PERIOD_DURATIONS:
        return None  # defensive -- should be unreachable given the schema CHECK constraint
    y, m, d = map(int, period_end.split("-"))
    end = date(y, m, d)
    dy, dm = _PERIOD_DURATIONS[period_type]
    total_months_back = dy * 12 + dm
    start_month_0 = (end.year * 12 + (end.month - 1)) - total_months_back
    start_year, start_month = divmod(start_month_0, 12)
    start_month += 1
    try:
        start = date(start_year, start_month, end.day) + timedelta(days=1)
    except ValueError:
        start = date(start_year, start_month + 1, 1) if start_month < 12 else date(start_year + 1, 1, 1)
    return start.isoformat()


def find_candidates(con: sqlite3.Connection) -> list[tuple[int, str, str, str]]:
    """Returns (fact_id, ticker, period_end, period_type) for every fact
    meeting all four qualifying criteria."""
    placeholders = ",".join("?" * len(POINT_IN_TIME_FACT_TYPES))
    rows = con.execute(
        f"SELECT f.fact_id, d.ticker, f.period_end, f.period_type "
        f"FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        f"WHERE f.period_start IS NULL AND f.period_end IS NOT NULL "
        f"AND f.period_type IS NOT NULL AND f.fact_type NOT IN ({placeholders})",
        tuple(POINT_IN_TIME_FACT_TYPES),
    ).fetchall()
    qualifying, rejected = [], []
    for fact_id, ticker, period_end, period_type in rows:
        if period_type not in _PERIOD_DURATIONS:
            rejected.append((fact_id, ticker, period_end, period_type, "period_type not a fixed-duration enum value"))
            continue
        qualifying.append((fact_id, ticker, period_end, period_type))
    return qualifying, rejected


def run_backfill(con: sqlite3.Connection, candidates: list[tuple[int, str, str, str]]) -> int:
    updated = 0
    for fact_id, ticker, period_end, period_type in candidates:
        new_start = _derive_period_start(period_end, period_type)
        if new_start is None:
            continue
        con.execute("UPDATE extracted_facts SET period_start = ? WHERE fact_id = ?",
                    (new_start, fact_id))
        updated += 1
    con.commit()
    return updated


def rederive_conclusions(con: sqlite3.Connection, tickers: list[str]) -> dict:
    before = con.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0]
    for t in tickers:
        write_ratio_results(con, compute_ratios_for_ticker(con, t))
        write_flag_results(con, compute_flags_for_ticker(con, t))
        write_trend_results(con, classify_trends_for_ticker(con, t))
    con.commit()
    after = con.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0]
    dupes = con.execute("""
        SELECT ticker, conclusion_type, metric, period_start, period_end, rule_version, COUNT(*) c
        FROM financial_reasoning_conclusions GROUP BY 1,2,3,4,5,6 HAVING c > 1
    """).fetchall()
    return {"before": before, "after": after, "duplicate_groups": len(dupes)}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scratch", action="store_true", help="apply to a fresh scratch copy, not production")
    p.add_argument("--apply", action="store_true", help="write to PRODUCTION -- requires explicit approval")
    args = p.parse_args()

    if args.apply:
        real_db = db.DEFAULT_DB
        backup_path = real_db.parent / f"ngx.sqlite.pre_flow_period_backfill_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")
        con = sqlite3.connect(real_db)
    elif args.scratch:
        scratch = db.new_scratch_db_path()
        shutil.copy(db.DEFAULT_DB, scratch)
        con = sqlite3.connect(scratch)
        print(f"Scratch copy: {scratch}")
    else:
        con = sqlite3.connect(f"file:{db.DEFAULT_DB}?mode=ro", uri=True)

    candidates, rejected = find_candidates(con)
    print(f"Qualifying facts: {len(candidates)}")
    print(f"Rejected (ambiguous period_type): {len(rejected)}")
    for r in rejected:
        print(f"  REJECTED: {r}")

    if not args.apply and not args.scratch:
        print("\nDry run (read-only against production) -- no changes written. "
             "Rerun with --scratch to apply and measure, or --apply for production "
             "(requires explicit operator approval).")
        con.close()
        return 0

    updated = run_backfill(con, candidates)
    print(f"\nBackfilled: {updated}")

    affected_tickers = sorted({t for _, t, _, _ in candidates})
    all_tickers = list_tickers(con)
    stats = rederive_conclusions(con, all_tickers)
    print(f"financial_reasoning_conclusions before: {stats['before']}")
    print(f"financial_reasoning_conclusions after:  {stats['after']}")
    print(f"net new: {stats['after'] - stats['before']}")
    print(f"duplicate groups: {stats['duplicate_groups']}")
    print(f"tickers whose facts were backfilled: {affected_tickers}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
