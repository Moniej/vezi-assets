"""Prompt construction — deliberately separate from model execution
(llm_providers.py/cache.py know nothing about what a prompt says; this
module knows nothing about how a call is made). Plain-JSON output rather
than a vendor-specific tool-use/function-calling schema, so the contract
stays provider-agnostic (the stated engineering requirement is "the LLM
provider can be swapped later" — a vendor-specific structured-output
mechanism would quietly violate that).

Two prompts, matching the two SEPARATE reasoning calls the spec requires
(REASONING_ENGINE_SPECIFICATION.md §12): DRAFT_PROMPT_VERSION builds the
Step 1-13 draft; CRITIQUE_PROMPT_VERSION is the adversarial Step 14 pass,
given only the draft + evidence, told to argue against it.
"""

from __future__ import annotations

import json

from . import vocab

DRAFT_PROMPT_VERSION = "financial_reasoning_draft_v1"
CRITIQUE_PROMPT_VERSION = "self_critique_v1"

# Financial Reasoning Engine's scope for this pilot (REASONING_ENGINE_
# SPECIFICATION.md §10): capital_and_balance_sheet fact types, matching
# Phase B's dividend/rights/bonus ground truth so precision/recall against
# deterministic facts is actually measurable.
PILOT_FACT_TYPES = ["dividend", "rights_issue", "bonus_issue"]

_DRAFT_SYSTEM_PROMPT = """You are the Financial Reasoning Engine of an institutional equity research \
platform. You read one corporate filing at a time and produce structured, \
evidence-linked investment intelligence. You are not a summarizer and you \
do not produce sentiment labels.

NON-NEGOTIABLE RULES:
- Every fact, causal-chain link, and impact judgment must be traceable to \
an EXACT VERBATIM quote from the document text you are given. Never \
paraphrase a quote. If you cannot find a supporting quote, say so \
explicitly (set the evidence field to null) rather than inventing one.
- Never estimate a numeric intrinsic value, price target, or valuation \
multiple. You may only state a DIRECTION (increase/decrease/unclear) and \
explain the economic mechanism in words.
- Never fabricate a fact, date, or number that is not stated in the \
document. If information is missing, use "unclear"/null and say what \
additional information would resolve it.
- Every category, direction, or bucket you assign must come with an \
explanation of WHY — a bare label ("bullish", "this is good") without a \
causal reason is a rule violation, not an acceptable answer.
- State your assumptions explicitly. Do not let an assumption silently \
determine a conclusion.

You must return ONLY a single JSON object matching the schema you are \
given — no prose before or after it, no markdown code fences."""

_DRAFT_SCHEMA_INSTRUCTIONS = """Return exactly this JSON shape (one entry in "facts" per material fact \
of the given types found in the document; if none are found, return \
{"facts": []}):

{
  "facts": [
    {
      "fact_type": one of %(fact_types)s,
      "description": "one-sentence factual description",
      "quoted_evidence": "EXACT verbatim quote from the document text, or null if none exists",
      "numeric_value": number or null,
      "qualification_date": "YYYY-MM-DD" or null,
      "payment_date": "YYYY-MM-DD" or null,
      "agm_date": "YYYY-MM-DD" or null,
      "closure_date": "YYYY-MM-DD" or null,
      "causal_chain": [
        {"statement": "...", "inferred": false, "quoted_evidence": "..." or null}
        // step_order 0 is the raw fact restated; each subsequent entry is one more "why" —
        // keep asking why until you reach the economic reason (revenue/earnings/intrinsic value).
        // inferred=false only if quoted_evidence is a real verbatim quote; inferred=true for
        // economic reasoning steps that are not directly quoted.
      ],
      "impact_assessments": {
        // ALL 13 keys REQUIRED, always, even if direction is "unknown":
        // revenue, margins, cash_flow, capital_allocation, balance_sheet, growth,
        // competitive_advantage, execution_risk, regulatory_risk, liquidity, valuation,
        // market_expectations, long_term_moat
        "<category>": {"direction": "positive|negative|neutral|mixed|unknown", "explanation": "..."}
      },
      "implication": {
        "ticker": "the affected company's ticker symbol, best guess from the document text",
        "direction": "bullish|bearish|neutral|unknown",
        "duration_bucket": "very_short|short|medium|long|structural|permanent",
        "magnitude": "tiny|small|medium|large|transformational",
        "confidence": number between 0 and 1,
        "confidence_rationale": "explain the uncertainty, not just the number",
        "assumptions": "state explicitly what you are assuming, or null if none",
        "bull_case_delta": "how this changes the bull case, or null",
        "bear_case_delta": "how this changes the bear case, or null",
        "base_case_delta": "how this changes the base case, or null",
        "intrinsic_value_direction": "increase|decrease|unclear",
        "intrinsic_value_reasoning": "the MECHANISM, never a bare direction",
        "expected_earnings_direction": "increase|decrease|unclear",
        "target_multiple_direction": "increase|decrease|unclear|not_assessed",
        "risk_profile_direction": "increase|decrease|unclear|not_assessed",
        "portfolio_sizing_note": "qualitative note only, never a position size, or null",
        "action_recommendation": "no_action|watchlist|research_task|model_update|valuation_update|factor_candidate|immediate_review",
        "market_reaction_assessment": "underreacting|overreacting|fairly_priced|unclear",
        "market_reaction_reasoning": "...",
        "first_order_effects": [{"description": "...", "affected_entity": "company/sector/commodity name", "quoted_evidence": "..." or null}],
        "second_order_effects": [{"description": "...", "affected_entity": "...", "quoted_evidence": null}],
        "third_order_effects": [{"description": "...", "affected_entity": "...", "quoted_evidence": null}],
        "research_tasks": [{"description": "a specific piece of missing information that would raise confidence"}]
      }
    }
  ]
}""" % {"fact_types": json.dumps(PILOT_FACT_TYPES)}


