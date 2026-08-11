"""Decision Intelligence Phase 15: Information Fusion.

Wires together every existing/prior-built layer into ONE composed object,
exactly the chain the task names:

  company_state -> filings/financial facts/regulatory events/insider
  activity/corporate actions/market data (all already inside
  company_state.py) -> valuation outputs (company_state.financial) ->
  change detection -> materiality -> confidence -> portfolio memory.

This module adds NO new data source and NO new computation over raw
facts -- it is purely an assembly point, so that "what is happening to
this company, what changed, why does it matter, and what evidence
supports that" can be answered from ONE object rather than five separate
function calls. Contradictory evidence is preserved, never resolved: if
`company_thesis.contradiction_note` is populated, it is carried through
verbatim, and `change_detection`'s own per-change source citations are
never merged into a single consensus narrative.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.change_detection import DetectedChange, detect_changes
from ngxrot.fre.company_economic_profile import EconomicProfile, build_economic_profile
from ngxrot.fre.company_state import CompanyState, build_company_state
from ngxrot.fre.company_thesis import CompanyThesis, build_company_thesis
from ngxrot.fre.confidence_engine import ConfidenceDimensions, compute_confidence
from ngxrot.fre.materiality import MaterialityAssessment, assess_materiality, rank_by_materiality
from ngxrot.fre.portfolio_memory import PortfolioMemoryNote, cross_reference


@dataclass
class CompanyIntelligenceBundle:
    ticker: str
    as_of_date: str
    prior_date: str
    state: CompanyState
    prior_state: CompanyState
    economic_profile: EconomicProfile
    thesis: CompanyThesis
    ranked_changes: list[MaterialityAssessment]
    confidence: ConfidenceDimensions
    portfolio_note: PortfolioMemoryNote


def build_intelligence_bundle(con: sqlite3.Connection, ticker: str, as_of_date: str, prior_date: str,
                               intelligence_cache: dict | None = None,
                               include_portfolio_note: bool = True) -> CompanyIntelligenceBundle:
    """`include_portfolio_note=False` skips the ~15-20s uncached
    `portfolio_memory.cross_reference()` call -- set False for batch/
    market-wide use where that cost is prohibitive (see market_
    intelligence.py's own disclosed limitation); True is the default
    for single-ticker "what is happening" queries, where full fusion
    (matching the task's own named chain) matters more than latency."""
    state = build_company_state(con, ticker, as_of_date, intelligence_cache)
    prior_state = build_company_state(con, ticker, prior_date, intelligence_cache)
    economic_profile = build_economic_profile(con, ticker, as_of_date, intelligence_cache)
    thesis = build_company_thesis(con, ticker, as_of_date)
    changes = detect_changes(prior_state, state)
    ranked = rank_by_materiality([assess_materiality(c) for c in changes])
    confidence = compute_confidence(state, thesis)
    portfolio_note = cross_reference(ticker) if include_portfolio_note else PortfolioMemoryNote(
        ticker=ticker, in_live_sleeve=False, hypothesis_id=None, action=None,
        size_pct_nav=None, as_of=None, rationale="portfolio_note skipped (include_portfolio_note=False)")

    return CompanyIntelligenceBundle(
        ticker=ticker, as_of_date=as_of_date, prior_date=prior_date,
        state=state, prior_state=prior_state, economic_profile=economic_profile,
        thesis=thesis, ranked_changes=ranked, confidence=confidence, portfolio_note=portfolio_note,
    )


def what_is_happening(bundle: CompanyIntelligenceBundle) -> str:
    """Deterministic, mechanically-assembled narrative -- every sentence
    traces to a specific field on the bundle, cited inline. Not LLM
    generation; a template over already-governed data."""
    lines = [f"{bundle.ticker} as of {bundle.as_of_date} (compared to {bundle.prior_date}):"]

    if not bundle.ranked_changes:
        lines.append("No material changes detected between the two snapshots.")
    else:
        lines.append(f"{len(bundle.ranked_changes)} change(s) detected, most material first:")
        for a in bundle.ranked_changes:
            lines.append(f"  [{a.level}] {a.change.description} "
                         f"(source: {a.change.source}; reason: {'; '.join(a.reasons)})")

    if bundle.thesis.bull_case:
        lines.append(f"Bull case: {bundle.thesis.bull_case}")
    if bundle.thesis.bear_case:
        lines.append(f"Bear case: {bundle.thesis.bear_case}")
    if bundle.thesis.contradiction_note:
        lines.append(f"CONTRADICTION (preserved, not resolved): {bundle.thesis.contradiction_note}")

    lines.append(f"Overall confidence: {bundle.confidence.overall} "
                 f"({'; '.join(bundle.confidence.overall_reasons)})")
    lines.append(f"In live validated quant sleeve: {bundle.portfolio_note.in_live_sleeve}")
    return "\n".join(lines)
