# Fund Alpha — Local Intelligence Model (LIM) Architecture

**Status: DESIGN ONLY. No training code, no schema changes, no modification
of the AI Intelligence Layer (frozen at `ai-layer-stable-baseline-2026-07-27`)
have been made or are proposed by this document. Nothing described here
executes until each phase is individually reviewed and approved (§7).**

## 0. What this is and isn't

Fund Alpha's AI Intelligence Layer (`src/ngxrot/documents/`) currently
depends on an external teacher model (Gemini, via `GeminiProvider`) for
every LLM-backed reasoning call. The **Local Intelligence Model (LIM)** is a
domain-specialized, locally-run model that will eventually let the platform
run the same reasoning pipeline without that external dependency.

**LIM is not a new reasoning architecture.** It is a new *provider* — a
different way of answering the exact same `LLMProvider.complete()` calls
`extract.py`/`self_critique.py` already make. It does not change what Steps
1-14 ask for, how grounding works, how the self-critique gate works, or
anything about the schema. If this design succeeds, the only thing that
changes is which model answers the prompt — exactly the same shape of
change as the 2026-07-22 Anthropic→Gemini swap, which touched exactly one
file (`llm_providers.py`) and zero pipeline logic.

**Explicit non-goals, this document and every phase in it:**
- No training code is written in this pass (owner instruction).
- No change to `src/ngxrot/documents/` (frozen baseline).
- No change to `alpha_engine.py`/`runner.py`/any portfolio-facing module —
  the existing hard boundary (no import of `ngxrot.documents` there) is
  unaffected and unrelated; LIM only ever competes with Gemini for the role
  of *provider inside* the documents pipeline, nothing more.
- LIM is never auto-promoted to the default provider. A cutover is a
  disclosed, tested, owner-approved config change (`configs/llm_provider.toml`),
  exactly like the Gemini swap — never automatic, never silent.

---

## 1. System architecture

### 1.1 Integration point: LIM is a provider, not a parallel pipeline

`llm_providers.py` already defines the seam this whole design hangs off:

```
class LLMProvider(ABC):
    def complete(self, system_prompt, user_prompt, max_tokens, ...) -> LLMResponse: ...

PROVIDER_REGISTRY = {"gemini": GeminiProvider, "mock": MockProvider}  # + "local_lim"
```

Nothing in `extract.py`, `self_critique.py`, `reasoning.py`, `cache.py`, or
`prompts.py` imports a concrete provider class — confirmed true today and a
condition this design must keep true. Adding LIM means:

1. A new `LocalLIMProvider(LLMProvider)` class in `llm_providers.py`
   (implementation deferred to Phase LIM-7, §7).
2. One new entry in `PROVIDER_REGISTRY`.
3. `configs/llm_provider.toml` gains `provider = "local_lim"` as a
   *selectable*, not default, option, plus a `local_lim` config block
   (endpoint URL, model_id, timeout).
4. Zero changes anywhere else. `llm_calls.model_id` simply starts recording
   `"qwen3-4b-lim-sft-v1"` (or whatever version string) instead of
   `"gemini-3.6-flash"` on the calls that use it. The whole audit trail
   (`llm_calls`, `document_hash`, cache-by-prompt) already treats
   `model_id` as free text — no schema change needed.

### 1.2 Where LIM-specific code lives

Training, dataset-export, and evaluation code for LIM is **not** part of the
reasoning pipeline and must not live inside `src/ngxrot/documents/` — mixing
training-time tooling into the already-audited, frozen inference-pipeline
package would blur a boundary that's been kept clean through six phases.
Proposed layout (created only as each phase actually starts, per §7):

```
src/ngxrot/lim/               # LIM-specific library code (dataset export,
                               # eval harness, local-provider client helpers)
  datasets/                    # read-only exporters over the existing DB
  eval/                        # eval harness (reuses grounding.py/pilot_summary.py)
scripts/lim/                   # runnable entry points (export_dataset.py,
                               # train_stage.py, run_eval.py, ...) — matches
                               # this project's existing scripts/ convention
lim_training/                  # NOT committed as code-with-data: base model
                               # downloads, checkpoints, LoRA adapters, raw
                               # JSONL datasets. Gitignored like data/archive/,
                               # data/staging/, data/capture/ — large binary
                               # artifacts, not source.
docs/lim_runs/                 # Markdown completion reports per phase,
                               # matching reports/phase_*.md convention
                               # (kept under docs/ to separate LIM narrative
                               # from the quant/AI-layer reports/ directory)
```

`llm_providers.py` itself (the one file that changes) stays in
`src/ngxrot/documents/` — it is pipeline code, just gaining one more
concrete implementation of an interface it already owns.

### 1.3 Data flow (system-level)

