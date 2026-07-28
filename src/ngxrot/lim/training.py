"""Reproducible, auditable QLoRA training orchestration (owner directive,
LIM-2, 2026-07-28). Not a quality-optimization pass -- "the objective of
LIM-2 is to establish a completely reproducible, auditable fine-tuning
pipeline built on immutable datasets." Every requirement is enforced here,
not merely documented:

  - example data comes ONLY from dataset_loader.py (registered, integrity
    -verified JSONL) -- this module never touches ngx.sqlite or any
    intermediate file itself;
  - a run's full identity (dataset versions + content hashes, teacher
    model ids, base model, quantization/LoRA config, hyperparameters,
    seed, git commit, reference-environment lock-file hash) is written to
    the immutable training_runs registry BEFORE any training step runs;
  - every checkpoint is logged as an append-only training_run_events row,
    so a checkpoint directory can always be traced back to the exact run
    that produced it (training_registry.run_for_checkpoint);
  - a dataset that fails its readiness check aborts the ENTIRE run before
    a single GPU cycle is spent, per the owner's "refuse to start
    training" instruction.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ngxrot.lim import dataset_loader, training_registry

PKG_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINTS_ROOT = PKG_ROOT / "lim_training" / "runs"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PKG_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001 -- git metadata is informational, never fatal
        return None


def _format_example_text(ex: dict, eos_token: str) -> str:
    """Generic instruction/context/response formatting -- works across all
    17 canonical dataset-schema shapes without a per-type branch, since
    every TrainingExample already carries the same instruction/context/
    expected_output fields regardless of task."""
    import json as _json
    return (f"### Instruction:\n{ex['instruction']}\n\n"
           f"### Context:\n{_json.dumps(ex.get('context', {}), default=str)}\n\n"
           f"### Response:\n{_json.dumps(ex.get('expected_output', {}), default=str)}{eos_token}")


class _JsonlExampleDataset:
    """Plain torch.utils.data.Dataset over already-loaded, already
    -verified canonical examples -- NOT huggingface `datasets` (see LIM-0's
    R-DATASETS-DILL finding: that library's construction paths are broken
    on this Python 3.14 stack at Unsloth's pinned version ceiling)."""

    def __init__(self, examples: list[dict], tokenizer, max_length: int):
        import torch
        self._torch = torch
        self.encoded = []
        for ex in examples:
            text = _format_example_text(ex, tokenizer.eos_token)
            enc = tokenizer(text, truncation=True, max_length=max_length, padding="max_length")
            enc["labels"] = list(enc["input_ids"])
            self.encoded.append(enc)

    def __len__(self):
        return len(self.encoded)

    def __getitem__(self, idx):
        return {k: self._torch.tensor(v) for k, v in self.encoded[idx].items()}


def run_training(
    con_lim, con_train, *, dataset_specs: list[tuple[str, str | None]], base_model: str,
    quantization_config: dict, lora_config: dict, hyperparameters: dict, seed: int,
    max_seq_length: int = 256, notes: str = "",
) -> dict:
    """`con_lim` is the dataset-version registry connection (lim_training/
    dataset_registry.sqlite); `con_train` is the SEPARATE training-run
    registry connection (lim_training/training_registry.sqlite) -- two
    different SQLite databases, never the same connection object.

    Raises dataset_loader.DatasetNotReadyError (propagated, never
    swallowed) if any requested dataset isn't ready -- this happens BEFORE
    `training_registry.start_run` is ever called, so an aborted-for-bad
    -data attempt leaves no run record at all (nothing was actually
    attempted)."""
    manifest = dataset_loader.load_training_set(con_lim, dataset_specs)

    run_id = training_registry.start_run(
        con_train, dataset_versions=manifest["dataset_versions"],
        dataset_content_hashes=manifest["content_hashes"],
        teacher_model_ids=manifest["teacher_model_ids"], base_model=base_model,
        quantization_config=quantization_config, lora_config=lora_config,
        hyperparameters=hyperparameters, seed=seed, git_commit=_git_commit(), notes=notes)

    run_dir = CHECKPOINTS_ROOT / run_id
    try:
        import torch
        torch.manual_seed(seed)
        from transformers import Trainer, TrainingArguments
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=base_model, max_seq_length=max_seq_length,
            load_in_4bit=quantization_config.get("load_in_4bit", True), dtype=None)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = FastLanguageModel.get_peft_model(
            model, r=lora_config["r"], lora_alpha=lora_config.get("lora_alpha", lora_config["r"] * 2),
            lora_dropout=lora_config.get("lora_dropout", 0.0),
            target_modules=lora_config.get("target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
            use_gradient_checkpointing=lora_config.get("gradient_checkpointing", "unsloth"),
            random_state=seed)

        examples = manifest["examples"]
        n_eval = max(1, len(examples) // 10)
        train_examples, eval_examples = examples[n_eval:], examples[:n_eval]
        train_ds = _JsonlExampleDataset(train_examples, tokenizer, max_seq_length)
        eval_ds = _JsonlExampleDataset(eval_examples, tokenizer, max_seq_length)

        args = TrainingArguments(
            output_dir=str(run_dir), seed=seed,
            per_device_train_batch_size=hyperparameters.get("batch_size", 1),
            gradient_accumulation_steps=hyperparameters.get("gradient_accumulation_steps", 4),
            gradient_checkpointing=True, bf16=True,
            max_steps=hyperparameters.get("max_steps", 20),
            save_steps=hyperparameters.get("save_steps", 10), save_total_limit=5,
            eval_strategy="steps", eval_steps=hyperparameters.get("save_steps", 10),
            logging_steps=1, report_to=["tensorboard"], optim="adamw_8bit",
            learning_rate=hyperparameters.get("learning_rate", 2e-4), disable_tqdm=True,
        )
        trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)
        result = trainer.train()

        for ckpt in sorted(run_dir.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1])):
            step = int(ckpt.name.split("-")[1])
            training_registry.log_event(con_train, run_id, event_type="checkpoint", step=step,
                                        checkpoint_path=str(ckpt))

        eval_metrics = trainer.evaluate()
        training_registry.log_event(con_train, run_id, event_type="eval",
                                    step=trainer.state.global_step, metrics=eval_metrics)
        training_registry.log_event(
            con_train, run_id, event_type="completed", step=trainer.state.global_step,
            metrics={"final_loss": result.training_loss, **eval_metrics})

        return {"run_id": run_id, "final_loss": result.training_loss,
               "eval_metrics": eval_metrics, "run_dir": str(run_dir),
               "n_train": len(train_examples), "n_eval": len(eval_examples)}
    except Exception as e:  # noqa: BLE001 -- a failed run must still be recorded, then re-raised
        training_registry.log_event(con_train, run_id, event_type="failed",
                                    metrics={"error": repr(e)})
        raise
