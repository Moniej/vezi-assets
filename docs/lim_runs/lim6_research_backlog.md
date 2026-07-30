# Research Backlog — Local Intelligence Model

Every item is a single testable hypothesis. Discipline carried forward
from LIM-5: one variable per experiment, evaluated against the frozen
LIM-5 baseline (`lim5-optimization-baseline`, plus `lim3-eval-baseline`
and `lim4-training-baseline` where relevant), never combined.

**Production default, frozen 2026-07-29 (`docs/lim_runs/rb2_closure.md`,
tag `lim6-lora-rank-baseline`): LoRA `r=8`.** Every experiment from RB-3
onward inherits this fixed rank from `configs/lim_training_defaults.toml`
(`scripts/lim/train.py`'s `--lora-r` default) unless that experiment's
own single independent variable IS the rank itself, in which case the
override must be an explicit CLI flag, never a changed default. Do not
revisit rank selection absent evidence materially contradicting RB-2/
RB-2b's conclusion.

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
- **STATUS: executed, result inconclusive/mixed against the pre
  -registered metric** (`docs/lim_runs/rb1_results.md`,
  `rb1_infrastructure_failure_log.md`). The blocking segfault/`OSError`
  1455 was confirmed as pure infrastructure (low system memory,
  reproduced and resolved by an owner-directed restart, byte-identical
  environment/config hash verified) — no code change. Once run, the
  pre-registered success metric was **not met**: `semantic_equivalence`
  on `extraction` was flat-to-lower (0.1704 → 0.1666) and
  `grounded_correctness` regressed (0.4387 → 0.3006), though several
  secondary metrics improved (`agreement_with_teacher` on `extraction`
  broke out of 0.0 for the first time, `hallucination_risk` dropped to
  0). The one unambiguous finding: the training loss curve visibly
  plateaued at 40 steps for the first time in any run — useful for
  calibrating RB-2/RB-4's own step counts. Follow-up (RB-1b, an
  intermediate step count and/or repeat seed) recommended before drawing
  any conclusion about training duration's effect on quality.

## RB-2 — LoRA rank sweep — ✅ COMPLETED (formally closed 2026-07-29)

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
- **STATUS: all 6 configs complete, analysis done** (`docs/lim_runs/
  rb2_results.md`, §1-9 plus the §10 update appended after the final
  config finished). Hypothesis **not confirmed as stated** — the data
  shows the opposite of "higher rank helps":
  - **Confirmed (2 seeds, replicated)**: r=32 is statistically
    significantly worse than BOTH r=8 and r=16 on `agreement_with_
    teacher`/`semantic_equivalence`/`grounded_correctness` at both seeds
    (all paired bootstrap CIs exclude zero) — including a 0/27 parse
    rate at seed=123 (total generation collapse, never completed a
    single balanced JSON object), the single most extreme finding in the
    experiment.
  - **Still provisional (mixed across seeds)**: r=8-vs-r16 — at seed=42
    r=8 statistically significantly beats r=16 on all three metrics; at
    seed=123 the same-direction trend is not significant, and `grounded_
    correctness` reverses direction. Not yet resolved.
  - Two real confounds were found and handled during this experiment: a
    fixed token-budget cap (fixed with a balanced-JSON stopping
    criterion, applied identically to every checkpoint) and a still
    -unresolved seed-dependent completion-rate effect (parse rate swings
    nearly as much by seed as by rank) that entangles "rank hurts
    representational quality" with "rank hurts generation termination."
  - **STUDY FORMALLY CLOSED** (`docs/lim_runs/rb2_closure.md`), following
    a dedicated 4-seed follow-up, RB-2b (`rb2b_results.md`), run
    specifically to resolve r=8-vs-r16 rather than force a conclusion
    from the original mixed 2-seed evidence. Result: `semantic_
    equivalence` is directionally consistent in ALL 4 seeds tested and
    its across-seed bootstrap CI excludes zero (a real, modest, ~37%
    relative effect favoring r=8); parse/completion rate also favors r=8
    in all 4 seeds. r=16 offers no offsetting resource advantage
    (roughly double the trainable parameters, both negligible for this
    model size). **Production default: r=8.** The r=32 termination
    -collapse mechanism is documented as a separate, informational-only
    research question (`rb2_r32_collapse_research_question.md`, four
    candidate hypotheses + a proposed diagnostic) that does not block
    this closure. RB-3/RB-4/RB-5 may now begin, using r=8 as the fixed
    default rank.

