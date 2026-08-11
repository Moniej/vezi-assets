"""Research OS -- Phase 4: Investment Research Application Layer.

Turns the Research Workspace (Phase 3) + Research Query Layer (Phase 2)
into reusable research APPLICATIONS: company research, sector research,
event research, comparative research, contradiction detection, a formal
conclusion object, a quality gate, and research templates.

An "investigation" is a `research_workspace.ResearchProject` -- NOT a
new project model. This module adds exactly two genuinely new tables
(`research_contradictions`, `research_conclusions`, schema/registry.sql
"Phase 4" section) plus additive columns on Phase 3's evidence/
hypothesis tables. Every data access goes through Phase 2's
`research_query.execute()` or Phase 1's `research_quality.py`/
`lineage.py`/`instrument_identity.py` -- nothing here runs ad-hoc SQL
against the market-data DB directly except thin, read-only composition
already established by those modules.

No AI dependency. No alpha: every "finding"/"conclusion" produced here
is descriptive (what happened, what changed, what's uncertain), never a
signal, score, or recommendation.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timezone

import pandas as pd

from . import research_workspace as rw
from .research_query import QuerySpec, execute as run_query
from .research_quality import (corporate_action_notes, missing_observations, quality_flags,
                               source_conflicts, ticker_identity_notes)
from .instrument_identity import resolve_ticker_history_symbols


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


# ---------------------------------------------------------------------------
# 1. Investigation lifecycle -- thin structure over rw.ResearchProject
# ---------------------------------------------------------------------------

_INVESTIGATION_STATUSES = {"DRAFT", "ACTIVE", "REVIEW", "COMPLETED", "ARCHIVED"}


def create_investigation(reg: sqlite3.Connection, title: str, research_question: str, *,
                         entities: list[str] | None = None, sectors: list[str] | None = None,
                         universes: list[str] | None = None, indices: list[str] | None = None,
                         start: str | None = None, end: str | None = None, as_of: str | None = None,
                         research_objective: str | None = None, owner: str | None = None,
                         tags: list[str] | None = None) -> rw.ResearchProject:
    """An investigation IS a research_workspace project; this just
    structures `scope` consistently instead of leaving it free-form.
    `rw.create_project`'s DRAFT/ARCHIVED-only status vocabulary already
    covers 4 of the 5 requested states (DRAFT/ACTIVE/COMPLETED/ARCHIVED)
    plus PAUSED; REVIEW is added below as an accepted transition value."""
    scope = {"entities": entities or [], "sectors": sectors or [], "universes": universes or [],
             "indices": indices or [], "date_range": {"start": start, "end": end}, "as_of": as_of,
             "research_objective": research_objective}
    return rw.create_project(reg, title, research_question, scope=scope, owner=owner, tags=tags)


def set_investigation_status(reg: sqlite3.Connection, research_id: str, status: str) -> rw.ResearchProject:
    if status not in _INVESTIGATION_STATUSES:
        raise rw.WorkspaceError(f"unknown investigation status {status!r} -- must be one of "
                                f"{sorted(_INVESTIGATION_STATUSES)}")
    if status == "REVIEW":
        # rw.update_project's underlying CHECK constraint (DRAFT/ACTIVE/
        # PAUSED/COMPLETED/ARCHIVED) does not include REVIEW -- represent
        # it as ACTIVE with an explicit note rather than widening that
        # CHECK constraint for one extra state (same reasoning as not
        # widening research_hypotheses' status vocabulary).
        rw.add_note(reg, research_id, "decision", "investigation entered REVIEW (pre-completion quality check)")
        return rw.update_project(reg, research_id, status="ACTIVE")
    return rw.update_project(reg, research_id, status=status)


# ---------------------------------------------------------------------------
# 2. Research plan -- recorded as a structured 'research_note' artifact,
# never silently changing the project's own immutable research_question.
# ---------------------------------------------------------------------------

def record_research_plan(reg: sqlite3.Connection, research_id: str, *, measurements: list[str],
                         required_data: list[str], comparisons: list[str],
                         evidence_criteria: list[str], limitations: list[str]) -> str:
    payload = {"measurements": measurements, "required_data": required_data,
              "comparisons": comparisons, "evidence_criteria": evidence_criteria,
              "limitations": limitations}
    artifact_id = rw.add_artifact(reg, research_id, "research_note",
                                  parameters={"kind": "research_plan"}, payload=payload)
    rw._log_event(reg, research_id, "plan_recorded", f"artifact_id={artifact_id}")
    return artifact_id


def get_research_plan(reg: sqlite3.Connection, research_id: str) -> dict | None:
    plans = [a for a in rw.list_artifacts(reg, research_id)
            if a["artifact_type"] == "research_note" and a["parameters"].get("kind") == "research_plan"]
    return plans[-1]["payload"] if plans else None


# ---------------------------------------------------------------------------
# 3. Evidence classification
# ---------------------------------------------------------------------------

_CLAIM_CLASSES = {"FACT", "OBSERVATION", "MEASUREMENT", "DOCUMENT", "CONTEXT", "ASSUMPTION",
                  "INTERPRETATION"}


def add_classified_evidence(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str,
                            evidence_type: str, source_reference: dict, description: str,
                            claim_class: str) -> str:
    """Same as rw.add_evidence, plus a required claim_class -- e.g.
    'Company revenue increased 20%' is an OBSERVATION/MEASUREMENT;
    'this suggests improving competitive position' is INTERPRETATION.
    The two must never be conflated."""
    if claim_class not in _CLAIM_CLASSES:
        raise rw.WorkspaceError(f"unknown claim_class {claim_class!r} -- must be one of {sorted(_CLAIM_CLASSES)}")
    return rw.add_evidence(con, reg, research_id, evidence_type, source_reference, description,
                           claim_class=claim_class)


# ---------------------------------------------------------------------------
# 4. Hypothesis extensions (confidence/reasoning) -- reuses Phase 3's
# status vocabulary and status-log mechanism unchanged.
# ---------------------------------------------------------------------------

def add_researched_hypothesis(reg: sqlite3.Connection, research_id: str, statement: str, *,
                              reason_for_investigation: str | None = None) -> str:
    hypothesis_id = rw.add_hypothesis(reg, research_id, statement)
    if reason_for_investigation:
        reg.execute("UPDATE research_hypotheses SET reason_for_investigation = ? WHERE hypothesis_id = ?",
                   (reason_for_investigation, hypothesis_id))
        reg.commit()
    return hypothesis_id


def set_hypothesis_confidence(reg: sqlite3.Connection, hypothesis_id: str, confidence: float,
                              researcher_notes: str | None = None) -> None:
    if not (0.0 <= confidence <= 1.0):
        raise rw.WorkspaceError(f"confidence must be in [0,1], got {confidence}")
    reg.execute("UPDATE research_hypotheses SET confidence = ?, researcher_notes = COALESCE(?, researcher_notes) "
               "WHERE hypothesis_id = ?", (confidence, researcher_notes, hypothesis_id))
    reg.commit()


# ---------------------------------------------------------------------------
# 5. Contradiction detection + recording -- genuinely new capability.
# Never auto-resolves: only surfaces candidates and lets the researcher
# record/investigate/resolve them.
# ---------------------------------------------------------------------------

def record_contradiction(reg: sqlite3.Connection, research_id: str, description: str,
                         item_a: dict, item_b: dict) -> str:
    contradiction_id = _new_id("CONTRA")
    now = _now()
    reg.execute(
        "INSERT INTO research_contradictions (contradiction_id, research_id, description, item_a_json, "
        "item_b_json, status, resolution_note, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (contradiction_id, research_id, description, json.dumps(item_a, default=str),
         json.dumps(item_b, default=str), "OPEN", None, now, now))
    reg.execute("INSERT INTO research_contradictions_status_log (contradiction_id, old_status, "
               "new_status, changed_at, reason) VALUES (?,?,?,?,?)",
               (contradiction_id, None, "OPEN", now, "recorded"))
    reg.commit()
    rw._log_event(reg, research_id, "contradiction_recorded", f"contradiction_id={contradiction_id}")
    return contradiction_id


def update_contradiction_status(reg: sqlite3.Connection, contradiction_id: str, new_status: str,
                                resolution_note: str = "") -> None:
    row = reg.execute("SELECT research_id, status FROM research_contradictions WHERE contradiction_id = ?",
                      (contradiction_id,)).fetchone()
    if row is None:
        raise rw.WorkspaceError(f"no contradiction with contradiction_id {contradiction_id!r}")
    research_id, old_status = row
    if new_status not in {"OPEN", "INVESTIGATED", "RESOLVED"}:
        raise rw.WorkspaceError(f"unknown contradiction status {new_status!r}")
    now = _now()
    reg.execute("UPDATE research_contradictions SET status = ?, resolution_note = ?, updated_at = ? "
               "WHERE contradiction_id = ?", (new_status, resolution_note or None, now, contradiction_id))
    reg.execute("INSERT INTO research_contradictions_status_log (contradiction_id, old_status, "
               "new_status, changed_at, reason) VALUES (?,?,?,?,?)",
               (contradiction_id, old_status, new_status, now, resolution_note))
    reg.commit()
    rw._log_event(reg, research_id, "contradiction_status_changed",
                 f"contradiction_id={contradiction_id} {old_status} -> {new_status}")


def list_contradictions(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT contradiction_id, description, item_a_json, item_b_json, status, "
                       "resolution_note, created_at, updated_at FROM research_contradictions "
                       "WHERE research_id = ? ORDER BY created_at", (research_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(zip(["contradiction_id", "description", "item_a", "item_b", "status",
                      "resolution_note", "created_at", "updated_at"], r))
        d["item_a"] = json.loads(d["item_a"])
        d["item_b"] = json.loads(d["item_b"])
        out.append(d)
    return out


def detect_source_conflicts(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str,
                            tolerance_pct: float = 0.01) -> list[str]:
    """Scans every ticker/date-range referenced by this investigation's
    attached queries for multi-source price disagreement (reuses
    research_quality.source_conflicts, Phase 1 -- no new detection
    logic) and RECORDS each as an OPEN contradiction. Returns the new
    contradiction_ids. Never auto-picks a 'winning' source."""
    queries = rw.list_queries(reg, research_id)
    tickers: set[str] = set()
    starts, ends = [], []
    for q in queries:
        tickers.update(q["entities_requested"] or [])
        if q["date_range_start"]:
            starts.append(q["date_range_start"])
        if q["date_range_end"]:
            ends.append(q["date_range_end"])
    if not tickers or not starts:
        return []
    conflicts = source_conflicts(con, sorted(tickers), min(starts), max(ends), tolerance_pct=tolerance_pct)
    ids = []
    for _, row in conflicts.iterrows():
        cid = record_contradiction(
            reg, research_id,
            f"Multiple sources disagree on {row.ticker} close for {row.trade_date} beyond "
            f"{tolerance_pct:.1%} tolerance",
            {"source": "multi-source min", "claim": f"close={row.min_close}"},
            {"source": "multi-source max", "claim": f"close={row.max_close}"})
        ids.append(cid)
    return ids


# ---------------------------------------------------------------------------
# 6. Descriptive analysis toolkit (pure functions; not alpha factors)
# ---------------------------------------------------------------------------

def growth_rate(series: pd.Series) -> float | None:
    s = series.dropna()
    if len(s) < 2 or s.iloc[0] == 0:
        return None
    return float(s.iloc[-1] / s.iloc[0] - 1.0)


def descriptive_summary(series: pd.Series) -> dict:
    s = series.dropna()
    if s.empty:
        return {"count": 0, "mean": None, "median": None, "std": None, "min": None, "max": None,
               "q25": None, "q75": None}
    return {"count": int(s.count()), "mean": float(s.mean()), "median": float(s.median()),
           "std": float(s.std()) if len(s) > 1 else 0.0, "min": float(s.min()), "max": float(s.max()),
           "q25": float(s.quantile(0.25)), "q75": float(s.quantile(0.75))}


def group_comparison(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    """Per-group descriptive stats -- a research utility, never a ranking."""
    rows = []
    for name, g in df.groupby(group_col):
        summary = descriptive_summary(g[value_col])
        summary[group_col] = name
        rows.append(summary)
    return pd.DataFrame(rows)


def period_over_period_change(df: pd.DataFrame, date_col: str, value_col: str, group_col: str | None = None) -> pd.DataFrame:
    df = df.sort_values(date_col).copy()
    if group_col:
        df["change"] = df.groupby(group_col)[value_col].diff()
        df["pct_change"] = df.groupby(group_col)[value_col].pct_change()
    else:
        df["change"] = df[value_col].diff()
        df["pct_change"] = df[value_col].pct_change()
    return df


def before_after_comparison(df: pd.DataFrame, date_col: str, value_col: str, cutoff_date: str) -> dict:
    before = df[df[date_col] < cutoff_date][value_col]
    after = df[df[date_col] >= cutoff_date][value_col]
    return {"before": descriptive_summary(before), "after": descriptive_summary(after),
           "cutoff_date": cutoff_date}


# ---------------------------------------------------------------------------
# 7. Company research
# ---------------------------------------------------------------------------

def company_profile(con: sqlite3.Connection, reg: sqlite3.Connection, ticker: str, *,
                    start: str | None = None, end: str | None = None,
                    research_id: str | None = None) -> dict:
    """Structured company research profile. Every field is either real
    data or explicitly `None`/'not available' -- NEVER fabricated to
    look complete."""
    profile: dict = {"ticker": ticker, "generated_at": _now()}

    identity = resolve_ticker_history_symbols(con, ticker)
    profile["identity"] = {"resolved": len(identity) >= 1, "ticker_history": [e.ticker for e in identity],
                           "eras": [{"ticker": e.ticker, "valid_from": e.valid_from, "valid_to": e.valid_to}
                                   for e in identity]}

    meta_row = con.execute("SELECT name, board, listing_date, delisting_date, sector_ngx, "
                           "reporting_currency FROM securities WHERE ticker = ?", (ticker,)).fetchone()
    if meta_row:
        profile["metadata"] = dict(zip(["name", "board", "listing_date", "delisting_date", "sector_ngx",
                                        "reporting_currency"], meta_row))
    else:
        profile["metadata"] = None

    if start and end:
        result = run_query(con, QuerySpec(query_type="prices", entities=[ticker], start=start, end=end,
                                          fields=["close", "volume"]), reg=reg, log=research_id is not None)
        if research_id and result.row_count > 0:
            rw.attach_query(reg, research_id, result.query_id, note=f"company_profile price history for {ticker}")
        obs = result.observations
        profile["price_history"] = {
            "n_observations": result.row_count,
            "date_range": [obs.trade_date.min(), obs.trade_date.max()] if not obs.empty else [None, None],
            "close": descriptive_summary(obs["close"]) if "close" in obs.columns else None,
            "volume": descriptive_summary(obs["volume"]) if "volume" in obs.columns else None,
            "growth_rate": growth_rate(obs["close"]) if "close" in obs.columns else None,
            "data_sources": result.data_sources,
        }
    else:
        profile["price_history"] = "not requested -- pass start/end to include"

    profile["corporate_actions"] = corporate_action_notes(con, [ticker]).to_dict(orient="records")
    profile["data_quality_flags"] = quality_flags(con, [ticker], start, end).to_dict(orient="records")

    membership = pd.read_sql("SELECT index_code, effective_from, effective_to FROM index_membership "
                             "WHERE ticker = ? ORDER BY effective_from", con, params=(ticker,))
    profile["universe_membership"] = membership.to_dict(orient="records") if not membership.empty else []

    if research_id:
        profile["research_findings"] = [f for f in rw.list_findings(reg, research_id)
                                        if ticker in f["statement"] or ticker in f["title"]]
    else:
        profile["research_findings"] = "not requested -- pass research_id to include"

    return profile


# ---------------------------------------------------------------------------
# 8. Sector research
# ---------------------------------------------------------------------------

def sector_profile(con: sqlite3.Connection, reg: sqlite3.Connection, sector: str, as_of_dates: list[str],
                   research_id: str | None = None) -> dict:
    """Sector composition + entries/exits across multiple as-of dates.
    Historical classification is NOT applied backwards -- every snapshot
    uses the CURRENT sector_ngx classification (this schema has no
    historical versioning), explicitly disclosed per snapshot, matching
    Phase 2's cross_section survivorship warning."""
    snapshots = {}
    for as_of in sorted(as_of_dates):
        result = run_query(con, QuerySpec(query_type="cross_section", entity_kind="sector",
                                          filters={"sector": sector}, as_of=as_of, fields=["close"]),
                           reg=reg, log=research_id is not None)
        if research_id and result.row_count > 0:
            rw.attach_query(reg, research_id, result.query_id, note=f"{sector} composition @ {as_of}")
        snapshots[as_of] = {"tickers": sorted(result.observations.ticker.tolist()) if not result.observations.empty else [],
                           "count": result.row_count, "warnings": result.warnings}

    dates_sorted = sorted(as_of_dates)
    changes = []
    for i in range(1, len(dates_sorted)):
        prev_set = set(snapshots[dates_sorted[i - 1]]["tickers"])
        cur_set = set(snapshots[dates_sorted[i]]["tickers"])
        changes.append({"from": dates_sorted[i - 1], "to": dates_sorted[i],
                       "entered": sorted(cur_set - prev_set), "exited": sorted(prev_set - cur_set),
                       "unchanged_count": len(prev_set & cur_set)})

    return {"sector": sector, "as_of_dates": dates_sorted, "snapshots": snapshots,
           "constituent_changes": changes,
           "note": "classification is CURRENT-day sector_ngx applied to every snapshot -- this schema "
                   "has no historical sector versioning, so entries/exits reflect membership at each "
                   "as-of date under today's taxonomy, not necessarily the taxonomy in force at that time"}


