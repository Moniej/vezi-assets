"""FSI Phase 3, Step 2: trend classification
(docs/fre_runs/fsi_phase3_preregistration.md Area 2).

Classifies a ticker's own directional trajectory -- `increasing` /
`decreasing` / `stable` -- for a metric across two of its own real,
NON-OVERLAPPING reporting periods. Deliberately neutral vocabulary: this
module states the mechanical direction only, never "improving"/
"deteriorating", since whether a rising or falling number is favorable
depends on the metric (rising leverage and rising margin are not
symmetric) and is exactly the kind of judgment call this phase is not
authorized to make (docs/fre_runs/fsi_phase3_preregistration.md's
"Phase 3 states the mechanical direction only, and does NOT infer
whether a direction is favorable").

Only NON-OVERLAPPING period pairs are ever compared -- using
`period_normalization.periods_overlap()` -- so a half-year cumulative
figure is never plotted against a full-year figure for a year that
contains it (the real NASCON H1-2024-vs-FY2024 case). This is the same
lesson the restatement-detection fix encoded, reused here for a
different, complementary purpose: there, overlap was wrongly treated as
evidence of a conflict; here, overlap is correctly treated as evidence
that a pair is NOT a valid sequential trend comparison.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from ngxrot.fre.confidence_propagation import propagate_confidence_tier
from ngxrot.fre.financial_ratios import RATIO_DEFINITIONS
from ngxrot.fre.period_normalization import periods_overlap

# 2026-08-13, FRE scale-validation program (Gate 2): real, confirmed gap
# found investigating ELLAHLAKES's own irregular 17-month reporting
# period (period_start=2024-08-01, period_end=2025-12-31, period_type=
# None -- a genuine, company-disclosed transition period, NOT an
# extraction defect; validate_period() correctly preserved it rather than
# force-mapping to FY). periods_overlap() alone is NOT sufficient: two
# periods can be non-overlapping and still economically NOT comparable
# via a raw pct_change if their durations differ materially (a 17-month
# revenue figure vs. an adjacent 12-month figure is not apples-to-apples
# -- the percent change would be distorted by the span mismatch, not a
# real change in performance). This module does NOT annualize/normalize
# to make the comparison work (that would be a modeling assumption this
# phase is not authorized to make, same discipline as the module's own
# "states the mechanical direction only" rule) -- it refuses the
# comparison instead, preserving both underlying facts untouched.
_MAX_DURATION_RATIO = 1.20  # generous vs. real calendar variance between
                            # two genuine same-type periods (e.g. a 365-
                            # vs-366-day FY across a leap year is ~1.003;
                            # a 91-vs-92-day quarter is ~1.011) while still
                            # decisively catching a 17-month (~517d) vs a
                            # 12-month (~365d) mismatch (ratio ~1.42)


def _duration_days(period_start: str, period_end: str) -> int:
    return (date.fromisoformat(period_end) - date.fromisoformat(period_start)).days + 1


def _durations_comparable(earlier: "_Point", later: "_Point") -> bool:
    """False if the two periods' calendar SPANS differ enough that a raw
    pct_change between their values would be distorted by the span
    mismatch itself, not by a real change -- e.g. ELLAHLAKES's own
    17-month period vs. any adjacent standard-length period. Both points
    are guaranteed non-null period_start/period_end by _base_fact_points'
    own WHERE clause before this is ever called."""
    d1 = _duration_days(earlier.period_start, earlier.period_end)
    d2 = _duration_days(later.period_start, later.period_end)
    if d1 <= 0 or d2 <= 0:
        return False
    ratio = max(d1, d2) / min(d1, d2)
    return ratio <= _MAX_DURATION_RATIO

RULE_VERSION = "trend_v1"

# The 12 leaves of configs/fact_taxonomy.toml's [financial_statements] group.
BASE_FACT_TYPES = (
    "revenue", "net_profit", "assets", "liabilities", "equity",
    "cfo", "cfi", "cff", "capex", "fcf", "ebit", "ebitda",
)

STABLE_THRESHOLD_PCT = 5.0  # disclosed, reasoned choice -- not empirically validated


@dataclass
class _Point:
    period_start: str
    period_end: str
    value: float
    confidence_tier: str | None
    fact_ids: list[tuple[int, str]]  # (fact_id, role) contributing to this single point


@dataclass
class TrendResult:
    ticker: str
    metric: str
    status: str  # 'computed' | 'insufficient_data'
    period_start: str  # the LATER period's start/end
    period_end: str
    value_numeric: float | None  # percent change
    value_text: str | None       # 'increasing' | 'decreasing' | 'stable'
    confidence_tier: str | None
    method: str
    limitations: str
    input_fact_ids: list[tuple[int, str]] = field(default_factory=list)


def _has_tabular_unit_check_column(con: sqlite3.Connection) -> bool:
    """Same guard as financial_ratios.py's own copy -- production is
    deliberately frozen/unmigrated for this column during the FRE
    scale-validation program; degrade gracefully rather than raise."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(extracted_facts)").fetchall()}
    return "tabular_unit_check" in cols


