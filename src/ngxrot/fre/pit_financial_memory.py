"""FSI Phase 4: Point-in-Time Financial Reasoning Memory
(docs/fre_runs/fsi_phase4_preregistration.md).

Read-only, no write path of any kind. Filters FSI Phase 3's frozen
`financial_reasoning_conclusions` (`fsi-phase3-baseline-2026-08-01`) to
only those conclusions "knowable" as of a given historical date -- i.e.
every underlying source fact's OWN FILING was already public by that
date. This answers exactly one question -- "what did we know, and by
what reasoning, as of date D" -- never "what should we do about it": no
new fact, no new computation, no valuation, no ranking, no scoring, no
alpha claim, no portfolio output, no recommendation.

Deliberately mirrors FRE-3's `CompanyMemory.as_of()` PIT-audit pattern:
the same look-ahead-bias risk that module was built to prevent for raw
facts/events is exactly the risk this module prevents for Phase 3's
derived reasoning conclusions.

GATING RULE (docs/fre_runs/fsi_phase4_preregistration.md Area 1): a
conclusion is knowable as of date D iff every one of its linked source
facts' document `filing_date <= D`. Filing date, never the financial
`period_start`/`period_end` -- a filing about FY2024 is not knowable the
day FY2024 ends, only the day the filing is actually published.

ZERO-LINKED-FACT EDGE CASE (docs/fre_runs/fsi_phase4_implementation_log.md
Entry 1): 4 of Phase 3's 24 `insufficient_data` conclusions have no
linked source fact at all (there was nothing to link -- the finding IS
the absence of a fact). Two disclosed fallback rules apply:
  - if the conclusion names a specific period, gate by the EARLIEST
    filing_date among ALL of that ticker's real facts for that exact
    period (the absence became knowable when that one filing did);
  - if the conclusion is ticker-wide with no period (e.g. "no cfo fact
    exists anywhere for this ticker"), gate by the LATEST filing_date
    among ALL of that ticker's real facts (a claim about a COMPLETE set
    of filings is only true once every filing in that set is known).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class SourceFactPIT:
    fact_id: int
    role: str
    fact_type: str
    doc_id: int
    filing_date: str


@dataclass
class KnowableConclusion:
    conclusion_id: int
    conclusion_type: str
    metric: str
    status: str
    value_numeric: float | None
    value_text: str | None
    confidence_tier: str | None
    method: str
    limitations: str
    period_start: str | None
    period_end: str | None
    computed_at: str
    knowable_as_of: str
    source_facts: list[SourceFactPIT] = field(default_factory=list)


@dataclass
class CompanyFinancialReasoningSnapshot:
    ticker: str
    as_of_date: str
    conclusions: list[KnowableConclusion]
    excluded_count: int  # conclusions that exist for this ticker but are not yet knowable as of this date


def _source_facts(con: sqlite3.Connection, conclusion_id: int) -> list[SourceFactPIT]:
    rows = con.execute(
        "SELECT fc.fact_id, fc.role, f.fact_type, f.doc_id, d.filing_date "
        "FROM financial_reasoning_conclusion_facts fc "
        "JOIN extracted_facts f ON f.fact_id = fc.fact_id "
        "JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE fc.conclusion_id = ? ORDER BY fc.fact_id, fc.role",
        (conclusion_id,),
    ).fetchall()
    return [SourceFactPIT(fact_id=r[0], role=r[1], fact_type=r[2], doc_id=r[3], filing_date=r[4])
            for r in rows]


def _earliest_filing_for_period(con: sqlite3.Connection, ticker: str,
                                 period_start: str, period_end: str) -> str | None:
    row = con.execute(
        "SELECT MIN(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.period_start = ? AND f.period_end = ?",
        (ticker, period_start, period_end),
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _latest_filing_for_ticker(con: sqlite3.Connection, ticker: str) -> str | None:
    row = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ?",
        (ticker,),
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _knowable_as_of_date(con: sqlite3.Connection, ticker: str, period_start: str | None,
                          period_end: str | None, source_facts: list[SourceFactPIT]) -> str | None:
    if source_facts:
        return max(f.filing_date for f in source_facts)
    if period_start is not None and period_end is not None:
        return _earliest_filing_for_period(con, ticker, period_start, period_end)
    return _latest_filing_for_ticker(con, ticker)


def as_of(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyFinancialReasoningSnapshot:
    """Every FSI Phase 3 conclusion for `ticker` knowable on or before
    `as_of_date` -- gated by public filing dates, never financial period
    dates. Single-ticker only (mirrors Phase 3's own Area 7 guardrail):
    this function has no parameter or return field that could compare
    or rank across tickers."""
    rows = con.execute(
        "SELECT conclusion_id, conclusion_type, metric, status, value_numeric, value_text, "
        "confidence_tier, method, limitations, period_start, period_end, computed_at "
        "FROM financial_reasoning_conclusions WHERE ticker = ? ORDER BY conclusion_id",
        (ticker,),
    ).fetchall()

    knowable: list[KnowableConclusion] = []
    excluded = 0
    for row in rows:
        (cid, ctype, metric, status, value_numeric, value_text, confidence_tier,
         method, limitations, period_start, period_end, computed_at) = row
        source_facts = _source_facts(con, cid)
        knowable_date = _knowable_as_of_date(con, ticker, period_start, period_end, source_facts)
        if knowable_date is None or knowable_date > as_of_date:
            excluded += 1
            continue
        knowable.append(KnowableConclusion(
            conclusion_id=cid, conclusion_type=ctype, metric=metric, status=status,
            value_numeric=value_numeric, value_text=value_text, confidence_tier=confidence_tier,
            method=method, limitations=limitations, period_start=period_start, period_end=period_end,
            computed_at=computed_at, knowable_as_of=knowable_date, source_facts=source_facts,
        ))
    return CompanyFinancialReasoningSnapshot(
        ticker=ticker, as_of_date=as_of_date, conclusions=knowable, excluded_count=excluded,
    )


def audit_no_lookahead(con: sqlite3.Connection, ticker: str, as_of_date: str) -> list[str]:
    """Mechanical self-check (docs/fre_runs/fsi_phase4_preregistration.md
    Area 3): returns a list of violation descriptions (empty = clean) --
    every conclusion `as_of()` returns for `ticker`/`as_of_date` must have
    EVERY source fact's filing_date <= as_of_date. Independent of
    as_of()'s own internal filter logic in the sense that it re-checks the
    raw per-fact dates directly, not just the conclusion's own recorded
    `knowable_as_of` value -- catching a bug in the gating computation
    itself, not merely re-asserting it."""
    snapshot = as_of(con, ticker, as_of_date)
    violations = []
    for c in snapshot.conclusions:
        for f in c.source_facts:
            if f.filing_date > as_of_date:
                violations.append(
                    f"conclusion_id={c.conclusion_id} ({ticker}/{c.metric}) includes fact_id={f.fact_id} "
                    f"from doc_id={f.doc_id} filed {f.filing_date}, which is AFTER as_of_date={as_of_date}"
                )
    return violations
