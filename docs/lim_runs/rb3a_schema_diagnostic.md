# RB-3a — Schema-Learning Diagnostic

**Purpose**: RB-3 (`docs/lim_runs/rb3_results.md`) found that a checkpoint
trained on `self_critique` never learns the required output schema
(`finding`/`explanation`/`resulting_status` — 0/24 held-out outputs match
it, 33% instead echo the prompt's input fields back). Per instruction,
this document isolates *why*, before spending any further compute on
optimization. **This is an investigation, not a training experiment** —
no new checkpoint is proposed here except the single, cheapest possible
diagnostic run in Phase 2, and even that is not to be run without
sign-off.

Eight candidate causes were named: dataset size, dataset formatting,
prompt template, response schema complexity, loss masking, sequence
length, teacher-output consistency, or another cause. Two are already
ruled out below by direct audit; one strong candidate has been found.

## Phase 0 — Audit findings (already done, zero-cost, no training involved)

| Candidate cause | Verdict | Evidence |
|---|---|---|
| **Dataset formatting / schema consistency** | **RULED OUT** | All 104 training examples' `expected_output` use the identical, correct key set `('finding', 'explanation', 'resulting_status')` — 104/104, no exceptions. The training data itself is not the source of schema confusion. |
| **Sequence length / truncation** | **RULED OUT** | Full formatted-example token length: min 105, p50 123, p95 179, max 210 — all well under `max_seq_length=256`. **0/104 examples exceed 256 tokens**; no truncation occurs at all, let alone into the response span. |
| **Teacher-output consistency (value diversity)** | **Likely not the cause** | `finding` values: `fail=8, concern=52, pass=44` (reasonably balanced, 3 real classes). `resulting_status`: `blocked_by_self_critique=25, unvalidated_ai_interpretation=79` (imbalanced but not degenerate — both values occur many times). No evidence of a collapsed or contradictory teacher signal. |
| **Prompt template / schema visibility** | **Strong candidate — see below** | See next section. |

### The strong candidate: the output schema's key names never appear in the input

Directly compared against `extraction` (RB-1/RB-2's proven-successful
training target), by literal string search across each example's
instruction + context:

| Dataset | Does the input ever contain the exact output key name? | Rate |
|---|---|---|
| `extraction` | Context literally contains `"fact_type": "..."` in every example — the model can learn to copy an existing key/value straight from input to output. | **132/132 (100%)** |
| `self_critique` | Neither the instruction nor the context ever contains the literal word `finding` anywhere. | **0/104 (0%)** |

`extraction`'s instructions are also uniform boilerplate ("Extract the
material fact from this dividend filing as structured data.") paired
with a context dict that already has the answer's shape embedded in it.
`self_critique`'s instructions are terse, per-example category labels
("Challenge this draft conclusion on the question:
unevidenced_inference.") that state *what to think about*, never *what
JSON shape to answer in*. The model has to bind the key names
`finding`/`explanation`/`resulting_status` to their meaning purely by
repeated exposure to the response side of 104 examples over 40 steps
(~1.5 effective epochs at batch 1 × grad-accum 4) — a categorically
harder schema-binding problem than `extraction`'s, where the key is
already sitting in the visible input every single time.

This also lines up with a second real difference not yet listed above:

| Candidate cause | Status | Evidence |
|---|---|---|
| **Response schema complexity (task type)** | **Plausible contributing factor, entangled with the above** | `extraction`'s response requires 2-3 short fields, frequently copied/lightly transformed from context (`description` is often near-verbatim from the source text). `self_critique`'s response requires an authored, multi-sentence analytical `explanation` referencing specific facts from context — a generative-reasoning task, not an extraction task. This is a harder learning target in its own right, independent of the schema-visibility issue above, and the two are not separable by audit alone (see Phase 2). |

## Phase 1 — Remaining audit-only checks (cheap, recommended before any training)

1. **Loss-masking correctness specific to `self_critique`.** **RULED
   OUT.** Decoded the supervised (non `-100`) label span for the first 5
   `self_critique` training examples via `_JsonlExampleDataset` +
   `_build_response_only_labels` directly (no training involved, decode
   -only). All 5 supervised spans begin exactly at `{"finding": "...",
   ...}` with no clipping — the `finding` key is fully intact and
   correctly supervised in every sampled case. This is not a masking bug.
2. **Instruction/context length and specificity vs. `extraction`** —
   already covered above (schema-key visibility); no further audit-only
   action remains.

## Phase 2 — Minimal single-variable training diagnostic (requires sign-off)

If Phase 1 finds no masking bug, the cheapest diagnostic that actually
distinguishes "schema was never visible" from "task is just too hard for
this step/rank budget" is:

- **Schema-hint experiment**: retrain on `self_critique` with a fixed,
  literal schema hint appended to every instruction (e.g. `"Respond with
  JSON: {\"finding\": ..., \"explanation\": ..., \"resulting_status\":
  ...}"`), holding every other variable at the frozen default (r=8, 40
  steps, lr=2e-4, seed=42) — single variable: prompt template.
  - If schema-match rate rises substantially above 0/24: confirms
    **schema-visibility** was the bottleneck, not task difficulty or step
    budget — the natural next question becomes whether this should be a
    permanent prompt-template change (project-wide) or scoped to
    generative tasks specifically.
  - If schema-match rate stays near 0/24 even with the hint spelled out:
    rules out schema-visibility, points instead at **task complexity /
    step-and-rank budget** (self_critique's generative-authorship demand
    may simply need more steps and/or more capacity than the
    extraction-tuned r=8/40-step default was ever validated for) — the
    next single-variable question would be a step-count sweep scoped to
    `self_critique` specifically (analogous to RB-1, but for this
    dataset), not a rank change (RB-2's closure was scoped to
    `extraction` and does not need to be revisited to ask this).

**Dataset size** as a standalone cause is not independently testable
without new data (blocked this phase, same constraint as RB-9/10/11) —
it remains a live but untestable candidate until that constraint is
lifted; the schema-hint experiment above is the correct next step
regardless, since it is a strict prerequisite for even knowing whether
size would matter.

## Summary

| Candidate | Status |
|---|---|
| Dataset formatting | Ruled out |
| Sequence length | Ruled out |
| Loss masking | **Ruled out** |
| Teacher-output consistency | Likely not the cause |
| Prompt template (schema visibility) | **Strong candidate** |
| Response schema complexity | Plausible, entangled with the above |
| Dataset size | Untestable this phase (blocked) |

**Recommendation**: all four audit-only checks (dataset formatting,
sequence length, loss masking, teacher-output consistency) are complete
and rule out everything except the input/prompt template and the
task's inherent generative complexity. Pending sign-off, the single
schema-hint training diagnostic in Phase 2 is the correct next step
before any further `self_critique` training or hyperparameter work. No
training has been started as part of this document — everything above
was decode/audit-only, zero gradient steps.
