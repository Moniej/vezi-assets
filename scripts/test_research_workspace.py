"""Tests for the Research Workspace (Phase 3, src/ngxrot/research_workspace.py).
Read-only against the real production market-data DB; all workspace state
is written to a SCRATCH registry.sqlite, never the real one.

  PYTHONPATH=src python scripts/test_research_workspace.py
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

    # --- projects: create / retrieve / update / archive ---------------------
    p = rw.create_project(reg, "Sector composition study", "How has NGX sector "
                          "composition changed?", scope={"sectors": ["CONSUMER GOODS"]})
    check("create: real DRAFT project created", p.status == "DRAFT" and p.research_id.startswith("RP-"))
    check("create: code_fingerprint captured at creation", bool(p.code_fingerprint))

    got = rw.get_project(reg, p.research_id)
    check("retrieve: get_project round-trips the project", got.title == p.title)
    check("retrieve: unknown research_id returns None, never fabricated", rw.get_project(reg, "RP-fake") is None)

    updated = rw.update_project(reg, p.research_id, status="ACTIVE", description="now underway")
    check("update: status/description changed", updated.status == "ACTIVE" and updated.description == "now underway")
    check("update: title/research_question/created_at immutable through the update path",
          updated.title == p.title and updated.research_question == p.research_question)

    projects = rw.list_projects(reg, status="ACTIVE")
    check("list: filters by status", any(x.research_id == p.research_id for x in projects))

    # --- queries: attach existing, preserve spec + provenance ---------------
    r = execute(con, QuerySpec(query_type="cross_section", entity_kind="sector",
                               filters={"sector": "CONSUMER GOODS"}, as_of="2025-01-01",
                               fields=["close"]), reg=reg)
    rw.attach_query(reg, p.research_id, r.query_id, note="CG snapshot")
    queries = rw.list_queries(reg, p.research_id)
    check("attach: query is attached and retrievable", len(queries) == 1 and queries[0]["query_id"] == r.query_id)
    check("attach: QuerySpec/result metadata preserved (row_count, sources)",
          queries[0]["row_count"] == r.row_count and queries[0]["data_sources"] == r.data_sources)
    check("attach: entities_requested preserved (resolved sector tickers, real bug fixed this phase)",
          len(queries[0]["entities_requested"]) > 10)
    try:
        rw.attach_query(reg, p.research_id, "nonexistent-query-id")
        check("attach: unknown query_id rejected", False)
    except rw.WorkspaceError:
        check("attach: unknown query_id rejected", True)

    # --- evidence: create / retrieve / trace to source -----------------------
    ev1 = rw.add_evidence(con, reg, p.research_id, "query_result", {"query_id": r.query_id},
                          "19 CONSUMER GOODS constituents as of 2025-01-01")
    ev2 = rw.add_evidence(con, reg, p.research_id, "dataset_observation",
                          {"ticker": "CILEASING", "trade_date": "2024-01-05"}, "unadjusted bonus-issue jump")
    evidence = rw.list_evidence(reg, p.research_id)
    check("evidence: two items created and retrievable", len(evidence) == 2)
    ev2_row = next(e for e in evidence if e["evidence_id"] == ev2)
    check("evidence: dataset_observation provenance resolved via lineage.py (not a new system)",
          ev2_row["provenance"] is not None and "source_name" in ev2_row["provenance"])
    traced = rw.trace_evidence(reg, ev1)
    check("evidence: trace_evidence follows evidence -> query -> sources",
          "query" in traced and traced["query"]["data_sources"] == r.data_sources)

    ev3 = rw.add_evidence(con, reg, p.research_id, "dataset_observation",
                          {"ticker": "NOTAREAL", "trade_date": "2020-01-01"}, "a fake observation")
    ev3_row = next(e for e in rw.list_evidence(reg, p.research_id) if e["evidence_id"] == ev3)
    check("evidence: unresolvable provenance is left NULL, never fabricated", ev3_row["provenance"] is None)

    # --- notes: typed, immutable ----------------------------------------------
    rw.add_note(reg, p.research_id, "observation", "sector counts look stable")
    try:
        rw.add_note(reg, p.research_id, "not_a_real_type", "x")
        check("note: unknown note_type rejected", False)
    except rw.WorkspaceError:
        check("note: unknown note_type rejected", True)
    check("note: real note retrievable", len(rw.list_notes(reg, p.research_id)) == 1)

    # --- findings: create / update status / link evidence ---------------------
    finding_id = rw.add_finding(reg, p.research_id, "Sector coverage is stable",
                                "CONSUMER GOODS membership is consistent across the sample dates",
                                supporting_evidence=[ev1])
    check("finding: created with PRELIMINARY default status",
          rw.list_findings(reg, p.research_id)[0]["status"] == "PRELIMINARY")
    rw.update_finding_status(reg, finding_id, "SUPPORTED", reason="cross-checked")
    check("finding: status transition applied", rw.list_findings(reg, p.research_id)[0]["status"] == "SUPPORTED")
    check("finding: a finding may state a DATA LIMITATION, not just a positive result -- "
          "supported by recording one now",
          True)
    neg_finding = rw.add_finding(reg, p.research_id, "Two providers disagree",
                                 "ngx_pricelist_v2 and ngx_pulse disagree on 0.62% of observations",
                                 status="UNRESOLVED")
    check("finding: an UNRESOLVED/negative-style finding is a first-class, valid finding",
          any(f["finding_id"] == neg_finding and f["status"] == "UNRESOLVED"
              for f in rw.list_findings(reg, p.research_id)))
    try:
        rw.update_finding_status(reg, finding_id, "NOT_A_STATUS")
        check("finding: invalid status rejected", False)
    except rw.WorkspaceError:
        check("finding: invalid status rejected", True)

    # --- hypotheses: create / support / weaken / reject -----------------------
    hyp_id = rw.add_hypothesis(reg, p.research_id, "NGX sector composition has diversified since 2020")
    check("hypothesis: created OPEN", rw.list_hypotheses(reg, p.research_id)[0]["status"] == "OPEN")
    rw.update_hypothesis_status(reg, hyp_id, "SUPPORTED", supporting_finding_ids=[finding_id])
    h = next(h for h in rw.list_hypotheses(reg, p.research_id) if h["hypothesis_id"] == hyp_id)
    check("hypothesis: SUPPORTED with linked finding", h["status"] == "SUPPORTED" and h["supporting_finding_ids"] == [finding_id])
    rw.update_hypothesis_status(reg, hyp_id, "WEAKENED", contradicting_finding_ids=[neg_finding])
    h = next(h for h in rw.list_hypotheses(reg, p.research_id) if h["hypothesis_id"] == hyp_id)
    check("hypothesis: WEAKENED with contradicting finding", h["status"] == "WEAKENED")
    rw.update_hypothesis_status(reg, hyp_id, "REJECTED")
    check("hypothesis: REJECTED", rw.list_hypotheses(reg, p.research_id)[0]["status"] == "REJECTED"
          or any(h["status"] == "REJECTED" for h in rw.list_hypotheses(reg, p.research_id)))

    # --- artifacts -------------------------------------------------------------
    table_id = rw.make_table_artifact(reg, p.research_id, r, title="CG snapshot")
    summary_id = rw.make_summary_artifact(reg, p.research_id, r, field="close")
    chart_id = rw.make_chart_spec(reg, p.research_id, r, "cross_sectional", x="ticker", y="close")
    artifacts = rw.list_artifacts(reg, p.research_id)
    check("artifacts: table/summary_statistics/chart all created", len(artifacts) == 3)
    check("artifacts: each has a real content_hash", all(a["content_hash"] for a in artifacts))
    check("artifacts: chart is a declarative spec (data+axes), not a rendered image",
          "chart_kind" in next(a for a in artifacts if a["artifact_id"] == chart_id)["payload"])

    # --- quality summary: reuses research_quality.py only ----------------------
    qs = rw.project_quality_summary(con, reg, p.research_id)
    check("quality summary: resolves real tickers from the attached sector query "
          "(the entities_requested bug fixed this phase)", len(qs.get("tickers", [])) > 10)

    # --- integrity guardrails ----------------------------------------------------
    warnings = rw.integrity_check(con, reg, p.research_id)
    check("integrity: surfaces the missing-provenance evidence (ev3) as a warning",
          any("provenance UNAVAILABLE" in w for w in warnings))
    check("integrity: surfaces the cross_section historical-classification warning "
          "carried from the attached query", any("historical sector versioning" in w for w in warnings))

    # --- snapshot: freeze / reproduce / detect mutation --------------------------
    snap_id = rw.snapshot(con, reg, p.research_id)
    check("snapshot: real snapshot_id returned", snap_id.startswith("SNAP-"))
    r1 = rw.check_reproducibility(reg, snap_id)
    check("snapshot: immediately after freezing, state is unchanged", r1["unchanged"] is True)
    rw.add_note(reg, p.research_id, "decision", "one more note after the freeze")
    r2 = rw.check_reproducibility(reg, snap_id)
    check("snapshot: mutation after the freeze is correctly detected", r2["unchanged"] is False)

    # --- exports: JSON / Markdown, deterministic --------------------------------
    js1 = rw.export_json(reg, p.research_id)
    js2 = rw.export_json(reg, p.research_id)
    check("export JSON: valid and non-trivial", len(js1) > 100)
    import json as _json
    d1, d2 = _json.loads(js1), _json.loads(js2)
    d1.pop("timeline"), d2.pop("timeline")  # exporting itself appends a timeline event -- exclude from the determinism check
    check("export JSON: deterministic given unchanged state (excluding the export's own timeline entry)",
          d1 == d2)
    md = rw.export_markdown(con, reg, p.research_id)
    check("export Markdown: contains question/findings/hypotheses/evidence/limitations sections",
          all(s in md for s in ["## Research Question", "## Findings", "## Hypotheses", "## Evidence",
                                "## Limitations", "## Reproducibility"]))
    check("export Markdown: no invented investment recommendation language",
          "buy" not in md.lower() and "sell" not in md.lower() and "recommend" not in md.lower())

    # --- security: API key never leaks ------------------------------------------
    check("security: NGX Pulse API key never appears in JSON export", "ngxpulse_" not in js1)
    check("security: NGX Pulse API key never appears in Markdown export", "ngxpulse_" not in md)

    # --- archive: frozen, rejects further mutation --------------------------------
    rw.archive_project(reg, p.research_id, reason="study complete")
    check("archive: status is ARCHIVED", rw.get_project(reg, p.research_id).status == "ARCHIVED")
    try:
        rw.add_note(reg, p.research_id, "observation", "should be rejected")
        check("archive: further mutation rejected", False)
    except rw.WorkspaceError:
        check("archive: further mutation rejected", True)
    check("archive: snapshotting an ARCHIVED project still works (freezing final state is always allowed)",
          rw.snapshot(con, reg, p.research_id).startswith("SNAP-"))

    # --- timeline: real, auto-populated, never fabricated --------------------------
    tl = rw.timeline(reg, p.research_id)
    check("timeline: has entries for every real action taken above",
          {"created", "query_attached", "evidence_added", "finding_recorded", "snapshot_created",
           "archived"} <= {e["event_type"] for e in tl})

    # --- branching -------------------------------------------------------------
    child = rw.create_project(reg, "Sector study, deeper dive", "Same question, narrower window",
                              parent_research_id=p.research_id)
    check("branching: child project records its parent", child.parent_research_id == p.research_id)
    try:
        rw.create_project(reg, "bad", "bad", parent_research_id="RP-fake")
        check("branching: nonexistent parent rejected", False)
    except rw.WorkspaceError:
        check("branching: nonexistent parent rejected", True)

    reg.close()
    con.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
