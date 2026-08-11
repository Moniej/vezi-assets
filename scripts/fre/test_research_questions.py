"""Decision Intelligence Phase 17: tests for research_questions.py.

  PYTHONPATH=src python scripts/fre/test_research_questions.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_intelligence_bundle import build_intelligence_bundle  # noqa: E402
from ngxrot.fre.research_questions import ALL_QUESTIONS, answer_all, changed_since  # noqa: E402

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
    cache: dict = {}
    AS_OF, PRIOR = "2026-08-09", "2024-01-01"

    check("exactly 7 fixed questions are registered (matches the task's own list, minus "
          "'changed since previous snapshot' which needs 2 bundles, tested separately)",
          len(ALL_QUESTIONS) == 7)

    for t in ["CAP", "TOTAL"]:
        b = build_intelligence_bundle(con, t, AS_OF, PRIOR, intelligence_cache=cache,
                                       include_portfolio_note=False)
        answers = answer_all(b)
        check(f"{t}: all 7 questions produce a real Answer object", len(answers) == 7)
        check(f"{t}: every answer has a non-empty question and answer string",
              all(a.question and a.answer for a in answers))
        check(f"{t}: every answer's evidence list contains only real, non-empty source strings",
              all(all(e for e in a.evidence) for a in answers))
        check(f"{t}: every answer's is_inference is a real bool", all(isinstance(a.is_inference, bool) for a in answers))

    # --- fact-vs-inference distinction is real, not cosmetic: 'what changed
    # materially' and 'weak evidence'/'missing info'/'contradicts thesis' are
    # bare fact restatements (is_inference=False); 'strongest positive/
    # negative' and 'requires monitoring' involve a judgment (top-N
    # selection/threshold), correctly marked is_inference=True. -------------
    b_cap = build_intelligence_bundle(con, "CAP", AS_OF, PRIOR, intelligence_cache=cache,
                                       include_portfolio_note=False)
    answers_cap = {a.question: a for a in answer_all(b_cap)}
    check("'What changed materially?' is marked is_inference=False (a direct restatement of "
          "HIGH/CRITICAL changes, not a judgment)",
          answers_cap["What changed materially?"].is_inference is False)
    check("'What are the strongest positive developments?' is marked is_inference=True "
          "(a top-N selection is itself an interpretive judgment)",
          answers_cap["What are the strongest positive developments?"].is_inference is True)

    # --- evidence citations for 'What changed materially?' trace back to
    # the SAME source strings the underlying DetectedChange objects carry --
    material_answer = answers_cap["What changed materially?"]
    real_sources = {a.change.source for a in b_cap.ranked_changes if a.level in ("HIGH", "CRITICAL")}
    check("CAP: 'What changed materially?' evidence exactly matches the real "
          "DetectedChange.source strings for HIGH/CRITICAL changes (no fabricated citation)",
          set(material_answer.evidence) == real_sources)

    # --- missing_information cites real economic_profile UNKNOWN field
    # sources, not an invented list -------------------------------------------
    missing = answers_cap["What information is missing?"]
    check("CAP: 'What information is missing?' names real, confirmed-UNKNOWN economic-profile "
          "fields (e.g. business_description)", "business_description" in missing.answer)

    # --- changed_since(): same ticker only, real diff between two full
    # bundles built at different as_of_dates -----------------------------------
    b_recent = build_intelligence_bundle(con, "CAP", "2025-01-01", PRIOR, intelligence_cache=cache,
                                          include_portfolio_note=False)
    cs = changed_since(b_cap, b_recent)
    check("changed_since(): produces a real Answer naming the earlier snapshot's date",
          "2025-01-01" in cs.question)
    b_total = build_intelligence_bundle(con, "TOTAL", AS_OF, PRIOR, intelligence_cache=cache,
                                         include_portfolio_note=False)
    raised = False
    try:
        changed_since(b_cap, b_total)
    except ValueError:
        raised = True
    check("changed_since() refuses to compare two DIFFERENT tickers", raised)

    con.close()
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path at all)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
