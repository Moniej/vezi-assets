# RB-3b Mode-Collapse Investigation

**Purpose**: understand *why* RB-3b's checkpoint achieved 100% valid
-value generation for `finding`/`resulting_status` while apparently
ignoring per-example evidence (`rb3b_results.md`), before designing
RB-3c. This is a read-only investigation against the already-trained
RB-3b checkpoint (`8d265e59-.../checkpoint-40`) — **no training, no code
change to the pipeline, nothing implemented beyond diagnostic scripts**.
All raw probe data is preserved at `docs/lim_runs/
rb3b_mode_collapse_probe_data.json`; the scripts that produced it are
`scripts/lim/rb3b_mode_collapse_probe.py` (primary tool),
`scripts/lim/rb3b_token_inspect.py` and `scripts/lim/
rb3b_determinism_check.py` (small exploratory checks kept for
provenance — see §4).

---

## 1. Distribution analysis — training labels vs. held-out ground truth vs. generated outputs

| | `finding` | | | `resulting_status` | |
|---|---|---|---|---|---|
| Source | fail | concern | pass | blocked_by_self_critique | unvalidated_ai_interpretation |
| Training set (n=104) | 8 (7.7%) | 52 (50.0%) | 44 (42.3%) | 25 (24.0%) | 79 (76.0%) |
| Held-out set, ground truth (n=24) | 0 | 12 (50%) | 12 (50%) | 7 (29%) | 17 (71%) |
| RB-3b generated, **stored** eval run (n=24) | 22 (92%) | 0 | 2 (8%) | 0 | 24 (100%) |
| RB-3b generated, **fresh** regeneration this session (n=24) | 0 | 0 | 24 (100%) | 0 | 24 (100%) |

Three independent facts jump out:

- **`concern` — the single most frequent training label (50%) — was never
  generated once, in either the stored run or the fresh regeneration.**
  This immediately rules out a naive "collapses to the training-majority
  class" explanation for `finding`: if training frequency alone drove the
  collapse, `concern` should be the *most* likely output, not the least.
- **The specific *fixed point* the model collapses to for `finding`
  is itself session-dependent** — the officially-recorded RB-3b run
  collapsed to `fail` (the training *minority* class, 7.7%); an
  independent fresh regeneration in this investigation's session
  collapsed to `pass` instead. Both sessions agree on the one thing that
  matters most: `concern` is essentially never produced.
- **`resulting_status`'s collapse target (`unvalidated_ai_interpretation`)
  is stable across both sessions** and does coincide with the
  training-majority class (76%) — but §5 below shows this coincidence is
  not the explanation; the base (untrained) model already had a
  near-identical prior before any fine-tuning happened at all.

## 2. Per-class performance — confusion matrices, precision/recall/F1

(Computed from the official RB-3b stored eval run, `5beeee3c-...`, n=24.)

**`finding`** (3-class):

| actual \\ predicted | fail | concern | pass |
|---|---:|---:|---:|
| fail (n=0) | 0 | 0 | 0 |
| concern (n=12) | 10 | 0 | 2 |
| pass (n=12) | 12 | 0 | 0 |

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| fail | 0.000 (0 correct / 22 predicted) | undefined (n=0 true) | 0.000 |
| concern | undefined (0 predicted) | 0.000 (0/12) | 0.000 |
| pass | 0.000 (0/2 predicted) | 0.000 (0/12) | 0.000 |

**Every cell of every per-class metric is 0** — not one single correct
`finding` prediction across all 24 held-out examples, despite 100% of
outputs being a *legal* value.

**`resulting_status`** (2-class):

| actual \\ predicted | blocked_by_self_critique | unvalidated_ai_interpretation |
|---|---:|---:|
| blocked_by_self_critique (n=7) | 0 | 7 |
| unvalidated_ai_interpretation (n=17) | 0 | 17 |

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| blocked_by_self_critique | undefined (0 predicted) | 0.000 (0/7) | 0.000 |
| unvalidated_ai_interpretation | 0.708 (17/24) | **1.000** (17/17) | 0.829 |

