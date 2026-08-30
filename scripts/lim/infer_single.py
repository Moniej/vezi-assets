"""LIM inference subprocess entry point. Run under `lim_training/venv`
(torch/unsloth/peft live there, not in the main project environment) — this
is the process `LocalLIMProvider.complete()` (src/ngxrot/documents/
llm_providers.py) shells out to. Reuses the exact loading pattern already
proven correct in scripts/lim/verify_checkpoint_inference.py (same
FastLanguageModel.from_pretrained + PeftModel.from_pretrained shape).

Protocol: reads a JSON request from stdin, writes a JSON response to
stdout. No other I/O on stdout (all diagnostic/progress text from
unsloth/torch goes to stderr, which the caller does not parse).

  {"system_prompt": "...", "user_prompt": "...", "max_new_tokens": 2048,
   "checkpoint_dir": "..."}
  ->
  {"response_text": "...", "input_tokens": N, "output_tokens": N,
   "latency_s": F}

  lim_training/venv/Scripts/python.exe scripts/lim/infer_single.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"


def main() -> None:
    req = json.loads(sys.stdin.read())
    system_prompt = req["system_prompt"]
    user_prompt = req["user_prompt"]
    max_new_tokens = req.get("max_new_tokens", 2048)
    max_seq_length = req.get("max_seq_length", 4096)
    checkpoint_dir = req["checkpoint_dir"]

    import torch
    from peft import PeftModel
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=max_seq_length, load_in_4bit=True, dtype=None)
    model = PeftModel.from_pretrained(model, checkpoint_dir)
    FastLanguageModel.for_inference(model)

    messages = [{"role": "system", "content": system_prompt},
               {"role": "user", "content": user_prompt}]
    inputs = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        return_tensors="pt", enable_thinking=False).to("cuda")
    input_tokens = int(inputs.shape[-1])

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(inputs, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tokenizer.eos_token_id)
    latency_s = time.time() - t0
    output_tokens = int(out.shape[-1] - input_tokens)
    text = tokenizer.decode(out[0][input_tokens:], skip_special_tokens=True)

    print(json.dumps({
        "response_text": text, "input_tokens": input_tokens,
        "output_tokens": output_tokens, "latency_s": latency_s,
    }))


if __name__ == "__main__":
    main()
