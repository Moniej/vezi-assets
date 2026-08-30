"""Investment OS end-to-end build (2026-08-13) -- the real, runnable paper
investment cycle, formalizing what test_integration_e2e.py rehearsed as a
one-off test into an actual operational script.

signal (AlphaEngine.recommendations(), UNMODIFIED, real call)
  -> eligibility (only 'buy' actions, only CONFIRMED hypotheses reach the
     Alpha Engine at all -- see alpha_engine.py's own docstring)
  -> portfolio construction -> risk checks -> paper order -> portfolio
     state -> performance -> attribution -> decision journal

NO BROKER. NO REAL CAPITAL. NO LIVE EXECUTION -- nothing in this script
or anything it imports can reach a broker; portfolio/execution.py has no
broker code path to reach.

Defaults to a SCRATCH portfolio database (a fresh one every run) so this
script is safe to run repeatedly without operator confirmation. Pass
--db to target a specific (e.g. persistent paper-tracking) database
explicitly -- never defaults to one, exactly like every other
production-adjacent script on this platform (db.py's own convention).

H-011 CAPACITY WARNING: as of this writing, H-011 (Size) is the ONLY
`confirmed` hypothesis in the registry. It is ALSO the platform's own,
independently and repeatedly documented capacity-constrained factor --
median leg capacity ~N694,000-N713,000 (docs/PHASE28_QUANT_ENGINE_AUDIT_
2026-08-02.md, docs/FACTOR_REGISTRY.md). If this script's recommendations
are dominated by H-011, this run is a PIPELINE INTEGRATION REHEARSAL, not
evidence of a scalable investment strategy -- printed explicitly below,
every time, not just in this docstring.

  PYTHONPATH=src python scripts/portfolio/run_paper_cycle.py [--db PATH] [--as-of YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot import registry as mreg  # noqa: E402
from ngxrot.alpha_engine import AlphaEngine  # noqa: E402 -- imported, never modified
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.construction import record_signals, construct_portfolio  # noqa: E402
from ngxrot.portfolio.risk import create_risk_policy, review_allocation, update_drawdown  # noqa: E402
from ngxrot.portfolio.execution import (  # noqa: E402
    orders_from_target_positions, simulate_fill, ExecutionAssumptions, create_order)
from ngxrot.portfolio.performance import (  # noqa: E402
    apply_fill_to_position, mark_to_market, record_nav, compute_performance)
from ngxrot.portfolio.attribution import (  # noqa: E402
    open_position_lifecycle, close_position_lifecycle, compute_attribution)
from ngxrot.portfolio.journal import record_decision, record_outcome  # noqa: E402
from ngxrot.portfolio.monitoring import run_monitoring_checks  # noqa: E402

CAPACITY_CONSTRAINED_HYPOTHESES = {
    "H-011": "Size -- median leg capacity ~N694,000-N713,000 "
             "(docs/PHASE28_QUANT_ENGINE_AUDIT_2026-08-02.md, docs/FACTOR_REGISTRY.md). "
             "The platform's only confirmed factor, and its own worst-capacity one.",
}


def _print_banner(recs) -> None:
    print("=" * 78)
    print("PAPER INVESTMENT CYCLE -- SIMULATION ONLY")
    print("No broker connected. No real capital. Not investment advice.")
    print("=" * 78)
    flagged = {r.hypothesis_id for r in recs if r.hypothesis_id in CAPACITY_CONSTRAINED_HYPOTHESES}
    for hid in flagged:
        print(f"CAPACITY WARNING: {hid} -- {CAPACITY_CONSTRAINED_HYPOTHESES[hid]}")
        print(f"  This cycle's use of {hid} is a PIPELINE INTEGRATION REHEARSAL.")
        print(f"  Its paper performance here is NOT evidence of a scalable investment edge.")
    if flagged:
        print("-" * 78)


def run_cycle(portfolio_db_path: str, as_of_entry: str, as_of_exit: str,
             portfolio_id: str = "PAPER_CYCLE") -> dict:
    pcon = pdb.init_db(portfolio_db_path)
    existing = pcon.execute("SELECT 1 FROM portfolios WHERE portfolio_id=?", (portfolio_id,)).fetchone()
    if not existing:
        pcon.execute(
            "INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
            "inception_date,created_at) VALUES (?,?,?,?,?,?)",
            (portfolio_id, "Paper Investment Cycle", "NGN", 1_000_000, as_of_entry, as_of_entry))
        pcon.commit()
    mcon = mdb.connect()  # PRODUCTION market data, READ-ONLY (real prices, never written to)
    reg_con = mreg.connect_registry()  # READ-ONLY hypothesis/experiment lineage

    engine = AlphaEngine()
    recs = engine.recommendations()
    _print_banner(recs)

    buy_recs = [r for r in recs if r.action == "buy"]
    print(f"AlphaEngine.recommendations(): {len(recs)} total, {len(buy_recs)} 'buy'.")
    if not buy_recs:
        print("No 'buy' recommendations -- correctly no-op (an empty confirmed-hypothesis "
             "set means the correct output is empty, not fabricated).")
        return {"status": "no_signal", "recommendations": len(recs)}

    if not pcon.execute("SELECT 1 FROM risk_policies WHERE portfolio_id=?", (portfolio_id,)).fetchone():
        create_risk_policy(pcon, portfolio_id, max_position_weight=0.15, max_gross_exposure=1.0,
                          max_net_exposure=1.0, max_participation_rate=0.10)

    sigs = record_signals(pcon, buy_recs)
    ad_id, targets = construct_portfolio(pcon, mcon, portfolio_id, sigs, "equal_weight",
                                         as_of_entry, current_nav=1_000_000)
    print(f"Signals recorded: {len(sigs)}. Target positions: {len(targets)}.")

    review = review_allocation(pcon, mcon, ad_id, 1_000_000, as_of_entry)
    print(f"Risk review: {review.risk_status}")
    if review.risk_status == "REJECTED":
        print("Allocation REJECTED by risk policy -- correctly stopping, no orders from a "
             "rejected decision.")
        return {"status": "risk_rejected", "risk_status": review.risk_status}

    order_ids = orders_from_target_positions(pcon, mcon, ad_id, {}, 1_000_000, as_of_entry)
    assumptions = ExecutionAssumptions(slippage_bps=10, market_impact_bps=5)
    fills, cash = {}, 1_000_000.0
    lifecycle_ids = {}
    for oid in order_ids:
        fill = simulate_fill(pcon, mcon, oid, assumptions)
        if not fill:
            continue
        fills[oid] = fill
        order = pcon.execute("SELECT ticker, side, target_position_id FROM orders WHERE order_id=?",
                            (oid,)).fetchone()
        ticker, side, tp_id = order
        apply_fill_to_position(pcon, portfolio_id, ticker, side, fill.fill_price, fill.quantity, fill.fill_date)
        cash -= fill.fill_price * fill.quantity + fill.commission
        sig_id = pcon.execute("SELECT signal_id FROM target_positions WHERE target_position_id=?",
                             (tp_id,)).fetchone()
        sig_id = sig_id[0] if sig_id else None
        hyp_id = buy_recs[0].hypothesis_id
        lifecycle_ids[ticker] = open_position_lifecycle(
            pcon, portfolio_id, ticker, fill.fill_id, sig_id, hyp_id, fill.fill_date)
    print(f"Orders: {len(order_ids)}. Fills: {len(fills)}.")

    did = record_decision(
        pcon, portfolio_id, "ALLOCATE",
        f"Paper cycle {as_of_entry}: risk-approved allocation from {len(buy_recs)} buy signal(s)",
        {"nav": 1_000_000}, {"risk_status": review.risk_status},
        hypothesis_id=buy_recs[0].hypothesis_id if buy_recs else None)

    mark_to_market(pcon, mcon, portfolio_id, as_of_exit)
    nav = record_nav(pcon, portfolio_id, as_of_exit, cash, track_record_status="PAPER")
    dd = update_drawdown(pcon, portfolio_id, as_of_exit, nav)
    print(f"NAV: {nav:,.2f}. Drawdown: {dd:.4f}.")

    total_realized = 0.0
    for ticker, pl_id in lifecycle_ids.items():
        entry_oid = next(oid for oid, f in fills.items() if
                        pcon.execute("SELECT ticker FROM orders WHERE order_id=?", (oid,)).fetchone()[0] == ticker)
        entry_fill = fills[entry_oid]
        xo = create_order(pcon, portfolio_id, ticker, "SELL", "MARKET", entry_fill.quantity, as_of_exit)
        xf = simulate_fill(pcon, mcon, xo, assumptions)
        if xf is None:
            continue
        apply_fill_to_position(pcon, portfolio_id, ticker, "SELL", xf.fill_price, xf.quantity, xf.fill_date)
        realized = (xf.fill_price - entry_fill.fill_price) * xf.quantity
        total_realized += realized
        close_position_lifecycle(pcon, portfolio_id, ticker, xf.fill_id, xf.fill_date, realized,
                                 entry_fill.commission + xf.commission)
    record_outcome(pcon, did, total_realized, f"Paper cycle closed: realized P&L={total_realized:,.2f}")

    perf = compute_performance(pcon, mcon, portfolio_id)
    # Attribution's period_end must cover the REAL exit fill dates, not the
    # as_of_exit signal date used to create the SELL orders -- fills
    # resolve to the next session strictly after that date (no-look-ahead),
    # so the actual exit_date can fall after as_of_exit. Using as_of_exit
    # directly here would silently exclude every closed lifecycle (the
    # exact bug test_integration_e2e.py's own development caught).
    max_exit_date = pcon.execute(
        "SELECT MAX(exit_date) FROM position_lifecycles WHERE portfolio_id=?",
        (portfolio_id,)).fetchone()[0] or as_of_exit
    attribution = compute_attribution(pcon, mcon, portfolio_id, as_of_entry, max_exit_date)
    alerts = run_monitoring_checks(pcon, mcon, portfolio_id, as_of_exit, allocation_decision_id=ad_id)
    print(f"Realized P&L: {total_realized:,.2f}. Attribution records: {len(attribution)}. "
         f"Monitoring alerts: {len(alerts)}.")

    return {
        "status": "completed", "portfolio_id": portfolio_id, "nav": nav, "drawdown": dd,
        "realized_pnl": total_realized, "n_signals": len(sigs), "n_orders": len(order_ids),
        "n_fills": len(fills), "n_attribution_records": len(attribution),
        "n_monitoring_alerts": len(alerts),
        "hypotheses_used": sorted({r.hypothesis_id for r in buy_recs}),
        "capacity_constrained_hypotheses_used": sorted(
            {r.hypothesis_id for r in buy_recs} & set(CAPACITY_CONSTRAINED_HYPOTHESES)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="portfolio DB path; omit for a fresh scratch DB")
    ap.add_argument("--as-of-entry", default="2026-08-05")
    ap.add_argument("--as-of-exit", default="2026-08-06")
    args = ap.parse_args()
    db_path = args.db or str(pdb.new_scratch_db_path())
    print(f"Portfolio DB: {db_path}")
    result = run_cycle(db_path, args.as_of_entry, args.as_of_exit)
    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
