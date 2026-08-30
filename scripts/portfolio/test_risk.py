"""Tests for ngxrot.portfolio.risk (Phase 2).

  PYTHONPATH=src python scripts/portfolio/test_risk.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.construction import record_signals, construct_portfolio  # noqa: E402
from ngxrot.portfolio.risk import create_risk_policy, review_allocation, update_drawdown  # noqa: E402

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

recs = [
    FakeRec("2026-08-07", "DANGCEM", "buy", 0.25, "q", 0.15, -0.30, "High", "r", "H-011"),
    FakeRec("2026-08-07", "GTCO", "buy", 0.25, "q", 0.10, -0.20, "High", "r", "H-011"),
    FakeRec("2026-08-07", "ZENITHBANK", "buy", 0.25, "q", 0.05, -0.10, "High", "r", "H-011"),
    FakeRec("2026-08-07", "MCNICHOLS", "buy", 0.25, "q", 0.20, -0.10, "High", "r", "H-011"),
]
sigs = record_signals(pcon, recs)

# --- position limit rejection ---
ad1, _ = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
review_no_policy = review_allocation(pcon, mcon, ad1, 1_000_000, "2026-08-07")
check("no risk_policy configured -> REJECTED by construction", review_no_policy.risk_status == "REJECTED")

create_risk_policy(pcon, "TEST", max_position_weight=0.10, max_gross_exposure=1.1,
                   max_net_exposure=1.1, max_participation_rate=0.20)
ad2, _ = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
review_strict = review_allocation(pcon, mcon, ad2, 1_000_000, "2026-08-07")
check("strict max_position_weight=0.10 vs 0.25 actual -> REJECTED", review_strict.risk_status == "REJECTED")
check("rejection reason names the specific breach", any(
    c.status == "fail" and "exceeds max_position_weight" in c.reason for c in review_strict.checks))

# --- lenient policy approval ---
create_risk_policy(pcon, "TEST", max_position_weight=0.30, max_gross_exposure=1.1,
                   max_net_exposure=1.1, max_participation_rate=0.20, max_sector_exposure=0.60,
                   max_single_name_exposure=0.30)
ad3, _ = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
review_lenient = review_allocation(pcon, mcon, ad3, 1_000_000, "2026-08-07")
check("lenient policy (0.30 limit vs 0.25 actual) -> APPROVED", review_lenient.risk_status == "APPROVED")
check("all checks recorded for the lenient review", len(review_lenient.checks) > 0)

# --- zero/negative position handling: no target positions at all ---
sigs_empty = record_signals(pcon, [r for r in recs if False])
ad4, positions_empty = construct_portfolio(pcon, mcon, "TEST", sigs_empty, "equal_weight", "2026-08-07")
review_empty = review_allocation(pcon, mcon, ad4, 1_000_000, "2026-08-07")
check("zero target positions -> APPROVED trivially (no exposure, no violation possible)",
     review_empty.risk_status == "APPROVED")

# --- liquidity/participation rejection with a tiny threshold ---
create_risk_policy(pcon, "TEST", max_position_weight=0.99, max_gross_exposure=1.1,
                   max_net_exposure=1.1, max_participation_rate=0.0001)
ad5, _ = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
review_illiquid = review_allocation(pcon, mcon, ad5, 1_000_000, "2026-08-07")
check("near-zero max_participation_rate -> REJECTED on liquidity",
     review_illiquid.risk_status == "REJECTED" and
     any(c.check_type == "liquidity" and c.status == "fail" for c in review_illiquid.checks))

# --- sector concentration ---
create_risk_policy(pcon, "TEST", max_position_weight=0.99, max_gross_exposure=1.1,
                   max_net_exposure=1.1, max_participation_rate=0.20, max_sector_exposure=0.10)
ad6, _ = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
review_sector = review_allocation(pcon, mcon, ad6, 1_000_000, "2026-08-07")
check("tight max_sector_exposure -> REJECTED on at least one sector",
     review_sector.risk_status == "REJECTED" and
     any(c.check_type == "sector_exposure" and c.status == "fail" for c in review_sector.checks))

# --- drawdown detection ---
dd1 = update_drawdown(pcon, "TEST", "2026-08-01", 1_000_000)
check("drawdown at peak (first observation) is zero", dd1 == 0.0)
dd2 = update_drawdown(pcon, "TEST", "2026-08-05", 900_000)
check("drawdown after a 10% decline is -0.10", abs(dd2 - (-0.10)) < 1e-9)
dd3 = update_drawdown(pcon, "TEST", "2026-08-06", 950_000)
check("drawdown recovers toward zero but peak stays at the historical high",
     abs(dd3 - ((950_000 - 1_000_000) / 1_000_000)) < 1e-9)

# --- same-day policy tiebreak (the real bug this module's development found and fixed) ---
create_risk_policy(pcon, "TEST", max_position_weight=0.99, max_gross_exposure=1.1,
                   max_net_exposure=1.1, max_participation_rate=0.99)  # lenient, created first
create_risk_policy(pcon, "TEST", max_position_weight=0.01, max_gross_exposure=1.1,
                   max_net_exposure=1.1, max_participation_rate=0.99)  # strict, created SECOND, same day
ad7, _ = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
review_tiebreak = review_allocation(pcon, mcon, ad7, 1_000_000, "2026-08-07")
check("two policies created same day -> the LATER one (strict) wins, not the earlier lenient one",
     review_tiebreak.risk_status == "REJECTED")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
