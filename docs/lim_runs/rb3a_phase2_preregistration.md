# RB-3a Phase 2 — Pre-Registration: Schema-Hint Experiment

**Written and committed before training runs.** This document fixes the
hypothesis, the single independent variable, the configuration, and the
success/failure thresholds in advance, so the later results write-up
cannot be shaped by the outcome.

## Question being asked

RB-3 found that a checkpoint trained on `self_critique` never produces
the expected output schema (`finding`/`explanation`/`resulting_status`
— 0/24 held-out matches) and instead often echoes the prompt's input
fields back. RB-3a's audit ruled out dataset-formatting inconsistency,
sequence-length truncation, and loss-masking bugs, and found that
`self_critique`'s required output key names never appear anywhere in its
input/instruction (0/104), unlike `extraction`'s (132/132).

**This experiment does not ask whether the model gets better overall.**
It asks one narrower question: **is the failure mode fundamentally a
schema-acquisition problem (fixable by making the schema visible in the
conditioning signal) rather than a reasoning problem?**

## Independent variable (exactly one)

A new `schema_hint: bool` flag, default `False` everywhere (so every
other experiment's behavior, past and future, is byte-identical to
today). When `True`, the prompt template (`training.py`'s
`_format_example_text`/`_prompt_prefix`, shared verbatim by
`scripts/lim/run_evaluation.py`) inserts one additional line between
`### Context` and `### Response`:

```
### Required JSON keys:
['finding', 'explanation', 'resulting_status']
```

This line is derived **at runtime from each example's own
`expected_output` key names** (never its values) — it is not stored in
the dataset, does not change dataset contents, and does not leak any
example's specific answer (the key set is identical across all 104
`self_critique` examples, confirmed by RB-3a's audit, so this is
equivalent to a fixed task-format instruction, not per-example
information). Training and evaluation prompts are built from the exact
same function, so they cannot diverge on this shape.

## Everything else held fixed vs. RB-3's exact baseline run

| Parameter | Value | Same as RB-3? |
|---|---|---|
| LoRA rank / alpha / dropout / target modules | r=8, alpha=16, dropout=0.0, `[q_proj,k_proj,v_proj,o_proj]` | Yes — frozen default, untouched |
| Optimizer | `adamw_8bit` (unchanged) | Yes |
| Learning rate | 2e-4 | Yes |
| max_steps / save_steps | 40 / 10 | Yes |
| batch_size / gradient_accumulation_steps | 1 / 4 | Yes |
| max_seq_length | 256 | Yes |
| Base model | `lim_training/qwen3_4b_model` | Yes |
| Dataset | `self_critique@self_critique-v1.0.0`, same 104 train / held-out examples | Yes — dataset contents unchanged |
| Seed | 42 | Yes — identical to RB-3's training run, for the most direct possible comparison |
| Evaluation pipeline | Same held-out test+validation set (n=24 for `self_critique`), same `--max-new-tokens 512`, same balanced-JSON stopping criterion, same `eval_metrics.py` scoring code | Yes — no scoring logic changes |
| **Prompt conditioning** | **schema hint added** | **No — this is the one variable** |

## Primary pre-registered metric

**Schema-match rate**: fraction of `self_critique` held-out examples
(n=24, same set RB-3 evaluated) whose parsed model output's key set is
**exactly** `{finding, explanation, resulting_status}` — no more, no
fewer keys. This is chosen specifically because it is uncontaminated by
the content-correctness question and by `reasoning_quality`'s
demonstrated fallback-extraction artifact (RB-3's own finding) — it
measures the schema-acquisition question directly and nothing else.

- **RB-3 baseline (no hint)**: 0/24 (0%).

| Outcome | Threshold | Interpretation |
|---|---|---|
| **Success** | Schema-match rate ≥ 15/24 (≥ 60%) | Schema-acquisition confirmed as the dominant, fixable bottleneck. Making the schema visible in the input resolves most of the failure. |
| **Partial / mixed** | Schema-match rate 1/24–14/24 | Schema visibility helps but is not sufficient alone — task complexity and/or step/rank budget remain live contributing causes. Do not force a single-cause conclusion. |
| **Failure** | Schema-match rate ≤ 2/24 (statistically indistinguishable from the 0/24 baseline) | Rejects schema-acquisition as the primary bottleneck. The failure is more likely rooted in task complexity (generative authorship demand) or step/capacity budget than in schema visibility. Stop; do not introduce additional variables in the same run. |

## Secondary / contextual metrics (reported, do not override the primary verdict)

- `self_critique_quality` (was exactly 0.0/24) — expected to move only if
  schema-match AND content correctness both improve; a schema-match
  improvement with `self_critique_quality` still at 0 would show the
  model learned the shape but not yet the content.
- `reasoning_quality` — reported for continuity with RB-3, but flagged
  again as unreliable evidence on its own (RB-3's fallback-extraction
  finding applies here too).
- **Input-echo rate**: fraction of outputs that echo prompt input fields
  instead of attempting a critique (was 8/24 = 33% in RB-3). Expected to
  drop if the hint disambiguates the task from the input schema.
- Parse rate (was 19/24 = 79% in RB-3).
- `extraction`'s own zero-shot scores on this checkpoint, reported per
  the same convention as RB-3 (not a same-checkpoint regression check —
  this checkpoint never trains on `extraction` either way).

## Stop rule

If the outcome is **Failure** per the table above: stop, document the
result plainly as a rejection of the schema-acquisition-as-primary-cause
hypothesis, and do not introduce additional variables (e.g., step count,
rank) in a follow-up without designing a new, separate single-variable
experiment. If **Success**: the bottleneck is identified; the natural
next question (a separate future experiment) is whether this fix should
generalize as a permanent prompt-template change. If **Partial/mixed**:
report both contributing factors honestly rather than picking one.

## Provenance

Written prior to launching the schema-hint training run. Will be
committed before that run starts, so this file's git history timestamp
independently establishes it preceded the result.
