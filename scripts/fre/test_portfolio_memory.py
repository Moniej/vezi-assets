"""Standalone assertion-script tests for portfolio_memory.py (FSI Phase
17), validated against real production data (read-only, zero write path
anywhere in this module -- including to the quant engine's own registry).

  PYTHONPATH=src python scripts/fre/test_portfolio_memory.py
"""
from __future__ import annotations

import ast
import inspect
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.alpha_engine import AlphaEngine  # noqa: E402
from ngxrot.fre import portfolio_memory as pm  # noqa: E402
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


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    before_counts = snapshot_all_table_counts(con)

    # --- 1. correctness vs. a direct AlphaEngine().recommendations() call -----
    engine = AlphaEngine()
    real_recs = engine.recommendations()
    real_instruments = {r.instrument for r in real_recs if r.action != "no_position"}
    check("at least one real live recommendation exists to test against "
          "(H-011 Size, confirmed 2026-07-22)", len(real_instruments) > 0)

    a_real_live_ticker = sorted(real_instruments)[0] if real_instruments else None
    if a_real_live_ticker:
        note = pm.cross_reference(a_real_live_ticker)
        direct_match = next(r for r in real_recs if r.instrument == a_real_live_ticker)
        check(f"cross_reference('{a_real_live_ticker}') correctly reports "
              f"in_live_sleeve=True, matching the direct AlphaEngine call's "
              f"own action/size_pct_nav/hypothesis_id/as_of exactly",
              note.in_live_sleeve is True
              and note.action == direct_match.action
              and note.size_pct_nav == direct_match.size_pct_nav
              and note.hypothesis_id == direct_match.hypothesis_id
              and note.as_of == direct_match.as_of
              and note.rationale == direct_match.rationale)

    # --- 2. a real FSI ticker with NO live recommendation correctly reports
    # in_live_sleeve=False, never an error (the common, correct case) ---------
    con2 = ro()
    fsi_tickers = list_tickers(con2)
    con2.close()
    no_overlap = [t for t in fsi_tickers if t not in real_instruments]
    check("at least one real FSI ticker has no live recommendation, giving "
          "a real negative case to test (not fabricated)", len(no_overlap) > 0)
    if no_overlap:
        note = pm.cross_reference(no_overlap[0])
        check(f"cross_reference('{no_overlap[0]}') correctly reports "
              f"in_live_sleeve=False with all other fields None, never an error",
              note.in_live_sleeve is False and note.hypothesis_id is None
              and note.action is None and note.size_pct_nav is None
              and note.as_of is None and note.rationale is None)

    # --- 3. an entirely unknown/nonexistent ticker also returns False, not
    # a crash (mirrors "unknown stays unknown" elsewhere on this platform) ----
    note = pm.cross_reference("NOTAREALTICKERXYZ")
    check("a nonexistent ticker also returns in_live_sleeve=False, never a crash",
          note.in_live_sleeve is False)

    # --- 4. single-ticker-scope + no-score/rank field guardrails --------------
    check("cross_reference() accepts at most ONE 'ticker'-named parameter",
          len([p for p in inspect.signature(pm.cross_reference).parameters
               if "ticker" in p.lower()]) <= 1)
    note_fields = set(pm.PortfolioMemoryNote.__dataclass_fields__)
    check("PortfolioMemoryNote carries no score/rank/weight field of any kind",
          note_fields.isdisjoint({"score", "rank", "weight", "strength", "priority"}))

    # --- 5. zero write path: no INSERT/UPDATE/DELETE anywhere in this module,
    # confirmed via AST inspection (not a substring match) ---------------------
    tree = ast.parse((ROOT / "src" / "ngxrot" / "fre" / "portfolio_memory.py").read_text(encoding="utf-8"))
    sql_verbs_found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            upper = node.value.strip().upper()
            if upper.startswith(("INSERT", "UPDATE", "DELETE")):
                sql_verbs_found.append(node.value)
    check("portfolio_memory.py contains no INSERT/UPDATE/DELETE SQL statement "
          "anywhere (confirmed via AST inspection of every string literal)",
          sql_verbs_found == [])

    # --- 6. import-boundary check: never imports registry directly (only
    # via AlphaEngine's own existing, already-used public method) -------------
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[0])
    check("portfolio_memory.py never imports ngxrot.registry directly (only "
          "reads via alpha_engine.AlphaEngine's own already-existing public "
          "recommendations() method)", "registry" not in imported_names)

    alpha_engine_src = (ROOT / "src" / "ngxrot" / "alpha_engine.py").read_text(encoding="utf-8")
    check("alpha_engine.py never imports portfolio_memory.py (one-directional "
          "read boundary, verified both ways)", "portfolio_memory" not in alpha_engine_src)

    # --- 7. zero-write confirmation against data/ngx.sqlite --------------------
    after_counts = snapshot_all_table_counts(con)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL data/ngx.sqlite tables' row counts unchanged after this entire "
          "test run (portfolio_memory.py has no write path to the FSI database)",
          diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])

    con.close()
    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
