"""Research OS -- generic experiment framework.

Deliberately separate from `registry.record_experiment` (which requires
an alpha-backtest-shaped config: signal/portfolio/costs/liquidity). This
module models the GENERIC research shape the task called for --

    hypothesis -> dataset -> universe -> observation period ->
    transformations -> analysis -> results -> reproducibility metadata

-- for any research question, including purely descriptive ones with no
trading content at all. It is NOT populated with an alpha hypothesis
anywhere in this codebase; the one example run this module's own test
exercises is intentionally descriptive ("what does the data coverage/
quality profile of the IRU look like"), not a signal or a bet.

Writes to the SAME registry.sqlite database `registry.py` already uses
(no new database), into the `research_runs` table added in schema/
registry.sql's 2026-08-10 Research OS section -- immutable, insert-only,
identical discipline to `experiments`.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import registry


@dataclass
class ExperimentSpec:
    """What a researcher intends to run, BEFORE running it. `dataset_
    snapshot_ids` should reference `dataset_snapshots` rows (see
    research_dataset.ResearchDataset.record_snapshot) so the exact data
    used is independently reproducible, not just described."""
    research_question: str
    dataset_snapshot_ids: list[str]
    observation_period_start: str | None = None
    observation_period_end: str | None = None
    universe_version: str | None = None
    transformations: list[str] = field(default_factory=list)
    analysis_method: str | None = None
    hypothesis_id: str | None = None  # optional link into registry.sqlite's hypotheses ledger


@dataclass
class ExperimentResult:
    spec: ExperimentSpec
    results: dict
    notes: str = ""


def record_research_run(reg: sqlite3.Connection, result: ExperimentResult) -> str:
    """Writes one immutable row to research_runs. Returns run_id."""
    spec = result.spec
    run_id = str(uuid.uuid4())
    reg.execute(
        "INSERT INTO research_runs (run_id, created_at, code_fingerprint, git_commit, "
        "hypothesis_id, research_question, dataset_snapshot_ids_json, universe_version, "
        "observation_period_start, observation_period_end, transformations_json, "
        "analysis_method, results_json, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (run_id, datetime.now(timezone.utc).isoformat(timespec="seconds"),
         registry.code_fingerprint(), registry._git_commit(), spec.hypothesis_id,
         spec.research_question, json.dumps(spec.dataset_snapshot_ids), spec.universe_version,
         spec.observation_period_start, spec.observation_period_end,
         json.dumps(spec.transformations), spec.analysis_method,
         json.dumps(result.results, sort_keys=True, default=str), result.notes),
    )
    reg.commit()
    return run_id


def load_research_run(reg: sqlite3.Connection, run_id: str) -> dict | None:
    """Reads one research_runs row back out, JSON fields decoded --
    round-trip counterpart to record_research_run, for a future notebook/
    UI to display past runs."""
    row = reg.execute(
        "SELECT run_id, created_at, code_fingerprint, git_commit, hypothesis_id, "
        "research_question, dataset_snapshot_ids_json, universe_version, "
        "observation_period_start, observation_period_end, transformations_json, "
        "analysis_method, results_json, notes FROM research_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    cols = ["run_id", "created_at", "code_fingerprint", "git_commit", "hypothesis_id",
            "research_question", "dataset_snapshot_ids", "universe_version",
            "observation_period_start", "observation_period_end", "transformations",
            "analysis_method", "results", "notes"]
    out = dict(zip(cols, row))
    out["dataset_snapshot_ids"] = json.loads(out["dataset_snapshot_ids"])
    out["transformations"] = json.loads(out["transformations"])
    out["results"] = json.loads(out["results"])
    return out
