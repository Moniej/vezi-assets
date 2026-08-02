# FSI Phase 17 — Implementation Log

*Per `docs/fre_runs/fsi_phase17_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Confirmed the real API before designing anything

Checked `src/ngxrot/alpha_engine.py` directly: `AlphaEngine().
recommendations()` returns `list[Recommendation]`, each carrying
`.instrument` (ticker), `.action`, `.size_pct_nav`, `.hypothesis_id`,
`.as_of`, `.rationale`. Confirmed a real, current live sleeve exists (20
recommendations, H-011 Size, none overlapping the 10 FSI tickers by
ticker symbol — small-cap names vs. the FSI track's large-cap anchors) —
giving a real positive test case (any of the 20) and a real negative
case (any FSI ticker) without needing a synthetic fixture.

## Entry 1 — `src/ngxrot/fre/portfolio_memory.py`

One function, `cross_reference(ticker) -> PortfolioMemoryNote`. Calls
`AlphaEngine().recommendations()` (read-only, exactly as `scripts/
engine_status.py` already does today), filters to the ticker's own
`instrument` matches, and returns a factual passthrough of the matching
`Recommendation`'s fields. No match -> `in_live_sleeve=False` with all
other fields `None`, never an error — the common, correct case for any
ticker outside the one currently-validated sleeve.

## Entry 2 — Guardrails enforced, not just documented

`PortfolioMemoryNote` carries no score/rank/weight field (mechanical
dataclass introspection). `cross_reference()` accepts only one
ticker-named parameter. AST inspection confirms zero INSERT/UPDATE/
DELETE SQL statement anywhere in the module (not a substring match —
checks every string literal via `ast.walk`). AST-based import check
confirms the module never imports `ngxrot.registry` directly (only
reads through `AlphaEngine`'s own already-public method) and that
`alpha_engine.py` never imports `portfolio_memory` (one-directional,
verified both ways, same pattern as Phase 14's own `alpha_engine`/
`runner` check).

## Entry 3 — Deliberately NOT wired into `company_research_dossier.py`

Per the pre-registration's Alternative 2: building this as an
independent, addable function keeps this phase's risk surface to one
new boundary (a read from the quant engine) rather than two (that read
PLUS a modification to Phase 11's frozen dossier composer, whose entire
existing test suite asserts exact equivalence to its current inputs).
A future phase could wire this in as a small, separately-tested step.

## Entry 4 — Validation and full regression (complete)

`scripts/fre/test_portfolio_memory.py` (13/13): correctness verified
against a real, currently-live H-011 recommendation (not a synthetic
fixture) and a real FSI ticker with no live recommendation; a
nonexistent ticker also returns `in_live_sleeve=False`, never a crash;
all guardrails (single-ticker, no-score-field, no-write-SQL,
import-boundary) confirmed; zero writes to `data/ngx.sqlite`.

Full regression: 27 test files (was 26), all green. `check_db_safety.py`
PASS. `test_reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5 harness:
all 4 components PASS, golden snapshot correctly unchanged (this phase
adds no new FSI fact or conclusion).

**No schema change. No modification to `alpha_engine.py`, `registry.py`,
or any other frozen module.**

**FSI Phase 17 is now complete, validated, and documented.** This closes
out Part 9 of the original frozen architecture doc's Tier-1 capability
list in full (Watchlist remains the one deliberately-deferred item,
per its own larger, separately-scoped design surface).
