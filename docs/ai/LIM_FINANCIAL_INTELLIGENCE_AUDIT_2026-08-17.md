# LIM / Ollama Financial Document Intelligence Audit — 2026-08-17

*Follow-up to `docs/LIM_ECONOMIC_VIABILITY_AUDIT_2026-08-13.md` (4 days prior). This audit's job is
narrower and more disciplined than re-deriving everything from scratch: verify what has actually
changed since that audit, decompose the vague "financial intelligence" question into the ten specific
sub-tasks this assignment names, and only proceed toward training if the fresh evidence says to.
**It does not.** No training was run. No inference was attempted (§0 explains why). Alpha Engine, H-011,
FRE production path, Evidence Engine, and Statistics Engine: zero changes, confirmed. `REASONING_WEIGHT`
unchanged at `0.0`.*

---

## 0. Phase 0 — Inventory, and what has changed since 2026-08-13

Directly re-verified, not assumed carried-over, on 2026-08-17:

| Item | 2026-08-13 audit | 2026-08-17 (today) | Changed? |
|---|---|---|---|
| `training_registry.sqlite` runs | 38 | **38** | No |
| Most recent training run | RB-3b, 2026-07-30 | RB-3b, 2026-07-30 | No |
| `eval_registry.sqlite` runs / examples | 24 / 1093 | **24** / unchanged | No |
| `dataset_registry.sqlite` versions | not enumerated | **14** | (baseline established, not previously counted) |
| `lim_training/quality_gate_status.json` `passed` | `false` | **`false`** | No |
| `LocalLIMProvider` safety wrapper (`scripts/lim/test_local_lim_provider.py`) | 13/13 | **13/13** | No |
| `scripts/lim/gold_standard.py` (11 docs, 20 facts, incl. ELLAHLAKES doc 11122 and TRANSCORP doc 9485) | present, built that session | **present, unchanged** | No |
| `extracted_facts` (production) | 495 | 495 | No |
| `financial_reasoning_conclusions` (production) | 267 | 403 | **Yes — but derived, not raw.** All growth is deterministic ratio/trend/flag computation (`financial_ratios.py`/`trend_classification.py`/`financial_health_flags.py`) over the SAME 495 facts — zero new raw financial-statement facts were extracted in the interim, so zero new LIM-usable gold examples exist either |
| Protected Alpha Engine files | zero diff | zero diff (re-confirmed) | No |

**Conclusion of Phase 0: nothing material has changed.** Neither of the 2026-08-13 audit's two named
preconditions for revisiting the ABANDON decision — (1) a working local-inference environment, (2) real
training/eval data for the actual target schema — has been met. This audit does not re-attempt the GPU
inference call that reliably crashed 3 independent times on 2026-08-13 (`torch.OutOfMemoryError`, then a
segfault at higher context length, on the same RTX 3050 6GB laptop GPU this session also runs on) —
retrying it today with no reason to believe the hardware or contention pattern has changed would
reproduce a known failure for zero new information, the same "diminishing evidence value" reasoning the
prior audit itself used to stop after 3 attempts. If a future session has a different machine or has
fixed the OOM/segfault pattern, that changes this calculus; nothing here suggests it has.

