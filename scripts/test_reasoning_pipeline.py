"""Engineering-correctness tests for the Phase C reasoning pipeline.
No pytest in this project (checked before adding one) — matches the
existing validate_*.py assertion-script convention instead.

Uses ONLY MockProvider (canned, fixed responses) against a throwaway temp
database (tempfile.mkdtemp() + db.init_db(tmp), same pattern as
rehearse_xs_size.py) — never the real ngx.sqlite, never a real API call.
These tests check the PIPELINE'S ENGINEERING CORRECTNESS (grounding logic,
enum validation, schema completeness, gate mechanics, caching) — they say
nothing about whether a REAL model's reasoning is any good; that question
is what scripts/run_phase_c_pilot.py + scripts/validate_phase_c_extraction.py
answer, against real API output, once an LLM vendor is configured.

  python -u scripts/test_reasoning_pipeline.py
"""

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.grounding import check_banned_phrase, check_grounding  # noqa: E402
from ngxrot.documents.json_utils import parse_json_object  # noqa: E402
from ngxrot.documents.llm_providers import (  # noqa: E402
    LLMConfig, LLMResponse, MockProvider, QuotaExceededError,
    build_default_provider, load_llm_config)
from ngxrot.documents.reasoning import financial_reasoning, resumable_financial_reasoning  # noqa: E402
from ngxrot.documents.self_critique import critique_implication  # noqa: E402
from ngxrot.documents import pilot_summary  # noqa: E402
from ngxrot.documents import pipeline_status as pstatus  # noqa: E402
from ngxrot.documents import vocab  # noqa: E402
from ngxrot.documents.cache import cached_complete, document_text_hash  # noqa: E402
from ngxrot.documents import retrieval  # noqa: E402
from ngxrot.documents.context import build_reasoning_context, historical_event_reaction  # noqa: E402
from ngxrot.documents.entities import record_relationship, resolve_or_create_entity  # noqa: E402
from ngxrot.documents import reasoning_engine  # noqa: E402
from ngxrot.documents import industry_reasoning  # noqa: E402
from ngxrot.documents.coverage_assessment import assess_coverage  # noqa: E402
from ngxrot.documents.evidence_ranking import (  # noqa: E402
    assess_implication_conflict, assign_trust_tier, evidence_ranking_summary,
    rank_evidence_for_fact)

FAILURES = []
TEST_CACHE_DIR = Path(tempfile.mkdtemp())  # isolated from the real
                                           # data/staging/llm_cache/ —
                                           # see cache.py's cache_dir param


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


DOC_TEXT = (
    "NOTICE OF DIVIDEND. The Board of Directors of TESTCO PLC is pleased to "
    "announce a final dividend of N1.90 per share for the financial year "
    "ended 31 December 2025. The register of members will close on "
    "10 April 2026 for qualification purposes, with payment expected on "
    "30 April 2026. Management noted continued growth in the retail "
    "banking segment."
)

ALL_13_IMPACTS = {c: {"direction": "unknown", "explanation": "not addressed by this filing at all really"}
                 for c in vocab.IMPACT_CATEGORIES}
ALL_13_IMPACTS["revenue"] = {"direction": "positive",
                             "explanation": "Dividend increase signals management confidence in "
                                           "sustained free cash flow generation going forward"}

GOOD_DRAFT_RESPONSE = json.dumps({
    "facts": [{
        "fact_type": "dividend",
        "description": "TESTCO declared a final dividend of N1.90/share",
        "quoted_evidence": "a final dividend of N1.90 per share for the financial year "
                           "ended 31 December 2025",
        "numeric_value": 1.90,
        "qualification_date": "2026-04-10",
        "payment_date": "2026-04-30",
        "agm_date": None,
        "closure_date": None,
        "causal_chain": [
            {"statement": "TESTCO declared a N1.90/share final dividend", "inferred": False,
             "quoted_evidence": "a final dividend of N1.90 per share for the financial year "
                                "ended 31 December 2025"},
            {"statement": "A maintained/raised dividend signals management confidence in "
                         "sustained cash generation", "inferred": True, "quoted_evidence": None},
        ],
        "impact_assessments": ALL_13_IMPACTS,
        "implication": {
            "ticker": "TESTCO", "direction": "bullish", "duration_bucket": "medium",
            "magnitude": "small", "confidence": 0.6,
            "confidence_rationale": "Single dividend notice, no forward guidance beyond the "
                                    "payment itself, so magnitude and duration are capped",
            "assumptions": "Assumes payment proceeds as scheduled with no intervening "
                          "capital-raise announcement",
            "bull_case_delta": "Modest support for the income thesis",
            "bear_case_delta": None, "base_case_delta": "In line with prior payout pattern",
            "intrinsic_value_direction": "increase",
            "intrinsic_value_reasoning": "A sustained dividend implies free cash flow adequate "
                                        "to cover the payout without impairing the balance sheet",
            "expected_earnings_direction": "unclear", "target_multiple_direction": "not_assessed",
            "risk_profile_direction": "not_assessed",
            "portfolio_sizing_note": "No sizing implication from a single dividend notice",
            "action_recommendation": "no_action",
            "market_reaction_assessment": "unclear",
            "market_reaction_reasoning": "No price data considered in this pass",
            "first_order_effects": [{"description": "Shareholders receive cash distribution",
                                     "affected_entity": "TESTCO", "quoted_evidence": None}],
            "second_order_effects": [], "third_order_effects": [],
            "research_tasks": [{"description": "Confirm prior-year dividend per share to "
                                               "establish trend direction"}],
        },
    }],
})

CRITIQUE_RESPONSE_ALL_PASS = json.dumps({"critiques": [
    {"question": "unevidenced_inference", "finding": "pass",
     "explanation": "The core fact is a direct quote; only the forward-looking economic "
                    "interpretation is inferred, which is disclosed as such"},
    {"question": "correlation_vs_causation", "finding": "pass",
     "explanation": "The chain has one evidenced and one inferred step, not a long "
                    "speculative leap from thin evidence"},
    {"question": "ignored_alternative_explanation", "finding": "concern",
     "explanation": "An alternative explanation is that this dividend is flat or a routine "
                    "payout unrelated to any confidence signal, which the draft did not "
                    "seriously entertain before concluding bullish"},
    {"question": "single_document_overreaction", "finding": "pass",
     "explanation": "Magnitude was assessed as small, not a transformational call resting "
                    "on one filing"},
    {"question": "contradicts_prior_evidence", "finding": "pass",
     "explanation": "No prior implication exists yet for this ticker/fact_type combination"},
    {"question": "insufficient_information", "finding": "pass",
     "explanation": "The filing directly states the dividend amount and both key dates"},
    {"question": "confidence_improving_information", "finding": "concern",
     "explanation": "Prior-year dividend history would let the model assess trend, not just "
                    "level", "research_task": "Obtain TESTCO's prior 3 years of dividend history"},
    {"question": "market_noise_check", "finding": "pass",
     "explanation": "A dividend declaration is a material, non-routine disclosure, not noise"},
]})


