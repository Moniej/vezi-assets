# RB-3a Phase 2 Results — Schema-Hint Experiment

**Status: PRIMARY HYPOTHESIS CONFIRMED**, with an important secondary
finding that narrows what "confirmed" means. Pre-registration:
`docs/lim_runs/rb3a_phase2_preregistration.md` (committed before this
run).

## Configuration verified identical to RB-3 except the one variable

| Parameter | RB-3 (baseline) | RB-3a (this run) | Same? |
|---|---|---|---|
| Training run | `ebe73677-...` | `13a8fdf7-24c8-4475-b6fe-de391c07777c` | — |
| Eval run | `3389f4a1-...` | `761b5236-7bea-40be-bdd7-6d26f6a82e3d` | — |
| LoRA config | `r=8, alpha=16, dropout=0.0, [q/k/v/o_proj]` | identical | Yes |
| Hyperparameters | `batch_size=1, grad_accum=4, max_steps=40, lr=2e-4` | identical | Yes |
| Seed | 42 | 42 | Yes |
| Dataset | `self_critique@self_critique-v1.0.0` | identical | Yes |
| Held-out example set (`self_critique`) | 24 examples | same 24 `unique_id`s, confirmed by direct set comparison | Yes |
| Eval settings | `--include-validation --max-new-tokens 512`, balanced-JSON stopping criterion | identical | Yes |
| **`schema_hint`** | **False** | **True** | **No — the one variable** |

## Primary pre-registered metric: schema-match rate

Fraction of `self_critique` held-out outputs (n=24) whose parsed key set
is exactly `{finding, explanation, resulting_status}`.

| | RB-3 | RB-3a | 
|---|---:|---:|
| Schema-match rate | 0/24 (0%) | **18/24 (75%)** |
| Bootstrap 95% CI (RB-3a) | — | [0.583, 0.917] — excludes the RB-3 baseline entirely |

**Against the pre-registered thresholds** (success ≥60%, partial 1–14/24,
failure ≤2/24): **75% clears the success threshold**, and the CI's own
lower bound (58.3%) still clears it. **Verdict: schema-acquisition is
confirmed as the dominant, fixable cause of RB-3's structural failure.**
Making the expected output schema visible in the input resolved the vast
majority of the 0/24 schema-match failure observed in RB-3.

## Secondary / contextual metrics

| Metric | RB-3 | RB-3a | Paired bootstrap diff (RB-3a − RB-3) |
|---|---:|---:|---|
| Parse rate | 19/24 (79%) | 20/24 (83%) | modest, as expected — schema-match was the larger gap, not raw JSON validity |
| Input-echo rate (outputs containing prompt input fields instead of a critique) | 8/24 (33%) | 1/24 (4%) | large drop, consistent with the hypothesis |
| `self_critique_quality` | 0.0/24 | **0.0/24 — unchanged** | n/a |
| `reasoning_quality` | 0.0441 | 0.0945 | mean diff +0.0504, CI [0.023, 0.077] — excludes zero, real |
| `semantic_equivalence` | 0.0054 | 0.0296 | modest increase |
| `grounded_correctness` | 0.2687 | 0.1111 | decreased — noisy, small n, not part of the pre-registered success criterion |

## Important secondary finding: schema structure learned, categorical value vocabulary not

Inspecting the 18 schema-matched outputs directly reveals **why
`self_critique_quality` stayed at exactly 0.0/24 despite the 75%
schema-match win**: the model now reliably produces the right *keys*,
but not the right *values*.

- `finding` is supposed to be one of exactly `{fail, concern, pass}`
  (a categorical label). **0 of 18** schema-matched outputs used any of
  these three values — instead, `finding` consistently contains a
  full free-text sentence (e.g. `"The draft conclusion is not valid
  because it confuses correlation with causation."`).
- `resulting_status` is supposed to be one of exactly
  `{blocked_by_self_critique, unvalidated_ai_interpretation}`. **0 of 18**
  used either value — instead the model invents plausible-sounding but
  never-trained-on words (`"revised"`, `"neutral"`, `"invalid"`).

