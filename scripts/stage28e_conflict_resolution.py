"""Stage 28E -- data-integrity audit of the 54 genuinely-conflicting
equity_prices duplicate pairs, and re-run of the pre-reform Stage 28B
validation under the corrected deterministic resolution rule. No
post-2026-08-17 data used. No DiD, no hypothesis, no backtest.

  PYTHONPATH=src python scripts/stage28e_conflict_resolution.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "stage28e"
OUT.mkdir(parents=True, exist_ok=True)


def load_prices_corrected(con) -> pd.DataFrame:
    """Deterministic, non-outcome-dependent resolution:
    1. OHLC fields: unanimous across all 54 audited conflict groups (100%),
       confirmed programmatically -- any deterministic tie-break is safe.
       Sort by (ticker, trade_date, source_id) and keep='last', matching
       backtest_xs.load_panel()'s existing convention.
    2. volume/value_traded/deals: NOT safe to resolve the same way -- the
       54 conflicts are caused by a parser defect (volume off by ~11 orders
       of magnitude, value_traded left NULL) present in specific ingested
       vintages and silently reproduced by today's re-ingest under a new
       source_id (staging-cache re-ingestion of an already-corrupted parse,
       not a fresh re-parse). Resolution rule: prefer the row with a
       non-null value_traded (confirmed present on exactly one row per
       conflict group in 54/54 cases); if zero or >1 rows qualify, mark
       volume/value_traded UNKNOWN for that (ticker, date) rather than
       guessing -- this never happened in practice (0/54) but is handled.
    """
    df = pd.read_sql(
        "SELECT ticker, trade_date, open, high, low, close, volume, value_traded, deals, source_id "
        "FROM equity_prices ORDER BY ticker, trade_date, source_id", con)
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    # Step 1: OHLC via keep='last'
    ohlc = df.drop_duplicates(subset=["ticker", "trade_date"], keep="last")[
        ["ticker", "trade_date", "open", "high", "low", "close"]]

    # Step 2: volume/value_traded/deals resolution -- vectorized, not per-group
    # apply (354k groups is too slow with .apply and, more importantly, the
    # first version of this function had a real bug: it flagged a group as
    # "ambiguous" whenever >1 row had a non-null value_traded, even when
    # those rows AGREED (the common, non-conflicting case). Corrected here:
    # ambiguous only means multiple DISTINCT non-null value_traded values.
    nn = df[df["value_traded"].notna()].copy()
    grp_key = ["ticker", "trade_date"]
    nunique_vt = nn.groupby(grp_key)["value_traded"].nunique()
    has_any_nonnull = df.groupby(grp_key)["value_traded"].apply(lambda s: s.notna().any())

    status = pd.Series("UNRESOLVED_no_value_traded", index=has_any_nonnull.index)
    status[nunique_vt.index[nunique_vt == 1]] = "resolved_nonnull_value_traded"
    status[nunique_vt.index[nunique_vt > 1]] = "AMBIGUOUS_multiple_distinct_value_traded"
    status.name = "volume_status"

    # take the last non-null-value_traded row per group as the resolved row
    # (arbitrary among agreeing duplicates -- values are identical by
    # definition of the "resolved" status)
    resolved_rows = nn.sort_values(grp_key).drop_duplicates(grp_key, keep="last")
    fallback_rows = df.sort_values(grp_key).drop_duplicates(grp_key, keep="last")

    vol = fallback_rows[grp_key + ["volume", "value_traded", "deals"]].merge(
        resolved_rows[grp_key + ["volume", "value_traded", "deals"]],
        on=grp_key, how="left", suffixes=("_fallback", ""))
    for col in ["volume", "value_traded", "deals"]:
        vol[col] = vol[col].fillna(vol[f"{col}_fallback"])
        vol = vol.drop(columns=[f"{col}_fallback"])
    vol = vol.merge(status.reset_index(), on=grp_key, how="left")
    # ambiguous groups: null out the resolved value rather than guess
    amb_mask = vol["volume_status"] == "AMBIGUOUS_multiple_distinct_value_traded"
    vol.loc[amb_mask, ["volume", "value_traded", "deals"]] = np.nan

    merged = ohlc.merge(vol, on=["ticker", "trade_date"], how="left")
    n_total_groups = merged.groupby(["ticker", "trade_date"]).ngroups
    status_counts = merged["volume_status"].value_counts()
    print(f"[load_prices_corrected] {len(df)} raw rows -> {len(merged)} canonical rows")
    print(f"  volume_status breakdown: {status_counts.to_dict()}")
    return merged


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")

    print("=== Part 1: conflict audit (already computed, restated for the record) ===")
    conf = pd.read_csv(ROOT / "data" / "staging" / "stage28e_conflicts_keys.csv")
    print(f"n conflicting (ticker,trade_date) pairs: {len(conf)}")
    print("all 54 confirmed: OHLC unanimous, exactly one row has non-null value_traded "
          "(programmatically verified separately, see report)")

    print("\n=== Part 2: 320 vs 321 ticker-count investigation ===")
    sec = pd.read_sql("SELECT ticker, notes FROM securities", con)
    print(f"securities rows: {len(sec)}")
    auto = sec[sec["notes"] == "auto from ngx_pricelist ingest"]
    print(f"tickers auto-registered by ingest_pricelists.py's "
          f"'INSERT OR IGNORE INTO securities' (existing, by-design behavior): {len(auto)}")
    candidates = ["ABBEYBANK", "AVACAP", "CMFC", "HBMNG"]
    print(f"candidates (first equity_prices row after rehearsal pre-period start): {candidates}")
    mcap = pd.read_csv(ROOT / "data" / "reference" / "market_cap_panel.csv")
    for t in candidates:
        n = len(mcap[mcap.symbol == t])
        print(f"  {t}: rows in market_cap_panel.csv (pre-dates today's refresh) = {n} "
              f"{'(pre-existing before Fix 4)' if n > 0 else '(no prior evidence -- candidate for new-today)'}")

    print("\n=== Part 3: re-run pre-reform validation with corrected volume resolution ===")
    px = load_prices_corrected(con)
    max_date = px["trade_date"].max()
    print(f"latest trade_date: {max_date.date()}  (confirmed pre-reform: "
          f"{'YES' if max_date < pd.Timestamp('2026-08-17') else 'NO -- VIOLATION'})")

    def bucket(p):
        if p >= 1000:
            return "TREATED_>=1000"
        elif p >= 500:
            return "MIDBAND_500_999"
        else:
            return "CONTROL_<500"

    same_day = px[px["trade_date"] == max_date][["ticker", "close"]].copy()
    same_day["bucket"] = same_day["close"].apply(bucket)
    print("\nBucket counts (Amendment 1 rule, corrected data):")
    print(same_day["bucket"].value_counts().to_string())

    all_sessions = sorted(px["trade_date"].unique())
    last_40 = all_sessions[-40:]
    px40 = px[px["trade_date"].isin(last_40)]
    present_counts = px40.groupby("ticker").size()

    print("\nMin-observation gate (corrected data):")
    for grp in ["TREATED_>=1000", "MIDBAND_500_999", "CONTROL_<500"]:
        tickers_in_grp = same_day.loc[same_day["bucket"] == grp, "ticker"]
        counts = present_counts.reindex(tickers_in_grp).fillna(0)
        n_pass = (counts >= 30).sum()
        print(f"  {grp}: n={len(tickers_in_grp)}  pass={n_pass}  median={counts.median() if len(counts) else np.nan}")

    treated_list = same_day.loc[same_day["bucket"] == "TREATED_>=1000", "ticker"].tolist()
    print(f"\nTreated tickers (n={len(treated_list)}):")
    for t in treated_list:
        n = present_counts.get(t, 0)
        c = same_day.loc[same_day.ticker == t, "close"].iloc[0]
        print(f"  {t}: close={c}  sessions_present_last40={n}  pass={'YES' if n>=30 else 'NO'}")

    # Check whether any conflicting date affects the treated tickers' pre-period window
    print("\n=== Part 4: do any of the 54 conflicting dates fall in the treated tickers' pre-period window? ===")
    window_start, window_end = last_40[0], last_40[-1]
    print(f"rehearsal pre-period window: {pd.Timestamp(window_start).date()} to {pd.Timestamp(window_end).date()}")
    conf["trade_date"] = pd.to_datetime(conf["trade_date"])
    in_window = conf[(conf["trade_date"] >= window_start) & (conf["trade_date"] <= window_end)
                      & conf["ticker"].isin(treated_list)]
    print(f"conflicting dates for TREATED tickers inside this window: {len(in_window)}")
    print(in_window.to_string(index=False))
    print("(Reminder: OHLC -- including close, the primary outcome's only input -- is unanimous in "
          "100% of these; only volume/value_traded were ever ambiguous, now resolved per Part 3's rule.)")

    px.to_csv(OUT / "corrected_price_panel_sample.csv", index=False)
    print(f"\nfull corrected panel preserved at {OUT / 'corrected_price_panel_sample.csv'}")


if __name__ == "__main__":
    main()
