# FSI Phase 13 — Coverage Expansion: Scaling the Validated Extraction Base (Pre-registration)

*Design only. No implementation, no extraction performed in this pass,
no LLM call, no subjective inference, no valuation, no ranking, no
portfolio logic, no alpha, no scoring, no expected-return prediction,
no recommendation, no hidden aggregation. Per instruction, written and
frozen BEFORE any execution begins. Builds on
`fsi-phase12-baseline-2026-08-02` and modifies nothing in Phases 1-12 —
all twelve remain frozen, touched only for future bug fixes.*

## 1. Complete architecture review

**LIM**: unchanged since every prior review — still RB-3c-interrupted,
`self_critique_quality` still 0.0, not a candidate input to anything.

**FRE-1 through FRE-6**: frozen, unchanged.

**Knowledge Graph**: 50 `entities`, 5 `entity_relationships` (4 real
`renamed_from` + 1 artifact), unchanged since Phase 9/10.

**FSI Phase 1-2 (extraction)**: 106 financial-statement facts, **5
tickers, 15 documents** — unchanged since Phase 2. This is the entire
evidentiary base for everything built since.

**FSI Phase 3 (reasoning)**: 177 conclusions, over the same 5
tickers/15 documents.

**CompanyMemory (FRE-3) / CompanyMemory360 (Phase 6) / CompanyThesis360
(Phase 8) / entity_context (Phase 10) / CompanyResearchDossier
(Phase 11) / CLI (Phase 12)**: six composition/presentation/operational
layers, all frozen, all tested, all correct — and all of them, without
exception, operate on the identical 5-ticker, 15-document base Phase 2
established on 2026-08-01.

**FSI Phase 5 (validation harness)**: covers Phase 1-4's own golden
snapshot and cross-phase consistency; does not cover Phases 6-12
(already disclosed in Phase 12's own pre-registration review, and
not revisited here).

## 2. Explicit evaluation of the six named categories

**Scaling limitations**: severe and unambiguous. Every phase built
since Phase 2 — six independent, correctly-engineered composition/
presentation/operational layers — operates on exactly 5 companies. No
amount of further composition, validation, or tooling built on top of
this base changes what it can say anything about.