The 0.708 precision / 1.000 recall / 0.829 F1 on
`unvalidated_ai_interpretation` looks like a real, partially-working
classifier at first glance — **it is not**. Precision 0.708 and recall
1.000 with 0.000 on the other class is the exact, unavoidable signature
of a constant classifier evaluated on an imbalanced set (predict the same
class every time; your precision on that class equals its base rate,
your recall on it is perfect by construction, and the other class scores
zero on every metric). This is not partial competence — it is the
textbook fingerprint of total collapse.

## 3. Confidence analysis — confidently collapsing, or defaulting under uncertainty?

Two genuinely different fields, two genuinely different answers.

### `resulting_status`: confidently collapsing

Full-vocabulary top-1 probability and entropy, read directly from the
real generation's own logits at the exact decision step, for all 24
examples: **top-1 probability 0.999–1.000, entropy 0.005–0.011** (out of
a maximum possible entropy of ~11.9 nats for this vocabulary size). This
is not "uncertain, but happens to default" — it is **maximally confident,
every single time, regardless of context**, including the 7/24 examples
where the correct answer was the *other* class. The model is not
hedging; it has a near-total, context-blind commitment to one specific
token.

### `finding`: partially uncertain, but with `concern` robustly suppressed

Full-vocabulary top-1 probability: 0.435–0.879. Entropy: 0.515–1.050 —
meaningfully higher than `resulting_status`'s, and genuinely variable
across examples (not a flat, fixed number every time). This is **real,
non-trivial uncertainty**, not confident collapse in the same sense.
However, within that uncertainty, one pattern is completely stable across
every single example in both sessions tested: **`concern`'s relative
share among the three legal candidates never exceeds ~0.23 and is often
under 0.08** — it is consistently, robustly the least-favored option,
even on the 12/24 examples where it is the *correct* answer. The
model's uncertainty is a genuine contest between `fail` and `pass`; `concern`
is barely in the running at any point.

### Ground-truth correlation check (fine-tuned model, in-session)

Cross-tabulating the model's own relative-probability argmax against
ground truth (n=24): **10/24 correct overall — but 10/12 on `pass`-truth
examples and exactly 0/12 on `concern`-truth examples.** The model's
"accuracy" is entirely explained by a fixed preference for a `pass/fail`
binary that happens to align with the `pass` cases; it has no observed
sensitivity to `concern` as a category at all.

## 4. Token-level probability analysis — methodology, including two discarded attempts

Getting a trustworthy confidence measurement took three attempts; the
first two are documented here deliberately, because the way they failed
is itself informative and this project's standing discipline is to
disclose methodology problems rather than quietly fix and hide them.

**Attempt 1 (discarded)**: reconstructed the decision-point prefix by
concatenating the prompt with a *hand-typed* compact-JSON string
(`'{"finding": "'`) and re-tokenizing it. This silently used an
out-of-distribution prefix — the model actually generates pretty-printed
JSON (`{\n  "finding": "fail",\n  ...`), never the compact form assumed.
Caught because the reported "top-1 token" didn't match the value that
was actually recorded during real generation.

**Attempt 2 (discarded)**: fixed the pretty-printing bug by extracting
the real prefix text from the *stored* raw generation and re-tokenizing
that. Still produced a top-1 token that contradicted the stored,
already-generated value for at least one example. Root-caused via a
dedicated determinism check (`rb3b_determinism_check.py`): the **same
prompt, same checkpoint, called three times in the same process is
perfectly deterministic** (identical output all 3 trials) — but that
determinism does **not** hold *across separate process/session
invocations*: a fresh session produced `pass` for an example the
original, officially-recorded eval run had produced `fail` for, with
everything else held equal. This is a real, confirmed (not
hypothesized) cross-session numerical instability, most plausibly from
non-associative floating-point accumulation in 4-bit-quantized/optimized
attention kernels — not a code bug, and not something this investigation
attempts to fix.

