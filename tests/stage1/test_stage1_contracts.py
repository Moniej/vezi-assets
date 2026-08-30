"""Stage 1 additive-contract and invariant gate.

This suite is deliberately independent of the live Fund Alpha databases and
of existing FRE, Alpha, Research OS, and Portfolio entry points.
"""

from __future__ import annotations

import sqlite3
import unittest
from datetime import date, datetime, timezone

from ngxrot.canonical.contracts import (
    AvailabilityPolicy,
    EvidenceItem,
    EvidenceStatus,
    FactAssertion,
    RecordStatus,
    Source,
    SourceAuthorityTier,
    TemporalQueryContext,
    TemporalValue,
    ValidationStatus,
)
from ngxrot.canonical.invariants import (
    assert_alpha_bridge_allowed,
    assert_evidence_grade_eligible,
    assert_formal_verdict_eligible,
    assert_relationship_visible,
    assert_research_bridge_allowed,
    deterministic_graph_projection,
    fact_visible,
    implication_eligible,
    is_effective,
    source_document_identity_is_valid,
    validate_cross_database_reference,
)
from ngxrot.migrations.framework import Migration, MigrationRunner, SchemaAssertionError


UTC = timezone.utc


def at(value: str) -> TemporalValue:
    return TemporalValue(datetime.fromisoformat(value).replace(tzinfo=UTC))


