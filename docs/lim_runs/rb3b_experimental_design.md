# RB-3b Experimental Design — Categorical Value-Vocabulary Acquisition

**Status: DESIGN ONLY. No training run has been started. Awaiting review
before implementation begins**, per explicit instruction. This document
exists to be reviewed and approved (or revised) before any code change or
training run for RB-3b.

## 1. Hypothesis

Given RB-3a's confirmed result — that making the output *schema* visible
in the prompt raised the `self_critique` schema-match rate from 0% to
75% — the model can also learn the constrained *categorical values* for
`finding` (must be exactly one of `fail`/`concern`/`pass`) and
`resulting_status` (must be exactly one of
`blocked_by_self_critique`/`unvalidated_ai_interpretation`), if those
value sets are made equally visible in the prompt, by the same kind of
single, runtime-derived, dataset-content-preserving conditioning-signal
change that fixed the key-structure problem.

**This is explicitly framed as a new, independent hypothesis — not an
extension of RB-3a.** RB-3a answered "does the model know what keys to
produce?" This asks "does the model know what values are legal for those
keys?" The two questions are separable, as demonstrated by RB-3a's own
result: 18/24 outputs had the exactly right keys, and 0/18 had a legal
value for either constrained field.

## 2. Rationale

- RB-3a already showed that visibility of a fixed vocabulary
  (the 3 key names) fixes a fixed-vocabulary learning problem, via a
  cheap, dataset-content-preserving, single-variable prompt change. The
  same mechanism is the most direct, most evidence-consistent thing to
  try next for a structurally identical problem (a small, fixed,
  currently-invisible-in-the-input vocabulary).
- The canonical value vocabularies are **governed, not inferred**: the
  production pipeline code itself defines them exactly.
  `src/ngxrot/documents/self_critique.py:23` — `_SEVERITY = {"pass": 0,
  "concern": 1, "fail": 2}` — is the sole source of truth for `finding`'s
  3 legal values. `resulting_status` is set by the same module's logic
  (`self_critique.py:194,198`) to exactly one of `blocked_by_self_
  critique` or `unvalidated_ai_interpretation` for this specific export
  path (`exporters.py::export_self_critique`) — even though
  `vocab.py`'s broader `IMPLICATION_STATUSES` set has 6 members, only
  these 2 are ever reachable through this export. This matters: deriving
  the hint from the wrong source (e.g. the full 6-value `vocab.py` set)
  would hand the model 4 values it can never legitimately produce for
  this task, actively working against the goal. The value-hint must be
  derived from **what this export path actually produces**, not from the
  broader domain vocabulary.

## 3. Single independent variable