# ---------------------------------------------------------------------------
# 9. Event research (descriptive only -- no expected return, no signal)
# ---------------------------------------------------------------------------

def event_window(con: sqlite3.Connection, reg: sqlite3.Connection, ticker: str, event_date: str,
                 pre_days: int = 10, post_days: int = 10, research_id: str | None = None) -> dict:
    from . import db
    pre_start = (pd.Timestamp(event_date) - pd.Timedelta(days=pre_days * 2)).strftime("%Y-%m-%d")
    post_end = (pd.Timestamp(event_date) + pd.Timedelta(days=post_days * 2)).strftime("%Y-%m-%d")
    result = run_query(con, QuerySpec(query_type="prices", entities=[ticker], start=pre_start, end=post_end,
                                      fields=["close", "volume"]), reg=reg, log=research_id is not None)
    if research_id and result.row_count > 0:
        rw.attach_query(reg, research_id, result.query_id, note=f"event window for {ticker} @ {event_date}")
    obs = result.observations
    if obs.empty:
        return {"ticker": ticker, "event_date": event_date, "found": False,
               "note": "no observations in the requested window"}
    before = obs[obs.trade_date < event_date].tail(pre_days)
    after = obs[obs.trade_date >= event_date].head(post_days)

    calendar_days = pd.read_sql(
        "SELECT DISTINCT trade_date FROM index_levels WHERE trade_date BETWEEN ? AND ?", con,
        params=(pre_start, post_end))
    expected_days = len(calendar_days)
    missing = expected_days - result.row_count if expected_days else None

    return {
        "ticker": ticker, "event_date": event_date, "found": True,
        "pre_window": {"n_observations": len(before), "close": descriptive_summary(before["close"]),
                      "volume": descriptive_summary(before["volume"])},
        "post_window": {"n_observations": len(after), "close": descriptive_summary(after["close"]),
                       "volume": descriptive_summary(after["volume"])},
        "missing_observations_in_full_window": missing,
        "data_quality_flags": quality_flags(con, [ticker], pre_start, post_end).to_dict(orient="records"),
        "data_sources": result.data_sources,
        "note": "descriptive only -- before/after price and volume levels, no expected return, "
               "signal, or alpha score computed",
    }


