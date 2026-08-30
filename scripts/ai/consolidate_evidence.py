"""Final evidence consolidation across Rounds 1-3 (2026-08-14). Pure
analysis over already-collected data -- makes NO live calls. Computes the
full per-identity metrics table for docs/ai/AI_PROVIDER_CONSOLIDATED_EVIDENCE_2026-08-14.md,
including two metrics not yet covered by provider_decision.py's existing
functions (computed here, inline, per this phase's own "consolidation,
not another architecture build" instruction rather than growing the
library further):

  unit_accuracy       -- 1 - (facts with a confirmed scaling error / all
                         numeric facts checked) -- distinct from
                         numeric_accuracy's stricter exact-value-match
                         definition; a fact can be numerically imprecise
                         (wrong column, off by a few percent) without
                         having the catastrophic 1000x/1e6x unit defect.
  ambiguity_handling   -- correctness on the two deliberately hard
                         classes already in the gold set: true-negative
                         documents (STANBIC/MORISON -- correct behavior
                         is returning no fabricated facts) and genuinely
                         ambiguous period-labeled documents (AFRIPRUD/UBA
                         -- correct behavior is matching one of the
                         accepted labels OR returning null, never an
                         actively wrong label).

  PYTHONPATH=src python scripts/ai/consolidate_evidence.py
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
    classify_provider, economics_metrics, evidence_tier, operational_metrics, quality_metrics,
    reproducibility_flags)
from grade_benchmark import GOLD, grade_case  # noqa: E402

TRUE_NEGATIVE_DOCS = {452, 9530}
AMBIGUOUS_PERIOD_DOCS = {4245, 7793}  # AFRIPRUD, UBA -- tuple period_type gold entries


def load_r1():
    return json.loads((ROOT / "data/staging/benchmark_results_2026-08-13.json").read_text(encoding="utf-8"))


def load_r2():
    return json.loads((ROOT / "data/staging/benchmark_results_round2_2026-08-13.json").read_text(encoding="utf-8"))


def load_r3():
    with (ROOT / "data/staging/benchmark_results_round3_2026-08-14.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def unit_accuracy(cases: list[dict]) -> dict:
    scoreable = [c for c in cases if c["success"] and c["structured_output_success"]]
    numeric_total = sum(c["numeric_total"] for c in scoreable)
    scaling_errors = sum(
        1 for c in scoreable for e in c["catastrophic_errors"] if "scaling error" in e)
    return {"numeric_total": numeric_total, "scaling_errors": scaling_errors,
           "unit_accuracy": (1 - scaling_errors / numeric_total) if numeric_total else None}


def ambiguity_handling(raw_results: list[dict]) -> dict:
    tn_results = [r for r in raw_results if r["doc_id"] in TRUE_NEGATIVE_DOCS and r["success"]]
    tn_correct = 0
    for r in tn_results:
        parsed = r.get("parsed_response") or {}
        facts = parsed.get("facts") or []
        real_valued = [f for f in facts if f.get("numeric_value") not in (None, 0)]
        if not real_valued:
            tn_correct += 1

    amb_results = [r for r in raw_results if r["doc_id"] in AMBIGUOUS_PERIOD_DOCS and r["success"]
                  and r.get("structured_output_success")]
    amb_total, amb_correct = 0, 0
    accepted = {4245: ("Q3", "9M"), 7793: ("Q3", "9M")}
    for r in amb_results:
        parsed = r.get("parsed_response") or {}
        for f in parsed.get("facts") or []:
            if f.get("fact_type") in ("revenue", "net_profit"):
                amb_total += 1
                pt = f.get("period_type")
                if pt is None or pt in accepted.get(r["doc_id"], ()):
                    amb_correct += 1

    n = len(tn_results) + amb_total
    correct = tn_correct + amb_correct
    return {"true_negative_n": len(tn_results), "true_negative_correct": tn_correct,
           "ambiguous_period_n": amb_total, "ambiguous_period_correct": amb_correct,
           "combined_rate": (correct / n) if n else None}


def main():
    r1, r2, r3 = load_r1(), load_r2(), load_r3()
    r3_standard = [r for r in r3 if r["phase"] == "standard"]
    r3_repro = [r for r in r3 if r["phase"] == "repro_repeat"]

    # identity -> {round_label: raw results}, including Groq/GLM (R1/R2 only, not re-tested R3)
    IDENTITY_ROUNDS = {
        "gemini-control": {"round1": [r for r in r1 if r["benchmark_identity"] == "gemini-control"],
                          "round2": [r for r in r2 if r["benchmark_identity"] == "gemini-control"],
                          "round3": [r for r in r3_standard if r["benchmark_identity"] == "gemini-control"]},
        "openrouter-llama-3.3-70b-instruct": {
            "round1": [r for r in r1 if r["benchmark_identity"] == "openrouter-llama-3.3-70b-instruct"],
            "round2": [r for r in r2 if r["benchmark_identity"] == "openrouter-llama-3.3-70b-instruct"],
            "round3": [r for r in r3_standard if r["benchmark_identity"] == "openrouter-llama-3.3-70b-instruct"]},
        "cerebras-gemma-4-31b": {
            "round1": [r for r in r1 if r["benchmark_identity"] == "cerebras-gemma-4-31b"],
            "round2": [r for r in r2 if r["benchmark_identity"] == "cerebras-gemma-4-31b"],
            "round3": [r for r in r3_standard if r["benchmark_identity"] == "cerebras-gemma-4-31b"]},
        "cerebras-gpt-oss-120b": {
            "round1": [r for r in r1 if r["benchmark_identity"] == "cerebras-gpt-oss-120b"],
            "round2": [r for r in r2 if r["benchmark_identity"] == "cerebras-gpt-oss-120b"],
            "round3": [r for r in r3_standard if r["benchmark_identity"] == "cerebras-gpt-oss-120b"]},
        "cerebras-zai-glm-4.7": {
            "round1": [r for r in r1 if r["benchmark_identity"] == "cerebras-zai-glm-4.7"],
            "round2": [], "round3": []},
        "groq-llama-3.3-70b-versatile": {
            "round1": [r for r in r1 if r["benchmark_identity"] == "groq-llama-3.3-70b-versatile"],
            "round2": [r for r in r2 if r["benchmark_identity"] == "groq-llama-3.3-70b-versatile-REDUCED-BUDGET"],
            "round3": []},
    }
    CONFIRMED_COSTS = {
        ("openrouter-llama-3.3-70b-instruct", "round1"): 0.028,
        ("openrouter-llama-3.3-70b-instruct", "round2"): 0.029,
        ("openrouter-llama-3.3-70b-instruct", "round3"): 0.072,
    }

    consolidated = {}
    for identity, rounds in IDENTITY_ROUNDS.items():
        all_raw = rounds["round1"] + rounds["round2"] + rounds["round3"]
        all_cases = [grade_case(r, GOLD[r["doc_id"]]) for r in all_raw]

        qm = quality_metrics(all_cases)
        ua = unit_accuracy(all_cases)
        ah = ambiguity_handling(all_raw)
        om_by_round = {r: operational_metrics(rounds[r]) for r in rounds}
        total_attempts = len(all_raw)
        n_success_structured = sum(1 for r in all_raw if r.get("structured_output_success"))

        repro_r1_r3 = reproducibility_flags(
            [grade_case(r, GOLD[r["doc_id"]]) for r in rounds["round1"]],
            [grade_case(r, GOLD[r["doc_id"]]) for r in rounds["round3"]],
            round1_label="round 1", round2_label="round 3") if rounds["round3"] else []

        econ_total = sum(v for (i, r), v in CONFIRMED_COSTS.items() if i == identity)
        econ = economics_metrics(all_raw, confirmed_cost_usd=econ_total if econ_total else None)

        tier = evidence_tier(qm, om_by_round, repro_r1_r3)
        label, reason = classify_provider(
            identity=identity, quality=qm, operational_by_round=om_by_round,
            reproducibility_flags_list=repro_r1_r3, is_control=(identity == "gemini-control"),
            structural_disable_reason=(
                "zero usable structured extractions across two independent task configurations "
                "(identical-task Round 1, reduced-budget Round 2) -- account TPM ceiling makes this "
                "task shape structurally unworkable without a paid tier upgrade"
            ) if identity == "groq-llama-3.3-70b-versatile" and qm["n_scoreable"] == 0 else None)

        # Round 3 Category A repeat-consistency, this identity only
        repeats = defaultdict(list)
        for r in r3_repro:
            if r["benchmark_identity"] == identity:
                repeats[r["doc_id"]].append((r["success"], r.get("structured_output_success")))
        repeat_consistency = {doc: len(set(v)) == 1 for doc, v in repeats.items()}

        consolidated[identity] = {
            "total_attempts": total_attempts, "n_success_structured": n_success_structured,
            "quality": qm, "unit_accuracy": ua, "ambiguity_handling": ah,
            "operational_by_round": om_by_round, "reproducibility_flags": repro_r1_r3,
            "repeat_consistency_round3": repeat_consistency, "economics": econ,
            "evidence_tier": tier, "classification": label, "classification_reason": reason,
        }

        print(f"=== {identity} ===")
        print(f"  classification: {label}  (evidence_tier={tier})")
        print(f"  total_attempts={total_attempts} n_success_structured={n_success_structured}")
        print(f"  numeric_acc={qm['numeric_accuracy']} unit_acc={ua['unit_accuracy']} "
             f"period_acc={qm['period_accuracy']} evidence_acc={qm['evidence_accuracy']}")
        print(f"  hallucination={qm['hallucination_rate']} catastrophic={qm['catastrophic_error_count']} "
             f"ambiguity_handling={ah['combined_rate']}")
        print(f"  op success by round: " + ", ".join(f"{r}={m['success_rate']}" for r, m in om_by_round.items()))
        print(f"  cost: {econ['cost_basis']}, total={econ['confirmed_cost_usd']}, "
             f"per_validated={econ['cost_per_validated_extraction_usd']}")
        print()

    out_path = ROOT / "data" / "staging" / "consolidated_evidence_2026-08-14.json"
    out_path.write_text(json.dumps(consolidated, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
