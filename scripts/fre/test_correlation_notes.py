"""Standalone assertion-script tests for correlation_notes.py (FSI
Phase 19). Read-only module -- but Section 2 still uses a disposable
scratch copy to insert a synthetic macro-exposure edge pair (proving
the positive-match path), while Section 1 confirms the REAL production
database's current, honest state: zero macro_exposure edges exist
today, so every real ticker pair must return an empty note.

  PYTHONPATH=src python scripts/fre/test_correlation_notes.py
"""
from __future__ import annotations

import ast
import inspect
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import correlation_notes as cn  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

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
    real_ro = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(real_ro)

    # --- 1. Real-data honest negative: entity_relationships holds 0
    # macro_exposure rows today, so a real ticker pair returns an empty
    # note, not a fabricated or stubbed one. -------------------------------
    macro_exposure_count = real_ro.execute(
        "SELECT COUNT(*) FROM entity_relationships WHERE relation_type IN "
        "('exposed_to_commodity','exposed_to_fx','exposed_to_policy')"
    ).fetchone()[0]
    check("precondition: entity_relationships holds 0 macro_exposure rows today "
          "(confirms this is a real, not assumed, honest-negative test)",
          macro_exposure_count == 0)

    note = cn.note_for_pair(real_ro, "NASCON", "CAP", "2026-08-02")
    check("note_for_pair() on two real tickers, with no macro_exposure edges in "
          "the real database, correctly returns an empty shared_exposures list "
          "(honest negative, not a stub)",
          note.shared_exposures == [] and note.ticker_a == "NASCON" and note.ticker_b == "CAP")

    try:
        cn.note_for_pair(real_ro, "NASCON", "NASCON", "2026-08-02")
        self_pair_raised = False
    except ValueError:
        self_pair_raised = True
    check("note_for_pair() raises ValueError for a self-pair (ticker_a == ticker_b)",
          self_pair_raised)

    unknown_note = cn.note_for_pair(real_ro, "NOTAREALTICKER", "CAP", "2026-08-02")
    check("note_for_pair() with an unknown/not-yet-graphed ticker returns an empty "
          "note rather than raising -- matches get_entity_context()'s own "
          "established 'absence of evidence is not evidence of absence' handling",
          unknown_note.shared_exposures == [])

    # --- 2. Positive-match path: synthetic macro_exposure edges on a
    # disposable scratch copy only -- confirms the matching logic actually
    # fires when the data exists. --------------------------------------------
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)

    nascon_id = con.execute("SELECT entity_id FROM entities WHERE canonical_name='NASCON'").fetchone()[0]
    cap_id = con.execute("SELECT entity_id FROM entities WHERE canonical_name='CAP'").fetchone()[0]

    commodity_id = con.execute(
        "INSERT INTO entities (entity_type, canonical_name, ticker, first_seen_doc_id) "
        "VALUES ('commodity', 'Brent Crude', NULL, NULL)"
    ).lastrowid

    rel_a_id = con.execute(
        "INSERT INTO entity_relationships (subject_entity_id, relation_type, object_entity_id, "
        "valid_from, valid_to, source_evidence_id, confidence) VALUES (?, 'exposed_to_commodity', ?, "
        "'2026-01-01', NULL, NULL, 0.8)",
        (nascon_id, commodity_id),
    ).lastrowid
    rel_b_id = con.execute(
        "INSERT INTO entity_relationships (subject_entity_id, relation_type, object_entity_id, "
        "valid_from, valid_to, source_evidence_id, confidence) VALUES (?, 'exposed_to_commodity', ?, "
        "'2026-01-01', NULL, NULL, 0.8)",
        (cap_id, commodity_id),
    ).lastrowid
    con.commit()

    synthetic_note = cn.note_for_pair(con, "NASCON", "CAP", "2026-08-02")
    check("with a synthetic shared exposed_to_commodity edge to the same "
          "counterpart, note_for_pair() correctly finds exactly one shared "
          "exposure reason",
          len(synthetic_note.shared_exposures) == 1)
    if synthetic_note.shared_exposures:
        reason = synthetic_note.shared_exposures[0]
        check("the shared-exposure reason names the correct relation_type, "
              "counterpart, and both source relationship_ids -- fully traceable, "
              "never a bare number",
              reason.relation_type == "exposed_to_commodity"
              and reason.counterpart_canonical_name == "Brent Crude"
              and reason.ticker_a_relationship_id == rel_a_id
              and reason.ticker_b_relationship_id == rel_b_id)

    # A different relation_type to the same counterpart must NOT match --
    # confirms the module requires same-type AND same-counterpart, not just
    # same-counterpart.
    con.execute(
        "UPDATE entity_relationships SET relation_type='exposed_to_fx' WHERE relationship_id=?",
        (rel_b_id,),
    )
    con.commit()
    mismatched_note = cn.note_for_pair(con, "NASCON", "CAP", "2026-08-02")
    check("a shared counterpart with DIFFERING relation_types does NOT count as a "
          "shared exposure (same-type AND same-counterpart both required)",
          mismatched_note.shared_exposures == [])

    con.close()

    # --- 3. Mechanical guardrails ------------------------------------------
    note_fields = set(cn.CorrelationNote.__dataclass_fields__)
    reason_fields = set(cn.SharedExposureReason.__dataclass_fields__)
    forbidden = {"score", "rank", "weight", "strength", "priority", "correlation", "coefficient"}
    check("CorrelationNote carries no score/rank/weight/correlation-coefficient field",
          note_fields.isdisjoint(forbidden))
    check("SharedExposureReason carries no score/rank/weight/correlation-coefficient field",
          reason_fields.isdisjoint(forbidden))

    params = set(inspect.signature(cn.note_for_pair).parameters)
    check("note_for_pair() accepts no limit/sort/rank/threshold/plural-tickers "
          "parameter (confirms pairwise-only, never an all-pairs mode)",
          params.isdisjoint({"limit", "top_n", "sort_by", "rank_by", "threshold", "tickers"}))

    src_text = (ROOT / "src" / "ngxrot" / "fre" / "correlation_notes.py").read_text(encoding="utf-8")
    tree = ast.parse(src_text)
    write_verbs_found = any(
        isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.strip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for node in ast.walk(tree)
    )
    check("correlation_notes.py contains no INSERT/UPDATE/DELETE SQL statement "
          "anywhere (AST-verified) -- read-only by construction",
          not write_verbs_found)

    forbidden_imports = {"ngxrot.alpha_engine", "ngxrot.registry"}
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    check("correlation_notes.py imports neither ngxrot.alpha_engine nor "
          "ngxrot.registry (no path toward the quant engine's write boundary)",
          forbidden_imports.isdisjoint(imported_modules))

    # --- 4. the REAL production database was never touched ---------------------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged -- "
          "the synthetic entity/edges in Section 2 only ever existed on a "
          "disposable scratch copy",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
