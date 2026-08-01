# FRE-6 — Valuation Engine Architecture Implementation

*Implementation report. Builds on `fre-architecture-baseline-2026-08-01`,
`fre3-company-memory-baseline-2026-08-01`, `fre5-company-thesis-baseline-2026-08-01`,
and FRE-2/FRE-4 (`f7dd990`, `e1dd1f9`). Additive only — no schema change,
no write path, no modification to any AI Intelligence Layer file or data,
and — per explicit instruction — architecturally separate from thesis
generation.*

## Objective

Implement `docs/fre/08_valuation_engine_architecture.md` as **architecture
only**: the `ValuationMethodAdapter` interface, six method adapters (DCF,
DDM, Residual Income, EV/EBITDA, P/E, P/B), sector-eligibility config, and
readiness gating — verified, not assumed, to correctly refuse to compute
anything on the real database today, since no financial-statements
dataset has ever been acquired.

## The hard boundary, honored explicitly

Per instruction, this module **must remain separate from thesis
generation and must not introduce expected-return outputs**.
`src/ngxrot/fre/valuation_engine.py` imports nothing from
`company_thesis.py`, `evidence_graph.py`, `company_memory.py`, or
`reaction_check.py` — verified mechanically (not just by inspection): a
test checks the file's actual `import`/`from` statement lines, not just
absence of the module names anywhere in the file (the docstring
deliberately names all four, to state the boundary in words; the test
checks the boundary in code, distinct from the prose that explains it).

## Real-data verification performed before writing any adapter

Checked directly, not assumed: `extracted_facts.fact_type` has exactly
three values across all 161 real rows — `dividend` (158), `rights_issue`
(2), `bonus_issue` (1). **Zero** revenue/EBITDA/balance-sheet/cash-flow
line items exist anywhere on this platform. `securities.sector_ngx` is
confirmed **0/320** populated. These two facts, both re-confirmed in this
pass (not merely cited from earlier FRE work), mean every one of the six
adapters below is architecturally guaranteed to report `NOT_READY` for
every real ticker today — verified against five real tickers (GTCO,
TOTAL, UCAP, CILEASING, and a nonexistent one), not just asserted.

## What was built

| Artifact | Role |
|---|---|
| `configs/valuation_method_eligibility.toml` | Company-type → eligible-method mapping (bank/insurance/holding_company/growth_company/turnaround_company/general), per Part 8's table |
| `configs/company_type_overrides.toml` | Owner-judged company-type override list — **deliberately empty**, since `sector_ngx` is unpopulated and guessing which tickers are banks/insurers would be exactly the kind of unearned, unconfirmed classification this platform's "owner-judged, never AI-inferred" rule exists to prevent |
| `src/ngxrot/fre/valuation_engine.py` | `ValuationMethodAdapter` ABC, six concrete adapters, `classify_company_type()`, `value_company()` → `TriangulatedValuation` |
| `scripts/fre/test_valuation_engine.py` | 28 assertion checks against the real database (no write path exists, no scratch copy needed) |

## Design specifics

- **`is_ready()` gates `compute()` unconditionally** — `compute()`'s base
  implementation re-checks readiness itself and raises `RuntimeError` if
  not ready, even if a caller bypasses `value_company()`'s own gating and
  calls an adapter directly. Verified on all six adapters against real
  data: every one refuses.
- **Every `ReadinessResult` carries a named, non-trivial reason** — never
  a bare `False`, matching the NOT-NULL-explanation discipline already
  used throughout `impact_assessments.explanation`/`confidence_rationale`
  elsewhere on this platform.
- **DDM's readiness check is real and slightly richer than the others**:
  it correctly finds real dividend history (e.g., 8 real dividend facts
  for TOTAL, joining Phase B's deterministic extraction and the LLM
  -sourced duplicates of the same events) but still reports `NOT_READY`,
  because a DDM additionally needs a cost-of-equity assumption this
  platform's ontology (Part 1) hasn't populated yet — a genuine,
  evidence-aware "closer but still not ready" result, not a blanket "no
  data" message identical across every method.
- **`company_type` defaults to `'general'` for every real ticker** — the
  override config is empty by design; this module does not infer bank/
  insurance/holdco status from ticker names or any other unconfirmed
  signal.
