"""Create a self-consistent, read-only SQLite baseline snapshot.

This is intentionally a one-way Stage 0 utility: it never opens the source
database for writing. SQLite's backup API includes committed WAL state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        schema_sql = "\n".join(row[0] or "" for row in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"))
        return {
            "integrity_check": [row[0] for row in con.execute("PRAGMA integrity_check")],
            "foreign_key_check": [list(row) for row in con.execute("PRAGMA foreign_key_check")],
            "schema_version": con.execute("PRAGMA schema_version").fetchone()[0],
            "user_version": con.execute("PRAGMA user_version").fetchone()[0],
            "schema_sql_sha256": hashlib.sha256(schema_sql.encode()).hexdigest(),
            "table_row_counts": {table: con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in tables},
        }
    finally:
        con.close()


def snapshot(source: Path, destination_dir: Path, commit: str) -> dict:
    destination_dir.mkdir(parents=True, exist_ok=True)
    output = destination_dir / source.name
    source_con = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    target_con = sqlite3.connect(output)
    try:
        source_con.backup(target_con)
    finally:
        target_con.close()
        source_con.close()
    verification_dir = destination_dir / "restore-verification"
    verification_dir.mkdir(exist_ok=True)
    restored = verification_dir / source.name
    shutil.copy2(output, restored)
    original_inspection = inspect(output)
    restored_inspection = inspect(restored)
    if original_inspection != restored_inspection:
        raise RuntimeError("restored snapshot inspection differs from source snapshot")
    result = {
        "source_path": str(source.resolve()),
        "snapshot_path": str(output.resolve()),
        "snapshot_sha256": sha256(output),
        "byte_size": output.stat().st_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_repository_commit": commit,
        "backup_method": "sqlite3.Connection.backup from URI mode=ro source",
        "restore_verification_path": str(restored.resolve()),
        "restore_verification_sha256": sha256(restored),
        **original_inspection,
    }
    manifest_path = destination_dir / f"{source.stem}.manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(output, 0o444)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit(f"source is not a file: {args.source}")
    print(json.dumps(snapshot(args.source, args.destination, args.commit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
