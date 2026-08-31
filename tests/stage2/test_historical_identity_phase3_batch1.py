"""Batch 1 evidence reviews are frozen, non-mutating continuity recommendations."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ngxrot.identity.continuity import ContinuityClass, recommend_continuity_treatment


ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "fixtures" / "frozen" / "historical_identity_phase3_batch1"
MANIFEST = REVIEW_DIR / "batch_manifest.json"


class HistoricalIdentityPhase3Batch1Tests(unittest.TestCase):
    def _review(self, filename: str) -> dict:
        path = REVIEW_DIR / filename
        self.assertTrue(path.exists(), "run scripts/build_historical_identity_phase3_batch1.py")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_holdco_restructurings_remain_two_instruments(self) -> None:
        for filename in ("ACCESS_ACCESSCORP_review.json", "GUARANTY_GTCO_review.json"):
            review = self._review(filename)
            self.assertEqual(review["recommended_canonical_treatment"], "retain_two_instruments")
            self.assertNotEqual(review["security_continuity"], "same_security")

    def test_verified_simple_rename_is_only_a_future_reconciliation_candidate(self) -> None:
        review = self._review("FBNH_FIRSTHOLDCO_review.json")
        self.assertEqual(review["issuer_continuity"], "same")
        self.assertEqual(review["security_continuity"], "same_security")
        self.assertEqual(review["ticker_continuity"], "simple_alias_change")
        self.assertEqual(review["recommended_canonical_treatment"], "future_forward_reconciliation_candidate")
        self.assertFalse(review["canonical_mutation"])

    def test_case_normalization_is_not_a_historical_alias_assertion(self) -> None:
        review = self._review("FIRSTHOLDCO_case_normalization_review.json")
        self.assertTrue(review["source_normalization_equivalent"])
        self.assertEqual(review["recommended_canonical_treatment"], "source_normalization_only")
        self.assertFalse(review["historical_alias_assertion_created"])

    def test_observation_handoff_bounds_are_not_validity_bounds(self) -> None:
        review = self._review("ACCESS_ACCESSCORP_review.json")
        bounds = review["observed_handoff_bounds"]
        self.assertEqual(bounds["last_old_symbol_observed"], "2022-03-23")
        self.assertEqual(bounds["first_new_symbol_observed"], "2022-03-28")
        self.assertNotIn("valid_from", bounds)
        self.assertNotIn("valid_to", bounds)

    def test_tier_three_handoff_cannot_promote_same_instrument_continuity(self) -> None:
        result = recommend_continuity_treatment(
            evidence_status="corroborated", event_type="ticker_rename",
        )
        self.assertEqual(result.classification, ContinuityClass.UNRESOLVED)
        self.assertEqual(result.recommended_treatment, "unresolved")

    def test_conflicting_evidence_stays_unresolved(self) -> None:
        result = recommend_continuity_treatment(
            evidence_status="conflicting", event_type="ticker_rename",
        )
        self.assertEqual(result.classification, ContinuityClass.UNRESOLVED)

    def test_manifest_hashes_every_frozen_review_and_declares_no_mutation(self) -> None:
        self.assertTrue(MANIFEST.exists(), "run scripts/build_historical_identity_phase3_batch1.py")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertFalse(manifest["canonical_mutation"])
        for filename, expected_hash in manifest["review_artifact_hashes"].items():
            actual = hashlib.sha256((REVIEW_DIR / filename).read_bytes()).hexdigest()
            self.assertEqual(actual, expected_hash)

    def test_evidence_qualified_coverage_is_reported_as_potential_not_applied(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        impact = manifest["h024_potential_impact"]
        self.assertEqual(impact["canonical_mappings_applied"], 0)
        self.assertEqual(impact["outcome_access"], "none")
        self.assertGreaterEqual(impact["potential_formations_if_future_assertions_approved"], 0)

    def test_live_identity_snapshot_is_unchanged(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["live_identity_mutation"], "none")


if __name__ == "__main__":
    unittest.main()
