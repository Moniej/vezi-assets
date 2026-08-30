"""AI Provider Expansion Phase 2 -- grades benchmark_results_2026-08-13.json
against benchmark_gold_set.GOLD. The source document is the authority;
model agreement is never used as ground truth. Reuses check_grounding()
(the same function extract.py's production grounding check uses) for
evidence accuracy rather than reinventing quote verification.

  PYTHONPATH=src python scripts/ai/grade_benchmark.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot.documents.grounding import check_grounding  # noqa: E402
from benchmark_gold_set import GOLD  # noqa: E402

RESULTS_PATH = ROOT / "data" / "staging" / "benchmark_results_2026-08-13.json"

SCORING_WEIGHTS = {
    "extraction_accuracy": 0.35, "evidence_accuracy": 0.25, "numerical_accuracy": 0.15,
    "reasoning_quality": 0.10, "latency": 0.10, "cost": 0.05,
}


def _period_type_ok(gold_pt, returned_pt) -> bool | None:
    """None means 'not scored' -- used both when the gold set has no
    period_type expectation AND when the model returned None. The latter
    is deliberate, not an oversight (2026-08-14 fix): the extraction
    prompt explicitly instructs 'if the period is unclear... leave
    period_type as null rather than guessing' -- a None return on a
    genuinely ambiguous case (e.g. AFRIPRUD/UBA's real Q3-vs-9M
    ambiguity) is the prompt's own encouraged conservative behavior, not
    a wrong answer, and must never be scored identically to an ACTIVELY
    wrong value (e.g. returning 'FY' when the correct answer is 'Q3').
    Conflating the two previously produced a false catastrophic-error
    flag on Gemini's real, correct AFRIPRUD extraction."""
    if gold_pt is None or returned_pt is None:
        return None  # not scored -- neither side made an assertion to conflict with
    if isinstance(gold_pt, tuple):
        return returned_pt in gold_pt
    return returned_pt == gold_pt


def _pt_compatible(gold_pt, returned_pt) -> bool:
    """True unless the two period_types ACTIVELY conflict (both stated and
    different) -- e.g. gold FY vs returned Q4 sharing the same calendar
    period_end (both end 31 Dec) must NOT be treated as compatible, or a
    model that extracted the wrong period entirely gets silently matched
    against a gold fact it never actually answered."""
    if gold_pt is None or returned_pt is None:
        return True
    if isinstance(gold_pt, tuple):
        return returned_pt in gold_pt
    return returned_pt == gold_pt


def _match_fact(gold_fact: dict, candidates: list[dict], used: set[int]) -> tuple[int, dict] | None:
    """Best-effort match: same fact_type AND period-compatible, among
    not-yet-used candidates. A period_end coincidence (e.g. Q4 and FY both
    ending 31 Dec) is NOT sufficient on its own if period_type actively
    conflicts -- that is a real recall miss (gold fact never returned),
    not a period error on a matched fact. Returns (index, fact) or None."""
    same_type = [(i, f) for i, f in enumerate(candidates)
                if i not in used and f.get("fact_type") == gold_fact["fact_type"]]
    if not same_type:
        return None
    gold_pt = gold_fact.get("period_type")
    exact_both = [(i, f) for i, f in same_type
                 if f.get("period_end") == gold_fact["period_end"]
                 and _pt_compatible(gold_pt, f.get("period_type"))]
    if exact_both:
        return exact_both[0]
    period_end_only = [(i, f) for i, f in same_type if f.get("period_end") == gold_fact["period_end"]]
    if period_end_only:
        conflicting = [(i, f) for i, f in period_end_only
                      if not _pt_compatible(gold_pt, f.get("period_type"))]
        if conflicting and len(period_end_only) == len(conflicting):
            return None  # every same-period_end candidate actively conflicts on period_type
                        # -- treat as a recall miss, not a forced mismatch
        return period_end_only[0]
    if gold_pt is None:
        return same_type[0]
    return None


