"""LIM-3: evaluation harness (owner directive, 2026-07-28). "Do not
optimize the model yet. The objective is to establish an objective
benchmark for every future improvement." Evaluates ONE local checkpoint
against every registered dataset type's held-out `test` split (LIM-1's
deterministic hash-bucket split -- examples training.py never saw), scoring
each generation against the teacher's own recorded expected_output. Records
a full, immutable, per-example result set in the eval-run registry so this
run can be compared, unchanged, against every future model version.

Design note (disclosed, not hidden): "agreement with teacher" is measured
against the expected_output already captured in the dataset at export time
-- which IS the teacher model's real output for that input, produced
during the AI Intelligence Layer's own reasoning pipeline -- rather than
issuing a new live call to the teacher API. This keeps every score
reproducible from data already on disk and avoids incurring new API cost
for a benchmark that must itself be re-run after every future training
improvement. See docs/lim_runs/lim3_completion.md for the full rationale
and for which named metrics had zero eligible held-out data this run (and
why) -- nothing here is silently papered over.

  lim_training/venv/Scripts/python.exe scripts/lim/run_evaluation.py \
      --checkpoint "lim_training/runs/a022e655-b4f1-4ca9-9f84-e9227165efc0/checkpoint-12"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"

# Every dataset type currently registered (schema.TASK_TYPES minus the 4
# that failed the LIM-1 audit gate: citation_grounding, confidence_
# estimation, financial_reasoning, portfolio_reasoning -- excluded here for
# the same reason training refuses them: a version that didn't clear its
# own quality gate is not legitimate data to benchmark against either).
REGISTERED_TYPES = [
    "contradiction_detection", "corporate_actions", "coverage_assessment",
    "entity_recognition", "event_understanding", "evidence_ranking", "extraction",
    "hallucination_detection", "investment_decision_support", "knowledge_graph_completion",
    "rag", "retrieval", "self_critique",
]


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return None


def gpu_mem_mb() -> dict:
    import torch
    return {"allocated_mb": round(torch.cuda.memory_allocated() / 1024**2, 1),
            "max_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024**2, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="LoRA checkpoint directory to evaluate")
    ap.add_argument("--dataset-types", nargs="*", default=REGISTERED_TYPES)
    ap.add_argument("--max-new-tokens", type=int, default=160)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    from ngxrot.lim import eval_dataset, eval_metrics, eval_registry, registry, training_registry
    from ngxrot.lim.training import _prompt_prefix

    con_lim = registry.init_registry()
    con_train = training_registry.init_registry()
    con_eval = eval_registry.init_registry()

    print(f"Loading held-out (test-split) examples for {len(args.dataset_types)} dataset types...")
    holdouts = eval_dataset.load_all_holdout_sets(con_lim, args.dataset_types, split="test")
    for t, h in holdouts.items():
        if "error" in h:
            print(f"  {t:32s} REFUSED: {h['error']}")
        else:
            print(f"  {t:32s} n_in_split={h['n_in_split']:3d} (of {h['n_total_accepted']} accepted, "
                 f"version={h['version']})")

    all_examples = []
    for t, h in holdouts.items():
        for ex in h.get("examples", []):
            all_examples.append((t, ex))
    print(f"\nTotal held-out examples to evaluate: {len(all_examples)}")
    if not all_examples:
        print("Nothing to evaluate -- aborting.")
        sys.exit(1)

    ckpt_dir = Path(args.checkpoint).resolve()
    run_prov = training_registry.run_for_checkpoint(con_train, str(ckpt_dir))
    training_run_id = run_prov["run_id"] if run_prov else None
    print(f"\nCheckpoint: {ckpt_dir}")
    print(f"Traced to training_run_id: {training_run_id}")

    import torch
    from peft import PeftModel
    from unsloth import FastLanguageModel

    torch.cuda.reset_peak_memory_stats()
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=512, load_in_4bit=True, dtype=None)
    model = PeftModel.from_pretrained(model, str(ckpt_dir))
    FastLanguageModel.for_inference(model)

    records = []
    example_rows = []
    t_start = time.time()
    for t, ex in all_examples:
        prompt = _prompt_prefix(ex)
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        input_tokens = inputs["input_ids"].shape[-1]

        torch.cuda.synchronize()
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        torch.cuda.synchronize()
        latency_s = time.time() - t0
        output_tokens = out.shape[-1] - input_tokens
        raw_text = tokenizer.decode(out[0][input_tokens:], skip_special_tokens=True)

        parsed = eval_metrics.parse_model_json(raw_text)
        scores = eval_metrics.score_example(ex, parsed)
        records.append({"dataset_type": t, "scores": scores, "latency_s": latency_s,
                        "output_tokens": output_tokens})
        example_rows.append({
            "dataset_type": t, "unique_id": ex["unique_id"], "instruction": ex["instruction"],
            "expected_output": ex.get("expected_output", {}), "model_output_raw": raw_text,
            "model_output_parsed": parsed, "scores": scores, "latency_s": latency_s,
            "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
        })
        print(f"[{t}:{ex['unique_id']}] agreement={scores['agreement_with_teacher']:.2f} "
             f"latency={latency_s:.2f}s out_tok={output_tokens}")

    total_wall_s = time.time() - t_start
    peak_gpu = gpu_mem_mb()

    metrics = eval_metrics.aggregate_metrics(records)
    metrics["gpu_memory"] = peak_gpu
    metrics["total_wall_s"] = round(total_wall_s, 2)
    metrics["throughput_examples_per_s"] = round(len(all_examples) / total_wall_s, 4)
    metrics["holdout_coverage"] = {
        t: {"n_in_split": h.get("n_in_split", 0),
           "status": "evaluated" if h.get("n_in_split", 0) > 0 else
                     (h.get("error") or "0 examples in test split for this version")}
        for t, h in holdouts.items()
    }

    dataset_versions = {t: h["version"] for t, h in holdouts.items() if "version" in h}
    content_hashes = {h["version"]: h["content_hash"] for h in holdouts.values() if "version" in h}

    eval_run_id = eval_registry.record_eval_run(
        con_eval, subject="local_checkpoint", dataset_versions=dataset_versions,
        dataset_content_hashes=content_hashes, base_model=str(BASE_MODEL_DIR),
        n_examples_evaluated=len(all_examples), metrics=metrics, training_run_id=training_run_id,
        checkpoint_path=str(ckpt_dir), git_commit=_git_commit(), notes=args.notes)
    for row in example_rows:
        eval_registry.record_example(con_eval, eval_run_id, **row)

    print(f"\n=== Eval run {eval_run_id} recorded ({len(all_examples)} examples) ===")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
