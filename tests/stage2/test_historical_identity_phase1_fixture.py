"""Phase 1 review artifacts must never be mistaken for verified identity."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class HistoricalIdentityPhase1FixtureTests(unittest.TestCase):
    def test_review_candidates_are_not_assertions_or_evidence_grade(self) -> None:
        candidate_path = ROOT / "fixtures" / "frozen" / "historical_identity_phase1_candidates.json"
        self.assertTrue(candidate_path.exists(), "run scripts/audit_historical_identity_phase1.py to create Phase 1 artifacts")
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["classification"], "review_candidates_not_identity_assertions")
        self.assertTrue(payload["rows"])
        for row in payload["rows"]:
            self.assertEqual(row["verification_status"], "corroborated")
            self.assertIsNone(row["evidence_item_id"])
            self.assertIn("cannot be verified", row["promotion_blocker"])

    def test_current_coverage_and_h024_unlocks_remain_zero_without_evidence(self) -> None:
        report_path = ROOT / "fixtures" / "frozen" / "historical_identity_phase1_coverage_report.json"
        self.assertTrue(report_path.exists(), "run scripts/audit_historical_identity_phase1.py to create Phase 1 artifacts")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["assertion_counts"]["verified"], 0)
        self.assertEqual(report["h024_coverage_simulation"]["instrument_formations_unlocked"], 0)
        self.assertEqual(report["h024_coverage_simulation"]["eligible_observations"], 0)
        priority = report["h024_identity_evidence_priority"]
        self.assertIn("no predictor/outcome values inspected", priority["method"])
        self.assertGreater(len(priority["priority_1"]), 0)
        self.assertEqual(priority["priority_1"], sorted(
            priority["priority_1"],
            key=lambda row: (-row["candidate_instrument_formations"], row["legacy_ticker"]),
        ))
        for values in report["historical_resolution_coverage_by_year"].values():
            self.assertEqual(values["historically_resolvable_verified"], 0)
            self.assertEqual(values["coverage_pct"], 0.0)
