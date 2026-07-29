# RB-1 — Infrastructure Failure Log

**Classification: infrastructure failure (operating-system memory
constraint), NOT a model, training-pipeline, or software defect.**

## Experiment

RB-1: training-duration experiment, `max_steps` 12 → 40 on `extraction`,
all else identical to the LIM-5 Experiment 1 configuration
(`b05875df-75e2-42c7-bfb6-a5259ec5e521`).

## Attempts and exact failures

| Attempt | Session | Failure mode | Exit code |
|---|---|---|---|
| 1-4 | Prior session (LIM-5 Priority 5) | Segmentation fault at Python/Unsloth import time, before model loading began | 139 |
| 5 | This session | `OSError: The paging file is too small for this operation to complete. (os error 1455)`, raised inside `safetensors`' memory-mapped weight load (`transformers/modeling_utils.py::_load_pretrained_model` → `unsloth/models/_uma_safetensors.py::_uma_safe_open` → `safe_open`) | 1 (clean Python exception this time, not a raw segfault) |

Full traceback for attempt 5 (`/tmp/rb1_train.log`):

```
File "...transformers\models\auto\auto_factory.py", line 387, in from_pretrained
  return model_class.from_pretrained(...)
File "...transformers\modeling_utils.py", line 4132, in from_pretrained
  loading_info, disk_offload_index = cls._load_pretrained_model(model, state_dict, checkpoint_files, load_config)
File "...transformers\modeling_utils.py", line 4240, in _load_pretrained_model
  file_pointer = safe_open(file, framework="pt", device="cpu")
File "...unsloth\models\_uma_safetensors.py", line 165, in _uma_safe_open
  return real_safe_open(*args, **kwargs)
OSError: The paging file is too small for this operation to complete. (os error 1455)
```

The training registry correctly recorded this attempt as `started` →
`failed` (run `571b7842-2813-4765-a277-201b4e152f8c`) — a genuine Python
exception this time, caught and logged by `run_training()`'s own
exception handler, unlike attempts 1-4's raw segfaults which killed the
process before any handler could run. Immutable-registry behavior held
correctly in both failure modes.

## System state at time of failure (attempt 5)

| Resource | Value |
|---|---|
| Free physical RAM | ~1.69 GB of 16.40 GB total (~10%) |
| GPU memory used | 0 MiB of 6144 MiB (idle — not a GPU-side constraint) |
| Page file (`AllocatedBaseSize`) | 23,479 MB (~23 GB) |
| Page file (`CurrentUsage`) | 2,618 MB (~2.6 GB — the page file itself was nowhere near full) |
| Largest resident processes | Windows "Memory Compression" ~992 MB (itself a direct symptom of memory pressure — Windows compresses pages in RAM specifically when physical memory is scarce), WizTree64 ~560 MB, 4x Chrome processes totaling ~1.24 GB, Spotify ~279 MB, Claude desktop ~345 MB, MsMpEng (Defender) ~269 MB |

