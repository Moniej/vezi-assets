"""Opt-in canonical identity resolver; no existing consumer calls it in Stage 2A."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum

from ngxrot.canonical.contracts import AvailabilityPolicy, TemporalQueryContext


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    TEMPORALLY_UNAVAILABLE = "temporally_unavailable"


@dataclass(frozen=True)
class InstrumentResolution:
    status: ResolutionStatus
    instrument_id: str | None = None
    company_id: str | None = None
    alias_id: str | None = None
    verification_status: str | None = None
    legacy_mapping_id: str | None = None


def resolve_instrument(con: sqlite3.Connection, *, identifier: str, identifier_type: str,
                       exchange: str | None = None,
                       temporal_context: TemporalQueryContext | None = None) -> InstrumentResolution:
    clauses = ["a.subject_type='instrument'", "a.identifier_type=?", "a.identifier_value=?"]
    values: list[object] = [identifier_type, identifier]
    if exchange is not None:
        clauses.append("a.exchange_code=?")
        values.append(exchange)
    rows = con.execute("SELECT a.alias_id,a.subject_id,a.verification_status,a.valid_from,a.valid_to,a.recorded_at,i.company_id FROM identifier_aliases a JOIN instrument_listings i ON i.instrument_id=a.subject_id WHERE " + " AND ".join(clauses), values).fetchall()
    if not rows:
        return InstrumentResolution(ResolutionStatus.UNKNOWN)
    visible = []
    for row in rows:
        alias_id, instrument_id, verification, valid_from, valid_to, recorded_at, company_id = row
        if temporal_context:
            # Unknown real-world validity may not be projected backwards.
            if valid_from is None and valid_to is None:
                continue
            decision = temporal_context.decision_time.value.isoformat()
            if valid_from and valid_from > decision:
                continue
            if valid_to and valid_to < decision:
                continue
            if temporal_context.availability_policy is AvailabilityPolicy.STRICT_SYSTEM_VINTAGE and (recorded_at is None or recorded_at > temporal_context.system_vintage.value.isoformat()):
                continue
        visible.append((alias_id, instrument_id, verification, company_id))
    if temporal_context and not visible:
        return InstrumentResolution(ResolutionStatus.TEMPORALLY_UNAVAILABLE)
    distinct = {row[1] for row in visible}
    if len(distinct) > 1:
        return InstrumentResolution(ResolutionStatus.AMBIGUOUS)
    alias_id, instrument_id, verification, company_id = visible[0]
    mapping = con.execute("SELECT mapping_id FROM legacy_identity_mappings WHERE canonical_subject_type='instrument' AND canonical_subject_id=? AND mapping_status='active' ORDER BY recorded_at DESC LIMIT 1", (instrument_id,)).fetchone()
    return InstrumentResolution(ResolutionStatus.RESOLVED, instrument_id, company_id, alias_id, verification, mapping[0] if mapping else None)
