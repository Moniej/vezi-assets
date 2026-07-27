"""Step 14 (docs/REASONING_ENGINE_SPECIFICATION.md §12): the mandatory
devil's-advocate gate. A SEPARATE reasoning call from the one that drafted
the implication — never the same completion re-affirming itself.

Every one of the 8 questions gets BOTH the model's own verdict AND an
independent mechanical check; the final finding is the more severe of the
two (a model saying "pass" never overrides a mechanical "concern"/"fail" —
this is the "don't just trust the model" principle from the spec, applied
here exactly as it is in grounding.py for quotes).
"""

from __future__ import annotations

from datetime import date

from . import vocab
from .cache import cached_complete
from .grounding import check_banned_phrase
from .json_utils import parse_json_object
from .llm_providers import LLMProvider
from .prompts import CRITIQUE_PROMPT_VERSION, build_critique_prompt

_SEVERITY = {"pass": 0, "concern": 1, "fail": 2}


def _escalate(model_finding: str, mechanical_finding: str | None) -> str:
    if mechanical_finding is None:
        return model_finding if model_finding in _SEVERITY else "concern"
    a = _SEVERITY.get(model_finding, 1)
    b = _SEVERITY.get(mechanical_finding, 1)
    return mechanical_finding if b >= a else model_finding


def _mechanical_checks(con, implication_id: int, fact_id: int) -> dict[str, tuple[str, str]]:
    """question -> (finding, reason), only for questions with a defined
    mechanical check (spec §12.1) — the two purely-generative questions
    (ignored_alternative_explanation, confidence_improving_information)
    are not here; they're handled via the banned-phrase check / mandatory
    research-task creation instead."""
    checks: dict[str, tuple[str, str]] = {}

    chain = con.execute(
        "SELECT inferred FROM causal_chain_steps WHERE fact_id = ? ORDER BY step_order",
        (fact_id,)).fetchall()
    inferred_n = sum(1 for (i,) in chain if i)
    evidenced_n = len(chain) - inferred_n
    if chain and evidenced_n == 0:
        checks["unevidenced_inference"] = (
            "concern", f"all {len(chain)} causal-chain steps are inferred; none are "
                      f"directly evidenced by a grounded quote")
    if evidenced_n > 0 and inferred_n > 2 * evidenced_n:
        checks["correlation_vs_causation"] = (
            "concern", f"{inferred_n} inferred steps vs {evidenced_n} evidenced — a long "
                      f"inferential leap on thin direct evidence")

    row = con.execute(
        "SELECT magnitude FROM investment_implications WHERE implication_id = ?",
        (implication_id,)).fetchone()
    magnitude = row[0] if row else None
    n_docs = con.execute(
        "SELECT COUNT(DISTINCT e.doc_id) FROM evidence e "
        "JOIN extracted_facts ef ON ef.evidence_id = e.evidence_id WHERE ef.fact_id = ?",
        (fact_id,)).fetchone()[0]
    if n_docs <= 1 and magnitude in ("large", "transformational"):
        checks["single_document_overreaction"] = (
            "concern", f"magnitude={magnitude!r} rests on a single source document "
                      f"(doc_id count={n_docs}) — exactly the overreaction risk named")

    impl_row = con.execute(
        "SELECT ticker, contradicts_implication_id FROM investment_implications "
        "WHERE implication_id = ?", (implication_id,)).fetchone()
    ticker, already_captured = impl_row
    fact_type = con.execute("SELECT fact_type FROM extracted_facts WHERE fact_id = ?",
                            (fact_id,)).fetchone()[0]
    if ticker:
        disagreement = con.execute(
            "SELECT ii.implication_id FROM investment_implications ii "
            "JOIN extracted_facts ef ON ef.fact_id = ii.fact_id "
            "WHERE ii.ticker = ? AND ef.fact_type = ? AND ii.implication_id != ? "
            "AND ii.direction != 'unknown' AND ii.direction != ("
            "  SELECT direction FROM investment_implications WHERE implication_id = ?)",
            (ticker, fact_type, implication_id, implication_id)).fetchone()
        if disagreement and not already_captured:
            checks["contradicts_prior_evidence"] = (
                "fail", f"a disagreeing prior implication (#{disagreement[0]}) exists for "
                       f"the same ticker/fact_type and the draft's own Step 12 did not "
                       f"capture it via contradicts_implication_id")

    real_evidence_n = con.execute(
        "SELECT COUNT(*) FROM evidence e JOIN extracted_facts ef ON ef.evidence_id = e.evidence_id "
        "WHERE ef.fact_id = ? AND ef.grounding_check = 'passed'", (fact_id,)).fetchone()[0]
    real_evidence_n += con.execute(
        "SELECT COUNT(*) FROM causal_chain_steps WHERE fact_id = ? AND evidence_id IS NOT NULL",
        (fact_id,)).fetchone()[0]
    if real_evidence_n < vocab.MIN_EVIDENCE_COUNT_FLOOR:
        checks["insufficient_information"] = (
            "concern", f"only {real_evidence_n} grounded evidence row(s) support this fact "
                      f"(floor={vocab.MIN_EVIDENCE_COUNT_FLOOR})")

    # market_noise_check: only meaningful for source_type='news' documents
    # (documents.news_classification); this pilot is all 'filing' documents,
    # so this mechanical check is a documented no-op here, not a gap —
    # flagged explicitly in the Phase C completion report.
    return checks


