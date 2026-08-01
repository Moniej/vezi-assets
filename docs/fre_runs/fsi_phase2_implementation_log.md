# FSI Phase 2 — Implementation Log

*Live journal, appended to throughout implementation, not reconstructed
afterward. Per `docs/fre_runs/fsi_phase2_execution_plan.md` (approved) and
the owner's implementation-order instruction. Each entry is dated/staged
and kept even if later superseded — append-only, matching this program's
own data discipline applied to its own documentation.*

## Entry 0 — Start

Implementation begins exactly per the approved execution plan. Order:
(1) shared infrastructure, (2) Balance Sheet Intelligence, (3) Cash Flow
Intelligence, (4) EBITDA/EBIT Intelligence. Validation anchors: UCAP
(period normalization), AFRIPRUD (terminology mapping), CAP (restatement
handling) — all real, already on hand from Phase 1.

**Scope clarification, recorded here rather than silently absorbed**: the
owner's implementation-order message specifies Cash Flow Intelligence as
Operating + Investing + Financing cash flow + Capex + derived FCF — five
items, more granular than the execution plan's own original sketch (which
only named `cfo`/`capex`/`fcf`). Treated as the owner's authoritative
refinement of Phase 2's own approved cash-flow scope, not a
self-introduced expansion — two additional fact_type leaves (`cfi`, `cff`)
are added on this basis, disclosed here explicitly.

## Entry 1 — Shared infrastructure: schema migration (complete)

