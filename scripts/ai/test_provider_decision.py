"""Tests for provider_decision.py -- synthetic unit tests for each scoring
rule in isolation, PLUS an integration test that loads the REAL Round 1 +
Round 2 + Round 3 benchmark data (Gate-2's confirmation batch folded into
gemini-control only, 2026-08-15) and asserts the classifier reproduces the
exact five classifications this layer was built to encode:

  Groq                    -> DISABLED
  OpenRouter/Llama 3.3 70B -> EXPERIMENTAL
  Cerebras/Gemma 4 31B     -> EXPERIMENTAL
  Cerebras/GPT-OSS 120B    -> EXPERIMENTAL
  Gemini                   -> EXPERIMENTAL/CONTROL

  PYTHONPATH=src python scripts/ai/test_provider_decision.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot.documents.provider_decision import (  # noqa: E402
    EVIDENCE_TIERS, classify_provider, detect_disagreement, document_level_variance,
    economics_metrics, evidence_tier, schema_compliance_check,
    operational_metrics, quality_metrics, reproducibility_flags, sample_confidence)
from grade_benchmark import GOLD, grade_case  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


# --- sample_confidence ---
check("sample_confidence(0) == none", sample_confidence(0) == "none")
check("sample_confidence(1) == very_low", sample_confidence(1) == "very_low")
check("sample_confidence(2) == very_low", sample_confidence(2) == "very_low")
check("sample_confidence(3) == low", sample_confidence(3) == "low")
check("sample_confidence(5) == low", sample_confidence(5) == "low")
check("sample_confidence(6) == moderate", sample_confidence(6) == "moderate")
check("sample_confidence(100) == moderate (this platform never reaches 'high')",
     sample_confidence(100) == "moderate")

# --- quality_metrics: synthetic cases ---
CASE_OK = dict(success=True, structured_output_success=True, numeric_total=2, numeric_correct=2,
              period_total=2, period_correct=1, evidence_total=2, evidence_grounded=2,
              n_facts_returned=2, hallucinated_facts=0, catastrophic_errors=[], true_negative_violation=False)
CASE_HALLUCINATED = dict(CASE_OK, hallucinated_facts=1, n_facts_returned=1, evidence_grounded=0, evidence_total=1)
CASE_FAILED = dict(success=False, structured_output_success=None, numeric_total=0, numeric_correct=0,
                   period_total=0, period_correct=0, evidence_total=0, evidence_grounded=0,
                   n_facts_returned=0, hallucinated_facts=0, catastrophic_errors=[], true_negative_violation=False)
CASE_CATASTROPHIC = dict(CASE_OK, catastrophic_errors=["1000x scaling error"])

qm = quality_metrics([CASE_OK, CASE_OK, CASE_FAILED])
check("quality_metrics: only scoreable (success+structured_ok) cases count toward n",
     qm["n_scoreable"] == 2)
check("quality_metrics: numeric_accuracy pools across scoreable cases", qm["numeric_accuracy"] == 1.0)
check("quality_metrics: catastrophic_error_count is 0 when none present", qm["catastrophic_error_count"] == 0)

qm2 = quality_metrics([CASE_OK, CASE_CATASTROPHIC])
check("quality_metrics: catastrophic error counted even though the case itself was 'scoreable'",
     qm2["catastrophic_error_count"] == 1)

qm3 = quality_metrics([])
check("quality_metrics on empty input: n_scoreable=0, confidence=none",
     qm3["n_scoreable"] == 0 and qm3["confidence"] == "none")
check("quality_metrics on empty input: accuracy fields are None, not 0 (never fabricate a rate from no data)",
     qm3["numeric_accuracy"] is None)

# --- operational_metrics ---
RAW_OK = {"success": True, "latency_ms": 1000}
RAW_RATE_LIMITED = {"success": False, "failure_reason": "429 rate_limit_exceeded", "latency_ms": 200}
RAW_STRUCTURAL = {"success": False, "failure_reason": "413 Request too large", "latency_ms": 100}
om = operational_metrics([RAW_OK, RAW_OK, RAW_RATE_LIMITED, RAW_STRUCTURAL])
check("operational_metrics: success_rate = 2/4", om["success_rate"] == 0.5)
check("operational_metrics: rate-limit failures tracked separately from structural",
     om["n_rate_limited"] == 1 and om["n_structural_failures"] == 1)
check("operational_metrics: median_latency_ms computed from successes+failures alike",
     om["median_latency_ms"] is not None)

om_empty = operational_metrics([])
check("operational_metrics on empty input: success_rate is None, not 0",
     om_empty["success_rate"] is None)

# --- economics_metrics ---
em = economics_metrics([RAW_OK, RAW_OK], confirmed_cost_usd=0.02)
check("economics_metrics: cost_basis reflects a confirmed cost", "confirmed" in em["cost_basis"])
em_unconfirmed = economics_metrics([RAW_OK], confirmed_cost_usd=None)
check("economics_metrics: unconfirmed cost is explicit, never silently $0",
     "not independently confirmed" in em_unconfirmed["cost_basis"]
     and em_unconfirmed["confirmed_cost_usd"] is None)

# --- reproducibility_flags ---
R1_SUCCESS = {"doc_id": 11122, "success": True, "structured_output_success": True}
R2_FAIL = {"doc_id": 11122, "success": True, "structured_output_success": False}
flags = reproducibility_flags([R1_SUCCESS], [R2_FAIL])
check("reproducibility_flags: succeeded R1, failed to reproduce R2 -> flagged",
     len(flags) == 1 and "round 1, failed to reproduce round 2" in flags[0])

flags_consistent_fail = reproducibility_flags(
    [{"doc_id": 11122, "success": False, "structured_output_success": None}],
    [{"doc_id": 11122, "success": False, "structured_output_success": None}])
check("reproducibility_flags: consistently failed BOTH rounds -> NOT flagged (no flip)",
     len(flags_consistent_fail) == 0)

flags_consistent_pass = reproducibility_flags([R1_SUCCESS], [R1_SUCCESS])
check("reproducibility_flags: consistently succeeded BOTH rounds -> NOT flagged",
     len(flags_consistent_pass) == 0)

# --- document_level_variance ---
dv = document_level_variance([
    {"doc_id": 1, "numeric_total": 4, "numeric_correct": 4},
    {"doc_id": 2, "numeric_total": 4, "numeric_correct": 0},
])
check("document_level_variance: 2 docs with 100% and 0% accuracy -> stdev=0.5",
     dv["n_docs"] == 2 and abs(dv["stdev"] - 0.5) < 1e-9)
dv1 = document_level_variance([{"doc_id": 1, "numeric_total": 4, "numeric_correct": 4}])
check("document_level_variance: <2 docs -> stdev=None, not fabricated",
     dv1["stdev"] is None)

# --- detect_disagreement: NEVER resolves a winner ---
facts_agree = {"modelA": [{"fact_type": "revenue", "period_end": "2024-12-31", "numeric_value": 1000}],
              "modelB": [{"fact_type": "revenue", "period_end": "2024-12-31", "numeric_value": 1005}]}
d_agree = detect_disagreement(facts_agree, tolerance_pct=0.02)
check("detect_disagreement: values within tolerance -> no disagreement flagged", len(d_agree) == 0)

facts_disagree = {"modelA": [{"fact_type": "revenue", "period_end": "2024-12-31", "numeric_value": 1000}],
                  "modelB": [{"fact_type": "revenue", "period_end": "2024-12-31", "numeric_value": 5000}]}
d_dis = detect_disagreement(facts_disagree, tolerance_pct=0.02)
check("detect_disagreement: a real 5x spread is flagged", len(d_dis) == 1)
check("detect_disagreement: NEVER includes a 'resolved_value'/'winner' key (source is authoritative, not vote)",
     "resolved_value" not in d_dis[0] and "winner" not in d_dis[0] and "correct_value" not in d_dis[0])
check("detect_disagreement: both raw values are preserved for human/deterministic follow-up",
     d_dis[0]["values_by_identity"] == {"modelA": 1000, "modelB": 5000})

facts_zero_vs_nonzero = {"modelA": [{"fact_type": "capex", "period_end": "2024-12-31", "numeric_value": 0}],
                         "modelB": [{"fact_type": "capex", "period_end": "2024-12-31", "numeric_value": 500}]}
d_zero = detect_disagreement(facts_zero_vs_nonzero)
check("detect_disagreement: zero-vs-nonzero handled without a divide-by-zero crash", len(d_zero) == 1)

# --- classify_provider: synthetic edge cases ---
label, reason = classify_provider(
    identity="synthetic-structural-disabled",
    quality=quality_metrics([]), operational_by_round={},
    reproducibility_flags_list=[], structural_disable_reason="2 consecutive 413s")
check("classify_provider: explicit structural_disable_reason -> DISABLED regardless of quality",
     label == "DISABLED")

label, reason = classify_provider(
    identity="synthetic-tiny-sample", quality=quality_metrics([CASE_OK]),
    operational_by_round={"round1": operational_metrics([RAW_OK])},
    reproducibility_flags_list=[], is_control=True)
check("classify_provider: n=1 (very_low confidence) + is_control -> EXPERIMENTAL/CONTROL",
     label == "EXPERIMENTAL/CONTROL")

label, reason = classify_provider(
    identity="synthetic-catastrophic", quality=quality_metrics([CASE_OK] * 6 + [CASE_CATASTROPHIC]),
    operational_by_round={"round1": operational_metrics([RAW_OK] * 7)},
    reproducibility_flags_list=[])
check("classify_provider: catastrophic error present, even with large n -> DISABLED, never promoted",
     label == "DISABLED")

label, reason = classify_provider(
    identity="synthetic-reproducibility-fail", quality=quality_metrics([CASE_OK] * 6),
    operational_by_round={"round1": operational_metrics([RAW_OK] * 6),
                          "round2": operational_metrics([RAW_OK] * 6)},
    reproducibility_flags_list=["mandatory doc X: succeeded round 1, failed to reproduce round 2"])
check("classify_provider: reproducibility flag caps at EXPERIMENTAL even with otherwise-good metrics",
     label == "EXPERIMENTAL")

label, reason = classify_provider(
    identity="synthetic-clears-bar", quality=quality_metrics([CASE_OK] * 8),
    operational_by_round={"round1": operational_metrics([RAW_OK] * 8),
                          "round2": operational_metrics([RAW_OK] * 8)},
    reproducibility_flags_list=[])
check("classify_provider: clears quality+operational bar in both rounds -> SECONDARY (never auto-PRIMARY)",
     label == "SECONDARY")
check("classify_provider: SECONDARY reason explicitly states it is capped, not fully promoted",
     "capped" in reason.lower())

label, reason = classify_provider(
    identity="synthetic-one-bad-round", quality=quality_metrics([CASE_OK] * 8),
    operational_by_round={"round1": operational_metrics([RAW_OK] * 8),
                          "round2": operational_metrics([RAW_OK, RAW_RATE_LIMITED, RAW_RATE_LIMITED])},
    reproducibility_flags_list=[])
check("classify_provider: good round1 but poor round2 operational reliability -> stays EXPERIMENTAL "
     "(a promotion needs EVERY round to clear the bar, not an average)", label == "EXPERIMENTAL")

# ---------------------------------------------------------------------------
# INTEGRATION: real Round 1 + Round 2 + Round 3 data, PLUS the Gate-2
# confirmation batch (scripts/fre/phase4_pilot_completion.py, commit
# 2a09558, 2026-08-15) folded into gemini-control only, reproduces the
# exact required classifications. This is the test that matters most --
# it proves the decision layer isn't just internally consistent, it
# actually encodes the real evidence correctly.
#
# Previously this integration test pooled ONLY Round 1 + Round 2 -- a
# known staleness explicitly flagged as a needed follow-up in
# docs/ai/AI_PROVIDER_CONSOLIDATED_EVIDENCE_2026-08-14.md SS7/SS9 once
# Round 3 (and, later, Gate-2) became new baseline evidence. Updated here
# so this test keeps proving the function reproduces reality instead of
# silently going stale. Gate-2 produced zero new evidence about any
# identity except Gemini -- the other four are pooled through Round 3
# only, unchanged in scope.
# ---------------------------------------------------------------------------
r1_path = ROOT / "data" / "staging" / "benchmark_results_2026-08-13.json"
r2_path = ROOT / "data" / "staging" / "benchmark_results_round2_2026-08-13.json"
r3_path = ROOT / "data" / "staging" / "benchmark_results_round3_2026-08-14.jsonl"

if r1_path.exists() and r2_path.exists() and r3_path.exists():
    r1_raw = json.loads(r1_path.read_text(encoding="utf-8"))
    r2_raw = json.loads(r2_path.read_text(encoding="utf-8"))
    with r3_path.open(encoding="utf-8") as f:
        r3_raw = [json.loads(line) for line in f if line.strip()]
    r3_raw = [r for r in r3_raw if r["phase"] == "standard"]  # standard phase only, matching
                                                              # grade_benchmark_round3.py's own
                                                              # pooled-classification treatment

    def graded_for(raw_results, identity):
        return [grade_case(r, GOLD[r["doc_id"]]) for r in raw_results if r["benchmark_identity"] == identity]

    def raw_for(raw_results, identity):
        return [r for r in raw_results if r["benchmark_identity"] == identity]

    # Gate-2's 4 results, reconstructed from its own scratch-DB output --
    # same construction scripts/ai/fold_gate2_into_gemini.py uses, reused
    # here rather than duplicated by value.
    from fold_gate2_into_gemini import GATE2_GRADEABLE, GATE2_RAW  # noqa: E402

    EXPECTED = {
        "groq-llama-3.3-70b-versatile": ("DISABLED", None),  # Round 1 identity name
        "openrouter-llama-3.3-70b-instruct": ("EXPERIMENTAL", False),
        "cerebras-gemma-4-31b": ("EXPERIMENTAL", False),
        "cerebras-gpt-oss-120b": ("EXPERIMENTAL", False),
        "gemini-control": ("EXPERIMENTAL/CONTROL", True),
    }

    for identity, (expected_label, is_control) in EXPECTED.items():
        r1_cases = graded_for(r1_raw, identity)
        # Round 2 used a reduced-budget Groq identity name -- fold it in for the Groq case
        r2_ident = "groq-llama-3.3-70b-versatile-REDUCED-BUDGET" if identity == "groq-llama-3.3-70b-versatile" \
            else identity
        r2_cases = graded_for(r2_raw, r2_ident)
        r2_raw_for_op = raw_for(r2_raw, r2_ident)
        r3_cases = graded_for(r3_raw, identity)  # empty for groq -- not retested in Round 3
        r3_raw_for_op = raw_for(r3_raw, identity)
        gate2_cases = graded_for(GATE2_GRADEABLE, identity) if identity == "gemini-control" else []
        gate2_raw = GATE2_RAW if identity == "gemini-control" else []

        all_cases = r1_cases + r2_cases + r3_cases + gate2_cases
        qm_real = quality_metrics(all_cases)
        om_real = {"round1": operational_metrics(raw_for(r1_raw, identity)),
                  "round2": operational_metrics(r2_raw_for_op),
                  "round3": operational_metrics(r3_raw_for_op)}
        if gate2_raw:
            om_real["gate2"] = operational_metrics(gate2_raw)
        # Round1 vs Round3 is the mandatory-case comparison basis once Round 3
        # exists (matches grade_benchmark_round3.py's own pooled-classification
        # precedent); falls back to Round1 vs Round2 only for identities Round 3
        # never retested (Groq).
        repro = reproducibility_flags(r1_cases, r3_cases if r3_cases else r2_cases,
                                      round1_label="round 1", round2_label="round 3" if r3_cases else "round 2")

        structural_reason = None
        if identity == "groq-llama-3.3-70b-versatile":
            n_usable = sum(1 for c in all_cases if c["success"] and c["structured_output_success"]
                          and c["n_facts_returned"] > 0)
            if n_usable == 0:
                structural_reason = ("zero usable structured extractions across two independent "
                                    "task configurations (identical-task Round 1, reduced-budget "
                                    "Round 2) -- account TPM ceiling makes this task shape "
                                    "structurally unworkable")

        label, reason = classify_provider(
            identity=identity, quality=qm_real, operational_by_round=om_real,
            reproducibility_flags_list=repro, is_control=bool(is_control),
            structural_disable_reason=structural_reason)
        check(f"REAL DATA (R1+R2+R3{'+Gate-2' if gate2_raw else ''}): {identity} classifies as "
             f"{expected_label} (got {label}) -- {reason[:80]}",
             label == expected_label)
else:
    print("[SKIP] integration test: Round 1/2/3 result files not found at expected paths")

# ---------------------------------------------------------------------------
# evidence_tier -- Phase 3 (Statistical Discipline)
# ---------------------------------------------------------------------------
check("EVIDENCE_TIERS is the 4 required tiers, in order weakest->strongest",
     EVIDENCE_TIERS == ("insufficient", "preliminary", "moderate", "promotion_eligible"))

check("evidence_tier: n=0 -> insufficient",
     evidence_tier(quality_metrics([]), {}, []) == "insufficient")
check("evidence_tier: catastrophic error resets to insufficient EVEN with a large sample",
     evidence_tier(quality_metrics([CASE_OK] * 10 + [CASE_CATASTROPHIC]), {}, []) == "insufficient")
check("evidence_tier: n=1 (very_low) -> insufficient",
     evidence_tier(quality_metrics([CASE_OK]), {}, []) == "insufficient")
check("evidence_tier: n=4 (low) -> preliminary",
     evidence_tier(quality_metrics([CASE_OK] * 4), {}, []) == "preliminary")
check("evidence_tier: n>=6 (moderate) but a reproducibility flag exists -> preliminary, not moderate",
     evidence_tier(quality_metrics([CASE_OK] * 6), {}, ["some mandatory case flip"]) == "preliminary")
check("evidence_tier: n>=6, no repro flag, but only 1 round of operational data -> moderate",
     evidence_tier(quality_metrics([CASE_OK] * 6), {"round1": operational_metrics([RAW_OK] * 6)}, [])
     == "moderate")
check("evidence_tier: n>=6, no repro flag, 2 rounds but one has <80% success -> moderate",
     evidence_tier(quality_metrics([CASE_OK] * 6),
                   {"round1": operational_metrics([RAW_OK] * 6),
                    "round2": operational_metrics([RAW_OK, RAW_OK, RAW_RATE_LIMITED])}, []) == "moderate")
check("evidence_tier: n>=6, no repro flag, 2 rounds both >=80% success -> promotion_eligible",
     evidence_tier(quality_metrics([CASE_OK] * 6),
                   {"round1": operational_metrics([RAW_OK] * 6),
                    "round2": operational_metrics([RAW_OK] * 6)}, []) == "promotion_eligible")

# Real data (R1+R2+R3, Gate-2 folded into gemini-control): confirm each
# real identity's tier matches its classification's own stated reasoning.
# groq -> insufficient (n_scoreable=0, structurally); openrouter ->
# preliminary (real ELLAHLAKES reproducibility flag, R1 vs R3); both
# Cerebras identities -> moderate (Round 2's real <80% operational success
# rate); gemini-control -> preliminary (R1-vs-R3 mandatory-case flag --
# Gate-2's own 4th-consecutive ELLAHLAKES success does not clear this: the
# flag is a real, permanent fact about Round 1 vs Round 3, not something a
# later successful round retroactively erases from that specific pairwise
# comparison).
if r1_path.exists() and r2_path.exists() and r3_path.exists():
    REAL_EXPECTED_TIERS = {
        "groq-llama-3.3-70b-versatile": "insufficient",
        "gemini-control": "preliminary",
        "openrouter-llama-3.3-70b-instruct": "preliminary",
        "cerebras-gemma-4-31b": "moderate",
        "cerebras-gpt-oss-120b": "moderate",
    }
    for identity, expected_tier in REAL_EXPECTED_TIERS.items():
        r1_cases = graded_for(r1_raw, identity)
        r2_ident = "groq-llama-3.3-70b-versatile-REDUCED-BUDGET" if identity == "groq-llama-3.3-70b-versatile" else identity
        r2_cases = graded_for(r2_raw, r2_ident)
        r3_cases = graded_for(r3_raw, identity)
        gate2_cases = graded_for(GATE2_GRADEABLE, identity) if identity == "gemini-control" else []
        gate2_raw = GATE2_RAW if identity == "gemini-control" else []
        qm_real = quality_metrics(r1_cases + r2_cases + r3_cases + gate2_cases)
        om_real = {"round1": operational_metrics(raw_for(r1_raw, identity)),
                  "round2": operational_metrics(raw_for(r2_raw, r2_ident)),
                  "round3": operational_metrics(raw_for(r3_raw, identity))}
        if gate2_raw:
            om_real["gate2"] = operational_metrics(gate2_raw)
        repro = reproducibility_flags(r1_cases, r3_cases if r3_cases else r2_cases,
                                      round1_label="round 1", round2_label="round 3" if r3_cases else "round 2")
        tier = evidence_tier(qm_real, om_real, repro)
        check(f"REAL DATA evidence_tier: {identity} -> {expected_tier} (got {tier})",
             tier == expected_tier)

# ---------------------------------------------------------------------------
# schema_compliance_check -- Round 3 Category E support
# ---------------------------------------------------------------------------
check("schema_compliance_check: None input -> 'empty', never raises",
     schema_compliance_check(None)["category"] == "empty")
check("schema_compliance_check: {} input -> 'empty'",
     schema_compliance_check({})["category"] == "empty")
check("schema_compliance_check: facts=[] -> 'empty' (correct for a true-negative document)",
     schema_compliance_check({"facts": []})["category"] == "empty")
check("schema_compliance_check: 'facts' key missing entirely -> 'malformed'",
     schema_compliance_check({"not_facts": []})["category"] == "malformed")
check("schema_compliance_check: 'facts' present but not a list -> 'malformed'",
     schema_compliance_check({"facts": "not a list"})["category"] == "malformed")

_FULL_IMPACT = {k: {"direction": "neutral", "explanation": "x"} for k in
               ("revenue", "margins", "cash_flow", "capital_allocation", "balance_sheet", "growth",
                "competitive_advantage", "execution_risk", "regulatory_risk", "liquidity",
                "valuation", "market_expectations", "long_term_moat")}
_FULL_IMPLICATION = {k: None for k in
                     ("ticker", "direction", "duration_bucket", "magnitude", "confidence",
                      "confidence_rationale", "assumptions", "bull_case_delta", "bear_case_delta",
                      "base_case_delta", "intrinsic_value_direction", "intrinsic_value_reasoning",
                      "expected_earnings_direction", "target_multiple_direction",
                      "risk_profile_direction", "portfolio_sizing_note", "action_recommendation",
                      "market_reaction_assessment", "market_reaction_reasoning", "first_order_effects",
                      "second_order_effects", "third_order_effects", "research_tasks")}
_FULLY_COMPLIANT_FACT = {
    "fact_type": "revenue", "description": "x", "quoted_evidence": "x", "numeric_value": 100,
    "period_start": None, "period_end": "2024-12-31", "period_type": "FY",
    "causal_chain": [], "impact_assessments": _FULL_IMPACT, "implication": _FULL_IMPLICATION,
}
result = schema_compliance_check({"facts": [_FULLY_COMPLIANT_FACT]})
check("schema_compliance_check: a fully-populated fact -> 'compliant', compliance_rate=1.0",
     result["category"] == "compliant" and result["compliance_rate"] == 1.0)

_PARTIAL_FACT = dict(_FULLY_COMPLIANT_FACT, impact_assessments={"revenue": {"direction": "neutral"}})
result_partial = schema_compliance_check({"facts": [_PARTIAL_FACT]})
check("schema_compliance_check: missing most impact_assessments sub-keys -> 'partial', not 'compliant'",
     result_partial["category"] == "partial")
check("schema_compliance_check: 'partial' result names the specific missing sub-keys",
     any("impact_assessments.margins" in m for m in result_partial["missing_keys_by_fact"][0]))

result_mixed = schema_compliance_check({"facts": [_FULLY_COMPLIANT_FACT, _PARTIAL_FACT]})
check("schema_compliance_check: mixed compliant+partial facts -> compliance_rate=0.5",
     result_mixed["compliance_rate"] == 0.5)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
