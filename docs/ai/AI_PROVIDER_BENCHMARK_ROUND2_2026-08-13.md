# AI Provider Benchmark — Round 2 — 2026-08-13

Second independent run, same gold-standard set (10 documents), same
`build_draft_prompt()` (unchanged, `financial_reasoning_draft_v3`), same
extraction schema, same `grade_benchmark.py` grading logic as Round 1
(`docs/ai/AI_PROVIDER_BENCHMARK_2026-08-13.md`). Purpose: increase
statistical confidence, not declare a winner. **No provider promoted.**

---

## 1. Provider/model matrix — what actually ran

| Identity | Task condition | n attempted | n succeeded |
|---|---|---:|---:|
| cerebras-gemma-4-31b | standard, max_tokens=16384, same as R1 | 10 | 4 |
| openrouter-llama-3.3-70b-instruct | standard, max_tokens=16384, same as R1 | 10 | 10 |
| gemini-control | standard — **single probe attempt only**, per instruction not to poll | 1 attempted, 9 skipped | 0 |
| cerebras-gpt-oss-120b | standard, max_tokens=16384, same as R1 | 10 | 3 |
| groq-llama-3.3-70b-versatile-REDUCED-BUDGET | **NOT the same task** — per-document reduced `max_tokens` computed from Round 1's real request-size telemetry, to fit inside the confirmed 12,000 TPM cap; 2 documents (MTNN, ELLAHLAKES) skipped outright as mathematically infeasible; UACN/OANDO also skipped (margin too thin) | 8 attempted, 2 skipped | 1 (structurally; output unusable) |
| cerebras-zai-glm-4.7 | **not run this round** — not in this round's authorized priority list | 0 | 0 |

Per your instruction: **no silent substitution.** Every skipped/blocked
case is recorded with an explicit reason (see §5), not omitted or
replaced with a different model.

## 2. Real cost this round

- **OpenRouter**: checked via `GET /v1/key` again — cumulative account
  usage now **$0.057** (up from $0.028 after Round 1), confirming ~$0.029
  real spend this round specifically.
- **Cerebras**: still no reachable usage/billing endpoint; real cost is
  non-zero (billing enabled) but not independently confirmed, same
  caveat as Round 1.
- **Groq**: $0 (only 1/10 calls ever completed; output was empty/unusable).
- **Gemini**: $0 (single probe call, rejected before any token billing).

## 3. Per-document results, by identity

### cerebras-gemma-4-31b (4/10 succeeded)
STANBIC ✅ (0 facts, correct true-negative), MORISON ✅ (0 facts, correct
true-negative), TRANSCORP ✅ (5 facts, structured_ok), UBA ✅ (4 facts,
structured_ok). **AFRIPRUD, CAP, UACN, OANDO, MTNN, ELLAHLAKES all failed
on Cerebras's per-minute token cap** — not because any single document
was too large (AFRIPRUD and CAP are small/medium docs that succeeded
individually in Round 1), but because Round 2 fires all 10 requests to
the same provider back-to-back, and the rolling 60-second TPM window
compounds across consecutive calls in a way Round 1's naturally
interleaved (across-provider) request pattern did not trigger nearly as
often. **This is a new, real operational-reliability finding Round 1
could not have surfaced.**

### cerebras-gpt-oss-120b (3/10 succeeded)
STANBIC ✅ (0 facts, correct true-negative), MORISON ✅ (0 facts, correct
true-negative), TRANSCORP ✅ (5 facts). Same TPM-window compounding
failure on the remaining 7 documents.

### openrouter-llama-3.3-70b-instruct (10/10 completed, 7/10 parsed)
Every document got a response this round (no hard failures), but
**MORISON, UACN, and ELLAHLAKES came back with unparseable output**
(`structured_output_success=False`) despite consuming real output tokens
(1,251 / 1,182 / 3,056 respectively) — the model produced text, just not
valid JSON matching the schema. Latency was markedly worse than Round 1
(median 134.3s vs 86.0s; TRANSCORP alone took 314.4s this round vs 63.7s
in Round 1) — consistent with a shared/rate-limited free-tier backend
whose responsiveness varies call-to-call, not something this benchmark
controls.

### gemini-control (0/10 — quota probe failed, correctly not polled further)
The single probe call (STANBIC) returned the same daily-quota 429 as
every Round 1 call after the first. Per instruction, the remaining 9
calls were **not attempted** — recorded as skipped with an explicit
reason, not silently treated as failures of the model itself.

