"""Synthetic rehearsal of the 2026-08-03 xs_liquidity engine extension
(H-016, docs/PREREG_H-016_liquidity.md). Same discipline as every prior
engine addition -- nothing here touches the real database, registry, or
adtv60 panel; synthetic value_traded series are constructed directly in
memory. This rehearsal validates xs_liquidity_scores' SELECTION LOGIC
(both directions), its placebo behavior, and the Economic Capacity
Validation filter-ladder mechanics (prereg Section 10) -- all new code
paths this hypothesis introduces.

  python -u scripts/rehearse_xs_liquidity.py

L1 planted ILLIQUIDITY premium (least-liquid names drift up faster,
   variance held equal across groups) + direction="illiquid" -> positive
   net excess, placebo p <= 0.05.
L2 the SAME planted illiquidity premium, but direction="liquid" -> should
   NOT recover the premium (confirms the two directions select genuinely
   different, non-overlapping name sets, not a sign-convention no-op).
L3 planted LIQUIDITY premium (most-liquid names drift up faster) +
   direction="liquid" -> positive net excess, placebo p <= 0.05.
L4 ADTV level unrelated to forward return, both directions -> placebo
   p > 0.05 (no false signal from the sort alone).
L5 filter-ladder mechanics: progressively stricter min_adtv_ngn floors
   monotonically shrink (never grow) the eligible-name count per
   formation date, and a sufficiently strict floor drops a formation date
   entirely once eligibility falls below 10 -- the SAME breadth guard
   every other xs_* method already enforces, not a new threshold.
L6 direction selects genuinely different, correctly-ordered name sets on
   a known, deterministic ADTV ranking (not inferred from a planted return
   premium): direction="illiquid" selects the lowest-ADTV names,
   direction="liquid" selects the highest-ADTV names, for the same
   formation date and universe.
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db, backtest_xs, metrics, stats, runner  # noqa: E402

RATES = {"buy_rate": 0.019, "sell_rate": 0.019, "line_items": {}}
TICKS = [f"SYN{i:03d}" for i in range(60)]
DATES = pd.bdate_range("2016-01-04", "2023-12-29")
VT: dict[str, float] = {}


def make_db(returns: pd.DataFrame, adtv_by_ticker: dict[str, float]):
    tmp = Path(tempfile.mkdtemp()) / "rehearsal.sqlite"
    con = db.init_db(tmp)
    px = (100 * (1 + returns).cumprod())
    rows = []
    for t in returns.columns:
        vt = adtv_by_ticker[t]
        for dt, c in px[t].items():
            rows.append((t, dt.strftime("%Y-%m-%d"), float(c), 1_000_000,
                         vt, 50, 1, 0.9, "2026-07-21"))
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


def base_cfg(direction: str, min_adtv_ngn: float = 0.0) -> dict:
    return runner.apply_defaults({
        "experiment": {"name": "rehearsal", "stage": "development"},
        "data": {"sim_start": "2017-06-01", "sim_end": "2023-12-29",
                 "sources": ["rehearsal"], "min_confidence": 0.9,
                 "vintage": "2026-07-21", "universe": [], "benchmark": "EW"},
        "signal": {"method": "xs_liquidity", "direction": direction,
                   "min_adtv_ngn": min_adtv_ngn,
                   "min_obs_formation": 120, "lookback_months": 12},
        "portfolio": {"top_n": 12, "rebalance": "quarterly",
                      "execution_lag_days": 1},
        "validation": {},
    })


def run_case(con, cfg):
    panel = backtest_xs.load_panel(con, cfg)
    d, p = cfg["data"], cfg["portfolio"]
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])
    bt = backtest_xs.benchmark_targets(con, panel, cfg, lag)
    bench = backtest_xs.simulate(close, bt, RATES["buy_rate"],
                                 RATES["sell_rate"], d["sim_start"], d["sim_end"])
    scores = backtest_xs.xs_liquidity_scores(con, panel, cfg)
    targets = backtest_xs.targets_from_scores(
        scores, close.loc[:d["sim_end"]].index, int(p["top_n"]), lag)
    res = backtest_xs.simulate(close, targets, RATES["buy_rate"],
                               RATES["sell_rate"], d["sim_start"], d["sim_end"],
                               bench_net=bench.net_returns)
    res.benchmark_returns = bench.net_returns
    return res, metrics.compute(res, 0.0)


def placebo_p(con, cfg, n=100):
    panel = backtest_xs.load_panel(con, cfg)
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

    scores = backtest_xs.xs_liquidity_scores(con, panel, cfg)
    idx = close.loc[:d["sim_end"]].index
    p_ = cfg["portfolio"]
    real = sharpe_of(backtest_xs.targets_from_scores(scores, idx, int(p_["top_n"]), lag))
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
            backtest_xs.targets_from_scores(sh, idx, int(p_["top_n"]), lag)))
    return real, stats.placebo_p_value(real, placebo)


def _base_noise(seed: int) -> np.ndarray:
    """ONE shared noise realization per seed -- L1 and L3 both draw from
    seed=101 so the only difference between them is WHICH group gets the
    extra drift, not an independent random draw. Without this, comparing
    L1's and L3's placebo p-values would compare two different noise
    realizations, not the symmetric planted-premium designs they're
    meant to be."""
    rng = np.random.default_rng(seed)
    return rng.normal(0.0002, 0.011, (len(DATES), len(TICKS)))


def planted_illiquidity_premium(seed: int = 101):
    """A NARROW 15-name 'core illiquid' group (very low ADTV, 300k) gets a
    persistent extra drift; the other 45 names (ADTV 700k-50M, no boost)
    do not. Variance held equal across all names -- same discipline as
    H-011's rehearsal (rules out a vol-drag confound). The 15/45 split
    (not 30/30) is deliberate: with top_n=12, a REAL selection draws
    ~12 of the 15 boosted names (~90%+ boosted), while a PLACEBO
    permutation's random 12-of-60 draw averages only 12*15/60=3 boosted
    names (25%) -- a much larger, more reliably separable gap than a
    30/30 split gives (which averages 50% boosted under placebo, close
    enough to swamp the signal in daily-return noise)."""
    r = pd.DataFrame(_base_noise(seed), index=DATES, columns=TICKS)
    r.iloc[:, :15] += 0.0006
    adtv = ({t: 300_000.0 for t in TICKS[:15]}
            | {t: 700_000.0 for t in TICKS[15:30]}
            | {t: 50_000_000.0 for t in TICKS[30:]})
    return r, adtv


def planted_liquidity_premium(seed: int = 101):
    """Mirror of the above, same shared noise (seed=101): a narrow 15-name
    'core liquid' group (the HIGHEST ADTV, 70M) gets the extra drift, so
    direction="liquid"'s nlargest(12) selection draws it first -- ahead
    of the 15-name 'peripheral liquid' group (30M, no boost) and the
    30-name illiquid group (500k, no boost)."""
    r = pd.DataFrame(_base_noise(seed), index=DATES, columns=TICKS)
    r.iloc[:, 45:] += 0.0006
    adtv = ({t: 500_000.0 for t in TICKS[:30]}
            | {t: 30_000_000.0 for t in TICKS[30:45]}
            | {t: 70_000_000.0 for t in TICKS[45:]})
    return r, adtv


def no_liquidity_premium(seed: int = 202):
    """ADTV level assigned RANDOMLY, independent of the (identical,
    zero-extra-drift) return process -- no structural link between a
    name's liquidity rank and its forward return."""
    r = pd.DataFrame(_base_noise(seed), index=DATES, columns=TICKS)
    rng2 = np.random.default_rng(seed + 1)
    adtv = {t: v for t, v in zip(TICKS, rng2.uniform(500_000.0, 50_000_000.0,
                                                      len(TICKS)))}
    return r, adtv


