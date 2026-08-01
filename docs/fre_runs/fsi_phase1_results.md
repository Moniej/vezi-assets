# FSI Phase 1 — Results Report

*Execution report against the frozen pre-registration
(`docs/fre_runs/fsi_phase1_preregistration.md`). Executed exactly per the
approved design, within the stated constraints: no OCR, no vendor data, no
metrics beyond revenue/net_profit, no schema change beyond the two
pre-registered/approved nullable columns, no valuation activation. **Per
instruction, Phase 2 does not begin regardless of these results.***

## 1. Document scoping (performed first, as pre-registered)

`scripts/fre/fsi_scope_candidates.py` — read-only, no database write.
Recorded selection criteria (fixed before running):

1. `source_confidence >= 0.8` (native-text only) — excludes the 4,134
   OCR-pending documents and, as a direct consequence, the known
   GTCO/Zenith FY2023 anchors (confirmed scanned-image/OCR-pending in
   Phase B/C).
2. `char_count > 3000` (a disclosed, reasoned-but-unvalidated floor —
   the real char_count distribution showed a median of 2,054, dominated
   by short corporate-action notices; 3,000 sits just above that median).
3. Document body contains, case-insensitive, at least one revenue term
   ("revenue"/"turnover") AND at least one profit term ("profit after
   tax"/"net profit"/"PAT") — both required.
4. Document body contains at least one Naira monetary indicator (₦, "N"
   immediately followed by a digit, "million"/"billion").

**Result: 2,580 documents passed filter 1-2; 349 passed the full
keyword filter**, spanning 49 distinct real tickers. `doc_type='results_notice'`
was confirmed as the closest (not exhaustive) match to "contains
structured financials," alongside a meaningful share of `doc_type='other'`
— a real, disclosed finding: `documents.doc_type` alone cannot reliably
identify a financial-statement-bearing filing, confirming the concern
named in the pre-registration itself.

## 2. Anchor company selection (recorded criteria)

Five companies selected, each with 3 real filings across different
periods (15 filings total, meeting the ≥15-filing pre-registered floor
exactly): **UCAP** (United Capital Plc), **BUAFOODS** (BUA Foods Plc),
**AFRIPRUD** (Africa Prudential Plc), **CAP** (Chemical and Allied
Products Plc), **NASCON** (Nascon Allied Industries Plc). Selection
criteria: all `doc_type='results_notice'` (the clearest single doc_type
match from scoping), all confirmed native-text, moderate document size
(6,000–17,000 characters — large enough to contain a full income
statement, small enough to read directly), spanning multiple real years
per company (2020–2026) to exercise genuine period variation.

## 3. Extraction — full provenance

`scripts/fre/fsi_extract_phase1.py` — every fact written with document
(`doc_id`), company (`ticker`, via the existing `documents.ticker` join),
metric (`fact_type`), value (`numeric_value`, in raw Naira), period
(`period_start`/`period_end`, the two FSI-Phase-1-approved schema
columns), confidence (`extraction_confidence`), and validation status
(embedded in `description`/the `evidence.quoted_text`, since no dedicated
column exists for it — every fact's description states its own cross
-validation method in full prose, not a bare label). Page/location
provenance uses the extracted text file's own line numbers (`[line N]`,
prefixed onto every `evidence.quoted_text`) — a disclosed proxy for a true
PDF page number, since the plain-text staging files do not preserve
original page boundaries.

**Result: 30/30 facts extracted (15 revenue + 15 net_profit), 100% of the
15-filing pilot, zero failures.** Applied for real: 30 new
`extracted_facts` rows (161→191), 30 new `evidence` rows (195→225),
`documents` unchanged (11,533), `foreign_key_check` clean, verified
before/after via the extraction script's own built-in row-count check.
Backup taken automatically before writing
(`data/ngx.sqlite.pre_fsi_extract_backup_2026-08-01`).

**No external or vendor data was used anywhere in this extraction** — per
instruction. Every cross-check is internal: each filing's own compact
"highlights" narrative restatement compared against its own detailed
"Statement of Profit or Loss" table (both present, as real text, in the
same source document).

## 4. Error categorization (the six required categories)

