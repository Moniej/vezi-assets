# FSI Phase 21 — Pre-registration

*Watchlist CLI. Per the owner's standing continuous-execution
authorization: gap identified, alternatives considered, implemented
without an approval checkpoint.*

## Gap identified

`watchlist.py` (Phase 18) has been a fully built, fully tested,
append-only, schema-backed, write-capable module for two phases now —
but it has **zero operator-facing entry point**. Every other
capability on this platform that produces something a researcher would
actually use has a thin CLI wrapper one phase after its own build
(Screening → Phase 14 then Phase 15's `screen_companies.py`; the
research dossier → Phase 11 then Phase 12's `generate_research_
dossier.py`). Watchlist is the one exception: an operator today cannot
add, remove, or list a watchlist entry without writing raw Python
against `sqlite3.Connection` directly. Phase 18's own final report
named this explicitly ("A CLI wrapper for Watchlist... is the natural,
low-risk next step"), and Phase 20's final report reconfirmed it as a
live candidate. This phase closes it.

## A new risk category, disclosed up front

Every CLI script built on this platform so far — `screen_companies.py`
(Phase 15), `generate_research_dossier.py` (Phase 12) — opens the
production database `mode=ro` (read-only) and can structurally never
write to it (confirmed again this phase by grepping every script under
`scripts/` for `mode=rw`: none exists). This phase's CLI is the
**first standing operator tool on this platform that can write to the
real production database** (as opposed to a one-time data-loading
script like `fsi_extract_phase13.py`, which is run once and retired).

This is judged acceptable, not a boundary violation, for four reasons:
(1) it exposes no new write logic — every write still routes through
`watchlist.add_entry()`/`remove_entry()`, already built and tested in
Phase 18, unmodified; (2) those functions are already append-only and
validated (unknown ticker, empty rationale/criteria, unresolvable
thesis pointer, double-removal all raise before any write); (3) a
mistaken entry is correctable via `remove_entry()` with a stated
reason, never silently lost — the full history remains reconstructible
via `get_history_for_ticker()`; (4) it is scoped to exactly one
table (`watchlist_entries`), the one table on this platform explicitly
designed for external curation input. All of this phase's own testing
against real data uses read-only commands (`list`/`history`) or a
disposable scratch copy for `add`/`remove` — the same discipline every
prior write-capable test on this platform has followed; this phase's
own test file never invokes a write subcommand against the real
production database.

## Why this is the single highest-leverage gap right now

- It is a named, twice-recommended gap (Phase 18's own final report,
  reconfirmed by Phase 20's), not a newly-invented idea.
- It converts an already-built, already-tested capability from
  "reachable only via Python" to "actually operable," which is a
  bigger jump in real usability than any other currently-buildable
  candidate (Sector-coverage view is blocked; the evaluation framework
  is blocked; coverage expansion is data-entry labor, not new
  capability).
- It requires zero new library logic — a pure argparse wrapper over
  four already-frozen functions (`add_entry`, `remove_entry`,
  `list_active`, `get_history_for_ticker`), mirroring Phase 15's own
  CLI-wrapper pattern exactly.

## Alternatives considered and rejected

1. **A CLI wrapper for `company_portfolio_context.py` (Phase 20)
   instead** — mirroring Phase 12's pattern for the annotated dossier.
   Real and valuable, but lower leverage: `generate_research_
   dossier.py` already exists and gives an operator most of the same
   information today; Watchlist has literally no CLI at all. Recorded
   as a live candidate for a near-future phase, not rejected outright.
2. **Building `add`/`remove` write access into the SAME script as
   Phase 20's read-only rendering CLI**, rather than a dedicated
   script. Rejected — conflating a read-only rendering tool with the
   platform's first write-capable operator tool would blur exactly the
   boundary this pre-registration is at pains to disclose. A dedicated
   `manage_watchlist.py`, named for what it does, keeps the one new
   risk category contained to one clearly-labeled file.
3. **Adding a confirmation prompt / `--yes` flag before any write**,
   modeled on typical destructive-CLI conventions. Rejected as
   unnecessary complexity — nothing `add_entry()`/`remove_entry()` does
   is destructive (append-only; a mistaken add is corrected via a
   removal with a stated, audited reason, never erased) — the existing
   module's own validation (raises before writing on any invalid
   input) is already the correct safety boundary. Adding a second,
   redundant confirmation layer would not be following an existing
   pattern on this platform, and none of the other library functions
   this platform has ever CLI-wrapped use one either.
4. **Coverage expansion round 2** — reconsidered again this phase,
   still rejected for the same reason as Phase 19/20's own review: not
   a new capability, belongs in the eventual final audit's optional-
   enhancements list, not a numbered phase.

## Design

- New script `scripts/fre/manage_watchlist.py`, argparse subcommands,
  mirroring Phase 15's `screen_companies.py` pattern exactly (UTF-8
  stdout/stderr, `choices=`/date validation, clear errors instead of
  raw tracebacks):
  - `add --ticker --rationale --source-thesis-as-of --entry-criteria
    [--review-cadence] [--added-at]` — opens the database read-write,
    calls `add_entry()` unmodified, prints the new
    `watchlist_entry_id` on success or the raised `ValueError`'s
    message on failure (never a raw traceback).
  - `remove --watchlist-entry-id --removed-at --removal-reason` —
    calls `remove_entry()` unmodified.
  - `list [--as-of]` — read-only, calls `list_active()` unmodified.
  - `history --ticker` — read-only, calls `get_history_for_ticker()`
    unmodified.
- `add`/`remove` open the connection via `db.connect(db.DEFAULT_DB)`
  (read-write, the standard library connector already used
  everywhere `watchlist.py`'s own functions expect a writable
  connection) and call `con.commit()` explicitly after a successful
  write — SQLite's default `isolation_level` would otherwise hold the
  transaction open. `list`/`history` open `mode=ro`, matching every
  prior read-only CLI on this platform.
- No new validation logic duplicated from `watchlist.py` — every
  `ValueError` `watchlist.py` already raises is caught once, at the
  top level, and printed to `stderr` with exit code 1, exactly
  `generate_research_dossier.py`'s own established error-handling
  pattern for an unknown ticker.

## Guardrails (mechanically verified, not just asserted)

- The test file invokes `add`/`remove` ONLY against a disposable
  scratch copy of the database (via a temporary `NGXROT_DB_PATH`
  environment override, the same mechanism `db.py`'s own
  `DEFAULT_DB` docstring names as sanctioned), and `list`/`history`
  against both the scratch copy and the real database read-only —
  the real production database's row counts are confirmed unchanged
  by this phase's own test run.
- Confirmed no `choices=`/argument on `list` accepts a `--limit`/
  `--sort-by`/`--rank-by` flag.
- Confirmed `watchlist.py` itself is byte-for-byte unchanged
  (`git diff --stat`) after this phase.

## Expected outcome

A new, additive operator tool; no schema change; no modification to
`watchlist.py` or any other frozen module. This closes the one
remaining operational gap in Part 9's now-fully-built Tier 1
capability set.
