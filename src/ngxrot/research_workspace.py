"""Research OS -- Phase 3: Research Workspace & Workflow Layer.

Turns the Research Query Layer (Phase 2) into a complete, reproducible
research INVESTIGATION: question -> scope -> queries -> evidence ->
analysis -> findings -> conclusion -> reproducible snapshot -> export.

Sits directly on top of Phase 2 (`research_query.py`, `query_log`) and
Phase 1 (`research_dataset.py`'s `dataset_snapshots`, `research_quality.
py`, `lineage.py`, `instrument_identity.py`). No dataset is copied here
-- a project references `query_id`s and `snapshot_id`s that already exist
immutably in `query_log`/`dataset_snapshots`.

All new tables live in the SAME `registry.sqlite` used by Phase 1/2
(`schema/registry.sql`, "Phase 3" section) -- no new database. Every
mutable object (`research_projects`, `research_findings`,
`research_hypotheses`) uses the same guard-trigger discipline the
platform already established (`hypotheses_frozen_guard`,
`hypotheses_guard_immutable_fields` in registry.sql): a fixed identity/
statement cannot change, only a constrained set of status-like fields
can, and every status transition is logged. Everything else
(`research_notes`, `research_evidence`, `research_artifacts`,
`research_snapshots`, `research_timeline`, `research_project_queries`)
is pure insert-only, matching `data_quality_log`'s append-only pattern
used throughout this project.

No AI dependency anywhere in this module.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from . import registry
from .lineage import trace_equity_observation
from .research_quality import quality_report


class WorkspaceError(ValueError):
    """Raised on an invalid/unsafe workspace operation -- unknown
    research_id, an attempt to modify an ARCHIVED project, an invalid
    status transition, etc. Always a specific, actionable message."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _hash_json(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _log_event(reg: sqlite3.Connection, research_id: str, event_type: str, detail: str = "") -> None:
    """Auto-populated, real actions only -- never a fabricated timeline
    entry. Called by every state-changing function in this module."""
    reg.execute(
        "INSERT INTO research_timeline (research_id, event_type, detail, occurred_at) VALUES (?,?,?,?)",
        (research_id, event_type, detail, _now()))
    reg.commit()


# ---------------------------------------------------------------------------
# Research project
# ---------------------------------------------------------------------------

@dataclass
class ResearchProject:
    research_id: str
    title: str
    research_question: str
    description: str | None
    status: str
    created_at: str
    updated_at: str
    owner: str | None
    tags: list[str]
    scope: dict | None
    dataset_snapshot_ids: list[str]
    code_fingerprint: str
    parent_research_id: str | None


_PROJECT_COLS = ["research_id", "title", "research_question", "description", "status",
                 "created_at", "updated_at", "owner", "tags_json", "scope_json",
                 "dataset_snapshot_ids_json", "code_fingerprint", "parent_research_id"]


def _row_to_project(row) -> ResearchProject:
    d = dict(zip(_PROJECT_COLS, row))
    return ResearchProject(
        research_id=d["research_id"], title=d["title"], research_question=d["research_question"],
        description=d["description"], status=d["status"], created_at=d["created_at"],
        updated_at=d["updated_at"], owner=d["owner"], tags=json.loads(d["tags_json"]),
        scope=json.loads(d["scope_json"]) if d["scope_json"] else None,
        dataset_snapshot_ids=json.loads(d["dataset_snapshot_ids_json"]),
        code_fingerprint=d["code_fingerprint"], parent_research_id=d["parent_research_id"])


def create_project(reg: sqlite3.Connection, title: str, research_question: str,
                   description: str = "", owner: str | None = None, tags: list[str] | None = None,
                   scope: dict | None = None, parent_research_id: str | None = None) -> ResearchProject:
    """Creates a DRAFT research project. `scope` should reference the
    EXISTING universe/PIT/identity systems (e.g. {"universe": "iru",
    "tickers": [...], "sectors": [...], "start": ..., "end": ...,
    "as_of": ..., "sources": [...], "fields": [...]}) -- this function
    does not validate scope against those systems itself; that happens
    naturally when queries are attached (Phase 2's own validate_spec
    already enforces it)."""
    if parent_research_id is not None and get_project(reg, parent_research_id) is None:
        raise WorkspaceError(f"parent_research_id {parent_research_id!r} does not exist")
    research_id = _new_id("RP")
    now = _now()
    reg.execute(
        f"INSERT INTO research_projects ({','.join(_PROJECT_COLS)}) VALUES ({','.join('?' * len(_PROJECT_COLS))})",
        (research_id, title, research_question, description, "DRAFT", now, now, owner,
         json.dumps(tags or []), json.dumps(scope) if scope else None, json.dumps([]),
         registry.code_fingerprint(), parent_research_id))
    reg.commit()
    _log_event(reg, research_id, "created", f"title={title!r}")
    if scope:
        _log_event(reg, research_id, "scope_defined", json.dumps(scope, default=str))
    if parent_research_id:
        _log_event(reg, research_id, "branched", f"parent={parent_research_id}")
    return get_project(reg, research_id)


