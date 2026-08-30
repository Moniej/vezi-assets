"""Typed, additive Fund Alpha canonical-domain contracts.

The module deliberately contains no database access and no consumer imports.
It is a stable vocabulary for a future migration, not a second persistence
model.  A field tagged ``compatibility_only`` exists only to make a legacy
caller adaptable during a bounded migration window.
"""

from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal


def uuid7() -> uuid.UUID:
    """Return a UUIDv7 without deriving identity from business attributes."""
    milliseconds = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (milliseconds << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)


class TemporalPrecision(str, Enum):
    DATE = "date"
    MINUTE = "minute"
    SECOND = "second"


@dataclass(frozen=True)
class TemporalValue:
    """A source-preserving temporal value; date precision never implies UTC midnight."""
    value: date | datetime
    precision: TemporalPrecision = TemporalPrecision.SECOND

    def __post_init__(self) -> None:
        if isinstance(self.value, datetime) and self.precision is TemporalPrecision.DATE:
            raise ValueError("date precision must use a date, not an invented datetime")
        if isinstance(self.value, date) and not isinstance(self.value, datetime) and self.precision is not TemporalPrecision.DATE:
            raise ValueError("a date-only value must declare date precision")
        if isinstance(self.value, datetime) and self.value.tzinfo is None:
            raise ValueError("time-of-day values must carry a trustworthy timezone")

    def no_later_than(self, cutoff: "TemporalValue") -> bool:
        """Conservative comparison: a date is visible only after its whole date is reached."""
        left = self.value.date() if isinstance(self.value, datetime) else self.value
        right = cutoff.value.date() if isinstance(cutoff.value, datetime) else cutoff.value
        if self.precision is TemporalPrecision.DATE or cutoff.precision is TemporalPrecision.DATE:
            return left <= right
        return self.value <= cutoff.value  # type: ignore[operator]


class AvailabilityPolicy(str, Enum):
    STRICT_SYSTEM_VINTAGE = "strict_system_vintage"
    VERIFIED_HISTORICAL_RECONSTRUCTION = "verified_historical_reconstruction"


class SourceAuthorityTier(str, Enum):
    OFFICIAL_REGULATOR = "official_regulator"
    OFFICIAL_EXCHANGE = "official_exchange"
    ISSUER_PRIMARY = "issuer_primary"
    ARCHIVED_ORIGINAL_SOURCE = "archived_original_source"
    INDEPENDENT_SECONDARY = "independent_secondary"
    UNVERIFIED = "unverified"
    SYNTHETIC = "synthetic"


class ValidationStatus(str, Enum):
    RAW = "raw"
    VALIDATED = "validated"
    REJECTED = "rejected"


class EvidenceStatus(str, Enum):
    UNSUPPORTED = "unsupported"
    GROUNDED = "grounded"
    EVIDENCE_GRADE = "evidence_grade"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


@dataclass
class CompanyIssuer:
    company_id: uuid.UUID = field(default_factory=uuid7)
    legal_name: str = ""
    incorporation_jurisdiction: str | None = None
    sector_code: str | None = None
    industry_code: str | None = None
    valid_from: TemporalValue | None = None
    valid_to: TemporalValue | None = None
    recorded_at: TemporalValue | None = None
    legacy_company_id: str | None = None  # compatibility_only


@dataclass
class InstrumentListing:
    instrument_id: uuid.UUID = field(default_factory=uuid7)
    company_id: uuid.UUID | None = None
    exchange_code: str | None = None
    instrument_type: str = "equity"
    currency: str | None = None
    listed_from: TemporalValue | None = None
    listed_to: TemporalValue | None = None
    recorded_at: TemporalValue | None = None
    legacy_security_id: str | None = None  # compatibility_only


@dataclass
class IdentifierAlias:
    alias_id: uuid.UUID = field(default_factory=uuid7)
    subject_kind: Literal["company", "instrument", "source"] = "company"
    subject_id: uuid.UUID | None = None
    identifier_type: str = "ticker"
    identifier_value: str = ""
    exchange_code: str | None = None
    valid_from: TemporalValue | None = None
    valid_to: TemporalValue | None = None
    evidence_id: uuid.UUID | None = None
    recorded_at: TemporalValue | None = None


@dataclass
class Source:
    source_id: uuid.UUID = field(default_factory=uuid7)
    name: str = ""
    authority_tier: SourceAuthorityTier = SourceAuthorityTier.UNVERIFIED
    source_data_confidence: float | None = None
    reliability_policy_version: str = "unversioned"
    is_synthetic: bool = False
    retention_policy: str | None = None
    recorded_at: TemporalValue | None = None


@dataclass
class SourceEndpoint:
    endpoint_id: uuid.UUID = field(default_factory=uuid7)
    source_id: uuid.UUID | None = None
    canonical_uri: str = ""
    endpoint_kind: str = "http"
    publication_time_policy: str | None = None
    retention_policy: str | None = None
    recorded_at: TemporalValue | None = None


