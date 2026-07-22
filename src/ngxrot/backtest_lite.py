"""Phase 2 backtest engine ("lite"): index-level rotation with per-side costs.

Deliberately NOT the final engine. What it does honestly:
  - signal at month-end close, execution ``execution_lag_days`` trading days
    later (no trading at the close you just measured);
  - weights drift with returns between rebalances (turnover is measured
    against drifted weights, not stale targets);
  - buy/sell costs deducted from return on the execution day;
  - long-only, fully invested from the first rebalance onward.

What it does NOT do (Phase 3 scope — results must not be read as tradeable):
  - no ADTV/participation constraint, no market impact;
  - trades index levels directly, as if a frictionless sector basket existed;
  - price indices only — no dividends (flagged in every experiment record).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import signal as sig


@dataclass
class BacktestResult:
    net_returns: pd.Series          # daily, from first execution date
    gross_returns: pd.Series
    weights: pd.DataFrame           # target weights at each execution date
    turnover: pd.Series             # one-way turnover per rebalance (sum of buys)
    costs: pd.Series                # cost drag per rebalance (fraction of NAV)
    exclusions: dict = field(default_factory=dict)  # exec_date -> excluded sectors
    benchmark_returns: pd.Series | None = None
    sector_contribution: dict = field(default_factory=dict)  # cum gross by sector


def run(
    levels: pd.DataFrame,            # daily levels, universe columns only
    benchmark: pd.Series,            # daily benchmark levels
    scores: pd.DataFrame,            # month-end momentum scores (from signal.py)
    events: pd.DataFrame,            # PIT events frame (may be empty)
    *,
    top_n: int,
    construction: str,
    rebalance: str,                  # 'monthly' | 'quarterly'
    execution_lag_days: int,
    catalyst_filter: bool,
    impairment_window_months: int,
    buy_rate: float,
    sell_rate: float,
    sim_start: str,
    sim_end: str,
) -> BacktestResult:
    daily = levels.loc[sim_start:sim_end]
    if daily.empty:
        raise ValueError("no data in simulation window")
    R = daily.pct_change().fillna(0.0)
    dates = daily.index

    sig_dates = [d for d in scores.index if d in dates]
    if rebalance == "quarterly":
        sig_dates = sig_dates[::3]
    elif rebalance != "monthly":
        raise ValueError(f"unknown rebalance {rebalance!r}")

    # signal date -> execution date (lag in trading days); drop unexecutable
    targets: dict[pd.Timestamp, pd.Series] = {}
    exclusions: dict[str, list[str]] = {}
    pos = {d: i for i, d in enumerate(dates)}
    for sd in sig_dates:
        i = pos[sd] + execution_lag_days
        if i >= len(dates):
            continue
        excl = (sig.excluded_sectors(events, sd, impairment_window_months)
                if catalyst_filter else set())
        row = scores.loc[sd]
        targets[dates[i]] = sig.select_top_n(row, top_n, excl, construction)
        if excl:
            exclusions[str(dates[i].date())] = sorted(excl)

    if not targets:
        raise ValueError("no executable rebalances in window (lookback too long?)")
    first_exec = min(targets)

    w = pd.Series(0.0, index=daily.columns)
    net, gross, turn, cost_s, wrows = [], [], [], [], []
    contrib = dict.fromkeys(daily.columns, 0.0)
    for d in dates:
        if d < first_exec:
            continue
        r_gross = float((w * R.loc[d]).sum())
        for sec in daily.columns:
            contrib[sec] += float(w[sec] * R.loc[d, sec])
        # drift weights through today's returns
        w_drift = w * (1.0 + R.loc[d])
        tot = w_drift.sum()
        w_drift = w_drift / tot if tot > 0 else w * 0.0
        cost = 0.0
        if d in targets:
            tgt = targets[d]
            buys = float((tgt - w_drift).clip(lower=0).sum())
            sells = float((w_drift - tgt).clip(lower=0).sum())
            cost = buys * buy_rate + sells * sell_rate
            turn.append(pd.Series(buys, index=[d]))
            cost_s.append(pd.Series(cost, index=[d]))
            wrows.append(tgt.rename(d))
            w = tgt
        else:
            w = w_drift
        gross.append(r_gross)
        net.append(r_gross - cost)

    idx = dates[dates >= first_exec]
    bench = benchmark.loc[idx].pct_change().fillna(0.0)
    return BacktestResult(
        net_returns=pd.Series(net, index=idx),
        gross_returns=pd.Series(gross, index=idx),
        weights=pd.DataFrame(wrows),
        turnover=pd.concat(turn) if turn else pd.Series(dtype=float),
        costs=pd.concat(cost_s) if cost_s else pd.Series(dtype=float),
        exclusions=exclusions,
        benchmark_returns=bench,
        sector_contribution={k: round(v, 4) for k, v in contrib.items()},
    )
