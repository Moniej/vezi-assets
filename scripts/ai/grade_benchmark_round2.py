"""Grades Round 2 results and produces a Round 1 vs Round 2 comparison.
Reuses grade_case/aggregate/composite_score from grade_benchmark.py
UNCHANGED -- identical grading logic for both rounds is required for the
comparison to mean anything.

  PYTHONPATH=src python scripts/ai/grade_benchmark_round2.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from grade_benchmark import GOLD, aggregate, composite_score, grade_case  # noqa: E402

ROUND1_RESULTS = ROOT / "data" / "staging" / "benchmark_results_2026-08-13.json"
ROUND2_RESULTS = ROOT / "data" / "staging" / "benchmark_results_round2_2026-08-13.json"


def grade_all(results_path: Path) -> dict:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    by_identity = defaultdict(list)
    graded = []
    for r in results:
        gold_spec = GOLD[r["doc_id"]]
        case = grade_case(r, gold_spec)
        case["ticker"] = r.get("ticker")
        graded.append(case)
        by_identity[r["benchmark_identity"]].append(case)
    out = {}
    for identity, cases in by_identity.items():
        agg = aggregate(cases)
        out[identity] = {**agg, "composite_score": composite_score(agg)}
    return out, graded


def main() -> None:
    r1_agg, r1_cases = grade_all(ROUND1_RESULTS)
    r2_agg, r2_cases = grade_all(ROUND2_RESULTS)

    print("=== Round 2 aggregate by identity ===\n")
    for identity, agg in sorted(r2_agg.items(), key=lambda x: -(x[1]["composite_score"] or 0)):
        print(f"--- {identity} --- composite={agg['composite_score']}")
        for k, v in agg.items():
            print(f"    {k}: {v}")
        print()

    print("\n=== Round 1 vs Round 2 (shared identities only) ===\n")
    shared = set(r1_agg) & set(r2_agg)
    comparison = {}
    for identity in sorted(shared):
        a1, a2 = r1_agg[identity], r2_agg[identity]
        comparison[identity] = {"round1": a1, "round2": a2}
        print(f"{identity}:")
        print(f"  composite:        R1={a1['composite_score']}  R2={a2['composite_score']}")
        print(f"  success_rate:     R1={a1['success_rate']}  R2={a2['success_rate']}")
        print(f"  numeric_accuracy: R1={a1['numeric_accuracy']}  R2={a2['numeric_accuracy']}")
        print(f"  period_accuracy:  R1={a1['period_accuracy']}  R2={a2['period_accuracy']}")
        print(f"  evidence_accuracy:R1={a1['evidence_accuracy']}  R2={a2['evidence_accuracy']}")
        print(f"  hallucination:    R1={a1['hallucination_rate']}  R2={a2['hallucination_rate']}")
        print(f"  catastrophic:     R1={a1['catastrophic_error_count']}  R2={a2['catastrophic_error_count']}")
        print(f"  median_latency_ms:R1={a1['median_latency_ms']}  R2={a2['median_latency_ms']}")
        print()

    # ELLAHLAKES reproducibility check (the mandatory case)
    print("=== ELLAHLAKES (doc 11122) Round 1 vs Round 2, per identity ===")
    r1_ell = {c["identity"]: c for c in r1_cases if c["doc_id"] == 11122}
    r2_ell = {c["identity"]: c for c in r2_cases if c["doc_id"] == 11122}
    for identity in sorted(set(r1_ell) | set(r2_ell)):
        c1, c2 = r1_ell.get(identity), r2_ell.get(identity)
        print(f"  {identity}: "
             f"R1 success={c1['success'] if c1 else 'N/A'} structured_ok={c1['structured_output_success'] if c1 else 'N/A'} numeric={c1['numeric_correct'] if c1 else 0}/{c1['numeric_total'] if c1 else 0}  |  "
             f"R2 success={c2['success'] if c2 else 'N/A'} structured_ok={c2['structured_output_success'] if c2 else 'N/A'} numeric={c2['numeric_correct'] if c2 else 0}/{c2['numeric_total'] if c2 else 0}")

    out = {"round1_aggregate": r1_agg, "round2_aggregate": r2_agg,
          "comparison_shared_identities": comparison,
          "round1_cases": r1_cases, "round2_cases": r2_cases}
    (ROOT / "data" / "staging" / "benchmark_round1_vs_round2_2026-08-13.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("\nWrote comparison to data/staging/benchmark_round1_vs_round2_2026-08-13.json")


if __name__ == "__main__":
    main()