### groq-llama-3.3-70b-versatile-REDUCED-BUDGET (1/10 structurally completed, 0/10 usable)
STANBIC completed (934 output tokens) but `structured_output_success=False`
— no usable extraction. Every subsequent attempt (MORISON onward) hit a
**rolling-window rate limit** ("Used 11,803, Requested 11,700" — the
account's TPM budget was already consumed by the STANBIC call moments
earlier), even though each individual request was correctly sized under
12,000 tokens in isolation. UACN, OANDO, MTNN, ELLAHLAKES were not
attempted at all — their prompt tokens alone leave under 500 tokens of
usable budget under the cap, confirmed mathematically from Round 1's
telemetry rather than re-tested live.

## 4. Round 1 vs Round 2 comparison

| Identity | Metric | Round 1 | Round 2 | Direction |
|---|---|---:|---:|---|
| cerebras-gemma-4-31b | composite | 0.940 | 0.953 | stable |
| | success_rate | 90% | **40%** | ⬇ operational reliability, not quality |
| | numeric_accuracy | 70.6% | 70.0% | stable |
| | evidence_accuracy | 97.4% | 100% | stable/improved |
| | hallucination_rate | 2.6% | 0.0% | stable/improved |
| cerebras-gpt-oss-120b | composite | 0.884 | 0.938 | stable |
| | success_rate | 90% | **30%** | ⬇ operational reliability, not quality |
| | evidence_accuracy | 78.9% | 100% | improved (small n=5 in R2, caveat below) |
| | hallucination_rate | 21.1% | **0.0%** | improved, but n=5 in R2 vs n=38 in R1 — not conclusive |
| openrouter-llama-3.3-70b-instruct | composite | 0.701 | 0.663 | stable |
| | success_rate | 100% | 100% | **stable — the most operationally reliable identity across both rounds** |
| | structured_output_success | 80% | 70% | slightly worse |
| | numeric_accuracy | 60.7% | 51.7% | slightly worse |
| | median_latency | 86.0s | 134.3s | worse |
| gemini-control | composite | 0.968 (n=1) | 0.145 (n=0) | **not comparable — cannot evaluate Gemini meaningfully under current quota conditions** |
| groq (identical task R1; reduced-budget R2) | composite | 0.149 (0/10) | 0.148 (0/10 usable) | **consistently unusable on this task shape regardless of adjustment** |

**On accuracy metrics where both rounds have a meaningful sample, the
numbers are consistent, not contradictory** — Cerebras and OpenRouter's
per-metric percentages moved by single digits, well within what a
handful of documents' worth of noise would produce. **The one large,
real, reproducible shift is success_rate for both Cerebras identities**,
and it is explained by a specific, understood mechanism (rolling TPM
window under back-to-back same-provider load), not by any change in
model behavior.

## 5. Failures and account limitations (this round's new findings)

1. **Cerebras's per-minute token cap compounds under sustained
   same-provider load.** Round 1 interleaved calls across 6 providers per
   document, giving natural spacing; Round 2 issued 10 consecutive
   same-provider requests, and the rolling 60-second window could not
   absorb it after 3-4 calls. This is an **operational throughput
   constraint**, distinct from Round 1's "one huge document" finding —
   both are real and both matter for production planning (batch spacing/
   throttling would be required, not just per-document budget sizing).
2. **Groq's rolling TPM window makes even a single reduced-budget request
   effectively unrepeatable within the same minute** — the second call
   (MORISON, well within its own 9,022-token budget) failed because the
   FIRST call had already consumed most of the account's 12,000 TPM
   allowance. Reducing `max_tokens` per request does not solve Groq's
   usability on this task; the account's TPM ceiling is the binding
   constraint at the request-cadence level, not just the per-request
   level.
3. **OpenRouter's ELLAHLAKES result did not reproduce.** Round 1: exact
   or near-exact correct values, correctly scaled. Round 2: the call
   completed (real tokens returned) but produced no parseable JSON. This
   is the single most consequential reproducibility finding in this
   round, because ELLAHLAKES is the mandatory regression case — **one
   successful run on the defect document is not evidence of a fixed,
   reliable capability.**
