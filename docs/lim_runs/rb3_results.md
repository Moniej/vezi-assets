# RB-3 Results — Train on `self_critique` instead of `extraction`

**Status: NEGATIVE RESULT (reproducible, informative).** The
pre-registered criterion technically passed through its `reasoning_
quality` branch, but the evidence shows that pass does not reflect
genuine reasoning capability — it is explained by a fallback path in the
evaluation metric, not by improved model behavior. The finding that
matters is `self_critique_quality` staying at exactly 0.0/24 combined
with a 0/24 output-schema match rate. **Working hypothesis: the failure
mode is output-schema learning, not reasoning failure**, pending the
diagnostic in `rb3a_schema_diagnostic.md`. This experiment is recorded as
a successful elimination of an incorrect direction, not a setback — do
not attempt to improve RB-3 directly; see the diagnostic plan for the
correct next step.

## Hypothesis (as pre-registered in the backlog)

Training on `self_critique` (single variable: dataset, all else identical
to the frozen r=8/40-step baseline) produces a measurable improvement on
`self_critique_quality`/`reasoning_quality`, both 0.0 in every prior run
because no checkpoint had ever trained on this type.

**Success metric**: `self_critique_quality` **or** `reasoning_quality` on
`self_critique`'s held-out test split improves vs. the LIM-5 baseline's
0.0; report `extraction`'s own scores too (different checkpoint, so no
direct regression risk, but report both per the backlog).

## Configuration

- Training run `ebe73677-a6a6-404c-951f-3654617b1812`:
  `self_critique@self_critique-v1.0.0`, seed=42, all hyperparameters at
  the frozen default (`r=8, alpha=16, dropout=0.0, max_steps=40, lr=2e-4,
  batch_size=1, grad_accum=4, max_seq_length=256`) — no overrides.
  `n_train=104`, `final_loss=2.1793`. Built on commit
  `dd2b1e4bceca41f49244fb9ab1582e4ce767a5ac` (post RB-2 closure).
- Eval run `3389f4a1-3b74-4eae-b32d-c399640cca65`: checkpoint-40,
  `--include-validation` (test+validation combined, n=24 for
  `self_critique`, larger than the originally-scoped n=9 test-only split),
  `--max-new-tokens 512`, balanced-JSON stopping criterion, all 8
  registered dataset types evaluated (n=130 total).

## Results — `self_critique` (n=24, the trained type)

| Metric | n | Mean | 95% bootstrap CI | Excludes 0? |
|---|---|---|---|---|
| `self_critique_quality` | 24 | **0.0000** | — (every value exactly 0) | No — dead flat |
| `reasoning_quality` | 24 | 0.0441 | [0.0266, 0.0631] | **Yes** |
| `semantic_equivalence` | 24 | 0.0054 | ~0 (23/24 values are 0) | No |
| `agreement_with_teacher` | 24 | 0.0000 | — | No |
| `grounded_correctness` | 24 | 0.2687 | wide, driven by a subset | not computed (not part of pre-registered metric) |
| Parse rate | — | 19/24 (79%) | — | — |

`self_critique_quality` is **exactly 0/24**, not merely low. Inspecting
the parsed-output key schemas explains why: **0 of 24** outputs use the
expected schema (`finding`/`explanation`/`resulting_status`). The actual
distribution of output shapes is:

| Output keys produced | Count |
|---|---|
| `(conclusion, reasoning)` | 5 |
| `(conclusion, explanation)` | 5 |
| unparsed | 5 |
| `(confidence, draft_direction, draft_magnitude, question, ticker)` — **echoes prompt input fields** | 4 |
| `(confidence, draft_direction, draft_magnitude, response, ticker)` — echoes input | 2 |
| 3 other input-echoing variants | 3 |

**8 of 24 (33%) outputs echo back the prompt's input fields
(`confidence`/`draft_direction`/`draft_magnitude`/`ticker`/`question`)
instead of producing a critique at all.** This is not a content-quality
problem — the model largely failed to learn the required *output schema*
for this task, in a substantial fraction of cases failing to produce a
critique-shaped output whatsoever. `self_critique_quality`'s implementation
(`eval_metrics.py`) does a strict key lookup (`parsed.get("finding")`)
with no fallback, so it correctly scores all of this as 0 — this is the
metric behaving as designed, not a metric bug.

