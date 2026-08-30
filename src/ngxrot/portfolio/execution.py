"""Phase 3: Paper Execution Engine (2026-08-12, BUILD ASSIGNMENT).

NO BROKER INTEGRATION. NO REAL-MONEY EXECUTION. Simulates orders/fills
against real historical/current market data only.

NO LOOK-AHEAD: an order derived from a signal `as_of` date S is filled at
the NEXT trading session strictly after S, never at S's own close --
"signal at close -> buy at same close" is exactly the unrealistic
assumption the build assignment prohibits unless the data explicitly
supports it without look-ahead, and it does not (a signal generated as of
a date's close cannot itself be acted on before the market reopens).

Commission is NOT invented -- reuses ngxrot.costs.side_rates +
ngxrot.db.cost_schedule_asof, the SAME fee model engine_full.py itself
uses (unmodified, imported read-only). Slippage and market impact ARE
configurable assumptions, explicitly labeled as such on every fill's
`assumptions_note` -- this platform has no measured intraday execution
data to calibrate them from.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

ORDER_STATUSES = ("CREATED", "SUBMITTED", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED")


@dataclass(frozen=True)
class ExecutionAssumptions:
    """Every field here is a configured parameter, not a discovered or
    measured constant -- passed explicitly by the caller, never defaulted
    silently to something that looks realistic."""
    slippage_bps: float
    market_impact_bps: float
    brokerage_override_pct: float | None = None
    limit_fill_window_sessions: int = 5   # how many subsequent sessions a LIMIT order
                                          # is allowed to wait for a fillable price


@dataclass(frozen=True)
class FillResult:
    fill_id: str
    order_id: str
    fill_date: str
    fill_price: float
    quantity: float
    commission: float
    slippage_bps: float
    market_impact_bps: float
    transaction_cost_total: float


def create_order(con: sqlite3.Connection, portfolio_id: str, ticker: str, side: str,
                 order_type: str, quantity: float, signal_timestamp: str,
                 allocation_decision_id: str | None = None, target_position_id: str | None = None,
                 limit_price: float | None = None) -> str:
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    if order_type not in ("MARKET", "LIMIT"):
        raise ValueError(f"order_type must be MARKET or LIMIT, got {order_type!r}")
    if order_type == "LIMIT" and limit_price is None:
        raise ValueError("LIMIT order requires limit_price")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    order_id = f"O-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute(
        "INSERT INTO orders (order_id, portfolio_id, allocation_decision_id, target_position_id, "
        "ticker, side, order_type, quantity, limit_price, signal_timestamp, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (order_id, portfolio_id, allocation_decision_id, target_position_id, ticker, side,
         order_type, quantity, limit_price, signal_timestamp, "CREATED", now))
    con.commit()
    return order_id


def _next_sessions(market_con: sqlite3.Connection, ticker: str, after_date: str, n: int):
    """PIT-safe by construction: only ever called with dates that are
    already in the past relative to `market_con`'s current data, and only
    ever looks FORWARD from `after_date` (strictly >), matching what a
    real trader would have experienced -- this function is the one place
    in the whole layer where look-ahead would leak if it looked backward
    or included `after_date` itself, so it deliberately does neither."""
    from .. import db as _db
    rows = market_con.execute(
        "SELECT ep.trade_date, ep.open, ep.high, ep.low, ep.close, ep.confidence "
        "FROM equity_prices ep JOIN ("
        "  SELECT ticker, trade_date, MAX(as_of_date) AS max_asof FROM equity_prices "
        "  WHERE ticker = ? AND trade_date > ? AND confidence >= 0.9 GROUP BY ticker, trade_date"
        ") m ON ep.ticker = ? AND ep.trade_date = m.trade_date AND ep.as_of_date = m.max_asof "
        "ORDER BY ep.trade_date ASC LIMIT ?",
        (ticker, after_date, ticker, n)).fetchall()
    return rows


def simulate_fill(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                  order_id: str, assumptions: ExecutionAssumptions) -> FillResult | None:
    """Attempts to fill a CREATED order against real subsequent price data.
    Returns None (and marks the order REJECTED with a reason) if no
    executable price can be found -- never fabricates a fill."""
    row = portfolio_con.execute(
        "SELECT portfolio_id, ticker, side, order_type, quantity, limit_price, signal_timestamp, status "
        "FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown order_id {order_id!r}")
    portfolio_id, ticker, side, order_type, quantity, limit_price, signal_timestamp, status = row
    if status != "CREATED":
        raise ValueError(f"order {order_id} is not in CREATED state (currently {status!r})")

    portfolio_con.execute("UPDATE orders SET status='SUBMITTED' WHERE order_id=?", (order_id,))
    portfolio_con.commit()

    sessions = _next_sessions(market_con, ticker, signal_timestamp, assumptions.limit_fill_window_sessions)
    if not sessions:
        _reject(portfolio_con, order_id, f"no executable price session found after {signal_timestamp} "
                                        f"within {assumptions.limit_fill_window_sessions} sessions -- "
                                        f"not filled, not fabricated")
        return None

    if order_type == "MARKET":
        fill_date, o, h, l, close, conf = sessions[0]
        raw_price = close  # next-session close -- the documented assumption, see module docstring
    else:  # LIMIT
        raw_price = None
        fill_date = None
        conf = None
        for trade_date, o, h, l, close, c in sessions:
            if h is None or l is None:
                continue  # session has no usable high/low on record -- cannot judge
                          # fillability for it, skipped rather than crashing or guessing
            if (side == "BUY" and l <= limit_price) or (side == "SELL" and h >= limit_price):
                raw_price = limit_price  # filled at the limit, not a better price -- conservative
                fill_date = trade_date
                conf = c
                break
        if raw_price is None:
            # CANCELLED, not REJECTED -- a single terminal-state transition,
            # not two. The earlier version called _reject() (sets
            # status='REJECTED', itself a terminal state the orders_no_
            # update_terminal trigger then correctly locks) and THEN tried
            # to also set status='CANCELLED' on the same row -- a real bug
            # this module's own immutability trigger caught during testing
            # (a terminal order cannot be re-mutated, by design). One
            # UPDATE, one terminal state, matching the state machine
            # exactly: CANCELLED is what "timed out without a fill" means,
            # not REJECTED (which is for input validated as unfillable
            # up front, e.g. an unknown ticker).
            portfolio_con.execute(
                "UPDATE orders SET status='CANCELLED', rejection_reason=? WHERE order_id=?",
                (f"LIMIT price {limit_price} not reached within "
                 f"{assumptions.limit_fill_window_sessions} sessions after {signal_timestamp} "
                 f"-- CANCELLED, not fabricated", order_id))
            portfolio_con.commit()
            return None

    slip_mult = (1 + assumptions.slippage_bps / 1e4) if side == "BUY" else (1 - assumptions.slippage_bps / 1e4)
    impact_mult = (1 + assumptions.market_impact_bps / 1e4) if side == "BUY" else (1 - assumptions.market_impact_bps / 1e4)
    fill_price = raw_price * slip_mult * impact_mult

    commission = _commission(market_con, fill_date, side, fill_price, quantity, assumptions)
    slippage_cost = abs(fill_price - raw_price * impact_mult) * quantity
    impact_cost = abs(raw_price * impact_mult - raw_price) * quantity
    transaction_cost_total = commission + slippage_cost + impact_cost

    fill_id = f"F-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    assumptions_note = (
        f"{'next-session close' if order_type == 'MARKET' else 'limit price on first session reached'}; "
        f"commission from cost_schedule_asof (real fee schedule, not invented); "
        f"slippage={assumptions.slippage_bps}bps and market_impact={assumptions.market_impact_bps}bps "
        f"are CONFIGURED ASSUMPTIONS, not measured from real execution data -- this platform has no "
        f"intraday fill data to calibrate them from.")
    portfolio_con.execute(
        "INSERT INTO fills (fill_id, order_id, fill_date, fill_price, quantity, commission, "
        "slippage_bps, market_impact_bps, transaction_cost_total, pricing_source_confidence, "
        "assumptions_note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (fill_id, order_id, fill_date, fill_price, quantity, commission, assumptions.slippage_bps,
         assumptions.market_impact_bps, transaction_cost_total, conf, assumptions_note, now))
    portfolio_con.execute("UPDATE orders SET status='FILLED' WHERE order_id=?", (order_id,))
    portfolio_con.commit()

    return FillResult(fill_id=fill_id, order_id=order_id, fill_date=fill_date, fill_price=fill_price,
                      quantity=quantity, commission=commission, slippage_bps=assumptions.slippage_bps,
                      market_impact_bps=assumptions.market_impact_bps,
                      transaction_cost_total=transaction_cost_total)


def _commission(market_con: sqlite3.Connection, trade_date: str, side: str, price: float,
                quantity: float, assumptions: ExecutionAssumptions) -> float:
    from .. import costs as _costs
    from .. import db as _db
    schedule = _db.cost_schedule_asof(market_con, trade_date)
    if schedule.empty:
        return 0.0  # no fee schedule on record for this date -- disclosed as zero, not guessed
    rates = _costs.side_rates(schedule, brokerage_override_pct=assumptions.brokerage_override_pct)
    rate = rates["buy_rate"] if side == "BUY" else rates["sell_rate"]
    return rate * price * quantity


def _reject(con: sqlite3.Connection, order_id: str, reason: str) -> None:
    con.execute("UPDATE orders SET status='REJECTED', rejection_reason=? WHERE order_id=?",
               (reason, order_id))
    con.commit()


def orders_from_target_positions(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                                 allocation_decision_id: str, current_positions: dict[str, float],
                                 current_nav: float, as_of: str) -> list[str]:
    """Diffs target_positions (from an APPROVED/APPROVED_WITH_WARNINGS
    allocation_decision) against current_positions (ticker -> current
    quantity, caller-supplied so this module never has to guess what's
    already held) to produce BUY/SELL orders for the delta. Requires the
    allocation_decision to already be risk-approved -- an order is never
    created from a REJECTED decision.

    Share quantity is sized using the LAST KNOWN price as of `as_of`
    (via db.equity_prices_asof, PIT-safe: trade_date <= as_of) -- this is
    a SIZING reference only, deliberately distinct from the ACTUAL fill
    price, which simulate_fill() resolves separately from the NEXT
    session strictly after the signal (the no-look-ahead rule this
    module's docstring states). Using the same day's price to decide HOW
    MANY shares to order is not a look-ahead violation -- a real investor
    deciding order size from the last quoted price, then having it filled
    at the next tradeable price, is exactly how real order sizing works.
    A ticker with no available reference price is skipped, not guessed."""
    from .. import db as _db

    row = portfolio_con.execute(
        "SELECT portfolio_id, risk_status FROM allocation_decisions WHERE allocation_decision_id = ?",
        (allocation_decision_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown allocation_decision_id {allocation_decision_id!r}")
    portfolio_id, risk_status = row
    if risk_status not in ("APPROVED", "APPROVED_WITH_WARNINGS"):
        raise ValueError(f"cannot create orders from a {risk_status} allocation_decision")

    targets = portfolio_con.execute(
        "SELECT target_position_id, ticker, target_weight FROM target_positions "
        "WHERE allocation_decision_id = ?", (allocation_decision_id,)).fetchall()

    order_ids = []
    for target_position_id, ticker, target_weight in targets:
        px = _db.equity_prices_asof(market_con, as_of, tickers=[ticker], min_confidence=0.9)
        if px.empty:
            continue  # no reference price available -- skipped, not guessed
        ref_price = float(px.sort_values("trade_date").iloc[-1].close)
        if ref_price <= 0:
            continue
        target_notional = target_weight * current_nav
        current_qty = current_positions.get(ticker, 0.0)
        current_notional = current_qty * ref_price
        delta_notional = target_notional - current_notional
        delta_qty = delta_notional / ref_price
        if abs(delta_qty) < 1e-6:
            continue  # already at target, no order needed
        side = "BUY" if delta_qty > 0 else "SELL"
        order_id = create_order(
            portfolio_con, portfolio_id, ticker, side, "MARKET", abs(delta_qty),
            signal_timestamp=as_of, allocation_decision_id=allocation_decision_id,
            target_position_id=target_position_id)
        order_ids.append(order_id)
    return order_ids
