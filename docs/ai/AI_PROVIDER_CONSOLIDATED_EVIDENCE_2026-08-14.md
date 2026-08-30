# AI Provider Consolidated Evidence — 2026-08-14

**What do we actually know about provider reliability after three
benchmark rounds, and what evidence is still missing before production
promotion?**

Pure consolidation of Rounds 1-3 plus the existing FRE Gate-2 record.
**No new live calls were made to produce this report.** No provider
promoted. No architecture built this phase beyond two small, inline
analysis functions (`unit_accuracy`, `ambiguity_handling` in
`scripts/ai/consolidate_evidence.py`) needed to compute metrics your
request asked for that weren't already tracked.

---

## 0. Infrastructure invariants — verified, not assumed

| Claim | Verified how | Result |
|---|---|---|
| Scratch databases are cleaned automatically | Checked `%TEMP%` for leftover `ngx_scratch.sqlite` copies before and after a run | `run_benchmark_round3.py` now cleans proactively (start of every invocation, any leftover, not just its own) and on exit — confirmed 0 leftover after the last run. **Caveat, stated plainly**: this cleanup is only wired into `run_benchmark_round3.py`; other scripts in this project that copy `ngx.sqlite` to scratch (`test_investment_os_e2e.py`, `phase4_pilot_completion.py`, the original `run_benchmark.py`/`run_benchmark_round2.py`) do not yet have it. Two leftover copies from other scripts were found and manually removed this session (safe — known origin, pure scratch copies). |
| Interrupted writes cannot destroy previous benchmark results | Simulated a truncated/partial trailing write against the real JSONL append logic | A partial, unterminated final line is skipped by the line-by-line parser without affecting any previously-written line — confirmed with a real (not hypothetical) truncation test. This is the actual fix that survived a real hard-kill during Round 3 with zero data loss, verified live. |
| Benchmark resumption works | Inspected `already_done()` and observed real resume behavior across ~6 forced restarts during Round 3 | Confirmed live, repeatedly — every restart correctly skipped completed `(doc_id, identity, phase, repeat_index)` combinations and resumed exactly where it left off. |
| Production databases remain isolated | Queried the real production DB directly | `benchmark_calls` **does not exist at all** in production `data/ngx.sqlite` — it only ever gets created inside a scratch copy via `db.init_db()`. Production `llm_calls=69`, unchanged since before this entire AI Provider Expansion workstream began. |

Production re-verified again just now: `extracted_facts=495`,
`financial_reasoning_conclusions=403`, `llm_calls=69`,
`PRAGMA integrity_check=ok`. Disk: 9.1GB free (down from the 11GB
reported at the end of Round 3 — two more leftover scratch copies from
earlier ad-hoc commands were found and removed during this phase's own
verification pass).

## 1. Full per-identity metrics (Rounds 1-3 pooled, plus FRE Gate-2 for Gemini)