| Category | Count | Detail |
|---|---|---|
| **Document selection errors** | 0/15 | Every scoped, selected document genuinely contained real, extractable revenue/net-profit figures — the scoping criteria worked as intended on this sample. |
| **Company attribution errors** | 0/15 | Every document's stated company name matched its `documents.ticker` assignment correctly (contrast with the real UCAP/NASCON mismatch found in FRE-3's fact 151 — no analogous case occurred in this pilot's 15 filings). |
| **Metric mapping errors/ambiguities** | 3/15 filings (all 3 AFRIPRUD) | AFRIPRUD is a share registrar with no line item literally called "Revenue" — its own headline metric is "Gross Earnings." Mapped `fact_type='revenue'` to Gross Earnings for all 3 filings, a disclosed judgment call, not a literal single-line read. Additionally, AFRIPRUD's own filings label the equivalent row inconsistently across time ("Gross earnings" in 2020, "Gross Revenue" in 2022) — a real label-inconsistency finding, not an error in the extracted value itself. |
| **Numerical extraction errors/difficulties** | 2/15 filings (BUAFOODS doc 9357, AFRIPRUD doc 7540) | Doc 9357's detailed statement table extracted from the source PDF with columns/labels separated (a real PDF-to-text layout artifact) — reconciled by exact-value matching against the filing's own clean highlights table. Doc 7540 had no explicit "Gross Earnings" row at all — the figure was derived as a 3-line sum (revenue from contracts + interest income + other income) and confirmed by rounding to the highlights table. Both resolved correctly; both would likely defeat a naive single-line-regex parser without additional structure-aware logic. |
| **Period errors** | 0 direct extraction errors; 1 disclosed cross-period finding | CAP's FY2021 filing (doc 5911) states its own FY2020 comparative revenue as ₦8,876mn, which does not match doc 4508 (the actual FY2020 filing)'s own originally-reported ₦8,737mn — most likely a restatement following CAP's merger with Portland Paints (completed 1 July 2021). Each fact is recorded from its own filing's own stated figure; no cross-filing reconciliation was attempted or needed. |
| **Unit errors** | 0/15 | All units (thousands vs. millions of Naira) were explicit in every source document and converted consistently to raw Naira during compilation; spot-checked during compilation, not just assumed. |

## 5. Comparison against pre-registered thresholds

| Threshold | Result |
|---|---|
| Success: ≥80% correct extraction on ≥15 filings | **Met: 30/30 = 100%** (both revenue and net_profit correctly extracted and internally cross-validated for all 15 filings) |
| Stop condition (scoping yields <15 candidates) | Not triggered — 349 candidates found, 15 selected |

**This exceeds the pre-registered success bar decisively.** Stated
honestly, or the result would misrepresent its own scope: this is a
**small, non-random, hand-selected pilot** (5 companies chosen partly for
document size manageability) validated **entirely via internal,
same-document cross-checks**, never against an independent external
source (no vendor data was used, per instruction) — the pre-registration's
own disclosed limitation ("if no independent secondary source is
available... the validation is weaker") applies to all 30 facts here,
not a subset. A 100% result on this specific pilot does not imply 100%
extraction accuracy would hold at real acquisition scale, across the
full native-text archive, or across company types not sampled here
(financial-services firms proved to have real, disclosed metric-mapping
complexity that a manufacturing/consumer-goods company like CAP or
NASCON did not).

## 6. A real cross-phase finding, surfaced by this execution

Adding real `revenue`/`net_profit` facts caused `valuation_engine.py`
(FRE-6)'s readiness gate to flip from `NOT_READY` to `READY` for
`dcf`/`ev_ebitda`/`pe` on all 5 anchor tickers for the first time on this
platform — exactly the future transition FRE-6's architecture was built
to make once real data existed. This surfaced a genuine, previously
-latent bug: `value_company()` called `adapter.compute()` unconditionally
once `is_ready()` returned `True`, and every adapter's `compute()` still
correctly has no implemented formula (`NotImplementedError`) — an
**uncaught crash**, not the intended graceful "ready, but not yet
implemented" disclosure. Fixed with a minimal, targeted change (catching
`NotImplementedError` specifically and downgrading to a disclosed
readiness note) — verified this produces **zero numeric valuation output,
identical to before the fix**; the fix changes only how the "ready but
unimplemented" state is reported, never what gets computed. This is
**not valuation activation** — no number is ever produced, before or
after — and is documented here rather than silently patched, since it is
a direct, real consequence of this execution's own approved scope.
`scripts/fre/test_valuation_engine.py` was updated to assert the new,
correct state (5 tickers now READY-but-unimplemented, `results` still
always empty) rather than left asserting a now-false claim.

