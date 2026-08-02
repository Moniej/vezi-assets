# FSI Phase 21 — Implementation Log

*Per `docs/fre_runs/fsi_phase21_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Confirmed no prior CLI on this platform can write, before designing

Grepped every script under `scripts/` for `mode=rw`: none exists.
Every prior CLI (`screen_companies.py`, `generate_research_
dossier.py`) opens `mode=ro`. This confirmed, rather than assumed, that
this phase's `add`/`remove` subcommands are the first standing
operator-facing write path to the real production database on this
platform — the risk category disclosed in the pre-registration.

## Entry 1 — `scripts/fre/manage_watchlist.py`

Four subcommands (`add`, `remove`, `list`, `history`), each a thin
wrapper around one of Phase 18's own functions, called unmodified.
`add`/`remove` open the database via `db.connect(db.DEFAULT_DB)`
(read-write) and call `con.commit()` explicitly after a successful
write; `list`/`history` open `mode=ro`, matching every prior read-only
CLI. Malformed dates are rejected with a custom stderr message and
exit code 1 (`_check_date()`), matching Phase 12/15's own established
convention exactly — NOT argparse's own generic `type=` conversion
error, which was the first draft's approach until this was corrected
to match precedent.

## Entry 2 — Test discipline: every write-path invocation targets a scratch copy

`test_manage_watchlist.py` sets `NGXROT_DB_PATH` (the sanctioned
override `db.py`'s own `DEFAULT_DB` docstring names) to a disposable
scratch copy for every `add`/`remove` subprocess invocation — this
test never once invokes a write subcommand against the real production
database. `list`/`history` are additionally exercised once, read-only,
directly against the real database, and compared for exact equivalence
against calling `list_active()`/`get_history_for_ticker()` directly.

## Entry 3 — Bug found and fixed during this phase's own test-writing (not a pre-existing defect)

The first test assertion for double-removal expected the substring
"already been removed", but `watchlist.remove_entry()`'s actual raised
message (Phase 18, frozen, correct) reads "was already removed on
{date}". This was the test's own wording mismatch, not a defect in
`watchlist.py` — fixed by correcting the test's expected substring to
"already removed", the actual message's own wording.

## Entry 4 — Full regression and validation (complete)

`scripts/fre/test_manage_watchlist.py` (new, 13/13 after the Entry 3
fix). Full regression: 31 test files (was 30), all green. `check_db_
safety.py` PASS (confirms this new script neither hardcodes a literal
database path nor calls a destructive unlink). `test_reasoning_
pipeline.py` ALL CHECKS PASSED. Phase 5 harness: all 4 components
PASS — 30 tables, unchanged before/after.

**No modification to `watchlist.py` or any other frozen module** —
this phase adds a script, not a library change. No schema change.

**FSI Phase 21 is now complete, validated, and documented.** This
closes the one remaining operational gap in Part 9's Tier 1 capability
set: every Tier-1 capability (Watchlist, Screening, Portfolio memory,
Qualitative correlation notes) is now both built AND operator-
reachable, except Sector-coverage view, which remains genuinely
blocked on `securities.sector_ngx` population.
