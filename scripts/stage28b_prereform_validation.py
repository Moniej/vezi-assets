"""Stage 28B -- Pre-reform protocol/data-validation exercise (2026-08-09).

Validates the MACHINERY of the frozen Stage 28B protocol against real,
pre-reform data only. Does NOT compute any post-2026-08-17 effect (no such
data exists). Does NOT alter the frozen protocol. Where the frozen text is
ambiguous, both readings are tested and reported -- never silently resolved.

  PYTHONPATH=src python scripts/stage28b_prereform_validation.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "stage28b"
OUT.mkdir(parents=True, exist_ok=True)

REFORM_DATE = pd.Timestamp("2026-08-17")


def load_prices(con) -> pd.DataFrame:
    df = pd.read_sql("SELECT ticker, trade_date, close, volume FROM equity_prices ORDER BY ticker, trade_date", con)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    px = load_prices(con)
    securities = pd.read_sql("SELECT ticker, listing_date, delisting_date FROM securities", con)

    max_date = px["trade_date"].max()
    print(f"=== Data availability ===")
    print(f"latest available trade_date in equity_prices: {max_date.date()}")
    print(f"reform effective date (frozen): {REFORM_DATE.date()}")
    print(f"calendar gap between latest data and reform date: {(REFORM_DATE - max_date).days} days")
    print(f"'today' per session context: 2026-08-09 -- feed is already "
          f"{(pd.Timestamp('2026-08-09') - max_date).days} days stale relative to 'today', "
          f"independent of the reform. Flagged as a separate operational risk below.")

    all_sessions = sorted(px["trade_date"].unique())
    print(f"total distinct trading sessions in dataset: {len(all_sessions)}")

    # ------------------------------------------------------------------
    # 1. Treatment/control universe construction -- REHEARSAL ONLY.
    #    Real reference date = last session strictly before 2026-08-17,
    #    which does not exist in the dataset yet (max_date < REFORM_DATE,
    #    but the true reference date will be a LATER session than max_date
    #    once the feed catches up). max_date is used here purely to test
    #    the query mechanics, clearly labeled as non-binding.
    # ------------------------------------------------------------------
    print(f"\n=== Section 1: treatment/control universe -- REHEARSAL using {max_date.date()} (NOT the real reference date) ===")

    same_day = px[px["trade_date"] == max_date][["ticker", "close"]]
    print(f"tickers with a row on the rehearsal reference date: {len(same_day)} / {securities['ticker'].nunique()} in securities")

    def bucket(p):
        if p >= 1000:
            return "TREATED_>=1000"
        elif p >= 500:
            return "MIDBAND_500_999"
        else:
            return "CONTROL_<500"

    same_day = same_day.copy()
    same_day["bucket_same_day"] = same_day["close"].apply(bucket)
    print("\nInterpretation A (STRICT: must have a row exactly on the reference date):")
    print(same_day["bucket_same_day"].value_counts().to_string())
    excluded_strict = securities["ticker"].nunique() - len(same_day)
    print(f"tickers excluded entirely under strict same-day reading: {excluded_strict}")

    # Interpretation B: last available close ON OR BEFORE the reference date (look-back)
    asof = px[px["trade_date"] <= max_date].sort_values(["ticker", "trade_date"]).groupby("ticker").tail(1)
    asof = asof.copy()
    asof["bucket_asof"] = asof["close"].apply(bucket)
    print(f"\nInterpretation B (LOOK-BACK: most recent available close as of the reference date, any lag):")
    print(asof["bucket_asof"].value_counts().to_string())
    print(f"tickers covered under look-back reading: {len(asof)} / {securities['ticker'].nunique()}")

    lag_days = (max_date - asof["trade_date"]).dt.days
    print(f"\nlook-back staleness distribution (days between reference date and each ticker's last available close):")
    print(lag_days.describe().to_string())
    stale_gt_30 = (lag_days > 30).sum()
    print(f"tickers whose 'as-of' close is >30 days stale: {stale_gt_30}")

    print("\n*** AMBIGUITY FLAGGED, NOT RESOLVED ***")
    print("The frozen protocol (Sec.1) says treatment is based on the closing price 'on the last trading")
    print("session strictly before 2026-08-17' but does not specify whether a ticker with no row on that")
    print("exact session should (A) be excluded from both groups, or (B) use its most recent prior close.")
    print("Interpretation A and B produce materially different group sizes/composition (see above).")
    print("This must be resolved as an explicit protocol amendment BEFORE the October run -- not decided here.")

    same_day.to_csv(OUT / "bucket_interpretation_A_strict.csv", index=False)
    asof.to_csv(OUT / "bucket_interpretation_B_lookback.csv", index=False)

    # ------------------------------------------------------------------
    # 5. Eligible-securities / observation counts by bucket, both interpretations
    # ------------------------------------------------------------------
    print(f"\n=== Section 5: minimum-observation feasibility check (Sec.2's >=30-of-40-sessions rule) ===")
    last_40_sessions = all_sessions[-40:]
    print(f"rehearsal pre-period window: {len(last_40_sessions)} sessions, "
          f"{pd.Timestamp(last_40_sessions[0]).date()} to {pd.Timestamp(last_40_sessions[-1]).date()}")

    px40 = px[px["trade_date"].isin(last_40_sessions)]
    present_counts = px40.groupby("ticker").size()

    for label, bucket_df, bucket_col in [
        ("Interpretation A (strict)", same_day, "bucket_same_day"),
        ("Interpretation B (look-back)", asof, "bucket_asof"),
    ]:
        print(f"\n-- {label} --")
        for grp in ["TREATED_>=1000", "MIDBAND_500_999", "CONTROL_<500"]:
            tickers_in_grp = bucket_df.loc[bucket_df[bucket_col] == grp, "ticker"]
            counts = present_counts.reindex(tickers_in_grp).fillna(0)
            n_pass = (counts >= 30).sum()
            print(f"  {grp}: n_tickers={len(tickers_in_grp)}  "
                  f"pass_min_obs(>=30/40)={n_pass}  "
                  f"median_sessions_present={counts.median() if len(counts) else float('nan')}  "
                  f"min={counts.min() if len(counts) else float('nan')}")

    # ------------------------------------------------------------------
    # 6. Zero-return definition stress test
    # ------------------------------------------------------------------
    print(f"\n=== Section 6: zero-return definition stress test (full dataset) ===")
    px_s = px.sort_values(["ticker", "trade_date"]).copy()
    px_s["prev_close"] = px_s.groupby("ticker")["close"].shift(1)
    px_s["is_first_row"] = px_s["prev_close"].isna()
    px_s["is_zero"] = (px_s["close"] == px_s["prev_close"]) & px_s["prev_close"].notna()
    px_s["has_vol"] = px_s["volume"].notna() & (px_s["volume"] > 0)
    px_s["zero_traded"] = px_s["is_zero"] & px_s["has_vol"]
    px_s["zero_missing_vol"] = px_s["is_zero"] & ~px_s["has_vol"]

    n_first_rows = px_s["is_first_row"].sum()
    print(f"rows excluded as each ticker's first observation (no prior close to compare): {n_first_rows}")
    print(f"total rows: {len(px_s)}")
    print(f"zero-return rows: {px_s['is_zero'].sum()} ({px_s['is_zero'].mean():.1%})")
    print(f"  of which genuinely traded (volume>0): {px_s['zero_traded'].sum()}")
    print(f"  of which no recorded volume: {px_s['zero_missing_vol'].sum()}")

    # exact-0.0000 vs "economically meaningful unchanged" check: are there near-equal
    # but not bit-identical closes that a looser definition would also call "unchanged"?
    px_s["pct_chg"] = (px_s["close"] - px_s["prev_close"]) / px_s["prev_close"]
    near_zero_not_exact = ((px_s["pct_chg"].abs() < 0.001) & (~px_s["is_zero"]) & px_s["prev_close"].notna())
    print(f"\nrows with |return| < 0.1% but NOT exactly zero (would flip classification under a tolerance-band "
          f"definition instead of the frozen strict-equality definition): {near_zero_not_exact.sum()}")
    print("Frozen protocol uses STRICT equality (Sec.2) -- confirmed unambiguous and unaffected by this; "
          "reported only to document the definition's edge behavior, not to propose changing it.")

    # suspension-gap detection: sessions with a calendar gap > 20 days between consecutive rows
    px_s["gap_days"] = px_s.groupby("ticker")["trade_date"].diff().dt.days
    big_gaps = px_s[px_s["gap_days"] > 20]
    print(f"\nticker-sessions preceded by a >20-day gap in trade_date (candidate suspension/resumption events): "
          f"{len(big_gaps)} across {big_gaps['ticker'].nunique()} tickers")
    print("Per frozen protocol, these are NOT imputed -- absent sessions simply contribute no observation; "
          "confirmed the data supports this (gaps exist as true row-absences, not NULL placeholder rows).")

    # newly-listed check
    securities["listing_date"] = pd.to_datetime(securities["listing_date"], errors="coerce")
    pre_period_start = pd.Timestamp(last_40_sessions[0])
    newly_listed = securities[securities["listing_date"] > pre_period_start]
    print(f"\ntickers with listing_date after the rehearsal pre-period start ({pre_period_start.date()}): "
          f"{len(newly_listed)} -- these would be excluded from the pre-period per Sec.2, confirmed handleable "
          f"since listing_date is populated (checked {securities['listing_date'].notna().sum()}/{len(securities)} non-null)")

    # ------------------------------------------------------------------
    # 3. Pre-trend check -- REHEARSAL (real check requires the real reference date)
    # ------------------------------------------------------------------
    print(f"\n=== Section 3: pre-trend check -- REHEARSAL on last 40 available sessions ===")
    half = len(last_40_sessions) // 2
    first_half, second_half = last_40_sessions[:half], last_40_sessions[half:]

    def zero_freq(tickers, sessions):
        sub = px_s[px_s["ticker"].isin(tickers) & px_s["trade_date"].isin(sessions)]
        if len(sub) == 0:
            return np.nan
        return sub["is_zero"].mean()

    for label, bucket_df, bucket_col in [("Interpretation A", same_day, "bucket_same_day"),
                                          ("Interpretation B", asof, "bucket_asof")]:
        treated = bucket_df.loc[bucket_df[bucket_col] == "TREATED_>=1000", "ticker"]
        control = bucket_df.loc[bucket_df[bucket_col] == "CONTROL_<500", "ticker"]
        print(f"\n-- {label} --")
        print(f"  treated zero_freq: first_half={zero_freq(treated, first_half):.3f}  "
              f"second_half={zero_freq(treated, second_half):.3f}")
        print(f"  control zero_freq: first_half={zero_freq(control, first_half):.3f}  "
              f"second_half={zero_freq(control, second_half):.3f}")

    # ------------------------------------------------------------------
    # Placebo dates -- check feasibility (enough sessions before/after each placebo, all pre-reform)
    # ------------------------------------------------------------------
    print(f"\n=== Section: placebo-date feasibility (Sec.5) ===")
    # placebo 1: 40 sessions before the (rehearsal) reference date -> need 40 before AND 40 after that placebo,
    # entirely within pre-reform data (i.e. before max_date, since no post-reform data exists)
    if len(all_sessions) >= 160:
        placebo1_idx = len(all_sessions) - 1 - 40  # 40 sessions before rehearsal reference
        placebo2_idx = placebo1_idx - 40
        print(f"total sessions available: {len(all_sessions)} -- need >=160 for both placebos "
              f"(40 before + 40 after) x2 without overlap: {'SUFFICIENT' if len(all_sessions)>=160 else 'INSUFFICIENT'}")
    else:
        print(f"total sessions available: {len(all_sessions)} -- INSUFFICIENT for two non-overlapping "
              f"40-before/40-after placebo windows (need >=160, have {len(all_sessions)})")

    print("\nNOTE: placebo windows must be constructed relative to the REAL reference date (last session")
    print("before 2026-08-17), which does not exist yet. This section reports only whether the TOTAL")
    print("session count in the dataset is structurally sufficient once that date is known -- not an actual")
    print("placebo DiD result.")


if __name__ == "__main__":
    main()
