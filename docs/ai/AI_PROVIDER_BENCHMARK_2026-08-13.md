# AI Provider Benchmark — 2026-08-13

**First benchmark run. Evidence collection only. No provider is promoted to
PRIMARY. Nothing here changes production — `configs/llm_provider.toml`
still points at Gemini, and no experimental provider is registered in
`PROVIDER_REGISTRY`.**

---

## 0. Real cost disclosure (checked, not assumed)

Per the standing "do not assume free-tier limits" instruction, I checked
actual account usage rather than assuming $0:

- **OpenRouter**: confirmed via `GET /v1/key` — **$0.028 real spend**,
  this account's entire lifetime usage, all from this run (10 calls,
  `meta-llama/llama-3.3-70b-instruct` — not the `:free` variant). Small,
  but non-zero and real.
- **Cerebras**: billing is enabled on this account (confirmed earlier by
  the 402→200 transition after you resolved it). No usage/billing API
  endpoint was reachable to confirm an exact dollar figure (`/v1/usage`,
  `/v1/billing`, `/v1/account` all 404/405) — **assume non-zero real cost
  and check the Cerebras dashboard directly**, per the same "don't assume
  free" discipline.
- **Groq**: $0 — every call failed before any tokens were billed.
- **Gemini**: $0 — free tier, but see §1, only 1/10 documents completed.

---

## 1. Providers and exact model identities tested

| Benchmark identity | Provider | Requested model | Actual model (from response) |
|---|---|---|---|
| gemini-control | Gemini | `gemini-3.6-flash` | `gemini-3.6-flash` |
| groq-llama-3.3-70b-versatile | Groq | `llama-3.3-70b-versatile` | — (never completed) |
| openrouter-llama-3.3-70b-instruct | OpenRouter | `meta-llama/llama-3.3-70b-instruct` | `meta-llama/llama-3.3-70b-instruct` (matched requested, no silent routing this run) |
| cerebras-gemma-4-31b | Cerebras | `gemma-4-31b` | `gemma-4-31b` |
| cerebras-zai-glm-4.7 | Cerebras | `zai-glm-4.7` | `zai-glm-4.7` |
| cerebras-gpt-oss-120b | Cerebras | `gpt-oss-120b` | `gpt-oss-120b` |

Per your instruction, the Groq and OpenRouter Llama models are recorded as
their own distinct identities — never conflated with each other or with
GPT-OSS-120B. GPT-OSS-120B and GLM-4.7 are Cerebras-hosted, evaluated
separately from the Groq/OpenRouter Llama-70B identities to let this
report speak to both **provider effect** (same model family, different
host: Llama-70B via Groq vs. OpenRouter) and **model effect** (three
different model families on the same host: Cerebras).

## 2. Methodology — identical task, zero provider-specific advantage

Every identity received:
- The exact same `build_draft_prompt()` output (`src/ngxrot/documents/prompts.py`,
  **unmodified**, `DRAFT_PROMPT_VERSION = "financial_reasoning_draft_v3"`)
  — the real production draft-reasoning prompt and JSON schema, not a
  simplified benchmark-only prompt.
- The exact same source document text, ticker, doc_type, filing_date.
- The exact same `max_tokens=16384` — **matching production's own real
  value** (`extract.py:172`), not an arbitrary benchmark number.
- The exact same grading logic (`scripts/ai/grade_benchmark.py`), run
  after the fact against independently-verified ground truth.

All traffic went through `benchmark_complete()` into `benchmark_calls`
(scratch DB copy) — confirmed zero rows written to `llm_calls`,
`extracted_facts`, or `financial_reasoning_conclusions` this run.
Production `extracted_facts=495`, `financial_reasoning_conclusions=403`
unchanged (re-verified after the run). Alpha Engine untouched.

## 3. Benchmark corpus (10 real documents)

Built and independently verified by direct source-text reading, not
derived from any model output — see `scripts/ai/benchmark_gold_set.py`
for every gold value with its exact source-line citation.

