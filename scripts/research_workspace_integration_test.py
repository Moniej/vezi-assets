"""End-to-end Research Workspace integration test (Phase 3, spec Section
26): a genuine, non-alpha research investigation, executed through the
full stack, then reproduced.

Research question: "How has the composition of the NGX equity universe
(by sector) changed over a defined historical period?"

Workflow: create project -> define scope -> execute queries (Phase 2) ->
collect evidence -> descriptive analysis (artifacts) -> record findings ->
freeze snapshot -> export report -> reproduce.

No trading strategy. No alpha. No predictive model. No portfolio.

Read-only against the real production DB; workspace state written to a
scratch registry.

  PYTHONPATH=src python scripts/research_workspace_integration_test.py
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

SECTORS = ["CONSUMER GOODS", "FINANCIAL SERVICES", "OIL AND GAS"]
AS_OF_DATES = ["2020-01-01", "2025-01-01"]


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    scratch_dir = Path(tempfile.mkdtemp())
    reg = registry.connect_registry(scratch_dir / "registry.sqlite")

    print("=" * 78)
    print("STEP 1: Create Research Project")
    print("=" * 78)
    project = rw.create_project(
        reg, title="NGX sector composition over time",
        research_question="How has the composition of the NGX equity universe "
                          "(by sector) changed over a defined historical period?",
        description="Purely descriptive: compares sector membership counts at two "
                    "points in time. No trading strategy, signal, or portfolio "
                    "construction is implied or produced.",
        scope={"sectors": SECTORS, "as_of_dates": AS_OF_DATES},
        tags=["descriptive", "universe-composition"])
    print(f"research_id = {project.research_id}")

    print()
    print("=" * 78)
    print("STEP 2: Define scope (already recorded at creation) -> execute queries")
    print("=" * 78)
    query_ids = {}
    for sector in SECTORS:
        for as_of in AS_OF_DATES:
            spec = QuerySpec(query_type="cross_section", entity_kind="sector",
                             filters={"sector": sector}, as_of=as_of, fields=["close"])
            result = execute(con, spec, reg=reg)
            rw.attach_query(reg, project.research_id, result.query_id,
                           note=f"{sector} constituents as of {as_of}")
            query_ids[(sector, as_of)] = result
            print(f"  {sector} @ {as_of}: {result.row_count} constituents "
                 f"(query_id={result.query_id})")

    print()
    print("=" * 78)
    print("STEP 3: Collect evidence")
    print("=" * 78)
    evidence_ids = []
    for (sector, as_of), result in query_ids.items():
        ev_id = rw.add_evidence(con, reg, project.research_id, "query_result",
                                {"query_id": result.query_id},
                                f"{sector} had {result.row_count} constituents as of {as_of}")
        evidence_ids.append(ev_id)
    print(f"  {len(evidence_ids)} evidence items recorded")

    print()
    print("=" * 78)
    print("STEP 4: Descriptive analysis (artifacts) -- no alpha, only counts")
    print("=" * 78)
    artifact_ids = []
    for (sector, as_of), result in query_ids.items():
        artifact_ids.append(rw.make_table_artifact(reg, project.research_id, result,
                                                    title=f"{sector} @ {as_of}"))
    comparison = {sector: {as_of: query_ids[(sector, as_of)].row_count for as_of in AS_OF_DATES}
                 for sector in SECTORS}
    print("  Sector constituent counts (descriptive only, no ranking/score):")
    for sector, counts in comparison.items():
        delta = counts[AS_OF_DATES[1]] - counts[AS_OF_DATES[0]]
        print(f"    {sector}: {counts[AS_OF_DATES[0]]} -> {counts[AS_OF_DATES[1]]} ({delta:+d})")

    print()
    print("=" * 78)
    print("STEP 5: Record findings")
    print("=" * 78)
    findings = []
    for sector, counts in comparison.items():
        delta = counts[AS_OF_DATES[1]] - counts[AS_OF_DATES[0]]
        if delta == 0:
            statement = (f"{sector} constituent count was unchanged ({counts[AS_OF_DATES[0]]}) "
                        f"between {AS_OF_DATES[0]} and {AS_OF_DATES[1]}, based on current-day "
                        f"sector_ngx classification (no historical sector versioning exists in "
                        f"this schema -- disclosed, not corrected).")
        else:
            statement = (f"{sector} constituent count changed from {counts[AS_OF_DATES[0]]} to "
                        f"{counts[AS_OF_DATES[1]]} ({delta:+d}) between the two as-of dates, based "
                        f"on current-day sector_ngx classification (no historical sector versioning "
                        f"exists in this schema -- disclosed, not corrected).")
        fid = rw.add_finding(reg, project.research_id, f"{sector} composition change",
                             statement, supporting_evidence=evidence_ids, status="PRELIMINARY")
        findings.append(fid)
        print(f"  [{fid}] {sector}: {statement[:70]}...")

    print()
    print("=" * 78)
    print("STEP 6: Integrity check + quality summary")
    print("=" * 78)
    warnings = rw.integrity_check(con, reg, project.research_id)
    print(f"  {len(warnings)} integrity warning(s):")
    for w in warnings[:3]:
        print(f"    - {w[:100]}...")
    quality = rw.project_quality_summary(con, reg, project.research_id)
    print(f"  quality summary covers {len(quality.get('tickers', []))} distinct tickers")

    print()
    print("=" * 78)
    print("STEP 7: Freeze research snapshot")
    print("=" * 78)
    snapshot_id = rw.snapshot(con, reg, project.research_id)
    print(f"  snapshot_id = {snapshot_id}")

    print()
    print("=" * 78)
    print("STEP 8: Export research report")
    print("=" * 78)
    md = rw.export_markdown(con, reg, project.research_id)
    report_path = scratch_dir / "report.md"
    report_path.write_text(md, encoding="utf-8")
    print(f"  Markdown report written ({len(md)} chars) -- {report_path}")
    js = rw.export_json(reg, project.research_id)
    print(f"  JSON export ({len(js)} chars)")

    print()
    print("=" * 78)
    print("STEP 9: Reproduce -- verify the snapshot detects no drift, then a real mutation")
    print("=" * 78)
    repro_before = rw.check_reproducibility(reg, snapshot_id)
    print(f"  immediately after freeze: unchanged={repro_before['unchanged']}")
    rw.update_finding_status(reg, findings[0], "SUPPORTED", reason="reviewed against both queries")
    repro_after = rw.check_reproducibility(reg, snapshot_id)
    print(f"  after a real finding-status change: unchanged={repro_after['unchanged']}")

    ok = (
        len(query_ids) == len(SECTORS) * len(AS_OF_DATES)
        and len(evidence_ids) == len(query_ids)
        and len(findings) == len(SECTORS)
        and repro_before["unchanged"] is True
        and repro_after["unchanged"] is False
        and "buy" not in md.lower() and "sell" not in md.lower()
        and "ngxpulse_" not in md and "ngxpulse_" not in js
    )

    reg.close()
    con.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print("END-TO-END RESEARCH INVESTIGATION " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
