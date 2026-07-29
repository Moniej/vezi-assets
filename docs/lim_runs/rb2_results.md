# RB-2 Results — LoRA Rank Sweep (Analysis on 5 of 6 Planned Configurations)

**r=32/seed=123 is an explicitly disclosed missing observation.** Per
instruction, it is not estimated, averaged over, or inferred — every
r=32 statistic below is a single-seed (seed=42) point, reported as such,
never blended with a second seed the way r=8 and r=16 are.

## 1. Completed experiments

| Config | Eval run | n | Status |
|---|---|---:|---|
| r=8, seed=42 | `871a2375-...` | 27 | Complete |
| r=8, seed=123 | `3cd8c1ee-...` | 27 | Complete |
| r=16, seed=42 | `71504999-...` | 27 | Complete |
| r=16, seed=123 | `ce06ef4e-...` | 27 | Complete |
| r=32, seed=42 | `8fbfbc1a-...` | 27 | Complete |

All five hold `max_steps=40` (the RB-1-established convergence point),
dataset (`extraction@extraction-v1.0.0`), and every other hyperparameter
constant — LoRA rank is the sole varied factor within each seed. All
five used the corrected evaluation methodology (below).

## 2. Missing experiment

**r=32, seed=123 — not run.** Blocked twice by the recurring
infrastructure memory-pressure pattern (`rb2_infrastructure_note.md`); a
third attempt was in flight when this analysis was requested and is
being tracked separately for later append, per instruction, without
altering any conclusion below.

## 3. Infrastructure limitations (disclosed, not silently absorbed into the results)

- **The memory-pressure pattern from RB-1 recurred twice more during
  RB-2**, and a new characteristic was observed: free RAM degraded from
  ~4.9 GB immediately after a restart down to ~1.06 GB after only 5
  sequential evaluation runs in the same session, even though each
  process exited cleanly. This is a real, reproducible property of this
  environment (Windows "Memory Compression" pressure accumulating across
  sequential large-model loads within one session), not a one-off.
- **A real measurement confound was found and fixed before any rank
  conclusion was drawn.** At a fixed `max_new_tokens` (160, then 300),
  100% of generations across every rank hit the token cap without
  completing — some from genuine verbose elaboration, some from
  degenerate repetition of a meta-commentary string. This made the raw
  rank comparison invalid, not just noisy. Fixed with a balanced-JSON
  stopping criterion (`run_evaluation.py::_make_balanced_json_stopping_
  criteria`) that halts generation once a syntactically-complete
  top-level JSON object is produced, applied identically to every
  checkpoint, plus a 512-token safety cap. This alone roughly doubled
  both the parse rate and `semantic_equivalence` on the same checkpoint
  when compared before/after the fix — proof the earlier numbers were
  measuring the confound, not rank.
- **Completion behavior is itself substantially seed-dependent, not
  purely rank-dependent** — a second, independent confound this analysis
  surfaces rather than absorbs silently:

  | Config | Parsed | Hit 512-token cap |
  |---|---:|---:|
  | r=8, seed=42 | 26/27 (96%) | 1/27 |
  | r=8, seed=123 | 17/27 (63%) | 9/27 |
  | r=16, seed=42 | 8/27 (30%) | 19/27 |
  | r=16, seed=123 | 13/27 (48%) | 13/27 |
  | r=32, seed=42 | 7/27 (26%) | 19/27 |

  Parse rate swings by 33 percentage points between r=8's two seeds
  alone — comparable in size to the swing between ranks. This means seed
  -to-seed generation-length variance is a real, still-not-fully-isolated
  factor, and every rank comparison below must be read with that in mind.

## 4. Statistical comparisons (paired, same held-out unique_ids, bootstrap CI)

