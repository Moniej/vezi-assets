"""Synthetic rehearsal of the cross-sectional engine (pre-use validation,
same discipline as every engine before it).

  python -u scripts/rehearse_xs_engine.py

Four assertions on a TEMP database (never data/ngx.sqlite; nothing is
registered; results are machinery checks, not market evidence):
  R1 xs_rank on a PLANTED persistent-drift panel -> positive net excess
     and real sharpe above the placebo distribution (p <= 0.05).
  R2 xs_rank on an IID (null) panel -> placebo p > 0.05 (no false signal).
  R3 xs_event with PLANTED post-event drift -> positive net excess vs bench.
  R4 xs_event with reactions but NO subsequent drift -> excess ~ <= 0.
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


def make_db(returns: pd.DataFrame) -> object:
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


def base_cfg(method: str, **sig) -> dict:
    return runner.apply_defaults({
        "experiment": {"name": "rehearsal", "stage": "development"},
        "data": {"sim_start": "2017-06-01", "sim_end": "2023-12-29",
                 "sources": ["rehearsal"], "min_confidence": 0.9,
                 "vintage": "2026-07-21", "universe": [], "benchmark": "EW"},
        "signal": {"method": method, **sig},
        "portfolio": {"top_n": 12, "rebalance": "quarterly",
                      "execution_lag_days": 1, "max_concurrent": 20},
        "validation": {},
    })


def run_case(con, cfg):
    res, cap, _ = backtest_xs.run_from_config(con, cfg, RATES)
    m = metrics.compute(res, 0.0)
    return res, m


def planted_momentum() -> pd.DataFrame:
    # slow persistent per-ticker drift (AR(1) on monthly alpha) -> 12-1 works
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


def event_panel(with_drift: bool):
    r = RNG.normal(0.0003, 0.010, (len(DATES), len(TICKS)))
    df = pd.DataFrame(r, index=DATES, columns=TICKS)
    events = []
    for t in TICKS:
        ci = df.columns.get_loc(t)
        for j in RNG.choice(np.arange(280, len(DATES) - 100), 8, replace=False):
            react = RNG.choice([0.015, -0.01, 0.03, 0.0])
            df.iloc[j:j + 3, ci] += react / 3
            if with_drift and react >= 0.015:      # drift follows big reactions
                df.iloc[j + 3:j + 63, ci] += 0.06 / 60
            events.append(dict(created=(DATES[j] - pd.Timedelta(hours=10)
                                        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               symbol=t, submission_type="Financial Statements",
                               created_date=DATES[j].strftime("%Y-%m-%d")))
    cal = Path(tempfile.mkdtemp()) / "events.csv"
    pd.DataFrame(events).to_csv(cal, index=False)
    return df, str(cal)


def placebo_p(con, cfg, n=40):
    gen = np.random.default_rng(7)
    real, plac = backtest_xs.placebo_stats(con, cfg, RATES, n, gen)
    return real, stats.placebo_p_value(real, plac)


print("R1: planted persistent drift, xs_rank ...")
con = make_db(planted_momentum())
cfg = base_cfg("xs_rank", formation_months=12, skip_months=1,
               min_obs_formation=120)
res, m = run_case(con, cfg)
real, p = placebo_p(con, cfg)
print(f"  net excess {m['excess_return_ann']:+.2%} | sharpe {real} | "
      f"placebo p={p:.3f}")
r1 = m["excess_return_ann"] > 0 and p <= 0.05

print("R2: iid null panel, xs_rank ...")
con2 = make_db(iid_panel())
res2, m2 = run_case(con2, cfg)
real2, p2 = placebo_p(con2, cfg)
print(f"  net excess {m2['excess_return_ann']:+.2%} | placebo p={p2:.3f}")
r2 = p2 > 0.05

print("R3: planted post-event drift, xs_event ...")
panel3, cal3 = event_panel(with_drift=True)
con3 = make_db(panel3)
cfg3 = base_cfg("xs_event", event_calendar=cal3, hold_sessions=60,
                entry_lag_sessions=3, select_fraction=0.3333)
res3, m3 = run_case(con3, cfg3)
gross_excess = m3["gross_ann_return"] - m3["ann_return_benchmark"]
print(f"  GROSS excess {gross_excess:+.2%} | net {m3['excess_return_ann']:+.2%} "
      f"| cost drag {m3['ann_cost_drag']:.2%}")
# engine-recovery assertion is on GROSS: the planted 6%/event drift is BELOW
# the honest 7.6% two-leg event round trip, so net<0 here is cost
# accounting working, not an engine failure
r3 = gross_excess > 0.03 and 0 < m3["ann_cost_drag"] < 0.15

print("R4: events with NO drift, xs_event ...")
panel4, cal4 = event_panel(with_drift=False)
con4 = make_db(panel4)
cfg4 = base_cfg("xs_event", event_calendar=cal4, hold_sessions=60,
                entry_lag_sessions=3, select_fraction=0.3333)
res4, m4 = run_case(con4, cfg4)
print(f"  net excess {m4['excess_return_ann']:+.2%}")
r4 = m4["excess_return_ann"] <= 0.01

print()
for name, ok in [("R1 planted momentum recovered", r1),
                 ("R2 null panel stays null", r2),
                 ("R3 planted PEAD recovered", r3),
                 ("R4 no-drift events stay null", r4)]:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
sys.exit(0 if all([r1, r2, r3, r4]) else 1)