# ---------------------------------------------------------------------------
# 10. Comparative research
# ---------------------------------------------------------------------------

def compare_entities(con: sqlite3.Connection, reg: sqlite3.Connection, entities: list[str], start: str,
                     end: str, field: str = "close", research_id: str | None = None) -> dict:
    result = run_query(con, QuerySpec(query_type="compare", entities=entities, start=start, end=end,
                                      fields=[field]), reg=reg, log=research_id is not None)
    if research_id and result.row_count > 0:
        rw.attach_query(reg, research_id, result.query_id, note=f"comparison: {', '.join(entities)}")
    comparability_warnings = []
    summary = result.execution_metadata.get("comparison_summary", [])
    counts = {row["ticker"]: row["n_observations"] for row in summary}
    if counts:
        max_n, min_n = max(counts.values()), min(counts.values())
        if max_n > 0 and (max_n - min_n) / max_n > 0.1:
            comparability_warnings.append(
                f"data availability differs materially across entities: {counts} -- comparing these "
                f"directly may not be apples-to-apples")
    return {"entities": entities, "period": {"start": start, "end": end}, "field": field,
           "comparison_summary": summary, "comparability_warnings": comparability_warnings,
           "data_sources": result.data_sources, "warnings": result.warnings}


# ---------------------------------------------------------------------------
# 11. Research tables (thin pivots over query results, stored as artifacts)
# ---------------------------------------------------------------------------

