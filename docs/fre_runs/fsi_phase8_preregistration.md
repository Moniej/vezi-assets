# FSI Phase 8 — Financial-Reasoning-Informed Investment Thesis (Pre-registration)

*Design only. No implementation, no schema change, no new fact type, no
new document, no LLM call, no numeric expected return, no valuation
output, no alpha claim, no portfolio ranking/allocation, no hidden
scoring, no buy/sell/hold output. Per instruction, written and frozen
BEFORE any execution begins. Builds on `fsi-phase7-baseline-2026-08-02`
and `fre5-company-thesis-baseline-2026-08-01`, and modifies neither —
both remain frozen, touched only for future bug fixes.*

*A note on constraints, stated up front because this message did not
restate them explicitly the way the prior seven approvals did: the
standing exclusions (no alpha, no ranking, no valuation, no
recommendation, no hidden scoring) are treated here as durable platform
charter rules — established independently in the FRE master index's
"never invent alpha" rule, in FRE-5's own frozen "no expected-return
prediction, no alpha claim, no valuation output, no scoring formula"
guardrail, and restated across seven consecutive approvals — not as
something this message's framing ("decision-support system") lifts.
This document proposes the highest-leverage step TOWARD that eventual
capability that is buildable entirely within those still-standing
constraints; it does not propose crossing them. If this reading is
wrong, correction is expected, per the same standing practice used in
every prior phase's own scope-selection disclosure.*

## 1. Review of the complete architecture — LIM, FRE, and FSI

