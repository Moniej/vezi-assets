# RB-3c Experimental Design — Does More Training Signal Close the Fine-Tuned-vs-Base-Model Gap?

**Status: DESIGN ONLY. No training run, no probe execution, no code
change has been made. Awaiting review before any implementation begins**,
per explicit instruction.

## 1. The question this experiment must answer

`rb3b_mode_collapse_investigation.md` established that RB-3b's apparent
"mode collapse" substantially **predates** its fine-tuning: the untrained
base model's argmax already matches the 40-step, rank-8 fine-tuned
model's argmax in 24/24 held-out examples for `resulting_status` and
21/24 for `finding`, with the fine-tuned-vs-base relative-probability gap
(Total Variation Distance, TVD — see §5) measured at **0.1704 for
`finding`** and **0.0001 for `resulting_status`** at the existing 40-step
checkpoint.

That investigation could not, by itself, say *why* 40 steps wasn't
enough to move `resulting_status` at all and only partially moved
`finding`. Two genuinely different explanations remain open, and they
point to different next actions:

- **H1 — Insufficient-optimization hypothesis**: the base-model prior is
  real but soft/erodable. 40 steps at r=8, with response-only masking
  diluting gradient signal across a much longer `explanation` field
  (`rb3b_mechanism_review.md` §3b), simply wasn't enough training
  exposure directed at these specific token positions. Under H1, running
  the *same* recipe for more steps should produce **continued, non
  -negligible growth in TVD** — the gap should keep closing (or at least
  keep moving) as training continues.
- **H2 — Dominant-pretrained-prior hypothesis**: the prior reflects a
  strong, largely fixed representational commitment from pretraining
  (e.g., token-embedding or attention-pattern associations) that a
  rank-8 LoRA adapter cannot meaningfully override regardless of step
  count, within a realistic budget. Under H2, TVD should **plateau
  early** — the movement already visible at step 40 is close to this
  configuration's ceiling, and more steps of the identical recipe won't
  meaningfully change the outcome.

These are not mutually exclusive across the two fields — the
investigation already found `finding` and `resulting_status` behaving
differently (real partial movement vs. essentially none), so **this
experiment evaluates H1/H2 separately per field**, not as one combined
verdict for `self_critique`.

## 2. Why step count is the right variable to distinguish H1 from H2

Step count is the cleanest lever for this specific question because it
changes *only* how much gradient exposure the identical training signal
gets — it does not change what the model is capable of representing
(unlike rank), what the loss objective rewards (unlike loss
-reweighting), or what data it sees (unlike a dataset change). If more
of the *exact same* training signal keeps moving the needle, the
bottleneck is optimization/exposure (H1) and scaling up steps (or a
similarly "more of the same" lever) is the right next move. If it
doesn't, the bottleneck is something the current recipe cannot reach at
all — supporting H2 and redirecting future work toward rank, loss
-reweighting, or data-side interventions (Ranks 3-5 in the investigation)
instead of simply training longer.

This is a distinct question from RB-1's own step-count finding (`extraction`,
12→40 steps, training-loss plateau at 40). RB-1 asked whether *training
loss* had converged; this experiment asks whether a *specific,
independently-measured representational gap* (the fine-tuned-vs-base
probability distance) keeps closing — a different, more targeted
question that RB-1's result cannot answer by itself, since `self_critique`
has never had its own step-count behavior measured at all.

## 3. Single independent variable

`max_steps` only. Every other parameter is held at RB-3b's exact
configuration:

