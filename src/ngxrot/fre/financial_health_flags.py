"""FSI Phase 3, Step 3: rule-based financial health flags
(docs/fre_runs/fsi_phase3_preregistration.md Area 3).

A small, fixed, named, disclosed rule set -- each rule is a plain,
auditable condition over Step 1 (ratio) / Step 2 (trend) conclusions
already written to `financial_reasoning_conclusions`. No free-text model
judgment enters this layer; every flag's trigger condition is stated in
code, in this one module, and is reproducible byte-for-byte on rerun.

Rules (illustrative starter set, per the pre-registration -- not
exhaustive, an execution-time decision, disclosed as such):

- `leverage_increasing`: the most recent debt_to_equity TREND is
  'increasing'.
- `cash_flow_earnings_divergence`: the most recent cfo_to_net_profit
  RATIO value is < 1.0 (net income exceeds operating cash generation --
  a named accounting-quality signal, not a valuation judgment).
- `margin_compression`: the most recent ebitda_margin or net_margin
  TREND is 'decreasing'.

Every rule mechanically emits `insufficient_data` (never silently
skipped) when its required underlying conclusion doesn't exist for a
ticker -- e.g. `cash_flow_earnings_divergence` is `insufficient_data`
for AFRIPRUD/CAP (no cfo ratio was ever computed for either).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ngxrot.fre.confidence_propagation import propagate_confidence_tier

RULE_VERSION = "flags_v1"


@dataclass
class FlagResult:
    ticker: str
    flag_name: str
    status: str  # 'computed' | 'insufficient_data'
    fired: bool | None
    triggering_value: float | None
    confidence_tier: str | None
    method: str
    limitations: str
    period_start: str | None = None
    period_end: str | None = None
    input_fact_ids: list[tuple[int, str]] = field(default_factory=list)


def _latest_conclusion(con: sqlite3.Connection, ticker: str, conclusion_type: str,
                        metric: str) -> tuple | None:
    """Most recent (by period_end) 'computed' conclusion for this
    ticker/type/metric, or None."""
    row = con.execute(
        "SELECT conclusion_id, value_numeric, value_text, confidence_tier, period_start, period_end "
        "FROM financial_reasoning_conclusions "
        "WHERE ticker = ? AND conclusion_type = ? AND metric = ? AND status = 'computed' "
        "ORDER BY period_end DESC LIMIT 1",
        (ticker, conclusion_type, metric),
    ).fetchone()
    return row


def _source_fact_ids(con: sqlite3.Connection, conclusion_id: int, via: str) -> list[tuple[int, str]]:
    rows = con.execute(
        "SELECT fact_id, role FROM financial_reasoning_conclusion_facts WHERE conclusion_id = ?",
        (conclusion_id,),
    ).fetchall()
    return [(fid, f"via_{via}_{role}") for fid, role in rows]


def _leverage_increasing(con: sqlite3.Connection, ticker: str) -> FlagResult:
    flag_name = "leverage_increasing"
    method = "fires if the most recent debt_to_equity TREND direction is 'increasing'"
    trend = _latest_conclusion(con, ticker, "trend", "debt_to_equity")
    if trend is None:
        return FlagResult(
            ticker=ticker, flag_name=flag_name, status="insufficient_data", fired=None,
            triggering_value=None, confidence_tier=None, method=method,
            limitations="No debt_to_equity trend exists for this ticker (fewer than 2 non-overlapping "
                        "periods with a computed debt_to_equity ratio).",
        )
    conclusion_id, value_numeric, value_text, tier, period_start, period_end = trend
    return FlagResult(
        ticker=ticker, flag_name=flag_name, status="computed", fired=(value_text == "increasing"),
        triggering_value=value_numeric, confidence_tier=tier, method=method,
        limitations=f"Based on the single most recent debt_to_equity trend pair "
                    f"({period_start}..{period_end}); does not consider earlier history.",
        period_start=period_start, period_end=period_end,
        input_fact_ids=_source_fact_ids(con, conclusion_id, "debt_to_equity_trend"),
    )


def _cash_flow_earnings_divergence(con: sqlite3.Connection, ticker: str) -> FlagResult:
    flag_name = "cash_flow_earnings_divergence"
    method = "fires if the most recent cfo_to_net_profit RATIO value is < 1.0"
    ratio = _latest_conclusion(con, ticker, "ratio", "cfo_to_net_profit")
    if ratio is None:
        return FlagResult(
            ticker=ticker, flag_name=flag_name, status="insufficient_data", fired=None,
            triggering_value=None, confidence_tier=None, method=method,
            limitations="No cfo_to_net_profit ratio was ever computed for this ticker "
                        "(cfo was never extracted for any of its real filings).",
        )
    conclusion_id, value_numeric, _, tier, period_start, period_end = ratio
    return FlagResult(
        ticker=ticker, flag_name=flag_name, status="computed", fired=(value_numeric < 1.0),
        triggering_value=value_numeric, confidence_tier=tier, method=method,
        limitations=f"Based on the single most recent period with both cfo and net_profit "
                    f"({period_start}..{period_end}); a one-period ratio, not a multi-period pattern.",
        period_start=period_start, period_end=period_end,
        input_fact_ids=_source_fact_ids(con, conclusion_id, "cfo_to_net_profit_ratio"),
    )


def _margin_compression(con: sqlite3.Connection, ticker: str) -> FlagResult:
    flag_name = "margin_compression"
    method = "fires if the most recent ebitda_margin OR net_margin TREND direction is 'decreasing'"
    ebitda_trend = _latest_conclusion(con, ticker, "trend", "ebitda_margin")
    net_trend = _latest_conclusion(con, ticker, "trend", "net_margin")
    if ebitda_trend is None and net_trend is None:
        return FlagResult(
            ticker=ticker, flag_name=flag_name, status="insufficient_data", fired=None,
            triggering_value=None, confidence_tier=None, method=method,
            limitations="Neither an ebitda_margin nor a net_margin trend exists for this ticker.",
        )
    available = [("ebitda_margin", ebitda_trend), ("net_margin", net_trend)]
    available = [(name, t) for name, t in available if t is not None]
    fired = any(t[2] == "decreasing" for _, t in available)
    tiers = [t[3] for _, t in available]
    input_fact_ids: list[tuple[int, str]] = []
    period_start = period_end = None
    for name, t in available:
        conclusion_id, value_numeric, value_text, tier, ps, pe = t
        input_fact_ids.extend(_source_fact_ids(con, conclusion_id, f"{name}_trend"))
        if period_end is None or pe > period_end:
            period_start, period_end = ps, pe
    missing_note = "" if len(available) == 2 else (
        f" NOTE: only {available[0][0]} trend was available; the other margin's trend did not exist "
        f"for this ticker -- this flag's evaluation is based on partial margin coverage."
    )
    return FlagResult(
        ticker=ticker, flag_name=flag_name, status="computed", fired=fired,
        triggering_value=None, confidence_tier=propagate_confidence_tier(tiers), method=method,
        limitations="Based on the single most recent trend pair per available margin, not a multi-period "
                    "pattern." + missing_note,
        period_start=period_start, period_end=period_end,
        input_fact_ids=input_fact_ids,
    )


_RULES = (_leverage_increasing, _cash_flow_earnings_divergence, _margin_compression)


def compute_flags_for_ticker(con: sqlite3.Connection, ticker: str) -> list[FlagResult]:
    return [rule(con, ticker) for rule in _RULES]


def write_flag_results(con: sqlite3.Connection, results: list[FlagResult]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for r in results:
        value_text = None if r.fired is None else ("fired" if r.fired else "not_fired")
        cur = con.execute(
            "INSERT INTO financial_reasoning_conclusions "
            "(ticker, conclusion_type, metric, status, value_numeric, value_text, confidence_tier, "
            "method, limitations, rule_version, period_start, period_end, computed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.ticker, "flag", r.flag_name, r.status, r.triggering_value, value_text, r.confidence_tier,
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
