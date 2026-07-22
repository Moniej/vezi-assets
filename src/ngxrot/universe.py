"""Investable Research Universe (IRU) — rule-based, point-in-time membership.

iru_members(con, as_of) applies configs/iru.toml at a date using only data
knowable then. Deterministic and versioned: hypotheses record the IRU
version; rule changes require a new version + IC decision.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

PKG_ROOT = Path(__file__).resolve().parents[2]
IRU_CFG = PKG_ROOT / "configs" / "iru.toml"


def load_rules() -> dict:
    return tomllib.loads(IRU_CFG.read_text(encoding="utf-8"))


RENAMES_PATH = PKG_ROOT / "data" / "reference" / "symbol_renames.csv"


def rename_chain() -> dict[str, str]:
    """old_symbol -> canonical (final) symbol, VERIFIED renames only,
    following chains (A->B->C maps A and B to C)."""
    if not RENAMES_PATH.exists():
        return {}
    r = pd.read_csv(RENAMES_PATH)
    step = dict(zip(r[r.status == "verified"].old_symbol,
                    r[r.status == "verified"].new_symbol))
    out = {}
    for old in step:
        cur, seen = old, set()
        while cur in step and cur not in seen:
            seen.add(cur)
            cur = step[cur]
        out[old] = cur
    return out


def iru_members(con, as_of: str, rules: dict | None = None) -> pd.DataFrame:
    """IRU_v2 members at as_of (PIT, trailing window, rename-canonical).

    Relative liquidity: rank by trailing avg daily value among frequency-
    qualified names; keep rank <= liquidity_rank_max. Regime-stable and
    deterministic. IRU is ELIGIBILITY only — data-quality gating is the
    coverage gate's job (separated per IC directive 2026-07-17).
    """
    r = rules or load_rules()
    m = r["membership"]
    start = (pd.Timestamp(as_of) - pd.Timedelta(days=m["trailing_days"])
             ).strftime("%Y-%m-%d")
    df = pd.read_sql(
        "SELECT ticker, trade_date, value_traded FROM equity_prices "
        "WHERE confidence >= 0.9 AND trade_date > ? AND trade_date <= ?",
        con, params=(start, as_of))
    chain = rename_chain()
    df["ticker"] = df.ticker.map(lambda t: chain.get(t, t))
    g = df.groupby("ticker").agg(n_days=("trade_date", "nunique"),
                                 avg_value=("value_traded", "mean"),
                                 last_trade=("trade_date", "max")).reset_index()

    excl = set(r["instrument"]["exclude_symbols"])
    pats = r["instrument"]["exclude_patterns"]
    g = g[~g.ticker.isin(excl)]
    g = g[~g.ticker.str.upper().str.contains("|".join(pats), regex=True)]

    market_days = pd.read_sql(
        "SELECT DISTINCT trade_date FROM equity_prices WHERE confidence >= 0.9 "
        "AND trade_date <= ? ORDER BY trade_date DESC LIMIT ?",
        con, params=(as_of, m["max_stale_sessions"]))
    stale_cutoff = market_days.trade_date.min() if len(market_days) else start

    qual = g[(g.n_days >= m["min_trading_days"])
             & (g.last_trade >= stale_cutoff)].copy()
    qual = qual.sort_values("avg_value", ascending=False)
    qual["liq_rank"] = range(1, len(qual) + 1)
    out = qual[qual.liq_rank <= m["liquidity_rank_max"]].copy()
    out["as_of"] = as_of
    return out.reset_index(drop=True)


def iru_annual_summary(con) -> pd.DataFrame:
    """IRU size at mid-year and year-end for every year with data."""
    years = pd.read_sql(
        "SELECT DISTINCT substr(trade_date,1,4) AS y FROM equity_prices "
        "WHERE confidence >= 0.9 ORDER BY y", con).y.tolist()
    rows = []
    for y in years:
        for tag, d in (("mid", f"{y}-06-30"), ("end", f"{y}-12-31")):
            mem = iru_members(con, d)
            rows.append(dict(year=int(y), point=tag, as_of=d, iru_size=len(mem),
                             median_avg_value=float(mem.avg_value.median())
                             if len(mem) else None))
    return pd.DataFrame(rows)
