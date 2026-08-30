"""Tests for ngxrot.portfolio.construction (Phase 1).

  PYTHONPATH=src python scripts/portfolio/test_construction.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
from ngxrot.portfolio.construction import (  # noqa: E402
    record_signals, construct_portfolio, construct_portfolio_from_weights)

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


def _setup():
    p = pdb.new_scratch_db_path()
    pcon = pdb.init_db(p)
    pcon.execute("INSERT INTO portfolios (portfolio_id,name,base_currency,initial_capital,"
                "inception_date,created_at) VALUES ('TEST','T','NGN',1000000,'2026-08-12','2026-08-12')")
    pcon.commit()
    return pcon, mdb.connect()


recs = [
    FakeRec("2026-08-07", "DANGCEM", "buy", 0.25, "quarterly", 0.15, -0.30, "High", "r", "H-011"),
    FakeRec("2026-08-07", "GTCO", "buy", 0.25, "quarterly", 0.10, -0.20, "High", "r", "H-011"),
    FakeRec("2026-08-07", "ZENITHBANK", "buy", 0.25, "quarterly", 0.05, -0.10, "High", "r", "H-011"),
    FakeRec("2026-08-07", "MCNICHOLS", "buy", 0.25, "quarterly", 0.20, -0.10, "High", "r", "H-011"),
    FakeRec("2026-08-07", "OANDO", "sell", None, "quarterly", None, None, "High", "avoid", "H-011"),
]

pcon, mcon = _setup()
sigs = record_signals(pcon, recs)
check("record_signals persists exactly one row per recommendation", len(sigs) == len(recs))
check("signals table has the same count", pcon.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == len(recs))

# equal_weight: only 'buy' actions get weight, sum to 1
ad_id, positions = construct_portfolio(pcon, mcon, "TEST", sigs, "equal_weight", "2026-08-07", current_nav=1_000_000)
check("equal_weight excludes non-buy signals (4 buys, 1 sell -> 4 positions)", len(positions) == 4)
check("equal_weight: each position gets 1/4", all(abs(p.target_weight - 0.25) < 1e-9 for p in positions))
check("equal_weight: weights sum to 1.0", abs(sum(p.target_weight for p in positions) - 1.0) < 1e-9)
check("equal_weight: notional = weight * NAV", all(abs(p.target_notional - p.target_weight * 1_000_000) < 1e-6 for p in positions))

# signal_weighted: renormalizes size_pct_nav
ad_id2, positions2 = construct_portfolio(pcon, mcon, "TEST", sigs, "signal_weighted", "2026-08-07", current_nav=1_000_000)
check("signal_weighted: weights sum to 1.0", abs(sum(p.target_weight for p in positions2) - 1.0) < 1e-9)

# rank_weighted: highest expected_excess_ann gets the largest weight
ad_id3, positions3 = construct_portfolio(pcon, mcon, "TEST", sigs, "rank_weighted", "2026-08-07", current_nav=1_000_000)
by_ticker = {p.ticker: p.target_weight for p in positions3}
check("rank_weighted: MCNICHOLS (highest expected_excess_ann=0.20) gets the largest weight",
     by_ticker["MCNICHOLS"] == max(by_ticker.values()))
check("rank_weighted: weights sum to 1.0", abs(sum(by_ticker.values()) - 1.0) < 1e-9)

# volatility_scaled: real market data, inverse-vol weighting
ad_id4, positions4 = construct_portfolio(pcon, mcon, "TEST", sigs, "volatility_scaled", "2026-08-07", current_nav=1_000_000)
check("volatility_scaled: produces positions from real market data", len(positions4) > 0)
check("volatility_scaled: weights sum to ~1.0", abs(sum(p.target_weight for p in positions4) - 1.0) < 1e-6)

# zero/no buy signals -> zero positions, not an error
no_buys = [r for r in recs if r.action != "buy"]
sigs_no_buy = record_signals(pcon, no_buys)
ad_id5, positions5 = construct_portfolio(pcon, mcon, "TEST", sigs_no_buy, "equal_weight", "2026-08-07")
check("zero buy signals: produces zero target positions, not an error", len(positions5) == 0)

# custom weights via construct_portfolio_from_weights
ad_id6, positions6 = construct_portfolio_from_weights(
    pcon, "TEST", sigs, {"DANGCEM": 0.6, "GTCO": 0.4}, "custom", "2026-08-07", current_nav=1_000_000)
check("custom weights: exact weights preserved", {p.ticker: p.target_weight for p in positions6} == {"DANGCEM": 0.6, "GTCO": 0.4})

# invalid method rejected
try:
    construct_portfolio(pcon, mcon, "TEST", sigs, "not_a_real_method", "2026-08-07")
    check("invalid construction method raises", False)
except ValueError:
    check("invalid construction method raises", True)

# signals and target_positions are immutable
try:
    pcon.execute("UPDATE signals SET action='hold' WHERE signal_id=?", (sigs[0].signal_id,))
    check("signals table rejects UPDATE", False)
except Exception:
    check("signals table rejects UPDATE", True)
try:
    pcon.execute("UPDATE target_positions SET target_weight=0.99 WHERE target_position_id=?",
                (positions[0].target_position_id,))
    check("target_positions table rejects UPDATE", False)
except Exception:
    check("target_positions table rejects UPDATE", True)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
