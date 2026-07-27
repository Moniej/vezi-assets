"""Per-document pilot processing lifecycle (2026-07-22 hardening) — what
makes run_phase_c_pilot.py resumable across quota exhaustion, interruption,
or crash, without ever duplicating a document's facts/implications.

Design: `document_processing_status` is the FAST skip/resume signal, but
it is never trusted alone — `should_skip()` and `resume_point()` both
cross-check the actual `extracted_facts`/`investment_implications` rows,
so a stale or crashed status row (e.g. the process was killed between
"mark processing" and "mark completed") can never cause a document to be
silently re-extracted. The status table can lie about WHAT happened; the
data tables cannot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

TERMINAL_STATUSES = {"completed", "blocked_by_self_critique"}
RETRYABLE_STATUSES = {"pending", "processing", "failed", "quota_exceeded"}


def _now() -> str:
    return datetime.now().isoformat()


def mark_status(con, doc_id: int, status: str, *, fact_count: int | None = None,
                implication_count: int | None = None, error_detail: str | None = None,
                model_id: str | None = None, prompt_version: str | None = None,
                started_at: str | None = None) -> None:
    """Upsert + immediate commit — this MUST be durable independent of
    whatever transaction extract.py/self_critique.py have open, so a crash
    immediately after this call still leaves an accurate status row."""
    existing = con.execute(
        "SELECT started_at FROM document_processing_status WHERE doc_id = ?",
        (doc_id,)).fetchone()
    keep_started_at = started_at or (existing[0] if existing else _now())
    con.execute(
        "INSERT INTO document_processing_status (doc_id, status, fact_count, "
        "implication_count, error_detail, model_id, prompt_version, started_at, "
        "updated_at) VALUES (?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(doc_id) DO UPDATE SET status=excluded.status, "
        "fact_count=excluded.fact_count, implication_count=excluded.implication_count, "
        "error_detail=excluded.error_detail, model_id=excluded.model_id, "
        "prompt_version=excluded.prompt_version, updated_at=excluded.updated_at",
        (doc_id, status, fact_count, implication_count, error_detail, model_id,
         prompt_version, keep_started_at, _now()))
    con.commit()


def get_status(con, doc_id: int) -> str | None:
    row = con.execute("SELECT status FROM document_processing_status WHERE doc_id = ?",
                      (doc_id,)).fetchone()
    return row[0] if row else None


def should_skip(con, doc_id: int) -> bool:
    """True only if BOTH the status table says terminal AND the underlying
    data agrees (a document with model_id-tagged extracted_facts rows, or a
    status of 'completed' with fact_count=0 meaning genuinely nothing was
    found — not a crash before any write happened)."""
    status = get_status(con, doc_id)
    if status not in TERMINAL_STATUSES:
        return False
    row = con.execute(
        "SELECT fact_count FROM document_processing_status WHERE doc_id = ?",
        (doc_id,)).fetchone()
    expected_facts = row[0] if row else None
    actual_facts = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE doc_id = ? AND model_id IS NOT NULL",
        (doc_id,)).fetchone()[0]
    if expected_facts is not None and expected_facts != actual_facts:
        # status table disagrees with reality (e.g. a crash between writing
        # facts and marking status) — do NOT trust the stale status, force
        # a resume/retry evaluation instead of skipping.
        return False
    return True


@dataclass
class ResumePoint:
    needs_extraction: bool           # False => facts already exist, skip extract_document
    fact_ids: list[int]
    implication_ids_needing_critique: list[int]   # subset still draft_pending_self_critique


def resume_point(con, doc_id: int) -> ResumePoint:
    """What's already been done for this document, read directly from the
    data tables (never from document_processing_status alone) — the
    mechanism that guarantees extract_document is never called twice for
    the same document, even after an arbitrary crash point."""
    fact_ids = [r[0] for r in con.execute(
        "SELECT fact_id FROM extracted_facts WHERE doc_id = ? AND model_id IS NOT NULL",
        (doc_id,)).fetchall()]
    if not fact_ids:
        return ResumePoint(needs_extraction=True, fact_ids=[], implication_ids_needing_critique=[])
    placeholders = ",".join("?" * len(fact_ids))
    pending_critique = [r[0] for r in con.execute(
        f"SELECT implication_id FROM investment_implications WHERE fact_id IN "
        f"({placeholders}) AND status = 'draft_pending_self_critique'",
        fact_ids).fetchall()]
    return ResumePoint(needs_extraction=False, fact_ids=fact_ids,
                       implication_ids_needing_critique=pending_critique)


def remaining_doc_ids(con, pilot_doc_ids: list[int]) -> list[int]:
    """Pilot doc_ids not yet in a terminal state — what a resumed run
    should actually process."""
    return [d for d in pilot_doc_ids if not should_skip(con, d)]


def determine_final_status(con, fact_ids: list[int]) -> str:
    """'blocked_by_self_critique' only if EVERY implication for this
    document's facts ended up blocked; 'completed' otherwise (including
    the legitimate zero-facts case — nothing to find is not a failure)."""
    if not fact_ids:
        return "completed"
    placeholders = ",".join("?" * len(fact_ids))
    statuses = [r[0] for r in con.execute(
        f"SELECT status FROM investment_implications WHERE fact_id IN ({placeholders})",
        fact_ids).fetchall()]
    if statuses and all(s == "blocked_by_self_critique" for s in statuses):
        return "blocked_by_self_critique"
    return "completed"
