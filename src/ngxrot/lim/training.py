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

import json
import subprocess
import tomllib
from pathlib import Path

from ngxrot.lim import dataset_loader, training_registry

PKG_ROOT = Path(__file__).resolve().parents[3]
DEFAULTS_CONFIG_PATH = PKG_ROOT / "configs" / "lim_training_defaults.toml"

# Frozen per RB-2's formal closure (docs/lim_runs/rb2_closure.md,
# 2026-07-29) -- r=8 over r=16 (retired) and r=32 (eliminated) via 10 real
# training runs, 4-seed replication, effect-size analysis, and
# significance testing. Same fallback-if-config-missing pattern as
# audit.py's DEFAULT_THRESHOLDS -- the TOML file is the source of truth;
# these constants exist only so a missing/corrupt config file degrades to
# the same values rather than an unrelated default.
DEFAULT_LORA_CONFIG = {
    "r": 8, "lora_alpha": 16, "lora_dropout": 0.0,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "gradient_checkpointing": "unsloth",
}
DEFAULT_QUANTIZATION_CONFIG = {"load_in_4bit": True, "quant_type": "nf4"}
DEFAULT_TRAINING_HYPERPARAMETERS = {
    "max_steps": 40, "save_steps": 10, "learning_rate": 2e-4,
    "batch_size": 1, "gradient_accumulation_steps": 4, "max_seq_length": 256,
}
DEFAULT_BASE_MODEL = "lim_training/qwen3_4b_model"


def load_training_defaults(path: Path = DEFAULTS_CONFIG_PATH) -> dict:
    """Returns {"lora", "quantization", "training", "base_model"} --
    the frozen production baseline every future experiment (RB-3 onward)
    must use unless its own single independent variable IS one of these
    fields, in which case the override must be explicit (a CLI flag),
    never a silent change to what "default" means."""
    if not path.exists():
        return {"lora": DEFAULT_LORA_CONFIG, "quantization": DEFAULT_QUANTIZATION_CONFIG,
                "training": DEFAULT_TRAINING_HYPERPARAMETERS, "base_model": DEFAULT_BASE_MODEL}
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        "lora": raw.get("lora", DEFAULT_LORA_CONFIG),
        "quantization": raw.get("quantization", DEFAULT_QUANTIZATION_CONFIG),
        "training": raw.get("training", DEFAULT_TRAINING_HYPERPARAMETERS),
        "base_model": raw.get("model", {}).get("base_model", DEFAULT_BASE_MODEL),
    }
CHECKPOINTS_ROOT = PKG_ROOT / "lim_training" / "runs"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PKG_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001 -- git metadata is informational, never fatal
        return None


def _schema_hint_line(ex: dict) -> str:
    """RB-3a Phase 2 (docs/lim_runs/rb3a_phase2_preregistration.md): derived
    at runtime from THIS example's own `expected_output` KEY NAMES only --
    never its values. Does not change dataset contents and does not leak
    the example's specific answer, since the key set is identical across
    every example of a given dataset type (confirmed by RB-3a's audit for
    self_critique: 104/104). Equivalent to a fixed task-format instruction,
    not per-example information."""
    keys = list(ex.get("expected_output", {}).keys())
    return f"### Required JSON keys:\n{keys}\n\n" if keys else ""


# RB-3b (docs/lim_runs/rb3b_experimental_design.md): scoped per-task, not
# generic across all 17 dataset shapes -- only self_critique currently has
# a known, governed, small categorical vocabulary problem. Verified before
# RB-3b's run that these field names are the only two self_critique fields
# needing this treatment (`finding`, `resulting_status`) -- `explanation`
# is free text and has no fixed vocabulary to hint.
_VALUE_HINT_FIELDS = {"self_critique": ("finding", "resulting_status")}


