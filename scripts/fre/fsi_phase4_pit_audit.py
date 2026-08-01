"""FSI Phase 4: mechanical PIT look-ahead audit
(docs/fre_runs/fsi_phase4_preregistration.md Area 3,
docs/fre_runs/fsi_phase4_implementation_log.md).

Read-only. For every one of the 15 real anchor documents' own
`filing_date`, tests `as_of()` at the date immediately BEFORE and AT that
filing_date for the document's own ticker -- 30 real test points, no
synthetic fixture needed. Reports any look-ahead violation (a conclusion
returned that depends on a not-yet-public filing); zero violations is
the pre-registered success criterion.

  PYTHONPATH=src python scripts/fre/fsi_phase4_pit_audit.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.pit_financial_memory import audit_no_lookahead  # noqa: E402

ANCHOR_DOC_IDS = (4248, 6911, 10772, 6664, 8009, 9357, 4245, 6349, 7540,
                   4508, 5911, 10115, 8801, 9460, 10929)


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    total_violations = []
    test_points = 0
    for doc_id in ANCHOR_DOC_IDS:
        ticker, filing_date = con.execute(
            "SELECT ticker, filing_date FROM documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        day_before = (date.fromisoformat(filing_date) - timedelta(days=1)).isoformat()
        for as_of_date in (day_before, filing_date):
            violations = audit_no_lookahead(con, ticker, as_of_date)
            test_points += 1
            status = "CLEAN" if not violations else f"{len(violations)} VIOLATION(S)"
            print(f"doc_id={doc_id} ticker={ticker} filing_date={filing_date} "
                  f"as_of={as_of_date}: {status}")
            total_violations.extend(violations)

    print(f"\n{test_points} real test points audited (one before + one at each of the 15 "
          f"anchor filings' own filing_date).")
    if total_violations:
        print(f"\n{len(total_violations)} LOOK-AHEAD VIOLATIONS FOUND:")
        for v in total_violations:
            print(f"  - {v}")
    else:
        print("\n0 look-ahead violations found across all real test points.")

    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    print(f"\ndocuments count unchanged: {doc_count_before == doc_count_after} "
          f"(this audit has no write path)")
    con.close()
    return 0 if not total_violations else 1


if __name__ == "__main__":
    sys.exit(main())
