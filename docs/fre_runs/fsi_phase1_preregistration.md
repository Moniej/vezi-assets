# Financial Statement Intelligence — Phase 1 Pre-registration

*Pre-registration only. No implementation, no extraction, no schema
change, no dependency installation. Per instruction, this document is
written and frozen BEFORE any execution begins — the same two-gate
discipline already used for FRE-5
(`docs/fre_runs/fre5_thesis_folding_preregistration.md`) and every LIM
training experiment. Builds on the approved roadmap review
(`docs/fre_runs/roadmap_review_financial_statement_intelligence.md`).*

## Why this is scoped as a narrow pilot, not the full acquisition

The roadmap review named two real, unresolved owner-level decisions
blocking the *full* Financial Statement Intelligence program: the
OCR-engine choice (open since 2026-07-16) and a possible vendor
relationship (a cost decision). **Neither is required to test feasibility
on the native-text subset that already exists** (7,399 documents,
`source_confidence >= 0.8`, confirmed by direct query). Per this whole
program's repeated discipline (FRE-2's classifier, FRE-3's
strategy-narrative deferral, FRE-5's fold-experiment narrowing), this
pre-registration scopes Phase 1 to **exactly what is executable today
without either blocked decision**, and explicitly defers everything else.

## A real finding, checked before scoping this pilot

`documents.doc_type` does not reliably separate "this document contains a
full income statement/balance sheet" from a short corporate-action
notice. The real distribution is dominated by `other` (7,727), `governance`
(915), `agm` (794), `board_meeting` (590), `closed_period` (590),
`results_notice` (357), `dividend` (328) — no `doc_type` value cleanly
means "annual/quarterly report with structured financials." `results_notice`
is the closest candidate but is not confirmed sufficient or exhaustive.
**Consequence for this pre-registration**: Phase 1's first real step is a
scoping pass to identify actual financial-statement-bearing documents
within the native-text subset — this is itself pre-registered as a
method step, not assumed as already solved.

## Phase 1 objective

Determine, on a small, deliberately narrow pilot, whether **revenue** and
**net profit** — the two figures most likely to be prominently and clearly
stated in any NGX annual/quarterly report (typically in an opening
highlights section, distinct from the detailed statement tables) — can be
reliably extracted from native-text filings with real, measured accuracy.
This is a feasibility test, not a claim that extraction works; the
pre-registered outcome could honestly be negative, exactly like several
LIM RB-series experiments.

## Scope — exactly what Phase 1 will do

1. **Schema step (additive, FRE-1 pattern, done first, verified before
   anything else)**: add two nullable columns to `extracted_facts` —
   `period_start`, `period_end` — via `ALTER TABLE ... ADD COLUMN` inside
   `try/except OperationalError`, exactly the pattern FRE-1 already built
   and tested for `causal_chain_steps.implication_layer`/`.reasoning_mode`.
   Verified with the full existing regression suite before any data is
   written, per the standing recovery-and-safeguard discipline
   (`docs/fre_runs/incident_2026-08-01_prod_db_wipe.md`).
2. **Document scoping**: from the 7,399 native-text documents, identify a
   candidate set that plausibly contains structured revenue/net-profit
   figures (starting from `doc_type IN ('results_notice', 'other')`,
   narrowed by a lightweight keyword/structure check — e.g., presence of
   "revenue"/"turnover" and "profit after tax"/"PAT" near a currency
   figure — never assumed from `doc_type` alone).
3. **Anchor selection**: identify 3–5 real NGX companies whose relevant
   filings are CONFIRMED native-text (explicitly avoiding the known
   GTCO/Zenith FY2023 OCR gap already on record from Phase B/C — those
   specific anchors do not qualify for a native-text-only pilot). Anchor
   selection is itself a Phase 1 output, not pre-named here, since
   confirming native-text status per candidate requires the same
   real-data check every other FRE phase has insisted on before deciding.
