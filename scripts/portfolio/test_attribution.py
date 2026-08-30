"""Tests for ngxrot.portfolio.attribution (Phase 5), including the exact
lineage-reconstruction requirement (Phase 12's "Lineage" section).

  PYTHONPATH=src python scripts/portfolio/test_attribution.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot import registry as mreg  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.construction import record_signals  # noqa: E402
from ngxrot.portfolio.execution import create_order, simulate_fill, ExecutionAssumptions  # noqa: E402
from ngxrot.portfolio.performance import apply_fill_to_position  # noqa: E402
from ngxrot.portfolio.attribution import (  # noqa: E402
    open_position_lifecycle, close_position_lifecycle, compute_attribution, reconstruct_lineage)

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


p = pdb.new_scratch_db_path()
pcon = pdb.init_db(p)
pcon.execute("INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
            "inception_date,created_at) VALUES ('TEST','T','NGN',1000000,'2026-08-12','2026-08-12')")
pcon.commit()
mcon = mdb.connect()
assumptions = ExecutionAssumptions(slippage_bps=10, market_impact_bps=5)

recs = [FakeRec("2026-08-05", "DANGCEM", "buy", 1.0, "q", 0.15, -0.3, "High",
               "buy DANGCEM per H-011", "H-011", ("exp-real-1",))]
sigs = record_signals(pcon, recs)

entry_order = create_order(pcon, "TEST", "DANGCEM", "BUY", "MARKET", 100, "2026-08-05")
entry_fill = simulate_fill(pcon, mcon, entry_order, assumptions)
apply_fill_to_position(pcon, "TEST", "DANGCEM", "BUY", entry_fill.fill_price, entry_fill.quantity, entry_fill.fill_date)
pl_id = open_position_lifecycle(pcon, "TEST", "DANGCEM", entry_fill.fill_id, sigs[0].signal_id, "H-011", entry_fill.fill_date)
check("position_lifecycle opened", pl_id is not None)

# opening again while already open returns the SAME lifecycle (an add-to-position, not a duplicate)
pl_id_again = open_position_lifecycle(pcon, "TEST", "DANGCEM", entry_fill.fill_id, sigs[0].signal_id, "H-011", entry_fill.fill_date)
check("reopening an already-open lifecycle for the same ticker is idempotent", pl_id_again == pl_id)

exit_order = create_order(pcon, "TEST", "DANGCEM", "SELL", "MARKET", 100, "2026-08-06")
exit_fill = simulate_fill(pcon, mcon, exit_order, assumptions)
apply_fill_to_position(pcon, "TEST", "DANGCEM", "SELL", exit_fill.fill_price, exit_fill.quantity, exit_fill.fill_date)
realized_pnl = (exit_fill.fill_price - entry_fill.fill_price) * 100
total_cost = entry_fill.commission + exit_fill.commission
closed_id = close_position_lifecycle(pcon, "TEST", "DANGCEM", exit_fill.fill_id, exit_fill.fill_date,
                                     realized_pnl, total_cost)
check("lifecycle closed, returns the same id", closed_id == pl_id)

row = pcon.execute("SELECT exit_date, holding_period_days, realized_pnl, total_cost FROM "
                   "position_lifecycles WHERE position_lifecycle_id=?", (pl_id,)).fetchone()
check("holding_period_days computed correctly (entry 08-05/exit-fill 08-06/08-07 span)", row[1] >= 1)
check("realized_pnl and total_cost persisted exactly", row[2] == realized_pnl and row[3] == total_cost)

# closing an already-closed / non-existent lifecycle returns None, not an error
none_result = close_position_lifecycle(pcon, "TEST", "A_TICKER_NEVER_OPENED", "F-x", "2026-08-06", 0, 0)
check("closing a lifecycle that was never opened returns None, not an error/exception", none_result is None)

# --- attribution ---
records = compute_attribution(pcon, mcon, "TEST", "2026-08-01", "2026-08-31")
by_dim = {(r["dimension"], r["dimension_value"]) for r in records}
check("attribution includes a ticker-dimension record for DANGCEM", ("ticker", "DANGCEM") in by_dim)
check("attribution includes a hypothesis-dimension record for H-011", ("hypothesis", "H-011") in by_dim)
check("attribution includes a signal-dimension record", any(d == "signal" for d, _ in by_dim))
check("ticker attribution pnl matches the realized_pnl exactly",
     next(r["pnl"] for r in records if r["dimension"] == "ticker") == realized_pnl)
check("single-position period: contribution_pct is 1.0 (100% of period P&L)",
     next(r["contribution_pct"] for r in records if r["dimension"] == "ticker") == 1.0)

# --- exact lineage reconstruction: P&L -> Position -> Fill -> Order -> Signal -> Hypothesis ---
reg_con = mreg.connect_registry()
chain = reconstruct_lineage(pcon, reg_con, pl_id)
check("lineage: realized_pnl matches exactly", chain["realized_pnl"] == realized_pnl)
check("lineage: entry_fill resolves to the real entry fill_id", chain["entry_fill"]["fill_id"] == entry_fill.fill_id)
check("lineage: exit_fill resolves to the real exit fill_id", chain["exit_fill"]["fill_id"] == exit_fill.fill_id)
check("lineage: entry order side is BUY", chain["entry_fill"]["order"]["side"] == "BUY")
check("lineage: exit order side is SELL", chain["exit_fill"]["order"]["side"] == "SELL")
check("lineage: signal resolves back to the exact signal recorded", chain["signal"]["signal_id"] == sigs[0].signal_id)
check("lineage: hypothesis_id is H-011", chain["hypothesis_id"] == "H-011")
check("lineage: real hypothesis record pulled from registry.sqlite (read-only)",
     chain["hypothesis"]["hypothesis_id"] == "H-011" and chain["hypothesis"]["status"] == "confirmed")
check("lineage: real experiment records pulled from registry.sqlite (H-011 has real experiments on record)",
     len(chain["experiments"]) > 0)

# --- lineage with no registry_con: chain stops at hypothesis_id, still complete within portfolio.sqlite ---
chain_no_reg = reconstruct_lineage(pcon, None, pl_id)
check("lineage without a registry connection still resolves fill/order/signal chain",
     chain_no_reg["entry_fill"]["fill_id"] == entry_fill.fill_id and chain_no_reg["hypothesis_id"] == "H-011")
check("lineage without a registry connection has no 'hypothesis'/'experiments' keys (not fabricated)",
     "hypothesis" not in chain_no_reg and "experiments" not in chain_no_reg)

# --- unknown lifecycle raises, not silently returns empty ---
try:
    reconstruct_lineage(pcon, reg_con, "PL-does-not-exist")
    check("unknown position_lifecycle_id raises", False)
except ValueError:
    check("unknown position_lifecycle_id raises", True)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
