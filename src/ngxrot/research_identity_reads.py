"""Stage 2D read-only canonical-preferred metadata identity inspection.

This is intentionally a narrow companion to the legacy query layer: it never
writes ``query_log`` and it does not alter default Research OS query behaviour.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum

from .canonical.contracts import TemporalQueryContext
from .research_identity_references import (
    CanonicalReferenceValidationStatus,
    validate_canonical_instrument_reference,
)
from .research_query import ResearchIdentityStatus, lookup_identity


class IdentityReadMode(str, Enum):
    LEGACY = "legacy"
    CANONICAL = "canonical"
    CANONICAL_PREFERRED = "canonical_preferred"


@dataclass(frozen=True)
class ResearchReadIdentity:
    mode_requested: IdentityReadMode
    effective_identity_kind: str  # canonical | legacy | none
    canonical_instrument_id: str | None
    canonical_company_id: str | None
    canonical_reference_status: str
    canonical_resolution_status: str
    canonical_exchange: str | None
    canonical_alias_id: str | None
    issuer_status: str
    legacy_identifier: str
    legacy_exchange: str | None
    fallback_used: bool
    pit_safe: bool
    persisted_reference_present: bool
    fresh_resolver_used: bool
    mismatch_detected: bool
    reason: str | None


@dataclass(frozen=True)
class MetadataIdentityInspection:
    metadata: dict | None
    identity: ResearchReadIdentity


def inspect_metadata_identity(
    os_connection: sqlite3.Connection, *, identifier: str, exchange: str | None = None,
    identity_mode: IdentityReadMode | str = IdentityReadMode.LEGACY,
    temporal_context: TemporalQueryContext | None = None,
    allow_legacy_fallback: bool = True,
    registry_connection: sqlite3.Connection | None = None,
    query_id: str | None = None,
) -> MetadataIdentityInspection:
    """Inspect one security's metadata with an explicit identity policy.

    A persisted Stage 2C reference wins when valid.  It is never re-resolved
    or repaired here; a broken reference stays observable.  Calls without a
    persisted reference use the Stage 2B resolver only in canonical modes.
    """
    mode = IdentityReadMode(identity_mode)
    persisted = _persisted_reference(registry_connection, query_id) if query_id else None
    if persisted is not None:
        identity = _from_persisted(os_connection, identifier, exchange, mode, persisted,
                                   allow_legacy_fallback)
    elif mode is IdentityReadMode.LEGACY:
        identity = _legacy_identity(identifier, exchange, "legacy mode requested")
    else:
        identity = _from_fresh_resolution(os_connection, identifier, exchange, mode,
                                          temporal_context, allow_legacy_fallback)
    return MetadataIdentityInspection(_legacy_metadata(os_connection, identity.legacy_identifier), identity)


def _persisted_reference(reg: sqlite3.Connection | None, query_id: str | None) -> dict[str, object] | None:
    if reg is None or query_id is None:
        return None
    try:
        cursor = reg.execute(
            "SELECT entities_requested_json, canonical_instrument_id, canonical_resolution_status, "
            "canonical_reference_status, canonical_exchange, canonical_resolution_decision_time, "
            "canonical_resolution_system_vintage, canonical_availability_policy "
            "FROM query_log WHERE query_id=?", (query_id,)
        )
        row = cursor.fetchone()
        return dict(zip((column[0] for column in cursor.description), row)) if row else None
    except sqlite3.Error as exc:
        raise ValueError("registry does not support Stage 2C canonical references") from exc


def _from_persisted(os_con: sqlite3.Connection, identifier: str, exchange: str | None,
                    mode: IdentityReadMode, row: dict[str, object], allow_fallback: bool) -> ResearchReadIdentity:
    persisted_id = row["canonical_instrument_id"]
    stored_resolution = row["canonical_resolution_status"]
    stored_reference = row["canonical_reference_status"]
    stored_exchange = row["canonical_exchange"] or exchange
    if persisted_id:
        validation = validate_canonical_instrument_reference(os_con, persisted_id, exchange=stored_exchange)
        if validation.status is CanonicalReferenceValidationStatus.VALID:
            company = os_con.execute("SELECT company_id FROM instrument_listings WHERE instrument_id=?", (persisted_id,)).fetchone()[0]
            mapped_identifier = _legacy_identifier_for_instrument(os_con, persisted_id) or identifier
            mismatch = mapped_identifier != identifier
            return ResearchReadIdentity(mode, "canonical", persisted_id, company, "validated",
                                        stored_resolution, stored_exchange, None,
                                        "resolved" if company else "unresolved", mapped_identifier,
                                        exchange, False, True, True, False, mismatch,
                                        "persisted canonical reference preferred")
        return _broken_persisted_identity(identifier, exchange, mode, persisted_id, stored_resolution,
                                          validation.status.value, allow_fallback)
    # Stage 2C can persist a non-resolved outcome with NULL ID.  It is a
    # historical fact, not an invitation to re-resolve it under today's rules.
    return _legacy_or_none(identifier, exchange, mode, stored_resolution, stored_reference,
                           allow_fallback and mode is IdentityReadMode.CANONICAL_PREFERRED,
                           persisted=True, reason="persisted canonical reference unavailable")


def _from_fresh_resolution(os_con: sqlite3.Connection, identifier: str, exchange: str | None,
                           mode: IdentityReadMode, temporal_context: TemporalQueryContext | None,
                           allow_fallback: bool) -> ResearchReadIdentity:
    lookup = lookup_identity(os_con, identifier, exchange=exchange, temporal_context=temporal_context,
                             allow_legacy_fallback=allow_fallback if mode is IdentityReadMode.CANONICAL_PREFERRED else False)
    if lookup.status is ResearchIdentityStatus.RESOLVED:
        return ResearchReadIdentity(mode, "canonical", lookup.instrument_id, lookup.company_id, "not_applicable",
                                    lookup.status.value, exchange, lookup.matched_alias_id, lookup.issuer_status,
                                    identifier, exchange, False, True, False, True, False, lookup.resolution_reason)
    if mode is IdentityReadMode.CANONICAL:
        return ResearchReadIdentity(mode, "none", None, None, "not_applicable", lookup.status.value,
                                    exchange, None, "unresolved", identifier, exchange, False, False,
                                    False, True, False, lookup.resolution_reason)
    if lookup.status is ResearchIdentityStatus.LEGACY_FALLBACK:
        return ResearchReadIdentity(mode, "legacy", None, None, "unresolved", lookup.canonical_status,
                                    exchange, None, "unresolved", lookup.legacy_ticker or identifier, exchange,
                                    True, lookup.pit_safe_canonical_resolution, False, True, False,
                                    lookup.resolution_reason)
    if lookup.status is ResearchIdentityStatus.AMBIGUOUS:
        return ResearchReadIdentity(mode, "none", None, None, "unresolved", lookup.status.value,
                                    exchange, None, "unresolved", identifier, exchange, False, False,
                                    False, True, False, lookup.resolution_reason)
    return _legacy_or_none(identifier, exchange, mode, lookup.status.value, "unresolved", allow_fallback,
                           persisted=False, reason=lookup.resolution_reason, fresh=True)


def _broken_persisted_identity(identifier: str, exchange: str | None, mode: IdentityReadMode,
                               instrument_id: str, resolution_status: str, validation_status: str,
                               allow_fallback: bool) -> ResearchReadIdentity:
    if mode is IdentityReadMode.CANONICAL or not allow_fallback:
        return ResearchReadIdentity(mode, "none", instrument_id, None, validation_status, resolution_status,
                                    exchange, None, "unresolved", identifier, exchange, False, False,
                                    True, False, True, "persisted canonical reference failed validation")
    return ResearchReadIdentity(mode, "legacy", instrument_id, None, validation_status, resolution_status,
                                exchange, None, "unresolved", identifier, exchange, True, False,
                                True, False, True, "persisted canonical reference failed validation; legacy compatibility shown")


def _legacy_or_none(identifier: str, exchange: str | None, mode: IdentityReadMode, resolution: str,
                    reference: str, allow_fallback: bool, *, persisted: bool, reason: str, fresh: bool = False) -> ResearchReadIdentity:
    if allow_fallback:
        return ResearchReadIdentity(mode, "legacy", None, None, reference, resolution, exchange, None,
                                    "unresolved", identifier, exchange, True, False, persisted, fresh,
                                    False, reason)
    return ResearchReadIdentity(mode, "none", None, None, reference, resolution, exchange, None,
                                "unresolved", identifier, exchange, False, False, persisted, fresh,
                                False, reason)


def _legacy_identity(identifier: str, exchange: str | None, reason: str) -> ResearchReadIdentity:
    return ResearchReadIdentity(IdentityReadMode.LEGACY, "legacy", None, None, "not_applicable",
                                "not_requested", exchange, None, "unresolved", identifier, exchange,
                                False, True, False, False, False, reason)


def _legacy_metadata(os_con: sqlite3.Connection, ticker: str) -> dict | None:
    row = os_con.execute("SELECT * FROM securities WHERE ticker=?", (ticker,)).fetchone()
    if row is None:
        return None
    columns = [c[0] for c in os_con.execute("SELECT * FROM securities WHERE ticker=?", (ticker,)).description]
    return dict(zip(columns, row))


def _legacy_identifier_for_instrument(os_con: sqlite3.Connection, instrument_id: str) -> str | None:
    row = os_con.execute(
        "SELECT legacy_value FROM legacy_identity_mappings WHERE legacy_namespace='ngx.securities.ticker' "
        "AND canonical_subject_type='instrument' AND canonical_subject_id=? AND mapping_status='active' "
        "ORDER BY recorded_at DESC LIMIT 1", (instrument_id,),
    ).fetchone()
    return row[0] if row else None
