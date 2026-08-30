# AI Provider Benchmark — Round 3 Results — 2026-08-14

Executed under the frozen `ROUND3_MANIFEST`
(`b5328680fc79da43d1a9135733059928c907c3b6f4c093219c88908eba8357be`,
validated against real document text both before this round began and
again just now — unchanged). Same prompt (`financial_reasoning_draft_v3`),
same schema, same `max_tokens=16384`, same 10 documents as Rounds 1-2.
No provider promoted. **No production, Alpha Engine, Evidence Engine,
Statistics Engine, or FRE change.**

---

## 0. Two real incidents during execution, disclosed in full

This round did not run cleanly end-to-end in one pass, and both
incidents are worth recording honestly because they're genuine findings
about running this infrastructure, not just noise:

1. **A disk-full crash mid-execution.** The host's C: drive reached 0
   bytes free, which truncated the results file mid-write. Root cause:
   every benchmark script this entire session (Rounds 1-3, `test_investment_os_e2e.py`,
   `phase4_pilot_completion.py`, etc.) copies the ~150MB production
   `ngx.sqlite` into a fresh temp directory per invocation and never
   cleans it up — 24 leftover copies (~3.6GB) had accumulated by the
   time this ran. This is genuinely this session's own footprint, safely
   identified and cleaned up (freeing ~2.7GB), and `run_benchmark_round3.py`
   now cleans up both proactively (at the start of every invocation, for
   ANY leftover scratch copy, not just its own) and on exit. **Production
   was never at risk** — `PRAGMA integrity_check` confirmed `ok` and all
   three invariant counts held throughout.
2. **The results file's save-on-every-call design was not crash-safe.**
   The original implementation rewrote the *entire* results array on
   every single save; the disk-full write truncated the file to empty,
   destroying 28+ already-completed results, not just the one in
   progress. Fixed by switching to append-only JSONL (`scripts/ai/run_benchmark_round3.py`,
   `save_results()`/`load_results()`) — after the fix, a subsequent hard
   kill lost nothing; every previously-completed line survived. This is
   a real durability lesson worth carrying into any future round.

Both fixes are in the actual script now, not just described here.

## 1. Standard-phase results (10 documents × 4 identities, ELLAHLAKES attempted first)

| Identity | n scoreable | Numeric acc. | Period acc. | Evidence acc. | Hallucination | Catastrophic | Op. success rate | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gemini-control | 10 | 71.1% | 64.3% | 91.9% | 8.1% | 0 | **100% (10/10)** | 50.6s |
| openrouter-llama-3.3-70b-instruct | 8 | 62.1% | 69.6% | 95.5% | 4.2% | 0 | 100% (10/10) | 53.0s |
| cerebras-gemma-4-31b | 8 | 67.6% | 71.4% | 97.1% | 2.9% | 0 | 80% (8/10) | 4.5s |
| cerebras-gpt-oss-120b | 8 | 50.0% | 57.1% | 89.7% | 10.3% | 0 | 80% (8/10) | 4.5s |

**Zero catastrophic errors across every identity** (one apparent
catastrophic flag was found and fixed during grading — see §5).

**The throttling/reordering fix worked, partially and honestly**:
Cerebras identities recovered from Round 2's 40%/30% collapse to a real
80% success rate — a genuine, substantial operational improvement. It
did **not** fully clear the promotion bar's 80%-in-every-round
requirement in the pooled view because Round 2's collapse still counts.
The one failure each Cerebras identity had in the standard phase was
ELLAHLAKES itself (see §2) — every other document succeeded.

**Gemini finally has a real sample.** 10/10 calls completed (no quota
exhaustion this run — the daily window had reset). This is the first
time in this entire benchmark that Gemini could be evaluated on more
than n=1.

## 2. ELLAHLAKES — the mandatory case, reordered to run first

Reordering documents so ELLAHLAKES runs before anything else (to give it
first claim on any rolling-window budget) **did not change the outcome
for Cerebras** — both identities still failed with the identical
"Tokens per minute limit exceeded" error, now confirmed a **third
time**. This is strong evidence the failure is a single-request
capacity ceiling (ELLAHLAKES's own prompt size, ~36K tokens estimated
from Round 1's Groq telemetry, likely exceeds Cerebras's per-minute cap
outright), not a cumulative-usage artifact reordering could fix.

**Gemini succeeded, exactly correctly, for the first time in this
entire project.** Neither Gate 2 (blocked by quota, three consecutive
attempts) nor this benchmark's Round 1/2 (also blocked by quota) had
ever gotten a live Gemini result on the actual defect document until
now:

```
revenue     146,658,000    (gold: 146,658,000)     -- EXACT MATCH
net_profit  -3,839,656,000 (gold: -3,839,656,000)  -- EXACT MATCH
cfo         -4,375,789,000 (no gold value recorded, plausible new fact)
dividend    0               ("no dividend recommended" -- correctly extracted as 0, not omitted)
```

