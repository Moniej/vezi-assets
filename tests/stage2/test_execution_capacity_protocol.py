"""Pre-result consistency checks for the immutable Execution & Capacity v1 protocol."""
from __future__ import annotations

import hashlib
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "execution_capacity_v1.toml"
PROTOCOL = ROOT / "docs" / "research_protocols" / "EXECUTION_CAPACITY_STUDY_V1_H011_H013.md"
MANIFEST = ROOT / "fixtures" / "frozen" / "execution_capacity_v1" / "protocol_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExecutionCapacityProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        self.protocol = PROTOCOL.read_text(encoding="utf-8")

    def test_protocol_and_config_freeze_identical_impact_scale(self) -> None:
        impact = self.cfg["impact"]
        self.assertEqual(impact["impact_sigma_daily_definition"], "sigma20_annualized / sqrt(252)")
        self.assertEqual(impact["formula"], "k * impact_sigma_daily * sqrt(participation)")
        self.assertEqual(impact["cap_per_fill"], 0.05)
        self.assertIn("impact_sigma_daily = sigma20_annualized / sqrt(252)", self.protocol)
        self.assertIn("impact_applied = min(impact_raw, 0.05)", self.protocol)

    def test_protocol_and_config_freeze_cash_priority_and_spread_semantics(self) -> None:
        execution = self.cfg["execution"]
        impact = self.cfg["impact"]
        self.assertTrue(execution["sell_orders_before_buy_orders"])
        self.assertFalse(execution["allow_negative_cash"])
        self.assertFalse(execution["allow_leverage"])
        self.assertEqual(execution["buy_cash_allocation"], "pro_rata_eligible_desired_fill_notionals")
        self.assertEqual(impact["one_way_spread_semantics"], "penalty_relative_to_observed_execution_session_close")
        self.assertTrue(impact["explicit_fees_accounted_separately"])
        self.assertIn("Eligible sells are processed before buys.", self.protocol)
        self.assertIn("allocated pro-rata by eligible desired fill notional", self.protocol)

    def test_protocol_and_config_freeze_acceptance_and_aggregation(self) -> None:
        acceptance = self.cfg["acceptance"]
        concentration = self.cfg["concentration"]
        duration = self.cfg["duration"]
        self.assertEqual(acceptance["alpha_capture_nonpositive_denominator_status"], "FAIL")
        self.assertEqual(acceptance["alpha_capture_missing_data_status"], "INSUFFICIENT_DATA")
        self.assertEqual(acceptance["pass_hhi_multiple_max"], 1.5)
        self.assertEqual(acceptance["marginal_hhi_multiple_max"], 2.0)
        self.assertTrue(concentration["cash_excluded_from_equity_hhi"])
        self.assertTrue(duration["headline_median_includes_all_submitted_orders"])
        self.assertIn("classification is `FAIL`", self.protocol)
        self.assertIn("classification is `INSUFFICIENT_DATA`", self.protocol)
        self.assertIn("median daily equity HHI", self.protocol)
        self.assertIn("including zero-fill expiries", self.protocol)

    def test_pre_result_manifest_binds_protocol_config_and_fee_schedule(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["artifact_type"], "pre_result_protocol_freeze")
        self.assertEqual(manifest["capacity_result_artifacts_before_freeze"], [])
        self.assertEqual(manifest["config"]["sha256"], sha256(CONFIG))
        self.assertEqual(manifest["protocol"]["sha256"], sha256(PROTOCOL))
        fee = manifest["frozen_inputs"]["explicit_fee_schedule"]
        self.assertEqual(fee["row_count"], 7)
        self.assertEqual(len(fee["deterministic_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
