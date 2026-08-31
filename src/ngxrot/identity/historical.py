"""Evidence-first historical identifier assertions.

This is a separate opt-in resolver: it never changes the global strict
identity resolver and it never treats a later capture as historical system
knowledge.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ngxrot.migrations.framework import Migration


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_ID = "20260831_001_historical_identity_assertions"


def historical_identity_assertion_migration() -> Migration:
    sql = (ROOT / "migrations" / f"{MIGRATION_ID}.sql").read_text(encoding="utf-8")
    return Migration(MIGRATION_ID, "ngx", 2, 3, sql)


class HistoricalIdentityPolicy(str, Enum):
    STRICT_SYSTEM_VINTAGE = "strict_system_vintage"
    VERIFIED_HISTORICAL_RECONSTRUCTION = "verified_historical_reconstruction"


class HistoricalResolutionStatus(str, Enum):
    RESOLVED_VERIFIED = "resolved_verified"
    RESOLVED_CURRENT_ONLY = "resolved_current_only"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class HistoricalInstrumentResolution:
    status: HistoricalResolutionStatus
    instrument_id: str | None = None
    assertion_ids: tuple[str, ...] = ()
    reconstruction_disclosed: bool = False


def assert_historical_identity(con: sqlite3.Connection, *, assertion_id: str,
                               instrument_id: str, ticker: str, valid_from: str,
                               valid_to: str | None, validity_precision: str,
                               verification_status: str, verification_method: str,
                               evidence_id: int | None, citation_reference: str | None,
                               source_authority_tier: str, recorded_at: str,
                               alias_id: str | None = None,
                               supersedes_assertion_id: str | None = None) -> None:
    """Append an assertion after enforcing the verified-evidence threshold."""
    if verification_status == "verified":
        if source_authority_tier not in {"tier1", "tier2", "tier3"}:
            raise ValueError("Tier 4 evidence cannot create a verified historical alias")
        if evidence_id is None or not citation_reference:
            raise ValueError("verified historical alias requires EvidenceItem and citation")
    if validity_precision == "interval_verified" and valid_to is None:
        raise ValueError("interval_verified requires both historical bounds")
    con.execute("""INSERT INTO historical_identifier_assertions(
        assertion_id,alias_id,canonical_instrument_id,identifier_type,identifier_value,
        exchange_code,valid_from,valid_to,validity_precision,verification_status,
        verification_method,evidence_id,citation_reference,source_authority_tier,
        recorded_at,supersedes_assertion_id
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        assertion_id, alias_id, instrument_id, "ticker", ticker, "NGX", valid_from,
        valid_to, validity_precision, verification_status, verification_method,
        evidence_id, citation_reference, source_authority_tier, recorded_at,
        supersedes_assertion_id,
    ))


def _valid_on(row: tuple, decision_date: str) -> bool:
    _, _, _, valid_from, valid_to, precision, *_ = row
    if precision == "observed_on_date_only":
        return valid_from == decision_date
    if precision == "interval_verified":
        return valid_from <= decision_date <= valid_to
    # Other declared precisions are deliberately non-resolving until their
    # conservative comparison rules are specifically implemented and approved.
    return False


def resolve_historical_instrument(con: sqlite3.Connection, *, ticker: str,
                                  exchange: str, decision_date: str,
                                  system_vintage: str,
                                  policy: HistoricalIdentityPolicy) -> HistoricalInstrumentResolution:
    """Resolve only evidence-backed historical aliases; never project current ones."""
    try:
        rows = con.execute("""SELECT assertion_id,canonical_instrument_id,verification_status,
            valid_from,valid_to,validity_precision,source_authority_tier,recorded_at
            FROM historical_identifier_assertions
            WHERE identifier_type='ticker' AND identifier_value=? AND exchange_code=?""",
                           (ticker, exchange)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    matching = [row for row in rows if _valid_on(row, decision_date)]
    if any(row[2] == "conflicting" for row in matching):
        return HistoricalInstrumentResolution(HistoricalResolutionStatus.CONFLICTING,
                                              assertion_ids=tuple(row[0] for row in matching))
    verified = [row for row in matching if row[2] == "verified"]
    if policy is HistoricalIdentityPolicy.STRICT_SYSTEM_VINTAGE:
        verified = [row for row in verified if row[7] <= system_vintage]
    identifiers = {row[1] for row in verified}
    if len(identifiers) == 1:
        return HistoricalInstrumentResolution(HistoricalResolutionStatus.RESOLVED_VERIFIED,
                                              next(iter(identifiers)), tuple(row[0] for row in verified),
                                              policy is HistoricalIdentityPolicy.VERIFIED_HISTORICAL_RECONSTRUCTION)
    if len(identifiers) > 1:
        return HistoricalInstrumentResolution(HistoricalResolutionStatus.AMBIGUOUS,
                                              assertion_ids=tuple(row[0] for row in verified))
    current = con.execute("""SELECT 1 FROM identifier_aliases
        WHERE subject_type='instrument' AND identifier_type='ticker'
          AND identifier_value=? AND exchange_code=? LIMIT 1""", (ticker, exchange)).fetchone()
    if current:
        return HistoricalInstrumentResolution(HistoricalResolutionStatus.RESOLVED_CURRENT_ONLY)
    return HistoricalInstrumentResolution(HistoricalResolutionStatus.UNRESOLVED,
                                          assertion_ids=tuple(row[0] for row in matching))
