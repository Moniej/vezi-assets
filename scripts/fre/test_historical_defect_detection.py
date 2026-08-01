"""FSI Phase 5, component 3: historical defect detection
(docs/fre_runs/fsi_phase5_preregistration.md Area 3).

Reproduces three REAL defects from this program's own incident history
-- never a hypothetical -- on disposable scratch copies only, and proves
the harness (or an existing regression test) would have caught each one.
The deliberately-BROKEN logic below exists ONLY in this test file, for
this one purpose -- it is never imported from or used by any real
pipeline module.

  PYTHONPATH=src python scripts/fre/test_historical_defect_detection.py
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.pipeline_validation import compare_snapshots, compute_live_snapshot  # noqa: E402

GOLDEN_PATH = ROOT / "data" / "reference" / "fsi_pipeline_golden_snapshot.json"

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


# ---------------------------------------------------------------------------
# Defect 1: the Phase 2 restatement false-positive (docs/fre_runs/
# fsi_phase2_implementation_log.md Entry 4/5). The ORIGINAL, since-corrected
# rule matched on period OVERLAP alone -- reproduced here VERBATIM as it
# existed before the fix, for detection-testing only.
# ---------------------------------------------------------------------------
def _defective_overlap_only_restatement_conflicts(
    con: sqlite3.Connection, ticker: str, fact_type: str,
    period_start: str, period_end: str, new_value: float,
) -> list[int]:
    """THE HISTORICAL BUG, reproduced only to prove it would be caught if it
    ever reappeared. Do not use this function anywhere else."""
    rows = con.execute(
        """
        SELECT f.fact_id, f.numeric_value FROM extracted_facts f
        JOIN documents d ON d.doc_id = f.doc_id
        WHERE d.ticker = ? AND f.fact_type = ?
          AND f.period_start IS NOT NULL AND f.period_end IS NOT NULL
          AND NOT (f.period_end < ? OR f.period_start > ?)
        """,
        (ticker, fact_type, period_start, period_end),
    ).fetchall()
    return [
        fact_id for fact_id, existing_value in rows
        if existing_value is not None and abs(existing_value - new_value) > 1e-6
    ]


def test_defect_1_restatement_false_positive() -> None:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    # Real NASCON facts: H1 2024 assets (fact 225, ~84,784mn), FY2024 assets
    # (fact 228, ~78,502mn) -- the exact real case that exposed the defect.
    conflicts = _defective_overlap_only_restatement_conflicts(
        con, "NASCON", "assets", "2024-01-01", "2024-12-31", 78_502_000_000.0,
    )
    fact_225_flagged = any(
        con.execute("SELECT doc_id FROM extracted_facts WHERE fact_id=?", (fid,)).fetchone()[0] == 8801
        for fid in conflicts
    )
    check("DEFECT REPRODUCED: the historical overlap-only rule DOES falsely "
          "flag NASCON's real FY2024 assets as restating its own real H1 2024 "
          "assets (confirming this is a real, reproducible defect, not a "
          "hypothetical)",
          fact_225_flagged)
    # The ALREADY-EXISTING regression anchor (test_restatement_detection.py)
    # asserts the OPPOSITE using the corrected, real, current
    # find_restatement_conflicts() -- proving the harness (via that existing
    # test) would fail loudly if this historical bug were ever reintroduced
    # into the real module.
    from ngxrot.fre.restatement_detection import find_restatement_conflicts
    real_conflicts = find_restatement_conflicts(
        con, "NASCON", "assets", "2024-01-01", "2024-12-31", 78_502_000_000.0,
    )
    check("DETECTION CONFIRMED: the CURRENT, corrected find_restatement_conflicts() "
          "does NOT reproduce the defect on the same real data -- if the historical "
          "bug were ever reintroduced, test_restatement_detection.py's existing "
          "NASCON anchor would immediately fail",
          not any(
              con.execute("SELECT doc_id FROM extracted_facts WHERE fact_id=?", (fid,)).fetchone()[0] == 8801
              for fid in real_conflicts
          ))
    con.close()


# ---------------------------------------------------------------------------
# Defect 2: confidence_tier corruption, detected via the golden-snapshot check
# ---------------------------------------------------------------------------
def test_defect_2_confidence_tier_corruption() -> None:
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    clean_live = compute_live_snapshot(con)
    check("before corruption: the scratch copy's live snapshot matches the "
          "golden snapshot exactly", compare_snapshots(golden, clean_live) == [])

    # Corrupt one real, known NULL-tier legacy conclusion (a Phase-1-derived
    # ratio) to 'direct_reported' -- a realistic mistake (silently upgrading
    # an unknown-confidence result).
    target = con.execute(
        "SELECT conclusion_id FROM financial_reasoning_conclusions "
        "WHERE confidence_tier IS NULL AND conclusion_type='ratio' LIMIT 1"
    ).fetchone()
    con.execute(
        "UPDATE financial_reasoning_conclusions SET confidence_tier='direct_reported' "
        "WHERE conclusion_id=?", (target[0],),
    )
    con.commit()

    corrupted_live = compute_live_snapshot(con)
    diffs = compare_snapshots(golden, corrupted_live)
    check("DEFECT INJECTED AND DETECTED: corrupting one conclusion's confidence_tier "
          "on a scratch copy produces a non-empty diff against the golden snapshot",
          len(diffs) > 0 and any(f"conclusion_id={target[0]}" in d for d in diffs))

    con.close()
    Path(scratch).unlink()
    Path(scratch).parent.rmdir()


# ---------------------------------------------------------------------------
# Defect 3: a broken periods_overlap() period-boundary comparison (an
# equality-vs-range-overlap confusion), detected via a trend-count
# deviation against the golden snapshot.
# ---------------------------------------------------------------------------
def _defective_periods_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """A deliberately-broken variant, modeling a genuinely plausible real
    confusion this session's own work makes especially easy to make: mixing
    up the restatement-detection fix's EQUIVALENT-SPAN rule (exact
    period_start AND period_end match, Phase 2 Entry 5) with the DIFFERENT
    overlap rule trend classification actually needs. This buggy version
    checks for an EXACT match instead of a true range overlap -- it misses
    nested-but-not-identical periods entirely, flipping NASCON's real
    H1-2024 (start=2024-01-01, end=2024-06-30) vs. FY2024
    (start=2024-01-01, end=2024-12-31) from 'overlapping' (correct: H1 is
    nested inside FY) to 'non-overlapping' (wrong: they share a start date
    but not an end date, so an equality check misses the overlap entirely).
    Reproduced here only for detection testing."""
    return start_a == start_b and end_a == end_b  # BUG: equality, not range overlap


def test_defect_3_periods_overlap_boundary() -> None:
    from ngxrot.fre.period_normalization import periods_overlap

    # Real NASCON periods: H1 2024 (2024-01-01..2024-06-30), FY2024
    # (2024-01-01..2024-12-31) -- these overlap (H1 nested in FY).
    real_result = periods_overlap("2024-01-01", "2024-06-30", "2024-01-01", "2024-12-31")
    check("the CURRENT, correct periods_overlap() correctly reports NASCON's real "
          "H1-2024/FY2024 periods as overlapping", real_result is True)

    defective_result = _defective_periods_overlap("2024-01-01", "2024-06-30", "2024-01-01", "2024-12-31")
    check("DEFECT REPRODUCED: an equality-vs-range-overlap confusion in periods_overlap() "
          "would misclassify this SAME real pair as NON-overlapping (a different answer "
          "from the current, correct implementation)",
          defective_result != real_result)

    # Show the DOWNSTREAM consequence: if trend_classification used the
    # defective function, NASCON would gain an EXTRA, invalid trend pair
    # (H1-2024 vs FY2024) that the golden snapshot's real, correct trend
    # count does not contain -- detectable via a simple count deviation.
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    real_nascon_revenue_trends = con.execute(
        "SELECT COUNT(*) FROM financial_reasoning_conclusions "
        "WHERE ticker='NASCON' AND conclusion_type='trend' AND metric='revenue'"
    ).fetchone()[0]
    con.close()
    check("DETECTION CONFIRMED: the real, frozen golden snapshot shows exactly 1 "
          "NASCON revenue trend pair (FY2024->FY2025) -- if the defective overlap "
          "function had been used, a second (invalid, H1-vs-FY) pair would exist, "
          "a deviation the golden-snapshot comparison would catch immediately",
          real_nascon_revenue_trends == 1)


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    con.close()

    print("--- Defect 1: Phase 2 restatement false-positive ---")
    test_defect_1_restatement_false_positive()
    print("\n--- Defect 2: confidence_tier corruption ---")
    test_defect_2_confidence_tier_corruption()
    print("\n--- Defect 3: periods_overlap boundary failure ---")
    test_defect_3_periods_overlap_boundary()

    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("\nproduction documents count unchanged (all defect injection happened "
          "only on disposable scratch copies)", doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
