# LIM-3 Root-Cause Diagnosis — `entity_recognition` Output Collapse

Scope: diagnosis only. No training-pipeline code was modified. Every claim
below is backed by either a direct read of the unmodified pipeline code or
a reproducible, read-only inspection of real tensors from the real
registered dataset and the real trained checkpoint's tokenizer/model
config (`scripts/lim/diagnose_training_pipeline.py` — re-running it
reproduces identical output).

## Hypothesis under test

"The repeated `Coca-Cola` entity output across held-out entity-recognition
examples strongly suggests prompt-label leakage or loss masking over the
full prompt rather than response-only supervision."

**Confirmed — and the actual defect is larger than the hypothesis stated.**
It is not only prompt-label leakage; the dominant effect is
**padding-label leakage**, which the hypothesis didn't name but which the
evidence shows is the single largest contributor.

## Evidence chain

### 1. Prompt construction (`src/ngxrot/lim/training.py::_format_example_text`)

```python
def _format_example_text(ex: dict, eos_token: str) -> str:
    return (f"### Instruction:\n{ex['instruction']}\n\n"
           f"### Context:\n{_json.dumps(ex.get('context', {}), default=str)}\n\n"
           f"### Response:\n{_json.dumps(ex.get('expected_output', {}), default=str)}{eos_token}")
```

Real example (`entity_recognition:1`), reproduced verbatim by the
diagnostic script:

```
### Instruction:
Identify this named entity and its type as mentioned in the filing.

### Context:
{"ticker": null}

### Response:
{"canonical_name": "GTCO", "entity_type": "company", "resolved_ticker": null}<|im_end|>
```

This whole string — instruction, context, AND response — is tokenized as
one sequence with no boundary marker passed to the tokenizer and no
separate handling of the response span downstream.

### 2. Tokenizer configuration actually in effect at training time

Directly inspected on the loaded tokenizer (not assumed from static config):

| | value |
|---|---|
| `pad_token` | `'<|vision_pad|>'` (id `151654`) — **distinct** from `eos_token` |
| `eos_token` | `'<|im_end|>'` (id `151645`) |
| `padding_side` | **`'left'`** |

`training.py`'s `_JsonlExampleDataset.__init__` calls
`tokenizer(text, truncation=True, max_length=max_length, padding="max_length")`
with no `padding_side` override, so it inherits this tokenizer default:
**every sequence is padded on the LEFT to the fixed `max_length=256`.**

### 3. Labels (`src/ngxrot/lim/training.py::_JsonlExampleDataset.__init__`)

```python
enc = tokenizer(text, truncation=True, max_length=max_length, padding="max_length")
enc["labels"] = list(enc["input_ids"])
```

`labels` is a verbatim copy of `input_ids` — **no `-100` masking is applied
anywhere**: not on the padding region, not on the prompt region. Verified
directly on a real tensor:

```
n_positions_with_label==-100 = 0
labels == input_ids everywhere? True
```

### 4. Where the real content actually lands, given left-padding

For `entity_recognition:1` (max_length=256):

```
n_real_tokens (attention_mask==1) = 52   (20.3% of the sequence)
n_pad_tokens  (attention_mask==0) = 204  (79.7% of the sequence)
padding location: LEFT
```

Decoding `labels[0:28]` (the first 28 positions — where a response-only
mask would look for "prompt," if padding were on the right as commonly
assumed) shows **28 repeats of `<|vision_pad|>`**, not the instruction
text — because with left-padding, the first 204 positions of every
sequence are pad, and the real 52-token prompt+response only occupies the
LAST 52 positions (confirmed: `labels[-52:]` decodes to exactly the
instruction+context+response text above).

**This means 204 of 256 label positions (79.7%) are the single repeated
pad token, fully unmasked, counted as a real supervised target at every
one of those positions.** Checked across all 39 real accepted
`entity_recognition` examples (not just one), to confirm this is
systematic rather than a one-off:

```
n_examples=39
mean pad% = 77.1   min=75.0   max=80.1
```

Every single training example has 75–80% of its loss-contributing label
sequence consumed by the pad token.

### 5. Data collator / Trainer inputs

```
trainer.data_collator = <function default_data_collator ...>
collated batch keys: ['input_ids', 'attention_mask', 'labels']
```

`training.py`'s `run_training()` constructs `Trainer(model=model, args=args,
train_dataset=train_ds, eval_dataset=eval_ds)` with **no `data_collator`
argument** — HF Trainer falls back to `default_data_collator`, which only
stacks the already-built per-example tensors; it performs no additional
masking or response-boundary logic. No `position_ids` are passed in the
batch either, so the model receives only `input_ids`/`attention_mask`/
`labels` and must derive positions internally. (`attention_mask` itself
IS correct — it does zero out the 204 left-padded positions, so the model
does not *attend* to padding. The defect is specifically that the *loss*
target does not respect the same boundary the *attention* mask does.)

## Root cause (proven)

**The training loss for every `entity_recognition` example is computed over
the entire 256-token sequence, unmasked. ~77–80% of that sequence is a
single repeated pad token (`<|vision_pad|>`), and essentially all of the
remainder is the instruction+context prompt, which is near-identical
across every example. The genuinely novel, per-example signal — the
actual entity-recognition response — occupies roughly 24 of 256 label
positions, under 10% of the total loss mass.**

With only 12 optimizer steps (effective batch size 4, ⇒ ~48 examples seen,
~1.3 epochs over 36 training examples) and a rank-8 LoRA adapter, nearly
all of the already-tiny gradient budget is spent on the trivial,
high-frequency objective of reproducing the pad token and the fixed
instruction template — both of which are nearly loss-free to learn almost
immediately — leaving negligible effective training signal for the actual
task.

## What remains inference, not proof

The specific hallucinated content (`{"entity": "Coca-Cola", "type":
"Company"}`, ticker `"KO"`) is **consistent with** — but not directly
provable from — the base model's own pretraining prior for this
Alpaca-style `### Instruction:/### Context:/### Response:` template
surfacing mostly unmodified, because the LoRA update was too small and
too diluted (per the proven mechanism above) to override it. This is a
reasonable inference from the evidence, not a claim verified against
Qwen3's actual pretraining corpus (which isn't available for inspection) —
flagged here explicitly as the one part of this diagnosis that is
plausible rather than proven.

## Scope discipline

No file under `src/ngxrot/lim/` was modified during this investigation.
`scripts/lim/diagnose_training_pipeline.py` only reads the real registered
dataset, the real tokenizer/model, and builds one throwaway `Trainer`
purely to inspect `trainer.data_collator` and batch keys — it never calls
`.train()`. Re-running it reproduces identical output (a genuine
reproducible experiment, not a one-time observation).

## Recommendation for LIM-4 (not implemented here)

The fix, once approved, is response-only loss masking: set
`labels[i] = -100` for every position that is either padding
(`attention_mask[i] == 0`) or part of the prompt (before the response
boundary — already computable today via the same "tokenize prompt-only,
count tokens" technique this diagnosis used to find `n_prompt_tokens`).
This is exactly LIM-4's stated first objective ("correct response-only
loss masking") — left entirely for that phase, per the instruction not to
modify the training pipeline until this diagnosis was reviewed.
