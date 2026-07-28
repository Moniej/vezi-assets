# LIM-4 Validation Report

Scope: a final validation pass over LIM-4's engineering work before it
becomes the foundation for LIM-5's model-improvement experiments. Per the
owner's framing, LIM-4's objective was to improve the integrity of the
training pipeline and validate the evaluation process — not to maximize
model performance — and this report validates that objective was met, not
model quality. **No model training or optimization was performed in this
pass.**

## 1. Verified: no training path can include held-out evaluation examples

Audited every caller of the dataset-loading functions across the
repository (`grep` for `load_examples`/`load_training_set`/
`load_holdout_set`):

| Caller | Function used | Test-split exposure |
|---|---|---|
| `training.py::run_training()` (the only production training entrypoint) | `dataset_loader.load_training_set()` | Structurally excluded |
| `scripts/lim/verify_checkpoint_resume.py` (LIM-2 stabilization) | `dataset_loader.load_training_set()` | Structurally excluded (protected regardless of dataset version requested) |
| `scripts/lim/run_evaluation.py` (the evaluation harness) | `eval_dataset.load_holdout_set()` | **Deliberately reads test** — this is the correct side of the barrier |
| `scripts/lim/diagnose_training_pipeline.py` (LIM-3 read-only diagnostic) | `dataset_loader.load_examples()` directly | Not filtered, but never calls `.train()`/optimizer — no model is ever updated from this script, confirmed by inspection |
| Test scripts (`test_training_pipeline.py`) | Both, directly | Intentional — these tests validate the choke point itself |

**Conclusion: `dataset_loader.load_training_set()` is the sole path by
which example data reaches an actual gradient update, and it now
structurally excludes every `test`-split `unique_id` via the registered
`splits.json`, regardless of which dataset version is requested.** Two
regression tests (`test_load_training_set_never_returns_test_split_examples`,
`test_load_training_set_refuses_without_splits_json`) hold this in place;
both pass, along with the full existing 24-check LIM-2 suite and 32-check
LIM-1 suite.

**Residual gap found and disclosed (not fixed in this pass):**
`registry.content_hash()` — the tamper-detection mechanism `dataset_loader.
verify_dataset_ready()` checks — covers only `accepted.jsonl`, **not**
`splits.json`. The code-logic contamination bug (training reading examples
never sanctioned for training) is now structurally impossible; a *direct
file-level edit* to `splits.json` moving a `test` id into `train` would
currently go undetected, since the registry has no stored reference hash
for that file. This is a different class of risk (deliberate/accidental
file tampering, not a code-logic bug) and is recommended as LIM-5
infrastructure hardening — not fixed here because it requires a dataset
-registry schema change (an immutable table `ALTER`/migration), which is a
larger, riskier change than this validation pass's scope, and none of the
13 registered dataset versions have shown any evidence of such tampering.

## 2. Verified: manual training loop mathematical equivalence

