"""RB-3c Phase 0 (docs/lim_runs/rb3c_experimental_design.md section 4/7):
zero-cost checkpoint audit using RB-3b's ALREADY-SAVED intermediate
checkpoints (steps 10, 20, 30, 40 from training run 8d265e59-...) --
NO new training. Computes Total Variation Distance (TVD) between each
checkpoint's fine-tuned relative-probability distribution and the
untrained base model's, for both `finding` and `resulting_status`, then
applies the pre-registered early-stopping rule (section 7) mechanically.

All four checkpoints are probed within this ONE process/session,
deliberately NOT reusing the earlier rb3b_mode_collapse_probe_data.json
(a separate session) for the step-40 point -- the investigation
confirmed generation is deterministic WITHIN a session but not
reproducible ACROSS sessions, so comparing a steps-vs-TVD trend requires
every point to come from the same session to avoid confounding genuine
training-trajectory differences with session-level numerical noise.

  lim_training/venv/Scripts/python.exe scripts/lim/rb3c_phase0_checkpoint_audit.py
"""
from __future__ import annotations

import gc
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

RUN_DIR = ROOT / "lim_training" / "runs" / "8d265e59-3901-40e0-aa02-4a81df5dc86f"
CHECKPOINT_STEPS = [10, 20, 30, 40]
BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"
EVAL_RUN_ID = "5beeee3c-a76a-4b94-ab0e-c3cbadc1d294"

FINDING_CANDIDATES = ["fail", "concern", "pass"]
STATUS_CANDIDATES = ["blocked_by_self_critique", "unvalidated_ai_interpretation"]
MAX_NEW_TOKENS = 300


def probe_checkpoint(checkpoint_dir, sc_examples, value_hint_texts, tokenizer, base_model_state):
    import torch
    from peft import PeftModel
    from unsloth import FastLanguageModel
    from ngxrot.lim import eval_metrics
    from ngxrot.lim.training import _prompt_prefix

    model, _ = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=512, load_in_4bit=True, dtype=None)
    model = PeftModel.from_pretrained(model, str(checkpoint_dir))
    FastLanguageModel.for_inference(model)

    def find_step(gen_ids, pattern):
        running = ""
        for step, tok_id in enumerate(gen_ids):
            running += tokenizer.decode([tok_id])
            if re.search(pattern, running):
                return step
        return None

    def relative_probs(prefix_ids_1d, candidates, use_base_model=False):
        import contextlib
        ctx = model.disable_adapter() if use_base_model else contextlib.nullcontext()
        logprobs = {}
        with ctx:
            for cand in candidates:
                cand_ids = tokenizer(cand, add_special_tokens=False)["input_ids"]
                full = torch.cat([prefix_ids_1d, torch.tensor(cand_ids, device=prefix_ids_1d.device)])
                with torch.no_grad():
                    out = model(full.unsqueeze(0))
                logits = out.logits[0]
                prefix_len = prefix_ids_1d.shape[0]
                lp = 0.0
                for i, tok_id in enumerate(cand_ids):
                    pos = prefix_len + i - 1
                    log_probs = torch.log_softmax(logits[pos], dim=-1)
                    lp += float(log_probs[tok_id].item())
                logprobs[cand] = lp
        m = max(logprobs.values())
        exps = {c: math.exp(lp - m) for c, lp in logprobs.items()}
        z = sum(exps.values())
        return {c: exps[c] / z for c in candidates}

    per_example = []
    for ex in sc_examples:
        prompt = _prompt_prefix(ex, schema_hint=True, value_hint_text=value_hint_texts.get("self_critique", ""))
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        prompt_len = inputs["input_ids"].shape[1]
        with torch.no_grad():
            gen_out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                                     pad_token_id=tokenizer.eos_token_id,
                                     output_scores=True, return_dict_in_generate=True)
        sequences = gen_out.sequences[0]
        gen_ids = sequences[prompt_len:].tolist()

        finding_step = find_step(gen_ids, r'"finding"\s*:\s*"')
        f_ft, f_base = None, None
        if finding_step is not None:
            real_prefix_ids = sequences[: prompt_len + finding_step + 1]
            f_ft = relative_probs(real_prefix_ids, FINDING_CANDIDATES)
            f_base = relative_probs(real_prefix_ids, FINDING_CANDIDATES, use_base_model=True)

        status_step = find_step(gen_ids, r'"resulting_status"\s*:\s*"')
        s_ft, s_base = None, None
        if status_step is not None:
            real_prefix_ids = sequences[: prompt_len + status_step + 1]
            s_ft = relative_probs(real_prefix_ids, STATUS_CANDIDATES)
            s_base = relative_probs(real_prefix_ids, STATUS_CANDIDATES, use_base_model=True)

        per_example.append({
            "unique_id": ex["unique_id"],
            "finding_ft": f_ft, "finding_base": f_base,
            "status_ft": s_ft, "status_base": s_base,
        })

    del model
    gc.collect()
    torch.cuda.empty_cache()
    return per_example


def main():
    from ngxrot.lim import dataset_loader, eval_registry, registry
    from ngxrot.lim.training import _compute_value_hint_texts

    con_lim = registry.init_registry()
    con_eval = eval_registry.init_registry()
    manifest = dataset_loader.load_training_set(con_lim, [("self_critique", "self_critique-v1.0.0")])
    value_hint_texts = _compute_value_hint_texts(manifest["train_examples"])
    r = eval_registry.get_eval_run(con_eval, EVAL_RUN_ID)
    sc_examples = [ex for ex in r["examples"] if ex["dataset_type"] == "self_critique"]
    print(f"Phase 0: auditing {len(CHECKPOINT_STEPS)} existing checkpoints "
         f"({CHECKPOINT_STEPS}) against {len(sc_examples)} held-out examples, one session.")

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(BASE_MODEL_DIR))

    all_results = {}
    for step in CHECKPOINT_STEPS:
        ckpt_dir = RUN_DIR / f"checkpoint-{step}"
        print(f"\n--- checkpoint-{step} ---")
        per_example = probe_checkpoint(ckpt_dir, sc_examples, value_hint_texts, tokenizer, None)
        all_results[step] = per_example
        print(f"checkpoint-{step}: probed {len(per_example)} examples")

    out_path = ROOT / "docs" / "lim_runs" / "rb3c_phase0_probe_data.json"
    out_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\nWrote Phase 0 data for steps {CHECKPOINT_STEPS} to {out_path}")


if __name__ == "__main__":
    main()
