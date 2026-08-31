"""Integrity checks for the immutable, non-evidence H-011 comparison fixture."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "frozen" / "h011_liquidity_comparison.sqlite"
MANIFEST = ROOT / "fixtures" / "frozen" / "h011_liquidity_comparison_manifest.json"
AUDIT = ROOT / "fixtures" / "frozen" / "h011_liquidity_mechanism_audit.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class H011LiquidityFixtureTests(unittest.TestCase):
    def test_manifest_binds_the_required_non_evidence_tables(self) -> None:
        self.assertTrue(FIXTURE.exists(), "frozen H-011 fixture is missing")
        self.assertTrue(MANIFEST.exists(), "frozen H-011 manifest is missing")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertTrue(manifest["non_evidence_regression_artifact"])
        self.assertEqual(manifest["evidence_eligibility"], "prohibited")
        self.assertEqual(manifest["classification"], "best_available_frozen_reconstruction")
        self.assertEqual(manifest["fixture_sqlite_sha256"], _sha256(FIXTURE))
        self.assertEqual(manifest["audit_sha256"], _sha256(AUDIT))
        self.assertEqual(manifest["reproduction_comparison"]["formation_count"]["classification"], "exact_match")
        self.assertEqual(manifest["reproduction_comparison"]["capacity_median_ngn"]["classification"], "exact_match")
        self.assertGreater(manifest["formation_count"], 0)
        required = {
            "daily_market_data", "security_identity", "market_cap_panel", "formations", "iru_membership",
            "target_weights", "benchmark_weights", "corporate_action_flags",
            "source_metadata", "modeled_cost_schedule",
        }
        with sqlite3.connect(FIXTURE) as connection:
            actual = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        self.assertTrue(required.issubset(actual))