A new `value_hint: bool` flag (default `False`, preserving every
existing experiment's byte-identical behavior), analogous in spirit to
RB-3a's `schema_hint`. When `True`, one additional line is appended to
the existing schema-hint block (schema_hint remains `True` — see §4):

```
### Field value constraints:
finding: one of ['fail', 'concern', 'pass']
resulting_status: one of ['blocked_by_self_critique', 'unvalidated_ai_interpretation']
```

**Derivation, and why it is not per-example leakage**: like RB-3a's key
list, this is a fixed, dataset-type-level constant (identical across
every `self_critique` example — confirmed in RB-3a's audit that the key
set itself is 104/104 uniform; the value *sets* are properties of the
task's governed vocabulary, not of any individual example's specific
correct answer). Two derivation options, to be decided at implementation
time and stated explicitly in the run's `notes` field for auditability:

- **(a) Observed-in-training-data derivation** (consistent with how
  `_schema_hint_line` already works — computed from the loaded training
  examples, not hardcoded): collect the distinct values seen for each
  field across all 104 training examples. Risk: if a legal value happens
  not to appear in this specific 104-example sample (plausible for a
  3-way categorical with n=8 for the rarest class, `fail`, per RB-3a's
  audit), the hint would be incomplete and misleading in the opposite
  direction of what's intended.
- **(b) Governed-source derivation** (from `self_critique._SEVERITY`'s
  keys, and a hardcoded 2-value list matching the two reachable
  branches of `self_critique.py`'s status-assignment logic): guarantees
  completeness regardless of sampling, but introduces a dependency on
  reading a value out of application code rather than dataset content —
  a new kind of coupling this project hasn't used before for a prompt
  -template decision.

  **Verified before finalizing this design**: directly checked the 104
  training examples' `expected_output` values — observed `finding` values
  are exactly `{pass, concern, fail}` (matching `_SEVERITY`'s 3 keys
  exactly, no more, no fewer) and observed `resulting_status` values are
  exactly `{blocked_by_self_critique, unvalidated_ai_interpretation}`
  (matching the 2 reachable branches in `self_critique.py`, not
  `vocab.py`'s broader 6-value set). **(a) and (b) agree exactly for
  this dataset version** — so either derivation produces an identical
  hint. **Recommendation: use (a)** (derive from training data, same
  mechanism `_schema_hint_line` already uses) to keep the change
  self-contained within `training.py` without a new cross-module import,
  now that (a)/(b) agreement is confirmed rather than assumed.

## 4. Controls — held fixed from RB-3a's own confirmed configuration

| Parameter | Value | Rationale |
|---|---|---|
| `schema_hint` | **True** (held fixed, not toggled) | RB-3a's confirmed win must be preserved, not re-tested. Turning it off here would reintroduce RB-3's original confound and make the result uninterpretable. |
| LoRA config | r=8, alpha=16, dropout=0.0, `[q/k/v/o_proj]` | Frozen production default (RB-2/RB-2b). |
| Hyperparameters | max_steps=40, save_steps=10, lr=2e-4, batch_size=1, grad_accum=4, max_seq_length=256 | Frozen production default. |
| Seed | 42 | Identical to RB-3/RB-3a, for the most direct comparison chain. |
| Dataset | `self_critique@self_critique-v1.0.0`, same 104 train examples | Unchanged. |
| Held-out evaluation set | Same 24 `self_critique` examples RB-3/RB-3a used (`--include-validation`, confirmed identical `unique_id` set in RB-3a) | Unchanged — this is what makes RB-3a's own eval run a valid, reusable baseline instead of requiring a fresh "value_hint=False" control run. |
| Evaluation settings | `--max-new-tokens 512`, balanced-JSON stopping criterion | Unchanged. |
| **`value_hint`** | **RB-3a's own run = False (baseline, already recorded); this experiment = True** | **The one variable.** |

**No new "value_hint=False" training run is needed as a control** — RB-3a's
already-completed training run (`13a8fdf7-...`) and eval run
(`761b5236-...`) serve as the exact `value_hint=False, schema_hint=True`
baseline, since nothing about that configuration changes. This keeps
RB-3b to a single new training run + single new eval run, not two.

## 5. Pre-registered success criteria

Two independent, jointly-required per-field metrics, computed only over
the outputs that already have the correct schema keys (i.e., conditioned
on the RB-3a win being preserved — an output with the wrong keys can't be
scored on value-correctness at all, and should be reported as its own
denominator, not silently excluded from the headline number).

**Primary metric**: **valid-value rate**, per field, among schema
-matched outputs (n will vary run to run; RB-3a's schema-matched n was
18/24) —
fraction whose `finding` value ∈ `{fail, concern, pass}` (regardless of
whether it's the *correct* one of the three — this experiment tests
vocabulary *constraint* learning, not full task correctness, exactly
mirroring RB-3a's schema-match metric testing key presence, not content
correctness), and separately, fraction whose `resulting_status` value ∈
`{blocked_by_self_critique, unvalidated_ai_interpretation}`.

- RB-3a baseline: **0/18 (0%) for both fields.**

| Outcome | Threshold (either field, evaluated independently) | Interpretation |
|---|---|---|
| **Success** | Valid-value rate ≥ 60% (mirroring RB-3a's own bar) | Value-vocabulary visibility, like schema-key visibility, is confirmed as fixable by the same class of intervention. |
| **Partial/mixed** | 1–59% | Helps but insufficient alone; report per-field, since `finding` (3-way) and `resulting_status` (2-way) may respond differently — do not average them into one number. |
| **Failure** | ≤ 2/18-scale-equivalent (statistically indistinguishable from RB-3a's 0/18) | Rejects the value-hint mechanism as the primary lever for this specific problem; points toward a training-time (not prompt-time) intervention — see the mechanism review, `rb3b_mechanism_review.md`. |

**Preserved control metric (must not regress)**: schema-match rate on the
same 24 held-out examples must remain **statistically indistinguishable
from or better than RB-3a's 75% (18/24)** — i.e., its paired-bootstrap CI
against RB-3a's own run should not show a significant decrease. If
schema-match rate regresses significantly, the experiment has introduced
a new confound (the added prompt text somehow destabilized the
already-solved key-structure problem) and the result must be reported as
invalidated, not interpreted on the value-vocabulary question alone.

**Secondary/contextual metric**: `self_critique_quality` (was 0.0/24 in
both RB-3 and RB-3a). If both value fields reach a high valid-value rate
AND the specific values chosen happen to match the teacher's recorded
answer, this metric would finally move — reported for continuity, but
not a pre-registered pass/fail criterion on its own, since getting a
valid-*category* right (this experiment's actual question) is logically
prior to and separate from getting the *correct* category (a harder,
un-scoped-here question).

## 6. Evaluation metrics

All computed the same way RB-3a's were computed (direct inspection of
`model_output_parsed` from the eval registry, no new scoring-code
dependency required for the analysis itself, though see §9 for a proposed
first-class metric to add if RB-3b proceeds):

1. Valid-value rate for `finding` (primary).
2. Valid-value rate for `resulting_status` (primary).
3. Schema-match rate (control, must not regress).
4. Parse rate, input-echo rate (contextual, continuity with RB-3/RB-3a).
5. `self_critique_quality`, `reasoning_quality` (contextual, not
   pass/fail criteria here).

## 7. Statistical analysis plan

- **Bootstrap CIs** (`eval_analysis.bootstrap_ci`, same 2000-resample,
  seed=42 default used throughout this project) for each primary
  valid-value-rate metric, treating each schema-matched example as an
  independent Bernoulli observation (1 = valid value, 0 = invalid),
  exactly as RB-3a's schema-match-rate CI was computed.
- **Paired comparison** (`eval_analysis.paired_bootstrap_ci_of_difference`)
  between RB-3b's schema-match rate and RB-3a's, paired by `unique_id`
  (identical held-out set, so full pairing is possible) — this is the
  regression-guard check in §5, not the primary question.
- Given the small n (schema-matched subset will likely be ≤24, possibly
  smaller if schema-match itself shifts), report **exact counts alongside
  every rate** (e.g. "13/18 = 72%"), not just percentages — consistent
  with this project's established discipline (RB-1's n=12 concern, RB-2's
  explicit small-n caveats) of never letting a percentage obscure a small
  denominator.
- `finding` (3-way) and `resulting_status` (2-way) are reported and
  interpreted **separately**, never pooled into a single "value
  correctness" number — they are different-cardinality problems and a
  pooled average could mask one field succeeding while the other fails.

## 8. Risks

1. **Prompt length growth**: adding a value-constraint line lengthens
   every prompt further on top of the already-added schema-hint line.
   RB-3a's audit found self_critique's longest formatted example
   (schema-hint enabled) at 227 tokens, still under the 256-token
   `max_seq_length` — but this experiment adds more text. Must re-verify
   the full-length token-count audit (the same check performed in RB-3a,
   §"Verified" note in the schema-hint implementation commit) before
   running, to rule out truncation as a confound rather than assuming it
   is still safe.
2. **Interaction with schema-match rate**: it's plausible the added
   value-constraint text could *help* schema adherence further (more
   explicit structure in the prompt) or *hurt* it (a longer, more complex
   hint block competing for attention/context budget on a small model).
   Either direction is a real possible outcome and must be reported, not
   assumed away — this is exactly why §5 pre-registers schema-match rate
   as a required non-regression control, not just an afterthought.
3. **Governed-source vs. observed-source disagreement** (§3): **checked,
   resolved.** `_SEVERITY`'s 3 values and the 104 training examples'
   observed `finding` values are identical sets; same for
   `resulting_status` against the 2 reachable `self_critique.py` status
   branches. No disagreement found for this dataset version — if the
   dataset is ever re-exported/re-versioned, this check should be
   redone, not assumed to still hold.
4. **Small subgroup sizes**: `finding=fail` had only 8/104 training
   examples (RB-3a's audit) — the rarest class. Even if the *vocabulary*
   (which 3 words are legal) is learned, whether the model ever
   *chooses* `fail` in held-out generation is a separate, much
   lower-powered question this experiment is not designed to resolve
   (only 24 held-out examples total, likely 1-3 with `fail` as the
   correct answer) — flagged in advance so a "the model never says fail"
   observation isn't over-interpreted as a vocabulary-learning failure
   when it may just be a base-rate/small-n artifact.
5. **Single seed**: like RB-3a, this design uses seed=42 only. If the
   result is a borderline "Partial/mixed" call, per this project's
   established discipline (RB-2b's precedent), a multi-seed follow-up
   would be warranted before drawing a firm conclusion — not built into
   this design up front, to keep the first pass minimal and cheap,
   consistent with RB-3a's own single-seed-first approach.

## 9. Implementation notes (for the reviewed design, not yet executed)

If this design is approved, the following code changes would be needed
— listed here for review completeness, **none implemented**:

1. A `value_hint: bool` parameter threaded through
   `_format_example_text`/`_prompt_prefix`/`_JsonlExampleDataset`/
   `run_training`, exactly mirroring how `schema_hint` was added in RB-3a
   (same files: `training.py`, `scripts/lim/train.py`,
   `scripts/lim/run_evaluation.py`).
2. A dataset-type-scoped mapping of field → legal-value-list, sourced per
   §3's decision (recommended: governed source for `finding`, cross
   -checked against observed training data for `resulting_status`) —
   likely a small constant local to `training.py`, scoped to
   `self_critique` only (not a generic mechanism for every dataset type,
   since only `self_critique` currently has this problem — matches this
   project's "generic across 17 shapes without a per-type branch" design
   principle only where genuinely generic; a per-type value-vocabulary
   table is inherently type-specific and should be declared as such, not
   forced into a false generic shape).
3. Optionally, a first-class `finding_value_valid`/`resulting_status_
   value_valid` metric added to `eval_metrics.py`'s `PER_EXAMPLE_METRICS`
   (following the existing pattern of `self_critique_quality` etc.) so
   this analysis doesn't have to be redone by hand-inspecting
   `model_output_parsed` every time — recommended if RB-3b or a
   follow-up is likely to be repeated, but not strictly required for a
   single run (RB-3a's analysis was done by direct inspection without a
   new metric, and that was sufficient).

## 10. Stopping condition

Run exactly one training + one eval (reusing RB-3a's run as the
`value_hint=False` baseline, per §4 — no new baseline run needed). Do not
proceed to a multi-seed replication, a combined schema+value ablation
grid, or any mechanism from `rb3b_mechanism_review.md` without a
dedicated review of this run's result first. If **Success**: the
production template gains a second confirmed conditioning-signal fix,
and the natural next question (separate, future experiment) becomes
whether `self_critique_quality` itself finally moves once both schema
and value vocabulary are addressed. If **Failure**: stop, document
plainly, and consider training-time interventions (§`rb3b_mechanism_
review.md`) as the next design, not a hyperparameter change on the same
prompt-only lever. If **Partial/mixed**: report per-field, do not average,
and consider whether the two fields warrant separate follow-up
experiments rather than one combined verdict.
