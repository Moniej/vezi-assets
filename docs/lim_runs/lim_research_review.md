# LIM Research Review — 2026-07-29

**Purpose**: a single reference document summarizing every completed
phase of the Local Intelligence Model (LIM) research program to date —
what was built, what was tried, what is confirmed, what was rejected,
what remains open, the current recommended production configuration, and
the prioritized queue of next experiments. This document freezes the
baseline as of commit `c789ffc` / tag `lim6-research-review-baseline
-2026-07-29`.

Every claim below is sourced from an immutable registry record (training
run, eval run, or dataset version) or a specific companion document under
`docs/lim_runs/`; nothing here is asserted from memory or intuition.

---

## 1. Completed phases

| Phase | Objective | Status | Tag |
|---|---|---|---|
| **LIM-0** | Environment & feasibility validation — real hardware, real GPU, no simulation | Complete. Two genuine incompatibilities found and fixed (a dependency version pin, a small architectural substitution). | — |
| **LIM-1** | Dataset generation pipeline against the live, read-only AI Intelligence Layer DB | Complete. 13/17 dataset types produced a registered, immutable, versioned dataset; 4 correctly refused by the audit gate for genuine data-quality defects (not built around). | — |
| **LIM-2** | Reproducible, auditable fine-tuning pipeline on immutable datasets — explicitly *not* a quality pass | Complete. Refuses to start training on any non-gate-passing dataset version; every run fully recorded before a GPU cycle executes. | `lim2-training-baseline-2026-07-28` |
| **LIM-3** | Objective evaluation framework + first real benchmark | Complete, plus a root-cause diagnosis of an `entity_recognition` output-collapse defect found during the first benchmark run. | `lim3-eval-baseline-2026-07-28` |
| **LIM-4** | First model-improvement phase: fix the LIM-3 root cause + every disclosed contributing factor, measure objectively | Complete. Fixed 3 confirmed bugs (padding-label leakage into the loss, `entity_recognition` context collisions, train/test contamination) via response-only loss masking and a manual training loop (a real transformers 5.5.0 + Unsloth bug produced inf/NaN loss under `Trainer.train()` with masked labels — isolated via 9 independently-controlled experiments). Validation pass added resume capability and confirmed no held-out example can reach a gradient update through any code path. | `lim4-training-baseline-2026-07-28` |
| **LIM-5** | Measurably improve model quality against frozen LIM-3/4 baselines via evidence, not intuition — 5 priorities (data quality audit, format/memorization analysis, evidence-based curriculum, next-gen metrics, controlled experiments) | Complete. All 5 priorities addressed; Experiment 1 (dataset swap `entity_recognition`→`extraction`) produced a real, monotonic improvement (`semantic_equivalence` 0.0850→0.1704); Experiment 2 (step count) blocked by infrastructure, honestly reported as untested rather than negative. | `lim5-optimization-baseline-2026-07-28` |
| **LIM-6 / RB series** | Consolidated comparative report + bottleneck ranking + research backlog, then execute the backlog's experiments one variable at a time | RB-1 through RB-3a executed — see §2. | `lim6-lora-rank-baseline-2026-07-29`, and now `lim6-research-review-baseline-2026-07-29` |

---

## 2. Every RB experiment

### RB-1 — Training duration (`max_steps` 12 → 40)

- **Hypothesis**: more steps (loss never plateaued at 12) improves `semantic_equivalence` on `extraction`.
- **Result: inconclusive/mixed against the pre-registered metric.** `semantic_equivalence` was flat-to-lower (0.1704 → 0.1666); `grounded_correctness` regressed (0.4387 → 0.3006); `agreement_with_teacher` broke out of 0.0 for the first time; `hallucination_risk` dropped to 0; the loss curve visibly plateaued at 40 steps for the first time in any run.
- **Confirmed conclusions (owner-approved)**: infrastructure hypothesis confirmed (the blocking segfault/`OSError 1455` was pure OS memory pressure, resolved by a clean restart, zero code change); 40 steps is sufficient for convergence; more steps alone did not show convincing evidence of improved semantic performance; the held-out set (n=12 at the time) was too small for strong conclusions — this directly motivated the later `--include-validation` expansion.
- Docs: `rb1_infrastructure_failure_log.md`, `rb1_results.md`.