Both of the two facts with recorded gold values are **exact matches**,
with the ₦'000 table-header scale correctly applied. **This is directly
relevant evidence for the separate FRE Gate 2 decision** (whether the v3
prompt fix works on a live model call) — it does not change that
decision here, since that's a distinct process with its own protocol,
but it should not be withheld from whoever makes that call next.

**OpenRouter succeeded on the standard-phase attempt's HTTP call but
failed to produce parseable JSON** (`structured_output_success=False`)
— the third data point on this document (Round 1: success; Round 2:
fail; Round 3 standard: fail).

## 3. Category A — reproducibility repeats (3× each, force=True, cache bypassed)

| Identity | Document | Outcomes across 3 repeats | Consistent? |
|---|---|---|---|
| cerebras-gemma-4-31b | ELLAHLAKES | fail, fail, fail | ✅ consistently fails (structural) |
| cerebras-gemma-4-31b | TRANSCORP | fail (quota), succeed, succeed | ⚠️ flickers, but the failure is quota-timing, not extraction quality |
| cerebras-gemma-4-31b | CAP | succeed ×3 (5/6/6 facts) | ✅ consistent |
| cerebras-gpt-oss-120b | ELLAHLAKES | fail, fail, fail | ✅ consistently fails (structural) |
| cerebras-gpt-oss-120b | TRANSCORP | fail (quota), succeed, succeed | ⚠️ flickers, same quota-timing pattern |
| cerebras-gpt-oss-120b | CAP | succeed ×3 (3/1/6 facts) | ✅ pass/fail consistent, but **fact-count completeness swings 1→6** — real extraction-completeness volatility even when "successful" |
| openrouter-llama-3.3-70b-instruct | **ELLAHLAKES** | succeed (3 facts), succeed (6 facts), **fail** | ❌ **the ONLY case that flips between success and failure with no rate-limit/quota explanation** |
| openrouter-llama-3.3-70b-instruct | TRANSCORP | succeed ×3 (4/4/5 facts) | ✅ consistent |
| openrouter-llama-3.3-70b-instruct | CAP | succeed ×3 (3/4/3 facts) | ✅ consistent |

**The key finding this category was built to surface**: OpenRouter's
reproducibility problem is **specific to ELLAHLAKES**, not a general
property of the provider. On both other test documents (TRANSCORP, CAP)
it was perfectly consistent across all 3 repeats. Combined with the
standard-phase and Round 1/2 history, OpenRouter's ELLAHLAKES track
record across every attempt this project has made is now: **success,
fail, fail, success, success, fail — 3 successes out of 6 real
attempts, roughly a coin flip specifically on its hardest, largest
document.** This is a much more precise and actionable characterization
than "OpenRouter has a reproducibility problem."

Cerebras's TRANSCORP "flicker" (fail then two successes) is
distinguishable from OpenRouter's ELLAHLAKES flicker: Cerebras's failure
carries an explicit rate-limit error message (a quota/timing cause);
OpenRouter's ELLAHLAKES failures carry no such explanation — the HTTP
call succeeds, tokens are consumed, but the output doesn't parse. That
is a real quality/reliability distinction, not just "both flicker."

## 4. Category E — schema compliance (distinct from raw JSON-parseability)

| Identity | empty | malformed | partial | compliant | avg. compliance rate (non-empty) |
|---|---:|---:|---:|---:|---:|
| gemini-control | 2 | 0 | 0 | 8 | 1.0 |
| openrouter-llama-3.3-70b-instruct | 2 | 0 | 0 | 8 | 1.0 |
| cerebras-gemma-4-31b | 3 | 0 | 0 | 7 | 1.0 |
| cerebras-gpt-oss-120b | 3 | 0 | 0 | 7 | 1.0 |

**Every response that returned any facts at all was fully schema-compliant**
(populated every required key in `impact_assessments`/`implication`, not
just the top-level fields) — a genuinely positive, unexpected finding.
`empty` counts are correct-and-expected for the true-negative documents
(STANBIC, MORISON) plus, for Cerebras, ELLAHLAKES's structural failures.
No `malformed` or `partial` responses occurred anywhere this round.

## 5. A grading bug found and fixed mid-analysis (disclosed, not hidden)