```mermaid
flowchart TB
    subgraph existing["EXISTING, FROZEN AI Intelligence Layer"]
        docs["documents / evidence / extracted_facts /\ncausal_chain_steps / impact_assessments /\ninvestment_implications / self_critique_reviews"]
        extract["extract.py (Steps 1-13)"]
        critique["self_critique.py (Step 14)"]
        ground["grounding.py (mechanical checks)"]
        retr["retrieval.py + context.py"]
        cov["coverage_assessment.py + evidence_ranking.py"]
        orch["reasoning_engine.py orchestrator"]
    end

    subgraph providers["LLMProvider implementations (interchangeable)"]
        gem["GeminiProvider\n(current default, teacher)"]
        lim["LocalLIMProvider\n(new, this initiative)"]
        mock["MockProvider\n(tests only)"]
    end

    subgraph limtrain["NEW: LIM training track (separate from the pipeline above)"]
        export["Dataset export\n(read-only over docs schema)"]
        gold["Human-reviewed gold set"]
        sft["SFT stages 1-4\n(QLoRA, curriculum)"]
        evalh["Eval harness\n(reuses grounding.py + pilot_summary.py methodology)"]
        server["Local inference server\n(llama.cpp, GGUF, OpenAI-compatible)"]
    end

    extract --> ground
    extract --> critique
    retr --> orch
    orch --> cov
    extract -. LLMProvider.complete .-> gem
    extract -. LLMProvider.complete .-> lim
    critique -. LLMProvider.complete .-> gem
    critique -. LLMProvider.complete .-> lim

    docs --> export
    export --> sft
    gold --> sft
    sft --> server
    server --> lim
    gem -. teacher traffic feeds .-> export
    lim -. shadow-mode output .-> evalh
    gem -. baseline .-> evalh
```

The only arrows crossing from "existing, frozen" into the new track are
**read-only exports** (dataset generation reads `extracted_facts`,
`causal_chain_steps`, `investment_implications`, `self_critique_reviews`,
`evidence` — never writes to them) and the **provider seam** (LIM answers
the same `complete()` calls Gemini does today). Nothing else touches the
existing layer.

### 1.4 Why this avoids duplicating functionality

Every capability LIM needs already exists and is reused, not rebuilt:

| Capability LIM needs | Existing component reused | New code needed |
|---|---|---|
| Retrieval-first context | `retrieval.py` / `context.py` | None |
| Structured output schema | `vocab.py` / schema CHECK constraints | None |
| Anti-hallucination check | `grounding.py` | None (LIM's output is checked exactly the same way Gemini's is) |
| Self-critique gate mechanics | `self_critique.py`'s mechanical checks | None — mechanical checks are model-agnostic already |
| Coverage/trust-tier awareness | `coverage_assessment.py` / `evidence_ranking.py` | None |
| Audit trail | `llm_calls` table | None (LIM calls log here identically) |
| Precision/recall/grounding metrics | `pilot_summary.py` methodology | Reused as the eval harness's basis (§6) |
| Provider swap mechanism | `PROVIDER_REGISTRY` / `configs/llm_provider.toml` | One new registry entry |

What's genuinely new: the **training track** (dataset export, SFT,
checkpointing, experiment tracking, the local inference server, and the
eval harness's LIM-specific pieces). Sections 2-6 cover that.

---

## 2. Model strategy

### 2.1 Base model recommendation: Qwen3, primary target size 4B

**Recommendation: Qwen3 (dense), with Qwen3-4B as the primary local
fine-tuning target and Qwen3-8B as a stretch target / first upgrade-path
step.** Comparison against Gemma, Llama, and Mistral, on the axes that
actually matter for this project:

| Axis | Qwen3 | Gemma 3 | Llama 3.x | Mistral (post-shift) |
|---|---|---|---|---|
| License | Apache 2.0, no usage cap | Google's Gemma Terms (permissive, some use restrictions apply) | Meta custom license — permissive but caps at 700M MAU and carries EU-specific restrictions | Apache 2.0 as of the current generation (a change from earlier, more restrictive Mistral licensing) |
| Native context length | 32,768 tokens (base), extendable to 131,072 via YaRN | Shorter native windows at the small end of the family | Varies by version, generally shorter native context at comparable size | Generally shorter native context at comparable size |
| Size lineup (dense) | 0.6B / 1.7B / **4B** / **8B** / 14B / 32B, plus MoE variants — a genuinely graduated ladder within one family/tokenizer | Strong at 4B specifically (notably RAM-efficient, ~4.2GB) but a thinner ladder above that at the sizes this project would use | 1B/3B/8B/70B+ — a bigger jump from 8B to the next usable size | 7B-class strongest option; thinner small-size lineup than Qwen |
| Distinct reasoning feature | Native "thinking" / "non-thinking" mode toggle per call (`enable_thinking`), directly useful (§5.4) | No equivalent toggle | No equivalent toggle | No equivalent toggle |
| Quantization/tooling maturity | Day-one GGUF, AWQ, GPTQ, and Unsloth support (large adoption) | Well supported, slightly smaller ecosystem for the fine-tuning tooling specifically | Very mature ecosystem (oldest, most tooling) | Mature but smaller adoption than Qwen/Llama for fine-tuning tooling |

