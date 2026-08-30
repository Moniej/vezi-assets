"""Forward-only migration runner, intentionally not connected to current db.init_db()."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone


class MigrationError(RuntimeError):
    pass


class SchemaAssertionError(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    migration_id: str
    database_target: str
    expected_pre_version: int
    expected_post_version: int
    sql: str
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checksum", hashlib.sha256(self.sql.encode("utf-8")).hexdigest())
        parts = self.migration_id.split("_", 3)
        if len(parts) != 4 or not parts[0].isdigit() or len(parts[0]) != 8 or not parts[1].isdigit() or len(parts[1]) != 3:
            raise ValueError("migration ID must be YYYYMMDD_NNN_domain_slug")
        if self.expected_post_version <= self.expected_pre_version:
            raise ValueError("migration version must advance")


class MigrationRunner:
    def __init__(self, migrations: list[Migration]) -> None:
        self.migrations = sorted(migrations, key=lambda migration: migration.migration_id)

    @staticmethod
    def _ensure_ledger(con: sqlite3.Connection) -> None:
        con.execute("""CREATE TABLE IF NOT EXISTS schema_migration_ledger (
            migration_id TEXT PRIMARY KEY, database_target TEXT NOT NULL,
            checksum TEXT NOT NULL, pre_version INTEGER NOT NULL,
            post_version INTEGER NOT NULL, applied_at TEXT NOT NULL,
            backup_manifest_sha256 TEXT
        )""")

    def current_version(self, con: sqlite3.Connection, database_target: str) -> int:
        self._ensure_ledger(con)
        row = con.execute("SELECT COALESCE(MAX(post_version), 0) FROM schema_migration_ledger WHERE database_target = ?", (database_target,)).fetchone()
        return int(row[0])

    def apply_pending(self, con: sqlite3.Connection, *, database_target: str,
                      backup_manifest_verified: bool, backup_manifest_sha256: str | None = None) -> None:
        if not backup_manifest_verified:
            raise MigrationError("a verified pre-migration backup manifest is required")
        self._ensure_ledger(con)
        for migration in (m for m in self.migrations if m.database_target == database_target):
            applied = con.execute("SELECT checksum FROM schema_migration_ledger WHERE migration_id = ?", (migration.migration_id,)).fetchone()
            if applied:
                if applied[0] != migration.checksum:
                    raise MigrationError(f"checksum mismatch for applied migration {migration.migration_id}")
                continue
            current = self.current_version(con, database_target)
            if current != migration.expected_pre_version:
                raise SchemaAssertionError(f"{migration.migration_id} expects version {migration.expected_pre_version}, found {current}")
            try:
                with con:
                    con.executescript(migration.sql)
                    con.execute("INSERT INTO schema_migration_ledger VALUES (?,?,?,?,?,?,?)", (
                        migration.migration_id, database_target, migration.checksum,
                        migration.expected_pre_version, migration.expected_post_version,
                        datetime.now(timezone.utc).isoformat(), backup_manifest_sha256,
                    ))
            except sqlite3.Error as exc:
                raise MigrationError(f"migration {migration.migration_id} failed; database left at prior transaction boundary") from exc

    def assert_schema(self, con: sqlite3.Connection, *, database_target: str, expected_version: int) -> None:
        actual = self.current_version(con, database_target)
        if actual != expected_version:
            raise SchemaAssertionError(f"{database_target} schema version {actual}; expected {expected_version}")
