"""Per-dataset-type exporters (DATASET_GENERATION_AND_TRAINING_SPEC.md §2).
Read-only against the AI Intelligence Layer's schema; every exporter
either issues a plain SQL query or calls an existing ngxrot.documents
module's public function (coverage_assessment.py, evidence_ranking.py,
context.py, retrieval.py) -- nothing here reimplements grounding, ranking,
coverage, or self-critique logic.

Every exporter has the same signature: `export_<type>(con, *, limit=None)
-> list[TrainingExample]`, registered in EXPORTERS below so the CLI/audit
layer never needs a type-specific branch. Honesty over completeness: a
type with no real data today (e.g. event_understanding, whose source
columns are 0/11533 populated) returns an empty list and says so --
nothing is fabricated to make a type look populated.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from ngxrot.documents import coverage_assessment, evidence_ranking
from ngxrot.documents.context import build_reasoning_context
from ngxrot.lim import quality
from ngxrot.lim.schema import TrainingExample, make_unique_id

PKG_ROOT = Path(__file__).resolve().parents[3]


def _make_example(con, *, task: str, unique_id: str, instruction: str, context: dict,
                  expected_output: dict, retrieved_documents: list, retrieved_facts: list,
                  source_documents: list, citations: list | None = None,
                  reasoning_chain: list | None = None, self_critique: dict | None = None,
                  contradiction_analysis: dict | None = None, coverage_score: float | None = None,
                  fact_id: int | None = None, implication_id: int | None = None,
                  reasoning_context: dict | None = None) -> TrainingExample:
    assessment = quality.assess_example_quality(
        con, task=task, fact_id=fact_id, implication_id=implication_id,
        coverage_score=coverage_score)
    status, reason = quality.decide_acceptance(task, assessment)
    return TrainingExample(
        unique_id=unique_id, task=task, instruction=instruction, context=context,
        retrieved_documents=retrieved_documents, retrieved_facts=retrieved_facts,
        reasoning_context=reasoning_context or {}, expected_output=expected_output,
        citations=citations or [], evidence_tier=assessment.evidence_tier,
        confidence=context.get("confidence"), coverage_score=coverage_score,
        reasoning_chain=reasoning_chain or [], self_critique=self_critique,
        contradiction_analysis=contradiction_analysis, acceptance_status=status,
        rejection_reason=reason, quality_score=assessment.quality_score,
        source_documents=source_documents)


def _fact_citations(con, fact_id: int) -> list[dict]:
    """The real `grounding_check` enum ('passed'/'failed'/'not_run'), fetched
    directly from extracted_facts -- NOT evidence_ranking's tier_rationale
    (a human-readable explanation string, wrong shape for audit.py's
    grounding_integrity check, which needs the literal status value)."""
    row = con.execute("SELECT grounding_check FROM extracted_facts WHERE fact_id = ?",
                      (fact_id,)).fetchone()
    grounding_check = row[0] if row else None
    return [{"evidence_id": r["evidence_id"], "doc_id": r["doc_id"],
            "quoted_text": r["quoted_text"], "grounding_check": grounding_check}
           for r in evidence_ranking.rank_evidence_for_fact(con, fact_id)]


# ---------------------------------------------------------------------------
# 1. extraction (all facts, deterministic + LLM) / 2. corporate_actions subset
# ---------------------------------------------------------------------------

def _fact_taxonomy_leaves(group_names: set[str] | None = None) -> set[str]:
    raw = tomllib.loads((PKG_ROOT / "configs/fact_taxonomy.toml").read_text(encoding="utf-8"))
    if group_names is None:
        return {t for spec in raw.values() for t in spec.get("types", [])}
    return {t for name, spec in raw.items() if name in group_names for t in spec.get("types", [])}


def _export_facts(con, *, task: str, fact_type_filter: set[str] | None, limit: int | None):
    clauses = []
    if fact_type_filter is not None:
        placeholders = ",".join("?" * len(fact_type_filter))
        clauses.append(f"ef.fact_type IN ({placeholders})")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (f"SELECT ef.fact_id, ef.doc_id, ef.fact_type, ef.description, ef.numeric_value, "
          f"ef.extraction_confidence, ef.model_id, d.ticker, d.filing_date "
          f"FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id {where} "
          f"ORDER BY ef.fact_id" + (f" LIMIT {limit}" if limit else ""))
    params = list(fact_type_filter) if fact_type_filter is not None else []
    rows = con.execute(sql, params).fetchall()
    out = []
    for fact_id, doc_id, fact_type, description, numeric_value, extraction_confidence, \
            model_id, ticker, filing_date in rows:
        out.append(_make_example(
            con, task=task, unique_id=make_unique_id(task, fact_id),
            instruction=f"Extract the material fact from this {fact_type} filing as structured data.",
            context={"ticker": ticker, "filing_date": filing_date, "fact_type": fact_type,
                    "confidence": extraction_confidence, "source": "llm" if model_id else "deterministic"},
            expected_output={"fact_type": fact_type, "description": description,
                            "numeric_value": numeric_value},
            retrieved_documents=[doc_id], retrieved_facts=[fact_id], source_documents=[doc_id],
            citations=_fact_citations(con, fact_id), fact_id=fact_id))
    return out


def export_extraction(con, *, limit=None):
    return _export_facts(con, task="extraction", fact_type_filter=None, limit=limit)


def export_corporate_actions(con, *, limit=None):
    leaves = _fact_taxonomy_leaves({"capital_and_balance_sheet", "corporate_events"})
    return _export_facts(con, task="corporate_actions", fact_type_filter=leaves, limit=limit)


# ---------------------------------------------------------------------------
# 3. financial_reasoning (Steps 1-13 full shape, LLM-sourced only)
# ---------------------------------------------------------------------------

def export_financial_reasoning(con, *, limit=None):
    sql = ("SELECT ef.fact_id, ef.doc_id, ef.fact_type, ef.description, d.ticker, d.filing_date, "
          "ii.implication_id, ii.direction, ii.magnitude, ii.duration_bucket, ii.confidence, "
          "ii.confidence_rationale "
          "FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id "
          "LEFT JOIN investment_implications ii ON ii.fact_id = ef.fact_id "
          "WHERE ef.model_id IS NOT NULL ORDER BY ef.fact_id" + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    _ctx_cache: dict = {}
    for fact_id, doc_id, fact_type, description, ticker, filing_date, implication_id, \
            direction, magnitude, duration_bucket, confidence, rationale in rows:
        chain = [{"step_order": r[0], "statement": r[1], "inferred": bool(r[2])}
                for r in con.execute(
                    "SELECT step_order, statement, inferred FROM causal_chain_steps "
                    "WHERE fact_id = ? ORDER BY step_order", (fact_id,)).fetchall()]
        impacts = {r[0]: {"direction": r[1], "explanation": r[2]} for r in con.execute(
            "SELECT category, direction, explanation FROM impact_assessments WHERE fact_id = ?",
            (fact_id,)).fetchall()}
        # Cache one ReasoningContext per (ticker, filing_date) -- it's
        # expensive (touches the quant equity panel via company_intelligence.
        # build_profile) and multiple facts commonly share the same ticker;
        # calling it per-fact was a real, needless N-times-over-tickers cost.
        cache_key = (ticker, filing_date)
        if cache_key not in _ctx_cache:
            try:
                _ctx_cache[cache_key] = build_reasoning_context(con, ticker, filing_date)
            except Exception:  # noqa: BLE001 -- coverage is best-effort context, never fatal to export
                _ctx_cache[cache_key] = None
        ctx = _ctx_cache[cache_key]
        cov = ctx.coverage_assessment.coverage_score if ctx and ctx.coverage_assessment else None
        out.append(_make_example(
            con, task="financial_reasoning", unique_id=make_unique_id("financial_reasoning", fact_id),
            instruction="Identify the material fact, explain why it matters causally, and assess "
                       "its impact across the standard categories.",
            context={"ticker": ticker, "filing_date": filing_date, "fact_type": fact_type,
                    "confidence": confidence},
            expected_output={"description": description, "direction": direction,
                            "magnitude": magnitude, "duration_bucket": duration_bucket,
                            "impact_assessments": impacts},
            retrieved_documents=[doc_id], retrieved_facts=[fact_id], source_documents=[doc_id],
            citations=_fact_citations(con, fact_id), reasoning_chain=chain,
            coverage_score=cov, fact_id=fact_id, implication_id=implication_id))
    return out


# ---------------------------------------------------------------------------
# 4. self_critique (both pass and fail/concern findings -- negatives wanted)
# ---------------------------------------------------------------------------

def export_self_critique(con, *, limit=None):
    sql = ("SELECT scr.critique_id, scr.implication_id, scr.question, scr.finding, "
          "scr.explanation, ii.fact_id, ii.direction, ii.magnitude, ii.confidence, "
          "ii.status, d.ticker "
          "FROM self_critique_reviews scr "
          "JOIN investment_implications ii ON ii.implication_id = scr.implication_id "
          "JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
          "JOIN documents d ON d.doc_id = ef.doc_id "
          "ORDER BY scr.critique_id" + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for critique_id, implication_id, question, finding, explanation, fact_id, direction, \
            magnitude, confidence, status, ticker in rows:
        out.append(_make_example(
            con, task="self_critique", unique_id=make_unique_id("self_critique", critique_id),
            instruction=f"Challenge this draft conclusion on the question: {question}.",
            context={"ticker": ticker, "draft_direction": direction, "draft_magnitude": magnitude,
                    "confidence": confidence, "question": question},
            expected_output={"finding": finding, "explanation": explanation,
                            "resulting_status": status},
            retrieved_documents=[], retrieved_facts=[fact_id], source_documents=[],
            self_critique={"question": question, "finding": finding}, fact_id=fact_id,
            implication_id=implication_id))
    return out


# ---------------------------------------------------------------------------
# 5. citation_grounding (positive AND negative -- real grounding failures included)
# ---------------------------------------------------------------------------

def export_citation_grounding(con, *, limit=None):
    sql = ("SELECT ef.fact_id, e.evidence_id, e.doc_id, e.quoted_text, ef.grounding_check, "
          "ef.description "
          "FROM extracted_facts ef JOIN evidence e ON e.evidence_id = ef.evidence_id "
          "WHERE ef.model_id IS NOT NULL ORDER BY ef.fact_id" + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for fact_id, evidence_id, doc_id, quoted_text, grounding_check, description in rows:
        out.append(_make_example(
            con, task="citation_grounding", unique_id=make_unique_id("citation_grounding", evidence_id),
            instruction="Does this quoted passage actually support the claim, verbatim?",
            context={"claim": description},
            expected_output={"verdict": "grounded" if grounding_check == "passed" else "not_grounded",
                            "grounding_check": grounding_check},
            retrieved_documents=[doc_id], retrieved_facts=[fact_id], source_documents=[doc_id],
            citations=[{"evidence_id": evidence_id, "doc_id": doc_id, "quoted_text": quoted_text,
                      "grounding_check": grounding_check}],
            fact_id=fact_id))
    return out


# ---------------------------------------------------------------------------
# 6. contradiction_detection (trust-tier-aware, per stabilization pass)
# ---------------------------------------------------------------------------

def export_contradiction_detection(con, *, limit=None):
    rows = con.execute(
        "SELECT implication_id FROM investment_implications "
        "WHERE contradicts_implication_id IS NOT NULL"
        + (f" LIMIT {limit}" if limit else "")).fetchall()
    out = []
    for (implication_id,) in rows:
        conflict = evidence_ranking.assess_implication_conflict(con, implication_id)
        if conflict is None:
            continue
        fact_id = con.execute(
            "SELECT fact_id FROM investment_implications WHERE implication_id = ?",
            (implication_id,)).fetchone()[0]
        out.append(_make_example(
            con, task="contradiction_detection",
            unique_id=make_unique_id("contradiction_detection", implication_id),
            instruction="Two implications disagree for the same ticker/fact_type. Which is more "
                       "reliable, and why?",
            context={"implication_id": implication_id,
                    "contradicts_implication_id": conflict.contradicts_implication_id},
            expected_output={"confidence_preferred": conflict.confidence_preferred,
                            "trust_tier_preferred": conflict.trust_tier_preferred,
                            "agreement": conflict.agreement, "rationale": conflict.note},
            retrieved_documents=[], retrieved_facts=[fact_id], source_documents=[],
            contradiction_analysis=conflict.__dict__, fact_id=fact_id,
            implication_id=implication_id))
    return out


# ---------------------------------------------------------------------------
# 7. investment_decision_support (research-flag framing, never advice)
# ---------------------------------------------------------------------------

def export_investment_decision_support(con, *, limit=None):
    sql = ("SELECT ii.implication_id, ii.fact_id, ii.direction, ii.magnitude, ii.duration_bucket, "
          "ii.action_recommendation, ii.bull_case_delta, ii.bear_case_delta, ii.base_case_delta, "
          "ii.confidence, d.ticker "
          "FROM investment_implications ii JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
          "JOIN documents d ON d.doc_id = ef.doc_id ORDER BY ii.implication_id"
          + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for implication_id, fact_id, direction, magnitude, duration_bucket, action, bull, bear, \
            base, confidence, ticker in rows:
        out.append(_make_example(
            con, task="investment_decision_support",
            unique_id=make_unique_id("investment_decision_support", implication_id),
            instruction="What would a disciplined research analyst flag for further review here? "
                       "This is a research-priority classification, NOT investment advice.",
            context={"ticker": ticker, "direction": direction, "magnitude": magnitude,
                    "confidence": confidence},
            expected_output={"action_recommendation": action, "bull_case_delta": bull,
                            "bear_case_delta": bear, "base_case_delta": base,
                            "duration_bucket": duration_bucket},
            retrieved_documents=[], retrieved_facts=[fact_id], source_documents=[],
            fact_id=fact_id, implication_id=implication_id))
    return out


# ---------------------------------------------------------------------------
# 8. portfolio_reasoning (deliberately scope-limited, spec §2.2 -- descriptive
# commentary only, never an allocation/weight)
# ---------------------------------------------------------------------------

def export_portfolio_reasoning(con, *, limit=None):
    sql = ("SELECT ii.implication_id, ii.fact_id, ii.portfolio_sizing_note, "
          "ii.risk_profile_direction, d.ticker "
          "FROM investment_implications ii JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
          "JOIN documents d ON d.doc_id = ef.doc_id "
          "WHERE ii.portfolio_sizing_note IS NOT NULL ORDER BY ii.implication_id"
          + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for implication_id, fact_id, note, risk_dir, ticker in rows:
        out.append(_make_example(
            con, task="portfolio_reasoning",
            unique_id=make_unique_id("portfolio_reasoning", implication_id),
            instruction="Describe, qualitatively, how this fact might bear on portfolio "
                       "considerations. Never propose a position size, weight, or allocation.",
            context={"ticker": ticker},
            expected_output={"portfolio_sizing_note": note, "risk_profile_direction": risk_dir},
            retrieved_documents=[], retrieved_facts=[fact_id], source_documents=[],
            fact_id=fact_id, implication_id=implication_id))
    return out


# ---------------------------------------------------------------------------
# 9. entity_recognition (entities table directly -- entity_mentions is
# currently unpopulated platform-wide, a real gap disclosed here rather than
# silently producing zero rows when a perfectly good source table exists)
# ---------------------------------------------------------------------------

def export_entity_recognition(con, *, limit=None):
    sql = ("SELECT entity_id, entity_type, canonical_name, ticker, first_seen_doc_id "
          "FROM entities WHERE first_seen_doc_id IS NOT NULL ORDER BY entity_id"
          + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for entity_id, entity_type, canonical_name, ticker, doc_id in rows:
        out.append(_make_example(
            con, task="entity_recognition", unique_id=make_unique_id("entity_recognition", entity_id),
            instruction="Identify this named entity and its type as mentioned in the filing.",
            context={"ticker": ticker},
            expected_output={"canonical_name": canonical_name, "entity_type": entity_type,
                            "resolved_ticker": ticker},
            retrieved_documents=[doc_id], retrieved_facts=[], source_documents=[doc_id]))
    return out


# ---------------------------------------------------------------------------
# 10. knowledge_graph_completion (entity_relationships -- honestly near-empty
# today, per spec §2 row #17's own maturity disclosure)
# ---------------------------------------------------------------------------

def export_knowledge_graph_completion(con, *, limit=None):
    sql = ("SELECT r.relationship_id, subj.canonical_name, r.relation_type, obj.canonical_name, "
          "r.confidence "
          "FROM entity_relationships r "
          "JOIN entities subj ON subj.entity_id = r.subject_entity_id "
          "JOIN entities obj ON obj.entity_id = r.object_entity_id "
          "ORDER BY r.relationship_id" + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for relationship_id, subj_name, relation_type, obj_name, confidence in rows:
        out.append(_make_example(
            con, task="knowledge_graph_completion",
            unique_id=make_unique_id("knowledge_graph_completion", relationship_id),
            instruction=f"Given entity {subj_name!r}, complete the relation {relation_type!r}.",
            context={"subject": subj_name, "relation_type": relation_type},
            expected_output={"object": obj_name, "confidence": confidence},
            retrieved_documents=[], retrieved_facts=[], source_documents=[]))
    return out


# ---------------------------------------------------------------------------
# 11. event_understanding (Phase C identification columns -- 0/11533 populated
# platform-wide today; exporter is real and will pick up rows the moment
# they exist, exports 0 honestly until then)
# ---------------------------------------------------------------------------

def export_event_understanding(con, *, limit=None):
    sql = ("SELECT doc_id, ticker, event_date, news_classification, filing_date "
          "FROM documents WHERE event_date IS NOT NULL ORDER BY doc_id"
          + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for doc_id, ticker, event_date, news_classification, filing_date in rows:
        out.append(_make_example(
            con, task="event_understanding", unique_id=make_unique_id("event_understanding", doc_id),
            instruction="Classify the event type and date this filing describes.",
            context={"ticker": ticker, "filing_date": filing_date},
            expected_output={"event_date": event_date, "news_classification": news_classification},
            retrieved_documents=[doc_id], retrieved_facts=[], source_documents=[doc_id]))
    return out


# ---------------------------------------------------------------------------
# 12. coverage_assessment (one example per real ticker with implications)
# ---------------------------------------------------------------------------

def export_coverage_assessment(con, *, limit=None):
    tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM investment_implications WHERE ticker IS NOT NULL"
        + (f" LIMIT {limit}" if limit else "")).fetchall()]
    out = []
    for ticker in tickers:
        ctx = build_reasoning_context(con, ticker)
        ca = ctx.coverage_assessment
        if ca is None:
            continue
        out.append(_make_example(
            con, task="coverage_assessment", unique_id=make_unique_id("coverage_assessment", ticker),
            instruction="Assess how much evidence backs this ticker and what's missing.",
            context={"ticker": ticker, "as_of": ctx.as_of},
            expected_output={"coverage_score": ca.coverage_score,
                            "confidence_ceiling": ca.confidence_ceiling,
                            "dimensions_present": ca.dimensions_present,
                            "dimensions_missing": ca.dimensions_missing,
                            "reasons": ca.reasons_confidence_limited},
            retrieved_documents=[d.doc_id for d in ctx.documents], retrieved_facts=[],
            source_documents=[d.doc_id for d in ctx.documents], coverage_score=ca.coverage_score))
    return out


# ---------------------------------------------------------------------------
# 13. evidence_ranking (per-fact ranked evidence + ticker-level tier summary)
# ---------------------------------------------------------------------------

def export_evidence_ranking(con, *, limit=None):
    fact_ids = [r[0] for r in con.execute(
        "SELECT fact_id FROM extracted_facts WHERE evidence_id IS NOT NULL ORDER BY fact_id"
        + (f" LIMIT {limit}" if limit else "")).fetchall()]
    out = []
    for fact_id in fact_ids:
        ranked = evidence_ranking.rank_evidence_for_fact(con, fact_id)
        if not ranked:
            continue
        out.append(_make_example(
            con, task="evidence_ranking", unique_id=make_unique_id("evidence_ranking", fact_id),
            instruction="Rank this fact's evidence by trust tier and explain the ranking.",
            context={"fact_id": fact_id},
            expected_output={"ranked_tiers": [{"tier": r["tier"], "tier_label": r["tier_label"],
                                              "rationale": r["tier_rationale"]} for r in ranked]},
            retrieved_documents=[r["doc_id"] for r in ranked], retrieved_facts=[fact_id],
            source_documents=[r["doc_id"] for r in ranked], fact_id=fact_id))
    return out


# ---------------------------------------------------------------------------
# 14. confidence_estimation (stated confidence vs. whether it survived
# self-critique unscathed -- a real, if rough, calibration proxy)
# ---------------------------------------------------------------------------

def export_confidence_estimation(con, *, limit=None):
    sql = ("SELECT implication_id, fact_id, confidence, status FROM investment_implications "
          "ORDER BY implication_id" + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for implication_id, fact_id, confidence, status in rows:
        n_fail = con.execute(
            "SELECT COUNT(*) FROM self_critique_reviews WHERE implication_id = ? AND finding = 'fail'",
            (implication_id,)).fetchone()[0]
        calibration_label = "justified" if n_fail == 0 else "overconfident"
        out.append(_make_example(
            con, task="confidence_estimation",
            unique_id=make_unique_id("confidence_estimation", implication_id),
            instruction="Was the stated confidence for this claim empirically justified?",
            context={"stated_confidence": confidence, "status": status},
            expected_output={"calibration_label": calibration_label, "n_self_critique_fails": n_fail},
            retrieved_documents=[], retrieved_facts=[fact_id], source_documents=[],
            fact_id=fact_id, implication_id=implication_id))
    return out


# ---------------------------------------------------------------------------
# 15. hallucination_detection (rejected-partition superset -- real grounding
# failures + real quality-rejected examples, always negatives)
# ---------------------------------------------------------------------------

def export_hallucination_detection(con, *, limit=None):
    sql = ("SELECT ef.fact_id, e.evidence_id, e.doc_id, e.quoted_text, ef.description "
          "FROM extracted_facts ef JOIN evidence e ON e.evidence_id = ef.evidence_id "
          "WHERE ef.model_id IS NOT NULL AND ef.grounding_check = 'failed' "
          "ORDER BY ef.fact_id" + (f" LIMIT {limit}" if limit else ""))
    rows = con.execute(sql).fetchall()
    out = []
    for fact_id, evidence_id, doc_id, quoted_text, description in rows:
        out.append(_make_example(
            con, task="hallucination_detection",
            unique_id=make_unique_id("hallucination_detection", evidence_id),
            instruction="Does this claim's supporting quote actually exist verbatim in the source?",
            context={"claim": description},
            expected_output={"verdict": "hallucinated", "reason": "quote not found verbatim in source"},
            retrieved_documents=[doc_id], retrieved_facts=[fact_id], source_documents=[doc_id],
            citations=[{"evidence_id": evidence_id, "doc_id": doc_id, "quoted_text": quoted_text,
                      "grounding_check": "failed"}],
            fact_id=fact_id))
    return out


# ---------------------------------------------------------------------------
# 16. retrieval (ticker+as_of -> which real documents/facts were relevant --
# derived from real extraction outcomes, no invented queries)
# ---------------------------------------------------------------------------

def export_retrieval(con, *, limit=None):
    tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM investment_implications WHERE ticker IS NOT NULL"
        + (f" LIMIT {limit}" if limit else "")).fetchall()]
    out = []
    for ticker in tickers:
        ctx = build_reasoning_context(con, ticker)
        if not ctx.facts:
            continue
        out.append(_make_example(
            con, task="retrieval", unique_id=make_unique_id("retrieval", ticker),
            instruction=f"Which documents and facts are relevant to reasoning about {ticker}?",
            context={"ticker": ticker, "as_of": ctx.as_of},
            expected_output={"relevant_doc_ids": [d.doc_id for d in ctx.documents],
                            "relevant_fact_ids": [f["fact_id"] for f in ctx.facts]},
            retrieved_documents=[d.doc_id for d in ctx.documents],
            retrieved_facts=[f["fact_id"] for f in ctx.facts],
            source_documents=[d.doc_id for d in ctx.documents]))
    return out


# ---------------------------------------------------------------------------
# 17. rag (multi-fact synthesis across an already-assembled ReasoningContext
# -- the harder, later-curriculum skill per spec §2 row #11)
# ---------------------------------------------------------------------------

def export_rag(con, *, limit=None):
    tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM investment_implications WHERE ticker IS NOT NULL"
        + (f" LIMIT {limit}" if limit else "")).fetchall()]
    out = []
    for ticker in tickers:
        ctx = build_reasoning_context(con, ticker)
        if len(ctx.facts) < 1:
            continue
        summary = [{"fact_type": f["fact_type"], "description": f["description"]}
                  for f in ctx.facts]
        out.append(_make_example(
            con, task="rag", unique_id=make_unique_id("rag", ticker),
            instruction=f"Given everything retrieved about {ticker}, synthesize a grounded answer "
                       f"to: what does the evidence say about this company?",
            context={"ticker": ticker, "as_of": ctx.as_of},
            expected_output={"synthesis": summary},
            reasoning_context={"coverage_notes": ctx.coverage_notes,
                              "n_facts": len(ctx.facts), "n_events": len(ctx.events)},
            retrieved_documents=[d.doc_id for d in ctx.documents],
            retrieved_facts=[f["fact_id"] for f in ctx.facts],
            source_documents=[d.doc_id for d in ctx.documents],
            coverage_score=ctx.coverage_assessment.coverage_score if ctx.coverage_assessment else None))
    return out


EXPORTERS = {
    "extraction": export_extraction,
    "corporate_actions": export_corporate_actions,
    "financial_reasoning": export_financial_reasoning,
    "self_critique": export_self_critique,
    "citation_grounding": export_citation_grounding,
    "contradiction_detection": export_contradiction_detection,
    "investment_decision_support": export_investment_decision_support,
    "portfolio_reasoning": export_portfolio_reasoning,
    "entity_recognition": export_entity_recognition,
    "knowledge_graph_completion": export_knowledge_graph_completion,
    "event_understanding": export_event_understanding,
    "coverage_assessment": export_coverage_assessment,
    "evidence_ranking": export_evidence_ranking,
    "confidence_estimation": export_confidence_estimation,
    "hallucination_detection": export_hallucination_detection,
    "retrieval": export_retrieval,
    "rag": export_rag,
}
