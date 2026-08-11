"""Stage 21C -- Drift-Only Market-Relative Diagnostic (2026-08-09).

Measurement/diagnostic only. No H-021, no portfolio, no strategy return, no
threshold/horizon/universe optimization. Imports MIN_RUN and HORIZONS
directly from Stage 21B's frozen script to guarantee zero drift in the
stale-run definition or horizon set. The T0 reopening jump is explicitly
discarded per the hard decision already made -- only post-T0 drift across
subsequent genuinely traded sessions is measured here.

Benchmark choice (disclosed): the platform's EW-IRU benchmark is itself
built by running backtest_xs.benchmark_targets()/simulate(), i.e. portfolio-
construction machinery -- reusing it here would blur the "no portfolio"
line. Instead this stage uses index_levels for NGXASI (NGX All-Share Index,
2012-2026, dense daily coverage) as the market-relative benchmark: a real,
existing, already-computed index series, not a new construction.

Cost model: reuses costs.side_rates() unmodified against the live
cost_schedule table -- the same function/table every backtest in this
project has used, not a new assumption invented for this stage.

  PYTHONPATH=src python scripts/stage21c_drift_only_market_relative.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from stage21b_trade_conditional_diagnostic import MIN_RUN, HORIZONS  # noqa: E402
from ngxrot import costs  # noqa: E402

OUT = ROOT / "data" / "staging" / "stage21c"
OUT.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20260809)


def load_prices() -> pd.DataFrame:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    df = pd.read_sql(
        "SELECT ticker, trade_date, close, volume FROM equity_prices ORDER BY ticker, trade_date", con
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_mcap() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "reference" / "market_cap_panel.csv")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.rename(columns={"symbol": "ticker"})


def load_benchmark() -> pd.Series:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    df = pd.read_sql(
        "SELECT trade_date, close_value FROM index_levels WHERE index_code='NGXASI' ORDER BY trade_date", con
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date")["close_value"]


def load_cost_schedule() -> dict:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    sch = pd.read_sql("SELECT * FROM cost_schedule", con)
    return costs.side_rates(sch)


def find_episodes_with_dates(g: pd.DataFrame) -> list[dict]:
    g = g.sort_values("trade_date").reset_index(drop=True)
    prev_close = g["close"].shift(1)
    is_zero = (g["close"] == prev_close) & prev_close.notna()
    has_vol = g["volume"].notna() & (g["volume"] > 0)
    run_id = (~is_zero).cumsum()
    episodes = []
    for rid, idx in is_zero.groupby(run_id).groups.items():
        idx = list(idx)
        run_len = int(is_zero.loc[idx].sum())
        if run_len < MIN_RUN:
            continue
        run_start_pos, run_end_pos = idx[0], idx[-1]
        t0_pos = run_end_pos + 1
        if t0_pos >= len(g):
            continue
        pre_run_close = g["close"].iloc[run_start_pos - 1] if run_start_pos > 0 else np.nan
        if pd.isna(pre_run_close):
            continue

        traded_positions = []
        pos = t0_pos
        n_scanned = 0
        while pos < len(g) and len(traded_positions) < max(HORIZONS) and n_scanned < 400:
            if has_vol.iloc[pos] or pos == t0_pos:
                traded_positions.append(pos)
            pos += 1
            n_scanned += 1

        if len(traded_positions) < 2:
            continue  # need at least T0 + one post-T0 traded session to measure any drift

        t0_close = g["close"].iloc[traded_positions[0]]
        t0_date = g["trade_date"].iloc[traded_positions[0]]

        row = dict(
            ticker=g["ticker"].iloc[0],
            run_start_date=g["trade_date"].iloc[run_start_pos],
            run_length=run_len,
            t0_date=t0_date,
        )
        for k in HORIZONS:
            if k == 1:
                continue  # T0 itself is the discarded jump; k=1 drift horizon is undefined by construction
            if len(traded_positions) >= k:
                pos_k = traded_positions[k - 1]
                row[f"drift_{k}"] = g["close"].iloc[pos_k] / t0_close - 1.0
                row[f"date_{k}"] = g["trade_date"].iloc[pos_k]
            else:
                row[f"drift_{k}"] = np.nan
                row[f"date_{k}"] = pd.NaT
        episodes.append(row)
    return episodes


def build_control_with_dates(px: pd.DataFrame, ep_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    stale_ends_by_ticker = ep_df.groupby("ticker")["run_start_date"].apply(list).to_dict()
    for ticker, g in px.groupby("ticker"):
        if len(g) < 250:
            continue
        g = g.sort_values("trade_date").reset_index(drop=True)
        has_vol = g["volume"].notna() & (g["volume"] > 0)
        stale_dates = set(stale_ends_by_ticker.get(ticker, []))
        stale_pos = set(g.index[g["trade_date"].isin(stale_dates)])
        excluded = set()
        for p in stale_pos:
            excluded.update(range(max(0, p - 5), min(len(g), p + 30)))
        traded_idx = [i for i in range(len(g)) if has_vol.iloc[i]]
        candidates = [i for i in traded_idx if i not in excluded and i + max(HORIZONS) < len(g)]
        if not candidates:
            continue
        n_sample = min(len(candidates), max(15, int(0.04 * len(candidates))))
        sampled = RNG.choice(candidates, size=n_sample, replace=False)
        for pos in sampled:
            t0_close = g["close"].iloc[pos]
            t0_date = g["trade_date"].iloc[pos]
            traded_positions = [pos]
            walk = pos + 1
            while walk < len(g) and len(traded_positions) < max(HORIZONS):
                if has_vol.iloc[walk]:
                    traded_positions.append(walk)
                walk += 1
            row = {"ticker": ticker, "t0_date": t0_date}
            for k in HORIZONS:
                if k == 1:
                    continue
                if len(traded_positions) >= k:
                    pos_k = traded_positions[k - 1]
                    row[f"drift_{k}"] = g["close"].iloc[pos_k] / t0_close - 1.0
                    row[f"date_{k}"] = g["trade_date"].iloc[pos_k]
                else:
                    row[f"drift_{k}"] = np.nan
                    row[f"date_{k}"] = pd.NaT
            rows.append(row)
    return pd.DataFrame(rows)


def bench_ret(bench: pd.Series, d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    if pd.isna(d0) or pd.isna(d1):
        return np.nan
    try:
        l0 = bench.asof(d0)
        l1 = bench.asof(d1)
    except Exception:
        return np.nan
    if pd.isna(l0) or pd.isna(l1) or l0 == 0:
        return np.nan
    return l1 / l0 - 1.0


def main() -> None:
    px = load_prices()
    mcap = load_mcap()
    bench = load_benchmark()
    rates = load_cost_schedule()
    print("=== Cost schedule (reused from costs.side_rates(), unmodified) ===")
    print(f"buy_rate={rates['buy_rate']:.4%}  sell_rate={rates['sell_rate']:.4%}  "
          f"round_trip={rates['buy_rate'] + rates['sell_rate']:.4%}")

    print("\n=== Building drift-only episodes (T0 jump discarded) ===")
    ep_rows = []
    for ticker, g in px.groupby("ticker"):
        if len(g) < 250:
            continue
        ep_rows.extend(find_episodes_with_dates(g))
    ep = pd.DataFrame(ep_rows)
    print(f"n_episodes={len(ep)}  n_tickers={ep['ticker'].nunique()}")
    ep.to_csv(OUT / "drift_episodes.csv", index=False)

    print("\n=== Building drift-only control (ticker-matched, non-post-stale) ===")
    ctrl = build_control_with_dates(px, ep)
    print(f"n_control={len(ctrl)}")
    ctrl.to_csv(OUT / "drift_control.csv", index=False)

    print("\n=== Attaching mcap tercile (at run_start_date, PIT) and pre-stale vol ===")
    mcap_sorted = mcap.rename(columns={"trade_date": "run_start_date"}).sort_values("run_start_date")
    ep2 = pd.merge_asof(
        ep.sort_values("run_start_date"), mcap_sorted, on="run_start_date", by="ticker",
        direction="backward", tolerance=pd.Timedelta(days=30),
    )
    ep2["size_tercile"] = pd.qcut(ep2["market_cap_nm"], 3, labels=["Small", "Mid", "Large"], duplicates="drop")
    ep2["runlen_bucket"] = pd.cut(ep2["run_length"], [4, 9, 19, 49, 10_000], labels=["5-9", "10-19", "20-49", "50+"])

    part_a = pd.read_csv(ROOT / "data" / "staging" / "stage21" / "part_a_descriptives.csv")
    ep2 = ep2.merge(part_a[["ticker", "trading_freq", "zero_return_freq"]], on="ticker", how="left")
    ep2["activity_bucket"] = pd.qcut(ep2["trading_freq"], 2, labels=["LessActive", "MoreActive"], duplicates="drop")

    print(f"\n=== Section 1: usable episode counts per horizon ===")
    for k in [3, 5, 10, 20]:
        n_ep = ep2[f"drift_{k}"].notna().sum()
        n_ctrl = ctrl[f"drift_{k}"].notna().sum()
        print(f"k={k}: episodes usable={n_ep}  control usable={n_ctrl}")

    print(f"\n=== Section 2: market-relative comparison (all horizons, none cherry-picked) ===")
    results = []
    for k in [3, 5, 10, 20]:
        sub = ep2.dropna(subset=[f"drift_{k}", f"date_{k}"]).copy()
        sub[f"bench_{k}"] = [bench_ret(bench, t0, d) for t0, d in zip(sub["t0_date"], sub[f"date_{k}"])]
        sub[f"excess_{k}"] = sub[f"drift_{k}"] - sub[f"bench_{k}"]

        csub = ctrl.dropna(subset=[f"drift_{k}", f"date_{k}"]).copy()
        csub[f"bench_{k}"] = [bench_ret(bench, t0, d) for t0, d in zip(csub["t0_date"], csub[f"date_{k}"])]
        csub[f"excess_{k}"] = csub[f"drift_{k}"] - csub[f"bench_{k}"]

        pos_frac = (sub[f"drift_{k}"] > 0).mean()
        n = len(sub)
        se = sub[f"excess_{k}"].std() / np.sqrt(n) if n > 1 else np.nan
        tstat = sub[f"excess_{k}"].mean() / se if se and se > 0 else np.nan

        results.append(dict(
            k=k, n=n,
            raw_drift_mean=sub[f"drift_{k}"].mean(),
            bench_ret_mean=sub[f"bench_{k}"].mean(),
            excess_drift_mean=sub[f"excess_{k}"].mean(),
            excess_drift_median=sub[f"excess_{k}"].median(),
            excess_drift_tstat=tstat,
            pct_positive_raw_drift=pos_frac,
            control_raw_drift_mean=csub[f"drift_{k}"].mean(),
            control_excess_drift_mean=csub[f"excess_{k}"].mean(),
            episode_minus_control_excess=sub[f"excess_{k}"].mean() - csub[f"excess_{k}"].mean(),
        ))
        sub.to_csv(OUT / f"episode_bench_k{k}.csv", index=False)
    res_df = pd.DataFrame(results)
    res_df.to_csv(OUT / "market_relative_summary.csv", index=False)
    print(res_df.to_string())

    print(f"\n=== Section 3: magnitude vs direction, k=10 (representative, not cherry-picked -- all k in table above) ===")
    sub10 = ep2.dropna(subset=["drift_10"])
    print("pct sessions with positive drift:", (sub10["drift_10"] > 0).mean())
    print("mean |drift_10|:", sub10["drift_10"].abs().mean(), "  mean signed drift_10:", sub10["drift_10"].mean())
    print("std drift_10:", sub10["drift_10"].std())

    print(f"\n=== Section 4: independence -- correlations with drift_10 ===")
    for col in ["market_cap_nm", "trading_freq", "zero_return_freq", "run_length"]:
        d = ep2.dropna(subset=["drift_10", col])
        if len(d) > 10:
            print(f"Spearman(drift_10, {col}) = {d['drift_10'].corr(d[col], method='spearman'):.4f}  n={len(d)}")

    print(f"\n=== Section 6: robustness splits (descriptive only, drift_10 & excess_10) ===")
    k10 = pd.read_csv(OUT / "episode_bench_k10.csv", parse_dates=["t0_date"])
    for col in ["size_tercile", "activity_bucket", "runlen_bucket"]:
        print(f"\n-- by {col} --")
        print(k10.groupby(col, observed=True)[["drift_10", "excess_10"]].agg(["mean", "count"]).to_string())

    print(f"\n=== Section 5: cost/capacity gate ===")
    rt_cost = rates["buy_rate"] + rates["sell_rate"]
    print(f"Round-trip transaction cost (existing platform schedule): {rt_cost:.4%}")
    for k in [3, 5, 10, 20]:
        row = res_df[res_df.k == k].iloc[0]
        print(f"k={k}: mean excess drift={row.excess_drift_mean:+.4%}  vs round-trip cost={rt_cost:.4%}  "
              f"survives_cost={'YES' if row.excess_drift_mean > rt_cost else 'NO'}  "
              f"(median excess={row.excess_drift_median:+.4%}, survives_median={'YES' if row.excess_drift_median > rt_cost else 'NO'})")


if __name__ == "__main__":
    main()
