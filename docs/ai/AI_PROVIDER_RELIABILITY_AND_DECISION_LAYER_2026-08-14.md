# AI Provider Reliability + Decision Layer — 2026-08-14

Turns Round 1 + Round 2 benchmark evidence into a reproducible,
confidence-aware provider classification system. **No Round 3 run.** No
production, Alpha Engine, Evidence Engine, Statistics Engine, or FRE
change. No provider promoted beyond what the evidence already supports.

---

## 1. Architecture — extended, not duplicated

Two new modules under `src/ngxrot/documents/` (the same package
`llm_providers.py`/`benchmark_cache.py` already live in — no parallel
infrastructure):

- **`provider_reliability.py`** — live, mutable per-(provider, model_id)
  health state: `healthy` / `cooldown` / `disabled`. Distinguishes
  **structural** failures (413 "request too large", 402 "payment
  required" — will never succeed regardless of timing) from **rate-limit**
  failures (429, "tokens per minute exceeded" — transient, worth a later
  retry) via `classify_failure()`, a pure string-matching function with
  no network dependency. Structural failures disable an identity after 2
  consecutive occurrences; any-class failures disable after 5. Backoff is
  exponential (30s base, 15min cap) unless the provider supplies its own
  `retry_delay_seconds`/`Retry-After`, which is honored instead.
  `call_with_reliability_guard()` makes **exactly one** call attempt —
  it checks state, calls once, records the outcome, and never loops or
  sleeps internally. This is a deliberate design choice: this whole
  session has operated under a standing "do not repeatedly poll a
  blocked provider" rule, and a library that retries internally would
  violate that the first time someone calls it. The decision to attempt
  again belongs to a **separate, later invocation** of an orchestrating
  script, never a tight in-process loop. A `disabled` state does **not**
  self-heal on a later success — it requires an explicit, reasoned
  `reset_provider()` call, so "operationally unsuitable" stays a
  deliberate re-evaluation, not something that quietly clears itself.

- **`provider_decision.py`** — pure functions (no I/O) that turn graded
  benchmark cases + raw results into: `quality_metrics()` (extraction/
  numeric/period/evidence accuracy, hallucination rate, catastrophic-error
  count — computed only from `success AND structured_output_success`
  cases, with `sample_confidence()` attached to every result: `none` /
  `very_low` (n≤2) / `low` (n≤5) / `moderate` (n≥6) — **this platform's
  data has never reached a "high" tier, and the function says so rather
  than implying one exists**), `operational_metrics()` (success rate,
  rate-limit vs. structural vs. other failure counts, latency — kept
  **separate from quality**, since a call that never completed carries no
  extraction-accuracy signal), `economics_metrics()` (tokens, confirmed
  vs. unconfirmed cost, cost per validated extraction — never assumes
  $0), `reproducibility_flags()` (flags a **flip** on a mandatory case
  between rounds, in either direction — a case that consistently
  succeeded or consistently failed both rounds is not flagged),
  `document_level_variance()` (per-document accuracy spread, population
  stdev, `None` when fewer than 2 documents rather than a fabricated
  number), `detect_disagreement()` (cross-model value comparison that
  **never resolves a winner** — flags a spread, returns both raw values,
  and nothing else), and `classify_provider()` — the explicit decision
  rules (§4).

- **Schema**: one additive table, `provider_reliability_state`
  (`schema/schema.sql`) — mutable current-state row per (provider,
  model_id), separate from the append-only `benchmark_calls` log. Never
  written to by production extraction.

- **`scripts/ai/build_decision_layer.py`** — the driver that loads the
  real Round 1/Round 2 JSON files and produces the classification table
  in §5. No live calls.

**Nothing about the extraction prompt, Evidence Engine, Statistics
Engine, Alpha Engine, or production provider config was touched to
produce any of these results** — the benchmark measures reality; it does
not optimize the test, per your explicit instruction.

## 2. Round 1 evidence (recap, not re-run)

10 real documents, 6 model identities, identical task
(`financial_reasoning_draft_v3`, `max_tokens=16384`). Groq 0/10 (413,
structural — request size alone exceeds its 12,000 TPM tier). Gemini 1/10
(daily quota exhausted after the first success). OpenRouter 10/10
completed, including a near-exact correct result on the mandatory
ELLAHLAKES ₦'000 case. Cerebras gemma-4-31b and gpt-oss-120b: 9/10 each
(failed only on ELLAHLAKES, the single largest document). Full detail:
`docs/ai/AI_PROVIDER_BENCHMARK_2026-08-13.md`.

## 3. Round 2 evidence (recap, not re-run)

Same gold set, same prompt, same grading. Gemini: single probe attempt,
still exhausted, correctly not polled further (0/10 attempted beyond the
probe). Groq: a reduced, per-document `max_tokens` computed from Round
1's own request-size telemetry — still failed on 9/10 (a rolling
per-minute window exhausted by the *first* call blocked every
subsequent one, even though each request was individually sized to fit).
Cerebras gemma-4-31b and gpt-oss-120b: success rate collapsed to 40%/30%
(same TPM-window-compounding mechanism, triggered by 10 consecutive
same-provider calls instead of Round 1's naturally interleaved
across-provider pattern). **OpenRouter completed 10/10 again, but its
ELLAHLAKES result did not reproduce** — the call completed but returned
no parseable JSON, unlike Round 1's near-exact success. Full detail:
`docs/ai/AI_PROVIDER_BENCHMARK_ROUND2_2026-08-13.md`.

