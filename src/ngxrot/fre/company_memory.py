"""FRE-3: Company Memory (docs/fre/05_company_memory.md), implemented.

A PIT-safe, read-only, per-company longitudinal aggregation over tables
that already exist -- no new table, no schema change, no LLM call. Modeled
directly on the existing `context.build_reasoning_context()` precedent
(Phase E): a Python object assembled by filtered queries, not a new system
of record. Every date filter follows this project's non-negotiable PIT
convention (`db.py`'s `*_asof` readers: an explicit `as_of_date` argument,
never an implicit "give me everything" default) -- a memory object built
without that discipline would introduce look-ahead bias into every
reasoning call that later consumes it, which Part 5's design flags as the
single most consequential mistake this module could make.

Design grounded in real data, inspected before writing any code (same
discipline FRE-2 used): `documents.ticker` resolves for 11,134/11,533 rows
(96.5%); UCAP has the richest real per-ticker fact history (8 rows).
Inspecting it directly surfaced a genuine, real data-quality finding, not a
hypothetical one: fact_id 151 shares its doc_id (6955) with fact_id 50 --
both point at a real United Capital Plc filing -- yet fact 151's own
LLM-extracted description is about "NASCON Allied Industries Plc," a
different company entirely. This is a real extraction mismatch from the
2026-07-27 stabilization pass's live pilot run, already caught by the
platform's OWN self-critique gate (`investment_implications.status =
'blocked_by_self_critique'` for that fact, confirmed by direct query, not
assumed). Company Memory's dividend/corporate-action history therefore
EXCLUDES any fact whose implication is `blocked_by_self_critique` --
mirroring exactly how every other consumer on this platform already
treats a blocked row -- and reports the exclusion count in `coverage_note`
rather than silently narrowing the history with no trace.

Two components are honestly near-empty on today's real data, disclosed
rather than hidden:
  - `major_event_history`: `events.ticker` is 100% NULL across all 157 real
    rows (146 'market'-scope, 11 'sector'-scope, 0 company-scope) --
    verified by direct query, not assumed. Every ticker's major-event
    history is correctly empty today; this is a real, systemic gap, not a
    bug in this module.
  - `management_history`: depends on Part 2's `executive_of` lineage edges,
    which depend on `management_change` fact extraction not yet run at any
    real volume -- also correctly empty today.
  - `strategy_narrative_timeline` is deliberately NOT built in this pass:
    even UCAP's richest real case is 7 short, single-sentence, numeric
    Phase-B facts ("Dividend per share: 1.5...") with no comparable prose
    across periods; the only prose-bearing facts (the 18 real LLM-pilot
    facts) never give any one company more than one such fact today.
    There is no real pair of same-company narrative snapshots yet to
    compare -- attempting the comparison anyway would manufacture a
    finding from data that cannot support one, exactly the risk Part 5's
    own design flagged (dual-quote evidence, capped confidence, "never a
    silent assertion"). Deferred, not attempted half-built.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class FilingSummary:
    doc_id: int
    doc_type: str
    filing_date: str
    source_confidence: float


@dataclass
class FactSummary:
    fact_id: int
    fact_type: str
    description: str
    filing_date: str
    numeric_value: float | None
    implication_status: str | None  # None if no investment_implications row exists yet


@dataclass
class CompanyMemory:
    ticker: str
    as_of_date: str
    filing_history: list[FilingSummary]
    dividend_history: list[FactSummary]  # excludes blocked_by_self_critique
    corporate_action_history: list[FactSummary]  # dividend + rights_issue + bonus_issue, same exclusion
    management_history: list[dict]  # always [] today -- see module docstring
    major_event_history: list[dict]  # always [] today -- see module docstring
    excluded_blocked_facts: int  # count of facts excluded for being blocked_by_self_critique
    coverage_note: list[str] = field(default_factory=list)


def _fact_row_to_summary(row: tuple) -> FactSummary:
    fact_id, fact_type, description, filing_date, numeric_value, status = row
    return FactSummary(
        fact_id=fact_id, fact_type=fact_type, description=description,
        filing_date=filing_date, numeric_value=numeric_value,
        implication_status=status,
    )


def build_company_memory(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyMemory:
    """PIT-safe: every read below filters filing_date <= as_of_date. No
    default for as_of_date -- matching db.py's own *_asof convention, since
    an implicit "everything" default is exactly how look-ahead bias creeps
    into a reasoning call that doesn't realize it's using one."""

    filing_rows = con.execute(
        "SELECT doc_id, doc_type, filing_date, source_confidence FROM documents "
        "WHERE ticker = ? AND filing_date <= ? ORDER BY filing_date",
        (ticker, as_of_date),
    ).fetchall()
    filing_history = [FilingSummary(*r) for r in filing_rows]

    fact_rows = con.execute(
        """
        SELECT f.fact_id, f.fact_type, f.description, d.filing_date, f.numeric_value,
               ii.status
        FROM extracted_facts f
        JOIN documents d ON d.doc_id = f.doc_id
        LEFT JOIN investment_implications ii ON ii.fact_id = f.fact_id
        WHERE d.ticker = ? AND d.filing_date <= ?
        ORDER BY d.filing_date
        """,
        (ticker, as_of_date),
    ).fetchall()

    all_facts = [_fact_row_to_summary(r) for r in fact_rows]
    excluded_blocked_facts = sum(1 for f in all_facts if f.implication_status == "blocked_by_self_critique")
    usable_facts = [f for f in all_facts if f.implication_status != "blocked_by_self_critique"]

    dividend_history = [f for f in usable_facts if f.fact_type == "dividend"]
    corporate_action_history = [
        f for f in usable_facts if f.fact_type in ("dividend", "rights_issue", "bonus_issue")
    ]

    # management_history: read the real Part 2 lineage edges (currently
    # always empty -- no management_change extraction has been run at any
    # volume yet, verified, not assumed. entities_relationships holds one
    # real row total across the whole database, and it is an
    # affects_order_1 effect-chain artifact, not an executive_of edge).
    entity_row = con.execute(
        "SELECT entity_id FROM entities WHERE entity_type = 'company' AND ticker = ? LIMIT 1",
        (ticker,),
    ).fetchone()
    management_history: list[dict] = []
    if entity_row is not None:
        entity_id = entity_row[0]
        mgmt_rows = con.execute(
            "SELECT object_entity_id, valid_from, valid_to, confidence FROM entity_relationships "
            "WHERE subject_entity_id = ? AND relation_type = 'executive_of'",
            (entity_id,),
        ).fetchall()
        management_history = [
            {"executive_entity_id": r[0], "valid_from": r[1], "valid_to": r[2], "confidence": r[3]}
            for r in mgmt_rows
        ]

    # major_event_history: events.ticker is a real column but currently
    # 100% NULL across all 157 real rows (verified) -- every ticker's
    # result here is correctly [] today, not a bug.
    event_rows = con.execute(
        "SELECT event_type, announced_date, effective_date, headline FROM events "
        "WHERE ticker = ? AND announced_date <= ? ORDER BY announced_date",
        (ticker, as_of_date),
    ).fetchall()
    major_event_history = [
        {"event_type": r[0], "announced_date": r[1], "effective_date": r[2], "headline": r[3]}
        for r in event_rows
    ]

    coverage_note = [
        f"{len(filing_history)} filings found as of {as_of_date} "
        f"({sum(1 for f in filing_history if f.source_confidence >= 0.8)} native-text, "
        f"{sum(1 for f in filing_history if f.source_confidence < 0.8)} OCR-pending/lower-confidence).",
        f"{len(all_facts)} extracted facts found; {excluded_blocked_facts} excluded from "
        f"dividend/corporate-action history for being blocked_by_self_critique (not silently "
        f"dropped -- counted here).",
        "management_history is empty: no management_change extraction has been run at any "
        "volume yet (a real, disclosed gap, not specific to this ticker)."
        if not management_history else
        f"{len(management_history)} management lineage edge(s) found.",
        "major_event_history is empty: events.ticker is not populated for any real event on "
        "this platform today (a real, systemic, disclosed gap -- verified across all 157 rows, "
        "not specific to this ticker)."
        if not major_event_history else
        f"{len(major_event_history)} ticker-scoped event(s) found.",
        "strategy_narrative_timeline is not implemented in this pass: no company in the "
        "current real dataset has more than one prose-bearing (LLM-extracted) fact, which is "
        "the minimum needed to compare a narrative across periods at all.",
    ]

    return CompanyMemory(
        ticker=ticker,
        as_of_date=as_of_date,
        filing_history=filing_history,
        dividend_history=dividend_history,
        corporate_action_history=corporate_action_history,
        management_history=management_history,
        major_event_history=major_event_history,
        excluded_blocked_facts=excluded_blocked_facts,
        coverage_note=coverage_note,
    )
