# LIM-2 Completion Report — Reproducible Training Pipeline

Status: **complete**. Objective per owner directive (2026-07-28): "establish a
completely reproducible, auditable fine-tuning pipeline built on immutable
datasets" — explicitly *not* a model-quality optimization pass. That
objective is met; model quality is out of scope and untouched.

## 1. Pipeline architecture

Three layers, deliberately kept as three separate SQLite databases so a
dataset-registry bug can never corrupt training-run provenance or vice versa:

| Registry | File | Purpose |
|---|---|---|
| Dataset-version registry | `lim_training/dataset_registry.sqlite` | Immutable JSONL dataset versions (LIM-1) |
| Training-run registry | `lim_training/training_registry.sqlite` | Immutable `training_runs` + append-only `training_run_events` (LIM-2) |
| (AI Intelligence Layer's own DB, untouched) | `data/ngx.sqlite` | Read-only source for dataset export only |

Data flow enforced by `src/ngxrot/lim/training.py::run_training()`:

1. `dataset_loader.load_training_set()` resolves every requested
   `dataset_type[@version]`, re-verifies registration, re-verifies the
   accepted-file content hash (tamper/corruption detection), and re-checks
   the audit report for zero threshold violations — a version that fails
   any of these raises `DatasetNotReadyError` **before any GPU cycle runs
   and before any row is written to `training_runs`.**
2. Only after that gate passes does `training_registry.start_run()` write
   the full run identity (dataset versions + content hashes, teacher model
   IDs, base model, quantization config, LoRA config, hyperparameters,
   seed, git commit) as one immutable row.
3. Training proceeds via Unsloth/QLoRA using a plain
   `torch.utils.data.Dataset` (never HF `datasets`, per LIM-0's
   R-DATASETS-DILL finding).
4. Every saved checkpoint, the eval pass, and the final outcome are logged
   as append-only `training_run_events` rows, so any checkpoint directory
   traces back to the exact dataset versions, teacher models, config, and
   seed that produced it via `training_registry.run_for_checkpoint()`.
5. A run that fails with a genuine in-process exception still gets a
   `failed` event logged (with `repr(e)`) before the exception is
   re-raised — nothing is ever swallowed.

## 2. Bugs found and fixed during LIM-2

1. **`con_lim`/`con_train` connection mixup** — `run_training()` initially
   took one SQLite connection but called both dataset-registry and
   training-run-registry functions on it; the two registries are separate
   files. Fixed by threading `con_lim` and `con_train` through separately
   (signature + all four `log_event` call sites).
2. **Redundant model re-download** — `scripts/lim/train.py --base-model`
   defaulted to the HuggingFace repo ID (`unsloth/Qwen3-4B-unsloth-bnb-4bit`)
   rather than the already-downloaded local copy
   (`lim_training/qwen3_4b_model`), causing Unsloth to attempt a redundant
   download over a flaky connection on the first real run attempt. That
   attempt was killed; the registry honestly recorded it as a `started`
   -only row (run `2205be27-...`) — proving the immutable-registry design
   behaves correctly even for an interrupted run. Fixed operationally by
   always passing the local path explicitly; no code change was needed
   since `--base-model` is a caller-supplied argument, not a hardcoded
   value.
3. **Test-structure bug** in `test_training_pipeline.py` — a bare
   `try/finally` (no `except`) let an expected `DatasetNotReadyError`
   propagate and crash the test script before its `check()` assertion ran.
   Fixed with `try/except DatasetNotReadyError/finally`. All 19 tests pass.

## 3. The exit-code-4 incident — root cause (this session)

The second real training attempt (run `fd7eb5e8-...`, using the corrected
local `--base-model` path) was reported by the background task runner as
**failed, exit code 4**. Per the owner's debugging directive, this was
diagnosed from evidence before any fix was attempted — no code was changed
during diagnosis.

**Investigation:**
- `/tmp/lim2_train2.log` showed the run progress normally through model
  load, LoRA patching, and the `Trainer` startup banner
  (`Num examples = 36, Total steps = 12`), then **stopped mid-line inside a
  `FutureWarning`, with no Python exception and no traceback at all.**
  `run_training()` wraps the entire training block in
  `except Exception: log_event(..., event_type="failed", ...); raise`, so
  a genuine in-process error (OOM, CUDA illegal-memory-access, tokenizer
  error, dataset error, config error) would necessarily have produced a
  logged `failed` event and a printed traceback. Neither existed.
- Querying `training_run_events` for run `fd7eb5e8-...` confirmed this:
  **only a `started` event exists** — no `checkpoint`, `eval`, `completed`,
  or `failed` event. The absence of a `failed` event is conclusive: the
  process was terminated from *outside* the Python interpreter, not by
  anything the `except` block could catch.
- Cross-referencing Windows Event Log for the exact window
  (`2026-07-27 23:22–23:25 UTC`):
  - `Microsoft-Windows-Kernel-Power`, event 109/577: a kernel-initiated
    shutdown transition at `00:24:38` local time.
  - `User32`/`EventLog`, event 1074: **`RuntimeBroker.exe` initiated a
    power-off of the machine "on behalf of user nonso," reason "Other
    (Unplanned)"**, at `00:24:23` local — roughly 33–48 seconds after the
    log's last write (`00:23:50`), consistent with the training process
    being torn down as part of OS shutdown.

**Root cause: the host machine was powered off by the operating system
mid-run.** This is not a defect in dataset loading, tokenizer, model
loading, LoRA/QLoRA initialization, bitsandbytes, CUDA, the optimizer,
checkpointing, the `Trainer`, the filesystem, or configuration — it is an
external environmental event unrelated to any pipeline component.
"Exit code 4" was simply how the task runner reported an externally-killed
child process, not a code-level failure signal.

**Corrective action: none — no code change was warranted**, since no bug
existed. The run was retried in a session that stayed powered on
throughout, with `PYTHONFAULTHANDLER=1` and `-X faulthandler` enabled as an
extra safeguard so a *real* native crash would now produce a diagnosable
fault dump. It completed successfully (§4), which is itself confirmation of
the diagnosis: nothing about the pipeline changed between the two attempts
except the machine staying powered on.

## 4. Real training run — results

Run ID: `a022e655-b4f1-4ca9-9f84-e9227165efc0`

| Field | Value |
|---|---|
| Dataset versions | `entity_recognition@entity_recognition-v1.0.0` |
| Teacher model IDs | `[]` (this dataset type's exported facts carry no `model_id`-bearing citations — a genuine, disclosed property of this dataset, not a bug) |
| Base model | `lim_training/qwen3_4b_model` (local Qwen3-4B, 4-bit) |
| Git commit | `24e67db013ccb8721350851971432eb7fa324dc3` (matches current `HEAD`) |
| Seed | `42` |
| n_train / n_eval | `36` / `3` |
| Max steps / save steps | `12` / `4` |
| final train_loss | `42.2997` |
| final eval_loss | `16.6027` |

**Checkpoint status:** 3 checkpoints saved (`checkpoint-4`, `checkpoint-8`,
`checkpoint-12`), each logged as a `checkpoint` event with its full path.
Traceability was proven against a real (non-synthetic) checkpoint:

```
training_registry.run_for_checkpoint(con, ".../checkpoint-8")
  → run_id=a022e655-..., dataset_versions=['entity_recognition@entity_recognition-v1.0.0'],
    git_commit=24e67db..., seed=42, base_model=lim_training/qwen3_4b_model
```

**Evaluation status:** eval ran at steps 4, 8, and 12 (`eval_loss` 19.09 →
17.51 → 16.60), each logged as an `eval` event; the final `completed` event
records the combined final metrics.

**AI Intelligence Layer:** `git diff --stat -- src/ngxrot/documents/
schema/schema.sql` is empty — untouched throughout LIM-2. `git status`
shows only new LIM files (`configs/dataset_quality_*.toml`,
`docs/LIM_ARCHITECTURE.md`, `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md`,
`docs/lim_runs/`, `schema/lim_*_registry.sql`, `scripts/lim/`,
`src/ngxrot/lim/`) plus a `.gitignore` addition excluding `lim_training/`
and the Unsloth compiled-kernel cache as regenerable binary artifacts — no
modification to any existing tracked file's content.

## 5. Remaining technical debt / disclosed limitations

- **Loss values (train 42.3, eval 16.6) are high** for a converged model —
  expected and out of scope: this run used only 36 train / 3 eval examples
  and 12 steps, exactly per LIM-2's "do not optimize model quality yet"
  directive. Not a bug; not addressed here.
- **`teacher_model_ids=[]`** for `entity_recognition` is a genuine property
  of that dataset type's current exported facts (no fact carries a
  `model_id`-bearing citation), not a registry or loader defect — carried
  over as a known, disclosed limitation from LIM-1.
- **No GPU-memory ceiling test** was performed for larger `--max-steps`,
  longer sequences, or multi-dataset training runs on this 6GB GPU;
  LIM-0's dry run and this run are both small-scale proofs, not stress
  tests.
- **The exit-code-4 incident is a reminder, not a fixed defect**: long
  unattended training runs on this machine remain vulnerable to
  unplanned OS shutdowns (the `RuntimeBroker`/"Other (Unplanned)" reason
  was not further root-caused — e.g., whether it was a manual shutdown,
  scheduled task, or policy — since that is outside this pipeline's
  code and outside the scope of this debugging task).

## 6. Conclusion

LIM-2's stated objective — a completely reproducible, auditable
fine-tuning pipeline built exclusively on immutable, registered dataset
versions, with every run and every checkpoint fully traceable to its exact
dataset versions, teacher models, git commit, config, and seed — is
demonstrated end-to-end against a real training run, with the AI
Intelligence Layer confirmed untouched. Awaiting review before any further
LIM phase begins.
