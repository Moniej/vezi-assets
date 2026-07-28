"""Immutable dataset-version registry (DATASET_GENERATION_AND_TRAINING_
SPEC.md §5). Schema: schema/lim_dataset_registry.sql (tracked); the actual
database lives at lim_training/dataset_registry.sqlite (gitignored, same
split as schema/registry.sql vs data/registry.sqlite for the quant engine's
hypothesis ledger -- a deliberately SEPARATE registry, never conflated).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PKG_ROOT / "schema" / "lim_dataset_registry.sql"
DEFAULT_DB_PATH = PKG_ROOT / "lim_training" / "dataset_registry.sqlite"


def init_registry(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.commit()
    return con


def content_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def next_version(con: sqlite3.Connection, dataset_type: str) -> str:
    """Auto-increments the MINOR version (v1.N.0) for a dataset_type -- a
    full-rebuild default. Callers cutting an explicit incremental/patch
    version can still pass their own `version` string to register_version
    directly instead of using this helper."""
    rows = con.execute(
        "SELECT version FROM dataset_versions WHERE dataset_type = ?", (dataset_type,)).fetchall()
    minors = []
    for (v,) in rows:
        try:
            minors.append(int(v.rsplit("-v", 1)[1].split(".")[1]))
        except (IndexError, ValueError):
            continue
    next_minor = (max(minors) + 1) if minors else 0
    return f"{dataset_type}-v1.{next_minor}.0"


def register_version(
    con: sqlite3.Connection, *, version: str, dataset_type: str, accepted_path: Path,
    rejected_path: Path, source_as_of: str | None = None, export_script_commit: str | None = None,
    parent_version: str | None = None, n_accepted: int = 0, n_rejected: int = 0,
    rejection_reason_counts: dict | None = None, teacher_model_ids: list | None = None,
    changelog: str = "",
) -> str:
    """Registers a new immutable dataset version. Raises sqlite3.
    IntegrityError if `version` already exists (PRIMARY KEY) -- callers
    must pick a genuinely new version string, never overwrite."""
    con.execute(
        "INSERT INTO dataset_versions (version, dataset_type, content_hash, generated_at, "
        "source_as_of, export_script_commit, parent_version, n_accepted, n_rejected, "
        "rejection_reason_counts, teacher_model_ids, changelog, accepted_path, rejected_path) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (version, dataset_type, content_hash(accepted_path),
         datetime.now(timezone.utc).isoformat(), source_as_of or date.today().isoformat(),
         export_script_commit, parent_version, n_accepted, n_rejected,
         json.dumps(rejection_reason_counts or {}), json.dumps(teacher_model_ids or []),
         changelog, str(accepted_path), str(rejected_path)))
    con.commit()
    return version


def record_lineage(con_lim: sqlite3.Connection, con_ngx, version: str, examples: list) -> None:
    """examples: list of TrainingExample (or dict). source_fact_id is
    derived from the canonical `retrieved_facts` field (first element, when
    present) -- every exporter already has to populate that field, so
    lineage needs no extra hidden convention. source_implication_id is then
    derived via a fast join against the real AI Intelligence Layer database
    (`con_ngx`, read-only) rather than requiring the exporter to duplicate
    that lookup. Bulk-inserted for efficiency."""
    fact_ids = sorted({(ex.to_dict() if hasattr(ex, "to_dict") else ex).get("retrieved_facts", [None])[0]
                      for ex in examples
                      if (ex.to_dict() if hasattr(ex, "to_dict") else ex).get("retrieved_facts")})
    fact_to_impl: dict[int, int] = {}
    if fact_ids:
        placeholders = ",".join("?" * len(fact_ids))
        for fid, iid in con_ngx.execute(
            f"SELECT fact_id, implication_id FROM investment_implications "
            f"WHERE fact_id IN ({placeholders})", fact_ids).fetchall():
            fact_to_impl[fid] = iid

    rows = []
    for ex in examples:
        d = ex.to_dict() if hasattr(ex, "to_dict") else ex
        fact_id = d.get("retrieved_facts", [None])[0] if d.get("retrieved_facts") else None
        rows.append((
            version, d["unique_id"], d["acceptance_status"], fact_id,
            fact_to_impl.get(fact_id), json.dumps(d.get("source_documents", [])),
        ))
    con_lim.executemany(
        "INSERT INTO dataset_example_lineage (version, unique_id, acceptance_status, "
        "source_fact_id, source_implication_id, source_doc_ids) VALUES (?,?,?,?,?,?)", rows)
    con_lim.commit()


def get_version(con: sqlite3.Connection, version: str) -> dict | None:
    row = con.execute(
        "SELECT version, dataset_type, content_hash, generated_at, source_as_of, "
        "export_script_commit, parent_version, n_accepted, n_rejected, "
        "rejection_reason_counts, teacher_model_ids, changelog, accepted_path, rejected_path "
        "FROM dataset_versions WHERE version = ?", (version,)).fetchone()
    if row is None:
        return None
    cols = ["version", "dataset_type", "content_hash", "generated_at", "source_as_of",
           "export_script_commit", "parent_version", "n_accepted", "n_rejected",
           "rejection_reason_counts", "teacher_model_ids", "changelog", "accepted_path",
           "rejected_path"]
    d = dict(zip(cols, row))
    d["rejection_reason_counts"] = json.loads(d["rejection_reason_counts"])
    d["teacher_model_ids"] = json.loads(d["teacher_model_ids"])
    return d


def list_versions(con: sqlite3.Connection, dataset_type: str | None = None) -> list[dict]:
    if dataset_type:
        rows = con.execute(
            "SELECT version FROM dataset_versions WHERE dataset_type = ? ORDER BY generated_at",
            (dataset_type,)).fetchall()
    else:
        rows = con.execute("SELECT version FROM dataset_versions ORDER BY generated_at").fetchall()
    return [get_version(con, v) for (v,) in rows]


def versions_containing(con: sqlite3.Connection, *, fact_id: int | None = None,
                        implication_id: int | None = None) -> list[str]:
    """Reverse lineage lookup: which dataset versions ever included this
    source row, in either partition."""
    if fact_id is not None:
        rows = con.execute(
            "SELECT DISTINCT version FROM dataset_example_lineage WHERE source_fact_id = ?",
            (fact_id,)).fetchall()
    elif implication_id is not None:
        rows = con.execute(
            "SELECT DISTINCT version FROM dataset_example_lineage WHERE source_implication_id = ?",
            (implication_id,)).fetchall()
    else:
        raise ValueError("must supply fact_id or implication_id")
    return [v for (v,) in rows]
