"""FSI Phase 9: Knowledge Graph Completeness -- verified entities and
rename lineage (docs/fre_runs/fsi_phase9_preregistration.md,
docs/fre_runs/fsi_phase9_implementation_log.md).

Populates two real, disclosed gaps using ONLY data this platform
already possesses and already trusts -- zero new extraction, zero LLM
call:

  1. `entities` rows (entity_type='company') for the 4 FSI tickers that
     do not yet have one (UCAP, BUAFOODS, AFRIPRUD, CAP) -- NASCON
     already has one and is untouched.
  2. `entity_relationships` rows (relation_type='renamed_from') for the
     4 ticker renames marked 'verified' in
     data/reference/symbol_renames.csv -- the 49 'candidate'-status rows
     are NEVER used. This requires creating entity rows for the 7
     symbols (of the renames' 8 old+new symbols) that don't yet have
     one -- GTCO already exists and is reused.

relation_type validated against the ALREADY-EXISTING, already-frozen
configs/relation_taxonomy.toml (built in FRE-1, discovered already
complete during this phase's own implementation -- see the
implementation log's Entry 0) -- this script only READS that file,
never modifies it.

  PYTHONPATH=src python scripts/fre/fsi_phase9_populate_knowledge_graph.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_phase9_populate_knowledge_graph.py --apply    # writes for real
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sqlite3
import sys
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

RENAMES_CSV = ROOT / "data" / "reference" / "symbol_renames.csv"
RELATION_TAXONOMY_TOML = ROOT / "configs" / "relation_taxonomy.toml"

FSI_TICKERS = ("UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON")


def _load_verified_renames() -> list[dict]:
    with open(RENAMES_CSV, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "verified"]
    return rows


def _validate_relation_type(relation_type: str) -> None:
    taxonomy = tomllib.loads(RELATION_TAXONOMY_TOML.read_text(encoding="utf-8"))
    all_types = {t for family in taxonomy.values() for t in family.get("types", [])}
    assert relation_type in all_types, (
        f"relation_type {relation_type!r} is not declared in {RELATION_TAXONOMY_TOML} "
        f"-- refusing to write an undeclared relation type"
    )


def _get_entity_id(con: sqlite3.Connection, canonical_name: str) -> int | None:
    row = con.execute(
        "SELECT entity_id FROM entities WHERE entity_type='company' AND canonical_name=?",
        (canonical_name,),
    ).fetchone()
    return row[0] if row else None


def _earliest_doc_by_raw_symbol(con: sqlite3.Connection, raw_symbol: str) -> int | None:
    row = con.execute(
        "SELECT doc_id FROM documents WHERE raw_symbol=? ORDER BY filing_date, doc_id LIMIT 1",
        (raw_symbol,),
    ).fetchone()
    return row[0] if row else None


def _earliest_doc_by_ticker(con: sqlite3.Connection, ticker: str) -> int | None:
    row = con.execute(
        "SELECT doc_id FROM documents WHERE ticker=? ORDER BY filing_date, doc_id LIMIT 1",
        (ticker,),
    ).fetchone()
    return row[0] if row else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    _validate_relation_type("renamed_from")

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase9_kg_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("entities", "entity_relationships", "documents", "extracted_facts")}

    now = datetime.now(timezone.utc).isoformat()
    entities_written = 0
    relationships_written = 0

    # --- Step 1: entities for the 4 missing FSI tickers ---------------------
    for ticker in FSI_TICKERS:
        existing = _get_entity_id(con, ticker)
        if existing is not None:
            print(f"[SKIP] entity for {ticker} already exists (entity_id={existing})")
            continue
        first_seen = _earliest_doc_by_ticker(con, ticker)
        print(f"{'[DRY RUN] ' if not args.apply else ''}CREATE entity: company/{ticker}, "
              f"first_seen_doc_id={first_seen}")
        if args.apply:
            con.execute(
                "INSERT INTO entities (entity_type, canonical_name, ticker, first_seen_doc_id) "
                "VALUES ('company', ?, NULL, ?)",
                (ticker, first_seen),
            )
            entities_written += 1

    # --- Step 2: entities + renamed_from edges for the 4 verified renames ---
    for row in _load_verified_renames():
        old_symbol, new_symbol = row["old_symbol"], row["new_symbol"]
        valid_from = row["new_first"]

        old_id = _get_entity_id(con, old_symbol)
        if old_id is None:
            first_seen = _earliest_doc_by_raw_symbol(con, old_symbol)
            print(f"{'[DRY RUN] ' if not args.apply else ''}CREATE entity: company/{old_symbol} "
                  f"(pre-rename), first_seen_doc_id={first_seen}")
            if args.apply:
                cur = con.execute(
                    "INSERT INTO entities (entity_type, canonical_name, ticker, first_seen_doc_id) "
                    "VALUES ('company', ?, NULL, ?)",
                    (old_symbol, first_seen),
                )
                old_id = cur.lastrowid
                entities_written += 1

        new_id = _get_entity_id(con, new_symbol)
        if new_id is None:
            first_seen = _earliest_doc_by_raw_symbol(con, new_symbol)
            print(f"{'[DRY RUN] ' if not args.apply else ''}CREATE entity: company/{new_symbol} "
                  f"(post-rename), first_seen_doc_id={first_seen}")
            if args.apply:
                cur = con.execute(
                    "INSERT INTO entities (entity_type, canonical_name, ticker, first_seen_doc_id) "
                    "VALUES ('company', ?, NULL, ?)",
                    (new_symbol, first_seen),
                )
                new_id = cur.lastrowid
                entities_written += 1
        else:
            print(f"[SKIP] entity for {new_symbol} already exists (entity_id={new_id})")

        print(f"{'[DRY RUN] ' if not args.apply else ''}CREATE relationship: "
              f"{new_symbol}(new) --[renamed_from]--> {old_symbol}(old), valid_from={valid_from}, "
              f"confidence=1.0 (owner-verified source data, not a probabilistic extraction)")
        if args.apply:
            con.execute(
                "INSERT INTO entity_relationships (subject_entity_id, relation_type, object_entity_id, "
                "valid_from, valid_to, source_evidence_id, confidence) VALUES (?,?,?,?,?,?,?)",
                (new_id, "renamed_from", old_id, valid_from, None, None, 1.0),
            )
            relationships_written += 1

    if args.apply:
        con.commit()

    after_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("entities", "entity_relationships", "documents", "extracted_facts")}
    print(f"\nBefore: {before_counts}")
    print(f"After:  {after_counts}")
    print(f"documents/extracted_facts unchanged: "
          f"{before_counts['documents'] == after_counts['documents'] and before_counts['extracted_facts'] == after_counts['extracted_facts']}")
    if args.apply:
        print(f"Wrote {entities_written} new entities rows, {relationships_written} new "
              f"entity_relationships rows.")
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