def _compute_value_hint_texts(examples: list[dict]) -> dict[str, str]:
    """RB-3b: derived ONCE from a full example set's OWN observed
    expected_output values (never per single example -- one example only
    carries one legal value, not the full domain). Verified before this
    experiment that the observed training-set values agree exactly with
    the governed source (self_critique.py's `_SEVERITY` dict and its two
    reachable resulting_status branches) -- see rb3b_experimental_
    design.md section 3. Caller must always compute this from the
    TRAINING split specifically (never validation/test), and reuse the
    identical resulting dict everywhere a value hint is needed for a given
    run, so training and evaluation never derive two different hints."""
    by_task: dict[str, dict[str, set]] = {}
    for ex in examples:
        fields = _VALUE_HINT_FIELDS.get(ex.get("task"))
        if not fields:
            continue
        out = ex.get("expected_output", {})
        bucket = by_task.setdefault(ex["task"], {f: set() for f in fields})
        for field in fields:
            if field in out:
                bucket[field].add(out[field])
    texts = {}
    for task, field_values in by_task.items():
        lines = [f"{field}: one of {sorted(values)}" for field, values in field_values.items() if values]
        if lines:
            texts[task] = "### Field value constraints:\n" + "\n".join(lines) + "\n\n"
    return texts


def _format_example_text(ex: dict, eos_token: str, schema_hint: bool = False,
                         value_hint_text: str = "") -> str:
    """Generic instruction/context/response formatting -- works across all
    17 canonical dataset-schema shapes without a per-type branch, since
    every TrainingExample already carries the same instruction/context/
    expected_output fields regardless of task. `schema_hint` is the RB-3a
    Phase 2 single-variable toggle -- default False keeps every other
    experiment's prompt shape byte-identical to before this was added.
    `value_hint_text` is RB-3b's toggle (a pre-computed string, since the
    legal-value set is a property of the whole dataset, not one example)
    -- default "" is likewise a no-op for every prior experiment."""
    hint = _schema_hint_line(ex) if schema_hint else ""
    return (f"### Instruction:\n{ex['instruction']}\n\n"
           f"### Context:\n{json.dumps(ex.get('context', {}), default=str)}\n\n"
           f"{hint}"
           f"{value_hint_text}"
           f"### Response:\n{json.dumps(ex.get('expected_output', {}), default=str)}{eos_token}")


def _prompt_prefix(ex: dict, schema_hint: bool = False, value_hint_text: str = "") -> str:
    """Everything up to and including '### Response:\\n' -- the exact
    template prefix scripts/lim/run_evaluation.py also generates from
    (training and evaluation must never diverge on this shape). Used here
    to find the prompt/response TOKEN boundary for response-only loss
    masking below. `schema_hint`/`value_hint_text` must be passed
    identically at training and evaluation time for a given experiment --
    see `_format_example_text`."""
    hint = _schema_hint_line(ex) if schema_hint else ""
    return (f"### Instruction:\n{ex['instruction']}\n\n"
           f"### Context:\n{json.dumps(ex.get('context', {}), default=str)}\n\n"
           f"{hint}"
           f"{value_hint_text}"
           f"### Response:\n")


def _build_response_only_labels(enc: dict, prompt_token_count: int, unique_id: str) -> list[int]:
    """LIM-4 fix for the LIM-3 root-cause diagnosis (docs/lim_runs/
    lim3_root_cause_diagnosis.md): response-only supervision. Masks
    (label=-100) every position that is NOT the actual response span --
    both padding (attention_mask==0) AND the prompt (instruction+context+
    '### Response:\\n'). Confirmed via docs/lim_runs/lim3_root_cause_
    diagnosis.md that this tokenizer pads on the LEFT, so real content
    occupies the LAST attention_mask.sum() positions of the fixed-length
    sequence -- the prompt occupies the first prompt_token_count of those
    real positions, and the response occupies the remainder."""
    input_ids = enc["input_ids"]
    attention_mask = enc["attention_mask"]
    n_real = sum(attention_mask)
    real_start = len(input_ids) - n_real  # left-padding: pad occupies [0, real_start)
    response_start = real_start + prompt_token_count
    if response_start >= len(input_ids):
        raise ValueError(
            f"{unique_id}: truncation removed the entire response span (response would start "
            f"at token {response_start} but the sequence is only {len(input_ids)} tokens long) "
            f"-- increase max_length or shorten this example's context")
    return [-100 if i < response_start else tok for i, tok in enumerate(input_ids)]