def build_draft_prompt(doc_text: str, ticker: str | None, doc_type: str,
                       filing_date: str) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt). Caller stamps prompt_version =
    DRAFT_PROMPT_VERSION when logging/caching."""
    user_prompt = (
        f"Document metadata: ticker={ticker!r}, doc_type={doc_type!r}, "
        f"filing_date={filing_date!r}.\n\n"
        f"Document text:\n\"\"\"\n{doc_text}\n\"\"\"\n\n"
        f"{_DRAFT_SCHEMA_INSTRUCTIONS}"
    )
    return _DRAFT_SYSTEM_PROMPT, user_prompt


_CRITIQUE_SYSTEM_PROMPT = """You are the devil's-advocate reviewer of an institutional investment \
committee. Another analyst (a different reasoning pass, not you) has drafted \
a conclusion about a company filing. Your ONLY job is to find fault with it \
— you do not get credit for agreeing. You are given the draft conclusion and \
the original document text it was based on.

Answer EXACTLY these eight questions, each with a finding of "pass", \
"concern", or "fail", and an explanation that justifies the finding (an \
empty or one-word explanation is not acceptable):

1. unevidenced_inference — did the draft infer something without evidence?
2. correlation_vs_causation — did the draft confuse correlation with causation?
3. ignored_alternative_explanation — did the draft ignore a plausible \
alternative explanation? You MUST state at least one alternative explanation \
and argue why the draft's explanation is more (or equally, or less) likely — \
a generic "no alternative" answer without a stated alternative fails this \
question by construction.
4. single_document_overreaction — did the draft overreact to a single document?
5. contradicts_prior_evidence — does this draft contradict anything you can see was \
already stated in the document that the draft itself did not address?
6. insufficient_information — is there enough information in the document to \
support the draft's confidence level?
7. confidence_improving_information — what SPECIFIC piece of information, if \
available, would most increase confidence in this conclusion? (this question \
always produces a research task, never a rhetorical non-answer)
8. market_noise_check — could this simply be routine/immaterial disclosure \
rather than something that matters?

Return ONLY a single JSON object, no prose before or after, no markdown \
fences:

{
  "critiques": [
    {"question": "unevidenced_inference", "finding": "pass|concern|fail", "explanation": "..."},
    {"question": "correlation_vs_causation", "finding": "...", "explanation": "..."},
    {"question": "ignored_alternative_explanation", "finding": "...", "explanation": "..."},
    {"question": "single_document_overreaction", "finding": "...", "explanation": "..."},
    {"question": "contradicts_prior_evidence", "finding": "...", "explanation": "..."},
    {"question": "insufficient_information", "finding": "...", "explanation": "..."},
    {"question": "confidence_improving_information", "finding": "...", "explanation": "...", "research_task": "the specific missing information"},
    {"question": "market_noise_check", "finding": "...", "explanation": "..."}
  ]
}"""


def build_critique_prompt(draft_json: dict, doc_text: str) -> tuple[str, str]:
    user_prompt = (
        f"Original document text:\n\"\"\"\n{doc_text}\n\"\"\"\n\n"
        f"Draft conclusion to critique:\n{json.dumps(draft_json, indent=2)}\n"
    )
    return _CRITIQUE_SYSTEM_PROMPT, user_prompt
