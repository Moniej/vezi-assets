# FSI Phase 22 — Implementation Log

*Per `docs/fre_runs/fsi_phase22_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Fresh full-platform review; the health-flag candidate investigated and set aside with real data

Before settling on this phase, the real `financial_reasoning_
conclusions` table was queried directly for every metric's computed
trend-conclusion count. `fcf` has zero computed trend conclusions on
the real database today; `cfo`/`cfi`/`cff` each have exactly one. A
new health flag built on any of these would be `insufficient_data` for
effectively every real ticker today — architecturally honest but far
weaker, in terms of immediate real usefulness and test coverage, than
this phase's CLI wrapper, which is fully exercised by all 10 real FSI
tickers plus CAVERTON today. Recorded as a live future candidate (see
pre-registration alternative #1), not built this phase.

## Entry 1 — `scripts/fre/generate_portfolio_context_dossier.py`

A thin CLI wrapper around Phase 20's `as_of()`/`render()`, mirroring
Phase 12's `generate_research_dossier.py` structure line-for-line
(UTF-8 stdout/stderr, `mode=ro` connection, ticker-existence check,
custom date-validation error, optional `--output`).

## Entry 2 — Real-data equivalence, including the CAVERTON edge case

Confirmed CLI stdout is byte-identical to calling `as_of()`/`render()`
directly, for all 10 real FSI tickers at each one's own latest real
filing date, AND for CAVERTON (confirmed via direct `AlphaEngine().
recommendations()` query to be in the live H-011 sleeve today) — the
one real combination exercising the "Currently in the live sleeve"
rendering branch through the actual CLI, not just in isolation.

## Entry 3 — Full regression and validation (complete)

`scripts/fre/test_generate_portfolio_context_dossier.py` (new,
10/10). Full regression: 32 test files (was 31), all green — no
existing test file needed any change. `check_db_safety.py` PASS.
`test_reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5 harness: all
4 components PASS — 30 tables, unchanged before/after.

**No modification to `company_portfolio_context.py` or any other
frozen module.** No schema change. The golden snapshot (137 facts /
267 conclusions) is unaffected.

**FSI Phase 22 is now complete, validated, and documented.** Both of
Part 9's built-and-wired composition views (the base research dossier,
Phase 12; this session's portfolio-annotated one, this phase) are now
equally reachable from the command line.
