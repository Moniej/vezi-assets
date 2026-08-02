"""Standalone assertion-script tests for screening.py (FSI Phase 14),
validated against real production data (read-only, zero write path
anywhere in this module).

  PYTHONPATH=src python scripts/fre/test_screening.py
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import screening  # noqa: E402
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
    before = snapshot_all_table_counts(con)

    # --- 1. correctness vs. a direct SQL query --------------------------------
    # NASCON's real leverage_increasing flag (conclusion_id 172, confirmed
    # by direct inspection) fires for period 2025-01-01..2025-12-31, gated
    # by its own latest source fact's filing_date (2026-03-03).
    real_fired_tickers = {r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM financial_reasoning_conclusions "
        "WHERE conclusion_type='flag' AND metric='leverage_increasing' "
        "AND status='computed' AND value_text='fired'"
    ).fetchall()}
    far_future = "2030-01-01"
    screen_result = screening.screen_by_flag(con, "leverage_increasing", fired=True, as_of_date=far_future)
    screen_tickers = {m.ticker for m in screen_result}
    check("screen_by_flag('leverage_increasing', fired=True) at a far-future date matches "
          "a direct SQL query of every real fired instance across all tickers",
          screen_tickers == real_fired_tickers and "NASCON" in screen_tickers)

    real_decreasing_net_profit = {r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM financial_reasoning_conclusions "
        "WHERE conclusion_type='trend' AND metric='net_profit' "
        "AND status='computed' AND value_text='decreasing'"
    ).fetchall()}
    trend_result = screening.screen_by_trend(con, "net_profit", "decreasing", as_of_date=far_future)
    trend_tickers = {m.ticker for m in trend_result}
    check("screen_by_trend('net_profit', 'decreasing') at a far-future date matches a direct "
          "SQL query, and correctly includes MTNN (its real FY2024 net_profit trend)",
          trend_tickers == real_decreasing_net_profit and "MTNN" in trend_tickers)

    # --- 2. PIT correctness: the exact NASCON boundary confirmed empirically --
    before_boundary = screening.screen_by_flag(con, "leverage_increasing", fired=True, as_of_date="2026-03-02")
    on_boundary = screening.screen_by_flag(con, "leverage_increasing", fired=True, as_of_date="2026-03-03")
    check("NASCON's real leverage_increasing flag is NOT screenable the day before its own "
          "conclusion's latest source fact is filed (2026-03-02)",
          "NASCON" not in {m.ticker for m in before_boundary})
    check("...but IS screenable exactly on that filing date (2026-03-03)",
          "NASCON" in {m.ticker for m in on_boundary})

    # --- 3. unrecognized categorical values raise, never silently return empty
    try:
        screening.screen_by_flag(con, "not_a_real_flag", fired=True, as_of_date=far_future)
        flag_raised = False
    except ValueError:
        flag_raised = True
    check("an unrecognized flag_metric raises ValueError, never silently returns []", flag_raised)

    try:
        screening.screen_by_trend(con, "revenue", "improving", as_of_date=far_future)
        direction_raised = False
    except ValueError:
        direction_raised = True
    check("an unrecognized trend direction raises ValueError, never silently returns []", direction_raised)

    try:
        screening.screen_by_trend(con, "not_a_real_metric", "increasing", as_of_date=far_future)
        metric_raised = False
    except ValueError:
        metric_raised = True
    check("an unrecognized trend metric raises ValueError, never silently returns []", metric_raised)

    # --- 4. ordering and no-aggregate guardrails -------------------------------
    all_fired_result = screening.screen_by_flag(con, "margin_compression", fired=True, as_of_date=far_future)
    result_tickers_in_order = [m.ticker for m in all_fired_result]
    check("screen_by_flag results are in strict alphabetical-ticker order, never value-sorted",
          result_tickers_in_order == sorted(result_tickers_in_order))

    all_increasing_result = screening.screen_by_trend(con, "revenue", "increasing", as_of_date=far_future)
    trend_tickers_in_order = [m.ticker for m in all_increasing_result]
    check("screen_by_trend results are in strict alphabetical-ticker order, never value-sorted",
          trend_tickers_in_order == sorted(trend_tickers_in_order))

    # --- 5. mechanical guardrails: no ranking-adjacent parameter or field -----
    for fn in (screening.screen_by_flag, screening.screen_by_trend):
        params = set(inspect.signature(fn).parameters)
        forbidden = {"limit", "top_n", "sort_by", "rank_by", "weight", "threshold", "min_value", "max_value"}
        check(f"{fn.__name__}'s signature has no limit/sort/rank/threshold-style parameter",
              params.isdisjoint(forbidden))

    match_fields = set(screening.ScreenMatch.__dataclass_fields__)
    check("ScreenMatch carries no score/rank/weight field of any kind",
          match_fields.isdisjoint({"score", "rank", "weight", "strength", "priority"}))

    # --- 6. import-boundary check: never touches alpha_engine.py/runner.py ----
    # Checks actual import STATEMENTS only (via the ast module), not a bare
    # substring match -- this module's own docstring legitimately mentions
    # "alpha_engine.py" in prose to explain the guardrail, which a naive
    # substring check would misflag as a violation.
    import ast
    screening_tree = ast.parse((ROOT / "src" / "ngxrot" / "fre" / "screening.py").read_text(encoding="utf-8"))
    imported_names = set()
    for node in ast.walk(screening_tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[0])
            if node.module.startswith("ngxrot"):
                imported_names.update(alias.name for alias in node.names)
    check("screening.py never imports alpha_engine or runner (no portfolio-facing boundary crossed)",
          "alpha_engine" not in imported_names and "runner" not in imported_names)
    alpha_engine_path = ROOT / "src" / "ngxrot" / "alpha_engine.py"
    if alpha_engine_path.exists():
        alpha_src = alpha_engine_path.read_text(encoding="utf-8")
        check("alpha_engine.py never imports screening.py (one-directional boundary, verified both ways)",
              "screening" not in alpha_src)

    # --- 7. zero-write confirmation --------------------------------------------
    after = snapshot_all_table_counts(con)
    diffs = diff_table_counts(before, after)
    check("ALL tables' row counts unchanged after this entire test run (screening.py has no write path)",
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