| Component | Verification |
|---|---|
| **Optimizer** | `_manual_train_loop` calls `trainer.create_optimizer_and_scheduler()` — Trainer's own method, not reimplemented. Same AdamW8bit, same param groups. |
| **LR scheduler** | Same call creates it. Verified LR values follow the exact expected linear-decay schedule at every step, both fresh and (see below) resumed. |
| **Gradient accumulation** | Found and fixed a bug in this validation pass: an earlier draft called `model.zero_grad()` inside the micro-batch loop (erasing each micro-batch's gradient before accumulation could occur). Fixed to zero once per macro-step; verified via loss correctly decreasing across steps. |
| **Mixed precision (bf16)** | Never reimplemented — `trainer.training_step()` is called directly, which internally applies the correct autocast context. |
| **Checkpointing** | Uses `trainer._save_checkpoint()` — Trainer's own method. Structure verified identical to `Trainer.train()`-produced checkpoints (`adapter_model.safetensors`, `optimizer.pt`, `scheduler.pt`, `rng_state.pth`, `trainer_state.json`). |
| **Resume** | **New capability, added and verified in this pass** (see below) — the original LIM-4 implementation had no resume path at all. |

### The resume gap found and closed

Testing revealed the standard `Trainer.train(resume_from_checkpoint=...)`
API — which the LIM-2 stabilization check used — **crashes before even
reaching the per-step loop** when pointed at a `_manual_train_loop`
-produced checkpoint: `compare_trainer_and_checkpoint_args` reads
`trainer_state.train_batch_size`, a field the manual loop's
hand-constructed `TrainerState` never populated (`TypeError: unsupported
operand type(s) for //: 'NoneType' and 'int'`). Separately, even if that
crash were bypassed, resuming through `Trainer.train()` would still route
through the exact per-step loop already proven broken for masked labels.

Fix: `_manual_train_loop` gained a `resume_from_checkpoint` parameter that
reuses Trainer's own internal `_load_from_checkpoint` (adapter weights),
`_load_optimizer_and_scheduler` (`optimizer.pt`/`scheduler.pt`), and
`_load_rng_state` (`rng_state.pth`) — the same methods the standard resume
path calls — without going through the top-level loop that both crashes
and (separately) blows up numerically.

A second bug was found and fixed while building the verification for
this: the manual loop never called `trainer.log()`, so `state.log_history`
— and therefore every checkpoint's `trainer_state.json` — silently carried
no loss curve at all (a real parity gap with `Trainer.train()`, which logs
every step). Fixed by adding an explicit `trainer.log({...})` call
matching Trainer's own per-step log record shape.

A third, methodological bug was caught and fixed in the verification
script itself before it could produce a false result: building a "first
half of an 8-step run" checkpoint using `max_steps=4` created a scheduler
whose OWN internal total is 4 steps (fully decaying to LR=0 by step 4)
rather than being the midpoint of an 8-step schedule. Fixed by adding a
`stop_at_step` parameter, decoupling "how many total steps the LR
schedule is built for" (`args.max_steps`, unchanged across resume) from
"where this particular call's loop halts."

**Empirical resume-fidelity proof** (`scripts/lim/verify_manual_loop_resume.py`,
run as 3 independent processes, mirroring LIM-2's methodology): an
uninterrupted 8-step run vs. a 4-step run resumed for 4 more steps, same
seed, same schedule:

| step | uninterrupted loss | resumed loss | loss relerr | LR match |
|---|---:|---:|---:|:---:|
| 5 | 2.6076 | 2.6143 | 0.26% | exact |
| 6 | 2.5858 | 2.6043 | 0.72% | exact |
| 7 | 2.5108 | 2.5223 | 0.46% | exact |
| 8 | 2.4846 | 2.4980 | 0.54% | exact |

**Verdict: PASS.** Loss agrees within <1% at every step (well inside the
GPU backward-pass noise band established in LIM-2's own stabilization
check), and `learning_rate` matches to full floating-point precision at
every step — direct proof the scheduler resumed the *same* 8-step total
schedule rather than restarting one, which is only possible if
optimizer/scheduler state was genuinely restored.

## 3. Evaluation metric classification

The owner's six-way taxonomy (exact-match / semantic / grounding /
citation / reasoning / performance) mixes two different axes — *how* a
metric is computed (exact-match vs. semantic) and *what* it's about
(grounding, citation, reasoning) — worth naming explicitly rather than
silently forcing every metric into one bucket:

| Metric | Implemented? | Computation style | Subject |
|---|---|---|---|
| `agreement_with_teacher` (`field_agreement`) | Yes | **Exact-match** (case-insensitive string / set equality per field) | General correctness |
| `self_critique_quality` | Yes | **Exact-match** (categorical `finding` field) | Reasoning-adjacent |
| `grounding_accuracy` | Yes | **Exact-match** (categorical verdict) | **Grounding** |
| `hallucination_flag_correct` | Yes | **Exact-match** (categorical verdict) | **Grounding** |
| `mean_latency_s` / `p95_latency_s` / `gpu_memory` / `throughput` | Yes | Measured, not scored | **Performance** |
| citation accuracy | **Not implemented** (named only in the LIM-3 report's prose, no function exists) | — | **Citation** |
| financial reasoning quality | **Not implemented** (LIM-3 proxied it informally via `agreement_with_teacher` on `investment_decision_support`/`rag`) | — | **Reasoning** |
| abstention behavior | **Not implemented** | — | — |
| *(none)* | — | **Semantic** | — |

**The stark finding, confirmed by this audit, not assumed: every currently
implemented scoring metric is exact-match. There is no semantic metric,
no dedicated citation metric, and no dedicated reasoning metric anywhere
in the framework.** This is exactly why LIM-4's real, visible improvement
(the checkpoint moving from a fixed unrelated hallucination to
NGX-grounded, schema-consistent output) scored identically to no
improvement at all — the instrument used genuinely cannot see the
difference between those two outcomes.

## 4. Next-generation evaluation metrics — design only, not implemented

Per the owner's explicit instruction, this is a design for LIM-5 to build
against, not code written in this pass.

### 4.1 Structurally different but semantically equivalent outputs

Two cheap, dependency-light, local (no API cost) techniques, applied
before scoring:
- **Field-alias normalization table**, per dataset type (e.g.
  `{"amount": "numeric_value", "date": "filing_date"}`) — deterministic,
  auditable, maintained alongside each exporter, same status as every
  other ad hoc/disclosed config in this package (`configs/*.toml`
  convention already established in LIM-1).
- **Unwrap common structural variants** before comparison — e.g. a model
  wrapping its answer in `{"dividend": {...}}` or `{"named_entities":
  [{...}]}` instead of a flat object (both observed in the real LIM-4 eval
  run) — flatten one level when there's exactly one top-level key and its
  value is a dict/single-item list, then apply normal field matching.

### 4.2 Partially correct outputs

`field_agreement` already returns a continuous `[0,1]` ratio, not a
boolean — the gap is in *reporting*, not computation. Recommend explicit
tiers for readability (`>=0.8` correct, `0.4-0.8` partial, `<0.4`
incorrect) surfaced in the aggregate report, plus **field-importance
weighting** (e.g. getting `fact_type` right should count for more than
matching an optional field), configured per dataset type the same way
`configs/dataset_quality_weights.toml` already weights quality dimensions.

### 4.3 Grounded-but-incomplete answers

A genuinely new metric, not a variant of an existing one: separate
**groundedness** (does the answer contradict nothing in the provided
`retrieved_facts`/`citations`/context — a containment/non-contradiction
check, not requiring semantic similarity) from **completeness** (what
fraction of the expected answer's key facts/fields are present at all).
An answer can score high groundedness + low completeness (true but
partial) or the reverse (complete-looking but contradicting a cited fact)
— today's single `agreement_with_teacher` number conflates both into one
score and can't distinguish these failure modes from each other.

### 4.4 Incorrect hallucinations (general-purpose, not just `hallucination_detection`)

Today, hallucination is only measurable on the one dataset type whose
labels explicitly say "hallucinated" (and that type currently has zero
held-out examples — LIM-3's finding). Propose a **task-agnostic
hallucination check** applicable to any generated output: extract
entities/tickers/dates the model's answer references, and check whether
each one actually appears in that example's own `context`/
`retrieved_documents`/`retrieved_facts` — i.e. a factual-grounding check
against the INPUT the model was actually given, independent of whether
the specific answer is otherwise correct. This would have caught the
LIM-3 "Coca-Cola"/`KO` hallucination directly and quantitatively (ticker
not in the NGX universe, not in the provided context) rather than relying
on manual inspection of raw output, as this validation pass and LIM-3/4
both had to do.

All four designs deliberately avoid a live LLM-judge call or new external
dependency, consistent with this project's established free-data-only,
zero-incremental-cost discipline — they are string/set/containment
operations over data already on disk.

## 5. Confirmed fixes (recap)

- Train/test split contamination: structurally eliminated (§1), not just
  patched around.
- `Trainer.train()` inf/NaN on masked labels: root-caused via 9
  independently-controlled experiments, replaced with a manual loop built
  from the framework's own validated primitives, now further verified for
  resume equivalence (§2) — two additional real bugs (missing
  `trainer.log()` calls, a scheduler-total/stop-point conflation) found
  and fixed during this exact verification work, not before.
- Evaluation scoring-rubric limitation: confirmed and precisely
  classified (§3), not merely asserted.

## 6. Remaining weaknesses

- `splits.json` tamper-detection gap (§1) — recommended for LIM-5
  infrastructure hardening.
- Zero semantic/citation/reasoning-specific metrics exist (§3) — this
  *is* LIM-5's evaluation-methodology prerequisite, not just a nice-to-have.
- `entity_recognition-v1.1.0` still has 13/39 examples in filing-level
  context collision groups (LIM-4 finding, unresolved — needs real
  mention-span data).
- The manual training loop's resume path has now been verified for a
  single-dataset, single-adapter QLoRA configuration only; multi-dataset
  runs and larger step counts are unverified (no evidence either way, not
  a known defect).
- LIM-4's latency regression (11.6s → 27.6s mean) remains unisolated from
  hardware throttling versus a real property of the checkpoint.

## 7. Recommendations for LIM-5

1. Do not begin model-quality optimization until at least the
   task-agnostic hallucination check (§4.4) exists — it is the cheapest of
   the four designs and directly targets the failure mode LIM-3 found by
   accident.
2. Implement field-alias normalization (§4.1) before drawing any
   conclusion from `agreement_with_teacher` on a retrained checkpoint —
   otherwise a real improvement can continue to score as a regression, as
   happened in LIM-4.
3. Treat the `splits.json` tamper-detection gap as infrastructure debt to
   close before scaling up how many dataset types are actively trained on.
4. Every LIM-5 training run must be benchmarked against both frozen
   baselines (`lim3-eval-baseline-2026-07-28` and the LIM-4 tag about to
   be created) via a new, immutable `eval_run` row — never overwriting
   either.

## 8. Conclusion

LIM-4's own objective — pipeline integrity and evaluation-process
validation, not model performance — is confirmed met by this pass, and
this pass itself found and fixed three additional real defects (the
resume crash, the missing log_history, the scheduler/stop-point
conflation) that LIM-4's original submission had not caught. No model
training or optimization was performed. Ready to commit and tag as the
foundation for LIM-5.
