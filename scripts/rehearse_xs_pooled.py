"""Synthetic rehearsal of the 2026-07-22 pooled overlapping-cohort
momentum extension (E1 in docs/EXECUTION_BACKLOG.md — unlocks H-010 /
Wave-3 candidate C1). Same discipline as every prior engine addition.

  python -u scripts/rehearse_xs_pooled.py

R10 planted persistent momentum (same panel as rehearse_xs_engine.py's
    R1) -> pooled run recovers positive excess, placebo p <= 0.05.
R11 null (IID) panel -> placebo p > 0.05 (pooling itself creates no false
    signal).
R12 cohort correlation is MEASURED, not assumed: on the planted-momentum
    panel, the average pairwise cohort return-correlation must be
    meaningfully below 1.0 (offsets genuinely decorrelate) — if this
    ever came back ~1.0, the "N independent bets" claim in any future
    H-010 prereg would be false regardless of how clean the code looks.
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db, backtest_xs, metrics, stats, runner  # noqa: E402

RNG = np.random.default_rng(20260722)
RATES = {"buy_rate": 0.019, "sell_rate": 0.019, "line_items": {}}
TICKS = [f"SYN{i:03d}" for i in range(60)]
DATES = pd.bdate_range("2016-01-04", "2023-12-29")


def make_db(returns: pd.DataFrame):
    tmp = Path(tempfile.mkdtemp()) / "rehearsal.sqlite"
    con = db.init_db(tmp)
    px = (100 * (1 + returns).cumprod())
    rows = []
    for t in returns.columns:
        for dt, c in px[t].items():
            rows.append((t, dt.strftime("%Y-%m-%d"), float(c), 1_000_000,
                         5_000_000.0, 50, 1, 0.9, "2026-07-21"))
    con.execute("INSERT OR IGNORE INTO sources (source_id, name, kind, "
                "reliability, base_confidence) VALUES (1,'rehearsal','x','x',0.9)")
    for t in returns.columns:
        con.execute("INSERT OR IGNORE INTO securities (ticker, name) "
                    "VALUES (?,?)", (t, t))
    con.executemany(
        "INSERT INTO equity_prices (ticker, trade_date, close, volume, "
        "value_traded, deals, source_id, confidence, as_of_date) "
        "VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    return con


def base_cfg(n_cohorts: int) -> dict:
    return runner.apply_defaults({
        "experiment": {"name": "rehearsal", "stage": "development"},
        "data": {"sim_start": "2017-06-01", "sim_end": "2023-12-29",
                 "sources": ["rehearsal"], "min_confidence": 0.9,
                 "vintage": "2026-07-21", "universe": [], "benchmark": "EW"},
        "signal": {"method": "xs_rank_pooled", "formation_months": 12,
                   "skip_months": 1, "min_obs_formation": 120,
                   "n_cohorts": n_cohorts},
        "portfolio": {"top_n": 12, "rebalance": "annual",
                      "execution_lag_days": 1},
        "engine": {"aum_ngn": 1e9},
        "liquidity": {"adtv_participation_cap_pct": 10.0},
        "validation": {"risk_free_annual_pct": 0.0},
    })


def planted_momentum() -> pd.DataFrame:
    n, k = len(DATES), len(TICKS)
    drift = np.zeros((n, k))
    a = RNG.normal(0, 0.0006, k)
    for i in range(n):
        if i % 21 == 0:
            a = 0.97 * a + RNG.normal(0, 0.0002, k)
        drift[i] = a
    noise = RNG.normal(0, 0.012, (n, k))
    return pd.DataFrame(drift + noise, index=DATES, columns=TICKS)


def iid_panel() -> pd.DataFrame:
    return pd.DataFrame(RNG.normal(0.0003, 0.012, (len(DATES), len(TICKS))),
                        index=DATES, columns=TICKS)


print("R10: planted persistent momentum, xs_rank_pooled (4 cohorts) ...")
con10 = make_db(planted_momentum())
cfg = base_cfg(4)
result, diag = backtest_xs.pooled_rank_run(con10, cfg, RATES)
m = metrics.compute(result, 0.0)
gen = np.random.default_rng(7)
real, plac = backtest_xs.placebo_stats(con10, cfg, RATES, 40, gen)
p10 = stats.placebo_p_value(real, plac)
print(f"  net excess {m['excess_return_ann']:+.2%} | sharpe {real} | "
      f"placebo p={p10:.3f}")
print(f"  cohort turnover: {diag['cohort_ann_turnover_oneway']}")
r10 = m["excess_return_ann"] > 0 and p10 <= 0.05

print("R11: IID null panel, xs_rank_pooled ...")
con11 = make_db(iid_panel())
result11, diag11 = backtest_xs.pooled_rank_run(con11, cfg, RATES)
m11 = metrics.compute(result11, 0.0)
gen = np.random.default_rng(7)
real11, plac11 = backtest_xs.placebo_stats(con11, cfg, RATES, 40, gen)
p11 = stats.placebo_p_value(real11, plac11)
print(f"  net excess {m11['excess_return_ann']:+.2%} | placebo p={p11:.3f}")
r11 = p11 > 0.05

print("R12: cohort correlation measured directly (planted-momentum panel) ...")
corr = pd.DataFrame(diag["cohort_return_correlation"])
offdiag = corr.values[~np.eye(len(corr), dtype=bool)]
mean_offdiag = float(np.mean(offdiag))
print(f"  cohort correlation matrix:\n{corr.round(3)}")
print(f"  mean off-diagonal correlation: {mean_offdiag:.3f}")
r12 = mean_offdiag < 0.95  # genuinely decorrelated, not a degenerate 1.0

print()
for name, ok in [("R10 planted momentum recovered (pooled)", r10),
                 ("R11 null panel stays null (pooled)", r11),
                 ("R12 cohort correlation measured, non-degenerate", r12)]:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
sys.exit(0 if all([r10, r11, r12]) else 1)
