"""FSI Phase 3, Step 4: evidence-linked reasoning context
(docs/fre_runs/fsi_phase3_preregistration.md Area 4).

Read-only. For any `financial_reasoning_conclusions` row, assembles the
full, structured evidence trail behind it: every linked `extracted_facts`
row (via `financial_reasoning_conclusion_facts`), each fact's own
`evidence` row (quoted filing text, page number) where one exists, and
the source `documents` row (ticker, filing_date, doc_type). This is
explanatory ASSEMBLY of already-real, already-validated data -- it
generates no new text, makes no new claim, and calls no LLM. The
optional narrative ("why") layer named in the pre-registration's Area 4
is a SEPARATE, not-yet-authorized capability; this module is the
non-generative half of that area, and is the only half built in this
pass.

SAFETY: every function here is read-only; none writes to any table.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class SourceFactContext:
    fact_id: int
    role: str
    fact_type: str
    numeric_value: float | None
    description: str
    period_start: str | None
    period_end: str | None
    confidence_tier: str | None
    doc_id: int
    ticker: str | None
    filing_date: str
    doc_type: str
    quoted_text: str | None
    page_number: int | None


@dataclass
class ReasoningContext:
    conclusion_id: int
    ticker: str
    conclusion_type: str
    metric: str
    status: str
    value_numeric: float | None
    value_text: str | None
    confidence_tier: str | None
    method: str
    limitations: str
    rule_version: str
    period_start: str | None
    period_end: str | None
    source_facts: list[SourceFactContext]


def get_reasoning_context(con: sqlite3.Connection, conclusion_id: int) -> ReasoningContext | None:
    row = con.execute(
        "SELECT conclusion_id, ticker, conclusion_type, metric, status, value_numeric, value_text, "
        "confidence_tier, method, limitations, rule_version, period_start, period_end "
        "FROM financial_reasoning_conclusions WHERE conclusion_id = ?",
        (conclusion_id,),
    ).fetchone()
    if row is None:
        return None
    (cid, ticker, ctype, metric, status, value_numeric, value_text, confidence_tier,
     method, limitations, rule_version, period_start, period_end) = row

    fact_rows = con.execute(
        "SELECT fc.fact_id, fc.role, f.fact_type, f.numeric_value, f.description, "
        "f.period_start, f.period_end, f.confidence_tier, f.doc_id, "
        "d.ticker, d.filing_date, d.doc_type, e.quoted_text, e.page_number "
        "FROM financial_reasoning_conclusion_facts fc "
        "JOIN extracted_facts f ON f.fact_id = fc.fact_id "
        "JOIN documents d ON d.doc_id = f.doc_id "
        "LEFT JOIN evidence e ON e.evidence_id = f.evidence_id "
        "WHERE fc.conclusion_id = ? ORDER BY fc.fact_id, fc.role",
        (conclusion_id,),
    ).fetchall()

    source_facts = [
        SourceFactContext(
            fact_id=r[0], role=r[1], fact_type=r[2], numeric_value=r[3], description=r[4],
            period_start=r[5], period_end=r[6], confidence_tier=r[7], doc_id=r[8],
            ticker=r[9], filing_date=r[10], doc_type=r[11], quoted_text=r[12], page_number=r[13],
        )
        for r in fact_rows
    ]

    return ReasoningContext(
        conclusion_id=cid, ticker=ticker, conclusion_type=ctype, metric=metric, status=status,
        value_numeric=value_numeric, value_text=value_text, confidence_tier=confidence_tier,
        method=method, limitations=limitations, rule_version=rule_version,
        period_start=period_start, period_end=period_end, source_facts=source_facts,
    )


def get_reasoning_contexts_for_ticker(
    con: sqlite3.Connection, ticker: str, conclusion_type: str | None = None,
) -> list[ReasoningContext]:
    """All reasoning contexts for a SINGLE ticker. Deliberately single-
    ticker-scoped -- per the pre-registration's Area 7 guardrail, this
    module has no function that accepts more than one ticker or returns
    any cross-ticker comparative field."""
    query = "SELECT conclusion_id FROM financial_reasoning_conclusions WHERE ticker = ?"
    params: list = [ticker]
    if conclusion_type is not None:
        query += " AND conclusion_type = ?"
        params.append(conclusion_type)
    query += " ORDER BY conclusion_id"
    ids = [r[0] for r in con.execute(query, params).fetchall()]
    return [get_reasoning_context(con, cid) for cid in ids]