def _base_fact_points(con: sqlite3.Connection, ticker: str, fact_type: str) -> list[_Point]:
    # 2026-08-13, FRE scale-validation program (Gate 2): this query reads
    # RAW facts directly, a SEPARATE path from financial_ratios._fact_for()
    # -- the tabular-unit-check quarantine fix there does NOT cover this
    # query. Found live during the Gate-2 investigation: without this
    # filter, a fact quarantined for a likely-unscaled table figure could
    # still feed a REVENUE/NET_PROFIT/etc. trend directly, bypassing the
    # ratio-side enforcement entirely.
    quarantine_filter = (" AND f.tabular_unit_check NOT IN ('flag','ambiguous')"
                        if _has_tabular_unit_check_column(con) else "")
    rows = con.execute(
        "SELECT f.period_start, f.period_end, f.numeric_value, f.confidence_tier, f.fact_id "
        "FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type = ? AND f.numeric_value IS NOT NULL "
        "AND f.period_start IS NOT NULL AND f.period_end IS NOT NULL"
        + quarantine_filter +
        " ORDER BY f.period_end",
        (ticker, fact_type),
    ).fetchall()
    return [_Point(ps, pe, val, tier, [(fid, "point_value")]) for ps, pe, val, tier, fid in rows]


def _ratio_points(con: sqlite3.Connection, ticker: str, metric: str) -> list[_Point]:
    rows = con.execute(
        "SELECT c.period_start, c.period_end, c.value_numeric, c.confidence_tier, c.conclusion_id "
        "FROM financial_reasoning_conclusions c "
        "WHERE c.ticker = ? AND c.conclusion_type = 'ratio' AND c.metric = ? AND c.status = 'computed' "
        "ORDER BY c.period_end",
        (ticker, metric),
    ).fetchall()
    points = []
    for ps, pe, val, tier, conclusion_id in rows:
        input_facts = con.execute(
            "SELECT fact_id, role FROM financial_reasoning_conclusion_facts WHERE conclusion_id = ?",
            (conclusion_id,),
        ).fetchall()
        points.append(_Point(ps, pe, val, tier, [(fid, role) for fid, role in input_facts]))
    return points


def _classify_pair(earlier: _Point, later: _Point, ticker: str, metric: str) -> TrendResult:
    method = (f"{metric} trend = pct_change(later={later.period_start}..{later.period_end}, "
              f"earlier={earlier.period_start}..{earlier.period_end}), "
              f"threshold=±{STABLE_THRESHOLD_PCT}% for 'stable'")
    input_fact_ids = (
        [(fid, f"earlier_period_{role}") for fid, role in earlier.fact_ids]
        + [(fid, f"later_period_{role}") for fid, role in later.fact_ids]
    )
    if earlier.value == 0:
        return TrendResult(
            ticker=ticker, metric=metric, status="insufficient_data",
            period_start=later.period_start, period_end=later.period_end,
            value_numeric=None, value_text=None, confidence_tier=None, method=method,
            limitations="Earlier period's value is exactly zero -- percent change is undefined.",
            input_fact_ids=input_fact_ids,
        )
    pct_change = (later.value - earlier.value) / abs(earlier.value) * 100.0
    if pct_change > STABLE_THRESHOLD_PCT:
        direction = "increasing"
    elif pct_change < -STABLE_THRESHOLD_PCT:
        direction = "decreasing"
    else:
        direction = "stable"
    tier = propagate_confidence_tier([earlier.confidence_tier, later.confidence_tier])
    limitations = (
        f"Based on exactly 2 real reporting periods ({earlier.period_start}..{earlier.period_end} vs "
        f"{later.period_start}..{later.period_end}) -- not a smoothed multi-point trend line. "
        + ("At least one period's underlying fact predates the confidence_tier column and was never "
           "backfilled -- this trend's confidence floor is unknown, not merely low. "
           if tier is None else "")
    )
    return TrendResult(
        ticker=ticker, metric=metric, status="computed",
        period_start=later.period_start, period_end=later.period_end,
        value_numeric=pct_change, value_text=direction, confidence_tier=tier, method=method,
        limitations=limitations, input_fact_ids=input_fact_ids,
    )


