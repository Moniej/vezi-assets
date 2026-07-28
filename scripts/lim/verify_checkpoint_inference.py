"""LIM-2 stabilization check #1: prove a single saved checkpoint is
independently loadable and produces valid inference. Deliberately run as a
standalone process per checkpoint (see verify_checkpoints.ps1/.sh driver) --
not a loop over checkpoints in one interpreter -- so that "independently
loadable" means what it says: a fresh process, fresh CUDA context, no state
carried over from loading a previous checkpoint.

  lim_training/venv/Scripts/python.exe scripts/lim/verify_checkpoint_inference.py <checkpoint_dir>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"

PROMPT = (
    "Extract the material fact from this filing excerpt as JSON with keys "
    "fact_type, description, numeric_value: \"The Board of Directors of "
    "TESTCO PLC is pleased to announce a final dividend of N1.90 per share "
    "for the financial year ended 31 December 2025.\""
)


def main():
    if len(sys.argv) != 2:
        print("usage: verify_checkpoint_inference.py <checkpoint_dir>", file=sys.stderr)
        sys.exit(1)
    ckpt_dir = Path(sys.argv[1]).resolve()
    if not ckpt_dir.is_dir():
        print(f"FAIL: checkpoint dir does not exist: {ckpt_dir}", file=sys.stderr)
        sys.exit(1)

    import torch
    from peft import PeftModel
    from unsloth import FastLanguageModel

    t0 = time.time()
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=256, load_in_4bit=True, dtype=None)
    base_load_s = time.time() - t0

    t0 = time.time()
    model = PeftModel.from_pretrained(model, str(ckpt_dir))
    adapter_load_s = time.time() - t0

    FastLanguageModel.for_inference(model)

    messages = [{"role": "user", "content": PROMPT}]
    inputs = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        return_tensors="pt", enable_thinking=False).to("cuda")
    input_tokens = inputs.shape[-1]

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(inputs, max_new_tokens=96, do_sample=False,
                             pad_token_id=tokenizer.eos_token_id)
    gen_s = time.time() - t0
    output_tokens = out.shape[-1] - input_tokens
    text = tokenizer.decode(out[0][input_tokens:], skip_special_tokens=True)

    has_nan_or_inf = bool(torch.isnan(out.float()).any() or torch.isinf(out.float()).any())

    result = {
        "checkpoint_dir": str(ckpt_dir),
        "base_load_s": round(base_load_s, 2),
        "adapter_load_s": round(adapter_load_s, 2),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "generation_latency_s": round(gen_s, 3),
        "output_ids_finite": not has_nan_or_inf,
        "output_nonempty": output_tokens > 0,
        "output_text": text,
        "verdict": "PASS" if (output_tokens > 0 and not has_nan_or_inf) else "FAIL",
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
