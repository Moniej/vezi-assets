"""LIM-5 Priority 1: training-data quality audit across every registered
dataset type. Reuses LIM-1's already-computed audit_report.json (duplicate
rate, grounding/citation integrity, confidence/quality-score/evidence-tier
distributions, class balance) rather than recomputing any of it -- this
script adds exactly two NEW dimensions LIM-1 never computed:

  - token-length distribution: how long the formatted training text is,
    per example (matters directly for max_seq_length choices and for
    understanding how much of the sequence's information the model must
    actually process for each type).
  - label consistency: groups examples by their CONTEXT signature (what
    the model actually sees as input) and flags groups where the SAME
    context maps to DIFFERENT expected_output -- the exact generalized
    form of the entity_recognition-v1.0.0 defect found in LIM-4 (39/39
    examples sharing one context with 39 different answers). Every
    dataset type gets checked for this now, not just the one that
    happened to be trained on.

Read-only against the registry and already-exported JSONL; no training,
no model loading.

  lim_training/venv/Scripts/python.exe scripts/lim/audit_training_data.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.lim import dataset_loader, registry  # noqa: E402
from ngxrot.lim.training import _format_example_text  # noqa: E402

REGISTERED_TYPES = [
    "contradiction_detection", "corporate_actions", "coverage_assessment",
    "entity_recognition", "event_understanding", "evidence_ranking", "extraction",
    "hallucination_detection", "investment_decision_support", "knowledge_graph_completion",
    "rag", "retrieval", "self_critique",
]


def _context_signature(ex: dict) -> str:
    return json.dumps(ex.get("context", {}), sort_keys=True, default=str)


def _label_consistency(examples: list[dict]) -> dict:
    by_context = defaultdict(list)
    for ex in examples:
        by_context[_context_signature(ex)].append(ex)
    n_distinct_contexts = len(by_context)
    collision_groups = {ctx: exs for ctx, exs in by_context.items() if len(exs) > 1}
    inconsistent_groups = 0
    n_examples_in_inconsistent_groups = 0
    for ctx, exs in collision_groups.items():
        outputs = {json.dumps(e.get("expected_output", {}), sort_keys=True, default=str) for e in exs}
        if len(outputs) > 1:
            inconsistent_groups += 1
            n_examples_in_inconsistent_groups += len(exs)
    return {
        "n_examples": len(examples),
        "n_distinct_contexts": n_distinct_contexts,
        "n_collision_groups": len(collision_groups),
        "n_inconsistent_groups": inconsistent_groups,
        "n_examples_in_inconsistent_groups": n_examples_in_inconsistent_groups,
        "worst_collision_group_size": max((len(v) for v in collision_groups.values()), default=0),
    }


def _token_length_distribution(examples: list[dict], tokenizer) -> dict:
    lengths = []
    for ex in examples:
        text = _format_example_text(ex, tokenizer.eos_token)
        lengths.append(len(tokenizer(text)["input_ids"]))
    if not lengths:
        return {"n": 0}
    return {
        "n": len(lengths), "mean": round(statistics.mean(lengths), 1),
        "median": statistics.median(lengths), "min": min(lengths), "max": max(lengths),
        "p95": sorted(lengths)[int(len(lengths) * 0.95) - 1] if len(lengths) > 1 else lengths[0],
        "pct_over_256": round(100 * sum(1 for l in lengths if l > 256) / len(lengths), 1),
    }


def main():
    con_lim = registry.init_registry()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(ROOT / "lim_training" / "qwen3_4b_model"))

    report = {}
    for dataset_type in REGISTERED_TYPES:
        try:
            resolved, examples = dataset_loader.load_examples(con_lim, dataset_type)
        except dataset_loader.DatasetNotReadyError as e:
            report[dataset_type] = {"error": str(e)}
            continue
        meta = registry.get_version(con_lim, resolved)
        audit_path = Path(meta["accepted_path"]).parent / "audit_report.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))["audit"]

        report[dataset_type] = {
            "version": resolved,
            "n_accepted": meta["n_accepted"],
            "n_rejected": meta["n_rejected"],
            "acceptance_rate": audit.get("acceptance_rate"),
            "quality_score": audit.get("quality_score_distribution"),
            "evidence_tier_distribution": audit.get("evidence_tier_distribution"),
            "grounding_integrity": audit.get("grounding_integrity"),
            "citation_integrity": audit.get("citation_integrity"),
            "class_balance": audit.get("class_balance_by_fact_type"),
            "duplicate_rate": audit.get("duplicate_detection", {}).get("duplicate_rate"),
            "company_distribution": audit.get("company_distribution", {}).get("n_distinct_tickers"),
            "token_length": _token_length_distribution(examples, tokenizer),
            "label_consistency": _label_consistency(examples),
        }

    out_path = ROOT / "docs" / "lim_runs" / "lim5_dataset_audit.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Written to {out_path}\n")

    print(f"{'type':30s} {'n_acc':>6s} {'n_rej':>6s} {'acc%':>6s} {'qscore':>7s} "
         f"{'ground':>7s} {'cite':>6s} {'dup%':>6s} {'tok_mean':>9s} {'tok_p95':>8s} "
         f"{'dist_ctx':>9s} {'incons_grp':>10s} {'worst_coll':>10s}")
    for t, r in report.items():
        if "error" in r:
            print(f"{t:30s} REFUSED: {r['error']}")
            continue
        q = r["quality_score"]["mean"] if r["quality_score"] else None
        lc = r["label_consistency"]
        tl = r["token_length"]
        print(f"{t:30s} {r['n_accepted']:6d} {r['n_rejected']:6d} "
             f"{(r['acceptance_rate'] or 0)*100:5.1f}% {str(q):>7s} "
             f"{str(r['grounding_integrity']):>7s} {str(r['citation_integrity']):>6s} "
             f"{(r['duplicate_rate'] or 0)*100:5.1f}% {tl.get('mean','-'):>9} {tl.get('p95','-'):>8} "
             f"{lc['n_distinct_contexts']:9d} {lc['n_inconsistent_groups']:10d} "
             f"{lc['worst_collision_group_size']:10d}")


if __name__ == "__main__":
    main()
