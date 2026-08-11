"""Canonical security identity / ticker-rename bridging.

Purely additive, read-only. Reuses the EXISTING `entities`/
`entity_relationships` tables (`relation_type='renamed_from'`) built by the
earlier FRE knowledge-graph work -- no new table, no new schema. Those
edges already record exactly the fact this module needs
(new_entity `renamed_from` old_entity, with an `effective_date`); this
module is the first thing that CONSUMES them for price-history purposes.

## Why this matters for price history specifically

Confirmed empirically (2026-08-10 cross-validation pass): BOTH
`ngx_pricelist_v2` (this platform's own primary reference) and NGX Pulse
store a renamed security's pre-rename and post-rename history under
completely separate ticker symbols, with a clean handoff at the rename
date -- e.g. GUARANTY's `equity_prices` rows end 2021-06-17, GTCO's begin
2021-06-24 (the entity_relationships `effective_date`). No data is
actually missing; a caller who only ever queries "GTCO" simply never sees
it. This module resolves the full symbol chain so research code can ask
for a security's COMPLETE real history without needing to already know
its rename history.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class TickerEra:
    ticker: str
    valid_from: str | None  # None = no known lower bound (earliest era)
    valid_to: str | None    # None = still current (latest era)


def resolve_ticker_history_symbols(con: sqlite3.Connection, ticker: str) -> list[TickerEra]:
    """All real ticker symbols a security has traded under, oldest first,
    reconstructed by walking `entity_relationships` `renamed_from` edges
    backward from `ticker`'s own entity. Returns `[TickerEra(ticker, None,
    None)]` (a single era, no known rename history) if the ticker has no
    entity-graph presence or no renamed_from edge -- never guessed, never
    fabricated from string similarity or any other heuristic."""
    # NOTE: `entities.ticker` is NULL for every real company entity found
    # in this database (confirmed directly) -- the real ticker string
    # lives in `entities.canonical_name` instead. Matched here, not
    # against the always-empty `ticker` column.
    row = con.execute("SELECT entity_id FROM entities WHERE canonical_name = ? AND entity_type='company'",
                       (ticker,)).fetchone()
    if row is None:
        return [TickerEra(ticker, None, None)]

    # Walk backward (newest -> oldest) collecting each rename edge's own
    # `valid_from` -- the date the NEWER symbol's era began (equivalently,
    # the date the OLDER symbol's era ended).
    symbols_newest_first = [ticker]
    rename_dates_newest_first: list[str] = []
    entity_id = row[0]
    seen = {entity_id}
    while True:
        edge = con.execute(
            "SELECT object_entity_id, valid_from FROM entity_relationships "
            "WHERE subject_entity_id = ? AND relation_type = 'renamed_from'",
            (entity_id,)).fetchone()
        if edge is None:
            break
        prior_entity_id, rename_date = edge
        if prior_entity_id in seen:  # defensive: never loop on a malformed cycle
            break
        prior = con.execute("SELECT canonical_name FROM entities WHERE entity_id = ?",
                             (prior_entity_id,)).fetchone()
        if prior is None or prior[0] is None:
            break
        rename_dates_newest_first.append(rename_date)
        symbols_newest_first.append(prior[0])
        seen.add(prior_entity_id)
        entity_id = prior_entity_id

    symbols_oldest_first = list(reversed(symbols_newest_first))
    dates_oldest_first = list(reversed(rename_dates_newest_first))  # dates_oldest_first[i] = when era i ends
    eras: list[TickerEra] = []
    for i, sym in enumerate(symbols_oldest_first):
        valid_from = dates_oldest_first[i - 1] if i > 0 else None
        valid_to = dates_oldest_first[i] if i < len(dates_oldest_first) else None
        eras.append(TickerEra(sym, valid_from, valid_to))
    return eras


def full_price_history_query(con: sqlite3.Connection, ticker: str, source_id: int) -> str:
    """Returns a ready-to-execute SQL SELECT (as a string, for the caller
    to run with their own params if desired) that unions `equity_prices`
    across every real symbol this security has ever traded under, tagging
    each row with the ORIGINAL ticker it was stored under (never silently
    relabels history) plus the CANONICAL (most-recent) ticker for grouping.
    Read-only; does not execute anything itself."""
    eras = resolve_ticker_history_symbols(con, ticker)
    symbols = [e.ticker for e in eras]
    canonical = ticker
    parts = [
        f"SELECT ticker AS original_ticker, '{canonical}' AS canonical_ticker, trade_date, "
        f"open, high, low, close, volume, source_id, confidence, as_of_date "
        f"FROM equity_prices WHERE source_id = {int(source_id)} AND ticker = '{sym}'"
        for sym in symbols
    ]
    return " UNION ALL ".join(parts) + " ORDER BY trade_date"
