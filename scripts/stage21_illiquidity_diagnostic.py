"""Stage 21 -- Illiquidity/Staleness Mechanism Diagnostic (2026-08-09).

Measurement/diagnostic script ONLY. No portfolio, no strategy return, no
threshold chosen by looking at forward-return results, no hypothesis
registered. Every metric definition and the one forward-return diagnostic
spec below is fixed before the script is run and is not altered afterward.

Frozen definitions (fixed BEFORE execution):
  - Zero-return session: close == previous trading session's close for the
    same ticker (strict equality on the stored close price).
  - "Genuine unchanged" vs "missing observation": a zero-return session is
    split into (a) volume IS NOT NULL AND volume > 0 (traded, price simply
    didn't move) vs (b) volume IS NULL OR volume == 0 (no recorded trade).
  - Illiquidity proxy (primary, PIT-safe): trailing 60-session zero-return
    frequency, computed strictly from sessions up to and including the
    snapshot date (no look-ahead).
  - Size proxy: market_cap_nm from data/reference/market_cap_panel.csv as of
    the same snapshot date (identical field to size_scores()'s panel["mcap"]
    input).
  - Forward-return diagnostic (frozen spec, single horizon, chosen as a
    round conventional number, NOT selected from a grid of candidates):
    cumulative raw close-to-close return over the NEXT 20 trading sessions
    after the snapshot date. Snapshots taken monthly (last available
    trading session of each calendar month common to both the price panel
    and the market-cap panel).
  - Sort: within each cross-sectional snapshot, rank the eligible universe
    into terciles by market cap, then within each market-cap tercile rank
    into terciles by the illiquidity proxy. Report mean forward return per
    (size tercile x illiquidity tercile) cell, pooled across all snapshot
    dates. Also one pooled OLS: fwd_return ~ illiq_rank_within_size_tercile
    + size_tercile dummies. This is a descriptive/diagnostic regression,
    not a strategy return, portfolio, or backtest -- no weights, no costs,
    no rebalancing rule.
  - Eligibility: ticker must have >=250 equity_prices sessions overall and
    a market-cap-panel match on the snapshot date to be included in any
    given cross-section.

  PYTHONPATH=src python scripts/stage21_illiquidity_diagnostic.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "stage21"
OUT.mkdir(parents=True, exist_ok=True)


def load_prices() -> pd.DataFrame:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    df = pd.read_sql(
        "SELECT ticker, trade_date, close, volume FROM equity_prices ORDER BY ticker, trade_date",
        con,
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_mcap() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "reference" / "market_cap_panel.csv")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.rename(columns={"symbol": "ticker"})


def part_a_descriptives(px: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, g in px.groupby("ticker"):
        g = g.sort_values("trade_date").reset_index(drop=True)
        if len(g) < 250:
            continue
        prev_close = g["close"].shift(1)
        is_zero = (g["close"] == prev_close) & prev_close.notna()
        has_vol = g["volume"].notna() & (g["volume"] > 0)
        zero_traded = is_zero & has_vol
        zero_missing = is_zero & ~has_vol
        n = len(g) - 1  # first row has no prior close

        # trading frequency
        trading_freq = has_vol.sum() / len(g)

        # staleness: consecutive zero-return run lengths
        run_id = (~is_zero).cumsum()
        run_lengths = is_zero.groupby(run_id).sum()
        max_run = run_lengths.max() if len(run_lengths) else 0
        mean_run = run_lengths[run_lengths > 0].mean() if (run_lengths > 0).any() else 0.0

        # historical stability: zero-return freq first half vs second half
        mid = len(g) // 2
        zf_first = is_zero.iloc[:mid].sum() / max(mid, 1)
        zf_second = is_zero.iloc[mid:].sum() / max(len(g) - mid, 1)

        # volume persistence: lag-1 autocorrelation of log(volume+1)
        logvol = np.log1p(g["volume"].fillna(0))
        vol_autocorr = logvol.autocorr(lag=1)

        # volume shocks: days where volume > 3x trailing 60-session mean volume
        trailing_vol_mean = g["volume"].fillna(0).rolling(60, min_periods=20).mean().shift(1)
        shock = (g["volume"].fillna(0) > 3 * trailing_vol_mean) & trailing_vol_mean.notna()
        shock_freq = shock.sum() / len(g)

        # price-discovery proxy: return autocorrelation (lag-1)
        ret = g["close"].pct_change()
        ret_autocorr = ret.autocorr(lag=1)

        # return clustering after inactivity: mean |return| on the session
        # immediately following a run of >=5 consecutive zero-return sessions,
        # vs the unconditional mean |return|
        run_end = (is_zero.shift(1).fillna(False)) & (~is_zero)
        long_run_end = run_end & (run_lengths.reindex(run_id).values >= 5) if len(run_lengths) else pd.Series(False, index=g.index)
        post_inactivity_idx = g.index[long_run_end.fillna(False)] if isinstance(long_run_end, pd.Series) else []
        post_inactivity_ret = ret.loc[post_inactivity_idx].abs().mean() if len(post_inactivity_idx) else np.nan
        unconditional_abs_ret = ret.abs().mean()

        rows.append(dict(
            ticker=ticker,
            n_sessions=len(g),
            zero_return_freq=is_zero.sum() / n if n else np.nan,
            zero_traded_freq=zero_traded.sum() / n if n else np.nan,
            zero_missing_freq=zero_missing.sum() / n if n else np.nan,
            trading_freq=trading_freq,
            max_consecutive_zero_run=int(max_run),
            mean_zero_run_len=mean_run,
            zero_freq_first_half=zf_first,
            zero_freq_second_half=zf_second,
            volume_autocorr_lag1=vol_autocorr,
            volume_shock_freq=shock_freq,
            return_autocorr_lag1=ret_autocorr,
            post_inactivity_abs_ret=post_inactivity_ret,
            unconditional_abs_ret=unconditional_abs_ret,
        ))
    return pd.DataFrame(rows)


def part_b_independence(px: pd.DataFrame, mcap: pd.DataFrame) -> dict:
    # trailing 60-session zero-return freq per ticker/date, PIT-safe
    px = px.sort_values(["ticker", "trade_date"]).copy()
    px["prev_close"] = px.groupby("ticker")["close"].shift(1)
    px["is_zero"] = (px["close"] == px["prev_close"]) & px["prev_close"].notna()
    px["illiq_60"] = (
        px.groupby("ticker")["is_zero"]
        .rolling(60, min_periods=30).mean()
        .reset_index(level=0, drop=True)
    )
    merged = px.merge(mcap[["ticker", "trade_date", "market_cap_nm"]], on=["ticker", "trade_date"], how="inner")
    merged = merged.dropna(subset=["illiq_60", "market_cap_nm"])
    merged["log_mcap"] = np.log(merged["market_cap_nm"].clip(lower=1))

    spearman = merged[["illiq_60", "market_cap_nm"]].corr(method="spearman").iloc[0, 1]
    pearson_log = merged[["illiq_60", "log_mcap"]].corr(method="pearson").iloc[0, 1]

    return dict(
        n_obs=len(merged),
        spearman_illiq_vs_mcap=spearman,
        pearson_illiq_vs_log_mcap=pearson_log,
    ), merged


def part_c_forward_return_diagnostic(merged: pd.DataFrame, px: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    px2 = px.sort_values(["ticker", "trade_date"]).copy()
    px2["fwd_ret_20"] = (
        px2.groupby("ticker")["close"].shift(-20) / px2["close"] - 1.0
    )
    snap = merged.merge(px2[["ticker", "trade_date", "fwd_ret_20"]], on=["ticker", "trade_date"], how="left")
    snap["month"] = snap["trade_date"].dt.to_period("M")
    snap = snap.sort_values(["ticker", "trade_date"]).groupby(["ticker", "month"]).tail(1)
    snap = snap.dropna(subset=["fwd_ret_20"])

    def tercile(s: pd.Series) -> pd.Series:
        try:
            return pd.qcut(s, 3, labels=["T1_low", "T2_mid", "T3_high"], duplicates="drop")
        except ValueError:
            return pd.Series(["NA"] * len(s), index=s.index)

    snap["size_tercile"] = snap.groupby("trade_date")["market_cap_nm"].transform(tercile)
    snap["illiq_tercile"] = snap.groupby(["trade_date", "size_tercile"])["illiq_60"].transform(tercile)

    cell = (
        snap.groupby(["size_tercile", "illiq_tercile"], observed=True)["fwd_ret_20"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )

    # pooled OLS: fwd_ret_20 ~ illiq_rank_within_size + size dummies
    snap["illiq_rank_within_size"] = snap.groupby(["trade_date", "size_tercile"])["illiq_60"].rank(pct=True)
    size_dum = pd.get_dummies(snap["size_tercile"], prefix="size", drop_first=True)
    X = pd.concat([snap[["illiq_rank_within_size"]], size_dum], axis=1).astype(float)
    X.insert(0, "const", 1.0)
    y = snap["fwd_ret_20"].astype(float)
    valid = X.notna().all(axis=1) & y.notna()
    X, y = X[valid].values, y[valid].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    sigma2 = (resid @ resid) / max(n - k, 1)
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(sigma2 * xtx_inv))
    coef_names = ["const", "illiq_rank_within_size"] + list(size_dum.columns)
    ols = pd.DataFrame({"coef": beta, "se": se, "t": beta / np.where(se == 0, np.nan, se)}, index=coef_names)

    return cell, ols


def main() -> None:
    px = load_prices()
    mcap = load_mcap()

    print("=== Part A: per-ticker descriptives ===")
    desc = part_a_descriptives(px)
    desc.to_csv(OUT / "part_a_descriptives.csv", index=False)
    print(f"n_tickers={len(desc)}")
    print(desc[[
        "zero_return_freq", "zero_traded_freq", "zero_missing_freq", "trading_freq",
        "max_consecutive_zero_run", "mean_zero_run_len", "volume_shock_freq",
        "return_autocorr_lag1",
    ]].describe(percentiles=[.1, .25, .5, .75, .9]).to_string())
    print("\nStability (corr of first-half vs second-half zero-return freq across tickers):")
    print(desc[["zero_freq_first_half", "zero_freq_second_half"]].corr().iloc[0, 1])
    print("\nReturn clustering after inactivity (mean |return|):")
    print("post_inactivity_abs_ret mean:", desc["post_inactivity_abs_ret"].mean())
    print("unconditional_abs_ret mean:  ", desc["unconditional_abs_ret"].mean())

    print("\n=== Part B: independence from H-011 (mcap) ===")
    stats, merged = part_b_independence(px, mcap)
    print(stats)
    merged.to_csv(OUT / "part_b_merged_panel.csv", index=False)

    print("\n=== Part C: frozen forward-return diagnostic (NOT a strategy return) ===")
    cell, ols = part_c_forward_return_diagnostic(merged, px)
    cell.to_csv(OUT / "part_c_cell_means.csv", index=False)
    ols.to_csv(OUT / "part_c_ols.csv")
    print(cell.to_string())
    print("\nPooled OLS (fwd_ret_20 ~ illiq_rank_within_size_tercile + size dummies):")
    print(ols.to_string())


if __name__ == "__main__":
    main()
