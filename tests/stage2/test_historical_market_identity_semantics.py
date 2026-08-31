"""The historical-market identity audit must preserve source-symbol semantics."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "fixtures" / "frozen" / "historical_market_identity_semantics_report.json"


class HistoricalMarketIdentitySemanticsTests(unittest.TestCase):
    def test_report_preserves_the_distinction_between_series_ownership_and_aliases(self) -> None:
        self.assertTrue(REPORT.exists(), "run scripts/audit_historical_market_identity_semantics.py")
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertIn("as_traded_historical_symbol", report["symbol_semantics"]["primary_official_pricelist"])
        self.assertTrue(report["market_series_ownership"]["separate_mapping_concept_justified"])
        self.assertIn("must_not_create_identifier_alias", report["market_series_ownership"]["guardrail"])

    def test_report_never_uses_h024_outcomes(self) -> None:
        self.assertTrue(REPORT.exists(), "run scripts/audit_historical_market_identity_semantics.py")
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["outcome_access"], "none")
        self.assertTrue(report["universe_construction"]["official_pricelist_method_1_historical_exchange_universe"])
        self.assertTrue(report["universe_construction"]["investing_backfill_method_2_currentish_filing_universe"])

    def test_raw_symbols_are_not_silently_relabelled_or_promoted_to_aliases(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        rename = report["known_rename_diagnostics"]
        self.assertTrue(rename)
        self.assertTrue(all(row["stored_under_separate_tickers"] for row in rename))
        self.assertTrue(all(not row["fund_alpha_row_relabeling_detected"] for row in rename))
        self.assertEqual(report["entity_relationship_rename_edge_limits"]["missing_evidence_references"],
                         report["entity_relationship_rename_edge_limits"]["edge_count"])

    def test_raw_only_symbols_are_explicitly_retained_as_filtering_diagnostics(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        first_year = report["raw_vs_ingested_by_year"]["2014"]
        self.assertGreater(len(first_year["raw_only_symbols"]), 0)
        self.assertEqual(first_year["ingested_only_symbols"], [])
        self.assertIn("2014", report["raw_to_ingested_lineage_limit"]["mismatch_years"])
        self.assertIn("do not infer", report["raw_to_ingested_lineage_limit"]["conclusion"])