4. **Gemini remains un-evaluable under current quota conditions.** Two
   consecutive session-days have now shown the same pattern: whatever
   quota remains after other work in a session is consumed within 1-2
   calls. A meaningful Gemini comparison requires either a dedicated
   quota-fresh session or a paid tier — neither was authorized or
   attempted here.

## 6. Statistical limitations (stated plainly, not glossed over)

- **Gemini has n=0 usable Round 2 cases and n=1 in Round 1 — no
  statistically meaningful statement about Gemini's accuracy is possible
  from this benchmark's data.** It remains the incumbent production
  provider on separate grounds (Gate 2's own deterministic validation),
  not because this benchmark demonstrates anything about it.
- **Cerebras identities' Round 2 sample sizes are small** (gemma-4-31b:
  4 documents; gpt-oss-120b: 3 documents) due to the TPM-window failures
  above — Round 2's accuracy percentages for these identities carry more
  sampling noise than Round 1's, even though the point estimates are
  similar.
- **Groq has never produced a single usable structured result across
  both rounds and two different task configurations** — this is now a
  reasonably confident negative finding (not just "insufficient
  evidence"), though a paid Groq tier remains untested.
- **No independent reasoning-quality judge exists in either round** —
  composite scores still proxy "reasoning quality" via structured-output
  success, same limitation as Round 1.
- **Two rounds is still a small number of rounds.** A third round,
  especially one that throttles same-provider request cadence to test
  whether that resolves the Cerebras/Groq TPM-compounding issue, would
  meaningfully add to this evidence base — not run here, as it was not
  part of this round's authorization.

## 7. Recommendation

**Per-identity, using PRIMARY / SECONDARY / FALLBACK / EXPERIMENTAL /
DISABLED — default is EXPERIMENTAL unless evidence clearly clears the
promotion gate. It does not, for any identity, this round:**

| Identity | Classification | Why |
|---|---|---|
| gemini-control | **EXPERIMENTAL** (incumbent status unchanged by this benchmark) | Cannot be evaluated under current quota; production status rests on Gate 2's separate deterministic validation, not this benchmark |
| cerebras-gemma-4-31b | **EXPERIMENTAL** | Best accuracy/hallucination profile across both rounds, but success_rate collapsed to 40% under realistic sustained load in Round 2 — a real throughput constraint, not yet mitigated or re-tested with throttling |
| cerebras-gpt-oss-120b | **EXPERIMENTAL** | Same throughput constraint as gemma-4-31b; Round 2's improved hallucination number (0%) is based on only 5 scoreable facts and is not yet trustworthy |
| openrouter-llama-3.3-70b-instruct | **EXPERIMENTAL** | Most operationally reliable completion rate (10/10 both rounds) but moderate-to-elevated hallucination both rounds, worse latency in Round 2, and a **non-reproduced result on the mandatory ELLAHLAKES case** — disqualifying on its own for anything beyond experimental status right now |
| cerebras-zai-glm-4.7 | **EXPERIMENTAL** (untested this round) | Round 1 showed a 33% structured-output success rate; not re-tested, no new evidence either way |
| groq-llama-3.3-70b-versatile | **DISABLED** for this task shape | Two rounds, two different configurations (identical-task and reduced-budget), zero usable structured results either time. Not "keep trying" — the account's TPM ceiling makes this task shape structurally unworkable without a paid tier upgrade, which was not authorized |

**No provider satisfies the promotion gate.** The clearest actionable
finding across both rounds is operational, not a quality ranking: any
future run against Cerebras or Groq needs deliberate request throttling
(spacing calls to respect the rolling TPM window) before their accuracy
numbers can be trusted at a meaningful sample size — this is now a
concrete, testable next step, not a guess.

## 8. Production and regression verification

- `extracted_facts=495`, `financial_reasoning_conclusions=403`,
  `llm_calls=69` — all **unchanged** from before Round 1 through the end
  of Round 2 (re-verified after this run).
- `git diff --stat` on `alpha_engine.py`/`engine_full.py`/`runner.py`/
  `registry.py` — empty.
- `scripts/test_reasoning_pipeline.py` — ALL CHECKS PASSED.
- `scripts/ai/test_provider_gateway.py` — 39/39 passed.
- All Round 2 traffic went through `benchmark_complete()` into a scratch-DB
  `benchmark_calls` table — zero rows in production `llm_calls`.
- No hypothesis registered, no Alpha Engine change, no broker, no capital,
  FRE HOLD decision untouched.
