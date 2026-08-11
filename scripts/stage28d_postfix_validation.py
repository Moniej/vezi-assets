"""Stage 28D -- post-fix pre-reform validation (2026-08-09). Applies the two
Stage 28B amendments (strict same-day treatment assignment; first-row
listing-date proxy) and re-runs the pre-reform-only checks against the
refreshed price feed (now current through 2026-08-07, still entirely
pre-reform -- reform effective 2026-08-17). No post-2026-08-17 data exists
or is used. No DiD, no economic gate, no return interpretation.

  PYTHONPATH=src python scripts/stage28d_postfix_validation.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "stage28d"
OUT.mkdir(parents=True, exist_ok=True)

REFORM_DATE = pd.Timestamp("2026-08-17")


def load_prices(con) -> pd.DataFrame:
    """De-duplicated one-row-per-(ticker,trade_date) panel, matching the
    platform's own established canonical convention
    (backtest_xs.load_panel(): drop_duplicates(subset=['ticker','trade_date'],
    keep='last')) -- NOT a new rule invented here. See Stage 28D writeup:
    equity_prices carries multiple source rows per ticker-day
    (ngx_pricelist_v1/v2, ngx_dol_v1) by design; almost all agree exactly
    (301,405/301,459 duplicate groups have identical close+volume), a small
    number (54) genuinely conflict and are resolved by keep='last' exactly
    as load_panel() already does."""
    df = pd.read_sql("SELECT ticker, trade_date, close, volume, source_id FROM equity_prices ORDER BY ticker, trade_date, source_id", con)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    n_before = len(df)
    df = df.drop_duplicates(subset=["ticker", "trade_date"], keep="last")
    print(f"[load_prices] de-duplicated {n_before} raw rows -> {len(df)} canonical (ticker,trade_date) rows")
    return df


def bucket(p):
    if p >= 1000:
        return "TREATED_>=1000"
    elif p >= 500:
        return "MIDBAND_500_999"
    else:
        return "CONTROL_<500"


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    px = load_prices(con)
    securities = pd.read_sql("SELECT ticker FROM securities", con)

    max_date = px["trade_date"].max()
    print("=== Data freshness (post-fix) ===")
    print(f"latest available trade_date: {max_date.date()}")
    print(f"gap to reform effective date (2026-08-17): {(REFORM_DATE - max_date).days} days")
    print(f"gap to 'today' (2026-08-09): {(pd.Timestamp('2026-08-09') - max_date).days} days "
          f"(negative = feed is now ahead of session date, i.e. current)")
    print(f"CONFIRMED: no row exists at or after 2026-08-17: "
          f"{(px['trade_date'] >= REFORM_DATE).sum()} rows (must be 0)")

    all_sessions = sorted(px["trade_date"].unique())
    print(f"total distinct trading sessions in dataset: {len(all_sessions)}")

    # ------------------------------------------------------------------
    # Amendment 1: strict same-day match only; no row on reference date -> INELIGIBLE
    # ------------------------------------------------------------------
    print(f"\n=== Section 1: treatment/control universe -- CORRECTED RULE (Amendment 1), rehearsal ref={max_date.date()} ===")
    same_day = px[px["trade_date"] == max_date][["ticker", "close"]].copy()
    same_day["bucket"] = same_day["close"].apply(bucket)

    all_tickers = set(securities["ticker"])
    eligible_tickers = set(same_day["ticker"])
    ineligible = all_tickers - eligible_tickers

    print(same_day["bucket"].value_counts().to_string())
    print(f"\nINELIGIBLE (no row on the reference session, per Amendment 1): {len(ineligible)} / {len(all_tickers)}")
    print(f"eligible (any bucket): {len(eligible_tickers)} / {len(all_tickers)}")

    same_day.to_csv(OUT / "corrected_bucket_assignment.csv", index=False)
    pd.Series(sorted(ineligible), name="ticker").to_csv(OUT / "ineligible_tickers.csv", index=False)

    # ------------------------------------------------------------------
    # Amendment 2: first equity_prices row as listing-date proxy
    # ------------------------------------------------------------------
    print(f"\n=== Section 2: newly-listed check (Amendment 2 -- first-row proxy) ===")
    first_row = px.sort_values(["ticker", "trade_date"]).groupby("ticker")["trade_date"].first()
    last_40 = all_sessions[-40:]
    pre_period_start = pd.Timestamp(last_40[0])
    newly_listed = first_row[first_row > pre_period_start]
    print(f"rehearsal pre-period start: {pre_period_start.date()}")
    print(f"tickers whose first-ever equity_prices row is after the pre-period start "
          f"(would be excluded from the pre-period): {len(newly_listed)}")
    if len(newly_listed):
        print(newly_listed.to_string())

    # ------------------------------------------------------------------
    # Min-observation gate under corrected rule
    # ------------------------------------------------------------------
    print(f"\n=== Section 5: minimum-observation feasibility (>=30/40), corrected rule ===")
    px40 = px[px["trade_date"].isin(last_40)]
    present_counts = px40.groupby("ticker").size()

    for grp in ["TREATED_>=1000", "MIDBAND_500_999", "CONTROL_<500"]:
        tickers_in_grp = same_day.loc[same_day["bucket"] == grp, "ticker"]
        counts = present_counts.reindex(tickers_in_grp).fillna(0)
        n_pass = (counts >= 30).sum()
        print(f"  {grp}: n_tickers={len(tickers_in_grp)}  pass_min_obs(>=30/40)={n_pass}  "
              f"median_sessions_present={counts.median() if len(counts) else float('nan')}  "
              f"min={counts.min() if len(counts) else float('nan')}  max={counts.max() if len(counts) else float('nan')}")

    print("\nTreated tickers and their session-presence detail:")
    treated_list = same_day.loc[same_day["bucket"] == "TREATED_>=1000", "ticker"].tolist()
    for t in treated_list:
        n = present_counts.get(t, 0)
        print(f"  {t}: close={same_day.loc[same_day.ticker==t,'close'].iloc[0]}  sessions_present_last40={n}")

    # ------------------------------------------------------------------
    # Pre-trend rehearsal on refreshed data, corrected groups
    # ------------------------------------------------------------------
    print(f"\n=== Section 3: pre-trend rehearsal (corrected groups, refreshed data) ===")
    px["prev_close"] = px.groupby("ticker")["close"].shift(1)
    px["is_zero"] = (px["close"] == px["prev_close"]) & px["prev_close"].notna()

    half = len(last_40) // 2
    first_half, second_half = last_40[:half], last_40[half:]

    def zf(tickers, sessions):
        sub = px[px.ticker.isin(tickers) & px.trade_date.isin(sessions)]
        return (sub["is_zero"].mean(), len(sub)) if len(sub) else (np.nan, 0)

    control_list = same_day.loc[same_day["bucket"] == "CONTROL_<500", "ticker"].tolist()
    midband_list = same_day.loc[same_day["bucket"] == "MIDBAND_500_999", "ticker"].tolist()

    for label, tickers in [("TREATED", treated_list), ("MIDBAND", midband_list), ("CONTROL", control_list)]:
        f_val, f_n = zf(tickers, first_half)
        s_val, s_n = zf(tickers, second_half)
        print(f"  {label} (n={len(tickers)}): first_half={f_val:.3f}(n={f_n})  second_half={s_val:.3f}(n={s_n})")

    print("\n(Rehearsal only -- real pre-trend check requires the real reference date, which is not yet")
    print("known. No DiD, no post-reform data, no economic interpretation performed.)")

    print("\n=== FINAL STATUS ===")
    print("WAIT -- 0 post-2026-08-17 sessions available. Protocol remains internally executable under")
    print("Amendments 1 and 2. No DiD run. No hypothesis. No backtest.")


if __name__ == "__main__":
    main()
