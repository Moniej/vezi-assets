"""RB-3b mode-collapse investigation (docs/lim_runs/rb3b_mode_collapse_investigation.md).
Read-only diagnostic against the ALREADY-TRAINED RB-3b checkpoint -- does
NOT train or modify anything.

Two implementation attempts preceded this one and were discarded after
failing self-consistency checks (documented in rb3b_mode_collapse_
investigation.md, not repeated here as code):
  1. Reconstructing the decision-point prefix by decoding stored raw text
     and RE-TOKENIZING it -- silently produced a DIFFERENT token-id
     sequence than the one actually used, caught only because its
     reported top-1 token contradicted greedy decoding's own guarantee.
  2. Regenerating fresh and comparing against the registry's STORED
     discrete output -- revealed that generation is deterministic WITHIN
     a process (3/3 identical trials) but NOT reproducible ACROSS
     process/session boundaries for at least one example (same prompt,
     same checkpoint, different session: "pass" vs the registry's stored
     "fail") -- a genuine cross-run numerical instability (likely
     kernel-level floating-point non-associativity under 4-bit
     quantization), not a code bug. This is itself load-bearing evidence
     for the investigation (see "Cross-session stability" in the results
     doc), not something to paper over.

This version therefore does NOT try to reproduce the registry's exact
stored tokens. It regenerates all 24 examples FRESH, in this ONE session
(self-consistent by the above test), using the REAL generated token ids
throughout (no retokenization of decoded text) to locate the exact
decision step and compute: full-vocab top-1 probability/entropy at that
step (read directly from the real generation's own scores), and relative
probability among the legal candidates (real prefix ids + a freshly
-tokenized short candidate suffix -- the one unavoidable, low-risk
retokenization, isolated to a clean few-token string).

  lim_training/venv/Scripts/python.exe scripts/lim/rb3b_mode_collapse_probe.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

CHECKPOINT = ROOT / "lim_training" / "runs" / "8d265e59-3901-40e0-aa02-4a81df5dc86f" / "checkpoint-40"
BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"
EVAL_RUN_ID = "5beeee3c-a76a-4b94-ab0e-c3cbadc1d294"

FINDING_CANDIDATES = ["fail", "concern", "pass"]
STATUS_CANDIDATES = ["blocked_by_self_critique", "unvalidated_ai_interpretation"]
MAX_NEW_TOKENS = 300


def main():
    from ngxrot.lim import dataset_loader, eval_registry, registry
    from ngxrot.lim.training import _compute_value_hint_texts, _prompt_prefix

    con_lim = registry.init_registry()
    con_eval = eval_registry.init_registry()

    manifest = dataset_loader.load_training_set(con_lim, [("self_critique", "self_critique-v1.0.0")])
    value_hint_texts = _compute_value_hint_texts(manifest["train_examples"])

    r = eval_registry.get_eval_run(con_eval, EVAL_RUN_ID)
    sc_examples = [ex for ex in r["examples"] if ex["dataset_type"] == "self_critique"]
    print(f"Probing {len(sc_examples)} self_critique held-out examples against {CHECKPOINT}")

    import torch
    from peft import PeftModel
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=512, load_in_4bit=True, dtype=None)
    model = PeftModel.from_pretrained(model, str(CHECKPOINT))
    FastLanguageModel.for_inference(model)

    def find_step(gen_ids, pattern):
        """Return the generation-step index whose token COMPLETES the
        first match of `pattern` in the incrementally-decoded text, i.e.
        the step right before the field's value begins."""
        running = ""
        for step, tok_id in enumerate(gen_ids):
            running += tokenizer.decode([tok_id])
            if re.search(pattern, running):
                return step
        return None

    def full_vocab_top1_from_scores(scores, step):
        logits = scores[step][0]
        probs = torch.softmax(logits, dim=-1)
        top1_prob, top1_id = probs.max(dim=-1)
        top1_token = tokenizer.decode([top1_id.item()])
        entropy = -(probs * torch.log(probs + 1e-12)).sum().item()
        return top1_token, float(top1_prob.item()), float(entropy)

    def relative_probs_real_prefix(prefix_ids_1d_tensor, candidates, use_base_model=False):
        """prefix_ids_1d_tensor: REAL token ids (prompt + real generated
        prefix up to and including the value's opening quote) -- only the
        short candidate suffix below is freshly tokenized. use_base_model=
        True disables the LoRA adapter (peft's disable_adapter() context
        manager -- no extra model copy, no extra GPU memory) to read the
        UNTUNED base model's own prior at the identical decision point,
        testing whether fine-tuning ever overcame a pre-existing
        pretrained bias toward these specific candidate words."""
        import contextlib
        ctx = model.disable_adapter() if use_base_model else contextlib.nullcontext()
        logprobs = {}
        with ctx:
            for cand in candidates:
                cand_ids = tokenizer(cand, add_special_tokens=False)["input_ids"]
                full = torch.cat([prefix_ids_1d_tensor,
                                  torch.tensor(cand_ids, device=prefix_ids_1d_tensor.device)])
                with torch.no_grad():
                    out = model(full.unsqueeze(0))
                logits = out.logits[0]
                prefix_len = prefix_ids_1d_tensor.shape[0]
                lp = 0.0
                for i, tok_id in enumerate(cand_ids):
                    pos = prefix_len + i - 1
                    log_probs = torch.log_softmax(logits[pos], dim=-1)
                    lp += float(log_probs[tok_id].item())
                logprobs[cand] = lp
        m = max(logprobs.values())
        exps = {c: math.exp(lp - m) for c, lp in logprobs.items()}
        z = sum(exps.values())
        return {c: exps[c] / z for c in candidates}, logprobs

    results = []
    for i, ex in enumerate(sc_examples):
        uid = ex["unique_id"]
        expected = ex["expected_output"]
        stored_parsed = ex["model_output_parsed"] or {}
        prompt = _prompt_prefix(ex, schema_hint=True, value_hint_text=value_hint_texts.get("self_critique", ""))
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        prompt_len = inputs["input_ids"].shape[1]

        with torch.no_grad():
            gen_out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                                     pad_token_id=tokenizer.eos_token_id,
                                     output_scores=True, return_dict_in_generate=True)
        sequences = gen_out.sequences[0]
        scores = gen_out.scores
        gen_ids = sequences[prompt_len:].tolist()
        fresh_text = tokenizer.decode(gen_ids, skip_special_tokens=True)

        from ngxrot.lim import eval_metrics
        fresh_parsed = eval_metrics.parse_model_json(fresh_text)

        finding_step = find_step(gen_ids, r'"finding"\s*:\s*"')
        f_top1_tok, f_top1_prob, f_entropy, f_rel_probs, f_base_rel_probs = None, None, None, None, None
        if finding_step is not None and finding_step + 1 < len(scores):
            f_top1_tok, f_top1_prob, f_entropy = full_vocab_top1_from_scores(scores, finding_step + 1)
            real_prefix_ids = sequences[: prompt_len + finding_step + 1]
            f_rel_probs, _ = relative_probs_real_prefix(real_prefix_ids, FINDING_CANDIDATES)
            f_base_rel_probs, _ = relative_probs_real_prefix(real_prefix_ids, FINDING_CANDIDATES, use_base_model=True)
            # Self-consistency check: greedy decoding guarantees the top-1
            # full-vocab token IS the token actually generated next.
            actual_next_tok = tokenizer.decode([gen_ids[finding_step + 1]])
            assert f_top1_tok == actual_next_tok or f_top1_tok.strip() == actual_next_tok.strip(), (
                f"{uid}: greedy invariant violated for finding -- top1={f_top1_tok!r} "
                f"actual_next={actual_next_tok!r}")

        status_step = find_step(gen_ids, r'"resulting_status"\s*:\s*"')
        s_top1_tok, s_top1_prob, s_entropy, s_rel_probs, s_base_rel_probs = None, None, None, None, None
        if status_step is not None and status_step + 1 < len(scores):
            s_top1_tok, s_top1_prob, s_entropy = full_vocab_top1_from_scores(scores, status_step + 1)
            real_prefix_ids = sequences[: prompt_len + status_step + 1]
            s_rel_probs, _ = relative_probs_real_prefix(real_prefix_ids, STATUS_CANDIDATES)
            s_base_rel_probs, _ = relative_probs_real_prefix(real_prefix_ids, STATUS_CANDIDATES, use_base_model=True)
            actual_next_tok = tokenizer.decode([gen_ids[status_step + 1]])
            assert s_top1_tok == actual_next_tok or s_top1_tok.strip() == actual_next_tok.strip(), (
                f"{uid}: greedy invariant violated for status -- top1={s_top1_tok!r} "
                f"actual_next={actual_next_tok!r}")

        results.append({
            "unique_id": uid,
            "expected_finding": expected.get("finding"),
            "stored_generated_finding": stored_parsed.get("finding"),
            "fresh_generated_finding": (fresh_parsed or {}).get("finding") if fresh_parsed else None,
            "finding_top1_token": f_top1_tok,
            "finding_top1_prob_full_vocab": f_top1_prob,
            "finding_entropy_full_vocab": f_entropy,
            "finding_relative_probs": f_rel_probs,
            "finding_base_model_relative_probs": f_base_rel_probs,
            "expected_status": expected.get("resulting_status"),
            "stored_generated_status": stored_parsed.get("resulting_status"),
            "fresh_generated_status": (fresh_parsed or {}).get("resulting_status") if fresh_parsed else None,
            "status_top1_token": s_top1_tok,
            "status_top1_prob_full_vocab": s_top1_prob,
            "status_entropy_full_vocab": s_entropy,
            "status_relative_probs": s_rel_probs,
            "status_base_model_relative_probs": s_base_rel_probs,
        })
        print(f"[{i+1}/{len(sc_examples)}] {uid} stored_finding={stored_parsed.get('finding')} "
             f"fresh_finding={(fresh_parsed or {}).get('finding')} done")

    out_path = ROOT / "docs" / "lim_runs" / "rb3b_mode_collapse_probe_data.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {len(results)} probed examples to {out_path}")


if __name__ == "__main__":
    main()