class Stage1ContractTests(unittest.TestCase):
    def test_new_ids_are_uuidv7(self) -> None:
        fact = FactAssertion(subject_id="company-1", predicate="revenue", value=1)
        self.assertEqual(fact.fact_id.version, 7)

    def test_publication_and_strict_vintage_visibility(self) -> None:
        source = Source(name="NGX", authority_tier=SourceAuthorityTier.OFFICIAL_EXCHANGE)
        fact = FactAssertion(
            subject_id="company-1", predicate="revenue", value=1,
            source_id=source.source_id,
            published_at=at("2026-03-15T00:00:00"),
            recorded_at=at("2026-03-17T00:00:00"),
        )
        early = TemporalQueryContext(
            decision_time=at("2026-03-14T00:00:00"),
            system_vintage=at("2026-03-20T00:00:00"),
        )
        strict = TemporalQueryContext(
            decision_time=at("2026-03-16T00:00:00"),
            system_vintage=at("2026-03-16T00:00:00"),
        )
        self.assertFalse(fact_visible(fact, early))
        self.assertFalse(fact_visible(fact, strict))

    def test_verified_reconstruction_requires_publication_verification(self) -> None:
        fact = FactAssertion(
            subject_id="company-1", predicate="revenue", value=1,
            published_at=at("2026-03-15T00:00:00"),
            recorded_at=at("2026-03-17T00:00:00"),
        )
        context = TemporalQueryContext(
            decision_time=at("2026-03-16T00:00:00"),
            system_vintage=at("2026-03-20T00:00:00"),
            availability_policy=AvailabilityPolicy.VERIFIED_HISTORICAL_RECONSTRUCTION,
        )
        self.assertFalse(fact_visible(fact, context))
        fact.publication_time_verification = "official_exchange_timestamp"
        self.assertTrue(fact_visible(fact, context))

    def test_fact_lifecycle_dimensions_are_independent(self) -> None:
        fact = FactAssertion(
            subject_id="company-1", predicate="revenue", value=1,
            validation_status=ValidationStatus.VALIDATED,
            evidence_status=EvidenceStatus.EVIDENCE_GRADE,
            record_status=RecordStatus.SUPERSEDED,
        )
        self.assertEqual(fact.record_status, RecordStatus.SUPERSEDED)
        self.assertEqual(fact.evidence_status, EvidenceStatus.EVIDENCE_GRADE)

    def test_evidence_grade_requires_grounded_evidence(self) -> None:
        fact = FactAssertion(subject_id="company-1", predicate="revenue", value=1)
        self.assertFalse(assert_evidence_grade_eligible(fact, []))
        evidence = EvidenceItem(source_id="source-1", locator="page:1", grounded=True)
        self.assertTrue(assert_evidence_grade_eligible(fact, [evidence]))

    def test_synthetic_cannot_support_formal_verdict(self) -> None:
        synthetic = Source(name="fixture", is_synthetic=True)
        self.assertFalse(assert_formal_verdict_eligible([synthetic]))

    def test_relationship_missing_recorded_at_is_not_strictly_visible(self) -> None:
        relation = type("Relation", (), {"published_at": None, "recorded_at": None})()
        ctx = TemporalQueryContext(decision_time=at("2026-03-16T00:00:00"), system_vintage=at("2026-03-20T00:00:00"))
        self.assertFalse(assert_relationship_visible(relation, ctx))

    def test_fre_cannot_bypass_alpha_bridge(self) -> None:
        self.assertFalse(assert_alpha_bridge_allowed("fre_implication"))
        self.assertTrue(assert_alpha_bridge_allowed("approved_formal_test_proposal"))

    def test_unknown_publication_timing_is_unavailable(self) -> None:
        fact = FactAssertion(subject_id="company-1", predicate="revenue", value=1, recorded_at=at("2026-03-17T00:00:00"))
        ctx = TemporalQueryContext(decision_time=at("2026-03-20T00:00:00"), system_vintage=at("2026-03-20T00:00:00"))
        self.assertFalse(fact_visible(fact, ctx))

    def test_effective_date_does_not_leak(self) -> None:
        event = type("Event", (), {"effective_time": at("2026-04-01T00:00:00")})()
        ctx = TemporalQueryContext(decision_time=at("2026-03-15T00:00:00"), system_vintage=at("2026-03-15T00:00:00"))
        self.assertFalse(is_effective(event, ctx))

    def test_retracted_and_superseded_records_remain_auditable(self) -> None:
        fact = FactAssertion(subject_id="company-1", predicate="revenue", value=1, record_status=RecordStatus.RETRACTED)
        self.assertEqual(fact.record_status, RecordStatus.RETRACTED)
        fact.record_status = RecordStatus.SUPERSEDED
        self.assertEqual(fact.record_status, RecordStatus.SUPERSEDED)

    def test_graph_is_deterministic_and_projection_only(self) -> None:
        a = type("R", (), {"subject_id": "a", "predicate": "owns", "object_id": "b"})()
        b = type("R", (), {"subject_id": "b", "predicate": "works_for", "object_id": "a"})()
        self.assertEqual(deterministic_graph_projection([a, b]), deterministic_graph_projection([b, a]))

    def test_research_requires_approved_formal_test_proposal(self) -> None:
        self.assertFalse(assert_research_bridge_allowed("research_hypothesis", False))
        self.assertTrue(assert_research_bridge_allowed("research_hypothesis", True))

    def test_failed_critique_blocks_implication(self) -> None:
        self.assertFalse(implication_eligible(self_critique_passed=False))

    def test_coverage_preserves_missingness(self) -> None:
        from ngxrot.canonical.contracts import DataCoverageAssessment
        coverage = DataCoverageAssessment(domain="ownership", availability_status="missing")
        self.assertEqual(coverage.availability_status, "missing")

    def test_unknown_membership_is_not_promoted_to_known(self) -> None:
        membership = FactAssertion(subject_id="index-1", predicate="member", value=None)
        self.assertIsNone(membership.value)

    def test_corporate_action_remains_specialized(self) -> None:
        from ngxrot.canonical.contracts import CorporateAction, EventAssertion
        self.assertNotIsInstance(EventAssertion(event_type="dividend"), CorporateAction)

    def test_source_and_document_ids_are_not_interchangeable(self) -> None:
        self.assertFalse(source_document_identity_is_valid("same", "same"))
        self.assertTrue(source_document_identity_is_valid("source", "document"))

    def test_cross_database_reference_failure_is_visible(self) -> None:
        self.assertFalse(validate_cross_database_reference("missing", {"known"}))


class MigrationFrameworkTests(unittest.TestCase):
    def test_migration_ledger_and_schema_assertion(self) -> None:
        con = sqlite3.connect(":memory:")
        migration = Migration(
            migration_id="20260830_000_pre_consolidation_baseline",
            database_target="ngx",
            expected_pre_version=0,
            expected_post_version=1,
            sql="CREATE TABLE baseline_marker (id INTEGER PRIMARY KEY)",
        )
        runner = MigrationRunner([migration])
        runner.apply_pending(con, database_target="ngx", backup_manifest_verified=True)
        runner.assert_schema(con, database_target="ngx", expected_version=1)
        with self.assertRaises(SchemaAssertionError):
            runner.assert_schema(con, database_target="ngx", expected_version=2)


if __name__ == "__main__":
    unittest.main()
