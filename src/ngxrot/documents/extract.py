"""Steps 1-13 (docs/REASONING_ENGINE_SPECIFICATION.md §1): builds one draft
`investment_implications` row (status='draft_pending_self_critique') per
material fact found in a document, plus its extracted_facts/evidence/
causal_chain_steps/impact_assessments/effect_chains/research_task_candidates.
Step 14 (self-critique) is a SEPARATE module (self_critique.py) — this
module never advances a row past the draft status.

Every enum-shaped field from the model is validated against vocab.py
before it touches the database: an invalid value is downgraded to the
safest default (never crashes the run, never silently accepted as-is) and
the substitution is recorded in confidence_rationale so it's visible, not
hidden.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import vocab
from .cache import cached_complete, document_text_hash
from .grounding import check_banned_phrase, check_grounding
from .json_utils import parse_json_object
from .llm_providers import LLMProvider
from .prompts import DRAFT_PROMPT_VERSION, build_draft_prompt
from .entities import record_relationship, resolve_or_create_entity

PKG_ROOT = Path(__file__).resolve().parents[3]
UNREVIEWED_LLM_CONFIDENCE_FLOOR = 0.3  # architecture doc §6: unreviewed LLM
                                      # output capped low until human review


def _fact_taxonomy_leaves() -> set[str]:
    raw = tomllib.loads((PKG_ROOT / "configs/fact_taxonomy.toml").read_text(encoding="utf-8"))
    return {t for spec in raw.values() for t in spec.get("types", [])}


@dataclass
class ExtractionResult:
    doc_id: int
    parse_ok: bool
    fact_ids: list[int] = field(default_factory=list)
    implication_ids: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    model_id: str | None = None


def _safe_enum(value, allowed: set[str], default: str, warnings: list[str], field_name: str):
    if value in allowed:
        return value, None
    note = f"{field_name}: model returned {value!r}, not in {sorted(allowed)} — downgraded to {default!r}"
    warnings.append(note)
    return default, note


def extract_document(con, provider: LLMProvider, doc_id: int,
                     force: bool = False, cache_dir=None) -> ExtractionResult:
    row = con.execute(
        "SELECT ticker, raw_symbol, doc_type, filing_date, text_path, "
        "source_confidence FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if row is None:
        raise ValueError(f"doc_id {doc_id} not found in documents")
    ticker, raw_symbol, doc_type, filing_date, text_path, source_confidence = row

    # MC-001 (2026-08-04, docs/MULTI_CURRENCY_FINANCIAL_ARCHITECTURE_
    # REVIEW_2026-08-04.md): reporting currency for facts drawn from this
    # document. securities.reporting_currency is authoritative when set
    # (populated only where directly confirmed, e.g. AIRTELAFRI='USD');
    # 'NGN' is the sole fallback because every fact ever extracted before
    # this column existed was independently confirmed NGN-denominated at
    # backfill time -- this default changes no existing behavior, it only
    # makes an assumption that was always implicit into an explicit,
    # overridable one.
    fact_currency = "NGN"
    if ticker:
        rc = con.execute(
            "SELECT reporting_currency FROM securities WHERE ticker=?",
            (ticker,)).fetchone()
        if rc and rc[0]:
            fact_currency = rc[0]

    if not text_path:
        raise ValueError(f"doc_id {doc_id} has no extracted text (Phase A "
                         f"extraction_method is not 'native') — cannot run "
                         f"the reasoning engine on a document with no readable text")
    doc_text = (PKG_ROOT / text_path).read_text(encoding="utf-8")
    display_ticker = ticker or raw_symbol

    system_prompt, user_prompt = build_draft_prompt(doc_text, display_ticker, doc_type, filing_date)
    # max_tokens generous (default here, not cache.py's, since this is the
    # single largest response shape in the pipeline): the draft schema asks
    # for 13 impact categories + a causal chain + the full implication
    # object + effect chains + research tasks, and some providers (observed:
    # Gemini 3.x) spend part of the budget on internal "thinking" tokens
    # before any visible output — confirmed empirically that a small budget
    # can be entirely consumed by thinking with zero output text.
    resp = cached_complete(con, provider, doc_id=doc_id, purpose="draft_reasoning",
                          prompt_version=DRAFT_PROMPT_VERSION,
                          system_prompt=system_prompt, user_prompt=user_prompt,
                          max_tokens=16384, force=force, cache_dir=cache_dir,
                          document_hash=document_text_hash(doc_text))

    result = ExtractionResult(doc_id=doc_id, parse_ok=True, model_id=resp.model_id)
    parsed = parse_json_object(resp.response_text)
    if parsed is None:
        result.parse_ok = False
        result.warnings.append("draft LLM response did not parse as JSON — "
                               "no facts recorded for this document (never "
                               "guessed from unparseable output)")
        return result

    taxonomy_leaves = _fact_taxonomy_leaves()
    as_of = date.today().isoformat()

    for fact in parsed.get("facts", []):
        fact_type = fact.get("fact_type")
        if fact_type not in taxonomy_leaves:
            result.warnings.append(f"fact_type {fact_type!r} not in "
                                   f"configs/fact_taxonomy.toml — routed to 'other'")
            fact_type = "other"

        quoted = fact.get("quoted_evidence")
        grounding = check_grounding(quoted, doc_text) if quoted else None
        grounding_status = "passed" if (grounding and grounding.passed) else \
            ("failed" if quoted else "not_run")
        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)",
            (doc_id, quoted or "[model provided no supporting quote]",
             source_confidence)).lastrowid

        extraction_confidence = UNREVIEWED_LLM_CONFIDENCE_FLOOR
        if grounding_status == "failed":
            extraction_confidence = 0.0  # ungrounded quote — architecture doc §4.4:
                                         # capped confidence, human review required
            result.warnings.append(f"fact_type={fact_type}: quoted_evidence not "
                                   f"found verbatim in source text — grounding FAILED, "
                                   f"extraction_confidence forced to 0.0")

        fact_id = con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, qualification_date, payment_date, agm_date, "
            "closure_date, evidence_id, extraction_confidence, model_id, "
            "prompt_version, grounding_check, extracted_at, currency) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, fact_type, fact.get("description", ""), fact.get("numeric_value"),
             fact.get("qualification_date"), fact.get("payment_date"),
             fact.get("agm_date"), fact.get("closure_date"), evidence_id,
             extraction_confidence, resp.model_id, DRAFT_PROMPT_VERSION,
             grounding_status, as_of, fact_currency)).lastrowid
        result.fact_ids.append(fact_id)

        for i, step in enumerate(fact.get("causal_chain", [])):
            step_evidence_id = None
            step_quote = step.get("quoted_evidence")
            if step_quote:
                step_grounding = check_grounding(step_quote, doc_text)
                if step_grounding.passed:
                    step_evidence_id = con.execute(
                        "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
                        "VALUES (?,?,?)", (doc_id, step_quote, source_confidence)).lastrowid
                else:
                    result.warnings.append(f"fact {fact_id} chain step {i}: "
                                           f"quoted_evidence not grounded, dropped")
            con.execute(
                "INSERT INTO causal_chain_steps (fact_id, step_order, statement, "
                "inferred, evidence_id) VALUES (?,?,?,?,?)",
                (fact_id, i, step.get("statement", ""), int(bool(step.get("inferred", True))),
                 step_evidence_id))

        impacts = fact.get("impact_assessments", {}) or {}
        for category in vocab.IMPACT_CATEGORIES:
            entry = impacts.get(category)
            if entry is None:
                result.warnings.append(f"fact {fact_id}: model omitted impact "
                                       f"category {category!r} — recorded as unknown")
                entry = {"direction": "unknown", "explanation": "not addressed by the model"}
            direction, _ = _safe_enum(entry.get("direction"), vocab.IMPACT_DIRECTIONS,
                                     "unknown", result.warnings, f"impact[{category}].direction")
            explanation = entry.get("explanation") or ""
            banned = check_banned_phrase(explanation)
            if not banned.passed:
                result.warnings.append(f"fact {fact_id} impact[{category}]: "
                                       f"explanation failed banned-phrase check "
                                       f"({banned.reason}) — kept but flagged")
            con.execute(
                "INSERT OR IGNORE INTO impact_assessments (fact_id, category, "
                "direction, explanation, evidence_id) VALUES (?,?,?,?,?)",
                (fact_id, category, direction, explanation or "(no explanation provided)",
                 evidence_id))

        impl = fact.get("implication", {}) or {}
        direction, _ = _safe_enum(impl.get("direction"), vocab.DIRECTIONS, "unknown",
                                  result.warnings, "implication.direction")
        duration_bucket, _ = _safe_enum(impl.get("duration_bucket"), vocab.DURATION_BUCKETS,
                                        "medium", result.warnings, "implication.duration_bucket")
        magnitude, _ = _safe_enum(impl.get("magnitude"), vocab.MAGNITUDES, "small",
                                  result.warnings, "implication.magnitude")
        action, _ = _safe_enum(impl.get("action_recommendation"), vocab.ACTION_RECOMMENDATIONS,
                               "watchlist", result.warnings, "implication.action_recommendation")
        market_reaction, _ = _safe_enum(impl.get("market_reaction_assessment"),
                                        vocab.MARKET_REACTIONS, "unclear", result.warnings,
                                        "implication.market_reaction_assessment")
        iv_dir, _ = _safe_enum(impl.get("intrinsic_value_direction"), vocab.DIRECTIONS_2WAY,
                               "unclear", result.warnings, "implication.intrinsic_value_direction")
        earn_dir, _ = _safe_enum(impl.get("expected_earnings_direction"), vocab.DIRECTIONS_2WAY,
                                 "unclear", result.warnings, "implication.expected_earnings_direction")
        tm_dir, _ = _safe_enum(impl.get("target_multiple_direction"), vocab.DIRECTIONS_2WAY_NA,
                               "not_assessed", result.warnings, "implication.target_multiple_direction")
        risk_dir, _ = _safe_enum(impl.get("risk_profile_direction"), vocab.DIRECTIONS_2WAY_NA,
                                 "not_assessed", result.warnings, "implication.risk_profile_direction")

        confidence = impl.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            result.warnings.append(f"implication.confidence {confidence!r} not numeric — set to 0.0")
            confidence = 0.0
        # never let a raw model confidence exceed the unreviewed floor —
        # same rule as extraction_confidence above, applied here too
        confidence = min(confidence, UNREVIEWED_LLM_CONFIDENCE_FLOOR)

        confidence_rationale = impl.get("confidence_rationale") or "(no rationale provided by model)"

        implication_id = con.execute(
            "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, "
            "magnitude, confidence, confidence_rationale, direction, assumptions, "
            "bull_case_delta, bear_case_delta, base_case_delta, "
            "intrinsic_value_direction, intrinsic_value_reasoning, "
            "expected_earnings_direction, target_multiple_direction, "
            "risk_profile_direction, portfolio_sizing_note, action_recommendation, "
            "market_reaction_assessment, market_reaction_reasoning, status, "
            "model_id, prompt_version, generated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fact_id, display_ticker, duration_bucket, magnitude, confidence,
             confidence_rationale, direction, impl.get("assumptions"),
             impl.get("bull_case_delta"), impl.get("bear_case_delta"),
             impl.get("base_case_delta"), iv_dir, impl.get("intrinsic_value_reasoning"),
             earn_dir, tm_dir, risk_dir, impl.get("portfolio_sizing_note"), action,
             market_reaction, impl.get("market_reaction_reasoning"),
             "draft_pending_self_critique", resp.model_id, DRAFT_PROMPT_VERSION,
             as_of)).lastrowid
        result.implication_ids.append(implication_id)

        subject_entity_id = resolve_or_create_entity(
            con, display_ticker, "company", doc_id, ticker=ticker) if display_ticker else None

        for order_n, key in ((1, "first_order_effects"), (2, "second_order_effects"),
                             (3, "third_order_effects")):
            for eff in impl.get(key, []) or []:
                eff_quote = eff.get("quoted_evidence")
                eff_evidence_id = None
                if eff_quote and check_grounding(eff_quote, doc_text).passed:
                    eff_evidence_id = con.execute(
                        "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
                        "VALUES (?,?,?)", (doc_id, eff_quote, source_confidence)).lastrowid
                affected_entity_id = None
                name = eff.get("affected_entity")
                if name:
                    affected_entity_id = resolve_or_create_entity(
                        con, name, "company" if name == display_ticker else
                        "competitor_mention", doc_id)
                con.execute(
                    "INSERT INTO effect_chains (implication_id, order_n, description, "
                    "affected_entity_id, evidence_id) VALUES (?,?,?,?,?)",
                    (implication_id, order_n, eff.get("description", ""),
                     affected_entity_id, eff_evidence_id))
                # Phase E (2026-07-26): persist a durable graph edge too, not
                # just a per-implication mention — but ONLY when there's
                # grounded evidence behind it (eff_evidence_id set) and it
                # isn't a self-relationship. relation_type is deliberately
                # the literal "which effect order" fact, never an invented
                # taxonomy label (competitor_of/supplier_to) the model was
                # never asked to classify — see entities.py's docstring.
                if affected_entity_id is not None and eff_evidence_id is not None \
                        and subject_entity_id is not None:
                    record_relationship(
                        con, subject_entity_id, f"affects_order_{order_n}",
                        affected_entity_id, eff_evidence_id,
                        confidence=UNREVIEWED_LLM_CONFIDENCE_FLOOR,
                        valid_from=filing_date)

        for task in impl.get("research_tasks", []) or []:
            con.execute(
                "INSERT INTO research_task_candidates (implication_id, description, "
                "status, created_at) VALUES (?,?,?,?)",
                (implication_id, task.get("description", ""), "open", as_of))

        _cross_reference(con, implication_id, display_ticker, fact_type, direction, confidence)

    con.commit()
    return result


def _cross_reference(con, implication_id: int, ticker: str | None, fact_type: str,
                     direction: str, confidence: float) -> None:
    """Steps 11-12: search prior implications for the same ticker/fact_type
    (append-only — never touches the prior row, only sets a pointer on the
    NEW one). Agreement -> corroborates_implication_id; disagreement ->
    contradicts_implication_id + a consistency_note stating which is more
    reliable, per confidence (never by deletion, matching event_pipeline
    .py's existing conflict-preservation rule)."""
    if not ticker:
        return
    prior = con.execute(
        "SELECT ii.implication_id, ii.direction, ii.confidence, ii.generated_at "
        "FROM investment_implications ii JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
        "WHERE ii.ticker = ? AND ef.fact_type = ? AND ii.implication_id != ? "
        "ORDER BY ii.generated_at DESC LIMIT 5",
        (ticker, fact_type, implication_id)).fetchall()
    for prior_id, prior_direction, prior_confidence, prior_at in prior:
        if prior_direction == direction:
            con.execute("UPDATE investment_implications SET corroborates_implication_id = ? "
                       "WHERE implication_id = ?", (prior_id, implication_id))
            return
        if prior_direction not in ("unknown",) and direction not in ("unknown",):
            more_reliable = "this new implication" if confidence >= prior_confidence else \
                f"the prior implication #{prior_id}"
            note = (f"Disagrees with prior implication #{prior_id} ({prior_at}): "
                    f"{prior_direction!r} vs this implication's {direction!r} for the "
                    f"same ticker/fact_type. {more_reliable} has higher stated "
                    f"confidence ({max(confidence, prior_confidence):.2f} vs "
                    f"{min(confidence, prior_confidence):.2f}) — both rows preserved, "
                    f"neither overwritten.")
            con.execute("UPDATE investment_implications SET contradicts_implication_id = ?, "
                       "consistency_note = ? WHERE implication_id = ?",
                       (prior_id, note, implication_id))
            return
