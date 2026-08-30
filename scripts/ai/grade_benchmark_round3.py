"""Grades Round 3 results: standard-phase quality/operational metrics
(reusing grade_case/quality_metrics/operational_metrics -- same functions
as Rounds 1-2, required for a like-for-like comparison), PLUS Round
3-specific analysis: reproducibility-repeat consistency (Category A),
schema-compliance rates (Category E), and updated classifications via the
real evidence_tier()/classify_provider() functions pooling all 3 rounds.

  PYTHONPATH=src python scripts/ai/grade_benchmark_round3.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot.documents.provider_decision import (  # noqa: E402
    classify_provider, economics_metrics, operational_metrics, quality_metrics,
    reproducibility_flags, schema_compliance_check)
from grade_benchmark import GOLD, grade_case  # noqa: E402

R3_PATH = ROOT / "data" / "staging" / "benchmark_results_round3_2026-08-14.jsonl"
R1_PATH = ROOT / "data" / "staging" / "benchmark_results_2026-08-13.json"
R2_PATH = ROOT / "data" / "staging" / "benchmark_results_round2_2026-08-13.json"


def load_r3():
    with R3_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    r3 = load_r3()
    r1 = json.loads(R1_PATH.read_text(encoding="utf-8"))
    r2 = json.loads(R2_PATH.read_text(encoding="utf-8"))

    standard = [r for r in r3 if r["phase"] == "standard"]
    repro = [r for r in r3 if r["phase"] == "repro_repeat"]

    identities = sorted({r["benchmark_identity"] for r in standard})

    print("=== Round 3 standard-phase quality + operational (per identity) ===\n")
    round3_quality = {}
    round3_op = {}
    for identity in identities:
        raw = [r for r in standard if r["benchmark_identity"] == identity]
        cases = [grade_case(r, GOLD[r["doc_id"]]) for r in raw]
        qm = quality_metrics(cases)
        om = operational_metrics(raw)
        round3_quality[identity] = qm
        round3_op[identity] = om
        print(f"--- {identity} ---")
        print(f"  quality: n_scoreable={qm['n_scoreable']} confidence={qm['confidence']} "
             f"numeric_acc={qm['numeric_accuracy']} period_acc={qm['period_accuracy']} "
             f"evidence_acc={qm['evidence_accuracy']} hallucination={qm['hallucination_rate']} "
             f"catastrophic={qm['catastrophic_error_count']}")
        print(f"  operational: success_rate={om['success_rate']} n_rate_limited={om['n_rate_limited']} "
             f"n_structural={om['n_structural_failures']} median_latency_ms={om['median_latency_ms']}")

        schema_cats = defaultdict(int)
        compliance_rates = []
        for r in raw:
            sc = schema_compliance_check(r.get("parsed_response"))
            schema_cats[sc["category"]] += 1
            if sc["compliance_rate"] is not None:
                compliance_rates.append(sc["compliance_rate"])
        avg_compliance = sum(compliance_rates) / len(compliance_rates) if compliance_rates else None
        print(f"  schema compliance (Category E): {dict(schema_cats)} avg_compliance_rate={avg_compliance}")
        print()

    print("=== Category A: reproducibility-repeat consistency (3 repeats each) ===\n")
    for identity in identities:
        for doc_id in (11122, 9485, 4508):
            reps = [r for r in repro if r["benchmark_identity"] == identity and r["doc_id"] == doc_id]
            if not reps:
                continue
            reps.sort(key=lambda r: r["repeat_index"])
            outcomes = [(r["success"], r.get("structured_output_success")) for r in reps]
            n_facts = [len(r.get("parsed_response", {}).get("facts", [])) if r.get("parsed_response") else 0
                      for r in reps]
            consistent = len(set(outcomes)) == 1
            print(f"{identity} doc={doc_id}: outcomes={outcomes} n_facts={n_facts} "
                 f"consistent={'YES' if consistent else 'NO -- FLICKERS between repeats'}")
    print()

    print("=== Updated classification (Round 1 + Round 2 + Round 3 pooled) ===\n")
    R2_IDENTITY_MAP = {
        "cerebras-gemma-4-31b": "cerebras-gemma-4-31b", "cerebras-gpt-oss-120b": "cerebras-gpt-oss-120b",
        "openrouter-llama-3.3-70b-instruct": "openrouter-llama-3.3-70b-instruct",
        "gemini-control": "gemini-control",
    }
    results_by_identity = {}
    for identity in identities:
        r1_i = [r for r in r1 if r["benchmark_identity"] == identity]
        r2_i = [r for r in r2 if r["benchmark_identity"] == R2_IDENTITY_MAP.get(identity, identity)]
        r3_i = [r for r in standard if r["benchmark_identity"] == identity]

        r1_cases = [grade_case(r, GOLD[r["doc_id"]]) for r in r1_i]
        r2_cases = [grade_case(r, GOLD[r["doc_id"]]) for r in r2_i]
        r3_cases = [grade_case(r, GOLD[r["doc_id"]]) for r in r3_i]
        all_cases = r1_cases + r2_cases + r3_cases

        qm_pooled = quality_metrics(all_cases)
        om_by_round = {"round1": operational_metrics(r1_i), "round2": operational_metrics(r2_i),
                      "round3": operational_metrics(r3_i)}
        repro_flags = reproducibility_flags(r1_cases, r3_cases, round1_label="round 1", round2_label="round 3")  # R1 vs R3 (both "clean" full runs);
                                                                 # R2's collapse was operational, not
                                                                 # a reproducibility signal in itself
        label, reason = classify_provider(
            identity=identity, quality=qm_pooled, operational_by_round=om_by_round,
            reproducibility_flags_list=repro_flags, is_control=(identity == "gemini-control"))

        results_by_identity[identity] = {
            "quality_pooled": qm_pooled, "operational_by_round": om_by_round,
            "reproducibility_flags": repro_flags, "classification": label, "reason": reason,
        }
        print(f"{identity}: {label}")
        print(f"  reason: {reason}")
        print(f"  pooled quality: n={qm_pooled['n_scoreable']} confidence={qm_pooled['confidence']} "
             f"numeric_acc={qm_pooled['numeric_accuracy']}")
        print(f"  operational success rate by round: "
             f"R1={om_by_round['round1']['success_rate']} R2={om_by_round['round2']['success_rate']} "
             f"R3={om_by_round['round3']['success_rate']}")
        print()

    out_path = ROOT / "data" / "staging" / "benchmark_round3_graded_2026-08-14.json"
    out_path.write_text(json.dumps(
        {"round3_quality": round3_quality, "round3_operational": round3_op,
        "pooled_classification": results_by_identity}, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
