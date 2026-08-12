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
from datetime import datetime, timezone

from ngxrot.fre.confidence_propagation import propagate_confidence_tier
from ngxrot.fre.financial_ratios import RATIO_DEFINITIONS
from ngxrot.fre.period_normalization import periods_overlap

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


def _base_fact_points(con: sqlite3.Connection, ticker: str, fact_type: str) -> list[_Point]:
    rows = con.execute(
        "SELECT f.period_start, f.period_end, f.numeric_value, f.confidence_tier, f.fact_id "
        "FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type = ? AND f.numeric_value IS NOT NULL "
        "AND f.period_start IS NOT NULL AND f.period_end IS NOT NULL "
        "ORDER BY f.period_end",
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
