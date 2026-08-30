"""Phase 5: Performance Attribution + Lineage (2026-08-12, BUILD ASSIGNMENT).

Answers "why did the portfolio make or lose money" by ticker/sector/
signal/strategy/hypothesis/trade/period, and provides the exact backward
reconstruction the build assignment names as more important than a
dashboard: P&L -> Position -> Fill -> Order -> Signal -> Hypothesis ->
(read-only) Research Run / Experiment in data/registry.sqlite.

registry.sqlite is READ-ONLY from this module -- no write ever touches it.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


def open_position_lifecycle(con: sqlite3.Connection, portfolio_id: str, ticker: str,
                            entry_fill_id: str, signal_id: str | None, hypothesis_id: str | None,
                            entry_date: str) -> str:
    """Called when a BUY fill opens a new position from flat. One
    lifecycle per flat->nonzero transition, matching performance.py's own
    single running-average-cost-lot simplification (disclosed, not a true
    multi-lot FIFO ledger)."""
    existing_open = con.execute(
        "SELECT position_lifecycle_id FROM position_lifecycles "
        "WHERE portfolio_id = ? AND ticker = ? AND exit_date IS NULL",
        (portfolio_id, ticker)).fetchone()
    if existing_open:
        return existing_open[0]  # already open -- an add-to-position, not a new lifecycle
    position_lifecycle_id = f"PL-{uuid.uuid4()}"
    con.execute(
        "INSERT INTO position_lifecycles (position_lifecycle_id, portfolio_id, ticker, signal_id, "
        "hypothesis_id, entry_fill_id, entry_date) VALUES (?,?,?,?,?,?,?)",
        (position_lifecycle_id, portfolio_id, ticker, signal_id, hypothesis_id, entry_fill_id, entry_date))
    con.commit()
    return position_lifecycle_id


def close_position_lifecycle(con: sqlite3.Connection, portfolio_id: str, ticker: str,
                             exit_fill_id: str, exit_date: str, realized_pnl: float,
                             total_cost: float, portfolio_total_pnl: float | None = None) -> str | None:
    """Closes the open lifecycle for (portfolio_id, ticker), if one
    exists. Returns the closed lifecycle_id, or None if nothing was open
    (a sell against no tracked lifecycle -- disclosed, not silently
    ignored, by the caller checking the None return)."""
    row = con.execute(
        "SELECT position_lifecycle_id, entry_date FROM position_lifecycles "
        "WHERE portfolio_id = ? AND ticker = ? AND exit_date IS NULL", (portfolio_id, ticker)).fetchone()
    if row is None:
        return None
    position_lifecycle_id, entry_date = row
    holding_days = (datetime.fromisoformat(exit_date) - datetime.fromisoformat(entry_date)).days
    contribution = (realized_pnl / portfolio_total_pnl) if portfolio_total_pnl else None
    con.execute(
        "UPDATE position_lifecycles SET exit_fill_id=?, exit_date=?, holding_period_days=?, "
        "realized_pnl=?, total_cost=?, contribution_to_portfolio=? WHERE position_lifecycle_id=?",
        (exit_fill_id, exit_date, holding_days, realized_pnl, total_cost, contribution,
         position_lifecycle_id))
    con.commit()
    return position_lifecycle_id


def compute_attribution(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                        portfolio_id: str, period_start: str, period_end: str) -> list[dict]:
    """Aggregates realized P&L (from CLOSED position_lifecycles within the
    period) by ticker, sector, signal, and hypothesis. Open (unclosed)
    lifecycles are NOT included -- only realized, attributable outcomes;
    unrealized mark-to-market attribution would need positions' own
    per-date history, out of scope for this minimum build (disclosed, not
    silently approximated)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    closed = portfolio_con.execute(
        "SELECT ticker, signal_id, hypothesis_id, realized_pnl FROM position_lifecycles "
        "WHERE portfolio_id = ? AND exit_date IS NOT NULL "
        "AND exit_date BETWEEN ? AND ? AND realized_pnl IS NOT NULL",
        (portfolio_id, period_start, period_end)).fetchall()

    total_pnl = sum(r[3] for r in closed) or None
    records = []

    by_ticker: dict[str, float] = {}
    by_signal: dict[str, float] = {}
    by_hypothesis: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    for ticker, signal_id, hypothesis_id, pnl in closed:
        by_ticker[ticker] = by_ticker.get(ticker, 0.0) + pnl
        if signal_id:
            by_signal[signal_id] = by_signal.get(signal_id, 0.0) + pnl
        if hypothesis_id:
            by_hypothesis[hypothesis_id] = by_hypothesis.get(hypothesis_id, 0.0) + pnl
        sector = _sector_for(market_con, ticker)
        if sector:
            by_sector[sector] = by_sector.get(sector, 0.0) + pnl

    for dimension, agg in (("ticker", by_ticker), ("signal", by_signal),
                          ("hypothesis", by_hypothesis), ("sector", by_sector)):
        for value, pnl in agg.items():
            contribution_pct = pnl / total_pnl if total_pnl else None
            attribution_id = f"ATTR-{uuid.uuid4()}"
            portfolio_con.execute(
                "INSERT INTO attribution_records (attribution_id, portfolio_id, period_start, "
                "period_end, dimension, dimension_value, pnl, contribution_pct, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (attribution_id, portfolio_id, period_start, period_end, dimension, str(value),
                 pnl, contribution_pct, now))
            records.append({"dimension": dimension, "dimension_value": value, "pnl": pnl,
                            "contribution_pct": contribution_pct})
    portfolio_con.commit()
    return records


