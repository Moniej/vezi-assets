# LIM-5 Priority 3 — Curriculum Design

## Conclusion: an elaborate multi-stage curriculum is NOT supported by current data

The owner's example progression (extraction → entities → corporate
actions → relationships → reasoning → self critique) presupposes six
distinct, usable skill-differentiated datasets. Priority 1's audit found:

- **`extraction` and `corporate_actions` are currently identical data**
  (§Priority 1, finding #1) — not two curriculum stages, one.
- **`entity_recognition`** has a data-quality defect (label inconsistency,
  Priority 1 finding #2) that curriculum ordering cannot fix — training on
  it earlier or later in a sequence doesn't resolve the underlying
  ambiguity; that requires better source data (real mention spans), not
  sequencing.
- **"relationships"** (`knowledge_graph_completion`) has exactly 1 usable
  example — cannot support any curriculum stage.
- **"reasoning"** (`financial_reasoning`) has 0 registered examples
  (failed its LIM-1 audit gate) — cannot support a stage either.
- Only **`extraction`/`corporate_actions`** (159, one dataset) and
  **`self_critique`** (128) are both large enough and clean enough
  (Priority 1) to be genuine curriculum candidates.

**With only two viable, distinct dataset types, there is no evidentiary
basis for a multi-stage curriculum.** Recommending one anyway would be
imposing a plausible-sounding structure the data doesn't support —
precisely what the owner's instruction warns against.

## What IS weakly supported: a single ordering hypothesis, untested

`extraction`'s mean quality_score (0.988) is higher than `self_critique`'s
(0.787), and `extraction` is a more direct structured-extraction task
while `self_critique` requires evaluating a claim's logical validity — a
plausible "simpler skill first" ordering. This is a **hypothesis**, not a
finding: no controlled experiment has yet tested whether interleaving
order affects outcome, and `self_critique`'s context does not actually
presuppose the model has learned `extraction` first (it supplies the
draft claim directly, not raw filing text requiring prior extraction).

## Recommendation

Do not implement a curriculum for LIM-5. If a future phase trains on both
`extraction` and `self_critique` together, treat "extraction-ordered-first"
as exactly one candidate variable for a future single-variable experiment
(Priority 5 discipline) — never assumed correct without a controlled
comparison against interleaved/random ordering.
