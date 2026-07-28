# LIM-3 Completion Report — Evaluation Framework (Objective Benchmark)

Status: framework built and a first real benchmark run recorded. Per the
owner's directive: "Do not optimize the model yet. The objective is to
establish an objective benchmark for every future improvement." This
report is that baseline, plus a candid account of what it did and didn't
measure this run.

## 1. Framework architecture

A fourth immutable registry, `lim_training/eval_registry.sqlite`
(schema: `schema/lim_eval_registry.sql`), deliberately separate from the
quant hypothesis ledger, dataset-version registry, and training-run
registry:

- **`eval_runs`** — one immutable row per benchmark execution: subject
  (`local_checkpoint`), the exact checkpoint path, the traced
  `training_run_id`, every dataset version + content hash evaluated, the
  held-out split used, the full metrics JSON, git commit, and an
  `eval_harness_hash` — a SHA-256 over `eval_metrics.py` + `eval_dataset.py`
  themselves, so a future change to *how* metrics are scored is as
  traceable as a change to the model being scored. UPDATE/DELETE blocked
  by trigger, same as the other three registries.
- **`eval_examples`** — one immutable row per scored held-out example
  (instruction, expected/teacher output, raw model output, parsed output,
  per-example scores, latency, token counts) — full per-example
  auditability behind every aggregate number.

