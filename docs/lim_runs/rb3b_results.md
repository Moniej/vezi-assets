# RB-3b Results — Categorical Value-Vocabulary Experiment

**Status: PRIMARY METRIC CONFIRMED, per the pre-registered definition —
and that confirmation immediately surfaces a new, previously-hidden
bottleneck (near-total mode collapse in which specific value is chosen).
Per instruction, this document stops here: no RB-3c, no additional fixes,
pending review.**

Design: `docs/lim_runs/rb3b_experimental_design.md` (frozen before this
run; no changes to hypothesis, success criteria, metrics, controls, or
analysis plan were made during implementation — see the one genuine
implementation blocker encountered, §"Infrastructure note" below, which
was resolved without any config change per the established protocol).

## Configuration verified identical to RB-3a except the one variable

| Parameter | RB-3a (baseline/control) | RB-3b (this run) | Same? |
|---|---|---|---|
| Training run | `13a8fdf7-...` | `8d265e59-3901-40e0-aa02-4a81df5dc86f` | — |
| Eval run | `761b5236-...` | `5beeee3c-a76a-4b94-ab0e-c3cbadc1d294` | — |
| LoRA config | r=8, alpha=16, dropout=0.0, `[q/k/v/o_proj]` | identical | Yes |
| Hyperparameters | max_steps=40, lr=2e-4, batch=1, grad_accum=4 | identical | Yes |
| Seed | 42 | 42 | Yes |
| Dataset | `self_critique@self_critique-v1.0.0`, 104 train | identical | Yes |
| Held-out set | 24 examples (test+validation) | same 24 `unique_id`s | Yes |
| `schema_hint` | True | True (held fixed, not re-tested) | Yes |
| **`value_hint`** | **False** | **True** | **No — the one variable** |

## Infrastructure note (genuine blocker, resolved without config change)

The first training attempt (`e673ae50-bddc-4442-9f9a-99d5ee6e3fc2`) failed
with `RuntimeError: Unsloth: No or negligible GPU memory available for
fused cross entropy.` Traced to an external process (a game, `FIFA23.exe`)
concurrently holding ~1.9GB of the 6GB laptop GPU's VRAM, leaving ~4GB
free. This was classified as an infrastructure failure, not a code or
design defect — recorded honestly in the registry (`started`→`failed`,
config confirmed identical: `schema_hint: true, value_hint: true`). After
the process was closed (GPU confirmed fully free: 6001MB), the identical
training command was retried byte-for-byte and succeeded
(`8d265e59-...`). No training configuration was changed to work around
this, consistent with this project's standing infrastructure-failure
protocol.

## Primary pre-registered metrics: valid-value rate (among schema-matched outputs)

| Field | RB-3a baseline (n schema-matched=18) | RB-3b (n schema-matched=24) | Bootstrap 95% CI (RB-3b) |
|---|---:|---:|---|
| `finding` valid-value rate | 0/18 (0%) | **24/24 (100%)** | [1.0, 1.0] |
| `resulting_status` valid-value rate | 0/18 (0%) | **24/24 (100%)** | [1.0, 1.0] |

**Against the pre-registered thresholds** (success ≥60%, per field,
independently): **both fields reach 100%, decisively clearing the
threshold.** By the letter of the pre-registered primary metric — does
the model produce a *legal* categorical value — **RB-3b's hypothesis is
confirmed.**

## Control metric (must not regress): schema-match rate

| | RB-3a | RB-3b |
|---|---:|---:|
| Schema-match rate | 18/24 (75%) | **24/24 (100%)** |

**Not regressed — improved further.** Every output in this run had
exactly the correct key set. The pre-registered non-regression control
is satisfied with room to spare; there is no evidence the added
value-constraint text destabilized the already-solved key-structure
problem.

## The new bottleneck this result surfaces: near-total mode collapse, not per-example discrimination