def make_test_db(doc_text: str = DOC_TEXT):
    tmp = Path(tempfile.mkdtemp()) / "test_reasoning.sqlite"
    con = db.init_db(tmp, seed=False)
    text_dir = Path(tempfile.mkdtemp())
    text_path = text_dir / "1.txt"
    text_path.write_text(doc_text, encoding="utf-8")
    con.execute("INSERT INTO securities (ticker, name, board) VALUES "
               "('TESTCO', 'Test Company Plc', 'main')")
    cur = con.execute(
        "INSERT INTO sources (name, kind, reliability, base_confidence) "
        "VALUES ('test_source','company_filing','primary',0.85)")
    source_id = cur.lastrowid
    con.execute(
        "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, source_type, "
        "filing_date, retrieved_date, local_path, text_path, extraction_method, "
        "char_count, source_confidence, source_id, as_of_date) VALUES "
        "(1,'TESTCO','TESTCO','dividend','filing','2026-04-01','2026-04-01',"
        "'x',?,'native',300,0.85,?,?)",
        (str(text_path), source_id, date.today().isoformat()))
    con.commit()
    return con


def test_grounding():
    ok = check_grounding("a final dividend of N1.90 per share", DOC_TEXT)
    check("grounding: exact substring passes", ok.passed)
    bad = check_grounding("a dividend of N99.00 per share", DOC_TEXT)
    check("grounding: fabricated quote fails", not bad.passed)
    empty = check_grounding("", DOC_TEXT)
    check("grounding: empty quote fails", not empty.passed)


def test_banned_phrase():
    bad = check_banned_phrase("This is bullish.")
    check("banned-phrase: bare verdict fails", not bad.passed)
    good = check_banned_phrase("Dividend growth signals management confidence in future cash flow")
    check("banned-phrase: real explanation passes", good.passed)


def test_json_parsing():
    check("json: plain object", parse_json_object('{"a": 1}') == {"a": 1})
    check("json: fenced", parse_json_object('```json\n{"a": 1}\n```') == {"a": 1})
    check("json: embedded in prose", parse_json_object('here is the result: {"a": 1} thanks') == {"a": 1})
    check("json: garbage returns None", parse_json_object("not json at all") is None)


def test_provider_config_and_factory():
    """New in the Gemini provider swap: configs/llm_provider.toml is the
    single source of truth for provider+model, and build_default_provider()
    is the only place that maps it to a concrete class. MockProvider is
    intentionally NOT in the registry (see llm_providers.py comment) — it
    always needs canned responses supplied directly by a test, so these
    checks exercise the real GeminiProvider path (construction only; no
    API call) plus the unknown-provider error path."""
    cfg = load_llm_config()
    check("config: real configs/llm_provider.toml loads", cfg.provider == "gemini")
    check("config: model_id present and non-empty", bool(cfg.model_id))

    import os
    had_key = os.environ.pop("GEMINI_API_KEY", None)
    had_google_key = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        build_default_provider(config=cfg)
        check("factory: GeminiProvider without credentials raises", False)
    except RuntimeError as e:
        check("factory: GeminiProvider without credentials raises clearly",
             "GEMINI_API_KEY" in str(e))
    finally:
        if had_key is not None:
            os.environ["GEMINI_API_KEY"] = had_key
        if had_google_key is not None:
            os.environ["GOOGLE_API_KEY"] = had_google_key

    overridden_cfg = LLMConfig(provider="gemini", model_id="gemini-3.6-flash",
                              api_key_env_var="GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "test-key-not-real"
    try:
        provider = build_default_provider(model_id="gemini-test-override", config=overridden_cfg)
        check("factory: model_id override applied without touching config file",
             provider.info.model_id == "gemini-test-override")
        check("factory: registry dispatches 'gemini' to GeminiProvider",
             type(provider).__name__ == "GeminiProvider")
    finally:
        del os.environ["GEMINI_API_KEY"]

    try:
        build_default_provider(config=LLMConfig(provider="nonexistent_vendor",
                                                model_id="x", api_key_env_var="X"))
        check("factory: unknown provider name raises", False)
    except ValueError:
        check("factory: unknown provider name raises", True)


def test_full_pipeline_all_pass():
    con = make_test_db()
    provider = MockProvider({
        "Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS,
    }, default=GOOD_DRAFT_RESPONSE)
    result = financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)

    check("pipeline: draft parsed OK", result.extraction.parse_ok)
    check("pipeline: one fact created", len(result.extraction.fact_ids) == 1)
    check("pipeline: one implication created", len(result.extraction.implication_ids) == 1)

    import pandas as pd
    facts = pd.read_sql("SELECT * FROM extracted_facts", con)
    check("pipeline: fact grounding passed (real quote)", facts.iloc[0].grounding_check == "passed")
    check("pipeline: fact extraction_confidence at unreviewed floor",
         abs(facts.iloc[0].extraction_confidence - 0.3) < 1e-9)

    impacts = pd.read_sql("SELECT * FROM impact_assessments", con)
    check("pipeline: all 13 impact categories present", len(impacts) == 13,
         f"got {len(impacts)}")
    check("pipeline: revenue category has explanation text",
         impacts[impacts.category == "revenue"].iloc[0].explanation != "")

    chain = pd.read_sql("SELECT * FROM causal_chain_steps ORDER BY step_order", con)
    check("pipeline: causal chain has 2 steps", len(chain) == 2)
    check("pipeline: step 0 evidenced", chain.iloc[0].inferred == 0)
    check("pipeline: step 1 inferred", chain.iloc[1].inferred == 1)

    impl = pd.read_sql("SELECT * FROM investment_implications", con).iloc[0]
    check("pipeline: implication confidence capped at unreviewed floor",
         impl.confidence <= 0.3 + 1e-9)
    check("pipeline: self-critique gate ran (status advanced past draft)",
         impl.status == "unvalidated_ai_interpretation")
    check("pipeline: concern discount applied (2 concerns -> confidence reduced)",
         impl.confidence < 0.3 - 1e-9)

    critiques = pd.read_sql("SELECT * FROM self_critique_reviews", con)
    check("pipeline: all 8 critique questions recorded", len(critiques) == 8,
         f"got {len(critiques)}")
    check("pipeline: 2 concerns recorded (model-declared)",
         (critiques.finding == "concern").sum() == 2)

    tasks = pd.read_sql("SELECT * FROM research_task_candidates", con)
    check("pipeline: research tasks created (draft + mandatory critique question)",
         len(tasks) == 2, f"got {len(tasks)}")

    calls = pd.read_sql("SELECT * FROM llm_calls", con)
    check("pipeline: 2 llm_calls logged (draft + critique)", len(calls) == 2)
    check("pipeline: no calls served from cache on first run",
         (calls.served_from_cache == 0).all())

    # Rerun: must be idempotent-in-spirit for caching (same prompt -> cache
    # hit) even though extract_document itself creates NEW rows each call
    # (it is not idempotent by design — re-running re-extracts; caching is
    # about not re-billing the API, not about skipping re-insertion).
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    calls2 = pd.read_sql("SELECT * FROM llm_calls WHERE served_from_cache = 1", con)
    check("caching: second run's calls served from cache", len(calls2) == 2,
         f"got {len(calls2)}")


