# Bottleneck Ranking — Evidence-Based, Post-LIM-5

Ranked by expected impact on model quality, restricted to what's testable
without adding datasets, expanding model size, or introducing new
capabilities (the owner's explicit constraint on the next phase). Each
entry cites the specific evidence behind its ranking, not intuition.

## In-scope, ranked by expected impact

### 1. Training duration (steps / epochs) — HIGHEST

**Evidence**: every real training run so far (LIM-2, LIM-4, LIM-5
Experiment 1) used `max_steps=12`, and in every one of them, the training
loss curve was **still decreasing at the final logged step**, never
plateaued (LIM-5 Exp.1: 2.99 → 2.39 over 12 steps, no sign of
convergence). 12 steps at effective batch size 4 over ~130-160 examples
is under one full epoch. This is the single most under-explored,
cheapest-to-test, most directly loss-curve-supported lever available.
**Status**: attempted (LIM-5 Experiment 2) but blocked by an
infrastructure segfault, not by any negative signal about the hypothesis
itself — untested, not disproven.

### 2. LoRA rank / trainable capacity

**Evidence**: `r=8` (5.9M trainable params, 0.15% of the 4B base) has
been used in every single run without variation. No experiment has yet
isolated whether this is capacity-limited. Plausible given Priority 2's
finding that the model learned only a shallow heuristic rather than the
full target schema — more adapter capacity is a direct, cheap,
single-variable hypothesis for whether that ceiling is capacity-bound or
data-bound (Priority 1's data defects remain the more likely explanation
for `entity_recognition` specifically, but this hasn't been isolated for
the cleaner `extraction`/`self_critique` data).

### 3. Dataset choice refinement (beyond Experiment 1)

**Evidence**: only `extraction` has been tried as a training target since
Priority 1's audit. `self_critique` (128 examples, a genuinely different
reasoning skill, good consistency) remains completely untested as a
training source. Given Experiment 1 already proved dataset choice is a
real, measurable lever, testing the OTHER viable dataset is a natural,
well-evidenced next single-variable step.

### 4. Learning rate / batch size / sequence length / gradient accumulation

**Evidence**: none of these have been varied in any run. Lower-confidence
than #1/#2 because no observed symptom (oscillating loss, exploding grad
norms, truncation warnings on the trained types) currently implicates any
of them specifically — these are "no evidence against, no evidence for"
hypotheses, genuinely open but not signaled as urgent by anything
observed so far.

### 5. Prompt/response format — LOW (already investigated)

**Evidence**: Priority 2 directly tested this (memorization-vs-learning
analysis) and found the `### Instruction/Context/Response` template is
NOT implicated in any observed defect — the only recommended change (a
generation-time stop sequence) is a small, already-specified fix, not an
open research question.

## Measurement gaps (block our ability to SEE improvement, not model quality directly)

### 6. Zero measurable examples for grounding/citation/hallucination-detection metrics

**Evidence**: `grounding_accuracy`, `citation_correctness`, and
`hallucination_flag_correct` show `n=0` ("not measurable") in **every one**
of the three real eval runs (LIM-3, LIM-4, LIM-5) — not because the
metrics are broken, but because no held-out example in the current
registered corpus carries the needed label
(`hallucination_detection`/`citation_grounding` have 0 held-out test
examples; no dataset type asks the model to output a citation). This
doesn't lower model quality, but it means **three of the six priority
evaluation dimensions the owner named cannot currently be used to judge
any future experiment** — a measurement blind spot, ranked here because
closing it (once new datasets are back in scope) will change what LIM-7+
can even claim to have tested.

## Out of scope for the next phase (real, evidenced, but blocked by owner constraint)

These are genuine defects found across LIM-4/LIM-5 with real expected
impact, explicitly **not** actionable right now because doing so would
mean adding new data/datasets, which the owner has ruled out for this
phase:

- `entity_recognition`'s residual context collisions (13/39 examples) —
  needs real `entity_mentions` data, still disclosed empty
  platform-wide.
- `evidence_ranking`'s uninformative `{"fact_id": N}` context — needs
  real evidence/quote content added to the export, not just reordering
  or hyperparameters.
- `citation_grounding`/`financial_reasoning` have 0 registered examples
  (failed their LIM-1 audit gates) — would need new export/data work to
  even become usable.

## Process risk (not a quality bottleneck, but blocks further experimentation)

### Infrastructure stability

Four consecutive segfaults blocked LIM-5 Experiment 2, correlated with
low system RAM after this session's long history of subprocess launches.
Until resolved (a fresh environment/process restart, per the LIM-5
report's own recommendation), item #1 above (the highest-ranked lever)
cannot actually be executed.