def grade_case(result: dict, gold_spec: dict) -> dict:
    """Grades ONE (doc, model identity) result. Returns a metrics dict;
    fields are None where genuinely not applicable (never fabricated)."""
    m = {
        "doc_id": result["doc_id"], "identity": result["benchmark_identity"],
        "success": result["success"], "structured_output_success": None,
        "catastrophic_errors": [], "numeric_correct": 0, "numeric_total": 0,
        "period_correct": 0, "period_total": 0, "evidence_grounded": 0,
        "evidence_total": 0, "hallucinated_facts": 0, "n_facts_returned": 0,
        "true_negative_violation": False, "latency_ms": result.get("latency_ms"),
        "input_tokens": result.get("input_tokens"), "output_tokens": result.get("output_tokens"),
    }
    if not result["success"]:
        return m
    m["structured_output_success"] = result["structured_output_success"]
    if not result["structured_output_success"]:
        return m

    parsed = result["parsed_response"] or {}
    facts = parsed.get("facts") or []
    m["n_facts_returned"] = len(facts)
    doc_text = (ROOT / "data" / "staging" / "document_text" / f"{result['doc_id']}.txt") \
        .read_text(encoding="utf-8")

    if gold_spec.get("true_negative"):
        # Correct behavior is facts=[] (or facts with no real numeric_value).
        real_valued = [f for f in facts if f.get("numeric_value") not in (None, 0)]
        m["true_negative_violation"] = len(real_valued) > 0
        m["hallucinated_facts"] = len(real_valued)
        return m

    used = set()
    for gf in gold_spec["facts"]:
        match = _match_fact(gf, facts, used)
        m["numeric_total"] += 1
        if gf.get("period_type") is not None:
            m["period_total"] += 1
        if match is None:
            continue  # not returned at all -- counts against recall, not penalized as "wrong"
        idx, rf = match
        used.add(idx)
        val = rf.get("numeric_value")
        if isinstance(val, (int, float)) and val != 0:
            ratio = abs(val) / abs(gf["value"]) if gf["value"] else None
            if ratio is not None:
                if abs(val - gf["value"]) / abs(gf["value"]) <= gf["tolerance_pct"]:
                    m["numeric_correct"] += 1
                elif abs(ratio - 0.001) < 0.001 * 0.05 or abs(ratio - 1000) < 1000 * 0.05:
                    m["catastrophic_errors"].append(
                        f"{gf['fact_type']}@{gf['period_end']}: 1000x scaling error "
                        f"(returned {val}, true {gf['value']})")
                elif abs(ratio - 1e-6) < 1e-6 * 0.05 or abs(ratio - 1e6) < 1e6 * 0.05:
                    m["catastrophic_errors"].append(
                        f"{gf['fact_type']}@{gf['period_end']}: 1,000,000x scaling error "
                        f"(returned {val}, true {gf['value']})")
        pt_ok = _period_type_ok(gf.get("period_type"), rf.get("period_type"))
        if pt_ok is False and gf.get("period_end"):
            m["catastrophic_errors"].append(
                f"{gf['fact_type']}: period_type mismatch (returned {rf.get('period_type')!r}, "
                f"expected {gf['period_type']!r})")
        if pt_ok is not None:
            m["period_correct"] += int(pt_ok)

    for f in facts:
        quote = f.get("quoted_evidence")
        if quote:
            m["evidence_total"] += 1
            gr = check_grounding(quote, doc_text)
            if gr.passed:
                m["evidence_grounded"] += 1
            else:
                m["hallucinated_facts"] += 1  # ungrounded quote -- fabricated evidence
        elif f.get("numeric_value") not in (None,):
            # a numeric claim with NO quote at all -- unsupported value
            m["hallucinated_facts"] += 1
    return m


def aggregate(cases: list[dict]) -> dict:
    n = len(cases)
    n_success = sum(c["success"] for c in cases)
    n_structured_ok = sum(1 for c in cases if c["structured_output_success"])
    numeric_total = sum(c["numeric_total"] for c in cases)
    numeric_correct = sum(c["numeric_correct"] for c in cases)
    period_total = sum(c["period_total"] for c in cases)
    period_correct = sum(c["period_correct"] for c in cases)
    evidence_total = sum(c["evidence_total"] for c in cases)
    evidence_grounded = sum(c["evidence_grounded"] for c in cases)
    n_facts_returned = sum(c["n_facts_returned"] for c in cases)
    hallucinated = sum(c["hallucinated_facts"] for c in cases)
    catastrophic = sum(len(c["catastrophic_errors"]) for c in cases)
    tn_violations = sum(c["true_negative_violation"] for c in cases)
    latencies = [c["latency_ms"] for c in cases if c["latency_ms"] is not None]
    out_tokens = [c["output_tokens"] for c in cases if c["output_tokens"] is not None]

    return {
        "n_cases": n, "success_rate": n_success / n if n else None,
        "structured_output_success_rate": n_structured_ok / n_success if n_success else None,
        "numeric_accuracy": numeric_correct / numeric_total if numeric_total else None,
        "numeric_matched_of": f"{numeric_correct}/{numeric_total}",
        "period_accuracy": period_correct / period_total if period_total else None,
        "period_matched_of": f"{period_correct}/{period_total}",
        "evidence_accuracy": evidence_grounded / evidence_total if evidence_total else None,
        "evidence_matched_of": f"{evidence_grounded}/{evidence_total}",
        "hallucination_rate": hallucinated / n_facts_returned if n_facts_returned else None,
        "hallucinated_of": f"{hallucinated}/{n_facts_returned}",
        "catastrophic_error_count": catastrophic,
        "true_negative_violations": tn_violations,
        "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "mean_output_tokens": sum(out_tokens) / len(out_tokens) if out_tokens else None,
        "n_failed": n - n_success,
    }


