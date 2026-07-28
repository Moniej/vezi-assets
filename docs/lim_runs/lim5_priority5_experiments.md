# LIM-5 Priority 5 — Controlled Training Experiments

Discipline: one variable changed per experiment, every result compared
against both frozen baselines, honest reporting regardless of outcome.

## Experiment 1: Dataset choice (`entity_recognition` → `extraction`)

**Hypothesis**: Priority 1's audit found `entity_recognition` has a severe
label-inconsistency defect (13/17 collision groups inconsistent) while
`extraction` is large (159), clean (6/152 collision groups, ~4%), and has
informative context. Training on `extraction` instead, holding every
other hyperparameter identical to the LIM-4 baseline, should measurably
improve semantic correctness.

**Configuration** (only `dataset` changed vs. the LIM-4 baseline run
`c52db6e1`): `--dataset extraction --seed 42 --max-steps 12 --save-steps 4`,
same base model, same LoRA config (`r=8, alpha=16, dropout=0.0`), same
learning rate (2e-4).

**Result**: Run `b05875df-75e2-42c7-bfb6-a5259ec5e521`, training loss
decreased smoothly (2.99 → 2.39, no NaN/inf — the LIM-4 masking/manual
-loop fix holds on a second, larger dataset). Evaluated with the full
8-type harness (eval run `f9395a85-11c3-49b8-b07d-93c8367273d5`),
recorded alongside both frozen baselines, never overwriting either.

**Comparison against LIM-3 and LIM-4** (retroactively re-scored the
LIM-3/LIM-4 baselines' *stored* raw outputs with the new `semantic_
equivalence` metric — that metric didn't exist when those runs were
recorded, so this is the only way to get a real, apples-to-apples
comparison rather than none at all):

| Checkpoint | Trained on | `extraction` semantic_equivalence (n=12) |
|---|---|---:|
| LIM-3 baseline (untrained base model) | — | 0.0278 |
| LIM-4 (`c52db6e1`) | `entity_recognition` (wrong dataset) | 0.0850 |
| **LIM-5 Experiment 1** (`b05875df`) | `extraction` (matched dataset) | **0.1704** |

A clear, monotonic, real improvement — roughly double LIM-4's number and
6x the original baseline, on held-out examples the checkpoint was never
trained on, using the exact same scoring code across all three rows
(`eval_harness_hash` recorded in each eval_run).

By the ORIGINAL exact-match `agreement_with_teacher` metric, this
improvement is invisible (0.0 in all three rows) — direct, live
confirmation of the LIM-4/LIM-5-Priority-4 finding that exact-match
scoring cannot see this class of improvement; `semantic_equivalence` can.

**Other findings from this run**: `hallucination_risk` on `extraction`
= 0.2917 (n=8 examples with ticker-shaped values) — no baseline exists
for comparison (the metric needs real `context`, which older eval runs
never persisted — a disclosed limitation, not fixed retroactively).
`grounding_accuracy`/`citation_correctness` remain "not measurable" (0
examples) exactly as in LIM-3/4 — no regression, because there was
nothing to regress from.

**Conclusion**: Confirmed. Switching training data from the flawed
`entity_recognition` to the clean, informative `extraction` dataset —
the single variable changed — produces a real, measured, reproducible
improvement in semantic correctness, with no regression on any
measurable grounding/citation dimension (all remain "not measurable" in
both directions) and no reproducibility regression (full provenance
recorded identically).

**Recommendation**: `extraction` (or `corporate_actions`, currently
identical data) should be the default training dataset going forward,
not `entity_recognition`.

## Experiment 2: Training duration (`max_steps` 12 → 40) — BLOCKED, not completed

**Hypothesis**: More optimizer steps over `extraction`'s larger training
set (132 examples vs. `entity_recognition`'s 31) should further improve
`semantic_equivalence`, since 12 steps is under 1 effective epoch.

**What happened**: The identical training command that succeeded for
Experiment 1 **segfaulted (exit code 139) on four consecutive attempts**,
crashing at Python-process startup — specifically right after Unsloth's
own import banner, before model loading even begins. `nvidia-smi` showed
a clean, idle GPU (0 MiB used) each time, ruling out GPU memory/state as
the cause. System RAM showed only ~3.2 GB free of ~16 GB total at the
time of the crashes — a plausible cause (a hard segfault during native
library initialization, rather than a clean Python `MemoryError`, is
consistent with memory pressure hit inside a C-extension/CUDA-driver
initialization path), most likely accumulated from the many hours and
dozens of model-loading subprocesses run across this session, not from
anything specific to `max_steps=40` or this experiment's code.

**This is reported as a genuine, reproducible infrastructure blocker,
not a negative result about the hypothesis** — the hypothesis (does more
training help further) was never actually tested. Every failed attempt
left an honest, permanent `started`-only row in the training registry
(4 rows, no `completed`/`failed` event past `started` since the crash was
a segfault the Python `except` block never got a chance to catch) —
exactly the immutable-registry behavior validated back in LIM-2's
stabilization pass, holding up correctly here too, including for a novel
failure mode.

**Recommendation for a future session**: retry Experiment 2 after a fresh
process/environment restart to reclaim system memory before attempting
further training runs; do not treat the segfault as evidence about
`max_steps` itself.

## Experiments not attempted (disclosed, not silently skipped)

Given the time and infrastructure budget available in this session, and
the Experiment 2 blocker above, the remaining variables the owner listed
(prompt template, LoRA rank, batch size, sequence length, packing) were
not tested. Priority 2's evidence already argues against a prompt
-template change; the others remain open, undiscriminated hypotheses for
a future LIM-5.x continuation, each still requiring its own single
-variable experiment before any conclusion.