**LIM** (`docs/LIM_ARCHITECTURE.md`, RB-series): mid-research, not
production-ready, confirmed by direct check of the most recent commit
touching `docs/lim_runs/` (`6b36cd2`, RB-3c monitor-cleanup addendum) —
no result exists past RB-3c's own interrupted Phase 0; `self_critique_
quality` remains 0.0 in every completed evaluation; RB-3b's own finding
is that LIM's self-critique output achieves schema validity through
near-total mode collapse, not genuine discrimination. **LIM remains, by
its own explicit non-goal, never auto-promoted to any default
provider role** — it is not a candidate input to anything proposed
below, and this review does not treat it as one.

**FRE track** (document-narrative reasoning, LLM-dependent where real
inference occurs): FRE-1 (schema/ontology) → FRE-2 (Evidence Graph,
mechanical) → FRE-3 (`CompanyMemory.as_of()`, mechanical, PIT-safe) →
FRE-4 (reaction-check, mechanical) → **FRE-5 (`CompanyThesis` — bull/
bear/base case folding, explicitly "an explainable investment-research
artifact, NOT a statistically validated thesis-folding experiment,"
pilot-scoped, frozen)** → FRE-6 (Valuation Engine architecture,
scaffolding only, `compute()` still refuses to run). All frozen.

**FSI track** (financial-statement facts and mechanical reasoning, zero
LLM calls): Phase 1-2 (extraction, 106 facts) → Phase 3 (ratios/trends/
flags, 177 conclusions) → Phase 4 (PIT-safe read access) → Phase 5
(validation harness, 0 deviations) → Phase 6 (unified memory
composition) → Phase 7 (deterministic report rendering). All frozen.

**The concrete state this review finds**: FRE-5's `CompanyThesis` is
the ONE component in the entire architecture explicitly designed to
aggregate evidence toward a decision-relevant view of a company while
remaining permanently barred from producing a number — its own module
docstring states this in the same words used throughout this program:
"No expected-return prediction, no alpha claim, no valuation output, no
scoring formula." But its real, current inputs are sparse: it folds
`investment_implications` deltas — LLM-derived, and, by its own
docstring, real for only one ticker (TOTAL) with a real multi-point
history of just 4 implications. It has never been connected to the FSI
track's now much richer, fully validated, PIT-safe body of mechanical
financial reasoning — 177 conclusions, 5 tickers, built and re-verified
across six subsequent phases. `CompanyThesis`'s own `financial_signal_
summary` field exists today specifically as a placeholder for exactly
this kind of input (its own docstring: "explicitly NOT the same as
`company_intelligence.py`'s blocked 'Financial Quality'") and is
currently unfed by it.

## 2. The single highest-impact remaining capability

**Connect FRE-5's `CompanyThesis` to the FSI track's validated
financial-reasoning conclusions (Phase 3/6) — folding real, mechanical,
PIT-safe flags and trends into the thesis's existing bull-case/bear-
case/financial-signal evidence, as additional cited evidence items,
never as a new score or number.**

## 3. Justification — why this precedes every other remaining item

The Investment Thesis Engine (Part 7) is architecturally positioned, by
this program's own design documents, as the layer between "we have
validated facts" and "a human can form a view" — and Part 9 (Portfolio
Reasoning)'s own dependency table names Part 7 as a hard prerequisite.
No later capability that touches decision support can be reached
without this one existing in a form richer than a 4-implication pilot
first. Every other remaining candidate either (a) does not feed toward
decision support at all, (b) depends on an unresolved owner-level
decision this document cannot make, or (c) is explicitly excluded by
the standing constraints regardless of framing. Section 4 makes this
comparison explicit, one candidate at a time.

## 4. Alternatives considered — the owner's own named candidates, each addressed

1. **Reasoning-mode rollout (FRE-8)**: tags/enforces `causal_chain_
   steps.reasoning_mode` in the LLM-based FRE track. Rejected as the
   next step — it deepens the AUDITABILITY of the existing narrative-
   reasoning mechanism, but does not itself add any new decision-
   relevant evidence or capability; it also requires an LLM vendor/cost
   decision not resolved here, the same blocker named against it in
   Phase 6's own review.
2. **Cross-document/multi-source reasoning (Part 6)**: a `news_
   outlets` registry, multi-source corroboration. Rejected — adds
   breadth of evidence TYPE, not a decision-organizing structure; still
   squarely "more research," and blocked on an external data-source
   decision this document cannot make.
3. **Investment Thesis Engine (Part 7)** — proposed above.
4. **Portfolio reasoning (FRE-9)**: watchlist/screening, Tier 1.
   Rejected for this phase, on TWO grounds, not merely the standing
   exclusion: (a) the owner's own repeated, explicit "no portfolio
   ranking/allocation" constraint has been restated across all seven
   prior approvals, and nothing in this message's new framing
   ("decision-support system") states that constraint is lifted; (b)
   independent of that constraint, Part 9's OWN dependency table names
   Part 7 (`CompanyThesis`) as its prerequisite — even a Tier 1
   watchlist selects among multiple companies using some standing view
   of each one, and today's `CompanyThesis` pilot is real for
   essentially one ticker. Proposing Portfolio Reasoning before
   Investment Thesis is properly fed would be sequencing the roadmap's
   own named dependency backwards.
5. **Knowledge graph expansion (Part 2)**: genuinely typed
   `entity_relationships.relation_type`. Rejected — orthogonal to
   financial-statement reasoning; would not build on anything FSI
   Phase 1-7 produced, and doesn't advance decision-support capability
   specifically.
6. **Evaluation improvements (FRE-10)**: `fre_eval` harness,
   gold-set-based. Rejected for this phase — blocked on an
   owner-authored "strategy-narrative gold set" dependency, named as
   FRE-10's own blocker since the original roadmap and reconfirmed as
   unresolved in Phase 5's own scope-selection review; it validates
   existing capability, it does not add new decision-relevant capacity.
7. **Valuation Engine v0 (FRE-7)**, named here for completeness even
   though absent from the owner's own candidate list: rejected —
   directly produces a number (a valuation range), the single most
   explicitly and repeatedly excluded category across every phase in
   this program; nothing in this review finds a basis for treating it
   as now authorized.

## 5. Objective

Build a **new, additive composition function** —
`CompanyThesis360.as_of(ticker, date)` or similarly named — that takes
FRE-5's existing `CompanyThesis` (built by `build_company_thesis()`,
unmodified) and FSI Phase 3's real financial-reasoning conclusions
(via Phase 4/6's existing PIT-safe read access, unmodified), and
produces one combined view in which every **fired** flag and every
**trend** direction from the FSI track appears as an additional,
separately-cited evidence item attached to the existing `bull_case`/
`bear_case`/`financial_signal_summary` fields — never blended into
`confidence`, never producing a new numeric field, never replacing
`CompanyThesis`'s own existing LLM-derived content.

## 6. Research question

Can the FSI track's mechanical, deterministic evidence (a fired
`leverage_increasing` flag, a `decreasing` margin trend) be folded into
the SAME evidence-citation structure `CompanyThesis` already uses for
LLM-derived deltas, without blurring the origin of either kind of
evidence (mechanical vs. LLM-derived) or without either kind silently
gaining more weight than the other?

## 7. Architectural rationale

This mirrors Phase 6's own precedent exactly — `CompanyMemory360` was a
pure composition over two independently-frozen PIT-safe modules,
touching neither. This phase applies the identical pattern one layer
up: compose over `CompanyThesis` (FRE-5) and the FSI financial-
reasoning conclusions (Phase 3, reached via Phase 4/6), touching
neither. The reason this is the correct NEXT composition (not, say,
composing Phase 7's report with something else) is that `CompanyThesis`
is the one object in the whole architecture whose entire purpose is
organizing evidence around bull/bear/base questions — exactly the shape
"decision support" requires — while its own frozen design already
proves that shape can exist without a number ever appearing in it.

## 8. Dependencies

`fre5-company-thesis-baseline-2026-08-01` (`build_company_thesis()`,
called not forked). `fsi-phase6-baseline-2026-08-01`
(`CompanyMemory360`/`pit_financial_memory`, called not forked, for the
FSI-side evidence). No new schema, no new table, no new fact.

## 9. Risks

- **Evidence-provenance blending risk**: if mechanical (FSI) and
  LLM-derived (FRE) evidence are not clearly labeled by origin in the
  combined view, a reader could mistake one kind's confidence
  properties for the other's (e.g., FSI's `NULL`-tier legacy-fact
  caveat is a different KIND of uncertainty than an LLM's own
  `confidence` float) — mitigated by requiring every folded FSI
  evidence item to carry its own `confidence_tier` (or the `NULL`
  disclosure) verbatim, never converted to a numeric confidence to
  match `CompanyThesis`'s existing field.
- **Scope-creep risk toward a combined score**: folding two evidence
  streams into "one view" could tempt a synthesized bull/bear balance
  metric (e.g., "3 bullish items vs. 1 bearish item") — explicitly
  rejected in Section 10 below; this phase counts nothing, weighs
  nothing, and outputs no ratio of evidence counts.
- **Sparse real data**: only NASCON and AFRIPRUD currently have a real
  FIRED flag (`leverage_increasing`, `margin_compression` respectively)
  among the 5 tickers — the other 3 tickers' combined view would show
  only "not fired"/`stable` evidence, correctly and honestly, not a
  sign the mechanism is broken.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## 10. Explicit statement of what will NOT be built

- No numeric expected return, no target price, no valuation figure of
  any kind (unchanged from FRE-5's own frozen guardrail).
- No combined bull/bear "score," count, ratio, or balance metric of any
  kind — evidence is listed, never tallied.
- No portfolio sizing, allocation, ranking, or watchlist output.
- No buy/sell/hold or other action-oriented recommendation.
- No modification to `company_thesis.py`, `financial_ratios.py`,
  `trend_classification.py`, `financial_health_flags.py`, or any other
  frozen module — this phase is a new, additive composition function
  only.
- No LLM call of any kind.
- No new schema, table, or column.

## 11. Success criteria

- `CompanyThesis360.as_of()` returns both the unmodified
  `CompanyThesis` and a new, clearly-separated list of FSI-sourced
  evidence items, for all 5 real tickers, with zero exceptions.
- Every folded FSI evidence item carries its own `confidence_tier` (or
  explicit `NULL`-tier disclosure), `method`, and `limitations`,
  verbatim from its source conclusion — verified by direct field
  equality, not by inspection.
- A mechanical check confirms the combined object contains no numeric
  field beyond what `CompanyThesis` and the FSI conclusions already
  independently contain (i.e., no new synthesized number was
  introduced by the composition itself).
- Single-ticker-scope guardrail holds, verified mechanically as in
  Phases 3-7.

## 12. Failure criteria

- Any numeric field appears in the combined output that does not trace
  directly to an existing `CompanyThesis` or `financial_reasoning_
  conclusions` field.
- Any FSI evidence item is folded without its own confidence_tier/
  limitations, or with those fields altered from their stored values.
- Any evidence-count, ratio, or balance metric appears anywhere in the
  output.
- Any modification to `company_thesis.py` or any other frozen module
  proves necessary — per standing instruction, this halts the phase for
  review, not a redesign in place.

## 13. Evaluation methodology

Read-only, real production data, no scratch fixture needed (all
underlying modules already have their own tested regression coverage):
for all 5 real tickers, at each ticker's own latest real filing date,
call `CompanyThesis360.as_of()` and confirm (a) no exception; (b) the
`thesis` sub-result is field-for-field identical to a direct call to
`build_company_thesis()`; (c) every folded FSI evidence item's
`confidence_tier`/`method`/`limitations` matches its source conclusion
in `financial_reasoning_conclusions` exactly; (d) a direct scan of the
combined object's own fields confirms no new numeric field was
introduced beyond what the two source objects already contained; (e)
the same `inspect.signature`-style single-ticker-scope audit used in
every prior phase.

## 14. Implementation boundary

**In scope**: one new, additive module containing a single composition
function and its own return dataclass; its own test file;
documentation. **Out of scope, explicitly**: everything named in
Section 10.

## Stop condition

If representing FSI evidence alongside `CompanyThesis`'s existing
fields is found to require any new synthesized field beyond a plain
list of cited evidence items (e.g., if a reviewer would need a count or
balance to make sense of the output), stop and report this as a design
limitation requiring explicit owner authorization before proceeding —
do not add a count or balance to make the output more readable at the
cost of crossing into scoring territory.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this correctly reads
"transform toward a decision-support system" as directional rather than
as authorization to relax the standing exclusions — must be reviewed
and approved before any implementation begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