def get_project(reg: sqlite3.Connection, research_id: str) -> ResearchProject | None:
    row = reg.execute(f"SELECT {','.join(_PROJECT_COLS)} FROM research_projects WHERE research_id = ?",
                      (research_id,)).fetchone()
    return _row_to_project(row) if row else None


def list_projects(reg: sqlite3.Connection, status: str | None = None) -> list[ResearchProject]:
    q = f"SELECT {','.join(_PROJECT_COLS)} FROM research_projects"
    params = ()
    if status:
        q += " WHERE status = ?"
        params = (status,)
    q += " ORDER BY created_at DESC"
    return [_row_to_project(r) for r in reg.execute(q, params).fetchall()]


def _require_project(reg: sqlite3.Connection, research_id: str) -> ResearchProject:
    p = get_project(reg, research_id)
    if p is None:
        raise WorkspaceError(f"no research project with research_id {research_id!r}")
    if p.status == "ARCHIVED":
        raise WorkspaceError(f"research project {research_id!r} is ARCHIVED (frozen) -- "
                             f"create a new project (optionally with parent_research_id set) instead")
    return p


def update_project(reg: sqlite3.Connection, research_id: str, *, status: str | None = None,
                   description: str | None = None, tags: list[str] | None = None,
                   scope: dict | None = None) -> ResearchProject:
    p = _require_project(reg, research_id)
    new_status = status or p.status
    new_desc = description if description is not None else p.description
    new_tags = tags if tags is not None else p.tags
    new_scope = scope if scope is not None else p.scope
    reg.execute(
        "UPDATE research_projects SET status=?, description=?, tags_json=?, scope_json=?, "
        "updated_at=? WHERE research_id=?",
        (new_status, new_desc, json.dumps(new_tags), json.dumps(new_scope) if new_scope else None,
         _now(), research_id))
    reg.commit()
    if status and status != p.status:
        _log_event(reg, research_id, "status_changed", f"{p.status} -> {status}")
    if scope is not None:
        _log_event(reg, research_id, "scope_defined", json.dumps(scope, default=str))
    return get_project(reg, research_id)


def archive_project(reg: sqlite3.Connection, research_id: str, reason: str = "") -> ResearchProject:
    p = update_project(reg, research_id, status="ARCHIVED")
    _log_event(reg, research_id, "archived", reason)
    return p


# ---------------------------------------------------------------------------
# Query attachment
# ---------------------------------------------------------------------------

def attach_query(reg: sqlite3.Connection, research_id: str, query_id: str, note: str = "") -> None:
    """Attaches an EXISTING query_log entry (Phase 2) to a project.
    Never copies the underlying dataset -- references query_log's own
    immutable QuerySpec/result-metadata row."""
    _require_project(reg, research_id)
    row = reg.execute("SELECT 1 FROM query_log WHERE query_id = ?", (query_id,)).fetchone()
    if row is None:
        raise WorkspaceError(f"query_id {query_id!r} does not exist in query_log -- "
                             f"execute it via research_query.execute() first")
    reg.execute("INSERT INTO research_project_queries (research_id, query_id, attached_at, note) "
               "VALUES (?,?,?,?)", (research_id, query_id, _now(), note))
    reg.commit()
    _log_event(reg, research_id, "query_attached", f"query_id={query_id}")


