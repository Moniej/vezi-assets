"""Pure policy gates for Stage 1 invariant tests; not wired into consumers yet."""

from __future__ import annotations

from .contracts import AvailabilityPolicy, EvidenceItem, FactAssertion, Source, TemporalQueryContext


def _publicly_available(record, context: TemporalQueryContext) -> bool:
    published_at = getattr(record, "published_at", None)
    if published_at is None or not published_at.no_later_than(context.decision_time):
        return False
    if context.availability_policy is AvailabilityPolicy.VERIFIED_HISTORICAL_RECONSTRUCTION:
        return bool(getattr(record, "publication_time_verification", None))
    return True


def fact_visible(fact: FactAssertion, context: TemporalQueryContext) -> bool:
    if not _publicly_available(fact, context):
        return False
    if context.availability_policy is AvailabilityPolicy.STRICT_SYSTEM_VINTAGE:
        return fact.recorded_at is not None and fact.recorded_at.no_later_than(context.system_vintage)
    return fact.recorded_at is None or fact.recorded_at.no_later_than(context.system_vintage)


def assert_evidence_grade_eligible(fact: FactAssertion, evidence: list[EvidenceItem]) -> bool:
    return bool(evidence) and all(item.grounded and item.grounding_result != "failed" for item in evidence)


def assert_formal_verdict_eligible(sources: list[Source]) -> bool:
    return bool(sources) and not any(source.is_synthetic for source in sources)


def assert_relationship_visible(relation, context: TemporalQueryContext) -> bool:
    if context.availability_policy is AvailabilityPolicy.STRICT_SYSTEM_VINTAGE:
        return relation.recorded_at is not None and relation.recorded_at.no_later_than(context.system_vintage)
    return _publicly_available(relation, context)


def assert_alpha_bridge_allowed(origin: str) -> bool:
    return origin == "approved_formal_test_proposal"


def is_effective(event, context: TemporalQueryContext) -> bool:
    """An announced action is never treated as effective before its effective time."""
    effective_time = getattr(event, "effective_time", None)
    return effective_time is not None and effective_time.no_later_than(context.decision_time)


def deterministic_graph_projection(assertions: list) -> tuple[tuple[str, str, str], ...]:
    """A rebuildable, sorted semantic projection; it is not a persistence store."""
    return tuple(sorted((str(item.subject_id), item.predicate, str(item.object_id)) for item in assertions))


def assert_research_bridge_allowed(origin: str, formal_test_proposal_approved: bool) -> bool:
    return origin == "research_hypothesis" and formal_test_proposal_approved


def implication_eligible(*, self_critique_passed: bool) -> bool:
    return self_critique_passed


def validate_cross_database_reference(reference: str, known_immutable_ids: set[str]) -> bool:
    return reference in known_immutable_ids


def source_document_identity_is_valid(source_id, document_version_id) -> bool:
    return source_id is not None and document_version_id is not None and source_id != document_version_id
