"""One-off diagnostic: check whether greedy generation is deterministic
WITHIN a single process (same model, same prompt, called twice) for the
example that showed a discrepancy against the stored eval-run result.
Not part of the permanent pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

CHECKPOINT = ROOT / "lim_training" / "runs" / "8d265e59-3901-40e0-aa02-4a81df5dc86f" / "checkpoint-40"
BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"
EVAL_RUN_ID = "5beeee3c-a76a-4b94-ab0e-c3cbadc1d294"


def main():
    from ngxrot.lim import dataset_loader, eval_registry, registry
    from ngxrot.lim.training import _compute_value_hint_texts, _prompt_prefix

    con_lim = registry.init_registry()
    con_eval = eval_registry.init_registry()
    manifest = dataset_loader.load_training_set(con_lim, [("self_critique", "self_critique-v1.0.0")])
    value_hint_texts = _compute_value_hint_texts(manifest["train_examples"])
    r = eval_registry.get_eval_run(con_eval, EVAL_RUN_ID)
    sc_examples = [ex for ex in r["examples"] if ex["dataset_type"] == "self_critique"]
    ex = sc_examples[0]
    print("unique_id:", ex["unique_id"])
    print("stored raw (first 40 chars):", repr(ex["model_output_raw"][:40]))

    import torch
    from peft import PeftModel
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=512, load_in_4bit=True, dtype=None)
    model = PeftModel.from_pretrained(model, str(CHECKPOINT))
    FastLanguageModel.for_inference(model)

    prompt = _prompt_prefix(ex, schema_hint=True, value_hint_text=value_hint_texts.get("self_critique", ""))
    print("prompt length (chars):", len(prompt))
    print("prompt hash:", hash(prompt))

    for trial in range(3):
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            gen_out = model.generate(**inputs, max_new_tokens=15, do_sample=False,
                                     pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.decode(gen_out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        print(f"trial {trial}: {text!r}")


if __name__ == "__main__":
    main()
