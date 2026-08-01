# FSI Phase 2 — Final Implementation Report

*Financial Statement Intelligence, Phase 2: Balance Sheet, Cash Flow, and
EBITDA/EBIT Intelligence. Prepared per the owner's governing
implementation-order instruction, on completion of all four approved
stages. This report is the ninth deliverable it itself describes; it is
the final artifact expected before the owner's review and before any
FSI Phase 3 discussion begins.*

---

## 1. Executive implementation summary

FSI Phase 2 extended verified financial-statement intelligence beyond
Phase 1's two metrics (revenue, net_profit) to ten more: assets,
liabilities, equity, cfo, cfi, cff, capex, fcf, ebitda, ebit — plus the
shared infrastructure needed to extract them safely (period
classification independent of a filing's own label, config-driven
terminology mapping, restatement conflict detection, and a four-tier
confidence hierarchy). Implementation proceeded in the owner's specified
order — shared infrastructure, then Balance Sheet, then Cash Flow, then
EBITDA/EBIT — across the same 15 real, hand-verified anchor filings used
throughout FRE-6 and FSI Phase 1 (UCAP, BUAFOODS, AFRIPRUD, CAP,
NASCON).

The pilot wrote **76 new financial-statement facts** (42 balance sheet +
13 cash flow + 21 ebitda/ebit) on top of Phase 1's original 30, for
**106 financial-statement facts total**, spanning 5 tickers. Every fact
carries full provenance (source label, document, period, confidence
tier) and traces to real, re-read filing text — no external or vendor
data was used anywhere in this phase.

One genuine architectural defect was discovered mid-implementation
(Stage 1's `restatement_detection.py` produced false positives on
legitimate nested reporting periods), was reported and approved for
correction per the owner's explicit authorization, fixed with a minimal,
scoped change, and is now permanently regression-anchored against
recurrence. This is documented in full in Entries 4–5 of
`docs/fre_runs/fsi_phase2_implementation_log.md` and summarized in
section 5 below.

No valuation activation, no portfolio reasoning, and no alpha generation
occurred at any point — `valuation_engine.py`'s `compute()` methods
still unconditionally refuse to run on real data (verified by regression
after every stage), exactly as in FRE-6 and FSI Phase 1.

## 2. Files modified

**New library modules** (shared infrastructure, Stage 1):
- `src/ngxrot/fre/period_normalization.py`
- `src/ngxrot/fre/terminology_mapping.py`
- `src/ngxrot/fre/restatement_detection.py` (corrected in Stage 3's
  Entry 5 — see section 5)

**New config**:
- `configs/financial_statement_terminology.toml` (created in Stage 1;
  extended in Stage 3 with `[fcf]`; extended in Stage 4 with two real
  AFRIPRUD "Profit Before Finance Cost(s) and Tax" synonyms)

**Modified config**:
- `configs/fact_taxonomy.toml` (`[financial_statements]` group extended
  from 2 to 12 leaves)