## 7. Verification performed

| Check | Result |
|---|---|
| `scripts/fre/fsi_extract_phase1.py` dry run vs. apply | Identical values in both, confirmed before writing |
| Row-count check (before/after, all tables) | Only `extracted_facts` (+30) and `evidence` (+30) changed; everything else, including `documents`, byte-identical |
| `PRAGMA foreign_key_check` | Clean |
| `scripts/check_db_safety.py` | PASS, 0 violations |
| `scripts/test_reasoning_pipeline.py` (pre-existing) | 154/154 PASS, unchanged |
| `scripts/fre/test_evidence_graph.py` (FRE-2) | 29/29 PASS, unchanged |
| `scripts/fre/test_company_memory.py` (FRE-3) | 16/16 PASS, unchanged |
| `scripts/fre/test_reaction_check.py` (FRE-4) | 16/16 PASS, unchanged |
| `scripts/fre/test_company_thesis.py` (FRE-5) | 21/21 PASS, unchanged (the new facts have no `investment_implications` row, so they never surface in any thesis) |
| `scripts/fre/test_valuation_engine.py` (FRE-6) | **40/40 PASS after the fix above** (was a crash before) |

## 8. What this does and does not establish

- **Does establish**: on this specific, small, hand-verified pilot,
  native-text NGX filings can yield reliable revenue/net_profit figures
  via careful internal cross-checking, with real, disclosed complications
  (sector-specific metric mapping, PDF-layout artifacts, cross-period
  restatements) that a future automated pipeline would need to handle
  explicitly, not assume away.
- **Does not establish**: extraction accuracy at scale, accuracy without
  internal highlights/table redundancy (many real filings may lack the
  convenient dual-restatement structure these 15 happened to have),
  accuracy for company types not sampled, or readiness for any real
  valuation computation (FRE-6's adapters remain formula-unimplemented
  regardless of readiness state).
- **Phase 2 (any line item beyond revenue/net_profit, any OCR work, any
  vendor relationship, any real valuation formula) does not begin as a
  result of this report** — per instruction, this stops here for review.

## Addendum — limitations formally recorded (2026-08-01, on approval)

Per the owner's explicit approval of this report ("the result confirms the
pre-registered hypothesis for the limited scope: native-text NGX filings
can reliably produce Revenue and Net Profit facts **under controlled
conditions**"), the following limitations are recorded formally as
accepted, load-bearing context for any future phase that cites this
result — not new findings, but the boundaries of this result, stated
explicitly rather than left implicit in the prose above:

1. **Small, hand-selected pilot** — 15 filings, 5 companies, chosen partly
   for document-size manageability (6,000–17,000 characters) and a
   confirmed `results_notice` doc_type; not a random or representative
   sample of the 349 real candidates the scoping step found, still less
   of the full native-text archive.
2. **No external validation** — every cross-check was internal
   (same-document highlights vs. detailed statement table); no
   independent secondary source, vendor feed, or owner-confirmed anchor
   value was used anywhere, per instruction. The pre-registration's own
   disclosed weaker-validation caveat for this case applies to all 30
   facts, not a subset.
3. **No OCR validation** — scoped entirely to the 7,399 native-text
   documents; the 4,134 OCR-pending documents (36% of the archive,
   including the known GTCO/Zenith FY2023 anchors) were untouched and
   remain untested for this extraction task.
4. **Limited financial taxonomy** — exactly two metrics (`revenue`,
   `net_profit`); no balance-sheet, cash-flow, EBITDA/EBIT, or ratio data
   was extracted in this pass.
5. **Not production-scale** — 15 filings is a feasibility floor (the
   pre-registration's own minimum), not a throughput or coverage
   commitment; no automation, scheduling, or bulk-processing mechanism
   was built or evaluated.

These five limitations bound every claim in this report and must be
carried forward explicitly by any phase that treats Phase 1 as a
precedent, rather than re-verified or assumed away.

---

*This concludes FSI Phase 1. Stopping here and awaiting review.*