def make_entity_metric_table(reg: sqlite3.Connection, research_id: str, query_result, metric: str,
                             title: str = "") -> str:
    df = query_result.observations
    if metric not in df.columns:
        raise rw.WorkspaceError(f"metric {metric!r} not present in this query result")
    pivot = df.pivot_table(index="trade_date", columns="ticker", values=metric)
    payload = {"title": title, "metric": metric, "table": pivot.reset_index().to_dict(orient="records")}
    return rw.add_artifact(reg, research_id, "table", source_query_id=query_result.query_id,
                          parameters={"metric": metric}, payload=payload)


# ---------------------------------------------------------------------------
# 12. Quality gate -- must run before COMPLETED, and its warnings are
# forced into the final report (never silently dropped).
# ---------------------------------------------------------------------------

def run_quality_gate(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str) -> dict:
    integrity_warnings = rw.integrity_check(con, reg, research_id)
    open_contradictions = [c for c in list_contradictions(reg, research_id) if c["status"] == "OPEN"]
    queries = rw.list_queries(reg, research_id)
    has_snapshot = bool(reg.execute("SELECT 1 FROM research_snapshots WHERE research_id = ? LIMIT 1",
                                    (research_id,)).fetchone())
    blocking = []
    if not queries:
        blocking.append("no queries attached -- an investigation with no executed queries cannot be completed")
    if open_contradictions:
        blocking.append(f"{len(open_contradictions)} OPEN contradiction(s) unresolved")
    warnings = list(integrity_warnings)
    passed = len(blocking) == 0
    return {"passed": passed, "blocking_issues": blocking, "warnings": warnings,
           "has_snapshot": has_snapshot, "n_queries": len(queries),
           "n_open_contradictions": len(open_contradictions)}


