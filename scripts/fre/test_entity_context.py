"""Standalone assertion-script tests for entity_context.py, validated
against real production data (read-only, zero write path anywhere in
this module).

  PYTHONPATH=src python scripts/fre/test_entity_context.py
"""
from __future__ import annotations

import csv
import inspect
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import company_memory_360 as cm360  # noqa: E402
from ngxrot.fre import entity_context as ec  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

RENAMES_CSV = ROOT / "data" / "reference" / "symbol_renames.csv"

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
    before_counts = snapshot_all_table_counts(con)

    fsi_tickers = ("UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON")

    # --- 1. Output equivalence against the underlying tables, for all 5
    # real tickers at a late as_of_date (nothing PIT-excluded) ---------------
    equivalence_ok = True
    for ticker in fsi_tickers:
        ctx = ec.get_entity_context(con, ticker, "2026-08-02")
        direct = con.execute(
            "SELECT entity_id, canonical_name, first_seen_doc_id FROM entities "
            "WHERE entity_type='company' AND canonical_name=?", (ticker,),
        ).fetchone()
        if direct is None or ctx.entity_id != direct[0] or ctx.canonical_name != direct[1] \
           or ctx.first_seen_doc_id != direct[2]:
            equivalence_ok = False
    check("get_entity_context()'s entity fields match a direct query of "
          "the entities table exactly, for all 5 real FSI tickers",
          equivalence_ok)

    # --- 2. GTCO (not an FSI ticker, but a real, known rename case) has
    # exactly the one real renamed_from relationship, matching the raw table
    # exactly -------------------------------------------------------------
    gtco_ctx = ec.get_entity_context(con, "GTCO", "2026-08-02")
    direct_rel = con.execute(
        "SELECT relationship_id, relation_type, subject_entity_id, object_entity_id, "
        "valid_from, valid_to, confidence FROM entity_relationships WHERE relation_type='renamed_from' "
        "AND subject_entity_id = (SELECT entity_id FROM entities WHERE canonical_name='GTCO')"
    ).fetchone()
    check("GTCO's real renamed_from relationship (subject=GTCO, "
          "object=GUARANTY) is returned, matching the raw entity_"
          "relationships row exactly",
          len(gtco_ctx.relationships) == 1
          and gtco_ctx.relationships[0].relationship_id == direct_rel[0]
          and gtco_ctx.relationships[0].valid_from == direct_rel[4]
          and gtco_ctx.relationships[0].confidence == direct_rel[6])
    check("GTCO's relationship direction is correctly 'subject' (GTCO is "
          "the NEW/post-rename entity in the renamed_from edge)",
          gtco_ctx.relationships[0].direction == "subject"
          and gtco_ctx.relationships[0].counterpart_canonical_name == "GUARANTY")

    # --- 3. All 5 FSI tickers correctly show ZERO relationships (matches
    # Phase 9's own disclosed finding: none of the 4 verified renames
    # involves any FSI ticker) ------------------------------------------------
    check("all 5 FSI tickers correctly show ZERO entity_relationships "
          "(matches Phase 9's own disclosed finding -- not a defect)",
          all(len(ec.get_entity_context(con, t, "2026-08-02").relationships) == 0
              for t in fsi_tickers))

    # --- 4. Only VERIFIED relationships exist -- confirm every real
    # renamed_from edge traces to a 'verified'-status CSV row, and that the
    # real candidate case (UBCAP->UCAP) produces NO relationship anywhere --
    with open(RENAMES_CSV, newline="", encoding="utf-8") as f:
        all_csv_rows = list(csv.DictReader(f))
    verified_pairs = {(r["old_symbol"], r["new_symbol"]) for r in all_csv_rows if r["status"] == "verified"}
    candidate_pairs = {(r["old_symbol"], r["new_symbol"]) for r in all_csv_rows if r["status"] == "candidate"}

    all_renamed_from = con.execute(
        "SELECT s.canonical_name, o.canonical_name FROM entity_relationships r "
        "JOIN entities s ON s.entity_id = r.subject_entity_id "
        "JOIN entities o ON o.entity_id = r.object_entity_id "
        "WHERE r.relation_type = 'renamed_from'"
    ).fetchall()
    real_pairs = {(old, new) for new, old in all_renamed_from}
    check("every real renamed_from relationship traces to a 'verified'-"
          "status row in symbol_renames.csv (never a 'candidate' row)",
          real_pairs.issubset(verified_pairs) and real_pairs.isdisjoint(candidate_pairs))

    check("the real UBCAP->UCAP candidate relationship does NOT exist "
          "anywhere in entity_context's output for UCAP (candidate data "
          "remains excluded from the production knowledge graph)",
          ("UBCAP", "UCAP") not in real_pairs
          and all(r.relation_type != "renamed_from" or r.counterpart_canonical_name != "UBCAP"
                  for r in ec.get_entity_context(con, "UCAP", "2026-08-02").relationships))

    # --- 5. PIT gating: an entity is invisible before its own first_seen_
    # doc's filing_date, and a None result never claims non-existence -------
    ucap_before = ec.get_entity_context(con, "UCAP", "2016-03-17")  # 1 day before UCAP's real first_seen filing_date
    ucap_on = ec.get_entity_context(con, "UCAP", "2016-03-18")       # exactly UCAP's real first_seen filing_date
    check("UCAP's entity context is None the day BEFORE its own real "
          "first_seen_doc filing_date (2016-03-18), and populated exactly "
          "ON that date -- PIT gating applied to entities for the first time",
          ucap_before.entity_id is None and ucap_on.entity_id == 40)

    # --- 6. Composition equivalence with CompanyMemory360 --------------------
    memory_equivalence_ok = True
    for ticker in fsi_tickers:
        combined = ec.as_of(con, ticker, "2026-08-02")
        direct_memory = cm360.as_of(con, ticker, "2026-08-02")
        if combined.memory != direct_memory:
            memory_equivalence_ok = False
    check("CompanyMemory360Graph's 'memory' sub-result is exactly "
          "equivalent to calling company_memory_360.as_of() directly, "
          "for all 5 tickers", memory_equivalence_ok)

    # --- 7. No forbidden analytics/scoring fields anywhere -------------------
    forbidden_terms = ("score", "rank", "centrality", "weight", "vote", "recommend")
    dataclass_fields = set()
    for cls in (ec.EntityContext, ec.RelationshipContext, ec.CompanyMemory360Graph):
        dataclass_fields.update(cls.__dataclass_fields__.keys())
    check("no dataclass field name in this module suggests scoring, "
          "ranking, centrality, weighting, voting, or recommendation",
          not any(bad in name.lower() for name in dataclass_fields for bad in forbidden_terms))

    # --- 8. Mechanical single-ticker-scope guardrail --------------------------
    public_funcs = [f for name, f in inspect.getmembers(ec, inspect.isfunction)
                    if not name.startswith("_")]
    check("every public function in entity_context.py accepts at most ONE "
          "'ticker'-named parameter",
          all(len([p for p in inspect.signature(f).parameters if "ticker" in p.lower()]) <= 1
              for f in public_funcs))

    con.close()

    # --- database immutability + zero schema change --------------------------
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run "
          "(zero database writes)", table_diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
