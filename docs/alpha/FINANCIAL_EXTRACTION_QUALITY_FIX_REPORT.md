# Financial Extraction Quality Fix Report — 2026-08-12

Production untouched throughout: `extracted_facts=495`, `financial_
reasoning_conclusions=267` — verified after every step below, not just at
the end. Every fix was built, tested, and measured against scratch copies
and real (free-tier) Gemini API calls. Alpha Engine, hypothesis registry,
Research Workspace/Query architecture: not touched. No production
migration has been applied or requested to be auto-applied — §13 names
exactly what is ready and awaiting explicit approval.

---

## 1. Period-schema defect

Root-caused precisely, not assumed. `src/ngxrot/documents/prompts.py`'s
extraction JSON schema requested `fact_type`, `description`,
`numeric_value`, `qualification_date`, `payment_date`, `agm_date`,
`closure_date` — **no `period_start`, `period_end`, or `period_type`
field at all.** Confirmed by reading the prompt source directly, not by
inference from the output.

A second, independent defect was found while designing the fix: `PILOT_
FACT_TYPES` (the list of fact types the prompt ever requests) covered
only 7 of the 14 types `configs/fact_taxonomy.toml`'s `[financial_
statements]` section actually supports — missing `assets`, `liabilities`,
`equity`, `cfo`, `cfi`, `cff`, `capex`, `fcf`, `cogs`, `gross_profit`
entirely. The extraction pipeline could not have produced a balance-sheet
fact even with perfect period handling.

A third, deeper defect was found only by testing the fix against real
production data: even where balance-sheet facts DO exist (the 10-ticker
production set), `financial_ratios._fact_for()`'s exact `period_start`
match meant **`debt_to_equity` (liabilities/equity, both point-in-time)
could never compute for any ticker, ever** — a point-in-time fact has no
meaningful `period_start`, so matching it against a flow fact's real
`period_start` can never succeed. Verified directly: DANGCEM, one of the
best-covered production tickers, had `debt_to_equity = insufficient_data`
on all 4 of its real periods before this fix, despite having real
liabilities/equity facts for every one of them. Not a coverage gap — a
matching-logic gap, and a materially bigger finding than the missing
prompt fields alone.

---

## 2. Period extraction fix

Three coordinated changes, each additive, none a redesign:

1. **`prompts.py`**: added `period_start`/`period_end`/`period_type` to
   the JSON schema, with explicit inline guidance distinguishing
   point-in-time (balance sheet: `period_start` always null) from flow
   (revenue/profit/cash-flow: both dates required) from genuinely
   irregular spans (real dates kept, `period_type` left null rather than
   force-fit into `Q1-Q4/H1/H2/9M/FY`). Widened `PILOT_FACT_TYPES` to the
   full 14-type `[financial_statements]` set (additive-only, same
   precedent Stage 10D already set for this exact constant). The
   **non-negotiable rule stated verbatim in the prompt**: "NEVER infer a
   period from the document's filing date, retrieval date, or any date
   other than the one the document gives for THAT figure... leave
   period_start/period_end/period_type as null rather than guessing."
2. **`extract.py`**: new `validate_period()` function — the actual
   enforcement layer, since a prompt instruction alone is a request, not
   a guarantee. Nulls (with a warning, never silently) any period_type
   outside the enum, any malformed date, any point-in-time fact with a
   model-provided `period_start`, any `period_start > period_end`, and —
   the specific defense against the brief's named failure mode — any
   `period_end` that exactly equals the document's own `filing_date`
   (a real reporting period essentially never ends on its own filing
   date; this is the exact signature of a retrieval-date substitution
   bug).
3. **`financial_ratios.py`**: `_fact_for()` now matches point-in-time
   fact types on `period_end` alone, ignoring `period_start` — required
   because real production data turned out to have an **inconsistent
   legacy convention** (DANGCEM's balance-sheet facts have
   `period_start=NULL` as expected; NASCON's have a real, non-null
   `period_start` from an older extraction pass). Requiring `NULL`
   specifically broke NASCON's own working regression test during
   development — the fix ignores `period_start` unconditionally for
   these types, which is correct for both conventions without needing a
   data migration first.

`DRAFT_PROMPT_VERSION` bumped `v1 → v2` for auditability (the cache key
itself already changes automatically since it hashes full prompt text —
this bump is about being able to tell which contract produced a row).

---

## 3. Numeric-consistency defect

TRANSCORP net_profit, fact from the original 2026-08-12 pilot: the linked
evidence quote correctly says "Profit after Tax improved 188%
year-on-year to N94.1 billion" — verified directly against the source
document text. The structured `numeric_value` field stored
`941,000,000,000` — exactly 10× too large. Traced further: the
implication's own self-critique reasoning (8 real LLM-generated
questions) correctly references "N94.1 billion" multiple times — the
model understood and reasoned about the correct number; the defect is
narrowly isolated to how that already-correct understanding was
serialized into the structured JSON field for that one fact.
`check_grounding` could not have caught this: the quote is verbatim
correct, so grounding reports `passed`. This is a distinct failure mode
from a hallucinated quote, and needed its own, different check.

---

## 4. Numeric validation fix

New module `src/ngxrot/documents/numeric_consistency.py`,
`check_numeric_consistency(numeric_value, quoted_text)` — deterministic,
regex-based, no LLM judgment call involved at all (per the brief's own
explicit instruction). Parses every number+scale-word magnitude
(million/mn, billion/bn, trillion/tn, thousand) out of the quoted
evidence text and compares each against `numeric_value`:

- **`pass`** — a parsed magnitude matches within 2% (rounding/formatting
  slack).
- **`flag`** — no candidate matches, but at least one candidate's ratio to
  `numeric_value` lands within 3% of a round factor (10×, 100×, 1000×, or
  the reciprocal) — the specific, narrow signature of a scale/decimal
  transcription error, deliberately not a generic "these differ" check
  (which would false-positive constantly on real documents that mention
  both this year's and last year's figures in the same quote).
- **`not_checked`** — nothing to compare (null value, or a quote with no
  parseable number+scale-word, e.g. a qualitative statement or a bare
  per-share figure).

**Never auto-corrects.** On a `flag`, `extract.py` halves the fact's
`extraction_confidence` (from the existing 0.3 unreviewed-LLM floor to
0.15) and records a warning naming the discrepancy — the exact
`extracted value → consistency check → PASS=usable / FLAG=review-queue`
flow the brief specified, implemented by reusing the platform's existing
confidence-floor-plus-warnings pattern (the same mechanism
`check_grounding` already uses for a failed quote), not a new
architecture.

New schema column `extracted_facts.numeric_consistency_check` (`not_run`/
`not_checked`/`pass`/`flag`), added via the same additive
`ALTER TABLE`-with-try/except pattern every prior migration on this
platform uses — mirrors the existing `grounding_check` column exactly.

**Verified against the exact real case and the task's own three named
examples** — all pass:

| Case | Stored value | Quoted magnitude | Result |
|---|---:|---:|---|
| TRANSCORP net_profit (real) | 941,000,000,000 | 94,100,000,000 | **flag** |
| 94.1bn vs 941bn (task example) | 941,000,000,000 | 94,100,000,000 | **flag** |
| 1.25bn vs 12.5bn (task example) | 12,500,000,000 | 1,250,000,000 | **flag** |
| 940m vs 940bn (task example) | 940,000,000,000 | 940,000,000 | **flag** |
| Genuinely correct value | 94,100,000,000 | 94,100,000,000 | pass |
| Multi-figure quote, no round-factor relationship | 408,000,000,000 | 408bn & 197bn | pass (no false positive) |

**Retroactively applied to the original pilot's 10 facts** (pure
deterministic re-check against already-extracted data — zero quota
cost): the TRANSCORP fact is the only one flagged; the other 9 all
correctly `pass` or `not_checked`, with zero false positives.

---

## 5. Period backfill methodology

New script `scripts/fre/backfill_flow_fact_period_start.py`
(dry-run / `--scratch` / `--apply`, mirroring the existing
`backfill_entity_relationship_recorded_at.py` pattern).

**Qualifying criteria (a fact is backfilled iff ALL hold):**
1. `fact_type` is a flow type, never point-in-time (assets/liabilities/
   equity are excluded categorically — a snapshot has no start to
   backfill regardless of what's stored).
2. `period_start IS NULL` (never overwrites an existing value, even one
   from an older/inconsistent convention).
3. `period_end IS NOT NULL` (the anchor the derivation needs).
4. `period_type` is one of the 8 CHECK-constrained enum values, each with
   a fixed, unambiguous duration (FY=1yr, H1/H2=6mo, Q1–Q4=3mo, 9M=9mo).
   Anything outside this set is **rejected**, not guessed — checked
   defensively even though the schema's own CHECK constraint should make
   it unreachable.

**Derivation**: `period_start = period_end − period_type's fixed
duration + 1 day`. Pure arithmetic on values already recorded on the fact
itself; no other document or fact is consulted, nothing is invented.

**PIT semantics**: unaffected by construction — the backfill touches only
`period_start` (completing the fact's own period description); it never
touches `filing_date`, `retrieved_date`, or `as_of_date`. A fact's actual
knowability date is unchanged.

**Run against production, dry-run (read-only)**: 51 qualifying facts, 0
rejected.

**Run against a scratch copy, applied + re-derivation of every ticker's
ratio/flag/trend conclusions**:

```
financial_reasoning_conclusions before: 267
financial_reasoning_conclusions after:  403
net new: 136
duplicate groups: 0
```

This is the COMBINED effect of the period backfill (Fix 3) and the
point-in-time matching fix (§1/§2's third defect) together, measured on
the current 10-ticker production set plus the 6 previously-blocked
tickers (`AIRTELAFRI, DEAPCAP, GEREGU, LASACO, UACN`, and `VERITASKAP`'s
qualifying facts) — a materially larger, more accurate number than the
80-row estimate from the earlier, incomplete ad-hoc version of this same
backfill (which predated the point-in-time matching fix and only covered
6 tickers in isolation, not the full re-derivation).

**Not applied to production.** Awaiting explicit operator approval — see
§13.

---

## 6. Before/after extraction quality

Measured on a real, fresh, live Gemini API call against `doc_id=9485`
(TRANSCORP FY2024 earnings release — the exact document that exposed the
original numeric bug), with both fixes active:

| Fact | Type | Value | period_start | period_end | period_type | consistency_check |
|---|---|---:|---|---|---|---|
| revenue | flow | 408,000,000,000 | 2024-01-01 | 2024-12-31 | FY | pass |
| ebit | flow | 149,000,000,000 | 2024-01-01 | 2024-12-31 | FY | pass |
| **net_profit** | flow | **94,100,000,000** | 2024-01-01 | 2024-12-31 | FY | **pass** |
| assets | point-in-time | 751,600,000,000 | **null** | 2024-12-31 | FY | pass |
| equity | point-in-time | 271,700,000,000 | **null** | 2024-12-31 | FY | pass |
| dividend | (corporate action) | 10,100,000,000 | 2024-01-01 | 2024-12-31 | FY | pass |

**6/6 facts have correct, complete period metadata** (flow facts get both
dates + type; point-in-time facts correctly get `period_start=null`).
**6/6 pass numeric consistency**, including the exact metric that was
wrong before — `net_profit` is now `94,100,000,000`, matching the source
document exactly (previously `941,000,000,000` on the same underlying
document). Whether the corrected value on this specific rerun reflects
the prompt fix directly or ordinary LLM run-to-run variance cannot be
proven from a single sample — **what §4's retroactive check proves
instead is that the safety net now exists**: had this rerun reproduced
the 10× error, `numeric_consistency_check` would have caught it, which it
did not fail to do on the original (unfixed) extraction of the same
document.

---

## 7. Before/after deterministic usability

The metric the brief names as the one that matters:

| | Before this fix | After this fix |
|---|---:|---:|
| Facts with any period metadata at all | 0% (0/10, original pilot) | 100% (6/6, TRANSCORP re-extraction) |
| Facts usable by `compute_ratios_for_ticker`/`classify_trends_for_ticker` | 0 | 6/6 flow+point-in-time facts structurally eligible (full ratio/trend computation requires a second period to pair against, not yet available for this single-document rerun) |
| `debt_to_equity` computable for ANY production ticker | **Never** (matching-logic gap, confirmed on DANGCEM) | **Yes** — confirmed computing correctly for DANGCEM (4/4 periods), CAP, NASCON on real production data |
| Production `financial_reasoning_conclusions`, full re-derivation (scratch) | 267 | 403 (+136, 0 duplicates) |

---

## 8. Cost and quota impact

**Dollar cost: $0** (free tier, confirmed via `configs/llm_provider.toml`
and direct observation — unchanged from the original pilot).

**Quota, measured directly, not assumed**: the free tier's daily cap
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `gemini-3.6-flash`)
is confirmed **20 requests/day**. The original pilot (§Phase 3, prior
report) consumed the full daily quota. This fix's own Phase 4 re-run hit
the same wall: one document's `draft_reasoning` call succeeded live (a
genuine, fresh, post-fix extraction); its `self_critique` calls failed
with the identical `429 RESOURCE_EXHAUSTED` daily-quota error. **This is
not a new problem this fix introduced — it is the same, already-measured
constraint**, now confirmed to persist across sessions/days of
cumulative usage, not just within one pilot run.

Cost-per-metric, stated in the correct unit (quota-days, not currency,
per the same reasoning as the original pilot report):

| Metric | Value |
|---|---:|
| Cost per document | $0 / ~1–2 requests of the 20/day quota (draft + 0–3 self-critique calls) |
| Cost per usable financial fact (period-complete, consistency-passed) | $0 / a fraction of one document's quota share |
| Cost per usable financial period | Not yet measurable — needs a second period per ticker to compute a trend, not reached this pass |
| Cost per ticker with 5 years of coverage | Unchanged from the prior audit's estimate (~10–13 days of quota-bound extraction for the 44-ticker backlog) — **this fix does not change the throughput ceiling, only what each unit of that scarce throughput now produces** |

The token footprint per call grew (3,377 input / 9,237 output tokens for
the TRANSCORP `draft_reasoning` call, vs. an average of ~2,700/2,000
tokens in the original pilot) — expected and acceptable, driven by the
wider `PILOT_FACT_TYPES` set (17 vs. 7 types) and the added period-schema
instructions; does not affect the free-tier request-count quota, which is
what actually binds.

---

## 9. Remaining failure modes

Disclosed, not hidden:

- **Self-critique could not be exercised post-fix** in this pass —
  blocked by the same daily quota the draft call itself nearly exhausted.
  The self-critique gate's own behavior against period-complete,
  consistency-checked facts remains unverified until quota resets.
- **A single fresh re-extraction is not a representative sample.** The
  full 5-ticker pilot the brief asked for (clean annual, quarterly/YTD,
  balance-sheet-heavy, messy/ambiguous, TRANSCORP-type) could not be
  completed today — only the TRANSCORP-type case was actually re-run live
  against the corrected pipeline. The other four categories are validated
  only via §2's deterministic unit tests (`test_period_extraction.py`,
  `test_numeric_consistency.py`), not a live LLM re-run.
- **The numeric-consistency check has a real, disclosed blind spot**: it
  can only catch a *round-factor* magnitude error (10×/100×/1000×) — a
  non-round transcription error (e.g. a digit-transposition producing
  94.1bn → 84.1bn) would not be flagged. This was a deliberate design
  choice to keep the false-positive rate near zero, not an oversight, but
  it means the check is a floor, not a complete guarantee — the same
  honest framing `check_banned_phrase`'s own docstring already uses for
  its analogous limitation.
- **The point-in-time matching fix (§1/§2) surfaced a genuine, disclosed
  data-consistency finding**: production's own balance-sheet facts follow
  two different historical conventions (`period_start=NULL` vs. a
  populated legacy value) depending on which extraction pass produced
  them. The fix handles both correctly, but the underlying inconsistency
  itself is not resolved — a future full data-quality pass could
  normalize it, not required for this fix to work correctly today.
- **`period_end == filing_date` rejection could, in principle, reject a
  genuinely same-day disclosure** (rare but not impossible for certain
  regulatory notices) — accepted as a deliberate false-positive risk in
  exchange for closing the exact retrieval-date-substitution failure mode
  the brief named explicitly; not observed to misfire on any real
  document in this pass.

---

## 10. GO / MODIFY / STOP decision

**MODIFY → conditional GO on the specific, narrow next step named below.**

Not STOP: every fix was verified against real data, real LLM calls, and
the platform's own existing regression suite (`test_financial_ratios.py`,
`test_financial_health_flags.py`, `test_trend_classification.py`,
`test_reasoning_pipeline.py` — all passing after these changes, zero
regressions introduced). The exact bug that motivated this whole exercise
(TRANSCORP's 10× net_profit error) is confirmed both retroactively
detectable (§4) and absent on a fresh post-fix extraction of the same
document (§6). `debt_to_equity` — completely broken platform-wide before
today — now computes correctly on real production data.

Not a full GO on the 44-ticker backlog yet: the daily quota blocked
completion of the full 5-document Phase 4 pilot the brief specified, so
self-critique behavior against the corrected pipeline and the other four
document-category cases remain unverified by a live run (only by unit
test). Scaling to 44 tickers today would repeat the same "spend scarce
quota before confirming quality" mistake this whole two-phase exercise
exists to avoid.

**Exact next action, in order:**
1. When daily quota resets, complete the remaining 4 documents of the
   Phase 4 pilot (STANBIC-messy, ELLAHLAKES-format-diverse, MORISON-thin,
   plus one clean quarterly case) — a small, bounded, already-scoped
   continuation, not a new pilot design.
2. Once that confirms the fix generalizes (not just on the one document
   already verified), request explicit operator approval for:
   a. Applying `backfill_flow_fact_period_start.py --apply` to
      production (already tested clean on scratch: +136 conclusions, 0
      duplicates, 0 production risk).
   b. Applying the `numeric_consistency_check` schema migration to
      production (purely additive, already applied cleanly to scratch).
3. Only after 1–2: consider the 44-ticker backlog extraction — still
   paced by the same measured 20-requests/day ceiling, not a number to
   be wished away.

**The Alpha Engine remains frozen. No production data was modified. No
hypothesis is registered by this document.**