def complete_investigation(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str,
                           conclusion_statement: str, state: str, *,
                           supporting_evidence: list[str] | None = None,
                           contradicting_evidence: list[str] | None = None,
                           uncertainties: str = "", limitations: str = "",
                           further_research: str = "", force: bool = False) -> dict:
    """Runs the quality gate; refuses to mark COMPLETED if blocking
    issues remain (unless force=True, which is itself logged). Always
    requires a conclusion to be recorded -- an investigation cannot be
    completed silently with no stated outcome."""
    gate = run_quality_gate(con, reg, research_id)
    if not gate["passed"] and not force:
        raise rw.WorkspaceError(
            f"quality gate FAILED for {research_id}: {gate['blocking_issues']} -- fix these, or pass "
            f"force=True to complete anyway (this will be logged, not hidden)")
    conclusion_id = record_conclusion(reg, research_id, conclusion_statement, state,
                                      supporting_evidence=supporting_evidence,
                                      contradicting_evidence=contradicting_evidence,
                                      uncertainties=uncertainties, limitations=limitations,
                                      further_research=further_research)
    if not gate["passed"] and force:
        rw.add_note(reg, research_id, "warning",
                   f"investigation force-completed with unresolved quality-gate issues: {gate['blocking_issues']}")
    # Status is set to COMPLETED BEFORE snapshotting -- the frozen
    # snapshot must reflect the investigation's actual final state, not
    # a moment just before completion (a real ordering bug caught by
    # scripts/test_research_applications.py's own reproducibility check:
    # snapshotting first left check_reproducibility() reporting spurious
    # drift immediately after completion, since project.status differed
    # between the frozen snapshot and the post-completion live state).
    project = rw.update_project(reg, research_id, status="COMPLETED")
    snap_id = rw.snapshot(con, reg, research_id)
    return {"project": project, "quality_gate": gate, "conclusion_id": conclusion_id,
           "research_snapshot_id": snap_id}


