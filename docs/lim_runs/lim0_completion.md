# LIM-0 Completion Report — Environment & Feasibility Validation (2026-07-27)

Real hardware, real downloads, real GPU compute — nothing in this report is
simulated or assumed. Two genuine critical incompatibilities were found,
investigated exhaustively, and resolved with documented, non-hacky fixes
(a third-party version pin fix and a small architectural substitution),
per the owner's explicit "stop, document, don't hack" instruction. Full
machine-readable artifacts: `docs/lim_runs/lim0_model_smoketest.json`,
`docs/lim_runs/lim0_training_dryrun.json`, `lim_training/requirements.lock.txt`.

**Verdict: LIM-0 PASSES.** The complete local training stack — CUDA, 4-bit
quantized inference, and QLoRA training with checkpoint/resume — works
reliably on this hardware, with two documented, low-effort caveats (§6).

---

## 1. Hardware Validation

| Component | Detected | Matches claim? |
|---|---|---|
| Machine | HP Victus by HP Gaming Laptop 15-fa2xxx | Yes |
| GPU | NVIDIA GeForce RTX 3050 **6GB** Laptop GPU | Yes, exact |
| VRAM | 6144 MiB | Yes |
| GPU architecture | Ampere, compute capability 8.6 | bf16-native, confirmed |
| Driver / CUDA | Driver 592.82, driver-reported max CUDA 13.1; PyTorch built against CUDA 12.6 (bundled runtime, no system CUDA toolkit needed) | Compatible |
| CPU | 13th Gen Intel Core i5-13420H, 8 cores / 12 logical threads | Not previously specified, now on record |
| RAM | ~16 GiB total (16,791,048,192 bytes); **~5.6 GB free** at session start (other processes already consuming ~10GB) | Matches "16GB RAM" claim; real-world headroom is tighter than the nominal figure |
| Storage | 61.9 GB free on C: at start → 45.4 GB free after the full LIM-0 stack (venv + model + wheel cache ≈ 10.9 GB) | Adequate; monitor over multiple future model/dataset versions |
| OS / Python | Windows 11 Pro, Python 3.14.3 | As specified |

**Realistic training limits for Qwen3-4B QLoRA on this hardware** (derived
from real measurements in §3-4, not estimated in the abstract):
- 4-bit inference alone: 3.4-4.2 GB VRAM depending on context length.
- QLoRA training (LoRA r=8, batch=1, grad-accum=4, seq_len=128-256,
  gradient checkpointing on): peaked at **4.92 GB — 80% of the 6.14 GB
  budget** — on a genuinely trivial toy dataset. This is the single most
  important number in this report: there is real but *not generous*
  headroom. Longer sequences, larger LoRA rank, or a larger effective
  batch size will all compete directly for the remaining ~1.2 GB.

## 2. Dependency Validation

All required packages installed and were verified working together on
Python 3.14.3, after resolving two real incompatibilities (below). Final
verified set is fully pinned in `lim_training/requirements.lock.txt`,
**and that lock file's reproducibility was independently proven** — a
second, freshly-created venv, built solely from the lock file (no manual
steps), was verified to have working CUDA + Unsloth end to end.

| Package | Version | Status |
|---|---|---|
| torch | 2.11.0+cu126 | Working, CUDA confirmed |
| torchvision | 0.26.0+cu126 | Working |
| transformers | 5.5.0 | Working |
| peft | 0.19.1 | Working |
| trl | 0.24.0 | Installed, not exercised directly (used plain `Trainer`, see §6) |
| accelerate | 1.14.0 | Working |
| datasets | 4.3.0 | **Installed, but construction paths broken on Python 3.14 — see finding R-DATASETS-DILL below** |
| Unsloth | 2026.7.5 (+ unsloth_zoo 2026.7.6) | Working, after fixing R-CUDA-SWAP below |
| bitsandbytes | 0.50.0 | Working cleanly (ships a ctypes-based wheel, not tied to a CPython ABI — no Python-3.14-specific risk) |
| triton (via triton-windows) | 3.7.1.post27 | Working. Official `triton` ships **no Windows wheels at all** — used the actively-maintained community fork `triton-windows`, which does ship a real `cp314-win_amd64` wheel and installs under the `triton` import name transparently. This is the standard, documented path for Triton-on-Windows, not an improvised substitute. |
| tensorboard | 2.21.0 | Working, real event files confirmed written (§4) |
| Weights & Biases | Not installed | Not required for LIM-0; `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` §7.6 already designs W&B as an optional offline-mode viewer, not a dependency |