### RB-2 / RB-2b — LoRA rank sweep (r ∈ {8, 16, 32}) — formally closed

- **Hypothesis**: r=8 under-capacitates the model; higher rank improves semantic correctness.
- **Result: hypothesis rejected — the opposite of "higher rank helps".**
  - **r=32: eliminated.** Statistically significantly worse than both r=8 and r=16 on `agreement_with_teacher`/`semantic_equivalence`/`grounded_correctness`, replicated across 2 seeds (every paired bootstrap CI excludes zero). Seed=123 showed **0/27 parsed** — total generation-termination collapse, not just lower quality.
  - **r=8 vs. r=16: resolved via a dedicated 4-seed follow-up (RB-2b).** `semantic_equivalence` directionally favored r=8 in **all 4 seeds** tested, across-seed 95% CI **[−0.179, −0.031]** (excludes zero) — a real, modest (~37% relative) effect. Parse/completion rate also favored r=8 in all 4 seeds. r=16 offered no compensating resource advantage.
- **Real confound found and fixed mid-study**: a fixed generation token-budget cap was hit by 100% of generations across every rank without completing valid JSON — fixed with a balanced-JSON stopping criterion, roughly doubling parse rate and `semantic_equivalence` on the same checkpoint.
- **Production decision**: **r=8 adopted as the frozen default.** r=16 retired, r=32 eliminated. Not to be revisited absent evidence materially contradicting this.
- **Separated, informational-only side question**: the r=32 termination-collapse mechanism (`rb2_r32_collapse_research_question.md`) — 4 candidate hypotheses documented, does not block closure.
- Docs: `rb2_results.md`, `rb2b_results.md`, `rb2_closure.md`, `rb2_infrastructure_note.md`, `rb2_r32_collapse_research_question.md`.

### RB-3 — Train on `self_critique` instead of `extraction` — negative result

- **Hypothesis**: `self_critique` is a viable training target; training on it improves `self_critique_quality`/`reasoning_quality` off their universal 0.0, mirroring Experiment 1's result on a different skill.
- **Result: negative.** `self_critique_quality` remained **exactly 0.0/24**. `reasoning_quality` moved off zero (0.0441, bootstrap CI [0.027, 0.063] excludes zero) but only via a metric-side lexical-overlap fallback scavenging credit from wrong-schema outputs — not genuine task performance. **0/24 outputs used the expected output schema** (`finding`/`explanation`/`resulting_status`); 8/24 (33%) echoed the prompt's own input fields back instead of attempting a critique.
- Read strictly, the pre-registered "or" criterion technically passed; read honestly, this does not confirm the hypothesis as written and is recorded as a **negative, reproducible result**, not a success.
- Docs: `rb3_results.md`.

### RB-3a — Schema-learning diagnostic (audit-only, no training) — in progress

- **Purpose**: isolate *why* RB-3's checkpoint never learns the output schema, before spending further compute on optimization.
- **Ruled out by direct audit**: dataset-formatting inconsistency (104/104 training examples use the correct schema), sequence-length truncation (max 210 tokens, well under the 256 limit — 0/104 truncated), loss-masking bug (decoded the supervised label span for 5 sampled examples directly — all begin exactly at `{"finding": ...` with no clipping).
- **Likely not the cause**: teacher-output/value consistency (finding/resulting_status value distributions are reasonably balanced, not degenerate).
- **Strong candidate identified**: `self_critique`'s required output key names never appear anywhere in its input/instructions (0/104), whereas `extraction`'s output key `fact_type` appears verbatim in every input context (132/132) — a much easier copy-style schema-binding problem. Entangled with `self_critique` being an inherently generative/authorship task vs. `extraction`'s closer-to-extractive one.
- **Proposed next step (not yet run, pending sign-off)**: a single schema-hint prompt-template training diagnostic, single variable, to directly test whether making the schema visible in the input fixes the 0/24 match rate.
- Docs: `rb3a_schema_diagnostic.md`.

---

