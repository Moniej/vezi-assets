"""Canonical training-example schema (DATASET_GENERATION_AND_TRAINING_SPEC.md
§3). One shape for every dataset type — task-specific content lives inside
the generic fields, never as a bespoke per-type schema. This is what keeps
the audit framework (audit.py) and export engine (exporters.py)
dataset-type-agnostic.

Fixed vocabularies below mirror ngxrot.documents.vocab.py's own pattern
(hardcoded, not config-driven — stable, spec-fixed categories, not
something a caller should silently extend).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# The 17 dataset types named in DATASET_GENERATION_AND_TRAINING_SPEC.md §2,
# in the same order as that section's table.
TASK_TYPES = (
    "financial_reasoning", "extraction", "entity_recognition",
    "corporate_actions", "event_understanding", "contradiction_detection",
    "self_critique", "investment_decision_support", "portfolio_reasoning",
    "retrieval", "rag", "citation_grounding", "hallucination_detection",
    "confidence_estimation", "coverage_assessment", "evidence_ranking",
    "knowledge_graph_completion",
)

ACCEPTANCE_STATUSES = {"accepted", "rejected"}

# Structured rejection_reason codes (spec §4.5/§4.3 -- "a short, structured
# code naming exactly why"). Free-text detail can still be appended after a
# colon; the code prefix is what the audit framework groups on.
REJECTION_REASON_CODES = {
    "grounding_failed",              # primary citation's grounding_check != 'passed'
    "contradicts_higher_tier_evidence",  # unresolved contradiction against better evidence
    "below_quality_threshold",       # quality_score below the type's configured floor
    "insufficient_coverage",         # source ticker's CoverageAssessment too thin
    "missing_required_field",        # exporter could not populate a required canonical field
}


@dataclass
class TrainingExample:
    unique_id: str
    task: str
    instruction: str
    context: dict = field(default_factory=dict)
    retrieved_documents: list = field(default_factory=list)
    retrieved_facts: list = field(default_factory=list)
    reasoning_context: dict = field(default_factory=dict)
    expected_output: dict = field(default_factory=dict)
    citations: list = field(default_factory=list)
    evidence_tier: int | None = None
    confidence: float | None = None
    coverage_score: float | None = None
    reasoning_chain: list = field(default_factory=list)
    self_critique: dict | None = None
    contradiction_analysis: dict | None = None
    acceptance_status: str = "accepted"
    rejection_reason: str | None = None
    quality_score: float = 0.0
    source_documents: list = field(default_factory=list)
    # Stamped at write time (registry.py), not construction time -- an
    # example doesn't know its own dataset_version until the exporter
    # commits it to a version.
    dataset_version: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.task not in TASK_TYPES:
            raise ValueError(f"task {self.task!r} not in TASK_TYPES: {TASK_TYPES}")
        if self.acceptance_status not in ACCEPTANCE_STATUSES:
            raise ValueError(f"acceptance_status {self.acceptance_status!r} not in "
                             f"{ACCEPTANCE_STATUSES}")
        if self.acceptance_status == "rejected" and not self.rejection_reason:
            raise ValueError("rejected examples must carry a rejection_reason "
                            "(never silently rejected -- spec §4.3)")
        if self.rejection_reason is not None:
            code = self.rejection_reason.split(":", 1)[0]
            if code not in REJECTION_REASON_CODES:
                raise ValueError(f"rejection_reason code {code!r} not in "
                                f"{REJECTION_REASON_CODES}")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


def make_unique_id(task: str, *source_ids: int) -> str:
    """Deterministic id from the task type + its source row id(s) -- same
    source row always produces the same unique_id across regenerations
    (a precondition for the reproducibility/lineage guarantees in spec §5),
    never a random uuid."""
    suffix = "-".join(str(s) for s in source_ids)
    return f"{task}:{suffix}"