def test_self_critique_fail_blocks_status():
    con = make_test_db()
    fail_critique = json.dumps({"critiques": [
        {"question": q, "finding": "pass", "explanation": "fine, nothing to add here at all"}
        for q in vocab.SELF_CRITIQUE_QUESTIONS if q != "contradicts_prior_evidence"
    ] + [{"question": "contradicts_prior_evidence", "finding": "pass",
         "explanation": "looks consistent with everything else"}]})
    provider = MockProvider({"Draft conclusion to critique": fail_critique},
                           default=GOOD_DRAFT_RESPONSE)
    result = financial_reasoning(con, provider, doc_id=1, force=True, cache_dir=TEST_CACHE_DIR)
    # Force a mechanical single_document_overreaction FAIL by manually
    # bumping magnitude to transformational before critique (simulates the
    # mechanical check firing even when the model says everything's fine).
    con.execute("UPDATE investment_implications SET magnitude = 'transformational' "
               "WHERE implication_id = ?", (result.extraction.implication_ids[0],))
    con.commit()
    from ngxrot.documents.self_critique import critique_implication
    con.execute("DELETE FROM self_critique_reviews")
    con.commit()
    critique_implication(con, provider, result.extraction.implication_ids[0], force=True,
                         cache_dir=TEST_CACHE_DIR)
    import pandas as pd
    impl = pd.read_sql("SELECT * FROM investment_implications", con).iloc[0]
    check("gate: mechanical concern overrides model 'pass' on magnitude escalation",
         impl.status in ("unvalidated_ai_interpretation", "blocked_by_self_critique"))
    reviews = pd.read_sql("SELECT * FROM self_critique_reviews WHERE "
                         "question='single_document_overreaction'", con)
    check("gate: single_document_overreaction escalated to concern despite model pass",
         reviews.iloc[0].finding == "concern")


def test_ungrounded_quote_forced_to_zero_confidence():
    con = make_test_db()
    bad_response = GOOD_DRAFT_RESPONSE.replace(
        "a final dividend of N1.90 per share for the financial year ended 31 December 2025",
        "a completely fabricated dividend figure that does not appear anywhere in the filing")
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=bad_response)
    # force=True: bypasses the prompt cache. Necessary here because this
    # test reuses the same doc text/metadata as test_full_pipeline_all_pass,
    # so the cache key is identical — without force, this would silently
    # replay the OTHER test's cached (grounded) response instead of calling
    # the mock provider with this test's fabricated one. Real pilot runs
    # don't hit this because each real document has unique text.
    result = financial_reasoning(con, provider, doc_id=1, force=True, cache_dir=TEST_CACHE_DIR)
    import pandas as pd
    facts = pd.read_sql("SELECT * FROM extracted_facts", con)
    check("grounding gate: fabricated quote -> grounding_check='failed'",
         facts.iloc[0].grounding_check == "failed")
    check("grounding gate: fabricated quote -> extraction_confidence forced to 0.0",
         facts.iloc[0].extraction_confidence == 0.0)
    check("grounding gate: warning recorded", any("grounding FAILED" in w
         for w in result.extraction.warnings))


def test_resumable_never_duplicates_extraction():
    """2026-07-22 hardening: the core resumability guarantee. Simulates an
    interrupted run (extraction completed, critique never ran — exactly
    what a quota failure mid-critique leaves behind, as actually happened
    in the real pilot) and confirms resumable_financial_reasoning resumes
    from the critique step WITHOUT calling extract_document again — proven
    by checking extracted_facts count stays at 1, not 2, after the
    "resumed" call, regardless of caching (a cache HIT would still insert
    a duplicate extracted_facts row if extraction ran again; caching only
    avoids re-billing the API, never re-insertion — see extract.py)."""
    from ngxrot.documents.extract import extract_document

    con = make_test_db()
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)
    # Directly call extract_document (NOT financial_reasoning) to leave the
    # implication at 'draft_pending_self_critique' — simulating a crash/
    # quota failure that happened after extraction but before critique.
    extraction = extract_document(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    check("resume setup: extraction produced 1 fact", len(extraction.fact_ids) == 1)

    import pandas as pd
    facts_before = pd.read_sql("SELECT * FROM extracted_facts", con)
    impl_before = pd.read_sql("SELECT * FROM investment_implications", con)
    check("resume setup: implication still draft_pending_self_critique",
         impl_before.iloc[0].status == "draft_pending_self_critique")

    result = resumable_financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)

    facts_after = pd.read_sql("SELECT * FROM extracted_facts", con)
    check("resume: extracted_facts count unchanged (no duplicate extraction)",
         len(facts_after) == len(facts_before) == 1, f"before={len(facts_before)} after={len(facts_after)}")
    check("resume: warning explicitly states extraction was skipped",
         any("skipped re-extraction" in w for w in result.extraction.warnings))
    impl_after = pd.read_sql("SELECT * FROM investment_implications", con)
    check("resume: implication advanced past draft (critique ran)",
         impl_after.iloc[0].status != "draft_pending_self_critique")
    critiques = pd.read_sql("SELECT * FROM self_critique_reviews", con)
    check("resume: critique actually ran (8 questions recorded)", len(critiques) == 8)

    # Calling it AGAIN (fully resumed state) must also not duplicate anything.
    resumable_financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    facts_final = pd.read_sql("SELECT * FROM extracted_facts", con)
    check("resume: calling again on a fully-resumed doc still doesn't duplicate",
         len(facts_final) == 1, f"got {len(facts_final)}")


