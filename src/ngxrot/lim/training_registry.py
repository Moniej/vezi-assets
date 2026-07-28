"""Immutable training-run experiment registry (owner directive, LIM-2,
2026-07-28). Schema: schema/lim_training_registry.sql (tracked); the
database lives at lim_training/training_registry.sqlite (gitignored) --
a THIRD registry, deliberately separate from both the quant hypothesis
ledger (data/registry.sqlite) and the LIM dataset-version registry
(lim_training/dataset_registry.sqlite). See the schema file's own header
for the full rationale.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PKG_ROOT / "schema" / "lim_training_registry.sql"
DEFAULT_DB_PATH = PKG_ROOT / "lim_training" / "training_registry.sqlite"
LOCK_FILE_PATH = PKG_ROOT / "lim_training" / "requirements.lock.txt"


def init_registry(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.commit()
    return con


def lock_file_hash() -> str | None:
    """Fingerprint of the reference training environment (owner: "treat the
    current environment as reference; do not upgrade unless a verified
    blocker requires it") -- recorded per run so environment drift is
    detectable after the fact, not just assumed away."""
    if not LOCK_FILE_PATH.exists():
        return None
    return hashlib.sha256(LOCK_FILE_PATH.read_bytes()).hexdigest()


def start_run(
    con: sqlite3.Connection, *, dataset_versions: list[str], dataset_content_hashes: dict,
    teacher_model_ids: list[str], base_model: str, quantization_config: dict, lora_config: dict,
    hyperparameters: dict, seed: int, base_model_revision: str | None = None,
    git_commit: str | None = None, notes: str = "",
) -> str:
    """Writes the ONE immutable row for this run, before any training step
    executes -- a crash immediately after this call still leaves an honest
    record of exactly what was attempted. Returns the new run_id."""
    run_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO training_runs (run_id, started_at, dataset_versions, "
        "dataset_content_hashes, teacher_model_ids, base_model, base_model_revision, "
        "quantization_config, lora_config, hyperparameters, seed, git_commit, "
        "lim_venv_lock_hash, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (run_id, datetime.now(timezone.utc).isoformat(), json.dumps(dataset_versions),
         json.dumps(dataset_content_hashes), json.dumps(teacher_model_ids), base_model,
         base_model_revision, json.dumps(quantization_config), json.dumps(lora_config),
         json.dumps(hyperparameters), seed, git_commit, lock_file_hash(), notes))
    con.commit()
    log_event(con, run_id, event_type="started", step=0)
    return run_id


def log_event(con: sqlite3.Connection, run_id: str, *, event_type: str, step: int | None = None,
             metrics: dict | None = None, checkpoint_path: str | None = None) -> int:
    cur = con.execute(
        "INSERT INTO training_run_events (run_id, event_type, occurred_at, step, metrics, "
        "checkpoint_path) VALUES (?,?,?,?,?,?)",
        (run_id, event_type, datetime.now(timezone.utc).isoformat(), step,
         json.dumps(metrics) if metrics is not None else None, checkpoint_path))
    con.commit()
    return cur.lastrowid


def get_run(con: sqlite3.Connection, run_id: str) -> dict | None:
    row = con.execute(
        "SELECT run_id, started_at, dataset_versions, dataset_content_hashes, "
        "teacher_model_ids, base_model, base_model_revision, quantization_config, "
        "lora_config, hyperparameters, seed, git_commit, lim_venv_lock_hash, notes "
        "FROM training_runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    cols = ["run_id", "started_at", "dataset_versions", "dataset_content_hashes",
           "teacher_model_ids", "base_model", "base_model_revision", "quantization_config",
           "lora_config", "hyperparameters", "seed", "git_commit", "lim_venv_lock_hash", "notes"]
    d = dict(zip(cols, row))
    for k in ("dataset_versions", "dataset_content_hashes", "teacher_model_ids",
             "quantization_config", "lora_config", "hyperparameters"):
        d[k] = json.loads(d[k])
    d["events"] = get_events(con, run_id)
    return d


def get_events(con: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = con.execute(
        "SELECT event_id, event_type, occurred_at, step, metrics, checkpoint_path "
        "FROM training_run_events WHERE run_id = ? ORDER BY event_id", (run_id,)).fetchall()
    out = []
    for event_id, event_type, occurred_at, step, metrics, checkpoint_path in rows:
        out.append({"event_id": event_id, "event_type": event_type, "occurred_at": occurred_at,
                   "step": step, "metrics": json.loads(metrics) if metrics else None,
                   "checkpoint_path": checkpoint_path})
    return out


def run_for_checkpoint(con: sqlite3.Connection, checkpoint_path: str) -> dict | None:
    """The core traceability query: given a checkpoint directory, find the
    exact training run (and, from it, the dataset versions/teacher models/
    git commit/seed) that produced it."""
    row = con.execute(
        "SELECT run_id FROM training_run_events WHERE checkpoint_path = ? "
        "AND event_type = 'checkpoint' LIMIT 1", (checkpoint_path,)).fetchone()
    if row is None:
        return None
    return get_run(con, row[0])


def list_runs(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute("SELECT run_id FROM training_runs ORDER BY started_at").fetchall()
    return [get_run(con, row[0]) for row in rows]
