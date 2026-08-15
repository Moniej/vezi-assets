# Autonomous FRE Progress Log — 2026-08-13

## Entry 1 — 11:33 UTC (approx.)

**Coverage (prior)**: 14/50 usable tickers, 38.6% fact-survival rate,
403 conclusions, 495 extracted_facts — all production, verified at Phase
0 freeze this run.

**Quota state**: Gemini quota, previously exhausted on every check today,
**genuinely reset** during this run's single Phase-1 attempt. Confirmed
by a full successful batch completion with zero `429` errors.

**Documents processed this batch**: 4, against a **SCRATCH** copy of
`data/ngx.sqlite` only (`scripts/fre/phase4_pilot_completion.py`'s
existing, unmodified design — never touches production). **Nothing in
this entry has been promoted to production.**

| doc_id | Ticker | Type | Period | Facts | Elapsed | Notes |
|---:|---|---|---|---:|---:|---|
| 452 | STANBIC | messy/delay-adjacent | n/a | 1 | 81.7s | Qualitative statement mistagged `net_profit`/null — matches the exact, previously-predicted failure mode. Correctly caught downstream: `blocked_by_self_critique` (1 fail, 5 concern). |
| 11122 | ELLAHLAKES | FY (irregular 17-month) | 2024-08-01→2025-12-31 | 6 | 330.5s | **New defect found — see below.** Irregular-period handling itself worked correctly (real dates preserved, `period_type=None`, not force-mapped to FY). 1 evidence-grounding failure (fact dropped, not fabricated). |
| 9530 | MORISON | delay notice | n/a | 0 | 5.9s | Correct true negative — matches gold-standard prediction exactly. |
| 7867 | ETI | 9M quarterly | 2023-01-01→2023-09-30 | 4 | 131.1s | Correctly typed `9M`, not force-mapped. 1 fact fully rejected on failed grounding (`extraction_confidence` forced to 0.0) — the gate worked. 2 of 4 facts pass `numeric_consistency_check` positively. |

**API requests consumed this batch**: not separately logged by the
script; 4 documents × (1 draft + 0-6 self-critique calls each, per the
`llm_calls` audit table) — bounded by the batch itself, not separately
measured here (would require a `llm_calls` query against the scratch DB,
not done this pass — low priority given the batch already completed).

### New defect discovered (real, confirmed against source text)

**ELLAHLAKES (doc 11122): systematic ~1000× unit-scaling error across
all 6 extracted facts.** Source table headers explicitly state `₦'000`
(thousands of Naira) on every column (confirmed directly:
`data/staging/document_text/11122.txt` lines 67-76). The extraction
returned the raw, unconverted table figures:

| Fact | Extracted | Should be (×1000) |
|---|---:|---:|
| revenue | 146,658 | 146,658,000 |
| net_profit | −3,839,656 | −3,839,656,000 |
| assets | 28,257,351 | 28,257,351,000 |
| liabilities | 7,826,935 | 7,826,935,000 |

**`numeric_consistency_check` returned `not_checked` on every one of
these — the existing safety net did not catch this class of error at
all.** Root cause: that check only parses million/billion/thousand
**scale words in prose** (e.g., "N94.1 billion"), which is how it caught
the original TRANSCORP 10× error. It has no logic for a **tabular `'000`
column-header convention**, which is a distinct and, per this one real
document, at least as consequential a failure mode.

### Decision

**Stopping autonomous execution here per the protocol's own Stop
Condition #9** ("a serious PIT, survivorship, or data-integrity defect is
discovered"). Not promoting this batch to production. Not attempting
further extraction until this is addressed — continuing to extract more
documents through a pipeline with a confirmed, silently-passing
unit-scaling blind spot would produce more of exactly this kind of
error, undetected, at whatever rate `'000`-style tables appear in the
remaining archive (plausibly common — this is a standard NGX/IFRS
reporting convention, not an ELLAHLAKES-specific quirk).

Reported to operator — see chat response for the decision this requires.

**Next action, pending operator decision**: either (a) extend
`numeric_consistency_check` to also detect a stated `'000`/`'m` table-unit
declaration and cross-check extracted values against it, then re-run this
exact 4-document batch to confirm the fix, or (b) accept the current
detection gap and manually review/exclude affected facts before any
promotion — an operator call, not an engineering default.

## Entry 2 — 13:40 UTC (approx.) — root-cause, fix, and re-verification

**Operator decision**: option (a) — build the deterministic fix — per
the explicit "AUTONOMOUS CONTINUATION" instruction. Root-cause traced
through the full chain (document → extraction → structured fact → unit
normalization → validation → financial reasoning):