## 3. Confirmed findings (evidence-backed, reproducible)

1. **Response-only loss masking + a manual training loop are required** on this transformers 5.5.0/Unsloth 2026.7.5 stack — `Trainer.train()` produces inf/NaN loss the instant `labels` contains any `-100`, isolated via 9 independently-controlled experiments (LIM-4).
2. **Dataset choice is a real, measurable lever.** Swapping the training target from `entity_recognition` to `extraction` alone produced a monotonic `semantic_equivalence` improvement (0.0850 → 0.1704, LIM-5 Experiment 1).
3. **40 training steps is sufficient for convergence** on `extraction`-sized (~130 example) data — the loss curve visibly plateaus by then (RB-1); more steps alone did not show convincing further semantic improvement.
4. **r=8 is the best-evidenced LoRA rank** of the three tested, on every metric, at every seed tested, for `extraction` at 40 steps — never significantly beaten by r=16 or r=32 (RB-2/RB-2b). Lower capacity has not once shown a quality cost in this data.
5. **`exact-match` (`agreement_with_teacher`) is a known blind spot**, not a true regression signal — it cannot detect schema-plausible-but-differently-shaped outputs. `semantic_equivalence` was purpose-built to resolve this and shows the true, improving direction across LIM-3→4→5.
6. **A fixed generation token-budget cap was silently capping 100% of generations** across every LoRA rank in RB-2's original setup — fixed with a balanced-JSON stopping criterion, verified to roughly double parse rate and `semantic_equivalence` on the same checkpoint.
7. **`extraction`'s output schema is learnable because its key names are already present in the input** (`fact_type` appears in 132/132 training contexts); this copy-style schema-binding is categorically easier than `self_critique`'s, where the required keys never appear in the input at all (RB-3a).
8. **Loss masking is verified correct specifically for `self_critique`**, not just in general — decoded supervised spans begin exactly at the response JSON's first key with no clipping (RB-3a Phase 1).
9. **OS memory pressure (Windows "Memory Compression"), not code defects, is the recurring cause of training/eval process crashes** (segfaults, `OSError 1455`) across a long session of sequential model-loading subprocesses — resolved every time by a clean machine restart, confirmed via byte-identical environment hashes before/after (RB-1, RB-2, RB-2b, RB-3).

## 4. Rejected hypotheses

1. **"Higher LoRA rank improves semantic correctness" — rejected.** The data shows the opposite: r=32 is decisively worse (including a 0/27 total generation collapse at one seed), and r=16 shows no advantage over r=8 on any metric at any seed (RB-2/RB-2b).
2. **"Self_critique is a viable training target that mirrors extraction's success" — rejected as tested.** `self_critique_quality` showed zero movement; the apparent `reasoning_quality` improvement is a metric-side artifact, not genuine task learning (RB-3).
3. **"The prompt/response format (`### Instruction/Context/Response`) is implicated in current defects" — rejected** (LIM-5 Priority 2): directly tested via a memorization-vs-learning analysis; the template itself is not the cause of any observed defect (the only recommended fix, a generation-time stop sequence, is a separate small item, RB-7 — not a rejection of the template itself).
4. **"More training steps alone continues to improve quality past 40" — not supported.** RB-1 found no convincing semantic improvement from 12→40 steps beyond the point of loss-curve plateau, alongside one regressed metric (`grounded_correctness`).

## 5. Unresolved / open questions