`reasoning_quality` has a fallback (`eval_metrics.py:343-345`: if no exact
`explanation`/`rationale`/`reasoning` key exists, take the first string
value >20 chars) that lets it extract partial lexical-overlap credit from
the `conclusion`/`reasoning`-schema outputs even though the schema is
wrong. That fallback is why this metric is not flat — but a mean of 0.044
with a CI of [0.027, 0.063] is a real, statistically-distinguishable-from
-zero effect that is nonetheless **very small in absolute terms** (every
individual value is under 0.14 on this metric's scale).

## Results — `extraction` (n=27, reported per backlog instruction, not a same-checkpoint regression check)

| Metric | n | Mean | Parse rate |
|---|---|---|---|
| `agreement_with_teacher` | 27 | 0.0864 | 9/27 (33%) |
| `semantic_equivalence` | 27 | 0.1111 | 9/27 (33%) |
| `grounded_correctness` | 27 | 0.1469 | 9/27 (33%) |

This is a **different checkpoint** than any `extraction`-trained run (this
one was trained only on `self_critique`), so there is no direct regression
risk to a previously-shipped artifact — the backlog flagged this
explicitly. Reported only as context: 0.1111 is well below RB-2b's pooled
r=8/`extraction`-trained baseline (0.2623), which is the expected
direction — a checkpoint that never trained on `extraction` scoring lower
on it than one that did is not a finding, just a sanity check that passed.

## Comparison to baseline

- `self_critique_quality`: 0.0 (LIM-3/4/5 baseline) → **0.0** (RB-3). No
  movement at all on the metric the backlog names first.
- `reasoning_quality`: 0.0 (baseline) → 0.0441, CI excludes zero. Real,
  reproducible, but small — driven by a fallback path picking up
  lexical-overlap credit from wrong-schema outputs, not by the model
  correctly performing the task end-to-end.
- Parse rate on the trained type (79%) is reasonable and not the
  bottleneck here — the bottleneck is 1/3 of *parsed* outputs not even
  attempting the critique task (echoing the input instead).

## Conclusion

The pre-registered success metric was an **"or"**: `self_critique_quality`
**or** `reasoning_quality` improving off 0.0. Read strictly, this
technically passes, because `reasoning_quality` has a statistically real,
non-zero effect. Read honestly: this is not the outcome the hypothesis
was written to test for. The hypothesis was that training on
`self_critique` would make the model **learn the skill**
("self_critique_quality... improves... mirroring Experiment 1's result on
a different skill"). Instead:

- The named-first metric (`self_critique_quality`) shows **zero movement**
  — a clean, unambiguous non-improvement, not a borderline or noisy one.
- The metric that did move (`reasoning_quality`) moved for a mechanical
  reason (a fallback string-extraction path in the metric itself) rather
  than because the model reliably produces correct, on-schema critiques.
- A third of the model's outputs on its own trained task don't even
  attempt the right output shape — they echo the prompt's input fields
  back verbatim.

**This is not a mirror of Experiment 1's extraction result.** RB-3 does
not provide evidence that `self_critique` is currently a viable standalone
training target at this step count/data size. The most likely proximate
cause is output-schema learning failure, not a reasoning-quality
ceiling — a model that can't reliably reproduce
`finding`/`explanation`/`resulting_status` can't be fairly judged on the
content of reasoning it isn't consistently attempting to produce.

## Recommendation

- Do **not** promote `self_critique` as a validated training target on the
  strength of this result, and do **not** attempt to improve RB-3 directly
  (e.g. by simply increasing steps or changing hyperparameters).
- Before any repeat attempt, isolate *why* the schema is never learned.
  See `docs/lim_runs/rb3a_schema_diagnostic.md` for the diagnostic plan
  and the audit findings already gathered (two candidate causes are
  already ruled out with evidence; one strong candidate has been
  identified).
- Treat RB-3 as a **negative result, reproducible and informative** —
  consistent with the standing instruction that "a negative result is
  still a successful scientific experiment if it is reproducible." No
  code or metric changes are warranted from this result alone.
- RB-4 (learning rate sweep) and RB-5 (batch size) remain unaffected and
  can proceed independently on the `extraction` target where the r=8/
  40-step baseline is already established.

## Artifacts preserved as the RB-3 negative-result baseline

For future training-improvement work on `self_critique` (post-diagnostic)
to be compared against, these are the frozen reference points — nothing
here should be deleted or overwritten:

- Training run `ebe73677-a6a6-404c-951f-3654617b1812` (immutable registry
  entry + checkpoint files under its `run_dir`).
- Eval run `3389f4a1-3b74-4eae-b32d-c399640cca65` (immutable registry
  entry, all 130 scored examples, including the 24 `self_critique` and
  27 `extraction` examples analyzed above).
