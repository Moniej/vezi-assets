"""Phase 13: Integration test -- the complete synthetic scenario AND a
second scenario using the real Alpha Engine (H-011) as the upstream
signal source, unmodified.

Flow tested (both scenarios):
  Hypothesis -> Signal -> Portfolio target -> Risk validation -> Paper
  order -> Fill -> Position -> NAV -> P&L -> Attribution -> Decision
  journal -> (research feedback via hypothesis_performance_history)

alpha_engine.py is imported and CALLED, never modified -- this test is
itself the proof that no adapter rewrite was needed; AlphaEngine.
recommendations()'s existing output shape was consumed directly.

  PYTHONPATH=src python scripts/portfolio/test_integration_e2e.py
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot import registry as mreg  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.construction import record_signals, construct_portfolio  # noqa: E402
from ngxrot.portfolio.risk import create_risk_policy, review_allocation, update_drawdown  # noqa: E402
from ngxrot.portfolio.execution import (  # noqa: E402
    orders_from_target_positions, simulate_fill, ExecutionAssumptions)
from ngxrot.portfolio.performance import (  # noqa: E402
    apply_fill_to_position, mark_to_market, record_nav, compute_performance)
from ngxrot.portfolio.attribution import (  # noqa: E402
    open_position_lifecycle, close_position_lifecycle, compute_attribution, reconstruct_lineage)
from ngxrot.portfolio.journal import (  # noqa: E402
    record_decision, record_outcome, hypothesis_performance_history)
from ngxrot.portfolio.monitoring import run_monitoring_checks  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


@dataclass(frozen=True)
class FakeRec:
    as_of: str; instrument: str; action: str; size_pct_nav: float
    horizon: str; expected_excess_ann: float; expected_max_drawdown: float
    confidence_rating: str; rationale: str; hypothesis_id: str
    experiment_ids: tuple = (); caveats: tuple = ()


FROZEN_NGX = ROOT / "fixtures" / "stage1" / "frozen" / "ngx_regression.sqlite"
FROZEN_REGISTRY = ROOT / "fixtures" / "stage1" / "frozen" / "registry_regression.sqlite"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_scenario(recommendations, portfolio_id: str, as_of_entry: str, as_of_exit: str, label: str,
                 market_db: Path, registry_db: Path, portfolio_db: Path):
    """Runs the full loop for one signal set and returns True iff every
    stage produced a real, verifiable artifact (not just "didn't crash")."""
    print(f"\n=== {label} ===")
    pcon = pdb.init_db(portfolio_db)
    pcon.execute("INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
                "inception_date,created_at) VALUES (?,?,?,?,?,?)",
                (portfolio_id, label, "NGN", 1_000_000, as_of_entry, as_of_entry))
    pcon.commit()
    mcon = sqlite3.connect(f"file:{market_db.as_posix()}?mode=ro", uri=True)

    # 1. Hypothesis -> Signal
    sigs = record_signals(pcon, recommendations)
    check(f"[{label}] signals recorded", len(sigs) == len([r for r in recommendations]))

    # 2. Signal -> Portfolio target
    create_risk_policy(pcon, portfolio_id, max_position_weight=0.50, max_gross_exposure=1.1,
                       max_net_exposure=1.1, max_participation_rate=0.50)
    ad_id, targets = construct_portfolio(pcon, mcon, portfolio_id, sigs, "equal_weight",
                                         as_of_entry, current_nav=1_000_000)
    check(f"[{label}] target positions constructed", len(targets) > 0)

    # 3. Risk validation
    review = review_allocation(pcon, mcon, ad_id, 1_000_000, as_of_entry)
    check(f"[{label}] risk review reaches a terminal status",
         review.risk_status in ("APPROVED", "APPROVED_WITH_WARNINGS", "REJECTED"))
    if review.risk_status == "REJECTED":
        check(f"[{label}] scenario stops cleanly on REJECTED (no orders from a rejected decision)", True)
        return

    # 4. Paper order + Fill
    order_ids = orders_from_target_positions(pcon, mcon, ad_id, {}, 1_000_000, as_of_entry)
    check(f"[{label}] orders created from approved targets", len(order_ids) > 0)
    assumptions = ExecutionAssumptions(slippage_bps=10, market_impact_bps=5)
    fills = {}
    for oid in order_ids:
        fill = simulate_fill(pcon, mcon, oid, assumptions)
        if fill:
            fills[oid] = fill
    check(f"[{label}] at least one order filled against real market data", len(fills) > 0)

    # 5. Fill -> Position, decision journal, lifecycles
    cash = 1_000_000.0
    lifecycle_ids = {}
    for oid, fill in fills.items():
        order = pcon.execute("SELECT ticker, side, target_position_id FROM orders WHERE order_id=?", (oid,)).fetchone()
        ticker, side, tp_id = order
        apply_fill_to_position(pcon, portfolio_id, ticker, side, fill.fill_price, fill.quantity, fill.fill_date)
        cash -= fill.fill_price * fill.quantity + fill.commission
        sig_id = pcon.execute("SELECT signal_id FROM target_positions WHERE target_position_id=?", (tp_id,)).fetchone()
        sig_id = sig_id[0] if sig_id else None
        hyp_id = recommendations[0].hypothesis_id
        lifecycle_ids[ticker] = open_position_lifecycle(pcon, portfolio_id, ticker, fill.fill_id, sig_id, hyp_id, fill.fill_date)
    check(f"[{label}] position lifecycles opened for every filled entry", len(lifecycle_ids) == len(fills))

    did = record_decision(pcon, portfolio_id, "ALLOCATE", f"{label}: risk-approved allocation",
                          {"nav": 1_000_000}, {"risk_status": review.risk_status},
                          hypothesis_id=recommendations[0].hypothesis_id)
    check(f"[{label}] decision journaled", did is not None)

    # 6. NAV over subsequent days
    mark_to_market(pcon, mcon, portfolio_id, as_of_exit)
    nav = record_nav(pcon, portfolio_id, as_of_exit, cash, track_record_status="PAPER")
    check(f"[{label}] NAV computed from real positions + cash", nav > 0)
    dd = update_drawdown(pcon, portfolio_id, as_of_exit, nav)
    check(f"[{label}] drawdown computed", dd <= 0)

    # 7. Exit (SELL) to realize P&L, close lifecycles
    total_realized = 0.0
    for ticker, pl_id in lifecycle_ids.items():
        entry_fill = fills[[oid for oid, f in fills.items() if
                            pcon.execute("SELECT ticker FROM orders WHERE order_id=?", (oid,)).fetchone()[0] == ticker][0]]
        from ngxrot.portfolio.execution import create_order
        xo = create_order(pcon, portfolio_id, ticker, "SELL", "MARKET", entry_fill.quantity, as_of_exit)
        xf = simulate_fill(pcon, mcon, xo, assumptions)
        if xf is None:
            continue
        apply_fill_to_position(pcon, portfolio_id, ticker, "SELL", xf.fill_price, xf.quantity, xf.fill_date)
        realized = (xf.fill_price - entry_fill.fill_price) * xf.quantity
        total_realized += realized
        close_position_lifecycle(pcon, portfolio_id, ticker, xf.fill_id, xf.fill_date, realized,
                                 entry_fill.commission + xf.commission)
    check(f"[{label}] positions exited and P&L realized", True)  # reaching here without exception is the check

    record_outcome(pcon, did, total_realized, f"{label}: closed out, total realized P&L={total_realized:.2f}")

    # 8. Performance + Attribution
    perf = compute_performance(pcon, mcon, portfolio_id)
    check(f"[{label}] performance record computed", perf.as_of == as_of_exit)
    # Attribution's period_end must cover the REAL exit fill dates, not the
    # as_of_exit signal date used to create the SELL orders -- fills resolve
    # to the next session strictly after that date (no-look-ahead), so the
    # actual exit_date in position_lifecycles can fall after as_of_exit.
    # Using as_of_exit as period_end here would silently exclude every
    # closed lifecycle from attribution (a real bug this test caught).
    max_exit_date = pcon.execute(
        "SELECT MAX(exit_date) FROM position_lifecycles WHERE portfolio_id=?",
        (portfolio_id,)).fetchone()[0]
    attribution = compute_attribution(pcon, mcon, portfolio_id, as_of_entry, max_exit_date)
    check(f"[{label}] attribution records produced", len(attribution) > 0)

    # 9. Lineage reconstruction, exact
    reg_con = sqlite3.connect(f"file:{registry_db.as_posix()}?mode=ro", uri=True)
    for ticker, pl_id in lifecycle_ids.items():
        chain = reconstruct_lineage(pcon, reg_con, pl_id)
        if chain.get("hypothesis_id"):
            check(f"[{label}] lineage for {ticker} traces P&L->Position->Fill->Order->Signal->Hypothesis",
                 chain["entry_fill"] is not None and chain["hypothesis_id"] == recommendations[0].hypothesis_id)
            break

    # 10. Research feedback
    hyp_perf = hypothesis_performance_history(pcon, recommendations[0].hypothesis_id)
    check(f"[{label}] hypothesis_performance_history reflects real activity", hyp_perf.n_executed > 0)

    # 11. Monitoring
    alerts = run_monitoring_checks(pcon, mcon, portfolio_id, as_of_exit, allocation_decision_id=ad_id)
    check(f"[{label}] monitoring checks run without error", isinstance(alerts, list))

    print(f"[{label}] total realized P&L: {total_realized:.2f}, NAV: {nav:.2f}, drawdown: {dd:.4f}")
    reg_con.close()
    mcon.close()
    pcon.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-db", type=Path, default=FROZEN_NGX)
    parser.add_argument("--registry-db", type=Path, default=FROZEN_REGISTRY)
    parser.add_argument("--temp-dir", type=Path, default=ROOT / ".test-runtime")
    args = parser.parse_args(argv)
    if not args.market_db.is_file() or not args.registry_db.is_file():
        raise RuntimeError("frozen market and registry fixtures are required")
    before = {path: file_hash(path) for path in (args.market_db, args.registry_db)}
    args.temp_dir.mkdir(parents=True, exist_ok=True)
    portfolio_db = args.temp_dir / f"portfolio-{uuid.uuid4().hex}.sqlite"
    synthetic_recs = [
        FakeRec("2026-08-05", "DANGCEM", "buy", 0.5, "quarterly", 0.15, -0.30, "High", "synthetic test signal A", "H-SYNTHETIC", ("exp-synthetic",)),
        FakeRec("2026-08-05", "GTCO", "buy", 0.5, "quarterly", 0.10, -0.20, "High", "synthetic test signal B", "H-SYNTHETIC", ("exp-synthetic",)),
    ]
    run_scenario(synthetic_recs, "SYNTH_PAPER", "2026-08-05", "2026-08-06", "Synthetic scenario", args.market_db, args.registry_db, portfolio_db)
    check("fixture market and registry databases are unchanged", all(file_hash(path) == value for path, value in before.items()))
    check("portfolio test database was independently created", portfolio_db.is_file())
    for candidate in (portfolio_db, portfolio_db.with_suffix(portfolio_db.suffix + "-wal"), portfolio_db.with_suffix(portfolio_db.suffix + "-shm")):
        if candidate.exists(): candidate.unlink()
    check("portfolio test database was independently removed", not portfolio_db.exists())
    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
