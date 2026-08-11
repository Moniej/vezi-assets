"""Decision Intelligence Phase 11: Market-Wide Intelligence.

Composes existing, real, first-party NGX market data
(`indices`/`index_levels`, per the task's own explicit instruction to
reuse this rather than invent a new source layer) with the new Phase 1/2/9
modules, aggregated across the genuine fact-bearing universe
(`genuine_fact_universe.list_genuine_financial_statement_tickers()`).

Deliberately bounded scope, disclosed honestly (see
`docs/fre_runs/decision_intelligence_build_report.md`): sector momentum,
FSI coverage by sector, capital-raising activity, regulatory-theme
clustering, and improving/deteriorating companies are built and tested.
Concentration-risk and cross-ticker correlation analysis are NOT built in
this pass -- `correlation_notes.py`'s own real data (0 macro-exposure
edges today) would make any such output vacuous, and a genuine
concentration-risk metric needs real portfolio holdings this platform's
Portfolio Construction module does not yet have (same Tier-2 gate as
Section 6 of the baseline audit).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.economic_peer_taxonomy import classify_ticker
from ngxrot.fre.genuine_fact_universe import list_genuine_financial_statement_tickers
from ngxrot.fre.scorecard import build_scorecard


@dataclass
class SectorMomentum:
    index_code: str
    index_name: str
    start_date: str
    end_date: str
    start_close: float | None
    end_close: float | None
    pct_change: float | None  # None if either close is unavailable -- never fabricated


@dataclass
class MarketIntelligence:
    as_of_date: str
    prior_date: str
    sector_momentum: list[SectorMomentum]
    fsi_coverage_by_sector: list  # sector_coverage.SectorCoverageRow, verbatim, unmodified
    capital_raising_events: list[dict]
    regulatory_theme_counts: dict[str, int]
    improving_companies: list[str]
    deteriorating_companies: list[str]
    companies_assessed: int
    companies_skipped: list[str]  # tickers where scorecard build raised, named honestly


def _index_close(con: sqlite3.Connection, index_code: str, on_or_before: str) -> float | None:
    row = con.execute(
        "SELECT close_value FROM index_levels WHERE index_code = ? AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT 1", (index_code, on_or_before),
    ).fetchone()
    return row[0] if row else None


def sector_momentum(con: sqlite3.Connection, as_of_date: str, prior_date: str) -> list[SectorMomentum]:
    rows = con.execute("SELECT index_code, name FROM indices ORDER BY index_code").fetchall()
    out = []
    for code, name in rows:
        start = _index_close(con, code, prior_date)
        end = _index_close(con, code, as_of_date)
        pct = (end - start) / start if (start and end and start != 0) else None
        out.append(SectorMomentum(code, name, prior_date, as_of_date, start, end, pct))
    return out


def capital_raising_events(con: sqlite3.Connection, as_of_date: str, prior_date: str) -> list[dict]:
    rows = con.execute(
        "SELECT event_id, ticker, event_type, announced_date, headline FROM events "
        "WHERE category = 'corporate' AND event_type IN "
        "('capital_raise','rights_issue','debt_issuance','bonus_issue') "
        "AND announced_date > ? AND announced_date <= ? ORDER BY announced_date",
        (prior_date, as_of_date),
    ).fetchall()
    return [dict(event_id=r[0], ticker=r[1], event_type=r[2], announced_date=r[3], headline=r[4])
            for r in rows]


def regulatory_theme_counts(con: sqlite3.Connection, as_of_date: str, prior_date: str) -> dict[str, int]:
    rows = con.execute(
        "SELECT event_type, COUNT(*) FROM events WHERE category IN "
        "('banking','monetary','market_structure','insurance','commodity','macro') "
        "AND announced_date > ? AND announced_date <= ? GROUP BY event_type ORDER BY 2 DESC",
        (prior_date, as_of_date),
    ).fetchall()
    return {event_type: count for event_type, count in rows}


def build_market_intelligence(con: sqlite3.Connection, as_of_date: str, prior_date: str,
                               intelligence_cache: dict | None = None) -> MarketIntelligence:
    from ngxrot.fre.sector_coverage import coverage_by_sector

    tickers = list_genuine_financial_statement_tickers(con)
    improving, deteriorating, skipped = [], [], []
    for t in tickers:
        try:
            sc = build_scorecard(con, t, as_of_date, prior_date, intelligence_cache=intelligence_cache)
        except Exception:
            skipped.append(t)
            continue
        if sc.fundamental_signal == "IMPROVING":
            improving.append(t)
        elif sc.fundamental_signal == "DETERIORATING":
            deteriorating.append(t)

    return MarketIntelligence(
        as_of_date=as_of_date, prior_date=prior_date,
        sector_momentum=sector_momentum(con, as_of_date, prior_date),
        fsi_coverage_by_sector=coverage_by_sector(con, as_of_date),
        capital_raising_events=capital_raising_events(con, as_of_date, prior_date),
        regulatory_theme_counts=regulatory_theme_counts(con, as_of_date, prior_date),
        improving_companies=improving, deteriorating_companies=deteriorating,
        companies_assessed=len(tickers) - len(skipped), companies_skipped=skipped,
    )
