"""FSI Phase 18: Watchlist Persistence (docs/fre_runs/
fsi_phase18_preregistration.md). Implements Part 9's own Tier-1
"Watchlist" capability (docs/fre/09_portfolio_reasoning.md) -- the last
of its three Tier-1 items to be built (Screening: Phase 14/15; Portfolio
memory: Phase 17).

Append-only: `remove_entry()` sets `removed_at`/`removal_reason` on an
existing row -- there is no DELETE anywhere in this module, and a
removed entry can never be removed again or "un-removed." The full
history of what was ever watchlisted, and why, is always
reconstructible via `get_history_for_ticker()`.

`entry_criteria` is required (schema-level NOT NULL) per Part 9's own
explicit design: "what would need to be true for this to become
portfolio-relevant" is written down BEFORE it is met, not rationalized
after -- this platform's own pre-registration discipline, applied here
to watchlist membership.

`source_thesis_as_of_date` is a reproducible POINTER (this ticker + this
date), never a stored copy of `CompanyThesis360`'s own data --
`add_entry()` validates the pointer is real by calling `company_thesis_
360.as_of()` and requiring it not to raise (NOT requiring non-empty
evidence -- a company can legitimately be watchlisted before much
evidence exists).

`list_active()` is the one function in this module that legitimately
spans multiple tickers -- same guardrails as `screening.py`: results
always in alphabetical-ticker order, no score/rank/weight field, no
numeric-threshold parameter. It answers "what is currently on the
watchlist," never "which entry is most important."
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from ngxrot.fre.company_thesis_360 import as_of as _thesis_as_of


@dataclass(frozen=True)
class WatchlistEntryRecord:
    """No score/rank/weight field -- a curated, evidence-linked note,
    never a ranked position."""
    watchlist_entry_id: int
    ticker: str
    added_at: str
    rationale: str
    source_thesis_as_of_date: str
    review_cadence: str | None
    entry_criteria: str
    removed_at: str | None
    removal_reason: str | None


def _row_to_record(row: tuple) -> WatchlistEntryRecord:
    return WatchlistEntryRecord(
        watchlist_entry_id=row[0], ticker=row[1], added_at=row[2], rationale=row[3],
        source_thesis_as_of_date=row[4], review_cadence=row[5], entry_criteria=row[6],
        removed_at=row[7], removal_reason=row[8],
    )


def add_entry(
    con: sqlite3.Connection, ticker: str, rationale: str, source_thesis_as_of_date: str,
    entry_criteria: str, review_cadence: str | None = None, added_at: str | None = None,
) -> int:
    """Single-ticker only. Validates `ticker` exists in `securities` and
    that `source_thesis_as_of_date` is a real, resolvable point-in-time
    pointer (company_thesis_360.as_of() must not raise) before writing.
    `rationale` and `entry_criteria` must be non-empty -- a watchlist
    entry with no stated criteria is exactly the "rationalized after the
    fact" pattern this design explicitly rejects."""
    if not rationale.strip():
        raise ValueError("rationale must be non-empty")
    if not entry_criteria.strip():
        raise ValueError("entry_criteria must be non-empty -- state it in advance, per Part 9's own design")

    exists = con.execute("SELECT 1 FROM securities WHERE ticker = ?", (ticker,)).fetchone()
    if exists is None:
        raise ValueError(f"unknown ticker {ticker!r} -- no matching row in securities")

    _thesis_as_of(con, ticker, source_thesis_as_of_date)  # raises if the pointer cannot be resolved

    added_at = added_at or datetime.now(timezone.utc).date().isoformat()
    cur = con.execute(
        "INSERT INTO watchlist_entries (ticker, added_at, rationale, source_thesis_as_of_date, "
        "review_cadence, entry_criteria, removed_at, removal_reason) VALUES (?,?,?,?,?,?,NULL,NULL)",
        (ticker, added_at, rationale, source_thesis_as_of_date, review_cadence, entry_criteria),
    )
    return cur.lastrowid


def remove_entry(con: sqlite3.Connection, watchlist_entry_id: int, removed_at: str, removal_reason: str) -> None:
    """Marks an entry removed -- never a DELETE. Raises if the entry
    does not exist or has already been removed (a removed entry cannot
    be removed again or 'un-removed')."""
    if not removal_reason.strip():
        raise ValueError("removal_reason must be non-empty")
    row = con.execute(
        "SELECT removed_at FROM watchlist_entries WHERE watchlist_entry_id = ?", (watchlist_entry_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"no watchlist entry with id {watchlist_entry_id}")
    if row[0] is not None:
        raise ValueError(f"watchlist entry {watchlist_entry_id} was already removed on {row[0]}")
    con.execute(
        "UPDATE watchlist_entries SET removed_at = ?, removal_reason = ? WHERE watchlist_entry_id = ?",
        (removed_at, removal_reason, watchlist_entry_id),
    )


def get_history_for_ticker(con: sqlite3.Connection, ticker: str) -> list[WatchlistEntryRecord]:
    """Single-ticker only. Every entry (active or removed) ever recorded
    for this ticker, chronological by added_at."""
    rows = con.execute(
        "SELECT watchlist_entry_id, ticker, added_at, rationale, source_thesis_as_of_date, "
        "review_cadence, entry_criteria, removed_at, removal_reason FROM watchlist_entries "
        "WHERE ticker = ? ORDER BY added_at, watchlist_entry_id", (ticker,),
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def list_active(con: sqlite3.Connection, as_of_date: str | None = None) -> list[WatchlistEntryRecord]:
    """Every entry active as of `as_of_date` (default: today, UTC) --
    added on or before that date, and not yet removed as of that date.
    Always returned in alphabetical-ticker order (never sorted by any
    value) -- descriptive filtering, never a ranking."""
    as_of_date = as_of_date or datetime.now(timezone.utc).date().isoformat()
    rows = con.execute(
        "SELECT watchlist_entry_id, ticker, added_at, rationale, source_thesis_as_of_date, "
        "review_cadence, entry_criteria, removed_at, removal_reason FROM watchlist_entries "
        "WHERE added_at <= ? AND (removed_at IS NULL OR removed_at > ?) "
        "ORDER BY ticker, watchlist_entry_id", (as_of_date, as_of_date),
    ).fetchall()
    return [_row_to_record(r) for r in rows]
