# FSI Phase 6 — Unified Point-in-Time Company Memory (Pre-registration)

*Design only. No implementation, no schema change, no new fact type, no
new document, no valuation output, no alpha claim, no portfolio
ranking/allocation, no scoring, no buy/sell output, no unsupported
conclusion. Per instruction, written and frozen BEFORE any execution
begins. Builds on `fsi-phase5-baseline-2026-08-01` and modifies nothing
in Phases 1-5 — all five remain frozen, touched only for future bug
fixes.*

## 1. Review of the current completed architecture

**FRE track** (document-narrative reasoning, LLM-based where it touches
real inference): FRE-1 (schema/ontology foundation) → FRE-2 (Evidence
Graph, mechanical) → FRE-3 (`CompanyMemory.as_of()` — dividend/event/
filing history, PIT-safe) → FRE-4 (reaction-check, mechanical) → FRE-5
(`CompanyThesis` folding, pilot-scoped) → FRE-6 (Valuation Engine
architecture — scaffolding only, `compute()` still unconditionally
refuses to run). All frozen; FRE-7 (Valuation Engine v0) and FRE-9
(Portfolio Reasoning Tier 1) remain the roadmap's own next-listed items
but are excluded by the owner's standing constraints.

**FSI track** (financial-statement facts and mechanical reasoning over
them, zero LLM calls anywhere): Phase 1 (pilot revenue/net_profit
extraction) → Phase 2 (balance sheet, cash flow, EBITDA/EBIT) → Phase 3
(ratios, trends, flags — `financial_reasoning_conclusions`) → Phase 4
(`pit_financial_memory.as_of()` — PIT-safe read access to Phase 3's
conclusions) → Phase 5 (regression/consistency validation harness). All
frozen; 106 facts, 177 conclusions, 5 tickers.

**A concrete architectural fact this review surfaced**: `docs/fre/
13_gap_analysis.md` (written 2026-07-22, before any FRE/FSI phase was
implemented) already named Part 5 (Company Memory) as "missing as an
aggregation object" over data that already existed. That gap was closed
by FRE-3. **The identical gap now exists one level up**: FRE-3's
`CompanyMemory.as_of()` and Phase 4's `pit_financial_memory.as_of()` are
two separate, unconnected modules, each independently PIT-safe (both
gate by `filing_date <= as_of_date` — confirmed by direct code
inspection of `company_memory.py`'s `build_company_memory()`), covering
non-overlapping data (dividends/events/filing-history vs. ratios/
trends/flags) for the SAME 5 real tickers. No single function today
answers "as of date D, everything we knew about Company X" — a
consumer must call both and manually reconcile two different return
shapes.

## 2. Remaining capability gaps identified (beyond the one proposed below)

For completeness, per the owner's instruction to identify gaps before
proposing — not all of these are proposed as Phase 6's scope:

- **Reasoning-mode rollout** (`docs/fre/12_research_roadmap.md`'s
  FRE-8): `causal_chain_steps.reasoning_mode` exists as a schema column
  (FRE-1) but is never populated or enforced anywhere. Real gap, but
  belongs to the LLM-based FRE track, not the mechanical FSI track —
  raises the same LLM-vendor/cost/unsupported-inference risk already
  flagged and deferred multiple times.
- **Typed knowledge-graph relations** (Part 2): `entity_relationships.
  relation_type` is still not genuinely typed (a free-text field, not a
  config-driven taxonomy). Real gap, orthogonal to financial-statement
  reasoning entirely — would not build on anything FSI Phase 1-5
  produced.
- **Cross-document/multi-source reasoning** (Part 6): `news_outlets`
  registry still does not exist; only one document provider is
  confirmed real. Real gap, but requires a new data source decision,
  not a reasoning-layer addition over what already exists.
- **Extending Phase 3's ratio/flag rule set** (current ratio, quick
  ratio, ROE, ROA — all computable in principle from existing facts).
  Rejected as this phase's own scope: Phase 3 is frozen and the owner
  has said no further modification absent a bug fix; a wholly separate,
  additive rule_version could in principle add these without touching
  frozen code, but this is "more of the same capability," not a new one,
  and was already implicitly deprioritized when Phase 5 rejected
  "extending Phase 3's rule set" as its own scope.

None of these four is proposed below — the first two sit outside the
FSI track entirely (higher risk, unrelated data), the third needs an
unresolved data-source decision, and the fourth is incremental rather
than a genuine new capability. The gap named in Section 1 — no unified,
PIT-safe view spanning both FRE-3 and Phase 4 — is proposed instead:
lower risk than all four, directly serves the owner's repeatedly-stated
priorities (provenance, PIT correctness, auditability), and touches only
already-frozen, already-tested modules via a new, thin, purely additive
read layer.

## 3. Objective

Build `CompanyMemory360.as_of(ticker, date)` — a single, read-only,
PIT-safe function that combines FRE-3's `CompanyMemory.as_of()`
(dividend/event/filing history) and Phase 4's
`pit_financial_memory.as_of()` (ratio/trend/flag conclusions) for one
ticker into one coherent snapshot, gated consistently by the same
public-filing-date discipline both already use independently. This adds
no new data, no new computation, no new inference — it is a
**composition layer**, calling both existing, frozen functions and
returning their results together, unmodified.

## 4. Research question

