# RB-2 Follow-up Research Question — r=32 Generation-Termination Collapse

**Status: informational, not a blocker.** Per owner directive, this
investigation does not delay selection of the production default LoRA
rank (`docs/lim_runs/rb2_closure.md`) or the start of RB-3/RB-4/RB-5. It
exists because a confirmed, replicated, dramatic failure mode deserves a
real explanation, not just an elimination.

## The finding, restated precisely

`r=32` was eliminated from consideration not merely because its
task-quality scores were lower, but because of *how* it failed:
generation frequently never produces a syntactically-complete JSON
object at all.

| Config | Parsed (of 27) | Hit the 512-token safety cap |
|---|---:|---:|
| r=32, seed=42 | 7 (26%) | 19 (70%) |
| r=32, seed=123 | **0 (0%)** | **27 (100%)** |

For comparison, r=8's two original seeds parsed at 96% and 63%. r=32 is
not merely "somewhat worse at completing" — at seed=123 it failed to
terminate *at all*, on every single held-out example.

## Hypothesis

**Higher LoRA rank, combined with a very small fine-tuning set (~130
examples) and a short training schedule (40 steps), makes the adapted
model more prone to entering a self-reinforcing non-terminating
generation state — independent of whether the content it's generating is
otherwise reasonable — because the larger number of trainable parameters
gives the optimizer more freedom to fit idiosyncratic, non-generalizing
patterns in this tiny dataset, and one of the patterns it fits is an
unstable or absent EOS/closing-brace signal.**

This is a hypothesis about a training dynamics / capacity-overfitting
interaction, not yet a proven mechanism.

## Candidate mechanisms (not mutually exclusive)

1. **EOS-probability suppression via overfitting.** With more adapter
   capacity and few steps, the model may overfit to surface statistics of
   the ~130 training responses (which are short and always followed by
   a real EOS in training) in a way that doesn't generalize: at
   inference, once the model drifts even slightly off the training
   distribution (e.g., an unfamiliar ticker or filing shape in a held-out
   example), a higher-capacity adapter may have learned a sharper, more
   narrowly-tuned distribution over "what comes next" that fails to
   assign adequate probability to EOS/closing-brace once the input
   deviates from anything memorized — vs. a lower-rank adapter's coarser,
   more conservative update that stays closer to the base model's own
   (well-calibrated) stopping behavior.
2. **Repetition-loop attractor sensitivity.** Greedy decoding is already
   known to be prone to repetition loops in small/undertrained models;
   higher rank may amplify whatever base-model tendency toward this
   exists, by more aggressively reshaping the output distribution near
   the training examples' style (elaborate, many-field JSON) without
   proportionally reshaping the "when to stop" signal, so once a loop
   starts (e.g. re-listing similar fields) there is nothing pulling the
   model back out of it.
3. **LoRA rank increasing effective step size in weight-space per
   optimizer update.** At a fixed learning rate, a higher-rank adapter has
   more free directions to move in per gradient step; over only 40 steps,
   this could produce a qualitatively different (not just quantitatively
   larger) update than lower rank -- e.g. reaching a different local
   region of weight space entirely rather than a scaled version of the
   same one r=8 reaches. This would predict rank and learning rate
   interact, which RB-4 (learning rate sweep, not yet run) could speak to
   indirectly even though it wasn't designed for this.
4. **Interaction with `gradient_checkpointing`/precision, unrelated to
   rank's representational role at all.** Given this project's own
   history of real, non-obvious framework-level surprises (the
   transformers 5.5.0 masked-label inf/NaN bug from LIM-4), a
   rank-specific numerical-stability artifact in this exact training
   stack cannot be ruled out without direct inspection (e.g., gradient
   norms per layer during training, not just the aggregate norm already
   logged).

## What would distinguish these mechanisms

- **Mechanism 1 vs. 2**: inspect EOS-token logit/probability specifically
  at the position where a correct response would stop, across
  checkpoints — if EOS probability is measurably suppressed at higher
  rank even on examples that DO eventually terminate, that supports
  mechanism 1 over a pure decoding-repetition story.
- **Mechanism 2**: check whether non-terminating generations are
  literally repeating a substring (as seen in some LIM-4/RB-2 raw
  outputs, e.g. the repeated "**Note**: The response should be..."
  block) vs. genuinely novel-but-unbounded elaboration (new field names
  each time, never repeating verbatim) — these have different practical
  fixes (repetition penalty helps the former, not the latter).
- **Mechanism 3**: repeat the r=32 training at a lower learning rate,
  holding rank fixed, and check whether the collapse rate drops --
  would implicate the rank/step-size interaction specifically.
- **Mechanism 4**: rule out/in directly by comparing gradient norms
  layer-by-layer between r=8 and r=32 runs (already-logged aggregate
  `grad_norm` doesn't distinguish this; would need per-layer logging,
  currently not implemented).

## Proposed future experiment (not executed now)

A dedicated, single-purpose diagnostic run: train r=32 exactly as in
RB-2 (seed=42, the less-catastrophic of the two seeds, to have *some*
successfully-terminating examples to compare against non-terminating
ones within the same checkpoint), then for every held-out example
record, at generation time: (a) the EOS-token probability at each
decoding step, (b) whether/where a repeated substring pattern emerges
(simple longest-repeated-suffix check), and (c) per-layer LoRA weight
update norms from the training run's saved optimizer state. Compare
terminating vs. non-terminating examples' EOS-probability trajectories
directly. This would need new instrumentation (none of the current
scripts log per-token EOS probability or per-layer norms) -- estimated
effort M, no new training data or capability required, purely
observational tooling added to existing checkpoints already on disk.

## Explicitly out of scope for this note

- Does not propose fixing r=32 (it is eliminated as a production
  candidate regardless of root cause -- §`rb2_closure.md`).
- Does not block or delay RB-3/RB-4/RB-5.
- Is not itself a claim that any one candidate mechanism above is
  correct -- all four remain open until the proposed diagnostic (or
  something like it) is actually run.
