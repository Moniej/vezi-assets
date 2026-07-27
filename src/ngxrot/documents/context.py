"""ReasoningContext (Phase E, owner-approved 2026-07-26): the single object
every reasoning module should consume instead of issuing its own DB
queries. Assembled once per (ticker, as_of) by `build_reasoning_context`,
which is the only place in this package allowed to know how each piece of
context is fetched — retrieval.py's finders, company_intelligence's
factor-exposure adapters, and this module's own event-reaction statistic.
Keeps the reasoning pipeline modular (a future storage-backend swap only
touches this one assembly function) and testable (a test can construct a
ReasoningContext directly without touching the database at all).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import evidence_ranking, retrieval
from .coverage_assessment import CoverageAssessment, assess_coverage
from .retrieval import RetrievalQuery, RetrievedDocument


@dataclass
class ReasoningContext:
    ticker: str
    as_of: str
    name: str | None = None

    documents: list[RetrievedDocument] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    event_reaction_stats: dict[str, dict] = field(default_factory=dict)
    entity_relationships: list[dict] = field(default_factory=list)
    factor_exposures: dict = field(default_factory=dict)   # ticker -> FactorExposure,
                                                            # from company_intelligence
    historical_implications: list[dict] = field(default_factory=list)
    peer_propagations: list[dict] = field(default_factory=list)  # received AS a peer (Phase F)

    coverage_notes: list[str] = field(default_factory=list)
    # Stabilization pass (2026-07-27): structured counterparts to
    # coverage_notes' free text. Populated last in build_reasoning_context
    # (after everything above exists) — both are descriptive-only, neither
    # mutates any row.
    coverage_assessment: CoverageAssessment | None = None
    evidence_ranking_summary: dict = field(default_factory=dict)

    @property
    def has_llm_facts(self) -> bool:
        return any(f.get("model_id") for f in self.facts)


def _evidence_for_facts(con, fact_ids: list[int]) -> list[dict]:
    if not fact_ids:
        return []
    placeholders = ",".join("?" * len(fact_ids))
    rows = con.execute(
        f"SELECT e.evidence_id, e.doc_id, e.quoted_text, e.source_confidence, "
        f"ef.fact_id FROM evidence e JOIN extracted_facts ef ON ef.evidence_id = e.evidence_id "
        f"WHERE ef.fact_id IN ({placeholders})", fact_ids).fetchall()
    cols = ["evidence_id", "doc_id", "quoted_text", "source_confidence", "fact_id"]
    return [dict(zip(cols, row)) for row in rows]


def historical_event_reaction(con, ticker: str, event_type: str, as_of: str, *,
                              window_days: int = 5, min_events: int = 2) -> dict | None:
    """Descriptive price-reaction statistic for past events of this type
    ('has this happened before, did it move price') — deliberately NOT
    signal.event_window_scores, which builds portfolio TARGET WEIGHTS for
    the backtest engine (enter=1.0/exit=0.0 rows), a different output
    shape than something citable as evidence. This reuses the same
    underlying PIT primitives event_window_scores itself depends on
    (db.events_asof, price history) and summarizes them descriptively
    instead — same data, no new event-study engine. A deliberate deviation
    from the letter of the Phase E spec (which named event_window_scores
    specifically); documented in the Phase E completion notes, not silent.
    Returns None if there is no price series to react against; returns an
    explicit `insufficient=True` result (not omitted) if fewer than
    `min_events` reactions can be measured, so the caller can see the
    check was made rather than assume it wasn't."""
    from .. import db as _db

    events_df = retrieval.find_events(con, ticker=ticker, event_type=event_type,
                                      sim_date=as_of, limit=200)
    if events_df is None or len(events_df) == 0:
        return None
    px = _db.equity_prices_asof(con, as_of, tickers=[ticker], min_confidence=0.9)
    if px.empty:
        return None
    px = px.sort_values("trade_date")
    close = px.set_index(pd.to_datetime(px.trade_date))["close"]

    reactions = []
    for _, ev in events_df.iterrows():
        ed = pd.Timestamp(str(ev.announced_date))
        before = close.loc[:ed]
        after = close.loc[ed:]
        if len(before) < 1 or len(after) < 2:
            continue
        p0 = before.iloc[-1]
        p1 = after.iloc[min(window_days, len(after) - 1)]
        if p0 and p0 > 0:
            reactions.append({"event_id": int(ev.event_id),
                              "announced_date": str(ev.announced_date),
                              "return": float(p1 / p0 - 1)})

    if len(reactions) < min_events:
        return {"event_type": event_type, "window_days": window_days,
               "n_events": len(reactions), "insufficient": True,
               "note": f"only {len(reactions)} historical reaction(s) observed "
                      f"(floor={min_events}) — not enough for a reliable "
                      f"descriptive statistic, shown as evidence of absence "
                      f"not silently omitted", "per_event": reactions}
    rets = pd.Series([r["return"] for r in reactions])
    return {"event_type": event_type, "window_days": window_days,
           "n_events": len(reactions), "insufficient": False,
           "mean_return": float(rets.mean()), "median_return": float(rets.median()),
           "per_event": reactions}