| doc_id | Ticker | Sector | Chars | Notable hard case |
|---:|---|---|---:|---|
| 11122 | ELLAHLAKES | Agriculture | 130,892 | **Mandatory regression**: the real ₦'000 defect document from Gate 2 |
| 452 | STANBIC | Bank | 4,565 | True-negative (pure regulatory narrative, zero numeric facts) |
| 9530 | MORISON | Industrial | 1,982 | True-negative (delay-in-filing notice, zero numeric facts) |
| 9485 | TRANSCORP | Conglomerate | 4,482 | ₦-billion prose scale words; the original TRANSCORP 10x prose case |
| 4245 | AFRIPRUD | Insurance | 10,915 | ₦'000 table; **real source-document defect**: reversed comparative-period columns in 2 rows |
| 4508 | CAP | Consumer goods | 8,259 | ₦-million table with BOTH Q4 and FY columns; prose/table EPS discrepancy in the source itself |
| 5163 | UACN | Conglomerate | 26,029 | ₦-million table; continuing vs. discontinued operations |
| 10625 | OANDO | Energy | 34,370 | ₦-**trillion** prose scale; PAT up 10% despite gross profit down 82% (real, non-obvious) |
| 7793 | UBA | Bank | 12,691 | ₦-million table; genuine Q3-vs-9M source-label ambiguity; statement-type-specific comparatives |
| 6393 | MTNN | Telecom | 36,874 | ₦-billion prose scale; ambiguous "N8.92 kobo" unit label in the source text itself |

Two real, pre-existing **source-document data-quality defects** were
found while building ground truth (AFRIPRUD's and CAP's reversed
comparative-period table columns) — these are properties of the original
NGX filings, not artifacts of this benchmark, and are documented in the
gold set with prose cross-checks proving the correct values.

## 4. Results by model identity

*Composite score uses your weights (Extraction 35% / Evidence 25% /
Numerical 15% / Reasoning 10% / Latency 10% / Cost 5%), with a **hard
fail to 0.0** on any catastrophic error or true-negative violation —
speed can never conceal a financial-data error. Reasoning quality is
proxied by structured-output success (no independent reasoning-quality
judge was built this pass — see §8 limitations).*

| Identity | Composite | n runs | Success rate | Structured-output success | Numeric accuracy | Period accuracy | Evidence accuracy | Hallucination rate | Catastrophic errors | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **gemini-control** | 0.968 | 10 | **10%** (1/10) | 100% | 80% (4/5) | 100% (2/2) | 100% (4/4) | 0% | 0 | 1.2s |
| **cerebras-gemma-4-31b** | 0.940 | 10 | 90% (9/10) | 100% | 71% (24/34) | 79% (22/28) | 97% (38/39) | 2.6% (1/39) | 0 | 5.4s |
| **cerebras-gpt-oss-120b** | 0.884 | 10 | 90% (9/10) | 100% | 62% (21/34) | 68% (19/28) | 79% (30/38) | **21% (8/38)** | 0 | 3.9s |
| **openrouter-llama-3.3-70b-instruct** | 0.701 | 10 | **100% (10/10)** | 80% (8/10) | 61% (17/28) | 62% (13/21) | 80% (16/20) | 18% (4/22) | 0 | 86.0s |
| **cerebras-zai-glm-4.7** | 0.611 | 10 | 90% (9/10) | **33% (3/9)** | 60% (3/5) | 60% (3/5) | 100% (6/6) | 0% | 0 | 17.4s |
| **groq-llama-3.3-70b-versatile** | 0.149 | 10 | **0% (0/10)** | N/A | N/A | N/A | N/A | N/A | 0 | — |

**Zero catastrophic errors (1,000×/1,000,000× scaling, wrong entity,
consolidated/standalone confusion) across every model that produced any
scoreable output.** This is a genuinely positive structural finding: the
shared v3 prompt's explicit unit-scale instruction appears to generalize
beyond Gemini.

*(Two apparent "catastrophic period errors" were found and traced during
grading to bugs in my own gold set / matching logic, not model
failures — corrected before this table was produced: AFRIPRUD's
document self-labels its period "Q3" even though it is calendar-YTD in
substance, which I'd gold-coded as "9M" only; and CAP's Q4/FY revenue
columns share the same `period_end` (both end 31 Dec), which my matcher
initially conflated. Both fixed in `grade_benchmark.py` before scoring —
flagging this openly since "measure, don't assume" cuts both ways.)*

## 5. The mandatory ELLAHLAKES regression case