| Metric | seed=42: r16−r8 | seed=123: r16−r8 | seed=42: r32−r8 |
|---|---|---|---|
| `agreement_with_teacher` | −0.247, CI excludes 0 (**real**) | −0.049, CI includes 0 (not significant) | −0.210, CI excludes 0 (**real**) |
| `semantic_equivalence` | −0.222, CI excludes 0 (**real**) | −0.049, CI includes 0 (not significant) | −0.235, CI excludes 0 (**real**) |
| `grounded_correctness` | −0.341, CI excludes 0 (**real**) | **+0.172**, CI includes 0 (not significant, opposite direction) | −0.214, CI excludes 0 (**real**) |
| `hallucination_risk` | +0.063, CI includes 0 | −0.063, CI includes 0 | −0.095, CI includes 0 |

(r32−r16, seed=42 only, for reference: not statistically distinguishable
on either `agreement_with_teacher` [+0.037, CI includes 0] or
`semantic_equivalence` [−0.012, CI includes 0].)

## 5. Fully supported conclusions

- **At seed=42, r=8 statistically significantly outperforms both r=16
  and r=32** on `agreement_with_teacher`, `semantic_equivalence`, and
  `grounded_correctness` (all three CIs exclude zero, all favoring r=8).
- **`hallucination_risk` shows no statistically distinguishable
  difference between any ranks tested**, at either seed (every CI
  includes zero) — genuinely inconclusive on this dimension, not a null
  finding dressed up as one.
- **Higher LoRA rank does not produce a same-seed improvement anywhere
  in this data.** No comparison, at any seed, on any metric, shows r=16
  or r=32 statistically beating r=8.

## 6. Provisional conclusions (do not treat as settled)

- **The seed=42 r=8-beats-r16 effect is NOT cleanly replicated at
  seed=123**: same direction on `agreement_with_teacher`/`semantic_
  equivalence` but not statistically significant, and `grounded_
  correctness` actually reverses direction (not significantly). This
  means "r=8 is better than r=16" is currently a seed-42-driven finding,
  not yet a rank-driven finding proven independent of seed.
  Distinguishing "rank hurts" from "this specific seed's r=16/r=32 runs
  happened to generate less parseable output" requires more seeds per
  rank than this experiment ran.
- **r=32 rests on one seed only.** Its apparent similarity to r=16 and
  gap below r=8 is a single observation, not a replicated finding, per
  the explicit instruction not to treat it as complete.
- **Whether the effect is really about representational capacity, or
  substantially about the seed-dependent completion-rate confound (§3),
  is not yet separable with the current data.** A rank that "hurts" by
  producing longer, less-often-complete JSON is a different finding from
  a rank that "hurts" the model's actual factual/semantic correctness
  conditional on completing — this analysis cannot yet distinguish them.

## 7. Rank every tested LoRA rank by evidence strength

1. **r=8 — strongest evidence, and best-performing.** 2 seeds, most
   consistent completion behavior (96%/63% parsed), wins every
   statistically-significant comparison run.
2. **r=16 — second-strongest evidence, worst average performance of the
   two multi-seed ranks.** 2 seeds, but internally inconsistent between
   seeds on `grounded_correctness`'s direction — the evidence quality
   itself is weaker than r=8's despite equal seed count, because its
   within-rank seed agreement is worse.
3. **r=32 — weakest evidence.** 1 seed only; every statistic is a single
   observation. Descriptively similar to r=16 on the one seed available,
   but this cannot be stated as a finding.

## 8. Are the observed differences large enough to justify further investigation?

**Yes.** A 0.21-0.25 absolute swing in `semantic_equivalence`/`agreement_
with_teacher` between r=8 and higher ranks, reproduced with statistical
significance at one full seed across three different metrics
simultaneously, is too large and too consistent (within that seed) to be
dismissed as noise — but it is exactly the kind of finding RB-1's own
lesson (a single-seed/single-run result can look decisive and still not
replicate) says must not be accepted without the second seed's
confirmation, which here is genuinely mixed rather than confirmatory.

## 9. Recommendation: continue RB-2's missing replication, do not move on yet

