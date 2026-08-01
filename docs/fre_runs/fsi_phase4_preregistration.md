# FSI Phase 4 — Point-in-Time Financial Reasoning Memory (Pre-registration)

*Design only. No implementation, no schema change, no new fact type, no
new document, no valuation output, no alpha claim, no portfolio ranking,
no scoring. Per instruction, written and frozen BEFORE any execution
begins — the same two-gate discipline used throughout LIM and every
prior FRE/FSI phase. Builds on `fsi-phase3-baseline-2026-08-01` (177
financial-reasoning conclusions, 5 tickers) and does not modify it —
Phase 3 remains frozen, touched only for future bug fixes per the
owner's instruction.*

## A note on scope selection, stated up front

The owner's approval message asked for "a complete research design and
pre-registration" for the next phase without naming its topic, subject
only to a set of hard exclusions (no alpha claims, portfolio rankings,
buy/sell recommendations, hidden scoring, unsupported investment
conclusions) and standards to preserve (provenance, reproducibility,
PIT correctness, confidence preservation, explicit uncertainty). This
document proposes a specific scope, chosen deliberately to avoid the
two most obvious "next steps" on the existing frozen roadmap
(`docs/fre/12_research_roadmap.md`'s own FRE-7 "Valuation Engine v0" and
FRE-9 "Portfolio Reasoning Tier 1") precisely because both sit close to
the excluded categories even in their own conservative original framing
(FRE-7 produces a *valuation range*; FRE-9 is a *watchlist/screening*
mechanism). Instead, this proposes closing a real, concrete gap this
session's own work exposed: **Phase 3's 177 conclusions have no
point-in-time (PIT) query discipline at all** — a genuine, well-motivated
problem, not manufactured to fill a design-document slot. If this is not
the direction the owner intended, redirection is expected and this
document should be treated as one candidate, not a foregone conclusion.

## The real gap this phase addresses