class _JsonlExampleDataset:
    """Plain torch.utils.data.Dataset over already-loaded, already
    -verified canonical examples -- NOT huggingface `datasets` (see LIM-0's
    R-DATASETS-DILL finding: that library's construction paths are broken
    on this Python 3.14 stack at Unsloth's pinned version ceiling)."""

    def __init__(self, examples: list[dict], tokenizer, max_length: int, schema_hint: bool = False,
                value_hint_texts: dict[str, str] | None = None):
        import torch
        self._torch = torch
        self.encoded = []
        value_hint_texts = value_hint_texts or {}
        for ex in examples:
            vht = value_hint_texts.get(ex.get("task"), "")
            text = _format_example_text(ex, tokenizer.eos_token, schema_hint=schema_hint, value_hint_text=vht)
            enc = tokenizer(text, truncation=True, max_length=max_length, padding="max_length")
            prompt_token_count = len(
                tokenizer(_prompt_prefix(ex, schema_hint=schema_hint, value_hint_text=vht),
                         add_special_tokens=True)["input_ids"])
            enc["labels"] = _build_response_only_labels(enc, prompt_token_count, ex["unique_id"])
            self.encoded.append(enc)

    def __len__(self):
        return len(self.encoded)

    def __getitem__(self, idx):
        return {k: self._torch.tensor(v) for k, v in self.encoded[idx].items()}


