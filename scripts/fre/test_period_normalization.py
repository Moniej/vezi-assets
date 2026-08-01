"""Standalone assertion-script tests for period_normalization.py, using
the real UCAP anchor (docs/fre_runs/fsi_phase2_execution_plan.md section 5).

  PYTHONPATH=src python scripts/fre/test_period_normalization.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.period_normalization import classify_period_type  # noqa: E402

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
    # --- the UCAP anchor: real, confirmed mislabeling ----------------------
    check("UCAP doc 4248 (2020-01-01 to 2020-09-30, headlined 'Q3 2020' in "
          "the real filing) classifies as '9M', NOT a standalone quarter -- "
          "the real bug this classifier exists to catch",
          classify_period_type("2020-01-01", "2020-09-30") == "9M")

    # --- all 15 real Phase 1 filings classify correctly, checked against
    # the real database, not hardcoded expectations -------------------------
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    expected = {
        4248: "9M", 6911: "FY", 10772: "FY",
        6664: "9M", 8009: "FY", 9357: "FY",
        4245: "9M", 6349: "H1", 7540: "H1",
        4508: "FY", 5911: "FY", 10115: "H1",
        8801: "H1", 9460: "FY", 10929: "FY",
    }
    for doc_id, expected_type in expected.items():
        row = con.execute(
            "SELECT DISTINCT period_start, period_end FROM extracted_facts WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
        actual = classify_period_type(row[0], row[1])
        check(f"doc {doc_id}: period_type={actual!r} matches expected {expected_type!r} "
              f"(span {row[0]} to {row[1]})", actual == expected_type)
    con.close()

    # --- standard quarters and half-years ----------------------------------
    check("Q1 (Jan-Mar)", classify_period_type("2024-01-01", "2024-03-31") == "Q1")
    check("Q2 (Apr-Jun)", classify_period_type("2024-04-01", "2024-06-30") == "Q2")
    check("Q3 (Jul-Sep)", classify_period_type("2024-07-01", "2024-09-30") == "Q3")
    check("Q4 (Oct-Dec)", classify_period_type("2024-10-01", "2024-12-31") == "Q4")
    check("H2 (Jul-Dec)", classify_period_type("2024-07-01", "2024-12-31") == "H2")

    # --- non-standard/ambiguous spans are left None, never guessed --------
    check("a cross-year span returns None (never guessed)",
          classify_period_type("2023-10-01", "2024-03-31") is None)
    check("a non-standard span (e.g. Feb-Aug) returns None (never guessed)",
          classify_period_type("2024-02-01", "2024-08-31") is None)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