The pre-registered primary metric asked only whether the emitted value is
*legal*, deliberately not whether it is *correct* (§5 of the design:
"this experiment tests vocabulary *constraint* learning, not full task
correctness"). Checking correctness directly against each example's
ground truth reveals why that distinction matters enormously here:

- **`finding`: 0/24 exact matches.** The model produced `fail` in 22/24
  outputs and `pass` in 2/24 — **`concern` was never produced, not once**.
  This held-out set's actual ground-truth distribion is `concern=12,
  pass=12, fail=0` — **the model's single most common answer (`fail`) is
  the one value that never appears as the correct answer anywhere in this
  held-out set**, and is also the *rarest* class in the training data
  (8/104), not the majority class. This is not a majority-class
  fallback in the usual sense — it's a collapse onto a specific token that
  doesn't track either the held-out distribution or the training
  distribution in an obvious way.
- **`resulting_status`: 18/24 raw matches, but for the wrong reason.**
  The model produced `unvalidated_ai_interpretation` in **24/24 outputs —
  every single one**, and never produced `blocked_by_self_critique`, not
  once. This held-out set's ground truth is `unvalidated_ai_interpretation
  =17, blocked_by_self_critique=7`. The 18/24 raw agreement figure
  (`self_critique_quality`-adjacent, though that metric scores on
  `finding` specifically, not this field) is **entirely an artifact of
  always guessing the majority class** (which for this 2-way field does
  happen to be the training-set majority, 79/104) — all 7 genuinely
  `blocked_by_self_critique` examples are answered wrong.

**`self_critique_quality` remains exactly 0.0/24 — completely
unchanged from RB-3a**, because that metric scores `finding` by exact
match, and `finding` never matches (0/24). The 100% valid-*value* result
and the 0% correct-*value* result are simultaneously true and are not in
tension — they measure different things, exactly as the pre-registration
anticipated distinguishing (§5), but the *degree* of collapse (a single
dominant token per field, with one class — `concern` — never produced at
all) is a specific, previously-invisible failure mode that the schema
-only and value-vocabulary-only experiments could not have surfaced
before this point: RB-3 couldn't see it (wrong keys entirely), RB-3a
could show valid keys but invalid values, and only now, with valid values
in hand, is it visible that the values chosen are governed by something
other than per-example evidence.

## Secondary / contextual metrics

| Metric | RB-3a | RB-3b | Paired diff (RB-3b − RB-3a) |
|---|---:|---:|---|
| Parse rate | 20/24 (83%) | 24/24 (100%) | improved |
| `self_critique_quality` | 0.0/24 | 0.0/24 | unchanged |
| `reasoning_quality` | 0.0945 | 0.1014 | +0.0069, CI [−0.014, 0.028] — includes zero, not distinguishable from noise |
| `semantic_equivalence` | 0.0296 | 0.2699 | large increase — but see caveat below |
| `agreement_with_teacher` | (n/a, not reported in RB-3a's headline) | 0.2361 | — |

**Caveat on `semantic_equivalence`'s increase**: this metric does fuzzy,
partial-credit field matching (not exact match), so the `resulting_
status` mode-collapse's 18/24 raw agreement plausibly drives a real share
of this increase — it should not be read as evidence of improved genuine
task understanding without further decomposition, which this experiment
was not designed to perform (the pre-registered analysis plan treats this
as a secondary/contextual metric only, not a pass/fail criterion, exactly
for this reason).

## `extraction` (contextual, same methodological caveat as RB-3a)

`extraction` parse rate 27/27, `semantic_equivalence` 0.4589,
`grounded_correctness` 0.8519. As in RB-3a, this checkpoint never trained
on `extraction`, and the eval run applies `--schema-hint`/`--value-hint`
globally (only `self_critique` has a mapped value-hint field, per
`_VALUE_HINT_FIELDS`, so `extraction` only picks up the schema-hint
component) — not directly comparable to RB-3/RB-3a's own `extraction`
numbers for the same reason already documented in `rb3a_results.md`.

## Conclusion

**Per the pre-registered success criteria exactly as written, RB-3b's
hypothesis is confirmed**: making the legal value set visible in the
prompt raised the valid-value rate from 0% (RB-3a) to 100% for both
constrained fields, with the schema-match control metric not only
preserved but improved (75%→100%). This is a real, decisive, evidence
-based result — the model reliably learned to emit tokens from the
correct constrained vocabulary once that vocabulary was made visible,
exactly mirroring RB-3a's own schema-key finding one level down the
compositional problem (keys → this experiment: values).

**This same result exposes a new, previously-hidden bottleneck**: valid
-value acquisition happened via what the per-example ground-truth
comparison shows is near-total mode collapse — `concern` (a real,
non-trivial fraction of ground truth) was never produced at all;
`blocked_by_self_critique` was never produced at all; the model appears
to default to a small number of fixed tokens per field largely
independent of per-example context, rather than genuinely discriminating
among the legal values using the evidence in each prompt. This was
invisible in RB-3 (wrong keys) and in RB-3a (right keys, wrong/illegal
values) — it only becomes visible now that the values are legal enough to
inspect for correctness at all.

Per instruction: **this document stops here.** No RB-3c is proposed or
started, and no additional fix has been implemented. The evidence is
reported plainly for review before any decision about the next
experiment.

## Artifacts preserved

- Failed attempt `e673ae50-bddc-4442-9f9a-99d5ee6e3fc2` (GPU-memory
  infrastructure failure, honestly recorded, not deleted).
- Training run `8d265e59-3901-40e0-aa02-4a81df5dc86f` (checkpoint-40 used
  for eval) and its 4 intermediate checkpoints.
- Eval run `5beeee3c-a76a-4b94-ab0e-c3cbadc1d294` (130 examples, all 8
  registered types, `schema_hint_enabled: true, value_hint_enabled: true`
  recorded in metrics).
- RB-3a's artifacts (`13a8fdf7-...`, `761b5236-...`) remain the unmodified
  baseline this run was compared against.
