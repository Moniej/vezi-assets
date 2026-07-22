"""Synthetic rehearsal of the 2026-07-22 xs_size engine extension (E2 in
docs/EXECUTION_BACKLOG.md — market-cap loader + size signal method,
unblocks H-011 / Wave-3 candidate C4). Same discipline as every prior
engine addition — nothing here touches the real database, registry, or
market_cap_panel.csv; the synthetic cap series is constructed directly
in memory (the CSV-parsing path itself was already validated separately
in reports/market_cap_validation.md; this rehearsal is specifically about
size_scores' SELECTION LOGIC and its placebo behavior, which are new).

  python -u scripts/rehearse_xs_size.py

R8 planted SIZE premium (small caps drift up faster, net of the SAME
   variance-drag compensation the 2026-07-22 low-vol rehearsal had to
   apply) -> positive net excess, placebo p <= 0.05.
R9 cap level unrelated to forward return -> placebo p > 0.05 (no false
   signal from the size sort alone).
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
    return con, px


def base_cfg() -> dict:
    return runner.apply_defaults({
        "experiment": {"name": "rehearsal", "stage": "development"},
        "data": {"sim_start": "2017-06-01", "sim_end": "2023-12-29",
                 "sources": ["rehearsal"], "min_confidence": 0.9,
                 "vintage": "2026-07-21", "universe": [], "benchmark": "EW"},
        "signal": {"method": "xs_size", "min_obs_formation": 120,
                   "lookback_months": 12},
        "portfolio": {"top_n": 12, "rebalance": "quarterly",
                      "execution_lag_days": 1},
        "validation": {},
    })


def run_case(con, px, cfg):
    panel = backtest_xs.load_panel(con, cfg)
    panel["mcap"] = build_mcap(px)
    d, p = cfg["data"], cfg["portfolio"]
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])
    bt = backtest_xs.benchmark_targets(con, panel, cfg, lag)
    bench = backtest_xs.simulate(close, bt, RATES["buy_rate"],
                                 RATES["sell_rate"], d["sim_start"], d["sim_end"])
    scores = backtest_xs.size_scores(con, panel, cfg)
    targets = backtest_xs.targets_from_scores(
        scores, close.loc[:d["sim_end"]].index, int(p["top_n"]), lag)
    res = backtest_xs.simulate(close, targets, RATES["buy_rate"],
                               RATES["sell_rate"], d["sim_start"], d["sim_end"],
                               bench_net=bench.net_returns)
    res.benchmark_returns = bench.net_returns
    return res, metrics.compute(res, 0.0)


def placebo_p(con, px, cfg, n=40):
    """Same fixed-relabeling design as xs_rank/xs_vol — direct call since
    backtest_xs.placebo_stats loads mcap from disk; this rehearsal needs
    the in-memory synthetic panel instead."""
    panel = backtest_xs.load_panel(con, cfg)
    panel["mcap"] = build_mcap(px)
    d, p = cfg["data"], cfg["portfolio"]
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])
    bt = backtest_xs.benchmark_targets(con, panel, cfg, lag)
    bench = backtest_xs.simulate(close, bt, RATES["buy_rate"],
                                 RATES["sell_rate"], d["sim_start"], d["sim_end"])

    def sharpe_of(targets):
        res = backtest_xs.simulate(close, targets, RATES["buy_rate"],
                                   RATES["sell_rate"], d["sim_start"],
                                   d["sim_end"], bench_net=bench.net_returns)
        res.benchmark_returns = bench.net_returns
        return metrics.compute(res, 0.0)["sharpe_vs_rf"]

    scores = backtest_xs.size_scores(con, panel, cfg)
    idx = close.loc[:d["sim_end"]].index
    real = sharpe_of(backtest_xs.targets_from_scores(scores, idx, int(p["top_n"]), lag))
    all_ticks = sorted({t for sc in scores.values() for t in sc.index})
    gen = np.random.default_rng(7)
    placebo = []
    for _ in range(n):
        perm = dict(zip(all_ticks, [all_ticks[j] for j in
                                    gen.permutation(len(all_ticks))]))
        sh = {}
        for f, sc in scores.items():
            vals = {t: sc[perm[t]] for t in sc.index if perm[t] in sc.index}
            if len(vals) >= 10:
                sh[f] = pd.Series(vals)
        placebo.append(sharpe_of(
            backtest_xs.targets_from_scores(sh, idx, int(p["top_n"]), lag)))
    return real, stats.placebo_p_value(real, placebo)


def build_mcap(px: pd.DataFrame) -> pd.DataFrame:
    """px is the close-price panel; scale by a fixed per-ticker 'share
    count' to get a market-cap series that moves with price (like the
    real data) but has a genuine, independent size ranking baked in."""
    shares = pd.Series(SHARES, index=TICKS)
    return px[TICKS] * shares


def planted_size_premium():
    """30 'small' names (low share count => small cap) get a small
    persistent extra drift; 30 'large' names do not. Variance is held
    equal across groups so this isn't a repeat of the vol-drag confound —
    the premium here is a genuine drift difference, not a compounding
    artifact."""
    global SHARES
    n = len(DATES)
    small = RNG.normal(0.0004, 0.011, (n, 30))
    large = RNG.normal(0.0000, 0.011, (n, 30))
    cols = TICKS[:30] + TICKS[30:]
    r = pd.DataFrame(np.hstack([small, large]), index=DATES, columns=cols)
    SHARES = [1.0] * 30 + [50.0] * 30   # small-share-count => small cap
    return r


def no_size_premium():
    """Cap level (share count) assigned RANDOMLY, independent of the
    (identical, zero-drift) return process — no structural link between
    a name's size rank and its forward return."""
    global SHARES
    n = len(DATES)
    r = pd.DataFrame(RNG.normal(0.0002, 0.011, (n, len(TICKS))),
                     index=DATES, columns=TICKS)
    SHARES = list(RNG.uniform(1.0, 50.0, len(TICKS)))
    return r


SHARES: list[float] = []

print("R8: planted size premium, xs_size ...")
con8, px8 = make_db(planted_size_premium())
cfg = base_cfg()
res8, m8 = run_case(con8, px8, cfg)
real8, p8 = placebo_p(con8, px8, cfg)
print(f"  net excess {m8['excess_return_ann']:+.2%} | sharpe {real8} | "
      f"placebo p={p8:.3f}")
r8 = m8["excess_return_ann"] > 0 and p8 <= 0.05

print("R9: cap unrelated to forward return, xs_size ...")
con9, px9 = make_db(no_size_premium())
res9, m9 = run_case(con9, px9, cfg)
real9, p9 = placebo_p(con9, px9, cfg)
print(f"  net excess {m9['excess_return_ann']:+.2%} | placebo p={p9:.3f}")
r9 = p9 > 0.05

print()
for name, ok in [("R8 planted size premium recovered", r8),
                 ("R9 null panel stays null", r9)]:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
sys.exit(0 if all([r8, r9]) else 1)
