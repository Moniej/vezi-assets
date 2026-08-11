"""Decision Intelligence Phase 17: Research Question Engine.

Answers a fixed set of structured research questions purely by inspecting
a `company_intelligence_bundle.CompanyIntelligenceBundle` (Phase 15) --
no new data source, no LLM call, no free-text generation beyond templated
assembly of already-governed fields. Every `Answer.evidence` entry is a
real citation (a `source` string from an underlying `DetectedChange`,
`DataPoint`, or thesis field); `Answer.is_inference=True` marks the
handful of answers that combine multiple facts into a judgment (e.g.
"strongest positive development" = a ranking among real facts, an
interpretation) versus a bare fact restatement (`is_inference=False`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ngxrot.fre.company_intelligence_bundle import CompanyIntelligenceBundle

_IMPROVING = ("improved", "new")
_WORSENING = ("worsened",)


@dataclass
class Answer:
    question: str
    answer: str
    evidence: list[str] = field(default_factory=list)
    is_inference: bool = False


def what_changed_materially(bundle: CompanyIntelligenceBundle) -> Answer:
    material = [a for a in bundle.ranked_changes if a.level in ("HIGH", "CRITICAL")]
    if not material:
        return Answer("What changed materially?",
                      "No HIGH or CRITICAL materiality changes detected between the two snapshots.",
                      is_inference=False)
    return Answer(
        "What changed materially?",
        "; ".join(f"[{a.level}] {a.change.description}" for a in material),
        evidence=[a.change.source for a in material], is_inference=False,
    )


def strongest_positive_developments(bundle: CompanyIntelligenceBundle) -> Answer:
    positives = [a for a in bundle.ranked_changes if a.change.direction in _IMPROVING]
    if not positives:
        return Answer("What are the strongest positive developments?",
                      "No positive-direction changes detected.", is_inference=True)
    top = positives[:3]
    return Answer(
        "What are the strongest positive developments?",
        "; ".join(f"[{a.level}] {a.change.description}" for a in top),
        evidence=[a.change.source for a in top], is_inference=True,
    )


def strongest_negative_developments(bundle: CompanyIntelligenceBundle) -> Answer:
    negatives = [a for a in bundle.ranked_changes if a.change.direction in _WORSENING]
    if not negatives:
        return Answer("What are the strongest negative developments?",
                      "No negative-direction changes detected.", is_inference=True)
    top = negatives[:3]
    return Answer(
        "What are the strongest negative developments?",
        "; ".join(f"[{a.level}] {a.change.description}" for a in top),
        evidence=[a.change.source for a in top], is_inference=True,
    )


def weak_evidence_claims(bundle: CompanyIntelligenceBundle) -> Answer:
    weak = [a for a in bundle.ranked_changes if a.change.confidence == "low"]
    if not weak:
        return Answer("Which claims have weak evidence?",
                      "No changes were flagged low-confidence (STALE inputs) in this comparison.",
                      is_inference=False)
    return Answer(
        "Which claims have weak evidence?",
        "; ".join(f"{a.change.description} (confidence=low: {a.reasons[-1] if a.reasons else ''})"
                 for a in weak),
        evidence=[a.change.source for a in weak], is_inference=False,
    )


def missing_information(bundle: CompanyIntelligenceBundle) -> Answer:
    unknown_econ = [name for name, dp in bundle.economic_profile.fields.items() if dp.status == "UNKNOWN"]
    missing_thesis = list(bundle.thesis.missing_evidence) if bundle.thesis and bundle.thesis.missing_evidence else []
    parts = []
    if unknown_econ:
        parts.append(f"Company-context fields with no evidence: {', '.join(unknown_econ)}")
    if missing_thesis:
        parts.append(f"Thesis-level missing evidence: {'; '.join(missing_thesis)}")
    if not parts:
        return Answer("What information is missing?", "No missing-information gaps recorded.",
                      is_inference=False)
    return Answer("What information is missing?", " | ".join(parts),
                  evidence=[dp.source for name, dp in bundle.economic_profile.fields.items()
                            if dp.status == "UNKNOWN"], is_inference=False)


def contradicts_current_thesis(bundle: CompanyIntelligenceBundle) -> Answer:
    if bundle.thesis and bundle.thesis.contradiction_note:
        return Answer("What contradicts the current thesis?", bundle.thesis.contradiction_note,
                      evidence=["company_thesis.CompanyThesis.contradiction_note"], is_inference=False)
    return Answer("What contradicts the current thesis?",
                  "No active contradiction recorded in the current thesis.", is_inference=False)


def developments_requiring_monitoring(bundle: CompanyIntelligenceBundle) -> Answer:
    medium_plus = [a for a in bundle.ranked_changes if a.level in ("MEDIUM", "HIGH", "CRITICAL")]
    if not medium_plus:
        return Answer("What developments require monitoring?",
                      "No MEDIUM-or-higher materiality changes detected.", is_inference=True)
    return Answer(
        "What developments require monitoring?",
        "; ".join(f"[{a.level}] {a.change.description}" for a in medium_plus),
        evidence=[a.change.source for a in medium_plus], is_inference=True,
    )


def changed_since(bundle_current: CompanyIntelligenceBundle,
                   bundle_previous_snapshot: CompanyIntelligenceBundle) -> Answer:
    """Compares two full bundles built at different `as_of_date`s (i.e. two
    successive research runs) -- NOT the same as `what_changed_materially`,
    which compares within ONE bundle's own prior_date/as_of_date window.
    Both bundles must be for the same ticker."""
    if bundle_current.ticker != bundle_previous_snapshot.ticker:
        raise ValueError("changed_since() compares two snapshots of the SAME ticker only")
    prev_descs = {a.change.description for a in bundle_previous_snapshot.ranked_changes}
    new_only = [a for a in bundle_current.ranked_changes if a.change.description not in prev_descs]
    if not new_only:
        return Answer(f"What changed since the previous research snapshot "
                      f"({bundle_previous_snapshot.as_of_date})?",
                      "No new changes since the previous snapshot.", is_inference=False)
    return Answer(
        f"What changed since the previous research snapshot ({bundle_previous_snapshot.as_of_date})?",
        "; ".join(f"[{a.level}] {a.change.description}" for a in new_only),
        evidence=[a.change.source for a in new_only], is_inference=False,
    )


ALL_QUESTIONS = {
    "what_changed_materially": what_changed_materially,
    "strongest_positive_developments": strongest_positive_developments,
    "strongest_negative_developments": strongest_negative_developments,
    "weak_evidence_claims": weak_evidence_claims,
    "missing_information": missing_information,
    "contradicts_current_thesis": contradicts_current_thesis,
    "developments_requiring_monitoring": developments_requiring_monitoring,
}


def answer_all(bundle: CompanyIntelligenceBundle) -> list[Answer]:
    return [fn(bundle) for fn in ALL_QUESTIONS.values()]
