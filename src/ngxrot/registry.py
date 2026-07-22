"""Experiment registry: immutable record of every run.

Each completed run inserts exactly one row into data/registry.sqlite (SQL
triggers forbid UPDATE/DELETE) and writes a JSON snapshot to
experiments/<id>.json. The record is inserted only when the run completes,
fully formed — there is no mutable 'running' state to tempt edits.

code_fingerprint: SHA256 over every .py/.sql/.toml under src/, schema/ and
configs/. This project is not a git repo; the fingerprint is the substitute
for a commit hash (git_commit column is populated automatically if a repo
appears later).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DB = PKG_ROOT / "data" / "registry.sqlite"
EXPERIMENTS_DIR = PKG_ROOT / "experiments"
_FINGERPRINT_DIRS = ("src", "schema", "configs")


def connect_registry(db_path: str | Path = REGISTRY_DB) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    # additive migrations FIRST (ALTER is allowed on the immutable tables; row
    # UPDATE/DELETE remain trigger-blocked). Must precede executescript so
    # triggers referencing new columns can be created on migrated DBs.
    for table, col, decl in [
            ("experiments", "rng_algorithm", "TEXT"),
            ("experiments", "rng_seed", "INTEGER"),
            ("experiments", "rng_iterations", "INTEGER"),
            ("hypotheses", "frozen", "INTEGER NOT NULL DEFAULT 0")]:
        try:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # column already exists, or table not created yet (fresh DB)
    con.executescript((PKG_ROOT / "schema" / "registry.sql").read_text(encoding="utf-8"))
    con.commit()
    return con


def code_fingerprint() -> str:
    h = hashlib.sha256()
    for d in _FINGERPRINT_DIRS:
        base = PKG_ROOT / d
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if f.suffix in {".py", ".sql", ".toml"} and f.is_file():
                h.update(str(f.relative_to(PKG_ROOT)).encode())
                h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG_ROOT,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except OSError:
        return None


def record_experiment(
    reg: sqlite3.Connection,
    *,
    config: dict,
    config_path: str | None,
    metrics: dict,
    validation_flags: dict,
    notes: str = "",
) -> str:
    """Insert one immutable experiment row + JSON snapshot. Returns the ID."""
    exp_id = str(uuid.uuid4())
    cfg_json = json.dumps(config, sort_keys=True)
    row = dict(
        experiment_id=exp_id,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        code_fingerprint=code_fingerprint(),
        git_commit=_git_commit(),
        config_path=config_path,
        config_hash=hashlib.sha256(cfg_json.encode()).hexdigest()[:16],
        config_json=cfg_json,
        hypothesis_id=config["experiment"].get("hypothesis_id"),
        stage=config["experiment"]["stage"],
        provider=",".join(config["data"]["sources"]),
        min_confidence=config["data"]["min_confidence"],
        vintage=config["data"].get("vintage") or None,
        sim_start=config["data"]["sim_start"],
        sim_end=config["data"]["sim_end"],
        # sector-era column; cross-sectional signals have no
        # lookbacks_months — store their parameter dict instead (full
        # config is in config_json either way)
        lookbacks_months=json.dumps(config["signal"].get(
            "lookbacks_months",
            {k: v for k, v in config["signal"].items() if k != "method"})),
        top_n=config["portfolio"]["top_n"],
        rebalance=config["portfolio"]["rebalance"],
        construction=config["portfolio"]["construction"],
        cost_assumptions=json.dumps(config["costs"], sort_keys=True),
        liquidity_constraints=json.dumps(config.get("liquidity", {}), sort_keys=True),
        seed=config["experiment"].get("seed"),
        rng_algorithm=config.get("rng", {}).get("algorithm", "PCG64"),
        rng_seed=config.get("rng", {}).get("seed"),
        rng_iterations=config.get("rng", {}).get("iterations", 0),
        metrics=json.dumps(metrics, sort_keys=True),
        validation_flags=json.dumps(validation_flags, sort_keys=True),
        notes=notes,
    )
    cols = ",".join(row)
    reg.execute(f"INSERT INTO experiments ({cols}) VALUES ({','.join(':' + c for c in row)})", row)
    if row["hypothesis_id"]:
        reg.execute(
            "INSERT OR IGNORE INTO hypothesis_experiments (hypothesis_id, experiment_id) "
            "VALUES (?,?)", (row["hypothesis_id"], exp_id))
    reg.commit()

    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    snap = {k: (json.loads(v) if k in {"config_json", "lookbacks_months", "cost_assumptions",
                                       "liquidity_constraints", "metrics", "validation_flags"}
                and v else v)
            for k, v in row.items()}
    (EXPERIMENTS_DIR / f"{exp_id}.json").write_text(
        json.dumps(snap, indent=2, sort_keys=True), encoding="utf-8")
    return exp_id