def test_pipeline_status_tracking():
    con = make_test_db()
    # doc_id 2/3 need a real `documents` row too (FK constraint) — minimal
    # stub rows, distinct from doc_id 1's full fixture from make_test_db().
    row = con.execute("SELECT source_id FROM sources LIMIT 1").fetchone()
    source_id = row[0]
    for doc_id in (2, 3):
        con.execute(
            "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, source_type, "
            "filing_date, retrieved_date, local_path, extraction_method, source_confidence, "
            "source_id, as_of_date) VALUES (?,'TESTCO','TESTCO','dividend','filing',"
            "'2026-04-01','2026-04-01','x','native',0.85,?,?)",
            (doc_id, source_id, date.today().isoformat()))
    con.commit()

    pstatus.mark_status(con, 1, "processing", model_id="gemini-3.6-flash",
                       prompt_version="v1")
    check("status: get_status reflects mark_status", pstatus.get_status(con, 1) == "processing")
    check("status: 'processing' is not skippable", not pstatus.should_skip(con, 1))

    pstatus.mark_status(con, 1, "completed", fact_count=0, implication_count=0)
    check("status: 'completed' with fact_count=0 matches reality (0 facts) -> skippable",
         pstatus.should_skip(con, 1))

    pstatus.mark_status(con, 2, "completed", fact_count=5, implication_count=5)
    check("status: 'completed' claiming 5 facts but 0 actually exist -> NOT trusted, not skipped",
         not pstatus.should_skip(con, 2))

    check("status: remaining_doc_ids filters out the genuinely-skippable doc",
         pstatus.remaining_doc_ids(con, [1, 2]) == [2])

    resume = pstatus.resume_point(con, 3)
    check("status: resume_point on an untouched doc needs extraction", resume.needs_extraction)

    check("status: determine_final_status with zero facts -> completed",
         pstatus.determine_final_status(con, []) == "completed")


def test_quota_error_not_retried():
    """cache.py's retry wrapper must NOT retry QuotaExceededError (it would
    waste 4 attempts/backoff on a daily quota that won't clear in seconds)
    — confirmed by counting how many times a poison provider's complete()
    is actually invoked."""
    calls = {"n": 0}

    class PoisonProvider:
        info = type("Info", (), {"model_id": "poison-v1"})()

        def complete(self, system_prompt, user_prompt, *, max_tokens=4096):
            calls["n"] += 1
            raise QuotaExceededError("simulated 429 RESOURCE_EXHAUSTED", retry_delay_seconds=12.0)

    con = make_test_db()
    try:
        cached_complete(con, PoisonProvider(), doc_id=1, purpose="draft_reasoning",
                        prompt_version="test_quota_v1", system_prompt="sys",
                        user_prompt="unique quota test prompt " + str(id(PoisonProvider)),
                        cache_dir=TEST_CACHE_DIR)
        check("quota: QuotaExceededError propagates", False)
    except QuotaExceededError as e:
        check("quota: QuotaExceededError propagates", True)
        check("quota: retry_delay_seconds parsed", e.retry_delay_seconds == 12.0)
    check("quota: complete() called exactly once (NOT retried 4x)", calls["n"] == 1,
         f"got {calls['n']} calls")

    import pandas as pd
    calls_logged = pd.read_sql("SELECT * FROM llm_calls", con)
    check("quota: no llm_calls row written for a failed call (nothing to log)",
         len(calls_logged) == 0)


def test_document_text_hash_and_cache_invalidation():
    from ngxrot.documents.cache import invalidate_cache_for_doc

    h1 = document_text_hash("some document text")
    h2 = document_text_hash("some document text")
    h3 = document_text_hash("different text")
    check("doc hash: identical text -> identical hash", h1 == h2)
    check("doc hash: different text -> different hash", h1 != h3)

    con = make_test_db()
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    import pandas as pd
    calls = pd.read_sql("SELECT * FROM llm_calls WHERE purpose='draft_reasoning'", con)
    check("doc hash: stored on the draft llm_calls row", calls.iloc[0].document_hash is not None
         and len(calls.iloc[0].document_hash) == 64)

    removed = invalidate_cache_for_doc(con, TEST_CACHE_DIR, doc_id=1, reason="test invalidation")
    check("cache invalidation: removed at least one cache file", removed >= 1)
    log = pd.read_sql("SELECT * FROM data_quality_log WHERE check_name='llm_cache_invalidation'", con)
    check("cache invalidation: logged to data_quality_log (auditable)", len(log) == 1)


def test_pilot_summary_generation():
    con = make_test_db()
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    pstatus.mark_status(con, 1, "completed", fact_count=1, implication_count=1)

    summary = pilot_summary.build_summary(con)
    check("summary: documents.processed reflects the completed doc",
         summary["documents"]["processed"] == 1)
    check("summary: self_critique.implications_total == 1",
         summary["self_critique"]["implications_total"] == 1)
    check("summary: performance.total_llm_calls == 2 (draft + critique)",
         summary["performance"]["total_llm_calls"] == 2)
    check("summary: performance.estimated_api_cost_usd is present (even if 0.0, assumed rate)",
         summary["performance"]["estimated_api_cost_usd"] is not None)
    check("summary: extraction.precision is None (no Phase B ground truth in this synthetic DB)",
         summary["extraction"]["precision"] is None)

    md = pilot_summary.render_markdown(summary)
    check("summary: markdown render includes the cost-confidence caveat", "assumed" in md)