**Held-out set** (`src/ngxrot/lim/eval_dataset.py`): reuses
`dataset_loader.verify_dataset_ready()` verbatim (registered,
content-hash-verified, audit-gate-passed — an eval must never score against
data that wasn't trustworthy enough to train on either), then filters to
the `test` partition of each version's `splits.json` — LIM-1's
deterministic hash-bucket split that `training.py` never consults (it
built its own ad hoc in-training validation slice). This is what makes the
evaluation genuinely held-out: none of these examples were used in any
training step.

**Scoring** (`src/ngxrot/lim/eval_metrics.py`): every metric is a mechanical
comparison against the recorded `expected_output` (the teacher model's own
output for that input, captured at dataset-export time) — never an
LLM-as-judge call, never a live re-query of the teacher API. This is a
disclosed design choice: it keeps every score reproducible byte-for-byte
from data already on disk and costs nothing to re-run after every future
training improvement, consistent with this project's free-data-only cost
discipline. A metric not applicable to a given example (e.g. grounding
verdict on a task type that doesn't carry one) scores `None` for that
example — aggregation reports **"not measurable"** with a reason, never a
fabricated 0 or a silent omission.

## 2. Metrics: what was and wasn't measurable this run

| Owner-specified metric | This run | Why |
|---|---|---|
| Agreement with teacher | **Measured**: overall mean 0.0055 (n=61) | Field-level match between the model's parsed JSON and the teacher's recorded `expected_output` |
| Self-critique quality | **Measured**: mean 0.0 (n=9, `self_critique` type) | Categorical match of the model's `finding` vs. the teacher's recorded finding |
| Financial reasoning quality | **Not directly measurable** | `financial_reasoning` failed its own LIM-1 audit gate (0 registered examples) — using ungated data would contradict the same "don't use data that failed its quality gate" principle training enforces. `investment_decision_support` and `rag` (both registered, both financial-reasoning-adjacent) were evaluated as the closest available proxies — see per-type table below — but are not the same task and are labeled as a proxy, not a substitute |
| Grounding accuracy | **Not measurable this run**: n=0 | Requires an `expected_output.verdict` field. The only two dataset types that carry one are `citation_grounding` (failed its LIM-1 audit gate — excluded) and `hallucination_detection` (registered, but its 2 total accepted examples both fell in the `train` bucket of the deterministic split — 0 in `test`) |
| Citation accuracy | **Not measurable this run**: n=0 | None of the 8 dataset types with a non-empty held-out set ask the model to *produce* a citation as output (citations are input/context metadata in this corpus, not a generation target) — a real scope gap in the current dataset schema, not a framework defect |
| Hallucination rate | **Not measurable this run**: n=0 | Same root cause as grounding accuracy — `hallucination_detection` has 0 held-out examples this run |
| Abstention behavior | **Not measurable this run**: n=0 | `coverage_assessment` (the type carrying a genuine low-evidence/abstention signal via `confidence_ceiling`/`dimensions_missing`) has 0 examples in its `test` split |
| Agreement with teacher | (see above) | |
| Inference latency | **Measured**: mean 11.56s, p95 11.81s per example (max_new_tokens=160) | |
| GPU memory usage | **Measured**: 3,539 MB allocated / 3,553 MB peak | RTX 3050 6GB laptop GPU, 4-bit base + LoRA adapter |
| Throughput | **Measured**: 0.0865 examples/s (61 examples / 705.4s wall time) | |

Four of the ten named metrics have zero eligible held-out examples in the
**current** registered corpus — this is a real, disclosed limitation of the
data, not the evaluation framework: the framework computes every one of
these metrics generically and will report real numbers the moment
eligible held-out data exists (e.g. once `citation_grounding` is fixed to
pass its audit gate, or `hallucination_detection`/`coverage_assessment`
grow past a couple of examples so their deterministic split actually
produces a non-empty `test` partition).

## 3. Real benchmark run

Eval run `1d018805-2a8f-4b3c-b836-77cbbdfaab12`, evaluating checkpoint
`.../a022e655-b4f1-4ca9-9f84-e9227165efc0/checkpoint-12` (traced via
`training_registry.run_for_checkpoint()` back to training run `a022e655-...`
— the same real, fully-provenanced run from LIM-2). 61 held-out examples
across 8 dataset types (5 types had 0 held-out examples and are recorded
as such, not silently skipped — see table above and `holdout_coverage` in
the recorded metrics).

| Dataset type | n (held-out) | agreement_with_teacher (mean) |
|---|---:|---:|
| corporate_actions | 18 | 0.0 |
| entity_recognition *(the type this checkpoint was actually trained on)* | 3 | 0.0 |
| evidence_ranking | 14 | 0.0 |
| extraction | 12 | 0.0278 |
| investment_decision_support | 2 | 0.0 |
| rag | 1 | 0.0 |
| retrieval | 2 | 0.0 |
| self_critique | 9 | 0.0 (self_critique_quality also 0.0) |

**Overall agreement_with_teacher: 0.0055 across 61 examples.**

### What the raw outputs actually show (evidence, not assumption)

Inspecting the recorded raw generations (`eval_examples.model_output_raw`)
explains the near-zero score honestly rather than leaving it as an
unexplained number:

- **On `entity_recognition` — the one type this checkpoint was actually
  fine-tuned on** — all 3 held-out examples produced the exact same
  fabricated, off-topic output: `{"entity": "Coca-Cola", "type":
  "Company"}` followed by a hallucinated repeat of the prompt template
  referencing ticker `"KO"` (Coca-Cola's real ticker — which appears
  nowhere in any of these NGX filings). This is a genuine finding, not a
  scoring bug: with only 12 optimizer steps over 36 training examples and
  `lora_dropout=0.0`/`r=8`, the adapter did not learn the task's actual
  schema (`canonical_name`/`entity_type`/`resolved_ticker`) — it collapsed
  to a fixed, memorized, wrong completion, most likely because
  `training.py`'s current loss computes over the *entire* input+response
  sequence unmasked (`labels = input_ids`, no `-100` masking of the
  instruction/context tokens), which dilutes gradient signal on the novel
  response schema with the much easier objective of reconstructing the
  prompt tokens themselves. This is a concrete, actionable recommendation
  for the next real training phase (mask the prompt in the loss; more
  steps; more data) — flagged here, not fixed here, per LIM-3's explicit
  "do not optimize the model yet" scope.
- **On task types the checkpoint was never trained on** (corporate_actions,
  evidence_ranking, extraction, investment_decision_support, rag,
  retrieval, self_critique), outputs are varied and topically-plausible
  free text or malformed JSON (e.g. `extraction` produced a runaway string
  of repeated zeros in a numeric field) rather than the fixed
  hallucination seen on `entity_recognition` — consistent with an
  untrained base model applying general instruction-following rather than
  a specific, memorized wrong answer. Scoring nearly 0 against a specific
  JSON schema it was never shown is the expected, honest result for these
  types, not a defect.

### Performance

| | |
|---|---|
| GPU memory (allocated / peak) | 3,539 MB / 3,553 MB |
| Mean generation latency | 11.56s (max_new_tokens=160, RTX 3050 6GB laptop) |
| p95 latency | 11.81s |
| Throughput | 0.0865 examples/s (61 examples in 705.4s wall time, including one-time model+adapter load) |

### Full provenance

- `training_run_id`: `a022e655-b4f1-4ca9-9f84-e9227165efc0` (traced via
  `run_for_checkpoint`, not hand-entered)
- `git_commit`: `d1ec959eb72cbcfc465ab7f2ff1e7eba5db7a9b5` (ngx-rotation
  HEAD at evaluation time)
- `eval_harness_hash`: `94c85334c3e621d5677913a962387dc921cef026b781bc80f0ed0ff96c12d1a2`
  (fingerprint of the scoring code itself)
- All 13 registered dataset versions' content hashes recorded in
  `eval_runs.dataset_content_hashes`, re-verified at load time by
  `dataset_loader`/`eval_dataset`

## 4. AI Intelligence Layer / Quant Engine

Unaffected by this phase — LIM-3 only reads already-registered,
already-exported JSONL datasets and an already-trained checkpoint; it adds
no new dependency on `ngx.sqlite` or the reasoning pipeline.

## 5. Remaining technical debt / disclosed limitations

- The four not-measurable metrics (grounding accuracy, citation accuracy,
  hallucination rate, abstention behavior) require either fixing
  `citation_grounding`'s audit-gate failure, growing `hallucination_
  detection`/`coverage_assessment` past their current handful of examples,
  or extending the dataset schema so citations are a generation target for
  some task type — any of these would unlock a genuine number where there
  is currently an honest "not measurable."
- `financial_reasoning`'s complete absence (0 registered examples) means
  the metric closest to the owner's "financial reasoning quality" request
  is currently proxied by `investment_decision_support`/`rag`, not the
  real thing.
- The `entity_recognition` finding above (fixed hallucinated output,
  likely from unmasked prompt-token loss) is a real, actionable training
  -quality issue surfaced by this benchmark — exactly what an "objective
  benchmark before further training" is supposed to do. No fix was applied
  here; LIM-3's scope is measurement, not optimization.
- No live teacher-model (Gemini) re-query was performed for this run —
  "agreement with teacher" is measured against each example's recorded
  `expected_output`, which IS the teacher's real output for that input,
  captured at export time. This is disclosed as a deliberate,
  zero-incremental-cost design choice, not an oversight; a future LIM-3.x
  mode could add a live-call comparison if the owner wants that
  specifically.

## 6. Conclusion

LIM-3's evaluation framework is built, generic across dataset type and
checkpoint, versioned, and immutable. The first real run establishes an
honest, low, and explicable objective baseline (0.0055 overall agreement
with teacher) for the LIM-2 checkpoint — not a target to defend, but the
number every future training improvement must be measured against. Nothing
was optimized. Awaiting review before any further LIM phase begins.