def build_reasoning_context(con, ticker: str, as_of: str | None = None,
                            cache: dict | None = None) -> ReasoningContext:
    as_of = as_of or date.today().isoformat()
    cache = cache if cache is not None else {}

    row = con.execute("SELECT name FROM securities WHERE ticker = ?", (ticker,)).fetchone()
    ctx = ReasoningContext(ticker=ticker, as_of=as_of, name=row[0] if row else None)

    ctx.documents = retrieval.retrieve_documents(
        con, RetrievalQuery(ticker=ticker, date_to=as_of, limit=100))
    ctx.facts = retrieval.find_facts(con, ticker=ticker, date_to=as_of, limit=200)
    ctx.evidence = _evidence_for_facts(con, [f["fact_id"] for f in ctx.facts])
    ctx.entity_relationships = retrieval.find_entity_relationships(con, ticker=ticker, limit=100)
    ctx.historical_implications = retrieval.find_prior_implications(
        con, ticker, before_date=as_of, limit=50)
    ctx.peer_propagations = retrieval.find_peer_propagations(con, ticker, limit=50)

    events_df = retrieval.find_events(con, ticker=ticker, sim_date=as_of, limit=100)
    if events_df is not None and len(events_df):
        ctx.events = events_df.to_dict("records")
        for et in sorted(set(events_df.event_type)):
            stat = historical_event_reaction(con, ticker, et, as_of)
            if stat is not None:
                ctx.event_reaction_stats[et] = stat

    from .. import company_intelligence
    try:
        profile = company_intelligence.build_profile(con, ticker, as_of, cache=cache)
        ctx.factor_exposures = profile.factor_exposures
    except Exception as e:  # noqa: BLE001 — company_intelligence.build_profile
        # depends on the full quant equity panel (backtest_xs.load_panel)
        # existing and being non-empty at min_confidence=0.9; that's true
        # for the real database but not for a minimal/synthetic one (or a
        # ticker outside the validated panel's coverage). A reasoning
        # context must degrade honestly here, not crash — "unknown stays
        # unknown" applies to factor exposures exactly as it does to any
        # other missing dataset.
        ctx.coverage_notes.append(
            f"factor-exposure computation unavailable for this database/ticker: {e!r}")

    if not ctx.facts:
        ctx.coverage_notes.append(
            "no extracted_facts on record for this ticker as of this date — "
            "the knowledge graph has no prior structured coverage")
    elif not ctx.has_llm_facts:
        ctx.coverage_notes.append(
            "only deterministic (Phase B) facts on record, no LLM-reasoned "
            "implications exist yet for this ticker")
    if not ctx.entity_relationships:
        ctx.coverage_notes.append("no persisted entity relationships for this ticker yet")
    if not ctx.events:
        ctx.coverage_notes.append("no events on record for this ticker as of this date")

    ctx.coverage_assessment = assess_coverage(con, ctx)
    ctx.evidence_ranking_summary = evidence_ranking.evidence_ranking_summary(con, ctx)

    return ctx
