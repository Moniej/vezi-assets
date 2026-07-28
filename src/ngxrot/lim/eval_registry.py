"""Immutable evaluation-run registry (owner directive, LIM-3, 2026-07-28):
"Store every evaluation in a versioned registry so results remain
reproducible and comparable across future model versions." Schema:
schema/lim_eval_registry.sql (tracked); the database lives at
lim_training/eval_registry.sqlite (gitignored) -- a FOURTH registry,
deliberately separate from the quant hypothesis ledger, the dataset-version
registry, and the training-run registry. See the schema file's own header
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
SCHEMA_PATH = PKG_ROOT / "schema" / "lim_eval_registry.sql"
DEFAULT_DB_PATH = PKG_ROOT / "lim_training" / "eval_registry.sqlite"

_HARNESS_FILES = ("eval_metrics.py", "eval_dataset.py")


def init_registry(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.commit()
    return con


def eval_harness_hash() -> str:
    """Fingerprint over the scoring logic itself (eval_metrics.py +
    eval_dataset.py), not just the model/dataset being scored -- a change to
    HOW a metric is computed must be as traceable as a change to what's
    being measured, or two eval_runs with different scoring code could be
    silently compared as if they were apples-to-apples."""
    h = hashlib.sha256()
    for name in _HARNESS_FILES:
        h.update((PKG_ROOT / "src" / "ngxrot" / "lim" / name).read_bytes())
    return h.hexdigest()


def record_eval_run(
    con: sqlite3.Connection, *, subject: str, dataset_versions: dict, dataset_content_hashes: dict,
    base_model: str, n_examples_evaluated: int, metrics: dict, training_run_id: str | None = None,
    checkpoint_path: str | None = None, holdout_split: str = "test", git_commit: str | None = None,
    notes: str = "",
) -> str:
    """Writes the ONE immutable summary row for this evaluation. Returns the
    new eval_run_id. Call record_example() for each scored held-out example
    (before or after this call -- eval_examples.eval_run_id is the only
    link, order doesn't matter, but this row is the canonical retrieval
    key)."""
    if subject not in ("local_checkpoint", "teacher_reference"):
        raise ValueError(f"subject must be 'local_checkpoint' or 'teacher_reference', got {subject!r}")
    eval_run_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO eval_runs (eval_run_id, evaluated_at, subject, training_run_id, checkpoint_path, "
        "base_model, dataset_versions, dataset_content_hashes, holdout_split, n_examples_evaluated, "
        "metrics, git_commit, eval_harness_hash, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (eval_run_id, datetime.now(timezone.utc).isoformat(), subject, training_run_id, checkpoint_path,
         base_model, json.dumps(dataset_versions), json.dumps(dataset_content_hashes), holdout_split,
         n_examples_evaluated, json.dumps(metrics, default=str), git_commit, eval_harness_hash(), notes))
    con.commit()
    return eval_run_id


def record_example(
    con: sqlite3.Connection, eval_run_id: str, *, dataset_type: str, unique_id: str, instruction: str,
    expected_output: dict, model_output_raw: str, model_output_parsed: dict | None, scores: dict,
    latency_s: float, input_tokens: int, output_tokens: int,
) -> int:
    cur = con.execute(
        "INSERT INTO eval_examples (eval_run_id, dataset_type, unique_id, instruction, expected_output, "
        "model_output_raw, model_output_parsed, scores, latency_s, input_tokens, output_tokens) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (eval_run_id, dataset_type, unique_id, instruction, json.dumps(expected_output, default=str),
         model_output_raw, json.dumps(model_output_parsed, default=str) if model_output_parsed is not None else None,
         json.dumps(scores, default=str), latency_s, input_tokens, output_tokens))
    con.commit()
    return cur.lastrowid


def get_eval_run(con: sqlite3.Connection, eval_run_id: str) -> dict | None:
    row = con.execute(
        "SELECT eval_run_id, evaluated_at, subject, training_run_id, checkpoint_path, base_model, "
        "dataset_versions, dataset_content_hashes, holdout_split, n_examples_evaluated, metrics, "
        "git_commit, eval_harness_hash, notes FROM eval_runs WHERE eval_run_id = ?",
        (eval_run_id,)).fetchone()
    if row is None:
        return None
    cols = ["eval_run_id", "evaluated_at", "subject", "training_run_id", "checkpoint_path", "base_model",
           "dataset_versions", "dataset_content_hashes", "holdout_split", "n_examples_evaluated",
           "metrics", "git_commit", "eval_harness_hash", "notes"]
    d = dict(zip(cols, row))
    for k in ("dataset_versions", "dataset_content_hashes", "metrics"):
        d[k] = json.loads(d[k])
    d["examples"] = get_examples(con, eval_run_id)
    return d


def get_examples(con: sqlite3.Connection, eval_run_id: str) -> list[dict]:
    rows = con.execute(
        "SELECT example_id, dataset_type, unique_id, instruction, expected_output, model_output_raw, "
        "model_output_parsed, scores, latency_s, input_tokens, output_tokens FROM eval_examples "
        "WHERE eval_run_id = ? ORDER BY example_id", (eval_run_id,)).fetchall()
    out = []
    for (example_id, dataset_type, unique_id, instruction, expected_output, model_output_raw,
         model_output_parsed, scores, latency_s, input_tokens, output_tokens) in rows:
        out.append({
            "example_id": example_id, "dataset_type": dataset_type, "unique_id": unique_id,
            "instruction": instruction, "expected_output": json.loads(expected_output),
            "model_output_raw": model_output_raw,
            "model_output_parsed": json.loads(model_output_parsed) if model_output_parsed else None,
            "scores": json.loads(scores), "latency_s": latency_s,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
        })
    return out


def list_eval_runs(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute("SELECT eval_run_id FROM eval_runs ORDER BY evaluated_at").fetchall()
    return [get_eval_run(con, row[0]) for row in rows]
