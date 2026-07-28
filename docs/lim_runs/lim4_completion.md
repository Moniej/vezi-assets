# LIM-4 Completion Report — First Model-Improvement Phase

Status: complete. Per the owner's framing, this phase's job was to fix the
confirmed LIM-3 root cause and every disclosed contributing factor, then
*objectively measure* the result against the frozen LIM-3 baseline — not
to declare victory. That measurement is below, including where the
current metric itself falls short of capturing a real, visible improvement.

## 1. Fixes implemented

### 1.1 Response-only loss masking (the confirmed LIM-3 root cause)

`src/ngxrot/lim/training.py::_JsonlExampleDataset` now masks (`label=-100`)
every position that isn't the actual response span — both the left-padding
region and the prompt (instruction+context+`### Response:\n`). Verified on
all 39 real `entity_recognition` examples: decoding each example's
supervised (non `-100`) region reproduces exactly its `expected_output`
JSON plus the EOS token, nothing else. Also verified this generalizes
without error across all 13 registered dataset types (some have much
longer contexts, e.g. `corporate_actions`/`extraction`; none hit the
truncation guard).

### 1.2 Fixed `entity_recognition` exporter context (new finding, not in the LIM-3 diagnosis)

While investigating "improved instruction formatting," found that
`entity_recognition-v1.0.0`'s context was `{"ticker": <entity's own
resolved ticker>}` — null for the large majority of entities (competitor/
subsidiary/shareholder mentions rather than the filer itself). Checked
directly: **all 39 of 39 examples shared the exact same context
(`{"ticker": null}`) while having 39 different expected `canonical_name`
values** — an information-theoretically unlearnable one-to-many mapping,
independent of and in addition to the masking defect. `entity_mentions`
(the table that would give a real quoted mention span) remains disclosed
as unpopulated platform-wide; this fix does not fabricate that. It adds
the one real, already-available signal that identifies which filing the
entity was first seen in (`documents.ticker`/`filing_date`/`doc_type` via
`entities.first_seen_doc_id`), breaking the collision without inventing
data. Re-exported as `entity_recognition-v1.1.0` (parent:
`entity_recognition-v1.0.0`), registered, passed the audit gate. Residual
ambiguity disclosed, not hidden: 26 of 39 examples now have a unique
context; 13 remain in groups of 2-4 sharing the same filing (multiple
entities genuinely first-seen in the same document) — a real, smaller
limitation that would need actual mention-span data to fully resolve.

### 1.3 Real train/validation split — a second, independently-discovered contamination bug

While assessing "train/validation balance," checked whether the first
LIM-2 training run's ad hoc `examples[:len(examples)//10]` in-training
eval slice overlapped with the officially-registered `test` split used by
`scripts/lim/run_evaluation.py`. It did: **the real LIM-2 training run
(`a022e655-...`) trained on `entity_recognition:21`, `:25`, and `:33` —
the exact same three unique_ids the LIM-3 benchmark later scored as
"held out."** `dataset_loader.load_training_set()` now reads the real,
registered `splits.json` (LIM-1's deterministic hash-bucket split) and
structurally excludes every `test`-split unique_id before returning
anything to the caller — training and validation examples are the only
things `training.py` can ever see. Two regression tests added
(`test_load_training_set_never_returns_test_split_examples`,
`test_load_training_set_refuses_without_splits_json`); all 24
LIM-2-suite checks and all LIM-1-suite checks still pass.

### 1.4 Curriculum ordering — assessed, not applied

Checked `entity_recognition-v1.1.0`'s `quality_score` and `evidence_tier`
distributions: `quality_score` is a constant `1.0` and `evidence_tier` is
`None` for all 39 examples — zero variance, no evidence-based signal to
order by. Per the owner's explicit "if justified," this is a documented
"not justified" finding, not a skipped step.

### 1.5 A new bug discovered and fixed during implementation: `Trainer.train()` produces inf/NaN with masked labels

The first real attempt to train with response-only masking failed: `loss=0`,
`grad_norm=nan` at every step. This was diagnosed from scratch (not
assumed to be the masking fix itself) with a long, reproducible experiment
chain, each step confirmed before moving to the next:

1. Manual forward+backward on a real masked example, outside any Trainer
  machinery: **loss=12.26, no NaN.**
2. Same, wrapped in `torch.autocast(bf16)` (mimicking Accelerate): fine.
3. `trainer.compute_loss()` called directly: fine (12.13).
4. `trainer.training_step()` called directly, with every `num_items_in_batch`
  variant (`None`, `int`, `tensor`): fine.
5. Gradient clipping (`accelerator.clip_grad_norm_`) on the resulting
  gradients: fine (valid norm, no NaN).
6. Manual `optimizer.step()` + a SECOND `training_step()` call: loss
  correctly **decreased** (12.13 → 11.69) — real learning, orchestrated by
  hand using the framework's own methods.
7. Ruled out (each independently, via controlled re-runs): gradient
  checkpointing (both Unsloth's and `TrainingArguments`', together and
  separately), `gradient_accumulation_steps` (tested at 1 and 4),
  `adamw_8bit` vs plain `adamw_torch`, `accelerator.accumulate()` context,
  and `_wrap_model()`.
8. Subclassing `Trainer` to instrument the exact return value of
  `training_step` *inside a real `trainer.train()` call* revealed the true
  failure: **the very first step's loss is `inf` (not just NaN)**, and all
  288 tracked gradients are NaN from that point on — a real first-step
  numerical blow-up specific to the fully-automated loop.
9. Decisive control: re-ran the identical real `trainer.train()` call with
  the OLD unmasked labels (`labels = input_ids` verbatim) on the same new
  model/dataset — **it trained correctly** (loss 29.22 → 23.08, valid
  grad norms). This isolates the trigger to the presence of `-100` in
  `labels`, specifically inside `Trainer.train()`'s own top-level
  orchestration (transformers 5.5.0 / Unsloth 2026.7.5 combination) — not
  the masking logic itself, not the model, not any primitive the loop
  calls (all independently verified correct in steps 1-6).

**Fix applied** (`training.py::_manual_train_loop`): calls the exact same,
independently-validated sequence by hand — `trainer.training_step()` per
micro-batch, `accelerator.clip_grad_norm_()`, `optimizer.step()`,
`lr_scheduler.step()`, and `trainer._save_checkpoint()` at save points —
bypassing only `Trainer.train()`'s own automated loop, which is where the
defect was isolated to. This is not a novel training loop; it is
`Trainer.train()`'s own documented steps, called directly. Checkpoint
structure verified unchanged (`optimizer.pt`/`scheduler.pt`/`rng_state.pth`/
`trainer_state.json` all present, same as every LIM-2 checkpoint).

**Side effect found and fixed**: with `report_to=["tensorboard"]`, the
manual loop (which never calls `trainer.log()` per step, since it bypasses
`_inner_training_loop` entirely) caused the TensorBoard callback's writer
to lazily initialize against an unfinalized `args.logging_dir` and fall
back to `torch.utils.tensorboard`'s own CWD-relative default, writing a
stray `./runs/` directory at the repo root instead of nested under the
run's own checkpoint directory. Since no per-step scalars were reaching
the integration anyway, it was removed (`report_to=[]`) rather than
worked around; the stray directory (2 folders, both from today's smoke
tests) was deleted (untracked, safe).

## 2. Real training run

Run `c52db6e1-28f8-41a6-b1c8-52076e8261b6`: `entity_recognition@entity_recognition-v1.1.0`,
seed 42, 12 steps, save every 4 — identical seed/steps/LoRA config to the
LIM-2 baseline run (`a022e655-...`) for a controlled comparison. Training
loss decreased smoothly across all 12 steps (no NaN/inf at any point).
Full provenance recorded in the training registry as usual (dataset
version + content hash, base model, git commit, seed, 3 checkpoints,
eval, completed).

Note on raw loss magnitude: this run's loss values are **not directly
comparable** to the LIM-2 baseline's raw numbers — the baseline supervised
~256 mostly-padding tokens per example (LIM-3's finding), this run
supervises only the ~24-36 real response tokens, a fundamentally
different denominator. The comparable measure is the LIM-3/4 evaluation
harness, run identically against both checkpoints below.

## 3. Re-evaluation against the frozen LIM-3 baseline

Eval run `9a6b06cf-be53-4bb1-a616-633da9921d48` recorded **alongside**,
never overwriting, the LIM-3 baseline (`1d018805-...`) — both remain in
the immutable `eval_runs` table. Same 61 held-out examples across the
same 8 dataset types, same scoring code (`eval_harness_hash` recorded on
both rows for exact comparability).

| | LIM-3 baseline | LIM-4 (this run) |
|---|---:|---:|
| Overall `agreement_with_teacher` | 0.0055 | 0.0 |
| `entity_recognition` `agreement_with_teacher` | 0.0 (n=3) | 0.0 (n=3) |
| `extraction` `agreement_with_teacher` | 0.0278 (n=12) | 0.0 (n=12) |
| Mean latency | 11.56s | 27.58s |

**The objective metric shows no improvement — if anything, a marginal
decrease.** This must be reported as-is. But inspecting the actual raw
outputs (recorded per-example in `eval_examples`, not just the aggregate
score) shows something the metric doesn't capture:

- **`entity_recognition:21`** (baseline): `{"entity": "Coca-Cola", "type":
  "Company"}` — the fixed, off-topic hallucination documented in LIM-3,
  referencing a US company (ticker `KO`) that appears in no NGX filing.
- **`entity_recognition:21`** (this run): `{"named_entities": [{"entity":
  "BUAFOODS", "type": "SEC Form 12B-25", "ticker": "BUAFOODS",
  "filing_ticker": "BUAFOODS", "filing_date": "2023-04-26",
  "filing_doc_type": "dividend"}]}` — a REAL NGX ticker, using the exact
  new context field names (`filing_ticker`/`filing_date`/`filing_doc_type`)
  introduced by the LIM-4 exporter fix. Still the wrong specific entity,
  but no longer a fabricated, ungrounded hallucination — this is a
  genuine, visible behavior change consistent with the training signal
  actually reaching the model now.
- **`corporate_actions`/`extraction`** (this run): now produce well-formed,
  topically-coherent, *parseable* JSON (previously a runaway string of
  repeated zeros); still scored 0.0 because the model settled on a
  different-but-plausible key schema (e.g. `{"dividend": {"amount": ...}}`
  instead of the exact `{"fact_type", "description", "numeric_value"}`
  keys `agreement_with_teacher` checks for).

**Disclosed limitation of the metric, found by this comparison, not
assumed going in**: `agreement_with_teacher`'s exact-key-match scoring
cannot distinguish "wrong family of output" from "right family, different
exact schema" — both score 0.0. This run is qualitative evidence the
masking fix worked (the model is now using training-signal-shaped,
NGX-grounded output instead of an unrelated hallucination), but the
CURRENT metric is not sensitive enough to confirm that quantitatively.
This is scoring-rubric technical debt to address before the metric can be
trusted to detect this class of improvement, not a claim that the fix
"worked" without evidence — the raw-output evidence above is real and
checkable, but it is qualitative, and is reported as such.

**Latency**: mean generation latency roughly doubled (11.56s → 27.58s,
p95 52.0s). Not isolated as a controlled measurement in this run (a single
continuous ~28-minute evaluation pass on a laptop GPU, no thermal/clock
monitoring) — plausibly hardware throttling rather than a property of the
checkpoint itself, but reported honestly rather than dismissed, since it
was not proven either way.

## 4. AI Intelligence Layer / Quant Engine

`git diff --stat` against `src/ngxrot/documents/`, `schema/schema.sql`,
and every quant-engine module remains empty — untouched throughout LIM-4.

## 5. Remaining technical debt

- **`agreement_with_teacher` needs fuzzy/normalized field matching** (or a
  schema-mapping step) to detect "correct content, different key names"
  improvements — found directly by this phase's own comparison, not
  theoretical.
- **`entity_recognition-v1.1.0` still has residual context collisions**
  (13 of 39 examples in groups of 2-4 sharing a filing) — would need real
  mention-span data (`entity_mentions`, still unpopulated) to fully
  resolve.
- **The `Trainer.train()` inf/NaN-with-masked-labels bug is unreported
  upstream** — it's a real defect in this specific transformers 5.5.0 /
  Unsloth 2026.7.5 combination, worked around here, not filed against
  either project.
- **Latency regression is disclosed, not conclusively isolated** — a
  dedicated, controlled latency benchmark (idle GPU, repeated runs) would
  be needed to separate hardware throttling from any real change.
- **Dataset is still very small** (31 train examples after masking removes
  the padding/prompt dilution) — the qualitative improvement seen here is
  consistent with genuine learning, but 12 steps over 31 examples remains
  far short of what would be needed for reliable exact-schema convergence.

## 6. Conclusion

Every LIM-4 objective was addressed with evidence, not assumption: the
confirmed LIM-3 masking defect is fixed and verified; a second, independent
data defect (`entity_recognition`'s unlearnable one-to-many context) was
found and fixed; a third, independent contamination bug (training on the
official held-out test set) was found and fixed; curriculum ordering was
assessed and honestly found not justified; and a new, serious framework
bug (`Trainer.train()` blowing up on masked labels) was root-caused and
fixed with a minimal, well-evidenced workaround. The re-evaluation against
the frozen LIM-3 baseline is reported exactly as measured — no aggregate
metric improvement, alongside real but currently metric-invisible
qualitative evidence of reduced hallucination and increased NGX-grounding.
Awaiting review before any further LIM phase begins.
