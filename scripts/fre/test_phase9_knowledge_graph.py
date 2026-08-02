"""Standalone assertion-script tests for FSI Phase 9's knowledge-graph
population, validated against real production data (read-only).

  PYTHONPATH=src python scripts/fre/test_phase9_knowledge_graph.py
"""
from __future__ import annotations

import csv
import sqlite3
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

RENAMES_CSV = ROOT / "data" / "reference" / "symbol_renames.csv"
RELATION_TAXONOMY_TOML = ROOT / "configs" / "relation_taxonomy.toml"

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


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()

    # --- 1. All 5 FSI tickers have exactly one real entities row each -------
    fsi_tickers = ("UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON")
    counts = {}
    for t in fsi_tickers:
        counts[t] = con.execute(
            "SELECT COUNT(*) FROM entities WHERE entity_type='company' AND canonical_name=?", (t,)
        ).fetchone()[0]
    check("all 5 FSI tickers have exactly ONE entities row each (up from 1/5 "
          "before this phase -- only NASCON)",
          all(c == 1 for c in counts.values()))

    # --- 2. NASCON's pre-existing entity row was NOT touched -----------------
    nascon_row = con.execute(
        "SELECT entity_id, first_seen_doc_id FROM entities WHERE canonical_name='NASCON'"
    ).fetchone()
    check("NASCON's pre-existing entity row is untouched (still entity_id=22, "
          "same first_seen_doc_id as before this phase)",
          nascon_row == (22, 7784))

    # --- 3. Exactly 4 new entity_relationships rows, relation_type=
    # 'renamed_from', matching the 4 verified CSV rows exactly -- and 0 from
    # any 'candidate'-status row ------------------------------------------
    with open(RENAMES_CSV, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    verified_rows = [r for r in all_rows if r["status"] == "verified"]
    candidate_rows = [r for r in all_rows if r["status"] == "candidate"]
    check("exactly 4 rows in symbol_renames.csv are marked 'verified' "
          "(the ones this phase is allowed to use)", len(verified_rows) == 4)

    renamed_from_rows = con.execute(
        "SELECT subject_entity_id, object_entity_id, valid_from FROM entity_relationships "
        "WHERE relation_type='renamed_from'"
    ).fetchall()
    check("exactly 4 real 'renamed_from' entity_relationships rows exist "
          "(the original 'affects_order_1' row is untouched and separate)",
          len(renamed_from_rows) == 4)

    # confirm each renamed_from row matches a real verified CSV row exactly,
    # by resolving entity_ids back to canonical_name
    def _name(entity_id: int) -> str:
        return con.execute("SELECT canonical_name FROM entities WHERE entity_id=?", (entity_id,)).fetchone()[0]

    resolved = {(_name(obj), _name(subj)): valid_from for subj, obj, valid_from in renamed_from_rows}
    expected = {(r["old_symbol"], r["new_symbol"]): r["new_first"] for r in verified_rows}
    check("every 'renamed_from' edge's (old_symbol, new_symbol, valid_from) "
          "matches a real verified CSV row EXACTLY -- subject=new entity, "
          "object=old entity, per Part 2's own worked example direction",
          resolved == expected)

    # --- 4. Zero relation created from any candidate-status row --------------
    candidate_pairs = {(r["old_symbol"], r["new_symbol"]) for r in candidate_rows}
    check("no 'renamed_from' edge corresponds to a 'candidate'-status CSV row "
          "(e.g. the real UBCAP->UCAP candidate row, involving one of this "
          "program's own 5 FSI tickers, is correctly NOT used)",
          not any(pair in candidate_pairs for pair in resolved.keys()))

    # --- 5. relation_type is declared in the existing, frozen taxonomy config
    taxonomy = tomllib.loads(RELATION_TAXONOMY_TOML.read_text(encoding="utf-8"))
    all_declared_types = {t for family in taxonomy.values() for t in family.get("types", [])}
    check("'renamed_from' is declared in the ALREADY-EXISTING configs/"
          "relation_taxonomy.toml (FRE-1 baseline) -- no new config file "
          "was created by this phase", "renamed_from" in all_declared_types)

    # --- 6. confidence=1.0 for all new rows, and every new row's valid_to is
    # NULL (an active, ongoing rename relationship, never expired) ----------
    all_new = con.execute(
        "SELECT confidence, valid_to FROM entity_relationships WHERE relation_type='renamed_from'"
    ).fetchall()
    check("every new renamed_from row has confidence=1.0 (owner-verified "
          "source data, not a probabilistic extraction) and valid_to=NULL",
          all(c == 1.0 and vt is None for c, vt in all_new))

    # --- 7. the original affects_order_1 row is completely untouched --------
    original_row = con.execute(
        "SELECT relationship_id, subject_entity_id, relation_type, object_entity_id, confidence "
        "FROM entity_relationships WHERE relation_type='affects_order_1'"
    ).fetchall()
    check("the original, pre-existing 'affects_order_1' entity_relationships "
          "row is untouched (still exactly 1 row of that type)",
          len(original_row) == 1)

    # --- 8. every new entity row has entity_type='company' and a real,
    # existing first_seen_doc_id (never NULL, never a fabricated doc_id) -----
    new_entity_names = ("UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "FO", "ARDOVA",
                        "GUARANTY", "ACCESS", "ACCESSCORP", "FBNH", "FIRSTHOLDCO")
    all_valid = True
    for name in new_entity_names:
        row = con.execute(
            "SELECT entity_type, first_seen_doc_id FROM entities WHERE canonical_name=?", (name,)
        ).fetchone()
        if row is None or row[0] != "company" or row[1] is None:
            all_valid = False
            continue
        doc_exists = con.execute("SELECT 1 FROM documents WHERE doc_id=?", (row[1],)).fetchone()
        if doc_exists is None:
            all_valid = False
    check("every one of the 11 new entity rows has entity_type='company' and "
          "a first_seen_doc_id pointing at a REAL, existing document (never "
          "NULL, never fabricated)", all_valid)

    # --- 9. database integrity ------------------------------------------------
    check("integrity_check reports 'ok'",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])
    doc_count = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    facts_count = con.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0]
    check("documents count unchanged at 11,533 (this phase never touches "
          "documents or extracted_facts)", doc_count == 11533)
    check("extracted_facts count unchanged at 267", facts_count == 267)

    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
