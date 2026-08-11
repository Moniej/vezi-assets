"""Decision Intelligence Phase 13/16: Institutional Company Research Report.

Extends `company_research_dossier.py` (FSI-11, unmodified) -- does not
rebuild its memory/thesis/knowledge-graph sections, reuses
`render_dossier()` verbatim for that portion. Phase 16 upgraded this from
Phase 13's first draft: now built on top of `company_intelligence_
bundle.py` (Phase 15's fusion layer) rather than re-composing state/
changes/confidence independently, and adds the sections Phase 16 named
that Phase 13 didn't have: Capital Allocation, Management (merged into
Insider Activity), Data-Quality Assessment, Evidence Timeline, Open
Questions, and "What Would Change The Current Assessment" (a deterministic
invalidation-condition generator, not a prediction).

SCOPE NOTE (unchanged from Phase 13, restated per Phase 16's own explicit
instruction): NO BUY/SELL/AVOID label, NO cross-sectional ranking, NO
unified conviction score, anywhere in this module.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.company_intelligence_bundle import CompanyIntelligenceBundle, build_intelligence_bundle
from ngxrot.fre.company_research_dossier import render_dossier, build_dossier
from ngxrot.fre.company_state import KNOWN


@dataclass
class FullCompanyReport:
    bundle: CompanyIntelligenceBundle
    dossier: object  # company_research_dossier.CompanyResearchDossier, unmodified


def build_full_report(con: sqlite3.Connection, ticker: str, as_of_date: str, prior_date: str,
                       intelligence_cache: dict | None = None,
                       include_portfolio_note: bool = True) -> FullCompanyReport:
    bundle = build_intelligence_bundle(con, ticker, as_of_date, prior_date, intelligence_cache,
                                        include_portfolio_note=include_portfolio_note)
    dossier = build_dossier(con, ticker, as_of_date)
    return FullCompanyReport(bundle=bundle, dossier=dossier)


def _dp(dp) -> str:
    if dp.status != KNOWN:
        return f"{dp.status}"
    return f"{dp.value!r} (as of {dp.as_of}; source: {dp.source})"


def _invalidation_conditions(report: FullCompanyReport) -> list[str]:
    """Deterministic, template-generated -- never a forecast. For each
    HIGH/CRITICAL change and each active contradiction, names the SPECIFIC
    fact/period that would need to update to resolve it. No probability,
    no direction-of-outcome claim."""
    b = report.bundle
    out: list[str] = []
    for a in b.ranked_changes:
        if a.level in ("HIGH", "CRITICAL"):
            out.append(f"A subsequent {a.change.field} figure (post-{b.as_of_date}) confirming "
                       f"or reversing the {a.change.direction} move recorded on {a.change.timestamp} "
                       f"would materially update this assessment.")
    if b.thesis.contradiction_note:
        out.append("Resolution of the recorded thesis contradiction (a newer, higher-confidence "
                   "implication superseding the conflicting one) would materially update this "
                   "assessment.")
    if b.state.financial["valuation_confidence"].status == KNOWN and \
            b.state.financial["valuation_confidence"].value in ("no_data", "single_method", "low"):
        out.append("Additional currency-clean, PIT-valid comparable-peer accounting facts "
                   "(net_profit/equity) would raise valuation_confidence beyond its current low tier.")
    return out or ["No specific invalidation trigger identified from currently available evidence."]


def render_full_report(report: FullCompanyReport) -> str:
    b = report.bundle
    s, c, ep = b.state, b.confidence, b.economic_profile
    thesis = b.thesis
    lines = [
        f"# Institutional Research Report: {b.ticker}",
        f"*As of {b.as_of_date}. Compared against {b.prior_date}.*",
        "",
        "## 1. Executive Investment View",
        f"Data completeness: {s.data_completeness:.0%}. Overall confidence: {c.overall} "
        f"({'; '.join(c.overall_reasons)}). This section is deliberately descriptive, not "
        f"prescriptive -- no BUY/WATCH/HOLD/AVOID recommendation is produced by this platform "
        f"(see Section 23).",
        "",
        "## 2. Company Overview",
        f"Sector: {_dp(s.business['sector'])}",
        f"Sub-industry: {_dp(s.business['sub_industry'])}",
        f"Business model: {_dp(s.business['business_model'])}",
        f"Business description: {_dp(s.business['business_description'])}",
        f"Products/services: {_dp(ep.fields['products_services'])}",
        f"Revenue segments: {_dp(s.business['segments'])}",
        f"Geography: {_dp(s.business['geography'])}",
        f"Competitive/peer context: {_dp(ep.fields['competitive_peer_context'])}",
        f"Customer concentration: {_dp(ep.fields['customer_concentration'])}",
        f"Supplier dependencies: {_dp(ep.fields['supplier_dependencies'])}",
        f"Management/ownership: {_dp(ep.fields['management_ownership'])}",
        f"Material subsidiaries: {_dp(ep.fields['material_subsidiaries'])}",
        f"Strategic priorities: {_dp(ep.fields['strategic_priorities'])}",
        "",
        "## 3. What Changed",
    ]
    if b.ranked_changes:
        for a in b.ranked_changes:
            lines.append(f"- [{a.level}] {a.change.category}/{a.change.field}: "
                         f"{a.change.description} ({'; '.join(a.reasons)})")
    else:
        lines.append("No material changes detected between the two snapshots.")
    lines += [
        "",
        "## 4. Fundamental Analysis / Financial Condition",
        f"Revenue: {_dp(s.financial['revenue'])}",
        f"Net profit: {_dp(s.financial['net_profit'])}",
        f"Equity: {_dp(s.financial['equity'])}",
        f"Assets: {_dp(s.financial['assets'])}",
        f"Liabilities: {_dp(s.financial['liabilities'])}",
        f"Capital structure: {_dp(ep.fields['capital_structure'])}",
        f"Accounting anomaly flags: {_dp(s.financial['accounting_anomaly_flags'])}",
        "",
        "## 5. Earnings Trajectory",
        "See Section 3 (financial changes) and Section 4 for the most recent knowable figures; "
        "no separate multi-period earnings series is rendered here beyond what change_detection "
        "already surfaced (single-snapshot financial state, not a full time series).",
        "",
        "## 6. Capital Allocation",
        thesis.capital_allocation_assessment if thesis and thesis.capital_allocation_assessment else "UNKNOWN",
        "",
        "## 7. Management & Insider Activity",
        f"Management assessment: {thesis.management_assessment if thesis and thesis.management_assessment else 'UNKNOWN'}",
        f"Insider transactions: {_dp(s.insider_activity)}",
        "",
        "## 8. Regulatory Developments",
        _dp(s.regulatory),
        "",
        "## 9. Corporate Actions / Historical Events",
        _dp(s.corporate_events),
        "",
        "## 10. Market Behavior",
        f"Close: {_dp(s.market['close'])}",
        f"60-day ADTV (NGN): {_dp(s.market['adtv_60d_ngn'])}",
        f"Realized volatility (12m annualized): {_dp(s.market['realized_vol_ann_12m'])}",
        f"Max drawdown (3y): {_dp(s.market['max_drawdown_3y'])}",
        f"Watchlist status: {_dp(s.market['watchlist_status'])}",
        "",
        "## 11. Bull Case", thesis.bull_case if thesis and thesis.bull_case else "UNKNOWN", "",
        "## 12. Base Case", thesis.base_case if thesis and thesis.base_case else "UNKNOWN", "",
        "## 13. Bear Case", thesis.bear_case if thesis and thesis.bear_case else "UNKNOWN", "",
        "## 14. Catalysts",
    ]
    lines += ([f"- {x}" for x in thesis.catalysts] if thesis and thesis.catalysts else ["UNKNOWN"])
    lines += ["", "## 15. Risks"]
    lines += ([f"- {x}" for x in thesis.key_risks] if thesis and thesis.key_risks else ["UNKNOWN"])
    lines += [
        "", "## 16. Contradictory Evidence",
        thesis.contradiction_note if thesis and thesis.contradiction_note else "None recorded.",
        "",
        "## 17. Valuation Status",
        f"VALUATION_CONFIDENCE = {s.financial['valuation_confidence'].value if s.financial['valuation_confidence'].status == KNOWN else 'UNKNOWN'}",
        f"Intrinsic value range: {_dp(s.financial['intrinsic_value_range'])}",
        "Per this platform's Core Principle: valuation is one evidence source among several, "
        "never fabricated when unsupported.",
        "",
        "## 18. Data-Quality Assessment",
        f"company_state data_completeness: {s.data_completeness:.0%}",
        f"economic_profile coverage (15 requested company-context fields): {ep.coverage:.0%}",
        f"Confirmed platform-wide UNKNOWN fields (never fabricated): "
        f"{sum(1 for f in ep.fields.values() if f.status != KNOWN)}/{len(ep.fields)}",
        "",
        "## 19. Confidence Assessment",
        f"Data: {c.data_confidence} ({c.data_confidence_reason})",
        f"Fundamental: {c.fundamental_confidence} ({c.fundamental_confidence_reason})",
        f"Thesis: {c.thesis_confidence} ({c.thesis_confidence_reason})",
        f"Valuation: {c.valuation_confidence} ({c.valuation_confidence_reason})",
        f"Catalyst: {c.catalyst_confidence} ({c.catalyst_confidence_reason})",
        f"Risk: {c.risk_confidence} ({c.risk_confidence_reason})",
        f"Overall: {c.overall} ({'; '.join(c.overall_reasons)})",
        "",
        "## 20. Evidence Timeline",
    ]
    timeline_entries = sorted(
        [(a.change.timestamp, f"[{a.level}] {a.change.description} (source: {a.change.source})")
         for a in b.ranked_changes],
    )
    lines += ([f"- {ts}: {desc}" for ts, desc in timeline_entries] if timeline_entries
              else ["No dated evidence items between the two snapshots."])
    lines += [
        "",
        "## 21. Open Questions",
    ]
    lines += ([f"- {x}" for x in thesis.missing_evidence] if thesis and thesis.missing_evidence
              else ["UNKNOWN"])
    lines += [
        "",
        "## 22. What Would Change The Current Assessment",
    ]
    lines += [f"- {x}" for x in _invalidation_conditions(report)]
    lines += [
        "",
        "## 23. Recommendation",
        "NOT PRODUCED BY THIS PLATFORM. Phase 8 (systematic BUY/WATCH/HOLD/AVOID vocabulary) "
        "and Phase 10 (cross-sectional ranking) were explicitly excluded from this build -- see "
        "docs/fre_runs/decision_intelligence_baseline_audit.md Section 6.",
        "",
        "## 24. Evidence Appendix",
        f"Source implication IDs: {thesis.source_implication_ids if thesis else []}",
        "Full memory/thesis/knowledge-graph evidence detail below (company_research_dossier.py, "
        "unmodified):",
        "",
        render_dossier(report.dossier),
    ]
    return "\n".join(str(x) for x in lines)
