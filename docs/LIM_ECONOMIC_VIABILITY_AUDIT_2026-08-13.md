# LIM Economic Viability Audit — 2026-08-13

Objective: not to finish LIM, not to make it the production extractor —
to determine, with evidence, whether continuing to invest engineering
time in the Local Intelligence Model has positive expected value as an
extraction engine. Production untouched throughout (`extracted_facts=495`,
`financial_reasoning_conclusions=267`, verified before and after). Alpha
Engine files (`alpha_engine.py`/`engine_full.py`/`runner.py`/`registry.py`)
have zero diffs. No Gemini quota was spent — this audit deliberately used
only LIM's own existing eval records and newly-built source-grounded gold
data, never a fresh Gemini call.

**Verdict up front: ABANDON as a near-term extraction-engine investment.**
Not because LIM "doesn't exist" or was never tried — 38 real training runs
and 24 real evaluations exist — but because the evidence, gathered fresh
today, points the same direction from every angle: quality, task-domain
coverage, and basic operational reliability all fail, independently of
each other.

---

## 1. Current LIM state

Real, substantial, pre-existing research infrastructure (`lim_training/`,
`src/ngxrot/lim/`, `scripts/lim/`) — not vaporware:

- Base model: Qwen3-4B, downloaded and present (`lim_training/qwen3_4b_model/`).
- 38 real LoRA fine-tuning runs on record (`training_registry.sqlite`), spanning
  2026-07-28 through 2026-07-30 — hyperparameter/rank/dataset-choice probes
  (LIM-2 through LIM-6, then an RB-3/3a/3b follow-on series), all `r=8-32`,
  `max_steps=2-40` (never a full epoch — see §12).
- 24 real evaluation runs, 1093 scored examples (`eval_registry.sqlite`).
- An already-authored, evidence-based research backlog
  (`docs/lim_runs/lim6_bottleneck_ranking.md`) ranking exactly what to try
  next and why — this audit did not need to re-derive that; it's cited
  directly in §12.
- **Not wired into the production pipeline**: `PROVIDER_REGISTRY` (this
  session's own check, and unchanged before today) contained only
  `"gemini"`. No `LocalLIMProvider` class existed until Phase 1 of this
  audit built one (see §9).

---

## 2. Evaluation methodology

Two independent evidence sources, combined because live inference turned
out to be blocked (§7):

1. **LIM's own existing eval-registry records** (24 runs, 1093 examples,
   built and scored by the project's own prior sessions, not by this
   audit) — used as-is, not re-scored, not cherry-picked. This audit
   explicitly does **not** treat `agreement_with_teacher` (exact-match
   vs. Gemini) as ground truth by itself — the registry's own
   `grounded_correctness`, `semantic_equivalence`, and raw
   `model_output_parsed` fields (checked directly against
   `expected_output`, itself derived from real source documents at
   dataset-export time) are used instead, per the assignment's explicit
   instruction not to grade LIM only by teacher agreement.
2. **A newly-built, source-grounded gold-standard set** (`scripts/lim/
   gold_standard.py`, Phase 2) — 11 real NGX filings, every expected value
   read directly from `data/staging/document_text/<doc_id>.txt` during
   this audit, not copied from any prior extraction. Includes the exact
   real TRANSCORP 10× case (doc 9485) by explicit instruction. **LIM was
   not actually run against this gold set** — a real, reproducible
   environment failure blocked it (§7) — this is disclosed as a gap, not
   papered over with a fabricated score.

---

## 3. Gold-set composition

| Doc ID | Ticker | Label | Expected facts |
|---:|---|---|---:|
| 8051, 8730 | SEPLAT | true_negative | 0 |
| 3852, 8240 | STANBIC | true_negative | 0 |
| 8103 | ELLAHLAKES | true_negative | 0 |
| 8158, 9530 | MORISON | true_negative | 0 |
| 452 | STANBIC | qualitative_only | 1 (non-numeric; a metric-mistag trap) |
| 8750 | TRANSCORP | quantitative | 6 |
| 9485 | TRANSCORP | **quantitative_adversarial** | 7, incl. the real 10× case |
| 11122 | ELLAHLAKES | **quantitative_adversarial** | 5, incl. a genuine irregular-period + two-different-loss-figures case |

11 documents, 20 total expected facts, 7 true negatives, 2 explicit
adversarial cases. Full detail in `scripts/lim/gold_standard.py`.

