"""FSI Phase 5: main validation harness runner
(docs/fre_runs/fsi_phase5_preregistration.md,
docs/fre_runs/fsi_phase5_implementation_log.md).

The single entry point an operator (or a future CI-style check) runs to
validate that the frozen FSI Phase 1-4 pipeline remains exactly as it
was: golden-snapshot reproducibility, cross-phase consistency, and
database immutability (row counts across ALL 29 tables + integrity/FK
checks, before and after this run). Read-only against production --
this script has no write path to `data/ngx.sqlite` at all.

  PYTHONPATH=src python scripts/fre/fsi_phase5_validate_pipeline.py
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


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(con)
    before_integrity = con.execute("PRAGMA integrity_check").fetchall()
    before_fk = con.execute("PRAGMA foreign_key_check").fetchall()

    overall_ok = True

    print("=== Component 1: golden-snapshot reproducibility ===")
    if not GOLDEN_PATH.exists():
        print(f"FAIL: golden snapshot not found at {GOLDEN_PATH}")
        overall_ok = False
    else:
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        live = compute_live_snapshot(con)
        diffs = compare_snapshots(golden, live)
        if diffs:
            print(f"FAIL: {len(diffs)} deviation(s) from the golden snapshot:")
            for d in diffs:
                print(f"  - {d}")
            overall_ok = False
        else:
            print(f"PASS: live output is byte-identical to the golden snapshot "
                  f"({live['extracted_facts_total_financial']} facts, "
                  f"{live['conclusions_total']} conclusions)")

    print("\n=== Component 2: cross-phase consistency (Phase 3 <-> Phase 4) ===")
    violations = verify_cross_phase_consistency(con)
    if violations:
        print(f"FAIL: {len(violations)} violation(s):")
        for v in violations:
            print(f"  - {v}")
        overall_ok = False
    else:
        print("PASS: 0 violations across all real tickers (full knowability at each "
              "ticker's own latest filing date; monotonicity across every real "
              "filing-date boundary)")

    con.close()

    print("\n=== Component 3: database immutability ===")
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    after_integrity = con.execute("PRAGMA integrity_check").fetchall()
    after_fk = con.execute("PRAGMA foreign_key_check").fetchall()
    table_diffs = diff_table_counts(before_counts, after_counts)
    if table_diffs:
        print(f"FAIL: row count changed in {len(table_diffs)} table(s): {table_diffs}")
        overall_ok = False
    else:
        print(f"PASS: all {len(before_counts)} tables' row counts unchanged before/after this run")
    if before_integrity != [("ok",)] or after_integrity != [("ok",)]:
        print(f"FAIL: integrity_check before={before_integrity} after={after_integrity}")
        overall_ok = False
    else:
        print("PASS: integrity_check 'ok' both before and after")
    if before_fk or after_fk:
        print(f"FAIL: foreign_key_check before={before_fk} after={after_fk}")
        overall_ok = False
    else:
        print("PASS: foreign_key_check clean both before and after")
    con.close()

    print(f"\n=== Overall: {'PASS' if overall_ok else 'FAIL'} ===")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
