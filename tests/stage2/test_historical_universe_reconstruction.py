"""Historical source series are not canonical identities or aliases."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from ngxrot.identity.continuity import ContinuityClass, recommend_continuity_treatment


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "fixtures" / "frozen" / "historical_universe_reconstruction_report.json"


class HistoricalUniverseReconstructionTests(unittest.TestCase):
    def _report(self) -> dict:
        self.assertTrue(REPORT.exists(), "run scripts/build_historical_universe_reconstruction.py")
        return json.loads(REPORT.read_text(encoding="utf-8"))

    def test_raw_only_debt_stays_visible_but_is_not_an_equity(self) -> None:
        report = self._report()
        series = {row["published_symbol"]: row for row in report["historical_market_series"]}
        self.assertEqual(series["FG102016S1"]["security_type"], "debt_instrument")
        self.assertEqual(series["FG102016S1"]["ingestion_status"], "not_ingested")
        self.assertFalse(series["FG102016S1"]["ordinary_equity_candidate"])

    def test_ordinary_historical_series_absent_from_current_security_is_not_dropped(self) -> None:
        report = self._report()
        self.assertGreaterEqual(report["historical_only_equity_candidates"]["count"], 0)
        self.assertIn("not automatically created", report["historical_only_equity_candidates"]["policy"])

    def test_known_transition_without_evidence_is_not_an_alias_merge(self) -> None:
        report = self._report()
        cases = {(row["predecessor_source_series"], row["successor_source_series"]): row
                 for row in report["continuity_review"]}
        gtco = cases[("GUARANTY", "GTCO")]
        self.assertEqual(gtco["classification"], "issuer_reorganization_uncertain")
        self.assertEqual(gtco["recommended_canonical_treatment"], "unresolved")
        self.assertEqual(gtco["evidence_status"], "insufficient_for_canonical_continuity")

    def test_series_ownership_is_distinct_from_alias(self) -> None:
        report = self._report()
        model = report["market_series_identity_mapping_contract"]
        self.assertTrue(model["distinct_from_identifier_alias"])
        self.assertIn("must_not_create_alias", model["guardrail"])

    def test_no_live_identity_mutation(self) -> None:
        report = self._report()
        self.assertEqual(report["live_mutation"], "none")

    def test_source_case_variants_remain_review_items_not_identity_merges(self) -> None:
        report = self._report()
        variants = report["source_symbol_normalization_candidates"]
        self.assertGreaterEqual(variants["count"], 1)
        self.assertIn("must not trigger alias", variants["policy"])

    def test_phase3_h024_priority_is_observation_count_only_and_deterministic(self) -> None:
        queue = json.loads((ROOT / "fixtures" / "frozen" / "historical_universe_phase3_evidence_queue.json").read_text(encoding="utf-8"))["items"]
        priority_two = [row for row in queue if row["priority"] == 2]
        self.assertTrue(priority_two)
        self.assertTrue(all(row["candidate_formations_priority_only"] > 0 for row in priority_two))
        self.assertEqual(priority_two, sorted(priority_two, key=lambda row: (-row["candidate_formations_priority_only"], row["transition"])))

    def test_evidence_supported_simple_rename_can_recommend_bounded_aliases(self) -> None:
        result = recommend_continuity_treatment(
            evidence_status="verified", event_type="ticker_rename",
        )
        self.assertEqual(result.classification, ContinuityClass.SAME_INSTRUMENT_ALIAS_CHANGE)
        self.assertEqual(result.recommended_treatment, "one_instrument_bounded_aliases")

    def test_security_replacement_and_holding_company_do_not_become_aliases(self) -> None:
        replacement = recommend_continuity_treatment(
            evidence_status="verified", event_type="security_replacement",
        )
        holding_company = recommend_continuity_treatment(
            evidence_status="verified", event_type="holding_company_reorganization",
        )
        self.assertEqual(replacement.classification, ContinuityClass.SUCCESSOR_REPLACEMENT_INSTRUMENT)
        self.assertEqual(replacement.recommended_treatment, "two_instruments_successor_relationship")
        self.assertEqual(holding_company.classification, ContinuityClass.ISSUER_REORGANIZATION_UNCERTAIN)
        self.assertEqual(holding_company.recommended_treatment, "unresolved")