def _classify_points(points: list[_Point], ticker: str, metric: str) -> list[TrendResult]:
    results = []
    for i in range(len(points) - 1):
        earlier, later = points[i], points[i + 1]
        if periods_overlap(earlier.period_start, earlier.period_end, later.period_start, later.period_end):
            continue  # e.g. NASCON's own real H1 2024 vs FY2024 -- not a valid sequential pair
        if not _durations_comparable(earlier, later):
            # Real, disclosed non-comparability (e.g. a 17-month transition
            # period) -- both facts are preserved untouched; this pair is
            # simply never turned into a pct_change trend claim. Recorded
            # as insufficient_data (not silently dropped) so the gap is
            # visible, not invisible.
            input_fact_ids = (
                [(fid, f"earlier_period_{role}") for fid, role in earlier.fact_ids]
                + [(fid, f"later_period_{role}") for fid, role in later.fact_ids]
            )
            results.append(TrendResult(
                ticker=ticker, metric=metric, status="insufficient_data",
                period_start=later.period_start, period_end=later.period_end,
                value_numeric=None, value_text=None, confidence_tier=None,
                method=f"{metric} trend = pct_change(...) -- REFUSED",
                limitations=(
                    f"Periods {earlier.period_start}..{earlier.period_end} and "
                    f"{later.period_start}..{later.period_end} have materially "
                    f"different durations ({_duration_days(earlier.period_start, earlier.period_end)}d "
                    f"vs {_duration_days(later.period_start, later.period_end)}d) -- a raw percent "
                    f"change would be distorted by the span mismatch itself, not a real change. "
                    f"Not annualized/normalized (that would be an unstated modeling assumption); "
                    f"both underlying facts are preserved, this pair is simply not comparable."),
                input_fact_ids=input_fact_ids,
            ))
            continue
        results.append(_classify_pair(earlier, later, ticker, metric))
    return results


def classify_trends_for_ticker(con: sqlite3.Connection, ticker: str) -> list[TrendResult]:
    results: list[TrendResult] = []
    for fact_type in BASE_FACT_TYPES:
        results.extend(_classify_points(_base_fact_points(con, ticker, fact_type), ticker, fact_type))
    for metric in RATIO_DEFINITIONS:
        results.extend(_classify_points(_ratio_points(con, ticker, metric), ticker, metric))
    return results


def write_trend_results(con: sqlite3.Connection, results: list[TrendResult]) -> int:
    """Idempotent on rerun (fixed 2026-08-12, production-reliability audit --
    same fix and same reasoning as financial_ratios.write_ratio_results)."""
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for r in results:
        existing = con.execute(
            "SELECT conclusion_id FROM financial_reasoning_conclusions WHERE "
            "ticker=? AND conclusion_type='trend' AND metric=? AND "
            "period_start IS ? AND period_end IS ? AND rule_version=?",
            (r.ticker, r.metric, r.period_start, r.period_end, RULE_VERSION),
        ).fetchall()
        for (old_id,) in existing:
            con.execute("DELETE FROM financial_reasoning_conclusion_facts WHERE conclusion_id=?", (old_id,))
            con.execute("DELETE FROM financial_reasoning_conclusions WHERE conclusion_id=?", (old_id,))
        cur = con.execute(
            "INSERT INTO financial_reasoning_conclusions "
            "(ticker, conclusion_type, metric, status, value_numeric, value_text, confidence_tier, "
            "method, limitations, rule_version, period_start, period_end, computed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.ticker, "trend", r.metric, r.status, r.value_numeric, r.value_text, r.confidence_tier,
             r.method, r.limitations, RULE_VERSION, r.period_start, r.period_end, now),
        )
        conclusion_id = cur.lastrowid
        for fact_id, role in r.input_fact_ids:
            con.execute(
                "INSERT INTO financial_reasoning_conclusion_facts (conclusion_id, fact_id, role) "
                "VALUES (?,?,?)",
                (conclusion_id, fact_id, role),
            )
        written += 1
    return written
