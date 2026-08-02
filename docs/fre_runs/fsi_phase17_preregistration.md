# FSI Phase 17 — Portfolio-Memory Cross-Reference (Pre-registration)

*Per the owner's standing continuous-execution authorization. Builds on
`fsi-phase16-baseline-2026-08-02`.*

## Architectural gap

Part 9 (`docs/fre/09_portfolio_reasoning.md`) names THREE Tier-1
capabilities: Watchlist, Screening, Portfolio memory (read-only cross-
reference). Screening shipped in Phases 14-15. Portfolio memory — "the
one Tier-1 capability that touches something real": a read-only note
confirming whether a ticker is currently in `alpha_engine.py`'s live
recommendation set — has never been built.

## Why highest-priority now

It is the last of Part 9's three already-designed, already-authorized
Tier-1 items, closing that section of the frozen architecture doc
entirely. It answers a real, concrete question a researcher using any
FSI dossier would have: "is the fund actually exposed to this ticker
right now?" — informational only, never feeding back into any FSI
conclusion, thesis, or recommendation.

## Alternatives considered and rejected

1. **Watchlist persistence.** The other remaining Part 9 Tier-1 item.
   Rejected for this phase — requires a new table and a curation
   workflow (who writes an entry, when); Portfolio memory is pure read,
   zero persistence, smaller surface.
2. **Wiring this directly into `company_research_dossier.py`'s own
   `build_dossier()`.** Considered, rejected as this phase's default —
   would modify a frozen module (Phase 11) and entangle the FSI dossier
   with quant-engine data for the first time inside a composition
   function whose entire existing test suite (Phase 11/12/16) asserts
   exact equivalence to calling its inputs directly. Building this as an
   independent, addable function first is the more conservative choice;
   wiring it into the dossier can be a small, separately-tested future
   step once the cross-reference itself is proven.
3. **A new Financial Intelligence flag (e.g. capital-allocation
   quality).** Real, but Part 9's own gap is more architecturally
   consequential (closes a whole named section of the frozen roadmap)
   and lower-risk (pure read, no new derivation logic).

## Why this fits the long-term architecture

Reuses `alpha_engine.py`'s own already-public `AlphaEngine.
recommendations()` method verbatim — the SAME one-directional read
pattern `company_intelligence.build_profile()` already established
(per Part 9's own text) for `factor_exposures`. No modification to
`alpha_engine.py`, `registry.py`, or any quant-engine module. No write
path back into the registry.

## Design decision (conservative, no pause)

`src/ngxrot/fre/portfolio_memory.py`: one function, `cross_reference
(ticker: str) -> PortfolioMemoryNote`. Calls `AlphaEngine().
recommendations()` (read-only, exactly as `scripts/engine_status.py`
already does today), filters to the given ticker's own `instrument`
matches, and returns a factual passthrough of the matching
`Recommendation`'s own fields (`action`, `size_pct_nav`, `hypothesis_
id`, `as_of`, `rationale`) — never a new claim, never re-derived,
never combined with any FSI conclusion. A ticker with zero matches
returns `in_live_sleeve=False`, never an error (this is a real,
common, correct case — most tickers are not in the one currently-
validated Size sleeve). NOT wired into `company_research_dossier.py`
in this phase (see Alternative 2).

## Success criteria

Correctly reflects a real ticker currently in the live Size sleeve (if
any exist at the time of testing) and correctly reflects zero-match
tickers as `in_live_sleeve=False`, never an error. Zero write path to
the registry (mechanically verified: no `INSERT`/`UPDATE`/`DELETE`
statement anywhere in the new module). Mechanical import-boundary check:
`alpha_engine.py`/`registry.py` never import this new module. Full
regression + Phase 5 harness both still pass.

---
*Implementation proceeds immediately.*
