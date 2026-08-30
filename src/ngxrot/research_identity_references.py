"""Stage 2C application-side integrity for Research OS identity references.

``registry.sqlite`` intentionally stores an immutable *reference* to the
canonical OS; it never becomes an identity authority and SQLite cannot make a
foreign key across those two databases.  This module is consequently small,
readable, and deliberately free of repair/backfill behaviour.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .canonical.contracts import TemporalQueryContext
from .migrations.catalog import baseline_migrations
from .migrations.framework import Migration, MigrationRunner


MIGRATION_ID = "20260830_001_research_canonical_identity_reference"
RESOLVER_VERSION = "research-os-canonical-resolver-v1"


class CanonicalReferenceStatus(str, Enum):
    VALIDATED = "validated"
    UNRESOLVED = "unresolved"
    STALE = "stale"
    MISSING_TARGET = "missing_target"
    NOT_APPLICABLE = "not_applicable"


class CanonicalReferenceValidationStatus(str, Enum):
    VALID = "valid"
    MISSING_TARGET = "missing_target"
    INVALID_FORMAT = "invalid_format"
    TEMPORALLY_INCONSISTENT = "temporally_inconsistent"
    OS_UNAVAILABLE = "os_unavailable"


@dataclass(frozen=True)
class CanonicalReferenceValidation:
    status: CanonicalReferenceValidationStatus
    instrument_id: str | None
    reason: str


@dataclass(frozen=True)
class CanonicalIdentityRequest:
    """Explicit opt-in for one new immutable query-log record only."""
    identifier: str
    exchange: str | None = None
    identifier_type: str = "ticker"
    temporal_context: TemporalQueryContext | None = None
    allow_legacy_fallback: bool = True


@dataclass(frozen=True)
class CanonicalQueryReference:
    instrument_id: str | None
    resolution_status: str
    exchange: str | None
    decision_time: str | None
    system_vintage: str | None
    availability_policy: str | None
    resolver_version: str
    reference_status: CanonicalReferenceStatus
    resolution_reason: str | None


@dataclass(frozen=True)
class CanonicalReferenceReconciliation:
    total: int
    valid: int
    missing_target: int
    invalid: int
    unresolved: int
    os_unavailable: int


def registry_identity_reference_migration() -> Migration:
    sql = (Path(__file__).resolve().parents[2] / "migrations" / f"{MIGRATION_ID}.sql").read_text(encoding="utf-8")
    return Migration(MIGRATION_ID, "registry", 1, 2, sql)


def apply_registry_identity_reference_migration(
    con: sqlite3.Connection, *, backup_manifest_sha256: str,
) -> None:
    """Apply the additive registry-only migration through the common ledger."""
    MigrationRunner([*baseline_migrations(), registry_identity_reference_migration()]).apply_pending(
        con, database_target="registry", backup_manifest_verified=True,
        backup_manifest_sha256=backup_manifest_sha256,
    )


def validate_canonical_instrument_reference(
    os_connection: sqlite3.Connection, canonical_instrument_id: str | None,
    *, exchange: str | None = None,
) -> CanonicalReferenceValidation:
    """Validate a reference without conflating OS failure with a missing row."""
    if not canonical_instrument_id:
        return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.INVALID_FORMAT, None, "canonical instrument id is required")
    try:
        parsed = uuid.UUID(canonical_instrument_id)
    except (ValueError, AttributeError, TypeError):
        return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.INVALID_FORMAT, canonical_instrument_id, "not a UUID")
    if parsed.version != 7:
        return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.INVALID_FORMAT, canonical_instrument_id, "canonical instrument id must be UUIDv7")
    try:
        row = os_connection.execute(
            "SELECT exchange_code FROM instrument_listings WHERE instrument_id=?", (canonical_instrument_id,)
        ).fetchone()
    except (sqlite3.Error, ValueError) as exc:
        return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.OS_UNAVAILABLE, canonical_instrument_id, f"OS unavailable: {exc}")
    if row is None:
        return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.MISSING_TARGET, canonical_instrument_id, "instrument listing does not exist")
    if exchange is not None and row[0] != exchange:
        return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.TEMPORALLY_INCONSISTENT, canonical_instrument_id, "requested exchange differs from canonical listing")
    return CanonicalReferenceValidation(CanonicalReferenceValidationStatus.VALID, canonical_instrument_id, "canonical instrument exists")


def canonical_reference_from_lookup(os_connection: sqlite3.Connection, lookup: Any) -> CanonicalQueryReference:
    """Convert a Stage 2B lookup into insert-only query-log metadata.

    Only a canonical ``resolved`` result with no legacy fallback may carry an
    ID.  All other outcomes retain their audit status but persist NULL.
    """
    context = {
        "decision_time": _temporal_value(getattr(lookup, "decision_time", None)),
        "system_vintage": _temporal_value(getattr(lookup, "system_vintage", None)),
        "availability_policy": getattr(lookup, "availability_policy", None),
    }
    status = getattr(lookup, "status").value
    if status == "resolved" and not getattr(lookup, "fallback_used", False) and getattr(lookup, "instrument_id", None):
        validation = validate_canonical_instrument_reference(
            os_connection, lookup.instrument_id, exchange=getattr(lookup, "exchange", None)
        )
        if validation.status is CanonicalReferenceValidationStatus.VALID:
            return CanonicalQueryReference(lookup.instrument_id, status, lookup.exchange, **context,
                                           resolver_version=RESOLVER_VERSION,
                                           reference_status=CanonicalReferenceStatus.VALIDATED,
                                           resolution_reason=getattr(lookup, "resolution_reason", None))
        return CanonicalQueryReference(None, status, lookup.exchange, **context,
                                       resolver_version=RESOLVER_VERSION,
                                       reference_status=CanonicalReferenceStatus.UNRESOLVED,
                                       resolution_reason=validation.reason)
    return CanonicalQueryReference(None, status, getattr(lookup, "exchange", None), **context,
                                   resolver_version=RESOLVER_VERSION,
                                   reference_status=CanonicalReferenceStatus.UNRESOLVED,
                                   resolution_reason=getattr(lookup, "resolution_reason", None))


def not_requested_reference() -> CanonicalQueryReference:
    return CanonicalQueryReference(None, "not_requested", None, None, None, None,
                                   RESOLVER_VERSION, CanonicalReferenceStatus.NOT_APPLICABLE, None)


def reconcile_canonical_instrument_references(
    registry_connection: sqlite3.Connection, os_connection: sqlite3.Connection,
) -> CanonicalReferenceReconciliation:
    """Read-only cross-database integrity report; it never repairs rows."""
    rows = registry_connection.execute(
        "SELECT canonical_instrument_id, canonical_exchange, canonical_reference_status "
        "FROM query_log"
    ).fetchall()
    total = valid = missing = invalid = unresolved = unavailable = 0
    for instrument_id, exchange, recorded_status in rows:
        if instrument_id is None:
            if recorded_status == CanonicalReferenceStatus.UNRESOLVED.value:
                unresolved += 1
            continue
        total += 1
        result = validate_canonical_instrument_reference(os_connection, instrument_id, exchange=exchange)
        if result.status is CanonicalReferenceValidationStatus.VALID:
            valid += 1
        elif result.status is CanonicalReferenceValidationStatus.MISSING_TARGET:
            missing += 1
        elif result.status is CanonicalReferenceValidationStatus.OS_UNAVAILABLE:
            unavailable += 1
        else:
            invalid += 1
    return CanonicalReferenceReconciliation(total, valid, missing, invalid, unresolved, unavailable)


def _temporal_value(value: object | None) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