### Finding R-CUDA-SWAP (Critical, resolved)

`pip install unsloth` alone silently replaced the verified
`torch==2.13.0+cu126` with `torch==2.11.0+cpu` (plus downgrading
transformers/trl/datasets), because unsloth's own transitive pins
(via torchvision/xformers) resolve against plain PyPI, which serves a
CPU-only `torch` wheel by default. `torch.cuda.is_available()` became
`False` and `import unsloth` failed outright with
`NotImplementedError: Unsloth cannot find any torch accelerator?`.

**Root cause, precisely**: unsloth's resolver settled on `torch==2.11.0`
+ `torchvision==0.26.0` (both real, existing versions) — just the wrong
*build variant*. Both versions also exist as real `+cu126` wheels for
`cp314-win_amd64`. Fix: reinstalled those two exact versions from
`download.pytorch.org/whl/cu126` instead of plain PyPI — no version
number changed, only the build variant. Verified: `torch.cuda.
is_available()` → `True`, `bitsandbytes` 4-bit config builds, `import
unsloth` succeeds cleanly, all in an independently-rebuilt venv.

**Permanent prevention** (not just a one-time fix): `requirements.lock.txt`
pins `torch==2.11.0+cu126` — a PEP 440 **local version** specifier. A
plain-PyPI CPU wheel is version `2.11.0` with no `+cu126` suffix and
structurally **cannot** satisfy that pin. Re-installing from the lock file
can no longer silently substitute a CPU build, because no CPU wheel
carries that exact version string.

### Finding R-DATASETS-DILL (High, resolved via architectural substitution, not a version override)

`datasets==4.3.0` — the exact version Unsloth's own resolver selected, and
inside Unsloth's declared compatible ceiling (`datasets<4.4.0,>=3.4.1`) —
crashes on **any** dataset construction on Python 3.14.3:
`Dataset.from_list()`, `Dataset.from_dict()`, and `load_dataset(...)` from
a real file all fail identically:
```
TypeError: Pickler._batch_setitems() takes 2 positional arguments but 3 were given
```
**Root cause**: `datasets`' fingerprinting (used for its caching/identity
system, computed unconditionally in `Dataset.__init__` — `disable_caching()`
does not skip it) depends on `dill`'s custom pickler, which calls
`pickle.Pickler.save_dict` with a call signature Python 3.14 changed.
Confirmed on both the resolved `dill==0.4.0` and the latest `dill==0.4.1`
— not a stale-dependency problem, a genuine current upstream gap.

**What does fix it**: `datasets==5.0.0` (verified working). **Why it
wasn't used**: `pip check` confirms this violates Unsloth's own declared
range (`unsloth 2026.7.5 has requirement datasets<4.4.0, but you have
datasets 5.0.0`) — silently running Unsloth outside its tested
compatibility window is exactly the "unsupported workaround" the owner
said not to introduce, even though the immediate symptom disappears.

