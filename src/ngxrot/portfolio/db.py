"""Connection/init for data/portfolio.sqlite -- the Investment Management
Layer's own database, isolated from data/ngx.sqlite and data/registry.sqlite.
Mirrors ngxrot.db.connect()/registry.connect_registry()'s own pattern
exactly (WAL + busy_timeout from day one, matching the 2026-08-12
production-reliability fix applied to both of those -- no reason for a
brand-new database to start without it)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = PKG_ROOT / "schema"
DEFAULT_DB = PKG_ROOT / "data" / "portfolio.sqlite"


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=30.0)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 30000")
    return con


def init_db(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    con = connect(db_path)
    con.executescript((SCHEMA_DIR / "portfolio.sql").read_text(encoding="utf-8"))
    con.commit()
    return con


def new_scratch_db_path() -> Path:
    """Same sanctioned pattern as ngxrot.db.new_scratch_db_path() -- a
    throwaway path for tests, never colliding with DEFAULT_DB."""
    import tempfile
    return Path(tempfile.mkdtemp()) / "scratch_portfolio.sqlite"