| Parameter | RB-3b (existing) | RB-3c (this design) | Same? |
|---|---|---|---|
| LoRA config | r=8, alpha=16, dropout=0.0, `[q/k/v/o_proj]` | identical | Yes |
| `schema_hint` | True | True (held fixed — RB-3a's confirmed win, not re-tested) | Yes |
| `value_hint` | True | True (held fixed — RB-3b's confirmed win, not re-tested) | Yes |
| Learning rate | 2e-4 | identical | Yes |
| Batch size / grad accumulation | 1 / 4 | identical | Yes |
| `max_seq_length` | 256 | identical | Yes |
| Dataset | `self_critique@self_critique-v1.0.0`, 104 train | identical | Yes |
| Seed | 42 | identical | Yes |
| Held-out eval set | 24 examples (test+validation) | identical | Yes |
| **`max_steps`** | **40** | **a new value (see §4)** | **No — the one variable** |

## 4. Design: reuse existing artifacts first, minimize new training

Three points are needed on a steps-vs-TVD curve to distinguish "still
closing" (H1) from "already plateaued" (H2): step 0 (the base model —
already measured, TVD=0 by definition), step 40 (RB-3b's existing
checkpoint — already measured: TVD=0.1704 finding, 0.0001 status), and
one new, larger step count.

**Proposed Phase 0 (zero-cost, no training, not yet executed)**: RB-3b's
training run (`8d265e59-...`) already saved intermediate checkpoints at
steps 10, 20, and 30 (in addition to 40), since `save_steps=10`. Running
the *existing* probe methodology (`scripts/lim/rb3b_mode_collapse_probe.py`,
generalized to accept a `--checkpoint` argument instead of a hardcoded
path) against these three checkpoints would give **four free data points**
(10, 20, 30, 40) on the steps-vs-TVD curve at **no new training cost at
all** — informing exactly how much further Phase 1's new step count
should reach (e.g., if TVD is already flat between steps 20-40, a modest
new step count would be sufficient to confirm the plateau; if TVD is
still rising steeply at step 40, a larger jump is needed to give H1 a
fair chance). **This phase is proposed, not executed** — it requires
running a script (read-only, no training) and is included here only as
part of the design for review, consistent with the instruction not to
begin training; if approved, Phase 0 would run before Phase 1's exact
step count is finalized.

**Phase 1 (new training run, not yet executed)**: one new training run
at a step count informed by Phase 0, or, if Phase 0 is skipped, a
pre-registered default of **`max_steps=160`** (4× RB-3b's 40, a similar
order-of-magnitude jump to RB-1's own 12→40, ~3.3×, applied here since no
step-count data exists yet for `self_critique` at all).

**Phase 2 (new eval + probe, not yet executed)**: run `scripts/lim/
run_evaluation.py` on the new checkpoint (identical settings to RB-3b:
`--include-validation --max-new-tokens 512 --schema-hint --value-hint`),
then run the probe methodology against it, producing TVD and discrete
-accuracy numbers directly comparable to the existing step-0 and step-40
measurements.

**No additional step counts beyond what Phase 0/1 specify will be added
without a new pre-registration** — see §9 (risk of fishing).

## 5. Metrics — pre-registered before any new run

### Primary metric: Total Variation Distance (TVD) between the fine-tuned model's and the base model's relative-probability distribution over legal candidates, per field, averaged over the 24 held-out examples

$$\text{TVD} = \frac{1}{n}\sum_{i=1}^{n} \frac{1}{2}\sum_{c \in \text{classes}} \left| P_{FT}(c \mid x_i) - P_{base}(c \mid x_i) \right|$$

computed identically to the investigation's own methodology (real
generation token ids, `disable_adapter()` for the base-model comparison,
no retokenization of decoded text). Bounded in [0, 1]; 0 means the
fine-tuned model's distribution is indistinguishable from the untrained
base model's at these positions; 1 means maximal divergence.

**Pre-registered anchor values** (already measured, not to be
recomputed differently after the fact):

| Field | TVD @ step 0 (base, by definition) | TVD @ step 40 (RB-3b, measured) |
|---|---:|---:|
| `finding` | 0.0000 | **0.1704** |
| `resulting_status` | 0.0000 | **0.0001** |

### Secondary metrics (reported, not pass/fail criteria on their own)

