"""Batch 2 keeps evidence retention, source discovery, and canonical evidence distinct."""
from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import SourceEndpoint, TemporalPrecision, TemporalValue
from ngxrot.identity.evidence_retention import (
    RetentionStatus,
    archive_retrieved_artifact,
    assess_retention,
    record_download_attempt,
)


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "fixtures" / "frozen" / "historical_identity_phase3_batch2"


class HistoricalIdentityPhase3Batch2Tests(unittest.TestCase):
    def _artifact(self, name: str) -> dict:
        path = OUT / name
        self.assertTrue(path.exists(), "run scripts/build_historical_identity_phase3_batch2.py")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_url_only_source_is_not_evidence_grade(self) -> None:
        status = assess_retention(
            source_discovered=True, source_accessible_in_browser=True,
            source_download_blocked_in_environment=True,
        )
        self.assertEqual(status, RetentionStatus.RETRIEVAL_FAILED)
        self.assertNotEqual(status, RetentionStatus.EVIDENCE_GRADE)

    def test_download_failure_is_distinct_from_source_absence(self) -> None:
        absent = assess_retention(source_discovered=False)
        failed = assess_retention(source_discovered=True, source_download_blocked_in_environment=True)
        self.assertEqual(absent, RetentionStatus.DISCOVERED_ONLY)
        self.assertEqual(failed, RetentionStatus.RETRIEVAL_FAILED)

    def test_archiving_is_content_addressed_and_does_not_mutate_source(self) -> None:
        raw = b"%PDF-fund-alpha-retention-test\n"
        original_hash = hashlib.sha256(raw).hexdigest()
        endpoint = SourceEndpoint(canonical_uri="https://example.test/notice.pdf", retention_policy="permitted")
        timestamp = TemporalValue(datetime(2026, 8, 31, tzinfo=timezone.utc), TemporalPrecision.SECOND)
        root = ROOT / ".test-runtime" / "identity_retention_archive"
        root.mkdir(parents=True, exist_ok=True)
        artifact_a = archive_retrieved_artifact(raw, root=root, endpoint=endpoint, retrieved_at=timestamp, recorded_at=timestamp)
        artifact_b = archive_retrieved_artifact(raw, root=root, endpoint=endpoint, retrieved_at=timestamp, recorded_at=timestamp)
        self.assertEqual(artifact_a.sha256, original_hash)
        self.assertEqual(artifact_a.storage_uri, artifact_b.storage_uri)
        self.assertEqual((root / original_hash[:2] / original_hash).read_bytes(), raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), original_hash)

    def test_download_attempt_cannot_claim_retrieval_without_bytes(self) -> None:
        attempt = record_download_attempt(
            source_url="https://example.test/notice.pdf", retrieved_at=None,
            error="ConnectionRefusedError",
        )
        self.assertEqual(attempt.status, RetentionStatus.RETRIEVAL_FAILED)
        self.assertIsNone(attempt.artifact_sha256)

    def test_fo_review_requires_primary_evidence_not_series_handoff(self) -> None:
        review = self._artifact("FO_ARDOVA_review.json")
        self.assertEqual(review["issuer_continuity"], "same")
        self.assertEqual(review["security_continuity"], "same_security")
        self.assertEqual(review["recommended_canonical_treatment"], "future_forward_reconciliation_candidate")
        self.assertNotIn("valid_from", review["observed_handoff_bounds"])
        self.assertFalse(review["canonical_mutation"])

    def test_batch2_retention_never_creates_live_evidence_or_aliases(self) -> None:
        manifest = self._artifact("batch_manifest.json")
        self.assertFalse(manifest["canonical_mutation"])
        self.assertEqual(manifest["live_identity_mutation"], "none")
        self.assertEqual(manifest["h024_outcome_access"], "none")

    def test_review_hashes_are_frozen(self) -> None:
        manifest = self._artifact("batch_manifest.json")
        for filename, expected in manifest["review_artifact_hashes"].items():
            self.assertEqual(hashlib.sha256((OUT / filename).read_bytes()).hexdigest(), expected)

    def test_case_normalization_does_not_establish_economic_identity(self) -> None:
        retention = self._artifact("evidence_retention_status.json")
        self.assertEqual(retention["url_citation_only_policy"], "not_evidence_grade")
        self.assertEqual(retention["canonical_ingestion_policy"], "not_executed_in_batch2")


if __name__ == "__main__":
    unittest.main()
