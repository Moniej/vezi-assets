"""Provider Decision Layer (2026-08-14, AI Provider Reliability + Decision
Layer). Turns raw benchmark results + graded cases (from
scripts/ai/run_benchmark*.py and scripts/ai/grade_benchmark*.py -- reused,
not duplicated) into confidence-aware quality/operational/economics
scores and an explicit PRIMARY/SECONDARY/FALLBACK/EXPERIMENTAL/DISABLED
classification.

Pure functions operating on plain dicts (the same shapes run_benchmark.py
and grade_benchmark.py already produce) -- no I/O, no live calls, fully
unit-testable offline. `scripts/ai/build_decision_layer.py` is the thin
driver that loads the real JSON files and calls these.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from .provider_reliability import classify_failure

# Sample-size confidence tiers. This platform never reaches "high" with the
# document counts used so far (10 docs/round) -- "moderate" is the
# ceiling, stated explicitly rather than implying a false high-confidence
# tier that was never actually reached.
def sample_confidence(n: int) -> str:
    if n <= 0:
        return "none"
    if n <= 2:
        return "very_low"
    if n <= 5:
        return "low"
    return "moderate"


# ---------------------------------------------------------------------------
# Quality (from GRADED cases -- scripts/ai/grade_benchmark.grade_case output)
# ---------------------------------------------------------------------------

def quality_metrics(cases: list[dict]) -> dict:
    """cases: graded case dicts for ONE identity, any number of rounds
    pooled. Only cases with success AND structured_output_success
    contribute to accuracy metrics (an unparseable/failed call carries no
    quality signal, only an operational one -- see operational_metrics)."""
    scoreable = [c for c in cases if c.get("success") and c.get("structured_output_success")]
    n = len(scoreable)
    numeric_total = sum(c["numeric_total"] for c in scoreable)
    numeric_correct = sum(c["numeric_correct"] for c in scoreable)
    period_total = sum(c["period_total"] for c in scoreable)
    period_correct = sum(c["period_correct"] for c in scoreable)
    evidence_total = sum(c["evidence_total"] for c in scoreable)
    evidence_grounded = sum(c["evidence_grounded"] for c in scoreable)
    n_facts = sum(c["n_facts_returned"] for c in scoreable)
    hallucinated = sum(c["hallucinated_facts"] for c in scoreable)
    catastrophic = sum(len(c.get("catastrophic_errors", [])) for c in cases)  # count on ALL
                                                                              # cases, not just
                                                                              # scoreable -- a
                                                                              # catastrophic error
                                                                              # is a hard fail
                                                                              # regardless
    tn_violations = sum(1 for c in cases if c.get("true_negative_violation"))
    return {
        "n_scoreable": n, "confidence": sample_confidence(n),
        "numeric_accuracy": numeric_correct / numeric_total if numeric_total else None,
        "numeric_sample": f"{numeric_correct}/{numeric_total}",
        "period_accuracy": period_correct / period_total if period_total else None,
        "period_sample": f"{period_correct}/{period_total}",
        "evidence_accuracy": evidence_grounded / evidence_total if evidence_total else None,
        "evidence_sample": f"{evidence_grounded}/{evidence_total}",
        "hallucination_rate": hallucinated / n_facts if n_facts else None,
        "hallucination_sample": f"{hallucinated}/{n_facts}",
        "structured_output_success_rate":
            n / len([c for c in cases if c.get("success")]) if any(c.get("success") for c in cases) else None,
        "catastrophic_error_count": catastrophic,
        "true_negative_violations": tn_violations,
    }


# ---------------------------------------------------------------------------
# Operational reliability (from RAW results -- run_benchmark*.py output,
# which carries failure_reason/latency/tokens that graded cases don't)
# ---------------------------------------------------------------------------

def operational_metrics(raw_results: list[dict]) -> dict:
    n = len(raw_results)
    n_success = sum(1 for r in raw_results if r.get("success"))
    failures = [r for r in raw_results if not r.get("success")]
    by_class = defaultdict(int)
    for r in failures:
        cls = classify_failure(r.get("failure_reason") or "", "")
        by_class[cls] += 1
    latencies = [r["latency_ms"] for r in raw_results if r.get("latency_ms") is not None]
    return {
        "n_calls": n, "n_success": n_success,
        "success_rate": n_success / n if n else None,
        "n_rate_limited": by_class["rate_limit"], "n_structural_failures": by_class["structural"],
        "n_other_failures": by_class["other"],
        "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "max_latency_ms": max(latencies) if latencies else None,
    }


def operational_metrics_by_round(raw_by_round: dict[str, list[dict]]) -> dict:
    return {round_name: operational_metrics(rs) for round_name, rs in raw_by_round.items()}


# ---------------------------------------------------------------------------
# Economics
# ---------------------------------------------------------------------------

def economics_metrics(raw_results: list[dict], confirmed_cost_usd: float | None = None) -> dict:
    successful = [r for r in raw_results if r.get("success")]
    total_in = sum(r.get("input_tokens") or 0 for r in successful)
    total_out = sum(r.get("output_tokens") or 0 for r in successful)
    n_validated = sum(1 for r in raw_results if r.get("structured_output_success"))
    cost_per_validated = (confirmed_cost_usd / n_validated) if (confirmed_cost_usd and n_validated) else None
    return {
        "total_input_tokens": total_in, "total_output_tokens": total_out,
        "n_successful_calls": len(successful), "n_validated_extractions": n_validated,
        "confirmed_cost_usd": confirmed_cost_usd,
        "cost_per_validated_extraction_usd": cost_per_validated,
        "cost_basis": "confirmed via provider API" if confirmed_cost_usd is not None
                     else "not independently confirmed -- do not assume $0",
    }


# ---------------------------------------------------------------------------
# Reproducibility and document-level variance
# ---------------------------------------------------------------------------

def reproducibility_flags(round1_cases: list[dict], round2_cases: list[dict],
                          mandatory_doc_ids: tuple[int, ...] = (11122,),
                          round1_label: str = "round 1", round2_label: str = "round 2") -> list[str]:
    """Flags a MANDATORY case that succeeded in one round and failed to
    reproduce in the other -- in either direction. A case that
    consistently failed (or consistently succeeded) in both rounds is not
    flagged; only a flip is evidence of non-reproducibility.

    round1_label/round2_label (2026-08-14 fix): the message text
    previously hardcoded literal "round 1"/"round 2" regardless of which
    two case lists were actually passed in -- comparing Round 1 against
    Round 3 produced a message that FALSELY said "succeeded round 2"
    when Round 2 was never even attempted for that case (skipped due to
    quota). Callers comparing any two rounds must now pass accurate
    labels so the message is never a misleading literal claim."""
    r1 = {c["doc_id"]: c for c in round1_cases}
    r2 = {c["doc_id"]: c for c in round2_cases}
    flags = []
    for doc_id in mandatory_doc_ids:
        c1, c2 = r1.get(doc_id), r2.get(doc_id)
        if c1 is None or c2 is None:
            continue
        ok1 = bool(c1.get("success")) and bool(c1.get("structured_output_success"))
        ok2 = bool(c2.get("success")) and bool(c2.get("structured_output_success"))
        if ok1 and not ok2:
            flags.append(f"mandatory doc {doc_id}: succeeded {round1_label}, failed to reproduce {round2_label}")
        elif ok2 and not ok1:
            flags.append(f"mandatory doc {doc_id}: succeeded {round2_label}, did not succeed {round1_label}")
    return flags


def document_level_variance(cases: list[dict]) -> dict:
    """Per-document numeric-accuracy spread (all rounds pooled) -- a high
    stdev means this identity's accuracy is document-shape-dependent, not
    a stable trait; population stdev needs >=2 documents to be meaningful."""
    by_doc = defaultdict(list)
    for c in cases:
        if c.get("numeric_total"):
            by_doc[c["doc_id"]].append(c["numeric_correct"] / c["numeric_total"])
    per_doc_acc = {doc: sum(v) / len(v) for doc, v in by_doc.items()}
    if len(per_doc_acc) < 2:
        return {"n_docs": len(per_doc_acc), "stdev": None, "per_doc_accuracy": per_doc_acc}
    return {"n_docs": len(per_doc_acc),
           "stdev": statistics.pstdev(list(per_doc_acc.values())),
           "per_doc_accuracy": per_doc_acc}


# ---------------------------------------------------------------------------
# Disagreement detection -- "the source document remains authoritative,
# multi-model agreement is evidence of consistency, not proof of
# correctness." NEVER resolves via majority vote.
# ---------------------------------------------------------------------------

def detect_disagreement(facts_by_identity: dict[str, list[dict]],
                        tolerance_pct: float = 0.02) -> list[dict]:
    """facts_by_identity: {identity: [fact_dict, ...]} for the SAME
    document. Groups by (fact_type, period_end) across identities; flags
    when >=2 identities report a numeric_value differing by more than
    tolerance_pct. Returns disagreement records requiring validation
    against the source document -- never picks a 'winning' value."""
    groups: dict[tuple, dict[str, float]] = defaultdict(dict)
    for identity, facts in facts_by_identity.items():
        for f in facts:
            key = (f.get("fact_type"), f.get("period_end"))
            val = f.get("numeric_value")
            if isinstance(val, (int, float)):
                groups[key][identity] = val
    disagreements = []
    for (fact_type, period_end), values in groups.items():
        if len(values) < 2:
            continue
        vals = list(values.values())
        vmin, vmax = min(vals), max(vals)
        if vmin == 0:
            if vmax != 0:
                disagreements.append({"fact_type": fact_type, "period_end": period_end,
                                     "values_by_identity": dict(values),
                                     "requires_validation": True, "reason": "zero-vs-nonzero"})
            continue
        if abs(vmax - vmin) / abs(vmin) > tolerance_pct:
            disagreements.append({"fact_type": fact_type, "period_end": period_end,
                                 "values_by_identity": dict(values), "requires_validation": True,
                                 "reason": f"spread {abs(vmax - vmin) / abs(vmin):.1%} > "
                                          f"{tolerance_pct:.1%} tolerance"})
    return disagreements


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

VALID_LABELS = {"PRIMARY", "SECONDARY", "FALLBACK", "EXPERIMENTAL", "DISABLED"}

PROMOTION_BAR = {
    "min_confidence": "moderate",       # sample_confidence(n) must be >= this
    "min_operational_success_rate": 0.8,  # required in EVERY round with data
    "min_rounds_with_data": 2,
}

# 2026-08-14, Phase 3 (Statistical Discipline). Four explicit evidence
# tiers, ordered weakest to strongest. A provider can only be considered
# for promotion from "promotion_eligible" -- and even then, classify_provider()
# still caps it at SECONDARY, never auto-PRIMARY (see below). Never call a
# provider "best" from a raw point estimate alone -- these tiers exist
# specifically so a high accuracy number on n=1 reads as "insufficient",
# not as leadership.
EVIDENCE_TIERS = ("insufficient", "preliminary", "moderate", "promotion_eligible")


def evidence_tier(quality: dict, operational_by_round: dict[str, dict],
                  reproducibility_flags_list: list[str]) -> str:
    """Returns one of EVIDENCE_TIERS. Pure function of already-computed
    quality/operational/reproducibility inputs -- no provider identity is
    consulted, so this cannot be gamed by which provider is being scored.

    insufficient       -- no scoreable data, tiny sample, or a catastrophic
                          error/true-negative violation (a catastrophic
                          error resets evidence to insufficient regardless
                          of however much data exists -- a large n does
                          NOT buy back trust after a hard failure).
    preliminary         -- real data exists but is either low-confidence
                          (n=3-5) or carries an unresolved reproducibility
                          flag on a mandatory case.
    moderate            -- adequate sample (n>=6) and no reproducibility/
                          catastrophic issue, but does not yet clear the
                          operational-reliability bar in every round with
                          data (this is exactly the current Cerebras
                          state: real, decent quality evidence, undermined
                          by an operational throughput problem, not a
                          quality one).
    promotion_eligible  -- clears sample size, reproducibility, zero
                          catastrophic errors, AND >=80% operational
                          success rate in every round, across >=2 rounds.
                          Necessary, not sufficient, for promotion --
                          classify_provider() still requires explicit
                          sign-off beyond this tier.
    """
    if quality["n_scoreable"] == 0:
        return "insufficient"
    if quality["catastrophic_error_count"] > 0 or quality["true_negative_violations"] > 0:
        return "insufficient"
    if quality["confidence"] in ("none", "very_low"):
        return "insufficient"
    if reproducibility_flags_list:
        return "preliminary"
    if quality["confidence"] == "low":
        return "preliminary"
    # confidence == "moderate" from here (sample_confidence's ceiling)
    rounds_with_data = {r: m for r, m in operational_by_round.items() if m["n_calls"] > 0}
    if len(rounds_with_data) < PROMOTION_BAR["min_rounds_with_data"]:
        return "moderate"
    op_rates = [m["success_rate"] for m in rounds_with_data.values() if m["success_rate"] is not None]
    if not op_rates or min(op_rates) < PROMOTION_BAR["min_operational_success_rate"]:
        return "moderate"
    return "promotion_eligible"


def classify_provider(*, identity: str, quality: dict, operational_by_round: dict[str, dict],
                      reproducibility_flags_list: list[str], is_control: bool = False,
                      structural_disable_reason: str | None = None) -> tuple[str, str]:
    """Returns (label, reason). Deliberately conservative: default is
    EXPERIMENTAL, and NOTHING is promoted merely for having the highest
    raw score -- promotion requires reaching the 'promotion_eligible'
    evidence tier (see evidence_tier() above), and even then this
    function caps the result at SECONDARY, never auto-PRIMARY."""
    control_suffix = "/CONTROL" if is_control else ""

    if structural_disable_reason:
        return "DISABLED", structural_disable_reason

    tier = evidence_tier(quality, operational_by_round, reproducibility_flags_list)

    if tier == "insufficient":
        if quality["catastrophic_error_count"] > 0 or quality["true_negative_violations"] > 0:
            return "DISABLED", \
                (f"{quality['catastrophic_error_count']} catastrophic error(s) / "
                f"{quality['true_negative_violations']} true-negative violation(s) observed "
                f"-- evidence tier reset to 'insufficient' regardless of sample size")
        if quality["n_scoreable"] == 0:
            return f"EXPERIMENTAL{control_suffix}", \
                "no scoreable extraction results yet -- insufficient evidence, not a negative finding"
        return f"EXPERIMENTAL{control_suffix}", \
            f"sample size too small (n={quality['n_scoreable']}) for any promotion decision"

    if tier == "preliminary":
        if reproducibility_flags_list:
            return f"EXPERIMENTAL{control_suffix}", \
                "failed to reproduce on a mandatory case: " + "; ".join(reproducibility_flags_list)
        return f"EXPERIMENTAL{control_suffix}", \
            f"preliminary evidence only (n={quality['n_scoreable']}, confidence={quality['confidence']}) " \
            "-- not enough for a promotion decision"

    if tier == "moderate":
        rounds_with_data = {r: m for r, m in operational_by_round.items() if m["n_calls"] > 0}
        op_rates = [m["success_rate"] for m in rounds_with_data.values() if m["success_rate"] is not None]
        worst = min(op_rates) if op_rates else None
        return f"EXPERIMENTAL{control_suffix}", \
            (f"moderate evidence (adequate quality sample, n={quality['n_scoreable']}) but operational "
            f"success rate ({worst}) has not cleared the {PROMOTION_BAR['min_operational_success_rate']} "
            f"bar in every round -- see PROMOTION_BAR")

    # tier == "promotion_eligible" -- still capped at SECONDARY, never
    # auto-PRIMARY. PRIMARY requires a THIRD confirming round plus
    # explicit operator sign-off, per "do not promote automatically."
    return "SECONDARY", \
        ("reaches the 'promotion_eligible' evidence tier (quality + operational + reproducibility "
        "all clear) -- capped at SECONDARY pending a third confirming round and explicit operator "
        "sign-off before PRIMARY/FALLBACK is even considered")


# ---------------------------------------------------------------------------
# Structured-output / schema compliance (Round 3, Category E). Deliberately
# DISTINCT from "did json.loads() succeed" (that's structured_output_success,
# already tracked) -- this checks whether the PARSED object actually
# matches build_draft_prompt()'s real schema shape (prompts.py,
# UNCHANGED -- this checker reads the schema, it does not define a new
# one). A response can be valid JSON and still be schema-noncompliant
# (missing required keys, wrong types) -- both failure modes are real and
# worth measuring separately.
# ---------------------------------------------------------------------------

_REQUIRED_IMPACT_KEYS = (
    "revenue", "margins", "cash_flow", "capital_allocation", "balance_sheet", "growth",
    "competitive_advantage", "execution_risk", "regulatory_risk", "liquidity", "valuation",
    "market_expectations", "long_term_moat",
)
_REQUIRED_IMPLICATION_KEYS = (
    "ticker", "direction", "duration_bucket", "magnitude", "confidence", "confidence_rationale",
    "assumptions", "bull_case_delta", "bear_case_delta", "base_case_delta",
    "intrinsic_value_direction", "intrinsic_value_reasoning", "expected_earnings_direction",
    "target_multiple_direction", "risk_profile_direction", "portfolio_sizing_note",
    "action_recommendation", "market_reaction_assessment", "market_reaction_reasoning",
    "first_order_effects", "second_order_effects", "third_order_effects", "research_tasks",
)
_REQUIRED_FACT_KEYS = (
    "fact_type", "description", "quoted_evidence", "numeric_value", "period_start",
    "period_end", "period_type", "causal_chain", "impact_assessments", "implication",
)


def schema_compliance_check(parsed: dict | None) -> dict:
    """Returns a per-response compliance report. Categories, matching
    Round 3's Category E test cases exactly:
      - 'empty'    : parsed is None, or parsed=={} , or facts==[] with no
                     other content (the true-negative case -- correct
                     for STANBIC/MORISON, so 'empty' is NOT itself a
                     failure; see facts_expected_empty below)
      - 'malformed': parsed is a dict but 'facts' is missing or not a list
      - 'partial'  : 'facts' is a list, but one or more entries are
                     missing required top-level keys, or impact_assessments/
                     implication are missing required sub-keys
      - 'compliant': every fact has every required key at every level
    NEVER raises -- a malformed response is exactly what this function
    exists to characterize, not something it should crash on."""
    if not parsed or not isinstance(parsed, dict):
        return {"category": "empty", "n_facts": 0, "n_compliant_facts": 0,
               "compliance_rate": None, "missing_keys_by_fact": []}
    facts = parsed.get("facts")
    if facts is None or not isinstance(facts, list):
        return {"category": "malformed", "n_facts": 0, "n_compliant_facts": 0,
               "compliance_rate": None, "missing_keys_by_fact": []}
    if len(facts) == 0:
        return {"category": "empty", "n_facts": 0, "n_compliant_facts": 0,
               "compliance_rate": None, "missing_keys_by_fact": []}

    missing_by_fact = []
    n_compliant = 0
    for f in facts:
        if not isinstance(f, dict):
            missing_by_fact.append(["<entry is not an object>"])
            continue
        missing = [k for k in _REQUIRED_FACT_KEYS if k not in f]
        impact = f.get("impact_assessments")
        if isinstance(impact, dict):
            missing += [f"impact_assessments.{k}" for k in _REQUIRED_IMPACT_KEYS if k not in impact]
        elif "impact_assessments" not in missing:
            missing.append("impact_assessments.<not a dict>")
        implication = f.get("implication")
        if isinstance(implication, dict):
            missing += [f"implication.{k}" for k in _REQUIRED_IMPLICATION_KEYS if k not in implication]
        elif "implication" not in missing:
            missing.append("implication.<not a dict>")
        missing_by_fact.append(missing)
        if not missing:
            n_compliant += 1

    category = "compliant" if n_compliant == len(facts) else "partial"
    return {"category": category, "n_facts": len(facts), "n_compliant_facts": n_compliant,
           "compliance_rate": n_compliant / len(facts) if facts else None,
           "missing_keys_by_fact": missing_by_fact}
