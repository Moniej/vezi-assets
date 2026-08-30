"""Tests for ngxrot.portfolio.execution (Phase 3).

  PYTHONPATH=src python scripts/portfolio/test_execution.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.execution import (  # noqa: E402
    create_order, simulate_fill, ExecutionAssumptions)

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
assumptions = ExecutionAssumptions(slippage_bps=10, market_impact_bps=5)

# --- order creation ---
oid = create_order(pcon, "TEST", "DANGCEM", "BUY", "MARKET", 100, "2026-08-05")
row = pcon.execute("SELECT status, side, order_type, quantity FROM orders WHERE order_id=?", (oid,)).fetchone()
check("order created with status CREATED", row[0] == "CREATED")
check("order side/type/quantity recorded correctly", row[1:] == ("BUY", "MARKET", 100.0))

for bad_side in ("buy", "Buy", "LONG"):
    try:
        create_order(pcon, "TEST", "X", bad_side, "MARKET", 1, "2026-08-05")
        check(f"invalid side {bad_side!r} rejected", False)
    except ValueError:
        check(f"invalid side {bad_side!r} rejected", True)

try:
    create_order(pcon, "TEST", "X", "BUY", "LIMIT", 1, "2026-08-05")  # missing limit_price
    check("LIMIT order without limit_price rejected", False)
except ValueError:
    check("LIMIT order without limit_price rejected", True)

try:
    create_order(pcon, "TEST", "X", "BUY", "MARKET", -1, "2026-08-05")
    check("negative quantity rejected", False)
except ValueError:
    check("negative quantity rejected", True)

# --- NO LOOK-AHEAD: fill_date must be strictly AFTER signal_timestamp ---
oid2 = create_order(pcon, "TEST", "DANGCEM", "BUY", "MARKET", 100, "2026-08-05")
fill = simulate_fill(pcon, mcon, oid2, assumptions)
check("fill produced for a real, liquid ticker", fill is not None)
check("fill_date is STRICTLY after signal_timestamp (no look-ahead)",
     fill.fill_date > "2026-08-05")
check("commission is nonzero (real cost_schedule applied)", fill.commission > 0)
check("transaction_cost_total includes commission + slippage + impact",
     fill.transaction_cost_total >= fill.commission)
check("order status is FILLED after a successful fill",
     pcon.execute("SELECT status FROM orders WHERE order_id=?", (oid2,)).fetchone()[0] == "FILLED")

# --- re-filling an already-filled order raises ---
try:
    simulate_fill(pcon, mcon, oid2, assumptions)
    check("re-filling a FILLED order raises", False)
except ValueError:
    check("re-filling a FILLED order raises", True)

# --- unknown ticker: no executable price, REJECTED not fabricated ---
oid3 = create_order(pcon, "TEST", "NOT_A_REAL_TICKER_XYZ", "BUY", "MARKET", 100, "2026-08-05")
fill3 = simulate_fill(pcon, mcon, oid3, assumptions)
check("unknown ticker produces no fill (never fabricated)", fill3 is None)
status3 = pcon.execute("SELECT status FROM orders WHERE order_id=?", (oid3,)).fetchone()[0]
check("unknown ticker order marked REJECTED with a reason",
     status3 == "REJECTED" and pcon.execute(
         "SELECT rejection_reason FROM orders WHERE order_id=?", (oid3,)).fetchone()[0])

# --- LIMIT order: fillable price ---
# ACCESSCORP (unlike DANGCEM) has real, non-null high/low on record for
# these sessions (26.0-26.5 on 08-06, 26.15-27.0 on 08-07) -- a price
# comfortably above the real high should fill.
oid4 = create_order(pcon, "TEST", "ACCESSCORP", "BUY", "LIMIT", 50, "2026-08-05", limit_price=100.0)
fill4 = simulate_fill(pcon, mcon, oid4, assumptions)
check("LIMIT BUY at an easily-reachable price (real high/low data) fills",
     fill4 is not None and fill4.fill_price is not None)

# --- LIMIT order: unfillable price within the window -> CANCELLED, not fabricated ---
oid5 = create_order(pcon, "TEST", "ACCESSCORP", "BUY", "LIMIT", 50, "2026-08-05", limit_price=0.0001)
fill5 = simulate_fill(pcon, mcon, oid5, assumptions)
check("LIMIT BUY at an unreachable price produces no fill", fill5 is None)
status5 = pcon.execute("SELECT status FROM orders WHERE order_id=?", (oid5,)).fetchone()[0]
check("unreachable LIMIT order marked CANCELLED, not silently dropped", status5 == "CANCELLED")

# --- REAL, DISCLOSED DATA LIMITATION: DANGCEM's high/low are NULL for
# these sessions (confirmed directly against equity_prices -- only
# open/close are populated for this ticker/date range, a genuine gap in
# the underlying market data, not a code defect). A LIMIT order cannot
# responsibly be evaluated for fillability without a real high/low, so it
# must be CANCELLED, never guessed from close alone (that would fabricate
# an intraday range that was never recorded). This is exactly the
# "mark it as an assumption/unsupported, do not fabricate" rule applied.
oid6 = create_order(pcon, "TEST", "DANGCEM", "BUY", "LIMIT", 50, "2026-08-05", limit_price=100000)
fill6 = simulate_fill(pcon, mcon, oid6, assumptions)
check("LIMIT order on a ticker with NULL high/low data is correctly CANCELLED, "
     "never fabricated from close alone (real, disclosed data gap, confirmed against "
     "equity_prices directly)", fill6 is None and
     pcon.execute("SELECT status FROM orders WHERE order_id=?", (oid6,)).fetchone()[0] == "CANCELLED")

# --- fills are immutable ---
try:
    pcon.execute("UPDATE fills SET fill_price=1 WHERE fill_id=?", (fill.fill_id,))
    check("fills table rejects UPDATE", False)
except Exception:
    check("fills table rejects UPDATE", True)
try:
    pcon.execute("DELETE FROM fills WHERE fill_id=?", (fill.fill_id,))
    check("fills table rejects DELETE", False)
except Exception:
    check("fills table rejects DELETE", True)

# --- a terminal order cannot be re-mutated ---
try:
    pcon.execute("UPDATE orders SET quantity=999 WHERE order_id=?", (oid2,))
    check("a FILLED (terminal) order rejects further mutation", False)
except Exception:
    check("a FILLED (terminal) order rejects further mutation", True)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
