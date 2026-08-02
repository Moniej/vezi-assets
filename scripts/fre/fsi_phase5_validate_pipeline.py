"""FSI Phase 5: main validation harness runner
(docs/fre_runs/fsi_phase5_preregistration.md,
docs/fre_runs/fsi_phase5_implementation_log.md; Component 4 added FSI
Phase 16, docs/fre_runs/fsi_phase16_preregistration.md).

The single entry point an operator (or a future CI-style check) runs to
validate that the frozen FSI pipeline remains exactly as it was:
golden-snapshot reproducibility, cross-phase consistency, database
immutability, and (since Phase 16) composition-layer smoke coverage
across every real ticker. Read-only against production -- this script
has no write path to `data/ngx.sqlite` at all.

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
from ngxrot.fre import company_memory_360, company_research_dossier, company_thesis_360, entity_context  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.financial_reasoning_report import render_report  # noqa: E402
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

    print("\n=== Component 4: composition-layer smoke coverage (added FSI Phase 16) ===")
    # Confirms every composition/reporting layer (Phase 6/7/8/10/11) runs
    # without exception for EVERY real ticker (discovered dynamically via
    # list_tickers(), never a hardcoded list) -- the exact class of check
    # that would have caught Phase 13 adding 5 tickers that no composition
    # layer had ever been exercised against, if it had existed sooner. A
    # coarse smoke check only (no exception): each phase's own dedicated
    # test file already carries the detailed equivalence/PIT assertions --
    # duplicating those here would violate "reuse, don't duplicate."
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    smoke_failures: list[str] = []
    tickers = list_tickers(con)
    for ticker in tickers:
        latest = con.execute(
            "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=?", (ticker,),
        ).fetchone()[0]
        if latest is None:
            smoke_failures.append(f"{ticker}: no extracted_facts filing date found")
            continue
        try:
            memory = company_memory_360.as_of(con, ticker, latest)
            render_report(memory)
            company_thesis_360.as_of(con, ticker, latest)
            entity_context.get_entity_context(con, ticker, latest)
            dossier = company_research_dossier.build_dossier(con, ticker, latest)
            company_research_dossier.render_dossier(dossier)
        except Exception as e:  # noqa: BLE001
            smoke_failures.append(f"{ticker}: {type(e).__name__}: {e}")
    con.close()
    if smoke_failures:
        print(f"FAIL: {len(smoke_failures)} ticker(s) raised an exception in the "
              f"composition chain:")
        for f in smoke_failures:
            print(f"  - {f}")
        overall_ok = False
    else:
        print(f"PASS: all {len(tickers)} real tickers pass through company_memory_360 -> "
              f"render_report -> company_thesis_360 -> entity_context -> "
              f"company_research_dossier (build+render) with zero exceptions")

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
        print(f"PASS: all {len(before_counts)} tables' row counts unchanged before/after this "
              f"ENTIRE run (Components 1, 2, and 4 included, not just up to Component 2)")
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
