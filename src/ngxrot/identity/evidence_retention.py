"""Evidence-retention status and archive helpers for historical identity review.

These helpers deliberately stop before database persistence.  They wrap the
canonical content-addressed archive rather than creating another storage
scheme, and make URL discovery, retrieval failure, retention and evidence
grade distinct states.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ngxrot.canonical.archive import LocalImmutableArchive
from ngxrot.canonical.contracts import DocumentArtifact, SourceEndpoint, TemporalValue


class RetentionStatus(str, Enum):
    DISCOVERED_ONLY = "discovered_only"
    RETRIEVAL_FAILED = "retrieval_failed"
    RETRIEVED_UNARCHIVED = "retrieved_unarchived"
    ARCHIVED_UNPARSED = "archived_unparsed"
    ARCHIVED_PARSED = "archived_parsed"
    EVIDENCE_GRADE = "evidence_grade"


@dataclass(frozen=True)
class DownloadAttempt:
    source_url: str
    status: RetentionStatus
    retrieved_at: TemporalValue | None
    artifact_sha256: str | None
    error: str | None = None


def assess_retention(*, source_discovered: bool, source_accessible_in_browser: bool = False,
                     source_download_blocked_in_environment: bool = False,
                     source_retrieved: bool = False, source_archived: bool = False,
                     source_parsed: bool = False, evidence_locator_created: bool = False) -> RetentionStatus:
    """Classify retention without treating browser visibility as possession."""
    if not source_discovered:
        return RetentionStatus.DISCOVERED_ONLY
    if source_download_blocked_in_environment:
        return RetentionStatus.RETRIEVAL_FAILED
    if not source_retrieved:
        return RetentionStatus.DISCOVERED_ONLY
    if not source_archived:
        return RetentionStatus.RETRIEVED_UNARCHIVED
    if not source_parsed:
        return RetentionStatus.ARCHIVED_UNPARSED
    if not evidence_locator_created:
        return RetentionStatus.ARCHIVED_PARSED
    return RetentionStatus.EVIDENCE_GRADE


def record_download_attempt(*, source_url: str, retrieved_at: TemporalValue | None,
                            error: str | None = None,
                            artifact_sha256: str | None = None) -> DownloadAttempt:
    """Represent a real retrieval outcome; failures can never have an artifact hash."""
    if error:
        return DownloadAttempt(source_url, RetentionStatus.RETRIEVAL_FAILED, retrieved_at, None, error)
    if artifact_sha256 is None:
        return DownloadAttempt(source_url, RetentionStatus.RETRIEVED_UNARCHIVED, retrieved_at, None)
    return DownloadAttempt(source_url, RetentionStatus.ARCHIVED_UNPARSED, retrieved_at, artifact_sha256)


def archive_retrieved_artifact(raw_bytes: bytes, *, root: Path, endpoint: SourceEndpoint,
                               retrieved_at: TemporalValue, recorded_at: TemporalValue,
                               media_type: str = "application/pdf") -> DocumentArtifact:
    """Put received bytes through the canonical immutable archive abstraction."""
    return LocalImmutableArchive(root).put(
        raw_bytes,
        media_type=media_type,
        source_endpoint=endpoint,
        retrieved_at=retrieved_at,
        recorded_at=recorded_at,
    )
