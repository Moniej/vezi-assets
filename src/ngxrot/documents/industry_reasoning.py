"""Industry Reasoning Engine (Phase F, docs/AI_INTELLIGENCE_LAYER_
ARCHITECTURE.md §4.5) — the one engine that reasons primarily off the
knowledge graph rather than a single document. Given a company-level
`investment_implication`, walks `entity_relationships` to flag SECONDARY,
explicitly lower-confidence considerations for peer entities.

Two deliberate, disclosed deviations from the architecture doc's original
sketch (both because the doc's premises didn't hold once actually built —
see reports/phase_f_completion.md for the full reasoning):

1. The doc assumed `entity_relationships.relation_type` would already hold
   classified values like `competitor_of`. Phase E populated it with the
   literal `affects_order_{1,2,3}` fact instead (the model was never asked
   to classify relationship *nature*, only to name an affected entity —
   see entities.py's docstring). Propagation here walks ANY
   `affects_order_*` edge whose OBJECT entity has entity_type=
   'competitor_mention' — today that's every such edge by construction
   (extract.py types every non-self affected entity that way), so this is
   a real filter, not a no-op, the moment entity typing becomes more
   precise.
2. The doc's own illustrative example ("Company A cuts prices" -> "Company
   B may face margin pressure") implies inferring the DIRECTION of the
   effect on the peer. This module deliberately does NOT do that
   algorithmically — inferring whether a peer is helped or hurt by a
   competitor's action is an economic-mechanism judgment, and this
   platform has never allowed that kind of inference to be made by a hard
   -coded rule instead of an evidence-grounded, self-critiqued reasoning
   pass. Propagated implications carry the source's direction/magnitude
   UNCHANGED but heavily discounted, `status='under_review'` (never
   `unvalidated_ai_interpretation` — that status implies the self-critique
   gate ran on THIS implication, which it did not), and a mandatory
   research_task_candidates row asking a future pass to actually determine
   the peer-specific direction. Propagation is a FLAGGING mechanism, not a
   directional call.
"""

from __future__ import annotations

from datetime import date

from . import vocab

MAX_PEERS_PER_IMPLICATION = 10   # bound on fan-out per propagation call


def _source_entity_id(con, ticker: str) -> int | None:
    row = con.execute(
        "SELECT entity_id FROM entities WHERE entity_type = 'company' AND ticker = ? "
        "ORDER BY entity_id LIMIT 1", (ticker,)).fetchone()
    return row[0] if row else None


def _peer_tickers(con, source_entity_id: int) -> list[tuple[int, str]]:
    """(entity_id, ticker) pairs for competitor_mention objects reachable
    from source_entity_id via ANY affects_order_* edge, restricted to
    peers that resolved to a real securities.ticker (see entities.py's
    _exact_name_match_ticker — unresolved mentions are skipped, never
    guessed)."""
    rows = con.execute(
        "SELECT DISTINCT obj.entity_id, obj.ticker FROM entity_relationships r "
        "JOIN entities obj ON obj.entity_id = r.object_entity_id "
        "WHERE r.subject_entity_id = ? AND r.relation_type LIKE 'affects_order_%' "
        "AND obj.entity_type = 'competitor_mention' AND obj.ticker IS NOT NULL",
        (source_entity_id,)).fetchall()
    return [(eid, tk) for eid, tk in rows]


def propagate_implication(con, implication_id: int,
                          discount: float = vocab.INDUSTRY_PROPAGATION_CONFIDENCE_DISCOUNT,
                          max_peers: int = MAX_PEERS_PER_IMPLICATION) -> list[int]:
    """Returns the implication_ids of any newly created (or already
    -existing, on a rerun) propagated rows. No-ops (returns []) for an
    implication that: doesn't exist, was blocked by self-critique, is
    itself already a propagation (one-hop-only — never chain), or has no
    ticker/no resolvable peers."""
    src = con.execute(
        "SELECT ii.fact_id, ii.ticker, ii.direction, ii.duration_bucket, ii.magnitude, "
        "ii.confidence, ii.status, ii.propagated_from_implication_id, ii.model_id, "
        "ii.prompt_version, ef.fact_type "
        "FROM investment_implications ii JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
        "WHERE ii.implication_id = ?", (implication_id,)).fetchone()
    if src is None:
        return []
    (fact_id, ticker, direction, duration_bucket, magnitude, confidence, status,
     already_propagated, model_id, prompt_version, fact_type) = src

    if status == "blocked_by_self_critique":
        return []            # never propagate a rejected draft
    if already_propagated is not None:
        return []            # one-hop only — a propagated implication never re-propagates
    if not ticker:
        return []

    source_entity_id = _source_entity_id(con, ticker)
    if source_entity_id is None:
        return []

    new_or_existing_ids = []
    as_of = date.today().isoformat()
    for peer_entity_id, peer_ticker in _peer_tickers(con, source_entity_id)[:max_peers]:
        if peer_ticker == ticker:
            continue          # never propagate a company to itself
        existing = con.execute(
            "SELECT implication_id FROM investment_implications WHERE "
            "propagated_from_implication_id = ? AND ticker = ?",
            (implication_id, peer_ticker)).fetchone()
        if existing:
            new_or_existing_ids.append(existing[0])
            continue

        rationale = (
            f"Propagated from implication #{implication_id} ({ticker}, {fact_type}) via an "
            f"entity_relationships edge — NOT independently evidenced or self-critiqued for "
            f"{peer_ticker} specifically. Direction/magnitude copied unchanged from the "
            f"source, confidence discounted x{discount} "
            f"(configs: vocab.INDUSTRY_PROPAGATION_CONFIDENCE_DISCOUNT). Whether {peer_ticker} "
            f"is actually helped or hurt by this event has NOT been assessed — see the "
            f"paired research task.")
        propagated_confidence = max(0.0, min(1.0, confidence * discount))

        new_id = con.execute(
            "INSERT INTO investment_implications (fact_id, ticker, model_id, prompt_version, "
            "duration_bucket, magnitude, confidence, confidence_rationale, direction, "
            "action_recommendation, status, propagated_from_implication_id, generated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fact_id, peer_ticker, model_id, prompt_version, duration_bucket, magnitude,
             propagated_confidence, rationale, direction, "research_task",
             "under_review", implication_id, as_of)).lastrowid

        con.execute(
            "INSERT INTO research_task_candidates (implication_id, description, status, "
            "created_at) VALUES (?,?,?,?)",
            (new_id, f"Determine whether {peer_ticker} is actually helped or hurt by "
                    f"{ticker}'s {fact_type} event (source implication #{implication_id}) — "
                    f"propagation only flagged relevance, it did not assess direction.",
             "open", as_of))

        new_or_existing_ids.append(new_id)

    con.commit()
    return new_or_existing_ids
