# RB-1 Results — Training Duration Experiment

Full infrastructure incident record: `docs/lim_runs/rb1_infrastructure_
failure_log.md`. This document covers the experiment itself, now that a
clean run was obtained.

## Hypothesis (pre-registered in `lim6_research_backlog.md`)

Increasing `max_steps` from 12 (never plateaued in any prior run) to 40
on `extraction`, all else identical to the LIM-5 Experiment 1 baseline,
further improves `semantic_equivalence`.

## Configuration

Identical to LIM-5 Experiment 1 (`b05875df-...`) except `max_steps=40`,
`save_steps=10` (vs. 12/4): same dataset (`extraction@extraction-v1.0.0`),
same seed (42), same LoRA config (`r=8, alpha=16, dropout=0.0`), same
learning rate (2e-4), same base model. Configuration hash and full
environment parity recorded in the infrastructure log.

## Pre-registered success metric — NOT confirmed

| | LIM-5 Exp.1 (`max_steps=12`) | RB-1 (`max_steps=40`) |
|---|---:|---:|
| `semantic_equivalence` on `extraction` (n=12) | 0.1704 | **0.1666** |
| `grounded_correctness` on `extraction` | 0.4387 | **0.3006** |

The pre-registered success criterion was "`semantic_equivalence` > 0.1704,
no regression in `grounded_correctness`/`hallucination_risk`."
**`semantic_equivalence` did not increase** (0.1666 vs. 0.1704 — a small
decrease, on a 12-example test set, so within the range where a couple of
examples flipping would explain it entirely) and **`grounded_correctness`
regressed** (0.4387 → 0.3006). By the letter of the pre-registered
criteria, this hypothesis is **not confirmed**.

## What DID move, reported for completeness (not to substitute for the above)

| Metric | LIM-5 Exp.1 | RB-1 | Direction |
|---|---:|---:|---|
| `agreement_with_teacher` on `extraction` (exact-match) | 0.0 | **0.1666** | First non-zero result on this metric for `extraction` across every run to date |
| `hallucination_risk` on `extraction` | 0.2917 (n=8) | **0.0** (n=6) | Improved, smaller applicable sample |
| `corporate_actions` `semantic_equivalence` | 0.1134 | 0.1852 | Improved |
| Overall `agreement_with_teacher` (all 8 types) | 0.0 | 0.0765 | Improved |
| Mean latency | 15.13s | 12.83s | Improved, continuing the downward trend since LIM-4's spike |
| Training loss curve | Still decreasing at step 12 (2.99 → 2.39) | **Visibly plateaued** by step 40 (1.965 → 1.962 → 1.961 → 1.962) | Confirms 40 steps reaches convergence where 12 did not |

## Interpretation

Training to convergence (40 steps, loss plateaued) produced a checkpoint
that is measurably different from the 12-step one — better on exact-match
agreement and hallucination avoidance, essentially flat-to-slightly-worse
on the two metrics this experiment was specifically pre-registered
against. This is not a clean win, and is reported as such. Plausible
reading: more training steps help the model commit more confidently to
*some* schema (raising exact-match hits when it happens to guess right,
per Priority 2's "shallow heuristic" finding), without necessarily
improving semantic faithfulness to the specific held-out answers, and a
12-example test set is small enough that a handful of examples changing
answer plausibly accounts for the entire observed movement in either
direction.

## Conclusion

**Reproducible, not proven as an improvement on the pre-registered
metric.** The infrastructure question (does the identical configuration
succeed given adequate system memory) is resolved: yes, confirmed by
direct reproduction. The model-quality question (does more training
improve semantic correctness) is **not** confirmed by this single run
against its own pre-registered criterion, even though it is not a clean
negative either — several other metrics moved favorably. Per the
project's discipline, a null/mixed result against the pre-registered
metric is reported honestly, not reframed around whichever secondary
metric looks best.

## Approved conclusions (owner review, 2026-07-28)

Recorded verbatim as the accepted findings of RB-1 — no broader success
or failure classification beyond what these four statements support:

1. **The infrastructure hypothesis is confirmed.** The previous failure
   was caused by temporary operating-system memory pressure, not the LIM
   training pipeline.
2. **Forty training steps are sufficient to reach convergence** for this
   dataset and configuration (`extraction`, `r=8`, seed 42, lr 2e-4).
3. **Increasing training duration alone does not provide convincing
   evidence of improved semantic performance** on the current held-out
   dataset.
4. **The held-out `extraction` evaluation set (n=12) is too small to draw
   strong statistical conclusions from a single run.**

These four statements are the full, final scope of what RB-1
established. Nothing beyond them should be inferred from this
experiment.

## Addendum: retroactive uncertainty quantification (`eval_analysis.py`)

Per the follow-up instruction to quantify uncertainty before further
sweeps, computed paired bootstrap confidence intervals (2000 resamples,
seed 42) on the mean difference (steps=40 − steps=12) for each metric,
using the same 12 held-out `extraction` unique_ids scored by both
checkpoints:

| Metric | Mean diff | 95% CI | Distinguishable from noise? |
|---|---:|---|:---:|
| `semantic_equivalence` | -0.0038 | [-0.1132, 0.1078] | **No** — confirms this genuinely is noise, not a real regression |
| `grounded_correctness` | -0.1380 | [-0.4034, 0.1518] | **No** — the apparent point-estimate drop is NOT statistically distinguishable from no change; the earlier characterization of this as a "regression" is corrected here to "not statistically supported" |
| `agreement_with_teacher` | +0.1666 | [0.0833, 0.2777] | **Yes** — this is the one metric where the CI entirely excludes zero |

This sharpens, rather than overturns, the approved conclusions: the
`semantic_equivalence` null result is now proven (not just observed) to
be indistinguishable from noise at n=12, exactly consistent with approved
conclusion #4. The one real, statistically-supported effect of more
training steps in this experiment is on `agreement_with_teacher` — more
steps measurably increased exact-match correctness even though it did not
measurably change semantic correctness or groundedness. This is a
genuinely new, more precise finding enabled by the strengthened protocol,
not a re-litigation of the approved conclusions.

## Recommendation

- Do not yet conclude "more steps helps" or "more steps doesn't help" —
  one run on a 12-example test set is not sufficient evidence either way
  for the specific pre-registered claim.
- A follow-up (RB-1b) should test an intermediate step count (e.g. 20-25)
  and/or repeat at 40 steps with a different seed to check whether the
  `grounded_correctness` regression and flat `semantic_equivalence` are
  stable findings or small-sample noise.
- The clear, unambiguous, useful result from this run is the loss-curve
  plateau itself — 40 steps is at or past convergence for this dataset
  size/LoRA rank combination, which is valuable information for RB-2
  (LoRA rank sweep) and RB-4 (learning rate sweep): those experiments
  should use a step count that reaches a comparable plateau, not
  necessarily 40 steps for every future config.
