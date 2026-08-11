"""Tests for the Research Query Layer (src/ngxrot/research_query.py).
Read-only against the real production DB; query logging is tested
against a scratch copy of registry.sqlite (never the real one).

  PYTHONPATH=src python scripts/test_research_query.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db, registry  # noqa: E402
from ngxrot.research_query import (  # noqa: E402
    QuerySpec, QueryValidationError, drawdown, execute, pct_change, rolling_stats)

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
    scratch_dir = Path(tempfile.mkdtemp())
    reg = registry.connect_registry(scratch_dir / "registry.sqlite")

    # --- prices (time series) -------------------------------------------
    r = execute(con, QuerySpec(query_type="prices", entities=["GTCO"], start="2023-01-01",
                               end="2023-01-31", fields=["close", "volume"]), reg=reg)
    check("prices: real rows returned", r.row_count > 0)
    check("prices: only requested + identifying columns present",
          set(r.observations.columns) == {"ticker", "trade_date", "close", "volume"})
    check("prices: data_sources populated even though source_id wasn't a requested field",
          len(r.data_sources) > 0)
    check("prices: provenance populated (batch summary, not empty)", len(r.provenance) > 0)
    check("prices: query_id is a real uuid-shaped string", len(r.query_id) == 36)

    # --- cross_section: exactly one row per ticker, not full history -----
    r2 = execute(con, QuerySpec(query_type="cross_section", entity_kind="sector",
                                filters={"sector": "CONSUMER GOODS"}, as_of="2025-01-01",
                                fields=["close"]), reg=reg)
    check("cross_section: one row per ticker (a snapshot, not full history)",
          r2.row_count == r2.observations.ticker.nunique())
    check("cross_section: every returned trade_date is <= as_of (no look-ahead)",
          (r2.observations.trade_date <= "2025-01-01").all())
    check("cross_section: historical-classification warning present for a past as_of",
          any("historical sector versioning" in w for w in r2.warnings))

    # --- universe_history --------------------------------------------------
    r3 = execute(con, QuerySpec(query_type="universe_history", filters={"universe": "iru"},
                                as_of="2024-06-30"), reg=reg)
    check("universe_history (IRU): real, non-trivial membership returned", r3.row_count > 10)
    check("universe_history: universe_version recorded in execution_metadata",
          r3.execution_metadata.get("universe_version") is not None)

    r3b = execute(con, QuerySpec(query_type="universe_history", entities=["NGXBNK"],
                                 entity_kind="index", as_of="2024-06-30"), reg=reg)
    check("universe_history (real NGX index NGXBNK): returns real constituents",
          r3b.row_count > 0)

    # --- compare -------------------------------------------------------------
    r4 = execute(con, QuerySpec(query_type="compare", entities=["GTCO", "ZENITHBANK"],
                                start="2023-01-01", end="2023-06-30", fields=["close"]), reg=reg)
    summary = r4.execution_metadata.get("comparison_summary")
    check("compare: descriptive summary has one row per ticker, no ranking/score field",
          summary is not None and len(summary) == 2
          and not any("score" in k or "rank" in k for row in summary for k in row))

    # --- entity_lookup / metadata --------------------------------------------
    r5 = execute(con, QuerySpec(query_type="entity_lookup", entities=["GTCO", "GUARANTY", "NOTAREAL"]),
                reg=reg)
    recs = {row["requested"]: row for row in r5.observations.to_dict("records")}
    check("entity_lookup: GTCO resolves with its real GUARANTY rename chain",
          recs["GTCO"]["full_chain"] == ["GUARANTY", "GTCO"])
    check("entity_lookup: pre-rename GUARANTY itself resolves too (not just the current symbol)",
          recs["GUARANTY"]["found"] is True)
    check("entity_lookup: a fake ticker is honestly reported not found, never guessed",
          recs["NOTAREAL"]["found"] is False)

    r6 = execute(con, QuerySpec(query_type="metadata", entities=["GTCO"]), reg=reg)
    check("metadata: real sector_ngx returned", r6.observations.iloc[0]["sector_ngx"] is not None)
    check("metadata: no market_cap/dividend field fabricated (never in this schema)",
          "market_cap" not in r6.observations.columns and "dividend" not in r6.observations.columns)

    # --- guardrails --------------------------------------------------------
    try:
        execute(con, QuerySpec(query_type="prices", entities=["GTCO"], start="2024-01-01",
                               end="2023-01-01"), reg=reg)
        check("guardrail: start > end rejected", False)
    except QueryValidationError:
        check("guardrail: start > end rejected", True)

    try:
        execute(con, QuerySpec(query_type="prices", entities=["GTCO"], start="2023-01-01",
                               end="2024-01-01", as_of="2023-06-30"), reg=reg)
        check("guardrail: look-ahead (end > as_of) rejected", False)
    except QueryValidationError:
        check("guardrail: look-ahead (end > as_of) rejected", True)

    try:
        execute(con, QuerySpec(query_type="prices", entities=["GTCO"], start="2023-01-01",
                               end="2023-01-05", fields=["market_cap"]), reg=reg)
        check("guardrail: unsupported field (market_cap, not in this schema) rejected", False)
    except QueryValidationError:
        check("guardrail: unsupported field (market_cap, not in this schema) rejected", True)

    try:
        execute(con, QuerySpec(query_type="prices", entities=["NOTAREALTICKER"], start="2023-01-01",
                               end="2023-01-05"), reg=reg)
        check("guardrail: unknown entity rejected", False)
    except QueryValidationError:
        check("guardrail: unknown entity rejected", True)

    try:
        execute(con, QuerySpec(query_type="prices", entities=["GTCO"], start="2023-01-01",
                               end="2023-01-05", limit=0), reg=reg)
        check("guardrail: non-positive limit rejected", False)
    except QueryValidationError:
        check("guardrail: non-positive limit rejected", True)

    # --- descriptive (non-alpha) calculations -------------------------------
    close = r.observations.sort_values("trade_date").set_index("trade_date")["close"]
    check("pct_change: matches a manual calculation", abs(
        pct_change(close).iloc[1] - (close.iloc[1] / close.iloc[0] - 1)) < 1e-9)
    check("drawdown: never positive", (drawdown(close) <= 1e-9).all())
    check("rolling_stats: returns mean/median/min/max/std columns",
          set(rolling_stats(close, 5).columns) == {"mean", "median", "min", "max", "std"})

    # --- reproducibility: identical query -> identical content_hash --------
    r_again = execute(con, QuerySpec(query_type="prices", entities=["GTCO"], start="2023-01-01",
                                     end="2023-01-31", fields=["close", "volume"]), reg=reg)
    check("reproducibility: identical query produces identical content_hash",
          r.content_hash() == r_again.content_hash())

    # --- query_log: immutable, real rows, no secrets leaked ------------------
    n = reg.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
    check("query_log: every successful execute() call above was logged", n >= 6)
    all_params = " ".join(row[0] for row in reg.execute("SELECT parameters_json FROM query_log").fetchall())
    check("query_log: NGX Pulse API key never appears in any logged query", "ngxpulse_" not in all_params)
    try:
        qid = reg.execute("SELECT query_id FROM query_log LIMIT 1").fetchone()[0]
        reg.execute("DELETE FROM query_log WHERE query_id = ?", (qid,))
        check("query_log is immutable: DELETE was unexpectedly allowed", False)
    except sqlite3.IntegrityError:
        check("query_log is immutable: DELETE correctly raised (trigger fired)", True)
    reg.rollback()

    reg.close()
    con.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