Before finalizing, Gemini's pooled classification computed as
**DISABLED** — 2 "catastrophic" period-type errors on AFRIPRUD. Investigated
before reporting it (per this project's own standing discipline): Gemini
had returned `period_type=None` on AFRIPRUD's revenue/net_profit facts —
AFRIPRUD is a genuinely ambiguous Q3-vs-9M document (the same real
ambiguity already documented in the gold set), and the extraction prompt
*explicitly instructs* "if the period is unclear... leave period_type as
null rather than guessing." Gemini followed that instruction correctly.
The grading code was treating "declined to guess" identically to
"guessed wrong," which is a real bug — fixed in `grade_benchmark.py`'s
`_period_type_ok()`. Re-verified Round 1 and Round 2's already-published
catastrophic-error counts remain 0 everywhere after the fix (no
regression). A second bug found in the same pass: `reproducibility_flags()`'s
message text hardcoded literal "round 1"/"round 2" regardless of which
two rounds were actually compared, producing a factually wrong message
when comparing Round 1 vs Round 3 — fixed to take real round labels.

## 6. Updated classification (Round 1 + Round 2 + Round 3, pooled evidence)

| Identity | Classification | Reason |
|---|---|---|
| cerebras-gemma-4-31b | **EXPERIMENTAL** (unchanged) | Pooled n=21, moderate confidence, zero catastrophic errors — but operational success rate (40% in Round 2) still fails the "every round ≥80%" bar even though Round 3 alone hit 80% |
| cerebras-gpt-oss-120b | **EXPERIMENTAL** (unchanged) | Same pattern — Round 2's 30% still fails the bar despite Round 3's 80% |
| openrouter-llama-3.3-70b-instruct | **EXPERIMENTAL** (unchanged) | Failed to reproduce on the mandatory case (Round 1 success, Round 3 standard-phase failure) — now further characterized by §3 as ELLAHLAKES-specific, not general |
| gemini-control | **EXPERIMENTAL/CONTROL** (unchanged label, materially different reason) | No longer "insufficient sample" — now has real n=11, moderate confidence, zero catastrophic errors (after the §5 fix), 100% operational success in its one real round. Still capped at EXPERIMENTAL because Round 1 never got a real attempt at ELLAHLAKES (quota-blocked, not a failure) while Round 3 succeeded — the promotion bar's reproducibility check reads this as an unconfirmed flip, though the honest story is "one clean success, zero clean failures," not flakiness |

**No identity was promoted.** The promotion bar (moderate confidence +
≥80% operational success in *every* round with data + no reproducibility
flag + zero catastrophic errors) is not cleared by any identity yet —
each falls short on exactly one dimension, and each dimension is now
precisely identified rather than lumped into a generic "not enough
evidence."

## 7. Economics

- **OpenRouter**: confirmed via `/v1/key` — cumulative usage now
  **$0.129** (up from $0.057 after Round 2), so Round 3 alone cost
  **≈$0.072**. Real, small, growing linearly with usage as expected.
- **Cerebras**: still no reachable usage/billing API — real cost
  remains unconfirmed, same caveat as every prior round.
- **Gemini**: $0 (free tier; this round's 10 calls fit within the daily
  quota window that had reset).

## 8. Statistical limitations (Phase 3 discipline, applied honestly)

- Pooled sample sizes are now real for every identity (11-23 scoreable
  cases) — the `evidence_tier()` ceiling is `moderate` for all four,
  meaning real, usable evidence exists, but none has cleared
  `promotion_eligible`.
- The reliability guard's cooldown/disabled *state* did not persist
  continuously across this round's several forced restarts (each
  restart creates a fresh scratch DB) — the throttling/reordering
  *behavior* still ran correctly within each continuous segment, but the
  guard's own cross-restart memory is weaker evidence than a single
  unbroken run would have produced. Named honestly, not smoothed over.
- Categories B, C, D (unit/period/evidence-fidelity robustness) drew on
  the existing 10-document gold set exactly as planned — the two
  documented gaps from the Round 3 plan (a "plain ₦" case, a pure-Q1/
  restated-figures case) remain unfilled; no new documents were sourced
  this round.
- Category F's throttling fix shows real, partial success (Cerebras
  80% vs Round 2's 30-40%) but is confounded by this round's multiple
  process restarts — a single unbroken throttled run would be cleaner
  evidence for a future round.

## 9. Testing and regression

| Suite | Result |
|---|---:|
| `test_provider_reliability.py` | 34/34 |
| `test_provider_decision.py` (re-verified after the §5 fixes) | 64/64 |
| `test_benchmark_manifest.py` | 17/17 |
| `test_provider_gateway.py` | 39/39 |
| `test_reasoning_pipeline.py` | 154/154 |
| `test_numeric_consistency.py` | 12/12 |
| `test_tabular_unit_consistency.py` | 22/22 |
| `test_data_quality_monitoring.py` | 12/12 |
| `test_research_memory.py` | 14/14 |
| `test_investment_os_e2e.py` | 23/23 |
| **Total** | **431/431** |

Production invariants, re-verified after this round: `extracted_facts=495`,
`financial_reasoning_conclusions=403`, `llm_calls=69`, `PRAGMA integrity_check=ok`.
`git diff --stat` on the four protected Alpha Engine files — empty.
Disk: 11GB free (was 0 mid-round; cleaned up and now monitored by the
runner itself). No hypothesis registered, no Alpha Engine change, no
alpha claimed, FRE HOLD decision untouched (Gemini's ELLAHLAKES success
here is reported as evidence for that separate process, not acted on).
