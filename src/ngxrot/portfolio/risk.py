"""Phase 2: Risk Management Layer (2026-08-12, BUILD ASSIGNMENT).

Evaluates a proposed AllocationDecision (target_positions) BEFORE
execution. Every limit is a configuration parameter on risk_policies --
never hardcoded, never presented as discovered alpha (per the build
assignment's explicit instruction). Liquidity/ADTV convention matches
src/ngxrot/backtest_xs.py's own capacity_report / execution_realism.py's
own participation-cap formula (adtv60 = 60-day rolling mean of
value_traded; participation = position_notional / adtv60) -- the SAME
definition already established and validated on this platform for H-011's
own capacity assessment (median leg ~NGN 694,336), not a competing
convention invented here.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

RISK_STATUSES = ("APPROVED", "APPROVED_WITH_WARNINGS", "REJECTED")


@dataclass(frozen=True)
class RiskCheckResult:
    check_type: str
    ticker: str | None
    status: str            # 'pass' | 'warning' | 'fail'
    measured_value: float | None
    threshold_value: float | None
    reason: str


@dataclass(frozen=True)
class RiskReview:
    allocation_decision_id: str
    risk_status: str       # RISK_STATUSES
    checks: list[RiskCheckResult] = field(default_factory=list)


def create_risk_policy(con: sqlite3.Connection, portfolio_id: str, *,
                       max_position_weight: float, max_gross_exposure: float,
                       max_net_exposure: float, max_participation_rate: float,
                       max_position_notional: float | None = None,
                       max_sector_exposure: float | None = None,
                       max_single_name_exposure: float | None = None,
                       max_drawdown_limit: float | None = None,
                       notes: str = "risk-policy parameters, not discovered alpha -- see risk.py docstring",
                       effective_from: str | None = None) -> str:
    """Registers a configurable risk policy. Every threshold here is a
    caller-supplied parameter; this function invents no default limits."""
    risk_policy_id = f"RP-{uuid.uuid4()}"
    effective_from = effective_from or datetime.now(timezone.utc).date().isoformat()
    con.execute(
        "INSERT INTO risk_policies (risk_policy_id, portfolio_id, max_position_weight, "
        "max_position_notional, max_gross_exposure, max_net_exposure, max_sector_exposure, "
        "max_single_name_exposure, max_participation_rate, max_drawdown_limit, "
        "effective_from, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (risk_policy_id, portfolio_id, max_position_weight, max_position_notional,
         max_gross_exposure, max_net_exposure, max_sector_exposure, max_single_name_exposure,
         max_participation_rate, max_drawdown_limit, effective_from, notes))
    con.commit()
    return risk_policy_id


def _latest_risk_policy(con: sqlite3.Connection, portfolio_id: str) -> dict | None:
    # ORDER BY effective_from alone is ambiguous when two policies are
    # created the same day (effective_from has day granularity, matching
    # every other effective-dated table on this platform, e.g.
    # cost_schedule) -- rowid DESC breaks the tie by actual insertion
    # order, which is what "latest" should mean here. Confirmed necessary
    # by this module's own test: a same-day strict policy created after a
    # lenient one was silently ignored before this tiebreak was added.
    row = con.execute(
        "SELECT risk_policy_id, max_position_weight, max_position_notional, max_gross_exposure, "
        "max_net_exposure, max_sector_exposure, max_single_name_exposure, max_participation_rate, "
        "max_drawdown_limit FROM risk_policies WHERE portfolio_id = ? "
        "ORDER BY effective_from DESC, rowid DESC LIMIT 1", (portfolio_id,)).fetchone()
    if row is None:
        return None
    cols = ["risk_policy_id", "max_position_weight", "max_position_notional", "max_gross_exposure",
           "max_net_exposure", "max_sector_exposure", "max_single_name_exposure",
           "max_participation_rate", "max_drawdown_limit"]
    return dict(zip(cols, row))


def _adtv60(market_con: sqlite3.Connection, ticker: str, as_of: str) -> float | None:
    """60-day trailing mean value_traded, PIT-safe (trade_date <= as_of via
    equity_prices_asof) -- same convention as backtest_xs.py's adtv60."""
    from .. import db as _db
    px = _db.equity_prices_asof(market_con, as_of, tickers=[ticker], min_confidence=0.9)
    if px.empty:
        return None
    px = px.sort_values("trade_date").tail(60)
    if len(px) < 10:
        return None  # insufficient history -- unknown, not zero
    val = px.value_traded.mean()
    return float(val) if val and val > 0 else None


