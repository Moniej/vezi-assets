"""FSI Phase 19: Qualitative Correlation Notes (docs/fre_runs/
fsi_phase19_preregistration.md). Implements Part 9's own Tier-1
"Qualitative correlation notes" capability
(docs/fre/09_portfolio_reasoning.md, lines 69-80).

Explicitly NOT a computed correlation coefficient and NOT a
shared-edge count -- both are Part 9's own pre-rejected designs
(alternatives #2). A `CorrelationNote` states only a narrative,
evidenced shared-exposure reason: two tickers each carry an edge of the
SAME macro-exposure relation type (`configs/relation_taxonomy.toml`'s
`[macro_exposure]` group: exposed_to_commodity/exposed_to_fx/
exposed_to_policy) to the SAME counterpart entity (e.g., "both
companies carry an exposed_to_commodity edge to Brent crude"). No
numeric field is ever produced.

Pairwise only -- two named tickers in, one note out. Never an
all-pairs/matrix mode; see the pre-registration's alternative #3 for
why (a matrix reads as a de facto ranked heatmap the moment it is
displayed).

Read-only composition over `entity_context.get_entity_context()`
(Phase 10, called unmodified, twice -- once per ticker). No new SQL
against `entities`/`entity_relationships`, no write to any table, no
import of `alpha_engine.py` or `registry.py` -- this is the same
one-directional read boundary every other FRE module maintains.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.entity_context import get_entity_context

# The [macro_exposure] group from configs/relation_taxonomy.toml --
# duplicated here as a literal tuple (not parsed from the TOML at
# runtime) because this module only needs to recognize these three
# names, not enumerate the platform's full taxonomy. Corporate
# structure / commercial / governance / graph-provenance relation types
# are deliberately excluded: they are either identity/lineage edges or
# direct commercial links between the pair itself, not a shared
# exposure to a common third party.
MACRO_EXPOSURE_RELATION_TYPES = ("exposed_to_commodity", "exposed_to_fx", "exposed_to_policy")


@dataclass(frozen=True)
class SharedExposureReason:
    """One evidenced reason two tickers might move together. No
    numeric field -- traceable back to both underlying
    entity_relationships rows via the two relationship_ids."""
    relation_type: str
    counterpart_entity_id: int
    counterpart_canonical_name: str
    ticker_a_relationship_id: int
    ticker_b_relationship_id: int


@dataclass
class CorrelationNote:
    ticker_a: str
    ticker_b: str
    as_of_date: str
    shared_exposures: list[SharedExposureReason] = field(default_factory=list)


def note_for_pair(con: sqlite3.Connection, ticker_a: str, ticker_b: str, as_of_date: str) -> CorrelationNote:
    """Pairwise only. Raises if ticker_a == ticker_b (a self-pair is
    not a correlation question). Unknown/not-yet-graphed tickers are
    handled exactly as get_entity_context() already handles them --
    zero relationships, hence zero shared exposures, never an error."""
    if ticker_a == ticker_b:
        raise ValueError("ticker_a and ticker_b must be different tickers")

    ctx_a = get_entity_context(con, ticker_a, as_of_date)
    ctx_b = get_entity_context(con, ticker_b, as_of_date)

    shared: list[SharedExposureReason] = []
    for rel_a in ctx_a.relationships:
        if rel_a.relation_type not in MACRO_EXPOSURE_RELATION_TYPES:
            continue
        for rel_b in ctx_b.relationships:
            if rel_b.relation_type == rel_a.relation_type \
                    and rel_b.counterpart_entity_id == rel_a.counterpart_entity_id:
                shared.append(SharedExposureReason(
                    relation_type=rel_a.relation_type,
                    counterpart_entity_id=rel_a.counterpart_entity_id,
                    counterpart_canonical_name=rel_a.counterpart_canonical_name,
                    ticker_a_relationship_id=rel_a.relationship_id,
                    ticker_b_relationship_id=rel_b.relationship_id,
                ))

    return CorrelationNote(ticker_a=ticker_a, ticker_b=ticker_b, as_of_date=as_of_date, shared_exposures=shared)
