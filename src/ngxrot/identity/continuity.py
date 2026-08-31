"""Pure, evidence-gated recommendations for historical series continuity.

The result is a review recommendation only.  It never mutates canonical
identity, aliases, relationships, or a database.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ContinuityClass(str, Enum):
    SAME_INSTRUMENT_ALIAS_CHANGE = "same_instrument_alias_change"
    SUCCESSOR_REPLACEMENT_INSTRUMENT = "successor_replacement_instrument"
    ISSUER_REORGANIZATION_UNCERTAIN = "issuer_reorganization_uncertain"
    UNRELATED = "unrelated"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ContinuityTreatment:
    classification: ContinuityClass
    recommended_treatment: str


def recommend_continuity_treatment(*, evidence_status: str,
                                   event_type: str | None) -> ContinuityTreatment:
    """Return a conservative non-mutating treatment recommendation.

    Only verified evidence of a simple ticker rename can propose one
    instrument with temporally bounded aliases.  Issuer reorganizations and
    security replacements are intentionally never collapsed into aliases.
    """
    if evidence_status != "verified":
        return ContinuityTreatment(ContinuityClass.UNRESOLVED, "unresolved")
    if event_type == "ticker_rename":
        return ContinuityTreatment(ContinuityClass.SAME_INSTRUMENT_ALIAS_CHANGE,
                                   "one_instrument_bounded_aliases")
    if event_type == "security_replacement":
        return ContinuityTreatment(ContinuityClass.SUCCESSOR_REPLACEMENT_INSTRUMENT,
                                   "two_instruments_successor_relationship")
    if event_type in {"holding_company_reorganization", "merger", "scheme"}:
        return ContinuityTreatment(ContinuityClass.ISSUER_REORGANIZATION_UNCERTAIN,
                                   "unresolved")
    if event_type == "unrelated":
        return ContinuityTreatment(ContinuityClass.UNRELATED, "retain_separate")
    return ContinuityTreatment(ContinuityClass.UNRESOLVED, "unresolved")
