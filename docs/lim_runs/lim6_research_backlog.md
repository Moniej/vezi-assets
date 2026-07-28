# Research Backlog — Local Intelligence Model

Every item is a single testable hypothesis. Discipline carried forward
from LIM-5: one variable per experiment, evaluated against the frozen
LIM-5 baseline (`lim5-optimization-baseline`, plus `lim3-eval-baseline`
and `lim4-training-baseline` where relevant), never combined.

## RB-1 — Complete the blocked training-duration experiment

- **Hypothesis**: increasing `max_steps` from 12 (never plateaued in any
  run so far) to 40+ on `extraction`, all else identical to LIM-5
  Experiment 1, further improves `semantic_equivalence`.
- **Expected outcome**: `semantic_equivalence` on `extraction` held-out
  examples increases beyond LIM-5's 0.1704, with train loss visibly
  plateauing by the final step (unlike every prior run).
- **Success metric**: `semantic_equivalence` (extraction, n=12) > 0.1704,
  no regression in `grounded_correctness`/`hallucination_risk` on the
  same examples.
- **Estimated effort**: S (~10 min: one training run + one targeted
  eval) — blocked only by environment stability, not implementation.
- **Priority**: **Highest** — directly continues the one already
  -proven-effective lever, cheapest remaining unknown.

## RB-2 — LoRA rank sweep

- **Hypothesis**: `r=8` (used in every run to date, 0.15% of base
  parameters) under-capacitates the model relative to what response-only
  masked training on `extraction` could use; `r=16` or `r=32` improves
  semantic correctness without destabilizing training.
- **Expected outcome**: higher rank → higher `semantic_equivalence`,
  possibly with diminishing or negative returns at some point (small
  data, risk of overfitting at high rank) — report whichever direction
  the evidence shows.
- **Success metric**: `semantic_equivalence` on `extraction` test split,
  compared at `r=8` (LIM-5 baseline) vs. `r=16` vs. `r=32`, one value
  changed per run.
- **Estimated effort**: M (~30 min: 2-3 training runs + eval each).
- **Priority**: High.

## RB-3 — Train on `self_critique` instead of `extraction`

- **Hypothesis**: `self_critique` (128 examples, informative context,
  good consistency per Priority 1) is a genuinely different, viable
  training target; training on it (single variable: dataset) produces a
  measurable improvement on `self_critique_quality`/`reasoning_quality`,
  mirroring Experiment 1's result on a different skill.
- **Expected outcome**: `self_critique_quality` and `reasoning_quality`
  (currently 0.0 in every run, since no checkpoint has ever trained on
  this type) move off zero.
- **Success metric**: `self_critique_quality` or `reasoning_quality` on
  `self_critique`'s held-out test split (n=9) improves vs. the LIM-5
  baseline's 0.0, no regression on `extraction`'s own scores (a separate
  checkpoint, so no direct regression risk, but report both).
- **Estimated effort**: S (~15 min).
- **Priority**: High — the other half of Priority 3's curriculum
  question (untested ordering hypothesis) depends on this existing as a
  standalone result first.

## RB-4 — Learning rate sweep

- **Hypothesis**: `2e-4` (used throughout) is untested against
  alternatives; a different rate could improve convergence within the
  same small step budget.
- **Expected outcome**: unclear direction — genuinely open, no prior
  signal (no divergence/oscillation observed at 2e-4).
- **Success metric**: `semantic_equivalence` on `extraction`, single
  variable (learning rate: e.g. 1e-4, 2e-4 [baseline], 5e-4).
- **Estimated effort**: M.
- **Priority**: Medium — no observed symptom currently implicates this.

## RB-5 — Batch size / gradient accumulation

- **Hypothesis**: effective batch size 4 (1 × 4 grad-accum steps) may be
  too small/noisy for stable convergence in few steps.
- **Expected outcome**: larger effective batch reduces per-step loss
  variance; unclear whether it improves final `semantic_equivalence`
  within the same step budget.
- **Success metric**: `semantic_equivalence` + loss-curve variance,
  single variable (grad accumulation steps: 4 [baseline], 8).
