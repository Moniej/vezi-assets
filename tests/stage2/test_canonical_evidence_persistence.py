"""Canonical evidence persistence is archive-backed, append-only, and identity-neutral."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import SourceAuthorityTier, TemporalPrecision, TemporalValue
from ngxrot.canonical.evidence_store import (
    EvidenceEligibilityFailure,
    EvidenceUse,
    CanonicalEvidenceStore,
    canonical_evidence_migration,
)
from ngxrot.migrations.framework import MigrationRunner


UTC_NOW = TemporalValue(datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc), TemporalPrecision.SECOND)
DATE_ONLY = TemporalValue(date(2025, 2, 13), TemporalPrecision.DATE)


class CanonicalEvidencePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2] / ".test-runtime" / "canonical-evidence" / str(uuid.uuid4())
        self.root.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(":memory:")
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.execute("""CREATE TABLE schema_migration_ledger(
            migration_id TEXT PRIMARY KEY, database_target TEXT NOT NULL, checksum TEXT NOT NULL,
            pre_version INTEGER NOT NULL, post_version INTEGER NOT NULL, applied_at TEXT NOT NULL,
            backup_manifest_sha256 TEXT
        )""")
        self.con.execute("INSERT INTO schema_migration_ledger VALUES (?,?,?,?,?,?,?)",
                         ("20260830_000_pre_consolidation_baseline", "ngx", "baseline", 0, 1, UTC_NOW.value.isoformat(), "backup"))
        self.con.execute("INSERT INTO schema_migration_ledger VALUES (?,?,?,?,?,?,?)",
                         ("20260830_001_canonical_identity_foundation", "ngx", "identity", 1, 2, UTC_NOW.value.isoformat(), "backup"))
        MigrationRunner([canonical_evidence_migration()]).apply_pending(
            self.con, database_target="ngx", backup_manifest_verified=True, backup_manifest_sha256="copy-backup"
        )
        self.store = CanonicalEvidenceStore(self.con, archive_root=self.root / "archive")

    def tearDown(self) -> None:
        self.con.close()
        # Retained archive bytes are read-only by design.  The ignored, known
        # writable test-runtime is cleaned by the fixture harness.

    def _import(self, raw: bytes = b"Official notice: ticker changed."):
        supplied = self.root / "notice.txt"
        supplied.write_bytes(raw)
        return self.store.import_evidence_document(
            supplied, source_url="https://official.example/notice", source_name="Official Exchange",
            source_authority=SourceAuthorityTier.OFFICIAL_EXCHANGE, retrieved_at=UTC_NOW,
            document_type="market_bulletin", published_at=DATE_ONLY,
        )

    def test_migration_creates_only_canonical_evidence_tables_at_version_three(self) -> None:
        self.assertEqual(MigrationRunner([canonical_evidence_migration()]).current_version(self.con, "ngx"), 3)
        tables = {row[0] for row in self.con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"canonical_sources", "canonical_document_artifacts", "canonical_document_versions",
                         "canonical_evidence_locators", "canonical_evidence_items", "canonical_citations"} <= tables)

    def test_same_bytes_have_stable_content_addressed_artifact(self) -> None:
        first = self._import()
        second = self._import()
        self.assertEqual(first.artifact.sha256, hashlib.sha256(b"Official notice: ticker changed.").hexdigest())
        self.assertEqual(first.artifact.storage_uri, second.artifact.storage_uri)
        self.assertEqual(first.artifact_id, second.artifact_id)

    def test_different_bytes_from_same_url_do_not_overwrite_history(self) -> None:
        first = self._import(b"Version A")
        second = self._import(b"Version B")
        self.assertNotEqual(first.artifact_id, second.artifact_id)
        self.assertNotEqual(first.document_version_id, second.document_version_id)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM canonical_document_artifacts").fetchone()[0], 2)

    def test_manual_import_preserves_operator_provenance(self) -> None:
        imported = self._import()
        row = self.con.execute("SELECT acquisition_mode, original_filename, retrieved_at_value FROM canonical_document_artifacts WHERE artifact_id=?", (imported.artifact_id,)).fetchone()
        self.assertEqual(row, ("manual_operator_import", "notice.txt", UTC_NOW.value.isoformat()))

    def test_manual_import_records_explicit_parsed_acquisition_attempt(self) -> None:
        self._import()
        row = self.con.execute("SELECT status, acquisition_mode FROM canonical_retrieval_attempts").fetchone()
        self.assertEqual(row, ("parsed", "manual_operator_import"))

    def test_date_only_publication_does_not_fabricate_time_of_day(self) -> None:
        imported = self._import()
        row = self.con.execute("SELECT published_at_value, published_at_precision FROM canonical_document_versions WHERE document_version_id=?", (imported.document_version_id,)).fetchone()
        self.assertEqual(row, ("2025-02-13", "date"))

    def test_document_header_can_verify_date_only_publication_metadata(self) -> None:
        supplied = self.root / "dated-notice.txt"
        supplied.write_text("24 February 2020")
        imported = self.store.import_evidence_document(
            supplied, source_url="https://official.example/dated", source_name="Official Exchange",
            source_authority=SourceAuthorityTier.OFFICIAL_EXCHANGE, retrieved_at=UTC_NOW,
            document_type="market_bulletin", published_at=TemporalValue(date(2020, 2, 24), TemporalPrecision.DATE),
            publication_time_verification="document_header_date",
        )
        row = self.con.execute("SELECT published_at_value, published_at_precision, publication_time_verification FROM canonical_document_versions WHERE document_version_id=?", (imported.document_version_id,)).fetchone()
        self.assertEqual(row, ("2020-02-24", "date", "document_header_date"))

    def test_url_only_and_retrieval_failure_cannot_be_evidence_grade(self) -> None:
        self.assertEqual(self.store.validate_identity_evidence("missing", EvidenceUse.HISTORICAL_TICKER_VALIDITY).failure,
                         EvidenceEligibilityFailure.ARTIFACT_MISSING)
        failure = self.store.record_retrieval_failure("https://official.example/blocked", error="ProxyError", recorded_at=UTC_NOW)
        self.assertEqual(failure.status, "retrieval_failed")
        self.assertIsNone(failure.artifact_id)

    def test_evidence_chain_requires_a_locator(self) -> None:
        imported = self._import()
        evidence_id = self.store.create_evidence_item(imported.document_version_id, locator_id=None,
                                                       evidence_type="identity", supporting_text="notice",
                                                       extraction_method="manual", extraction_confidence=1.0,
                                                       verification_status="validated", recorded_at=UTC_NOW)
        result = self.store.validate_identity_evidence(evidence_id, EvidenceUse.HISTORICAL_TICKER_VALIDITY)
        self.assertEqual(result.failure, EvidenceEligibilityFailure.LOCATOR_MISSING)

    def test_complete_chain_is_retrievable_and_identity_eligible(self) -> None:
        imported = self._import()
        locator_id = self.store.create_locator(imported.document_version_id, page_number=1,
                                               paragraph="Ticker change notice", quote="ticker changed", recorded_at=UTC_NOW)
        evidence_id = self.store.create_evidence_item(imported.document_version_id, locator_id=locator_id,
                                                       evidence_type="ticker_symbol", supporting_text="ticker changed",
                                                       extraction_method="manual", extraction_confidence=1.0,
                                                       verification_status="validated", recorded_at=UTC_NOW)
        citation_id = self.store.create_citation(evidence_id, source_url="https://official.example/notice",
                                                 authority_metadata={"tier": "official_exchange"}, recorded_at=UTC_NOW)
        chain = self.store.load_evidence_chain(evidence_id)
        self.assertEqual(chain.citation_id, citation_id)
        self.assertTrue(self.store.validate_identity_evidence(evidence_id, EvidenceUse.HISTORICAL_TICKER_VALIDITY).eligible)

    def test_ticker_evidence_cannot_silently_qualify_as_series_ownership(self) -> None:
        imported = self._import()
        locator = self.store.create_locator(imported.document_version_id, page_number=1, quote="ticker changed", recorded_at=UTC_NOW)
        evidence = self.store.create_evidence_item(imported.document_version_id, locator_id=locator, evidence_type="ticker_symbol",
            supporting_text="ticker changed", extraction_method="manual", extraction_confidence=1.0,
            verification_status="validated", recorded_at=UTC_NOW)
        self.store.create_citation(evidence, source_url="https://official.example/notice", authority_metadata={}, recorded_at=UTC_NOW)
        result = self.store.validate_identity_evidence(evidence, EvidenceUse.SERIES_OWNERSHIP)
        self.assertFalse(result.eligible)
        self.assertEqual(result.failure, EvidenceEligibilityFailure.ASSERTION_TYPE_UNSUPPORTED)

    def test_tier_four_evidence_is_categorically_ineligible(self) -> None:
        supplied = self.root / "secondary.txt"
        supplied.write_text("secondary")
        imported = self.store.import_evidence_document(supplied, source_url="https://news.example/x", source_name="News",
            source_authority=SourceAuthorityTier.INDEPENDENT_SECONDARY, retrieved_at=UTC_NOW, document_type="news")
        locator = self.store.create_locator(imported.document_version_id, page_number=1, quote="secondary", recorded_at=UTC_NOW)
        evidence = self.store.create_evidence_item(imported.document_version_id, locator_id=locator, evidence_type="identity",
            supporting_text="secondary", extraction_method="manual", extraction_confidence=1.0, verification_status="validated", recorded_at=UTC_NOW)
        self.store.create_citation(evidence, source_url="https://news.example/x", authority_metadata={}, recorded_at=UTC_NOW)
        self.assertEqual(self.store.validate_identity_evidence(evidence, EvidenceUse.HISTORICAL_TICKER_VALIDITY).failure,
                         EvidenceEligibilityFailure.SOURCE_AUTHORITY_INSUFFICIENT)

    def test_synthetic_evidence_is_categorically_ineligible(self) -> None:
        supplied = self.root / "synthetic.txt"
        supplied.write_text("synthetic")
        imported = self.store.import_evidence_document(supplied, source_url="synthetic://fixture", source_name="Fixture",
            source_authority=SourceAuthorityTier.SYNTHETIC, is_synthetic=True, retrieved_at=UTC_NOW, document_type="fixture")
        locator = self.store.create_locator(imported.document_version_id, page_number=1, quote="synthetic", recorded_at=UTC_NOW)
        evidence = self.store.create_evidence_item(imported.document_version_id, locator_id=locator, evidence_type="identity",
            supporting_text="synthetic", extraction_method="manual", extraction_confidence=1.0, verification_status="validated", recorded_at=UTC_NOW)
        self.store.create_citation(evidence, source_url="synthetic://fixture", authority_metadata={}, recorded_at=UTC_NOW)
        self.assertEqual(self.store.validate_identity_evidence(evidence, EvidenceUse.HISTORICAL_TICKER_VALIDITY).failure,
                         EvidenceEligibilityFailure.SYNTHETIC_SOURCE)

    def test_identity_tables_are_unchanged_by_evidence_persistence(self) -> None:
        self.con.executescript("CREATE TABLE instrument_listings(instrument_id TEXT PRIMARY KEY); CREATE TABLE identifier_aliases(alias_id TEXT PRIMARY KEY); CREATE TABLE legacy_identity_mappings(mapping_id TEXT PRIMARY KEY);")
        before = tuple(self.con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("instrument_listings", "identifier_aliases", "legacy_identity_mappings"))
        self._import()
        after = tuple(self.con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("instrument_listings", "identifier_aliases", "legacy_identity_mappings"))
        self.assertEqual(before, after)

    def test_retained_access_and_fbn_pdfs_can_form_a_complete_fixture_chain(self) -> None:
        archive = Path(__file__).resolve().parents[2] / "data" / "archive" / "xissuer_docs"
        retained = [
            (archive / "15197_34667_ACCESS_BANK_PLC_SCHEME_OF_ARRANGEMENT_BETWEEN_ACCESS_.pdf",
             "236badfaba26292d0dda457cd80eead15f713e6097122918049e0608bc786b79"),
            (archive / "25784_43129_FBN_HOLDINGS_PLC-FIRST_HOLDCO_PLC_-_CHANGE_OF_NAME_NOTIFICATION_CORPORATE_ACTIONS_FEBRUARY_2025.pdf",
             "c68d19788314631086c79afb70fee2db1bb69fbbab71b4f493b2f34341b6525f"),
        ]
        for path, expected_hash in retained:
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)
            imported = self.store.import_evidence_document(path, source_url=f"file-fixture:{path.name}",
                source_name="Issuer primary fixture", source_authority=SourceAuthorityTier.ISSUER_PRIMARY,
                retrieved_at=UTC_NOW, document_type="issuer_notice")
            locator = self.store.create_locator(imported.document_version_id, page_number=1, quote="issuer notice", recorded_at=UTC_NOW)
            evidence = self.store.create_evidence_item(imported.document_version_id, locator_id=locator, evidence_type="same_security_continuity",
                supporting_text="issuer notice", extraction_method="deterministic_pdf_text", extraction_confidence=1.0,
                verification_status="validated", recorded_at=UTC_NOW)
            self.store.create_citation(evidence, source_url=f"file-fixture:{path.name}", authority_metadata={"tier": "issuer_primary"}, recorded_at=UTC_NOW)
            self.assertTrue(self.store.validate_identity_evidence(evidence, EvidenceUse.INSTRUMENT_CONTINUITY).eligible)

    def test_tier_one_manual_import_manifests_are_explicitly_unimported(self) -> None:
        root = Path(__file__).resolve().parents[2] / "fixtures" / "frozen" / "historical_identity_evidence_bridge"
        expected = {"FO_ARDOVA", "FBNH_FIRSTHOLDCO", "ACCESS_ACCESSCORP", "GUARANTY_GTCO"}
        manifests = {path.stem.replace("_ngx_manual_import", ""): json.loads(path.read_text(encoding="utf-8"))
                     for path in root.glob("*_ngx_manual_import.json")}
        self.assertEqual(set(manifests), expected)
        for manifest in manifests.values():
            self.assertFalse(manifest["canonical_mutation"])
            self.assertEqual(manifest["import_status"], "not_imported")
            self.assertEqual(manifest["acquisition_mode"], "manual_operator_import")
        batch = json.loads((root / "batch_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(batch["h024_outcome_access"], "none")
        for filename, expected_hash in batch["manual_import_manifests"].items():
            self.assertEqual(hashlib.sha256((root / filename).read_bytes()).hexdigest(), expected_hash)

    def test_tier_one_qualification_package_preserves_identity_isolation(self) -> None:
        root = Path(__file__).resolve().parents[2] / "fixtures" / "frozen" / "historical_identity_evidence_qualification_batch1"
        manifest = json.loads((root / "evidence_chain_manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["canonical_identity_mutation"])
        self.assertEqual(manifest["h024_outcome_access"], "none")
        self.assertTrue(all(delta == 0 for delta in manifest["identity_table_deltas"].values()))
        for filename in ("FO_ARDOVA_evidence_qualification.json", "FBNH_FIRSTHOLDCO_evidence_qualification.json"):
            qualification = json.loads((root / filename).read_text(encoding="utf-8"))
            self.assertFalse(qualification["canonical_identity_mutation"])
            self.assertFalse(qualification["reconciliation_design_ready"])


if __name__ == "__main__":
    unittest.main()
