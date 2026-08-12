"""Regression test for research quality/completeness in the Research
Workspace (2026-08-11, HANDOFF.md, Priority 7).

Exercises a real end-to-end flow: run a document_context query against
the real production database, attach it as evidence, then verify
document_completeness_summary/integrity_check/export_markdown all
surface it correctly. Workspace state is written to a SCRATCH
registry.sqlite, never the real one (matches every other workspace test).

  PYTHONPATH=src python scripts/test_research_completeness.py
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
from ngxrot import research_workspace as rw  # noqa: E402
from ngxrot.research_query import QuerySpec, execute  # noqa: E402

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

    p = rw.create_project(reg, "NASCON completeness check", "How complete is our "
                          "picture of NASCON?", scope={"tickers": ["NASCON"]})

    # --- before any document_context evidence: honest "nothing yet" -------
    empty_summary = rw.document_completeness_summary(reg, p.research_id)
    check("document_completeness_summary: honestly reports nothing attached yet, "
         "not a fabricated score", empty_summary["per_ticker"] == [] and
         empty_summary["mean_coverage_score"] is None)

    # --- attach a real document_context query + a real prices query -------
    ctx_result = execute(con, QuerySpec(query_type="document_context", entities=["NASCON"],
                                        as_of="2026-08-10"), reg=reg)
    rw.attach_query(reg, p.research_id, ctx_result.query_id)
    price_result = execute(con, QuerySpec(query_type="prices", entities=["NASCON"],
                                          start="2026-01-01", end="2026-06-01"), reg=reg)
    rw.attach_query(reg, p.research_id, price_result.query_id)

    ev_id = rw.add_document_evidence(reg, p.research_id, ctx_result)
    ev_row = next(e for e in rw.list_evidence(reg, p.research_id) if e["evidence_id"] == ev_id)
    check("document_context evidence carries the new dimensions_missing/tier-distribution fields",
         "dimensions_missing" in ev_row["source_reference"] and
         "source_tier_distribution" in ev_row["source_reference"])

    # --- document_completeness_summary now reflects real data -------------
    summary = rw.document_completeness_summary(reg, p.research_id)
    check("document_completeness_summary: NASCON now assessed", summary["tickers_assessed"] == ["NASCON"])
    check("document_completeness_summary: real coverage_score present and in [0,1]",
         summary["mean_coverage_score"] is not None and 0.0 <= summary["mean_coverage_score"] <= 1.0)
    check("document_completeness_summary: per_ticker row carries dimensions_missing as a real list",
         isinstance(summary["per_ticker"][0]["dimensions_missing"], list))

    # --- integrity_check surfaces the completeness gap ----------------------
    warnings = rw.integrity_check(con, reg, p.research_id)
    check("integrity_check: surfaces a '[research completeness]' warning for NASCON "
         "(NASCON's real coverage is known to be < 1.0, so at least one dimension is missing)",
         any("[research completeness] NASCON" in w for w in warnings))

    # --- a ticker with NO document_context attached is flagged honestly ---
    rw.attach_query(reg, p.research_id, execute(
        con, QuerySpec(query_type="prices", entities=["GTCO"], start="2026-01-01",
                       end="2026-02-01"), reg=reg).query_id)
    summary2 = rw.document_completeness_summary(reg, p.research_id)
    check("document_completeness_summary: a ticker referenced only by a price query "
         "(GTCO) is correctly reported as missing document_context, not silently omitted",
         "GTCO" in summary2["tickers_missing_document_context"])
    warnings2 = rw.integrity_check(con, reg, p.research_id)
    check("integrity_check: surfaces GTCO's missing document-context coverage explicitly",
         any("GTCO" in w and "no document/FRE coverage" in w for w in warnings2))

    # --- export_markdown includes the new section --------------------------
    md = rw.export_markdown(con, reg, p.research_id)
    check("export Markdown: contains a '## Research Completeness' section",
         "## Research Completeness" in md)
    check("export Markdown: the completeness table includes NASCON's real coverage score",
         "NASCON" in md and str(summary["per_ticker"][0]["coverage_score"]) in md)

    reg.close()
    con.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
