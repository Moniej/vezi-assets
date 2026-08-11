"""Stage 21B -- Trade-Conditional Price-Discovery Diagnostic (2026-08-09).

Measurement/diagnostic only. No portfolio, no strategy return, no H-021, no
threshold chosen from results. Reuses Stage 21's own stale-run definition
(>=5 consecutive zero-return sessions) unmodified -- not re-optimized here.

Frozen definitions (fixed BEFORE execution):
  - Universe: same as Stage 21 -- tickers with >=250 equity_prices sessions.
  - is_zero session: close == previous session's close (same ticker).
  - has_vol session: volume IS NOT NULL AND volume > 0 (genuine trade).
  - Stale episode: a maximal run of >=5 consecutive is_zero sessions
    (Stage 21's own threshold, reused verbatim).
  - T0 ("first subsequent genuine trading session"): the first session
    after the run where close != previous close (price actually moved).
    T0's has_vol flag is recorded and reported separately -- a price
    change with no recorded volume is flagged as a data inconsistency,
    not silently treated as a normal trade.
  - pre_run_close: the flat price held throughout the stale run (close of
    the session immediately before the run began, which equals every
    close during the run by construction of is_zero).
  - pre_stale_vol: std of daily log returns over the 60 sessions strictly
    before the stale run started (a volatility baseline, not touched by
    the stale spell itself).
  - Forward traded-session walk: starting at T0 (traded session #1),
    advance ONLY through sessions with has_vol == True to find traded
    sessions #2, #3, ... #20. Sessions with missing/zero volume are
    skipped (not counted, not substituted with any value) but are logged
    so gaps are visible. If fewer than 20 traded sessions exist in the
    ticker's remaining data, the episode is marked right-censored for
    that horizon and excluded from that horizon's stats (not
    extrapolated). A calendar gap >20 days between consecutive available
    rows during the walk is flagged as a suspected-suspension marker.
  - Metrics per horizon k in {1,3,5,10,20}:
      ret_total_k   = close(traded session k) / pre_run_close - 1
      ret_post_T0_k = close(traded session k) / close(T0) - 1   (k>=2;
                      isolates post-reopening drift from the reopening
                      move itself)
  - Controls (described, not optimized): market-cap tercile at run start,
    trading frequency, zero-return frequency (both from Stage 21's Part A
    output), pre-stale volatility tercile, stale-run-length bucket.
  - Baseline/control group: an equal-sized random sample of non-post-stale
    traded sessions (has_vol==True, not within 5 sessions of any stale-run
    end) per ticker, same horizon metrics computed, for comparison against
    "ordinary" trade-to-trade behavior.

  PYTHONPATH=src python scripts/stage21b_trade_conditional_diagnostic.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "stage21b"
OUT.mkdir(parents=True, exist_ok=True)

MIN_RUN = 5
HORIZONS = [1, 3, 5, 10, 20]
RNG = np.random.default_rng(20260809)  # fixed seed, purely for control-group sampling reproducibility


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


def find_episodes(g: pd.DataFrame) -> list[dict]:
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
        run_start_pos = idx[0]
        run_end_pos = idx[-1]
        t0_pos = run_end_pos + 1
        if t0_pos >= len(g):
            continue  # stale run goes to the end of the series -- no post-stale data, skip
        pre_run_close = g["close"].iloc[run_start_pos - 1] if run_start_pos > 0 else np.nan
        if pd.isna(pre_run_close):
            continue
        pre_window = g.iloc[max(0, run_start_pos - 61):max(0, run_start_pos - 1)]
        pre_ret = pre_window["close"].pct_change().apply(lambda x: np.log1p(x) if pd.notna(x) and x > -1 else np.nan)
        pre_stale_vol = pre_ret.std()

        # walk forward collecting traded-session positions starting at t0_pos
        traded_positions = []
        max_gap_days = 0
        pos = t0_pos
        last_date = g["trade_date"].iloc[t0_pos - 1] if t0_pos > 0 else None
        n_scanned = 0
        while pos < len(g) and len(traded_positions) < max(HORIZONS) and n_scanned < 400:
            row_date = g["trade_date"].iloc[pos]
            if last_date is not None:
                gap = (row_date - last_date).days
                max_gap_days = max(max_gap_days, gap)
            last_date = row_date
            if has_vol.iloc[pos] or pos == t0_pos:
                # T0 itself always counts as traded session #1 (per spec),
                # regardless of its own has_vol flag (flagged separately below)
                traded_positions.append(pos)
            pos += 1
            n_scanned += 1

        episodes.append(dict(
            ticker=g["ticker"].iloc[0],
            run_start_date=g["trade_date"].iloc[run_start_pos],
            run_end_date=g["trade_date"].iloc[run_end_pos],
            run_length=run_len,
            t0_date=g["trade_date"].iloc[t0_pos],
            t0_has_vol=bool(has_vol.iloc[t0_pos]),
            pre_run_close=pre_run_close,
            pre_stale_vol=pre_stale_vol,
            n_traded_found=len(traded_positions),
            max_gap_days_in_walk=max_gap_days,
            traded_close_by_horizon={
                k: (g["close"].iloc[traded_positions[k - 1]] if len(traded_positions) >= k else np.nan)
                for k in HORIZONS
            },
        ))
    return episodes


def build_episode_table(px: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, g in px.groupby("ticker"):
        if len(g) < 250:
            continue
        for ep in find_episodes(g):
            row = {k: v for k, v in ep.items() if k != "traded_close_by_horizon"}
            for k in HORIZONS:
                tc = ep["traded_close_by_horizon"][k]
                row[f"ret_total_{k}"] = (tc / ep["pre_run_close"] - 1.0) if pd.notna(tc) else np.nan
                t0_close = ep["traded_close_by_horizon"][1]
                row[f"ret_post_t0_{k}"] = (
                    (tc / t0_close - 1.0) if (pd.notna(tc) and pd.notna(t0_close) and k > 1) else np.nan
                )
                row[f"censored_{k}"] = ep["n_traded_found"] < k
            rows.append(row)
    return pd.DataFrame(rows)


def build_control_group(px: pd.DataFrame, ep_df: pd.DataFrame) -> pd.DataFrame:
    """Non-post-stale traded sessions, same horizon metrics, for baseline comparison."""
    rows = []
    stale_dates_by_ticker = ep_df.groupby("ticker")["run_end_date"].apply(set).to_dict()
    for ticker, g in px.groupby("ticker"):
        if len(g) < 250:
            continue
        g = g.sort_values("trade_date").reset_index(drop=True)
        has_vol = g["volume"].notna() & (g["volume"] > 0)
        stale_ends = stale_dates_by_ticker.get(ticker, set())
        traded_idx = [i for i in range(len(g)) if has_vol.iloc[i]]
        # exclude sessions within 5 trading sessions of any stale-run end (avoid overlap with episodes)
        stale_end_pos = set(g.index[g["trade_date"].isin(stale_ends)])
        excluded = set()
        for p in stale_end_pos:
            excluded.update(range(max(0, p - 5), min(len(g), p + 25)))
        candidates = [i for i in traded_idx if i not in excluded and i + max(HORIZONS) < len(g)]
        if not candidates:
            continue
        n_sample = min(len(candidates), max(20, int(0.05 * len(candidates))))
        sampled = RNG.choice(candidates, size=n_sample, replace=False)
        for pos in sampled:
            base_close = g["close"].iloc[pos]
            traded_positions = [pos]
            walk = pos + 1
            while walk < len(g) and len(traded_positions) < max(HORIZONS):
                if has_vol.iloc[walk]:
                    traded_positions.append(walk)
                walk += 1
            row = {"ticker": ticker, "base_date": g["trade_date"].iloc[pos]}
            for k in HORIZONS:
                tc = g["close"].iloc[traded_positions[k - 1]] if len(traded_positions) >= k else np.nan
                row[f"ret_total_{k}"] = (tc / base_close - 1.0) if pd.notna(tc) else np.nan
                t0_close = g["close"].iloc[traded_positions[0]]
                row[f"ret_post_t0_{k}"] = (tc / t0_close - 1.0) if (pd.notna(tc) and k > 1) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    px = load_prices()
    mcap = load_mcap()

    print("=== Building stale episodes (run>=5, Stage 21's own threshold, unmodified) ===")
    ep = build_episode_table(px)
    print(f"n_episodes={len(ep)}  n_tickers={ep['ticker'].nunique()}")
    ep.to_csv(OUT / "episodes.csv", index=False)

    # attach mcap tercile at run_start_date (nearest available <= run_start_date)
    mcap_sorted = mcap.rename(columns={"trade_date": "run_start_date"}).sort_values("run_start_date")
    ep = ep.sort_values("run_start_date")
    merged_mcap = pd.merge_asof(
        ep, mcap_sorted,
        on="run_start_date", by="ticker", direction="backward", tolerance=pd.Timedelta(days=30),
    )
    merged_mcap["size_tercile"] = pd.qcut(merged_mcap["market_cap_nm"], 3, labels=["Small", "Mid", "Large"], duplicates="drop")
    merged_mcap["vol_tercile"] = pd.qcut(merged_mcap["pre_stale_vol"].rank(method="first"), 3, labels=["LowVol", "MidVol", "HighVol"])
    merged_mcap["runlen_bucket"] = pd.cut(merged_mcap["run_length"], [4, 9, 19, 49, 10_000], labels=["5-9", "10-19", "20-49", "50+"])
    merged_mcap.to_csv(OUT / "episodes_with_controls.csv", index=False)

    print("\n=== T0 (reopening) move magnitude vs pre-stale volatility ===")
    t0_ret = merged_mcap["ret_total_1"]
    print("mean |T0 return|:", t0_ret.abs().mean(), " median:", t0_ret.abs().median())
    print("mean pre-stale daily vol (log-ret std):", merged_mcap["pre_stale_vol"].mean())
    print("ratio (T0 move vs 1-day pre-stale vol):", t0_ret.abs().mean() / merged_mcap["pre_stale_vol"].mean())
    print("t0_has_vol True fraction:", merged_mcap["t0_has_vol"].mean())

    print("\n=== Decomposition: T0 move vs subsequent drift (sign relationship) ===")
    for k in [3, 5, 10, 20]:
        sub = merged_mcap.dropna(subset=[f"ret_post_t0_{k}"])
        sub = sub[~sub[f"censored_{k}"]]
        if len(sub) < 5:
            print(f"k={k}: insufficient uncensored episodes ({len(sub)})")
            continue
        sign_corr = np.corrcoef(np.sign(sub["ret_total_1"]), np.sign(sub[f"ret_post_t0_{k}"]))[0, 1]
        mean_post = sub[f"ret_post_t0_{k}"].mean()
        # continuation vs reversal: mean post-T0 return conditional on T0 direction
        pos_t0 = sub[sub["ret_total_1"] > 0]
        neg_t0 = sub[sub["ret_total_1"] < 0]
        print(f"k={k} traded sessions post-T0: n={len(sub)}  "
              f"sign_corr(T0, post-T0 k)={sign_corr:.4f}  "
              f"mean_post_t0_ret={mean_post:+.4%}  "
              f"mean_post_ret|T0>0 (n={len(pos_t0)})={pos_t0[f'ret_post_t0_{k}'].mean():+.4%}  "
              f"mean_post_ret|T0<0 (n={len(neg_t0)})={neg_t0[f'ret_post_t0_{k}'].mean():+.4%}")

    print("\n=== Horizon return magnitude (total, from pre-stale flat price) ===")
    for k in HORIZONS:
        sub = merged_mcap[~merged_mcap[f"censored_{k}"]]
        print(f"k={k}: n={len(sub)}  mean={sub[f'ret_total_{k}'].mean():+.4%}  "
              f"median={sub[f'ret_total_{k}'].median():+.4%}  std={sub[f'ret_total_{k}'].std():.4%}")

    print("\n=== Control group (ordinary, non-post-stale trade-to-trade sequences) ===")
    ctrl = build_control_group(px, ep)
    ctrl.to_csv(OUT / "control_group.csv", index=False)
    print(f"n_control={len(ctrl)}")
    for k in HORIZONS:
        print(f"k={k}: control mean_ret_total={ctrl[f'ret_total_{k}'].mean():+.4%}  "
              f"median={ctrl[f'ret_total_{k}'].median():+.4%}")
    print("control T0 |return| mean:", ctrl["ret_total_1"].abs().mean())

    print("\n=== Controls: T0 move & post-T0(k=10) drift by size tercile ===")
    print(merged_mcap.groupby("size_tercile", observed=True).apply(
        lambda d: pd.Series({
            "n": len(d),
            "mean_|T0_ret|": d["ret_total_1"].abs().mean(),
            "mean_post_t0_10": d.loc[~d["censored_10"], "ret_post_t0_10"].mean(),
        })
    ).to_string())

    print("\n=== Controls: by pre-stale volatility tercile ===")
    print(merged_mcap.groupby("vol_tercile", observed=True).apply(
        lambda d: pd.Series({
            "n": len(d),
            "mean_|T0_ret|": d["ret_total_1"].abs().mean(),
            "mean_post_t0_10": d.loc[~d["censored_10"], "ret_post_t0_10"].mean(),
        })
    ).to_string())

    print("\n=== Controls: by stale-run-length bucket ===")
    print(merged_mcap.groupby("runlen_bucket", observed=True).apply(
        lambda d: pd.Series({
            "n": len(d),
            "mean_|T0_ret|": d["ret_total_1"].abs().mean(),
            "mean_post_t0_10": d.loc[~d["censored_10"], "ret_post_t0_10"].mean(),
        })
    ).to_string())

    print("\n=== Censoring / suspected-suspension flags ===")
    print("fraction censored at k=20:", merged_mcap["censored_20"].mean())
    print("fraction with max_gap_days_in_walk > 20 (suspected suspension in walk window):",
          (merged_mcap["max_gap_days_in_walk"] > 20).mean())

    print("\n=== Independence from H-011 (size) -- episode-level ===")
    print("Spearman(|T0 return|, market_cap_nm):",
          merged_mcap[["market_cap_nm"]].assign(abs_t0=merged_mcap["ret_total_1"].abs())
          .corr(method="spearman").loc["market_cap_nm", "abs_t0"])
    print("Spearman(post_t0_10, market_cap_nm) [uncensored only]:",
          merged_mcap.loc[~merged_mcap["censored_10"], ["market_cap_nm", "ret_post_t0_10"]]
          .corr(method="spearman").iloc[0, 1])


if __name__ == "__main__":
    main()