Every `financial_reasoning_conclusions` row carries a `computed_at`
timestamp (when Phase 3's code ran, 2026-08-01), but nothing in Phase 3
governs or even records **when a conclusion was actually knowable** — the
date on which every one of its underlying source facts' filings had
actually been made public. Confirmed by direct query, the 15 real anchor
filings' `filing_date`s span 2020-10-21 through 2026-03-03, and multiple
filings for the same ticker are frequently more than a year apart (e.g.
NASCON: doc 8801 filed 2024-07-31, doc 9460 filed 2025-03-04, doc 10929
filed 2026-03-03). A naive query against `financial_reasoning_
conclusions` today has no way to answer "what did we know about NASCON's
leverage trend as of 2025-01-01" without accidentally including a
conclusion that depends on doc 10929 — a filing that did not exist yet
on that date. This is exactly the class of look-ahead risk FRE-3's own
design named as its single most severe risk when it built
`CompanyMemory.as_of()` — and that mechanism, already built, tested, and
proven on real data, is the direct, existing precedent this phase
extends rather than reinvents.

## Objective

Design (and, once approved, build) a **`CompanyFinancialReasoningMemory.
as_of(ticker, date)`** read layer over Phase 3's frozen conclusions,
returning only conclusions where every underlying source fact's
filing was public on or before the given date — with a mechanical,
automated audit proving zero look-ahead violations, mirroring FRE-3's
own PIT-audit precedent exactly. This is explicitly a **query/access
discipline addition**, not a new analytical method: it reuses Phase 3's
177 conclusions verbatim, computes nothing new, and derives no new
ratio, trend, or flag.

## Explicit non-goals (restated, because this is the area of highest risk)

- No new fact types, no new extraction, no new document.
- No valuation output, no expected return, no target price, no alpha
  claim.
- No portfolio ranking, no buy/sell recommendation, no watchlist, no
  screening mechanism.
- No hidden scoring system — this phase returns existing conclusions
  filtered by a disclosed, mechanical date rule, never a computed
  "score."
- No cross-company output of any kind — `as_of()` accepts exactly one
  ticker, mirroring Phase 3's own Area 7 guardrail and FRE-3's existing
  single-company `CompanyMemory` contract.
- No modification of Phase 3's own conclusions, rules, or schema — this
  phase is purely additive read access on top of the frozen baseline.

## Scope — four required design areas

### 1. PIT-knowability definition for a conclusion

A `financial_reasoning_conclusions` row is **knowable as of date D** if
and only if every `extracted_facts` row it is linked to (via
`financial_reasoning_conclusion_facts`) traces to a `documents` row
whose `filing_date <= D`. This is a strict, mechanical, all-or-nothing
rule — a conclusion with even one contributing fact from a
not-yet-public filing is not knowable, in full, regardless of how many
of its other inputs were already public. (A ratio's numerator and
denominator are two fact_ids from potentially two *different* documents
in principle, though in this dataset every ratio's inputs share the
same document; a trend's earlier/later points are necessarily two
different documents by construction — making this rule genuinely
load-bearing, not vacuous, for every trend and flag conclusion in Phase
3's real output.)

### 2. The `as_of()` interface

Proposed signature (design only, not built): `as_of(con, ticker: str,
as_of_date: str) -> CompanyFinancialReasoningSnapshot`, returning every
knowable conclusion (per Area 1) for that ticker, grouped by
`conclusion_type`, each retaining its own `confidence_tier`, `method`,
and `limitations` fields **unchanged** — this phase must not simplify,
summarize, or drop the `NULL`-tier signal Phase 3 was careful to
preserve. Mirrors `CompanyMemory.as_of()`'s existing return-object
pattern (a structured, per-company snapshot, not a raw SQL result) for
consistency with the platform's own established convention.

### 3. Mechanical look-ahead audit

A dedicated audit function/test, modeled directly on FRE-3's own
PIT-audit precedent: for a range of real `as_of_date` values (proposed:
one date immediately before and one immediately after each of the 15
real anchor filings' own `filing_date`, giving 30 real, concrete test
points, no synthetic fixture needed), assert that `as_of()` never
returns a conclusion whose underlying facts include a filing dated after
`as_of_date`. A single detected violation is treated with the same
severity as FRE-3's own precedent: this halts the phase, not merely logs
a warning.

### 4. Confidence and limitations pass-through, verified

A conclusion returned by `as_of()` must carry the identical
`confidence_tier`/`method`/`limitations` values it has in `financial_
reasoning_conclusions` — verified by a direct equality check in the test
suite, not assumed. No conclusion is ever "upgraded" or "downgraded" by
the memory layer itself; PIT filtering only ever removes a conclusion
entirely (not-yet-knowable) or returns it exactly as Phase 3 wrote it.

## Pre-registered success / partial / failure criteria

| Component | Success | Partial | Failure |
|---|---|---|---|
| PIT-knowability filter (Area 1) | 0 look-ahead violations across all 30 real audit points (Area 3) | n/a — this is a binary correctness property, not a graded one | Any violation found |
| `as_of()` field pass-through (Area 4) | 100% of returned conclusions match their source row's confidence_tier/method/limitations exactly | n/a | Any field altered or dropped |
| Single-company scope (mirrors Phase 3 Area 7) | Mechanical signature audit confirms `as_of()` and every helper accept exactly one ticker | n/a | Any function accepting >1 ticker or returning a comparative field |

If a look-ahead violation IS found during Area 3's audit, that is itself
the most valuable possible finding this phase could produce — it means
Phase 3's own conclusions (or this phase's filter logic) have a real PIT
defect — and must be reported honestly, the same way the restatement-
detection defect was reported in FSI Phase 2, not quietly patched over.

## Dependencies

The frozen `fsi-phase3-baseline-2026-08-01` dataset (177 conclusions)
and `financial_reasoning_conclusion_facts`' existing join structure
(read-only reuse — no schema change). `documents.filing_date`, already
populated for all 15 real anchor filings. FRE-3's existing `Company
Memory` module and its own PIT-audit test as the direct design
precedent (reused, not forked).

## Risks

- **The all-or-nothing knowability rule (Area 1) could make many
  conclusions "not yet knowable" for early as_of_dates within a ticker's
  own history** — e.g. a trend conclusion is never knowable until BOTH
  of its two contributing filings are public, meaning the very first
  real as_of_date at which any trend becomes knowable is necessarily the
  SECOND filing's own date, never the first. This is a real, structural
  consequence of the rule, not a bug — disclosed here so it is not later
  mistaken for one.
- **Only 15 real documents / 5 tickers exist in this dataset** — the
  audit's 30 real test points are a small, real, disclosed sample, not
  a statistically powered validation; consistent with every prior
  phase's own honest small-pilot framing.
- **Scope-selection risk**: this document's own topic choice (Area "A
  note on scope selection" above) may not match what the owner actually
  intended by "the next phase" — flagged explicitly rather than
  proceeding on an unstated assumption.

## Stop condition

If Area 3's audit finds any real look-ahead violation and the cause
cannot be resolved without modifying Phase 3's own frozen conclusions or
schema, stop and report it as a blocker requiring explicit authorization
— per the same standing instruction that governed the Phase 2
restatement-detection correction — rather than silently altering frozen
Phase 3 output.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this is the scope the
owner intended for "the next phase" — must be reviewed and approved
before any implementation begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
