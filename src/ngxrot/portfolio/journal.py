"""Phase 6: Investment Decision Journal + Research Feedback Loop
(2026-08-12, BUILD ASSIGNMENT).

decision_journal is permanent institutional memory -- schema/portfolio.sql
enforces (via trigger) that only actual_outcome_pnl/postmortem may ever be
updated on an existing row; every other field is fixed at insert time.

hypothesis_performance_history closes the loop the assignment calls the
most important institutional feature: rolling a hypothesis's signals ->
executions -> P&L -> cost back up so research can see which hypotheses
actually made money, not just which ones passed a backtest gate.

Regime-conditional performance ("strongest in regime A, weakest in regime
B") is explicitly NOT built here -- this platform has no portfolio-level
regime classifier to condition on, and building one would be a research
task in its own right, not infrastructure. Disclosed, not silently
approximated with an invented regime label.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


def record_decision(con: sqlite3.Connection, portfolio_id: str, decision: str, rationale: str,
                    portfolio_state: dict, risk_state: dict, strategy_id: str | None = None,
                    hypothesis_id: str | None = None, signal_id: str | None = None,
                    expected_return: float | None = None, expected_risk: float | None = None,
                    timestamp: str | None = None) -> str:
    decision_id = f"DJ-{uuid.uuid4()}"
    timestamp = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute(
        "INSERT INTO decision_journal (decision_id, timestamp, portfolio_id, strategy_id, "
        "hypothesis_id, signal_id, portfolio_state_json, decision, rationale, risk_state_json, "
        "expected_return, expected_risk, actual_outcome_pnl, postmortem) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
        (decision_id, timestamp, portfolio_id, strategy_id, hypothesis_id, signal_id,
         json.dumps(portfolio_state, default=str), decision, rationale,
         json.dumps(risk_state, default=str), expected_return, expected_risk))
    con.commit()
    return decision_id


def record_outcome(con: sqlite3.Connection, decision_id: str, actual_outcome_pnl: float,
                   postmortem: str) -> None:
    """The ONLY legal update to a decision_journal row -- enforced by the
    schema's own trigger (decision_journal_guard_immutable_fields), which
    aborts if any other field changes. This function only ever sets these
    two columns, so it cannot accidentally violate that trigger."""
    con.execute(
        "UPDATE decision_journal SET actual_outcome_pnl = ?, postmortem = ? WHERE decision_id = ?",
        (actual_outcome_pnl, postmortem, decision_id))
    con.commit()


def get_decision(con: sqlite3.Connection, decision_id: str) -> dict | None:
    row = con.execute(
        "SELECT decision_id, timestamp, portfolio_id, strategy_id, hypothesis_id, signal_id, "
        "portfolio_state_json, decision, rationale, risk_state_json, expected_return, "
        "expected_risk, actual_outcome_pnl, postmortem FROM decision_journal WHERE decision_id = ?",
        (decision_id,)).fetchone()
    if row is None:
        return None
    cols = ["decision_id", "timestamp", "portfolio_id", "strategy_id", "hypothesis_id", "signal_id",
           "portfolio_state", "decision", "rationale", "risk_state", "expected_return",
           "expected_risk", "actual_outcome_pnl", "postmortem"]
    d = dict(zip(cols, row))
    d["portfolio_state"] = json.loads(d["portfolio_state"]) if d["portfolio_state"] else None
    d["risk_state"] = json.loads(d["risk_state"]) if d["risk_state"] else None
    return d


@dataclass(frozen=True)
class HypothesisPerformance:
    hypothesis_id: str
    n_signals: int
    n_executed: int
    realized_pnl: float
    transaction_costs: float
    n_closed_positions: int
    win_rate: float | None
    regime_breakdown: str  # explicitly states this dimension is not built


def hypothesis_performance_history(portfolio_con: sqlite3.Connection, hypothesis_id: str
                                   ) -> HypothesisPerformance:
    """The research-feedback rollup: Hypothesis X -> N signals -> M
    executed -> realized P&L -> transaction cost -> win rate. This is
    computed from position_lifecycles + fills (real simulated outcomes),
    never from a backtest number -- the whole point of this loop is
    telling research what ACTUALLY happened when a hypothesis's signals
    were paper-traded, not repeating what the original validation
    gauntlet already said."""
    n_signals = portfolio_con.execute(
        "SELECT COUNT(*) FROM signals WHERE hypothesis_id = ?", (hypothesis_id,)).fetchone()[0]

    # Counts executed orders via position_lifecycles.hypothesis_id (set at
    # lifecycle-open time), NOT via the target_positions->signals chain --
    # that chain only exists for orders created through
    # orders_from_target_positions(); an order created directly via
    # create_order() (as any ad-hoc/manual order would be) has no
    # target_position_id, and the earlier target_positions-based query
    # silently undercounted those (confirmed by this module's own test:
    # a direct-order entry/exit pair reported n_executed=0 despite two
    # real fills existing). position_lifecycles is the robust link because
    # it's populated by open_position_lifecycle() regardless of how the
    # underlying order was created.
    n_executed = portfolio_con.execute(
        "SELECT COUNT(DISTINCT order_id) FROM ("
        "  SELECT f.order_id FROM position_lifecycles pl "
        "  JOIN fills f ON f.fill_id = pl.entry_fill_id WHERE pl.hypothesis_id = ? "
        "  UNION "
        "  SELECT f.order_id FROM position_lifecycles pl "
        "  JOIN fills f ON f.fill_id = pl.exit_fill_id WHERE pl.hypothesis_id = ?"
        ")", (hypothesis_id, hypothesis_id)).fetchone()[0]

    lifecycles = portfolio_con.execute(
        "SELECT realized_pnl, total_cost FROM position_lifecycles "
        "WHERE hypothesis_id = ? AND exit_date IS NOT NULL", (hypothesis_id,)).fetchall()
    realized_pnl = sum(r[0] for r in lifecycles if r[0] is not None)
    transaction_costs = sum(r[1] for r in lifecycles if r[1] is not None)
    n_closed = len(lifecycles)
    win_rate = None
    if n_closed:
        wins = sum(1 for r in lifecycles if r[0] and r[0] > 0)
        win_rate = wins / n_closed

    return HypothesisPerformance(
        hypothesis_id=hypothesis_id, n_signals=n_signals, n_executed=n_executed,
        realized_pnl=realized_pnl, transaction_costs=transaction_costs,
        n_closed_positions=n_closed, win_rate=win_rate,
        regime_breakdown="NOT BUILT -- no portfolio-level regime classifier exists on this "
                         "platform; would require its own research task, not infrastructure")
