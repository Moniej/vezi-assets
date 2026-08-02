"""FSI Phase 14: Evidence-Based Screening (docs/fre_runs/
fsi_phase14_preregistration.md). Implements Part 9's own Tier-1
"Screening" capability (docs/fre/09_portfolio_reasoning.md) -- the first
function in this program that legitimately operates across ALL tickers
at once, per that document's own explicit authorization: "descriptive
filtering over already-produced research, structurally identical to a
SQL WHERE clause... never computes or implies an expected return."

Both functions below iterate over every real ticker (`financial_ratios.
list_tickers()`) and reuse FSI Phase 4's `pit_financial_memory.as_of()`
per ticker -- PIT-safety is inherited from that frozen module, not
re-implemented here. Neither function is modified by, nor imports from,
`alpha_engine.py`/`runner.py`/any portfolio-construction module -- this
is verified mechanically in `scripts/fre/test_screening.py`, not just
asserted here.

Deliberate, load-bearing design restriction (see the pre-registration's
own Section 5): only CATEGORICAL filter values are accepted (a flag's
fired/not_fired boolean, or a trend's increasing/decreasing/stable
direction) -- never a numeric threshold on a ratio value. Results are
always returned in alphabetical-ticker order, never sorted by magnitude,
and no aggregate statistic is ever computed. This keeps the module
inside Part 9's own Tier-1 boundary (research/advisory filtering) and
away from Tier-2 (ranking/scoring/sizing), which remains gated exactly
as before.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.financial_ratios import RATIO_DEFINITIONS, list_tickers
from ngxrot.fre.pit_financial_memory import as_of as _pit_as_of
from ngxrot.fre.trend_classification import BASE_FACT_TYPES

# The 3 real flag names Phase 3's financial_health_flags.py computes --
# matching company_thesis_360.py's own private _CONCERN_FLAG_METRICS
# tuple exactly (that module's own list is not imported here since it is
# private to that module; both name the same 3 real rules independently).
KNOWN_FLAG_METRICS = ("leverage_increasing", "cash_flow_earnings_divergence", "margin_compression")

# Every metric Phase 3's trend_classification.py ever produces a trend
# for: the 12 base fact_type leaves plus the 5 Step-1 ratio metrics.
KNOWN_TREND_METRICS = tuple(BASE_FACT_TYPES) + tuple(RATIO_DEFINITIONS)

_VALID_DIRECTIONS = ("increasing", "decreasing", "stable")


@dataclass(frozen=True)
class ScreenMatch:
    """One ticker's matching conclusion. No score/rank/weight field --
    only the matched ticker and the existing conclusion's own fields,
    verbatim from `financial_reasoning_conclusions` via `pit_financial_
    memory.as_of()`. Field order here is documentation-only; result
    ORDER is governed by the caller, always alphabetical by ticker."""
    ticker: str
    conclusion_id: int
    metric: str
    value_text: str | None
    value_numeric: float | None
    confidence_tier: str | None
    method: str
    limitations: str
    period_start: str | None
    period_end: str | None
    knowable_as_of: str


def screen_by_flag(con: sqlite3.Connection, flag_metric: str, fired: bool, as_of_date: str) -> list[ScreenMatch]:
    """Every ticker whose named health flag is knowable, as of
    `as_of_date`, to have fired (or not fired). `flag_metric` must be one
    of KNOWN_FLAG_METRICS -- an unrecognized name raises, it is never
    silently treated as "no matches" (that would be indistinguishable
    from a real, correct negative result)."""
    if flag_metric not in KNOWN_FLAG_METRICS:
        raise ValueError(f"unrecognized flag_metric {flag_metric!r}; expected one of {KNOWN_FLAG_METRICS}")
    wanted_value_text = "fired" if fired else "not_fired"

    matches: list[ScreenMatch] = []
    for ticker in sorted(list_tickers(con)):
        snapshot = _pit_as_of(con, ticker, as_of_date)
        for c in snapshot.conclusions:
            if c.conclusion_type == "flag" and c.metric == flag_metric and c.status == "computed" \
                    and c.value_text == wanted_value_text:
                matches.append(ScreenMatch(
                    ticker=ticker, conclusion_id=c.conclusion_id, metric=c.metric,
                    value_text=c.value_text, value_numeric=c.value_numeric,
                    confidence_tier=c.confidence_tier, method=c.method, limitations=c.limitations,
                    period_start=c.period_start, period_end=c.period_end, knowable_as_of=c.knowable_as_of,
                ))
    return matches


def screen_by_trend(con: sqlite3.Connection, metric: str, direction: str, as_of_date: str) -> list[ScreenMatch]:
    """Every ticker whose named metric's most recent classified trend is
    knowable, as of `as_of_date`, to be in the given direction. `metric`
    must be one of KNOWN_TREND_METRICS; `direction` must be one of
    'increasing'/'decreasing'/'stable' -- either an unrecognized value
    raises, never silently returns an empty (indistinguishable from a
    real negative) result."""
    if metric not in KNOWN_TREND_METRICS:
        raise ValueError(f"unrecognized trend metric {metric!r}; expected one of {KNOWN_TREND_METRICS}")
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(f"unrecognized direction {direction!r}; expected one of {_VALID_DIRECTIONS}")

    matches: list[ScreenMatch] = []
    for ticker in sorted(list_tickers(con)):
        snapshot = _pit_as_of(con, ticker, as_of_date)
        for c in snapshot.conclusions:
            if c.conclusion_type == "trend" and c.metric == metric and c.status == "computed" \
                    and c.value_text == direction:
                matches.append(ScreenMatch(
                    ticker=ticker, conclusion_id=c.conclusion_id, metric=c.metric,
                    value_text=c.value_text, value_numeric=c.value_numeric,
                    confidence_tier=c.confidence_tier, method=c.method, limitations=c.limitations,
                    period_start=c.period_start, period_end=c.period_end, knowable_as_of=c.knowable_as_of,
                ))
    return matches
