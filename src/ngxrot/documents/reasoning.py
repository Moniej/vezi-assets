"""Top-level entry point: the Financial Reasoning Engine
(docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md §4.5, §9). Ties extract.py
(Steps 1-13, draft) and self_critique.py (Step 14, gate) together for one
document. The only function a pilot-runner script needs to call.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .extract import ExtractionResult, extract_document
from .llm_providers import LLMProvider
from .self_critique import critique_implication


@dataclass
class FinancialReasoningResult:
    doc_id: int
    extraction: ExtractionResult
    critiques: list[dict] = field(default_factory=list)


def financial_reasoning(con, provider: LLMProvider, doc_id: int,
                        force: bool = False, cache_dir=None) -> FinancialReasoningResult:
    extraction = extract_document(con, provider, doc_id, force=force, cache_dir=cache_dir)
    critiques = []
    for implication_id in extraction.implication_ids:
        critiques.append(critique_implication(con, provider, implication_id,
                                              force=force, cache_dir=cache_dir))
    return FinancialReasoningResult(doc_id=doc_id, extraction=extraction, critiques=critiques)


def resumable_financial_reasoning(con, provider: LLMProvider, doc_id: int,
                                 force: bool = False, cache_dir=None) -> FinancialReasoningResult:
    """2026-07-22 hardening: like financial_reasoning(), but never
    duplicates a document's facts/implications across runs. If this
    document already has model-sourced extracted_facts (from a prior run
    interrupted after extraction but before/during critique — e.g. a
    quota failure mid-critique), extraction is SKIPPED entirely and only
    the implications still `draft_pending_self_critique` are critiqued.
    financial_reasoning() itself is deliberately left unchanged so its
    existing callers/tests keep their exact, already-verified behavior —
    this is a separate, additive entry point for resumable orchestration
    (run_phase_c_pilot.py), not a replacement."""
    from . import pipeline_status as pstatus

    resume = pstatus.resume_point(con, doc_id)
    if resume.needs_extraction or force:
        extraction = extract_document(con, provider, doc_id, force=force, cache_dir=cache_dir)
        to_critique = extraction.implication_ids
    else:
        fact_ids = resume.fact_ids
        placeholders = ",".join("?" * len(fact_ids))
        all_implication_ids = [r[0] for r in con.execute(
            f"SELECT implication_id FROM investment_implications WHERE fact_id IN "
            f"({placeholders})", fact_ids).fetchall()]
        extraction = ExtractionResult(
            doc_id=doc_id, parse_ok=True, fact_ids=fact_ids,
            implication_ids=all_implication_ids,
            warnings=["resumed: extraction already existed for this document — "
                     "skipped re-extraction to avoid duplicating facts"])
        to_critique = resume.implication_ids_needing_critique

    critiques = [critique_implication(con, provider, implication_id, force=force,
                                      cache_dir=cache_dir) for implication_id in to_critique]
    return FinancialReasoningResult(doc_id=doc_id, extraction=extraction, critiques=critiques)
