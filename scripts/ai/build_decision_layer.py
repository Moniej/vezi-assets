"""Driver: loads real Round 1 + Round 2 benchmark data, computes quality/
operational/economics scores and classifications via provider_decision.py,
and writes a consolidated JSON for docs/ai/AI_PROVIDER_RELIABILITY_AND_
DECISION_LAYER_2026-08-14.md to draw from. No live calls.

  PYTHONPATH=src python scripts/ai/build_decision_layer.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot.documents.provider_decision import (  # noqa: E402
    classify_provider, document_level_variance, economics_metrics, operational_metrics,
    quality_metrics, reproducibility_flags)
from grade_benchmark import GOLD, grade_case  # noqa: E402

R1_RAW = json.loads((ROOT / "data/staging/benchmark_results_2026-08-13.json").read_text(encoding="utf-8"))
R2_RAW = json.loads((ROOT / "data/staging/benchmark_results_round2_2026-08-13.json").read_text(encoding="utf-8"))

CONFIRMED_COSTS = {
    # (identity, round) -> confirmed USD, from OpenRouter's own /v1/key API (checked, not assumed)
    ("openrouter-llama-3.3-70b-instruct", "round1"): 0.028,
    ("openrouter-llama-3.3-70b-instruct", "round2"): 0.029,
}

IDENTITIES = {
    "cerebras-gemma-4-31b": {"is_control": False, "round2_name": "cerebras-gemma-4-31b"},
    "cerebras-gpt-oss-120b": {"is_control": False, "round2_name": "cerebras-gpt-oss-120b"},
    "openrouter-llama-3.3-70b-instruct": {"is_control": False, "round2_name": "openrouter-llama-3.3-70b-instruct"},
    "gemini-control": {"is_control": True, "round2_name": "gemini-control"},
    "groq-llama-3.3-70b-versatile": {"is_control": False, "round2_name": "groq-llama-3.3-70b-versatile-REDUCED-BUDGET"},
}


def raw_for(raw, identity):
    return [r for r in raw if r["benchmark_identity"] == identity]


def graded_for(raw, identity):
    return [grade_case(r, GOLD[r["doc_id"]]) for r in raw if r["benchmark_identity"] == identity]


def main() -> None:
    report = {}
    for identity, cfg in IDENTITIES.items():
        r1_raw_i = raw_for(R1_RAW, identity)
        r2_raw_i = raw_for(R2_RAW, cfg["round2_name"])
        r1_cases = graded_for(R1_RAW, identity)
        r2_cases = graded_for(R2_RAW, cfg["round2_name"])
        all_cases = r1_cases + r2_cases

        qm = quality_metrics(all_cases)
        om_by_round = {"round1": operational_metrics(r1_raw_i), "round2": operational_metrics(r2_raw_i)}
        econ_r1 = economics_metrics(r1_raw_i, CONFIRMED_COSTS.get((identity, "round1")))
        econ_r2 = economics_metrics(r2_raw_i, CONFIRMED_COSTS.get((identity, "round2")))
        repro = reproducibility_flags(r1_cases, r2_cases)
        dv = document_level_variance(all_cases)

        structural_reason = None
        if identity == "groq-llama-3.3-70b-versatile":
            n_usable = sum(1 for c in all_cases if c["success"] and c["structured_output_success"]
                          and c["n_facts_returned"] > 0)
            if n_usable == 0:
                structural_reason = (
                    "zero usable structured extractions across two independent task "
                    "configurations (identical-task Round 1, reduced-budget Round 2) -- "
                    "account TPM ceiling makes this task shape structurally unworkable "
                    "without a paid tier upgrade")

        label, reason = classify_provider(
            identity=identity, quality=qm, operational_by_round=om_by_round,
            reproducibility_flags_list=repro, is_control=cfg["is_control"],
            structural_disable_reason=structural_reason)

        report[identity] = {
            "quality": qm, "operational_by_round": om_by_round,
            "economics_round1": econ_r1, "economics_round2": econ_r2,
            "reproducibility_flags": repro, "document_level_variance": dv,
            "classification": label, "classification_reason": reason,
        }
        print(f"=== {identity} ===")
        print(f"  classification: {label}")
        print(f"  reason: {reason}")
        print(f"  quality: n_scoreable={qm['n_scoreable']} confidence={qm['confidence']} "
             f"numeric_acc={qm['numeric_accuracy']} hallucination={qm['hallucination_rate']} "
             f"catastrophic={qm['catastrophic_error_count']}")
        print(f"  operational: R1_success_rate={om_by_round['round1']['success_rate']} "
             f"R2_success_rate={om_by_round['round2']['success_rate']}")
        print(f"  reproducibility_flags: {repro}")
        print()

    out_path = ROOT / "data" / "staging" / "provider_decision_layer_2026-08-14.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
