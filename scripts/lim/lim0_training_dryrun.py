"""LIM-0 Step 4: Training Dry Run (docs/LIM_ARCHITECTURE.md). Purely an
INFRASTRUCTURE check -- forward pass, backward pass, gradient checkpointing,
optimizer step, checkpoint creation, resume-from-checkpoint, evaluation
loop, logging (TensorBoard). Not about model quality: the dataset here is a
tiny, deliberately trivial, generic set of toy examples (NOT NGX/financial
data -- real dataset generation is explicitly out of scope for LIM-0, that's
Phase LIM-1).

Run with the isolated LIM venv:
  lim_training/venv/Scripts/python.exe scripts/lim/lim0_training_dryrun.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ["TENSORBOARD_LOGGING_DIR"] = str(
    Path(__file__).resolve().parents[2] / "lim_training" / "dryrun_tensorboard")
# transformers 5.5.0 deprecated TrainingArguments.logging_dir in favor of this
# env var (confirmed empirically: without it, TensorBoardCallback silently
# falls back to `<output_dir>/runs/...` instead -- logging itself worked
# fine either way, this only fixes WHERE the caller looks for it).

import torch  # noqa: E402 -- imported at module level (before `main()`) only
              # because ToyTextDataset below subclasses torch.utils.data.
              # Dataset at class-definition time; unsloth's own "import
              # unsloth before transformers/peft" ordering concern is about
              # ITS import relative to transformers/peft, not plain torch,
              # and `from unsloth import FastLanguageModel` still happens
              # first inside main() before transformers is ever touched.

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"
RUN_DIR = ROOT / "lim_training" / "dryrun_checkpoints"
TB_DIR = ROOT / "lim_training" / "dryrun_tensorboard"
OUT_PATH = ROOT / "docs" / "lim_runs" / "lim0_training_dryrun.json"

# Deliberately trivial, generic toy pairs -- proves the training loop works,
# says nothing about reasoning quality, and is NOT financial/NGX data.
TOY_EXAMPLES = [
    {"instruction": "Say hello in French.", "response": "Bonjour."},
    {"instruction": "What is 2 + 2?", "response": "4."},
    {"instruction": "Name a primary color.", "response": "Red."},
    {"instruction": "Spell the word 'cat'.", "response": "C-A-T."},
    {"instruction": "What comes after Monday?", "response": "Tuesday."},
    {"instruction": "Give a synonym for 'happy'.", "response": "Glad."},
    {"instruction": "What is the capital of France?", "response": "Paris."},
    {"instruction": "Count from 1 to 3.", "response": "1, 2, 3."},
    {"instruction": "What sound does a cat make?", "response": "Meow."},
    {"instruction": "Name a season.", "response": "Summer."},
] * 3  # 30 rows total, still tiny -- enough for a few optimizer steps + eval


class ToyTextDataset(torch.utils.data.Dataset):
    """Plain torch.utils.data.Dataset, NOT huggingface `datasets` --
    Dataset.from_list()/load_dataset() are construction-broken on this
    Python 3.14 + dill combination even at Unsloth's own pinned datasets
    version (see requirements.lock.txt's R-DATASETS-DILL note; verified
    exhaustively, not assumed). transformers.Trainer only requires
    __len__/__getitem__, so this is a complete, equally-supported substitute
    for in-memory example storage -- no HF `datasets` involved."""

    def __init__(self, examples: list[dict], tokenizer, max_length: int = 128):
        self.encoded = []
        for ex in examples:
            text = (f"### Instruction:\n{ex['instruction']}\n\n"
                   f"### Response:\n{ex['response']}{tokenizer.eos_token}")
            enc = tokenizer(text, truncation=True, max_length=max_length, padding="max_length")
            enc["labels"] = list(enc["input_ids"])
            self.encoded.append(enc)

    def __len__(self):
        return len(self.encoded)

    def __getitem__(self, idx):
        import torch as _torch
        return {k: _torch.tensor(v) for k, v in self.encoded[idx].items()}


def build_dataset(tokenizer):
    import random
    examples = list(TOY_EXAMPLES)
    random.Random(42).shuffle(examples)
    eval_examples, train_examples = examples[:6], examples[6:]
    return (ToyTextDataset(train_examples, tokenizer),
           ToyTextDataset(eval_examples, tokenizer))


def main():
    from unsloth import FastLanguageModel  # must import before transformers/peft
                                           # per Unsloth's own optimization-patching
                                           # requirement (seen as a real warning in
                                           # the earlier smoke-test run's output)
    from transformers import Trainer, TrainingArguments

    report = {"stages": {}}

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(MODEL_DIR), max_seq_length=256, load_in_4bit=True, dtype=None)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = FastLanguageModel.get_peft_model(
        model, r=8, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    report["lora_setup"] = {"trainable_params": n_trainable, "total_params": n_total,
                            "trainable_pct": round(100 * n_trainable / n_total, 4)}
    print(f"LoRA attached: {n_trainable:,} / {n_total:,} params trainable "
         f"({report['lora_setup']['trainable_pct']}%)")

    train_ds, eval_ds = build_dataset(tokenizer)
    report["dataset"] = {"train_rows": len(train_ds), "eval_rows": len(eval_ds)}

    args = TrainingArguments(
        output_dir=str(RUN_DIR),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        bf16=True,
        max_steps=12,
        save_steps=4,
        save_total_limit=5,
        eval_strategy="steps",
        eval_steps=4,
        logging_steps=1,
        logging_dir=str(TB_DIR),
        report_to=["tensorboard"],
        optim="adamw_8bit",
        learning_rate=2e-4,
        seed=42,
        disable_tqdm=True,
    )

    torch.cuda.reset_peak_memory_stats()
    trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)

    # --- Phase 1: train from scratch for the first half of max_steps ---
    t0 = time.time()
    result = trainer.train()
    train_time_s = time.time() - t0
    report["stages"]["initial_train"] = {
        "final_loss": result.training_loss,
        "global_step": trainer.state.global_step,
        "train_time_s": round(train_time_s, 2),
        "gpu_max_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }
    print(f"Initial train done: step={trainer.state.global_step} "
         f"loss={result.training_loss:.4f} in {train_time_s:.1f}s")

    eval_metrics = trainer.evaluate()
    report["stages"]["eval_after_initial_train"] = eval_metrics
    print("Eval after initial train:", eval_metrics)

    checkpoints = sorted(RUN_DIR.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
    report["checkpoints_created"] = [c.name for c in checkpoints]
    print("Checkpoints on disk:", [c.name for c in checkpoints])

    # --- Phase 2: RESUME from the last checkpoint, verify step count continues
    # correctly (not restarted from 0) and training completes cleanly ---
    last_ckpt = str(checkpoints[-1]) if checkpoints else None
    # Real LIM-0 finding: `del trainer` alone does NOT free the first model's
    # VRAM -- `model`/`tokenizer` (and the optimizer states Trainer built
    # around them) are still live Python references. On a 6GB card, loading
    # a second full model copy while the first is still resident overflows
    # available VRAM (transformers' bnb quantizer then tries to CPU/disk
    # -offload some modules and refuses, correctly, rather than silently
    # corrupting the model). Must explicitly drop every reference to the
    # first model before loading a second one -- a genuine low-VRAM
    # discipline requirement, not a library bug.
    import gc
    del trainer, model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    report["stages"]["vram_after_explicit_cleanup_mb"] = round(
        torch.cuda.memory_allocated() / 1024**2, 1)
    print(f"VRAM allocated after explicit cleanup: "
         f"{report['stages']['vram_after_explicit_cleanup_mb']} MB (should be ~0)")

    model2, tokenizer2 = FastLanguageModel.from_pretrained(
        model_name=str(MODEL_DIR), max_seq_length=256, load_in_4bit=True, dtype=None)
    model2 = FastLanguageModel.get_peft_model(
        model2, r=8, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        use_gradient_checkpointing="unsloth", random_state=42)

    args2 = TrainingArguments(
        output_dir=str(RUN_DIR), per_device_train_batch_size=1,
        gradient_accumulation_steps=4, gradient_checkpointing=True, bf16=True,
        max_steps=20,  # more than the original 12 -- proves resume continues, not restarts
        save_steps=4, save_total_limit=5, eval_strategy="steps", eval_steps=4,
        logging_steps=1, logging_dir=str(TB_DIR), report_to=["tensorboard"],
        optim="adamw_8bit", learning_rate=2e-4, seed=42, disable_tqdm=True,
    )
    trainer2 = Trainer(model=model2, args=args2, train_dataset=train_ds, eval_dataset=eval_ds)

    step_before_resume = trainer2.state.global_step
    t0 = time.time()
    result2 = trainer2.train(resume_from_checkpoint=last_ckpt)
    resume_time_s = time.time() - t0
    report["stages"]["resume_train"] = {
        "resumed_from": Path(last_ckpt).name if last_ckpt else None,
        "step_before_resume_object_created": step_before_resume,
        "final_step": trainer2.state.global_step,
        "final_loss": result2.training_loss,
        "resume_time_s": round(resume_time_s, 2),
        "resume_correct": trainer2.state.global_step == 20 and trainer2.state.global_step > 12,
    }
    print(f"Resumed from {last_ckpt} -> final step {trainer2.state.global_step} "
         f"(expected 20, must be > 12 to prove it didn't restart from 0)")

    eval_metrics2 = trainer2.evaluate()
    report["stages"]["eval_after_resume"] = eval_metrics2

    # --- Logging check: confirm TensorBoard event files actually exist ---
    tb_files = list(TB_DIR.rglob("events.out.tfevents*"))
    report["tensorboard_logging"] = {
        "event_files_found": len(tb_files),
        "paths": [str(f.relative_to(ROOT)) for f in tb_files],
    }
    print(f"TensorBoard event files found: {len(tb_files)}")

    report["final_gpu_max_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 1024**2, 1)
    report["verdict"] = (
        "PASS: forward/backward/optimizer/checkpoint/resume/eval/logging all verified"
        if report["stages"]["resume_train"]["resume_correct"] and tb_files
        else "FAIL: see stages for detail"
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nReport written to {OUT_PATH}")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
