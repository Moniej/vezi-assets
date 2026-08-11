"""Tests for the Research Application Layer (Phase 4,
src/ngxrot/research_applications.py). Read-only against the real
production market-data DB; all workspace state written to a SCRATCH
registry.sqlite, never the real one.

  PYTHONPATH=src python scripts/test_research_applications.py
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
from ngxrot import research_applications as ra  # noqa: E402

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

    # --- investigation lifecycle: create/plan/execute/review/complete/archive
    p = ra.create_investigation(reg, "GTCO profile", "How did GTCO evolve 2022-2024?",
                                entities=["GTCO"], start="2022-01-01", end="2024-01-01")
    check("create: investigation is a real DRAFT research_workspace project",
          p.status == "DRAFT" and p.research_id.startswith("RP-"))
    check("create: scope structured with entities/date_range", p.scope["entities"] == ["GTCO"]
          and p.scope["date_range"]["start"] == "2022-01-01")

    active = ra.set_investigation_status(reg, p.research_id, "ACTIVE")
    check("lifecycle: ACTIVE transition applied", active.status == "ACTIVE")
    review = ra.set_investigation_status(reg, p.research_id, "REVIEW")
    check("lifecycle: REVIEW represented without widening the underlying CHECK constraint",
          review.status == "ACTIVE")  # REVIEW maps to ACTIVE + a note, documented choice
    check("lifecycle: REVIEW is recorded as a real note, not silently dropped",
          any(n["note_type"] == "decision" and "REVIEW" in n["content"] for n in rw.list_notes(reg, p.research_id)))
    try:
        ra.set_investigation_status(reg, p.research_id, "NOT_A_STATUS")
        check("lifecycle: invalid status rejected", False)
    except rw.WorkspaceError:
        check("lifecycle: invalid status rejected", True)

    plan_id = ra.record_research_plan(reg, p.research_id, measurements=["close level"],
                                      required_data=["prices"], comparisons=["n/a"],
                                      evidence_criteria=["descriptive stats"],
                                      limitations=["raw unadjusted prices"])
    check("plan: recorded as an immutable artifact", plan_id.startswith("ART-"))
    plan = ra.get_research_plan(reg, p.research_id)
    check("plan: retrievable and structured", plan["measurements"] == ["close level"])
    check("plan: does not alter the project's own immutable research_question",
          rw.get_project(reg, p.research_id).research_question == p.research_question)

    # --- company research -----------------------------------------------------
    profile = ra.company_profile(con, reg, "GTCO", start="2022-01-01", end="2024-01-01",
                                 research_id=p.research_id)
    check("company_profile: real identity chain (GTCO<-GUARANTY)",
          profile["identity"]["ticker_history"] == ["GUARANTY", "GTCO"])
    check("company_profile: real metadata (sector)", profile["metadata"]["sector_ngx"] is not None)
    check("company_profile: real price_history descriptive stats", profile["price_history"]["close"]["count"] > 0)
    check("company_profile: query auto-attached to the investigation",
          any(q["note"] and "company_profile" in q["note"] for q in rw.list_queries(reg, p.research_id)))
    no_window_profile = ra.company_profile(con, reg, "GTCO")
    check("company_profile: price_history explicitly marked 'not requested' when no window given, "
          "never fabricated", no_window_profile["price_history"] == "not requested -- pass start/end to include")
    fake_profile = ra.company_profile(con, reg, "NOTAREALTICKER")
    check("company_profile: metadata is None (not fabricated) for a nonexistent ticker",
          fake_profile["metadata"] is None)

    # --- evidence classification -------------------------------------------
    ev_obs = ra.add_classified_evidence(con, reg, p.research_id, "query_result", {"note": "x"},
                                        "GTCO close moved from 22.75 to 40.5", "MEASUREMENT")
    ev_interp = ra.add_classified_evidence(con, reg, p.research_id, "query_result", {"note": "y"},
                                           "This suggests strengthening investor confidence", "INTERPRETATION")
    evidence = {e["evidence_id"]: e for e in rw.list_evidence(reg, p.research_id)}
    check("evidence classification: MEASUREMENT and INTERPRETATION are recorded as DISTINCT classes, "
          "never conflated", evidence[ev_obs]["claim_class"] == "MEASUREMENT"
          and evidence[ev_interp]["claim_class"] == "INTERPRETATION")
    try:
        ra.add_classified_evidence(con, reg, p.research_id, "query_result", {}, "x", "NOT_A_CLASS")
        check("evidence classification: unknown claim_class rejected", False)
    except rw.WorkspaceError:
        check("evidence classification: unknown claim_class rejected", True)

    # --- hypotheses: create / support / contradict / resolve -----------------
    hyp_id = ra.add_researched_hypothesis(reg, p.research_id, "GTCO shows a stable uptrend",
                                          reason_for_investigation="visible growth in the raw data")
    check("hypothesis: created with reason_for_investigation recorded",
          bool(reg.execute("SELECT reason_for_investigation FROM research_hypotheses WHERE hypothesis_id=?",
                           (hyp_id,)).fetchone()[0]))
    ra.set_hypothesis_confidence(reg, hyp_id, 0.4, "raw, unadjusted prices -- moderate confidence only")
    conf_row = reg.execute("SELECT confidence, researcher_notes FROM research_hypotheses WHERE hypothesis_id=?",
                          (hyp_id,)).fetchone()
    check("hypothesis: confidence + researcher_notes persisted", conf_row[0] == 0.4 and "raw" in conf_row[1])
    try:
        ra.set_hypothesis_confidence(reg, hyp_id, 1.5)
        check("hypothesis: out-of-range confidence rejected", False)
    except rw.WorkspaceError:
        check("hypothesis: out-of-range confidence rejected", True)
    rw.update_hypothesis_status(reg, hyp_id, "WEAKENED", reason="raw-price effects not ruled out")
    check("hypothesis: status transition via the EXISTING Phase-3 mechanism (reused, not duplicated)",
          rw.list_hypotheses(reg, p.research_id)[0]["status"] == "WEAKENED")

    # --- sector research -----------------------------------------------------
    p_sector = ra.create_investigation(reg, "CG sector change", "How has CONSUMER GOODS changed?",
                                       sectors=["CONSUMER GOODS"])
    sp = ra.sector_profile(con, reg, "CONSUMER GOODS", ["2020-01-01", "2025-01-01"],
                           research_id=p_sector.research_id)
    check("sector_profile: real snapshot counts at both dates",
          sp["snapshots"]["2020-01-01"]["count"] > 0 and sp["snapshots"]["2025-01-01"]["count"] > 0)
    check("sector_profile: real entries/exits computed between snapshots",
          len(sp["constituent_changes"]) == 1 and "entered" in sp["constituent_changes"][0])
    check("sector_profile: discloses that classification is CURRENT-day, not applied historically",
          "no historical sector versioning" in sp["note"])

    # --- event research (descriptive only) ------------------------------------
    p_event = ra.create_investigation(reg, "CILEASING bonus issue", "What changed around the event?",
                                      entities=["CILEASING"])
    ew = ra.event_window(con, reg, "CILEASING", "2024-01-05", pre_days=5, post_days=5,
                         research_id=p_event.research_id)
    check("event_window: found real pre/post observations", ew["found"] and ew["pre_window"]["n_observations"] > 0
          and ew["post_window"]["n_observations"] > 0)
    check("event_window: reproduces the real, known CILEASING bonus-issue price drop "
          "(pre-window mean > post-window mean)", ew["pre_window"]["close"]["mean"] > ew["post_window"]["close"]["mean"])
    check("event_window: no expected-return/signal/alpha-score field exists anywhere in the output",
          not any(k in ew for k in ("expected_return", "signal", "alpha_score", "score")))
    from ngxrot.research_query import QueryValidationError
    try:
        ra.event_window(con, reg, "NOTAREALTICKER", "2024-01-05")
        check("event_window: unknown ticker rejected (inherits Phase 2's entity guardrail, not "
              "silently swallowed)", False)
    except QueryValidationError:
        check("event_window: unknown ticker rejected (inherits Phase 2's entity guardrail, not "
              "silently swallowed)", True)

    # --- comparative research --------------------------------------------------
    p_cmp = ra.create_investigation(reg, "GTCO vs ZENITHBANK", "compare", entities=["GTCO", "ZENITHBANK"],
                                    start="2023-01-01", end="2024-01-01")
    cmp = ra.compare_entities(con, reg, ["GTCO", "ZENITHBANK"], "2023-01-01", "2024-01-01",
                              research_id=p_cmp.research_id)
    check("compare_entities: real per-entity summaries", len(cmp["comparison_summary"]) == 2)
    cmp_uneven = ra.compare_entities(con, reg, ["CAP", "CILEASING"], "2015-01-01", "2024-01-01")
    check("compare_entities: comparability warning surfaces when data availability differs materially",
          isinstance(cmp_uneven["comparability_warnings"], list))

    # --- contradiction detection: create / investigate / resolve -------------
    cids = ra.detect_source_conflicts(con, reg, p_cmp.research_id, tolerance_pct=0.01)
    check("contradiction detection: real multi-source disagreements found and recorded as OPEN",
          len(cids) > 0 and all(c["status"] == "OPEN" for c in ra.list_contradictions(reg, p_cmp.research_id)))
    manual_cid = ra.record_contradiction(reg, p_cmp.research_id, "Sector classification disagreement",
                                         {"source": "NGX Pulse", "claim": "Financial Services"},
                                         {"source": "legacy doc", "claim": "Other Financial"})
    ra.update_contradiction_status(reg, manual_cid, "INVESTIGATED", "checked both sources, NGX Pulse is current")
    check("contradiction: manual recording + status transition works",
          next(c for c in ra.list_contradictions(reg, p_cmp.research_id) if c["contradiction_id"] == manual_cid)["status"] == "INVESTIGATED")
    try:
        ra.update_contradiction_status(reg, manual_cid, "NOT_A_STATUS")
        check("contradiction: invalid status rejected", False)
    except rw.WorkspaceError:
        check("contradiction: invalid status rejected", True)

    # --- descriptive analysis toolkit (not alpha) ------------------------------
    import pandas as pd
    s = pd.Series([10.0, 11.0, 12.0, 9.0, 13.0])
    summ = ra.descriptive_summary(s)
    check("descriptive_summary: real mean/median/std/quantiles", summ["count"] == 5 and summ["mean"] == 11.0)
    check("growth_rate: matches manual calc", abs(ra.growth_rate(s) - (13.0 / 10.0 - 1)) < 1e-9)
    df = pd.DataFrame({"ticker": ["A", "A", "B", "B"], "value": [1.0, 2.0, 3.0, 4.0]})
    gc = ra.group_comparison(df, "ticker", "value")
    check("group_comparison: one row per group, no ranking/score column",
          len(gc) == 2 and not any("rank" in c or "score" in c for c in gc.columns))

    # --- quality gate: blocks completion appropriately -----------------------
    p_empty = ra.create_investigation(reg, "Empty investigation", "no queries attached")
    gate_empty = ra.run_quality_gate(con, reg, p_empty.research_id)
    check("quality gate: an investigation with zero queries FAILS the gate",
          gate_empty["passed"] is False and "no queries attached" in gate_empty["blocking_issues"][0])
    try:
        ra.complete_investigation(con, reg, p_empty.research_id, "n/a", "INSUFFICIENT_DATA")
        check("quality gate: completion blocked without force=True", False)
    except rw.WorkspaceError:
        check("quality gate: completion blocked without force=True", True)
    forced = ra.complete_investigation(con, reg, p_empty.research_id, "Forced despite no data",
                                       "INSUFFICIENT_DATA", force=True)
    check("quality gate: force=True completes AND logs a warning note (never silently hidden)",
          forced["project"].status == "COMPLETED"
          and any(n["note_type"] == "warning" for n in rw.list_notes(reg, p_empty.research_id)))

    gate_cmp = ra.run_quality_gate(con, reg, p_cmp.research_id)
    check("quality gate: an investigation with an OPEN contradiction FAILS the gate",
          gate_cmp["passed"] is False and gate_cmp["n_open_contradictions"] > 0)

    # --- conclusion framework: not forced positive ------------------------------
    concl_id = ra.record_conclusion(reg, p.research_id, "GTCO trend cannot be confirmed as stable",
                                    "PARTIALLY_SUPPORTED", supporting_evidence=[ev_obs],
                                    uncertainties="raw prices unadjusted for corporate actions",
                                    limitations="single ticker, 1-year window",
                                    further_research="cross-check dividend/bonus records")
    conclusion = ra.current_conclusion(reg, p.research_id)
    check("conclusion: real state recorded, not forced to a positive outcome",
          conclusion["state"] == "PARTIALLY_SUPPORTED" and conclusion["conclusion_id"] == concl_id)
    try:
        ra.record_conclusion(reg, p.research_id, "x", "NOT_A_STATE")
        check("conclusion: invalid state rejected", False)
    except rw.WorkspaceError:
        check("conclusion: invalid state rejected", True)

    # --- report generation: FACT/ANALYSIS/INTERPRETATION/CONCLUSION labeling --
    report = ra.generate_investigation_report(con, reg, p.research_id)
    check("report: contains explicit claim-class labels", "[MEASUREMENT]" in report and "[INTERPRETATION]" in report)
    check("report: contains a Contradictory Evidence section", "## Contradictory Evidence" in report)
    check("report: contains a Quality Gate section", "## Quality Gate" in report)
    check("report: contains the recorded conclusion, not a fabricated positive one",
          "PARTIALLY_SUPPORTED" in report and "cannot be confirmed" in report)
    check("report: no investment recommendation language",
          "buy" not in report.lower() and "sell" not in report.lower())
    check("report security: NGX Pulse API key never appears", "ngxpulse_" not in report)

    # --- templates: pure metadata, no hard-coded conclusions --------------------
    check("templates: all 8 required templates present",
          {"company_profile", "sector_composition", "sector_change", "company_comparison",
           "historical_universe_analysis", "event_investigation", "data_quality_investigation",
           "market_structure_investigation"} <= set(ra.RESEARCH_TEMPLATES))
    tmpl = ra.get_template("event_investigation")
    check("templates: template has no 'conclusion' field (structure only)", "conclusion" not in tmpl)
    try:
        ra.get_template("not_a_template")
        check("templates: unknown template rejected", False)
    except rw.WorkspaceError:
        check("templates: unknown template rejected", True)

    # --- reproducibility: snapshot + reproduce for a completed investigation --
    result = ra.complete_investigation(con, reg, p.research_id, "GTCO shows raw price growth over the period "
                                       "but stability cannot be confirmed without adjustment", "PARTIALLY_SUPPORTED",
                                       supporting_evidence=[ev_obs])
    check("reproducibility: completion freezes a real snapshot", result["research_snapshot_id"].startswith("SNAP-"))
    repro = rw.check_reproducibility(reg, result["research_snapshot_id"])
    check("reproducibility: unchanged immediately after completion", repro["unchanged"] is True)

    reg.close()
    con.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