## RB-3 — Train on `self_critique` instead of `extraction` — ❌ NEGATIVE RESULT

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
- **STATUS: NEGATIVE RESULT, formally recorded** (`docs/lim_runs/
  rb3_results.md`). Run at the frozen r=8/40-step default, seed=42,
  `self_critique@self_critique-v1.0.0`, evaluated on the expanded
  test+validation set (n=24, up from the originally-scoped n=9).
  **`self_critique_quality` remained exactly 0.0/24** — a clean,
  unambiguous non-improvement on the metric named first in the success
  criterion. `reasoning_quality` did move off zero (0.0 → 0.0441,
  bootstrap CI [0.027, 0.063] excludes zero), and the pre-registered "or"
  criterion technically passed on this branch — but the evidence shows
  this does **not** reflect genuine reasoning improvement: it is a
  metric-side fallback extracting lexical-overlap credit from
  wrong-schema outputs, not the model performing the task. Root cause:
  **0 of 24 outputs use the expected output schema**
  (`finding`/`explanation`/`resulting_status`); 8 of 24 (33%) instead echo
  the prompt's own input fields back verbatim instead of attempting a
  critique. **Working hypothesis: this is an output-schema learning
  failure, not a reasoning failure** (see the diagnostic below). Do not
  promote `self_critique` and do not attempt to improve RB-3 directly.
  `extraction`'s own score on this (different, self_critique-only)
  checkpoint was reported per instruction (0.1111 semantic_equivalence)
  but is not a same-checkpoint regression signal, since this checkpoint
  never trained on `extraction`. All artifacts (training run
  `ebe73677-...`, eval run `3389f4a1-...`) are preserved as the negative
  -result baseline for future comparison.

## RB-3a — Schema-learning diagnostic — ✅ CONFIRMED (Phase 2 complete, 2026-07-30)

See `docs/lim_runs/rb3a_schema_diagnostic.md` (Phase 0/1 audit),
`rb3a_phase2_preregistration.md` (pre-registered hypothesis/thresholds,
committed before training), and `rb3a_results.md` (full results).

**Phase 0/1 audit** ruled out dataset-schema inconsistency,
sequence-length truncation, and loss-masking bugs; identified that
`self_critique`'s required output key names never appear in its
input/instruction (unlike `extraction`, where they do 132/132).

**Phase 2 (schema-hint training experiment): CONFIRMED.** A single
runtime-derived conditioning-signal change (listing the expected JSON
keys in the prompt, no dataset-content change) took the `self_critique`
schema-match rate from **0/24 (RB-3) to 18/24 = 75% (RB-3a)**, bootstrap
95% CI [0.583, 0.917] — clears the pre-registered ≥60% success threshold
even at its lower bound. Input-echoing (33% in RB-3) dropped to 4%.
**Schema acquisition is confirmed as the dominant, fixable cause of RB-3's
structural failure.**

**New, narrower open question surfaced by this result**:
`self_critique_quality` remained exactly 0.0/24 even among the 18
schema-matched outputs, because **0/18** used a valid categorical value
for `finding` (expected one of `fail`/`concern`/`pass`; got full free-text
sentences instead) or `resulting_status` (expected one of
`blocked_by_self_critique`/`unvalidated_ai_interpretation`; got invented
words like "revised"/"neutral"/"invalid"). The schema-*key* problem is
solved; a distinct categorical-*value*-vocabulary problem remains,
previously invisible because the key-level failure masked it. Proposed
next step (tentatively **RB-3b**, not yet started): an analogous
single-variable value-enumeration hint experiment, pre-registered the
same way.

**Methodological note (documented, not fixed)**: `run_evaluation.py`'s
`--schema-hint` flag applies uniformly across all dataset types in a
run, so this run's `extraction` numbers (evaluated with an
extraction-specific hint this checkpoint never trained on) are not
directly comparable to RB-3's `extraction` numbers — flagged in
`rb3a_results.md`, does not affect the primary `self_critique` finding.

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