- **Two eligible methods named in the config
  (`sum_of_the_parts`/`normalized_earnings_multiple`/`asset_based_floor`,
  for holding/turnaround company types) have no adapter class at all** —
  disclosed explicitly as "not yet implemented" in `readiness_by_method`
  rather than silently omitted, so a future reader querying a holdco's
  eligible methods sees exactly what's missing, not a shorter list with
  no explanation.

## Alternatives considered

1. **Implement at least one adapter's real formula, gated to run only on
   synthetic/placeholder data for demonstration.** Rejected — a working
   formula with no real data to validate it against would create exactly
   the false confidence Part 8's own design explicitly warns against
   ("a plausible-looking number computed from disclosed assumptions is
   not evidence that those assumptions are correct"); leaving `compute()`
   unimplemented past the readiness gate states the honest limit clearly.
2. **Infer company type from ticker name patterns (e.g., tickers
   containing "BANK").** Rejected — an unconfirmed heuristic presented as
   a classification is exactly the risk the empty override file's own
   docstring names; `general` for everyone, disclosed, is more honest than
   a guess dressed up as structure.
3. **Skip the `sum_of_the_parts`/turnaround-method stubs entirely rather
   than name them with no adapter.** Rejected — Part 8's eligibility table
   names them for a reason (holding companies and turnarounds need
   different methods); naming them as "not yet implemented" preserves the
   architecture's intent without pretending they're built.

## Trade-offs

- Zero adapters can be exercised end-to-end today — this is a complete,
  verified scaffold, not a partial working system. That is the correct
  trade-off given the explicit instruction to keep this phase to
  architecture only, not a race to compute something before the
  underlying data exists.
- The DDM/DCF/Residual-Income/EV-EBITDA/PE/PB split means six small
  classes instead of one parametrized function — deliberately, per Part
  8's own reasoning: conflating architecturally distinct methods behind
  one shared formula would misrepresent them as more similar than they are.

## Risks

- **A future implementer could be tempted to fill in `compute()`'s
  `NotImplementedError` before real data exists**, defeating the
  readiness gate's purpose — the gate itself (checked in `compute()`, not
  only in the caller) is the structural defense against this, not a
  comment alone.
- **The empty override config could quietly get populated with unverified
  guesses under time pressure** — the file's own docstring states this
  explicitly as the risk to avoid; enforcement is procedural, the same
  limitation already disclosed for other "owner-judged" registries on
  this platform (e.g., `news_outlets`).

## Future extensions

- Real adapters become buildable once a financial-statements dataset is
  acquired (`docs/fre/10_dataset_strategy.md`'s single highest-leverage,
  still-unacquired item) — no redesign needed, only filling in
  `compute()` behind the same, already-tested `is_ready()` gates.
- A real, owner-confirmed `company_type_overrides.toml` population, once
  the owner is ready to make those specific calls.
- Sum-of-the-parts and normalized-earnings-multiple adapters, once Part
  2's `subsidiary_of` lineage edges have real data to enumerate a
  holding company's parts.

## Verification performed

| Check | Result |
|---|---|
| `scripts/fre/test_valuation_engine.py` | **28/28 PASS** (module-isolation from thesis generation verified via actual import statements, all 6 adapters refuse on 5 real tickers, `compute()`'s safety gate fires unconditionally, config files load correctly, zero financial-statement data confirmed to exist anywhere, `sector_ngx` confirmed 0/320) |
| `scripts/test_reasoning_pipeline.py` (pre-existing) | 154/154 PASS, unchanged |
| `scripts/fre/test_evidence_graph.py` (FRE-2) | 29/29 PASS, unchanged |
| `scripts/fre/test_company_memory.py` (FRE-3) | 16/16 PASS, unchanged |
| `scripts/fre/test_reaction_check.py` (FRE-4) | 16/16 PASS, unchanged |
| `scripts/fre/test_company_thesis.py` (FRE-5) | 21/21 PASS, unchanged |
| `scripts/check_db_safety.py` | PASS, 0 violations |
| Production DB row counts, all 27 tables | Unchanged — this module has no write path at all |

## Dependencies

`docs/fre/08_valuation_engine_architecture.md` (the design this
implements). No dependency on, or from, FRE-2/3/4/5's modules — verified
architecturally isolated, per instruction. Blocked, structurally and by
design, on a financial-statements dataset for any adapter to ever leave
`NOT_READY`.

---

*Per the standing instruction, this concludes FRE-6. Stopping here and
awaiting review.*
