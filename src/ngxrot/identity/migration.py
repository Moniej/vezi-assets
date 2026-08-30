"""Stage 2A schema/backfill runner; it never rewrites legacy securities."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import uuid7
from ngxrot.migrations.catalog import baseline_migrations
from ngxrot.migrations.framework import Migration, MigrationRunner


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_ID = "20260830_001_canonical_identity_foundation"
SQL_PATH = ROOT / "migrations" / "20260830_001_canonical_identity_foundation.sql"


def identity_migration() -> Migration:
    return Migration(MIGRATION_ID, "ngx", 1, 2, SQL_PATH.read_text(encoding="utf-8"))


def apply_identity_foundation(con: sqlite3.Connection, *, backup_manifest_sha256: str) -> dict[str, int]:
    """Apply baseline+Stage 2A once, then conservatively map every legacy security."""
    runner = MigrationRunner([*baseline_migrations(), identity_migration()])
    runner.apply_pending(con, database_target="ngx", backup_manifest_verified=True,
                         backup_manifest_sha256=backup_manifest_sha256)
    if runner.current_version(con, "ngx") == 2:
        _backfill_security_instruments(con)
    return identity_counts(con)


def _backfill_security_instruments(con: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = con.execute("SELECT ticker, listing_date, delisting_date FROM securities WHERE ticker IS NOT NULL ORDER BY ticker").fetchall()
    with con:
        for ticker, listing_date, delisting_date in rows:
            existing = con.execute("SELECT canonical_subject_id FROM legacy_identity_mappings WHERE legacy_namespace='ngx.securities.ticker' AND legacy_value=? AND canonical_subject_type='instrument' AND mapping_status='active'", (ticker,)).fetchone()
            if existing:
                continue
            instrument_id = str(uuid7())
            listing_status = "delisted" if delisting_date else "unknown"
            con.execute("INSERT INTO instrument_listings(instrument_id,company_id,exchange_code,instrument_type,listing_status,listing_date,delisting_date,recorded_at) VALUES (?,?,?,?,?,?,?,?)", (instrument_id, None, "NGX", "equity", listing_status, listing_date, delisting_date, now))
            alias_id = str(uuid7())
            con.execute("INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,valid_from,valid_to,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (alias_id, "instrument", instrument_id, "ticker", ticker, "NGX", None, None, "verified", now))
            con.execute("INSERT INTO legacy_identity_mappings(mapping_id,legacy_namespace,legacy_value,canonical_subject_type,canonical_subject_id,mapping_status,evidence_reference,recorded_at) VALUES (?,?,?,?,?,?,?,?)", (str(uuid7()), "ngx.securities.ticker", ticker, "instrument", instrument_id, "active", f"legacy:securities:{ticker}", now))


def identity_counts(con: sqlite3.Connection) -> dict[str, int]:
    tables = ("company_issuers", "instrument_listings", "identifier_aliases", "legacy_identity_mappings")
    result = {name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in tables}
    result["null_company_mappings"] = con.execute("SELECT COUNT(*) FROM instrument_listings WHERE company_id IS NULL").fetchone()[0]
    result["temporal_bounds_known"] = con.execute("SELECT COUNT(*) FROM identifier_aliases WHERE valid_from IS NOT NULL OR valid_to IS NOT NULL").fetchone()[0]
    return result
