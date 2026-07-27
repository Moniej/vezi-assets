"""CoverageAssessment (stabilization pass, 2026-07-27, owner-approved — see
HANDOFF.md). Quantifies how much evidence actually backs a company's
reasoning context — not a free-text impression (ReasoningContext.
coverage_notes already existed for that), but a fixed, auditable checklist
(vocab.COVERAGE_DIMENSIONS) each ticker either satisfies or doesn't, a
resulting coverage_score, a confidence_ceiling derived mechanically from that
score, and the specific reasons the ceiling is where it is.

Deliberately descriptive, not enforcing: this module never writes to
investment_implications.confidence. reasoning_engine.py compares each
implication's STORED confidence against this assessment's ceiling and
reports any breach for owner review (`ReasoningResult.
confidence_ceiling_breaches`) — same "disclosed, not silently patched"
posture the self-critique gate already uses for concerns/fails.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import vocab

PKG_ROOT = Path(__file__).resolve().parents[3]


def _fact_taxonomy_leaf_count() -> int:
    raw = tomllib.loads((PKG_ROOT / "configs/fact_taxonomy.toml").read_text(encoding="utf-8"))
    return len({t for spec in raw.values() for t in spec.get("types", [])})


@dataclass
class CoverageAssessment:
    ticker: str
    as_of: str

    n_documents_total: int = 0
    n_documents_processed: int = 0
    n_facts: int = 0
    n_distinct_fact_types: int = 0
    n_taxonomy_fact_types: int = 0
    n_evidence_rows: int = 0
    n_grounded_evidence_rows: int = 0
    n_distinct_source_documents: int = 0
    has_entity_relationships: bool = False
    has_event_history: bool = False
    has_factor_exposures: bool = False
    has_cross_ticker_corroboration: bool = False
    has_financial_statements: bool = False   # permanently False today — no
                                             # financial-statements dataset
                                             # exists platform-wide
    has_secondary_sources: bool = False      # permanently False today — no
                                             # news/analyst ingestion built yet

    dimensions_present: list[str] = field(default_factory=list)
    dimensions_missing: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    confidence_ceiling: float = 0.0
    reasons_confidence_limited: list[str] = field(default_factory=list)


def _confidence_ceiling(coverage_score: float) -> float:
    from .extract import UNREVIEWED_LLM_CONFIDENCE_FLOOR
    for threshold, multiplier in vocab.COVERAGE_CONFIDENCE_CEILING_BANDS:
        if coverage_score >= threshold:
            return round(UNREVIEWED_LLM_CONFIDENCE_FLOOR * multiplier, 4)
    return round(UNREVIEWED_LLM_CONFIDENCE_FLOOR * vocab.COVERAGE_CONFIDENCE_CEILING_BANDS[-1][1], 4)


def assess_coverage(con, ctx) -> CoverageAssessment:
    """Built from an already-assembled ReasoningContext (ctx) plus a handful
    of direct queries for facts ReasoningContext doesn't carry (grounding_
    check per fact, cross-ticker corroboration) — avoids re-issuing the
    queries context.py already ran."""
    ca = CoverageAssessment(ticker=ctx.ticker, as_of=ctx.as_of)

    ca.n_documents_total = len(ctx.documents)
    ca.n_documents_processed = sum(1 for d in ctx.documents if d.already_extracted)
    ca.n_facts = len(ctx.facts)
    ca.n_distinct_fact_types = len({f["fact_type"] for f in ctx.facts})
    ca.n_taxonomy_fact_types = _fact_taxonomy_leaf_count()
    ca.n_evidence_rows = len(ctx.evidence)
    ca.n_distinct_source_documents = len({e["doc_id"] for e in ctx.evidence})
    ca.has_entity_relationships = len(ctx.entity_relationships) > 0
    ca.has_event_history = len(ctx.events) > 0
    ca.has_factor_exposures = bool(ctx.factor_exposures)

    fact_ids = [f["fact_id"] for f in ctx.facts]
    if fact_ids:
        placeholders = ",".join("?" * len(fact_ids))
        ca.n_grounded_evidence_rows = con.execute(
            f"SELECT COUNT(*) FROM extracted_facts WHERE fact_id IN ({placeholders}) "
            f"AND grounding_check = 'passed'", fact_ids).fetchone()[0]
        ca.has_cross_ticker_corroboration = con.execute(
            f"SELECT 1 FROM investment_implications WHERE fact_id IN ({placeholders}) "
            f"AND corroborates_implication_id IS NOT NULL LIMIT 1", fact_ids).fetchone() is not None

    checks = {
        "has_facts": ca.n_facts > 0,
        "has_grounded_evidence": ca.n_grounded_evidence_rows > 0,
        "has_multiple_source_documents": ca.n_distinct_source_documents >= 2,
        "has_multiple_fact_types": ca.n_distinct_fact_types >= 2,
        "has_entity_relationships": ca.has_entity_relationships,
        "has_event_history": ca.has_event_history,
        "has_factor_exposures": ca.has_factor_exposures,
        "has_cross_ticker_corroboration": ca.has_cross_ticker_corroboration,
        "has_financial_statements": ca.has_financial_statements,
        "has_secondary_sources": ca.has_secondary_sources,
    }
    assert set(checks) == set(vocab.COVERAGE_DIMENSIONS), \
        "coverage_assessment.py's checklist drifted from vocab.COVERAGE_DIMENSIONS"

    ca.dimensions_present = [d for d in vocab.COVERAGE_DIMENSIONS if checks[d]]
    ca.dimensions_missing = [d for d in vocab.COVERAGE_DIMENSIONS if not checks[d]]
    ca.coverage_score = round(len(ca.dimensions_present) / len(vocab.COVERAGE_DIMENSIONS), 4)
    ca.confidence_ceiling = _confidence_ceiling(ca.coverage_score)

    reasons = [f"{len(ca.dimensions_present)}/{len(vocab.COVERAGE_DIMENSIONS)} mechanical "
              f"coverage dimensions present (score={ca.coverage_score}); confidence ceiling "
              f"set to {ca.confidence_ceiling} accordingly"]
    _EXPLANATIONS = {
        "has_facts": "no extracted_facts on record for this ticker",
        "has_grounded_evidence": "no fact has a quote that passed the verbatim grounding check",
        "has_multiple_source_documents": "evidence traces back to a single source document — "
                                        "same single-document-overreaction risk self_critique.py checks per-fact",
        "has_multiple_fact_types": "only one fact_type has ever been observed for this ticker",
        "has_entity_relationships": "no persisted entity relationships (competitors/peers) for this ticker",
        "has_event_history": "no events on record for this ticker as of this date",
        "has_factor_exposures": "quant factor-exposure computation unavailable for this ticker/database",
        "has_cross_ticker_corroboration": "no prior implication for this ticker/fact_type has ever "
                                         "corroborated another — either no repetition observed, or every "
                                         "repetition disagreed",
        "has_financial_statements": "no financial-statements dataset exists platform-wide yet "
                                    "(docs/EXECUTION_BACKLOG.md) — this dimension cannot be satisfied "
                                    "by ANY ticker until that dataset is built",
        "has_secondary_sources": "no news/analyst ingestion exists platform-wide yet — this dimension "
                                 "cannot be satisfied by ANY ticker until that pipeline is built",
    }
    reasons.extend(_EXPLANATIONS[d] for d in ca.dimensions_missing)
    ca.reasons_confidence_limited = reasons
    return ca
