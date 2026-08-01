"""FSI Phase 2 shared infrastructure: restatement conflict detection
(docs/fre_runs/fsi_phase2_execution_plan.md section 4.3).

Read-only: finds prior extracted_facts for the same ticker/fact_type/
REPORTING SPAN with a DIFFERENT value -- the direct, disclosed answer to
CAP's real, confirmed finding (docs/fre_runs/fsi_phase1_results.md):
CAP's FY2021 filing (doc 5911) stated its own FY2020 comparative revenue
as N8,876mn, which does not match doc 4508 (the actual FY2020 filing)'s
own originally-reported N8,737mn -- most likely a restatement following
CAP's 2021 merger with Portland Paints.

This function only DETECTS candidates; it never decides what to do with
them (the caller -- the extraction script -- decides whether to write a
new fact with `restates_fact_id` set, per the "no overwriting historical
values" constraint: the original row is NEVER updated or deleted, both
stand, append-only, exactly like `investment_implications.contradicts_
implication_id`'s existing pattern on this platform).

ARCHITECTURAL CORRECTION (docs/fre_runs/fsi_phase2_implementation_log.md
Entry 4/5): the ORIGINAL rule matched on any OVERLAPPING period rather
than an EQUIVALENT one. This produced false positives on legitimate
nested reporting periods -- e.g. NASCON's H1 2024 filing (period
2024-01-01..2024-06-30) and its own later FY2024 filing (period
2024-01-01..2024-12-31) legitimately overlap and legitimately differ
(a half-year cash/balance figure is not the same quantity as a
full-year one), yet the old rule flagged the FY2024 fact as
"restating" the H1 2024 fact, which is false -- these are two
different reporting granularities of the same real year, not a
restatement of the same fact.

A genuine restatement, by definition, is the SAME reporting period
reported again with a different value (CAP's case: two different
filings, each independently reporting FY2020, disagreeing on the
number). Cumulative/nested reporting (a company's own interim filing
vs. its own later annual filing) is definitionally a DIFFERENT
reporting span, even though the calendar time overlaps. The corrected
rule therefore requires an EXACT match on both period_start AND
period_end -- "equivalent reporting spans" -- before two facts are
even considered candidates for a restatement relationship. This is the
minimal criterion that separates the two cases: it still catches CAP
(both the original and the comparative figure state the identical
FY2020 span) and no longer catches NASCON (H1 and FY spans are never
equal).

Note on Phase 2's own extraction convention: like Phase 1, Phase 2 only
extracts each filing's OWN reported period, never a filing's comparative
prior-period column restated inline -- so this mechanism is not expected
to fire naturally among Phase 2's own new facts (two DIFFERENT filings
each reporting their OWN period do not conflict unless that period is
identical). It exists as a safety net for any future phase that does
extract comparative columns, and is validated here against the real CAP
numbers on a disposable scratch fixture (never inserted into the
production database) AND against the real NASCON H1-vs-FY2024 data
(read directly from production, no fixture needed, since the legitimate
non-conflict is already real data on hand), per docs/fre_runs/
fsi_phase2_execution_plan.md's test plan.
"""
from __future__ import annotations

import sqlite3

_FLOAT_TOLERANCE = 1e-6


def find_restatement_conflicts(
    con: sqlite3.Connection,
    ticker: str,
    fact_type: str,
    period_start: str,
    period_end: str,
    new_value: float,
) -> list[int]:
    """Returns fact_ids of existing extracted_facts rows for the same
    ticker/fact_type whose reporting span is EXACTLY EQUAL to
    (period_start, period_end) -- not merely overlapping -- and whose
    numeric_value differs from new_value beyond a small float tolerance.
    An equal span is required, not just overlap, so that legitimate
    nested/cumulative reporting periods (e.g. a company's own H1 filing
    vs. its own later FY filing for the same year) are never mistaken
    for a restatement of the same fact. Read-only -- writes nothing."""
    rows = con.execute(
        """
        SELECT f.fact_id, f.numeric_value FROM extracted_facts f
        JOIN documents d ON d.doc_id = f.doc_id
        WHERE d.ticker = ? AND f.fact_type = ?
          AND f.period_start = ? AND f.period_end = ?
        """,
        (ticker, fact_type, period_start, period_end),
    ).fetchall()
    return [
        fact_id for fact_id, existing_value in rows
        if existing_value is not None and abs(existing_value - new_value) > _FLOAT_TOLERANCE
    ]