---

## 4. Accuracy results

**LIM was not scored against the gold set above — inference is currently
non-functional in this environment (§7).** Reporting a score anyway would
be exactly the "fabricated benchmark result" this assignment prohibits.

What IS real and reportable, from the existing eval registry (best
checkpoint on record, RB-3b, `8d265e59-...`/`checkpoint-40`,
`agreement_with_teacher=0.201` — the highest of any checkpoint ever
trained):

| Metric | Value | n |
|---|---:|---:|
| `agreement_with_teacher` (exact-match to Gemini) | 20.1% | 130 |
| `semantic_equivalence` | 24.9% | 130 |
| `grounded_correctness` (`extraction` dataset_type only) | 85.2% | 27 |
| `grounded_correctness` (`evidence_ranking`/`rag`/`retrieval`) | **0.0%** | 34 |
| `grounded_correctness` (overall, all 9 dataset types) | 41.3% | 128 |
| `self_critique_quality` | 0.0% | 24 |

**Critical caveat, not an afterthought**: every one of these numbers comes
from LIM's own training/eval task — single-fact **dividend/corporate-action**
extraction from short snippets (mean 81 input tokens, max 124). **Zero**
of LIM's 1093 eval examples exercise the actual target task this audit
exists to evaluate: multi-fact financial-statement extraction (revenue,
net_profit, assets, equity, cash flow, across multiple periods) from real
filings up to 130,892 characters. `docs/lim_runs/lim6_bottleneck_ranking.md`
(written before this audit, independently) confirms this precisely:
*"`citation_grounding`/`financial_reasoning` have 0 registered examples...
would need new export/data work to even become usable."* **LIM's best
measured number (20-85%, depending on metric) describes a task that is not
the bottleneck this audit was commissioned to address.**

---

## 5. Critical-error analysis

Real examples, pulled directly from the eval registry (`eval_examples`
table, RB-3b run), not constructed for this report:

| Case | Expected | LIM output | Error |
|---|---|---|---|
| `extraction:26` | `dividend = 992.0` | `dividend = 0.125` | **~7,936× too small** — not a round factor (10×/100×/1000×), meaning the platform's own `numeric_consistency_check` (Phase-1-of-a-prior-audit, checks round-factor deviations) **would not catch this class of error** |
| `extraction:25` | `dividend = 4.0` | `dividend = 0.25` | 16× off, also non-round |
| `extraction:17` | `numeric_value = null` (expected value is genuinely absent from this fact) | `numeric_value = 0.025` | **Fabricated a specific number where none exists in the ground truth** — the opposite of the platform's "abstain, never guess" invariant |

**On abstention (Phase 3's central question — fails safe, or confidently
wrong?)**: the evidence says **confidently wrong, not fail-safe**. In
every one of the 24 `extraction`-type examples inspected, LIM produced a
plausible-shaped, specific numeric value — never a null, never an
uncertainty flag, even where the correct answer was `null`. This is the
single most operationally dangerous finding in this audit: a model that
produces well-formed but wrong structured financial facts is worse than
one that fails loudly, because downstream consumers (`financial_ratios.py`,
`compute_ratios_for_ticker`) have no signal to distinguish a real fact
from a fabricated one at the point of consumption.

---

## 6. Adversarial results

The assignment's own adversarial list, checked against real, existing
evidence (not simulated for this report):

