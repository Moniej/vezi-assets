"""FSI Phase 2 architectural correction (docs/fre_runs/
fsi_phase2_implementation_log.md Entry 4/5): removes the six incorrect
restates_fact_id links written before the restatement_detection.py fix
(overlap-only rule -> equivalent-span rule).

Affected: NASCON fact_ids 228,229,230 (assets/liabilities/equity, FY2024,
written during Stage 2) and 241,242,243 (cfo/cfi/cff, FY2024, written
during Stage 3), each incorrectly marked as restating its own real H1
2024 fact (225-227, 238-240) solely because the periods overlap -- not
because either fact is actually wrong or restated. This script sets
restates_fact_id back to NULL for exactly these six rows. No other
column, and no other row, is touched.

  PYTHONPATH=src python scripts/fre/fsi_phase2_fix_restatement_false_positives.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_phase2_fix_restatement_false_positives.py --apply    # writes for real
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

AFFECTED_FACT_IDS = [228, 229, 230, 241, 242, 243]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase2_restatement_fix_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before = con.execute(
        f"SELECT fact_id, fact_type, restates_fact_id FROM extracted_facts "
        f"WHERE fact_id IN ({','.join('?' * len(AFFECTED_FACT_IDS))})",
        AFFECTED_FACT_IDS,
    ).fetchall()
    print(f"Before: {before}")

    total_before = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE restates_fact_id IS NOT NULL"
    ).fetchone()[0]
    print(f"Total facts with a non-NULL restates_fact_id anywhere, before: {total_before}")

    if args.apply:
        con.executemany(
            "UPDATE extracted_facts SET restates_fact_id = NULL WHERE fact_id = ?",
            [(fid,) for fid in AFFECTED_FACT_IDS],
        )
        con.commit()

    after = con.execute(
        f"SELECT fact_id, fact_type, restates_fact_id FROM extracted_facts "
        f"WHERE fact_id IN ({','.join('?' * len(AFFECTED_FACT_IDS))})",
        AFFECTED_FACT_IDS,
    ).fetchall()
    print(f"After:  {after}")

    total_after = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE restates_fact_id IS NOT NULL"
    ).fetchone()[0]
    print(f"Total facts with a non-NULL restates_fact_id anywhere, after: {total_after}")

    if args.apply:
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
