"""Teacher-generation acceptance pipeline (DATASET_GENERATION_AND_TRAINING_
SPEC.md §4). The teacher model proposes; it never gets to decide it is
correct. Every stage before Quality Scoring reuses an existing,
already-tested module directly -- nothing here reimplements grounding,
evidence ranking, or self-critique; it only reads their already-computed
results and applies a deterministic, disclosed formula on top.

Hard exclusions run BEFORE any weighting (mirrors extract.py's own
"grounding failure forces confidence to exactly 0.0, not a low-weighted
average" rule) -- a quality_score of 0.0 with a named rejection_reason,
never a merely-low score for these two cases.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ngxrot.documents import evidence_ranking

PKG_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PKG_ROOT / "configs" / "dataset_quality_weights.toml"

# Ad hoc, disclosed, owner-adjustable weights (same status as vocab.py's
# CONFIDENCE_DISCOUNT_PER_CONCERN) -- an owner call once real acceptance
# rates are observed across more data, not a validated statistical fit.
# Kept here as the code default; configs/dataset_quality_weights.toml
# (loaded by exporters.py) can override without a code change.
DEFAULT_WEIGHTS = {
    "self_critique_severity": 0.35,
    "evidence_tier": 0.30,
    "coverage_score": 0.20,
    "citation_integrity": 0.15,
}

# Tier 1 (best) -> 1.0 ... tier 4 (worst) -> 0.25, matching
# evidence_ranking.EVIDENCE_TRUST_TIERS' 1=best/4=worst convention.
_TIER_SCORE = {1: 1.00, 2: 0.75, 3: 0.50, 4: 0.25}
_FINDING_SCORE = {"pass": 1.0, "concern": 0.6, "fail": 0.0}

# Per-task-type acceptance thresholds -- deliberately different bars for
# different purposes (spec §4.5): a Self-Critique NEGATIVE example is
# valuable precisely because it failed, so it's accepted at a much lower
# quality_score than a Financial-Reasoning POSITIVE example would need.
DEFAULT_ACCEPTANCE_THRESHOLDS = {
    "financial_reasoning": 0.55,
    "extraction": 0.50,
    "corporate_actions": 0.50,
    "citation_grounding": 0.40,
    "coverage_assessment": 0.0,     # descriptive dataset, not a claim -- always accepted
                                    # once a hard exclusion doesn't apply
    "evidence_ranking": 0.0,        # same -- descriptive
    "self_critique": 0.0,           # BOTH pass and fail examples are wanted; gated by
                                    # hard exclusions only, not a quality floor
    "contradiction_detection": 0.0, # same -- the disagreement itself is the signal
    "hallucination_detection": 0.0, # rejected-partition examples ARE this dataset
}
_DEFAULT_THRESHOLD = 0.50

# Task types whose entire purpose is to contain grounding FAILURES as
# training material (real, disclosed hallucination examples) -- the
# grounding_failed hard exclusion below exists to keep bad claims OUT of
# positive-claim datasets (financial_reasoning, extraction, citation_
# grounding); applying it here would make hallucination_detection reject
# every example it could ever contain, since a grounding failure is
# precisely what this dataset type is FOR, not a defect in it.
GROUNDING_EXCLUSION_EXEMPT_TASKS = {"hallucination_detection"}


def load_config(path: Path = CONFIG_PATH) -> dict:
    """The TOML file is the real source of truth; the module-level
    DEFAULT_* dicts above exist only as the in-code fallback if the config
    file is ever missing, mirroring pilot_summary.py's `_cost_rates()`
    pattern for configs/llm_provider.toml."""
    if not path.exists():
        return {"weights": DEFAULT_WEIGHTS, "acceptance_thresholds": DEFAULT_ACCEPTANCE_THRESHOLDS}
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return {"weights": raw.get("weights", DEFAULT_WEIGHTS),
           "acceptance_thresholds": raw.get("acceptance_thresholds", DEFAULT_ACCEPTANCE_THRESHOLDS)}


@dataclass
class QualityAssessment:
    quality_score: float
    hard_exclusion: str | None       # rejection_reason code, or None
    components: dict = field(default_factory=dict)
    evidence_tier: int | None = None


def _self_critique_severity(con, implication_id: int | None) -> float | None:
    if implication_id is None:
        return None
    rows = con.execute(
        "SELECT finding FROM self_critique_reviews WHERE implication_id = ?",
        (implication_id,)).fetchall()
    if not rows:
        return None
    scores = [_FINDING_SCORE.get(f, 0.6) for (f,) in rows]
    return sum(scores) / len(scores)


def _contradiction_hard_exclusion(con, implication_id: int | None) -> str | None:
    """Mirrors spec §4.4's second hard rule: never accept a claim a
    higher-trust-tier source already disputes, unresolved."""
    if implication_id is None:
        return None
    conflict = evidence_ranking.assess_implication_conflict(con, implication_id)
    if conflict is None:
        return None
    if conflict.agreement is False and conflict.trust_tier_preferred == "prior":
        return (f"contradicts_higher_tier_evidence:implication {implication_id} "
               f"contradicts #{conflict.contradicts_implication_id}, whose evidence "
               f"trust tier ({conflict.tiers.get('prior')}) beats this one's "
               f"({conflict.tiers.get('this')})")
    return None


def assess_example_quality(
    con, *, task: str, fact_id: int | None = None, implication_id: int | None = None,
    coverage_score: float | None = None, weights: dict | None = None,
) -> QualityAssessment:
    """The single quality-scoring entry point every exporter calls. Reuses
    evidence_ranking.py for tiering/conflict detection; never re-derives
    grounding or self-critique logic itself."""
    weights = weights if weights is not None else load_config()["weights"]
    components: dict = {}

    grounding_ok = True
    if fact_id is not None:
        row = con.execute(
            "SELECT grounding_check FROM extracted_facts WHERE fact_id = ?",
            (fact_id,)).fetchone()
        if (row is not None and row[0] not in ("passed", "not_run")
                and task not in GROUNDING_EXCLUSION_EXEMPT_TASKS):
            return QualityAssessment(
                quality_score=0.0,
                hard_exclusion=f"grounding_failed:fact {fact_id} grounding_check={row[0]!r}")
        grounding_ok = row is None or row[0] != "failed" or task in GROUNDING_EXCLUSION_EXEMPT_TASKS

    contradiction_exclusion = _contradiction_hard_exclusion(con, implication_id)
    if contradiction_exclusion is not None:
        return QualityAssessment(quality_score=0.0, hard_exclusion=contradiction_exclusion)

    evidence_tier = None
    if fact_id is not None:
        ranked = evidence_ranking.rank_evidence_for_fact(con, fact_id)
        evidence_tier = ranked[0]["tier"] if ranked else 4
        components["evidence_tier_score"] = _TIER_SCORE[evidence_tier]

    sc_severity = _self_critique_severity(con, implication_id)
    if sc_severity is not None:
        components["self_critique_severity"] = sc_severity

    if coverage_score is not None:
        components["coverage_score"] = max(0.0, min(1.0, coverage_score))

    components["citation_integrity"] = 1.0 if grounding_ok else 0.0

    active_weights = {k: w for k, w in weights.items()
                     if _component_key(k) in components}
    total_weight = sum(active_weights.values())
    if total_weight == 0:
        score = 0.0
    else:
        score = sum(components[_component_key(k)] * w for k, w in active_weights.items()) / total_weight

    return QualityAssessment(quality_score=round(score, 4), hard_exclusion=None,
                             components=components, evidence_tier=evidence_tier)


def _component_key(weight_key: str) -> str:
    return {"self_critique_severity": "self_critique_severity",
           "evidence_tier": "evidence_tier_score",
           "coverage_score": "coverage_score",
           "citation_integrity": "citation_integrity"}[weight_key]


def acceptance_threshold(task: str, thresholds: dict | None = None) -> float:
    table = thresholds if thresholds is not None else load_config()["acceptance_thresholds"]
    return table.get(task, table.get("default", _DEFAULT_THRESHOLD))


def decide_acceptance(task: str, assessment: QualityAssessment,
                      thresholds: dict | None = None) -> tuple[str, str | None]:
    """Returns (acceptance_status, rejection_reason)."""
    if assessment.hard_exclusion is not None:
        return "rejected", assessment.hard_exclusion
    floor = acceptance_threshold(task, thresholds)
    if assessment.quality_score < floor:
        return "rejected", (f"below_quality_threshold:{assessment.quality_score} < {floor} "
                            f"for task {task!r}")
    return "accepted", None
