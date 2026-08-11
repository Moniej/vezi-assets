"""Decision Intelligence Phase 15: tests for company_intelligence_bundle.py.

  PYTHONPATH=src python scripts/fre/test_company_intelligence_bundle.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_intelligence_bundle import (  # noqa: E402
    build_intelligence_bundle, what_is_happening,
)

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

    for t in ["CAP", "TOTAL"]:
        b = build_intelligence_bundle(con, t, AS_OF, PRIOR, intelligence_cache=cache,
                                       include_portfolio_note=False)
        check(f"{t}: bundle.ticker/as_of_date/prior_date echo the request",
              b.ticker == t and b.as_of_date == AS_OF and b.prior_date == PRIOR)
        check(f"{t}: bundle.state is a real CompanyState for the CURRENT as_of_date",
              b.state.as_of_date == AS_OF)
        check(f"{t}: bundle.prior_state is a real CompanyState for the PRIOR date",
              b.prior_state.as_of_date == PRIOR)
        check(f"{t}: bundle.ranked_changes is CRITICAL/HIGH-first sorted",
              [a.level for a in b.ranked_changes] ==
              sorted([a.level for a in b.ranked_changes],
                     key=lambda l: -{"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}[l]))
        narrative = what_is_happening(b)
        check(f"{t}: what_is_happening() renders a real, non-empty narrative",
              isinstance(narrative, str) and len(narrative) > 20)
        check(f"{t}: narrative contains the overall confidence dimension verbatim",
              b.confidence.overall in narrative)
        if b.thesis.contradiction_note:
            check(f"{t}: an active contradiction_note is PRESERVED in the narrative, not "
                  f"silently dropped", "CONTRADICTION" in narrative)

    # --- every change in ranked_changes cites a real source string, so a
    # user could trace "why" back to the exact originating module/fact ------
    b_cap = build_intelligence_bundle(con, "CAP", AS_OF, PRIOR, intelligence_cache=cache,
                                       include_portfolio_note=False)
    check("CAP: every ranked change's underlying DetectedChange has a real, non-empty source",
          all(a.change.source for a in b_cap.ranked_changes))

    # --- include_portfolio_note=False skips cross_reference() cleanly,
    # never crashes, and discloses the skip in the note's own rationale ----
    check("CAP: portfolio_note.rationale discloses it was skipped when "
          "include_portfolio_note=False", "skipped" in (b_cap.portfolio_note.rationale or ""))

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
