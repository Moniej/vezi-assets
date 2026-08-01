"""FRE-2: backfill causal_chain_steps.implication_layer on the real database.

This is the ONE script in this pass meant to write to the real production
database (data/ngx.sqlite, via db.DEFAULT_DB) -- everything else (tests,
demos) operates on a scratch copy. Given
docs/fre_runs/incident_2026-08-01_prod_db_wipe.md, this script is
deliberately conservative:

  - Defaults to --dry-run (prints the report, writes nothing). --apply is
    required, explicitly, to write anything.
  - Refuses to --apply unless a same-day backup of the production database
    already exists (data/ngx.sqlite.pre_fre2_backup_<today>) -- creates one
    itself if missing, never skips this step silently.
  - Prints full before/after row counts across every table (not just
    causal_chain_steps) and runs PRAGMA foreign_key_check after writing,
    exactly like the FRE-1 migration's own verification did.

  PYTHONPATH=src python scripts/fre/backfill_implication_layers.py            # dry run (default)
  PYTHONPATH=src python scripts/fre/backfill_implication_layers.py --apply    # writes for real
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
from ngxrot.fre.evidence_graph import backfill_implication_layers  # noqa: E402


def table_counts(con: sqlite3.Connection) -> dict[str, int]:
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="Actually write the backfilled labels. Omit for a dry run.")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if not real_db.exists():
        print(f"No database at {real_db} -- nothing to do.")
        return 0

    before_con = sqlite3.connect(real_db)
    before_counts = table_counts(before_con)
    before_con.close()

    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fre2_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")
        else:
            print(f"Backup already exists, reusing: {backup_path}")

    con = sqlite3.connect(real_db)
    report = backfill_implication_layers(con, dry_run=not args.apply)
    print(f"\n{'APPLY' if args.apply else 'DRY RUN'} report:")
    print(f"  total_steps        = {report.total_steps}")
    print(f"  already_labeled    = {report.already_labeled}")
    print(f"  newly_financial    = {report.newly_financial}")
    print(f"  newly_business     = {report.newly_business}")
    print(f"  newly_competitive  = {report.newly_competitive}")
    print(f"  left_unclassified  = {report.left_unclassified}")

    after_counts = table_counts(con)
    changed = {t: (before_counts[t], after_counts[t])
               for t in before_counts if before_counts[t] != after_counts[t]}
    print(f"\nRow-count changes (should be EMPTY -- this backfill only "
          f"updates existing rows, never inserts/deletes): {changed}")
    if changed:
        con.close()
        print("ABORTING: unexpected row-count change detected.")
        return 1

    if args.apply:
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
        if fk_bad:
            con.close()
            return 1
    con.close()
    print("\nOK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