def _sector_for(market_con: sqlite3.Connection, ticker: str) -> str | None:
    row = market_con.execute("SELECT sector_ngx FROM securities WHERE ticker = ?", (ticker,)).fetchone()
    return row[0] if row and row[0] else None


def reconstruct_lineage(portfolio_con: sqlite3.Connection, registry_con: sqlite3.Connection | None,
                        position_lifecycle_id: str) -> dict:
    """The exact backward reconstruction the build assignment names as
    more important than a dashboard: P&L -> Position (lifecycle) -> Fill
    -> Order -> Signal -> Hypothesis -> (read-only) Research Run/
    Experiment in data/registry.sqlite. `registry_con` is optional --
    pass None to stop the chain at hypothesis_id (still a complete,
    verifiable chain within data/portfolio.sqlite alone)."""
    pl = portfolio_con.execute(
        "SELECT portfolio_id, ticker, signal_id, hypothesis_id, entry_fill_id, exit_fill_id, "
        "realized_pnl, total_cost, contribution_to_portfolio FROM position_lifecycles "
        "WHERE position_lifecycle_id = ?", (position_lifecycle_id,)).fetchone()
    if pl is None:
        raise ValueError(f"unknown position_lifecycle_id {position_lifecycle_id!r}")
    portfolio_id, ticker, signal_id, hypothesis_id, entry_fill_id, exit_fill_id, pnl, cost, contrib = pl

    chain: dict = {"position_lifecycle_id": position_lifecycle_id, "ticker": ticker,
                   "realized_pnl": pnl, "total_cost": cost, "contribution_to_portfolio": contrib}

    for label, fill_id in (("entry", entry_fill_id), ("exit", exit_fill_id)):
        if not fill_id:
            chain[f"{label}_fill"] = None
            continue
        fill = portfolio_con.execute(
            "SELECT order_id, fill_date, fill_price, quantity, commission, transaction_cost_total "
            "FROM fills WHERE fill_id = ?", (fill_id,)).fetchone()
        order_id, fill_date, fill_price, qty, commission, txn_cost = fill
        order = portfolio_con.execute(
            "SELECT ticker, side, order_type, signal_timestamp, allocation_decision_id FROM orders "
            "WHERE order_id = ?", (order_id,)).fetchone()
        chain[f"{label}_fill"] = {
            "fill_id": fill_id, "order_id": order_id, "fill_date": fill_date,
            "fill_price": fill_price, "quantity": qty, "commission": commission,
            "transaction_cost_total": txn_cost,
            "order": {"ticker": order[0], "side": order[1], "order_type": order[2],
                     "signal_timestamp": order[3], "allocation_decision_id": order[4]},
        }

    if signal_id:
        sig = portfolio_con.execute(
            "SELECT as_of, instrument, action, rationale, hypothesis_id, experiment_ids_json "
            "FROM signals WHERE signal_id = ?", (signal_id,)).fetchone()
        if sig:
            chain["signal"] = {"signal_id": signal_id, "as_of": sig[0], "instrument": sig[1],
                               "action": sig[2], "rationale": sig[3], "hypothesis_id": sig[4],
                               "experiment_ids": json.loads(sig[5]) if sig[5] else []}

    chain["hypothesis_id"] = hypothesis_id
    if hypothesis_id and registry_con is not None:
        hyp = registry_con.execute(
            "SELECT description, status, conclusion FROM hypotheses WHERE hypothesis_id = ?",
            (hypothesis_id,)).fetchone()
        if hyp:
            chain["hypothesis"] = {"hypothesis_id": hypothesis_id, "description": hyp[0],
                                   "status": hyp[1], "conclusion": hyp[2]}
        experiments = registry_con.execute(
            "SELECT e.experiment_id, e.stage, e.created_at FROM hypothesis_experiments he "
            "JOIN experiments e ON e.experiment_id = he.experiment_id "
            "WHERE he.hypothesis_id = ?", (hypothesis_id,)).fetchall()
        chain["experiments"] = [{"experiment_id": e[0], "stage": e[1], "created_at": e[2]}
                                for e in experiments]

    return chain
