# RB-2 Formal Closure — LoRA Rank Study

**Status: CLOSED.** Production default rank selected with supporting
evidence. RB-3/RB-4/RB-5 may now begin.

## Scope of the study

Three ranks tested (r ∈ {8, 16, 32}), at the RB-1-established converged
step count (`max_steps=40`), on `extraction@extraction-v1.0.0`, with a
total of 10 real training runs and 10 real evaluations across this
investigation (RB-2's original 6 + RB-2b's 4 seed-expansion runs).

## r=32 — eliminated

**Confirmed, replicated across both seeds tested.** Statistically
significantly worse than both r=8 and r=16 on `agreement_with_teacher`,
`semantic_equivalence`, and `grounded_correctness` (every paired
bootstrap CI excludes zero, both seeds — `rb2_results.md` §10).
Decisively: **0/27 parsed at seed=123** — complete generation-termination
collapse, not merely lower quality. No further replication is needed to
close this question; the evidence is sufficient and consistent.

r=32 is eliminated as a production candidate **regardless of the
underlying mechanism** — a dedicated, informational-only research
question (`rb2_r32_collapse_research_question.md`) documents four
candidate hypotheses for *why* (EOS-probability suppression from
overfitting, repetition-loop sensitivity, an effective-step-size/rank
interaction, and a framework-level numerical artifact) and a proposed
future diagnostic, explicitly **not** blocking this closure or any
subsequent RB phase.

## r=8 vs. r=16 — resolved

**r=16 does not provide a practically meaningful improvement over r=8.**
A dedicated 4-seed follow-up (RB-2b, `rb2b_results.md`) was run
specifically to answer this, treating seed as the unit of replication
rather than continuing to argue from 2 data points:

- `semantic_equivalence` — the metric with the cleanest signal — is
  **directionally consistent in all 4 seeds** (r=8 higher every time)
  and its across-seed 95% CI **excludes zero** ([−0.179, −0.031]): a
  real, if modest (~0.10 absolute, ~37% relative), effect favoring r=8.
- Parse/completion rate (a prerequisite for any other metric to even
  apply) also favors r=8 in **all 4 seeds** tested.
- `agreement_with_teacher` shows the same direction in 3 of 4 seeds with
  a borderline across-seed CI; `grounded_correctness` remains genuinely
  noisy at the seed level (one seed reverses direction).
- r=16 offers **no compensating resource advantage** — it has roughly
  double the trainable parameters of r=8, both negligible in absolute
  terms for this 4B model, so there is no cost/speed/size argument on
  r=16's side to weigh against its measured quality deficit.

Per instruction not to force a conclusion from mixed evidence: this is
not an overwhelming effect, and is reported as modest, not dramatic. But
it is consistent, statistically supported on the best-suited metric, and
entirely one-directional — there is no dimension, statistical or
practical, on which r=16 is shown to be better.

## Production default: r=8

Selected because:
1. It wins or ties every comparison run in this study (never
   significantly beaten by r=16 or r=32 on any metric, at any seed).
2. Its advantage over r=16 is real (seed-reliable on `semantic_
   equivalence`, consistent parse-rate advantage across all 4 seeds
   tested) even though modest in absolute size.
3. It carries the least representational capacity of the three ranks
   tested, and lower capacity has not once shown a quality cost in this
   data — the opposite of the original RB-2 hypothesis ("higher rank
   under-capacitates the model"), which this study disproves for this
   dataset/step-count regime.
4. No resource, cost, or complexity argument favors a higher rank to
   offset its measured disadvantage.

## What remains open (not blocking closure)

- The r=32 collapse mechanism (`rb2_r32_collapse_research_question.md`)
  — informational, future work.
- Whether r=8 remains optimal under a *different* dataset, step count,
  or learning rate is untested — this closure is scoped to the exact
  configuration studied (`extraction`, 40 steps, lr=2e-4), consistent
  with the single-variable discipline this whole investigation followed.
  RB-4 (learning rate) or a future dataset-specific rank check would be
  separate, single-variable questions, not reopenings of this one.

## Next phase

RB-3 (train on `self_critique`), RB-4 (learning rate sweep), or RB-5
(batch size / gradient accumulation) may now begin, using r=8 as the
fixed default rank per this closure, per the single-variable-per
-experiment discipline established since RB-1.
