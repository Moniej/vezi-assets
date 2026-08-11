"""Research OS -- data-quality visibility.

Composes EXISTING sources of truth (data_quality_log, corporate_actions,
extracted_facts, equity_prices, instrument_identity.py's rename bridging)
into a single, read-only quality report for a given ticker set/date range.
No new table, no new detection logic beyond simple composition -- this
module does not decide what counts as a quality problem; it surfaces what
the platform's own existing checks have already recorded, plus a couple
of cheap, purely descriptive joins (missing-day count, multi-source
disagreement) that were previously only ever produced ad hoc in one-off
scripts (e.g. this session's ngxpulse_cross_validation.py).
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from .instrument_identity import resolve_ticker_history_symbols


def quality_flags(con: sqlite3.Connection, tickers: list[str], start: str | None = None,
                   end: str | None = None) -> pd.DataFrame:
    """All data_quality_log rows for these tickers (optionally date-
    bounded), unresolved first. Bulk/summary entries (trade_date IS NULL,
    e.g. entity_code='MULTIPLE') are included only when no ticker/date
    filter would exclude them, since they are not tied to one ticker."""
    if not tickers:
        return pd.DataFrame(columns=["check_name", "entity_code", "trade_date", "severity",
                                      "detail", "resolved", "logged_at"])
    ph = ",".join("?" * len(tickers))
    q = (f"SELECT check_name, entity_code, trade_date, severity, detail, resolved, logged_at "
         f"FROM data_quality_log WHERE entity_type='ticker' AND entity_code IN ({ph})")
    params: list = list(tickers)
    if start:
        q += " AND (trade_date >= ? OR trade_date IS NULL)"
        params.append(start)
    if end:
        q += " AND (trade_date <= ? OR trade_date IS NULL)"
        params.append(end)
    q += " ORDER BY resolved ASC, logged_at DESC"
    return pd.read_sql(q, con, params=params)


def missing_observations(con: sqlite3.Connection, tickers: list[str], start: str, end: str,
                          reference_index: str = "NGXASI") -> pd.DataFrame:
    """Per-ticker count of trading days (dates the reference index itself
    has a level for, i.e. the market was open) with NO equity_prices row
    in [start, end]. A cheap, honest completeness signal -- does not
    attempt to distinguish "genuinely didn't trade" (illiquid name) from
    "we failed to capture it" (disclosed as a limitation, not resolved
    here)."""
    calendar = pd.read_sql(
        "SELECT DISTINCT trade_date FROM index_levels WHERE index_code = ? "
        "AND trade_date BETWEEN ? AND ?", con, params=(reference_index, start, end))
    trading_days = set(calendar.trade_date)
    rows = []
    for t in tickers:
        have = pd.read_sql(
            "SELECT DISTINCT trade_date FROM equity_prices WHERE ticker = ? "
            "AND trade_date BETWEEN ? AND ?", con, params=(t, start, end))
        have_days = set(have.trade_date)
        rows.append({"ticker": t, "trading_days_in_calendar": len(trading_days),
                     "days_present": len(have_days & trading_days),
                     "days_missing": len(trading_days - have_days)})
    return pd.DataFrame(rows)


def source_conflicts(con: sqlite3.Connection, tickers: list[str], start: str, end: str,
                      tolerance_pct: float = 0.01) -> pd.DataFrame:
    """(ticker, trade_date) pairs where more than one source has a close
    price and they disagree by more than tolerance_pct. Read-only
    detection, same spirit as this session's cross-validation script but
    generalized to any ticker set/window instead of a fixed 12-ticker
    sample."""
    if not tickers:
        return pd.DataFrame(columns=["ticker", "trade_date", "n_sources", "min_close",
                                      "max_close", "pct_diff"])
    ph = ",".join("?" * len(tickers))
    q = (f"SELECT ticker, trade_date, source_id, close FROM equity_prices "
         f"WHERE ticker IN ({ph}) AND trade_date BETWEEN ? AND ?")
    df = pd.read_sql(q, con, params=list(tickers) + [start, end])
    if df.empty:
        return pd.DataFrame(columns=["ticker", "trade_date", "n_sources", "min_close",
                                      "max_close", "pct_diff"])
    g = df.groupby(["ticker", "trade_date"]).agg(
        n_sources=("source_id", "nunique"), min_close=("close", "min"), max_close=("close", "max"),
    ).reset_index()
    g["pct_diff"] = (g.max_close - g.min_close) / g.min_close.replace(0, pd.NA)
    return g[(g.n_sources > 1) & (g.pct_diff > tolerance_pct)].sort_values("pct_diff", ascending=False)


def ticker_identity_notes(con: sqlite3.Connection, tickers: list[str]) -> pd.DataFrame:
    """One row per ticker showing whether it has a known rename chain
    (reuses instrument_identity.py -- no re-derivation)."""
    rows = []
    for t in tickers:
        eras = resolve_ticker_history_symbols(con, t)
        rows.append({"ticker": t, "has_rename_history": len(eras) > 1,
                     "full_chain": [e.ticker for e in eras],
                     "earliest_era_start": eras[0].valid_from})
    return pd.DataFrame(rows)


def corporate_action_notes(con: sqlite3.Connection, tickers: list[str]) -> pd.DataFrame:
    """Real corporate-action facts on file for these tickers, from BOTH
    representations this platform currently has (disclosed as
    unsynchronized in docs/fre_runs/ngxpulse_data_foundation_gaps_report.
    md Section 1) -- the quant-layer `corporate_actions` table and the
    FRE-layer `extracted_facts` bonus/rights/dividend facts. Prices in
    equity_prices are NOT adjusted for any of these (confirmed raw/
    unadjusted this session)."""
    if not tickers:
        return pd.DataFrame(columns=["ticker", "source_table", "action_type", "date", "detail"])
    ph = ",".join("?" * len(tickers))
    ca = pd.read_sql(
        f"SELECT ticker, action_type, COALESCE(declared_date, markdown_date) AS date, "
        f"ratio_new, ratio_old, dividend_per_share FROM corporate_actions WHERE ticker IN ({ph})",
        con, params=tickers)
    ca["source_table"] = "corporate_actions"
    ca["detail"] = ca.apply(
        lambda r: f"ratio {r.ratio_new}/{r.ratio_old}" if pd.notna(r.ratio_new)
        else (f"dividend {r.dividend_per_share}" if pd.notna(r.dividend_per_share) else None), axis=1)
    ca = ca[["ticker", "source_table", "action_type", "date", "detail"]]

    ef = pd.read_sql(
        f"""SELECT d.ticker AS ticker, ef.fact_type AS action_type,
               COALESCE(ef.agm_date, ef.period_end, d.filing_date) AS date, ef.description AS detail
           FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id
           WHERE d.ticker IN ({ph})
             AND ef.fact_type IN ('bonus_issue','rights_issue','dividend')""",
        con, params=tickers)
    ef["source_table"] = "extracted_facts"
    ef = ef[["ticker", "source_table", "action_type", "date", "detail"]]

    return pd.concat([ca, ef], ignore_index=True).sort_values(["ticker", "date"])


def quality_report(con: sqlite3.Connection, tickers: list[str], start: str, end: str) -> dict:
    """Composes every check above into one dict -- the single entry point
    a researcher (or a future notebook UI) should call for "what should I
    know about this ticker set/window before I trust it."""
    return {
        "tickers": sorted(tickers),
        "period": {"start": start, "end": end},
        "quality_flags": quality_flags(con, tickers, start, end).to_dict(orient="records"),
        "missing_observations": missing_observations(con, tickers, start, end).to_dict(orient="records"),
        "source_conflicts": source_conflicts(con, tickers, start, end).to_dict(orient="records"),
        "identity_notes": ticker_identity_notes(con, tickers).to_dict(orient="records"),
        "corporate_action_notes": corporate_action_notes(con, tickers).to_dict(orient="records"),
    }
