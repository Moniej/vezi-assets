"""Pre-outcome guards for the frozen H-024 dataset builder."""
from __future__ import annotations

import unittest
import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd

from ngxrot.h024_dataset import action_flags, eligibility_reason, predictor_row

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "frozen" / "h024_liquidity_shock_volatility.sqlite"
MANIFEST = ROOT / "fixtures" / "frozen" / "h024_liquidity_shock_volatility_manifest.json"


class H024DatasetTests(unittest.TestCase):
    def test_frozen_package_contains_no_forward_outcome_values(self) -> None:
        self.assertTrue(FIXTURE.exists(), "H-024 frozen dataset is missing")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(manifest["dataset_sha256"], digest)
        self.assertEqual(manifest["outcome_materialization"], "not_materialized")
        with sqlite3.connect(FIXTURE) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(h024_observations)")}
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM h024_observations WHERE eligible_for_primary=1").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM h024_observations WHERE instrument_id IS NOT NULL").fetchone()[0], 0)
        self.assertFalse(any(column.startswith("forward_rv") for column in columns))
    def test_adtv_and_baseline_minimums_are_exact(self) -> None:
        self.assertEqual(eligibility_reason(adtv_valid_count=44, baseline_valid_count=120,
                                            identity_status="resolved"), "insufficient_adtv60")
        self.assertEqual(eligibility_reason(adtv_valid_count=45, baseline_valid_count=119,
                                            identity_status="resolved"), "insufficient_adtv_baseline")
        self.assertIsNone(eligibility_reason(adtv_valid_count=45, baseline_valid_count=120,
                                             identity_status="resolved"))

    def test_staleness_threshold_is_not_optimized(self) -> None:
        self.assertFalse(eligibility_reason(adtv_valid_count=45, baseline_valid_count=120,
                                            identity_status="resolved", zero_return_fraction=.80) == "extreme_staleness")
        self.assertEqual(eligibility_reason(adtv_valid_count=45, baseline_valid_count=120,
                                            identity_status="resolved", zero_return_fraction=.80001), "extreme_staleness")

    def test_predictor_uses_only_rows_through_decision_date(self) -> None:
        dates = pd.bdate_range("2025-01-01", periods=380)
        frame = pd.DataFrame({"trade_date": dates, "value_traded": 1000.0,
                              "close": range(100, 480), "volume": 10.0,
                              "deals": 2.0})
        decision = dates[300]
        first = predictor_row(frame, decision)
        changed = frame.copy()
        changed.loc[changed.trade_date > decision, ["value_traded", "close"]] = [99999999.0, 1.0]
        second = predictor_row(changed, decision)
        self.assertEqual(first["adtv60"], second["adtv60"])
        self.assertEqual(first["liquidity_shock"], second["liquidity_shock"])
        self.assertEqual(first["lagged_rv20"], second["lagged_rv20"])

    def test_known_action_is_flagged_by_window_without_inspecting_outcome(self) -> None:
        decision = pd.Timestamp("2025-01-31")
        flags = action_flags(decision, [pd.Timestamp("2025-02-03")],
                             pd.bdate_range("2025-01-01", "2025-05-01"))
        self.assertTrue(flags["action_in_forward_5d_window"])
        self.assertTrue(flags["action_in_forward_20d_window"])
        self.assertTrue(flags["action_in_forward_60d_window"])

    def test_historically_unresolved_identity_is_excluded(self) -> None:
        self.assertEqual(eligibility_reason(adtv_valid_count=60, baseline_valid_count=200,
                                            identity_status="temporally_unavailable"),
                         "identity_temporally_unavailable")
