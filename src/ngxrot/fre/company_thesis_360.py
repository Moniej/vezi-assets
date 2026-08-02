"""FSI Phase 8: Financial-Reasoning-Informed Investment Thesis
(docs/fre_runs/fsi_phase8_preregistration.md).

A pure, read-only COMPOSITION layer, mirroring FSI Phase 6's own
precedent exactly: calls FRE-5's `build_company_thesis()` and Phase 6's
`company_memory_360.as_of()`, both unmodified, and returns both
alongside two new, purely mechanical evidence lists drawn from the FSI
financial-reasoning conclusions already present inside the Phase 6
snapshot. Neither underlying module is modified, forked, or
reimplemented.

No scoring, weighting, ranking, voting, balancing algorithm, confidence
aggregation, alpha estimate, expected return, investment recommendation,
or portfolio suggestion of any kind. No synthesized "overall thesis
strength" field exists anywhere in this module -- by design, not by
omission (see `CompanyThesis360`'s own dataclass fields, verified by
direct introspection in this module's test suite).

Evidence categorization rule (the ONLY judgment this module makes, and
it restates a rule Phase 3 already established, rather than inventing a
new one -- see docs/fre_runs/fsi_phase8_implementation_log.md Entry 0):
- `concern_evidence`: every FIRED financial-health flag
  (`leverage_increasing`, `margin_compression`,
  `cash_flow_earnings_divergence`) -- all three were designed in Phase 3
  as risk/concern checks, never as positive signals, so a fired flag
  restates an already-established meaning, not a new one.
- `supplementary_evidence`: everything else the FSI track produces (all
  ratios, all trends, not-fired flags, insufficient_data flags) --
  deliberately NOT assigned a bull/bear polarity, since Phase 3's own
  design committed trend direction to neutral vocabulary specifically
  to avoid a valuation-adjacent favorability judgment; this module does
  not reopen that decision.

Conflicting evidence is never resolved: if a concern flag fires for one
period while an unrelated ratio looks favorable for another, both
appear as separate, individually-auditable items -- this module performs
no reconciliation of any kind.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.company_memory_360 import CompanyMemory360, as_of as memory_as_of
from ngxrot.fre.company_thesis import CompanyThesis, build_company_thesis
from ngxrot.fre.pit_financial_memory import KnowableConclusion

_CONCERN_FLAG_METRICS = ("leverage_increasing", "margin_compression", "cash_flow_earnings_divergence")


@dataclass
class FSIEvidenceItem:
    conclusion_id: int
    conclusion_type: str  # 'ratio' | 'trend' | 'flag'
    metric: str
    status: str  # 'computed' | 'insufficient_data'
    value_numeric: float | None
    value_text: str | None
    confidence_tier: str | None
    method: str
    limitations: str
    period_start: str | None
    period_end: str | None


@dataclass
class CompanyThesis360:
    ticker: str
    as_of_date: str
    thesis: CompanyThesis
    memory: CompanyMemory360
    concern_evidence: list[FSIEvidenceItem] = field(default_factory=list)
    supplementary_evidence: list[FSIEvidenceItem] = field(default_factory=list)


def _to_evidence_item(c: KnowableConclusion) -> FSIEvidenceItem:
    return FSIEvidenceItem(
        conclusion_id=c.conclusion_id, conclusion_type=c.conclusion_type, metric=c.metric,
        status=c.status, value_numeric=c.value_numeric, value_text=c.value_text,
        confidence_tier=c.confidence_tier, method=c.method, limitations=c.limitations,
        period_start=c.period_start, period_end=c.period_end,
    )


def _is_fired_concern_flag(c: KnowableConclusion) -> bool:
    return c.conclusion_type == "flag" and c.metric in _CONCERN_FLAG_METRICS and c.value_text == "fired"


def as_of(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyThesis360:
    """Single-ticker only (mirrors the guardrail already enforced in
    every prior FSI module). Calls build_company_thesis() and
    company_memory_360.as_of() unmodified for the SAME (ticker,
    as_of_date), then mechanically splits the financial conclusions
    already present in the memory snapshot into concern/supplementary
    evidence -- no new query, no new fact, no new inference."""
    thesis = build_company_thesis(con, ticker, as_of_date)
    memory = memory_as_of(con, ticker, as_of_date)

    concern_evidence = []
    supplementary_evidence = []
    for c in memory.financial.conclusions:
        item = _to_evidence_item(c)
        if _is_fired_concern_flag(c):
            concern_evidence.append(item)
        else:
            supplementary_evidence.append(item)

    return CompanyThesis360(
        ticker=ticker, as_of_date=as_of_date, thesis=thesis, memory=memory,
        concern_evidence=concern_evidence, supplementary_evidence=supplementary_evidence,
    )
