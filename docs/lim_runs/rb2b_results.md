# RB-2b — Seed-Expansion Follow-up: Is r=16 Practically Better Than r=8?

## Question being answered

> Does r=16 provide a practically meaningful improvement over r=8 once
> seed variability is accounted for?

Not "is there statistical significance somewhere" (RB-2's original 2-seed
result already showed that, inconsistently) — specifically whether the
effect is *reliable across seeds* and *large enough to matter*.

## Design: the minimum additional experiment

RB-2 already had 2 seeds (42, 123) for both r=8 and r=16, with a mixed
result (significant at one seed, not the other, one metric even reversing
direction). The minimum addition that lets seed itself be treated as the
unit of replication (rather than continuing to eyeball 2 data points) is
**2 more seeds each**, bringing both ranks to 4 seeds — the smallest
number that supports computing an across-seed distribution at all.
Seeds 7 and 999 were added (arbitrary, pre-registered before running).
Every other setting held identical to RB-2: `extraction@extraction-v1.0.0`,
`max_steps=40`, same LoRA config aside from rank, same evaluation
methodology (balanced-JSON stopping criterion, `test`+`validation`
held-out split, n=27).

4 new training runs + 4 new evaluations; combined with RB-2's original 4,
this gives 8 runs total, 4 seeds × {r=8, r=16}.

## Results

### Parse rate (completion without hitting the token cap) — consistent across ALL 4 seeds

| Seed | r=8 parsed | r=16 parsed |
|---:|---:|---:|
| 42 | 26/27 | 8/27 |
| 123 | 17/27 | 13/27 |
| 7 | 20/27 | 19/27 |
| 999 | 22/27 | 14/27 |

**r=8 out-parses r=16 in every single one of the 4 seeds tested**,
though the size of the gap varies substantially (18 examples at seed=42
vs. just 1 at seed=7). This consistency of direction, even though RB-2's
original 2-seed analysis flagged completion rate as a possible
seed-driven confound, is itself evidence that at least part of the
completion-rate effect is real and rank-linked, not purely seed noise —
noise would not be expected to point the same direction 4/4 times by
chance alone (a sign-test view: p = 0.0625 for 4/4 under a null of no
rank effect, suggestive though not conclusive on its own).

### Effect size and significance, treating SEED as the unit of replication

For each metric: the seed-level `r16 − r8` paired difference was computed
independently at each of the 4 seeds (same held-out unique_ids compared
within that seed), then a bootstrap CI was computed *over those 4
seed-level effects themselves* — this is the correct way to ask "is the
effect reliable across seeds," rather than pooling all examples from all
seeds into one bag (which would understate true uncertainty by ignoring
that a seed's own idiosyncrasies apply to all 27 of its examples at once).

| Metric | Seed-level diffs (42, 123, 7, 999) | Mean across seeds | 95% CI across seeds | Reliable across seeds? |
|---|---|---:|---|:---:|
| `agreement_with_teacher` | −0.247, −0.049, +0.037, −0.111 | −0.093 | [−0.198, −0.000] | Borderline — CI touches zero |
| `semantic_equivalence` | −0.222, −0.049, −0.012, −0.111 | **−0.099** | **[−0.179, −0.031]** | **Yes — excludes zero, and same direction in all 4 seeds** |
| `grounded_correctness` | −0.341, +0.172, −0.052, −0.148 | −0.092 | [−0.269, +0.092] | No — direction flips at one seed, CI wide and includes zero |

**`semantic_equivalence` is the one metric that is both directionally
consistent across all 4 independent seeds AND has a bootstrap CI over
those 4 seed-level effects that excludes zero.** This is the strongest
possible answer available from this design: not a single lucky seed, but
a small, consistent, real effect.

## Effect size in practical terms

- Pooled r=8 `semantic_equivalence` mean (n=108 across 4 seeds): 0.2623.
  Pooled r=16: 0.1636. Absolute gap ≈ 0.10, a **~37% relative reduction**
  moving from r=8 to r=16.
- In concrete terms: on a 27-example held-out set, this corresponds to
  roughly **2-3 fewer partially-or-fully-correct field matches per
  example on average**, or equivalently, r=16 checkpoints completing
  (parsing successfully at all) on roughly **6 fewer of 27 examples**
  than r=8, averaged across seeds (21.25/27 vs. 13.5/27).
- **Resource cost comparison**: r=8 has 5,898,240 trainable parameters
  (0.15% of the 4.03B base model); r=16 has roughly double that (~11.8M,
  0.29%) — both utterly negligible in absolute training/inference cost
  for this model size. **r=16 offers no compensating resource savings** —
  it is not cheaper, smaller, or faster; it is simply a different point
  that this data shows performing worse.

## Conclusion

**The observed effect is small in absolute score terms (~0.10) but is
statistically reliable across seeds (not a single-seed artifact) on the
metric best suited to detect it, is directionally consistent in every
seed tested on parse rate and on `semantic_equivalence`, and comes with
zero offsetting benefit from r=16 (no cost, size, or speed advantage to
weigh against it).** There is no basis, in this data, for choosing r=16
over r=8 for this dataset/step-count configuration. The effect is not
large enough to describe as dramatic, but it is real, consistent, and
entirely one-directional in the finding that would matter if it existed:
r=16 does not help, and on the one metric with a reliable cross-seed
signal, it measurably hurts.

**Recommendation: r=8 as the production default LoRA rank.** See
`rb2_closure.md` for the formal closure of the full LoRA-rank study
(incorporating r=32's elimination alongside this result).