- **Estimated effort**: M (larger effective batch = slower wall time per
  step on this 6GB GPU).
- **Priority**: Medium.

## RB-6 — Sequence length / packing

- **Hypothesis**: `max_seq_length=256` is untested against longer
  sequences; low priority specifically for `extraction`
  (p95 token length 138, well under 256 — Priority 1) but relevant if
  RB-3 (`self_critique`, p95=168) or any future longer-context type is
  used.
- **Expected outcome**: no measurable effect for `extraction` specifically
  (not truncated today); primarily a prerequisite check before training
  on any type whose p95 approaches or exceeds 256.
- **Success metric**: confirm zero truncation (via the audit script's
  `pct_over_256`) for whichever type is trained next; only run a real
  length-increase experiment if that check fails.
- **Estimated effort**: S (an audit check, not necessarily a training run).
- **Priority**: Low for now, conditional trigger for later.

## RB-7 — Generation-time stop sequence (Priority 2 finding)

- **Hypothesis**: adding a stop sequence (or relying on `eos_token_id` in
  `generate()`) at inference time prevents the observed base-model
  template-completion leakage (fabricated follow-on "### Instruction:..."
  text after the real answer), independent of any training change.
- **Expected outcome**: cleaner raw outputs, likely fewer `parse_model_
  json` failures (`model_output_parsed=None` cases) — an indirect but
  measurable proxy.
- **Success metric**: parse-failure rate (fraction of held-out examples
  with `model_output_parsed is None`) decreases vs. the LIM-5 baseline,
  same checkpoint, same test set, only the generation call changed.
- **Estimated effort**: S (no retraining needed, evaluation-side change only).
- **Priority**: Medium — cheap, safe, evidence-backed, doesn't touch the
  training pipeline at all.

## RB-8 — Persist `context` in the eval registry (infrastructure)

- **Hypothesis**: adding a `context` column to `eval_examples` would let
  `grounded_correctness`/`hallucination_risk`/`citation_correctness` be
  computed retroactively against historical eval runs, not only future
  ones (currently impossible for LIM-3/LIM-4 — Priority 4's disclosed gap).
- **Expected outcome**: full three-way (LIM-3/4/5) comparison becomes
  possible on all 9 metrics, not just the 6 that don't need context.
- **Success metric**: re-running the comparative report after this change
  shows non-null `grounded_correctness`/`hallucination_risk` rows for
  LIM-3 and LIM-4, not just LIM-5.
- **Estimated effort**: S (schema addition + one field in `record_
  example`); requires a registry schema change, so treat with the same
  care as any other immutable-registry modification.
- **Priority**: Medium — valuable but not blocking any model-quality
  experiment directly.

## Blocked (not actionable this phase — requires new data/datasets)

Listed for roadmap completeness, per the bottleneck ranking; explicitly
**not** to be started until the owner lifts the "no new datasets" 
constraint.

- **RB-9**: Populate `entity_mentions` to resolve `entity_recognition`'s
  residual context collisions (13/39 examples).
- **RB-10**: Redesign `evidence_ranking`'s export to include real
  evidence/quote content instead of a bare `fact_id`.
- **RB-11**: Re-audit `citation_grounding`/`financial_reasoning` (both
  currently 0 registered examples) to unlock the citation-correctness
  and reasoning-quality evaluation dimensions.

## Priority summary

| ID | Item | Priority | Effort |
|---|---|---|---|
| RB-1 | Training duration (resume blocked experiment) | Highest | S |
| RB-2 | LoRA rank sweep | High | M |
| RB-3 | Train on `self_critique` | High | S |
| RB-7 | Generation stop-sequence | Medium | S |
| RB-4 | Learning rate sweep | Medium | M |
| RB-5 | Batch size / grad accumulation | Medium | M |
| RB-8 | Persist eval context (infra) | Medium | S |
| RB-6 | Sequence length / packing | Low (conditional) | S |
| RB-9/10/11 | Data-quality fixes | Blocked this phase | — |