**Why Qwen3 wins for this project specifically**, not in the abstract:

1. **Context length is a hard requirement, not a nice-to-have.** A real
   document already processed by this platform's Gemini pilot consumed
   35,636 input tokens in a single call (`llm_calls.call_id=38`,
   2026-07-27 validation run). Gemma/Llama/Mistral's native context windows
   at comparable small sizes are generally shorter; Qwen3's 32K native
   (128K+ via YaRN) is the safer fit without immediately depending on
   retrieval-chunking alone to stay in-window (retrieval-first design in
   §5.3 reduces this pressure further, but the base model shouldn't be the
   bottleneck).
2. **License clarity.** Apache 2.0 with no usage cap avoids the Llama
   family's monthly-active-user ceiling and EU carve-outs entirely —
   irrelevant risk to eliminate rather than track, for a platform that may
   eventually run this model as part of a commercial research product.
   (Mistral has closed this gap by also moving to Apache 2.0 — a real
   point in its favor, noted honestly, but its small-size lineup is
   thinner than Qwen3's.)
3. **A genuine same-family upgrade path.** 4B → 8B → 14B → 32B are the
   *same* architecture family, tokenizer, and (largely) training recipe —
   moving up the ladder when better hardware is available is a config
   change (base model + quant settings), not a new integration. This
   directly satisfies the "upgrade path without architectural changes"
   requirement (§2.4).
4. **The thinking/non-thinking toggle maps naturally onto this platform's
   existing two-call structure** (draft extraction vs. self-critique) — see
   §5.4. This is a Qwen3-specific capability none of the alternatives offer
   in the same form.

**Where Gemma is genuinely stronger and should be re-evaluated later:**
Gemma 3 4B's reported ~4.2GB RAM footprint is the single best number for
extreme resource efficiency among the four families at that size. If, after
Phase LIM-2/3 (§7), Qwen3-4B's real on-device footprint or quality proves a
poor fit, Gemma 3 4B is the documented fallback candidate — not a
consolation choice, a legitimate one, held in reserve rather than dismissed.

**Explicit disclosure:** model releases move faster than architecture docs.
By the time Phase LIM-0 (§7) actually starts, a newer Qwen3.x point release
(the ecosystem already shows Qwen3.5/3.6 lineups with larger native context)
may be the better concrete pick. This document fixes the *family and size
class* (Qwen3, ~4B primary), not a specific dated checkpoint — the exact
checkpoint is re-validated as the first concrete decision of Phase LIM-0,
not hard-pinned here.

### 2.2 Quantization strategy

**Training: QLoRA (4-bit NF4 frozen base + bf16 LoRA adapters).** The base
model's weights are quantized to 4-bit (via `bitsandbytes`) and frozen;
gradients and optimizer state only exist for the small LoRA adapter
parameters (rank 8-16 targeting attention + MLP projections). This is the
only fine-tuning approach realistic on 6GB of VRAM — full fine-tuning or
even plain (non-quantized) LoRA on an 4-8B model does not fit.

**Recommended training stack: Unsloth on top of QLoRA**, not vanilla
`peft`/`transformers`. Current published figures put a 9B-class QLoRA
fine-tune's peak VRAM at roughly 6.5GB *with* Unsloth's custom kernels
(vs. the 6-10GB vanilla-QLoRA range reported for 8B models generally,
where 6GB is explicitly flagged as likely insufficient without such
optimization). Concretely for this hardware:

- **Qwen3-4B, QLoRA + Unsloth: comfortably fits** with headroom for a
  reasonable sequence length, batch size 1 + gradient accumulation, and
  gradient checkpointing. This is the **primary, safe local training
  target.**
- **Qwen3-8B, QLoRA + Unsloth: borderline-feasible, not guaranteed.**
  Realistic only with aggressive settings — batch size 1, gradient
  checkpointing on, a paged 8-bit optimizer (PagedAdamW), and a *capped*
  training sequence length (see §2.3 on why full-document training isn't
  the plan anyway). Treated as a **stretch target for Phase LIM-3+**, not
  a Phase LIM-2 commitment.
- **14B and above: not a local-training target on this hardware at all.**
  Reserved for the upgrade path (§2.4) — cloud GPU burst training or a
  future local GPU with materially more VRAM.

**Inference: GGUF (Q4_K_M or Q5_K_M) via llama.cpp**, separate from the
training-time quantization choice. After a LoRA adapter is trained, it is
merged into the base model and exported to GGUF for serving — this is a
one-time offline conversion step per checkpoint, not a training-time
constraint, and lets inference use whichever quant level trades
quality/speed best once real eval numbers exist (§6).

### 2.3 Hardware compatibility: HP Victus 15 (RTX 3050, 6GB VRAM, 16GB RAM)

Concrete implications of this exact hardware, not generic advice:

- **VRAM (6GB) is the binding constraint, not RAM.** The design responds to
  it in three ways: (a) 4-bit QLoRA (§2.2), (b) Unsloth's memory-optimized
  kernels, (c) **training on shorter, retrieval-scale examples rather than
  raw 30K+-token filings.** SFT examples are built at the granularity this
  platform's own retrieval layer already operates at — a located passage +
  its structured output — not "ingest an entire filing end-to-end." A model
  that is only ever asked (at inference time, via the retrieval-first
  design in §5.3) to reason over what's already been retrieved does not
  need to be *trained* on raw whole-document context either. This is a
  direct, load-bearing design choice, not just a memory workaround: it
  keeps training sequence lengths in the low thousands of tokens for most
  of the curriculum (§3.4), which is what actually makes local QLoRA
  training feasible at all on 6GB, independent of which model size is used.
- **16GB system RAM** is adequate for data loading, tokenization, and the
  4-bit base model's CPU-side footprint (a few GB) with headroom for the OS
  and other processes — not a binding constraint at the 4B/8B scale, but
  would become one if any CPU-offload fallback were ever needed for a
  larger model; flagged, not currently a blocker.
- **Batch size 1 with gradient accumulation** (effective batch 8-16) is the
  expected operating point throughout; this is normal for QLoRA on
  consumer GPUs and does not compromise training quality, only wall-clock
  time.
- **Inference (post-training) is comfortably lighter than training** — a
  4-bit GGUF 4B/8B model for serving fits well within 6GB with room for a
  reasonable context window, since inference needs no gradients/optimizer
  state at all.

### 2.4 Upgrade path to larger GPUs, without architectural changes

Because the model family (Qwen3), the training method (QLoRA via
Unsloth/peft), the dataset format, and the inference serving path
(GGUF/llama.cpp with an OpenAI-compatible endpoint) are all **size
-independent choices**, moving to a bigger GPU changes exactly three
things, none of which touch pipeline code:

1. `base_model` config value: `Qwen3-4B` → `Qwen3-8B` → `Qwen3-14B` → `Qwen3-32B`.
2. Quantization/training config: less aggressive settings become optional
   (larger batch size, longer max sequence length, full LoRA instead of
   QLoRA, eventually full fine-tuning if ever justified) — all config,
   never code.
3. Training location: local GPU → a rented cloud GPU for a training burst,
   still producing the same artifact shape (a LoRA adapter + merged GGUF)
   that the local inference server consumes identically either way. This
   makes "train on rented hardware, run locally" a fully supported hybrid
   mode from day one, not a future re-architecture — a real, disclosed
   option for whenever 8B+ local training proves too tight in practice.

No change to `LocalLIMProvider`, the dataset schema, the eval harness, or
any pipeline file is implied by any of the above.

---

## 3. Training strategy

### 3.1 SFT pipeline (overview)

Standard QLoRA supervised fine-tuning loop: 4-bit base model (frozen) +
LoRA adapters (trainable) via Unsloth, trained on JSONL instruction/response
pairs exported per §4, validated against a held-out split, checkpointed
per §3.5. No RLHF/DPO/RL stage is in scope for this design — SFT only,
consistent with "do not introduce training code" for this pass and with
keeping the first working version as simple as the platform's own
"smallest thing that works, extend deliberately" convention throughout
Phases A-F.

### 3.2 Synthetic dataset generation FROM the existing reasoning engine

This is the platform's single biggest structural advantage for this
initiative and the design leans on it directly: **Gemini's real, already
-running teacher traffic already produced labeled training examples.** The
18 real `investment_implications` rows (and their `extracted_facts`,
`causal_chain_steps`, `impact_assessments`, `self_critique_reviews`) that
exist in the database today did not need to be specially generated — they
are the byproduct of the platform already working. Dataset generation is
therefore an **export**, not a synthesis process:

- Every `extracted_facts` row with `model_id IS NOT NULL AND grounding_check
  = 'passed'` → a (document passage, structured extraction) instruction
  pair for the Financial Reasoning dataset (§4).
- Every `self_critique_reviews` row → a (draft claim, critique question,
  finding+explanation) pair for the Self-Critique dataset — **including
  `fail`/`concern` rows as much as `pass` rows.** The real CILEASING case
  from the 2026-07-27 validation run (implication blocked on a genuine
  `insufficient_information` fail) is exactly the kind of hard negative
  example a model needs to see to learn when to say "not enough evidence,"
  not just how to sound confident.
- Every `investment_implications` row with `contradicts_implication_id` or
  `corroborates_implication_id` set, plus every `evidence_ranking.
  assess_implication_conflict` disagreement case (stabilization pass,
  2026-07-27) → the Contradiction dataset (§4) — teaching the model to
  reason explicitly about conflicting evidence, including the specific
  "higher stated confidence ≠ higher trust tier" pattern the platform can
  now detect mechanically.

This keeps dataset growth genuinely coupled to the platform's own usage —
every future real document processed by Gemini adds a training-example
candidate automatically, at zero additional engineering cost.

### 3.3 Human-reviewed gold datasets

A smaller, hand-verified subset — an analyst spot-reviews a sample of
teacher outputs and corrects factual/reasoning errors — becomes: (a) the
**held-out evaluation set**, never trained on until the final curriculum
stage, and (b) a small **gold fine-tuning set** used only in the last
curriculum stage (§3.4) as a "polish" pass. This mirrors the platform's
existing tiered-trust philosophy (exchange-official data at confidence 0.9
vs. aggregator data at 0.5, in the quant data layer) applied to *training
data* trust instead: teacher-generated examples are the bulk (a lower,
still-useful trust tier), gold-reviewed examples are the top tier, used
sparingly and last.

### 3.4 Curriculum learning stages

Each stage trains (or continues training) a LoRA adapter, gated by an
eval-set check before advancing — the same "show the phase's output,
confirm, then proceed" discipline this project has used since Phase A:

1. **Stage 1 — Instruction-following + schema adherence.** Highest volume,
   easiest, can include templated/schema-fuzzed synthetic examples on top
   of real ones. Goal: the model reliably emits valid JSON matching
   `vocab.py`'s enums, nothing about reasoning quality yet.
2. **Stage 2 — Grounded fact extraction + citation.** Real
   `extracted_facts`/`evidence` pairs. Goal: quotes are verbatim,
   `numeric_value`/date fields are correctly pulled, matching Phase B's own
   95%-type validation bar philosophy.
3. **Stage 3 — Causal reasoning + impact assessment.** Real
   `causal_chain_steps`/`impact_assessments`/`investment_implications`
   (Steps 1-13 full shape). Goal: precision/recall vs. the same Phase B
   ground truth already used to score Gemini (90.0%/100.0% today) —
   directly comparable numbers.
4. **Stage 4 — Self-critique (adversarial).** Trained as its own adapter
   (or a continued stage with a distinct system prompt), using contrastive
   pass/fail/concern examples. Goal: reproduce the platform's own known
   real disagreements (e.g., does the model also fail the CILEASING case on
   `insufficient_information`?) — a genuine regression-style target, not an
   abstract quality score.
5. **Stage 5 — Gold-reviewed polish + contradiction/evidence-ranking.**
   Smallest, highest-trust dataset; incorporates the contradiction dataset
   (§3.2) and analyst corrections. Last, deliberately, so it has the
   largest per-example influence on the final adapter.

### 3.5 Checkpointing, resumability, experiment tracking, evaluation

- **Checkpointing:** save adapter weights + optimizer state every N steps
  to a versioned directory (`lim_training/checkpoints/<run_id>/step_<n>/`),
  each with a small sidecar JSON (step, epoch, eval-set loss, dataset
  version hash, base model + revision, LoRA config, git commit of the
  training code). Mirrors `pipeline_status.py`'s own rule: **the status/
  metadata file is a fast signal, never trusted alone** — a resume always
  re-validates that the checkpoint's weights actually load and match the
  recorded config before continuing, the same "don't trust a status row
  that might be stale from a crash" discipline already proven out in
  `pipeline_status.should_skip()`.
- **Experiment tracking:** a lightweight, **local-only**, append-only run
  registry (a small SQLite table or JSONL log — deliberately not a new
  external dependency like W&B/MLflow, since the long-term goal is a fully
  local model and the platform already prefers small self-built tooling
  over heavy frameworks, as seen throughout `scripts/`). Each row: run_id,
  timestamp, base_model, dataset_version, LoRA config, hyperparameters,
  final eval metrics, git commit hash. This is a genuinely separate
  registry from the quant engine's `data/registry.sqlite` hypothesis
  ledger — different domain, not to be conflated — but explicitly modeled
  on the same "immutable, append-only, never silently overwritten"
  principle that ledger already established.
- **Evaluation, during training:** held-out split loss/accuracy per
  checkpoint, used only to pick which checkpoint advances to the next
  curriculum stage — the *real* evaluation (grounding, citation accuracy,
  precision/recall vs. Gemini) happens in the dedicated eval harness (§6),
  run less frequently (per-stage, not per-checkpoint) since it's more
  expensive (runs actual inference through the local server).

---

## 4. Dataset architecture

Every dataset below is generated by a **read-only export** over the
existing schema — no new tables, no writes to the AI Intelligence Layer.
Exports are versioned JSONL files under `lim_training/datasets/<name>/<version>/`.

| Dataset | Source (existing schema) | Format | Curriculum stage | Notes |
|---|---|---|---|---|
| **Instruction** | Templated schema-adherence examples + real prompts from `prompts.py` | (system, user, JSON response) | 1 | Includes deliberately-fuzzed/invalid inputs so the model learns to degrade gracefully (matches `extract.py`'s own `_safe_enum` downgrade behavior — the model should learn the SAME safe-default posture the pipeline already enforces mechanically) |
| **Financial reasoning** | `extracted_facts` (`model_id IS NOT NULL`) + `causal_chain_steps` + `impact_assessments`, joined to `documents.text_path` | (document passage, structured extraction) | 2-3 | The core dataset; grows automatically with every real document Gemini processes |
| **Self-critique** | `self_critique_reviews`, all `finding` values including `fail`/`concern` | (draft implication, critique question, finding + explanation) | 4 | Hard negatives (real blocks) are high-value, not filtered out |
| **Contradiction** | `investment_implications.contradicts_implication_id`/`.corroborates_implication_id` + `evidence_ranking.assess_implication_conflict` disagreement cases | (two implications, evidence trust tiers, correct preference + rationale) | 5 | Directly built on the stabilization pass's new trust-tier-aware conflict logic |
| **Investment decision** | `investment_implications`'s direction/magnitude/duration_bucket/action_recommendation/bull-bear-base fields | (facts + context, decision fields) | 3-5 | **Labels must be framed as "what a disciplined analyst would flag for further research," never as investment advice** — inherits the platform's non-negotiable Discovery-candidate-only framing; this framing is part of the label text itself, not an afterthought |
| **RAG (multi-fact synthesis)** | `retrieval.py`/`context.py` outputs paired with `reasoning_engine.ReasoningResult` | (query, retrieved context set, synthesized grounded answer) | 5 (hardest — requires reasoning across multiple already-retrieved facts, a genuinely different skill from single-document extraction) | |
| **Citation-grounding** | `evidence` rows + `extracted_facts.grounding_check`, including the real grounding-FAILURE rows already on record (fact_id 147/148) | (claim, candidate quote, verdict: grounded/not-grounded) | 2 | Negative examples (real grounding failures) are as important as positive ones — teaches the model to recognize when it *can't* find support |

All exports are validated by a script that reuses `grounding.py`'s checks
directly (never re-implements them) before a dataset version is considered
usable for training — the same "don't just trust the source, re-verify
mechanically" discipline the stabilization pass's `_fresh_grounding_reverify`
already established.

---

## 5. Inference architecture

### 5.1 Local inference server

**Recommendation: `llama.cpp`'s built-in server (`llama-server`)**, not a
Python-wrapped alternative, and not vLLM. Rationale specific to this
environment: `llama-server` ships an OpenAI-compatible `/v1/chat/completions`
endpoint out of the box, has mature Windows+CUDA builds
(`-DGGML_CUDA=ON`), and is the standard consumer-GPU serving choice —
vLLM's tooling and performance advantages are aimed at datacenter-class
multi-GPU Linux deployments, not a 6GB laptop GPU on Windows. Runs as a
separate local process (`llama-server --model <gguf> --port 8080`),
decoupled from the Python reasoning pipeline's process entirely.

### 5.2 Model provider abstraction

`LocalLIMProvider(LLMProvider)` — a thin HTTP client to `llama-server`'s
OpenAI-compatible endpoint, implementing exactly the same `.complete()`
contract `GeminiProvider` and `MockProvider` already implement. Registered
in `PROVIDER_REGISTRY["local_lim"]`, selected via
`configs/llm_provider.toml`. Because the endpoint is OpenAI-compatible,
the client code is genuinely small — request/response shape translation,
timeout/retry handling (reusing `cache.py`'s existing retry wrapper
pattern), and `model_id`/token-count population for the `llm_calls` audit
row exactly as `GeminiProvider` does today.

### 5.3 Retrieval-first workflow

No new retrieval mechanism. `retrieval.py`/`context.py` are reused
unchanged — `LocalLIMProvider` only ever receives what
`build_reasoning_context`/`retrieve_documents` already narrowed down,
identically to how `GeminiProvider` is used today. This is precisely why
LIM's training data (§3-4) is built at retrieval-passage scale rather than
whole-document scale: production-time LIM will never be asked to process
significantly more context than that, and training on realistic-shape
context is both more feasible (§2.3) and more representative of the actual
inference workload than raw-document training would be.

### 5.4 Conversation memory

Not present in today's pipeline (every existing call is stateless,
per-document or per-fact). A future interactive "ask about this company"
surface needs a bounded, **explicitly session-scoped** memory object:

```
LIMConversationSession:
    ticker, as_of
    turns: list[{question, answer, cited_row_ids}]   # bounded window,
                                                       # oldest turns dropped
```

**Hard rule, stated explicitly because it's easy to get wrong:**
conversation memory is ephemeral and session-scoped only. It is never
persisted into any table the reasoning pipeline treats as evidence-grade —
a user's chat turn is not a citable source, and nothing in a conversation
session may ever be written into `evidence`/`extracted_facts`/
`investment_implications`. This preserves the platform's evidence-grade
discipline exactly the way `industry_reasoning.py`'s propagated
implications (Phase F) are kept `status='under_review'` rather than
silently treated as equal to a directly-evidenced row.

### 5.5 Reasoning mode vs. extraction mode

Qwen3's native `enable_thinking` toggle maps directly onto the pipeline's
existing two-call structure, and this mapping is a deliberate design choice
enabled specifically by the model recommendation in §2.1:

| Pipeline call | Mode | Why |
|---|---|---|
| `extract.py`'s draft extraction (Steps 1-13) | **Extraction mode** (`enable_thinking=False`) | Structured, mostly-deterministic JSON output; speed matters more than deliberation on a 6GB card; the causal-chain reasoning is already scaffolded by the prompt's own step structure, not free-form chain-of-thought |
| `self_critique.py`'s Step 14 gate + any future conversational Q&A | **Reasoning mode** (`enable_thinking=True`) | Adversarial critique and multi-fact synthesis benefit from genuine deliberation; this is the SEPARATE model call the spec already requires to be independent from the drafting call (§14 design), so paying the extra latency/compute cost only here, not on every extraction call, is a natural fit |

---

## 6. Evaluation framework

Every metric below is measured **against the same real, already-established
Gemini teacher baseline** (90.0% precision / 100.0% recall vs. Phase B
ground truth, 100% grounding + citation integrity on live re-verification,
22.2% self-critique rejection rate — all from the 2026-07-27 stabilization
validation) so LIM's numbers are directly comparable, not evaluated in a
vacuum.

| Metric | Method | Reused from |
|---|---|---|
| Hallucination rate | Fraction of claims with no supporting quote, or `grounding_check='failed'` | `grounding.py` (unchanged, model-agnostic) |
| Grounding accuracy | Fresh, live re-verification of every quote against on-disk source text (never trust a stored flag alone) | `validate_stabilization_e2e.py`'s `_fresh_grounding_reverify` methodology |
| Citation accuracy | Evidence row resolves, `doc_id` matches the citing fact's own document | `validate_stabilization_e2e.py`'s `_citation_integrity` methodology |
| Financial reasoning quality | (a) mechanical proxies — reuse `self_critique.py`'s own `unevidenced_inference`/`correlation_vs_causation` checks as automated signals; (b) periodic human rubric review on the gold set (cannot be fully mechanized — disclosed honestly, not faked as a single number) | `self_critique.py` mechanical checks (a); new rubric process (b) |
| Self-critique effectiveness | Regression-style replay: does LIM's own Step-14 gate reproduce the platform's known real blocks (e.g. the CILEASING `insufficient_information` fail)? | New eval script, same DB rows as ground truth |
| Investment usefulness | Deliberately qualitative and low-frequency — owner/analyst side-by-side review of LIM vs. Gemini outputs on the same real documents. Not assigned a synthetic numeric score — matches the platform's "never fabricate confidence" rule applied to model evaluation itself | New process, not automated |
| Latency / GPU memory / throughput | Wall-clock per call, peak VRAM during inference, tokens/sec — measured via the local server's own stats plus a wrapping timer | Same shape as `llm_calls.latency_s` already tracked |

**Gating criterion for any provider-default change:** LIM must match the
Gemini baseline within an owner-agreed tolerance across *every* row above
before it is even considered as a swappable option — and even then, a
default-provider change is a disclosed, deliberate config edit with its own
review, exactly like the Anthropic→Gemini precedent, never an automatic
cutover triggered by a passing eval run.

---

## 7. Roadmap

Every phase below follows the same gate this project has used since Phase
A: **Design → Implementation → Testing → Documentation → Review**, with an
explicit stop for owner approval before the next phase starts. Nothing
below begins until this document itself is approved.

**Phase LIM-0 — Environment & tooling validation (no training).**
Verify local CUDA/driver/GPU setup; install `llama.cpp` (built + CUDA),
`peft`/`bitsandbytes`/`unsloth`; download an off-the-shelf (not fine-tuned)
Qwen3-4B GGUF; run it through `llama-server`; implement the smallest
possible `LocalLIMProvider` stub and confirm the existing pipeline
(`extract.py` unchanged) produces a real, if not yet fine-tuned, result
through the exact same code path Gemini uses. De-risks all infrastructure
before any training investment. **Confirms/updates the exact Qwen3.x
checkpoint choice per §2.1's disclosure.**

**Phase LIM-1 — Dataset export pipeline.**
Read-only exporters producing the seven dataset types (§4) as versioned
JSONL, each validated against `grounding.py`'s mechanical checks. No
training. Output: a dataset completion report (row counts per type, same
class of `reports/phase_*.md` convention) for owner review.

**Phase LIM-2 — SFT Stage 1 (instruction-following + schema adherence).**
Smallest, safest first real training run on Qwen3-4B; establishes the
training loop, checkpointing, and experiment-registry infrastructure (§3.5).
Eval: does output parse as valid, schema-conformant JSON — nothing about
reasoning quality yet.

**Phase LIM-3 — SFT Stage 2 (grounded fact extraction + citation).**
Trains on the Financial-reasoning + Citation-grounding datasets. Eval:
grounding/citation accuracy vs. the Gemini baseline (§6), on held-out real
documents.

**Phase LIM-4 — SFT Stage 3 (causal reasoning + impact assessment).**
Full Steps 1-13 shape. Eval: precision/recall vs. Phase B ground truth,
directly comparable to Gemini's measured 90.0%/100.0%.

**Phase LIM-5 — SFT Stage 4 (self-critique, adversarial).**
Separate adapter/stage for the Step-14 role, trained on contrastive
pass/fail/concern examples. Eval: self-critique effectiveness regression
(§6) against known real teacher blocks.

**Phase LIM-6 — Gold-reviewed polish + contradiction/evidence-ranking.**
Incorporates human-reviewed corrections and the Contradiction dataset. Eval:
full §6 suite against the held-out gold set.

**Phase LIM-7 — Local inference server + `LocalLIMProvider` productionization.**
Merge final adapters into the base model, export GGUF, deploy via
`llama-server`, implement the full provider (§5.1-5.2) plus the
reasoning/extraction mode switch (§5.5) and the conversation-memory
scaffold (§5.4, if in scope by then).

**Phase LIM-8 — Shadow-mode A/B evaluation.**
Run LIM *alongside* Gemini (never replacing it) on new real documents;
compare the full §6 metric suite head-to-head over a real trial period;
produce a go/no-go recommendation report. The owner decides whether, and
when, to change the default provider config — never automatic, never
silent, exactly like the existing Gemini swap.

Every phase produces its own `docs/lim_runs/phase_lim_N_completion.md`
report before the next phase is proposed, matching this project's existing
`reports/phase_*.md` convention.

---

## 8. Open decisions flagged for the owner (not resolved by this document)

1. Exact Qwen3.x checkpoint/version to start from (deferred to Phase LIM-0,
   §2.1) — model releases move faster than this document.
2. Whether Phase LIM-3+'s Qwen3-8B stretch target is worth attempting
   locally at all, or whether a short cloud-GPU burst (§2.4's hybrid mode)
   is preferred from the start once 4B curriculum results are in.
3. Local experiment-tracking approach: custom SQLite/JSONL registry
   (recommended, §3.5) vs. adopting an existing tool (e.g. W&B in offline
   mode) — a genuine trade-off between "no new dependency" and "more
   mature tooling," not resolved here.
4. Scope and timing of the conversation-memory feature (§5.4) — this
   document designs it so the architecture doesn't foreclose it, but no
   phase above commits to building it; it may be deferred well past
   Phase LIM-8 depending on whether an interactive surface is prioritized.
5. Financial-reasoning-quality's human-rubric process (§6) — cadence,
   reviewer(s), and rubric specifics are not defined here, only that it
   must exist and must not be faked as a single automated number.

---

## 9. Summary of hard boundaries (restated for emphasis)

- LIM is a `LLMProvider` implementation, nothing more architecturally.
- No schema changes. No changes to `extract.py`/`self_critique.py`/
  `reasoning.py`/`grounding.py`/`retrieval.py`/`context.py`/
  `reasoning_engine.py`/`industry_reasoning.py`/`coverage_assessment.py`/
  `evidence_ranking.py` are implied by anything in this document.
- Training/dataset/eval code lives outside `src/ngxrot/documents/`.
- Dataset generation is read-only over the existing schema.
- LIM never becomes the default provider without an explicit, disclosed,
  tested, owner-approved config change — same bar as the Gemini swap.
- Conversation memory (if ever built) never feeds evidence-grade tables.
- This document authorizes nothing. Phase LIM-0 does not start until it is
  explicitly approved, and each subsequent phase gates the same way.
