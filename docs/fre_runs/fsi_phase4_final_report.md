# FSI Phase 4 — Final Report

*Point-in-Time Financial Reasoning Memory. Prepared per the owner's
instruction to document findings and freeze this phase as a baseline on
completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase4_implementation_log.md`; this report summarizes
outcomes.*

## Executive summary

FSI Phase 4 built a read-only `CompanyFinancialReasoningMemory.
as_of(ticker, date)` layer over FSI Phase 3's frozen 177 conclusions,
answering exactly one question — "what information and reasoning
conclusions were available as of a historical date" — with zero new
facts, zero new extraction, zero valuation, zero ranking, zero scoring,
zero alpha claims, and zero portfolio outputs. Every conclusion is
gated by its underlying source facts' real, public **filing dates**,
never by financial period dates, per the owner's explicit requirement.
A mechanical audit across all 30 real test points (before/at each of the
15 anchor filings' own filing date) found **zero look-ahead
violations**. A dedicated scratch-fixture test confirms historical
corrections and restatements preserve the original knowledge state, by
construction, without any new restatement-resolution logic being
required.

## Files created

- `src/ngxrot/fre/pit_financial_memory.py` — `as_of()`,
  `audit_no_lookahead()`, and the two disclosed zero-linked-fact
  fallback rules.
- `scripts/fre/fsi_phase4_pit_audit.py` — the 30-real-test-point
  look-ahead audit script.
- `scripts/fre/test_pit_financial_memory.py` — 15 assertions, including
  the restatement-preservation scratch fixture.
- `docs/fre_runs/fsi_phase4_implementation_log.md`,
  `fsi_phase4_final_report.md` (this document).

**No schema change was made in this phase** — Phase 4 reads Phase 3's
existing `financial_reasoning_conclusions`/`financial_reasoning_
conclusion_facts` tables and `documents.filing_date`; nothing new was
added, and Phase 3's own tables/rows were never modified.

## Requirement-by-requirement results

1. **All facts must respect public availability dates, not only
   financial period dates.** Implemented exactly: the gating key is
   `documents.filing_date`, never `extracted_facts.period_start`/
   `period_end`. Verified directly — NASCON's FY2024 ratios (period
   ending 2024-12-31) are not knowable until doc 9460's own filing date
   (2025-03-04), over two months after the period itself ended.
2. **Historical corrections and restatements must preserve the original
   knowledge state.** Verified via a scratch fixture: a conclusion tied
   to a real, pre-restatement fact remains present, unchanged, and
   byte-identical in its own value/method both before and after a
   synthetic later restatement's own filing date. This holds by
   construction — `extracted_facts` and `financial_reasoning_
   conclusions` are both append-only (already true from Phases 1-3), and
   each fact is gated independently by its own filing date — no
   additional restatement-chain-resolution logic was needed or built.
3. **Reasoning conclusions must maintain provenance to the facts
   available at that time.** Every `KnowableConclusion` carries its full
   `source_facts` list (fact_id, role, fact_type, doc_id, filing_date)
   alongside its own `method`/`limitations`/`confidence_tier`, unaltered
   from Phase 3's own values.
4. **No overwriting historical states.** This module has no write path
   of any kind, confirmed by direct query (`documents`,
   `extracted_facts`, and `financial_reasoning_conclusions` row counts
   all unchanged after every test run against real production data).
5. **Every PIT query must be reproducible and auditable.** `as_of()` is
   a pure function of `(ticker, as_of_date)` over frozen data — reruns
   are byte-identical by construction. `audit_no_lookahead()` provides
   the auditability mechanism directly, independently re-checking every
   returned conclusion's own per-fact dates rather than trusting
   `as_of()`'s internal computation.

## PIT leakage audit results

All 30 real test points (one day before + one on the filing_date, for
each of the 15 anchor documents) — **0 violations**. Full detail in the
implementation log Entry 3 and the audit script's own output.

## The zero-linked-fact edge case, resolved and disclosed

4 of Phase 3's 24 `insufficient_data` conclusions have no linked source
fact (there was nothing to link — the finding IS an absence). Two
distinct, disclosed fallback rules apply: period-specific absences
(e.g. CAP's FY2020 `debt_to_equity`) are gated by the earliest filing
for that exact period; ticker-wide absences with no period (e.g. "no
cfo fact exists anywhere for UCAP") are gated by the LATEST of that
ticker's real filings, since a claim about a complete set of filings is
only true once every filing in that set is known. Both verified by
direct test against real data.

## Regression and integrity results

Full suite passes, including all 6 pre-existing FSI Phase 3 test files
plus the 2 new Phase 4 test artifacts (15 assertions + a 30-point audit
script). FRE-6 remains at 40/40 unchanged — Phase 4, like Phase 3,
writes nothing to `extracted_facts`. `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean; `documents` (11,533),
`extracted_facts` (267), and `financial_reasoning_conclusions` (177) row
counts all unchanged after this phase — Phase 4 has no write path to
production at all.

## Known limitations

- **Only 15 real documents / 5 tickers exist in this dataset** — the
  audit's 30 real test points are a small, real, disclosed sample, not
  a statistically powered validation, consistent with every prior
  phase's own honest framing.
- **The restatement-preservation guarantee is verified on a scratch
  fixture, not a naturally-occurring real case** — `restates_fact_id`
  is 0 database-wide as of this baseline; the guarantee is
  architectural (append-only + per-fact gating), not yet exercised by
  a genuine restatement chain in the real data.
- **The zero-linked-fact fallback rules are a reasoned, not empirically
  validated, design choice** for a case that affects only 4 of 177
  conclusions — disclosed as such, not presented as the only possible
  resolution.

## Recommendations for the next phase

1. If a future phase extracts a genuine restatement chain (two facts
   for the identical reporting span, differing values, real
   `restates_fact_id` link), rerun the restatement-preservation test
   against that REAL case in addition to the current scratch fixture.
2. Any future phase touching Phase 3's or Phase 4's shared logic
   (`periods_overlap()`, `confidence_propagation.py`,
   `pit_financial_memory.py`'s own gating rule) should continue the
   established discipline: a genuine architectural change requires
   stopping and requesting approval before modifying already-frozen,
   already-tested shared infrastructure.
3. Per the owner's standing exclusions, no future phase built on top of
   this memory layer should introduce valuation, ranking, scoring, or
   recommendation output without an explicit, separate authorization —
   this phase's guardrail audits (single-ticker scope, no comparative
   fields) are a template for how to verify that boundary mechanically,
   not just assert it.

---

**FSI Phase 4 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