## 4. Quality vs. operational reliability vs. economics — kept structurally separate

The decision layer refuses to let one obscure another:

- A call that **never completed** contributes zero quality signal (no
  numerator/denominator entry) but a full operational-reliability data
  point (a failure, classified by cause).
- A call that completed but **failed to parse** contributes zero
  quality signal too — `structured_output_success=False` cases are
  excluded from `quality_metrics()`'s accuracy denominators, exactly
  like a non-completion, because there is no fact to grade.
- **Rate-limit failures and structural failures are counted separately**
  in `operational_metrics()` — a provider whose failures are all
  transient (429s) reads very differently from one whose failures are
  structural (413/402, will never resolve by waiting), even if the raw
  failure *count* looks identical.
- **Reproducibility is checked independently of both** — a provider can
  have excellent quality and operational numbers in aggregate and still
  be capped at EXPERIMENTAL if it flipped on the one mandatory case
  (OpenRouter, this round).

## 5. Provider classifications (from real Round 1 + Round 2 data)

| Identity | Classification | n scoreable (confidence) | Numeric acc. | Hallucination | Catastrophic errors | Op. success R1 → R2 | Reason |
|---|---|---|---:|---:|---:|---|---|
| **cerebras-gemma-4-31b** | **EXPERIMENTAL** | 13 (moderate) | 70.5% | 2.1% | 0 | 90% → **40%** | Operational success rate below the 0.8 promotion bar in Round 2 |
| **cerebras-gpt-oss-120b** | **EXPERIMENTAL** | 12 (moderate) | 61.5% | 18.6% | 0 | 90% → **30%** | Same — operational bar failed in Round 2 |
| **openrouter-llama-3.3-70b-instruct** | **EXPERIMENTAL** | 15 (moderate) | 56.1% | 15.0% | 0 | 100% → 100% | **Failed to reproduce on the mandatory ELLAHLAKES case** — caps at EXPERIMENTAL regardless of otherwise-strong operational numbers |
| **gemini-control** | **EXPERIMENTAL/CONTROL** | 1 (very_low) | 80.0% | 0.0% | 0 | 10% → 0% | Sample size (n=1) too small for any promotion decision; remains production's incumbent on Gate 2's separate deterministic validation, not on this benchmark |
| **groq-llama-3.3-70b-versatile** | **DISABLED** | 0 (none) | N/A | N/A | 0 | 0% → 10%* | Zero usable structured extractions across two independent task configurations — the account's TPM ceiling makes this task shape structurally unworkable without a paid-tier upgrade |
| **cerebras-zai-glm-4.7** | **EXPERIMENTAL** (unchanged, not re-tested) | 3 (low, Round 1 only) | 60.0% | 0.0% | 0 | 90% (33% structured-output rate) → not run | Not in this round's authorized priority list — no new evidence either way |