Backed up production DB first
(`data/ngx.sqlite.pre_fsi_phase2_schema_backup_20260801_201841`). Added
three additive, nullable columns to `extracted_facts`:
`period_type` (CHECK'd enum, 8 values), `confidence_tier` (CHECK'd enum,
4 values, matching the execution plan's hierarchy exactly),
`restates_fact_id` (self-referencing FK, modeled on
`investment_implications.corroborates_implication_id`). Both
`schema/schema.sql` (fresh-DB path) and `src/ngxrot/db.py` (existing-DB
`ALTER TABLE` + `try/except OperationalError` path) updated, exactly
mirroring the proven FRE-1/FSI-Phase-1 pattern.

**Verification, in order**: (1) scratch-copy test — 191 rows before/after,
byte-identical content, new columns present and all-NULL, `foreign_key_
check` clean; (2) real-DB application — same checks, all pass, zero
row-count drift anywhere across all 27 tables; (3) full regression —
`test_reasoning_pipeline.py` 154/154, FRE-2 29/29, FRE-3 16/16, FRE-4
16/16, FRE-5 21/21, FRE-6 40/40, `check_db_safety.py` clean. No
unexpected discovery, no bug, no deviation from the execution plan's
exact DDL sketch.

## Entry 2 — Shared infrastructure: config + three library modules (complete)

`configs/fact_taxonomy.toml`'s `[financial_statements]` group extended
from 2 to 12 leaves (added `assets`, `liabilities`, `equity`, `cfo`,
`cfi`, `cff`, `capex`, `fcf`, `ebitda`, `ebit`). New
`configs/financial_statement_terminology.toml` seeded with Phase 1's
confirmed real synonyms (AFRIPRUD's Gross Earnings/Gross Revenue,
NASCON/CAP/UCAP's consistent "Revenue"/"Profit for the..." labels) plus
reasonable, disclosed synonyms for the new metrics (not yet
real-filing-confirmed for balance sheet/cash flow -- to be verified
against actual filing text in Stages 2-3 below, and the config updated
if a real label differs from what's guessed here).

Three new library modules: `period_normalization.py`
(`classify_period_type`, calendar-month-span-based, never trusting a
filing's own label), `terminology_mapping.py` (`map_label_to_concept`,
config-driven, case-insensitive, returns `None` on no match, never a
guess), `restatement_detection.py` (`find_restatement_conflicts`,
read-only, modeled on `investment_implications`' existing corroborates/
contradicts pattern).

**Validated against all three named real anchors**:
- **UCAP (period normalization)**: 23/23 checks pass. All 15 real Phase 1
  facts' stored `period_start`/`period_end` re-classify correctly,
  INCLUDING the exact anchor case -- doc 4248's real 9-month span
  classifies as `'9M'`, not a standalone quarter, despite the filing's
  own "Q3 2020" headline.
- **AFRIPRUD (terminology mapping)**: 8/8 checks pass. Both of AFRIPRUD's
  real, differently-labeled synonyms ("Gross earnings", "Gross Revenue")
  correctly map to `revenue`; a real typo found in AFRIPRUD's own filing
  text ("TOTAL ASSESTS") is kept as a literal, disclosed synonym rather
  than silently corrected.
- **CAP (restatement handling)**: 6/6 checks pass, using a disposable
  scratch fixture (never written to production) reproducing the real
  CAP FY2020 comparative-vs-original numbers (8,876mn vs. 8,737mn).
  **Disclosed methodological note**: Phase 2, like Phase 1, only extracts
  each filing's OWN reported period, never a comparative prior-period
  column restated inline -- so this mechanism is not expected to fire
  naturally among Phase 2's own new facts; it is validated here as a
  safety net using the real CAP numbers on a controlled fixture, not as
  a live extraction result.

**Full regression after this stage**: `test_reasoning_pipeline.py`
154/154, FRE-2 29/29, FRE-3 16/16, FRE-4 16/16, FRE-5 21/21, FRE-6
40/40, `check_db_safety.py` clean. No unexpected discovery, no bug, no
deviation from the execution plan.

**Shared infrastructure (Stage 1) is now complete.** Proceeding to Stage
2, Balance Sheet Intelligence, per the approved implementation order.

## Entry 3 — Stage 2: Balance Sheet Intelligence (complete)

`scripts/fre/fsi_extract_phase2_balance_sheet.py` re-reads the actual
filing text (`data/staging/document_text/<doc_id>.txt`) for all 15 of
Phase 1's own anchor documents and extracts `assets`/`liabilities`/
`equity` triples, applying `classify_period_type`,
`map_label_to_concept` (with an `assert` on every mapped label — a real
implementation safety net, not decorative, see below), and
`find_restatement_conflicts` per filing. Every fact written with
`confidence_tier='direct_reported'`. Dry-run first, then `--apply`.

**Real discoveries, disclosed as they happened, not smoothed over**:

- **Terminology-config bug, caught by the script's own assertion, not by
  me**: `map_label_to_concept("TOTAL SHAREHOLDERS FUND")` (no apostrophe
  — UCAP's actual real label, docs 6911/10772) returned `None`, because
  only the apostrophe'd variant existed in
  `configs/financial_statement_terminology.toml`. Fixed by adding the
  exact literal variant (see the config's own `[equity]` note, updated
  same-day). Re-ran dry-run clean afterward. This is precisely the kind
  of gap the "no silent substitution" constraint exists to surface loud
  rather than let pass quietly.
- **AFRIPRUD doc 4245 line-wrap artifact (real, document-conversion
  issue, not a code bug)**: the PDF-to-text conversion produced
  `TOTAL LIABILITIES`/`TOTAL EQUITY` numeric values in an order that did
  not match the filing's own stated column headers. Resolved by
  cross-referencing AFRIPRUD's own narrative "highlights" bullets (a
  second, independent same-document source) — the corrected pairing is
  confirmed correct because the accounting identity
  (`assets = liabilities + equity`) holds EXACTLY only under that
  pairing, and holds nowhere near exactly under the wrapped order. This
  is the accounting-identity check (built in FRE-1's ontology, unused
  until now) doing real validation work for the first time on this
  platform.
- **CAP doc 4508 has no extractable balance-sheet figures (real,
  disclosed document-content limitation)**: the filing discloses only a
  leverage ratio, no absolute assets/liabilities/equity figures. No fact
  written for this doc_id — disclosed here explicitly rather than
  silently skipped. This is why Stage 2 produced 14, not 15, of each
  balance-sheet fact_type.

**Accounting-identity validation results** (`liabilities + equity -
assets`, computed per filing from the newly-written facts): 12 of 14
filings match to the exact naira, 2 show a trivial rounding residual
(BUAFOODS doc 6664: −1,000; NASCON doc 8801: +1,000,000 — both
negligible against tens-of-billions-scale figures, consistent with
source-table rounding, not treated as errors). This is a strong
correctness signal for the extraction methodology as a whole, achieved
using an existing ontology mechanism exactly as FRE-1 designed it to be
used.

**Write results**: `extracted_facts` 191 → 233 (+42 = 14 assets + 14
liabilities + 14 equity), `evidence` 225 → 267 (+42, one per fact),
`documents` unchanged at 11,533. Pre-write backup taken automatically
(`data/ngx.sqlite.pre_fsi_phase2_balance_sheet_backup_20260801`).
`PRAGMA foreign_key_check` clean before and after.

**Full regression after this stage**: `test_reasoning_pipeline.py`
154/154, FRE-2 29/29, FRE-3 16/16, FRE-4 16/16, FRE-5 21/21,
`check_db_safety.py` clean. FRE-6 initially showed **39/40** — one
stale assertion in `scripts/fre/test_valuation_engine.py` still
hardcoded the FSI-Phase-1-era expectation of exactly 30
financial-statement facts. Confirmed via direct query that the real,
correct new total is 72 (`assets=14, liabilities=14, equity=14,
net_profit=15, revenue=15`), updated the assertion and its explanatory
comment to match the new real state (same discipline as the identical
update already made once before, when Phase 1 first took the count
from 0 to 30), re-ran: **40/40 pass.**

**Stage 2 (Balance Sheet Intelligence) is now complete.** Proceeding to
Stage 3, Cash Flow Intelligence, per the approved implementation order.

## Entry 4 — BLOCKER discovered during Stage 3: restatement detection

false-positives on nested (non-restating) periods (implementation

paused, awaiting review)

**Stage 3 extraction itself succeeded**: `scripts/fre/
fsi_extract_phase2_cash_flow.py` re-read all 15 anchor filings' text.
Real finding, disclosed: only 5 of 15 contain any cash-flow-statement
data at all (UCAP x3, AFRIPRUD x3, CAP x2 of 3, BUAFOODS x2 of 3 have
NONE — abridged results announcements with no cash-flow section). The
5 that do: BUAFOODS doc 6664 (narrative cfo+cff only), CAP doc 4508
(a literal, directly-reported "Free Cash Flow" line item plus a
narrative "net capital expenditure" figure — an edge case the design
expected only as *derived*, not reported; added `[fcf]` to
`configs/financial_statement_terminology.toml` to record this), and
NASCON docs 8801/9460/10929 (the only ticker with full tabulated
cfo/cfi/cff in every filing). Dry-run clean, applied: `extracted_facts`
233→246 (+13), `evidence` 267→280 (+13), `foreign_key_check` clean.

**Then a genuine architectural bug surfaced**, via the restatement
check that fired automatically during the `--apply` write path
(`find_restatement_conflicts`, built and validated in Stage 1). NASCON
is the only ticker among the 15 anchors with BOTH an interim (H1 2024,
doc 8801, period 2024-01-01→2024-06-30) and a later annual (FY2024,
doc 9460, period 2024-01-01→2024-12-31) filing. These two periods
legitimately OVERLAP (H1 is nested inside FY) and legitimately have
DIFFERENT values (a half-year cash/balance figure differs from a
full-year one) — this is not a restatement, just two different
reporting granularities of the same real year. `find_restatement_
conflicts`'s logic (any overlap + differing value = conflict) cannot
tell this apart from a true same-period comparative-column restatement
(the CAP anchor it was actually validated against in Stage 1). It fired
anyway, and the calling extraction scripts wrote the resulting
(incorrect) `restates_fact_id` without a check for this case, because
no such case existed in Stage 1's own validation set.

**Confirmed scope, by direct query** — exactly 6 facts in production
currently carry a `restates_fact_id`, all 6 false positives of this
same kind:
- fact 228 (NASCON assets, FY2024) incorrectly marked as restating
  fact 225 (NASCON assets, H1 2024) — written **silently during Stage
  2**, not noticed or disclosed at the time; same for fact 229→226
  (liabilities) and 230→227 (equity).
- fact 241 (NASCON cfo, FY2024) incorrectly marked as restating fact
  238 (NASCON cfo, H1 2024) — written just now during Stage 3; same
  for fact 242→239 (cfi) and 243→240 (cff).

No other ticker/fact_type combination is affected (10929's FY2025 facts
correctly show no conflict, since 2025 does not overlap 2024).

**Why this blocks continuing rather than being a Stage-3-scope fix**:
the numeric values, periods, labels, and confidence tiers of all 6
facts are correct and require no change — only the `restates_fact_id`
field is wrong, and it is wrong because of a genuine gap in Stage 1's
own shared `restatement_detection.py` module (approved, tested, and
frozen before Stage 2 began). Correcting it means changing that
module's overlap logic (e.g. requiring the periods to be the same
span, or excluding proper-subset containment, rather than treating any
overlap as a conflict) — a design change to already-approved shared
infrastructure, not a new Stage-3 extraction decision. Per the
governing instruction ("No redesigns unless a genuine implementation
blocker is discovered... stop immediately, document it with evidence,
explain why it blocks implementation, and wait for approval"), this
qualifies, and implementation is paused here.

**Nothing further has been written to production since this was
found.** Stage 4 (EBITDA/EBIT Intelligence) has not been started.
Full regression has not yet been re-run for Stage 3. Awaiting review
and direction before any further action (including whether to null the
6 affected `restates_fact_id` values, redesign the overlap logic, or
some other remediation the owner prefers).

## Entry 5 — Architectural correction: restatement detection now

requires equivalent reporting spans (approved, complete)

**Root cause** (restated precisely): `find_restatement_conflicts`'s
original SQL matched on period OVERLAP (`NOT (period_end < ? OR
period_start > ?)`). Overlap is necessary but not sufficient evidence of
a restatement -- a company's own interim filing and its own later annual
filing for the same year legitimately overlap in calendar time while
reporting two different, equally valid spans. The module's own Stage 1
validation only ever tested the CAP case (two filings both claiming the
identical FY2020 span), so this gap was invisible until a ticker with
both an interim and annual filing among the 15 anchors actually
exercised it -- NASCON, the first such ticker processed.

**Architectural change**: the WHERE clause now requires
`f.period_start = ? AND f.period_end = ?` -- an EXACT match on both
bounds ("equivalent reporting spans"), not merely a non-empty
intersection. This is the minimal change that separates the two cases:
a true restatement is, by definition, the same reporting period
reported twice with a different number; nested/cumulative reporting is,
by definition, a different reporting period. Full updated docstring and
rationale recorded directly in `src/ngxrot/fre/restatement_detection.py`.

**Affected records, exact scope** (confirmed by direct query before
touching anything): exactly 6 rows in `extracted_facts` had a non-NULL
`restates_fact_id` anywhere in the database, all 6 the same false
positive --
- fact 228 (NASCON assets, FY2024) → had falsely pointed to fact 225
  (NASCON assets, H1 2024); fact 229 (liabilities) → 226; fact 230
  (equity) → 227. Written silently during Stage 2, not disclosed at the
  time.
- fact 241 (NASCON cfo, FY2024) → had falsely pointed to fact 238
  (NASCON cfo, H1 2024); fact 242 (cfi) → 239; fact 243 (cff) → 240.
  Written during Stage 3.

`scripts/fre/fsi_phase2_fix_restatement_false_positives.py` (dry-run
then `--apply`) set all 6 `restates_fact_id` values to NULL and nothing
else -- no `numeric_value`, `description`, `period`, or `confidence_tier`
on any row was touched, since those were all correct. Pre-write backup:
`data/ngx.sqlite.pre_fsi_phase2_restatement_fix_backup_2026-08-01`.
Verified before/after: exactly 6 → 0 non-NULL `restates_fact_id` values
database-wide, `foreign_key_check` clean, no other row count changed.

**Regression anchors, both required to pass**:
- **CAP** (genuine restatement, must still be DETECTED):
  `scripts/fre/test_restatement_detection.py`'s existing synthetic-
  fixture check (doc 4508's real FY2020 revenue, 8,737mn, vs. a
  synthetic same-FY2020-span comparative figure of 8,876mn) still
  passes -- exact-span-match does not weaken this case, since both
  figures already shared the identical period.
- **NASCON** (nested reporting, must NEVER be flagged) -- added as a
  new, PERMANENT regression case in the same test file, using NASCON's
  real production data directly (no fixture needed, since both real
  facts already exist): confirms `find_restatement_conflicts` returns no
  conflict for NASCON's real FY2024 assets against its own real H1 2024
  assets, and repeats the same check for cfo. Both pass.
- Full suite re-run: `test_restatement_detection.py` 9/9 (up from 6/6,
  +3 new NASCON checks).

**Why the new rule correctly separates the two cases**: a restatement
is a claim about the SAME fact (the same company, same metric, same
exact reporting period) being reported differently by two sources.
Overlap is a property of calendar time; equivalence of span is a
property of reporting identity. Two filings can only be making a
competing claim about "the same fact" if they are describing the exact
same period -- if the spans differ, they are simply reporting different
(if related) quantities, and disagreement between them is expected and
uninteresting, not a data-quality signal.

**Full regression after this correction**: `check_db_safety.py` PASS,
`test_reasoning_pipeline.py` ALL CHECKS PASSED, `test_period_
normalization.py` 23/23, `test_terminology_mapping.py` 8/8, `test_
restatement_detection.py` 9/9, FRE-2 29/29, FRE-3 16/16, FRE-4 16/16,
FRE-5 21/21. FRE-6 initially showed 39/40 -- the same class of stale
assertion as Stage 2 (this time expecting 72 financial-statement facts,
not accounting for Stage 3's 13 new cash-flow facts). Confirmed by
direct query the correct new total is 85 (15 revenue + 15 net_profit +
14 assets + 14 liabilities + 14 equity + 4 cfo + 3 cfi + 4 cff + 1
capex + 1 fcf), updated the assertion and comment to match, re-ran:
**40/40 pass.**

**Stage 3 (Cash Flow Intelligence) is now complete, and the shared
restatement-detection defect is corrected and regression-anchored
against recurrence.** Both CAP and NASCON anchors pass. Proceeding to
Stage 4, EBITDA/EBIT Intelligence, per the approved implementation
order.

## Entry 6 — Stage 4: EBITDA/EBIT Intelligence (complete)

`scripts/fre/fsi_extract_phase2_ebitda_ebit.py` re-read the income-
statement sections of all 15 anchor filings. Central governing rule,
per the owner's explicit constraint: never assume Operating Profit,
Operating Income, EBIT, EBITDA, PBT, or EBT are equivalent unless
explicitly supported by the filing or the approved terminology mapping.
Applied per ticker (real, disclosed findings, not assumptions):

- **UCAP (bank, docs 4248/6911/10772)**: reports only "Profit Before
  Tax" and an internal "Operating profit before income tax" line that
  is itself PBT under another name -- for a bank, net interest income
  is core operating business, not a non-operating item to strip out the
  way EBIT excludes finance costs for a manufacturer. No filing ever
  uses the word EBIT or EBITDA. **Zero facts written for UCAP** -- a
  disclosed architectural scope gap for financial institutions, not an
  extraction failure.
- **CAP (docs 4508/5911/10115)**: doc 4508 states a literal "EBIT" line
  (direct_reported, FY2020: N1,645mn). Docs 5911/10115 use "Operating
  Profit" instead -- same company, different year's label -- mapped via
  the existing terminology config rule (mapped_equivalent), deliberately
  NOT upgraded to direct_reported on the basis of company identity
  alone. No EBITDA anywhere: CAP never discloses a depreciation/
  amortisation figure in any of its 3 filings, so EBITDA cannot be
  derived either -- a genuine, disclosed gap.
- **AFRIPRUD (docs 4245/6349/7540)**: reports "Profit Before Finance
  Cost(s) and Tax" (singular/plural "cost" varies by filing, both real,
  both added as new mapped_equivalent synonyms to
  `configs/financial_statement_terminology.toml`) -- structurally EBIT
  by its own definition, confirmed by its position immediately before a
  "Finance costs" deduction and "Profit Before Tax" line. All three
  filings ALSO disclose depreciation-of-PP&E + depreciation-of-ROU-
  assets + amortisation-of-intangibles as separate lines, enabling a
  **derived EBITDA** (= EBIT + D&A) for all three -- the one
  architecturally-permitted derivation
  (`configs/financial_ontology.toml`'s `ebit`/`d_and_a` → `ebitda`
  definitional edges), exercised for the first time in this pilot, full
  derivation trace recorded in each fact's own description (e.g. doc
  4245: EBIT 1,570,712k + D&A [40,792k + 4,268k + 17,496k = 62,556k] =
  EBITDA 1,633,268k).
- **BUAFOODS (docs 6664/8009/9357)**: Group-level "Operating Profit"
  (mapped_equivalent, precise thousands-denominated table) AND a
  literal "EBITDA" figure, but only as a rounded narrative statement
  ("~N86.4 billion" etc.), never in the precise table -- direct_reported
  but disclosed as lower-precision than every other EBITDA figure in
  this stage.
- **NASCON (docs 8801/9460/10929)**: both "Operating profit" (mapped_
  equivalent) and a literal "EBITDA" figure, both read from the same
  precise, tabulated highlights table -- the highest-precision EBITDA
  source in this stage.

**Confidence-hierarchy discipline maintained throughout**: every fact's
tier was set per-metric, not assumed uniform per filing -- e.g. CAP doc
4508 carries a direct_reported ebit but no ebitda at all (rather than a
guessed one); AFRIPRUD carries a mapped_equivalent ebit alongside a
derived ebitda in the same filing. `interpretation` remains written
zero times, confirmed by direct query.

**Write results**: `extracted_facts` 246 → 267 (+21 = 12 ebit + 9
ebitda), `evidence` 280 → 301 (+21). Pre-write backup:
`data/ngx.sqlite.pre_fsi_phase2_ebitda_ebit_backup_2026-08-01`.
`foreign_key_check` clean; all 21 restatement-conflict checks correctly
returned empty (including NASCON's own new H1-vs-FY ebit/ebitda pairs --
a live, real confirmation that Entry 5's architectural fix holds under
new data, not just the anchors it was validated against).

**Full regression after this stage**: `check_db_safety.py` PASS,
`test_reasoning_pipeline.py` ALL CHECKS PASSED, `test_period_
normalization.py` 23/23, `test_terminology_mapping.py` 8/8, `test_
restatement_detection.py` 9/9, FRE-2 29/29, FRE-3 16/16, FRE-4 16/16,
FRE-5 21/21. FRE-6 initially showed 39/40 -- the same recurring class of
stale assertion (this time expecting 85 financial-statement facts, not
accounting for Stage 4's 21 new ebit/ebitda facts). Confirmed by direct
query the correct new total is 106 (assets 14, capex 1, cff 4, cfi 3,
cfo 4, ebit 12, ebitda 9, equity 14, fcf 1, liabilities 14, net_profit
15, revenue 15), updated the assertion and comment to match, re-ran:
**40/40 pass.**

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean (database-wide, not just the new
rows); `documents` count unchanged at 11,533 throughout every stage of
Phase 2; `restates_fact_id` non-NULL count is exactly 0 database-wide
(no genuine restatement occurred among any real Phase 2 fact, consistent
with Entry 2's own methodological note that this mechanism is a safety
net, not expected to fire naturally); `confidence_tier='interpretation'`
count is exactly 0 (the hard rule -- never written by any Phase 2
extraction script -- holds across all four stages).

**Stage 4 (EBITDA/EBIT Intelligence) is now complete. All four stages
of FSI Phase 2's approved implementation order are complete, validated,
and documented.** Proceeding to prepare the final FSI Phase 2
implementation report, per the owner's governing instruction, then
stopping for review.
