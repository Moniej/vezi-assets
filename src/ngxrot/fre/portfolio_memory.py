"""FSI Phase 17: Portfolio-Memory Cross-Reference (docs/fre_runs/
fsi_phase17_preregistration.md). Implements Part 9's own Tier-1
"Portfolio memory (read-only cross-reference)" capability
(docs/fre/09_portfolio_reasoning.md) -- "the one Tier-1 capability that
touches something real": whether a ticker is currently in `alpha_engine.
py`'s live recommendation set.

Reuses `AlphaEngine.recommendations()` VERBATIM, exactly as `scripts/
engine_status.py` already does today -- the identical one-directional
read pattern Part 9 names for `company_intelligence.build_profile()`'s
own `factor_exposures` reuse. No modification to `alpha_engine.py` or
`registry.py`. No write path back into the registry anywhere in this
module (mechanically verified in `scripts/fre/test_portfolio_memory.py`).

Purely informational: a `PortfolioMemoryNote` is a factual passthrough of
an existing, already-governed `Recommendation`'s own fields -- never a
new claim, never re-derived, never combined with, or fed into, any FSI
conclusion/thesis/flag. A ticker with no live recommendation returns
`in_live_sleeve=False`, never an error -- this is the common, correct
case for any ticker outside the one currently-validated sleeve.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioMemoryNote:
    """Single-ticker only. No score/rank/weight field -- only a factual
    passthrough of the matching Recommendation's own already-governed
    fields (or all-None/False if the ticker has no live recommendation)."""
    ticker: str
    in_live_sleeve: bool
    hypothesis_id: str | None
    action: str | None
    size_pct_nav: float | None
    as_of: str | None
    rationale: str | None


def cross_reference(ticker: str) -> PortfolioMemoryNote:
    """Read-only. Returns whether `ticker` currently appears in the live
    alpha engine's recommendation set (AlphaEngine().recommendations()),
    called unmodified. Never writes to the registry."""
    from ngxrot.alpha_engine import AlphaEngine

    engine = AlphaEngine()
    recs = engine.recommendations()
    match = next((r for r in recs if r.instrument == ticker), None)

    if match is None:
        return PortfolioMemoryNote(
            ticker=ticker, in_live_sleeve=False, hypothesis_id=None,
            action=None, size_pct_nav=None, as_of=None, rationale=None,
        )
    return PortfolioMemoryNote(
        ticker=ticker, in_live_sleeve=True, hypothesis_id=match.hypothesis_id,
        action=match.action, size_pct_nav=match.size_pct_nav,
        as_of=match.as_of, rationale=match.rationale,
    )