Complete r=32/seed=123 (already in progress, to be appended without
altering this report) before drawing any final capacity conclusion.
Beyond that, the higher-priority follow-up is **not** a new rank value —
it is isolating the seed-dependent completion-rate confound (§3) from
the capacity question, since right now they are entangled. A targeted
follow-up (same rank, several seeds, tracking parse rate as its own
tracked variable rather than an incidental side-effect) would do more to
settle "does rank matter" than testing a fourth rank value would.
Recommend RB-2 stays the active research priority until r=8-vs-r16 is
either confirmed or overturned by a proper multi-seed comparison; do not
begin a new hyperparameter dimension (RB-4/RB-5) in parallel with this
one still unresolved.

---

## 10. Update — r=32/seed=123 completed (appended, sections 1-9 unmodified)

The missing configuration finished after §1-9 were written and reviewed.
Per instruction, sections 1-9 above are left exactly as originally
reported (including their "provisional"/"missing" framing, which was
accurate at the time) — this section adds the new data and states
plainly which prior conclusions it strengthens, confirms, or leaves
unchanged. Nothing above was edited.

**Result: r=32/seed=123 produced 0/27 parsed generations** — every
single one hit the 512-token safety cap without ever completing a
balanced JSON object (worse than r=32/seed=42's already-weak 7/27).
`agreement_with_teacher`, `semantic_equivalence`, and `grounded_
correctness` are all exactly 0.0 (n=27, zero-width CI, since parsing
failure scores 0.0 deterministically for every example).

### Updated statistical comparisons (now 2 seeds for every rank)

| Metric | seed=123: r32−r8 | seed=123: r32−r16 |
|---|---|---|
| `agreement_with_teacher` | −0.210, CI excludes 0 (**real**) | −0.161, CI excludes 0 (**real**) |
| `semantic_equivalence` | −0.210, CI excludes 0 (**real**) | −0.161, CI excludes 0 (**real**) |
| `grounded_correctness` | −0.270, CI excludes 0 (**real**) | −0.441, CI excludes 0 (**real**) |
| `hallucination_risk` | not computable (0 ticker-shaped values produced) | not computable |

Pooled r=32 (both seeds, n=54): `agreement_with_teacher` mean 0.0432,
`semantic_equivalence` mean 0.0432, `grounded_correctness` mean 0.1235 —
all pulled down substantially by seed=123's total collapse.

### What this changes

- **§6's "r=32 rests on one seed only" is resolved**: r=32 now has 2
  seeds, and **both independently show r=32 statistically significantly
  worse than r=8 AND worse than r=16** (all four CIs exclude zero). This
  is no longer a single-observation, provisional finding — it is a
  replicated one. Move "r=32 is worse than both other ranks" from §6
  (provisional) to confirmed.
- **§6's seed-dependence concern about r=8-vs-r16 is UNCHANGED** — this
  new data doesn't bear on that specific comparison (it was already
  computed at both seeds in §4) and remains exactly as mixed/inconclusive
  as originally reported. Do not read r=32's clean replication as
  resolving r=16's.
- **§3's seed-dependent completion-rate confound is sharpened, not
  resolved**: r=32/seed=123's 0/27 is the most extreme completion
  failure observed anywhere in this experiment, deepening rather than
  explaining away the open question of how much of "rank hurts" is a
  representational-capacity effect versus a completion/verbosity effect
  that happens to correlate with rank. If anything, a rank showing TWO
  -for-two total-or-near-total non-termination is now the strongest
  single piece of evidence in this whole experiment that something about
  higher rank + this tiny dataset + this step count systematically
  degrades the model's ability to terminate generation at all — a
  finding worth its own targeted follow-up, separate from (and now more
  interesting than) the original capacity question.
- **§7's ranking is updated**: r=32 moves from "weakest evidence" to
  "strong evidence of being the worst-performing rank tested" — still
  ranked last, but no longer for lack of data.
- **§9's recommendation is reinforced, not changed**: the outstanding
  work is still isolating the completion-rate confound from a genuine
  capacity effect, now with a sharper, better-evidenced target (why does
  r=32 fail to terminate almost entirely across both seeds?) rather than
  a vaguer one.