print("L1: planted illiquidity premium, direction=illiquid ...")
ret1, adtv1 = planted_illiquidity_premium()
con1, _ = make_db(ret1, adtv1)
cfg_illiq = base_cfg("illiquid")
res1, m1 = run_case(con1, cfg_illiq)
real1, p1 = placebo_p(con1, cfg_illiq)
print(f"  net excess {m1['excess_return_ann']:+.2%} | sharpe {real1:.3f} | "
      f"placebo p={p1:.3f}")
l1 = m1["excess_return_ann"] > 0 and p1 <= 0.05

print("L2: SAME planted illiquidity premium, direction=liquid (should NOT recover it) ...")
cfg_liq_same = base_cfg("liquid")
res2, m2 = run_case(con1, cfg_liq_same)
real2, p2 = placebo_p(con1, cfg_liq_same)
print(f"  net excess {m2['excess_return_ann']:+.2%} | sharpe {real2:.3f} | "
      f"placebo p={p2:.3f}")
l2 = not (m2["excess_return_ann"] > 0 and p2 <= 0.05)

print("L3: planted liquidity premium, direction=liquid ...")
ret3, adtv3 = planted_liquidity_premium()
con3, _ = make_db(ret3, adtv3)
cfg_liq = base_cfg("liquid")
res3, m3 = run_case(con3, cfg_liq)
real3, p3 = placebo_p(con3, cfg_liq)
print(f"  net excess {m3['excess_return_ann']:+.2%} | sharpe {real3:.3f} | "
      f"placebo p={p3:.3f}")