DOC_TEXT_WITH_COMPETITOR = (
    "NOTICE OF DIVIDEND. The Board of Directors of TESTCO PLC is pleased to "
    "announce a final dividend of N1.90 per share for the financial year "
    "ended 31 December 2025. The register of members will close on "
    "10 April 2026 for qualification purposes, with payment expected on "
    "30 April 2026. Rival lender ZENITHBANK PLC may face competitive "
    "pressure from this announcement as customers compare payout yields."
)

GOOD_DRAFT_RESPONSE_WITH_COMPETITOR = GOOD_DRAFT_RESPONSE.replace(
    '"second_order_effects": [], "third_order_effects": [],',
    '"second_order_effects": [{"description": "Rival lender faces '
    'competitive pressure on payout yield comparisons", '
    '"affected_entity": "ZENITHBANK PLC", "quoted_evidence": '
    '"Rival lender ZENITHBANK PLC may face competitive pressure from this '
    'announcement as customers compare payout yields."}], "third_order_effects": [],')


def test_retrieval_layer():
    con = make_test_db()
    docs = retrieval.retrieve_documents(con, retrieval.RetrievalQuery(ticker="TESTCO"))
    check("retrieval: finds the fixture document by ticker", len(docs) == 1)
    check("retrieval: not yet extracted before any reasoning call",
         docs and docs[0].already_extracted is False)
    check("retrieval: has_text True (native extraction_method)", docs and docs[0].has_text)

    none_docs = retrieval.retrieve_documents(con, retrieval.RetrievalQuery(ticker="NOSUCHCO"))
    check("retrieval: unknown ticker returns nothing", len(none_docs) == 0)

    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)

    docs_after = retrieval.retrieve_documents(con, retrieval.RetrievalQuery(ticker="TESTCO"))
    check("retrieval: already_extracted True after extraction",
         docs_after and docs_after[0].already_extracted is True)

    facts = retrieval.find_facts(con, ticker="TESTCO")
    check("retrieval: find_facts returns the new dividend fact", len(facts) == 1
         and facts[0]["fact_type"] == "dividend")

    prior = retrieval.find_prior_implications(con, "TESTCO")
    check("retrieval: find_prior_implications returns the new implication", len(prior) == 1)


def test_reasoning_context_coverage_and_assembly():
    con = make_test_db()
    ctx_before = build_reasoning_context(con, "TESTCO")
    check("context: coverage_notes flags zero facts before any extraction",
         any("no extracted_facts" in n for n in ctx_before.coverage_notes))
    check("context: has_llm_facts False before extraction", ctx_before.has_llm_facts is False)

    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)

    ctx_after = build_reasoning_context(con, "TESTCO")
    check("context: facts populated after extraction", len(ctx_after.facts) == 1)
    check("context: has_llm_facts True after extraction", ctx_after.has_llm_facts is True)
    check("context: evidence rows attached", len(ctx_after.evidence) >= 1)
    # This synthetic test DB has no populated quant equity panel (that's a
    # much larger fixture than this pipeline's tests build) — build_
    # reasoning_context must degrade honestly rather than crash, which is
    # exactly what's being checked here: company_intelligence.build_profile
    # raises internally (empty panel) and context.py catches it, leaving
    # factor_exposures empty with an explicit coverage note instead of
    # propagating the exception.
    check("context: factor_exposures degrades to empty (no crash) when the "
         "quant equity panel doesn't exist in this database",
         ctx_after.factor_exposures == {})
    check("context: coverage_notes discloses why factor exposures are unavailable",
         any("factor-exposure computation unavailable" in n for n in ctx_after.coverage_notes))
    check("context: historical_implications includes the new implication",
         len(ctx_after.historical_implications) == 1)


def test_coverage_assessment_before_and_after_extraction():
    con = make_test_db()
    ctx_before = build_reasoning_context(con, "TESTCO")
    ca_before = ctx_before.coverage_assessment
    check("coverage: assessment attached automatically by build_reasoning_context",
         ca_before is not None)
    check("coverage: score is 0 before any extraction", ca_before.coverage_score == 0.0)
    check("coverage: has_facts absent before extraction", "has_facts" in ca_before.dimensions_missing)
    check("coverage: financial-statements gap disclosed for a ticker with no financial facts "
         "(fixed 2026-08-11 -- has_financial_statements is now computed per-ticker, not hardcoded)",
         any("[financial_statements]" in r for r in ca_before.reasons_confidence_limited))
    check("coverage: permanent gap (secondary sources) always disclosed",
         any("news/analyst ingestion" in r for r in ca_before.reasons_confidence_limited))
    from ngxrot.documents.extract import UNREVIEWED_LLM_CONFIDENCE_FLOOR
    check("coverage: ceiling never exceeds the platform-wide unreviewed floor",
         ca_before.confidence_ceiling <= UNREVIEWED_LLM_CONFIDENCE_FLOOR)

    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    ctx_after = build_reasoning_context(con, "TESTCO")
    ca_after = ctx_after.coverage_assessment
    check("coverage: score increases after real extraction", ca_after.coverage_score > ca_before.coverage_score)
    check("coverage: has_facts present after extraction", "has_facts" in ca_after.dimensions_present)
    check("coverage: has_grounded_evidence present (the fixture's quote is real and grounded)",
         "has_grounded_evidence" in ca_after.dimensions_present)
    check("coverage: has_multiple_source_documents still missing (single fixture doc)",
         "has_multiple_source_documents" in ca_after.dimensions_missing)
    check("coverage: dimensions checklist matches vocab.COVERAGE_DIMENSIONS exactly",
         set(ca_after.dimensions_present) | set(ca_after.dimensions_missing) == set(vocab.COVERAGE_DIMENSIONS))


