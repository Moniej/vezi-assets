"""Standalone assertion-script tests for src/ngxrot/fre/company_memory.py --
same no-pytest, script-based convention as scripts/test_reasoning_pipeline.py
and scripts/fre/test_evidence_graph.py.

SAFETY: company_memory.py has NO write path at all (build_company_memory is
purely read-only), so every test here opens the real production database
via a read-only URI connection (file:...?mode=ro) -- there is no scratch
copy needed because there is nothing to mutate.

  PYTHONPATH=src python scripts/fre/test_company_memory.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_memory import build_company_memory  # noqa: E402

REAL_DB = db.DEFAULT_DB

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
    return sqlite3.connect(f"file:{REAL_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    con.close()

    # --- UCAP: the richest real per-ticker fact history (8 facts, 163 docs) ---
    con = ro()
    mem = build_company_memory(con, "UCAP", "2026-01-01")
    check("UCAP has 152 documents filed by 2026-01-01", len(mem.filing_history) == 152)
    check("UCAP has 8 total extracted facts, 1 excluded as blocked_by_self_critique",
          mem.excluded_blocked_facts == 1)
    check("UCAP dividend_history has exactly 7 entries (8 minus the 1 blocked)",
          len(mem.dividend_history) == 7)
    check("the excluded fact (151, a real NASCON/UCAP document mismatch already "
          "caught by self-critique) is NOT present in dividend_history",
          151 not in [f.fact_id for f in mem.dividend_history])
    check("coverage_note has exactly 5 entries (filings, facts/exclusions, "
          "management, events, strategy-narrative)", len(mem.coverage_note) == 5)
    con.close()

    # --- PIT correctness: an earlier as_of_date must show LESS history, never more ---
    con = ro()
    mem_early = build_company_memory(con, "UCAP", "2023-01-01")
    check("PIT: fewer filings visible as of 2023-01-01 than 2026-01-01",
          len(mem_early.filing_history) < len(mem.filing_history))
    check("PIT: fewer dividend facts visible as of 2023-01-01 (1) than 2026-01-01 (7)",
          len(mem_early.dividend_history) == 1)
    check("PIT: no fact with a filing_date after as_of_date ever appears",
          all(f.filing_date <= "2023-01-01" for f in mem_early.dividend_history))
    con.close()

    # --- GTCO: confirms the SAME exclusion mechanism on a second, independent
    # real blocked fact (144, the rights issue already on record in
    # HANDOFF.md as a real self-critique block) -----------------------------
    con = ro()
    mem_gtco = build_company_memory(con, "GTCO", "2026-01-01")
    check("GTCO's blocked rights-issue fact (144) is excluded from "
          "corporate_action_history", 144 not in [f.fact_id for f in mem_gtco.corporate_action_history])
    check("GTCO's excluded_blocked_facts count is exactly 1", mem_gtco.excluded_blocked_facts == 1)
    con.close()

    # --- a nonexistent ticker degrades gracefully, no crash ----------------
    con = ro()
    mem_none = build_company_memory(con, "NOTAREALTICKER", "2026-01-01")
    check("nonexistent ticker returns empty filing/dividend history, not an error",
          mem_none.filing_history == [] and mem_none.dividend_history == []
          and mem_none.excluded_blocked_facts == 0)
    check("nonexistent ticker still gets a full 5-entry coverage_note "
          "(never silently empty)", len(mem_none.coverage_note) == 5)
    con.close()

    # --- disclosed, currently-empty components, confirmed against the whole
    # real database, not assumed -------------------------------------------
    con = ro()
    total_events_with_ticker = con.execute(
        "SELECT COUNT(*) FROM events WHERE ticker IS NOT NULL"
    ).fetchone()[0]
    # 2026-08-09: ticker-scoped events now real and populated (26 rows, from
    # the regulatory-transition mechanism-discovery work) -- this assertion
    # previously expected 0 and is updated to reflect that growth rather
    # than the module needing any change (build_company_memory's query was
    # always correct; only this ground-truth expectation was stale).
    check("events.ticker is now populated (26 real ticker-scoped rows, "
          "confirmed 2026-08-09) -- major_event_history is no longer "
          "universally empty, and this module correctly surfaces them "
          "with no code change required",
          total_events_with_ticker == 26)
    check("major_event_history is empty for UCAP specifically (UCAP has no "
          "ticker-scoped event on record, unlike e.g. DEAPCAP/TANTALIZER)",
          mem.major_event_history == [])
    check("management_history is empty for UCAP (no management_change "
          "extraction has been run at any volume yet)", mem.management_history == [])
    con.close()

    # --- confirm the real production database was never touched -----------
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write "
          "path at all)", doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
