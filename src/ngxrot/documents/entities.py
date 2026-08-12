"""Minimal entity resolution for Phase C (docs/AI_INTELLIGENCE_LAYER_
ARCHITECTURE.md §4.2). Deliberately simple for this pilot's scale: exact
canonical-name match (case-insensitive), else create. The architecture doc's
full design (fuzzy matching + a human-confirmable merge queue before two
mentions are silently combined) is NOT built here — at pilot scale (a
handful of documents) a wrong silent merge is a real but small-blast-radius
risk; building the full merge-queue UI/workflow for a ~20-document pilot
would be scope creep beyond Phase C. Flagged explicitly in the completion
report, not silently simplified.

`record_relationship` (Phase E, 2026-07-26) is the first code path that
actually writes to `entity_relationships` — the table existed since Phase C
"for schema completeness" but nothing ever populated it (confirmed by grep
before this change). Deliberately conservative: relation_type is only ever
the honest, literal thing the model already said (which effect-chain order
this is), never an invented taxonomy label like "competitor_of"/
"supplier_to" the model was never asked to produce — inventing a more
specific relationship type than the evidence supports would itself be a
small fabrication. A real semantic relationship taxonomy would require
extending the extraction prompt to actually ask the model to classify
relationship nature — a bigger, LLM-cost-bearing change, not made here.

`resolve_or_create_entity` also now records to `entity_mentions` (fixed
2026-08-11, HANDOFF.md) — same class of gap as `entity_relationships`
above: the table existed since Phase C, nothing had ever written to it
(confirmed by grep before this change). Pure mechanical bookkeeping (which
document mentions which entity), no LLM judgment involved, no fabrication
risk — every call to `resolve_or_create_entity` already knows this fact.
"""

from __future__ import annotations


def _exact_name_match_ticker(con, name: str) -> str | None:
    """Phase E (2026-07-26): the ONLY ticker-resolution attempt made for a
    free-text entity mention — exact, case-insensitive, whitespace-trimmed
    match against securities.name. Deliberately NOT fuzzy (no substring/
    edit-distance matching): this platform's standing rule is "never guess
    a match" (see data/reference/symbol_renames.csv's verified-only
    discipline, documents.raw_symbol resolution in Phase A). Most
    real-world mentions ("GTBank" for GTCO, "Zenith" for ZENITHBANK) will
    NOT resolve under this rule — an accepted, disclosed coverage
    limitation, not a bug to silently work around with fuzzy matching."""
    row = con.execute(
        "SELECT ticker FROM securities WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
        (name,)).fetchone()
    return row[0] if row else None


def _record_mention(con, doc_id: int, entity_id: int) -> None:
    """entity_mentions has existed in the schema since Phase C but nothing
    ever wrote to it (confirmed by grep before this change, 2026-08-11) --
    resolve_or_create_entity is the one place that already knows "this
    entity was mentioned in this document" every time it's called, whether
    the entity is newly created or already existed. Idempotent by explicit
    check (the table carries no UNIQUE constraint on (doc_id, entity_id),
    matching record_relationship's own idempotency style rather than
    relying on a schema constraint)."""
    existing = con.execute(
        "SELECT 1 FROM entity_mentions WHERE doc_id = ? AND entity_id = ?",
        (doc_id, entity_id)).fetchone()
    if existing is None:
        con.execute("INSERT INTO entity_mentions (doc_id, entity_id) VALUES (?,?)",
                   (doc_id, entity_id))


def resolve_or_create_entity(con, canonical_name: str, entity_type: str,
                             doc_id: int, ticker: str | None = None) -> int:
    name = canonical_name.strip()
    row = con.execute(
        "SELECT entity_id FROM entities WHERE LOWER(canonical_name) = LOWER(?)",
        (name,)).fetchone()
    if row:
        entity_id = row[0]
        _record_mention(con, doc_id, entity_id)
        con.commit()
        return entity_id
    if ticker is None and entity_type != "company":
        ticker = _exact_name_match_ticker(con, name)
    cur = con.execute(
        "INSERT INTO entities (entity_type, canonical_name, ticker, first_seen_doc_id) "
        "VALUES (?,?,?,?)",
        (entity_type, name, ticker, doc_id))
    entity_id = cur.lastrowid
    _record_mention(con, doc_id, entity_id)
    con.commit()
    return entity_id


def record_relationship(con, subject_entity_id: int, relation_type: str,
                        object_entity_id: int, source_evidence_id: int,
                        confidence: float, valid_from: str | None = None) -> int | None:
    """Evidence-backed only: caller must supply a `source_evidence_id` that
    already passed grounding (checked by the caller, not here — this
    function trusts the id it's given the same way extracted_facts trusts
    an already-validated evidence_id). Never called for a self-relationship
    (subject == object) or without evidence — both are the caller's
    responsibility, enforced at the one call site in extract.py.
    Idempotent: a rerun (e.g. force=True re-extraction) does not duplicate
    the same (subject, relation_type, object, evidence) row."""
    if subject_entity_id == object_entity_id:
        return None
    existing = con.execute(
        "SELECT relationship_id FROM entity_relationships WHERE subject_entity_id = ? "
        "AND relation_type = ? AND object_entity_id = ? AND source_evidence_id = ?",
        (subject_entity_id, relation_type, object_entity_id, source_evidence_id)).fetchone()
    if existing:
        return existing[0]
    cur = con.execute(
        "INSERT INTO entity_relationships (subject_entity_id, relation_type, "
        "object_entity_id, valid_from, source_evidence_id, confidence) "
        "VALUES (?,?,?,?,?,?)",
        (subject_entity_id, relation_type, object_entity_id, valid_from,
         source_evidence_id, confidence))
    con.commit()
    return cur.lastrowid