def test_evidence_ranking_tiers_and_conflict_disagreement():
    con = make_test_db()
    check("trust tier: primary filing + passed grounding -> tier 1",
         assign_trust_tier(source_type="filing", grounding_check="passed", is_propagated=False).tier == 1)
    check("trust tier: failed grounding forced to tier 4 regardless of source_type",
         assign_trust_tier(source_type="filing", grounding_check="failed", is_propagated=False).tier == 4)
    check("trust tier: propagated implication forced to tier 4",
         assign_trust_tier(source_type=None, grounding_check=None, is_propagated=True).tier == 4)

    today = date.today().isoformat()
    fact_a = con.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, extraction_confidence, "
        "model_id, prompt_version, grounding_check, extracted_at) VALUES "
        "(1,'dividend','fact A — grounded, tier 1',0.3,'manual-test','test','passed',?)",
        (today,)).lastrowid
    ev_a = con.execute(
        "INSERT INTO evidence (doc_id, quoted_text, source_confidence) VALUES "
        "(1,'a final dividend of N1.90 per share',0.85)").lastrowid
    con.execute("UPDATE extracted_facts SET evidence_id = ? WHERE fact_id = ?", (ev_a, fact_a))
    fact_b = con.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, extraction_confidence, "
        "model_id, prompt_version, grounding_check, extracted_at) VALUES "
        "(1,'dividend','fact B — no evidence of its own, will be marked propagated',0.3,"
        "'manual-test','test','not_run',?)", (today,)).lastrowid

    impl_a = con.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "generated_at) VALUES (?,'TESTCO','medium','small',0.5,'rationale A','bullish',"
        "'no_action','unvalidated_ai_interpretation',?)", (fact_a, today)).lastrowid
    impl_b = con.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "propagated_from_implication_id, contradicts_implication_id, generated_at) VALUES "
        "(?,'TESTCO','medium','small',0.8,'rationale B','bearish','no_action','under_review',"
        "?,?,?)", (fact_b, impl_a, impl_a, today)).lastrowid
    con.commit()

    ranked = rank_evidence_for_fact(con, fact_a)
    check("evidence ranking: fact A's evidence ranks as tier 1",
         len(ranked) == 1 and ranked[0]["tier"] == 1)

    no_conflict = assess_implication_conflict(con, impl_a)
    check("conflict: implication with no contradicts_implication_id returns None",
         no_conflict is None)

    conflict = assess_implication_conflict(con, impl_b)
    check("conflict: contradiction detected", conflict is not None)
    if conflict is not None:
        check("conflict: higher STATED confidence (0.8) prefers 'this' (impl_b)",
             conflict.confidence_preferred == "this")
        check("conflict: higher TRUST TIER prefers 'prior' (impl_a, tier 1 vs impl_b's tier 4)",
             conflict.trust_tier_preferred == "prior")
        check("conflict: disagreement correctly flagged (confidence and trust tier diverge)",
             conflict.agreement is False)
        check("conflict: note names the disagreement explicitly", "DISAGREEMENT" in conflict.note)

    ctx = build_reasoning_context(con, "TESTCO")
    summary = ctx.evidence_ranking_summary
    check("evidence_ranking_summary: attached automatically by build_reasoning_context",
         bool(summary))
    check("evidence_ranking_summary: detects at least one conflict",
         summary["n_conflicts_detected"] >= 1)
    check("evidence_ranking_summary: detects the trust/confidence disagreement",
         summary["n_conflicts_where_trust_and_confidence_disagree"] >= 1)


def test_reasoning_result_confidence_ceiling_breach():
    con = make_test_db()
    today = date.today().isoformat()
    fact_id = con.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, extraction_confidence, "
        "model_id, prompt_version, grounding_check, extracted_at) VALUES "
        "(1,'dividend','artificially high-confidence fact for breach testing',0.3,"
        "'manual-test','test','not_run',?)", (today,)).lastrowid
    # Confidence of 0.8 could never be produced by extract.py itself (capped at
    # UNREVIEWED_LLM_CONFIDENCE_FLOOR=0.3) — constructed directly here purely to
    # exercise the breach-detection path against a value that exceeds every
    # possible coverage-derived ceiling (max ceiling == the floor itself).
    con.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "generated_at) VALUES (?,'TESTCO','medium','small',0.8,'artificial for testing',"
        "'bullish','no_action','unvalidated_ai_interpretation',?)", (fact_id, today))
    con.commit()

    provider = MockProvider({}, default="{}")  # never called — doc 1 already "extracted"
                                               # (model_id set on the manual fact above)
    result = reasoning_engine.reason_about_company(con, provider, "TESTCO", cache_dir=TEST_CACHE_DIR)
    check("orchestrator: coverage_assessment attached to ReasoningResult",
         result.coverage_assessment is not None)
    check("orchestrator: evidence_ranking_summary attached to ReasoningResult",
         isinstance(result.evidence_ranking_summary, dict) and bool(result.evidence_ranking_summary))
    check("orchestrator: no new document retrieved (manual fact already marks doc 1 extracted)",
         result.newly_processed_doc_ids == [])
    check("orchestrator: the artificially high-confidence implication is flagged as a breach",
         any(b["stored_confidence"] == 0.8 for b in result.confidence_ceiling_breaches))


def test_entity_relationships_populated_from_grounded_effect():
    con = make_test_db(doc_text=DOC_TEXT_WITH_COMPETITOR)
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE_WITH_COMPETITOR)
    financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)

    import pandas as pd
    rels = pd.read_sql(
        "SELECT r.*, subj.canonical_name AS subject_name, obj.canonical_name AS object_name "
        "FROM entity_relationships r "
        "JOIN entities subj ON subj.entity_id = r.subject_entity_id "
        "JOIN entities obj ON obj.entity_id = r.object_entity_id", con)
    check("entity_relationships: exactly one row (the grounded second_order_effect)",
         len(rels) == 1, f"got {len(rels)}")
    if len(rels):
        r = rels.iloc[0]
        check("entity_relationships: subject is the company itself", r.subject_name == "TESTCO")
        check("entity_relationships: object is the grounded competitor mention",
             r.object_name == "ZENITHBANK PLC")
        check("entity_relationships: relation_type encodes the effect order, not an "
             "invented taxonomy label", r.relation_type == "affects_order_2")
        check("entity_relationships: evidence-linked", r.source_evidence_id is not None)
        check("entity_relationships: confidence at the unreviewed-LLM floor",
             abs(r.confidence - 0.3) < 1e-9)

    found = retrieval.find_entity_relationships(con, ticker="TESTCO")
    check("retrieval: find_entity_relationships surfaces the new edge", len(found) == 1)
    # Note: a forced re-extraction is NOT expected to be duplicate-free here —
    # extract_document itself is not idempotent on rerun (a fresh `evidence`
    # row is inserted every call, by the same established design documented
    # in test_full_pipeline_all_pass's comment on financial_reasoning); the
    # real dedup guarantee record_relationship provides — the SAME
    # source_evidence_id never produces two rows — is covered directly in
    # test_record_relationship_rejects_self_and_ungrounded below.