def list_queries(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute(
        "SELECT q.query_id, q.executed_at, q.query_type, q.parameters_json, q.row_count, "
        "q.date_range_start, q.date_range_end, q.data_sources_json, q.warnings_json, "
        "q.content_hash, q.entities_requested_json, pq.attached_at, pq.note "
        "FROM research_project_queries pq JOIN query_log q ON q.query_id = pq.query_id "
        "WHERE pq.research_id = ? ORDER BY pq.attached_at", (research_id,)).fetchall()
    cols = ["query_id", "executed_at", "query_type", "parameters", "row_count", "date_range_start",
            "date_range_end", "data_sources", "warnings", "content_hash", "entities_requested",
            "attached_at", "note"]
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        d["parameters"] = json.loads(d["parameters"])
        d["data_sources"] = json.loads(d["data_sources"])
        d["warnings"] = json.loads(d["warnings"])
        d["entities_requested"] = json.loads(d["entities_requested"]) if d["entities_requested"] else []
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

_NOTE_TYPES = {"observation", "interpretation", "question", "assumption", "decision", "warning"}


def add_note(reg: sqlite3.Connection, research_id: str, note_type: str, content: str) -> str:
    _require_project(reg, research_id)
    if note_type not in _NOTE_TYPES:
        raise WorkspaceError(f"unknown note_type {note_type!r} -- must be one of {sorted(_NOTE_TYPES)}")
    note_id = _new_id("NOTE")
    reg.execute("INSERT INTO research_notes (note_id, research_id, note_type, content, created_at) "
               "VALUES (?,?,?,?,?)", (note_id, research_id, note_type, content, _now()))
    reg.commit()
    _log_event(reg, research_id, "note_added", f"note_id={note_id} type={note_type}")
    return note_id


def list_notes(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT note_id, note_type, content, created_at FROM research_notes "
                       "WHERE research_id = ? ORDER BY created_at", (research_id,)).fetchall()
    return [dict(zip(["note_id", "note_type", "content", "created_at"], r)) for r in rows]


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

_EVIDENCE_TYPES = {"query_result", "dataset_observation", "source_document", "company_metadata",
                    "corporate_action", "historical_event", "calculation", "chart_table"}


def add_evidence(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str,
                 evidence_type: str, source_reference: dict, description: str,
                 claim_class: str | None = None) -> str:
    """`con` is the market-data DB (data/ngx.sqlite), used ONLY to
    resolve provenance for `dataset_observation` evidence via the
    EXISTING lineage.py -- no second provenance system. If provenance
    cannot be resolved, `provenance` is left explicitly NULL/absent
    rather than fabricated (Section 21: "missing provenance").

    `claim_class` (Phase 4, optional) tags the evidence as FACT/
    OBSERVATION/MEASUREMENT/DOCUMENT/CONTEXT/ASSUMPTION/INTERPRETATION --
    validated by the caller (research_applications.py), not here, since
    this module stays agnostic to Phase-4-specific vocabulary. Must be
    set at INSERT time: research_evidence is immutable, so there is no
    way to classify it after the fact."""
    _require_project(reg, research_id)
    if evidence_type not in _EVIDENCE_TYPES:
        raise WorkspaceError(f"unknown evidence_type {evidence_type!r} -- must be one of "
                             f"{sorted(_EVIDENCE_TYPES)}")
    provenance = None
    if evidence_type == "dataset_observation" and "ticker" in source_reference and "trade_date" in source_reference:
        lin = trace_equity_observation(con, source_reference["ticker"], source_reference["trade_date"])
        if lin.found:
            provenance = {"source_name": lin.source_name, "source_kind": lin.source_kind,
                         "ingestion_run": lin.ingestion_run, "validation_status": lin.validation_status,
                         "confidence": lin.confidence}
    evidence_id = _new_id("EV")
    reg.execute(
        "INSERT INTO research_evidence (evidence_id, research_id, evidence_type, source_reference_json, "
        "description, provenance_json, created_at, claim_class) VALUES (?,?,?,?,?,?,?,?)",
        (evidence_id, research_id, evidence_type, json.dumps(source_reference, default=str), description,
         json.dumps(provenance) if provenance else None, _now(), claim_class))
    reg.commit()
    _log_event(reg, research_id, "evidence_added",
              f"evidence_id={evidence_id} type={evidence_type} provenance={'resolved' if provenance else 'unavailable'}")
    return evidence_id


def list_evidence(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute(
        "SELECT evidence_id, evidence_type, source_reference_json, description, provenance_json, "
        "created_at, claim_class FROM research_evidence WHERE research_id = ? ORDER BY created_at",
        (research_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(zip(["evidence_id", "evidence_type", "source_reference", "description", "provenance",
                      "created_at", "claim_class"], r))
        d["source_reference"] = json.loads(d["source_reference"])
        d["provenance"] = json.loads(d["provenance"]) if d["provenance"] else None
        out.append(d)
    return out


def trace_evidence(reg: sqlite3.Connection, evidence_id: str) -> dict:
    """'What evidence supports this statement?' -> trace it back to its
    query/dataset/provider. Composition only, no new lineage system."""
    row = reg.execute("SELECT evidence_id, research_id, evidence_type, source_reference_json, "
                      "provenance_json FROM research_evidence WHERE evidence_id = ?",
                      (evidence_id,)).fetchone()
    if row is None:
        raise WorkspaceError(f"no evidence with evidence_id {evidence_id!r}")
    evidence_id, research_id, evidence_type, source_ref_json, provenance_json = row
    source_ref = json.loads(source_ref_json)
    chain = {"evidence_id": evidence_id, "evidence_type": evidence_type, "source_reference": source_ref,
            "provenance": json.loads(provenance_json) if provenance_json else None}
    if "query_id" in source_ref:
        q = reg.execute("SELECT query_type, parameters_json, data_sources_json FROM query_log "
                        "WHERE query_id = ?", (source_ref["query_id"],)).fetchone()
        if q:
            chain["query"] = {"query_type": q[0], "parameters": json.loads(q[1]),
                             "data_sources": json.loads(q[2])}
    return chain


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

_FINDING_STATUSES = {"PRELIMINARY", "SUPPORTED", "CONTESTED", "REJECTED", "UNRESOLVED"}


def add_finding(reg: sqlite3.Connection, research_id: str, title: str, statement: str,
                supporting_evidence: list[str] | None = None, status: str = "PRELIMINARY") -> str:
    """A finding is NOT an alpha signal -- e.g. 'sector membership data is
    incomplete before a given date' or 'two providers disagree on a
    subset of observations' are valid findings. Nothing here scores,
    ranks, or recommends anything."""
    _require_project(reg, research_id)
    if status not in _FINDING_STATUSES:
        raise WorkspaceError(f"unknown finding status {status!r} -- must be one of {sorted(_FINDING_STATUSES)}")
    for ev_id in supporting_evidence or []:
        if reg.execute("SELECT 1 FROM research_evidence WHERE evidence_id = ?", (ev_id,)).fetchone() is None:
            raise WorkspaceError(f"supporting_evidence references unknown evidence_id {ev_id!r}")
    finding_id = _new_id("FIND")
    now = _now()
    reg.execute(
        "INSERT INTO research_findings (finding_id, research_id, title, statement, status, "
        "supporting_evidence_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (finding_id, research_id, title, statement, status, json.dumps(supporting_evidence or []), now, now))
    reg.execute("INSERT INTO research_findings_status_log (finding_id, old_status, new_status, "
               "changed_at, reason) VALUES (?,?,?,?,?)", (finding_id, None, status, now, "created"))
    reg.commit()
    _log_event(reg, research_id, "finding_recorded", f"finding_id={finding_id} status={status}")
    return finding_id


def update_finding_status(reg: sqlite3.Connection, finding_id: str, new_status: str,
                          reason: str = "", supporting_evidence: list[str] | None = None) -> None:
    row = reg.execute("SELECT research_id, status FROM research_findings WHERE finding_id = ?",
                      (finding_id,)).fetchone()
    if row is None:
        raise WorkspaceError(f"no finding with finding_id {finding_id!r}")
    research_id, old_status = row
    if new_status not in _FINDING_STATUSES:
        raise WorkspaceError(f"unknown finding status {new_status!r} -- must be one of {sorted(_FINDING_STATUSES)}")
    now = _now()
    if supporting_evidence is not None:
        reg.execute("UPDATE research_findings SET status=?, supporting_evidence_json=?, updated_at=? "
                   "WHERE finding_id=?", (new_status, json.dumps(supporting_evidence), now, finding_id))
    else:
        reg.execute("UPDATE research_findings SET status=?, updated_at=? WHERE finding_id=?",
                   (new_status, now, finding_id))
    reg.execute("INSERT INTO research_findings_status_log (finding_id, old_status, new_status, "
               "changed_at, reason) VALUES (?,?,?,?,?)", (finding_id, old_status, new_status, now, reason))
    reg.commit()
    _log_event(reg, research_id, "finding_status_changed",
              f"finding_id={finding_id} {old_status} -> {new_status}")


def list_findings(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT finding_id, title, statement, status, supporting_evidence_json, "
                       "created_at, updated_at FROM research_findings WHERE research_id = ? "
                       "ORDER BY created_at", (research_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(zip(["finding_id", "title", "statement", "status", "supporting_evidence",
                      "created_at", "updated_at"], r))
        d["supporting_evidence"] = json.loads(d["supporting_evidence"])
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Hypotheses (Phase-3, generic -- distinct from registry.py's alpha `hypotheses`)
# ---------------------------------------------------------------------------

_HYPOTHESIS_STATUSES = {"OPEN", "SUPPORTED", "WEAKENED", "REJECTED", "UNRESOLVED"}


def add_hypothesis(reg: sqlite3.Connection, research_id: str, statement: str) -> str:
    """A research project's hypothesis is OPTIONAL and generic (not a
    trading hypothesis) -- e.g. 'the reported sector composition of the
    NGX has become more diversified since 2020.' No statistical
    hypothesis-testing framework is implemented; status is tracked by
    the researcher's own judgment against recorded findings."""
    _require_project(reg, research_id)
    hypothesis_id = _new_id("HYP")
    now = _now()
    reg.execute(
        "INSERT INTO research_hypotheses (hypothesis_id, research_id, statement, status, "
        "supporting_finding_ids_json, contradicting_finding_ids_json, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (hypothesis_id, research_id, statement, "OPEN", json.dumps([]), json.dumps([]), now, now))
    reg.execute("INSERT INTO research_hypotheses_status_log (hypothesis_id, old_status, new_status, "
               "changed_at, reason) VALUES (?,?,?,?,?)", (hypothesis_id, None, "OPEN", now, "created"))
    reg.commit()
    _log_event(reg, research_id, "hypothesis_added", f"hypothesis_id={hypothesis_id}")
    return hypothesis_id


def update_hypothesis_status(reg: sqlite3.Connection, hypothesis_id: str, new_status: str,
                             supporting_finding_ids: list[str] | None = None,
                             contradicting_finding_ids: list[str] | None = None,
                             reason: str = "") -> None:
    row = reg.execute("SELECT research_id, status FROM research_hypotheses WHERE hypothesis_id = ?",
                      (hypothesis_id,)).fetchone()
    if row is None:
        raise WorkspaceError(f"no hypothesis with hypothesis_id {hypothesis_id!r}")
    research_id, old_status = row
    if new_status not in _HYPOTHESIS_STATUSES:
        raise WorkspaceError(f"unknown hypothesis status {new_status!r} -- must be one of "
                             f"{sorted(_HYPOTHESIS_STATUSES)}")
    cur = reg.execute("SELECT supporting_finding_ids_json, contradicting_finding_ids_json "
                      "FROM research_hypotheses WHERE hypothesis_id = ?", (hypothesis_id,)).fetchone()
    supporting = supporting_finding_ids if supporting_finding_ids is not None else json.loads(cur[0])
    contradicting = contradicting_finding_ids if contradicting_finding_ids is not None else json.loads(cur[1])
    now = _now()
    reg.execute("UPDATE research_hypotheses SET status=?, supporting_finding_ids_json=?, "
               "contradicting_finding_ids_json=?, updated_at=? WHERE hypothesis_id=?",
               (new_status, json.dumps(supporting), json.dumps(contradicting), now, hypothesis_id))
    reg.execute("INSERT INTO research_hypotheses_status_log (hypothesis_id, old_status, new_status, "
               "changed_at, reason) VALUES (?,?,?,?,?)", (hypothesis_id, old_status, new_status, now, reason))
    reg.commit()
    _log_event(reg, research_id, "hypothesis_status_changed",
              f"hypothesis_id={hypothesis_id} {old_status} -> {new_status}")


def list_hypotheses(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT hypothesis_id, statement, status, supporting_finding_ids_json, "
                       "contradicting_finding_ids_json, created_at, updated_at FROM research_hypotheses "
                       "WHERE research_id = ? ORDER BY created_at", (research_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(zip(["hypothesis_id", "statement", "status", "supporting_finding_ids",
                      "contradicting_finding_ids", "created_at", "updated_at"], r))
        d["supporting_finding_ids"] = json.loads(d["supporting_finding_ids"])
        d["contradicting_finding_ids"] = json.loads(d["contradicting_finding_ids"])
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Analysis artifacts (tables / summary stats / comparisons / lightweight
# chart SPECS -- declarative, not rendered images; not a BI platform)
# ---------------------------------------------------------------------------

_ARTIFACT_TYPES = {"table", "summary_statistics", "comparison", "chart", "data_extract",
                   "calculation", "research_note"}


def add_artifact(reg: sqlite3.Connection, research_id: str, artifact_type: str, *,
                 source_query_id: str | None = None, parameters: dict | None = None,
                 payload: dict | list | None = None) -> str:
    _require_project(reg, research_id)
    if artifact_type not in _ARTIFACT_TYPES:
        raise WorkspaceError(f"unknown artifact_type {artifact_type!r} -- must be one of "
                             f"{sorted(_ARTIFACT_TYPES)}")
    artifact_id = _new_id("ART")
    content_hash = _hash_json(payload)
    reg.execute(
        "INSERT INTO research_artifacts (artifact_id, research_id, artifact_type, source_query_id, "
        "parameters_json, content_hash, payload_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (artifact_id, research_id, artifact_type, source_query_id, json.dumps(parameters or {}, default=str),
         content_hash, json.dumps(payload, default=str) if payload is not None else None, _now()))
    reg.commit()
    _log_event(reg, research_id, "artifact_added", f"artifact_id={artifact_id} type={artifact_type}")
    return artifact_id


def make_table_artifact(reg: sqlite3.Connection, research_id: str, query_result, title: str = "") -> str:
    """Wraps a Phase-2 QueryResult's observations as a `table` artifact."""
    payload = {"title": title, "columns": list(query_result.observations.columns),
              "rows": query_result.observations.to_dict(orient="records")}
    return add_artifact(reg, research_id, "table", source_query_id=query_result.query_id,
                        parameters=query_result.parameters, payload=payload)


def make_summary_artifact(reg: sqlite3.Connection, research_id: str, query_result, field: str = "close",
                          group_col: str = "ticker") -> str:
    """Descriptive (non-alpha) summary statistics per group, from a
    Phase-2 QueryResult -- mean/median/min/max/std/count only."""
    df = query_result.observations
    if field not in df.columns:
        raise WorkspaceError(f"field {field!r} not present in this query result's observations")
    stats = df.groupby(group_col)[field].agg(["count", "mean", "median", "min", "max", "std"]).reset_index()
    payload = {"field": field, "group_col": group_col, "stats": stats.to_dict(orient="records")}
    return add_artifact(reg, research_id, "summary_statistics", source_query_id=query_result.query_id,
                        parameters={"field": field, "group_col": group_col}, payload=payload)


def make_chart_spec(reg: sqlite3.Connection, research_id: str, query_result, chart_kind: str,
                    x: str = "trade_date", y: str = "close", series_col: str = "ticker") -> str:
    """A lightweight, DECLARATIVE chart spec (data + axes description),
    not a rendered image -- deliberately not a BI platform. `chart_kind`
    is one of 'time_series'|'cross_sectional'|'sector_composition'|
    'missingness', all descriptive."""
    valid_kinds = {"time_series", "cross_sectional", "sector_composition", "missingness"}
    if chart_kind not in valid_kinds:
        raise WorkspaceError(f"unknown chart_kind {chart_kind!r} -- must be one of {sorted(valid_kinds)}")
    df = query_result.observations
    payload = {"chart_kind": chart_kind, "x": x, "y": y, "series_col": series_col,
              "data": df.to_dict(orient="records") if not df.empty else []}
    return add_artifact(reg, research_id, "chart", source_query_id=query_result.query_id,
                        parameters={"chart_kind": chart_kind, "x": x, "y": y}, payload=payload)


def list_artifacts(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT artifact_id, artifact_type, source_query_id, parameters_json, "
                       "content_hash, payload_json, created_at FROM research_artifacts "
                       "WHERE research_id = ? ORDER BY created_at", (research_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(zip(["artifact_id", "artifact_type", "source_query_id", "parameters", "content_hash",
                      "payload", "created_at"], r))
        d["parameters"] = json.loads(d["parameters"])
        d["payload"] = json.loads(d["payload"]) if d["payload"] else None
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Quality summary (composition of research_quality.py only)
# ---------------------------------------------------------------------------

def project_quality_summary(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str) -> dict:
    """Composes research_quality.quality_report over every ticker
    referenced by this project's attached queries -- no duplicated
    quality logic."""
    _require_project(reg, research_id)
    queries = list_queries(reg, research_id)
    tickers: set[str] = set()
    starts, ends = [], []
    for q in queries:
        for e in q["entities_requested"] or []:
            tickers.add(e)
        if q["date_range_start"]:
            starts.append(q["date_range_start"])
        if q["date_range_end"]:
            ends.append(q["date_range_end"])
    if not tickers or not starts or not ends:
        return {"tickers": sorted(tickers), "note": "no ticker-level queries attached yet -- "
                "quality summary requires at least one prices/compare/cross_section query"}
    return quality_report(con, sorted(tickers), min(starts), max(ends))


# ---------------------------------------------------------------------------
# Integrity guardrails (aggregation of guarantees Phase 2 already
# enforces at query time, plus workspace-level checks)
# ---------------------------------------------------------------------------

def integrity_check(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str) -> list[str]:
    """Aggregates integrity warnings across the whole project. Look-
    ahead is already REJECTED (not just warned) at query execution time
    by research_query.validate_spec -- nothing look-ahead-contaminated
    can ever reach query_log/be attached here. This function surfaces
    what remains: survivorship warnings carried from attached queries,
    evidence recorded without resolvable provenance, and unresolved
    data-quality flags on the tickers actually used."""
    _require_project(reg, research_id)
    warnings: list[str] = []
    for q in list_queries(reg, research_id):
        for w in q["warnings"]:
            warnings.append(f"[query {q['query_id']}] {w}")
    for ev in list_evidence(reg, research_id):
        if ev["evidence_type"] == "dataset_observation" and ev["provenance"] is None:
            warnings.append(f"[evidence {ev['evidence_id']}] provenance UNAVAILABLE for a "
                            f"dataset_observation -- this evidence cannot be traced to a source; "
                            f"disclosed here, not hidden")
    q_summary = project_quality_summary(con, reg, research_id)
    for flag in q_summary.get("quality_flags", []):
        if not flag.get("resolved"):
            warnings.append(f"[data quality] unresolved {flag['check_name']} on {flag['entity_code']} "
                            f"({flag.get('trade_date')})")
    return warnings


# ---------------------------------------------------------------------------
# Reproducible snapshot
# ---------------------------------------------------------------------------

def snapshot(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str) -> str:
    """Freezes the CURRENT state of a project: the project row itself,
    plus every note/evidence/finding/hypothesis/artifact/query
    attachment id and a content hash of each -- not the underlying
    datasets (those are already immutable via Phase-1 dataset_snapshots/
    Phase-2 query_log; this just records WHICH ones were in play)."""
    project = get_project(reg, research_id)
    if project is None:
        raise WorkspaceError(f"no research project with research_id {research_id!r}")
    state = {
        "project": {"research_id": project.research_id, "title": project.title,
                   "research_question": project.research_question, "status": project.status,
                   "scope": project.scope, "dataset_snapshot_ids": project.dataset_snapshot_ids},
        "queries": [{"query_id": q["query_id"], "content_hash": q["content_hash"]}
                   for q in list_queries(reg, research_id)],
        "notes": [n["note_id"] for n in list_notes(reg, research_id)],
        "evidence": [e["evidence_id"] for e in list_evidence(reg, research_id)],
        "findings": [{"finding_id": f["finding_id"], "status": f["status"]}
                    for f in list_findings(reg, research_id)],
        "hypotheses": [{"hypothesis_id": h["hypothesis_id"], "status": h["status"]}
                      for h in list_hypotheses(reg, research_id)],
        "artifacts": [{"artifact_id": a["artifact_id"], "content_hash": a["content_hash"]}
                     for a in list_artifacts(reg, research_id)],
    }
    research_snapshot_id = _new_id("SNAP")
    content_hash = _hash_json(state)
    reg.execute(
        "INSERT INTO research_snapshots (research_snapshot_id, research_id, created_at, "
        "code_fingerprint, git_commit, project_state_json, content_hash) VALUES (?,?,?,?,?,?,?)",
        (research_snapshot_id, research_id, _now(), registry.code_fingerprint(), registry._git_commit(),
         json.dumps(state, default=str), content_hash))
    reg.commit()
    _log_event(reg, research_id, "snapshot_created", f"research_snapshot_id={research_snapshot_id}")
    return research_snapshot_id


def load_snapshot(reg: sqlite3.Connection, research_snapshot_id: str) -> dict:
    row = reg.execute("SELECT research_id, created_at, code_fingerprint, git_commit, project_state_json, "
                      "content_hash FROM research_snapshots WHERE research_snapshot_id = ?",
                      (research_snapshot_id,)).fetchone()
    if row is None:
        raise WorkspaceError(f"no research snapshot with id {research_snapshot_id!r}")
    cols = ["research_id", "created_at", "code_fingerprint", "git_commit", "project_state", "content_hash"]
    d = dict(zip(cols, row))
    d["project_state"] = json.loads(d["project_state"])
    return d


def check_reproducibility(reg: sqlite3.Connection, research_snapshot_id: str) -> dict:
    """Detects DATASET MUTATION (Section 21): re-derives the current
    state of the same project and compares content_hash. A completed
    research snapshot must reference immutable state -- if the CURRENT
    live state's hash no longer matches, something changed since the
    freeze (new evidence/findings/etc were added -- normal if the
    project is still ACTIVE, a red flag if it claims to be COMPLETED)."""
    frozen = load_snapshot(reg, research_snapshot_id)
    research_id = frozen["research_id"]
    project = get_project(reg, research_id)
    current_state = {
        "project": {"research_id": project.research_id, "title": project.title,
                   "research_question": project.research_question, "status": project.status,
                   "scope": project.scope, "dataset_snapshot_ids": project.dataset_snapshot_ids},
        "queries": [{"query_id": q["query_id"], "content_hash": q["content_hash"]}
                   for q in list_queries(reg, research_id)],
        "notes": [n["note_id"] for n in list_notes(reg, research_id)],
        "evidence": [e["evidence_id"] for e in list_evidence(reg, research_id)],
        "findings": [{"finding_id": f["finding_id"], "status": f["status"]}
                    for f in list_findings(reg, research_id)],
        "hypotheses": [{"hypothesis_id": h["hypothesis_id"], "status": h["status"]}
                      for h in list_hypotheses(reg, research_id)],
        "artifacts": [{"artifact_id": a["artifact_id"], "content_hash": a["content_hash"]}
                     for a in list_artifacts(reg, research_id)],
    }
    current_hash = _hash_json(current_state)
    return {"research_snapshot_id": research_snapshot_id, "frozen_content_hash": frozen["content_hash"],
           "current_content_hash": current_hash, "unchanged": current_hash == frozen["content_hash"]}


def timeline(reg: sqlite3.Connection, research_id: str) -> list[dict]:
    rows = reg.execute("SELECT event_type, detail, occurred_at FROM research_timeline "
                       "WHERE research_id = ? ORDER BY occurred_at, event_id", (research_id,)).fetchall()
    return [dict(zip(["event_type", "detail", "occurred_at"], r)) for r in rows]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_json(reg: sqlite3.Connection, research_id: str) -> str:
    p = get_project(reg, research_id)
    if p is None:
        raise WorkspaceError(f"no research project with research_id {research_id!r}")
    payload = {
        "project": {"research_id": p.research_id, "title": p.title,
                   "research_question": p.research_question, "description": p.description,
                   "status": p.status, "created_at": p.created_at, "updated_at": p.updated_at,
                   "owner": p.owner, "tags": p.tags, "scope": p.scope,
                   "dataset_snapshot_ids": p.dataset_snapshot_ids, "code_fingerprint": p.code_fingerprint,
                   "parent_research_id": p.parent_research_id},
        "queries": list_queries(reg, research_id),
        "notes": list_notes(reg, research_id),
        "evidence": list_evidence(reg, research_id),
        "findings": list_findings(reg, research_id),
        "hypotheses": list_hypotheses(reg, research_id),
        "artifacts": list_artifacts(reg, research_id),
        "timeline": timeline(reg, research_id),
    }
    _log_event(reg, research_id, "exported", "format=json")
    return json.dumps(payload, indent=2, default=str, sort_keys=False)


def export_markdown(con: sqlite3.Connection, reg: sqlite3.Connection, research_id: str) -> str:
    """Deterministic Markdown report -- presents the researcher's OWN
    recorded findings/evidence/conclusions verbatim. Generates no
    investment recommendation and calls no LLM; this function is pure
    Python string formatting over already-recorded, real data."""
    p = get_project(reg, research_id)
    if p is None:
        raise WorkspaceError(f"no research project with research_id {research_id!r}")
    lines = [f"# {p.title}", "", f"**research_id**: {p.research_id}  ", f"**status**: {p.status}  ",
            f"**created**: {p.created_at}  **updated**: {p.updated_at}", ""]
    lines += ["## Research Question", "", p.research_question, ""]
    if p.description:
        lines += ["## Description", "", p.description, ""]
    lines += ["## Scope", "", f"```json\n{json.dumps(p.scope, indent=2, default=str)}\n```" if p.scope
             else "_no explicit scope recorded_", ""]
    lines += ["## Dataset", "", f"dataset_snapshot_ids: {p.dataset_snapshot_ids or '_none recorded_'}", ""]

    lines += ["## Queries", ""]
    queries = list_queries(reg, research_id)
    if queries:
        lines.append("| query_id | type | rows | period | sources |")
        lines.append("|---|---|---|---|---|")
        for q in queries:
            lines.append(f"| {q['query_id']} | {q['query_type']} | {q['row_count']} | "
                        f"{q['date_range_start']}..{q['date_range_end']} | {', '.join(q['data_sources'])} |")
    else:
        lines.append("_no queries attached_")
    lines.append("")

    lines += ["## Evidence", ""]
    evidence = list_evidence(reg, research_id)
    if evidence:
        for e in evidence:
            prov = "resolved" if e["provenance"] else "UNAVAILABLE (disclosed, not hidden)"
            lines.append(f"- **[{e['evidence_id']}]** ({e['evidence_type']}, provenance: {prov}): "
                        f"{e['description']}")
    else:
        lines.append("_no evidence recorded_")
    lines.append("")

    lines += ["## Analysis Artifacts", ""]
    artifacts = list_artifacts(reg, research_id)
    if artifacts:
        for a in artifacts:
            lines.append(f"- **[{a['artifact_id']}]** {a['artifact_type']} "
                        f"(content_hash={a['content_hash']}, source_query={a['source_query_id']})")
    else:
        lines.append("_no artifacts recorded_")
    lines.append("")

    lines += ["## Findings", ""]
    findings = list_findings(reg, research_id)
    if findings:
        for f in findings:
            lines.append(f"### [{f['finding_id']}] {f['title']} -- **{f['status']}**")
            lines.append("")
            lines.append(f['statement'])
            if f["supporting_evidence"]:
                lines.append(f"\nSupporting evidence: {', '.join(f['supporting_evidence'])}")
            lines.append("")
    else:
        lines.append("_no findings recorded_")
        lines.append("")

    lines += ["## Hypotheses", ""]
    hyps = list_hypotheses(reg, research_id)
    if hyps:
        for h in hyps:
            lines.append(f"- **[{h['hypothesis_id']}]** ({h['status']}): {h['statement']}")
            if h["supporting_finding_ids"]:
                lines.append(f"  - supporting: {', '.join(h['supporting_finding_ids'])}")
            if h["contradicting_finding_ids"]:
                lines.append(f"  - contradicting: {', '.join(h['contradicting_finding_ids'])}")
    else:
        lines.append("_no hypotheses tracked -- not every research question requires one_")
    lines.append("")

    lines += ["## Limitations / Integrity Warnings", ""]
    warnings = integrity_check(con, reg, research_id)
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("_none recorded_")
    lines.append("")

    lines += ["## Reproducibility", "",
             f"code_fingerprint at project creation: `{p.code_fingerprint}`  ",
             f"current code_fingerprint: `{registry.code_fingerprint()}`", ""]

    lines += ["## Timeline", ""]
    for ev in timeline(reg, research_id):
        lines.append(f"- `{ev['occurred_at']}` **{ev['event_type']}** {ev['detail'] or ''}")

    _log_event(reg, research_id, "exported", "format=markdown")
    return "\n".join(lines)
