"""FSI Phase 21: Watchlist CLI (docs/fre_runs/fsi_phase21_preregistration.md).

A thin command-line wrapper around Phase 18's `add_entry()`/
`remove_entry()`/`list_active()`/`get_history_for_ticker()`, each
called unmodified. No new validation logic -- every `ValueError` these
functions already raise is caught once, at the top level, and printed
to stderr with exit code 1, never a raw traceback.

**The first standing operator tool on this platform that can write to
the real production database** -- `add`/`remove` open it read-write
(`list`/`history` remain read-only). This is judged acceptable because
every write still routes through Phase 18's own already-tested,
already-validated, append-only functions; see the pre-registration's
"A new risk category, disclosed up front" section for the full
reasoning. No new write logic is introduced by this script.

  PYTHONPATH=src python scripts/fre/manage_watchlist.py add --ticker NASCON \
      --rationale "..." --source-thesis-as-of 2026-06-29 --entry-criteria "..."
  PYTHONPATH=src python scripts/fre/manage_watchlist.py remove --watchlist-entry-id 1 \
      --removed-at 2026-08-03 --removal-reason "..."
  PYTHONPATH=src python scripts/fre/manage_watchlist.py list --as-of 2026-08-02
  PYTHONPATH=src python scripts/fre/manage_watchlist.py history --ticker NASCON
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.watchlist import (  # noqa: E402
    add_entry, get_history_for_ticker, list_active, remove_entry,
)


def _check_date(label: str, value: str | None) -> str | None:
    """Matches Phase 12/15's own established convention: a malformed date
    is rejected with a clear, custom stderr message and exit code 1 --
    NOT argparse's own generic type-conversion error."""
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        print(f"ERROR: {label} {value!r} is not a valid date (expected YYYY-MM-DD).", file=sys.stderr)
        sys.exit(1)
    return value


def _print_entries(entries) -> None:
    if not entries:
        print("No entries.")
        return
    for e in entries:
        status = f"removed on {e.removed_at} ({e.removal_reason})" if e.removed_at else "active"
        print(f"[{e.watchlist_entry_id}] {e.ticker} -- added {e.added_at} -- {status}")
        print(f"    rationale: {e.rationale}")
        print(f"    entry_criteria: {e.entry_criteria}")
        print(f"    source_thesis_as_of_date: {e.source_thesis_as_of_date}")
        print(f"    review_cadence: {e.review_cadence or '(none stated)'}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Add, remove, or list Part 9 Tier-1 watchlist entries. "
                    "add/remove write to the production database via Phase 18's "
                    "own already-validated, append-only add_entry()/remove_entry() "
                    "-- no new write logic is introduced by this script."
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    add_parser = sub.add_parser("add", help="Add a new watchlist entry")
    add_parser.add_argument("--ticker", required=True)
    add_parser.add_argument("--rationale", required=True)
    add_parser.add_argument("--source-thesis-as-of", required=True, dest="source_thesis_as_of_date")
    add_parser.add_argument("--entry-criteria", required=True, dest="entry_criteria")
    add_parser.add_argument("--review-cadence", default=None, dest="review_cadence")
    add_parser.add_argument("--added-at", default=None, dest="added_at")

    remove_parser = sub.add_parser("remove", help="Mark an existing watchlist entry removed")
    remove_parser.add_argument("--watchlist-entry-id", required=True, type=int, dest="watchlist_entry_id")
    remove_parser.add_argument("--removed-at", required=True, dest="removed_at")
    remove_parser.add_argument("--removal-reason", required=True, dest="removal_reason")

    list_parser = sub.add_parser("list", help="List all currently-active watchlist entries")
    list_parser.add_argument("--as-of", default=None, dest="as_of_date")

    history_parser = sub.add_parser("history", help="Full watchlist history for one ticker")
    history_parser.add_argument("--ticker", required=True)

    args = parser.parse_args()

    if args.mode == "add":
        _check_date("--source-thesis-as-of", args.source_thesis_as_of_date)
        _check_date("--added-at", args.added_at)
    elif args.mode == "remove":
        _check_date("--removed-at", args.removed_at)
    elif args.mode == "list":
        _check_date("--as-of", args.as_of_date)

    try:
        if args.mode == "add":
            con = db.connect(db.DEFAULT_DB)
            entry_id = add_entry(
                con, args.ticker, rationale=args.rationale,
                source_thesis_as_of_date=args.source_thesis_as_of_date,
                entry_criteria=args.entry_criteria,
                review_cadence=args.review_cadence, added_at=args.added_at,
            )
            con.commit()
            con.close()
            print(f"Added watchlist_entry_id={entry_id} for {args.ticker}.")
        elif args.mode == "remove":
            con = db.connect(db.DEFAULT_DB)
            remove_entry(con, args.watchlist_entry_id, removed_at=args.removed_at,
                         removal_reason=args.removal_reason)
            con.commit()
            con.close()
            print(f"Removed watchlist_entry_id={args.watchlist_entry_id}.")
        elif args.mode == "list":
            con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
            entries = list_active(con, as_of_date=args.as_of_date)
            con.close()
            _print_entries(entries)
        else:
            con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
            entries = get_history_for_ticker(con, args.ticker)
            con.close()
            _print_entries(entries)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
