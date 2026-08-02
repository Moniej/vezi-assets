"""FSI Phase 24: Sector-Coverage View (docs/fre_runs/
fsi_phase24_preregistration.md). Implements Part 9's own Tier-1
"Sector-coverage view" capability (docs/fre/09_portfolio_reasoning.md,
lines 63-67) -- the fifth and last of Part 9's five Tier-1
capabilities, genuinely buildable for the first time now that FSI
Phase 23 populated `securities.sector_ngx` for 136/320 real securities.

"An aggregation of the current watchlist/research pipeline by sector...
answers 'how balanced is our research coverage across sectors,' a
research-management question, not a portfolio-exposure question." Three
plain counts per sector -- total tickers, FSI-researched tickers,
watchlist tickers -- never a combined score, percentage, or ranking
(Part 9's own pre-rejected "shadow ranking" alternative applies equally
to a composite coverage score, so none is computed here). Tickers with
`sector_ngx IS NULL` are reported under an explicit "UNKNOWN" bucket,
always sorted last -- disclosed, never silently dropped.

Reuses `financial_ratios.list_tickers()` (Phase 3) and `watchlist.
list_active()` (Phase 18) unmodified. No new SQL beyond simple
per-sector counting. No write path anywhere.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.financial_ratios import list_tickers
from ngxrot.fre.watchlist import list_active

UNKNOWN_SECTOR = "UNKNOWN"


@dataclass(frozen=True)
class SectorCoverageRow:
    """Three plain counts -- no score/rank/weight/percentage/ratio
    field of any kind."""
    sector_ngx: str
    total_tickers: int
    fsi_covered_tickers: int
    watchlist_tickers: int


def coverage_by_sector(con: sqlite3.Connection, as_of_date: str) -> list[SectorCoverageRow]:
    """Every distinct sector_ngx value in securities (including an
    explicit UNKNOWN bucket for NULL), each with its own total-ticker,
    FSI-covered, and watchlist count as of as_of_date. Always
    alphabetical by sector_ngx, UNKNOWN forced last -- never sorted by
    any count."""
    sector_by_ticker: dict[str, str] = {}
    for ticker, sector_ngx in con.execute("SELECT ticker, sector_ngx FROM securities"):
        sector_by_ticker[ticker] = sector_ngx if sector_ngx is not None else UNKNOWN_SECTOR

    fsi_tickers = set(list_tickers(con))
    watchlist_tickers = {e.ticker for e in list_active(con, as_of_date=as_of_date)}

    totals: dict[str, int] = {}
    fsi_counts: dict[str, int] = {}
    watchlist_counts: dict[str, int] = {}
    for ticker, sector in sector_by_ticker.items():
        totals[sector] = totals.get(sector, 0) + 1
        if ticker in fsi_tickers:
            fsi_counts[sector] = fsi_counts.get(sector, 0) + 1
        if ticker in watchlist_tickers:
            watchlist_counts[sector] = watchlist_counts.get(sector, 0) + 1

    known_sectors = sorted(s for s in totals if s != UNKNOWN_SECTOR)
    ordered_sectors = known_sectors + ([UNKNOWN_SECTOR] if UNKNOWN_SECTOR in totals else [])

    return [
        SectorCoverageRow(
            sector_ngx=sector,
            total_tickers=totals[sector],
            fsi_covered_tickers=fsi_counts.get(sector, 0),
            watchlist_tickers=watchlist_counts.get(sector, 0),
        )
        for sector in ordered_sectors
    ]
