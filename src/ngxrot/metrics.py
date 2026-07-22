"""Performance metrics for a BacktestResult.

Sharpe uses a configurable annual risk-free rate. Default 0.0 is WRONG for
Nigeria (NGN T-bill yields have ranged roughly 4-25%+): a naira strategy
earning 20% when T-bills pay 20% has created nothing. Configs should set
validation.risk_free_annual_pct; the default exists only so plumbing runs
work, and the metric name says what was used.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import stats

TRADING_DAYS = 252


def _ann_return(r: pd.Series) -> float:
    if len(r) == 0:
        return float("nan")
    growth = float((1 + r).prod())
    return growth ** (TRADING_DAYS / len(r)) - 1


def _max_drawdown(r: pd.Series) -> float:
    nav = (1 + r).cumprod()
    return float((nav / nav.cummax() - 1).min())


def compute(result, rf_annual_pct: float = 0.0) -> dict:
    r = result.net_returns
    years = len(r) / TRADING_DAYS
    ann = _ann_return(r)
    vol = float(r.std() * np.sqrt(TRADING_DAYS))
    rf = rf_annual_pct / 100.0
    bench_ann = _ann_return(result.benchmark_returns)

    # hit rate: holding periods (execution date to next) beating the benchmark
    execs = list(result.weights.index)
    hits = total = 0
    for a, b in zip(execs, execs[1:] + [r.index[-1]]):
        seg, bseg = r.loc[a:b], result.benchmark_returns.loc[a:b]
        if len(seg) < 2:
            continue
        total += 1
        hits += int((1 + seg).prod() > (1 + bseg).prod())

    return {
        "ann_return": round(ann, 4),
        "ann_return_benchmark": round(bench_ann, 4),
        "excess_return_ann": round(ann - bench_ann, 4),
        "ann_vol": round(vol, 4),
        "sharpe_vs_rf": round((ann - rf) / vol, 3) if vol > 0 else None,
        "rf_annual_pct_used": rf_annual_pct,
        "max_drawdown": round(_max_drawdown(r), 4),
        "hit_rate_vs_benchmark": round(hits / total, 3) if total else None,
        "n_rebalances": len(execs),
        "avg_oneway_turnover_per_rebalance": round(float(result.turnover.mean()), 4)
            if len(result.turnover) else 0.0,
        "ann_turnover_oneway": round(float(result.turnover.sum()) / years, 3),
        "ann_cost_drag": round(float(result.costs.sum()) / years, 4),
        "gross_ann_return": round(_ann_return(result.gross_returns), 4),
        "period_days": len(r),
        "excess_ttest": stats.excess_ttest(r, result.benchmark_returns),
    }