def review_allocation(portfolio_con: sqlite3.Connection, market_con: sqlite3.Connection,
                      allocation_decision_id: str, current_nav: float, as_of: str
                      ) -> RiskReview:
    """The core Phase-2 entry point: pulls the target_positions for
    `allocation_decision_id`, evaluates every configured limit, persists
    each RiskCheckResult, updates the allocation_decision's risk_status,
    and returns the full review. A portfolio with NO risk_policy on record
    is a REJECTED-by-construction case (never silently approved with no
    policy applied)."""
    policy = _latest_risk_policy(portfolio_con, _portfolio_id_for_decision(portfolio_con, allocation_decision_id))
    checks: list[RiskCheckResult] = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if policy is None:
        checks.append(RiskCheckResult(
            check_type="position_limit", ticker=None, status="fail",
            measured_value=None, threshold_value=None,
            reason="no risk_policy configured for this portfolio -- a proposal cannot be "
                  "approved with no risk controls applied"))
        return _finalize(portfolio_con, allocation_decision_id, checks, None, now)

    targets = portfolio_con.execute(
        "SELECT ticker, target_weight, target_notional FROM target_positions "
        "WHERE allocation_decision_id = ?", (allocation_decision_id,)).fetchall()

    gross = sum(abs(w) for _, w, _ in targets)
    net = sum(w for _, w, _ in targets)
    checks.append(_exposure_check("gross_exposure", gross, policy["max_gross_exposure"]))
    checks.append(_exposure_check("net_exposure", net, policy["max_net_exposure"], allow_negative=True))

    sector_exposure: dict[str, float] = {}
    for ticker, weight, notional in targets:
        # position_limit
        checks.append(_position_limit_check(ticker, weight, notional, policy))
        # single_name_exposure (same as position_limit but reported as its own
        # named check per the brief's own distinct control name)
        if policy["max_single_name_exposure"] is not None:
            checks.append(_threshold_check(
                "single_name_exposure", ticker, abs(weight), policy["max_single_name_exposure"],
                f"{ticker} weight {abs(weight):.4f} vs max_single_name_exposure "
                f"{policy['max_single_name_exposure']:.4f}"))
        # liquidity
        checks.append(_liquidity_check(market_con, ticker, notional, current_nav, weight, as_of, policy))
        # sector exposure (accumulated, checked after the loop)
        sector = _sector_for(market_con, ticker)
        if sector:
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + abs(weight)

    if policy["max_sector_exposure"] is not None:
        for sector, exposure in sector_exposure.items():
            checks.append(_threshold_check(
                "sector_exposure", None, exposure, policy["max_sector_exposure"],
                f"sector {sector!r} combined weight {exposure:.4f} vs "
                f"max_sector_exposure {policy['max_sector_exposure']:.4f}"))

    # drawdown circuit-breaker, if a limit is configured and drawdown history exists
    if policy["max_drawdown_limit"] is not None:
        checks.append(_drawdown_check(portfolio_con, _portfolio_id_for_decision(
            portfolio_con, allocation_decision_id), policy["max_drawdown_limit"]))

    return _finalize(portfolio_con, allocation_decision_id, checks, policy["risk_policy_id"], now)