- Discrete argmax accuracy per field, per class (continuity with
  `rb3b_results.md`'s confusion matrices) — already known to be
  uninformative at step 40 (0/24 on `finding`, majority-class artifact on
  `resulting_status`), but tracked to check for a possible TVD
  -vs-accuracy dissociation (§8, Outcome E).
- Schema-match rate (control — `schema_hint`/`value_hint` are held fixed;
  must not regress from RB-3b's 100%).
- Parse rate, `self_critique_quality`, `reasoning_quality` (continuity
  with RB-3/RB-3a/RB-3b's reporting conventions).

## 6. Statistical analysis plan

- TVD is a per-example-averaged statistic; report the **per-example TVD
  contribution's bootstrap 95% CI** (`eval_analysis.bootstrap_ci`, same
  2000-resample/seed=42 convention used throughout this project) at each
  step count tested, and a **paired bootstrap comparison**
  (`paired_bootstrap_ci_of_difference`, paired by `unique_id`, identical
  held-out set throughout) between step-40's TVD and the new step
  count's TVD, per field.
- Report exact per-step TVD values as a table (steps vs. TVD), not just
  the endpoint comparison — a monotonic-looking trend across 4+ points
  (if Phase 0 is run) is stronger evidence than a single two-point
  difference, consistent with this project's preference for multiple
  observations over a single delta wherever cheaply available.
- `finding` and `resulting_status` are analyzed and reported
  **independently** — no combined/averaged verdict across fields, per
  the investigation's own finding that they behave differently.

## 7. Early-stopping rule (evaluated after Phase 0, gates Phase 1)

**This section governs whether Phase 1 (the new, longer training run)
happens at all.** It is evaluated mechanically once Phase 0's four
checkpoint measurements exist (steps 10, 20, 30, 40 — the last already
available from RB-3b) and is not to be revised after seeing Phase 0's
actual numbers, per the instruction not to redesign after the fact.

### `resulting_status` — pre-decided by existing evidence

The step-40 anchor already measured in `rb3b_mode_collapse_investigation.md`
(TVD = 0.0001, 24/24 argmax agreement with the untrained base model) is
about as extreme a plateau signal as this metric can produce — a
fine-tuned model indistinguishable from an untrained one. **This field is
pre-registered as already satisfying the stopping criterion (H2,
plateau) without needing Phase 0 at all.** Phase 0's audit will still
compute this field's steps 10/20/30 values (zero extra cost, same
forward passes as `finding`'s audit) purely for completeness and to
check for a non-monotonic surprise (see below), but a "cancel" verdict
for this field is the default, override-only outcome.

**Override condition** (would require re-opening this field's verdict,
not silently overriding it): if Phase 0 shows TVD at any of steps
10/20/30 is *substantially higher* than 0.0001 (e.g., ≥0.05, an order of
magnitude above the step-40 anchor), implying non-monotonic behavior
(the model moved away from the base prior and then back), this
specific, surprising pattern must be reported explicitly and would
warrant treating this field as unresolved rather than silently keeping
the pre-decided verdict — but this is flagged as unlikely, not expected.

### `finding` — decided by the Phase 0 trend, mechanically

Using the four points (0 [base, TVD=0 by definition], 10, 20, 30, 40 —
step 40 already measured at 0.1704):

1. Compute the three consecutive-interval deltas: Δ(10→20), Δ(20→30),
   Δ(30→40).
2. Compute the paired bootstrap 95% CI (n=24, paired by `unique_id`, the
   same 2000-resample/seed=42 convention used throughout this project)
   for each of the two *most recent* deltas: Δ(20→30) and Δ(30→40).

**CANCEL Phase 1** (conclude H2 — plateau, from Phase 0 evidence alone)
**if BOTH** of the following hold:
- (a) Both Δ(20→30)'s and Δ(30→40)'s paired bootstrap CIs include zero
  (no statistically distinguishable movement in either of the last two
  10-step intervals), **and**
- (b) |Δ(30→40)| ≤ |Δ(20→30)| (the rate of movement is not
  accelerating) — this guards against concluding "plateau" from two
  individually-underpowered-but-still-trending-upward intervals.

**PROCEED to Phase 1** if **either**:
- (a) At least one of Δ(20→30) or Δ(30→40)'s CI excludes zero
  (statistically real continued movement within the existing
  checkpoints), **or**
- (b) The magnitude trend is flat-or-growing (|Δ(30→40)| > |Δ(20→30)|)
  even if both individual CIs are inconclusive — reported explicitly as
  a judgment call resting on trend shape rather than significance, not
  hidden behind non-significant p-values.

### Overall Phase 1 go/no-go

Phase 1 (the new training run) proceeds if **either field's** evaluation
above says proceed. Phase 1 is skipped entirely only if **both fields**
conclude cancel — i.e., only if `finding`'s mechanical rule above also
says cancel, since `resulting_status` is already pre-decided as cancel
by default. If Phase 1 does proceed (because `finding` warranted it),
`resulting_status` is still measured and reported at the new step count
regardless — a single training run necessarily updates the whole model,
so both fields' outcomes are always reported together even when only one
field's evidence justified running it.

This rule is evaluated exactly once, immediately after Phase 0's four
measurements are in hand, and is not to be re-derived or loosened after
seeing the actual Phase 0 numbers.

## 8. Pre-registered interpretation of every possible outcome

| Outcome | `finding` TVD trend | `resulting_status` TVD trend | Interpretation | Recommended next step |
|---|---|---|---|---|
| **A — Both still closing** | Continues rising substantially past 0.1704, CI excludes no-change | Rises measurably above 0.0001 (even a small absolute move is notable given its near-zero anchor) | **H1 supported for both fields.** More training signal, under the identical recipe, is the working lever. | Continue scaling steps (or consider this confirmed and move to the next unvaried hyperparameter, e.g. RB-4/RB-5) |
| **B — `finding` closes further, `resulting_status` stays flat** | Rises substantially | Stays within noise of 0.0001 (CI includes no-change) | **Mixed, field-specific**: H1 for `finding`, H2 for `resulting_status`. The 2-way field's prior is categorically harder to move than the 3-way field's. | Keep scaling steps for `finding`-like problems; pursue a *different* lever (rank, loss-reweighting, or data) specifically for `resulting_status`-like (highly skewed, near-ceiling) fields |
| **C — Both plateau** | Stays within noise of 0.1704 | Stays within noise of 0.0001 | **H2 supported for both.** Step count is not the fix for either field. | Do not scale steps further; pivot to Rank 3 (loss-reweighting) or Rank 4 (rank/capacity) from the investigation as the next single-variable candidate |
| **D — TVD reverses** (moves back toward the base model) | Drops below 0.1704 | (unlikely given its near-zero floor, but watch for it) | **Unexpected — does not fit H1 or H2 cleanly.** Possible overfitting-oscillation or an artifact of the specific step count chosen. | Do not force an H1/H2 conclusion; treat as its own open question requiring a dedicated follow-up (e.g. checking intermediate steps, per Phase 0, before concluding anything) |
| **E — TVD moves but accuracy doesn't** (or vice versa) | any | any | **Dissociation, reported explicitly, not smoothed over.** TVD growth without accuracy gain means training is moving the distribution *somewhere*, not necessarily toward the *correct* class — must not be reported as "the model is learning the task" without this caveat. | Treat TVD as a measure of *prior-override capacity*, not correctness; correctness remains a separate, unresolved question regardless of this experiment's TVD result |

No outcome is pre-classified as an unqualified "success" — per the
standing instruction across this entire research program, the result
will be reported exactly as the evidence shows, including if it lands
between these named cases.

## 9. Risks

1. **Fishing for a supportive result.** Testing many step counts until
   one shows movement would be an unprincipled search, not an
   experiment. Mitigated by pre-registering the exact new step count
   (§4) before running anything, and by committing here to add no
   further step counts without a fresh pre-registration if this result
   is ambiguous.
2. **Infrastructure fragility.** Longer training runs mean more wall-clock
   exposure to the memory-pressure failures documented repeatedly this
   session (RB-1, RB-2, RB-2b, RB-3, RB-3b). The established protocol
   (verify resources, do not modify config to work around a transient
   failure, retry byte-identical after confirming environment parity)
   applies unchanged.
3. **Single seed.** Seed=42 only, matching every RB-3-series run so far.
   If Outcome B or D materializes and the result is borderline, a
   multi-seed follow-up (RB-2b's precedent) would be warranted before
   drawing a firm conclusion — not built into this first pass, to keep
   it minimal.
4. **TVD as a construct.** TVD measures how far the fine-tuned
   distribution has moved from the base model's — it does **not**
   measure whether it moved toward the *correct* answer (Outcome E
   exists precisely to guard against conflating the two). Every result
   from this experiment must report both TVD and discrete accuracy, and
   must not let a large TVD alone stand in as evidence of task learning.
5. **Prompt length / truncation.** Unchanged from RB-3b (schema_hint +
   value_hint combined already verified safe: 1/104 training examples
   truncated by 11 tokens at `max_seq_length=256`, disclosed, not a
   blocker). No new risk introduced by changing `max_steps` alone.

## 10. Stopping condition

Run Phase 0 (if approved — zero training cost) to inform Phase 1's exact
step count, then exactly one new training run (Phase 1) and one new
eval+probe pass (Phase 2). Do not proceed to a rank, loss-reweighting, or
data-side experiment without a dedicated review of this result first,
regardless of which pre-registered outcome (§8) materializes. This
experiment answers exactly one question — does more of the identical
training recipe close the gap — and its own decision matrix entry (Ranks
3-4 of `rb3b_mode_collapse_investigation.md`) is where the next choice
would come from, not decided in advance here.

## 11. What has and has not been done

- **Done**: this design document only.
- **Not done**: Phase 0's checkpoint audit, Phase 1's training run,
  Phase 2's eval/probe, any code change, any new registry entry.
- Awaiting review before any of the above begins.