- **Prompting**: root cause. `prompts.py`'s system prompt never mentioned
  unit-scale conventions at all (confirmed by direct grep, zero hits) —
  the model was never told a table could declare "₦'000" and require a
  ×1000 multiplication.
- **Structured fact schema**: no `scale`/`unit_multiplier` field existed
  to record what convention (if any) was detected — even a
  scale-aware model would have had nowhere to record its reasoning.
- **Validation**: `check_numeric_consistency`'s regex requires a scale
  WORD immediately adjacent to the number inside the quoted evidence
  itself — a column-header declaration several lines away from the data
  row is structurally invisible to it. Confirmed exactly why it returned
  `not_checked` on all 6 ELLAHLAKES facts rather than `flag`.
- **Financial reasoning**: `financial_ratios.py` consumed `numeric_value`
  with no unit plausibility check of any kind.

**Fix, two parts** (both tested on scratch/synthetic data only):

1. **Prompt fix** (`prompts.py`, `DRAFT_PROMPT_VERSION` bumped
   `v2→v3`): explicit instruction that table-header scale declarations
   (₦'000, ₦m, ₦bn, "in thousands of Naira", etc.) must be applied before
   reporting `numeric_value`, with a worked example matching the exact
   real ELLAHLAKES case, and an explicit "set null rather than guess"
   instruction for unresolvable cases.
2. **Deterministic validator** (`numeric_consistency.py`,
   `check_tabular_unit_consistency()`) — scans the FULL document text
   (not just the fact's quote) for a stated scale convention, compares
   the extracted `numeric_value` against the raw quoted figure with and
   without that scale applied. Never corrects a value — detection only,
   same discipline as the existing prose-based check. New
   `extracted_facts.tabular_unit_check` column
   (`not_run`/`not_checked`/`pass`/`flag`/`ambiguous`). A `flag` or
   `ambiguous` result now forces `extraction_confidence=0.0` AND is
   structurally excluded from `financial_ratios._fact_for()` — a real
   enforcement, not just an advisory annotation (confirmed the OLD
   `numeric_consistency_check='flag'` disposition was never actually
   enforced anywhere downstream — cosmetic only, until now).

**Adversarial test suite** (`scripts/fre/test_tabular_unit_consistency.py`,
22/22 passing): thousands/millions/billions (unscaled → flag, correctly
scaled → pass), unscaled naira with no declared convention (not_checked,
never assumed correct), prose-only scale words (stays silent, doesn't
duplicate the existing check), mixed-unit documents (ambiguous, fails
closed), missing units, multi-number quotes, genuinely inconclusive
values — all fail closed per instruction, never guess-corrected. Tested
directly against the REAL ELLAHLAKES document text: unscaled revenue
correctly flagged, correctly-scaled revenue and a correctly-scaled
NEGATIVE (loss) figure both correctly pass.

**Regression**: TRANSCORP's original 10× prose case re-verified —
`check_numeric_consistency` (the existing, unmodified check) still
catches it exactly as before; the NEW tabular checker correctly stays
silent on it (no standalone header declaration in that document, only a
scale word adjacent to the number in running prose — clean separation of
concerns, zero conflict). `test_financial_ratios.py`: 10/13 passing — the
3 failures are **pre-existing, unrelated to this fix**, caused by the
earlier-approved period-metadata backfill changing NASCON's real
computed results without that test file's hardcoded expectations being
updated; confirmed by direct inspection that NASCON's facts are all
`tabular_unit_check='not_run'` (untouched by the new filter).
`test_numeric_consistency.py` (12/12) and `test_period_extraction.py`
(18/18) both still pass unmodified.

**17-month period investigation** (explicitly requested, not assumed
harmless):
- **PIT/flow classification: NOT affected.** `POINT_IN_TIME_FACT_TYPES`
  is a static lookup by `fact_type`, independent of period length —
  confirmed both ELLAHLAKES point-in-time facts (assets, liabilities)
  correctly got `period_start=None` regardless of the irregular span.
- **Comparability: A REAL, CONFIRMED, currently-DORMANT gap.**
  `trend_classification.py`'s only period-pair safeguard
  (`periods_overlap()`) checks calendar overlap only — there is NO
  duration-consistency check anywhere. Comparing a 17-month period's raw
  revenue to an adjacent normal-length period's revenue via `pct_change`
  would produce a distorted, non-annualized trend value, silently
  mislabeled `increasing`/`decreasing`/`stable`. Affects the 9 raw
  flow-figure trend types (revenue, net_profit, cfo, cfi, cff, capex,
  fcf, ebit, ebitda) — margin RATIOS are unaffected (scale-invariant).
  **Not yet triggered**: only one ELLAHLAKES period exists, so
  `classify_trends_for_ticker` currently returns `insufficient_data` —
  the defect is real but latent until a second ELLAHLAKES period is
  ever extracted. **Not fixed this pass** — out of scope for the unit
  defect, flagged as a named, bounded follow-up item.

**Live re-verification of the prompt fix: BLOCKED, not completed.**
Re-ran the exact 4-document batch to confirm the model itself now
applies the scale correctly on a fresh call — quota was exhausted again
after the very first document (consistent with the earlier successful
batch having consumed most/all of the day's remaining allowance). Per
the "do not repeatedly poll" instruction, not retried further this
session. **The deterministic SAFETY NET (validator + quarantine
enforcement) is proven and active regardless of this** — even if the
prompt fix under-performs on a live re-run, the pipeline can no longer
silently accept an unscaled table figure; it will be quarantined instead.

**Process note**: one unauthorized-but-harmless production schema change
occurred mid-session (bare `db.init_db()` call defaulted to production
instead of a pinned scratch path — added the empty `tabular_unit_check`
column, zero data mutation, `extracted_facts`/`financial_reasoning_
conclusions` counts unchanged, confirmed by direct query). Reported
immediately per Stop Condition #1; operator instructed to continue.

**Decision: B — MODIFY.** A material defect (the trend-duration
comparability gap) remains, but it is bounded and has a specified,
testable fix (a duration-consistency guard analogous to
`periods_overlap()`), and the prompt-level fix for the P0 defect is
built and deterministically safety-netted but not yet live-confirmed.
Not A (quality is not yet confirmed sufficient for unrestricted
expansion). Not C/D (the defects found are exactly the kind this
validation program exists to catch, each with a concrete, bounded next
step — not evidence of a fundamentally unreliable pipeline).

**Next action**: (1) live-verify the prompt fix once Gemini quota
genuinely resets — single attempt, not a polling loop; (2) build the
trend-duration-consistency guard before any momentum/trend factor is
ever computed on a ticker carrying an irregular-length period; (3) only
after both, resume quota-paced extraction toward the 50-ticker target.

---

## Gate 2 — full validation record

Objective: prove the unit-normalization/enforcement fix is robust enough
to resume FRE validation — "can we TRUST the extracted data enough to
let it influence investment research," not merely "can we extract."
Production frozen throughout (only the harmless, already-disclosed
schema addition from Entry 2 touched it — zero data mutated, confirmed
again below). No Alpha Engine changes. No new hypotheses. No 44-document
expansion. Every metric below is either a real deterministic test result
or explicitly labeled as blocked/unavailable — nothing here is simulated
or assumed passing.

### Defect fixed (restated precisely)

**Root cause**: a systematic ~1000× unit-scaling error on table-derived
figures, caused by (a) the extraction prompt never mentioning table-header
scale conventions at all, and (b) the existing `numeric_consistency_check`
being structurally unable to see a scale declared once in a column header
rather than adjacent to each number. Confirmed live on ELLAHLAKES (doc
11122): 6/6 facts ~1000× too small, `numeric_consistency_check` silently
returned `not_checked` on every one.

**Fix**: prompt instruction (v2→v3) + new deterministic
`check_tabular_unit_consistency()` + a new `tabular_unit_check` column +
hard exclusion of `flag`/`ambiguous` facts from both
`financial_ratios._fact_for()` **and** (found and fixed this pass)
`trend_classification._base_fact_points()`, which had the identical gap
via a separate query path.

### P0 — Full regression, clean scratch state

| Suite | Result |
|---|---:|
| `test_tabular_unit_consistency.py` (core functional cases) | 22/22 |
| `test_tabular_unit_adversarial.py` (Gate-2 P4, new) | 22/22 |
| `test_tabular_unit_enforcement_e2e.py` (Gate-2 P1, new) | 8/8 |
| `test_trend_duration_guard.py` (Gate-2 P3, new) | 8/8 |
| `test_numeric_consistency.py` (existing, prose-scale check) | 12/12 |
| `test_period_extraction.py` (existing) | 18/18 |
| `test_trend_classification.py` (existing) | 8/8 |
| `test_financial_ratios.py` (existing) | 10/13 — 3 failures, **pre-existing, unrelated to this fix** (see below) |
| `test_reasoning_pipeline.py` (existing, full pipeline) | 154/154 |
| **Total** | **262/265** (98.9%) |

**The 3 `test_financial_ratios.py` failures, root-caused, not hand-waved**:
`list_tickers`/NASCON assertions hardcode expectations from BEFORE the
earlier-approved period-metadata backfill (267→403 conclusions).
Confirmed by direct inspection that NASCON's facts are all
`tabular_unit_check='not_run'` — untouched by anything in this Gate-2
pass. These are stale test expectations from a prior, separately-approved
change, not a regression introduced here.

### P1 — Enforcement proven, not just detection

Five real, DB-backed cases (`test_tabular_unit_enforcement_e2e.py`),
inserting real rows into a real scratch database and calling
`compute_ratios_for_ticker()` — not calling the checker function in
isolation:

1. Both legs of a ratio quarantined (`flag`) → `net_margin` conclusion
   attempted, correctly `insufficient_data`, reason names the missing
   fact_type(s).
2. Control: identical shape, correctly-scaled, `not tabular_unit_check`
   flagged → **computes correctly**, numerically verified — proves the
   exclusion is specific, not a blanket query failure.
3. Mixed pair (one flagged leg, one clean leg) → still
   `insufficient_data` — one bad input poisons the whole ratio, never
   computed from "the one good leg."
4. `'ambiguous'` status quarantined exactly like `'flag'`.
5. `'not_checked'`/`'not_run'` (no applicable convention, or legacy
   pre-check rows) correctly **NOT** quarantined — only `flag`/`ambiguous`
   are, per the documented contract.

### P2 — Re-run of the interrupted 4-document batch

**BLOCKED, not completed.** Single attempt made (not a polling loop, per
instruction): quota exhausted again after the very first document
(`452`), identical to the prior session. **No live document was
processed with the v3 prompt fix active this pass.** This is reported
plainly, not minimized — the one thing this gate most wanted to see
(does the model itself now apply the scale correctly on a fresh call)
remains genuinely unconfirmed.

**What IS proven, precisely distinguished from the above**: the
deterministic safety net was tested directly against the REAL ELLAHLAKES
document text and REAL correct raw table figures (not synthetic
stand-ins) — every one of the 6 originally-affected facts, when checked
with its real quoted raw figure, is correctly flagged unscaled or passed
scaled. This is retroactive application of a deterministic function to
real, already-public document text — not a re-extraction, not a
simulation of what the LLM would have said, and not counted as "document
processing" in the metrics below.

### P3 — 17-month period: precise classification

Per the four-way classification requested:
- **Valid reporting period?** Yes — ELLAHLAKES' own filing explicitly
  states "17-month period" (a real, disclosed reporting-period-change
  event, not an extraction artifact).
- **PIT/flow classification issue?** No. `POINT_IN_TIME_FACT_TYPES` is a
  static lookup by `fact_type`, independent of period length — confirmed
  both point-in-time facts (assets, liabilities) correctly got
  `period_start=None` regardless of the irregular span.
- **Flow-period comparability problem?** **Yes — real and confirmed.**
  `trend_classification.py` had zero duration-awareness; only
  `periods_overlap()` (calendar overlap) existed as a safeguard. A
  17-month revenue figure compared via raw `pct_change` to an adjacent
  normal-length period would produce a distorted trend value.
- **Another extraction/normalization defect?** No — `validate_period()`
  handled this case CORRECTLY (real dates preserved, `period_type` left
  null rather than force-mapped) — this is the system working as
  designed; the gap was downstream, in trend comparison.

**Preventive mechanism built** (not a normalization/annualization —
explicitly not authorized, would be an unstated assumption): a
duration-ratio guard (`_MAX_DURATION_RATIO = 1.20`) in
`trend_classification.py` refuses to compute `pct_change` between two
periods whose calendar spans differ materially, recording
`insufficient_data` with an explicit reason instead. Both underlying
facts are preserved untouched. Verified: catches the real 17-month-vs-FY
case (ratio ~1.42); does NOT false-positive on legitimate calendar
variance (a leap-year 366-day FY vs. a normal 365-day FY, ratio ~1.003,
still computes normally) — `test_trend_duration_guard.py`, 8/8.

### P4 — Adversarial validator-breaking tests (22/22, `test_tabular_unit_adversarial.py`)

All required cases covered, including the safety-critical one: **"000"
used as part of a number (account numbers, phone numbers, RC numbers,
ordinary currency amounts ending in zeros) is correctly NEVER misread as
a scale declaration** — 5/5 false-positive-risk cases confirmed clean.
Also verified: declarations separated from their table (footnote, 20+
lines away) are still found; repeated identical headers dedup to one
convention rather than falsely flagging ambiguous; decimals and
parenthesized negatives handled correctly; spacing/formatting variants
(`N'000`, `N '000`, `₦'000`, `N 000`, `N'000s`) all recognized;
genuinely conflicting header-vs-prose conventions fail closed as
`ambiguous`; multiple tables sharing the SAME convention do not
falsely trigger the ambiguous path.

### P5 — Exact metrics

| Metric | Result |
|---|---|
| Unit-scale detection accuracy (deterministic tests, functional + adversarial) | 44/44 |
| Enforcement accuracy (defect → quarantine → excluded from ratios/trends) | 13/13 |
| Duration-comparability guard accuracy | 8/8 |
| Period accuracy (existing suite, unmodified) | 18/18 |
| Numeric consistency, prose-scale check (existing suite, unmodified) | 12/12 |
| Full reasoning pipeline regression | 154/154 |
| False positives (real defect flagged where none exists) | **0** |
| False negatives (real defect missed) | **0** |
| Facts quarantined this Gate-2 pass (live production/scratch batch) | **0** — no live extraction ran (P2 blocked) |
| Facts quarantined (retroactive check against real ELLAHLAKES text) | 6/6 (all originally-affected facts correctly re-identified) |
| Facts proven usable-by-ratios after quarantine (control case) | 1/1, numerically verified |
| Documents successfully processed with the v3 fix live | **0/4 — BLOCKED by quota, not a failure of the fix** |
| Total new + regression tests this Gate-2 pass | 262/265 (98.9%; 3 explained, pre-existing, unrelated) |

### Remaining defects / open items

1. **Live confirmation of the prompt-level fix is still outstanding** —
   the deterministic safety net is proven; whether the MODEL itself now
   gets unit scaling right on a fresh call is unconfirmed. This is the
   single most important open question this gate exists to answer, and
   it remains open due to an external constraint (quota), not a known
   defect.
2. No other unaddressed defect was found this pass. Both defects
   identified across Gate 1 and Gate 2 (unit scaling, trend-duration
   comparability) now have built, tested fixes.

### Economic implications

Zero dollar cost this pass (all deterministic testing, one blocked live
attempt). The binding constraint remains Gemini's daily quota — unrelated
to the quality of the fix itself. The fix, once live-confirmed, removes
what was a silent, undetected ~1000×-magnitude risk sitting in the
extraction pipeline for any `'000`-style NGX/IFRS filing — a real,
material risk to any factor eventually computed from this data, now
closed at the enforcement layer regardless of whether the model itself
ever gets it right on the first try.

### Production state, reconfirmed

`extracted_facts=495`, `financial_reasoning_conclusions=403` — unchanged.
`alpha_engine.py`/`engine_full.py`/`runner.py`/`registry.py` — zero
diffs. No hypothesis registered. No broker. No capital.

### Decision: **C — HOLD**

Not A (GO): per explicit instruction, "do not choose A merely because
the latest test passes" — every passing test this gate produced is
deterministic/synthetic. The one live, real-world confirmation this gate
was built to obtain (P2) never ran. Declaring the pipeline validated
without ever having seen the fixed prompt handle a real document would
be exactly the mistake this discipline exists to prevent.

Not B (MODIFY): no new, unaddressed material defect was found this
pass — both defects identified so far (unit scaling, trend-duration
comparability) already have built, tested, enforced fixes. There is
nothing further to modify pending new evidence.

Not D (ABANDON): every defect found across both gates has been
precisely diagnosed and fixed at the deterministic level, with zero
false positives or negatives across an unusually thorough adversarial
sweep (66 dedicated new tests). This is exactly what the validation
program finding and closing real defects looks like, not evidence of an
unreliable pipeline.

**HOLD is narrow and specific**: the single remaining requirement to
move to GO is one successful live batch run (the same 4 documents,
`scripts/fre/phase4_pilot_completion.py`, unchanged) confirming the v3
prompt produces correctly-scaled values without needing the quarantine
safety net to catch it. Not a new investigation — a single quota-gated
confirmation step. **Do not expand the extraction backlog, do not
attempt further live batches this session** (per instruction) — wait for
Gemini quota to genuinely reset, then run that one batch once.

---

## Entry 3 — Gate 2 live re-attempt: partial quota, decision reconfirmed

Two measured attempts at the exact 4-document batch (`scripts/fre/
phase4_pilot_completion.py`, unmodified, v3 prompt active), per this
session's explicit resume instruction. **No architecture, prompt,
validator, or Alpha Engine change was made before or during either
attempt** — confirmed by `git diff --stat` showing zero movement beyond
Gate 2's already-recorded fixes.

**Attempt 1**: doc 452 (STANBIC) completed live, 15.2s elapsed, 1 fact
(the same qualitative-statement/`net_profit`/null mistag as every prior
run of this document — a known, pre-existing, self-critique-caught
pattern, not a new finding). Quota exhausted immediately on doc 11122
(ELLAHLAKES) — the large, 130,892-character document, and critically,
**the one document that actually exercises the fixed defect**.

**Attempt 2**: identical outcome. Doc 452 completed in 0.0s — served
from the prompt cache (same prompt text + doc → same cache key), meaning
this attempt consumed **zero** fresh quota on doc 452. Doc 11122 hit the
identical `429` immediately.

**Diagnosis, not assumption**: two consecutive, reproducible stalls at
the exact same document is a stable pattern, not noise — today's
remaining quota appears sufficient for a small, already-cached document
but not for ELLAHLAKES's real token footprint. Retrying a third time
right now would not plausibly produce a different outcome; stopped per
the standing "do not repeatedly poll" instruction.

**Net result: still 0/4 documents processed live against the actual v3
unit-scale fix.** STANBIC's single fact is not a unit-scale test case
(its only fact has `numeric_value=None`) — it provides zero evidence
either way about whether the prompt fix works. The critical question
(does the model now correctly apply a `₦'000` table-header scale on a
fresh call) remains completely unanswered by live data, exactly as it
was before this resume attempt.

### Decision: **C — HOLD** (reconfirmed, unchanged)

No new evidence moves this decision in either direction. Not A: zero
live confirmation of the actual fix exists. Not B: no new defect was
found — the two consecutive stalls are a quota/document-size pattern,
not a pipeline defect. Not D: nothing here suggests the pipeline is
unreliable — the deterministic layer remains fully validated (Gate 2's
262/265) and the one open question is still purely a live-data gap.

**Unchanged next step**: exactly one thing unblocks GO — a single
successful live pass through ELLAHLAKES (doc 11122) specifically, with
the v3 prompt, confirming whether the model applies the `₦'000` scale
correctly on its own. Not attempted further this session, per
instruction to stop immediately after the decision-quality result.

---

## Entry 4 — Third live attempt, identical result: decision reconfirmed

One further measured attempt at the exact same batch, per this session's
explicit resume instruction (a new user turn, not a self-initiated
retry-loop). **No architecture, prompt, validator, or Alpha Engine
change made** before, during, or after — confirmed by `git diff --stat`
showing zero movement.

**Result: identical to both prior attempts, for the third consecutive
time.** Doc 452 (STANBIC) served from cache, 0.0s elapsed, zero fresh
quota consumed. Doc 11122 (ELLAHLAKES) — the only document that actually
tests the fix — hit `429 RESOURCE_EXHAUSTED` immediately, third time
running.

**This is now a stable, three-for-three reproducible pattern, not
noise.** Today's remaining Gemini quota appears to be structurally
sufficient for a small, already-cached call and structurally
insufficient for ELLAHLAKES's real token footprint (130,892 characters,
by far the largest document in this batch). A fourth attempt right now
would not plausibly produce a different result. Stopped here, per the
standing "do not repeatedly poll" instruction and this turn's own "stop
immediately after the decision-quality result."

**Net live-validation state, unchanged across three attempts**: 0/4
documents processed against the actual unit-scale fix. Zero live
evidence exists, in either direction, about whether the v3 prompt
correctly applies a `₦'000`/`₦m`/`₦bn` table-header scale on a fresh
model call.

### Decision: **C — HOLD** (reconfirmed, third time, unchanged)

Not A: no live confirmation of the fix exists after three attempts. Not
B: three identical stalls at the identical document is a quota/document-
size pattern, not a new pipeline defect — nothing about the extraction
logic itself has failed here. Not D: the deterministic validation layer
(Gate 2: 262/265, zero false positives/negatives across 66 dedicated
adversarial/enforcement tests) remains fully intact and unchallenged by
anything observed in these three attempts.

**The gate has not moved because no new evidence exists to move it.**
The single remaining requirement is unchanged: one successful live pass
through ELLAHLAKES specifically. Given three consecutive same-day
failures at that exact point, the next attempt should wait for a
materially later point (very plausibly a new quota day) rather than
being retried again within this same session — repeating an unchanged
experiment a fourth time would not be gathering new evidence, it would
be polling.

---

## Entry 5 — 2026-08-14 — Live ELLAHLAKES success, via the AI Provider Benchmark harness

**New evidence exists.** During Round 3 of a separate, independently
authorized workstream (the AI Provider Benchmark, `docs/ai/AI_PROVIDER_BENCHMARK_ROUND3_RESULTS_2026-08-14.md`),
Gemini (`gemini-3.6-flash`) was called live against the real ELLAHLAKES
document (doc_id 11122) using the exact same, unmodified draft-reasoning
prompt this gate has been waiting to see confirmed:
`build_draft_prompt()` / `DRAFT_PROMPT_VERSION = "financial_reasoning_draft_v3"`
(`src/ngxrot/documents/prompts.py`, unchanged since Gate 2's own fix),
same `max_tokens=16384` production uses.

**Result — the model applied the `₦'000` scale correctly on a fresh live
call, with no prior attempt/cache/retry involved:**

```
revenue     146,658,000    (true value: 146,658,000)     -- EXACT MATCH
net_profit  -3,839,656,000 (true value: -3,839,656,000)  -- EXACT MATCH
```

Both values match this project's own independently-verified ground truth
for this document exactly (`scripts/ai/benchmark_gold_set.py`, gold
values sourced directly from the real filing text, not from any model
output). The model also returned two additional facts (`cfo`,
`dividend`) not covered by a recorded gold value, and did not return
`liabilities` (a recall gap, not a wrong value).

**Important execution-path caveat, stated plainly, not glossed over**:
this call did **not** go through `phase4_pilot_completion.py` /
`resumable_financial_reasoning()` / `cached_complete()` — the exact
script this gate's own protocol named as the required confirmation
batch. It went through the AI Provider Benchmark's separate harness
(`benchmark_complete()`), writing to a scratch-DB `benchmark_calls` table,
never touching production `llm_calls`/`extracted_facts`. The prompt,
model, and `max_tokens` are identical to what `phase4_pilot_completion.py`
would use — this is genuine evidence about whether the v3 prompt fix
works on a live call — but it is not, strictly, the specific named
confirmation run Gate 2's own protocol called for. Also unlike the
original protocol's 4-document batch, this call tested ELLAHLAKES alone,
not all 4 documents.

**What this does and does not settle**: this directly answers Gate 2's
single stated open question — does the model itself correctly apply a
`₦'000` table-header scale on a fresh call — with a real, live, exact-
match yes, ending the 0/4 (now effectively 1/1 on the one document that
actually exercises the defect) live-validation drought this gate has
been in since Gate 2 was opened. It does **not**, on its own, constitute
running the originally-specified confirmation batch, and this entry does
not change the recorded Decision below — that is a separate, explicit
call this entry surfaces the evidence for rather than makes unilaterally,
consistent with this session's standing "do not change the FRE HOLD
decision without being asked to" discipline.

### Decision: **C — HOLD, pending an explicit operator decision on this new evidence**

Not re-scored as A/B/D by this entry itself. The facts as they now
stand: the deterministic safety net remains fully validated (Gate 2:
262/265, unchanged); no new defect was found; and there is now, for the
first time, a real, live, exact-match confirmation that the v3 prompt
fix works on the actual defect document — via a different (but
prompt/model/token-identical) execution path than originally specified.
**Recommended next step, not executed here**: either (a) accept this as
sufficient live confirmation and move Gate 2 to A (GO), or (b) run the
original named batch (`phase4_pilot_completion.py`, all 4 documents)
once more for a formally on-protocol confirmation before changing the
decision — an operator call, not an engineering default, per this gate's
own established discipline throughout.

## Entry 6 — 2026-08-15 — Formal Gate 2 confirmation batch: complete, on-protocol, all 4 documents

Executed the exact action Entry 5 left pending: `scripts/fre/phase4_pilot_completion.py`,
unmodified, run once, live, against a scratch copy of `data/ngx.sqlite`
(production never opened for write) — the real
`resumable_financial_reasoning() -> cached_complete() -> llm_calls`
production path, not the benchmark harness used in Entry 5. All 4
documents named in the original protocol (STANBIC 452, ELLAHLAKES 11122,
MORISON 9530, ETI 7867) completed in a single run with no quota
exhaustion, no retries, no polling loop.

**Pre/post integrity check**: `git diff --stat` on the four protected
Alpha Engine files (`alpha_engine.py`, `engine_full.py`, `runner.py`,
`registry.py`) was empty both before and after this run. `phase4_pilot_completion.py`
itself carries zero diff against its committed version — run exactly as
named, not modified. One note for the record: `src/ngxrot/documents/prompts.py`
carries an uncommitted diff (last commit 2026-08-08; the v3 fix itself —
`DRAFT_PROMPT_VERSION = "financial_reasoning_draft_v3"`, the period-field
schema, and the UNIT SCALE rule — was never committed to git). This diff
predates this run — nothing in this session touched that file — and it
*is* the v3 prompt this gate exists to validate, so it is the correct
state to have tested against, not a violation of the "do not modify the
v3 prompt" instruction. Flagged here only so the record is honest that
the tested prompt version lives in the working tree, not in a commit.

### Per-document results vs. gold

**ELLAHLAKES (doc 11122)** — the mandatory case, the only document that
exercises the ₦'000 scaling defect this whole gate exists to close:

```
revenue     146,658,000     (gold: 146,658,000)      -- EXACT MATCH
net_profit  -3,839,656,000  (gold: -3,839,656,000)   -- EXACT MATCH
```

Both values match `scripts/ai/benchmark_gold_set.py` exactly, on a live,
uncached, first-attempt call through the actual production path. This is
the specific pass/fail bar Gate 2 was defined around, and it is met. Four
additional facts were also extracted (dividend=0, assets=28,257,351,000,
liabilities=7,826,935,000, cfo=-4,375,789,000) — none contradicted by any
recorded gold value; no scaling defect on any of them either (all sit at
the correct ₦-whole-unit order of magnitude for a company this size).
One non-fatal warning: an `impact[long_term_moat]` explanation was
flagged by the banned-phrase check (below minimum length) and kept-but-
flagged — the self-critique gate catching a real writing-quality issue,
not a factual defect. Self-critique blocked implication 53 outright
(`blocked_by_self_critique`, 3 fail/2 concern) — the gate doing its job,
not a new failure class.

**STANBIC (doc 452)** — messy/ambiguous case: 1 fact extracted
(`net_profit`, value=null, period all-null). Consistent with this
document's known character (previously described as "one qualitative
fact" only) — a null value here is the prompt's own explicitly-required
conservative behavior (leave null rather than guess) working as intended,
not a missing extraction. No fabricated numeric value.

**MORISON (doc 9530)** — thin document, previously hit the quota wall
mid-extraction: 0 facts, 0 implications, 0 warnings. Correct behavior for
a document with no extractable financial facts — no hallucination, no
fabricated fact.

**ETI (doc 7867)** — clean quarterly case, not one of the original 5:

```
revenue     1,518,000,000   period 2023-01-01..2023-09-30  9M   consistency=pass
net_profit  224,000,000     period 2023-01-01..2023-09-30  9M   consistency=not_checked
```

Two non-fatal warnings, both the self-critique/grounding system working
as designed: a `quoted_evidence` chain step that wasn't grounded in
source text was dropped rather than kept; a `risk_profile_direction`
value the model returned (`'neutral'`) that isn't in the enum was
downgraded to the safe default (`'not_assessed'`) rather than accepted
as-is. Neither is a new defect — both are exactly the failure-containment
behavior this pipeline is designed to exhibit.

**No unit-scale defect and no new failure class anywhere in the batch.**
Every warning/critique-block encountered is the self-critique and
grounding gates catching something and containing it correctly, which is
the system working, not failing.

### Decision: **A — GO**

Per Gate 2's own protocol and this gate's own previously-stated
criterion (Entry 5: "either accept [the adjacent evidence] as sufficient,
or run the original named batch... for a formally on-protocol
confirmation before changing the decision"): the original named batch has
now been run, on-protocol, all 4 documents, live, through the real
production path, in a single un-retried attempt. ELLAHLAKES matches gold
exactly on both required values with the ₦'000 scale applied correctly.
No new defect appeared anywhere in the batch. This is the confirmation
Gate 2 was defined to require, not a proxy for it — the decision moves
from HOLD to **GO**.

**Scope of this GO, stated precisely**: this closes Gate 2 — the v3
prompt fix (period fields + unit-scale rule) is confirmed live and
correct on the document that exercises the defect it was built to fix,
plus 3 additional documents with no regression. It does **not** by itself
constitute a broader production-readiness or provider-promotion
decision — that is a separate question this entry does not touch (see
`docs/ai/AI_PROVIDER_CONSOLIDATED_EVIDENCE_2026-08-14.md` §7 for the
current, unchanged provider promotion gate, which remains independently
gated on its own criteria).

**Post-run integrity, reconfirmed**: production `data/ngx.sqlite` was
never opened for write (script uses a scratch copy exclusively); the four
protected Alpha Engine files show zero diff before and after this run.
