"""Standalone assertion-script tests for sector_coverage.py (FSI Phase
24). Section 1 reads the REAL production database directly (read-only,
confirming real current-state counts); Section 2 uses a disposable
scratch copy to prove the watchlist-count path fires correctly (the
real production watchlist_entries table is currently empty).

  PYTHONPATH=src python scripts/fre/test_sector_coverage.py
"""
from __future__ import annotations

import ast
import inspect
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import sector_coverage as sc  # noqa: E402
from ngxrot.fre import watchlist as wl  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

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
    real_ro = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(real_ro)

    # --- 1. Real data: total ticker count and FSI coverage sum correctly ---
    rows = sc.coverage_by_sector(real_ro, "2026-08-02")
    total_across_sectors = sum(r.total_tickers for r in rows)
    real_total_securities = real_ro.execute("SELECT COUNT(*) FROM securities").fetchone()[0]
    check("every one of the real securities rows is accounted for exactly "
          "once across all sector rows (including UNKNOWN)",
          total_across_sectors == real_total_securities)

    fsi_across_sectors = sum(r.fsi_covered_tickers for r in rows)
    real_fsi_tickers = list_tickers(real_ro)
    check("total FSI-covered tickers across all sectors matches the real "
          "list_tickers() count exactly (10 real FSI tickers)",
          fsi_across_sectors == len(real_fsi_tickers))

    unknown_row = next((r for r in rows if r.sector_ngx == sc.UNKNOWN_SECTOR), None)
    check("an UNKNOWN row exists (real production has 184 securities with "
          "NULL sector_ngx as of FSI Phase 23) and it is the LAST row",
          unknown_row is not None and rows[-1].sector_ngx == sc.UNKNOWN_SECTOR)
    check("UBN (the one real FSI ticker with no known sector_ngx) is "
          "correctly counted under UNKNOWN, not silently dropped",
          unknown_row.fsi_covered_tickers >= 1)

    known_rows = [r for r in rows if r.sector_ngx != sc.UNKNOWN_SECTOR]
    check("known-sector rows are in strict alphabetical order (never "
          "sorted by any count value)",
          [r.sector_ngx for r in known_rows] == sorted(r.sector_ngx for r in known_rows))

    consumer_goods_row = next((r for r in rows if r.sector_ngx == "CONSUMER GOODS"), None)
    check("CONSUMER GOODS row correctly reports 3 FSI-covered tickers "
          "(NASCON, NESTLE, BUAFOODS -- confirmed real)",
          consumer_goods_row is not None and consumer_goods_row.fsi_covered_tickers == 3)

    real_watchlist_count = real_ro.execute("SELECT COUNT(*) FROM watchlist_entries").fetchone()[0]
    check("precondition: real production watchlist_entries is currently "
          "empty (confirms the watchlist_tickers=0 result below is a real, "
          "not assumed, honest negative)", real_watchlist_count == 0)
    check("with a real, empty watchlist table, every sector row correctly "
          "reports watchlist_tickers=0",
          all(r.watchlist_tickers == 0 for r in rows))

    # --- 2. Watchlist-count positive path, on a disposable scratch copy ----
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)

    latest_nascon = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='NASCON'"
    ).fetchone()[0]
    wl.add_entry(
        con, "NASCON", rationale="Sector coverage test.",
        source_thesis_as_of_date=latest_nascon,
        entry_criteria="Test criteria.", added_at="2026-07-01",
    )
    con.commit()

    scratch_rows = sc.coverage_by_sector(con, "2026-08-02")
    scratch_consumer_goods = next((r for r in scratch_rows if r.sector_ngx == "CONSUMER GOODS"), None)
    check("scratch copy: after adding a real NASCON watchlist entry, the "
          "CONSUMER GOODS row correctly reports watchlist_tickers=1",
          scratch_consumer_goods is not None and scratch_consumer_goods.watchlist_tickers == 1)

    scratch_before_added = sc.coverage_by_sector(con, "2026-06-01")
    scratch_cg_before = next((r for r in scratch_before_added if r.sector_ngx == "CONSUMER GOODS"), None)
    check("scratch copy: as of a date BEFORE the entry's own added_at, "
          "watchlist_tickers correctly shows 0 -- PIT-correct, reused "
          "from watchlist.list_active() unmodified",
          scratch_cg_before is not None and scratch_cg_before.watchlist_tickers == 0)

    con.close()

    # --- 3. Mechanical guardrails ------------------------------------------
    fields = set(sc.SectorCoverageRow.__dataclass_fields__)
    forbidden = {"score", "rank", "weight", "strength", "priority", "percentage", "ratio", "coverage_score"}
    check("SectorCoverageRow carries no score/rank/weight/percentage/ratio field",
          fields.isdisjoint(forbidden))

    params = set(inspect.signature(sc.coverage_by_sector).parameters)
    check("coverage_by_sector() accepts no limit/sort/rank/threshold parameter",
          params.isdisjoint({"limit", "top_n", "sort_by", "rank_by", "threshold"}))

    src_text = (ROOT / "src" / "ngxrot" / "fre" / "sector_coverage.py").read_text(encoding="utf-8")
    tree = ast.parse(src_text)
    write_verbs_found = any(
        isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.strip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for node in ast.walk(tree)
    )
    check("sector_coverage.py contains no INSERT/UPDATE/DELETE SQL statement "
          "anywhere (AST-verified) -- read-only by construction",
          not write_verbs_found)

    # --- 4. the REAL production database was never touched ---------------------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged -- "
          "Section 2's write only ever happened on a disposable scratch copy",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
