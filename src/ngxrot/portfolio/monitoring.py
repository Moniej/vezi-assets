"""Phase 9: Monitoring integration (2026-08-12, BUILD ASSIGNMENT).

Extends the platform's existing monitoring PATTERN (change detection ->
materiality -> persisted, machine-readable alert -- the same shape
scripts/run_continuous_intelligence.py already established for ticker-
scoped alerts) to the investment-management layer, WITHOUT modifying
ngx.sqlite's monitoring_runs/alerts tables or run_continuous_intelligence.py
itself -- a portfolio-level alert (drawdown breach, risk violation,
concentration) is not ticker-scoped the same way those tables assume, so
this writes to portfolio_alerts (data/portfolio.sqlite) instead, matching
the pattern, not merging into a schema it doesn't fit.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MonitoringConfig:
    """Every threshold here is a configuration parameter, matching risk.py's
    own discipline -- not a discovered or hardcoded-as-optimal constant."""
    stale_data_days: int = 5
    drift_threshold: float = 0.05          # abs(actual_weight - target_weight)
    concentration_threshold: float = 0.35   # single-position weight warning level
    drawdown_warning: float = -0.10
    drawdown_critical: float = -0.20
    pnl_anomaly_zscore: float = 3.0


def _alert(con: sqlite3.Connection, portfolio_id: str, as_of: str, alert_type: str,
          severity: str, message: str, details: dict | None = None) -> str:
    import json
    alert_id = f"PA-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute(
        "INSERT INTO portfolio_alerts (alert_id, portfolio_id, as_of, alert_type, severity, "
        "message, details_json, generated_at) VALUES (?,?,?,?,?,?,?,?)",
        (alert_id, portfolio_id, as_of, alert_type, severity, message,
         json.dumps(details, default=str) if details else None, now))
    con.commit()
    return alert_id


def check_data_freshness(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                         portfolio_id: str, as_of: str, cfg: MonitoringConfig) -> list[str]:
    row = market_con.execute("SELECT MAX(trade_date) FROM equity_prices").fetchone()
    latest = row[0] if row else None
    if latest is None:
        return [_alert(portfolio_con, portfolio_id, as_of, "data_freshness", "critical",
                       "no equity_prices data found at all")]
    gap_days = (datetime.fromisoformat(as_of) - datetime.fromisoformat(latest)).days
    if gap_days > cfg.stale_data_days:
        return [_alert(portfolio_con, portfolio_id, as_of, "data_freshness", "warning",
                       f"latest market data is {gap_days} days old (>{cfg.stale_data_days} threshold)",
                       {"latest_trade_date": latest, "gap_days": gap_days})]
    return []


def check_portfolio_drift(portfolio_con: sqlite3.Connection, portfolio_id: str,
                          allocation_decision_id: str, as_of: str, cfg: MonitoringConfig) -> list[str]:
    targets = portfolio_con.execute(
        "SELECT ticker, target_weight FROM target_positions WHERE allocation_decision_id = ?",
        (allocation_decision_id,)).fetchall()
    alerts = []
    for ticker, target_weight in targets:
        row = portfolio_con.execute(
            "SELECT weight FROM positions WHERE portfolio_id = ? AND ticker = ? "
            "ORDER BY as_of DESC LIMIT 1", (portfolio_id, ticker)).fetchone()
        actual_weight = row[0] if row else 0.0
        drift = abs(actual_weight - target_weight)
        if drift > cfg.drift_threshold:
            alerts.append(_alert(portfolio_con, portfolio_id, as_of, "portfolio_drift", "warning",
                                 f"{ticker}: actual weight {actual_weight:.4f} vs target "
                                 f"{target_weight:.4f}, drift {drift:.4f} exceeds threshold "
                                 f"{cfg.drift_threshold:.4f}",
                                 {"ticker": ticker, "actual": actual_weight, "target": target_weight}))
    return alerts


def check_risk_violations(portfolio_con: sqlite3.Connection, portfolio_id: str,
                          allocation_decision_id: str, as_of: str) -> list[str]:
    fails = portfolio_con.execute(
        "SELECT check_type, ticker, reason FROM risk_checks "
        "WHERE allocation_decision_id = ? AND status = 'fail'", (allocation_decision_id,)).fetchall()
    return [_alert(portfolio_con, portfolio_id, as_of, "risk_violation", "critical",
                  f"{check_type}" + (f" ({ticker})" if ticker else "") + f": {reason}",
                  {"check_type": check_type, "ticker": ticker})
            for check_type, ticker, reason in fails]


def check_execution_failures(portfolio_con: sqlite3.Connection, portfolio_id: str, as_of: str) -> list[str]:
    failed = portfolio_con.execute(
        "SELECT order_id, ticker, status, rejection_reason FROM orders "
        "WHERE portfolio_id = ? AND status IN ('REJECTED','CANCELLED')", (portfolio_id,)).fetchall()
    return [_alert(portfolio_con, portfolio_id, as_of, "execution_failure", "warning",
                  f"order {order_id} ({ticker}) {status}: {reason}",
                  {"order_id": order_id, "ticker": ticker})
            for order_id, ticker, status, reason in failed]


def check_concentration(portfolio_con: sqlite3.Connection, portfolio_id: str, as_of: str,
                        cfg: MonitoringConfig) -> list[str]:
    rows = portfolio_con.execute(
        "SELECT ticker, weight FROM positions p WHERE portfolio_id = ? AND as_of = "
        "(SELECT MAX(as_of) FROM positions p2 WHERE p2.portfolio_id = p.portfolio_id "
        "AND p2.ticker = p.ticker)", (portfolio_id,)).fetchall()
    return [_alert(portfolio_con, portfolio_id, as_of, "position_concentration", "warning",
                  f"{ticker} weight {weight:.4f} exceeds concentration threshold "
                  f"{cfg.concentration_threshold:.4f}", {"ticker": ticker, "weight": weight})
            for ticker, weight in rows if weight > cfg.concentration_threshold]


def check_drawdown(portfolio_con: sqlite3.Connection, portfolio_id: str, as_of: str,
                   cfg: MonitoringConfig) -> list[str]:
    row = portfolio_con.execute(
        "SELECT drawdown FROM drawdown_tracking WHERE portfolio_id = ? AND as_of = ?",
        (portfolio_id, as_of)).fetchone()
    if row is None:
        return []
    dd = row[0]
    if dd <= cfg.drawdown_critical:
        return [_alert(portfolio_con, portfolio_id, as_of, "drawdown", "critical",
                       f"drawdown {dd:.2%} breaches critical threshold {cfg.drawdown_critical:.2%}")]
    if dd <= cfg.drawdown_warning:
        return [_alert(portfolio_con, portfolio_id, as_of, "drawdown", "warning",
                       f"drawdown {dd:.2%} breaches warning threshold {cfg.drawdown_warning:.2%}")]
    return []


def check_pnl_anomaly(portfolio_con: sqlite3.Connection, portfolio_id: str, as_of: str,
                      cfg: MonitoringConfig) -> list[str]:
    import statistics
    rows = portfolio_con.execute(
        "SELECT daily_return FROM performance_records WHERE portfolio_id = ? AND daily_return IS NOT NULL "
        "ORDER BY as_of DESC LIMIT 30", (portfolio_id,)).fetchall()
    returns = [r[0] for r in rows]
    if len(returns) < 5:
        return []  # insufficient history to judge "anomalous" -- not flagged
    latest = returns[0]
    hist = returns[1:]
    mean, stdev = statistics.mean(hist), statistics.pstdev(hist)
    if stdev == 0:
        return []
    z = (latest - mean) / stdev
    if abs(z) > cfg.pnl_anomaly_zscore:
        return [_alert(portfolio_con, portfolio_id, as_of, "pnl_anomaly", "warning",
                       f"daily_return {latest:.4%} is {z:.1f} std devs from the trailing "
                       f"{len(hist)}-day mean {mean:.4%} (threshold {cfg.pnl_anomaly_zscore})")]
    return []


def run_monitoring_checks(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                          portfolio_id: str, as_of: str, cfg: MonitoringConfig | None = None,
                          allocation_decision_id: str | None = None) -> list[str]:
    """Runs every check that has enough context to run and returns the
    list of alert_ids generated (empty list = nothing tripped, not
    "monitoring didn't run"). allocation_decision_id is optional -- drift
    and risk_violation checks are skipped (not fabricated as empty passes)
    when none is supplied."""
    cfg = cfg or MonitoringConfig()
    alerts: list[str] = []
    alerts += check_data_freshness(portfolio_con, market_con, portfolio_id, as_of, cfg)
    if allocation_decision_id:
        alerts += check_portfolio_drift(portfolio_con, portfolio_id, allocation_decision_id, as_of, cfg)
        alerts += check_risk_violations(portfolio_con, portfolio_id, allocation_decision_id, as_of)
    alerts += check_execution_failures(portfolio_con, portfolio_id, as_of)
    alerts += check_concentration(portfolio_con, portfolio_id, as_of, cfg)
    alerts += check_drawdown(portfolio_con, portfolio_id, as_of, cfg)
    alerts += check_pnl_anomaly(portfolio_con, portfolio_id, as_of, cfg)
    return alerts
