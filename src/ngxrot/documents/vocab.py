"""Fixed vocabularies for the reasoning engine — hardcoded, not config-driven
(these are stable, spec-fixed categories from docs/REASONING_ENGINE_
SPECIFICATION.md, not something a user should be able to silently extend by
editing a TOML — same reasoning as event_pipeline.py's module-level
_DIRECTIONS/_SEVERITIES sets). Every schema CHECK constraint in
schema/schema.sql has an exact counterpart here so Python-side validation
catches a bad value before it ever reaches a database CHECK failure.
"""

from __future__ import annotations

# Same vocabulary as event_pipeline.py's _DIRECTIONS — reused, not
# reinvented, so an AI-sourced direction and a hand-curated event's
# direction mean exactly the same thing platform-wide.
DIRECTIONS = {"bullish", "bearish", "neutral", "unknown"}

IMPACT_CATEGORIES = {
    "revenue", "margins", "cash_flow", "capital_allocation", "balance_sheet",
    "growth", "competitive_advantage", "execution_risk", "regulatory_risk",
    "liquidity", "valuation", "market_expectations", "long_term_moat",
}
IMPACT_DIRECTIONS = {"positive", "negative", "neutral", "mixed", "unknown"}

DURATION_BUCKETS = {"very_short", "short", "medium", "long", "structural", "permanent"}
MAGNITUDES = {"tiny", "small", "medium", "large", "transformational"}

DIRECTIONS_2WAY = {"increase", "decrease", "unclear"}
DIRECTIONS_2WAY_NA = {"increase", "decrease", "unclear", "not_assessed"}
THESIS_IMPACTS = {"strengthens", "weakens", "neutral"}

ACTION_RECOMMENDATIONS = {
    "no_action", "watchlist", "research_task", "model_update",
    "valuation_update", "factor_candidate", "immediate_review",
}

MARKET_REACTIONS = {"underreacting", "overreacting", "fairly_priced", "unclear"}

IMPLICATION_STATUSES = {
    "draft_pending_self_critique", "blocked_by_self_critique",
    "unvalidated_ai_interpretation", "under_review",
    "promoted_to_discovery_candidate", "rejected_by_review",
}

GROUNDING_CHECKS = {"not_run", "passed", "failed", "overridden"}

SELF_CRITIQUE_QUESTIONS = (
    "unevidenced_inference", "correlation_vs_causation",
    "ignored_alternative_explanation", "single_document_overreaction",
    "contradicts_prior_evidence", "insufficient_information",
    "confidence_improving_information", "market_noise_check",
)
CRITIQUE_FINDINGS = {"pass", "concern", "fail"}
CRITIQUE_ACTIONS = {
    "none", "confidence_lowered", "status_downgraded",
    "research_task_created", "flagged_for_human_review",
}

# Self-critique config, per REASONING_ENGINE_SPECIFICATION.md §14 (open
# decisions the spec explicitly left for the owner to set during the Phase D
# pilot rather than inventing a number). Documented here, not silently
# hardcoded elsewhere, so a reviewer can find and change them in one place.
INDUSTRY_PROPAGATION_CONFIDENCE_DISCOUNT = 0.5   # ad hoc default (architecture
                                                  # doc §4.5/open decision #6:
                                                  # "TBD with owner before Phase
                                                  # F") — multiplicative, applied
                                                  # to the source implication's
                                                  # already-capped confidence.
                                                  # Flagged in reports/
                                                  # phase_f_completion.md;
                                                  # owner-adjustable.

CONFIDENCE_DISCOUNT_PER_CONCERN = 0.10   # ad hoc, flagged in the completion report
MIN_EVIDENCE_COUNT_FLOOR = 1            # a fact backed by zero evidence rows
                                          # is a schema violation already (§11
                                          # chain-completeness check); this
                                          # floor of 1 is deliberately
                                          # permissive for the pilot — a
                                          # stricter floor is an owner call
                                          # once real disagreement rates are
                                          # observed, not invented now.