def _manual_train_loop(trainer, args, con_train, run_id: str, *,
                       resume_from_checkpoint: str | None = None,
                       stop_at_step: int | None = None) -> float:
    """LIM-4 fix (docs/lim_runs/lim4_completion.md): bypasses `Trainer.
    train()`'s own top-level loop, which was empirically proven (not
    assumed) to produce inf/NaN loss on the very first step whenever
    `labels` contains ANY `-100` (response-only masking) -- on this exact
    transformers 5.5.0 / Unsloth 2026.7.5 combination, with this exact
    model/LoRA/quantization config. Root-cause isolation (see the
    completion report for the full experiment log): every individual
    primitive `Trainer.train()` calls -- `training_step`, `compute_loss`,
    `accelerator.clip_grad_norm_`, `optimizer.step()` -- was independently
    verified correct (real, non-NaN, DECREASING loss across steps) when
    invoked directly in this exact sequence; only the fully-automated
    `.train()` loop itself was broken, and ONLY once masked labels were
    introduced (the identical setup with the OLD unmasked labels trained
    correctly via plain `.train()`). This function reproduces the same,
    independently-validated primitive sequence by hand -- it is not a
    novel training loop, it is `Trainer.train()`'s own documented
    steps, called directly instead of through its buggy top-level
    orchestration.

    LIM-4 validation-pass addition: `resume_from_checkpoint` reuses
    Trainer's own `_load_from_checkpoint` (adapter weights),
    `_load_optimizer_and_scheduler` (optimizer.pt/scheduler.pt), and
    `_load_rng_state` (rng_state.pth) -- the same internal methods
    `Trainer.train(resume_from_checkpoint=...)` calls -- rather than the
    top-level resume API itself, which was found (validation pass) to
    crash before even reaching the buggy per-step loop, because a
    hand-constructed `TrainerState` here doesn't populate every field the
    standard resume path cross-checks (e.g. `train_batch_size`).

    `stop_at_step` lets a caller deliberately halt an intentionally-partial
    run (e.g. to produce a mid-schedule checkpoint for a resume test)
    WITHOUT changing what total-step count the LR scheduler is built for
    -- `args.max_steps` always defines the scheduler's total, `stop_at_step`
    (if given, and smaller) only controls where THIS call's loop stops.
    Conflating the two would build a scheduler for the wrong total (e.g. a
    "4-step" schedule that fully decays to LR=0 by step 4, instead of the
    correct midpoint of an 8-step schedule) -- the mistake this docstring
    exists to prevent a future caller from repeating."""
    import itertools

    from transformers.trainer_callback import TrainerState

    max_steps = args.max_steps
    save_steps = args.save_steps
    model = trainer.model

    trainer.create_optimizer_and_scheduler(num_training_steps=max_steps)
    trainer.state = TrainerState()
    trainer.state.max_steps = max_steps
    trainer.state.train_batch_size = args.train_batch_size
    trainer.current_gradient_accumulation_steps = args.gradient_accumulation_steps
    model.train()

    start_step = 0
    if resume_from_checkpoint is not None:
        trainer._load_from_checkpoint(resume_from_checkpoint, model)
        trainer._load_optimizer_and_scheduler(resume_from_checkpoint)
        trainer._load_rng_state(resume_from_checkpoint)
        prior_state = TrainerState.load_from_json(
            str(Path(resume_from_checkpoint) / "trainer_state.json"))
        start_step = prior_state.global_step
    trainer.state.global_step = start_step

    loop_end_step = stop_at_step if stop_at_step is not None else max_steps

    train_dl = trainer.get_train_dataloader()
    batch_iter = itertools.cycle(train_dl)  # repeats across epochs, like Trainer's own multi-epoch loop
    total_loss = 0.0
    for global_step in range(start_step + 1, loop_end_step + 1):
        model.zero_grad()  # once per macro-step -- gradients accumulate across the micro-batches below
        for _ in range(args.gradient_accumulation_steps):
            batch = next(batch_iter)
            prepared = trainer._prepare_inputs(batch)
            loss = trainer.training_step(model, prepared, num_items_in_batch=None)
        grad_norm = trainer.accelerator.clip_grad_norm_(model.parameters(), args.max_grad_norm)
        trainer.optimizer.step()
        trainer.lr_scheduler.step()
        trainer.state.global_step = global_step
        total_loss += loss.item()

        # LIM-4 validation-pass fix: Trainer.train() logs loss/grad_norm/lr
        # into state.log_history every `logging_steps` (which then gets
        # serialized into each checkpoint's trainer_state.json); this
        # manual loop never called trainer.log() at all, so log_history --
        # and therefore every saved checkpoint's loss curve -- was silently
        # empty. Mirrors Trainer's own per-step log record shape.
        trainer.log({
            "loss": round(loss.item(), 4),
            "grad_norm": grad_norm.item() if hasattr(grad_norm, "item") else float(grad_norm),
            "learning_rate": trainer.lr_scheduler.get_last_lr()[0],
        })

        if global_step % save_steps == 0 or global_step == loop_end_step:
            trainer.state.stateful_callbacks["TrainerControl"] = trainer.control.state()
            trainer._save_checkpoint(model, None)
            ckpt_path = str(Path(args.output_dir) / f"checkpoint-{global_step}")
            training_registry.log_event(con_train, run_id, event_type="checkpoint",
                                        step=global_step, checkpoint_path=ckpt_path)

    n_steps_run = loop_end_step - start_step
    return total_loss / n_steps_run if n_steps_run else 0.0


