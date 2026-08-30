"""Phase 4: Performance / NAV Engine (2026-08-12, BUILD ASSIGNMENT).

Computes portfolio-level performance from actual simulated fills only --
never from a proposed/unfilled target. track_record_status is ALWAYS one
of BACKTEST_ONLY / PAPER; this module never writes 'LIVE' (the schema
allows it as a legal future value, but no code path here reaches it --
per the hard constraint "do not connect real money").

Benchmark comparison is opt-in and explicit: pass benchmark_id=None
(default) to skip it entirely rather than silently assuming one. NGXASI
is an available OPTION in this platform's index_levels table, not a
default this module chooses on the caller's behalf.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

TRACK_RECORD_STATUSES = ("BACKTEST_ONLY", "PAPER", "LIVE")  # 'LIVE' never written by this module


def apply_fill_to_position(con: sqlite3.Connection, portfolio_id: str, ticker: str, side: str,
                           fill_price: float, quantity: float, as_of: str) -> None:
    """Updates (or creates) the positions row for (portfolio_id, ticker,
    as_of) from a single fill. Weighted-average cost on a BUY; realized
    P&L booked on a SELL (FIFO-equivalent since this is a single running
    average-cost lot, not a queue of individual lots -- disclosed
    simplification, matching the "do not fabricate what isn't modeled"
    rule: a true FIFO/LIFO lot-level accounting is not built)."""
    prior = con.execute(
        "SELECT quantity, average_cost, realized_pnl FROM positions "
        "WHERE portfolio_id = ? AND ticker = ? ORDER BY as_of DESC LIMIT 1",
        (portfolio_id, ticker)).fetchone()
    prior_qty, prior_avg_cost, prior_realized = prior if prior else (0.0, 0.0, 0.0)

    if side == "BUY":
        new_qty = prior_qty + quantity
        new_avg_cost = ((prior_qty * prior_avg_cost) + (quantity * fill_price)) / new_qty if new_qty else 0.0
        realized_pnl = prior_realized
    else:  # SELL
        new_qty = prior_qty - quantity
        new_avg_cost = prior_avg_cost  # unchanged by a sell
        realized_pnl = prior_realized + quantity * (fill_price - prior_avg_cost)

    market_value = new_qty * fill_price
    unrealized_pnl = new_qty * (fill_price - new_avg_cost) if new_qty else 0.0
    con.execute(
        "INSERT OR REPLACE INTO positions (portfolio_id, ticker, as_of, quantity, average_cost, "
        "market_value, weight, unrealized_pnl, realized_pnl) VALUES (?,?,?,?,?,?,?,?,?)",
        (portfolio_id, ticker, as_of, new_qty, new_avg_cost, market_value, 0.0,
         unrealized_pnl, realized_pnl))
    con.commit()


def mark_to_market(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                   portfolio_id: str, as_of: str) -> None:
    """Reprices every held position to `as_of`'s latest known price
    (PIT-safe) and recomputes weight/unrealized_pnl -- called once per
    valuation date, independent of whether a fill happened that day (a
    held position's mark-to-market value changes even with zero trading)."""
    from .. import db as _db
    rows = portfolio_con.execute(
        "SELECT DISTINCT ticker FROM positions WHERE portfolio_id = ?", (portfolio_id,)).fetchall()
    tickers = [r[0] for r in rows]
    if not tickers:
        return
    latest = {}
    for t in tickers:
        current = portfolio_con.execute(
            "SELECT quantity, average_cost, realized_pnl FROM positions "
            "WHERE portfolio_id = ? AND ticker = ? ORDER BY as_of DESC LIMIT 1",
            (portfolio_id, t)).fetchone()
        latest[t] = current

    total_mv = 0.0
    marks = {}
    for t, (qty, avg_cost, realized) in latest.items():
        if qty == 0:
            continue
        px = _db.equity_prices_asof(market_con, as_of, tickers=[t], min_confidence=0.9)
        if px.empty:
            continue  # no price available -- last known value carried forward implicitly (row not rewritten)
        price = float(px.sort_values("trade_date").iloc[-1].close)
        mv = qty * price
        total_mv += mv
        marks[t] = (qty, avg_cost, mv, qty * (price - avg_cost), realized)

    for t, (qty, avg_cost, mv, upnl, realized) in marks.items():
        weight = mv / total_mv if total_mv else 0.0
        portfolio_con.execute(
            "INSERT OR REPLACE INTO positions (portfolio_id, ticker, as_of, quantity, average_cost, "
            "market_value, weight, unrealized_pnl, realized_pnl) VALUES (?,?,?,?,?,?,?,?,?)",
            (portfolio_id, t, as_of, qty, avg_cost, mv, weight, upnl, realized))
    portfolio_con.commit()


def record_nav(con: sqlite3.Connection, portfolio_id: str, as_of: str, cash: float,
               track_record_status: str = "PAPER") -> float:
    if track_record_status == "LIVE":
        raise ValueError("this build never writes track_record_status='LIVE' -- "
                         "no real capital is connected (hard constraint)")
    positions_value = con.execute(
        "SELECT COALESCE(SUM(market_value), 0) FROM positions p "
        "WHERE portfolio_id = ? AND as_of = (SELECT MAX(as_of) FROM positions p2 "
        "WHERE p2.portfolio_id = p.portfolio_id AND p2.ticker = p.ticker AND p2.as_of <= ?)",
        (portfolio_id, as_of)).fetchone()[0]
    nav = cash + positions_value
    con.execute(
        "INSERT OR REPLACE INTO nav_snapshots (portfolio_id, as_of, cash, positions_value, nav, "
        "track_record_status) VALUES (?,?,?,?,?,?)",
        (portfolio_id, as_of, cash, positions_value, nav, track_record_status))
    con.commit()
    return nav


@dataclass(frozen=True)
class PerformanceSummary:
    as_of: str
    track_record_status: str
    daily_return: float | None
    cumulative_return: float | None
    cagr: float | None
    volatility_ann: float | None
    max_drawdown: float | None
    sharpe: float | None
    sortino: float | None
    turnover: float | None
    transaction_costs_cum: float | None
    number_of_trades_cum: int
    win_rate: float | None
    benchmark_id: str | None
    benchmark_cumulative_return: float | None


def compute_performance(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                        portfolio_id: str, risk_free_ann: float = 0.0,
                        benchmark_id: str | None = None) -> PerformanceSummary:
    """Computes and persists a performance_records row for the LATEST
    nav_snapshots date on record. Sharpe/Sortino/volatility are computed
    only when the return series has at least 2 points; with fewer, the
    fields are left None rather than reporting a statistically meaningless
    number from a single observation."""
    import pandas as pd

    nav_rows = portfolio_con.execute(
        "SELECT as_of, nav, track_record_status FROM nav_snapshots "
        "WHERE portfolio_id = ? ORDER BY as_of", (portfolio_id,)).fetchall()
    if not nav_rows:
        raise ValueError(f"no nav_snapshots recorded for portfolio {portfolio_id!r} yet")

    df = pd.DataFrame(nav_rows, columns=["as_of", "nav", "track_record_status"])
    df["daily_return"] = df["nav"].pct_change()
    df["cumulative_return"] = df["nav"] / df["nav"].iloc[0] - 1.0

    latest = df.iloc[-1]
    n_days = len(df)
    returns = df["daily_return"].dropna()

    volatility_ann = float(returns.std() * math.sqrt(252)) if len(returns) >= 2 else None
    downside = returns[returns < 0]
    sortino = None
    sharpe = None
    if len(returns) >= 2 and returns.std() > 0:
        excess = returns.mean() * 252 - risk_free_ann
        sharpe = float(excess / volatility_ann) if volatility_ann else None
        if len(downside) >= 2 and downside.std() > 0:
            sortino = float(excess / (downside.std() * math.sqrt(252)))

    running_max = df["nav"].cummax()
    drawdown_series = (df["nav"] - running_max) / running_max
    max_drawdown = float(drawdown_series.min())

    span_days = (pd.Timestamp(latest["as_of"]) - pd.Timestamp(df.iloc[0]["as_of"])).days
    cagr = None
    if span_days > 0 and latest["nav"] > 0 and df.iloc[0]["nav"] > 0:
        years = span_days / 365.25
        cagr = float((latest["nav"] / df.iloc[0]["nav"]) ** (1 / years) - 1) if years > 0 else None

    fills = portfolio_con.execute(
        "SELECT f.fill_price, f.quantity, f.transaction_cost_total, o.side FROM fills f "
        "JOIN orders o ON o.order_id = f.order_id WHERE o.portfolio_id = ?", (portfolio_id,)).fetchall()
    number_of_trades_cum = len(fills)
    transaction_costs_cum = sum(f[2] for f in fills) if fills else 0.0
    turnover = None
    if number_of_trades_cum and latest["nav"] > 0:
        traded_notional = sum(f[0] * f[1] for f in fills)
        turnover = float(traded_notional / latest["nav"])

    win_rate = _win_rate(portfolio_con, portfolio_id)

    benchmark_cum_return = None
    if benchmark_id is not None:
        benchmark_cum_return = _benchmark_return(market_con, benchmark_id, df.iloc[0]["as_of"], latest["as_of"])

    summary = PerformanceSummary(
        as_of=latest["as_of"], track_record_status=latest["track_record_status"],
        daily_return=float(latest["daily_return"]) if pd.notna(latest["daily_return"]) else None,
        cumulative_return=float(latest["cumulative_return"]), cagr=cagr,
        volatility_ann=volatility_ann, max_drawdown=max_drawdown, sharpe=sharpe, sortino=sortino,
        turnover=turnover, transaction_costs_cum=transaction_costs_cum,
        number_of_trades_cum=number_of_trades_cum, win_rate=win_rate,
        benchmark_id=benchmark_id, benchmark_cumulative_return=benchmark_cum_return)

    portfolio_con.execute(
        "INSERT OR REPLACE INTO performance_records (portfolio_id, as_of, track_record_status, "
        "daily_return, cumulative_return, cagr, volatility_ann, max_drawdown, sharpe, sortino, "
        "turnover, transaction_costs_cum, number_of_trades_cum, win_rate, benchmark_id, "
        "benchmark_cumulative_return) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (portfolio_id, summary.as_of, summary.track_record_status, summary.daily_return,
         summary.cumulative_return, summary.cagr, summary.volatility_ann, summary.max_drawdown,
         summary.sharpe, summary.sortino, summary.turnover, summary.transaction_costs_cum,
         summary.number_of_trades_cum, summary.win_rate, summary.benchmark_id,
         summary.benchmark_cumulative_return))
    portfolio_con.commit()
    return summary


def _win_rate(con: sqlite3.Connection, portfolio_id: str) -> float | None:
    rows = con.execute(
        "SELECT realized_pnl FROM position_lifecycles WHERE portfolio_id = ? AND exit_date IS NOT NULL",
        (portfolio_id,)).fetchall()
    closed = [r[0] for r in rows if r[0] is not None]
    if not closed:
        return None
    wins = sum(1 for pnl in closed if pnl > 0)
    return wins / len(closed)


def _benchmark_return(market_con: sqlite3.Connection, benchmark_id: str, start: str, end: str) -> float | None:
    from .. import db as _db
    levels = _db.index_levels_range(market_con, start, end, index_codes=[benchmark_id], min_confidence=0.9)
    if levels.empty or len(levels) < 2:
        return None
    levels = levels.sort_values("trade_date")
    first, last = levels.iloc[0].close_value, levels.iloc[-1].close_value
    return float(last / first - 1.0) if first else None
