# LIM Local Inference Diagnostic — 2026-08-18

*Phase 0 + Phase 1 of `LIM_NARROW_TASK_VALIDATION` — this task's own instruction: "Start with Phase 0
and Phase 1 only." Stops here; no narrow-task dataset work, no baseline, no training. No production
change of any kind was made — this pass only ran read-only diagnostics and local model inference
against scratch/no data.*

---

## Phase 0 — Freeze, confirmed

| Invariant | Result |
|---|---|
| Alpha Engine (`alpha_engine.py`/`engine_full.py`/`runner.py`/`registry.py`) | Zero diff, before and after |
| H-011 | Not touched, not re-run |
| `REASONING_WEIGHT` | `0.0`, confirmed before and after |
| FRE production path | Unchanged |
| Evidence Engine / Statistics Engine | Unchanged |
| Production DB writes | None — `extracted_facts` = 495, unchanged before and after |
| `lim_training/quality_gate_status.json` `passed` | `false`, unchanged |
| Existing regression suite | `scripts/lim/test_local_lim_provider.py` 13/13, re-confirmed clean after the diagnostic below |

No invariant was violated. Proceeded to Phase 1.

---

## Phase 1 — Local inference diagnostic

**A materially different starting condition than the 2026-08-13 audit, found before any test was
run**: Ollama (v0.32.14) is installed on this machine and was not part of the prior audit at all — that
audit only tested the raw `transformers`/`unsloth`/`bitsandbytes` subprocess path
(`LocalLIMProvider`/`verify_checkpoint_inference.py`). Ollama already has `qwen2.5:7b` pulled (a generic
model, unrelated to the fine-tuned LIM checkpoints — useful here purely as an environment probe,
decoupled from any question about LIM's own trained quality). GPU state at the start: 31MiB/6144MiB
used, 3% utilization — clear, unlike the 2026-08-13 state where a concurrent game process held
unreported VRAM.

### Progressive test results (Ollama path, `qwen2.5:7b`)

| Step | Test | Result |
|---|---|---|
| 1 | Tiny prompt (`ollama run`, cold start) | **PASS** — 31.3s (includes model load), correct output |
| 2 | Short context, warm | **PASS** — 3.08s, `prompt_eval_count=32` |
| 3 | Short, constrained generation | **PASS** — 2.93s |
| 4 | Structured JSON output (unit-interpretation-shaped prompt: `"N842,614 million"` → `{currency, scale_word, scale_multiplier}`) | **PASS** — 4.45s, valid JSON, correct values |
| 5 | Moderate context (2,000 real chars from ELLAHLAKES, doc 11122) | **PASS** — 5.36s, correct one-sentence document-type summary |
| 6 | Full financial-document context (ELLAHLAKES, doc 11122, **131,576 real characters / 16,386 real tokens**, `num_ctx=40000`) | **PASS** — 357.72s (~6 min), coherent, on-topic content grounded in the real document (currency/interest-rate/credit-risk sections) — **no hallucinated off-topic content**, unlike the 2026-08-13 finding on the old checkpoint |

Resource check after step 6: GPU 4,163MiB/6,144MiB (68%, real headroom remained — never maxed);
system RAM dropped to 2.19GB free (from 4.86GB at the start) — tight, a real and disclosed constraint,
but did not cause a failure. Ollama itself split the 6.8GB model 39%/61% CPU/GPU automatically
(`ollama ps`) — graceful degradation the raw path does not appear to do.

### Isolated retry of the ORIGINAL crashing path (raw transformers/unsloth, the actual LIM checkpoint)

With the GPU confirmed clear (`ollama stop` run first, `nvidia-smi` re-checked: 31MiB used), re-ran the
**exact, unmodified** `scripts/lim/verify_checkpoint_inference.py` against the **exact, real, previously
best-performing checkpoint** (`8d265e59-.../checkpoint-40`, RB-3b) — the identical script/checkpoint/
hardware combination that produced a `torch.OutOfMemoryError` three times on 2026-08-13.

**Result: PASS.** `base_load_s=6.41`, `adapter_load_s=0.43`, `generation_latency_s=6.063`, real
structured JSON output (`{"fact_type": "dividend_announcement", "description": "...", "numeric_value":
"1.90"}`), `verdict: PASS`.

**This is decisive for root-cause isolation**: same script, same checkpoint, same base model, same
hardware, same library versions — the only thing that changed is GPU contention. This strongly confirms
the 2026-08-13 OOM was caused by **concurrent processes** (the game process reported that day), not by
CUDA/runtime version, quantization config, or a fundamental hardware incapability at small context.

### What was deliberately NOT re-tested, and why

The 2026-08-13 audit also found a **segmentation fault specifically at `max_seq_length=2048`** — a
different failure mode than the small-context OOM, and one the prior audit's own evidence suggests is
context-length-driven, not contention-driven (the OOM was shown to be independent of context length at
512–1536; the segfault only appeared once context grew to 2048). `extract_document()` (the real
production entry point `smoketest_extraction.py` exercises) has **no truncation or chunking logic** —
a real document's full text (e.g. ELLAHLAKES's 16,386 tokens) would be passed straight through to a
provider whose raw-path default is `max_seq_length=4096`, i.e. roughly 4x over budget. Per this task's
own explicit instruction ("do not waste time repeatedly reproducing the same crash," "if the environment
cannot reliably run the model, STOP"), this was **not** attempted — the incremental information from
risking a real segfault (which could disrupt more than just this test) was judged low relative to the
risk, especially once Ollama had already proven a full-document-scale call works reliably through a
different, more graceful backend.

---

## Classification

## **B — PARTIALLY USABLE**

Not **A — environment fixed**: the raw transformers/unsloth path's large-context failure mode
(segfault at ≥2048 tokens) was never re-tested and is not shown to be resolved. Claiming full fix would
overstate what was actually verified.

Not **C — hardware-constrained**: the hardware (RTX 3050 6GB) is demonstrably capable of real,
full-document-scale (131K character, 16K token) local inference — proven directly via Ollama, not
theorized. The earlier failures were substantially, not marginally, explained by software/contention
factors, not a hard hardware ceiling.

Not **D — unusable**: directly contradicted by two independent, real, reproducible successes today
(Ollama full-document run; the exact previously-crashing checkpoint script now passing cleanly).

**Precise breakdown, since the two paths behave differently**:

| Path | Small context (unit/period-scale prompts) | Full-document context |
|---|---|---|
| Ollama (`qwen2.5:7b`, generic — environment probe only) | **Proven working** | **Proven working** (6 min latency, disclosed as slow, not a failure) |
| Raw transformers/unsloth (the actual fine-tuned LIM checkpoints) | **Proven working today** (VRAM contention was the real cause, now absent) | **Not tested** — real segfault risk at ≥2048 tokens, deliberately not re-provoked |

**Direct implication for the narrow-task program this diagnostic exists to inform**: all three of
Phase 2's candidate tasks (unit interpretation, period interpretation, document classification) are
naturally **short-input** tasks — a unit label, a period phrase, or (for classification) even a short
document excerpt rather than a full filing, per step 5's successful 2,000-character test. This is
exactly the regime now proven reliable on both paths. Document classification specifically, if it needs
full-document context rather than an excerpt, should route through Ollama (proven at scale) rather than
the raw transformers path (unproven at scale, real crash history) until that path is separately
retested with a bounded/chunked input.

---

## Exact next action (per this task's own scope: stop after Phase 0/1)

Do not proceed to Phase 2 in this same pass — reporting back per the checkpoint structure this task
itself defines. If continuation is authorized: Phase 2 (task definition) and Phase 3 (dataset
construction) can proceed on the strength of §"Classification" above — inference is real and usable for
the short-input shape all three narrow tasks require. Any future full-document-scale raw-transformers
test should be run once, deliberately, with a hard timeout and `max_seq_length` explicitly bounded below
2048 first (e.g. 1536, the highest value confirmed safe on 2026-08-13), stepped up cautiously rather than
jumped straight to a full filing.