Can the two existing, independently-built PIT-safe memory objects (FRE-3
and Phase 4) be combined into one consistent view without any
discrepancy in how they interpret "as of date D" — i.e., do they
actually agree on what counts as "knowable," given they were designed
five phases apart by two different, though closely related, mechanisms?

## 5. Hypothesis

Both mechanisms already gate on `documents.filing_date <= as_of_date`
(confirmed by direct code inspection, not assumed), so combining them
should produce a coherent result with no reconciliation logic needed
beyond calling both and merging the two outputs into one return object.
Genuinely open: it is not yet verified whether the two mechanisms treat
edge cases (e.g. a ticker's first-ever real filing date, or a date with
no data on either side) identically — this phase's own validation will
confirm or refute that, not assume it.

## 6. Alternatives considered

1. **Do nothing — leave the two memory objects separate.** Rejected —
   the fragmentation is a real, named gap (Section 1), and the owner's
   repeated emphasis on auditability favors one coherent, well-tested
   access point over two that a future consumer must independently
   discover and reconcile.
2. **Merge the two underlying modules into one, rewriting both.**
   Rejected — this would modify FRE-3 and Phase 4's own frozen code,
   violating the standing "no further modifications except bug fixes"
   instruction already given for every prior phase. A pure composition
   layer that calls both, unmodified, is the only option consistent
   with that constraint.
3. **Reasoning-mode rollout (FRE-8), typed relations (Part 2),
   cross-document/multi-source reasoning (Part 6), or extending Phase
   3's rule set** — each considered and rejected in Section 2 above,
   with reasons specific to each.
4. **Extend the combined view with a derived "overall company health"
   summary field.** Rejected outright — this is exactly the shape a
   hidden scoring system would take (a single combined signal
   synthesized from multiple independent facts), directly excluded by
   the owner's standing constraints; Phase 6 returns the two existing
   result sets side by side, never a new synthesized field.

## 7. Success criteria

- `CompanyMemory360.as_of()` returns both FRE-3's `CompanyMemory` and
  Phase 4's `CompanyFinancialReasoningSnapshot` for all 5 real tickers,
  at a range of real `as_of_date` values, with zero exceptions/crashes.
- Both underlying calls' own PIT guarantees are preserved exactly (a
  mechanical audit reruns FRE-3's own PIT-audit-style check and Phase
  4's `audit_no_lookahead()` against the combined function's output and
  finds identical results to calling each function directly).
- Single-ticker-scope guardrail (mirroring Phase 3 Area 7 and Phase 4)
  holds: `CompanyMemory360.as_of()` accepts exactly one ticker, returns
  no comparative/ranking field.

## 8. Failure criteria

- Any discrepancy between the combined function's output and calling
  FRE-3/Phase 4 directly (a reconciliation bug) — must be reported
  honestly and, if the root cause requires modifying either frozen
  module, treated as an architectural blocker requiring separate
  authorization, per standing instruction.
- Any case where the two mechanisms' PIT gating disagrees on the same
  real `as_of_date` (e.g. one includes a filing the other excludes for
  the same date) — a genuine, reportable inconsistency between two
  previously-independent implementations, not something to silently
  resolve by picking one side.

## 9. Dependencies

`fsi-phase5-baseline-2026-08-01` in full (Phases 1-5 unmodified).
FRE-3's `company_memory.py` (`build_company_memory()`, unmodified,
called not forked). Phase 4's `pit_financial_memory.py` (`as_of()`,
unmodified, called not forked). No new schema, no new table.

## 10. Evaluation method

Read-only tests against real production data (no scratch fixture
needed — both underlying functions already have their own scratch-based
regression tests from FRE-3 and Phase 4): for all 5 real tickers, at
each ticker's own real filing dates (reusing Phase 4's existing 30-point
real-date set from Phase 4's own audit), call `CompanyMemory360.as_of()`
and confirm (a) both sub-results are present and non-crashing, (b) the
`financial` sub-result exactly equals a direct call to
`pit_financial_memory.as_of()`, (c) the `corporate` sub-result exactly
equals a direct call to `build_company_memory()`, (d) a mechanical
single-ticker-scope signature audit (the same `inspect.signature` style
check used in Phases 3-5) passes.

## 11. Implementation boundary

**In scope**: one new, additive module (`src/ngxrot/fre/
company_memory_360.py` or similar — exact name an execution-time
decision) containing a single composition function and its own return
dataclass; its own test file; documentation. **Out of scope, explicitly**:
any modification to `company_memory.py` or `pit_financial_memory.py`;
any new fact, ratio, trend, or flag; any schema change; any combined/
derived/synthesized field beyond returning the two existing result sets
side by side; any valuation, ranking, scoring, or investment-output
capability of any kind. If implementation reveals that a coherent
combination requires changing either frozen module's behavior, this
is, by definition, a scope violation of this pre-registration — stop and
request review before proceeding, per standing instruction.

## Risks

- **Composition-layer risk is low but not zero**: even a "just call both
  and return them together" design could surface a real disagreement
  between two independently-built PIT mechanisms (Section 5's open
  question) — the evaluation method above exists specifically to find
  this, not assume it away.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## Stop condition

If the evaluation method (Section 10) finds any discrepancy between the
combined function's output and the two underlying functions called
directly, stop and report it as a genuine finding before proceeding —
do not silently paper over a disagreement between two previously-
independent, previously-trusted PIT mechanisms.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this is the scope the
owner intended — must be reviewed and approved before any implementation
begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