**Only one model produced any live result at all on this document**:
Gemini, Groq, and all three Cerebras identities failed before reaching a
usable response — Gemini and Groq on quota/tier limits, Cerebras on its
per-minute token cap (ELLAHLAKES is by far the largest document, 130,892
chars). **OpenRouter (Llama 3.3 70B) is the only live evidence this
benchmark has on the actual defect document**:

```
revenue     146,658,000   (gold: 146,658,000)  -- EXACT MATCH, correct ×1000 scale applied
assets   28,257,351,000   (gold: 28,257,351,000) -- EXACT MATCH, correct ×1000 scale applied
net_profit  -3,856,655,000 (gold: -3,839,656,000) -- correct MAGNITUDE/scale, ~0.4% off
                                                     (likely picked a neighboring column in
                                                     a multi-period table, not a scale error)
liabilities  -- not returned (recall miss, not a wrong value)
```

**This is a real, meaningful result**: OpenRouter's Llama 3.3 70B
correctly applied the ₦'000 table-header scale on live data, on the exact
document that caused the original defect. It is one data point, not
proof of general reliability, but it is the only live evidence this
benchmark produced on the case that matters most.

## 6. Failure taxonomy

| Failure mode | Who | Root cause |
|---|---|---|
| **Structural token-budget rejection (413)** | Groq, all 10/10 docs | Groq's on-demand tier caps at 12,000 tokens/minute; this task's `max_tokens=16384` alone exceeds that, independent of document size. Not a document-size problem — even the smallest document (1,982 chars) failed identically. |
| **Daily request quota (429)** | Gemini, 9/10 docs | Free-tier cap of 20 requests/day for `gemini-3.6-flash`, already partially consumed by earlier work today. Only the 4th call in this run (AFRIPRUD) succeeded before exhaustion. |
| **Per-minute token quota (429)** | Cerebras (all 3 identities), ELLAHLAKES only | Cerebras' per-minute token cap, hit specifically on the one 130k-char document — every other document on Cerebras succeeded. |
| **Unparseable structured output** | Cerebras zai-glm-4.7, 6/9 completed docs; OpenRouter, 2/10 docs | GLM-4.7 consistently spends 11,000-16,000 output tokens on internal `reasoning` before/instead of the JSON payload, frequently exhausting the 16,384 budget before any parseable JSON is produced — a genuine model/schema-shape mismatch, not a harness bug (confirmed via raw response inspection). |
| **Elevated hallucination rate** | Cerebras gpt-oss-120b (21%), OpenRouter (18%) | Facts with a stated `numeric_value` but no verbatim-quotable `quoted_evidence`, or a quote that doesn't actually appear in the source text — i.e., real fabrication, not a grading artifact (each flagged case was individually checked against `check_grounding()`, the same function production's own anti-hallucination gate uses). |

## 7. Token usage and cost (successful calls only)

| Identity | Successful calls | Total input tokens | Total output tokens | Real $ cost |
|---|---:|---:|---:|---:|
| openrouter-llama-3.3-70b-instruct | 10 | 88,546 | 26,604 | **$0.028 confirmed** (§0) |
| cerebras-gemma-4-31b | 9 | 64,872 | 52,475 | non-zero, not independently confirmed (§0) |
| cerebras-zai-glm-4.7 | 9 | 58,469 | **100,217** | non-zero, not independently confirmed — note the output-token count relative to only 3/9 successful parses: most of this spend produced no usable output |
| cerebras-gpt-oss-120b | 9 | 57,644 | 50,907 | non-zero, not independently confirmed |
| gemini-control | 1 | 5,684 | 6,715 | $0 (free tier) |
| groq-llama-3.3-70b-versatile | 0 | — | — | $0 (no call ever billed) |

