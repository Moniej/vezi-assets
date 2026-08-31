"""Small archive-backed canonical evidence persistence adapter.

This module persists only the chain required to audit historical identity
evidence.  It neither asserts identity nor changes legacy document storage.
"""
from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ngxrot.canonical.archive import LocalImmutableArchive
from ngxrot.canonical.contracts import (
    DocumentArtifact, SourceEndpoint, SourceAuthorityTier, TemporalPrecision,
    TemporalValue, uuid7,
)
from ngxrot.migrations.framework import Migration
from ngxrot.migrations.framework import MigrationRunner


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_ID = "20260831_000_canonical_evidence_persistence_foundation"


def canonical_evidence_migration() -> Migration:
    sql = (ROOT / "migrations" / f"{MIGRATION_ID}.sql").read_text(encoding="utf-8")
    return Migration(MIGRATION_ID, "ngx", 2, 3, sql)


def apply_canonical_evidence_persistence(con: sqlite3.Connection, *, backup_manifest_sha256: str) -> None:
    """Apply only the additive evidence foundation to a verified backup-backed copy."""
    MigrationRunner([canonical_evidence_migration()]).apply_pending(
        con, database_target="ngx", backup_manifest_verified=True,
        backup_manifest_sha256=backup_manifest_sha256,
    )


class EvidenceUse(str, Enum):
    HISTORICAL_TICKER_VALIDITY = "historical_ticker_validity"
    INSTRUMENT_CONTINUITY = "instrument_continuity"
    SERIES_OWNERSHIP = "series_ownership"
    CORPORATE_EVENT_ASSERTION = "corporate_event_assertion"


class EvidenceEligibilityFailure(str, Enum):
    ARTIFACT_MISSING = "artifact_missing"
    LOCATOR_MISSING = "locator_missing"
    SOURCE_AUTHORITY_INSUFFICIENT = "source_authority_insufficient"
    PUBLICATION_CONTEXT_MISSING = "publication_context_missing"
    RETRIEVAL_ONLY = "retrieval_only"
    UNRESOLVED_OR_CONFLICTING = "unresolved_or_conflicting_evidence"
    SYNTHETIC_SOURCE = "synthetic_source"
    PARSER_LOCATOR_INTEGRITY_FAILURE = "parser_locator_integrity_failure"
    ASSERTION_TYPE_UNSUPPORTED = "assertion_type_unsupported"
    OS_UNAVAILABLE = "os_unavailable"


@dataclass(frozen=True)
class PersistedImport:
    artifact_id: str
    document_version_id: str
    source_id: str
    endpoint_id: str
    artifact: DocumentArtifact


@dataclass(frozen=True)
class RetrievalFailure:
    status: str
    artifact_id: None
    retrieval_attempt_id: str


@dataclass(frozen=True)
class EvidenceEligibility:
    eligible: bool
    failure: EvidenceEligibilityFailure | None = None


@dataclass(frozen=True)
class EvidenceChain:
    evidence_id: str
    locator_id: str | None
    document_version_id: str
    artifact_id: str
    source_id: str
    citation_id: str


def _temporal(value: TemporalValue) -> tuple[str, str]:
    raw = value.value.isoformat()
    return raw, value.precision.value


def _parse(raw: bytes, media_type: str) -> tuple[str, str, str]:
    if media_type == "application/pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            return "pdfplumber", getattr(pdfplumber, "__version__", "unknown"), "\n\f\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    return "utf8_plaintext", "1", raw.decode("utf-8", errors="replace")