def test_record_relationship_rejects_self_and_ungrounded():
    con = make_test_db()
    eid = resolve_or_create_entity(con, "TESTCO", "company", doc_id=1)
    ev_id = con.execute(
        "INSERT INTO evidence (doc_id, quoted_text, source_confidence) VALUES (1,'x',0.85)"
    ).lastrowid
    con.commit()
    result = record_relationship(con, eid, "affects_order_1", eid, ev_id, confidence=0.3)
    check("record_relationship: self-relationship rejected (returns None)", result is None)

    other = resolve_or_create_entity(con, "OTHERCO", "competitor_mention", doc_id=1)
    rid1 = record_relationship(con, eid, "affects_order_1", other, ev_id, confidence=0.3)
    rid2 = record_relationship(con, eid, "affects_order_1", other, ev_id, confidence=0.3)
    check("record_relationship: real relationship created", rid1 is not None)
    check("record_relationship: duplicate call returns the same row, not a new one",
         rid1 == rid2)


def test_historical_event_reaction():
    con = make_test_db()
    source_id = con.execute("SELECT source_id FROM sources LIMIT 1").fetchone()[0]
    import pandas as pd
    dates = pd.date_range("2024-01-02", periods=40, freq="B")
    price = 10.0
    for i, d in enumerate(dates):
        price = price * (1.01 if i == 20 else 1.00)  # a jump right at the event date
        con.execute(
            "INSERT INTO equity_prices (ticker, trade_date, close, source_id, "
            "confidence, as_of_date) VALUES ('TESTCO', ?, ?, ?, 0.9, ?)",
            (d.date().isoformat(), price, source_id, d.date().isoformat()))
    event_dates = [dates[20].date().isoformat(), dates[5].date().isoformat()]
    for i, ed in enumerate(event_dates):
        con.execute(
            "INSERT INTO events (event_type, announced_date, scope, ticker, headline, "
            "source_id, confidence, as_of_date) VALUES ('test_event', ?, 'ticker', "
            "'TESTCO', 'test event', ?, 0.9, ?)", (ed, source_id, ed))
    con.commit()

    stat = historical_event_reaction(con, "TESTCO", "test_event", "2024-03-01",
                                     window_days=3, min_events=2)
    check("event reaction: stat computed (2 historical events, floor met)",
         stat is not None and stat["insufficient"] is False)
    check("event reaction: n_events == 2", stat and stat["n_events"] == 2)

    sparse = historical_event_reaction(con, "TESTCO", "another_event_type", "2024-03-01",
                                       min_events=2)
    check("event reaction: unseen event_type returns None (no events at all)", sparse is None)


def test_reasoning_engine_orchestrator():
    con = make_test_db()
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE)

    result = reasoning_engine.reason_about_company(con, provider, "TESTCO",
                                                    cache_dir=TEST_CACHE_DIR)
    check("orchestrator: retrieved and processed the one unextracted candidate document",
         result.newly_processed_doc_ids == [1])
    check("orchestrator: assembled exactly one FactSummary", len(result.facts) == 1)
    fs = result.facts[0]
    check("orchestrator: fact summary carries the causal chain (why/why-now)",
         len(fs.causal_chain) == 2)
    check("orchestrator: fact summary carries all 13 impact categories",
         len(fs.impact_assessments) == 13)
    check("orchestrator: implication attached to the fact summary", fs.implication is not None)
    check("orchestrator: first_order effect captured under order 1",
         1 in fs.effects_by_order and len(fs.effects_by_order[1]) == 1)
    check("orchestrator: alternative_explanations surfaced from self-critique concern",
         len(fs.alternative_explanations) == 1)
    check("orchestrator: confidence_improving_info surfaced from research tasks",
         len(fs.confidence_improving_info) >= 1)
    # See test_reasoning_context_coverage_and_assembly's comment: this
    # synthetic DB has no quant equity panel, so factor_exposures degrades
    # to empty rather than crashing — checked via coverage_notes instead.
    check("orchestrator: coverage_notes propagated from the context onto the result",
         any("factor-exposure" in n for n in result.coverage_notes))

    # Idempotency: nothing left to retrieve on a second call.
    result2 = reasoning_engine.reason_about_company(con, provider, "TESTCO",
                                                     cache_dir=TEST_CACHE_DIR)
    check("orchestrator: second call retrieves nothing new (already extracted)",
         result2.newly_processed_doc_ids == [])
    check("orchestrator: second call still surfaces the same one fact",
         len(result2.facts) == 1)


def _add_peer_security(con, ticker: str, name: str):
    con.execute("INSERT INTO securities (ticker, name, board) VALUES (?, ?, 'main')",
               (ticker, name))
    con.commit()


def test_peer_ticker_resolution():
    con = make_test_db()
    _add_peer_security(con, "ZENITHBANK", "ZENITHBANK PLC")

    eid_match = resolve_or_create_entity(con, "zenithbank plc", "competitor_mention", doc_id=1)
    import pandas as pd
    row = pd.read_sql("SELECT * FROM entities WHERE entity_id = ?", con, params=(eid_match,)).iloc[0]
    check("ticker resolution: exact case-insensitive name match resolves to a real ticker",
         row.ticker == "ZENITHBANK")

    eid_nomatch = resolve_or_create_entity(con, "Some Rival Bank Not In Securities",
                                           "competitor_mention", doc_id=1)
    row2 = pd.read_sql("SELECT * FROM entities WHERE entity_id = ?", con,
                       params=(eid_nomatch,)).iloc[0]
    check("ticker resolution: unmatched name stays ticker=NULL (never guessed)",
         row2.ticker is None)