**New extraction scripts**:
- `scripts/fre/fsi_extract_phase2_balance_sheet.py` (Stage 2)
- `scripts/fre/fsi_extract_phase2_cash_flow.py` (Stage 3)
- `scripts/fre/fsi_extract_phase2_ebitda_ebit.py` (Stage 4)
- `scripts/fre/fsi_phase2_fix_restatement_false_positives.py` (one-off
  correction script, Stage 3's architectural fix)

**New tests**:
- `scripts/fre/test_period_normalization.py` (23/23)
- `scripts/fre/test_terminology_mapping.py` (8/8)
- `scripts/fre/test_restatement_detection.py` (9/9, including the new
  permanent NASCON anchor)

**Modified tests**:
- `scripts/fre/test_valuation_engine.py` (the financial-statement-fact
  count assertion updated four times as real data grew: 30 → 72 → 85 →
  106 — same discipline applied consistently, never left stale)

**Modified core infrastructure** (Stage 1 only):
- `schema/schema.sql` (additive columns, see section 3)
- `src/ngxrot/db.py` (`init_db()` additive `ALTER TABLE` blocks for the
  same three columns, existing-DB migration path)

**Documentation**:
- `docs/fre_runs/fsi_phase2_preregistration.md`,
  `fsi_phase2_execution_plan.md` (pre-implementation, already approved)
- `docs/fre_runs/fsi_phase2_implementation_log.md` (live journal, 6
  entries)
- `docs/fre_runs/fsi_phase2_final_report.md` (this document)

No file outside `docs/fre_runs/`, `scripts/fre/`, `configs/`,
`src/ngxrot/fre/`, `schema/schema.sql`, and `src/ngxrot/db.py` was
touched. No LIM, AI Intelligence Layer, Quant Engine, or existing
production pipeline code was modified.

## 3. Schema changes

All additive, all nullable, all wrapped in `try/except
sqlite3.OperationalError` in `db.py`'s existing-DB path and mirrored in
`schema/schema.sql`'s fresh-DB path — no column was ever removed,
renamed, or made non-nullable:

```sql
period_type      TEXT CHECK (period_type IN ('Q1','Q2','Q3','Q4','H1','H2','9M','FY')),
confidence_tier  TEXT CHECK (confidence_tier IN
                   ('direct_reported','mapped_equivalent','derived','interpretation')),
restates_fact_id INTEGER REFERENCES extracted_facts(fact_id),
```

All three added to `extracted_facts` in Stage 1, before any Stage 2-4
fact was written. No further schema change occurred in Stages 2-4 (as
pre-registered — the columns were sufficient for balance sheet, cash
flow, and ebitda/ebit alike).

## 4. Extraction results

| Stage | Fact types | New facts | Filings with data | Filings with a disclosed gap |
|---|---|---|---|---|
| 2 — Balance Sheet | assets, liabilities, equity | 42 (14+14+14) | 14 of 15 | CAP doc 4508 (no absolute figures, only a leverage ratio) |
| 3 — Cash Flow | cfo, cfi, cff, capex, fcf | 13 (4+3+4+1+1) | 5 of 15 | 10 of 15 (UCAP x3, AFRIPRUD x3, CAP x2, BUAFOODS x2 — abridged filings with no cash-flow statement at all) |
| 4 — EBITDA/EBIT | ebit, ebitda | 21 (12+9) | ebit: 12 of 15; ebitda: 9 of 15 | UCAP x3 (bank, PBT only, never EBIT/EBITDA); CAP's ebitda x3 (no D&A ever disclosed) |

**Total: 76 new facts, 106 financial-statement facts overall** (with
Phase 1's original 15 revenue + 15 net_profit).

Per-ticker fact-type coverage is uneven by design, not by omission — it
directly reflects what each real filing actually discloses:
- **UCAP** (bank): revenue, net_profit, assets, liabilities, equity only
  (no cash-flow statement, no EBIT/EBITDA concept applies to a bank's
  income-statement structure).
- **CAP**: revenue, net_profit, ebit in all 3 filings; assets/
  liabilities/equity in 2 of 3 (doc 4508 has none); fcf + capex in 1 of
  3 (doc 4508 only); no ebitda anywhere (no D&A disclosed), no cfo/cfi/
  cff anywhere.
- **AFRIPRUD**: revenue, net_profit, assets, liabilities, equity, ebit,
  ebitda (derived) in all 3 filings; no cash-flow data anywhere.
- **BUAFOODS**: revenue, net_profit, assets, liabilities, equity, ebit,
  ebitda in all 3 filings; cfo + cff in 1 of 3 (doc 6664 only, narrative
  only); no cfi or capex anywhere.
- **NASCON**: the most complete ticker — revenue, net_profit, assets,
  liabilities, equity, cfo, cfi, cff, ebit, ebitda in all 3 filings; only
  capex/fcf are absent (never separately broken out in NASCON's own
  tables).

## 5. Validation results

**Confidence-hierarchy discipline**: every one of the 76 new facts
carries an explicit, per-metric (never per-filing-assumed) tier —
`direct_reported` (e.g. CAP's literal "EBIT" line, NASCON's tabulated
EBITDA), `mapped_equivalent` (e.g. "Operating Profit" → ebit, AFRIPRUD's
"Profit Before Finance Cost and Tax" → ebit), or `derived` (AFRIPRUD's
EBITDA = EBIT + D&A, the one architecturally-permitted derivation,
exercised for the first time in this pilot with a full derivation trace
in each fact's own description). `confidence_tier='interpretation'` was
written **zero times**, confirmed by direct query — the hard rule holds.

**Accounting-identity check** (Stage 2, `assets = liabilities + equity`,
enabled by FRE-1's ontology and used for real validation for the first
time on this platform): 12 of 14 filings match to the exact naira, 2
show a trivial (≤N1mn) rounding residual. A strong, positive correctness
signal for the extraction methodology as a whole.

**Terminology-mapping bug caught by the extraction script's own
assertion** (Stage 2): `map_label_to_concept("TOTAL SHAREHOLDERS FUND")`
(UCAP's real, apostrophe-less label) initially returned `None`; fixed by
adding the exact real variant to the config, not by loosening the
matching logic.

**Restatement-detection architectural defect** (discovered Stage 3,
corrected Stage 3, approved by the owner): the original rule flagged any
*overlapping* period with a differing value as a restatement candidate.
NASCON — the only ticker among the 15 anchors with both an interim (H1
2024) and a later annual (FY2024) filing — exposed this: its real FY2024
facts were falsely marked as "restating" its own real H1 2024 facts,
because the periods legitimately overlap without being the same
reporting span. Six facts in production (3 written silently during
Stage 2, 3 during Stage 3) carried this false `restates_fact_id`.
Corrected by requiring **equivalent reporting spans** (exact
`period_start`/`period_end` match) rather than mere overlap — the
minimal change that separates a genuine restatement (same period,
disagreeing values, the real CAP case) from cumulative/nested reporting
(different periods that happen to overlap, the real NASCON case). The
six false links were nulled via a dedicated backup-then-apply script,
touching no other field. Both the CAP anchor (genuine restatement, must
still be detected) and a new permanent NASCON anchor (nested reporting,
must never be flagged) pass — 9/9 in `test_restatement_detection.py`.
Full root cause, affected records, and verification are in
`fsi_phase2_implementation_log.md` Entries 4–5.

**Real cross-filing consistency checks** (not designed in advance, found
along the way): AFRIPRUD doc 7540's own FY2022 comparative column
exactly reproduces doc 6349's own reported EBIT (1,155,807k); BUAFOODS
doc 6664's Operating Profit + Other income − Finance charges reproduces
its own stated PBT to the exact thousand. Both are positive,
un-forced signals that the extracted figures are internally coherent,
not merely plausible-looking.

## 6. Regression results

Full suite, run after every stage, final state after Stage 4:

| Suite | Result |
|---|---|
| `check_db_safety.py` | PASS |
| `test_reasoning_pipeline.py` | ALL CHECKS PASSED |
| `test_period_normalization.py` | 23/23 |
| `test_terminology_mapping.py` | 8/8 |
| `test_restatement_detection.py` | 9/9 |
| FRE-2 `test_evidence_graph.py` | 29/29 |
| FRE-3 `test_company_memory.py` | 16/16 |
| FRE-4 `test_reaction_check.py` | 16/16 |
| FRE-5 `test_company_thesis.py` | 21/21 |
| FRE-6 `test_valuation_engine.py` | 40/40 (after 4 stale-count updates, same pattern each time — a growing real fact count is expected, not a regression) |

Production database integrity, verified directly after Stage 4:
`PRAGMA integrity_check` → `ok`; `PRAGMA foreign_key_check` → clean,
database-wide; `documents` count unchanged at 11,533 across every stage
of Phase 2 (zero unintended write paths); `restates_fact_id` non-NULL
count is exactly 0 database-wide (no genuine restatement occurred among
any real Phase 2 fact — expected, per Entry 2's own disclosed
methodological note); backward compatibility confirmed — every prior
FRE module (2 through 6) still passes unmodified except for the single,
disclosed, expected fact-count assertion in FRE-6.

## 7. Performance observations

All extraction was manual, hand-verified re-reading of 15 real filings
(no automated OCR, no LLM-based extraction, no vendor feed) — the same
methodology as Phase 1, scaled to 4x the fact types. No performance
bottleneck was encountered: all writes completed in well under a second
per stage, `foreign_key_check` and `integrity_check` are effectively
instantaneous at this data volume (267 facts, 11,533 documents). The
main real cost in this phase was investigative, not computational —
determining, per filing, which figures are safe to extract under the
"never assume equivalence" constraint (e.g. recognizing UCAP's banking
structure precludes EBIT/EBITDA, or that BUAFOODS's Group vs Company
columns require a consistent choice already established in earlier
stages).

## 8. Known limitations

- **Small, hand-selected pilot** (15 filings, 5 tickers) — not
  externally validated, not production-scale, same limitation already
  disclosed for Phase 1 and still true here.
- **Coverage is uneven and filing-dependent, not systematic**: which
  fact types exist for a given ticker/period depends entirely on what
  that specific filing happened to disclose, not on a complete or
  predictable schema. A consumer of this data must check per-fact
  provenance, not assume coverage.
- **EBITDA precision varies by source**: NASCON's and AFRIPRUD's EBITDA
  values are exact (from a precise table or a full derivation);
  BUAFOODS's are narrative-only, rounded to 3 significant figures. Both
  are `direct_reported` (or `derived`), but not equally precise — this
  is disclosed per-fact in each description, not uniformly flagged at
  the fact_type level.
- **No EBIT/EBITDA concept for financial institutions in this
  architecture yet**: UCAP (bank) and, by extension, any future bank/
  insurance-sector filing will always yield zero ebit/ebitda facts under
  the current "never assume PBT ≈ EBIT for a bank" rule. This is a
  deliberate scope boundary, not a gap to silently patch — a genuine
  bank-appropriate profitability metric (if ever needed) would require
  a new, explicitly-designed fact_type, not a reuse of ebit/ebitda —
  extending to a new sector's metrics remains a future, explicitly-
  scoped decision.
- **The restatement-detection mechanism remains a safety net, not a
  live-firing feature**: across all 76 new Phase 2 facts, it correctly
  found zero genuine restatements (by design, since Phase 2 never
  extracts comparative-column data) and, after the Stage 3 fix, zero
  false positives. It has still only ever been validated against one
  real genuine-restatement case (CAP) and one real nested-period case
  (NASCON) — a third, different real scenario could in principle expose
  another edge this pilot didn't encounter.
- **`derived` tier has exercised exactly one formula** (`ebitda = ebit +
  d_and_a`, AFRIPRUD only) — the architecture's broader derivation
  capacity (e.g. `fcf = cfo - capex`) has never been exercised on real
  data, since no filing in this pilot provided both inputs for the same
  period.

## 9. Recommendations for FSI Phase 3

1. **Expand the anchor set before adding new metrics.** The single
   sharpest lesson of Phase 2 is that real architectural gaps (the
   restatement false-positive) only surface when a new *combination* of
   real filings is processed (here: a ticker with both interim and
   annual reports). Before extending to new fact types, consider
   deliberately adding a few more tickers/filing-pattern combinations
   (e.g. a ticker with a genuine mid-year restatement, or one filing
   both audited and unaudited results for an overlapping period) to
   pressure-test shared infrastructure against real edge cases, not just
   the two currently-anchored ones.
2. **Consider a bank/insurance-appropriate profitability fact_type**
   before attempting broader financial-sector coverage — UCAP and
   AFRIPRUD's real structural differences from manufacturers are large
   enough that reusing ebit/ebitda for financial institutions would
   require either a new, explicitly-designed metric or an explicit,
   owner-approved decision to leave that sector permanently out of
   EBIT/EBITDA scope.
3. **Ratio derivation** (named in the original Phase 2 pre-registration
   scope but not part of this execution plan's four stages) remains
   unimplemented and would be a natural, explicitly-scoped next step —
   e.g. current ratio, debt-to-equity, now computable from Stage 2's
   real assets/liabilities/equity facts.
4. **`fcf = cfo - capex` derivation** is architecturally ready but has
   never fired on real data; if Phase 3 adds filings where both cfo and
   capex are disclosed for the same period, this is a good, already-
   designed capability to validate for the first time.
5. Continue the discipline that has held for five phases running: design
   → owner approval → implement → honest results (including negative/
   gap findings) → stop for review. This report is itself the checkpoint
   for that discipline; no further action will be taken until reviewed.

---

**FSI Phase 2 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any FSI Phase 3 work
begins.