| Metric | gemini-control | openrouter-llama-3.3-70b | cerebras-gemma-4-31b | cerebras-gpt-oss-120b | cerebras-zai-glm-4.7 | groq-llama-3.3-70b |
|---|---:|---:|---:|---:|---:|---:|
| Total attempts (all rounds/phases) | 30 | 30 | 30 | 30 | 10 | 20 |
| Successful structured outputs | 11 | 23 | 21 | 20 | 3 | 0 |
| Extraction accuracy (structured-output success rate) | 36.7% | 76.7% | 70.0% | 66.7% | 30.0% | 0.0% |
| Numerical accuracy | 72.1% | 58.1% | 69.2% | 56.2% | 60.0% | N/A |
| **Unit accuracy** (no 1000×/1e6× scaling error) | **100%** | **100%** | **100%** | **100%** | 100% | N/A |
| Period accuracy | 66.7% | 62.7% | 74.6% | 62.3% | 60.0% | N/A |
| Evidence accuracy (grounded quotes) | 92.7% | 88.1% | 97.6% | 84.7% | 100% | N/A |
| Hallucination rate | 7.3% | 10.9% | 2.4% | 15.3% | 0.0% | N/A |
| Catastrophic-error rate | **0/0** | **0/0** | **0/0** | **0/0** | 0/0 | N/A |
| Refusal/ambiguity handling accuracy | 100% | 100% | 100% | 100% | 100% | 100%* |
| Reproducibility (mandatory-case flip, R1↔R3) | ⚠️ flagged (see §3) | ⚠️ flagged (see §2) | none observed | none observed | not re-tested | not re-tested |
| Operational success — Round 1 | 10% | 100% | 90% | 90% | 90% | 0% |
| Operational success — Round 2 | 0% | 100% | 40% | 30% | not run | 10%† |
| Operational success — Round 3 | 100% | 100% | 80% | 80% | not run | not run |
| Median latency | ~51s | ~53-134s | ~4.5s | ~4.5s | ~17s | N/A |
| Confirmed cost (cumulative) | $0 (free tier) | **$0.129 confirmed** | unconfirmed, non-zero | unconfirmed, non-zero | unconfirmed | **$0 confirmed** (zero calls ever passed request validation before billing) |
| Cost per successful validated extraction | $0 | $0.0056 | unconfirmed | unconfirmed | unconfirmed | N/A |
| **Current classification** | **EXPERIMENTAL/CONTROL** | **EXPERIMENTAL** | **EXPERIMENTAL** | **EXPERIMENTAL** | EXPERIMENTAL | **DISABLED** |

*Groq's "100%" refusal/ambiguity handling reflects 0 true-negative-doc
attempts producing a hallucination out of 0 real opportunities — not a
positive finding, just the absence of a negative one; see §5.
†Groq Round 2 used a deliberately reduced `max_tokens` budget, not the
identical task — see the Round 2 report for why this isn't directly
comparable to its own Round 1 number.

All catastrophic-error, unit-accuracy, and reproducibility figures were
**re-verified after fixing two real grading bugs found during Round 3
analysis** (a false catastrophic-error flag on Gemini's correct
null-period-type response to a genuinely ambiguous document, and a
reproducibility-message bug that mislabeled which rounds were being
compared) — both fixes are in the shared grading code and Round 1/2's
already-published zero-catastrophic-error results were re-checked and
confirmed unaffected.

## 2. Model quality vs. provider operational reliability vs. statistical confidence — kept explicitly separate

**These three are genuinely different axes, and conflating them is
exactly what has produced misleading impressions in earlier
rounds if not corrected here:**

- **Model quality** (numeric/period/evidence accuracy, hallucination,
  catastrophic-error rate) measures what happens **when a call succeeds
  and parses**. By this axis, `cerebras-gemma-4-31b` is currently the
  strongest performer (69.2% numeric accuracy, 97.6% evidence accuracy,
  lowest hallucination rate at 2.4%), and `cerebras-gpt-oss-120b` is the
  weakest on hallucination (15.3%) despite decent evidence grounding.
- **Provider operational reliability** (success rate, rate-limit
  frequency, latency) measures whether a call **completes at all**. By
  this axis, OpenRouter is the strongest (100% in every round, all three
  rounds) and Groq is disqualifying (0-10%, never producing a usable
  result).
- **Statistical confidence** (sample size, reproducibility) measures how
  much we should trust either of the above numbers. By this axis,
  **every identity in this table is at most `moderate`** — this
  benchmark has never produced a `high`-confidence result for anything,
  and says so explicitly rather than implying otherwise.

