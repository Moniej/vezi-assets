"""Synthetic rehearsal of the 2026-07-22 engine extensions: xs_vol
(low-volatility signal) and annual/semiannual rebalance cadence for
xs_rank. Same discipline as rehearse_xs_engine.py — nothing here touches
the real database or the registry.

  python -u scripts/rehearse_xs_engine_v2.py

R5 xs_vol on a panel with a PLANTED low-vol premium (low-vol names drift
   up slightly faster net of vol, matching the textbook anomaly) ->
   positive net excess, placebo p <= 0.05.
R6 xs_vol on a panel where vol and forward return are UNRELATED -> placebo
   p > 0.05 (no false signal from the vol sort alone).
R7 xs_rank at annual rebalance materially cuts turnover vs quarterly on
   the SAME planted-momentum panel from rehearse_xs_engine.py's R1
   (turnover check, not a re-proof of momentum recovery).
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


def base_cfg(method: str, rebalance: str, **sig) -> dict:
    return runner.apply_defaults({
        "experiment": {"name": "rehearsal", "stage": "development"},
        "data": {"sim_start": "2017-06-01", "sim_end": "2023-12-29",
                 "sources": ["rehearsal"], "min_confidence": 0.9,
                 "vintage": "2026-07-21", "universe": [], "benchmark": "EW"},
        "signal": {"method": method, **sig},
        "portfolio": {"top_n": 12, "rebalance": rebalance,
                      "execution_lag_days": 1, "max_concurrent": 20},
        "validation": {},
    })


def placebo_p(con, cfg, n=40):
    gen = np.random.default_rng(7)
    real, plac = backtest_xs.placebo_stats(con, cfg, RATES, n, gen)
    return real, stats.placebo_p_value(real, plac)


def lowvol_premium_panel() -> pd.DataFrame:
    """30 low-vol names: small daily noise + small persistent positive
    drift. 30 high-vol names: large noise, zero drift. Vol groups are
    FIXED for the whole window (no group-switching) so the vol sort is
    stable and the premium is genuinely attributable to the vol axis."""
    n = len(DATES)
    lo_vol = RNG.normal(0.0004, 0.008, (n, 30))
    hi_vol = RNG.normal(0.0000, 0.028, (n, 30))
    cols = [f"SYN{i:03d}" for i in range(30)] + \
           [f"SYN{i:03d}" for i in range(30, 60)]
    return pd.DataFrame(np.hstack([lo_vol, hi_vol]), index=DATES, columns=cols)


def novol_premium_panel() -> pd.DataFrame:
    """Vol varies across names but expected COMPOUNDED return does NOT
    depend on it. Drawing arithmetic means independently of vol is NOT
    enough: variance drag means expected geometric growth ~= mean - vol^2/2,
    so an i.i.d.-mean panel still hands high-vol names a spurious REALIZED
    disadvantage. Compensate each name's arithmetic mean by +vol^2/2 so
    expected compounded growth is equalized across the vol axis — the
    correct null for 'vol has no genuine predictive content'."""
    n, k = len(DATES), len(TICKS)
    vols = RNG.uniform(0.008, 0.028, k)
    target_geo = 0.0002
    means = target_geo + 0.5 * vols ** 2
    r = np.zeros((n, k))
    for j in range(k):
        r[:, j] = RNG.normal(means[j], vols[j], n)
    return pd.DataFrame(r, index=DATES, columns=TICKS)


print("R5: planted low-vol premium, xs_vol ...")
con5 = make_db(lowvol_premium_panel())
cfg5 = base_cfg("xs_vol", "quarterly", vol_lookback_months=12,
               min_obs_formation=120)
res5, cap5, _ = backtest_xs.run_from_config(con5, cfg5, RATES)
m5 = metrics.compute(res5, 0.0)
real5, p5 = placebo_p(con5, cfg5)
print(f"  net excess {m5['excess_return_ann']:+.2%} | sharpe {real5} | "
      f"placebo p={p5:.3f}")
r5 = m5["excess_return_ann"] > 0 and p5 <= 0.05

print("R6: vol unrelated to forward return, xs_vol ...")
con6 = make_db(novol_premium_panel())
res6, cap6, _ = backtest_xs.run_from_config(con6, cfg5, RATES)
m6 = metrics.compute(res6, 0.0)
real6, p6 = placebo_p(con6, cfg5)
print(f"  net excess {m6['excess_return_ann']:+.2%} | placebo p={p6:.3f}")
r6 = p6 > 0.05

print("R7: annual vs quarterly rebalance, turnover check (xs_rank) ...")


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


con7 = make_db(planted_momentum())
cfg_q = base_cfg("xs_rank", "quarterly", formation_months=12, skip_months=1,
                 min_obs_formation=120)
cfg_a = base_cfg("xs_rank", "annual", formation_months=12, skip_months=1,
                 min_obs_formation=120)
res_q, _, _ = backtest_xs.run_from_config(con7, cfg_q, RATES)
res_a, _, _ = backtest_xs.run_from_config(con7, cfg_a, RATES)
mq = metrics.compute(res_q, 0.0)
ma = metrics.compute(res_a, 0.0)
print(f"  quarterly turnover {mq['ann_turnover_oneway']:.2f}x/yr | "
      f"annual turnover {ma['ann_turnover_oneway']:.2f}x/yr | "
      f"n_rebalances q={mq['n_rebalances']} a={ma['n_rebalances']}")
# per-rebalance turnover is naturally HIGHER at annual cadence (a full
# year of relative drift moves the portfolio more per rebalance than a
# quarter does) so total turnover doesn't scale down 4x with the 4x-fewer
# rebalances — a clearly-lower total plus far fewer rebalance EVENTS
# (each carrying its own fixed cost/slippage in reality) is the genuine,
# expected result.
r7 = (ma["ann_turnover_oneway"] < mq["ann_turnover_oneway"] * 0.7
      and ma["n_rebalances"] < mq["n_rebalances"] * 0.3)

print()
for name, ok in [("R5 planted low-vol premium recovered", r5),
                 ("R6 vol-only sort stays null without a real premium", r6),
                 ("R7 annual rebalance materially cuts turnover", r7)]:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
sys.exit(0 if all([r5, r6, r7]) else 1)