4. **Extraction**: deterministic parsing first (regex/structural, matching
   Phase B's proven approach for corporate-action figures), LLM-assisted
   only where deterministic parsing fails, every LLM-assisted figure
   routed through the existing, unmodified `grounding.py` check — no new
   grounding mechanism invented.
5. **Storage**: two `extracted_facts` rows per filing (`fact_type='revenue'`,
   `fact_type='net_profit'`), each with `numeric_value`, `period_start`,
   `period_end` populated, `evidence_id` linked — the same shape every
   other fact type on this platform already uses, no new table.
6. **Validation**: for each anchor company, cross-check the extracted
   figure against the SAME source document's own summary/highlights
   restatement where one exists (an internal, same-document cross-check),
   and — only where an owner-confirmable independent secondary source is
   readily available — a secondary check. No external data is fetched as
   part of this pre-registration itself; sourcing the cross-check is
   Phase 1's own execution step, not performed here.

## What Phase 1 explicitly does NOT do (deferred, named, not attempted)

- No OCR of the 4,134 scanned/lower-confidence documents.
- No vendor relationship or paid data source.
- No extraction of any line item beyond `revenue`/`net_profit` (EBITDA,
  balance-sheet items, cash-flow items are explicitly Phase 2+, only
  attempted if Phase 1 succeeds).
- No wiring into `valuation_engine.py`'s adapters — that remains a later,
  separately-verified step even if Phase 1 succeeds outright.
- No change to `company_intelligence.py`'s `UNAVAILABLE_FIELDS` — that
  stays exactly as disclosed until real coverage, not a single pilot,
  justifies revisiting it.

## Pre-registered success / partial / failure criteria

Set now, before any extraction is attempted, per the standing discipline
that a threshold stated after seeing results is not a threshold:

- **Success**: on a pilot sample of at least 15 real filings across the
  3–5 anchor companies, both `revenue` and `net_profit` are correctly
  extracted (matching the same-document cross-check, and any secondary
  source where available) for **≥80%** of filings, with zero
  `grounding_check='failed'` rows silently ignored (a failed grounding
  check is itself reported, not excluded from the denominator).
- **Partial**: 40–79% correct extraction rate — informative, not a green
  light to proceed to Phase 2 without redesign; report exactly which
  failure modes recur (e.g., a specific report-format era or sector
  the deterministic parser handles poorly).
- **Failure**: <40% correct extraction rate, or the document-scoping step
  itself fails to identify a usable candidate set of at least 15 filings
  from the native-text subset — reported honestly, with the specific
  blocking reason, exactly like LIM's RB-1/RB-3 negative results.

The 80%/40% bounds are a disclosed, reasoned-but-not-empirically-derived
choice (there is no prior extraction-accuracy data on this exact task to
calibrate against) — stated explicitly as a judgment call, not hidden as
if it were evidence-derived, the same honesty this platform has applied to
every other unvalidated threshold (Part 1's ontology, FRE-4's liquidity
floor).

## Stop condition

If the document-scoping step (item 2 above) cannot identify at least 15
plausible candidate filings from the native-text subset, stop and report
that as the finding — do not lower the bar or substitute OCR/vendor data
to manufacture a larger sample, since doing so would silently violate this
phase's own "native-text only, no blocked decisions" scope.

## Dependencies

FRE-1's additive-schema pattern (reused, not re-invented). Phase A's
existing native-text archive (7,399 documents, unchanged). `grounding.py`
(existing, unmodified). The GTCO/Zenith OCR-gap finding (Phase B/C,
inherited, explicitly excludes those specific companies from this pilot's
anchor set).

## Risks

- **Anchor scarcity**: confirming genuinely native-text, figure-bearing
  filings for 3–5 companies may itself prove harder than expected, given
  the `doc_type` ambiguity already found — flagged as the most likely
  cause of an early, honest stop.
- **False precision from a same-document cross-check only**: if no
  independent secondary source is available for a given anchor, the
  validation is weaker (checking a document against its own restatement of
  the same figure, not a truly independent source) — disclosed per-anchor
  in the results, not averaged away.
- **Small-sample instability**: 15 filings is a feasibility floor, not a
  statistically powered sample — any accuracy figure from Phase 1 carries
  the same small-n caveat this program has applied everywhere else (Part
  11's evaluation framework).

## Review checkpoint

Per the same two-gate discipline as FRE-5: this pre-registration itself
must be reviewed and approved before Phase 1 execution (schema step,
scoping, extraction, validation) begins. Results are reported separately,
afterward, exactly as they come out — including a negative or partial
result, honestly, without redesigning the criteria after seeing them.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
