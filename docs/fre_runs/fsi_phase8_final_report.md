# FSI Phase 8 — Final Report

*Financial-Reasoning-Informed Investment Thesis. Prepared per the
owner's instruction to document, commit, and freeze this phase as a
baseline on completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase8_implementation_log.md`; this report summarizes
outcomes.*

## Executive summary

FSI Phase 8 built `CompanyThesis360.as_of(ticker, date)` — a pure
composition of FRE-5's `CompanyThesis` and FSI Phase 6's
`CompanyMemory360`, connecting the platform's Investment Thesis Engine
to the FSI track's validated financial-reasoning conclusions for the
first time. Neither underlying module was modified. Real, fired
financial-health-concern flags (NASCON's `leverage_increasing`,
AFRIPRUD's `margin_compression`) now appear as individually-auditable,
fully-cited evidence items alongside the existing thesis — with no
scoring, weighting, ranking, voting, balancing, confidence aggregation,
expected return, or synthesized "overall thesis strength" field
anywhere in the design.

## Files created (deliverables)

- **CompanyThesis360 module**: `src/ngxrot/fre/company_thesis_360.py`.
- **Tests**: `scripts/fre/test_company_thesis_360.py` (13 assertions).
- **Documentation**: this report plus the implementation log.
- **Implementation log**: `docs/fre_runs/fsi_phase8_implementation_log.md`.

**No schema change. No modification to `company_thesis.py`,
`company_memory_360.py`, `pit_financial_memory.py`, or
`company_memory.py`.**

## Implementation-boundary requirements, verified one by one

1. **Composition layer only.** Confirmed — `as_of()` calls two existing
   functions and partitions already-existing data; it computes nothing
   new.
2. **No scoring/weighting/ranking/voting/balancing/confidence
   aggregation/alpha/expected returns/recommendations/portfolio
   suggestions.** Confirmed by direct dataclass-field introspection of
   both `CompanyThesis360` and `FSIEvidenceItem` — no such field exists
   anywhere.
3. **Draws only from `CompanyThesis`, FSI financial reasoning, and
   `CompanyMemory360`.** Confirmed — the module imports exactly these
   three, nothing else.
4. **Every evidence item references its originating evidence and is
   individually auditable.** Confirmed: every folded item's own
   `conclusion_id`/`method`/`limitations`/`confidence_tier` is checked
   directly against its source conclusion and matches exactly.
5. **Conflicting evidence preserved as separate items, never
   auto-resolved.** Confirmed by design — the module performs no
   reconciliation of any kind; every conclusion becomes exactly one
   evidence item, regardless of what any other conclusion says.
6. **No synthesized "overall thesis strength" field.** Confirmed by
   direct introspection — `CompanyThesis360`'s six fields are exactly
   `{ticker, as_of_date, thesis, memory, concern_evidence,
   supplementary_evidence}`.

## A deliberate design refinement, disclosed

The pre-registration's own wording loosely described folding "every
fired flag and every trend direction" into the thesis. Before writing
code, this was narrowed more conservatively than pre-registered: **trend
directions are never assigned a bull/bear polarity in this module.**
Phase 3's own design committed trend classification to neutral
vocabulary specifically to avoid a valuation-adjacent favorability
judgment (rising revenue and rising leverage are not symmetric);
inventing a per-metric polarity table now would have been a new
judgment this program has never authorized. Only the three financial-
health flags — themselves designed in Phase 3 as risk/concern checks,
never as positive signals — are categorized, and only when fired.
Everything else (ratios, trends, not-fired flags, insufficient_data
flags) is exposed as neutral, informational `supplementary_evidence`.

## Validation results

- **Output equivalence**: the `thesis` sub-result is exactly equal to
  calling `build_company_thesis()` directly, for all 5 real tickers —
  true regardless of whether concern evidence exists (3 of 5 tickers
  have none today, and their `thesis` field still matches exactly, by
  construction). The `memory` sub-result is likewise exactly equal to
  calling `company_memory_360.as_of()` directly.
- **Correct integration on all 5 anchor companies**: `concern_evidence`
  exactly matches the real, known-fired flags — NASCON/
  `leverage_increasing`, AFRIPRUD/`margin_compression`, and correctly
  empty for UCAP/CAP/BUAFOODS.
- **Completeness and non-overlap**: every financial conclusion is
  categorized into exactly one of the two evidence lists, verified via
  set operations, not spot-checked.
- **Database immutability**: all 29 tables' row counts, `integrity_
  check`, and `foreign_key_check` unchanged/clean before and after.
- **Zero schema changes**: confirmed by code review.
- **Full regression suite**: all 13 prior FSI Phase 1-7 test files (178
  assertions) plus the new 13-assertion test file, plus
  `check_db_safety.py`, `test_reasoning_pipeline.py`, and FRE-2 through
  FRE-6 (FRE-6 unchanged at 40/40).
- **Phase 5 validation harness re-run after implementation**: still
  reports PASS on all three components (golden-snapshot reproducibility,
  cross-phase consistency, database immutability) — confirming Phase 8
  introduced no regression.

## Findings

No architectural blocker was encountered. The composition pattern
established in Phase 6 (compose over two independently-frozen modules,
touching neither) applied cleanly one layer up, over `CompanyThesis`
and `CompanyMemory360` — the same result Phase 6 found when composing
`CompanyMemory` and `pit_financial_memory`: independently-built,
independently-governed modules that were each designed under this
program's own consistent discipline compose without friction.

## Known limitations

- **Real concern evidence exists for only 2 of 5 tickers today**
  (NASCON, AFRIPRUD) — this is a real, honest reflection of Phase 3's
  own real flag results, not a limitation of this module.
- **Only 3 flags exist to fold** — Phase 3's own frozen rule set;
  extending it is out of scope here and was already rejected as its own
  phase's scope in Phase 5/6's own reviews.
- **Trends and ratios remain unfoldeded into bull/bear categorization**
  by deliberate design choice (see the design-refinement section above)
  — a future phase could revisit this only with an explicit,
  separately-authorized, disclosed per-metric polarity design, not as
  a silent extension of this one.

## Recommendations for the next phase

1. If Phase 3's flag rule set is ever extended (via a new
   `rule_version`, without modifying frozen code), this module's
   `_CONCERN_FLAG_METRICS` list would need a deliberate, disclosed
   decision about whether to include the new flag — never an automatic
   inclusion.
2. A future phase could design (with its own pre-registration) whether
   and how trend directions might ever be categorized by favorability —
   this remains an explicitly open, unauthorized question, not a
   foregone conclusion.
3. Continue the standing discipline: any future capability remains
   subject to the same exclusions restated across all eight approvals —
   no alpha, ranking, scoring, valuation, or unsupported conclusion.

---

**FSI Phase 8 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
