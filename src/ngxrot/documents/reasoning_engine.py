"""Question-driven Financial Reasoning Engine orchestrator (Phase E,
owner-approved 2026-07-26) — the "reason over the graph first, consult
documents only when additional evidence is required" entry point that did
not exist before Phase E. `financial_reasoning`/`resumable_financial_
reasoning` (reasoning.py) remain the PER-DOCUMENT primitive they always
were; this module coordinates them, it does not replace or duplicate
their logic.

Workflow (`reason_about_company`):
  1. Load a ReasoningContext for the ticker (context.py — existing graph
     rows: facts, implications, entity relationships, factor exposures,
     event history).
  2. Measure coverage (ReasoningContext.coverage_notes, already computed).
  3. If coverage is thin, retrieve additional documents via retrieval.py
     and run them through the UNCHANGED extraction + grounding +
     self-critique pipeline (`resumable_financial_reasoning`) — no new
     LLM call shape is introduced, no gate is bypassed.
  4. Re-load the context (cheap SQL) so newly created rows are included.
  5. Assemble a structured ReasoningResult purely by aggregating already
     -governed rows (extracted_facts, causal_chain_steps,
     impact_assessments, effect_chains, self_critique_reviews,
     research_task_candidates, factor_exposures, event_reaction_stats) —
     this step makes NO new LLM call and therefore has nothing new to pass
     through grounding/self-critique; every fact/implication it cites
     already passed those gates when it was created.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import industry_reasoning, retrieval
from .context import ReasoningContext, build_reasoning_context
from .llm_providers import LLMProvider
from .reasoning import resumable_financial_reasoning

DEFAULT_MAX_NEW_DOCUMENTS = 5   # cap on retrieval-triggered new LLM extraction
                                # per call — avoids one question silently
                                # burning an unbounded number of API calls


@dataclass
class FactSummary:
    fact_id: int
    fact_type: str
    description: str            # "what happened"
    doc_id: int
    filing_date: str
    causal_chain: list[dict] = field(default_factory=list)          # "why" / "why now"
    impact_assessments: dict[str, dict] = field(default_factory=dict)
    implication: dict | None = None
    effects_by_order: dict[int, list[dict]] = field(default_factory=dict)  # 1/2/3rd order
    principal_risks: list[dict] = field(default_factory=list)
    alternative_explanations: list[dict] = field(default_factory=list)
    contradicting_evidence: list[dict] = field(default_factory=list)
    confidence_improving_info: list[dict] = field(default_factory=list)


@dataclass
class ReasoningResult:
    ticker: str
    as_of: str
    name: str | None
    facts: list[FactSummary] = field(default_factory=list)
    factor_exposures: dict = field(default_factory=dict)
    event_reaction_stats: dict = field(default_factory=dict)
    entity_relationships: list[dict] = field(default_factory=list)
    coverage_notes: list[str] = field(default_factory=list)
    newly_processed_doc_ids: list[int] = field(default_factory=list)
    retrieval_warnings: list[str] = field(default_factory=list)
    peer_propagations_received: list[dict] = field(default_factory=list)  # this ticker AS a peer
    propagated_implication_ids: list[int] = field(default_factory=list)   # this ticker's NEW
                                                                          # implications propagated OUT


_RISK_CATEGORIES = {"execution_risk", "regulatory_risk", "liquidity"}


def _fact_summary(con, fact_row: dict) -> FactSummary:
    fact_id = fact_row["fact_id"]
    fs = FactSummary(fact_id=fact_id, fact_type=fact_row["fact_type"],
                     description=fact_row["description"], doc_id=fact_row["doc_id"],
                     filing_date=fact_row["filing_date"])

    fs.causal_chain = [
        {"step_order": r[0], "statement": r[1], "inferred": bool(r[2])}
        for r in con.execute(
            "SELECT step_order, statement, inferred FROM causal_chain_steps "
            "WHERE fact_id = ? ORDER BY step_order", (fact_id,)).fetchall()]

    fs.impact_assessments = {
        r[0]: {"direction": r[1], "explanation": r[2]}
        for r in con.execute(
            "SELECT category, direction, explanation FROM impact_assessments "
            "WHERE fact_id = ?", (fact_id,)).fetchall()}
    fs.principal_risks = [
        {"category": cat, **entry} for cat, entry in fs.impact_assessments.items()
        if cat in _RISK_CATEGORIES and entry["direction"] == "negative"]

    impl_row = con.execute(
        "SELECT implication_id, ticker, direction, duration_bucket, magnitude, "
        "confidence, confidence_rationale, status, action_recommendation, "
        "market_reaction_assessment, contradicts_implication_id, "
        "corroborates_implication_id, consistency_note "
        "FROM investment_implications WHERE fact_id = ?", (fact_id,)).fetchone()
    if impl_row is None:
        return fs
    (implication_id, ticker, direction, duration_bucket, magnitude, confidence,
     rationale, status, action, market_reaction, contradicts_id, corroborates_id,
     consistency_note) = impl_row
    fs.implication = {
        "implication_id": implication_id, "ticker": ticker, "direction": direction,
        "duration_bucket": duration_bucket, "magnitude": magnitude, "confidence": confidence,
        "confidence_rationale": rationale, "status": status, "action_recommendation": action,
        "market_reaction_assessment": market_reaction,
        "contradicts_implication_id": contradicts_id,
        "corroborates_implication_id": corroborates_id, "consistency_note": consistency_note,
    }

    for order_n, desc, entity_name in con.execute(
        "SELECT ec.order_n, ec.description, en.canonical_name FROM effect_chains ec "
        "LEFT JOIN entities en ON en.entity_id = ec.affected_entity_id "
        "WHERE ec.implication_id = ? ORDER BY ec.order_n", (implication_id,)).fetchall():
        fs.effects_by_order.setdefault(order_n, []).append(
            {"description": desc, "affected_entity": entity_name})

    for question, finding, explanation in con.execute(
        "SELECT question, finding, explanation FROM self_critique_reviews "
        "WHERE implication_id = ?", (implication_id,)).fetchall():
        if question == "ignored_alternative_explanation" and finding in ("concern", "fail"):
            fs.alternative_explanations.append({"finding": finding, "explanation": explanation})
        if question == "contradicts_prior_evidence" and finding in ("concern", "fail"):
            fs.contradicting_evidence.append({"finding": finding, "explanation": explanation})
    if consistency_note:
        fs.contradicting_evidence.append({"finding": "cross_reference", "explanation": consistency_note})

    fs.confidence_improving_info = [
        {"description": r[0], "status": r[1]} for r in con.execute(
            "SELECT description, status FROM research_task_candidates "
            "WHERE implication_id = ?", (implication_id,)).fetchall()]

    return fs


def _needs_retrieval(ctx: ReasoningContext) -> bool:
    """Coverage is 'thin' if there are candidate documents for this ticker
    that have never been through extraction — not merely if coverage_notes
    is non-empty (a ticker can legitimately have zero events on record,
    that alone shouldn't trigger a document fetch)."""
    return any(d.has_text and not d.already_extracted for d in ctx.documents)


def reason_about_company(con, provider: LLMProvider, ticker: str, as_of: str | None = None,
                         cache_dir=None, force: bool = False,
                         max_new_documents: int = DEFAULT_MAX_NEW_DOCUMENTS) -> ReasoningResult:
    ctx = build_reasoning_context(con, ticker, as_of)
    newly_processed: list[int] = []
    warnings: list[str] = []

    if _needs_retrieval(ctx):
        candidates = [d for d in ctx.documents if d.has_text and not d.already_extracted]
        for doc in candidates[:max_new_documents]:
            try:
                result = resumable_financial_reasoning(
                    con, provider, doc.doc_id, force=force, cache_dir=cache_dir)
                newly_processed.append(doc.doc_id)
                warnings.extend(result.extraction.warnings)
            except Exception as e:  # noqa: BLE001 — one bad document must not
                                    # abort reasoning about the rest of the
                                    # company's evidence; disclosed, not swallowed
                warnings.append(f"doc_id {doc.doc_id}: extraction failed, skipped ({e!r})")
        if len(candidates) > max_new_documents:
            warnings.append(
                f"{len(candidates) - max_new_documents} additional unretrieved candidate "
                f"document(s) exist beyond max_new_documents={max_new_documents} — not fetched "
                f"this call, not silently ignored")
        ctx = build_reasoning_context(con, ticker, as_of)  # re-load: cheap SQL,
                                                            # picks up new rows

    result = ReasoningResult(ticker=ticker, as_of=ctx.as_of, name=ctx.name,
                             factor_exposures=ctx.factor_exposures,
                             event_reaction_stats=ctx.event_reaction_stats,
                             entity_relationships=ctx.entity_relationships,
                             coverage_notes=ctx.coverage_notes,
                             newly_processed_doc_ids=newly_processed,
                             retrieval_warnings=warnings,
                             peer_propagations_received=ctx.peer_propagations)

    seen_fact_ids = set()
    for f in ctx.facts:
        if f["fact_id"] in seen_fact_ids:
            continue
        seen_fact_ids.add(f["fact_id"])
        result.facts.append(_fact_summary(con, f))

    # Phase F: propagate any implication that came from a document THIS
    # call newly processed — not every existing implication on every call,
    # which would silently re-walk the whole graph's history each time.
    if newly_processed:
        new_doc_ids = set(newly_processed)
        for fs in result.facts:
            if fs.doc_id in new_doc_ids and fs.implication is not None:
                result.propagated_implication_ids.extend(
                    industry_reasoning.propagate_implication(
                        con, fs.implication["implication_id"]))

    return result
