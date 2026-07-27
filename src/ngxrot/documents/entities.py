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
small fabrication.
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


def resolve_or_create_entity(con, canonical_name: str, entity_type: str,
                             doc_id: int, ticker: str | None = None) -> int:
    name = canonical_name.strip()
    row = con.execute(
        "SELECT entity_id FROM entities WHERE LOWER(canonical_name) = LOWER(?)",
        (name,)).fetchone()
    if row:
        return row[0]
    if ticker is None and entity_type != "company":
        ticker = _exact_name_match_ticker(con, name)
    cur = con.execute(
        "INSERT INTO entities (entity_type, canonical_name, ticker, first_seen_doc_id) "
        "VALUES (?,?,?,?)",
        (entity_type, name, ticker, doc_id))
    con.commit()
    return cur.lastrowid


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
