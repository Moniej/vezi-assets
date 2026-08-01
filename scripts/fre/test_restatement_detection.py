"""Standalone assertion-script tests for restatement_detection.py, using
the real CAP anchor (docs/fre_runs/fsi_phase2_execution_plan.md section 5).

SAFETY: the synthetic "comparative figure" fact is inserted ONLY into a
disposable scratch copy of the real database, never into production --
Phase 2's own extraction convention (like Phase 1's) never extracts a
filing's comparative prior-period column, so this exact conflict does not
occur naturally among real extracted facts; this test reproduces the real
CAP numbers on a scratch fixture specifically to validate the detection
logic itself.

  PYTHONPATH=src python scripts/fre/test_restatement_detection.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.restatement_detection import find_restatement_conflicts  # noqa: E402

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
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # --- NASCON permanent regression anchor (docs/fre_runs/
    # fsi_phase2_implementation_log.md Entry 4/5): the ORIGINAL
    # overlap-only rule falsely flagged NASCON's real FY2024 facts as
    # "restating" its own real H1 2024 facts, because the two periods
    # overlap (H1 is nested inside FY) even though they are legitimately
    # different reporting spans, not a restatement. Uses REAL production
    # data directly (read-only, no fixture needed) -- both filings and
    # both fact values already exist for real. This anchor is permanent:
    # any future change to find_restatement_conflicts must keep passing
    # it, exactly as the CAP anchor below must keep passing. -----------
    nascon_h1_assets = con.execute(
        "SELECT numeric_value FROM extracted_facts WHERE doc_id = 8801 AND fact_type = 'assets'"
    ).fetchone()
    nascon_fy_assets = con.execute(
        "SELECT numeric_value FROM extracted_facts WHERE doc_id = 9460 AND fact_type = 'assets'"
    ).fetchone()
    check("NASCON's real H1 2024 assets (doc 8801) and FY2024 assets (doc "
          "9460) are both on hand as expected, with different values (a "
          "half-year balance vs. a full-year one)",
          nascon_h1_assets is not None and nascon_fy_assets is not None
          and nascon_h1_assets[0] != nascon_fy_assets[0])
    conflicts_fy_assets = find_restatement_conflicts(
        con, ticker="NASCON", fact_type="assets",
        period_start="2024-01-01", period_end="2024-12-31",
        new_value=nascon_fy_assets[0],
    )
    check("NASCON's real FY2024 assets is NEVER flagged as restating its "
          "own real H1 2024 assets -- overlapping-but-unequal reporting "
          "spans are not a restatement (the false positive this "
          "architectural fix exists to prevent)",
          not conflicts_fy_assets)
    nascon_h1_cfo = con.execute(
        "SELECT numeric_value FROM extracted_facts WHERE doc_id = 8801 AND fact_type = 'cfo'"
    ).fetchone()
    nascon_fy_cfo = con.execute(
        "SELECT numeric_value FROM extracted_facts WHERE doc_id = 9460 AND fact_type = 'cfo'"
    ).fetchone()
    conflicts_fy_cfo = find_restatement_conflicts(
        con, ticker="NASCON", fact_type="cfo",
        period_start="2024-01-01", period_end="2024-12-31",
        new_value=nascon_fy_cfo[0],
    )
    check("same false-positive check repeated for NASCON's real cfo facts "
          "(H1 2024 doc 8801 vs. FY2024 doc 9460) -- also never flagged",
          nascon_h1_cfo is not None and nascon_fy_cfo is not None
          and not conflicts_fy_cfo)
    # confirm the real, already-extracted CAP FY2020 fact (doc 4508) is
    # exactly what Phase 1 recorded, before building the test fixture on it
    real_fact = con.execute(
        "SELECT numeric_value FROM extracted_facts WHERE doc_id = 4508 AND fact_type = 'revenue'"
    ).fetchone()
    check("CAP doc 4508's real, already-extracted FY2020 revenue is "
          "8,737,000,000 (Phase 1's own recorded value)",
          real_fact is not None and real_fact[0] == 8_737_000_000.0)
    con.close()

    # --- build the scratch fixture: copy the real DB, then insert ONE
    # synthetic fact reproducing doc 5911's real stated FY2020 COMPARATIVE
    # figure (8,876,000,000) -- a figure Phase 1 never actually extracted
    # as its own fact, since it never extracts comparative columns --------
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)
    con.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
        "period_start, period_end, extraction_confidence, grounding_check, extracted_at) "
        "VALUES (5911, 'revenue', 'TEST FIXTURE ONLY -- reproduces doc 5911 real stated "
        "FY2020 comparative figure for restatement-detection testing', 8876000000.0, "
        "'2020-01-01', '2020-12-31', 0.9, 'passed', '2026-08-01T00:00:00')"
    )
    con.commit()

    conflicts = find_restatement_conflicts(
        con, ticker="CAP", fact_type="revenue",
        period_start="2020-01-01", period_end="2020-12-31",
        new_value=8_876_000_000.0,
    )
    check("find_restatement_conflicts detects doc 4508's real fact (8,737mn) "
          "as conflicting with the synthetic 8,876mn comparative figure for "
          "the same ticker/fact_type/overlapping period",
          any(True for fid in conflicts if
              con.execute("SELECT doc_id FROM extracted_facts WHERE fact_id=?", (fid,)).fetchone()[0] == 4508))

    no_conflict = find_restatement_conflicts(
        con, ticker="CAP", fact_type="revenue",
        period_start="2020-01-01", period_end="2020-12-31",
        new_value=8_737_000_000.0,  # the SAME value as the real fact -- no conflict
    )
    check("an identical value (within tolerance) is NOT flagged as a conflict",
          not any(True for fid in no_conflict if
                  con.execute("SELECT doc_id FROM extracted_facts WHERE fact_id=?", (fid,)).fetchone()[0] == 4508))

    non_overlapping = find_restatement_conflicts(
        con, ticker="CAP", fact_type="revenue",
        period_start="2021-01-01", period_end="2021-12-31",  # FY2021, doesn't overlap FY2020
        new_value=999_999_999.0,
    )
    check("a non-overlapping period is never flagged, regardless of value "
          "difference", 4508 not in [
              con.execute("SELECT doc_id FROM extracted_facts WHERE fact_id=?", (fid,)).fetchone()[0]
              for fid in non_overlapping
          ])

    con.close()
    Path(scratch).unlink()
    Path(scratch).parent.rmdir()

    # --- confirm the real production database was never touched -----------
    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged", doc_count_after == doc_count_before)
    fact_count = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE description LIKE 'TEST FIXTURE ONLY%'"
    ).fetchone()[0]
    check("the synthetic test fixture fact was NEVER written to production "
          "(it only ever existed in the disposable scratch copy)", fact_count == 0)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