def test_industry_propagation_core():
    con = make_test_db(doc_text=DOC_TEXT_WITH_COMPETITOR)
    _add_peer_security(con, "ZENITHBANK", "ZENITHBANK PLC")
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE_WITH_COMPETITOR)
    result = financial_reasoning(con, provider, doc_id=1, cache_dir=TEST_CACHE_DIR)
    src_id = result.extraction.implication_ids[0]

    import pandas as pd
    ent = pd.read_sql("SELECT * FROM entities WHERE canonical_name = 'ZENITHBANK PLC'", con)
    check("propagation setup: ZENITHBANK PLC entity resolved to a real ticker",
         len(ent) == 1 and ent.iloc[0].ticker == "ZENITHBANK")

    new_ids = industry_reasoning.propagate_implication(con, src_id)
    check("propagation: exactly one peer implication created", len(new_ids) == 1, f"got {new_ids}")

    peer = pd.read_sql("SELECT * FROM investment_implications WHERE implication_id = ?",
                       con, params=(new_ids[0],)).iloc[0]
    src = pd.read_sql("SELECT * FROM investment_implications WHERE implication_id = ?",
                      con, params=(src_id,)).iloc[0]
    check("propagation: peer implication targets ZENITHBANK", peer.ticker == "ZENITHBANK")
    check("propagation: status is under_review (never independently self-critiqued)",
         peer.status == "under_review")
    check("propagation: propagated_from_implication_id set correctly",
         peer.propagated_from_implication_id == src_id)
    check("propagation: confidence discounted vs. source",
         peer.confidence < src.confidence)
    check("propagation: direction copied unchanged, not algorithmically inverted",
         peer.direction == src.direction)

    tasks = pd.read_sql("SELECT * FROM research_task_candidates WHERE implication_id = ?",
                        con, params=(new_ids[0],))
    check("propagation: paired research task created to determine actual peer direction",
         len(tasks) == 1 and "Determine whether" in tasks.iloc[0].description)

    chained = industry_reasoning.propagate_implication(con, new_ids[0])
    check("propagation: one-hop only — a propagated implication never re-propagates",
         chained == [])

    again = industry_reasoning.propagate_implication(con, src_id)
    check("propagation: rerunning returns the same implication_id, not a duplicate",
         again == new_ids)
    count = pd.read_sql(
        "SELECT COUNT(*) AS n FROM investment_implications WHERE propagated_from_implication_id = ?",
        con, params=(src_id,)).iloc[0].n
    check("propagation: exactly one row exists after rerun", count == 1)

    found = retrieval.find_peer_propagations(con, "ZENITHBANK")
    check("retrieval: find_peer_propagations surfaces it for ZENITHBANK", len(found) == 1)


def test_industry_propagation_skips_blocked_implication():
    con = make_test_db(doc_text=DOC_TEXT_WITH_COMPETITOR)
    _add_peer_security(con, "ZENITHBANK", "ZENITHBANK PLC")
    fail_critique = json.dumps({"critiques": [
        {"question": q, "finding": "fail" if q == "unevidenced_inference" else "pass",
         "explanation": "deliberately failing this one question for the test case"}
        for q in vocab.SELF_CRITIQUE_QUESTIONS]})
    provider = MockProvider({"Draft conclusion to critique": fail_critique},
                           default=GOOD_DRAFT_RESPONSE_WITH_COMPETITOR)
    # force=True: this test's draft/critique content is identical to
    # test_industry_propagation_core's (same doc text, same GOOD_DRAFT_
    # RESPONSE_WITH_COMPETITOR), so the critique prompt's cache key would
    # otherwise collide and silently replay that OTHER test's all-pass
    # cached response instead of this test's fail_critique — same pitfall
    # documented on test_ungrounded_quote_forced_to_zero_confidence.
    result = financial_reasoning(con, provider, doc_id=1, force=True, cache_dir=TEST_CACHE_DIR)
    src_id = result.extraction.implication_ids[0]
    import pandas as pd
    status = pd.read_sql("SELECT status FROM investment_implications WHERE implication_id = ?",
                         con, params=(src_id,)).iloc[0].status
    check("propagation setup: source implication is blocked_by_self_critique", status == "blocked_by_self_critique")
    new_ids = industry_reasoning.propagate_implication(con, src_id)
    check("propagation: a blocked_by_self_critique implication never propagates", new_ids == [])


def test_orchestrator_propagates_and_peer_sees_it():
    con = make_test_db(doc_text=DOC_TEXT_WITH_COMPETITOR)
    _add_peer_security(con, "ZENITHBANK", "ZENITHBANK PLC")
    provider = MockProvider({"Draft conclusion to critique": CRITIQUE_RESPONSE_ALL_PASS},
                           default=GOOD_DRAFT_RESPONSE_WITH_COMPETITOR)

    # force=True: the prior test (test_industry_propagation_skips_blocked_
    # implication) wrote a FAILING critique response to the on-disk cache
    # under this exact same (doc content, draft content) key — without
    # force this call would silently replay that poisoned entry instead of
    # this test's own all-pass provider. Same pitfall as elsewhere in this
    # file; cached_complete's force=True still WRITES (overwrites) the
    # cache, it doesn't just skip reading it, so this call also re-heals
    # the shared entry for anything running after it.
    result = reasoning_engine.reason_about_company(con, provider, "TESTCO", force=True,
                                                    cache_dir=TEST_CACHE_DIR)
    check("orchestrator: propagated exactly one implication to ZENITHBANK",
         len(result.propagated_implication_ids) == 1, f"got {result.propagated_implication_ids}")

    peer_result = reasoning_engine.reason_about_company(con, provider, "ZENITHBANK",
                                                        cache_dir=TEST_CACHE_DIR)
    check("orchestrator: ZENITHBANK's own call surfaces the received propagation",
         len(peer_result.peer_propagations_received) == 1)
    check("orchestrator: ZENITHBANK has no documents of its own — nothing retrieved",
         peer_result.newly_processed_doc_ids == [])


if __name__ == "__main__":
    test_grounding()
    test_banned_phrase()
    test_json_parsing()
    test_provider_config_and_factory()
    test_full_pipeline_all_pass()
    test_self_critique_fail_blocks_status()
    test_ungrounded_quote_forced_to_zero_confidence()
    test_resumable_never_duplicates_extraction()
    test_pipeline_status_tracking()
    test_quota_error_not_retried()
    test_document_text_hash_and_cache_invalidation()
    test_pilot_summary_generation()
    test_retrieval_layer()
    test_reasoning_context_coverage_and_assembly()
    test_coverage_assessment_before_and_after_extraction()
    test_evidence_ranking_tiers_and_conflict_disagreement()
    test_reasoning_result_confidence_ceiling_breach()
    test_entity_relationships_populated_from_grounded_effect()
    test_record_relationship_rejects_self_and_ungrounded()
    test_historical_event_reaction()
    test_reasoning_engine_orchestrator()
    test_peer_ticker_resolution()
    test_industry_propagation_core()
    test_industry_propagation_skips_blocked_implication()
    test_orchestrator_propagates_and_peer_sees_it()

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
