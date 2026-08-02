# FSI Phase 26 — Final Report

*Sector-to-Company-Type Mapping. Full narrative in
`docs/fre_runs/fsi_phase26_implementation_log.md`.*

## Executive summary

FSI Phase 26 closed the architectural disconnect between Phase 23's
real sector data and FRE-6's company-type-conditioned valuation-method
eligibility design. `configs/sector_company_type_mapping.toml` +
`src/ngxrot/fre/sector_company_type_mapping.py` provide a
deterministic, disclosed, never-inferred translation from NGX's own
sector classification onto `valuation_engine.py`'s existing six-type
taxonomy; `classify_company_type()` was extended (not replaced) with
one new precedence tier. Verified directly, not assumed: zero change
to any of the 10 real FSI tickers' actual readiness/valuation output.

## Files created/modified

- `configs/sector_company_type_mapping.toml` (new).
- `src/ngxrot/fre/sector_company_type_mapping.py` (new):
  `derive_company_type_for_ticker()`.
- `src/ngxrot/fre/valuation_engine.py`: `classify_company_type()`
  signature extended to `(con, ticker)`, gains one new precedence
  tier; its one call site (`value_company()`) updated; docstrings
  corrected. **No `ValuationMethodAdapter` subclass touched.**
- `scripts/fre/test_sector_company_type_mapping.py` (new, 18
  assertions).
- `scripts/fre/test_valuation_engine.py`: one assertion updated
  (GTCO's classification, now correctly `"bank"`), two new assertions
  added (UBN and AFRIPRUD/UCAP still correctly fall back to
  `"general"`).
- This report, the implementation log, and the pre-registration.

## Results

- 12 of NGX's 13 top-level sectors resolve to a company_type; the
  13th (`FINANCIAL SERVICES`) resolves via sub-industry for Banking
  and Insurance only — the other three sub-industries (Micro-Finance
  Banks, Mortgage Carriers, and the genuinely heterogeneous "Other
  Financial Institutions") are deliberately left unresolved, disclosed
  in the config's own comments, not guessed.
- `growth_company`/`turnaround_company` never appear in the mapping —
  both are lifecycle, not industry, classifications, and remain
  reachable only via the existing owner-override mechanism.
- Confirmed directly: none of the 10 real FSI tickers resolve to
  `"bank"`/`"insurance"` under the new mapping, so every existing
  readiness/valuation-output assertion for them is unchanged (42/42
  in `test_valuation_engine.py`, up from 40 — the 2 new checks are
  additive confirmations, not replacements of any prior assertion's
  meaning).
- Confirmed the one real output-shape change this phase does produce
  (CONGLOMERATES-classified tickers now report `eligible_methods=
  ['sum_of_the_parts']`, which has no adapter implementation) is
  handled honestly by `value_company()`'s own pre-existing "adapter is
  None" branch — a clear, disclosed reason, never a crash, never a
  fabricated result.
- Full regression (36 test files, up from 35), `check_db_safety.py`,
  `test_reasoning_pipeline.py`, and Phase 5's harness (4 components,
  31 tables) all pass. Zero unintended data mutations confirmed via
  row-count diffing across every test run.

## Readiness gates: what changed, what remains blocked

**Changed** (disclosed, verified, non-visible in practice today):
`classify_company_type()` now returns `"bank"`/`"insurance"`/
`"holding_company"` instead of always `"general"` for tickers whose
sector resolves unambiguously and who have no owner override — this
changes which methods `is_ready()` is checked against for those
tickers, but since none of them (GTCO, the other Banking/Insurance
names, the Conglomerates names) have real financial-statement facts
extracted (they are not among the 10 FSI tickers), their readiness
output remains `NOT_READY` in every case either way, and `compute()`
still refuses unconditionally on every adapter regardless of method or
company_type.

**Remains blocked, unaffected by this phase**:
`compute()`'s formulas are still `NotImplementedError` on every
adapter — no valuation output exists anywhere, activation of which
still requires a future, separate, explicit architecture-revision
authorization. Part 9 Tier 2 (ranking/sizing/risk) remains gated
behind the ≥2-validated-factor precondition, untouched. `sum_of_
the_parts`/`normalized_earnings_multiple`/`asset_based_floor` remain
unimplemented adapters — this phase does not build any of them, only
correctly routes Conglomerates-classified tickers toward the one that
already exists as a named-but-unbuilt eligibility entry.

## Status

The sector-to-valuation translation layer Phase 23's data population
made buildable now exists, tested, and backward-compatible. No
valuation output was activated anywhere on this platform as a result.

## Recommendations for the next phase

Per the owner's explicit instruction: proceed directly to Phase 27
(Industry Exposure Integration), continuing the same continuous-
execution workflow.

---

**FSI Phase 26 is complete: fully implemented, validated, and
documented.**