**Final approach (used for every number above)**: re-generate each
example fresh, once, in a single self-consistent session, with
`output_scores=True` to capture the *exact* real per-step logits — no
retokenization of decoded text anywhere in the decision-point prefix.
Every reported top-1 token is asserted, in code, to equal the token
actually generated next at that position (a hard, self-verifying
correctness check derived from greedy decoding's own definition); the
probe script raises immediately if this invariant is ever violated. It
was not violated in any of the 24 examples in the final run.

**Base-model comparison (the same session, same real prefixes, `peft`'s
`disable_adapter()` context manager — no second model load, no extra
GPU memory)**: for every example, the identical decision-point prefix was
also evaluated with the LoRA adapter disabled, reading the **untrained
base model's own prior** at that exact position.

## 5. Ranked causal mechanisms — confirmed observations vs. hypotheses

### Rank 1 — CONFIRMED (directly measured, not inferred): the collapse substantially predates this fine-tuning run

| Field | Fine-tuned vs. base-model argmax agreement | Fine-tuned vs. base relative-prob shift (avg) |
|---|---|---|
| `resulting_status` | **24/24 (100%)** identical argmax | ≤0.0001 — no measurable change |
| `finding` | **21/24 (87.5%)** identical argmax | fail +14.4pp, concern +1.7pp, pass −16.0pp |

For `resulting_status`, the 40-step, rank-8 LoRA adapter had **no
measurable effect whatsoever** on this decision — the untrained base
Qwen3-4B model already assigns ~100% probability to
`unvalidated_ai_interpretation` at this exact prompt position, before any
task-specific training. RB-3b's fine-tuning did not create this collapse;
it inherited it unchanged.

For `finding`, fine-tuning did produce a real, measurable shift (roughly
+14pp toward `fail`, −16pp away from the base model's even-more-extreme
`pass` dominance) — but the shift changed the *margin*, not the
*outcome*, in 21 of 24 cases. `concern`'s share barely moved (+1.7pp) and
remained the least-favored option in the base model too — meaning
**`concern`'s suppression is not a training-frequency artifact at all**
(it is the training-set plurality class, 50%) — it is a property the
*untrained* base model already had, likely reflecting `concern`'s lower
prior likelihood as a bare English word/verdict token in this exact
grammatical slot compared to the far more common binary
pass/fail collocation, inherited from general pretraining, not from this
project's data.

This is the single most important, directly-evidenced finding of this
investigation: **the dominant cause is not something RB-3b's training
introduced — it is a pre-existing base-model prior that a 40-step,
rank-8 LoRA adapter did not have enough training signal to override**,
fully for `resulting_status` and substantially for `finding`.

### Rank 2 — CONFIRMED (observed, not yet explained): a field-order asymmetry in confidence

`finding` is the *first* field emitted (right after the fixed
schema/value-hint boilerplate) — the model must commit to a categorical
verdict with zero self-generated reasoning tokens preceding it.
`resulting_status` is the *last* field, preceded by the model's own
(lengthy, free-text) `explanation`. This ordering correlates cleanly with
the confidence asymmetry observed (§3): `resulting_status`'s decision,
made after many tokens of self-attention context, is far more
confident/peaked (though wrongly so) than `finding`'s, made cold. This
correlation is real and observed directly in this data; **whether field
order is *causal* here (as opposed to, e.g., simply reflecting that a
2-way decision is inherently easier to collapse on than a 3-way one) is
not tested by this investigation** and is listed as a hypothesis, not a
confirmed mechanism.

### Rank 3 — HYPOTHESIS (untested): response-only loss masking dilutes gradient signal on value tokens

Previously identified in `rb3b_mechanism_review.md` §3b: every response
token is supervised equally; the free-text `explanation` field (dozens of
tokens) numerically dominates the loss relative to the handful of tokens
that make up `finding`/`resulting_status`'s values. Still plausible as a
*contributing* factor to why 40 steps wasn't enough training signal to
overcome the base-model prior (Rank 1) — but now clearly secondary to
Rank 1, not the primary driver, since Rank 1's base-model comparison
shows the prior exists independent of this run's training dynamics
entirely.

### Rank 4 — HYPOTHESIS (untested): insufficient step count/capacity specifically for overturning a strong pretrained prior

The real, partial shift observed for `finding` (Rank 1) suggests more
training signal (steps and/or rank) *can* move the needle — the open
question is how much would be needed, and whether it would ever be
enough for `resulting_status`'s near-total (~100%) base prior. Untested
directly; the natural next single-variable question (see §6).

### Rank 5 — HYPOTHESIS (untested, deprioritized): task/label intrinsic difficulty (`concern` as a harder "middle" category)

A generic classification-difficulty explanation (middle/ambiguous
categories are often intrinsically harder to learn than the extremes)
remains plausible in principle but is now a weaker candidate than it
looked before Rank 1's base-model finding: `concern`'s suppression is
already present in the *untrained* base model, which had no opportunity
to find it "hard to learn" from this project's data at all. This
hypothesis would need to explain why the *pretrained* model disfavors
`concern` specifically, which is a different (and much less
project-specific) question than originally framed.

## 6. Decision matrix — highest-information-gain single-variable intervention for RB-3c

| Candidate intervention | Directly targets | Expected information gain | Cost/risk | Overlaps a closed question? |
|---|---|---|---|---|
| **Increase `max_steps` for `self_critique` specifically (mirrors RB-1's own methodology, single variable)** | Rank 1 + Rank 4 directly: does more training signal measurably shrink the fine-tuned-vs-base-model gap already confirmed to exist? | **Highest** — directly tests whether the confirmed mechanism (insufficient signal to override the base prior) is fixable by the cheapest available lever, using a base-model-relative-probability shift as an *additional*, more sensitive pre-registerable metric (not just discrete accuracy) | Low — cheap (~10-20 min), no new code, no loss-computation risk | No — RB-1 closed a *different* dataset (`extraction`); step count for `self_critique` specifically has never been tested |
| Loss reweighting toward value-token positions (mechanism review §3b) | Rank 3 directly | Moderate — would show whether amplified gradient signal alone (without more steps) closes the gap faster | Moderate-high — touches loss computation, the exact category of change that caused LIM-4's real inf/NaN bug; needs careful, incremental validation | No, but higher engineering risk for a first attempt |
| Re-open LoRA rank specifically for `self_critique` (r=16/32 retested on this dataset only) | Rank 1/4 (capacity dimension) | Moderate — RB-2/RB-2b already showed r=16/32 are *worse* for `extraction`; unclear this transfers, and re-testing risks appearing to relitigate a formally closed question even though the design doc explicitly reserved this as in-scope for a *different* dataset | Moderate — 2-3 training runs | Adjacent to RB-2's closure (which was explicitly scoped to `extraction`, not `self_critique` — a new question, but a sensitive one to reopen without strong justification) |
| Structured/enum-constrained decoding at inference time | None of the ranked mechanisms — this would mask the collapse rather than explain or fix it | Lowest for *this* investigation's question (already excluded from RB-3b for the same reason, `rb3b_mechanism_review.md` §1-2) | Low engineering risk, but answers a different question entirely | No, but out of scope by design |

**Recommendation for the highest-information-gain next single-variable
experiment**: a step-count experiment scoped to `self_critique`
specifically (holding `value_hint`/`schema_hint` both fixed at `True`,
r=8, all else identical to RB-3b), pre-registering the **fine-tuned-vs
-base-model relative-probability gap** (this investigation's own Rank-1
metric) as a primary success criterion *in addition to* discrete
accuracy — since discrete accuracy alone showed zero information in
RB-3b (0/24 on `finding`) while the probability-gap metric already shows
real, measurable movement is possible. This is a recommendation for
review, not a proposal to begin — **no RB-3c has been designed or
started**, per instruction.

## 7. Artifacts

- `scripts/lim/rb3b_mode_collapse_probe.py` — primary diagnostic (kept,
  documents its own two discarded attempts in its module docstring).
- `scripts/lim/rb3b_token_inspect.py`, `scripts/lim/
  rb3b_determinism_check.py` — small exploratory checks that surfaced the
  pretty-printed-JSON bug and the cross-session non-determinism finding;
  kept for provenance.
- `docs/lim_runs/rb3b_mode_collapse_probe_data.json` — full per-example
  probe output (24 examples × fine-tuned and base-model relative
  probabilities, top-1 tokens/probabilities/entropy, stored vs. fresh
  generated values) backing every number in this document.
- No training run, no checkpoint, no pipeline code was created or
  modified by this investigation.
