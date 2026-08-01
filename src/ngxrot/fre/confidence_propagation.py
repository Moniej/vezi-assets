"""FSI Phase 3 shared infrastructure: confidence-tier propagation
(docs/fre_runs/fsi_phase3_preregistration.md Area 1).

A derived conclusion (ratio/trend/flag) is only as trustworthy as its
WEAKEST input fact. Order, strongest to weakest:
`direct_reported` > `mapped_equivalent` > `derived` > unknown (`NULL`).

`NULL` is the floor, not a mid-point -- Phase 1's original 30 facts
(revenue, net_profit) predate the `confidence_tier` column entirely and
were never backfilled (a real, disclosed data-quality fact, not
hypothetical). If ANY input to a conclusion carries a `NULL` tier, the
conclusion's own tier is `NULL` too -- "unknown" never silently becomes
"as good as the best input," and it never becomes "as good as the worst
NAMED tier" either. This is a deliberate, conservative choice: an
analyst reading a derived ratio must be able to tell "at least one of
the numbers behind this has no recorded confidence at all," not just
"the recorded confidence is low."
"""
from __future__ import annotations

_TIER_RANK = {
    "direct_reported": 3,
    "mapped_equivalent": 2,
    "derived": 1,
}


def propagate_confidence_tier(tiers: list[str | None]) -> str | None:
    """Given the confidence_tier of every fact/conclusion feeding a new
    derived conclusion, return the propagated tier: the weakest of the
    named tiers, or None if any input tier is None (the floor)."""
    if not tiers:
        return None
    if any(tier is None for tier in tiers):
        return None
    worst_rank = min(_TIER_RANK[tier] for tier in tiers)
    for tier, rank in _TIER_RANK.items():
        if rank == worst_rank:
            return tier
    return None  # unreachable given the CHECK-constrained tier values above
