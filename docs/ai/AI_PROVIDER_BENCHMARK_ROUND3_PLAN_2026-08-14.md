# AI Provider Benchmark — Round 3 Plan — 2026-08-14

**Planning and testing only. Round 3 is NOT executed by this document.**
Stop condition satisfied: the plan and its tests are complete; execution
requires separate, explicit authorization.

---

## Phase 1 — Audit of the Decision Layer

Reviewed `provider_reliability.py` and `provider_decision.py` against
your checklist, against the real Round 1 + Round 2 records, and by
direct code inspection (not just assertion):

| Requirement | Status | Evidence |
|---|---|---|
| Every classification is derived programmatically | ✅ | `scripts/ai/test_provider_decision.py`'s integration test loads real Round 1/2 JSON and asserts `classify_provider()` reproduces all 5 required labels — nothing hand-picked |
| No score can be promoted via hard-coded provider preferences | ✅ | `grep` confirms zero `identity ==`/provider-name branches anywhere in `provider_decision.py` or `provider_reliability.py` — `classify_provider()`'s `identity` parameter is not even read inside the function body |
| Sample-size limitations are enforced | ✅ | `sample_confidence()` / `evidence_tier()` — n≤2 is always `insufficient`/`very_low`, regardless of the accuracy number attached to it |
| Reproducibility failures are penalized | ✅, with a stated scope limit | `reproducibility_flags()` correctly caps OpenRouter at EXPERIMENTAL for its ELLAHLAKES flip. **Limitation, disclosed**: it currently checks only the one mandatory document; `document_level_variance()` computes per-document spread for every document but isn't yet wired into the classification gate — a named Round 3 improvement (§ Category A) |
| Operational failures separated from model-quality failures | ✅ | `quality_metrics()` only counts `success AND structured_output_success` cases; `operational_metrics()` is a fully separate function over raw results, including rate-limit-vs-structural-vs-other failure counts |
| Structural failures cannot be "fixed" by waiting | ✅ | `record_failure()` disables after 2 consecutive structural failures (413/402-class) vs. 5 for any-class — verified: Groq's 413 message ("...tokens per minute (TPM)...") is correctly classified `structural`, not `rate_limit`, despite mentioning TPM — order-of-check matters and is tested explicitly |
| Transient 429s use cooldown, not polling | ✅ | `call_with_reliability_guard()` makes exactly one call attempt per invocation; a blocked identity raises `ProviderInCooldownError`/`ProviderDisabledError` without attempting the call — verified the guarded function's underlying `call_fn` is never invoked when blocked |
| Actual served model is always recorded | ✅ | `resp.model_id` (not the requested `model_id`) is what `benchmark_cache.py`/`run_benchmark.py` log as `actual_model`/`model_id_returned` — confirmed by `grep`, and by Round 1's real OpenRouter data (`meta-llama/llama-3.3-70b-instruct` requested and served, no substitution observed) |
| Provider fallback is auditable | ⚠️ **Honest gap, not silently claimed** | No fallback *routing chain* exists anywhere in this codebase yet — confirmed by `grep -rl fallback`, which returns only two unrelated comments (a currency-default fallback, a docstring mention of OpenRouter's own internal routing). This is correct sequencing, not an oversight: your own Phase 10 (2026-08-13 assignment) explicitly deferred fallback design until "after independent benchmarking proves provider quality," which hasn't happened. The reliability layer's `healthy`/`cooldown`/`disabled` states are exactly what a future fallback chain would consult, but the chain itself is unbuilt |
| No benchmark result can silently enter production | ✅ | `benchmark_calls` is a schema-separate table from `llm_calls`; `llm_calls=69` unchanged across all of Rounds 1, 2, and this layer's build; re-verified again just now (§ Phase 4) |

## Phase 2 — Round 3 Design

### Provider scope (per your instruction — no capacity spent on unsuitable providers)

| Identity | Included | Why |
|---|---|---|
| Cerebras / gemma-4-31b | ✅ | EXPERIMENTAL, moderate evidence tier — real candidate |
| Cerebras / gpt-oss-120b | ✅ | EXPERIMENTAL, moderate evidence tier — real candidate |
| OpenRouter / Llama 3.3 70B | ✅ | EXPERIMENTAL, preliminary tier (reproducibility unresolved) — the most important identity to re-test on ELLAHLAKES specifically |
| Gemini | ✅, opportunistic only | EXPERIMENTAL/CONTROL, insufficient tier (n=1) — included as a single quota probe per document batch, same non-polling discipline as Rounds 1-2; not weighted equally in scheduling since its quota has failed 2 sessions running |
| Groq | ❌ excluded | DISABLED — zero usable extractions across two independent task configurations; re-testing would be exactly the "waste capacity on a demonstrated-unsuitable provider" this instruction forbids |
| Cerebras / zai-glm-4.7 | ❌ excluded | Not named in your Round 3 priority list; Round 1's own data (33% structured-output success rate) doesn't justify spending capacity ahead of the four included identities |

### Frozen manifest

`src/ngxrot/documents/benchmark_manifest.py::ROUND3_MANIFEST` — a real,
content-hashed, immutable (`frozen=True` dataclass) object. Hash:
`b5328680fc79da43d1a9135733059928c907c3b6f4c093219c88908eba8357be` (computed at plan time — `test_benchmark_manifest.py`
verifies this hash is reproducible and that any field edit changes it,
so drift between plan and execution is detectable, not assumable).

| Field | Frozen value |
|---|---|
| `benchmark_version` | `round3-plan-2026-08-14` |
| `prompt_version` | `financial_reasoning_draft_v3` — verified equal to `prompts.DRAFT_PROMPT_VERSION` right now, by test |
| `schema_version` | `draft_schema_v3_pilot_fact_types` — the `_DRAFT_SCHEMA_INSTRUCTIONS` shape, unchanged since Round 1 |
| `document_ids` | the same 10 gold-set documents as Rounds 1-2 (452, 9530, 9485, 4245, 4508, 5163, 10625, 7793, 6393, 11122) |
| `document_versions` | sha256 of each document's real text, verified to match the actual files on disk right now (`test_benchmark_manifest.py`, 0 mismatches) |
| `providers` / `models` | cerebras (gemma-4-31b, gpt-oss-120b), openrouter (meta-llama/llama-3.3-70b-instruct), gemini (gemini-3.6-flash) |
| `temperature` | **provider default (unspecified) — a named execution blocker, see below** |
| `reasoning_settings` | **provider default (unspecified) — same caveat** |
| `max_tokens` | `16384` — identical to production and Rounds 1-2, not adjusted for any provider |
| `context_strategy` | full document text inline in the user prompt (the only strategy `build_draft_prompt()` implements) |
| `grading_version` | `grade_benchmark_v3_round3` — Round 1's matcher fixes (AFRIPRUD/CAP period disambiguation) plus the new `schema_compliance_check()` and evidence-fidelity line-citation check below |

**Named execution blocker, disclosed rather than silently worked around**:
`llm_providers.py`'s three experimental provider classes and
`GeminiProvider` do not currently accept a `temperature` or
`reasoning_effort` parameter at all — there is no plumbing to set them.
Freezing the manifest's `temperature`/`reasoning_settings` fields as
"provider default" is accurate to what Round 1/2 actually did, but
Category A's reproducibility testing would benefit from an explicit
`temperature=0` setting. Adding that plumbing is a **provider-behavior
change** and this task's own instruction is "do not modify... existing
provider behavior" — so it is named here as a **prerequisite for a
maximally clean Round 3**, not built speculatively. Round 3 can execute
without it (using provider defaults, identical to Round 1/2's own
conditions), just with slightly less controlled reproducibility
conditions than ideal.

## Phase 2 (continued) — Test matrix

### A. Reproducibility (within-round, controlled — distinct from Rounds 1-2's cross-round comparison)

Repeat the **same (document, identity)** combination 3× each, using
`force=True` on `benchmark_complete()` to bypass the on-disk cache (a
cache hit would just return the same stored response and defeat the
purpose). Documents: **ELLAHLAKES (mandatory)**, TRANSCORP (smallest,
cleanest control), CAP (medium, has the source-document's own EPS
prose/table discrepancy — a good stress case for consistency). 4
identities × 3 documents × 3 repeats = **36 calls**. Metric: does
`structured_output_success` and `numeric_accuracy` stay consistent
across the 3 repeats for the same (document, identity)? A single flip
(as OpenRouter/ELLAHLAKES showed across Rounds 1→2) is exactly what this
category is built to catch at finer grain and lower cost than a full
extra round.

### B. Unit robustness

| Case | Document | Status |
|---|---|---|
| ₦'000 (table header) | ELLAHLAKES (11122) | ✅ in gold set, mandatory |
| ₦ million (table header) | CAP (4508), UACN (5163) | ✅ in gold set |
| ₦ billion (prose) | TRANSCORP (9485), MTNN (6393) | ✅ in gold set |
| ₦ trillion (prose) | OANDO (10625) | ✅ in gold set |
| Plain ₦ (no stated scale, raw absolute figures) | **none in the current gold set** | ⚠️ **gap — needs sourcing a real document before execution**, not fabricated |

### C. Period robustness

| Case | Document | Status |
|---|---|---|
| FY | CAP, TRANSCORP, OANDO | ✅ |
| H1 | UACN, MTNN | ✅ |
| Q3 / 9M-labeled-as-Q3 ambiguity | UBA, AFRIPRUD | ✅ (both are REAL, independently confirmed source-label ambiguities, not synthetic) |
| Comparative periods | present in every non-true-negative document | ✅ |
| Pure Q1 | **none in the current gold set** | ⚠️ **gap — needs sourcing** |
| Confirmed restated-figures disclosure | **none in the current gold set** | ⚠️ **gap — needs sourcing** |

### D. Evidence fidelity (page/section/table/row/column/source text)

**The current extraction schema has no page/section/row/column fields —
only a flat `quoted_evidence` string.** Adding them would be a schema
change, forbidden by this task's own freeze instruction. Round 3
therefore tests evidence fidelity **without touching the schema**, by
reusing what already exists:
1. `check_grounding()` (unchanged) confirms `quoted_evidence` is an exact
   whitespace-tolerant substring of the real document text — already
   done in Rounds 1-2.
2. **New, additive**: for each grounded quote, deterministically locate
   its line-number span in the source `document_text` file (already
   line-numbered) and compare against the gold set's own
   `source_line` annotations (already present in
   `benchmark_gold_set.py` for most facts) — a purely post-hoc,
   deterministic check requiring no prompt/schema change, added to
   `grade_benchmark_v3_round3`.

### E. Structured-output reliability

`schema_compliance_check()` (new, built and tested this phase — 9
passing tests) classifies every response into exactly the 5 cases you
specified: `empty` (correct for STANBIC/MORISON true-negatives — not
itself a failure), `malformed` (no valid `facts` list), `partial`
(valid facts array, but individual facts/impact_assessments/implication
missing required keys), and `compliant`. Distinct from, and computed
alongside, raw `structured_output_success` (did `json.loads` succeed at
all) — a response can be valid JSON and still schema-noncompliant, and
Round 3 will report both rates separately.

### F. Operational stress

**The single most actionable finding from Round 2**: Cerebras and Groq
both degraded sharply under back-to-back same-provider calls (a rolling
TPM window compounding across consecutive requests), even though
individually-sized requests worked fine in isolation. Round 3's runner
(not built yet — see § Execution prerequisites) must:
1. Wire `call_with_reliability_guard()` into the actual call path, so
   real cooldown/disabled state gates every attempt.
2. **Throttle same-provider request cadence** — space consecutive calls
   to the same provider by a fixed interval (candidate: 65s, comfortably
   past a 60s rolling window) rather than firing all 10 documents
   back-to-back, directly testing whether Round 2's operational collapse
   was a cadence artifact or a harder capacity ceiling.
3. Record latency, throughput (successful validated extractions per unit
   wall-clock time), and retry-budget consumption per identity.

## Phase 3 — Statistical Discipline (code, not just prose)

`src/ngxrot/documents/provider_decision.py::evidence_tier()` — four
explicit tiers, `EVIDENCE_TIERS = ("insufficient", "preliminary",
"moderate", "promotion_eligible")`:

- **insufficient**: n=0, n≤2, or ANY catastrophic error/true-negative
  violation (a catastrophic error resets evidence to insufficient
  regardless of how much other data exists — a large n does not buy
  back trust after a hard failure).
- **preliminary**: n=3-5, OR a reproducibility flag on a mandatory case
  even with a larger n (this is exactly OpenRouter's real state today).
- **moderate**: n≥6, no catastrophic/reproducibility issue, but does not
  yet clear ≥80% operational success in every round with data (this is
  exactly both Cerebras identities' real state today — real, decent
  quality evidence, undermined by an operational throughput problem).
- **promotion_eligible**: clears all of the above. Necessary, not
  sufficient — `classify_provider()` still caps this at SECONDARY, never
  auto-PRIMARY; PRIMARY explicitly requires a third confirming round
  plus operator sign-off.

**Verified against real data** (not asserted): `cerebras-gemma-4-31b`
and `cerebras-gpt-oss-120b` → `moderate`; `openrouter-llama-3.3-70b-instruct`
→ `preliminary`; `gemini-control` and `groq-llama-3.3-70b-versatile` →
`insufficient` — 5/5 matching the classification layer's own stated
reasoning, confirmed by `test_provider_decision.py`.

**Never call a provider "best" from a point estimate**: nowhere in
`provider_decision.py` does any function rank or sort providers by a
single accuracy number — `classify_provider()` only ever answers "does
this identity clear an explicit, named bar," never "is this identity's
score higher than that one's."

## Phase 4 — Testing and regression

| Suite | Result |
|---|---:|
| `test_provider_reliability.py` (existing, unaffected) | 34/34 |
| `test_provider_decision.py` (extended: +evidence_tier, +schema_compliance_check, +real-data tier checks) | 64/64 |
| `test_benchmark_manifest.py` (new) | 17/17 |
| `test_provider_gateway.py` (Phase 1, unaffected) | 39/39 |
| `test_reasoning_pipeline.py` (full existing pipeline) | 154/154 |
| `test_numeric_consistency.py` | 12/12 |
| `test_tabular_unit_consistency.py` | 22/22 |
| `test_data_quality_monitoring.py` | 12/12 |
| `test_research_memory.py` | 14/14 |
| `test_investment_os_e2e.py` | 23/23 |
| **Total** | **395/395** |

Production invariants, re-verified after this build: `extracted_facts=495`,
`financial_reasoning_conclusions=403`, `llm_calls=69` — all unchanged.
`git diff --stat` on `alpha_engine.py`/`engine_full.py`/`runner.py`/
`registry.py` — empty.

## Promotion gate (restated, unchanged from the decision layer)

1. Zero catastrophic errors, zero true-negative violations.
2. No reproducibility flag on any mandatory case.
3. Quality confidence reaches `moderate` (n≥6 scoreable cases).
4. Operational success rate ≥80% in **every** round with data (not an
   average).
5. At least 2 rounds with data clearing the above.
6. Even then: capped at SECONDARY. PRIMARY requires a third confirming
   round and explicit operator sign-off — never automatic.

## Stop conditions for Round 3 itself (once authorized)

Carried forward from the standing session rules, restated for this
specific round:
- Do not repeatedly poll an exhausted quota — one probe per identity per
  session, same as Rounds 1-2.
- Do not modify the prompt, schema, grading rules, or documents once
  Round 3 begins — any change after seeing partial results invalidates
  the round and must be logged as a new, separately-authorized amendment,
  not a silent edit.
- Do not touch Alpha Engine, Evidence Engine, Statistics Engine, FRE, or
  production provider config.
- If a catastrophic error appears on any identity, stop and report
  immediately — do not continue collecting more data past a hard
  failure to see if it "averages out."
- Real cost must be checked (not assumed) after execution, same as
  Rounds 1-2's OpenRouter `/v1/key` check.

## Expected outputs (once Round 3 executes)

- `data/staging/benchmark_results_round3_*.json` (raw, mirroring Rounds
  1-2's format, extended with `schema_compliance` and
  `evidence_fidelity` fields per response).
- Updated `provider_decision_layer_*.json` via `build_decision_layer.py`,
  now with 3 rounds of data per identity instead of 2 — the first point
  at which `evidence_tier()`'s `min_rounds_with_data=2` bar has real
  headroom to distinguish a 2-round vs. 3-round confirmation.
- `docs/ai/AI_PROVIDER_BENCHMARK_ROUND3_RESULTS_2026-08-XX.md` (a
  results report, not this plan) with the same honesty discipline as
  Rounds 1-2: report a null/negative result plainly if that's what the
  data shows.
- An updated classification table — very possibly **no change** from
  today's (EXPERIMENTAL/EXPERIMENTAL/EXPERIMENTAL/EXPERIMENTAL-CONTROL/
  DISABLED), since Category F's throttling fix is a hypothesis about
  Round 2's operational collapse, not a guarantee.

## Execution prerequisites (not built, named honestly)

1. **The actual Round 3 runner script** — this plan and its manifest are
   built; the script that reads `ROUND3_MANIFEST`, throttles requests,
   calls `call_with_reliability_guard()`, and writes results does not
   exist yet. Building it is "executing Round 3" territory and was not
   done here, per your explicit "stop after the plan" instruction.
2. **Two additional real documents** to close the Category B (plain ₦)
   and Category C (pure Q1, confirmed restated figures) gaps — sourcing
   requires reading candidates from the production document archive
   (11,589 documents available) and independently verifying gold values,
   the same process used for the original 10. Not done here to avoid
   scope creep into execution prep.
3. **Temperature/reasoning-effort plumbing** in `llm_providers.py`, if a
   maximally controlled Category A reproducibility test is wanted — an
   optional enhancement, not a blocker (Round 3 can run under provider
   defaults, identical to Rounds 1-2).

None of these are required to *authorize* Round 3 — they are the
concrete next actions once authorization is given.