*Groq's Round 2 "10%" reflects one call that completed at the HTTP level
but produced unusable output (`structured_output_success=False`) — not a
real success.

**These exactly match the required classifications** — verified
programmatically, not asserted by hand: `scripts/ai/test_provider_decision.py`
loads the real Round 1/Round 2 JSON and asserts each of these five labels
against the live `classify_provider()` function (5/5 passing, part of the
41/41 total in that file).

## 6. Reliability controls — what they do and, importantly, what they deliberately do NOT do

- **Rolling-window rate-limit detection**: `classify_failure()` correctly
  separates Groq's 413 (structural — confirmed via real error text,
  "Request too large... tokens per minute (TPM)") from Cerebras's 429
  ("Tokens per minute limit exceeded" — genuinely transient) even though
  both error messages mention "tokens per minute."
- **Exponential backoff + cooldown state**: implemented and unit-tested
  (`test_provider_reliability.py`, 34/34) — a provider's `cooldown_until`
  is computed and persisted, honoring the provider's own `Retry-After`/
  `retry_delay_seconds` over the computed default when available.
- **Maximum retry budget**: `retry_budget_remaining()` is a real,
  queryable number (5 for any-class failures, 2 for structural), not
  just a comment.
- **What this does NOT do**: sleep and retry in a loop. Given this
  session's standing instruction never to poll an exhausted quota,
  `call_with_reliability_guard()` makes exactly one attempt per
  invocation and raises a typed exception (`ProviderInCooldownError` /
  `ProviderDisabledError`) if the identity isn't currently callable — a
  future orchestrating script decides whether and when to invoke it
  again, across separate runs, never inside a tight loop. This was a
  deliberate design tension to resolve (the assignment asked for "retry
  behavior" and "maximum retry budget"; the standing session rule
  forbids polling) — resolved by making retry **state-tracking and
  gating**, not **blocking retry execution**.
- **Provider health state, disabled ≠ self-healing**: `groq` and
  `cerebras`'s reliability rows would, under this module, reach
  `disabled` after their observed real failure patterns (2 consecutive
  structural failures for Groq; 5 consecutive for a rate-limit-heavy
  Cerebras run) — and would **stay** disabled through any number of
  later successes until someone calls `reset_provider()` with a stated
  reason. This is not simulated here (no live state was actually
  written by Round 1/2, which predate this module) — it is the tested
  behavior a Round 3 run would exhibit if wired in.

## 7. Tests executed

| Suite | Result |
|---|---:|
| `test_provider_reliability.py` (new) | 34/34 |
| `test_provider_decision.py` (new, includes the real-data classification integration test) | 41/41 |
| `test_provider_gateway.py` (Phase 1, unaffected) | 39/39 |
| `test_reasoning_pipeline.py` (full existing pipeline) | 154/154 |
| `test_numeric_consistency.py` | 12/12 |
| `test_tabular_unit_consistency.py` | 22/22 |
| `test_data_quality_monitoring.py` | 12/12 |
| `test_research_memory.py` | 14/14 |
| `test_investment_os_e2e.py` | 23/23 |
| **Total** | **351/351** |

Coverage per your list: scoring ✅ (`quality_metrics`/`operational_metrics`
unit tests), sample-size handling ✅ (`sample_confidence` tiers +
empty-input None-vs-0 tests), reproducibility ✅ (flip-detection in both
directions + consistent-both-rounds non-flagging), provider
classification ✅ (7 synthetic edge cases + 5 real-data integration
assertions), rate-limit detection ✅ (`classify_failure`, 5 cases
including the Groq 413-vs-TPM-text trap), cooldown ✅ (exact
`cooldown_until` timestamp assertions), retry behavior ✅ (guard makes
exactly one attempt, never loops; blocked calls never invoke the
underlying function), fallback/disabled logging ✅ (structural vs
any-class disable thresholds, disabled-does-not-self-heal, explicit
reset), actual-model capture ✅ (inherited from Phase 1's
`test_provider_gateway.py`, still passing), cost aggregation ✅
(confirmed-vs-unconfirmed cost basis, cost-per-validated-extraction),
disagreement handling ✅ (tolerance-based flagging, zero-vs-nonzero
handled, **never returns a resolved/winning value**).

