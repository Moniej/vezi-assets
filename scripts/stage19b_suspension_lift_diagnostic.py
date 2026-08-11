"""Stage 19B -- frozen, pre-registered diagnostic (2026-08-08). NOT a backtest,
NOT a portfolio. Two diagnostics only, spec fixed before execution and not
altered after seeing output:

1. Post-lift persistence: baseline = close at T+2 sessions after reopening
   (excludes the first 2 sessions to strip the auction/reopening shock),
   cumulative raw return from T+2 to T+7 / T+12 / T+22. Truncated windows
   (re-suspension or data end) are reported as truncated, not extrapolated
   or dropped.
2. Liquidity/executability: daily volume + cumulative turnover over the
   T+2..window span; compared against H-011's existing 10%-of-60-day-ADTV
   capacity rule. No bid/ask data exists on this platform, so turnover is
   the sole liquidity proxy (disclosed limitation, not worked around).

Events (suspension-lift, from docs/STAGE19_REGULATORY_STATE_TRANSITION_RESEARCH_2026-08-08.md):
  MBENEFIT   lift 2025-03-20
  INTENEGINS lift 2025-10-07
  ASOSAVINGS lift 2025-10-21 (re-suspended 2025-11-22)
  ZICHIS     lift 2026-03-23

  PYTHONPATH=src python scripts/stage19b_suspension_lift_diagnostic.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVENTS = [
    ("MBENEFIT", "2025-03-20"),
    ("INTENEGINS", "2025-10-07"),
    ("ASOSAVINGS", "2025-10-21"),
    ("ZICHIS", "2026-03-23"),
]

WINDOWS = [5, 10, 20]  # sessions forward from the T+2 baseline


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    for ticker, lift_date in EVENTS:
        rows = con.execute(
            "SELECT trade_date, close, volume FROM equity_prices "
            "WHERE ticker=? AND trade_date >= ? ORDER BY trade_date",
            (ticker, lift_date),
        ).fetchall()
        print(f"\n=== {ticker}  lift={lift_date}  sessions_available={len(rows)} ===")
        if len(rows) < 3:
            print("  INSUFFICIENT DATA for T+2 baseline -- reporting as such, not extrapolating.")
            continue

        t2_date, t2_close, _ = rows[2]
        print(f"  T+2 baseline: {t2_date} close={t2_close}")

        for w in WINDOWS:
            idx = 2 + w
            if idx >= len(rows):
                print(f"  [{w}-session fwd] TRUNCATED -- only {len(rows) - 3} sessions "
                      f"available after T+2 (need {w}). Not extrapolated.")
                continue
            end_date, end_close, _ = rows[idx]
            ret = (end_close / t2_close) - 1.0
            print(f"  [{w}-session fwd] T+2 -> {end_date}: close {t2_close} -> {end_close}  "
                  f"cum_return={ret:+.2%}")

        # Liquidity / executability over whatever window actually exists post T+2
        post_t2 = rows[2:]
        vols = [v for _, _, v in post_t2 if v is not None]
        n_missing_vol = sum(1 for _, _, v in post_t2 if v is None)
        total_turnover_shares = sum(vols) if vols else 0
        avg_daily_vol = (sum(vols) / len(vols)) if vols else None
        print(f"  Liquidity (T+2 onward, {len(post_t2)} sessions, {n_missing_vol} missing volume):")
        print(f"    avg_daily_volume={avg_daily_vol}")
        print(f"    total_volume_shares={total_turnover_shares}")

        # Pre-suspension 60-session ADTV baseline (PIT-available liquidity context)
        pre = con.execute(
            "SELECT volume FROM equity_prices WHERE ticker=? AND trade_date < ? "
            "ORDER BY trade_date DESC LIMIT 60",
            (ticker, lift_date),
        ).fetchall()
        pre_vols = [v for (v,) in pre if v is not None]
        pre_adtv = (sum(pre_vols) / len(pre_vols)) if pre_vols else None
        print(f"    pre-suspension 60-session ADTV (last available before lift date)="
              f"{pre_adtv} (n={len(pre_vols)} non-null of {len(pre)} rows)")
        if avg_daily_vol is not None and pre_adtv:
            print(f"    post-lift avg daily volume vs pre-suspension ADTV ratio="
                  f"{avg_daily_vol / pre_adtv:.2f}x")
        cap_10pct = f"{avg_daily_vol * 0.10:,.0f} shares/day" if avg_daily_vol else "n/a"
        print(f"    H-011-style 10%-of-ADTV cap on post-lift volume: {cap_10pct}")


if __name__ == "__main__":
    main()
