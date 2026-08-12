"""Regression test for the entity_mentions fix (2026-08-11, HANDOFF.md).
entity_mentions existed in the schema since Phase C but nothing ever wrote
to it -- as a direct consequence, documents.retrieval.retrieve_documents's
entity_name-filtered path (an existing, real feature used by the
reasoning engine) always returned zero rows, silently, with no test
coverage catching it. Fixed in entities.py (resolve_or_create_entity now
records mentions) + backfilled historically
(scripts/backfill_entity_mentions.py).

Read-only against the real production database, plus one synthetic-DB
check of the live write path.

  PYTHONPATH=src python scripts/test_entity_mentions.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.entities import resolve_or_create_entity  # noqa: E402
from ngxrot.documents.retrieval import RetrievalQuery, retrieve_documents  # noqa: E402

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)

    n_mentions = con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
    check("entity_mentions is no longer empty (backfilled from real data)", n_mentions >= 70)

    n_entities_mentioned = con.execute(
        "SELECT COUNT(DISTINCT entity_id) FROM entity_mentions").fetchone()[0]
    n_entities_total = con.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    check("every real entity has at least one recorded mention "
          "(entities.first_seen_doc_id guarantees this)",
          n_entities_mentioned == n_entities_total)

    orphan_docs = con.execute(
        "SELECT COUNT(*) FROM entity_mentions em WHERE NOT EXISTS "
        "(SELECT 1 FROM documents d WHERE d.doc_id = em.doc_id)").fetchone()[0]
    orphan_entities = con.execute(
        "SELECT COUNT(*) FROM entity_mentions em WHERE NOT EXISTS "
        "(SELECT 1 FROM entities e WHERE e.entity_id = em.entity_id)").fetchone()[0]
    check("no dangling doc_id references in entity_mentions", orphan_docs == 0)
    check("no dangling entity_id references in entity_mentions", orphan_entities == 0)

    dupes = con.execute(
        "SELECT COUNT(*) FROM (SELECT doc_id, entity_id, COUNT(*) c FROM entity_mentions "
        "GROUP BY doc_id, entity_id HAVING c > 1)").fetchone()[0]
    check("no duplicate (doc_id, entity_id) pairs (idempotency held)", dupes == 0)

    # --- the actual downstream fix: entity_name retrieval now works -------
    name = con.execute(
        "SELECT canonical_name FROM entities WHERE entity_type = 'competitor_mention' LIMIT 1"
    ).fetchone()[0]
    docs = retrieve_documents(con, RetrievalQuery(entity_name=name, limit=10))
    check(f"retrieve_documents(entity_name={name!r}) now returns real results "
          f"(previously always 0 rows, silently, for every entity_name query)",
          len(docs) > 0)

    con.close()

    # --- live write path: resolve_or_create_entity records a mention ------
    scon = db.init_db(":memory:", seed=False)
    scon.execute("INSERT INTO securities (ticker, name, board) VALUES "
                "('TESTCO', 'Test Company Plc', 'main')")
    cur = scon.execute(
        "INSERT INTO sources (name, kind, reliability, base_confidence) "
        "VALUES ('test_source','company_filing','primary',0.85)")
    source_id = cur.lastrowid
    scon.execute(
        "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, source_type, "
        "filing_date, retrieved_date, local_path, source_confidence, source_id, as_of_date) "
        "VALUES (1,'TESTCO','TESTCO','dividend','filing','2026-04-01','2026-04-01','x',"
        "0.85,?,'2026-04-01')", (source_id,))
    scon.commit()
    eid = resolve_or_create_entity(scon, "Test Entity", "competitor_mention", 1)
    check("live write path: resolve_or_create_entity records a mention on entity creation",
          scon.execute("SELECT COUNT(*) FROM entity_mentions WHERE doc_id=1 AND entity_id=?",
                       (eid,)).fetchone()[0] == 1)
    resolve_or_create_entity(scon, "Test Entity", "competitor_mention", 1)  # same entity, same doc
    check("live write path: calling it again for the same (doc, entity) does not duplicate",
          scon.execute("SELECT COUNT(*) FROM entity_mentions WHERE doc_id=1 AND entity_id=?",
                       (eid,)).fetchone()[0] == 1)
    scon.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
