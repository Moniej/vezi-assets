"""Tests for ngxrot.portfolio.journal (Phase 6).

  PYTHONPATH=src python scripts/portfolio/test_journal.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.construction import record_signals  # noqa: E402
from ngxrot.portfolio.execution import create_order, simulate_fill, ExecutionAssumptions  # noqa: E402
from ngxrot.portfolio.performance import apply_fill_to_position  # noqa: E402
from ngxrot.portfolio.attribution import open_position_lifecycle, close_position_lifecycle  # noqa: E402
from ngxrot.portfolio.journal import (  # noqa: E402
    record_decision, record_outcome, get_decision, hypothesis_performance_history)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


p = pdb.new_scratch_db_path()
pcon = pdb.init_db(p)
pcon.execute("INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
            "inception_date,created_at) VALUES ('TEST','T','NGN',1000000,'2026-08-12','2026-08-12')")
pcon.commit()

did = record_decision(pcon, "TEST", "ALLOCATE", "H-011 signal, risk-approved",
                      {"nav": 1_000_000}, {"status": "APPROVED"}, hypothesis_id="H-011")
d = get_decision(pcon, did)
check("decision recorded and readable", d["decision"] == "ALLOCATE" and d["hypothesis_id"] == "H-011")
check("actual_outcome_pnl/postmortem start NULL", d["actual_outcome_pnl"] is None and d["postmortem"] is None)

record_outcome(pcon, did, 12345.67, "position closed positive, thesis played out as expected")
d2 = get_decision(pcon, did)
check("outcome update sets pnl/postmortem", d2["actual_outcome_pnl"] == 12345.67)
check("outcome update does not disturb the original decision/rationale",
     d2["decision"] == d["decision"] and d2["rationale"] == d["rationale"])

# --- immutability: only actual_outcome_pnl/postmortem may ever change ---
try:
    pcon.execute("UPDATE decision_journal SET rationale=? WHERE decision_id=?", ("rewritten", did))
    check("rewriting rationale is blocked", False)
except Exception:
    check("rewriting rationale is blocked", True)
try:
    pcon.execute("UPDATE decision_journal SET decision=? WHERE decision_id=?", ("REBALANCE", did))
    check("rewriting decision is blocked", False)
except Exception:
    check("rewriting decision is blocked", True)
try:
    pcon.execute("DELETE FROM decision_journal WHERE decision_id=?", (did,))
    check("deleting a decision is blocked", False)
except Exception:
    check("deleting a decision is blocked", True)
# but a SECOND legitimate outcome update (both allowed columns) must still work
record_outcome(pcon, did, 99999.0, "revised postmortem after further review")
d3 = get_decision(pcon, did)
check("a second legitimate outcome update (allowed columns only) succeeds",
     d3["actual_outcome_pnl"] == 99999.0)

check("unknown decision_id returns None, not an error", get_decision(pcon, "DJ-not-real") is None)

# --- research feedback loop ---
@dataclass(frozen=True)
class FakeRec:
    as_of: str; instrument: str; action: str; size_pct_nav: float
    horizon: str; expected_excess_ann: float; expected_max_drawdown: float
    confidence_rating: str; rationale: str; hypothesis_id: str
    experiment_ids: tuple = (); caveats: tuple = ()

mcon = mdb.connect()
assumptions = ExecutionAssumptions(slippage_bps=10, market_impact_bps=5)
recs = [FakeRec("2026-08-05", "DANGCEM", "buy", 1.0, "q", 0.15, -0.3, "High", "r", "H-011")]
sigs = record_signals(pcon, recs)
eo = create_order(pcon, "TEST", "DANGCEM", "BUY", "MARKET", 100, "2026-08-05")
ef = simulate_fill(pcon, mcon, eo, assumptions)
apply_fill_to_position(pcon, "TEST", "DANGCEM", "BUY", ef.fill_price, ef.quantity, ef.fill_date)
pl_id = open_position_lifecycle(pcon, "TEST", "DANGCEM", ef.fill_id, sigs[0].signal_id, "H-011", ef.fill_date)
xo = create_order(pcon, "TEST", "DANGCEM", "SELL", "MARKET", 100, "2026-08-06")
xf = simulate_fill(pcon, mcon, xo, assumptions)
apply_fill_to_position(pcon, "TEST", "DANGCEM", "SELL", xf.fill_price, xf.quantity, xf.fill_date)
pnl = (xf.fill_price - ef.fill_price) * 100
close_position_lifecycle(pcon, "TEST", "DANGCEM", xf.fill_id, xf.fill_date, pnl, ef.commission + xf.commission)

perf = hypothesis_performance_history(pcon, "H-011")
check("hypothesis_performance_history: n_signals counted", perf.n_signals == 1)
check("hypothesis_performance_history: n_executed counts BOTH entry and exit orders (real bug fixed)",
     perf.n_executed == 2)
check("hypothesis_performance_history: realized_pnl matches the real closed lifecycle", perf.realized_pnl == pnl)
check("hypothesis_performance_history: n_closed_positions=1", perf.n_closed_positions == 1)
check("hypothesis_performance_history: regime_breakdown explicitly discloses it is not built",
     "NOT BUILT" in perf.regime_breakdown)

# a hypothesis with zero activity returns zeros, not an error
perf_empty = hypothesis_performance_history(pcon, "H-999-NEVER-USED")
check("hypothesis with no signals/lifecycles returns zeros cleanly, not an error",
     perf_empty.n_signals == 0 and perf_empty.n_closed_positions == 0 and perf_empty.win_rate is None)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