def critique_implication(con, provider: LLMProvider, implication_id: int,
                         force: bool = False, cache_dir=None) -> dict:
    """Runs the full Step 14 gate for one implication and updates its
    status per §12.2. Returns a small summary dict for the caller/report."""
    impl = con.execute(
        "SELECT fact_id, ticker, direction, magnitude, duration_bucket, confidence, "
        "confidence_rationale FROM investment_implications WHERE implication_id = ?",
        (implication_id,)).fetchone()
    if impl is None:
        raise ValueError(f"implication_id {implication_id} not found")
    fact_id, ticker, direction, magnitude, duration_bucket, confidence, rationale = impl

    fact = con.execute(
        "SELECT doc_id, fact_type, description FROM extracted_facts WHERE fact_id = ?",
        (fact_id,)).fetchone()
    doc_id, fact_type, description = fact
    doc_row = con.execute("SELECT text_path FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    from pathlib import Path
    pkg_root = Path(__file__).resolve().parents[3]
    doc_text = (pkg_root / doc_row[0]).read_text(encoding="utf-8")

    draft_summary = {
        "fact_type": fact_type, "description": description, "ticker": ticker,
        "direction": direction, "magnitude": magnitude, "duration_bucket": duration_bucket,
        "confidence": confidence, "confidence_rationale": rationale,
    }
    system_prompt, user_prompt = build_critique_prompt(draft_summary, doc_text)
    # See extract.py's identical comment: generous max_tokens because some
    # providers spend part of the budget on internal reasoning before any
    # visible output; 8 critique questions with real explanations is a
    # smaller (but not small) response than the draft's.
    resp = cached_complete(con, provider, doc_id=doc_id, purpose="self_critique",
                          prompt_version=CRITIQUE_PROMPT_VERSION,
                          system_prompt=system_prompt, user_prompt=user_prompt,
                          max_tokens=8192, force=force, cache_dir=cache_dir)

    parsed = parse_json_object(resp.response_text)
    mechanical = _mechanical_checks(con, implication_id, fact_id)
    as_of = date.today().isoformat()

    model_by_question = {}
    if parsed:
        for c in parsed.get("critiques", []):
            model_by_question[c.get("question")] = c

    findings = {}
    for q in vocab.SELF_CRITIQUE_QUESTIONS:
        model_c = model_by_question.get(q, {})
        model_finding = model_c.get("finding", "concern")
        explanation = model_c.get("explanation") or "(model provided no explanation)"

        if q == "ignored_alternative_explanation":
            banned = check_banned_phrase(explanation)
            if not banned.passed:
                model_finding = "fail"
                explanation += f" [banned-phrase check failed: {banned.reason}]"

        mech = mechanical.get(q)
        final_finding = _escalate(model_finding, mech[0] if mech else None)
        if mech and mech[0] != model_finding:
            explanation += f" [mechanical check: {mech[1]}]"

        resulting_action = "none"
        if q == "confidence_improving_information":
            resulting_action = "research_task_created"
            task_desc = model_c.get("research_task") or explanation
            con.execute(
                "INSERT INTO research_task_candidates (implication_id, description, "
                "status, created_at) VALUES (?,?,?,?)",
                (implication_id, task_desc, "open", as_of))
        elif final_finding == "fail":
            resulting_action = "flagged_for_human_review"
        elif final_finding == "concern":
            resulting_action = "confidence_lowered"

        con.execute(
            "INSERT INTO self_critique_reviews (implication_id, question, finding, "
            "explanation, resulting_action, model_id, prompt_version, reviewed_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (implication_id, q, final_finding, explanation, resulting_action,
             resp.model_id, CRITIQUE_PROMPT_VERSION, as_of))
        findings[q] = final_finding

    n_fail = sum(1 for f in findings.values() if f == "fail")
    n_concern = sum(1 for f in findings.values() if f == "concern")

    if n_fail > 0:
        new_status = "blocked_by_self_critique"
        con.execute("UPDATE investment_implications SET status = ? WHERE implication_id = ?",
                   (new_status, implication_id))
    else:
        new_status = "unvalidated_ai_interpretation"
        new_confidence = confidence
        appended_rationale = rationale
        if n_concern > 0:
            new_confidence = max(0.0, confidence - n_concern * vocab.CONFIDENCE_DISCOUNT_PER_CONCERN)
            concern_notes = "; ".join(
                f"{q}: {model_by_question.get(q, {}).get('explanation', '')}"
                for q in vocab.SELF_CRITIQUE_QUESTIONS if findings[q] == "concern")
            appended_rationale = f"{rationale} [Step 14 concerns: {concern_notes}]"
        con.execute(
            "UPDATE investment_implications SET status = ?, confidence = ?, "
            "confidence_rationale = ? WHERE implication_id = ?",
            (new_status, new_confidence, appended_rationale, implication_id))

    con.commit()
    return {"implication_id": implication_id, "status": new_status,
           "findings": findings, "n_fail": n_fail, "n_concern": n_concern}