**Data coverage limitations**: the same root cause as scaling, examined
more granularly. Even within the 5 existing tickers, coverage is
uneven and was disclosed as such at the time (Phase 2's own final
report): UCAP (a bank) has no cash-flow/EBITDA data by architectural
design; AFRIPRUD has no cash-flow data in any of its 3 filings; CAP has
cash-flow data in only 1 of 3. Every ticker has only 3 real periods,
producing at most 2 valid trend comparisons each (Phase 3's own
disclosed limitation). A **real, already-scoped, currently-unused
resource exists**: Phase 1's own scoping step (`scripts/fre/
fsi_scope_candidates.py`) found 349 real candidate documents spanning
**49 distinct tickers** — of which only 15 documents, across 5 tickers,
were ever hand-extracted. 44 real, already-identified tickers'
candidate filings have sat unused since 2026-08-01.

**Research workflow limitations**: Phase 12's CLI closed the most
acute usability gap (no operational entry point existed at all).
Remaining workflow gaps (batch mode, alternate output formats) are
real but minor, already named and explicitly deferred in Phase 12's
own report.

**Institutional usability**: the report/dossier/CLI chain (Phases 7,
11, 12) is complete and correct for any ticker it has data for — the
binding constraint on institutional usability is, again, that this is
true for only 5 companies. A CLI over a 5-company research base is not
yet an institutional research system in any meaningful sense.

**Validation weaknesses**: Phase 5's own golden-snapshot mechanism does
not cover Phases 6-12 or the Knowledge Graph, as already found in
Phase 12's own review. Real, but lower-severity than the coverage
problem: regression protection for Phases 6-12 already substantially
exists, distributed across each phase's own dedicated test file (6
files, 70 assertions), re-run as part of the standing full-regression
discipline after every phase.

**Missing capabilities**: reasoning-mode rollout, cross-document
reasoning, event/macro/sector reasoning, and further knowledge-graph
expansion all remain blocked by real, previously-checked data gaps
(`events.ticker` 0/157, `securities.sector_ngx` 0/320, `index_
membership` 100% synthetic) or standing LLM-vendor/cost/policy
exclusions — unchanged since Phase 9/10's own reviews, not re-derived
here.

## 3. The single highest-value remaining bottleneck

**Data coverage.** Every other category above is either a downstream
consequence of this one (scaling, research workflow, institutional
usability all trace back to "5 companies is not enough"), a real but
lower-severity gap already substantially mitigated (validation), or
blocked by something outside this program's control (missing
capabilities). Twelve phases of increasingly sophisticated,
increasingly well-tested machinery have been built on a foundation that
has not grown since the first day of this program. This is the
bottleneck that limits everything else's real value, not merely one
capability among several.

## 4. Objective

Extend the FSI track's already-validated, hand-verified extraction
methodology (Phase 1/2's own native-text-only, no-OCR, no-vendor-data,
config-driven terminology-mapping/period-classification/confidence-
tier discipline — reused verbatim, not redesigned) to a larger set of
real tickers drawn from the **already-scoped** 49-ticker/349-document
candidate pool Phase 1 identified, and — for the first time — run the
complete downstream pipeline (Phases 3-12, all frozen, all unmodified)
against the expanded base, to find out whether six phases of
architecture that has only ever been exercised on 5 companies actually
generalizes, or contains hidden assumptions specific to the original
pilot set.

## 5. Rationale

This is not "the next possible feature" — it is a return to the
platform's own foundational constraint, now that the machinery built on
top of it (Phases 3-12) has been proven correct and stable across
eight consecutive phases. The original scoping (Phase 1) already did
the hard work of finding real, native-text, extractable candidates; 44
of the 49 tickers it found have never been used. Extracting from them
uses the SAME rigor already validated (hand verification, disclosed
terminology mapping, confidence-tier discipline) — this is not a new
kind of work, it is more of the SAME kind of work Phase 1/2 already
proved reliable, at a scale that finally starts to look like coverage
rather than a proof of concept.

## 6. Alternatives considered

1. **Extend Phase 5's validation harness to cover Phases 6-12.** A real
   candidate (already named in Phase 12's own review). Rejected as the
   PRIMARY choice again — the coverage bottleneck is more severe and
   more consequential than a validation-consolidation gap that already
   has substantial (if distributed) test coverage.
2. **Reasoning-mode rollout, cross-document/multi-source reasoning,
   event/macro/sector reasoning, further knowledge-graph expansion.**
   All re-confirmed blocked by real, previously-checked data gaps or
   standing exclusions (Section 2); none is proposed here.
3. **Batch-mode CLI / alternate report formats.** Real but minor,
   already deferred in Phase 12's own report; do not compete with the
   coverage bottleneck for priority.
4. **A wholly new extraction methodology (OCR, vendor data, automated
   scraping at scale).** Rejected — this would abandon the hand-
   verified, disclosed rigor that has been this program's central
   discipline since Phase 1, exactly the trade-off Phase 1's own
   pre-registration explicitly declined to make ("no OCR, no vendor
   data"). This phase proposes MORE of the same validated method, not a
   faster, less rigorous one.
5. **Do nothing further — treat 5 tickers as a permanent, sufficient
   base.** Rejected — this is the alternative Section 3 argues against
   directly; every other capability built since Phase 2 is
   under-utilized by a base this narrow.

## 7. Dependencies

`scripts/fre/fsi_scope_candidates.py` and its own real, already-
produced output (349 candidates, 49 tickers) — re-used, not re-run
from scratch, though re-running it to confirm the candidate list is
still current is a reasonable first execution step. The existing,
frozen terminology-mapping (`configs/financial_statement_
terminology.toml`), period-normalization, confidence-tier, and
restatement-detection modules (Phase 2/3's own shared infrastructure)
— reused unmodified. `fsi-phase12-baseline-2026-08-02` in full, for the
downstream re-validation step.

## 8. Risks

- **Scale of manual effort**: hand-verifying extraction for 10+ new
  tickers at Phase 1/2's own rigor is a substantially larger effort
  than any single composition phase in this program — this is a real,
  disclosed trade-off of choosing rigor over speed, consistent with
  every prior extraction phase's own discipline, not a reason to lower
  the bar.
- **New terminology/period/restatement edge cases are likely**: Phase
  1/2's own real history shows every new company brought a new, real
  surprise (AFRIPRUD's sector-specific terminology, UCAP's period
  mislabeling, CAP's restatement) — 10+ new tickers should be expected
  to surface more, not fewer, real findings of this kind; this is
  treated as expected and valuable, not as a sign something is wrong.
- **Downstream re-validation could reveal a genuine architectural
  assumption specific to the original 5 tickers** (e.g., a composition
  function that happens to work only because all 5 original tickers
  share some property the new ones don't) — if found, this is exactly
  the kind of genuine architectural blocker prior phases have been
  instructed to stop and report rather than silently patch around.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual
  intent — flagged explicitly, redirection expected if wrong.

## 9. Success criteria

- A re-run of `fsi_scope_candidates.py` (or a review of its existing
  output) confirms the 49-ticker/349-document candidate pool is still
  valid and current.
- At least 10 new real tickers are selected from that pool (bringing
  the total real-ticker roster from 5 to 15+), each with at least 2
  real filings spanning different periods (matching the minimum needed
  for Phase 3's own trend-classification mechanism to produce at least
  one real data point per ticker).
- Extraction of the same core metrics already built (revenue,
  net_profit, balance sheet, cash flow where disclosed, EBITDA/EBIT
  where disclosed) achieves ≥80% hand-verified accuracy per metric
  family — the same bar Phase 1's own pre-registration set, applied
  identically, not loosened.
- After extraction, re-running Phases 3-12 in full against the
  expanded dataset produces correct, real output for every new ticker,
  with zero modification to any frozen module — proving the existing
  architecture generalizes.
- The full regression suite and Phase 5's validation harness both
  still pass after the expansion.

## 10. Failure criteria

- Any metric family's hand-verified accuracy falls below 80% — report
  this honestly per family (matching Phase 1/2's own independent-
  family-scoring discipline), do not lower the bar or discard the
  finding.
- Any of Phases 3-12 is found to require modification to correctly
  handle a new ticker — stop immediately and report this as a genuine
  architectural finding requiring separate authorization, per standing
  instruction; do not patch a frozen module to accommodate new data
  without that authorization.
- Any new extraction introduces OCR, vendor data, or any relaxation of
  the existing hand-verification discipline.

## 11. Implementation boundaries

**In scope**: re-confirming Phase 1's own scoping output; selecting 10+
new tickers from it; hand-extracting the same core metrics using the
existing, frozen extraction scripts' own pattern (dry-run/`--apply`,
matching every prior FSI extraction script); re-running Phases 3-12
against the expanded dataset (using their own existing, frozen code,
unmodified — this is a data expansion, not a code change); a
completion report documenting results per metric family, per ticker,
honestly, including any new real findings (terminology, period,
restatement edge cases) in the same disclosed style as Phase 1/2's own
implementation logs.

**Out of scope, explicitly**: any modification to any of the twelve
frozen FSI phases' own code; any new reasoning capability; any
valuation, ranking, scoring, alpha claim, expected-return prediction,
recommendation, or hidden aggregation; any OCR or vendor-data
extraction; any LLM call; any change to the extraction methodology
itself (terminology mapping, period classification, confidence-tier
rules, restatement detection) beyond adding real, disclosed synonyms/
findings the same way Phase 2 already did when it encountered them.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether data coverage is
correctly identified as the platform's own highest-value remaining
bottleneck — must be reviewed and approved before any implementation
begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
