# RB-3b Mechanism Review — Candidate Levers for Categorical Value-Vocabulary Learning

**Status: informational survey only. Nothing in this document has been
implemented.** Per instruction, this reviews the evaluation pipeline and
training setup to identify *all plausible mechanisms* that could
influence the value-vocabulary problem RB-3a surfaced, before RB-3b's
design (`rb3b_experimental_design.md`) is executed or expanded. Listing a
mechanism here is not a recommendation to use it — RB-3b's design
document proposes exactly one variable (a prompt-side value hint); this
document exists to make sure that choice was made with the full
alternative space visible, not because it's the only option.

## Problem recap

`self_critique`'s trained checkpoint reliably produces the right JSON
*keys* (75%, RB-3a) but never a legal *value* for `finding` (must be
`fail`/`concern`/`pass`) or `resulting_status` (must be
`blocked_by_self_critique`/`unvalidated_ai_interpretation`) — 0/18 valid
values even among schema-matched outputs. Three broad categories of
mechanism could plausibly address this: constraining generation at
inference time, constraining generation via structured decoding more
generally, and changing what the model is taught during training. RB-3b
as designed uses none of the first two — it is purely a training-input
(prompt) change.

## 1. Enum-constrained decoding (inference-time)

**Mechanism**: a custom `LogitsProcessor` (transformers already exposes
this hook — used for a different purpose in this project's own
`_make_balanced_json_stopping_criteria`, which is a `StoppingCriteria`,
not a `LogitsProcessor`, but establishes that this class of hook is
already understood and used here) that masks all non-permitted tokens at
generation steps corresponding to a known field position, forcing the
sampled token to come from the legal set (`fail`/`concern`/`pass` for
`finding`, etc.).

**Would this help?** Mechanically, yes — it can *guarantee* a legal value
is emitted, 100% of the time, regardless of what the model actually
learned. **This is the key reason it is not proposed as RB-3b's
mechanism**: it would make `self_critique_quality`-style metrics pass
without answering RB-3b's actual research question (did the model learn
the vocabulary?). It treats the symptom (illegal values in the output) at
the exact moment of generation, not the underlying representation. It is
a legitimate **production-hardening** technique — worth having in the
inference path regardless of what RB-3b finds, since even a well-trained
model can occasionally sample an invalid token — but conflating it with
RB-3b's experiment would make the experiment's own success criterion
untestable (a constrained decoder passes the valid-value-rate metric
unconditionally, by construction, telling us nothing about training).

**Where it would need to hook in**: `scripts/lim/run_evaluation.py`'s
`model.generate()` call already accepts a `stopping_criteria` list; a
`logits_processor` list is the analogous hook for this technique, added
alongside it, not in place of it.