1. **Why does `self_critique` never learn its output schema — schema-visibility, task-complexity, or both?** RB-3a has ruled out 4 candidate causes but has not yet run the schema-hint diagnostic that would separate the two live hypotheses (§2, RB-3a).
2. **The r=32 generation-collapse mechanism** — 4 candidate hypotheses documented (`rb2_r32_collapse_research_question.md`), informational only, not yet investigated further.
3. **Whether r=8 remains optimal under a different dataset, step count, or learning rate** — the RB-2 closure is explicitly scoped to `extraction`/40 steps/lr=2e-4; untested outside that regime.
4. **Learning rate** (2e-4 used throughout) — completely unvaried; genuinely open, no observed symptom implicates it either way (RB-4, not yet started).
5. **Batch size / gradient accumulation** (effective batch 4) — completely unvaried (RB-5, not yet started).
6. **Latency**: LIM-4 showed a large latency spike (27.58s mean vs. LIM-3's 11.56s) that partially but not fully recovered by LIM-5 (15.13s) — never isolated as a controlled measurement (no thermal/clock monitoring); still an open question, not resolved.
7. **Three of six priority evaluation dimensions remain structurally unmeasurable** (`grounding_accuracy`, `citation_correctness`, `hallucination_flag_correct` all show n=0 in every real eval run) — not a broken metric, but zero registered held-out examples carry the needed labels. Closing this (RB-8, persisting `context` retroactively; RB-11, re-auditing the source datasets) is blocked pending new-dataset scope being reopened.
8. **`entity_recognition`'s residual context collisions** (13/39 examples) and **`evidence_ranking`'s uninformative `{"fact_id": N}` context** — real, evidenced defects, explicitly blocked this phase pending new data (RB-9, RB-10).

## 6. Current recommended production configuration

Frozen in `configs/lim_training_defaults.toml`, loaded via
`training.load_training_defaults()` and used as every CLI default in
`scripts/lim/train.py` unless explicitly overridden for a single-variable
experiment:

```toml
[lora]
r = 8
lora_alpha = 16              # 2 * r, fixed convention
lora_dropout = 0.0
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
gradient_checkpointing = "unsloth"

[quantization]
load_in_4bit = true
quant_type = "nf4"

[training]
max_steps = 40
save_steps = 10
learning_rate = 2e-4
batch_size = 1
gradient_accumulation_steps = 4
max_seq_length = 256

[model]
base_model = "lim_training/qwen3_4b_model"
```

Every value above is backed by a specific completed experiment (r=8 by
RB-2/RB-2b, max_steps=40 by RB-1, the rest carried forward unvaried and
explicitly flagged as open in §5, not silently assumed safe). This
configuration is the **required baseline** for every future experiment
unless that experiment's own single independent variable is one of these
fields.

## 7. Prioritized next experiments

| Priority | Item | Type | Why |
|---|---|---|---|
| **1 (highest, gating)** | RB-3a Phase 2 — schema-hint diagnostic | Single training run, pending sign-off | Must resolve before any further `self_critique` work; directly explains RB-3's failure mode or rules it out |
| **2** | RB-7 — generation-time stop sequence | Eval-side only, no retraining | Cheap, safe, already evidence-backed (LIM-5 Priority 2), reduces parse failures independent of any training change |
| **3** | RB-4 — learning rate sweep | Training experiment on `extraction` | No observed symptom implicates 2e-4, but it is completely unvaried — genuinely open |
| **4** | RB-5 — batch size / gradient accumulation | Training experiment on `extraction` | Same rationale as RB-4; unvaried, open |
| **5** | RB-8 — persist `context` retroactively in the eval registry | Infrastructure/schema change | Unlocks 3 of 6 priority evaluation dimensions for LIM-3/4-era runs, not blocking any model-quality experiment directly |
| **6 (conditional)** | RB-6 — sequence length / packing | Audit, only if a future dataset's p95 length approaches 256 | Not currently triggered by `extraction`; monitor per new training target |
| **Blocked this phase** | RB-9 (`entity_recognition` context collisions), RB-10 (`evidence_ranking` context content), RB-11 (`citation_grounding`/`financial_reasoning` re-audit) | Requires new datasets | Explicitly out of scope until the owner lifts the "no new datasets" constraint |

---

## 8. Provenance

- Frozen at commit `c789ffc` (RB-3 negative result + RB-3a diagnostic), tagged `lim6-research-review-baseline-2026-07-29`.
- Prior baseline tags, still valid and unchanged: `lim2-training-baseline-2026-07-28`, `lim3-eval-baseline-2026-07-28`, `lim4-training-baseline-2026-07-28`, `lim5-optimization-baseline-2026-07-28`, `lim6-lora-rank-baseline-2026-07-29`.
- Every metric cited above traces to an immutable `eval_run`/`training_run` registry record or a named companion document under `docs/lim_runs/`; none are restated from memory.
