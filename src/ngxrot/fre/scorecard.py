"""Decision Intelligence Phase 9: Recommendation Scorecard.

SCOPE NOTE (owner decision, this build): Phase 8's systematic BUY/WATCH/
HOLD/AVOID vocabulary and Phase 10's cross-sectional ranking are
DELIBERATELY NOT implemented in this scorecard -- they directly conflict
with `docs/fre/09_portfolio_reasoning.md`'s explicit, dated rejection of
"shadow ranking" and `docs/fre_runs/OWNER_DECISION_BACKLOG_2026-08-02.md`'s
standing gate ("Part 9 Tier 2 ... never to be shortcut by FRE/FSI ...
until >=2 validated independent factors exist"), per
`docs/fre_runs/decision_intelligence_baseline_audit.md` Section 6 and the
owner's own explicit scope restriction in response to that finding.

This scorecard is therefore DESCRIPTIVE, not PRESCRIPTIVE: seven
independent per-category signals, each a direct, disclosed, mechanical
read (never a blended score), shown side by side -- conflict is preserved,
never averaged away, per Phase 5's own explicit instruction. There is no
`recommendation`/`conviction`/composite-score field anywhere in this
module.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.change_detection import DetectedChange, detect_changes
from ngxrot.fre.company_state import KNOWN, CompanyState, build_company_state
from ngxrot.fre.company_thesis import CompanyThesis, build_company_thesis
from ngxrot.fre.confidence_engine import ConfidenceDimensions, compute_confidence
from ngxrot.fre.materiality import assess_materiality

UNKNOWN_SIGNAL = "UNKNOWN"


@dataclass
class Scorecard:
    ticker: str
    as_of_date: str

    fundamental_signal: str   # IMPROVING | DETERIORATING | MIXED | STABLE | UNKNOWN
    fundamental_confidence: str
    corporate_action_signal: str  # ACTIVE | QUIET | UNKNOWN
    regulatory_signal: str        # FAVORABLE | ADVERSE | NEUTRAL | UNKNOWN
    insider_signal: str           # NET_BUYING | NET_SELLING | MIXED | UNKNOWN
    market_signal: str            # RISING | FALLING | STABLE | UNKNOWN
    valuation_signal: str         # UNDERVALUED | OVERVALUED | FAIR | UNKNOWN

    confidence: ConfidenceDimensions
    data_completeness: float

    primary_thesis: str | None       # thesis.bull_case, verbatim
    counter_thesis: str | None       # thesis.bear_case, verbatim
    base_case: str | None
    key_risks: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    contradiction_note: str | None = None
    missing_evidence: list[str] = field(default_factory=list)

    material_changes: list[dict] = field(default_factory=list)  # [{category, field, level, description}]
    evidence_ids: list[int] = field(default_factory=list)       # source_implication_ids, verbatim


def _fundamental_signal(changes: list[DetectedChange]) -> str:
    fin = [c for c in changes if c.category == "financial" and c.direction in ("improved", "worsened")]
    if not fin:
        return "STABLE" if changes else UNKNOWN_SIGNAL
    improved = sum(1 for c in fin if c.direction == "improved")
    worsened = sum(1 for c in fin if c.direction == "worsened")
    if improved and not worsened:
        return "IMPROVING"
    if worsened and not improved:
        return "DETERIORATING"
    return "MIXED"


def _regulatory_signal(state: CompanyState) -> str:
    if state.regulatory.status != KNOWN:
        return UNKNOWN_SIGNAL
    directions = [e.get("direction") for e in state.regulatory.value if e.get("direction")]
    pos = sum(1 for d in directions if d in ("positive", "bullish"))
    neg = sum(1 for d in directions if d in ("negative", "bearish"))
    if pos and not neg:
        return "FAVORABLE"
    if neg and not pos:
        return "ADVERSE"
    return "NEUTRAL" if directions else UNKNOWN_SIGNAL


def _insider_signal(state: CompanyState) -> str:
    if state.insider_activity.status != KNOWN:
        return UNKNOWN_SIGNAL
    txns = state.insider_activity.value
    n_buy = sum(1 for t in txns if t.nature == "PURCHASE" and not t.routine_flag)
    n_sell = sum(1 for t in txns if t.nature == "SALE" and not t.routine_flag)
    if n_buy and not n_sell:
        return "NET_BUYING"
    if n_sell and not n_buy:
        return "NET_SELLING"
    return "MIXED" if (n_buy or n_sell) else UNKNOWN_SIGNAL


def _market_signal(changes: list[DetectedChange]) -> str:
    price_changes = [c for c in changes if c.category == "market" and c.field == "close"]
    if not price_changes:
        return UNKNOWN_SIGNAL
    return "RISING" if price_changes[0].direction == "improved" else \
           "FALLING" if price_changes[0].direction == "worsened" else "STABLE"


def _valuation_signal(state: CompanyState) -> str:
    price_dp = state.market["close"]
    range_dp = state.financial["intrinsic_value_range"]
    if price_dp.status != KNOWN or range_dp.status != KNOWN:
        return UNKNOWN_SIGNAL
    low, high = range_dp.value
    price = price_dp.value
    if price < low:
        return "UNDERVALUED"
    if price > high:
        return "OVERVALUED"
    return "FAIR"


def build_scorecard(con: sqlite3.Connection, ticker: str, as_of_date: str, prior_as_of_date: str,
                     intelligence_cache: dict | None = None) -> Scorecard:
    """`prior_as_of_date` is the comparison point for change detection
    (e.g. 90 days earlier) -- callers choose it explicitly; this function
    never picks one on its own."""
    current = build_company_state(con, ticker, as_of_date, intelligence_cache)
    prior = build_company_state(con, ticker, prior_as_of_date, intelligence_cache)
    changes = detect_changes(prior, current)
    assessments = [assess_materiality(c) for c in changes]

    thesis: CompanyThesis | None = build_company_thesis(con, ticker, as_of_date)
    confidence = compute_confidence(current, thesis)

    material_changes = [
        {"category": a.change.category, "field": a.change.field, "level": a.level,
         "description": a.change.description}
        for a in sorted(assessments, key=lambda a: -{"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}[a.level])
    ]

    corp_status = current.corporate_events.status
    n_corp = len([c for c in changes if c.category == "corporate_event"])
    corporate_action_signal = ("ACTIVE" if n_corp > 0 else "QUIET") if corp_status == KNOWN else UNKNOWN_SIGNAL

    return Scorecard(
        ticker=ticker, as_of_date=as_of_date,
        fundamental_signal=_fundamental_signal(changes),
        fundamental_confidence=confidence.fundamental_confidence,
        corporate_action_signal=corporate_action_signal,
        regulatory_signal=_regulatory_signal(current),
        insider_signal=_insider_signal(current),
        market_signal=_market_signal(changes),
        valuation_signal=_valuation_signal(current),
        confidence=confidence,
        data_completeness=current.data_completeness,
        primary_thesis=thesis.bull_case if thesis else None,
        counter_thesis=thesis.bear_case if thesis else None,
        base_case=thesis.base_case if thesis else None,
        key_risks=list(thesis.key_risks) if thesis and thesis.key_risks else [],
        catalysts=list(thesis.catalysts) if thesis and thesis.catalysts else [],
        contradiction_note=thesis.contradiction_note if thesis else None,
        missing_evidence=list(thesis.missing_evidence) if thesis and thesis.missing_evidence else [],
        material_changes=material_changes,
        evidence_ids=list(thesis.source_implication_ids) if thesis and thesis.source_implication_ids else [],
    )
