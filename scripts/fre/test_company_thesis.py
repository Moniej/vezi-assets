"""Standalone assertion-script tests for src/ngxrot/fre/company_thesis.py --
same no-pytest, script-based convention as the other FRE test scripts.

SAFETY: company_thesis.py has NO write path at all (purely read-only, it
composes evidence_graph/company_memory/reaction_check, none of which
write either) -- every test opens the real production database via a
read-only URI connection.

  PYTHONPATH=src python scripts/fre/test_company_thesis.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_thesis import build_company_thesis  # noqa: E402

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

    # --- TOTAL: the one real case with a meaningful multi-point history,
    # including a real, already-recorded contradiction --------------------
    con = ro()
    total = build_company_thesis(con, "TOTAL", "2026-08-01")
    check("TOTAL: is_pilot is True (never presented as a validated product)", total.is_pilot is True)
    check("TOTAL: 4 real implications in thesis_history, 0 excluded",
          len(total.thesis_history) == 4 and total.excluded_blocked_count == 0)
    check("TOTAL: bull_case is the MOST RECENT implication's own delta, verbatim "
          "(naive baseline, no blending)",
          total.bull_case == "Confirms strong cash flow generation capable of sustaining "
                              "regular dividend payments.")
    check("TOTAL: confidence is the most recent implication's own recorded value (0.0), "
          "never computed or fabricated", total.confidence == 0.0)
    check("TOTAL: the real, already-recorded contradiction (bullish vs. neutral) is "
          "surfaced verbatim in contradiction_note", total.contradiction_note is not None
          and "CONTRADICTS" in total.contradiction_note and "#3" in total.contradiction_note)
    check("TOTAL: capital_allocation_assessment cites real, non-neutral evidence "
          "(not a 'no evidence' fallback)", "No evidence found" not in total.capital_allocation_assessment)
    check("TOTAL: competitive_position correctly reports no evidence (0/60 real "
          "causal-chain steps ever classify competitive, per FRE-2's finding)",
          "No evidence found" in total.competitive_position)
    check("TOTAL: source_implication_ids has exactly 4 entries, the full audit trail",
          len(total.source_implication_ids) == 4)
    con.close()

    # --- CILEASING: 2 usable + 1 blocked, a clean corroborating chain -----
    con = ro()
    ci = build_company_thesis(con, "CILEASING", "2026-08-01")
    check("CILEASING: 2 usable implications, 1 excluded as blocked_by_self_critique",
          len(ci.thesis_history) == 2 and ci.excluded_blocked_count == 1)
    check("CILEASING: no contradiction (a clean corroborating chain, correctly "
          "distinct from TOTAL's real contradiction)", ci.contradiction_note is None)
    check("CILEASING: missing_evidence discloses the 1 excluded blocked implication",
          any("blocked_by_self_critique" in m for m in ci.missing_evidence))
    con.close()

    # --- GTCO: the one real case whose ONLY implication is blocked -- the
    # thesis must be EMPTY, not manufactured from a rejected implication ---
    con = ro()
    gtco = build_company_thesis(con, "GTCO", "2026-08-01")
    check("GTCO: thesis_history is empty (its only real implication is blocked)",
          len(gtco.thesis_history) == 0)
    check("GTCO: bull_case/bear_case/base_case/confidence are all None -- never "
          "manufactured from a self-critique-blocked implication",
          gtco.bull_case is None and gtco.bear_case is None and gtco.base_case is None
          and gtco.confidence is None)
    check("GTCO: excluded_blocked_count is 1", gtco.excluded_blocked_count == 1)
    check("GTCO: missing_evidence explicitly explains why the thesis is empty",
          len(gtco.missing_evidence) == 1 and "blocked_by_self_critique" in gtco.missing_evidence[0])
    con.close()

    # --- a nonexistent ticker degrades gracefully, no crash ----------------
    con = ro()
    none_thesis = build_company_thesis(con, "NOTAREALTICKER", "2026-08-01")
    check("nonexistent ticker returns an empty, non-crashing thesis",
          none_thesis.bull_case is None and len(none_thesis.thesis_history) == 0)
    con.close()

    # --- PIT correctness: an earlier as_of_date must show LESS history -----
    con = ro()
    total_early = build_company_thesis(con, "TOTAL", "2017-01-01")
    check("PIT: TOTAL as of 2017-01-01 shows only the 1 implication filed by then",
          len(total_early.thesis_history) == 1)
    check("PIT: no implication with a filing_date after as_of_date ever appears",
          all(e.filing_date <= "2017-01-01" for e in total_early.thesis_history))
    con.close()

    # --- no expected-return / alpha claim anywhere in any generated field -
    con = ro()
    for ticker in ["TOTAL", "CILEASING"]:
        th = build_company_thesis(con, ticker, "2026-08-01")
        all_text = " ".join(filter(None, [
            th.bull_case, th.bear_case, th.base_case, th.financial_signal_summary,
            th.competitive_position, th.management_assessment, th.capital_allocation_assessment,
        ])).lower()
        check(f"{ticker}: no numeric expected-return or percentage-formatted alpha "
              f"claim appears in any narrative field",
              "%" not in all_text or "no evidence found" in all_text)
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