def run_training(
    con_lim, con_train, *, dataset_specs: list[tuple[str, str | None]], base_model: str,
    quantization_config: dict, lora_config: dict, hyperparameters: dict, seed: int,
    max_seq_length: int = 256, notes: str = "", schema_hint: bool = False, value_hint: bool = False,
) -> dict:
    """`con_lim` is the dataset-version registry connection (lim_training/
    dataset_registry.sqlite); `con_train` is the SEPARATE training-run
    registry connection (lim_training/training_registry.sqlite) -- two
    different SQLite databases, never the same connection object.

    `schema_hint` (RB-3a Phase 2, default False): the ONLY variable that
    experiment changes vs. the frozen baseline -- see
    docs/lim_runs/rb3a_phase2_preregistration.md. `value_hint` (RB-3b,
    default False): the ONLY variable RB-3b changes -- see
    docs/lim_runs/rb3b_experimental_design.md. RB-3b holds schema_hint
    fixed at True (preserving RB-3a's confirmed win as a control, not
    re-testing it) and toggles value_hint alone. Both flags are recorded
    into the immutable `hyperparameters` JSON blob so they're auditable
    per run without a registry schema change.

    Raises dataset_loader.DatasetNotReadyError (propagated, never
    swallowed) if any requested dataset isn't ready -- this happens BEFORE
    `training_registry.start_run` is ever called, so an aborted-for-bad
    -data attempt leaves no run record at all (nothing was actually
    attempted)."""
    manifest = dataset_loader.load_training_set(con_lim, dataset_specs)

    hyperparameters = {**hyperparameters, "schema_hint": schema_hint, "value_hint": value_hint}
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

        # LIM-4 fix (docs/lim_runs/lim4_completion.md): use the REAL
        # registered train/validation split (dataset_loader.load_training_
        # set already excludes the `test` split entirely) instead of the
        # previous ad hoc `examples[:len//10]` slice -- that slice trained
        # on unique_ids scripts/lim/run_evaluation.py later scored as
        # "held out" (a real, confirmed contamination bug in the first
        # LIM-2 run), because it wasn't derived from splits.json at all.
        train_examples = manifest["train_examples"]
        eval_examples = manifest["validation_examples"]
        # RB-3b: derived ONCE from train_examples specifically (never
        # validation/test), then reused identically for both train_ds and
        # eval_ds -- eval_ds is only ever used for periodic eval_loss
        # monitoring (LIM-4), never generation, but must still see the
        # same prompt shape the model was actually trained on.
        value_hint_texts = _compute_value_hint_texts(train_examples) if value_hint else {}
        train_ds = _JsonlExampleDataset(train_examples, tokenizer, max_seq_length,
                                        schema_hint=schema_hint, value_hint_texts=value_hint_texts)
        has_eval = len(eval_examples) > 0
        eval_ds = (_JsonlExampleDataset(eval_examples, tokenizer, max_seq_length,
                                       schema_hint=schema_hint, value_hint_texts=value_hint_texts)
                  if has_eval else None)

        args = TrainingArguments(
            output_dir=str(run_dir), seed=seed,
            per_device_train_batch_size=hyperparameters.get("batch_size", 1),
            gradient_accumulation_steps=hyperparameters.get("gradient_accumulation_steps", 4),
            gradient_checkpointing=False, bf16=True,
            max_steps=hyperparameters.get("max_steps", 20),
            save_steps=hyperparameters.get("save_steps", 10), save_total_limit=5,
            eval_strategy="steps" if has_eval else "no",
            eval_steps=hyperparameters.get("save_steps", 10) if has_eval else None,
            # LIM-4 note: report_to=[] (was ["tensorboard"]) -- _manual_train_loop
            # never calls trainer.log() per step (it calls training_step/clip/
            # optimizer.step() directly, bypassing _inner_training_loop entirely),
            # so no per-step scalars ever reached the TensorBoard callback anyway;
            # worse, with report_to=["tensorboard"] the callback's writer lazily
            # initialized against an unfinalized args.logging_dir (normally
            # finalized inside Trainer.train(), which this fix bypasses) and fell
            # back to torch.utils.tensorboard's own CWD-relative default, writing
            # a stray ./runs/ directory at the repo root instead of under the
            # run's own checkpoint dir. Keeping a reporting integration that's
            # both non-functional and produces a stray side effect serves no
            # purpose; removed rather than worked around.
            logging_steps=1, report_to=[], optim="adamw_8bit",
            learning_rate=hyperparameters.get("learning_rate", 2e-4), disable_tqdm=True,
        )
        trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)
        final_train_loss = _manual_train_loop(trainer, args, con_train, run_id)

        eval_metrics = trainer.evaluate() if has_eval else {}
        training_registry.log_event(con_train, run_id, event_type="eval",
                                    step=trainer.state.global_step, metrics=eval_metrics)
        training_registry.log_event(
            con_train, run_id, event_type="completed", step=trainer.state.global_step,
            metrics={"final_loss": final_train_loss, **eval_metrics})

        return {"run_id": run_id, "final_loss": final_train_loss,
               "eval_metrics": eval_metrics, "run_dir": str(run_dir),
               "n_train": len(train_examples), "n_eval": len(eval_examples)}
    except Exception as e:  # noqa: BLE001 -- a failed run must still be recorded, then re-raised
        training_registry.log_event(con_train, run_id, event_type="failed",
                                    metrics={"error": repr(e)})
        raise
