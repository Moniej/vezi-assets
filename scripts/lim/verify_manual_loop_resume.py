"""LIM-4 validation pass: verify resume fidelity for the NEW manual training
loop (_manual_train_loop), mirroring LIM-2's checkpoint-resume stabilization
check but for the masked-label / manual-loop path. Standard `Trainer.
train(resume_from_checkpoint=...)` was found (this validation pass) to
crash before reaching the per-step loop at all, because a hand-constructed
TrainerState doesn't populate every field the standard resume path
cross-checks -- so `_manual_train_loop` gained its own
`resume_from_checkpoint` argument that reuses Trainer's own internal
`_load_from_checkpoint`/`_load_optimizer_and_scheduler`/`_load_rng_state`
methods. This script proves that resume path is faithful: an 8-step run,
uninterrupted, must be statistically indistinguishable from a 4-step run
resumed for 4 more steps.

Run as three SEPARATE processes (like LIM-2's checkpoint-inference check)
-- not three model loads in one process -- so a 6GB GPU never has to hold
more than one 4-bit model at a time, and so each phase is genuinely
independent:

  lim_training/venv/Scripts/python.exe scripts/lim/verify_manual_loop_resume.py run_a
  lim_training/venv/Scripts/python.exe scripts/lim/verify_manual_loop_resume.py run_b1
  lim_training/venv/Scripts/python.exe scripts/lim/verify_manual_loop_resume.py run_b2
  lim_training/venv/Scripts/python.exe scripts/lim/verify_manual_loop_resume.py compare
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"
SEED = 42
OUT_A = ROOT / "lim_training" / "runs" / "_verify_manual_resume_A"
OUT_B = ROOT / "lim_training" / "runs" / "_verify_manual_resume_B"


def _build_trainer(output_dir: Path, examples, max_steps: int):
    import torch
    from transformers import Trainer, TrainingArguments
    from unsloth import FastLanguageModel

    from ngxrot.lim.training import _JsonlExampleDataset

    torch.manual_seed(SEED)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=256, load_in_4bit=True, dtype=None)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = FastLanguageModel.get_peft_model(
        model, r=8, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        use_gradient_checkpointing=False, random_state=SEED)
    ds = _JsonlExampleDataset(examples, tokenizer, 256)
    args = TrainingArguments(
        output_dir=str(output_dir), seed=SEED, per_device_train_batch_size=1,
        gradient_accumulation_steps=4, gradient_checkpointing=False, bf16=True,
        max_steps=max_steps, save_steps=4, save_total_limit=5, logging_steps=1,
        report_to=[], optim="adamw_8bit", learning_rate=2e-4, disable_tqdm=True)
    return Trainer(model=model, args=args, train_dataset=ds), args


def _load_examples():
    from ngxrot.lim import dataset_loader, registry
    con_lim = registry.init_registry()
    _, examples = dataset_loader.load_examples(con_lim, "entity_recognition", "entity_recognition-v1.1.0")
    return examples[:8]


def _start_run(notes):
    from ngxrot.lim import training_registry
    con_train = training_registry.init_registry()
    run_id = training_registry.start_run(
        con_train, dataset_versions=["entity_recognition@entity_recognition-v1.1.0"],
        dataset_content_hashes={}, teacher_model_ids=[], base_model=str(BASE_MODEL_DIR),
        quantization_config={}, lora_config={}, hyperparameters={}, seed=SEED, notes=notes)
    return con_train, run_id


def run_a():
    from ngxrot.lim.training import _manual_train_loop
    con_train, run_id = _start_run("LIM-4 validation: manual-loop resume fidelity, run A (uninterrupted 8 steps)")
    trainer, args = _build_trainer(OUT_A, _load_examples(), max_steps=8)
    _manual_train_loop(trainer, args, con_train, run_id)
    print("Run A complete.")


def run_b1():
    from ngxrot.lim.training import _manual_train_loop
    con_train, run_id = _start_run("LIM-4 validation: manual-loop resume fidelity, run B step 1-4")
    # max_steps=8 here (NOT 4) -- the LR scheduler must be built for the
    # SAME total (8) as the intended full run, matching run A exactly;
    # stop_at_step=4 only controls where THIS call's loop halts. Building
    # this trainer with max_steps=4 would instead create a schedule that
    # fully decays to LR=0 by step 4 -- a different, wrong schedule for
    # what's supposed to be the first half of an 8-step run (an earlier,
    # caught mistake in this same script).
    trainer, args = _build_trainer(OUT_B, _load_examples(), max_steps=8)
    _manual_train_loop(trainer, args, con_train, run_id, stop_at_step=4)
    print("Run B1 (steps 1-4 of an 8-step schedule) complete.")


def run_b2():
    from ngxrot.lim.training import _manual_train_loop
    con_train, run_id = _start_run("LIM-4 validation: manual-loop resume fidelity, run B RESUMED steps 5-8")
    trainer, args = _build_trainer(OUT_B, _load_examples(), max_steps=8)
    ckpt4 = OUT_B / "checkpoint-4"
    _manual_train_loop(trainer, args, con_train, run_id, resume_from_checkpoint=str(ckpt4))
    print("Run B2 (resumed steps 5-8) complete.")


def compare():
    log_a = json.loads((OUT_A / "checkpoint-8" / "trainer_state.json").read_text())["log_history"]
    log_b = json.loads((OUT_B / "checkpoint-8" / "trainer_state.json").read_text())["log_history"]
    by_step_a = {e["step"]: e for e in log_a if "loss" in e}
    by_step_b = {e["step"]: e for e in log_b if "loss" in e}

    print("=== Fidelity comparison: uninterrupted steps 5-8 (run A) vs resumed steps 5-8 (run B) ===")
    all_pass = True
    for step in (5, 6, 7, 8):
        a, b = by_step_a.get(step), by_step_b.get(step)
        if a is None or b is None:
            print(f"step {step}: MISSING (a={a is not None} b={b is not None})")
            all_pass = False
            continue
        loss_relerr = abs(a["loss"] - b["loss"]) / max(abs(a["loss"]), 1e-9)
        gn_relerr = abs(a["grad_norm"] - b["grad_norm"]) / max(abs(a["grad_norm"]), 1e-9)
        lr_exact = abs(a["learning_rate"] - b["learning_rate"]) < 1e-9
        ok = loss_relerr < 5e-2 and gn_relerr < 0.5 and lr_exact
        print(f"step {step}: A loss={a['loss']:.4f} grad_norm={a['grad_norm']:.4f} lr={a['learning_rate']:.8f}")
        print(f"         B loss={b['loss']:.4f} grad_norm={b['grad_norm']:.4f} lr={b['learning_rate']:.8f}"
             f"  -> loss_relerr={loss_relerr*100:.2f}% gn_relerr={gn_relerr*100:.2f}% lr_exact={lr_exact}"
             f"  {'MATCH' if ok else 'MISMATCH'}")
        all_pass = all_pass and ok

    print(f"\nVerdict: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    {"run_a": run_a, "run_b1": run_b1, "run_b2": run_b2, "compare": compare}[sys.argv[1]]()