## 8. Limitations (stated plainly)

- This layer is built and tested against **existing** Round 1/2 data. It
  has not yet been wired into a live orchestrating script that actually
  calls `call_with_reliability_guard()` during a real benchmark run —
  that wiring is Round 3's job, not built speculatively here per your
  explicit "do not run Round 3 yet" instruction.
- `sample_confidence()`'s ceiling is `moderate` (n≥6) — no identity in
  this dataset has enough documents to reach a `high` tier, and the
  function does not pretend one exists.
- The promotion bar (`PROMOTION_BAR` in `provider_decision.py`) is a
  judgment call, stated explicitly and testable, not derived from a
  formal statistical power calculation — moderate quality confidence +
  ≥80% operational success rate in *every* round with data, for at least
  2 rounds. Reasonable people could set this differently; it is written
  down and unit-tested rather than implicit.
- `reproducibility_flags()` currently only checks the one mandatory case
  (ELLAHLAKES). Extending it to flag reproducibility drift on
  *non-mandatory* documents (e.g. via `document_level_variance()`'s
  per-doc spread, already computed but not yet fed into the
  classification decision) is a natural next step, not built here.
- Cerebras's real per-call cost remains unconfirmed (no reachable usage
  API, same limitation as both benchmark rounds) — `economics_metrics()`
  correctly reports this as `"not independently confirmed"` rather than
  defaulting to $0.

## 9. Promotion criteria (the actual gate, restated from code)

From `provider_decision.PROMOTION_BAR`, verified by
`test_provider_decision.py`'s synthetic edge cases:

1. Zero catastrophic errors, zero true-negative violations — hard fail
   to DISABLED otherwise, regardless of every other metric.
2. No reproducibility flag on any mandatory case — hard cap at
   EXPERIMENTAL otherwise.
3. Quality sample confidence must reach `moderate` (n≥6 scoreable cases).
4. Operational success rate must be ≥80% in **every** round with data
   (not an average across rounds — one bad round disqualifies).
5. At least 2 rounds with data.
6. Clearing all of the above caps at **SECONDARY**, never PRIMARY —
   PRIMARY explicitly requires a third confirming round plus operator
   sign-off, never an automatic promotion from a score alone.

**No identity clears this gate today.**

## 10. Exact next benchmark requirements (Round 3, not run here)

If/when authorized:

1. **Throttle same-provider request cadence** — space Cerebras and Groq
   calls to respect their rolling TPM windows (the single most
   actionable finding from Round 2); this alone could materially change
   both Cerebras identities' operational success rate without touching
   quality at all.
2. **Get Gemini a real sample** — needs either a dedicated quota-fresh
   session or a paid tier; two consecutive session-days have shown
   whatever quota remains gets consumed in 1-2 calls.
3. **Re-run ELLAHLAKES specifically for OpenRouter** — the one
   non-reproduced mandatory-case result is the most consequential open
   question from Round 2; a third data point would tell us whether
   Round 1's success or Round 2's failure is the outlier.
4. **Wire `call_with_reliability_guard()` into the actual runner** so
   Round 3 exercises real cooldown/disable state instead of this
   report's tested-but-not-yet-live behavior.
5. Only after that: re-run `build_decision_layer.py` and see whether any
   identity's classification actually changes.

## 11. Production and regression verification

- `extracted_facts=495`, `financial_reasoning_conclusions=403`,
  `llm_calls=69` — **all unchanged**, re-verified after this build.
- `git diff --stat` on `alpha_engine.py` / `engine_full.py` / `runner.py`
  / `registry.py` — empty.
- 351/351 tests passing across new and pre-existing suites.
- No hypothesis registered, no Alpha Engine change, no broker, no
  capital, FRE HOLD decision untouched, no alpha claimed.