**What already existed and is directly reused, not rebuilt** (per this assignment's own instruction):
`lim_training/qwen3_4b_model` (base Qwen3-4B weights), 38 real LoRA training runs, 24 real eval runs
across 9 dataset types (`extraction`, `citation_grounding`, `confidence_estimation`,
`contradiction_detection`, `corporate_actions`, `coverage_assessment`, `entity_recognition`,
`event_understanding`, `evidence_ranking`, `financial_reasoning`, `hallucination_detection`,
`investment_decision_support`, `knowledge_graph_completion`, `portfolio_reasoning`, `rag`, `retrieval`,
`self_critique` — 17 directories under `lim_training/datasets/`), `LocalLIMProvider` (the production
safety wrapper that refuses construction without a passed gate), and the 11-document source-grounded
gold set including both mandatory benchmark cases this assignment names.

---

## 1. Recommended task scope (Phase 1 — the genuinely new analysis this audit adds)

The prior audit found LIM's real numbers describe *a* task, just not *the* bottleneck task. This
assignment asks for something the prior audit didn't do explicitly: decompose "financial intelligence"
into its ten named sub-tasks and judge each on its own, against real evidence where it exists.

| # | Task | 4B-local-suitable in principle? | Real evidence today |
|---|---|---|---|
| 1 | Document understanding (is this a financial statement / news article / dividend notice?) | **Yes** — coarse classification, low ambiguity, low stakes if wrong (double-checkable downstream) | No dedicated eval examples exist; closest proxy (`entity_recognition`) untested on real documents |
| 2 | Financial fact extraction (revenue/net_profit/etc from tables) | **No, not now** — this is the platform's actual production bottleneck, already served at measured 90-100% quality by Gemini; LIM has **0 of 1093** real eval examples on this exact schema | `docs/lim_runs/lim6_bottleneck_ranking.md`: *"would need new export/data work to even become usable"* |
| 3 | Unit interpretation (₦'000 / ₦m / ₦bn) | **Yes, promising** — narrow, well-specified, exactly the ELLAHLAKES defect class (already fixed on the Gemini side via the v3 prompt's UNIT SCALE rule, not via LIM) | 0 training examples exist for this schema specifically |
| 4 | Period interpretation (FY/H1/Q1/9M from text) | **Yes, promising** — same shape as #3, narrow and well-specified | 0 training examples |
| 5 | Accounting-semantic classification (Revenue vs Other Income vs Finance Income) | Plausible for a narrow classifier, genuinely harder — real accounting judgment involved | 0 training examples; `financial_reasoning` dataset type registered but empty |
| 6 | Evidence localization (find the actual source text/page) | **No — measured, not assumed.** LIM's own closest analogous tasks (`evidence_ranking`/`rag`/`retrieval`) scored **0.0% grounded_correctness** across 34 real examples, including outputs completely unrelated to the input (World Cup / photovoltaic-cell text) | Real, damning, already-measured data |
| 7 | Cross-fact relationship detection (within one filing) | Unknown — genuinely interesting (Phase 9's target), but **0 registered examples** | Untested, not proven either way |
| 8 | Contradiction detection | Same status as #7 — 0 examples, untested | Untested |
| 9 | Financial reasoning | **No** — `self_critique_quality` measured at **0.0%** (24 real examples); this platform's own charter and this assignment's own guardrail ("LIM must NOT become the source of mathematical truth") both point the same direction | Real, measured, disqualifying |
| 10 | Directional reasoning | **No, by explicit design** — this session's own separate `DIRECTIONAL_REASONING_REPAIR_AND_VALIDATION_2026-08-17.md` and `..._DATA_READINESS_2026-08-17.md` already show even Gemini-tier reasoning struggles here (62.5% bullish-call failure rate on real data); a 4B local model has no basis for taking this on, and this assignment's own instruction is explicit that deterministic code, not any LLM, computes ratios/growth/margins/P-E/trends | Cross-referenced against real, contemporaneous work this session |

**Bottom line**: tasks #1/#3/#4 are the honest candidates for a future narrow-task LIM role — small,
well-specified, low-ambiguity classification problems, the textbook fit for a fine-tuned small model.
Tasks #2/#6/#9/#10 should stay with Gemini/deterministic code, on real, measured evidence, not
assumption. Tasks #5/#7/#8 are genuinely unproven — not disqualified, not validated, just never tested.

---

## 2–3. Dataset audit & gold-dataset construction (Phases 2–3)

**No new gold data was built in this pass** — the 2026-08-13 gold set already satisfies this
assignment's explicit requirements and nothing has changed to extend it:

- **ELLAHLAKES**: doc 11122, labeled `quantitative_adversarial`, 5 expected facts, explicitly including
  *"a genuine irregular-period + two-different-loss-figures case"* — this is the exact real defect class
  the platform's Gate-2 confirmation batch validated on the Gemini side (₦'000-scale revenue/net_profit,
  confirmed exact-match against gold in this session's earlier FRE Gate-2 work). **Already the mandatory
  benchmark example this assignment requires**, built from real source text
  (`data/staging/document_text/11122.txt`), not copied from any prior extraction.
- **TRANSCORP**: doc 9485, labeled `quantitative_adversarial`, 7 expected facts, **including the real
  10× case** — also already present, also already the mandatory benchmark example this assignment
  requires.
- Full gold set: 11 documents, 20 expected facts, 7 true negatives (SEPLAT ×2, STANBIC ×2, ELLAHLAKES ×1,
  MORISON ×2), 2 adversarial cases (the two above), 1 qualitative-only metric-mistag trap (STANBIC 452).

**Classification, honestly, per this assignment's GOLD/SILVER/UNVERIFIED split**:

| Tier | Definition | Count |
|---|---|---|
| GOLD | Value read directly from real source text during dataset construction, independently of any model's prior extraction | 20 facts (the gold set above) |
| SILVER | Model-extracted, cross-validated against a second independent check (e.g. accounting-identity holds, or narrative+table agreement) | The 495 real `extracted_facts` production rows carry this tier informally via `confidence_tier`/`extraction_confidence`, but **none of them were built as LIM training pairs** — they were never exported into `lim_training/datasets/` in a task-matched schema |
| UNVERIFIED | Raw model output, no independent check | LIM's own 1093 real eval examples — real, not fabricated, but **on a different task** (single-fact dividend/corporate-action extraction, mean 81 input tokens) than the one this assignment cares about |

**Is there enough GOLD/SILVER data to train the actual target task (multi-fact financial-statement
extraction)? No — quantified, not hand-waved: 20 gold facts across 11 documents.** A LoRA fine-tune
needs at minimum dozens to low-hundreds of task-matched examples per sub-task to have any chance of
generalizing past memorization; 20 examples spread across facts as different as revenue, net_profit,
assets, and a true-negative check is not that, by a wide margin. This matches — does not contradict —
the 2026-08-13 audit's independent finding that `citation_grounding`/`financial_reasoning` datasets have
**0** registered examples.

---

## 4. Train/validation/test split design (Phase 4)

**Not built in this pass, and honestly explained why**: a deterministic, leakage-free split is only a
meaningful artifact once there is a dataset large enough to split. Splitting 20 gold facts across 11
documents into train/validation/test buckets (per this assignment's own instruction: *train on
companies/documents A–N, validate on separate companies, test on completely held-out documents*) would
leave single-digit document counts per bucket — not a split, a coin flip. Producing a manifest now would
create the appearance of methodological rigor over a dataset too small for the method to mean anything.
**This is deferred, not skipped** — the moment gold data exists at meaningful scale (see §7's estimate),
building this manifest is the very next concrete step, and the design principle (no ticker/document/
fiscal-period appearing in more than one split) is already the platform's own established PIT/leakage
discipline used everywhere else on this platform (e.g. `restatement_detection.py`'s comparative-column
handling) — nothing new needs to be invented for it.

---

## 5. Is LoRA training justified? (Phase 5 decision)

## **B — INSUFFICIENT DATA; BUILD DATASET FIRST**

Quantified, per this assignment's own required inputs:

| Input | Value |
|---|---|
| Task-matched gold examples (the real target schema) | 20 |
| Examples per sub-task (of the 10 named in §1) | 0–20, wildly uneven, and 0 for 6 of the 10 tasks |
| Token volume at real document scale | Unmeasured — inference is non-functional (§0), so even a token-volume estimate for a real 130K-character filing would be speculative |
| Label quality | High for the 20 that exist (source-grounded, not model-copied) — but 20 is not a dataset |
| Task diversity | 3 of 10 tasks (§1: unit, period, document-type) are plausible near-term candidates; 4 of 10 (extraction, evidence, reasoning, directional) are explicitly ruled out on real measured evidence; 3 of 10 are genuinely untested |
| Company diversity | 11 documents across roughly 8 distinct tickers (STANBIC, SEPLAT, MORISON, ELLAHLAKES, TRANSCORP + true-negative padding) — thin for any one sub-task |
| Document diversity | 11 documents total, platform-wide, for this schema |

**No positive result was manufactured to justify proceeding.** The honest answer at every one of these
inputs is "not enough," consistently, not selectively. This is the same conclusion as the 2026-08-13
audit's precondition #2, independently re-derived here from this assignment's own specific inputs rather
than cited wholesale.

**Per this assignment's own explicit instruction ("Do not train anything until the audit proves that
training is justified") — Phases 6–9 (LoRA training run, financial-document benchmark against
Gemini/Groq/Cerebras/OpenRouter, specialized adversarial tests, cross-fact understanding test) are
NOT executed in this pass.** Running them against 20 gold examples, or against a model whose inference
path is non-functional on the available hardware, would produce numbers that look like rigor without
being rigor — exactly what this assignment's own "do not manufacture a positive result" and "never treat
LLM confidence as factual accuracy" guardrails exist to prevent.

---

## 6–9. Training run, benchmark, adversarial tests, cross-fact test

**Not run — see §5.** No LoRA-V2 checkpoint was created. No baseline-vs-checkpoint comparison was made.
No benchmark against Gemini/Groq/Cerebras/OpenRouter's real numbers (already established elsewhere: see
`docs/ai/AI_PROVIDER_CONSOLIDATED_EVIDENCE_2026-08-14.md`) was run for LIM, because LIM currently cannot
execute a real-document-scale inference call at all (§0) — comparing a non-functional system against
working ones would not be a fair benchmark, it would be a guaranteed, uninformative zero. The specialized
unit/period/entity/semantics/evidence adversarial tests this assignment names in Phase 8, and the
cross-fact multi-signal test in Phase 9, are exactly the RIGHT next experiments once §4's dataset and
§0's inference environment are both real — they are not run here because running them today would
produce fabricated-looking results against an environment already proven not to work.

---

## 10. Economic/decision classification (Phase 10)

## **C — RESEARCH-ONLY**

Not **D — Abandon**: the 2026-08-13 audit was explicit that LIM "is not deleted, not written off as
worthless" — real, substantial research infrastructure exists (38 training runs, 24 evals, a working
safety-gated provider wrapper, a real gold-standard benchmark set already covering both of this
assignment's mandatory cases), and 3 of the 10 decomposed sub-tasks (§1) remain genuinely plausible
future candidates, not disqualified.

Not **A — Promising, continue training**: nothing in this pass demonstrates readiness to train — §5's
own quantified inputs say the opposite, and the inference environment cannot currently execute even to
generate a baseline.

Not **B — Useful for narrow task only**: that would require having actually *validated* LIM as useful on
some narrow task with real evidence. §1's "promising" tasks (unit/period/document-type) are hypotheses
grounded in task shape, not results — 0 training examples exist for any of them. Calling this "B" would
be promoting on architecture-fit reasoning alone, which is exactly the kind of unearned promotion this
assignment's guardrails forbid.

---

## 11. Architectural recommendation

**No production role is recommended today** — that would contradict §5/§10 directly. If and when §4's
dataset and §0's inference environment are both resolved, the evidence-grounded next candidate role,
specifically, is:

**Role 3 — Semantic chunk classification** (narrow: unit-scale tagging, period-type tagging,
document-type tagging), evaluated as a **local preprocessing pass whose output is always verified by
the existing deterministic checks** (`numeric_consistency_check`, `validate_period()`) before ever
reaching `extracted_facts` — never as a standalone extraction engine (Role 4), never as evidence
localization (Role 5 — already disqualified by real, measured 0.0% grounded_correctness), never as
contradiction detection (Role 6 — untested, not disqualified, but not evidenced either) until §1's tasks
#5/#7/#8 get real training data and a working inference environment to be evaluated honestly.

---

## 12–14. Failure analysis, economic assessment, comparison with current providers

Fully covered by `docs/LIM_ECONOMIC_VIABILITY_AUDIT_2026-08-13.md` §5–§9 and reconfirmed unchanged by
§0 above — not re-derived here to avoid duplicating a report that is still current. Headline, re-stated:
confirmed confident fabrication (non-round-factor errors up to ~8000×, no abstention), catastrophic
evidence-grounding failure (0.0%), self-critique quality 0.0%, zero measurable cost or throughput
advantage over Gemini (both $0 marginal; LIM currently has zero working throughput), and a non-functional
local inference environment reproduced 3 times independently.

---

## 15. Exact next step

**Not training. Not benchmarking. Two concrete, cheap, low-risk actions, in order:**

1. **Resolve the local-inference environment** (the 2026-08-13 audit's precondition #1, still unmet).
   This is a hardware/environment fix, not a modeling decision — confirm whether a non-quantized smaller
   context run, a different quantization scheme, or simply running on different hardware avoids the
   OOM/segfault pattern. This alone would let a future session generate a real baseline (base Qwen3-4B
   vs. the existing RB-3b checkpoint) on the already-built gold set, which is the cheapest possible next
   real signal.
2. **Only if (1) succeeds**, scope a small, targeted dataset-construction effort for the three
   §1-identified promising narrow tasks (unit interpretation, period interpretation, document-type
   classification) — not the full ten-task list, not the extraction bottleneck task itself (that stays
   on Gemini, per real measured quality). Target scale: enough to make §4's train/validation/test split
   meaningful — tens of examples per task, minimum, not the current 0–20.

Do not skip to (2) without (1) — an unusable inference environment makes any dataset investment
unrealizable in the near term regardless of its size.

---

## Explicit confirmations

- Alpha Engine (`alpha_engine.py`/`engine_full.py`/`runner.py`/`registry.py`): zero diff, verified before
  and after this audit.
- H-011: not touched, not re-run.
- `REASONING_WEIGHT`: unchanged at `0.0`.
- FRE production path, Evidence Engine, Statistics Engine: zero changes — this audit made no writes of
  any kind (read-only inspection of `lim_training/*.sqlite`, existing docs, and existing scripts).
- No production data mutation, therefore no backup/restore step was required for this pass.
- Existing tests: `scripts/lim/test_local_lim_provider.py` re-run, 13/13 pass, unchanged.
- No provider was promoted. No new provider was added. LIM was not promoted. `lim_training/
  quality_gate_status.json` `passed` remains `false`, unmodified.
- Model quality vs. provider reliability kept explicitly separate throughout — this audit's findings are
  about LIM's own measured quality and this session's own hardware, not a claim about Gemini/Groq/
  Cerebras/OpenRouter's reliability, which is tracked separately in `docs/ai/
  AI_PROVIDER_CONSOLIDATED_EVIDENCE_2026-08-14.md`.
