"""FSI Phase 10: Knowledge Graph Context Integration
(docs/fre_runs/fsi_phase10_preregistration.md).

A pure, read-only COMPOSITION layer connecting the knowledge graph
(`entities`/`entity_relationships`, populated in FSI Phase 9) to the FSI
composition chain (`CompanyMemory360`, Phase 6) for the first time.
Neither underlying table nor module is modified.

No new reasoning, no graph-traversal heuristics, no inferred
relationships, no relationship scoring, no centrality metrics, no graph
analytics, no recommendation logic, no ranking, no valuation, no
portfolio functionality, no LLM call. This module exposes ONLY verified
graph context already present in the platform -- every returned
relationship retains its own `relation_type`, counterpart entity,
`valid_from`/`valid_to`, `confidence`, and `source_evidence_id`
verbatim from `entity_relationships`.

PIT discipline (docs/fre_runs/fsi_phase10_implementation_log.md
Entry 0): an entity is visible as of a given date only if its own
`first_seen_doc_id`'s `filing_date <= as_of_date` -- the same
`documents.filing_date` gate every prior FSI phase (4, 6, 8) already
uses, applied here to `entities` for the first time. A `None` result
means "no graph presence is yet KNOWN as of this date," never "this
company did not exist" -- absence of evidence is not evidence of
absence. `entity_relationships` rows are filtered the same way via
their own `valid_from`/`valid_to` columns.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.company_memory_360 import CompanyMemory360, as_of as memory_as_of


@dataclass
class RelationshipContext:
    relationship_id: int
    relation_type: str
    direction: str  # 'subject' | 'object' -- whether this ticker's own entity is the subject or object
    counterpart_entity_id: int
    counterpart_canonical_name: str
    valid_from: str | None
    valid_to: str | None
    confidence: float
    source_evidence_id: int | None


@dataclass
class EntityContext:
    ticker: str
    as_of_date: str
    entity_id: int | None
    canonical_name: str | None
    first_seen_doc_id: int | None
    relationships: list[RelationshipContext] = field(default_factory=list)


@dataclass
class CompanyMemory360Graph:
    ticker: str
    as_of_date: str
    memory: CompanyMemory360
    graph: EntityContext


def get_entity_context(con: sqlite3.Connection, ticker: str, as_of_date: str) -> EntityContext:
    """Single-ticker only. No default for as_of_date, matching every
    other PIT-safe reader on this platform."""
    row = con.execute(
        "SELECT e.entity_id, e.canonical_name, e.first_seen_doc_id, d.filing_date "
        "FROM entities e JOIN documents d ON d.doc_id = e.first_seen_doc_id "
        "WHERE e.entity_type = 'company' AND e.canonical_name = ?",
        (ticker,),
    ).fetchone()

    if row is None or row[3] > as_of_date:
        return EntityContext(
            ticker=ticker, as_of_date=as_of_date, entity_id=None,
            canonical_name=None, first_seen_doc_id=None, relationships=[],
        )

    entity_id, canonical_name, first_seen_doc_id, _filing_date = row

    rel_rows = con.execute(
        "SELECT relationship_id, relation_type, subject_entity_id, object_entity_id, "
        "valid_from, valid_to, confidence, source_evidence_id "
        "FROM entity_relationships "
        "WHERE (subject_entity_id = ? OR object_entity_id = ?) "
        "AND (valid_from IS NULL OR valid_from <= ?) "
        "AND (valid_to IS NULL OR valid_to > ?)",
        (entity_id, entity_id, as_of_date, as_of_date),
    ).fetchall()

    relationships = []
    for rel_id, rel_type, subj_id, obj_id, valid_from, valid_to, confidence, source_evidence_id in rel_rows:
        direction = "subject" if subj_id == entity_id else "object"
        counterpart_id = obj_id if direction == "subject" else subj_id
        counterpart_name = con.execute(
            "SELECT canonical_name FROM entities WHERE entity_id = ?", (counterpart_id,)
        ).fetchone()[0]
        relationships.append(RelationshipContext(
            relationship_id=rel_id, relation_type=rel_type, direction=direction,
            counterpart_entity_id=counterpart_id, counterpart_canonical_name=counterpart_name,
            valid_from=valid_from, valid_to=valid_to, confidence=confidence,
            source_evidence_id=source_evidence_id,
        ))

    return EntityContext(
        ticker=ticker, as_of_date=as_of_date, entity_id=entity_id,
        canonical_name=canonical_name, first_seen_doc_id=first_seen_doc_id,
        relationships=relationships,
    )


def as_of(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyMemory360Graph:
    """Composes CompanyMemory360 (Phase 6, called unmodified) with the
    ticker's own knowledge-graph context (this module). Single-ticker
    only, mirroring every prior FSI composition's own guardrail."""
    memory = memory_as_of(con, ticker, as_of_date)
    graph = get_entity_context(con, ticker, as_of_date)
    return CompanyMemory360Graph(ticker=ticker, as_of_date=as_of_date, memory=memory, graph=graph)