def composite_score(agg: dict) -> float | None:
    """Weighted score per the assignment's own starting weights, but with
    HARD FAIL: any true_negative_violation or catastrophic_error_count > 0
    forces the composite to 0 regardless of other metrics -- "never allow
    the weighted score to hide catastrophic failure." A model with no
    scoreable cases at all returns None (not 0 -- 0 would misrepresent
    'never ran' as 'ran and failed everything')."""
    if agg["n_cases"] == 0 or agg["success_rate"] is None:
        return None
    if agg["catastrophic_error_count"] > 0 or agg["true_negative_violations"] > 0:
        return 0.0
    extraction = agg["structured_output_success_rate"] or 0.0
    evidence = agg["evidence_accuracy"] if agg["evidence_accuracy"] is not None else 0.0
    numerical = agg["numeric_accuracy"] if agg["numeric_accuracy"] is not None else 0.0
    reasoning = extraction  # no independent reasoning-quality judge in this run; see report caveat
    lat = agg["median_latency_ms"] or 0
    latency_score = max(0.0, 1.0 - lat / 60000)  # 0 at >=60s, 1 at 0s -- crude, documented
    cost_score = 1.0  # all providers used were $0 marginal cost this run (free tiers) -- see report
    return round(
        SCORING_WEIGHTS["extraction_accuracy"] * extraction +
        SCORING_WEIGHTS["evidence_accuracy"] * evidence +
        SCORING_WEIGHTS["numerical_accuracy"] * numerical +
        SCORING_WEIGHTS["reasoning_quality"] * reasoning +
        SCORING_WEIGHTS["latency"] * latency_score +
        SCORING_WEIGHTS["cost"] * cost_score, 4)


def main() -> None:
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    by_identity = defaultdict(list)
    graded = []
    for r in results:
        gold_spec = GOLD[r["doc_id"]]
        case = grade_case(r, gold_spec)
        graded.append(case)
        by_identity[r["benchmark_identity"]].append(case)

    print(f"{len(results)} total cases graded across {len(by_identity)} model identities\n")
    leaderboard = []
    for identity, cases in by_identity.items():
        agg = aggregate(cases)
        score = composite_score(agg)
        leaderboard.append((identity, score, agg))

    leaderboard.sort(key=lambda x: (x[1] is None, -(x[1] or 0)))
    out = {"graded_cases": graded, "aggregate_by_identity": {},
          "leaderboard": [(i, s) for i, s, _ in leaderboard]}
    for identity, score, agg in leaderboard:
        out["aggregate_by_identity"][identity] = {**agg, "composite_score": score}
        print(f"=== {identity} === composite_score={score}")
        for k, v in agg.items():
            print(f"    {k}: {v}")
        print()

    ellahlakes_cases = [c for c in graded if c["doc_id"] == 11122]
    print("=== ELLAHLAKES mandatory regression case (per identity) ===")
    for c in ellahlakes_cases:
        print(f"  {c['identity']}: success={c['success']} structured_ok="
             f"{c['structured_output_success']} numeric={c['numeric_correct']}/"
             f"{c['numeric_total']} catastrophic_errors={c['catastrophic_errors']}")

    (ROOT / "data" / "staging" / "benchmark_graded_2026-08-13.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote graded results to data/staging/benchmark_graded_2026-08-13.json")


if __name__ == "__main__":
    main()
