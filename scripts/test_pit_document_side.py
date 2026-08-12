"""Look-ahead-trap tests for the document/FRE side's point-in-time
integrity (2026-08-11, HANDOFF.md, Priority 5). Mirrors
phase1_smoke_test.py's pattern (prove a lookahead trap is blocked) but
for entity_relationships/peer_propagations/facts, which had NO date
filtering at all before this fix -- confirmed by direct query against the
real database (entity_relationships.valid_from genuinely spans
2020-2026), then fixed.

Read-only against the real production DB, plus one synthetic-DB check
for peer propagations (no real propagated implication exists in
production yet, per direct query before writing this test).

  PYTHONPATH=src python scripts/test_pit_document_side.py
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.retrieval import find_entity_relationships, find_peer_propagations  # noqa: E402
from ngxrot.documents.context import build_reasoning_context  # noqa: E402
from ngxrot.research_query import QuerySpec, execute  # noqa: E402

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

    # --- entity_relationships: real look-ahead trap on the real database ----
    unfiltered = find_entity_relationships(con, limit=200)
    check("sanity: real entity_relationships genuinely span multiple years "
         "(the look-ahead trap this test proves is blocked is real, not hypothetical)",
         any(r["valid_from"] and r["valid_from"] < "2021-01-01" for r in unfiltered)
         and any(r["valid_from"] and r["valid_from"] > "2026-01-01" for r in unfiltered))

    as_of_2021 = find_entity_relationships(con, as_of="2021-01-01", limit=200)
    check("LOOKAHEAD TRAP BLOCKED: as_of='2021-01-01' excludes every relationship "
         "whose valid_from is after that date",
         all(r["valid_from"] is None or r["valid_from"] <= "2021-01-01" for r in as_of_2021))
    check("as_of filtering is not simply returning everything (real rows were excluded)",
         len(as_of_2021) < len(unfiltered))
    check("as_of filtering is not simply returning nothing (real rows survived)",
         len(as_of_2021) > 0)

    # --- same trap via the research_query.py entity_relationships bridge ----
    # NCR has 3 real entity_relationships rows, all valid_from='2026-01-27'
    # (confirmed by direct query before writing this test).
    r_before = execute(con, QuerySpec(query_type="entity_relationships", entities=["NCR"],
                                      as_of="2026-01-01"), reg=None, log=False)
    r_after = execute(con, QuerySpec(query_type="entity_relationships", entities=["NCR"],
                                     as_of="2026-06-01"), reg=None, log=False)
    check("research_query.py: entity_relationships query type respects as_of "
         "(NCR's 3 real relationships, valid_from=2026-01-27, are excluded before "
         "that date and included after)",
         r_before.row_count == 0 and r_after.row_count == 3)

    # --- build_reasoning_context: the core reasoning engine itself --------
    ctx_old = build_reasoning_context(con, "NCR", as_of="2026-01-01")
    ctx_new = build_reasoning_context(con, "NCR", as_of="2026-06-01")
    check("build_reasoning_context: entity_relationships now genuinely differ "
         "between a historical as_of and today for the same ticker (was previously "
         "IDENTICAL regardless of as_of -- the exact bug this fix closes)",
         len(ctx_old.entity_relationships) < len(ctx_new.entity_relationships))

    # --- query_facts: as_of alone (no explicit end) now bounds results ------
    # NASCON has real extracted_facts spanning 2023-03-02 to 2026-04-28
    # (confirmed by direct query before writing this test).
    fr = execute(con, QuerySpec(query_type="facts", entities=["NASCON"], as_of="2023-06-01"),
                reg=None, log=False)
    fr_full = execute(con, QuerySpec(query_type="facts", entities=["NASCON"]), reg=None, log=False)
    check("LOOKAHEAD TRAP BLOCKED: research_query.py's facts query type now honors as_of "
         "even with no explicit end (previously returned every fact regardless of date)",
         fr.row_count > 0 and fr.row_count < fr_full.row_count)
    check("query_facts: every returned fact's filing_date is <= as_of, none from the future",
         (fr.observations["filing_date"] <= "2023-06-01").all())

    con.close()

    # --- peer_propagations: synthetic DB (none exist in production yet) ----
    scratch_dir = Path(tempfile.mkdtemp())
    scon = db.init_db(scratch_dir / "ngx.sqlite", seed=False)
    scon.execute("INSERT INTO securities (ticker, name, board) VALUES "
                "('AAA', 'AAA Plc', 'main'), ('BBB', 'BBB Plc', 'main')")
    cur = scon.execute("INSERT INTO sources (name, kind, reliability, base_confidence) "
                       "VALUES ('t','company_filing','primary',0.85)")
    sid = cur.lastrowid
    scon.execute("INSERT INTO documents (doc_id, ticker, doc_type, source_type, filing_date, "
                "retrieved_date, local_path, source_confidence, source_id, as_of_date) "
                "VALUES (1,'AAA','earnings','filing','2026-01-01','2026-01-01','x',0.85,?,'2026-01-01')",
                (sid,))
    fact_id = scon.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, extraction_confidence, "
        "extracted_at) VALUES (1,'earnings','test fact',1.0,'2026-01-01')").lastrowid
    src_impl = scon.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "generated_at) VALUES (?,'AAA','short','small',0.3,'x','bullish','no_action',"
        "'draft_pending_self_critique','2026-01-01')", (fact_id,)
    ).lastrowid
    scon.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "generated_at, propagated_from_implication_id) VALUES "
        "(?,'BBB','short','small',0.15,'x','bullish','no_action','under_review',"
        "'2026-06-01',?)", (fact_id, src_impl))
    scon.commit()

    early = find_peer_propagations(scon, "BBB", as_of="2026-03-01")
    late = find_peer_propagations(scon, "BBB", as_of="2026-12-01")
    unfiltered_prop = find_peer_propagations(scon, "BBB")
    check("find_peer_propagations: as_of='2026-03-01' excludes a propagation "
         "generated 2026-06-01 (after that date)", len(early) == 0)
    check("find_peer_propagations: as_of='2026-12-01' includes it (generated before)",
         len(late) == 1)
    check("find_peer_propagations: no as_of (default) preserves prior unfiltered behavior",
         len(unfiltered_prop) == 1)

    scon.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
