"""Folds the Gate-2 confirmation batch (commit 2a09558,
scripts/fre/phase4_pilot_completion.py, 2026-08-15) into Gemini's pooled
evidence and recomputes its classification. Reuses grade_case/
quality_metrics/operational_metrics/evidence_tier/classify_provider
exactly as consolidate_evidence.py already does for Rounds 1-3 -- no new
scoring path invented for this batch.

Gate-2's 4 results came from the real production path
(resumable_financial_reasoning() -> cached_complete() -> llm_calls),
not the benchmark harness, so they were never written to a
benchmark_results_*.json(l) file. Reconstructed here directly from the
Gate-2 run's scratch DB (extracted_facts/llm_calls/evidence tables) into
the same raw-result shape run_benchmark*.py produces, so they can be fed
through the identical grading/pooling functions. Source scratch DB:
C:\\Users\\nonso\\AppData\\Local\\Temp\\tmpht0olmlg\\ngx_scratch.sqlite
(confirmed still on disk; queried read-only, never modified).

  PYTHONPATH=src python scripts/ai/fold_gate2_into_gemini.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot.documents.provider_decision import (  # noqa: E402
    classify_provider, evidence_tier, operational_metrics, quality_metrics, reproducibility_flags)
from grade_benchmark import GOLD, grade_case  # noqa: E402

IDENTITY = "gemini-control"

# Reconstructed directly from the Gate-2 run's scratch DB (read-only
# query, doc-id-scoped extracted_facts/evidence rows + llm_calls latency/
# token sums) -- not hand-typed from memory. Elapsed times are the
# per-document totals phase4_pilot_completion.py itself printed for this
# run (STANBIC 0.6s, ELLAHLAKES 209.3s, MORISON 9.1s, ETI 79.7s).
GATE2_RAW = [
    {
        "doc_id": 452, "benchmark_identity": IDENTITY, "success": True,
        "structured_output_success": True,
        "parsed_response": {"facts": [
            {"fact_type": "net_profit", "numeric_value": None, "period_start": None,
             "period_end": None, "period_type": None,
             "quoted_evidence": "Stanbic IBTC Group remains well capitalised, liquid and "
                                "continues to trade profitably."},
        ]},
        "latency_ms": 600, "input_tokens": 3460 + 1825, "output_tokens": 1835 + 644,
    },
    {
        "doc_id": 11122, "benchmark_identity": IDENTITY, "success": True,
        "structured_output_success": True,
        "parsed_response": {"facts": [
            {"fact_type": "revenue", "numeric_value": 146658000.0,
             "period_start": "2024-08-01", "period_end": "2025-12-31", "period_type": None,
             "quoted_evidence": "Revenue 146,658 - 146,658 -"},
            {"fact_type": "net_profit", "numeric_value": -3839656000.0,
             "period_start": "2024-08-01", "period_end": "2025-12-31", "period_type": None,
             "quoted_evidence": "Profit/(Loss) after taxation ( 3,839,656) (893,938) "
                                "( 3,830,733) ( 754,233)"},
            {"fact_type": "dividend", "numeric_value": 0.0,
             "period_start": "2024-08-01", "period_end": "2025-12-31", "period_type": None,
             "quoted_evidence": "The directors have not recommended any dividend for the "
                                "period ended 31 December 2025 because the company made a loss"},
            {"fact_type": "assets", "numeric_value": 28257351000.0,
             "period_start": None, "period_end": "2025-12-31", "period_type": "FY",
             "quoted_evidence": "Total assets 28,257,351 24,551,843 11,494,107 7,790,336"},
            {"fact_type": "liabilities", "numeric_value": 7826935000.0,
             "period_start": None, "period_end": "2025-12-31", "period_type": "FY",
             "quoted_evidence": "Total liabilities 7,826,935 2,703,344 7,746,241 2,633,309"},
            {"fact_type": "cfo", "numeric_value": -4375789000.0,
             "period_start": "2024-08-01", "period_end": "2025-12-31", "period_type": None,
             "quoted_evidence": "Net cash from/(used in) operating activities (4,375,789) "
                                "(286,138) (4,366,946) (628,482)"},
        ]},
        "latency_ms": 209300,
        "input_tokens": 42413 + 40760 + 40772 + 40739 + 40747 + 40755,
        "output_tokens": 8923 + 674 + 770 + 631 + 811 + 712,
    },
    {
        "doc_id": 9530, "benchmark_identity": IDENTITY, "success": True,
        "structured_output_success": True, "parsed_response": {"facts": []},
        "latency_ms": 9100, "input_tokens": 2935, "output_tokens": 5,
    },
    {
        "doc_id": 7867, "benchmark_identity": IDENTITY, "success": True,
        "structured_output_success": True,
        "parsed_response": {"facts": [
            {"fact_type": "revenue", "numeric_value": 1518000000.0,
             "period_start": "2023-01-01", "period_end": "2023-09-30", "period_type": "9M",
             "quoted_evidence": "Group net revenues (net interest income plus non-interest "
                                "revenue) for the first nine months of 2023 were $1,518 "
                                "million"},
            {"fact_type": "net_profit", "numeric_value": 224000000.0,
             "period_start": "2023-01-01", "period_end": "2023-09-30", "period_type": "9M",
             "quoted_evidence": "Moreover, we delivered profits attributable to ETI "
                                "shareholders of $224m, which translated to a return on "
                                "tangible shar"},
        ]},
        "latency_ms": 79700,
        "input_tokens": 28446 + 26806 + 26798, "output_tokens": 3405 + 633 + 888,
    },
]

# 7867 (ETI) has no gold spec -- it wasn't part of any prior GOLD set
# (script's own docstring: "not in the original 5"). Excluded from
# quality grading below (grade_case requires a gold spec; no ad-hoc gold
# entry is being invented here), included in operational metrics only,
# same treatment any un-graded document would get.
GATE2_GRADEABLE = [r for r in GATE2_RAW if r["doc_id"] in GOLD]
GATE2_UNGRADED_DOC_IDS = [r["doc_id"] for r in GATE2_RAW if r["doc_id"] not in GOLD]


def load_r1():
    return json.loads((ROOT / "data/staging/benchmark_results_2026-08-13.json").read_text(encoding="utf-8"))


def load_r2():
    return json.loads((ROOT / "data/staging/benchmark_results_round2_2026-08-13.json").read_text(encoding="utf-8"))


def load_r3():
    with (ROOT / "data/staging/benchmark_results_round3_2026-08-14.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    r1 = [r for r in load_r1() if r["benchmark_identity"] == IDENTITY]
    r2 = [r for r in load_r2() if r["benchmark_identity"] == IDENTITY]
    r3_standard = [r for r in load_r3() if r["phase"] == "standard" and r["benchmark_identity"] == IDENTITY]

    print("=== BEFORE (Rounds 1-3 pooled, pre-Gate-2) ===")
    cases_before = [grade_case(r, GOLD[r["doc_id"]]) for r in r1 + r2 + r3_standard]
    qm_before = quality_metrics(cases_before)
    om_before = {"round1": operational_metrics(r1), "round2": operational_metrics(r2),
                "round3": operational_metrics(r3_standard)}
    repro_before = reproducibility_flags(
        [grade_case(r, GOLD[r["doc_id"]]) for r in r1],
        [grade_case(r, GOLD[r["doc_id"]]) for r in r3_standard],
        round1_label="round 1", round2_label="round 3")
    tier_before = evidence_tier(qm_before, om_before, repro_before)
    label_before, reason_before = classify_provider(
        identity=IDENTITY, quality=qm_before, operational_by_round=om_before,
        reproducibility_flags_list=repro_before, is_control=True)
    print(f"  n_scoreable={qm_before['n_scoreable']} confidence={qm_before['confidence']} "
         f"catastrophic={qm_before['catastrophic_error_count']} "
         f"tn_violations={qm_before['true_negative_violations']}")
    print(f"  tier={tier_before}  label={label_before}")
    print(f"  reason: {reason_before}")
    print()

    print("=== AFTER (Rounds 1-3 + Gate-2 batch pooled) ===")
    all_raw = r1 + r2 + r3_standard + GATE2_RAW
    all_gradeable_raw = r1 + r2 + r3_standard + GATE2_GRADEABLE
    cases_after = [grade_case(r, GOLD[r["doc_id"]]) for r in all_gradeable_raw]
    qm_after = quality_metrics(cases_after)
    om_after = {"round1": operational_metrics(r1), "round2": operational_metrics(r2),
               "round3": operational_metrics(r3_standard),
               "gate2": operational_metrics(GATE2_RAW)}
    repro_after = reproducibility_flags(
        [grade_case(r, GOLD[r["doc_id"]]) for r in r1],
        [grade_case(r, GOLD[r["doc_id"]]) for r in r3_standard],
        round1_label="round 1", round2_label="round 3")
    # Gate-2's own ELLAHLAKES result, checked directly against round1/round3
    # for a flip -- not a new function, same reproducibility_flags() call,
    # just an additional pairwise check since Gate-2 is a genuinely new
    # round with its own attempt at the mandatory case.
    gate2_case_11122 = grade_case(
        next(r for r in GATE2_RAW if r["doc_id"] == 11122), GOLD[11122])
    repro_gate2_vs_r3 = reproducibility_flags(
        [grade_case(r, GOLD[r["doc_id"]]) for r in r3_standard], [gate2_case_11122],
        round1_label="round 3", round2_label="gate-2 batch")
    tier_after = evidence_tier(qm_after, om_after, repro_after)
    label_after, reason_after = classify_provider(
        identity=IDENTITY, quality=qm_after, operational_by_round=om_after,
        reproducibility_flags_list=repro_after, is_control=True)
    print(f"  n_scoreable={qm_after['n_scoreable']} confidence={qm_after['confidence']} "
         f"catastrophic={qm_after['catastrophic_error_count']} "
         f"tn_violations={qm_after['true_negative_violations']}")
    print(f"  numeric_accuracy={qm_after['numeric_accuracy']} ({qm_after['numeric_sample']})")
    print(f"  hallucination_rate={qm_after['hallucination_rate']} ({qm_after['hallucination_sample']})")
    print(f"  operational success by round: " +
         ", ".join(f"{k}={v['success_rate']}" for k, v in om_after.items()))
    print(f"  reproducibility_flags (r1 vs r3, unchanged): {repro_before}")
    print(f"  reproducibility check (r3 vs gate-2 batch, ELLAHLAKES): {repro_gate2_vs_r3}")
    print(f"  ungraded docs in this batch (no gold spec, operational-only): {GATE2_UNGRADED_DOC_IDS}")
    print(f"  tier={tier_after}  label={label_after}")
    print(f"  reason: {reason_after}")
    print()

    print(f"CHANGE: {label_before} -> {label_after}   (tier: {tier_before} -> {tier_after})")

    out = {
        "before": {"quality": qm_before, "operational_by_round": om_before,
                  "reproducibility_flags": repro_before, "evidence_tier": tier_before,
                  "classification": label_before, "reason": reason_before},
        "after": {"quality": qm_after, "operational_by_round": om_after,
                 "reproducibility_flags": repro_after,
                 "reproducibility_check_gate2_vs_round3": repro_gate2_vs_r3,
                 "ungraded_doc_ids": GATE2_UNGRADED_DOC_IDS,
                 "evidence_tier": tier_after, "classification": label_after, "reason": reason_after},
        "gate2_raw_results": GATE2_RAW,
    }
    out_path = ROOT / "data" / "staging" / "gemini_gate2_folded_classification_2026-08-15.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