@dataclass
class DocumentArtifact:
    artifact_id: uuid.UUID = field(default_factory=uuid7)
    sha256: str = ""
    storage_uri: str = ""
    byte_size: int = 0
    media_type: str = "application/octet-stream"
    source_endpoint_id: uuid.UUID | None = None
    retrieved_at: TemporalValue | None = None
    recorded_at: TemporalValue | None = None
    retention_restricted: bool = False


@dataclass
class DocumentVersion:
    document_version_id: uuid.UUID = field(default_factory=uuid7)
    artifact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    document_type: str = "unknown"
    published_at: TemporalValue | None = None
    publication_time_verification: str | None = None
    filing_date: TemporalValue | None = None
    supersedes_document_version_id: uuid.UUID | None = None
    recorded_at: TemporalValue | None = None


@dataclass
class ParsedDocumentRepresentation:
    representation_id: uuid.UUID = field(default_factory=uuid7)
    document_version_id: uuid.UUID | None = None
    parser_name: str = ""
    parser_version: str = ""
    artifact_sha256: str = ""
    representation_uri: str | None = None
    recorded_at: TemporalValue | None = None


@dataclass
class EvidenceLocator:
    locator_id: uuid.UUID = field(default_factory=uuid7)
    document_version_id: uuid.UUID | None = None
    parsed_representation_id: uuid.UUID | None = None
    locator: str = ""
    quote: str | None = None
    page_number: int | None = None
    table_locator: str | None = None


@dataclass
class EvidenceItem:
    evidence_id: uuid.UUID = field(default_factory=uuid7)
    source_id: uuid.UUID | str | None = None
    locator: str = ""
    document_version_id: uuid.UUID | None = None
    evidence_locator_id: uuid.UUID | None = None
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    grounded: bool = False
    grounding_result: str = "not_run"
    recorded_at: TemporalValue | None = None


@dataclass
class Citation:
    citation_id: uuid.UUID = field(default_factory=uuid7)
    evidence_id: uuid.UUID | None = None
    rendered_text: str = ""
    citation_role: str = "supporting"


@dataclass
class FactAssertion:
    fact_id: uuid.UUID = field(default_factory=uuid7)
    subject_id: uuid.UUID | str | None = None
    predicate: str = ""
    value: Any = None
    value_unit: str | None = None
    period_start: TemporalValue | None = None
    period_end: TemporalValue | None = None
    event_time: TemporalValue | None = None
    effective_time: TemporalValue | None = None
    published_at: TemporalValue | None = None
    retrieved_at: TemporalValue | None = None
    recorded_at: TemporalValue | None = None
    valid_from: TemporalValue | None = None
    valid_to: TemporalValue | None = None
    source_id: uuid.UUID | str | None = None
    evidence_ids: list[uuid.UUID] = field(default_factory=list)
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    validation_status: ValidationStatus = ValidationStatus.RAW
    evidence_status: EvidenceStatus = EvidenceStatus.UNSUPPORTED
    record_status: RecordStatus = RecordStatus.ACTIVE
    supersedes_fact_id: uuid.UUID | None = None
    publication_time_verification: str | None = None


@dataclass
class EventAssertion:
    event_id: uuid.UUID = field(default_factory=uuid7)
    subject_id: uuid.UUID | str | None = None
    event_type: str = ""
    event_time: TemporalValue | None = None
    effective_time: TemporalValue | None = None
    published_at: TemporalValue | None = None
    recorded_at: TemporalValue | None = None
    evidence_ids: list[uuid.UUID] = field(default_factory=list)
    record_status: RecordStatus = RecordStatus.ACTIVE


@dataclass
class CorporateAction:
    corporate_action_id: uuid.UUID = field(default_factory=uuid7)
    instrument_id: uuid.UUID | None = None
    action_type: str = ""
    announcement_event_id: uuid.UUID | None = None
    effective_time: TemporalValue | None = None
    adjustment_terms: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[uuid.UUID] = field(default_factory=list)
    recorded_at: TemporalValue | None = None


@dataclass
class RelationshipAssertion:
    relationship_id: uuid.UUID = field(default_factory=uuid7)
    subject_id: uuid.UUID | str | None = None
    predicate: str = ""
    object_id: uuid.UUID | str | None = None
    valid_from: TemporalValue | None = None
    valid_to: TemporalValue | None = None
    published_at: TemporalValue | None = None
    recorded_at: TemporalValue | None = None
    evidence_ids: list[uuid.UUID] = field(default_factory=list)
    record_status: RecordStatus = RecordStatus.ACTIVE


@dataclass
class DataCoverageAssessment:
    assessment_id: uuid.UUID = field(default_factory=uuid7)
    subject_id: uuid.UUID | str | None = None
    domain: str = ""
    availability_status: Literal["available", "partial", "missing", "unknown"] = "unknown"
    source_coverage: float | None = None
    evidence_coverage: float | None = None
    data_quality_assessment: str | None = None
    observed_at: TemporalValue | None = None
    recorded_at: TemporalValue | None = None


@dataclass(frozen=True)
class TemporalQueryContext:
    decision_time: TemporalValue
    system_vintage: TemporalValue
    availability_policy: AvailabilityPolicy = AvailabilityPolicy.STRICT_SYSTEM_VINTAGE
    min_source_confidence: float | None = None
    consumer: str | None = None

