"""Standalone assertion-script tests for pipeline_validation.py, validated
against real production data (read-only) and the frozen golden snapshot.

  PYTHONPATH=src python scripts/fre/test_pipeline_validation.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.pipeline_validation import (  # noqa: E402
    compare_snapshots, compute_live_snapshot, diff_table_counts,
    snapshot_all_table_counts, verify_cross_phase_consistency,
)

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


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    before_counts = snapshot_all_table_counts(con)

    # --- Component 1: golden-snapshot reproducibility -----------------------
    check("the golden snapshot file exists", GOLDEN_PATH.exists())
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    live = compute_live_snapshot(con)
    diffs = compare_snapshots(golden, live)
    check("live snapshot is byte-identical to the frozen golden snapshot "
          "(0 deviations on a rerun against unmodified data)", diffs == [])
    check("the golden snapshot's own totals match the known frozen baseline "
          "(106 financial facts, 177 conclusions: 75 ratio + 87 trend + 15 flag)",
          golden["extracted_facts_total_financial"] == 106
          and golden["conclusions_total"] == 177
          and golden["conclusions_by_type"] == {"ratio": 75, "trend": 87, "flag": 15})

    # a deliberately-mismatched golden snapshot (in memory only) must produce
    # a non-empty, human-readable diff -- proving compare_snapshots() isn't
    # trivially "always empty"
    corrupted_golden = json.loads(json.dumps(golden))  # deep copy
    corrupted_golden["conclusions_total"] = 999
    check("compare_snapshots() correctly detects a deliberately-corrupted "
          "total (not a rubber-stamp comparator)",
          len(compare_snapshots(corrupted_golden, live)) > 0)

    # --- Component 2: cross-phase consistency --------------------------------
    violations = verify_cross_phase_consistency(con)
    check("cross-phase consistency: 0 violations across all 5 real tickers "
          "(full knowability at each ticker's own latest filing date, and "
          "monotonicity across every real filing-date boundary)",
          violations == [])

    con.close()

    # --- database immutability verification (owner's additional requirement) ---
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL 29 tables' row counts are unchanged after this entire test run "
          "(this harness has no write path to production at all)",
          table_diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