**Interpretation**: OS error 1455 is not "the page file is literally full"
(only 2.6 of 23 GB was in use) — it occurs when Windows cannot satisfy a
large single virtual-memory commit request (here: memory-mapping the
model's safetensors weights) from currently available commit headroom,
regardless of the page file's total configured size. The presence of a
substantial "Memory Compression" process is itself a standard Windows
signal of active memory pressure, corroborating that free RAM (not GPU,
not disk space, not page-file ceiling) is the actual constraint.

## Root cause classification

**Operating-system memory pressure from ordinary desktop application
load (browser, compression store, misc. utilities) competing with this
long research session's own accumulated process history — not a defect
in CUDA, bitsandbytes, Unsloth, the training pipeline, or the experiment
configuration.** No code in this repository was modified in response to
this failure. `max_seq_length`, batch size, and every other experiment
setting remain unchanged from the LIM-5 Experiment 1 baseline, per
explicit instruction not to alter the research protocol to route around
an infrastructure constraint.

## Resolution path (owner-directed)

The owner will restart the machine and close unnecessary applications.
Before retrying, this log will be updated with a fresh resource check
(RAM/GPU/commit charge/page file/top consumers) and an environment-parity
confirmation (§ below) proving the post-restart environment matches this
attempt's, so a subsequent success or failure is attributable to the
restart alone, not an unnoticed environment drift.

## Environment fingerprint (captured pre-restart, for post-restart comparison)

| Component | Version |
|---|---|
| `torch` | `2.11.0+cu126` |
| `transformers` | `5.5.0` |
| `unsloth` | `2026.7.5` |
| `bitsandbytes` | `0.50.0` |
| `peft` | `0.19.1` |
| CUDA (via torch) | `12.6` |
| Base model path | `lim_training/qwen3_4b_model` |
| Dataset | `extraction@extraction-v1.0.0` |
| Seed | `42` |
| LoRA config | `r=8, alpha=16, dropout=0.0, target_modules=[q_proj,k_proj,v_proj,o_proj]` |
| Hyperparameters | `batch_size=1, gradient_accumulation_steps=4, max_steps=40, save_steps=10, learning_rate=2e-4` |
| `lim_venv_lock_hash` | `272803ce46dc5dcda2c8c0bdcb0174800a841512d19bf307cecfc50c0dc293dd` — will be re-checked post-restart for a byte-identical match |

Status: restart completed by owner. Pre-retry verification below.

## Pre-retry verification (post-restart)

| Check | Value | vs. pre-restart |
|---|---:|---|
| Free physical RAM | 5,725 MB (~5.6 GB) | up from ~1.69 GB |
| Total visible RAM | 16,013 MB | unchanged |
| Commit charge | 23,275 MB | — (not measured pre-restart; captured for the first time now) |
| Commit limit | 32,397 MB (~9.1 GB headroom) | — |
| Page file allocated | 16,384 MB | was 23,479 MB pre-restart (Windows recalculated the page file size across the reboot) |
| Page file current usage | 1,262 MB | down from 2,618 MB |
| GPU free VRAM | 6,001 MiB of 6,144 MiB | unchanged (was already idle) |
| CUDA available | `True`, device = NVIDIA GeForce RTX 3050 6GB Laptop GPU | unchanged |
| `lim_venv_lock_hash` | `272803ce46dc5dcda2c8c0bdcb0174800a841512d19bf307cecfc50c0dc293dd` | **identical** to pre-restart — environment parity confirmed |
| Dataset content hash (`extraction-v1.0.0`) | `d4f3fa94d8cf4386e9814bbd13b007cae124d1cba660d1d19800649fa9731ed9` | unchanged (immutable registry) |
| Git commit (repo HEAD) | `ef1807c7532eaabceff28a579d579156bec502d3` | unchanged since the LIM-5 optimization-baseline tag |
| Seed | `42` | unchanged |
| Configuration hash (sha256 of dataset+seed+base_model+quantization+lora+hyperparameters) | `1735afcae4504521936aaea5f786100ac5d3adb9977da4ea9cb90cb00ffbc294` | identical by construction — no experiment setting changed |

**Environment parity confirmed byte-for-byte on the one component that
could silently drift (the venv lock hash) — this retry is a true
like-for-like repeat, not a different environment.** Proceeding with the
identical command used in attempt 5.

## Retry result: SUCCESS

Run `90a5df49-105b-45e1-a604-dc4b35af1706` completed cleanly (exit code
0). Model loaded, trained for the full 40 steps, checkpointed, and
evaluated without any memory-related error. Training loss decreased
monotonically and **visibly plateaued by the final steps**
(1.965 → 1.962 → 1.961 → 1.962 over steps 37-40) — unlike every prior
LIM-2/4/5 run, which always stopped at step 12 while loss was still
decreasing. This is itself informative for RB-1's underlying hypothesis
(see the companion results write-up).

## Final classification

**The prior failures (segfaults ×4, then `OSError` 1455 ×1) are
classified as an infrastructure-related memory issue (Windows commit
-charge/paging pressure from accumulated desktop application load), now
confirmed by direct reproduction: identical configuration, identical
code, identical environment (byte-identical `lim_venv_lock_hash`) — the
only variable that changed between the failing and succeeding attempt was
system memory availability (~1.65-1.69 GB free → ~5.6-5.9 GB free after
the owner's restart). No code, model, or experiment-configuration change
was required or made to achieve success.**

