"""Structured (SQL-first) retrieval layer for the Financial Reasoning Engine
(Phase E, owner-approved 2026-07-26).

This is the "consult additional documents/facts/events only when needed"
half of the architecture — the part that did not exist before Phase E.
Deliberately SQL-only for now: everything the reasoning engine needs to
find (a company's filings, its extracted facts, its historical events, its
entity relationships) is already keyed on indexed columns (ticker,
fact_type, event_type, doc_type, dates). No embeddings/vector search yet
(owner directive) — that would be a genuine new dependency (an embedding
model + a vector index to keep in sync) for a capability structured
retrieval hasn't yet been shown to need.

The seam for adding semantic retrieval later without touching callers is
`retrieve_documents(con, query: RetrievalQuery)`: every other finder in
this module is a convenience wrapper that builds a `RetrievalQuery` and
calls it. A future semantic ranker is a second implementation selected the
same way `llm_providers.PROVIDER_REGISTRY` selects a concrete LLMProvider
— a new function/class plus a config flag, not a change to any caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import db as _db  # noqa: F401  (re-exported for callers that want
                          # events_asof/equity_prices_asof alongside retrieval
                          # without a second import line)


@dataclass(frozen=True)
class RetrievalQuery:
    ticker: str | None = None
    entity_name: str | None = None
    fact_type: str | None = None
    event_type: str | None = None
    doc_type: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 50


@dataclass
class RetrievedDocument:
    doc_id: int
    ticker: str | None
    raw_symbol: str | None
    doc_type: str
    filing_date: str
    source_confidence: float
    has_text: bool          # text_path is not NULL — extractable today
    already_extracted: bool  # extracted_facts already exist for this doc


def retrieve_documents(con, query: RetrievalQuery, vintage: str | None = None) -> list[RetrievedDocument]:
    """The one seam a future semantic retriever would replace/augment.
    Structured-only: exact ticker match, doc_type match, filing_date range,
    entity mention join. Ranked by filing_date DESC (most recent first) —
    no relevance scoring exists yet because there is only one signal
    (recency) to rank on without embeddings.

    `vintage` (added 2026-08-12, production-reliability audit, Finding A):
    the CAPTURE-vintage cutoff, distinct from date_from/date_to (which
    filter filing_date -- the market's knowledge date). Filters
    `documents.as_of_date <= vintage` -- when the OS itself retrieved the
    document, mirroring db.py's vintage parameter on the market-data
    readers exactly. Verified on the live database: 98.8% of documents
    have a retrieved_date more than 30 days after filing_date (avg gap
    ~4.6 years), so filtering on filing_date alone lets a historical query
    see documents the system had not yet captured as of that date. `None`
    (the default) preserves the exact prior unfiltered behavior -- this
    only matters for a genuine historical replay, not a live "as of today"
    query (today's vintage is a no-op since as_of_date is always <= today)."""
    clauses, params = [], {}
    joins = ""
    if query.ticker:
        clauses.append("(d.ticker = :ticker OR d.raw_symbol = :ticker)")
        params["ticker"] = query.ticker
    if query.doc_type:
        clauses.append("d.doc_type = :doc_type")
        params["doc_type"] = query.doc_type
    if query.date_from:
        clauses.append("d.filing_date >= :date_from")
        params["date_from"] = query.date_from
    if query.date_to:
        clauses.append("d.filing_date <= :date_to")
        params["date_to"] = query.date_to
    if vintage:
        clauses.append("d.as_of_date <= :vintage")
        params["vintage"] = vintage
    if query.entity_name:
        joins += (" JOIN entity_mentions em ON em.doc_id = d.doc_id "
                 " JOIN entities en ON en.entity_id = em.entity_id ")
        clauses.append("LOWER(en.canonical_name) = LOWER(:entity_name)")
        params["entity_name"] = query.entity_name
    if query.fact_type:
        joins += " JOIN extracted_facts ef_f ON ef_f.doc_id = d.doc_id "
        clauses.append("ef_f.fact_type = :fact_type")
        params["fact_type"] = query.fact_type

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (f"SELECT DISTINCT d.doc_id, d.ticker, d.raw_symbol, d.doc_type, "
          f"d.filing_date, d.source_confidence, d.text_path "
          f"FROM documents d {joins} {where} "
          f"ORDER BY d.filing_date DESC LIMIT :limit")
    params["limit"] = query.limit

    rows = con.execute(sql, params).fetchall()
    out = []
    for doc_id, ticker, raw_symbol, doc_type, filing_date, source_confidence, text_path in rows:
        extracted = con.execute(
            "SELECT 1 FROM extracted_facts WHERE doc_id = ? AND model_id IS NOT NULL LIMIT 1",
            (doc_id,)).fetchone() is not None
        out.append(RetrievedDocument(
            doc_id=doc_id, ticker=ticker, raw_symbol=raw_symbol, doc_type=doc_type,
            filing_date=filing_date, source_confidence=source_confidence,
            has_text=text_path is not None, already_extracted=extracted))
    return out


def find_facts(con, *, ticker: str | None = None, fact_type: str | None = None,
               date_from: str | None = None, date_to: str | None = None,
               vintage: str | None = None, limit: int = 50) -> list[dict]:
    """extracted_facts joined back to their document, for a company. Both
    LLM-sourced (model_id set) and deterministic (model_id NULL) facts are
    returned — the caller decides whether to filter, matching
    validate_extracted_facts.py's existing model_id IS NULL discipline
    rather than silently picking one source here.

    `vintage` (added 2026-08-12, production-reliability audit, Finding A):
    same capture-vintage cutoff as retrieve_documents' `vintage` -- filters
    `documents.as_of_date <= vintage`, distinct from date_to's filing_date
    filter. `None` (the default) preserves the exact prior unfiltered
    behavior."""
    clauses, params = [], {"limit": limit}
    if ticker:
        clauses.append("(d.ticker = :ticker OR d.raw_symbol = :ticker)")
        params["ticker"] = ticker
    if fact_type:
        clauses.append("ef.fact_type = :fact_type")
        params["fact_type"] = fact_type
    if date_from:
        clauses.append("d.filing_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("d.filing_date <= :date_to")
        params["date_to"] = date_to
    if vintage:
        clauses.append("d.as_of_date <= :vintage")
        params["vintage"] = vintage
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (f"SELECT ef.fact_id, ef.doc_id, ef.fact_type, ef.description, "
          f"ef.numeric_value, ef.extraction_confidence, ef.model_id, "
          f"d.filing_date, d.ticker, d.raw_symbol "
          f"FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id "
          f"{where} ORDER BY d.filing_date DESC LIMIT :limit")
    cols = ["fact_id", "doc_id", "fact_type", "description", "numeric_value",
           "extraction_confidence", "model_id", "filing_date", "ticker", "raw_symbol"]
    return [dict(zip(cols, row)) for row in con.execute(sql, params).fetchall()]


def find_entity_relationships(con, *, ticker: str | None = None,
                              entity_name: str | None = None,
                              relation_type: str | None = None,
                              as_of: str | None = None,
                              vintage: str | None = None,
                              limit: int = 50) -> list[dict]:
    """`as_of` (added 2026-08-11, HANDOFF.md -- Priority 5, point-in-time
    integrity): when given, excludes any relationship not yet valid as of
    that date (`valid_from > as_of`) and any relationship already expired
    by then (`valid_to < as_of`). Real look-ahead risk this closes: this
    function previously had NO date filtering at all -- entity_relationships.
    valid_from genuinely spans 2020-2026 on the real database, so a caller
    reconstructing "what did we know as of <a past date>" would silently
    see relationships recorded from documents filed AFTER that date. `None`
    (the default) preserves the exact prior unfiltered behavior for
    existing callers that intentionally want the full history.

    `vintage` (added 2026-08-12, production-reliability audit, Finding A):
    a SEPARATE gate from `as_of` -- as_of/valid_from/valid_to describe when
    a relationship was true in the real world; vintage gates on
    `recorded_at`, when THIS SYSTEM actually captured it (verified on the
    real database: relationship_id=11 has valid_from=2026-01-27 but its
    source document's capture date is 2026-08-08 -- a historical query
    as_of='2026-03-01' would previously see it as "known" six months
    before the system had it). Conservative on missing data: a
    relationship with recorded_at IS NULL (no source_evidence_id, or one
    never backfilled) is EXCLUDED once vintage is given, not assumed safe
    -- capture time unknown is not the same as capture time acceptable.
    `None` (the default) preserves the exact prior unfiltered behavior."""
    clauses, params = [], {"limit": limit}
    if ticker:
        clauses.append("(subj.ticker = :ticker OR obj.ticker = :ticker)")
        params["ticker"] = ticker
    if entity_name:
        clauses.append("(LOWER(subj.canonical_name) = LOWER(:entity_name) "
                       "OR LOWER(obj.canonical_name) = LOWER(:entity_name))")
        params["entity_name"] = entity_name
    if relation_type:
        clauses.append("r.relation_type = :relation_type")
        params["relation_type"] = relation_type
    if as_of:
        clauses.append("(r.valid_from IS NULL OR r.valid_from <= :as_of)")
        clauses.append("(r.valid_to IS NULL OR r.valid_to >= :as_of)")
        params["as_of"] = as_of
    if vintage:
        clauses.append("(r.recorded_at IS NOT NULL AND r.recorded_at <= :vintage)")
        params["vintage"] = vintage
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (f"SELECT r.relationship_id, subj.canonical_name AS subject_name, "
          f"r.relation_type, obj.canonical_name AS object_name, "
          f"r.valid_from, r.valid_to, r.confidence, r.source_evidence_id "
          f"FROM entity_relationships r "
          f"JOIN entities subj ON subj.entity_id = r.subject_entity_id "
          f"JOIN entities obj ON obj.entity_id = r.object_entity_id "
          f"{where} ORDER BY r.valid_from DESC LIMIT :limit")
    cols = ["relationship_id", "subject_name", "relation_type", "object_name",
           "valid_from", "valid_to", "confidence", "source_evidence_id"]
    return [dict(zip(cols, row)) for row in con.execute(sql, params).fetchall()]


def find_events(con, *, ticker: str | None = None, event_type: str | None = None,
                sim_date: str | None = None, min_confidence: float = 0.0,
                limit: int = 50):
    """Thin wrapper around db.events_asof — reused, not duplicated (that
    function already implements PIT-correct, restatement-aware event
    reads; this module adds no new event-reading logic, only ticker/type
    filtering + a limit for retrieval-sized results)."""
    from datetime import date as _date
    df = _db.events_asof(con, sim_date or _date.today().isoformat(),
                        event_types=[event_type] if event_type else None,
                        min_confidence=min_confidence)
    if df.empty:
        return df
    if ticker:
        df = df[(df.ticker == ticker) | (df.scope != "ticker")]
    return df.sort_values("announced_date", ascending=False).head(limit)


def find_peer_propagations(con, ticker: str, *, as_of: str | None = None,
                           limit: int = 20) -> list[dict]:
    """investment_implications this ticker RECEIVED as a peer (Phase F,
    industry_reasoning.propagate_implication) — propagated_from_implication_id
    IS NOT NULL rows keyed to this ticker. Distinct from
    find_prior_implications, which returns implications this ticker's OWN
    facts produced.

    `as_of` (added 2026-08-11, HANDOFF.md -- Priority 5): excludes any
    propagation generated after that date (`ii.generated_at > as_of`) --
    same class of look-ahead gap as find_entity_relationships, closed the
    same way. `None` (the default) preserves the exact prior unfiltered
    behavior."""
    clauses = ["ii.ticker = ?", "ii.propagated_from_implication_id IS NOT NULL"]
    params: list = [ticker]
    if as_of:
        clauses.append("ii.generated_at <= ?")
        params.append(as_of)
    params.append(limit)
    rows = con.execute(
        "SELECT ii.implication_id, ii.propagated_from_implication_id, ii.direction, "
        "ii.magnitude, ii.confidence, ii.confidence_rationale, ii.status, ii.generated_at, "
        "src.ticker AS source_ticker "
        "FROM investment_implications ii "
        "JOIN investment_implications src ON src.implication_id = ii.propagated_from_implication_id "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY ii.generated_at DESC LIMIT ?", params).fetchall()
    cols = ["implication_id", "propagated_from_implication_id", "direction", "magnitude",
           "confidence", "confidence_rationale", "status", "generated_at", "source_ticker"]
    return [dict(zip(cols, row)) for row in rows]


def find_prior_implications(con, ticker: str, *, before_date: str | None = None,
                            limit: int = 20) -> list[dict]:
    """investment_implications already produced for this ticker (any status
    — the caller decides whether blocked_by_self_critique rows are still
    worth surfacing as "considered but rejected"). Mirrors extract.py's
    `_cross_reference` query shape exactly, generalized to a retrieval
    caller instead of being inlined in the extraction path."""
    clauses, params = ["ii.ticker = :ticker"], {"ticker": ticker, "limit": limit}
    if before_date:
        clauses.append("ii.generated_at <= :before_date")
        params["before_date"] = before_date
    where = " AND ".join(clauses)
    sql = (f"SELECT ii.implication_id, ii.fact_id, ii.direction, ii.magnitude, "
          f"ii.duration_bucket, ii.confidence, ii.status, ii.generated_at, "
          f"ef.fact_type, ef.doc_id "
          f"FROM investment_implications ii "
          f"JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
          f"WHERE {where} ORDER BY ii.generated_at DESC LIMIT :limit")
    cols = ["implication_id", "fact_id", "direction", "magnitude", "duration_bucket",
           "confidence", "status", "generated_at", "fact_type", "doc_id"]
    return [dict(zip(cols, row)) for row in con.execute(sql, params).fetchall()]
