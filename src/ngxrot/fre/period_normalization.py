"""FSI Phase 2 shared infrastructure: period-type classification
(docs/fre_runs/fsi_phase2_execution_plan.md section 4.3).

Classifies a fact's `period_type` from its ACTUAL `period_start`/
`period_end` span, never from a filing's own headline label -- the direct,
confirmed reason: UCAP's real FY2020 filing (doc 4248) headlined its
results "Q3 2020" while the underlying statement covered nine months
(2020-01-01 to 2020-09-30), a real, confirmed mislabeling
(docs/fre_runs/fsi_phase1_results.md). A classifier trusting the label
would have recorded this fact as a standalone quarter; classifying from
the calendar-month span catches it automatically, with zero dependence on
how the source document phrased its own headline.

Deliberately calendar-month-based, not day-count-based: raw day counts
for a quarter (90-92 days) and a half-year (181-184 days) vary enough
across leap years and calendar position that a pure day-count threshold
would be fragile. Matching on (start_month, end_month) is exact and
requires no tolerance band.
"""
from __future__ import annotations

from datetime import date

_MONTH_SPAN_TO_PERIOD_TYPE = {
    (1, 3): "Q1",
    (4, 6): "Q2",
    (7, 9): "Q3",
    (10, 12): "Q4",
    (1, 6): "H1",
    (7, 12): "H2",
    (1, 9): "9M",
    (1, 12): "FY",
}


def classify_period_type(period_start: str, period_end: str) -> str | None:
    """period_start/period_end are 'YYYY-MM-DD' strings (matching
    extracted_facts' existing column format). Returns one of
    'Q1'/'Q2'/'Q3'/'Q4'/'H1'/'H2'/'9M'/'FY', or None if the span does not
    match any standard NGX reporting period shape -- an unclassifiable
    span is left as None (unknown stays unknown), never guessed."""
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)
    if start.year != end.year:
        return None  # a standard NGX interim/annual period never spans a calendar year boundary
    return _MONTH_SPAN_TO_PERIOD_TYPE.get((start.month, end.month))


def periods_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """True if [start_a, end_a] and [start_b, end_b] share any calendar
    time. Added for FSI Phase 3 (docs/fre_runs/fsi_phase3_preregistration.md
    Area 2): trend classification must never compare two periods that
    overlap in calendar time but represent different reporting spans --
    e.g. NASCON's own real H1 2024 filing vs. its own later FY2024 filing
    (a half-year cumulative figure is not a data point on the same
    trajectory as a full-year figure for a year that contains it). This is
    the same overlap test `restatement_detection.py` used BEFORE its
    Entry-4/5 correction -- reused here deliberately, for the opposite
    purpose: restatement detection needed to stop treating overlap as
    sufficient evidence of a conflict; trend classification needs overlap
    as sufficient evidence to SKIP a pair, so two genuinely different
    reporting granularities of the same real year are never plotted as
    sequential points on one trend line."""
    a_start, a_end = date.fromisoformat(start_a), date.fromisoformat(end_a)
    b_start, b_end = date.fromisoformat(start_b), date.fromisoformat(end_b)
    return not (a_end < b_start or a_start > b_end)