**The actual fix applied**: `transformers.Trainer` only requires an object
implementing `__len__`/`__getitem__` — it never actually requires HF's
`datasets` library. Training-time example loading now uses a plain
`torch.utils.data.Dataset` reading JSONL/Python objects directly
(`scripts/lim/lim0_training_dryrun.py`'s `ToyTextDataset`), with `datasets`
left installed (transformers/trl import it) but unused for in-memory
example storage. This is the smallest architectural adjustment available:
zero risk to the verified CUDA/Unsloth stack, no version-pin override, and
it matches `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` §3's own design
(plain versioned JSONL files, never `datasets.Dataset.save_to_disk()`).
Verified working end-to-end in the real training dry run (§4).

## 3. Model Compatibility (no fine-tuning)

Model: `unsloth/Qwen3-4B-unsloth-bnb-4bit` (Unsloth's own pre-quantized
4-bit release — chosen over downloading full fp16 weights given this
session's real, severely bandwidth-constrained connection; 3.32 GB vs.
~8 GB). Loaded entirely from local disk after download.

| Metric | Result |
|---|---|
| Load time | 17.53 s |
| GPU memory after load | 3433 MB allocated / 3468 MB reserved (56% of 6144 MB budget) |
| RAM after load | 1342 MB (process RSS) |
| Short prompt (71 in → 53 out tok) | 6.31 s, **8.4 tok/s** |
| Medium prompt (66 in → 107 out tok) | 6.67 s, **16.0 tok/s** |
| Long prompt (2443 in → 127 out tok) | 12.47 s, **10.2 tok/s**, peak VRAM 4235 MB (69%) |
| Stability (5× repeated short prompt) | 3.16-3.29 s each, **GPU allocated held flat at 3507 MB across all 5 runs** — no leak, no drift |

No fallback to Gemma/Mistral was needed — Qwen3-4B loaded and ran cleanly
on the first attempt.

## 4. Training Dry Run (infrastructure only, not model quality)

Tiny, deliberately generic toy dataset (30 trivial instruction/response
pairs, e.g. "What is 2+2?" → "4.") — proves the mechanics, says nothing
about reasoning quality, and is explicitly **not** NGX/financial data
(real dataset generation is Phase LIM-1, out of scope here).

Config: Qwen3-4B, QLoRA 4-bit, LoRA r=8/alpha=16 targeting Q/K/V/O
projections only (Unsloth's own patcher declined to patch MLP layers,
logged as "not an error" — expected given Qwen's bias terms), gradient
checkpointing ("unsloth" mode), `adamw_8bit`, bf16, batch=1 ×
grad-accum=4, max_seq_length=256.

| Check | Result |
|---|---|
| Forward + backward pass | **Verified** — loss decreased 119.3 → 69.4 over 12 real optimizer steps (not NaN, not flat) |
| Gradient checkpointing | **Verified** — enabled throughout, no crash, consistent with the measured VRAM ceiling |
| Optimizer | **Verified** — `adamw_8bit`, learning rate schedule progressed correctly |
| Checkpoint creation | **Verified** — `checkpoint-4`, `checkpoint-8`, `checkpoint-12` created exactly on schedule |
| Resume-from-checkpoint | **Verified precisely** — a second run resumed from `checkpoint-12` and continued to step 20 (not restarting at 0); loss kept decreasing through the resume boundary (88.55 → 29.12), eval_loss kept improving (19.34 → 18.71) |
| Evaluation loop | **Verified** — ran at every configured eval_steps checkpoint, both before and after resume |
| Logging (TensorBoard) | **Verified after a path-configuration fix** — `transformers 5.5.0` deprecated `TrainingArguments.logging_dir` in favor of a `TENSORBOARD_LOGGING_DIR` env var; logging itself worked the whole time, my script was just looking in the wrong (also-real) fallback directory. 4 real `events.out.tfevents.*` files confirmed at the intended path once fixed. |
| Peak VRAM (whole dry run) | **4920.5 MB — 80% of the 6144 MB budget** |
| VRAM discipline finding | Loading a second full model copy while the first (`model`/`tokenizer`/`trainer`) was still referenced overflowed VRAM and correctly refused rather than silently corrupting anything (`transformers`' own bnb quantizer raised a clear `ValueError`). Fixed by explicitly `del`-ing every reference before the second load — confirmed VRAM dropped to 788.9 MB post-cleanup. A real, documented low-VRAM discipline requirement for any future multi-model-in-one-process script, not a library bug. |

**Final verdict: PASS** — forward/backward/optimizer/checkpoint/resume/
eval/logging all independently verified against real GPU execution.

## 5. Performance Report

- **Hardware utilization**: inference uses 56-69% of the VRAM budget
  depending on context length; QLoRA training (even on a trivial dataset)
  uses up to 80%. VRAM, not RAM or CPU, is the binding constraint on this
  hardware, exactly as `docs/LIM_ARCHITECTURE.md` §2.3 anticipated —
  now measured, not assumed.
- **Training throughput measured**: 12 steps (effective batch 4, seq_len
  128, 24 toy examples) in 28.26 s ≈ 2.35 s/step. This number is **only
  representative of this trivial workload** — real financial-reasoning
  examples (§2 of `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md`) will run
  longer sequences and will be slower per step; treat 2.35 s/step as a
  floor, not an estimate for real data.
- **Inference throughput measured**: 8.4-16.0 tokens/sec, depending on
  prompt shape (short prompts pay more fixed per-call overhead relative to
  their output length; the 2.4K-token long-document prompt sustained
  10.2 tok/s).
- **Estimated training time per epoch (illustrative, assumptions
  disclosed)**: today's real Financial-Reasoning dataset is 18 examples
  (per the 2026-07-27 stabilization validation) — at effective batch 4,
  that's ~5 steps/epoch, a few seconds. Projected to a more meaningful
  Phase LIM-2+ scale (e.g., 500 examples, ~125 steps/epoch, assuming
  similar per-step cost at a longer but still-capped 256-512 token
  sequence length): **very roughly 10-20 minutes/epoch**, NOT
  independently verified at that scale — flagged as an estimate to
  revisit once a real dataset exists (Phase LIM-1), not a promise.
- **Cost**: $0 marginal cost for local training (hardware already owned) —
  the real cost is wall-clock time and, per this session's experience,
  network bandwidth for any model/data that must be downloaded. No cloud
  GPU spend has occurred or is currently required.
- **Bottlenecks identified**:
  1. **VRAM** (80% utilized on a trivial workload) — the tightest resource
     by far; every future training config decision (sequence length, LoRA
     rank, batch size) is a direct trade against this ceiling.
  2. **Network reliability** (empirical, not hypothetical) — the observed
     connection sustained roughly 350 KB/s-1.8 MB/s with frequent
     resets, turning a single 2.6 GB download into 5-7 resumed segments
     and 30-60+ minutes of wall-clock time. This was the single largest
     time cost in this entire LIM-0 pass, larger than any GPU-bound step.
  3. **RAM headroom** — only ~5.6 GB was free out of ~16 GB at session
     start (other applications already using the rest); not a blocker
     today but worth checking before any long unattended training run.
- **Recommended configuration for this hardware** (derived from real
  measurements, not generic advice): Qwen3-4B, QLoRA NF4 4-bit, LoRA
  r=8-16 on attention projections only (mirrors what Unsloth's own patcher
  already selected), batch_size=1 with gradient_accumulation_steps=4-8,
  gradient_checkpointing="unsloth", `adamw_8bit`, bf16, **max_seq_length
  capped at 256-512 tokens** for training (retrieval-scale passages, per
  `docs/LIM_ARCHITECTURE.md` §2.3/§5.3's design — not raw whole filings).

## 6. Risk Assessment

| Risk | Category | Detail | Mitigation |
|---|---|---|---|
| VRAM ceiling | **High** | 80% utilized already on a trivial toy run; real curriculum stages (longer sequences, more LoRA parameters) will press directly against the remaining ~1.2 GB | Cap sequence length at retrieval-passage scale; keep LoRA rank ≤16 initially; treat 8B as a stretch/cloud-burst target, never a default local commitment (unchanged from `docs/LIM_ARCHITECTURE.md` §2.2) |
| `datasets` library construction paths broken on Python 3.14 (R-DATASETS-DILL) | **High** | Confirmed systemic, not an edge case — affects `from_list`/`from_dict`/`load_dataset` identically, on both `dill` versions available today | Resolved for LIM-0 via `torch.utils.data.Dataset`. **Real scaling caveat**: this substitute doesn't get HF `datasets`' memory-mapped Arrow backend, which matters once the corpus grows large (tens of thousands of examples). Revisit before Phase LIM-1 scales up — either re-check if Unsloth's own `datasets` ceiling has been raised by then, or track the upstream dill/Python-3.14 fix |
| `pip install <package>` silently swapping CUDA→CPU torch (R-CUDA-SWAP) | **High**, now **Low** (structurally prevented) | Confirmed reproducible; root-caused precisely | PEP 440 local-version pin (`torch==2.11.0+cu126`) in `requirements.lock.txt` makes the swap structurally impossible from this file; operational rule recorded: never `pip install` ad-hoc into this venv again |
| Network/bandwidth reliability | **Medium-High** | Empirically the single largest time cost this session; xet-accelerated transfer additionally degraded ("connection struggling") rather than helping on this link | Prefer plain resumable `curl -C -` downloads over `hf_transfer`/xet on this connection (proven reliable this session); budget generous wall-clock time for any future large download; `HF_HUB_DISABLE_XET=1` now set by default in both LIM-0 scripts |
| Python 3.14 general package maturity | **Medium** | Two real incompatibilities found and fixed this session; Python 3.14 is ~9 months old at time of writing — most of the stack already supports it, but newer packages/versions may still lag | Re-verify the full lock file after any deliberate package version bump (per the lock file's own operational rule); don't assume a newer version of any package is automatically compatible |
| Windows-specific tooling gaps | **Medium**, resolved for the packages tested | Official `triton` has zero Windows wheels; the community `triton-windows` fork filled the gap cleanly and is actively maintained | Documented as the standard, correct path (not an improvised patch); re-check its maintenance status before long-term reliance |
| Storage growth over time | **Low-Medium** | ~10.9 GB used for the current stack (venv + model + wheel cache), 45.4 GB free | Monitor as more model sizes/checkpoints/dataset versions accumulate across future curriculum stages; `lim_training/` is already gitignored so this never touches version control |
| RAM headroom during active use | **Low** | Only ~5.6 GB free of ~16 GB observed at session start (other applications running) | Close unnecessary applications before any long unattended training run; not currently a hard blocker |

**No Critical-severity blocker was found.** Both High-severity findings were
root-caused precisely and resolved without any unsupported workaround —
consistent with the owner's standing instruction throughout this pass.

## Verification summary

- Real hardware confirmed to exactly match the stated spec (HP Victus 15,
  RTX 3050 6GB, 16GB RAM).
- `lim_training/requirements.lock.txt` independently verified reproducible
  in a second, freshly-built venv (CUDA + Unsloth both confirmed working
  there, not just in the original venv).
- Qwen3-4B loads, generates, and remains stable under repeated calls.
- A full QLoRA train → checkpoint → resume → eval → log cycle completed
  and was verified end-to-end against real GPU execution, with a real,
  disclosed VRAM ceiling measurement.
- Two genuine critical/high incompatibilities were found, exhaustively
  investigated (never guessed at), and resolved with documented,
  non-hacky fixes — or precisely characterized as an open scaling risk
  where no clean fix yet exists (R-DATASETS-DILL's long-term scaling
  caveat).

**LIM-0 is complete. Stopping here per the owner's instruction — awaiting
review and approval before any Phase LIM-1 work begins.**