**Quota constraints observed directly, not assumed**: Gemini free tier =
20 requests/day (hard cap, hit mid-run); Groq on-demand tier = 12,000
tokens/minute (structurally incompatible with this task's shape);
Cerebras = a per-minute token cap large enough for every document except
the 130k-char outlier. A model with $0 marginal cost but a request/token
cap this restrictive has materially worse practical throughput than a
paid alternative that actually completes the batch — exactly the
distinction Phase 8 asked not to collapse.

## 8. Reproducibility and limitations (stated plainly)

- **Gemini's 0.968 composite score is built on a single successful
  document (n=1).** It should not be read as "Gemini is the best
  provider" — it is "Gemini did well on the one case it got to run,"
  which is a much weaker claim. A second run (once quota resets) is
  required before this identity's score means anything comparable to the
  others' 9-10 case averages.
- **No independent reasoning-quality judge was built this pass** —
  "reasoning quality" in the composite score is proxied by
  structured-output success, which conflates "the model reasoned well"
  with "the model's JSON parsed." A real reasoning-quality dimension
  (e.g., a second-pass grader checking causal-chain/impact-assessment
  coherence) is future work, not built speculatively here.
- **OpenRouter's actual-served-model matched the requested model on every
  call this run** — no silent substitution was observed, but this is one
  run; the mechanism (recording `resp.model_id` from the response, not
  the request) remains in place for future runs where it might differ.
- **Cost figures are incomplete for Cerebras** — no usage API was
  reachable; only OpenRouter's cost is independently confirmed.
- **Small per-document fact counts** (gold sets of 4-6 facts per
  document) mean single-document numeric/period accuracy is noisy;
  aggregate percentages above pool across all 9-10 documents per identity
  specifically to reduce (not eliminate) this noise.
- **A second validation run is required before any promotion decision**,
  per your own instruction — this is evidence collection, not a verdict.

## 9. Provider vs. model effect

- **Same model family, different host** (Llama 3.3 70B): Groq never
  completed a single call (structural tier limit); OpenRouter completed
  100% of calls but slowly (median 86s, up to 867s on the largest
  document) and with real (if small) per-call cost. This is a clean
  **provider effect** — identical model, materially different practical
  usability.
- **Same host, different models** (Cerebras: Gemma-4-31B, GLM-4.7,
  GPT-OSS-120B): Gemma-4-31B and GPT-OSS-120B both completed 9/10 docs
  reliably with very different hallucination rates (2.6% vs 21%); GLM-4.7
  completed 9/10 but only produced parseable output on 3 — a clean
  **model effect** on the identical host/infrastructure.
- Per your instruction: **no provider superiority claim is made from
  this.** Groq's failure here is a tier/task-shape mismatch, not
  evidence Groq's underlying models are worse — a Groq account on a
  higher tier, or a task with a smaller `max_tokens` budget, could behave
  entirely differently. This is recorded as a **capacity finding about
  this specific account+task combination**, not a model-quality verdict.

## 10. Leaderboard (evidence, not a ranking to act on)

1. cerebras-gemma-4-31b — 0.940 (real n=9, no catastrophic errors, low hallucination, moderate recall)
2. cerebras-gpt-oss-120b — 0.884 (real n=9, no catastrophic errors, but notably high hallucination rate)
3. openrouter-llama-3.3-70b-instruct — 0.701 (only 100% completion rate including the mandatory ELLAHLAKES case, but slow and moderate hallucination)
4. cerebras-zai-glm-4.7 — 0.611 (structurally unreliable output format on this schema)
5. groq-llama-3.3-70b-versatile — 0.149 (never completed a call; task-shape/tier mismatch)
6. gemini-control — 0.968 but **n=1, not comparable** — see §8

## 11. Recommendation

**KEEP ALL EXPERIMENTAL. No promotion.**

This satisfies none of the Phase 11 promotion gate's own questions yet:
Gemini's control comparison has too little live data this run (n=1) to
say any experimental provider is "at least as accurate," no provider has
been through a second validation run, and Cerebras's real per-call cost
is unconfirmed. The one clear, actionable finding is that **Groq, as
currently configured (this account tier + this task's `max_tokens`
budget), cannot serve this workload at all** — not a quality judgment,
a capacity fact. `cerebras-gemma-4-31b` is the strongest candidate for a
second validation run given today's evidence (highest real-sample
composite score, zero catastrophic errors, lowest hallucination rate
among providers with a meaningful sample size) — but per your own
instruction, one run's lead does not earn promotion.

**Next exact step, if you want it**: a second, independent run of this
same benchmark (same documents, same prompt, same gold set) once Gemini's
daily quota resets, specifically to get Gemini a comparable n and to
confirm `cerebras-gemma-4-31b`'s lead is not a one-run artifact — not
starting automatically, since Phase 3 was scoped as "the first
benchmark," and repeating it is a new authorization, not a continuation.