This is exactly the scenario the pre-registration's secondary-metrics
section flagged as a live possibility ("a schema-match improvement with
`self_critique_quality` still at 0 would show the model learned the
shape but not yet the content") — and it is what happened. The
schema-acquisition fix worked precisely as scoped: it fixed the
*structural* failure (wrong keys / echoed input), not the separate,
previously-invisible-behind-the-bigger-failure problem of learning the
correct *categorical value vocabulary* for `finding`/`resulting_status`.

Four of the six remaining "unparsed" outputs are also worth noting
qualitatively: they clearly attempt the correct three keys
(`finding`/`explanation`/`resulting_status`) but fail strict JSON syntax
(single quotes instead of double, or a markdown `###`-prefixed
pseudo-JSON instead of a real object) — a shallower, syntax-level defect
distinct from both the schema-key problem (fixed) and the value
-vocabulary problem (open).

## Methodological note — a discovered eval-script coupling, not fixed here

The `--schema-hint` flag on `scripts/lim/run_evaluation.py` applies
uniformly to **every** dataset type evaluated in a run, deriving each
example's hint from that example's *own* `expected_output` keys. This
run evaluated all 8 registered types with `--schema-hint` on, which means
`extraction`'s eval prompts in this run also received an
`extraction`-specific schema hint (`['fact_type', 'description',
'numeric_value']`) — even though this checkpoint was never trained on
`extraction`, hinted or not. As a result, **this run's `extraction`
numbers (parse rate 24/27, `semantic_equivalence` 0.4016) are not
directly comparable to RB-3's `extraction` numbers** (9/27, 0.1111): two
things changed at once (checkpoint AND eval-prompt shape for that type),
not one. This does not affect or invalidate the primary `self_critique`
comparison above (schema_hint was applied consistently, in both training
and eval, only for `self_critique`, matching the pre-registration).
Flagged as an architectural note for future experiments — **not fixed
here**, since scoping the flag per-trained-type isn't needed for this
experiment's own conclusion and doing so now would be an unrelated
change outside RB-3a's scope.

## Conclusion

**Confirmed**: schema-acquisition (not reasoning capacity, not the
memorized-heuristic hypothesis) was the dominant, correctly-identified
bottleneck behind RB-3's structural failure. A single, cheap,
dataset-content-preserving conditioning-signal change (making the
schema visible in the input) took the schema-match rate from 0% to 75%,
with a CI that excludes the baseline.

**Not yet confirmed / new open question**: fixing schema acquisition did
not, by itself, fix categorical value-vocabulary acquisition
(`finding`/`resulting_status`'s enum values). `self_critique_quality`
remains at exactly 0.0/24 for a different, now-isolated reason than RB-3
reported — RB-3's report attributed the 0.0 to the model never
attempting the right shape; this report shows that even when the shape
is right, the categorical values are still wrong 100% of the time. This
is a narrower, more tractable-looking problem than RB-3's original
diagnosis, but it is untested and should not be assumed to resolve on its
own.

## Recommendation — next experiment

The evidence points to a **value-vocabulary-learning diagnostic** as the
single highest-priority next step, analogous in spirit to RB-3a itself:
before touching hyperparameters, check whether the categorical value sets
for `finding`/`resulting_status` are visible/learnable from the training
data in a way comparable to how the key names now are — e.g. whether an
explicit enumeration hint (`"finding must be exactly one of: fail,
concern, pass"`, following the same runtime-derived-from-`expected_
output`, no-dataset-change pattern established here) resolves it, mirroring
this experiment's own design. This should be pre-registered the same way
RB-3a was, as its own single-variable follow-up (tentatively "RB-3b"),
not folded into further step-count or rank changes.

## Artifacts preserved

- Training run `13a8fdf7-24c8-4475-b6fe-de391c07777c` (checkpoint-40 used
  for eval) and its 4 intermediate checkpoints.
- Eval run `761b5236-7bea-40be-bdd7-6d26f6a82e3d` (130 examples, all 8
  registered types, `schema_hint_enabled: true` recorded in metrics).
- RB-3's original artifacts (training `ebe73677-...`, eval `3389f4a1-...`)
  remain the unmodified baseline this run was compared against.