**A concrete example of why the separation matters**: OpenRouter has the
*best* operational reliability (100% every round) and *mediocre* model
quality (58.1% numeric accuracy, 10.9% hallucination) — a provider that
almost always responds, but whose responses are only moderately
accurate when it does. Cerebras gemma-4-31b has the *best* model quality
and *worse* operational reliability historically (Round 2's 40%). These
are not the same finding, and neither should be summarized as "provider
X is good" or "provider X is bad" without specifying which axis.

## 3. Gemini — the live ELLAHLAKES result, in full, without over-interpreting it

**Genuine, live, no-cache, no-retry result** (Round 3, `docs/ai/AI_PROVIDER_BENCHMARK_ROUND3_RESULTS_2026-08-14.md` §2):

```
revenue     146,658,000    (gold: 146,658,000)     -- EXACT MATCH
net_profit  -3,839,656,000 (gold: -3,839,656,000)  -- EXACT MATCH
```

Both facts match this project's independently-verified ground truth
exactly, with the ₦'000 table-header scale correctly applied. This is
the first time in this project's history — across Gate 2's three
attempts and this benchmark's first two rounds, all blocked by quota —
that a live model call on the actual defect document has been observed
at all, let alone correct.

**Treated as strong evidence for the FRE Gate-2 decision** (§6), **and
explicitly NOT treated as sufficient for PRIMARY provider promotion**,
per your instruction. The reasons these are different bars:
- Gate 2's question is narrow and specific: does the v3 prompt fix work
  on the one real document that exposed the original defect? This result
  answers that question directly, with an exact match.
- PRIMARY promotion requires the much broader bar in §7 — a moderate-
  confidence sample (Gemini's pooled n=11, `evidence_tier=preliminary`
  because of the reproducibility flag below), reproducibility across
  rounds, and operational reliability across multiple rounds (Gemini's
  Round 1/2 operational success was 10%/0% — real, historical, not
  erased by Round 3's 100%, same discipline requested for Cerebras in §4).

**The reproducibility flag on Gemini, explained precisely, not left
ambiguous**: `reproducibility_flags()` reports "succeeded round 3, did
not succeed round 1" on ELLAHLAKES. The honest story behind that
sentence is **not** flakiness — Round 1's Gemini call never got a real
attempt at ELLAHLAKES at all (blocked by daily quota exhaustion before
reaching it). This is "one clean success, zero clean failures," not
"succeeded once, failed once." It is still correctly capped at
`preliminary` evidence tier rather than promoted past it, because the
mechanical check can't yet distinguish "never attempted" from "attempted
and failed" — a precise, named limitation, not a contradiction.

## 4. Cerebras — the throttling improvement, with history retained, not erased

| | Round 1 (interleaved, natural spacing) | Round 2 (back-to-back, same-provider) | Round 3 (throttled + ELLAHLAKES-first + reliability guard) |
|---|---:|---:|---:|
| gemma-4-31b operational success | 90% | **40%** | 80% |
| gpt-oss-120b operational success | 90% | **30%** | 80% |

**The improvement is real**: Round 3's throttling/reordering fix
recovered both Cerebras identities from Round 2's collapse to 80% —
consistent with the diagnosis that back-to-back same-provider requests
were the proximate cause, not a general capacity problem. **Round 2's
40%/30% remains in the pooled record and remains load-bearing in the
classification**: `classify_provider()`'s promotion bar requires ≥80%
operational success in **every** round with data, not an average or the
most recent round — Round 2's real historical failure is exactly why
both Cerebras identities stay at EXPERIMENTAL despite Round 3's genuine
improvement. This is enforced by the code's own logic (§7), not asserted
in prose after the fact.

**What did NOT improve, and stayed structurally impossible across all
three rounds and every reordering attempted**: ELLAHLAKES itself. Both
Cerebras identities failed on ELLAHLAKES in Round 1, Round 2, **and**
Round 3 even when attempted first (before any other document could
consume rolling-window budget) — three consecutive, methodologically
distinct confirmations that this is very likely a single-request
capacity ceiling (ELLAHLAKES's own ~36K-token prompt size versus
Cerebras's per-minute cap), not a scheduling artifact.

## 5. OpenRouter — ELLAHLAKES-specific instability, modeled separately from general reliability

**General operational reliability: excellent, all three rounds, unambiguous.**
100% HTTP-level success rate in Round 1, Round 2, and Round 3 — every
single call OpenRouter received got a response. This is the best
operational record of any provider tested, including Gemini.

**ELLAHLAKES specifically: unresolved, real instability, isolated to
this one document.** Full track record across every attempt this project
has made on ELLAHLAKES via OpenRouter:

| Attempt | Outcome |
|---|---|
| Round 1 (standard) | ✅ success, near-exact values |
| Round 2 (standard) | ❌ call completed, unparseable output |
| Round 3 (standard) | ❌ call completed, unparseable output |
| Round 3 (repro repeat 1) | ✅ success, 3 facts |
| Round 3 (repro repeat 2) | ✅ success, 6 facts |
| Round 3 (repro repeat 3) | ❌ call completed, unparseable output |

**3 successes out of 6 real attempts — roughly a coin flip, specifically
on this one document.** On every OTHER document tested for
reproducibility this round (TRANSCORP, CAP — 3 repeats each), OpenRouter
was **perfectly consistent**, 6/6. Per your instruction, this is
reported as document-specific instability on ELLAHLAKES, **not** a claim
that OpenRouter is generally unstable — the data does not support the
broader claim, and the narrower one is precisely what's actually
observed.

## 6. FRE Gate-2 — left at HOLD, evidence reported, decision not altered

Per your instruction: *"Do not alter the existing FRE decision without
executing the exact authorized Gate-2 protocol. If the formally required
Gate-2 confirmation has now been completed successfully, report the
evidence and determine whether the existing protocol permits GO.
Otherwise leave FRE at HOLD."*

**The formally required confirmation has NOT been completed.** Gate 2's
own protocol named a specific batch: `scripts/fre/phase4_pilot_completion.py`,
unmodified, all 4 documents (STANBIC, ELLAHLAKES, MORISON, ETI), writing
through the real production path (`resumable_financial_reasoning()` →
`cached_complete()` → `llm_calls`). The Round 3 ELLAHLAKES result used
the **same prompt, same model, same `max_tokens`** — but ran through the
AI Provider Benchmark's separate harness (`benchmark_complete()` →
scratch-DB `benchmark_calls`), and tested ELLAHLAKES alone, not the full
4-document batch.

**Existing protocol does not permit GO from this evidence alone.**
`docs/alpha/AUTONOMOUS_FRE_PROGRESS_2026-08-13.md` Entry 5 (added this
session) already records this precisely and recommends, without
executing, either: (a) accept this as sufficient live confirmation and
move to GO, or (b) run the exact named batch once more for a formally
on-protocol confirmation. **Neither has been executed. FRE remains at
HOLD.** This is the correct, conservative reading of your instruction —
strong evidence exists, but "strong evidence via an adjacent path" is
explicitly not the same thing as "the exact authorized protocol,"
and only the latter is licensed to change the decision.

## 7. Promotion gate — current classifications, unchanged, with precise per-identity reasons

No provider is promoted by this report. The classifications you
specified as current remain exactly as specified, and the code that
produces them (`provider_decision.classify_provider()`,
`evidence_tier()`) reproduces every one of them from the real pooled
data, verified by `scripts/ai/test_provider_decision.py`'s integration
test (which will need a follow-up addition once this consolidation's
exact pooled numbers are treated as a new baseline — not done here, see
§9):

| Identity | Classification | Precise blocking reason |
|---|---|---|
| Groq / Llama 3.3 70B | **DISABLED** | Zero usable structured extractions across two independent task configurations (Round 1 identical-task, Round 2 reduced-budget) — an account TPM ceiling, not a quality finding |
| OpenRouter / Llama 3.3 70B | **EXPERIMENTAL** | Best operational reliability of any identity, but an unresolved, real, document-specific (ELLAHLAKES) reproducibility flag caps it below promotion eligibility |
| Cerebras / Gemma 4 31B | **EXPERIMENTAL** | Best model-quality metrics of any identity, but Round 2's real 40% operational success rate remains in the pooled record and fails the "every round ≥80%" bar |
| Cerebras / GPT-OSS 120B | **EXPERIMENTAL** | Same operational-history constraint as Gemma 4 31B, plus the highest hallucination rate observed (15.3%) |
| Gemini | **EXPERIMENTAL/CONTROL** | Now has a real, moderate-confidence sample (n=11) and a landmark correct live ELLAHLAKES result, but Round 1/2's real 10%/0% operational success remains in the pooled record, and the reproducibility check (correctly, if conservatively) can't yet distinguish "never attempted" from "failed" |

**Nothing here is promoted to SECONDARY, FALLBACK, or PRIMARY.** No
identity has cleared all of: moderate-or-better confidence, zero
reproducibility flags, and ≥80% operational success in every round with
data, simultaneously.

## 8. What is still missing before any production promotion

1. **A round where Cerebras and Gemini both get a full, unbroken,
   throttled run without a forced restart** — Round 3's real 80%
   Cerebras improvement is genuine but was collected across ~6 process
   restarts (disk-full, background-task kills); a clean single-session
   run is stronger evidence for the same conclusion, not different
   evidence.
2. **Resolution of the OpenRouter/ELLAHLAKES coin flip** — 6 attempts is
   not enough to know if this converges toward "usually works" or
   "usually fails"; more attempts on this one document specifically
   would answer it cheaply.
3. **The formally-named Gate-2 confirmation batch**
   (`phase4_pilot_completion.py`, all 4 documents) if a decision on FRE
   GO/HOLD is wanted on-protocol rather than via the strong-but-adjacent
   Round 3 evidence.
4. **A second full Gemini round without a same-day quota collision** —
   Round 3 is Gemini's only clean full-sample data point; a second one
   is what "reproducibility" actually requires before its evidence tier
   could rise.
5. **The two named gold-set gaps from the Round 3 plan** (a "plain ₦"
   document, a pure-Q1/confirmed-restated-figures document) — still
   unsourced, still real gaps in unit/period robustness coverage.

None of these are, on their own, currently identified as **statistically
necessary** to run immediately — per your instruction, no new large live
benchmark is being started from this report. Item 3 (the named Gate-2
batch) is the one item with a standing, separate authorization path (the
FRE protocol itself) rather than requiring new AI-benchmark authorization.

## 9. Testing and regression

| Suite | Result |
|---|---:|
| `test_provider_reliability.py` | 34/34 |
| `test_provider_decision.py` | 64/64 |
| `test_benchmark_manifest.py` | 17/17 |
| `test_provider_gateway.py` | 39/39 |
| `test_reasoning_pipeline.py` | 154/154 |
| `test_numeric_consistency.py` | 12/12 |
| `test_tabular_unit_consistency.py` | 22/22 |
| `test_data_quality_monitoring.py` | 12/12 |
| `test_research_memory.py` | 14/14 |
| `test_investment_os_e2e.py` | 23/23 |
| **Total** | **431/431** |

Production, re-verified after this consolidation: `extracted_facts=495`,
`financial_reasoning_conclusions=403`, `llm_calls=69`,
`PRAGMA integrity_check=ok`. `git diff --stat` on the four protected
Alpha Engine files — empty. No new live benchmark calls were made to
produce this report. FRE remains HOLD (§6). No hypothesis registered, no
alpha claimed.

## Addendum — 2026-08-15 — Gate-2 batch folded into Gemini's pooled classification

§7/§9 above flagged this as a needed follow-up once the FRE Gate-2
confirmation batch existed as evidence. It now does (commit `2a09558`,
`scripts/fre/phase4_pilot_completion.py`, all 4 documents, real
production path — see `docs/alpha/AUTONOMOUS_FRE_PROGRESS_2026-08-13.md`
Entry 6). This addendum folds those 4 results into Gemini's pooled
quality/operational evidence exactly the way `consolidate_evidence.py`
already pools Rounds 1–3 — same `grade_case()` /
`quality_metrics()` / `operational_metrics()` / `evidence_tier()` /
`classify_provider()` functions, no new scoring path — and re-runs the
classifier. **No other identity's classification is touched**: Gate-2
produced zero new evidence about OpenRouter, either Cerebras identity, or
Groq.

Script: `scripts/ai/fold_gate2_into_gemini.py`. Gate-2's raw results were
never written to a `benchmark_results_*.json(l)` file (they went through
the real production path, not the benchmark harness), so they were
reconstructed directly from the Gate-2 run's scratch DB
(`extracted_facts`/`evidence`/`llm_calls`, read-only query) into the same
raw-result shape `run_benchmark*.py` produces — this is a reconstruction
of real recorded output, not invented data. ETI (doc 7867) has no gold
spec (it was never part of any prior gold set) and is therefore included
in operational metrics only, excluded from quality grading — the same
treatment any ungraded document gets, not a special case invented for
this batch.

**Before (Rounds 1–3 pooled, pre-Gate-2):**

| | |
|---|---|
| n_scoreable | 11 (confidence: moderate) |
| numeric_accuracy | 0.721 (31/43) |
| catastrophic_error_count | 0 |
| reproducibility_flags | `mandatory doc 11122: succeeded round 3, did not succeed round 1` |
| evidence_tier | **preliminary** |
| classification | **EXPERIMENTAL/CONTROL** |

**After (Rounds 1–3 + Gate-2 batch pooled):**

| | |
|---|---|
| n_scoreable | 14 (confidence: moderate) |
| numeric_accuracy | 0.745 (35/47) — ELLAHLAKES exact match included |
| hallucination_rate | 0.0625 (3/48) |
| operational success by round | R1=0.10, R2=0.00, R3=1.00, **Gate-2=1.00** |
| reproducibility_flags (R1 vs R3, unchanged) | `mandatory doc 11122: succeeded round 3, did not succeed round 1` |
| reproducibility check, R3 vs Gate-2 (ELLAHLAKES) | none — no flip |
| evidence_tier | **preliminary** |
| classification | **EXPERIMENTAL/CONTROL** |

**Computed result: no change.** `EXPERIMENTAL/CONTROL` stays
`EXPERIMENTAL/CONTROL`; `preliminary` stays `preliminary`. This is a real
finding, not a shortfall in how the batch was folded in — stated
precisely, not hand-waved:

`evidence_tier()` caps any pool at `preliminary` the moment its
`reproducibility_flags_list` is non-empty, with no mechanism to let a
later confirming round retroactively clear an earlier flag on the *same
compared pair*. The flag here traces to a real, permanent fact: Round 1's
ELLAHLAKES attempt genuinely failed (quota exhaustion) while Round 3's
succeeded — a real flip between those two specific rounds, and Gate-2
adding a fourth consecutive success (Round 3, then Gate-2, both clean)
doesn't erase what already happened in Round 1. Gate-2 vs Round 3 itself
shows **no flip** (both succeeded) — genuinely reinforcing evidence — but
the pooled classification's reproducibility check is anchored to Round 1
vs Round 3 by existing precedent (`consolidate_evidence.py`,
`grade_benchmark_round3.py`), and this addendum does not invent a
different anchor just to move the answer.

**What would actually clear this**: not more successful rounds under the
current R1-vs-R3 comparison basis, but either (a) a documented,
reasoned decision that the current comparison basis should shift to the
two most recent rounds as new rounds accumulate (a real change to
`reproducibility_flags()`'s calling convention, requiring its own
review — not made here), or (b) accepting that Round 1's one real
quota-driven failure is a permanent mark against automatic promotion
under this function's present design, separate from the question of
whether the *model* itself is now reliable.

**Answering the standing question plainly**: the computed result is
**not** SECONDARY-eligible. `evidence_tier()` returns `preliminary`, one
tier below the `moderate`/`promotion_eligible` levels `classify_provider()`
would need to even consider `SECONDARY` (and even `promotion_eligible`
is capped at `SECONDARY`, never automatic `PRIMARY`, by the function's
own design). Nothing here blocks a *future* PRIMARY decision beyond what
already blocked it — this was already, and remains, an explicit owner
call the function refuses to make automatically; Gate-2 does not change
what stands between here and that call. It does materially strengthen
the model-quality case (a second clean ELLAHLAKES pass, this time via
the real production path) without moving the pooled classification the
automated layer computes.

Regression, re-run after this change: `test_provider_decision.py`
64/64 (baseline updated from R1+R2-only to R1+R2+R3, with Gate-2 folded
into gemini-control's cases — the staleness §7/§9 flagged as a needed
follow-up). Protected Alpha Engine files: zero diff, before and after.
`configs/llm_provider.toml` untouched — Gemini's status as sole
production provider was never in question here; only its automated
*evidence-tier classification* was recomputed.