# ---------------------------------------------------------------------------
# 13. Conclusion framework
# ---------------------------------------------------------------------------

_CONCLUSION_STATES = {"SUPPORTED", "PARTIALLY_SUPPORTED", "INCONCLUSIVE", "CONTRADICTED",
                      "INSUFFICIENT_DATA"}


def record_conclusion(reg: sqlite3.Connection, research_id: str, statement: str, state: str, *,
                      supporting_evidence: list[str] | None = None,
                      contradicting_evidence: list[str] | None = None,
                      uncertainties: str = "", limitations: str = "", further_research: str = "") -> str:
    if state not in _CONCLUSION_STATES:
        raise rw.WorkspaceError(f"unknown conclusion state {state!r} -- must be one of {sorted(_CONCLUSION_STATES)}")
    conclusion_id = _new_id("CONCL")
    reg.execute(
        "INSERT INTO research_conclusions (conclusion_id, research_id, statement, state, "
        "supporting_evidence_json, contradicting_evidence_json, uncertainties, limitations, "
        "further_research, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (conclusion_id, research_id, statement, state, json.dumps(supporting_evidence or []),
         json.dumps(contradicting_evidence or []), uncertainties, limitations, further_research, _now()))
    reg.commit()
    rw._log_event(reg, research_id, "conclusion_recorded", f"conclusion_id={conclusion_id} state={state}")
    return conclusion_id


