"""Phase 1: Portfolio Construction Layer (2026-08-12, BUILD ASSIGNMENT).

Consumes alpha_engine.Recommendation objects (read-only -- alpha_engine.py
is never imported for modification, only its dataclass and
AlphaEngine.recommendations() output) and produces a proposed portfolio
(TargetPosition rows under one AllocationDecision), persisted to
data/portfolio.sqlite.

STRATEGY-AGNOSTIC BY DESIGN: this module does not invent an investment
strategy. Alpha signal (from alpha_engine.py) is a separate concept from
position sizing (this module) is a separate concept from risk constraint
(risk.py) is a separate concept from execution decision (execution.py) --
never conflated. None of the construction methods below are claimed to be
alpha; they are mechanical ways of turning a set of "buy" signals into
weights.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

CONSTRUCTION_METHODS = ("equal_weight", "signal_weighted", "rank_weighted",
                        "volatility_scaled", "custom")


@dataclass(frozen=True)
class SignalRecord:
    """Portfolio-layer's own persisted view of an alpha_engine.Recommendation
    -- a durable snapshot, not a reimplementation. Built by
    record_signals() from whatever AlphaEngine.recommendations() returns."""
    signal_id: str
    as_of: str
    instrument: str
    action: str
    size_pct_nav: float | None
    horizon: str | None
    expected_excess_ann: float | None
    expected_max_drawdown: float | None
    confidence_rating: str
    rationale: str
    hypothesis_id: str | None
    experiment_ids: tuple = ()
    caveats: tuple = ()


@dataclass(frozen=True)
class TargetPosition:
    target_position_id: str
    ticker: str
    target_weight: float
    target_notional: float | None
    signal_id: str | None
    signal_timestamp: str | None
    hypothesis_id: str | None
    confidence: str | None
    reason: str
    construction_method: str


def record_signals(con: sqlite3.Connection, recommendations: list, recorded_at: str | None = None
                   ) -> list[SignalRecord]:
    """Persists a list of alpha_engine.Recommendation objects (or any object
    with the same field shape -- duck-typed deliberately so this module
    never needs to import alpha_engine.Recommendation's class itself) as
    immutable SignalRecord rows. Returns the persisted records with their
    assigned signal_id."""
    recorded_at = recorded_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    for r in recommendations:
        signal_id = f"S-{uuid.uuid4()}"
        con.execute(
            "INSERT INTO signals (signal_id, as_of, instrument, action, size_pct_nav, horizon, "
            "expected_excess_ann, expected_max_drawdown, confidence_rating, rationale, "
            "hypothesis_id, experiment_ids_json, caveats_json, recorded_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (signal_id, r.as_of, r.instrument, r.action, r.size_pct_nav, r.horizon,
             r.expected_excess_ann, r.expected_max_drawdown, r.confidence_rating, r.rationale,
             r.hypothesis_id, json.dumps(list(r.experiment_ids)), json.dumps(list(r.caveats)),
             recorded_at))
        out.append(SignalRecord(
            signal_id=signal_id, as_of=r.as_of, instrument=r.instrument, action=r.action,
            size_pct_nav=r.size_pct_nav, horizon=r.horizon,
            expected_excess_ann=r.expected_excess_ann, expected_max_drawdown=r.expected_max_drawdown,
            confidence_rating=r.confidence_rating, rationale=r.rationale,
            hypothesis_id=r.hypothesis_id, experiment_ids=tuple(r.experiment_ids),
            caveats=tuple(r.caveats)))
    con.commit()
    return out


def _weights_equal_weight(signals: list[SignalRecord]) -> dict[str, float]:
    buys = [s for s in signals if s.action == "buy"]
    if not buys:
        return {}
    w = 1.0 / len(buys)
    return {s.instrument: w for s in buys}


def _weights_signal_weighted(signals: list[SignalRecord]) -> dict[str, float]:
    """Weight proportional to each signal's OWN size_pct_nav (its
    within-sleeve weight, per alpha_engine.py's own documented semantics),
    renormalized to sum to 1 across the buy set -- this is a portfolio-
    construction mechanism, not a claim that the underlying size_pct_nav
    values are themselves optimal."""
    buys = [s for s in signals if s.action == "buy" and s.size_pct_nav]
    total = sum(s.size_pct_nav for s in buys)
    if not buys or total <= 0:
        return {}
    return {s.instrument: s.size_pct_nav / total for s in buys}


def _weights_rank_weighted(signals: list[SignalRecord]) -> dict[str, float]:
    """Linear rank weighting: signals are ordered by expected_excess_ann
    (falling back to input order if not provided), rank 1 (best) gets the
    highest weight, weights sum to 1. A mechanical tie-break rule, not an
    alpha claim about which signal is "better" beyond what the signal
    itself already asserted via expected_excess_ann."""
    buys = [s for s in signals if s.action == "buy"]
    if not buys:
        return {}
    ranked = sorted(buys, key=lambda s: (s.expected_excess_ann is None, -(s.expected_excess_ann or 0)))
    n = len(ranked)
    raw_weights = [n - i for i in range(n)]  # n, n-1, ..., 1
    total = sum(raw_weights)
    return {s.instrument: w / total for s, w in zip(ranked, raw_weights)}


def _weights_volatility_scaled(con: sqlite3.Connection, signals: list[SignalRecord],
                               as_of: str, lookback_days: int = 60) -> dict[str, float]:
    """Inverse-volatility weighting using trailing realized daily-return
    volatility from db.equity_prices_asof (already PIT-safe -- trade_date
    <= as_of). A position with lower recent volatility gets a larger
    weight, normalized to sum to 1. If price history is insufficient for
    a ticker, it is EXCLUDED (never assigned a fabricated/default
    volatility) and this is disclosed via the caller's warnings, not
    silently dropped."""
    from .. import db as _db
    import pandas as pd

    buys = [s for s in signals if s.action == "buy"]
    if not buys:
        return {}
    tickers = [s.instrument for s in buys]
    px = _db.equity_prices_asof(con, as_of, tickers=tickers, min_confidence=0.9)
    if px.empty:
        return {}
    px = px.sort_values("trade_date")
    vols = {}
    for t in tickers:
        series = px[px.ticker == t].tail(lookback_days + 1)
        if len(series) < max(10, lookback_days // 3):
            continue  # insufficient history -- excluded, not guessed
        rets = series.close.pct_change().dropna()
        vol = rets.std()
        if vol and vol > 0:
            vols[t] = vol
    if not vols:
        return {}
    inv_vol = {t: 1.0 / v for t, v in vols.items()}
    total = sum(inv_vol.values())
    return {t: w / total for t, w in inv_vol.items()}


def construct_portfolio(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                        portfolio_id: str, signals: list[SignalRecord],
                        method: str, as_of: str, current_nav: float | None = None
                        ) -> tuple[str, list[TargetPosition]]:
    """Turns a list of SignalRecord into an AllocationDecision +
    TargetPosition rows, persisted immutably. Returns (allocation_decision_id,
    target_positions).

    Two separate connections, deliberately: `portfolio_con` is
    data/portfolio.sqlite (where the result is written); `market_con` is
    data/ngx.sqlite (read-only, for methods that need PIT price/volatility
    data, e.g. volatility_scaled) -- this package never writes to
    data/ngx.sqlite, and conflating the two connections into one parameter
    was an earlier design mistake caught by this module's own test (see
    scripts/portfolio/test_construction.py) before it could propagate into
    risk.py/execution.py, which share the same two-database need.

    method must be one of CONSTRUCTION_METHODS. 'custom' requires the
    caller to have already computed weights and pass them via
    construct_portfolio_from_weights() instead -- this function only
    implements the four named mechanical methods."""
    if method not in CONSTRUCTION_METHODS:
        raise ValueError(f"unknown construction method {method!r}, must be one of {CONSTRUCTION_METHODS}")
    if method == "custom":
        raise ValueError("method='custom' has no built-in weighting rule -- "
                         "use construct_portfolio_from_weights() with pre-computed weights")

    if method == "equal_weight":
        weights = _weights_equal_weight(signals)
    elif method == "signal_weighted":
        weights = _weights_signal_weighted(signals)
    elif method == "rank_weighted":
        weights = _weights_rank_weighted(signals)
    elif method == "volatility_scaled":
        weights = _weights_volatility_scaled(market_con, signals, as_of)

    return construct_portfolio_from_weights(
        portfolio_con, portfolio_id, signals, weights, method, as_of, current_nav)


def construct_portfolio_from_weights(con: sqlite3.Connection, portfolio_id: str,
                                     signals: list[SignalRecord], weights: dict[str, float],
                                     method: str, as_of: str, current_nav: float | None = None
                                     ) -> tuple[str, list[TargetPosition]]:
    """`con` here is always data/portfolio.sqlite -- this is the shared
    persistence path every construction method funnels through, and it
    never needs market data (that was already resolved into `weights` by
    the caller)."""
    """The shared persistence path every construction method (including
    'custom') funnels through -- one AllocationDecision, N TargetPosition
    rows, all immutable once written."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    allocation_decision_id = f"AD-{uuid.uuid4()}"
    by_instrument = {s.instrument: s for s in signals}

    con.execute(
        "INSERT INTO allocation_decisions (allocation_decision_id, portfolio_id, as_of, "
        "construction_method, rationale, n_target_positions, risk_status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (allocation_decision_id, portfolio_id, as_of, method,
         f"{method} construction over {len(weights)} buy signal(s)", len(weights),
         "pending", now))

    out = []
    for ticker, weight in weights.items():
        sig = by_instrument.get(ticker)
        target_position_id = f"TP-{uuid.uuid4()}"
        notional = weight * current_nav if current_nav is not None else None
        reason = (sig.rationale if sig else f"weight assigned by {method} construction, "
                                             f"no matching signal record found")
        con.execute(
            "INSERT INTO target_positions (target_position_id, allocation_decision_id, portfolio_id, "
            "ticker, target_weight, target_notional, signal_id, signal_timestamp, hypothesis_id, "
            "confidence, reason, construction_method, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (target_position_id, allocation_decision_id, portfolio_id, ticker, weight, notional,
             sig.signal_id if sig else None, sig.as_of if sig else None,
             sig.hypothesis_id if sig else None, sig.confidence_rating if sig else None,
             reason, method, now))
        out.append(TargetPosition(
            target_position_id=target_position_id, ticker=ticker, target_weight=weight,
            target_notional=notional, signal_id=sig.signal_id if sig else None,
            signal_timestamp=sig.as_of if sig else None, hypothesis_id=sig.hypothesis_id if sig else None,
            confidence=sig.confidence_rating if sig else None, reason=reason, construction_method=method))
    con.commit()
    return allocation_decision_id, out
