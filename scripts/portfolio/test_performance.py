"""Tests for ngxrot.portfolio.performance (Phase 4).

  PYTHONPATH=src python scripts/portfolio/test_performance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.performance import (  # noqa: E402
    apply_fill_to_position, mark_to_market, record_nav, compute_performance)

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
mcon = mdb.connect()

# --- position accounting: weighted-average cost on successive buys ---
apply_fill_to_position(pcon, "TEST", "DANGCEM", "BUY", 100.0, 10, "2026-08-01")
row = pcon.execute("SELECT quantity, average_cost, realized_pnl FROM positions "
                   "WHERE portfolio_id='TEST' AND ticker='DANGCEM' ORDER BY as_of DESC LIMIT 1").fetchone()
check("first buy: quantity=10, average_cost=100", row == (10.0, 100.0, 0.0))

apply_fill_to_position(pcon, "TEST", "DANGCEM", "BUY", 200.0, 10, "2026-08-02")
row2 = pcon.execute("SELECT quantity, average_cost FROM positions "
                    "WHERE portfolio_id='TEST' AND ticker='DANGCEM' ORDER BY as_of DESC LIMIT 1").fetchone()
check("second buy at 200: quantity=20, average_cost=150 (weighted average)", row2 == (20.0, 150.0))

# --- realized P&L on a sell ---
apply_fill_to_position(pcon, "TEST", "DANGCEM", "SELL", 180.0, 5, "2026-08-03")
row3 = pcon.execute("SELECT quantity, average_cost, realized_pnl FROM positions "
                    "WHERE portfolio_id='TEST' AND ticker='DANGCEM' ORDER BY as_of DESC LIMIT 1").fetchone()
check("sell 5 @180 from avg_cost 150: quantity=15, realized_pnl = 5*(180-150) = 150",
     row3[0] == 15.0 and abs(row3[2] - 150.0) < 1e-9)
check("average_cost unchanged by a sell", row3[1] == 150.0)

# --- NAV computation ---
mark_to_market(pcon, mcon, "TEST", "2026-08-07")  # real market data for whatever's held
nav = record_nav(pcon, "TEST", "2026-08-07", cash=500_000.0, track_record_status="PAPER")
check("NAV = cash + positions_value, both real numbers", nav >= 500_000.0)

row_nav = pcon.execute("SELECT track_record_status FROM nav_snapshots WHERE portfolio_id='TEST' "
                       "AND as_of='2026-08-07'").fetchone()
check("track_record_status recorded as PAPER, not fabricated as LIVE", row_nav[0] == "PAPER")

try:
    record_nav(pcon, "TEST", "2026-08-08", cash=500_000.0, track_record_status="LIVE")
    check("recording track_record_status='LIVE' is refused (hard constraint)", False)
except ValueError:
    check("recording track_record_status='LIVE' is refused (hard constraint)", True)

# --- performance computation over a short synthetic NAV series ---
p2 = pdb.new_scratch_db_path()
pcon2 = pdb.init_db(p2)
pcon2.execute("INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
             "inception_date,created_at) VALUES ('PERF','T','NGN',1000000,'2026-08-01','2026-08-01')")
pcon2.commit()
navs = [("2026-08-01", 1_000_000), ("2026-08-02", 1_010_000), ("2026-08-03", 990_000),
       ("2026-08-04", 1_020_000), ("2026-08-05", 1_050_000)]
for d, n in navs:
    pcon2.execute("INSERT INTO nav_snapshots (portfolio_id, as_of, cash, positions_value, nav, "
                 "track_record_status) VALUES ('PERF', ?, 0, ?, ?, 'PAPER')", (d, n, n))
pcon2.commit()
perf = compute_performance(pcon2, mcon, "PERF")
check("cumulative_return computed correctly (1,050,000/1,000,000 - 1 = 0.05)",
     abs(perf.cumulative_return - 0.05) < 1e-9)
check("volatility_ann computed with >=2 return observations", perf.volatility_ann is not None)
check("max_drawdown is negative (there was a real decline day 2->3)", perf.max_drawdown < 0)
check("track_record_status propagates from nav_snapshots", perf.track_record_status == "PAPER")

# --- single-observation series: Sharpe/Sortino/vol left None, not fabricated ---
p3 = pdb.new_scratch_db_path()
pcon3 = pdb.init_db(p3)
pcon3.execute("INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
             "inception_date,created_at) VALUES ('ONE','T','NGN',1000000,'2026-08-01','2026-08-01')")
pcon3.commit()
pcon3.execute("INSERT INTO nav_snapshots (portfolio_id, as_of, cash, positions_value, nav, "
             "track_record_status) VALUES ('ONE', '2026-08-01', 0, 1000000, 1000000, 'PAPER')")
pcon3.commit()
perf_one = compute_performance(pcon3, mcon, "ONE")
check("single NAV observation: volatility_ann is None, not a fabricated number",
     perf_one.volatility_ann is None)
check("single NAV observation: sharpe is None", perf_one.sharpe is None)

# --- benchmark: explicit opt-in only ---
perf_no_bench = compute_performance(pcon2, mcon, "PERF", benchmark_id=None)
check("no benchmark configured -> benchmark fields are None, never invented",
     perf_no_bench.benchmark_id is None and perf_no_bench.benchmark_cumulative_return is None)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