**Verdict**: plausible, cheap, real production value — but deliberately
excluded from RB-3b's own design because it would answer a different
question ("can we force legal output") not the one RB-3b asks ("did the
model learn the vocabulary").

## 2. Structured generation / grammar-constrained decoding (inference-time, broader)

**Mechanism**: a JSON-schema-or-grammar-constrained decoding framework
(the general case of #1 — constrains not just enum-valued fields but the
entire output's structure: keys, types, and value sets simultaneously).
Not currently a dependency of this project (no `outlines`/`guidance`/
`lm-format-enforcer`-style library is imported anywhere in
`requirements.lock.txt` per the existing dependency surface established
in LIM-0/LIM-2).

**Would this help?** Yes, and it subsumes #1 — it would also guarantee
schema-key correctness (RB-3a's problem) simultaneously, at generation
time, for any future checkpoint regardless of what it learned.

**Why not use it instead of RB-3a/RB-3b's prompt-based approach
entirely?** Same objection as #1, one level up: it would make both RB-3a
and RB-3b's own research questions moot by construction, and specifically
would prevent this project from ever learning whether the *model itself*
can acquire this fixed vocabulary through training/prompting — which is
the actual question the owner has directed this research program to
answer, not merely "can the pipeline produce well-formed output" (a
question a wrapper answers trivially, but says nothing about the LIM's
own learned capability, which is the entire point of training it locally
at all rather than always routing to constrained scaffolding).

**A real, disclosed cost**: adding a new third-party constrained
-decoding dependency would be a non-trivial addition to this project's
carefully-pinned, LIM-0-validated environment (`requirements.lock.txt`,
whose hash is checked before every experiment retry in this project's own
infrastructure-failure protocol) — not something to add lightly or
mid-experiment.

**Verdict**: the most powerful mechanism reviewed, and worth a
**separate, explicitly-scoped future item** (a production-hardening
question, analogous in spirit to RB-7's generation-time stop sequence)
— but out of scope for RB-3b specifically, which is designed to test
whether the *model* learns the vocabulary, not whether the *pipeline*
can enforce it externally.

## 3. Training-label / prompt design (training-time) — RB-3b's own category

Several distinct sub-mechanisms exist within this category; RB-3b's
design proposes exactly one (3a). Listed for completeness:

### 3a. Prompt-side value-vocabulary hint (RB-3b's proposed mechanism)

Exactly what `rb3b_experimental_design.md` proposes: list the legal
values for constrained fields in the prompt, the same class of fix that
worked for schema keys in RB-3a. Cheapest, most directly evidence
-motivated (RB-3a's own result), single-variable, and — critically —
actually tests whether the model *learns* the vocabulary rather than
just being told the answer at generation time. **This is why it is the
proposed mechanism for RB-3b**, not because the other mechanisms are
implausible.

### 3b. Loss reweighting toward categorical-value token positions

**Mechanism**: the current response-only masking (`_build_response_
only_labels`) supervises every response token equally. `finding`'s value
is a handful of tokens out of a much longer response (median response
length 62 tokens per RB-3's audit); the free-text `explanation` field
likely dominates the gradient signal by sheer token count. A targeted
loss-weighting scheme (e.g. a per-position weight multiplier applied
inside `_manual_train_loop`'s loss computation, or a custom
`compute_loss` override) could amplify gradient signal specifically at
the `finding`/`resulting_status` value token positions.

**Why not proposed for RB-3b directly**: this changes the *training
objective* itself (loss computation), a materially different and more
invasive kind of change than a prompt edit — and would need its own
careful validation (this project's history includes a real,
hard-won transformers/masked-label bug, LIM-4's inf/NaN finding; any
change to loss computation carries real risk of reintroducing a class of
bug this project has already spent significant effort eliminating). A
plausible **future RB-3c or later candidate** if RB-3b's prompt-only
approach turns out insufficient, but a strictly larger, riskier change
that should not be reached for first.

### 3c. Task decomposition (separate classification sub-task)

**Mechanism**: reformulate `self_critique` training as two coupled
sub-tasks — a small, separate categorical-classification example format
that isolates just "given this context, is the finding fail/concern/
pass?" from the free-text critique-writing task — potentially easier to
learn in isolation, then recombined at inference.

**Why not proposed for RB-3b directly**: this is a **dataset-content**
change (new example format/possibly new training examples), which is
explicitly out of scope — RB-3b (like RB-3a) is designed to test a
conditioning-signal change with **zero dataset-content modification**,
consistent with this project's standing single-variable discipline and
the owner's repeated instruction not to add new datasets/formats this
phase. Noted as a candidate only for a future phase where dataset
-content changes are back in scope.

### 3d. Explicit negative/contrastive examples in the prompt

**Mechanism**: show the model what an *invalid* value looks like
alongside the constraint (e.g. "not: 'reliable'/'invalid'/'neutral' —
those are not legal values"), directly targeting the exact failure mode
RB-3a observed (the model inventing plausible-sounding words). This is a
variant of 3a with more information per prompt, not a different
mechanism category.

**Why not proposed for RB-3b directly**: strictly more complex than 3a
for an untested first attempt — violates the "minimum experiment to
answer the question" principle this project followed for RB-2b (owner:
"design and execute the minimum additional experiment required"). Worth
trying as a fallback only if 3a (the plain value-hint) produces a
**Partial/mixed** result specifically on the "model still invents novel
words" failure mode, not as a first attempt.

## Summary table

| Mechanism | Category | Tests the research question? | Proposed for RB-3b? |
|---|---|---|---|
| 3a. Prompt-side value hint | Training-time (conditioning signal) | Yes — directly | **Yes — this is RB-3b's design** |
| Enum-constrained decoding | Inference-time | No — masks the question by construction | No — flagged as a separate future production-hardening item |
| Structured/grammar-constrained generation | Inference-time (broader) | No — same reason, more powerfully | No — separate future item, new dependency, out of scope |
| 3b. Loss reweighting | Training-time (objective change) | Yes, but a materially riskier, more invasive change | No — candidate for a later RB-3c if 3a proves insufficient |
| 3c. Task decomposition | Training-time (dataset-content change) | Yes, but requires new data/format | No — blocked this phase (no new datasets), future candidate |
| 3d. Contrastive/negative examples | Training-time (prompt variant of 3a) | Yes | No — reserve as a fallback if 3a shows the "invents novel words" failure mode specifically |

## Conclusion

RB-3b's proposed single-variable design (3a) is the correct first
experiment: it is the cheapest, least invasive, most directly motivated
by RB-3a's own confirmed result, and — unlike the two inference-time
mechanisms — it actually tests whether the *model* acquires the
vocabulary rather than papering over the question with an external
constraint. The other five mechanisms remain documented, plausible, and
available as follow-ups depending on RB-3b's outcome, per its own
stopping conditions (§10 of the experimental design) — none should be
combined with RB-3b's first run, and none are implemented by this
document.
