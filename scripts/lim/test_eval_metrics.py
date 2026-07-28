"""LIM-5 Priority 4: engineering-correctness tests for the next-generation
evaluation metrics (semantic_equivalence, grounded_correctness,
citation_correctness, hallucination_risk, reasoning_quality) plus a
backward-compatibility check that the original LIM-3 metrics are
unchanged. Matches this project's no-pytest, assertion-script convention.

  lim_training/venv/Scripts/python.exe scripts/lim/test_eval_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.lim import eval_metrics as em  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def test_backward_compatibility_unchanged():
    """The 4 original LIM-3 metrics must keep computing identically --
    every future eval_run must stay comparable to the frozen LIM-3/4
    baselines on these specific keys."""
    expected = {"canonical_name": "GTCO", "entity_type": "company"}
    parsed = {"canonical_name": "GTCO", "entity_type": "company"}
    check("agreement_with_teacher: unchanged exact-match behavior",
         em.field_agreement(expected, parsed) == 1.0)
    check("agreement_with_teacher: unchanged on partial mismatch",
         em.field_agreement(expected, {"canonical_name": "WRONG", "entity_type": "company"}) == 0.5)
    check("self_critique_quality still task-gated",
         em.self_critique_quality({"task": "extraction"}, {}) is None)
    check("grounding_accuracy still requires a 'verdict' key",
         em.grounding_accuracy({"expected_output": {"no_verdict_here": 1}}, {}) is None)


def test_semantic_equivalence_beats_exact_match_on_real_wrapping():
    """Reproduces the real extraction:41 case from the LIM-4 eval run:
    model wraps the correct content in a {"dividend": {...}} envelope
    with aliased field names -- agreement_with_teacher scores 0 (exact
    key mismatch), semantic_equivalence must score meaningfully higher."""
    example = {
        "expected_output": {"fact_type": "dividend",
                           "description": "Dividend per share: 4; AGM date 2023-01-25",
                           "numeric_value": 4.0},
    }
    wrapped = {"dividend": {"amount": 4.0, "date": "2023-01-25",
                           "description": "Dividend per share: 4; AGM date 2023-01-25"}}
    old = em.field_agreement(example["expected_output"], wrapped)
    new = em.semantic_equivalence(example, wrapped)
    check("semantic_equivalence scores strictly higher than exact-match on real wrapped output",
         new > old, detail=f"old={old} new={new}")
    check("semantic_equivalence never scores below agreement_with_teacher",
         new >= old)


def test_semantic_equivalence_still_zero_for_wrong_content():
    example = {"expected_output": {"fact_type": "dividend", "numeric_value": 4.0}}
    wrong = {"fact_type": "rights_issue", "numeric_value": 999.0}
    check("semantic_equivalence correctly scores near-zero for genuinely wrong content",
         em.semantic_equivalence(example, wrong) < 0.3)


def test_hallucination_risk_distinguishes_grounded_from_fabricated():
    """Reproduces the real LIM-3 finding: entity_recognition:21's context
    never mentions "KO"/Coca-Cola -- hallucination_risk must flag it, and
    must NOT flag a ticker that genuinely came from the example's own
    context."""
    example = {
        "context": {"filing_ticker": "GTCO", "filing_date": "2024-07-15"},
        "citations": [], "expected_output": {"canonical_name": "Nigerian Capital Market"},
    }
    check("hallucination_risk flags a fabricated, out-of-context ticker",
         em.hallucination_risk(example, {"entity": "KO", "type": "Company"}) == 1.0)
    check("hallucination_risk scores 0.0 for a ticker present in the example's own context",
         em.hallucination_risk(example, {"entity": "GTCO", "type": "ticker"}) == 0.0)
    check("hallucination_risk is None when output has no ticker-shaped value",
         em.hallucination_risk(example, {"note": "no tickers mentioned here"}) is None)


def test_grounded_correctness_partial_credit():
    # "PZ" is deliberately NOT used here -- grounded_correctness ignores
    # leaf strings under 3 chars (avoids noise from very short values),
    # so a 2-char ticker would silently not count as a checkable value.
    example = {"context": {"ticker": "PZCUSSONS", "filing_date": "2022-10-17"}, "citations": []}
    fully_grounded = {"ticker": "PZCUSSONS", "date": "2022-10-17"}
    partially_grounded = {"ticker": "PZCUSSONS", "date": "1999-01-01"}
    check("grounded_correctness: all values traceable to context scores 1.0",
         em.grounded_correctness(example, fully_grounded) == 1.0)
    g = em.grounded_correctness(example, partially_grounded)
    check("grounded_correctness: partially traceable values score strictly between 0 and 1",
         0.0 < g < 1.0, detail=f"got {g}")
    check("grounded_correctness: None when example has no context/citations to check against",
         em.grounded_correctness({"context": {}, "citations": []}, {"a": "b"}) is None)


def test_citation_correctness_honest_about_non_applicability():
    """No current dataset type asks the model to cite a specific id in
    its output -- citation_correctness must stay None (not fabricate a
    score) unless the output actually references an id field."""
    example = {"citations": [{"doc_id": 123}], "expected_output": {}}
    check("citation_correctness: None when output doesn't reference any id field",
         em.citation_correctness(example, {"canonical_name": "GTCO"}) is None)
    check("citation_correctness: scores when output DOES reference a real doc_id",
         em.citation_correctness(example, {"doc_id": 123}) == 1.0)
    check("citation_correctness: None when example has no real citation ids at all",
         em.citation_correctness({"citations": [], "expected_output": {}}, {"doc_id": 123}) is None)


def test_reasoning_quality_partial_credit():
    example = {"expected_output": {"finding": "fail",
                                   "explanation": "Offer for Subscription causes 23.42% dilution, not a rights issue."}}
    close = {"finding": "fail",
            "explanation": "The filing is an Offer for Subscription with 23.42% dilution, contradicting the rights issue claim."}
    unrelated = {"finding": "fail", "explanation": "Completely unrelated text about oil prices in Texas."}
    q_close = em.reasoning_quality(example, close)
    q_unrelated = em.reasoning_quality(example, unrelated)
    check("reasoning_quality: overlapping explanation scores meaningfully higher than unrelated text",
         q_close > q_unrelated, detail=f"close={q_close} unrelated={q_unrelated}")
    check("reasoning_quality: None when expected_output has no free-text field",
         em.reasoning_quality({"expected_output": {"verdict": "grounded"}}, {}) is None)


def test_partial_credit_tiers():
    check("tier: >=0.8 is correct", em.partial_credit_tier(0.9) == "correct")
    check("tier: 0.4-0.8 is partial", em.partial_credit_tier(0.5) == "partial")
    check("tier: <0.4 is incorrect", em.partial_credit_tier(0.1) == "incorrect")
    check("tier: None stays None", em.partial_credit_tier(None) is None)


def test_aggregate_metrics_reports_new_keys_and_tiers():
    records = [
        {"dataset_type": "extraction", "latency_s": 1.0, "output_tokens": 10,
         "scores": em.score_example(
             {"expected_output": {"fact_type": "dividend"}, "context": {}, "citations": []},
             {"fact_type": "dividend"})},
    ]
    agg = em.aggregate_metrics(records)
    for key in ("semantic_equivalence", "grounded_correctness", "citation_correctness",
               "hallucination_risk", "reasoning_quality"):
        check(f"aggregate_metrics includes new key {key!r}", key in agg["overall"])
    check("aggregate_metrics includes original agreement_with_teacher (backward compatible)",
         "agreement_with_teacher" in agg["overall"])
    check("aggregate_metrics reports partial-credit tiers for agreement_with_teacher",
         "tiers" in agg["overall"]["agreement_with_teacher"])


if __name__ == "__main__":
    test_backward_compatibility_unchanged()
    test_semantic_equivalence_beats_exact_match_on_real_wrapping()
    test_semantic_equivalence_still_zero_for_wrong_content()
    test_hallucination_risk_distinguishes_grounded_from_fabricated()
    test_grounded_correctness_partial_credit()
    test_citation_correctness_honest_about_non_applicability()
    test_reasoning_quality_partial_credit()
    test_partial_credit_tiers()
    test_aggregate_metrics_reports_new_keys_and_tiers()

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