l3 = m3["excess_return_ann"] > 0 and p3 <= 0.05

print("L4: ADTV unrelated to forward return, both directions ...")
ret4, adtv4 = no_liquidity_premium(seed=409)
con4, _ = make_db(ret4, adtv4)
_, p4a = placebo_p(con4, base_cfg("illiquid"))
_, p4b = placebo_p(con4, base_cfg("liquid"))
print(f"  illiquid leg placebo p={p4a:.3f} | liquid leg placebo p={p4b:.3f}")
l4 = p4a > 0.05 and p4b > 0.05

print("L5: filter-ladder mechanics (min_adtv_ngn) ...")
panel4 = backtest_xs.load_panel(con4, base_cfg("illiquid"))
ladder = [0.0, 1_000_000.0, 5_000_000.0, 10_000_000.0, 25_000_000.0,
          50_000_000.0, 100_000_000.0]
counts_by_rung = []
for floor in ladder:
    cfg_r = base_cfg("illiquid", min_adtv_ngn=floor)
    sc = backtest_xs.xs_liquidity_scores(con4, panel4, cfg_r)
    n_formations = len(sc)
    med_elig = (int(np.median([len(s) for s in sc.values()])) if sc else 0)
    counts_by_rung.append((floor, n_formations, med_elig))
    print(f"  floor=NGN{floor:>13,.0f}  formation_dates={n_formations:>3d}  "
          f"median_eligible={med_elig:>3d}")
med_counts = [c[2] for c in counts_by_rung]
l5_monotonic = all(med_counts[i] >= med_counts[i + 1]
                   for i in range(len(med_counts) - 1))
l5_eventually_infeasible = counts_by_rung[-1][1] == 0 or counts_by_rung[-1][2] < 10
l5 = l5_monotonic and l5_eventually_infeasible

print("L6: direction selects correctly-ordered, deterministic name sets ...")
det_adtv = {t: float(i + 1) * 1_000_000.0 for i, t in enumerate(TICKS)}
det_ret = pd.DataFrame(_base_noise(303), index=DATES, columns=TICKS)
con6, _ = make_db(det_ret, det_adtv)
panel6 = backtest_xs.load_panel(con6, base_cfg("illiquid"))
sc_illiq = backtest_xs.xs_liquidity_scores(con6, panel6, base_cfg("illiquid"))
sc_liq = backtest_xs.xs_liquidity_scores(con6, panel6, base_cfg("liquid"))
some_f = sorted(sc_illiq)[len(sc_illiq) // 2]
top_illiq = set(sc_illiq[some_f].nlargest(12).index)
top_liq = set(sc_liq[some_f].nlargest(12).index)
expected_illiq = set(sorted(det_adtv, key=det_adtv.get)[:12])
expected_liq = set(sorted(det_adtv, key=det_adtv.get, reverse=True)[:12])
l6 = (top_illiq == expected_illiq and top_liq == expected_liq
      and top_illiq.isdisjoint(top_liq))
print(f"  illiquid-leg top12 matches lowest-ADTV12: {top_illiq == expected_illiq}")
print(f"  liquid-leg top12 matches highest-ADTV12: {top_liq == expected_liq}")
print(f"  legs disjoint: {top_illiq.isdisjoint(top_liq)}")

print()
checks = [
    ("L1 planted illiquidity premium recovered (illiquid leg)", l1),
    ("L2 illiquid-planted premium NOT recovered by liquid leg", l2),
    ("L3 planted liquidity premium recovered (liquid leg)", l3),
    ("L4 null panel stays null, both directions", l4),
    ("L5 filter ladder: monotonic shrink + eventual infeasibility", l5),
    ("L6 direction selects correct, disjoint, ordered name sets", l6),
]
for name, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
sys.exit(0 if all(ok for _, ok in checks) else 1)
