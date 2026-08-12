"""One-time backfill for entity_relationships.recorded_at (2026-08-12,
production-reliability audit, Finding A).

For every relationship with a source_evidence_id, recorded_at is set to
that evidence's document's as_of_date (our own capture-vintage marker,
same field db.py's market-data readers gate on via `vintage`). Rows with
no source_evidence_id (4 of 22 on the real database at the time this was
written) are left NULL -- capture time genuinely unknown, not guessed.

Idempotent: only touches rows where recorded_at IS NULL, so rerunning is
always safe.

  python -u scripts/fre/backfill_entity_relationship_recorded_at.py            # dry run
  python -u scripts/fre/backfill_entity_relationship_recorded_at.py --apply    # writes for real
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    con = db.init_db()

    rows = con.execute(
        "SELECT r.relationship_id, d.as_of_date "
        "FROM entity_relationships r "
        "JOIN evidence e ON e.evidence_id = r.source_evidence_id "
        "JOIN documents d ON d.doc_id = e.doc_id "
        "WHERE r.recorded_at IS NULL"
    ).fetchall()
    no_evidence = con.execute(
        "SELECT COUNT(*) FROM entity_relationships "
        "WHERE recorded_at IS NULL AND source_evidence_id IS NULL"
    ).fetchone()[0]

    print(f"To backfill: {len(rows)} relationship(s) with a source document "
         f"({no_evidence} more have no source_evidence_id at all -- left NULL, "
         f"capture time genuinely unknown).")
    for relationship_id, as_of_date in rows:
        print(f"  relationship_id={relationship_id} -> recorded_at={as_of_date}")

    if not args.apply:
        print("\nDry run -- no changes written. Rerun with --apply.")
        return 0

    backup_path = db.DEFAULT_DB.parent / f"ngx.sqlite.pre_entity_rel_recorded_at_backfill_{date.today().isoformat()}"
    if not backup_path.exists():
        shutil.copy(db.DEFAULT_DB, backup_path)
        print(f"Backup created: {backup_path}")

    for relationship_id, as_of_date in rows:
        con.execute("UPDATE entity_relationships SET recorded_at = ? WHERE relationship_id = ?",
                    (as_of_date, relationship_id))
    con.commit()
    print(f"\nBackfilled {len(rows)} row(s). {no_evidence} row(s) remain NULL (no source evidence).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