def list_conclusions(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT conclusion_id, statement, state, supporting_evidence_json, "
                       "contradicting_evidence_json, uncertainties, limitations, further_research, "
                       "created_at FROM research_conclusions WHERE research_id = ? ORDER BY created_at",
                       (research_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(zip(["conclusion_id", "statement", "state", "supporting_evidence",
                      "contradicting_evidence", "uncertainties", "limitations", "further_research",
                      "created_at"], r))
        d["supporting_evidence"] = json.loads(d["supporting_evidence"])
        d["contradicting_evidence"] = json.loads(d["contradicting_evidence"])
        out.append(d)
    return out


def current_conclusion(reg: sqlite3.Connection, research_id: str) -> dict | None:
    conclusions = list_conclusions(reg, research_id)
    return conclusions[-1] if conclusions else None


# ---------------------------------------------------------------------------
# 14. Research report generator -- extends rw.export_markdown with
# Contradictions/Quality-Gate/Conclusion sections and explicit FACT/
# ANALYSIS/INTERPRETATION/CONCLUSION labeling.
# ---------------------------------------------------------------------------

def generate_investigation_report(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str) -> str:
    p = rw.get_project(reg, research_id)
    if p is None:
        raise rw.WorkspaceError(f"no research project with research_id {research_id!r}")

    lines = [f"# {p.title}", "", f"**research_id**: {p.research_id}  ", f"**status**: {p.status}  ",
            f"**created**: {p.created_at}  **updated**: {p.updated_at}", ""]
    lines += ["## Research Question", "", p.research_question, ""]
    if p.scope:
        lines += ["## Scope", "", f"```json\n{json.dumps(p.scope, indent=2, default=str)}\n```", ""]

    plan = get_research_plan(reg, research_id)
    lines += ["## Research Plan", ""]
    if plan:
        for key in ["measurements", "required_data", "comparisons", "evidence_criteria", "limitations"]:
            lines.append(f"**{key.replace('_', ' ').title()}**:")
            for item in plan.get(key, []):
                lines.append(f"- {item}")
    else:
        lines.append("_no formal research plan recorded_")
    lines.append("")

    lines += ["## Data Sources / Queries", ""]
    queries = rw.list_queries(reg, research_id)
    if queries:
        lines.append("| query_id | type | rows | period | sources |")
        lines.append("|---|---|---|---|---|")
        for q in queries:
            lines.append(f"| {q['query_id']} | {q['query_type']} | {q['row_count']} | "
                        f"{q['date_range_start']}..{q['date_range_end']} | {', '.join(q['data_sources'])} |")
    else:
        lines.append("_no queries attached_")
    lines.append("")

    lines += ["## Evidence (classified)", ""]
    evidence = rw.list_evidence(reg, research_id)
    ev_classes = {}
    if evidence:
        rows_cls = reg.execute("SELECT evidence_id, claim_class FROM research_evidence WHERE research_id = ?",
                               (research_id,)).fetchall()
        ev_classes = dict(rows_cls)
        for e in evidence:
            cls = ev_classes.get(e["evidence_id"]) or "UNCLASSIFIED"
            prov = "resolved" if e["provenance"] else "UNAVAILABLE (disclosed, not hidden)"
            lines.append(f"- **[{cls}]** [{e['evidence_id']}] ({e['evidence_type']}, provenance: {prov}): "
                        f"{e['description']}")
    else:
        lines.append("_no evidence recorded_")
    lines.append("")

    lines += ["## Analysis (artifacts)", ""]
    artifacts = [a for a in rw.list_artifacts(reg, research_id)
                if not (a["artifact_type"] == "research_note" and a["parameters"].get("kind") == "research_plan")]
    if artifacts:
        for a in artifacts:
            lines.append(f"- **[ANALYSIS]** [{a['artifact_id']}] {a['artifact_type']} "
                        f"(content_hash={a['content_hash']})")
    else:
        lines.append("_no analysis artifacts recorded_")
    lines.append("")

    lines += ["## Findings", ""]
    findings = rw.list_findings(reg, research_id)
    if findings:
        for f in findings:
            lines.append(f"### [{f['finding_id']}] {f['title']} -- **{f['status']}**")
            lines.append("")
            lines.append(f"**[FACT/ANALYSIS]** {f['statement']}")
            lines.append("")
    else:
        lines.append("_no findings recorded_")
        lines.append("")

    lines += ["## Contradictory Evidence", ""]
    contradictions = list_contradictions(reg, research_id)
    if contradictions:
        for c in contradictions:
            lines.append(f"- **[{c['status']}]** [{c['contradiction_id']}] {c['description']}")
            lines.append(f"  - A: {c['item_a']}")
            lines.append(f"  - B: {c['item_b']}")
            if c["resolution_note"]:
                lines.append(f"  - resolution: {c['resolution_note']}")
    else:
        lines.append("_none recorded_")
    lines.append("")

    lines += ["## Hypotheses", ""]
    hyps = rw.list_hypotheses(reg, research_id)
    if hyps:
        conf_rows = dict(reg.execute("SELECT hypothesis_id, confidence FROM research_hypotheses "
                                     "WHERE research_id = ?", (research_id,)).fetchall())
        for h in hyps:
            conf = conf_rows.get(h["hypothesis_id"])
            conf_str = f", confidence={conf:.2f}" if conf is not None else ""
            lines.append(f"- **[{h['hypothesis_id']}]** ({h['status']}{conf_str}): {h['statement']}")
    else:
        lines.append("_no hypotheses tracked_")
    lines.append("")

    lines += ["## Quality Gate", ""]
    gate = run_quality_gate(con, reg, research_id)
    lines.append(f"**passed**: {gate['passed']}")
    if gate["blocking_issues"]:
        lines.append("\n**Blocking issues**:")
        for b in gate["blocking_issues"]:
            lines.append(f"- {b}")
    lines.append(f"\n**{len(gate['warnings'])} quality warning(s)** (full list preserved, not hidden):")
    for w in gate["warnings"][:20]:
        lines.append(f"- {w}")
    if len(gate["warnings"]) > 20:
        lines.append(f"- ... and {len(gate['warnings']) - 20} more (see `integrity_check()` for the full list)")
    lines.append("")

    lines += ["## Conclusion", ""]
    conclusion = current_conclusion(reg, research_id)
    if conclusion:
        lines.append(f"**[CONCLUSION, {conclusion['state']}]** {conclusion['statement']}")
        lines.append("")
        if conclusion["supporting_evidence"]:
            lines.append(f"Supporting: {', '.join(conclusion['supporting_evidence'])}")
        if conclusion["contradicting_evidence"]:
            lines.append(f"Contradicting: {', '.join(conclusion['contradicting_evidence'])}")
        if conclusion["uncertainties"]:
            lines.append(f"\n**What remains uncertain**: {conclusion['uncertainties']}")
        if conclusion["limitations"]:
            lines.append(f"\n**Data limitations**: {conclusion['limitations']}")
        if conclusion["further_research"]:
            lines.append(f"\n**Further research needed**: {conclusion['further_research']}")
    else:
        lines.append("_no conclusion recorded yet_")
    lines.append("")

    lines += ["## Reproducibility", "",
             f"code_fingerprint at project creation: `{p.code_fingerprint}`  ", ""]
    snaps = reg.execute("SELECT research_snapshot_id, created_at, content_hash FROM research_snapshots "
                       "WHERE research_id = ? ORDER BY created_at", (research_id,)).fetchall()
    if snaps:
        lines.append("| snapshot_id | created_at | content_hash |")
        lines.append("|---|---|---|")
        for s in snaps:
            lines.append(f"| {s[0]} | {s[1]} | {s[2]} |")
    else:
        lines.append("_no snapshot frozen yet_")
    lines.append("")

    rw._log_event(reg, research_id, "exported", "format=investigation_report")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 15. Research templates -- pure metadata, no hard-coded conclusions.
# ---------------------------------------------------------------------------

RESEARCH_TEMPLATES: dict[str, dict] = {
    "company_profile": {
        "questions": ["What is the historical identity, sector, and trading profile of this company?"],
        "required_data": ["securities metadata", "price/volume history", "corporate actions"],
        "analysis": ["descriptive_summary(close)", "descriptive_summary(volume)", "growth_rate(close)"],
        "expected_outputs": ["company_profile() dict"],
        "quality_checks": ["identity resolved", "data_quality_flags reviewed"],
    },
    "sector_composition": {
        "questions": ["What is the current composition of a given sector?"],
        "required_data": ["cross_section query for the sector"],
        "analysis": ["constituent count"],
        "expected_outputs": ["sector_profile() with a single as_of date"],
        "quality_checks": ["historical-classification warning reviewed"],
    },
    "sector_change": {
        "questions": ["How has sector composition changed between two or more dates?"],
        "required_data": ["cross_section query per as_of date"],
        "analysis": ["constituent entries/exits between snapshots"],
        "expected_outputs": ["sector_profile() with multiple as_of dates"],
        "quality_checks": ["historical-classification warning reviewed at every snapshot"],
    },
    "company_comparison": {
        "questions": ["How do two or more companies compare over a given period?"],
        "required_data": ["compare query across the entities"],
        "analysis": ["per-entity descriptive stats", "comparability warnings"],
        "expected_outputs": ["compare_entities() dict"],
        "quality_checks": ["data-availability comparability warning reviewed"],
    },
    "historical_universe_analysis": {
        "questions": ["What securities belonged to a universe/index at a given historical date?"],
        "required_data": ["universe_history query"],
        "analysis": ["membership list, entries/exits over time"],
        "expected_outputs": ["research_query.query_universe_history results"],
        "quality_checks": ["survivorship warning reviewed if using current universe rules on a past date"],
    },
    "event_investigation": {
        "questions": ["What observable market-data changes occurred around a documented event?"],
        "required_data": ["price/volume time series spanning the event window"],
        "analysis": ["before/after descriptive comparison, missing-observation count"],
        "expected_outputs": ["event_window() dict"],
        "quality_checks": ["missing observations in the window disclosed", "no expected-return computed"],
    },
    "data_quality_investigation": {
        "questions": ["How reliable is the data for a given ticker set/window?"],
        "required_data": ["quality_flags, missing_observations, source_conflicts"],
        "analysis": ["aggregate unresolved-flag counts, source-agreement rate"],
        "expected_outputs": ["research_quality.quality_report() / run_quality_gate()"],
        "quality_checks": ["this template IS the quality check"],
    },
    "market_structure_investigation": {
        "questions": ["How has trading activity (volume, value traded) evolved for a set of securities?"],
        "required_data": ["prices query with volume/value_traded fields"],
        "analysis": ["descriptive volume statistics, period-over-period change"],
        "expected_outputs": ["descriptive_summary()/period_over_period_change() over volume"],
        "quality_checks": ["stale-price flags reviewed (low volume can indicate staleness, not just illiquidity)"],
    },
}


def get_template(name: str) -> dict:
    if name not in RESEARCH_TEMPLATES:
        raise rw.WorkspaceError(f"unknown research template {name!r} -- must be one of "
                                f"{sorted(RESEARCH_TEMPLATES)}")
    return RESEARCH_TEMPLATES[name]
