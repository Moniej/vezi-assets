"""Decision Intelligence Phase 12: Portfolio Decision Support.

NOT autonomous trading, NOT sizing, NOT allocation -- decision support
only, composing `scorecard.py` (Phase 9) over an explicit, caller-supplied
list of hypothetical holdings. This module never invents a portfolio: the
caller must name the tickers. It also never writes back into
`alpha_engine.py`/the quant registry (the same hard boundary
`portfolio_memory.py` itself already enforces) -- `cross_reference()` is
called read-only, exactly as `company_portfolio_context.py` already does.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.portfolio_memory import cross_reference
from ngxrot.fre.scorecard import Scorecard, build_scorecard

_CRITICAL_MATERIALITY = "CRITICAL"


@dataclass
class PortfolioDecisionSupport:
    as_of_date: str
    prior_date: str
    holdings: list[str]
    portfolio_health: dict[str, str]        # ticker -> overall confidence (LOW/MEDIUM/HIGH)
    thesis_changes: list[dict]              # [{ticker, field, level, description}]
    risk_alerts: list[dict]                 # [{ticker, reason}]
    research_queue: list[str]               # tickers needing review, sorted worst-first
    scorecards: dict[str, Scorecard] = field(default_factory=dict)
    failed_tickers: list[str] = field(default_factory=list)  # named honestly, never silently dropped


def _risk_alerts_for(sc: Scorecard) -> list[str]:
    reasons = []
    for chg in sc.material_changes:
        if chg["level"] == _CRITICAL_MATERIALITY:
            reasons.append(f"CRITICAL change: {chg['description']}")
    if sc.regulatory_signal == "ADVERSE":
        reasons.append("regulatory signal is ADVERSE")
    if sc.insider_signal == "NET_SELLING":
        reasons.append("insider activity is NET_SELLING (non-routine)")
    if sc.contradiction_note:
        reasons.append(f"active contradiction in thesis: {sc.contradiction_note}")
    return reasons


def build_portfolio_decision_support(
    con: sqlite3.Connection, holdings: list[str], as_of_date: str, prior_date: str,
    intelligence_cache: dict | None = None,
) -> PortfolioDecisionSupport:
    scorecards: dict[str, Scorecard] = {}
    failed: list[str] = []
    for t in holdings:
        try:
            scorecards[t] = build_scorecard(con, t, as_of_date, prior_date,
                                             intelligence_cache=intelligence_cache)
        except Exception:
            failed.append(t)

    portfolio_health = {t: sc.confidence.overall for t, sc in scorecards.items()}

    thesis_changes = []
    for t, sc in scorecards.items():
        for chg in sc.material_changes:
            if chg["category"] in ("financial", "corporate_event", "regulatory"):
                thesis_changes.append({"ticker": t, **chg})

    risk_alerts = []
    for t, sc in scorecards.items():
        for reason in _risk_alerts_for(sc):
            risk_alerts.append({"ticker": t, "reason": reason})
        # Portfolio Memory cross-reference is read-only and always-live
        # (portfolio_memory.py's own disclosed non-PIT limitation, not
        # something this module can fix) -- surfaced as an alert only when
        # a HOLDING is not (or no longer) in the live validated sleeve.
        note = cross_reference(t)
        if not note.in_live_sleeve:
            risk_alerts.append({"ticker": t, "reason": "not in the live validated quant sleeve "
                                                        "(portfolio_memory.cross_reference(), always-live)"})

    _ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    research_queue = sorted(
        [t for t, sc in scorecards.items()
         if sc.confidence.overall == "LOW" or sc.data_completeness < 0.5],
        key=lambda t: (_ORDER[scorecards[t].confidence.overall], scorecards[t].data_completeness),
    )

    return PortfolioDecisionSupport(
        as_of_date=as_of_date, prior_date=prior_date, holdings=holdings,
        portfolio_health=portfolio_health, thesis_changes=thesis_changes,
        risk_alerts=risk_alerts, research_queue=research_queue,
        scorecards=scorecards, failed_tickers=failed,
    )
