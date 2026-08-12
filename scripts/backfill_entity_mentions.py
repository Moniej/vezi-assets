"""Backfill entity_mentions for entities/relationships created before the
2026-08-11 fix to resolve_or_create_entity (HANDOFF.md) -- entity_mentions
has existed in the schema since Phase C but nothing ever wrote to it until
that fix, and the fix only covers FUTURE extraction calls. This backfills
the historical gap from data the platform already has, without inventing
anything:

  1. entities.first_seen_doc_id -- every entity is guaranteed to have been
     mentioned in the document it was first created from.
  2. entity_relationships.source_evidence_id -> evidence.doc_id -- every
     relationship's subject AND object entity were both mentioned in the
     document that grounded that relationship's evidence.

Idempotent (matches _record_mention's own existence check) -- safe to
rerun after the live fix has already added new rows going forward.

  PYTHONPATH=src python scripts/backfill_entity_mentions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    con = db.connect()

    from_first_seen = con.execute(
        "SELECT entity_id, first_seen_doc_id FROM entities WHERE first_seen_doc_id IS NOT NULL"
    ).fetchall()

    from_relationships = con.execute("""
        SELECT er.subject_entity_id, ev.doc_id FROM entity_relationships er
        JOIN evidence ev ON ev.evidence_id = er.source_evidence_id
        UNION
        SELECT er.object_entity_id, ev.doc_id FROM entity_relationships er
        JOIN evidence ev ON ev.evidence_id = er.source_evidence_id
    """).fetchall()

    candidates = {(eid, did) for eid, did in from_first_seen} | {(eid, did) for eid, did in from_relationships}

    existing = {(eid, did) for eid, did in
               con.execute("SELECT entity_id, doc_id FROM entity_mentions").fetchall()}

    to_insert = candidates - existing

    print(f"candidate (entity_id, doc_id) mentions derivable from existing data: {len(candidates)}")
    print(f"already present (idempotent skip): {len(candidates) - len(to_insert)}")
    print(f"to insert this run: {len(to_insert)}")

    if args.dry_run:
        print("--dry-run: no writes performed")
        return 0

    for entity_id, doc_id in sorted(to_insert):
        con.execute("INSERT INTO entity_mentions (doc_id, entity_id) VALUES (?,?)", (doc_id, entity_id))
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
    n_entities_mentioned = con.execute("SELECT COUNT(DISTINCT entity_id) FROM entity_mentions").fetchone()[0]
    n_docs = con.execute("SELECT COUNT(DISTINCT doc_id) FROM entity_mentions").fetchone()[0]
    print(f"inserted: {len(to_insert)} rows")
    print(f"entity_mentions now holds {total} rows: {n_entities_mentioned} distinct entities "
          f"across {n_docs} distinct documents")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
