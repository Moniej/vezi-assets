"""Stage 1 / A-3 — corporate-action (bonus/scrip/rights) exposure audit.

Generic, reusable diagnostic: given any hypothesis's own ``targets`` dict
(the exact {execution_date: Series(weights)} its scoring pipeline already
produces — unmodified, never rebuilt here), find real unexplained-jump
diagnostic flags (``data_quality_log``, check_name='unexplained_jump')
that fall inside a period the hypothesis actually HELD that ticker. This
answers a narrower, more useful question than "does an adjustment
mechanism exist" (it does not, platform-wide, per
docs/METHODOLOGY_HARDENING_2026-08-04.md) — it answers "is THIS
hypothesis's own realized return series actually touched by the gap."

Does not adjust any price. Does not fabricate a ratio. Detection only.
"""

from __future__ import annotations

import pandas as pd


def holding_periods_from_targets(targets: dict, sim_end: str) -> dict[str, list[tuple]]:
    """{ticker -> [(execution_date, next_execution_date_or_sim_end), ...]}
    from a hypothesis's own targets dict, unmodified. A ticker is
    considered HELD for the whole interval between the execution date it
    enters a target and the next execution date (whether or not it is
    still selected then) — mirrors how backtest_xs.simulate marks
    positions to market daily between rebalances."""
    dates = sorted(targets)
    out: dict[str, list[tuple]] = {}
    for i, dt in enumerate(dates):
        end = dates[i + 1] if i + 1 < len(dates) else pd.Timestamp(sim_end)
        for tick in targets[dt].index:
            out.setdefault(tick, []).append((dt, end))
    return out


def unexplained_jump_exposure(con, holding_periods: dict[str, list[tuple]],
                              sim_start: str, sim_end: str) -> pd.DataFrame:
    """Real ``unexplained_jump`` data_quality_log rows whose (ticker,
    trade_date) falls inside one of this hypothesis's own holding
    intervals. Empty DataFrame = no detected overlap (not proof of
    absence — only as good as the underlying unexplained_jump diagnostic
    and the holding-period reconstruction)."""
    jumps = pd.read_sql(
        "SELECT DISTINCT entity_code AS ticker, trade_date FROM data_quality_log "
        "WHERE check_name = 'unexplained_jump' AND trade_date BETWEEN ? AND ?",
        con, params=(sim_start, sim_end))
    jumps["trade_date"] = pd.to_datetime(jumps.trade_date)
    hits = []
    for _, j in jumps.iterrows():
        for (s, e) in holding_periods.get(j.ticker, []):
            if s <= j.trade_date <= e:
                hits.append({"ticker": j.ticker, "jump_date": j.trade_date,
                            "holding_start": s, "holding_end": e})
    return pd.DataFrame(hits)
