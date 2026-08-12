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
    as_of_date: str


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
        "SELECT fc.fact_id, fc.role, f.fact_type, f.doc_id, d.filing_date, d.as_of_date "
        "FROM financial_reasoning_conclusion_facts fc "
        "JOIN extracted_facts f ON f.fact_id = fc.fact_id "
        "JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE fc.conclusion_id = ? ORDER BY fc.fact_id, fc.role",
        (conclusion_id,),
    ).fetchall()
    return [SourceFactPIT(fact_id=r[0], role=r[1], fact_type=r[2], doc_id=r[3],
                          filing_date=r[4], as_of_date=r[5])
            for r in rows]


def _earliest_filing_for_period(con: sqlite3.Connection, ticker: str,
                                 period_start: str, period_end: str) -> tuple[str, str] | None:
    """Returns (filing_date, as_of_date) of the SAME governing document --
    correlated, not independent MIN()s, so the capture-vintage check below
    (added 2026-08-12) reflects the document that actually made the period
    knowable, not an unrelated row's capture date."""
    row = con.execute(
        "SELECT d.filing_date, d.as_of_date FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.period_start = ? AND f.period_end = ? "
        "ORDER BY d.filing_date ASC LIMIT 1",
        (ticker, period_start, period_end),
    ).fetchone()
    return (row[0], row[1]) if row else None


def _latest_filing_for_ticker(con: sqlite3.Connection, ticker: str) -> tuple[str, str] | None:
    """Returns (filing_date, as_of_date) of the SAME governing document --
    see _earliest_filing_for_period's docstring."""
    row = con.execute(
        "SELECT d.filing_date, d.as_of_date FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? ORDER BY d.filing_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    return (row[0], row[1]) if row else None


def _knowable_as_of_date(con: sqlite3.Connection, ticker: str, period_start: str | None,
                          period_end: str | None,
                          source_facts: list[SourceFactPIT]) -> tuple[str, str | None] | None:
    """Returns (knowable_date, capture_vintage) -- capture_vintage is the
    latest as_of_date among the governing fact(s) (added 2026-08-12,
    production-reliability audit, Finding A), None only in the
    zero-linked-fact fallback cases where _earliest_filing_for_period /
    _latest_filing_for_ticker found nothing at all (knowable_date is then
    also None, handled by the caller exactly as before)."""
    if source_facts:
        return max(f.filing_date for f in source_facts), max(f.as_of_date for f in source_facts)
    if period_start is not None and period_end is not None:
        found = _earliest_filing_for_period(con, ticker, period_start, period_end)
    else:
        found = _latest_filing_for_ticker(con, ticker)
    return found if found is not None else (None, None)


def as_of(con: sqlite3.Connection, ticker: str, as_of_date: str,
          vintage: str | None = None) -> CompanyFinancialReasoningSnapshot:
    """Every FSI Phase 3 conclusion for `ticker` knowable on or before
    `as_of_date` -- gated by public filing dates, never financial period
    dates. Single-ticker only (mirrors Phase 3's own Area 7 guardrail):
    this function has no parameter or return field that could compare
    or rank across tickers.

    `vintage` (added 2026-08-12, production-reliability audit, Finding A):
    a SEPARATE gate from `as_of_date` -- as_of_date is the market's
    knowledge date (filing_date); vintage is when THIS SYSTEM captured the
    governing document(s) (documents.as_of_date). This module's own
    `audit_no_lookahead` only ever re-checked filing_date, so it reported
    "clean" even though nothing here gated on capture time -- verified on
    the live database, 98.8% of documents have a retrieved_date more than
    30 days after filing_date (avg gap ~4.6 years), so a historical
    `as_of_date` query without a vintage gate can include conclusions
    built from documents the system did not yet possess as of that date.
    `None` (the default) preserves the exact prior unfiltered behavior."""
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
        knowable_date, capture_vintage = _knowable_as_of_date(con, ticker, period_start, period_end, source_facts)
        if knowable_date is None or knowable_date > as_of_date:
            excluded += 1
            continue
        if vintage and (capture_vintage is None or capture_vintage > vintage):
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


def audit_no_lookahead(con: sqlite3.Connection, ticker: str, as_of_date: str,
                        vintage: str | None = None) -> list[str]:
    """Mechanical self-check (docs/fre_runs/fsi_phase4_preregistration.md
    Area 3): returns a list of violation descriptions (empty = clean) --
    every conclusion `as_of()` returns for `ticker`/`as_of_date` must have
    EVERY source fact's filing_date <= as_of_date. Independent of
    as_of()'s own internal filter logic in the sense that it re-checks the
    raw per-fact dates directly, not just the conclusion's own recorded
    `knowable_as_of` value -- catching a bug in the gating computation
    itself, not merely re-asserting it.

    `vintage` (added 2026-08-12, production-reliability audit, Finding A):
    when given, also re-checks every source fact's own document
    as_of_date (capture date) against `vintage`, independent of as_of()'s
    internal gating -- this is the check that would have caught Finding A
    directly (the pre-fix version of this function only ever checked
    filing_date, so it reported "clean" in the presence of the bug)."""
    snapshot = as_of(con, ticker, as_of_date, vintage=vintage)
    violations = []
    for c in snapshot.conclusions:
        for f in c.source_facts:
            if f.filing_date > as_of_date:
                violations.append(
                    f"conclusion_id={c.conclusion_id} ({ticker}/{c.metric}) includes fact_id={f.fact_id} "
                    f"from doc_id={f.doc_id} filed {f.filing_date}, which is AFTER as_of_date={as_of_date}"
                )
            if vintage and f.as_of_date > vintage:
                violations.append(
                    f"conclusion_id={c.conclusion_id} ({ticker}/{c.metric}) includes fact_id={f.fact_id} "
                    f"from doc_id={f.doc_id} captured (as_of_date) {f.as_of_date}, which is AFTER "
                    f"vintage={vintage}"
                )
    return violations