class CanonicalEvidenceStore:
    def __init__(self, con: sqlite3.Connection, *, archive_root: Path) -> None:
        self.con = con
        self.archive = LocalImmutableArchive(archive_root)

    def _source_endpoint(self, *, source_name: str, authority: SourceAuthorityTier, is_synthetic: bool,
                         source_url: str, recorded_at: TemporalValue) -> tuple[str, str]:
        recorded_value, recorded_precision = _temporal(recorded_at)
        existing = self.con.execute("SELECT source_id FROM canonical_sources WHERE source_name=? AND authority_tier=? AND reliability_policy_version=? AND is_synthetic=?",
                                    (source_name, authority.value, "historical_identity_source_policy_v1", int(is_synthetic))).fetchone()
        if existing:
            source_id = existing[0]
        else:
            source_id = str(uuid7())
            self.con.execute("INSERT INTO canonical_sources VALUES (?,?,?,?,?,?,?,?)", (
                source_id, source_name, authority.value, "historical_identity_source_policy_v1", int(is_synthetic), None,
                recorded_value, recorded_precision,
            ))
        endpoint = self.con.execute("SELECT endpoint_id FROM canonical_source_endpoints WHERE source_id=? AND canonical_uri=?",
                                    (source_id, source_url)).fetchone()
        if endpoint:
            return source_id, endpoint[0]
        endpoint_id = str(uuid7())
        self.con.execute("INSERT INTO canonical_source_endpoints VALUES (?,?,?,?,?,?,?,?)", (
            endpoint_id, source_id, source_url, "manual_operator_supplied", None, "permitted", recorded_value, recorded_precision,
        ))
        return source_id, endpoint_id

    def import_evidence_document(self, local_path: Path, *, source_url: str, source_name: str,
                                 source_authority: SourceAuthorityTier, retrieved_at: TemporalValue,
                                 document_type: str, published_at: TemporalValue | None = None,
                                 publication_time_verification: str | None = None,
                                 is_synthetic: bool = False) -> PersistedImport:
        """Archive exact operator bytes; retrieval always means operator import here."""
        raw = local_path.read_bytes()
        source_id, endpoint_id = self._source_endpoint(source_name=source_name, authority=source_authority,
                                                        is_synthetic=is_synthetic, source_url=source_url,
                                                        recorded_at=retrieved_at)
        endpoint = SourceEndpoint(endpoint_id=__import__("uuid").UUID(endpoint_id), source_id=__import__("uuid").UUID(source_id),
                                  canonical_uri=source_url, endpoint_kind="manual_operator_supplied", retention_policy="permitted",
                                  recorded_at=retrieved_at)
        artifact = self.archive.put(raw, media_type="application/pdf" if local_path.suffix.lower() == ".pdf" else "text/plain",
                                    source_endpoint=endpoint, retrieved_at=retrieved_at, recorded_at=retrieved_at)
        retrieved_value, retrieved_precision = _temporal(retrieved_at)
        self.con.execute("INSERT INTO canonical_retrieval_attempts VALUES (?,?,?,?,?,?,?)", (
            str(uuid7()), source_url, "parsed", "manual_operator_import", None,
            retrieved_value, retrieved_precision,
        ))
        artifact_row = self.con.execute("SELECT artifact_id FROM canonical_document_artifacts WHERE content_sha256=?", (artifact.sha256,)).fetchone()
        if artifact_row:
            artifact_id = artifact_row[0]
        else:
            artifact_id = str(uuid7())
            self.con.execute("INSERT INTO canonical_document_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                artifact_id, endpoint_id, artifact.sha256, artifact.storage_uri, artifact.byte_size, artifact.media_type,
                "manual_operator_import", local_path.name, retrieved_value, retrieved_precision, retrieved_value,
                retrieved_precision, int(artifact.retention_restricted),
            ))
        version_row = self.con.execute("SELECT document_version_id FROM canonical_document_versions WHERE artifact_id=?", (artifact_id,)).fetchone()
        if version_row:
            self.con.commit()
            return PersistedImport(artifact_id, version_row[0], source_id, endpoint_id, artifact)
        version_id = str(uuid7())
        published_value, published_precision = (None, None) if published_at is None else _temporal(published_at)
        self.con.execute("INSERT INTO canonical_document_versions VALUES (?,?,?,?,?,?,?,?,?)", (
            version_id, artifact_id, document_type, published_value, published_precision, publication_time_verification, None,
            retrieved_value, retrieved_precision,
        ))
        parser, parser_version, parsed = _parse(raw, artifact.media_type)
        self.con.execute("INSERT INTO canonical_parsed_document_representations VALUES (?,?,?,?,?,?,?,?,?)", (
            str(uuid7()), version_id, parser, parser_version, artifact.sha256, None, parsed, retrieved_value, retrieved_precision,
        ))
        self.con.commit()
        return PersistedImport(artifact_id, version_id, source_id, endpoint_id, artifact)

    def record_retrieval_failure(self, source_url: str, *, error: str, recorded_at: TemporalValue) -> RetrievalFailure:
        value, precision = _temporal(recorded_at)
        attempt_id = str(uuid7())
        self.con.execute("INSERT INTO canonical_retrieval_attempts VALUES (?,?,?,?,?,?,?)", (attempt_id, source_url, "retrieval_failed", "direct_retrieval", error, value, precision))
        self.con.commit()
        return RetrievalFailure("retrieval_failed", None, attempt_id)

    def create_locator(self, document_version_id: str, *, page_number: int | None = None, section_title: str | None = None,
                       paragraph: str | None = None, table_locator: str | None = None, quote: str | None = None,
                       char_start: int | None = None, char_end: int | None = None, recorded_at: TemporalValue) -> str:
        representation = self.con.execute("SELECT representation_id FROM canonical_parsed_document_representations WHERE document_version_id=? ORDER BY representation_id LIMIT 1", (document_version_id,)).fetchone()
        value, precision = _temporal(recorded_at)
        locator_id = str(uuid7())
        self.con.execute("INSERT INTO canonical_evidence_locators VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            locator_id, document_version_id, representation[0] if representation else None, None, quote, page_number,
            section_title, paragraph, table_locator, char_start, char_end, value, precision,
        ))
        self.con.commit()
        return locator_id

    def create_evidence_item(self, document_version_id: str, *, locator_id: str | None, evidence_type: str,
                             supporting_text: str, extraction_method: str, extraction_confidence: float | None,
                             verification_status: str, recorded_at: TemporalValue) -> str:
        row = self.con.execute("""SELECT ep.source_id FROM canonical_document_versions dv
            JOIN canonical_document_artifacts da ON da.artifact_id=dv.artifact_id
            JOIN canonical_source_endpoints ep ON ep.endpoint_id=da.source_endpoint_id
            WHERE dv.document_version_id=?""", (document_version_id,)).fetchone()
        if not row:
            raise ValueError("document version does not exist")
        value, precision = _temporal(recorded_at)
        evidence_id = str(uuid7())
        self.con.execute("INSERT INTO canonical_evidence_items VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            evidence_id, row[0], document_version_id, locator_id, evidence_type, supporting_text, extraction_method,
            extraction_confidence, verification_status, value, precision,
        ))
        self.con.commit()
        return evidence_id

    def create_citation(self, evidence_id: str, *, source_url: str, authority_metadata: dict, recorded_at: TemporalValue,
                        citation_metadata: dict | None = None) -> str:
        value, precision = _temporal(recorded_at)
        citation_id = str(uuid7())
        self.con.execute("INSERT INTO canonical_citations VALUES (?,?,?,?,?,?,?,?)", (
            citation_id, evidence_id, source_url, json.dumps(authority_metadata, sort_keys=True),
            json.dumps(citation_metadata or {}, sort_keys=True), "supporting", value, precision,
        ))
        self.con.commit()
        return citation_id

    def load_evidence_chain(self, evidence_id: str) -> EvidenceChain:
        row = self.con.execute("""SELECT ei.evidence_id, ei.locator_id, ei.document_version_id, da.artifact_id,
            ei.source_id, c.citation_id FROM canonical_evidence_items ei
            JOIN canonical_document_versions dv ON dv.document_version_id=ei.document_version_id
            JOIN canonical_document_artifacts da ON da.artifact_id=dv.artifact_id
            JOIN canonical_citations c ON c.evidence_id=ei.evidence_id WHERE ei.evidence_id=?""", (evidence_id,)).fetchone()
        if not row:
            raise KeyError(evidence_id)
        return EvidenceChain(*row)

    def validate_identity_evidence(self, evidence_id: str, use: EvidenceUse) -> EvidenceEligibility:
        try:
            row = self.con.execute("""SELECT da.artifact_id, ei.locator_id, cs.authority_tier, cs.is_synthetic,
                dv.published_at_value, ei.verification_status, ei.evidence_type, COUNT(c.citation_id)
                FROM canonical_evidence_items ei JOIN canonical_document_versions dv ON dv.document_version_id=ei.document_version_id
                JOIN canonical_document_artifacts da ON da.artifact_id=dv.artifact_id
                JOIN canonical_sources cs ON cs.source_id=ei.source_id LEFT JOIN canonical_citations c ON c.evidence_id=ei.evidence_id
                WHERE ei.evidence_id=? GROUP BY ei.evidence_id""", (evidence_id,)).fetchone()
        except sqlite3.Error:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.OS_UNAVAILABLE)
        if not row:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.ARTIFACT_MISSING)
        _, locator_id, authority, synthetic, published, verification, evidence_type, citations = row
        if synthetic:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.SYNTHETIC_SOURCE)
        if authority in {SourceAuthorityTier.INDEPENDENT_SECONDARY.value, SourceAuthorityTier.UNVERIFIED.value, SourceAuthorityTier.SYNTHETIC.value}:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.SOURCE_AUTHORITY_INSUFFICIENT)
        if not locator_id:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.LOCATOR_MISSING)
        locator = self.con.execute("SELECT document_version_id FROM canonical_evidence_locators WHERE locator_id=?", (locator_id,)).fetchone()
        if not locator:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.PARSER_LOCATOR_INTEGRITY_FAILURE)
        if not citations:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.RETRIEVAL_ONLY)
        if verification in {"rejected", "conflicting", "unresolved"}:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.UNRESOLVED_OR_CONFLICTING)
        allowed_types = {
            EvidenceUse.HISTORICAL_TICKER_VALIDITY: {"ticker_symbol"},
            EvidenceUse.SERIES_OWNERSHIP: {"market_series_ownership"},
            EvidenceUse.INSTRUMENT_CONTINUITY: {"same_security_continuity"},
            EvidenceUse.CORPORATE_EVENT_ASSERTION: {"corporate_event"},
        }
        if evidence_type not in allowed_types[use]:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.ASSERTION_TYPE_UNSUPPORTED)
        if use is EvidenceUse.HISTORICAL_TICKER_VALIDITY and not published:
            return EvidenceEligibility(False, EvidenceEligibilityFailure.PUBLICATION_CONTEXT_MISSING)
        return EvidenceEligibility(True)