def _portfolio_id_for_decision(con: sqlite3.Connection, allocation_decision_id: str) -> str:
    row = con.execute("SELECT portfolio_id FROM allocation_decisions WHERE allocation_decision_id = ?",
                      (allocation_decision_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown allocation_decision_id {allocation_decision_id!r}")
    return row[0]


def _exposure_check(check_type: str, measured: float, threshold: float | None,
                    allow_negative: bool = False) -> RiskCheckResult:
    if threshold is None:
        return RiskCheckResult(check_type, None, "pass", measured, None, "no threshold configured")
    breached = (measured > threshold) if not allow_negative else (abs(measured) > threshold)
    status = "fail" if breached else "pass"
    return RiskCheckResult(check_type, None, status, measured, threshold,
                           f"{check_type}={measured:.4f} vs threshold={threshold:.4f}")


def _threshold_check(check_type: str, ticker: str | None, measured: float, threshold: float,
                     reason: str) -> RiskCheckResult:
    status = "fail" if measured > threshold else "pass"
    return RiskCheckResult(check_type, ticker, status, measured, threshold, reason)


def _position_limit_check(ticker: str, weight: float, notional: float | None, policy: dict
                          ) -> RiskCheckResult:
    if abs(weight) > policy["max_position_weight"]:
        return RiskCheckResult("position_limit", ticker, "fail", abs(weight),
                               policy["max_position_weight"],
                               f"{ticker} weight {abs(weight):.4f} exceeds max_position_weight "
                               f"{policy['max_position_weight']:.4f}")
    if policy["max_position_notional"] is not None and notional is not None \
            and abs(notional) > policy["max_position_notional"]:
        return RiskCheckResult("position_limit", ticker, "fail", abs(notional),
                               policy["max_position_notional"],
                               f"{ticker} notional {abs(notional):,.0f} exceeds "
                               f"max_position_notional {policy['max_position_notional']:,.0f}")
    return RiskCheckResult("position_limit", ticker, "pass", abs(weight),
                           policy["max_position_weight"], f"{ticker} within position limits")


def _liquidity_check(market_con: sqlite3.Connection, ticker: str, notional: float | None,
                     current_nav: float, weight: float, as_of: str, policy: dict) -> RiskCheckResult:
    notional = notional if notional is not None else abs(weight) * current_nav
    adtv = _adtv60(market_con, ticker, as_of)
    if adtv is None:
        return RiskCheckResult("liquidity", ticker, "warning", None, policy["max_participation_rate"],
                               f"{ticker}: insufficient price history to compute ADTV60 -- "
                               f"liquidity UNKNOWN, flagged rather than assumed safe")
    participation = notional / adtv
    if participation > policy["max_participation_rate"]:
        return RiskCheckResult("liquidity", ticker, "fail", participation,
                               policy["max_participation_rate"],
                               f"{ticker}: estimated participation {participation:.2%} of ADTV60 "
                               f"exceeds max_participation_rate {policy['max_participation_rate']:.2%}")
    return RiskCheckResult("liquidity", ticker, "pass", participation,
                           policy["max_participation_rate"],
                           f"{ticker}: participation {participation:.2%} within limit")


def _sector_for(market_con: sqlite3.Connection, ticker: str) -> str | None:
    row = market_con.execute("SELECT sector_ngx FROM securities WHERE ticker = ?", (ticker,)).fetchone()
    return row[0] if row and row[0] else None


def _drawdown_check(con: sqlite3.Connection, portfolio_id: str, limit: float) -> RiskCheckResult:
    row = con.execute(
        "SELECT drawdown FROM drawdown_tracking WHERE portfolio_id = ? "
        "ORDER BY as_of DESC LIMIT 1", (portfolio_id,)).fetchone()
    if row is None:
        return RiskCheckResult("drawdown", None, "pass", None, limit,
                               "no drawdown history yet -- nothing to breach")
    dd = row[0]
    status = "fail" if dd < -abs(limit) else "pass"
    return RiskCheckResult("drawdown", None, status, dd, -abs(limit),
                           f"current drawdown {dd:.2%} vs limit {-abs(limit):.2%}")


def _finalize(con: sqlite3.Connection, allocation_decision_id: str, checks: list[RiskCheckResult],
             risk_policy_id: str | None, now: str) -> RiskReview:
    if any(c.status == "fail" for c in checks):
        risk_status = "REJECTED"
    elif any(c.status == "warning" for c in checks):
        risk_status = "APPROVED_WITH_WARNINGS"
    else:
        risk_status = "APPROVED"

    for c in checks:
        con.execute(
            "INSERT INTO risk_checks (risk_check_id, allocation_decision_id, risk_policy_id, ticker, "
            "check_type, status, measured_value, threshold_value, reason, checked_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"RC-{uuid.uuid4()}", allocation_decision_id, risk_policy_id, c.ticker,
             c.check_type, c.status, c.measured_value, c.threshold_value, c.reason, now))
    con.execute("UPDATE allocation_decisions SET risk_status = ? WHERE allocation_decision_id = ?",
               (risk_status, allocation_decision_id))
    con.commit()
    return RiskReview(allocation_decision_id=allocation_decision_id, risk_status=risk_status, checks=checks)


def update_drawdown(con: sqlite3.Connection, portfolio_id: str, as_of: str, equity: float) -> float:
    """Records a drawdown_tracking row: peak_equity is the running max of
    equity seen so far (including this one), drawdown = (equity -
    peak)/peak (<=0), max_drawdown_to_date = min(drawdown) over history.
    Returns the new drawdown value."""
    prior = con.execute(
        "SELECT peak_equity, max_drawdown_to_date FROM drawdown_tracking "
        "WHERE portfolio_id = ? ORDER BY as_of DESC LIMIT 1", (portfolio_id,)).fetchone()
    prior_peak = prior[0] if prior else equity
    prior_max_dd = prior[1] if prior else 0.0
    peak = max(prior_peak, equity)
    drawdown = (equity - peak) / peak if peak > 0 else 0.0
    max_dd = min(prior_max_dd, drawdown)
    con.execute(
        "INSERT OR REPLACE INTO drawdown_tracking (portfolio_id, as_of, equity, peak_equity, "
        "drawdown, max_drawdown_to_date) VALUES (?,?,?,?,?,?)",
        (portfolio_id, as_of, equity, peak, drawdown, max_dd))
    con.commit()
    return drawdown
