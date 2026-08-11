"""End-to-end integration test for the Research Query Layer (spec
Section 22): a genuine research question, executed through the real
stack (validation -> entity resolution -> PIT query -> SQLite -> lineage
-> structured QueryResult -> query_log), then reproduced.

Research question: "Show the historical price observations for a
representative set of NGX companies over a defined period, using the
point-in-time database and preserving source lineage."

Read-only against the real production DB; logs to a scratch registry.

  PYTHONPATH=src python scripts/research_query_integration_test.py
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
from ngxrot.lineage import trace_equity_observation  # noqa: E402
from ngxrot.research_query import QuerySpec, execute  # noqa: E402

REPRESENTATIVE_TICKERS = ["GTCO", "ZENITHBANK", "DANGCEM", "MTNN", "BUAFOODS", "SEPLAT"]


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    scratch_dir = Path(tempfile.mkdtemp())
    reg = registry.connect_registry(scratch_dir / "registry.sqlite")

    print("Research question: \"Show the historical price observations for a "
          "representative set of NGX companies over a defined period, using the "
          "point-in-time database and preserving source lineage.\"")
    print()
    print(f"Representative set: {REPRESENTATIVE_TICKERS}")
    print("Period: 2023-01-01 -> 2024-12-31")
    print()

    spec = QuerySpec(query_type="prices", entities=REPRESENTATIVE_TICKERS,
                     start="2023-01-01", end="2024-12-31", fields=["close", "volume"])

    print("Step 1: validation + entity resolution (inside execute())")
    result = execute(con, spec, reg=reg)
    print(f"  -> {result.row_count} observations across {len(REPRESENTATIVE_TICKERS)} tickers")
    print(f"  -> entities_resolved: "
          f"{[(e['requested'], e['canonical'], e['full_chain']) for e in result.entities_resolved]}")

    print()
    print("Step 2: data sources actually used")
    print(f"  -> {result.data_sources}")

    print()
    print("Step 3: lineage / provenance (batch summary from the query result)")
    for p in result.provenance:
        print(f"  -> {p['ticker']}: {p['n_rows']} rows from {p['source_name']} "
              f"({p['source_kind']}, {p['source_reliability']}), {p['first_date']}..{p['last_date']}")

    print()
    print("Step 4: drill into ONE specific observation's full lineage (not just the batch summary)")
    sample_ticker = result.observations.ticker.iloc[0]
    sample_date = result.observations.trade_date.iloc[0]
    full_lineage = trace_equity_observation(con, sample_ticker, sample_date)
    print(f"  -> {sample_ticker} {sample_date}: source={full_lineage.source_name} "
          f"ingestion_run={full_lineage.ingestion_run} validation_status={full_lineage.validation_status}")

    print()
    print("Step 5: structured QueryResult -- content hash for reproducibility")
    h1 = result.content_hash()
    print(f"  -> content_hash = {h1}")

    print()
    print("Step 6: reproduce -- re-run the IDENTICAL query and compare")
    result2 = execute(con, spec, reg=reg)
    h2 = result2.content_hash()
    print(f"  -> re-run content_hash = {h2}")
    reproduced = h1 == h2 and result.row_count == result2.row_count
    print(f"  -> REPRODUCED: {reproduced}")

    print()
    print("Step 7: query_log -- both executions are independently recorded and auditable")
    logged = reg.execute("SELECT query_id, row_count, content_hash FROM query_log "
                         "ORDER BY executed_at").fetchall()
    for row in logged:
        print(f"  -> {row}")

    con.close()
    reg.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    ok = reproduced and len(logged) == 2 and result.row_count > 0
    print()
    print("INTEGRATION TEST " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
