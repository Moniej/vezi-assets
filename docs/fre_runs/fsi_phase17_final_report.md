# FSI Phase 17 — Final Report

*Portfolio-Memory Cross-Reference. Full narrative in
`docs/fre_runs/fsi_phase17_implementation_log.md`.*

## Executive summary

FSI Phase 17 built `src/ngxrot/fre/portfolio_memory.py`, implementing the
last of Part 9's three Tier-1 capabilities (Watchlist, Screening,
Portfolio memory) — a read-only cross-reference confirming whether a
ticker is currently in `alpha_engine.py`'s live recommendation set.
Reuses `AlphaEngine().recommendations()` verbatim; no modification to
the quant engine anywhere.

## Files created

- `src/ngxrot/fre/portfolio_memory.py` (new): `cross_reference()`,
  `PortfolioMemoryNote`.
- `scripts/fre/test_portfolio_memory.py` (new, 13 assertions).
- This report, the implementation log, and the pre-registration.

**No schema change. No modification to `alpha_engine.py`, `registry.py`,
or any FSI module.**

## Results

- Correctness confirmed against a real, currently-live H-011 Size sleeve
  recommendation (not a synthetic fixture) and a real FSI ticker with no
  live recommendation.
- A nonexistent ticker returns `in_live_sleeve=False`, never a crash.
- Zero write path anywhere: no INSERT/UPDATE/DELETE SQL in the module
  (AST-verified), no import of `ngxrot.registry`, and `alpha_engine.py`
  does not import this module (one-directional, both directions verified).
- Full regression (27 test files) and Phase 5's validation harness both
  pass; golden snapshot correctly unchanged.

## Design decision disclosed

Deliberately NOT wired into `company_research_dossier.py` this phase —
keeps the new risk surface to one boundary (reading the quant engine)
rather than two (that read plus modifying a frozen composition module).
A future phase could add this wiring as a small, separately-tested step.

## Status: Part 9 (Portfolio Reasoning Tier 1) now closed

Watchlist, Screening (Phase 14/15), and Portfolio memory (this phase)
are Part 9's full Tier-1 list. Watchlist persistence remains the one
deliberately-deferred item (its own larger design surface: a new table
and a curation workflow) — everything else Part 9 named as buildable-now
is now built.

## Recommendations for the next phase

Per the owner's standing continuous-execution authorization, the next
architecture review should reassess the platform holistically now that
Part 9 is substantially closed — Watchlist persistence, a new Financial
Intelligence capability, or further coverage expansion are the live
candidates, to be evaluated fresh rather than assumed.

---

**FSI Phase 17 is complete: fully implemented, validated, and
documented.**
