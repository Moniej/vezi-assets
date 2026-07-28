"""LIM-0 Step 3: Model Compatibility smoke test (docs/LIM_ARCHITECTURE.md,
no fine-tuning). Loads the recommended base model in 4-bit, locally, and
measures GPU memory, RAM, tokens/sec, prompt latency, and stability across
several prompts representative of the reasoning pipeline's own prompt
shapes (short extraction-style vs. longer document-style). Writes a JSON
report to docs/lim_runs/lim0_model_smoketest.json.

Run with the isolated LIM venv:
  lim_training/venv/Scripts/python.exe scripts/lim/lim0_model_smoketest.py
"""

from __future__ import annotations

import gc
import json
import os
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # xet transfer client struggled
                                                    # on this connection (LIM-0
                                                    # risk finding) -- irrelevant
                                                    # once loading purely local
                                                    # files, set defensively.

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"
OUT_PATH = ROOT / "docs" / "lim_runs" / "lim0_model_smoketest.json"

PROMPTS = {
    "short_extraction_style": (
        "Extract the material fact from this filing excerpt as JSON with keys "
        "fact_type, description, numeric_value: \"The Board of Directors of "
        "TESTCO PLC is pleased to announce a final dividend of N1.90 per share "
        "for the financial year ended 31 December 2025.\""
    ),
    "medium_reasoning_style": (
        "A company just announced a dividend increase from N1.20 to N1.90 per "
        "share. Explain in 2-3 sentences what this might signal about "
        "management's confidence in future cash flow, and name one alternative "
        "explanation that would NOT imply improving fundamentals."
    ),
    "long_document_style": (
        "Summarize the key material facts in this filing, and for each one "
        "state whether it is a positive, negative, or neutral signal for "
        "shareholders: " + ("The company reported quarterly results. " * 400)
    ),
}


def gpu_mem_mb() -> dict:
    import torch
    return {
        "allocated_mb": round(torch.cuda.memory_allocated() / 1024**2, 1),
        "reserved_mb": round(torch.cuda.memory_reserved() / 1024**2, 1),
        "max_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }


def ram_mb() -> float:
    import psutil
    return round(psutil.Process(os.getpid()).memory_info().rss / 1024**2, 1)


def main():
    import torch
    torch.cuda.reset_peak_memory_stats()
    report = {"model_dir": str(MODEL_DIR), "stages": {}}

    report["stages"]["before_load"] = {"gpu": gpu_mem_mb(), "ram_mb": ram_mb()}

    t0 = time.time()
    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(MODEL_DIR),
        max_seq_length=4096,
        load_in_4bit=True,
        dtype=None,  # auto -> bf16 on this GPU
    )
    FastLanguageModel.for_inference(model)
    load_time_s = time.time() - t0

    torch.cuda.synchronize()
    report["stages"]["after_load"] = {
        "gpu": gpu_mem_mb(), "ram_mb": ram_mb(), "load_time_s": round(load_time_s, 2),
    }

    generations = {}
    for name, prompt in PROMPTS.items():
        messages = [{"role": "user", "content": prompt}]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt", enable_thinking=False,
        ).to("cuda")
        input_tokens = inputs.shape[-1]

        torch.cuda.synchronize()
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(
                inputs, max_new_tokens=128, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.cuda.synchronize()
        elapsed = time.time() - t0
        output_tokens = out.shape[-1] - input_tokens
        text = tokenizer.decode(out[0][input_tokens:], skip_special_tokens=True)

        generations[name] = {
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "latency_s": round(elapsed, 3),
            "tokens_per_second": round(output_tokens / elapsed, 2) if elapsed > 0 else None,
            "gpu_after": gpu_mem_mb(),
            "output_preview": text[:300],
        }
        print(f"[{name}] {output_tokens} tok in {elapsed:.2f}s "
              f"({output_tokens/elapsed:.1f} tok/s), input={input_tokens} tok")

    report["generations"] = generations

    # Stability check: run the short prompt N more times back-to-back, confirm
    # no crash/OOM and no unbounded VRAM growth across repeated calls.
    stability_runs = []
    prompt = PROMPTS["short_extraction_style"]
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
        return_tensors="pt", enable_thinking=False).to("cuda")
    for i in range(5):
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(inputs, max_new_tokens=64, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        torch.cuda.synchronize()
        stability_runs.append({
            "run": i, "latency_s": round(time.time() - t0, 3),
            "gpu_allocated_mb": gpu_mem_mb()["allocated_mb"],
        })
    report["stability_runs"] = stability_runs
    report["stability_verdict"] = (
        "stable" if max(r["gpu_allocated_mb"] for r in stability_runs)
        - min(r["gpu_allocated_mb"] for r in stability_runs) < 200
        else "VRAM growth observed across repeated calls -- investigate"
    )

    report["final_gpu_state"] = gpu_mem_mb()
    report["final_ram_mb"] = ram_mb()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {OUT_PATH}")
    print(json.dumps({k: v for k, v in report.items() if k != "generations"}, indent=2))


if __name__ == "__main__":
    main()