| Adversarial case | Evidence | Result |
|---|---|---|
| Evidence grounding / citation | `evidence_ranking` eval examples | **Catastrophic**: model output was completely unrelated to the input — real examples show fabricated content about the 2022 World Cup and a Britannica photovoltaic-cell article in place of financial evidence ranking. This is a documented, known issue on this checkpoint family — `scripts/lim/rb3b_mode_collapse_probe.py` exists specifically to investigate it. |
| Confidently-wrong numerics | §5 above | Confirmed — non-round-factor errors up to ~8000×, no abstention |
| Point-in-time vs. flow facts, multi-period documents, unit conversion (thousands/millions/billions), negative values (losses), restated/comparative figures, tables | Gold set §3 (docs 8750, 9485, 11122) | **Not testable today** — inference blocked (§7). These are real, present in the gold set (e.g., 11122's 4-column Group/Company comparative table in thousands of naira, with two genuinely different loss figures), but LIM's actual behavior on them is unmeasured, not assumed to be either good or bad. |
| Documents with no usable financial facts (true negatives) | LIM's own eval set has **no true-negative examples at all** — every example expects a non-null extraction | LIM has never been evaluated on "correctly extract nothing" — a real, disclosed gap independent of quality |
| Ambiguous/conflicting wording | Not testable today (same as above) | Unmeasured |

**Bottom line for Phase 3's stated goal**: on every adversarial dimension
where real evidence exists, LIM fails in the dangerous direction
(confident fabrication, not safe abstention). On the dimensions specific
to the actual target task (period handling, PIT-vs-flow, true negatives),
there is no evidence at all — not because LIM handles them well, but
because it has never been asked to.

---

## 7. Throughput / operational reliability

**This section contains a real, reproducible, current-session finding,
not a historical one.** Three independent live attempts today, on the
exact machine this platform runs on:

1. `scripts/lim/smoketest_extraction.py` via the newly-built
   `LocalLIMProvider` (real `extract_document()` call, real prompt,
   4096-token context): `torch.OutOfMemoryError`, "Tried to allocate 3.23
   GiB... 4.96 GiB is free."
2. The same failure, byte-for-byte identical error, at `max_seq_length`
   512/1024/1536 — proving the OOM is driven by loading the base model's
   weights during `caching_allocator_warmup`, not by context length.
3. At `max_seq_length=2048`: a **segmentation fault** (exit code 139).
4. **`scripts/lim/verify_checkpoint_inference.py`** — the exact,
   previously-proven, unmodified script used to validate every one of the
   38 training checkpoints during LIM's own development — **also fails
   today**, with the identical OOM, at its own original `max_seq_length=256`.

This is not a new-code bug: it reproduces on old, already-proven code.
Tried the SDK's suggested fix (`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`)
— **not supported on Windows** (confirmed by the library's own warning
message). Checked for a resource-contention confound: `nvidia-smi` shows
5,767 MiB free of 6,144 MiB total (RTX 3050 6GB Laptop GPU) with one
foreground process (a game, `FIFA23.exe`) holding an unreported amount of
VRAM — **the same specific external-process-contention pattern already
documented in this platform's own LIM-5 report** (`docs/lim_runs/
lim_comparative_report_3_4_5.md`: *"4 consecutive segfaults blocked LIM-5
Experiment 2, correlated with low system RAM"*). **This is a known,
previously-documented, still-unresolved reliability problem, not a new
one this audit introduced.**

Given three independent reproductions including a previously-trusted
script, further retries were not attempted (diminishing evidence value,
per this audit's own "reward information gained" instruction).

**Measured historical latency** (from the eval registry, on 81-124 token
inputs — NOT representative of real document scale): mean 11.6–27.6s per
example across LIM-3/4/5 checkpoints, `p95` up to 52s. **Documents/hour,
tokens/context at real document scale, cost per document, cost per
ticker, cost for 304 documents, and human-review burden are all
UNKNOWN** — not zero, not estimated, genuinely unmeasurable while the
environment cannot execute a single real-document-scale inference call.

**Hardware requirement, stated plainly**: the available machine (RTX 3050,
6GB VRAM laptop GPU) is currently **insufficient** to reliably run even a
4-bit-quantized 4B-parameter model's inference path under the installed
library versions (`transformers 5.5.0`, `torch 2.11.0+cu126`) — this is a
measured fact today, not a theoretical concern.

---

## 8. Economics

| Metric | Value |
|---|---|
| Marginal $ cost per LIM call | $0 (local weights, already-downloaded) |
| Marginal $ cost per Gemini call | $0 (free tier, confirmed in prior FRE audits) |
| Gemini's real constraint | Throughput — 20 requests/day, measured directly in two prior pilots |
| LIM's real constraint (today) | **Cannot execute at all** — 0 successful real-document-scale calls |
| Documents/hour, LIM | UNKNOWN (blocked) |
| Cost per document, ticker, or the 304-document backlog | UNKNOWN (blocked) — not invented |
| Hardware requirement | Currently unmet by the available GPU (§7) |
| Human review burden | UNKNOWN, but §5's evidence (confident fabrication, not abstention) implies it would need to be **at or near 100%** if ever deployed at current quality — which would eliminate any throughput advantage even if the hardware problem were fixed |

**Break-even calculation, honestly**: since both providers are $0 marginal
cost, the only lever LIM could ever win on is **throughput** (avoiding
Gemini's 20/day cap). A break-even point requires LIM to have a
measurable, positive documents/hour rate. It does not currently have one.
**No break-even point can be calculated — this is stated as UNKNOWN, per
instruction, not defaulted to "favorable" or "unfavorable."**

---

## 9. Gemini comparison

| Dimension | Gemini (production) | LIM (today) |
|---|---|---|
| Can currently execute real extraction | Yes (quota-limited: ~10/day) | **No** (§7) |
| Identity accuracy | 100% (10/10, real pilot) | Not measurable on real docs |
| Fact-type accuracy | 90% (9/10) | Not measurable on real docs; on its own trained (different) task: mixed, with confirmed fabrication |
| Period accuracy | 100% post-fix (6/6) | Not measurable — 0 training examples for this schema |
| Numeric accuracy | 90% pre-fix, now systematically caught by `numeric_consistency_check` for round-factor errors | Confirmed non-round-factor errors up to ~8000× on its own task — **would evade the existing safety net** |
| Evidence grounding | 100% (10/10) | 0.0% on the closest analogous task (`evidence_ranking`) |
| True-negative behavior | 100% (3/3 confirmed) | Never evaluated on true negatives at all |
| Provider isolation / fail-safe | N/A (is the trusted default) | Built this audit (Phase 1): `LocalLIMProvider` cannot be config-selected, refuses construction without a passed quality gate, no silent fallback |

---

## 10. Quality gate

Derived from the **existing pipeline's own real risk profile** (not
arbitrary numbers — each threshold below is something the pipeline
already enforces or has already measured on Gemini):

| Gate | Derived from | LIM result |
|---|---|---|
| **A. Safe extraction** | The platform's explicit "never fabricate" invariant (`extract.py`'s `validate_period()`, `numeric_consistency`'s never-auto-correct rule) | **FAIL** — fabricates unrelated content under uncertainty rather than abstaining |
| **B. Numeric correctness** | `numeric_consistency_check`'s own tolerance (≈2% pass band, flags round-factor deviations) | **FAIL** — non-round-factor errors up to ~8000×, a class the existing safety net cannot catch |
| **C. Period correctness** | `financial_ratios._fact_for()`'s exact-period-match requirement (a period error doesn't degrade a ratio, it silently drops the fact) | **NOT ASSESSABLE** — 0 training/eval examples on this schema |
| **D. Evidence grounding** | `grounding_check`'s existing deterministic gate, Gemini's real 100% (10/10) | **FAIL** — 0.0% on the closest analogous task |
| **E. True-negative behavior** | Gemini's real 100% (3/3) | **NOT ASSESSABLE** on gold set; qualitatively worse pattern observed on adjacent tasks |
| **F. End-to-end usefulness** | Whether facts become `computed` (not `insufficient_data`) rows | **NOT ASSESSABLE** — no demonstrated output on the real schema |

**The assignment's central rule applies exactly**: *"A model that is
cheaper but produces materially dangerous financial facts is NOT
economically superior."* LIM is not even cheaper in any way Gemini isn't
already ($0 marginal either way) — and it fails or cannot be assessed on
every one of the six gates.

Gate status recorded formally at `lim_training/quality_gate_status.json`
(`passed: false`) — this is the file `LocalLIMProvider` (§ below) reads
before allowing construction.

---

## 11. Decision

# 4. ABANDON LIM

**As a near-term extraction-engine investment — not a deletion of the
research artifacts.** Evidence, independently converging from every
angle checked:

1. **Quality**: even on its own, narrower, already-trained task (dividend
   extraction from short snippets), LIM tops out at 20-25% agreement/
   semantic-equivalence and 41-85% grounded-correctness (heavily
   task-dependent, collapsing to 0.0% on grounding-adjacent tasks). This
   sits squarely in the "2-25% teacher-agreement range" the assignment
   names as disqualifying.
2. **Task-domain mismatch**: 0 of LIM's 1093 real eval examples exercise
   the actual bottleneck task (multi-fact financial-statement extraction).
   Its best measured numbers describe a different, easier problem.
3. **Dangerous failure mode**: confirmed confident fabrication (unrelated
   content, non-round-factor magnitude errors up to ~8000×), not safe
   abstention — the specific failure mode the assignment's central rule
   warns against.
4. **Operational reliability**: currently cannot execute a single
   real-document-scale inference call on the available hardware —
   reproduced 3 times today, including on a previously-proven script, and
   consistent with an already-documented, unresolved problem from LIM-5.
5. **Economics**: no cost advantage exists ($0 marginal either way); the
   only possible advantage (throughput) is currently negative-infinite
   (zero working throughput vs. Gemini's real, working ~10 docs/day).

This is **not** "optimize it because it exists" — it is the opposite: the
evidence this session gathered (not assumed, not carried over from
memory) says the extraction-engine bet has not paid off and the
preconditions for it to pay off soon are not in place.

---

## 12. Recommended next action

**Do not launch Phase 7 (closing-the-gap training experiment)** — the
assignment's own trigger for that phase ("if the evaluation shows LIM is
reasonably close to the required quality bar") is not met. LIM is not
close; it is untested on the actual task and unreliable on the
infrastructure meant to run it.

**Move founder/engineering attention back to the highest-EV path**, which
this session's own prior work (`docs/alpha/FUNDAMENTAL_ALPHA_VALIDATION_
2026-08-13.md`) already identified: **resume quota-paced Gemini
extraction toward the 50-ticker coverage target.** That path is $0,
already proven at real quality (100%/90%/100%/100% across the dimensions
Gemini has actually been measured on), and blocked only by a calendar-time
constraint, not a capability gap.

**LIM is not deleted, not written off as worthless** — it remains exactly
what it was before this audit: real research infrastructure with a
documented, evidence-based backlog (`lim6_bottleneck_ranking.md`) ranking
next experiments (train longer — every run's loss was still decreasing at
its final step, under one full epoch; the highest-ranked untried lever).
**Two concrete preconditions would need to change before this decision is
revisited**, named explicitly so a future session can check them cheaply
without re-running this whole audit:

1. **A working, reliable local-inference environment** on the target
   hardware (or a hardware upgrade) — fixing the recurring OOM/segfault
   pattern first documented in LIM-5 and reconfirmed today.
2. **Real training/eval data for the actual target schema** (multi-fact
   financial-statement extraction with periods) — currently 0 examples
   exist; `lim6_bottleneck_ranking.md` §"out of scope" already names this
   as blocked by a prior owner constraint (no new datasets that phase),
   not by difficulty.

Until both are true, further LIM engineering time has low expected
information value relative to the Gemini extraction path, which is ready
to resume today at zero further engineering cost.

---

## What was built this session (Phase 1, for completeness)

Not the main deliverable, but required by the assignment and now real,
tested infrastructure for whenever LIM's preconditions are met:

- `LocalLIMProvider` (`src/ngxrot/documents/llm_providers.py`) — a real
  provider class, subprocess-based (shells to `lim_training/venv`,
  reusing the exact proven load pattern), **never** the default provider,
  **never** config-selectable (`build_default_provider("local_lim")`
  raises `LIMQualityGateError` by name, not a silent fallback), and
  refuses construction unless `lim_training/quality_gate_status.json`
  records `passed: true` — which it now does not (§10).
- `scripts/lim/test_local_lim_provider.py` — 13/13 passing, covering
  registry isolation, gate rejection/acceptance, and the one legitimate
  `allow_unvalidated=True` escape hatch (for a future eval harness only).
- `scripts/lim/infer_single.py` — the subprocess entry point (runs under
  `lim_training/venv`, not the main environment).
- `scripts/lim/gold_standard.py` — the 11-document, 20-fact,
  source-grounded gold set (§3), ready for the next attempt once
  inference is reliable.
- `scripts/lim/smoketest_extraction.py` — the timing/diagnostic harness
  that surfaced the real OOM/segfault findings in §7.

All existing Gemini-path tests (`scripts/test_reasoning_pipeline.py`,
`scripts/fre/test_period_extraction.py`) reconfirmed passing, unmodified,
after these changes.

---

## Status confirmation

- Production `extracted_facts=495`, `financial_reasoning_conclusions=267`
  — unchanged, verified before and after this audit.
- `alpha_engine.py`/`engine_full.py`/`runner.py`/`registry.py` — zero
  diffs, verified at Phase 0 and unchanged since.
- No Gemini quota consumed by this audit.
- No validation gate weakened — `LocalLIMProvider`'s gate is a NEW,
  additional safety mechanism, and the existing `numeric_consistency_check`/
  `grounding_check`/`validate_period()` gates were not touched.
