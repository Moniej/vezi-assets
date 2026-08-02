# FSI Phase 21 — Final Report

*Watchlist CLI. Full narrative in
`docs/fre_runs/fsi_phase21_implementation_log.md`.*

## Executive summary

FSI Phase 21 built `scripts/fre/manage_watchlist.py`, a thin
command-line wrapper around Phase 18's `add_entry()`/`remove_entry()`/
`list_active()`/`get_history_for_ticker()`. This is the first standing
operator tool on this platform capable of writing to the real
production database — every prior CLI (`screen_companies.py`,
`generate_research_dossier.py`) is read-only by construction. The new
risk category is disclosed in full in the pre-registration and
mitigated structurally: no new write logic exists anywhere in this
script, every write still routes through Phase 18's own already-
tested, append-only, validated functions.

## Files created/modified

- `scripts/fre/manage_watchlist.py` (new): `add`/`remove`/`list`/
  `history` subcommands.
- `scripts/fre/test_manage_watchlist.py` (new, 13 assertions).
- This report, the implementation log, and the pre-registration.

**No modification to `watchlist.py` or any other frozen module, and no
schema change.**

## Results

- `add`/`remove` correctly commit to a real (scratch, in testing)
  database; a raised `ValueError` (unknown ticker, malformed date,
  double-removal) surfaces as a clear stderr message with exit code 1,
  never a raw traceback.
- `list`/`history` output verified to match calling `list_active()`/
  `get_history_for_ticker()` directly, both against a scratch copy and
  against the real production database (read-only).
- Every `add`/`remove` invocation in this phase's own test file
  targets a disposable scratch copy via an `NGXROT_DB_PATH` override —
  the real production database was never written to during
  development or testing of this phase; confirmed unchanged via
  `snapshot_all_table_counts()`/`diff_table_counts()`.
- Full regression (31 test files, up from 30), `check_db_safety.py`,
  `test_reasoning_pipeline.py`, and Phase 5's harness (4 components,
  30 tables) all pass.

## Design decisions disclosed

- No confirmation prompt or `--yes` flag before a write — judged
  unnecessary since `add_entry()`/`remove_entry()` are already
  append-only and self-validating (raise before writing on any invalid
  input); a mistaken entry is corrected via a removal with a stated,
  audited reason, never erased. No other CLI on this platform uses
  such a prompt either.
- Malformed dates are rejected with a custom stderr message (matching
  Phase 12/15's convention) rather than argparse's own generic `type=`
  conversion error — a design choice corrected during implementation
  (see implementation log Entry 1) after the first draft used
  argparse's own type-conversion path.

## Status: Part 9 (Portfolio Reasoning Tier 1) — fully built and now fully operable

Watchlist, Screening, Portfolio memory, and Qualitative correlation
notes are all built, tested, frozen, AND now reachable from the
command line (Screening: Phase 15; this phase: Watchlist). Only
Sector-coverage view remains, genuinely blocked on `securities.
sector_ngx` population — an external data dependency.

## Recommendations for the next phase

Per the owner's standing continuous-execution authorization: a CLI
wrapper for Phase 20's `company_portfolio_context.py` (mirroring Phase
12's pattern) remains a live, low-risk candidate. With Part 9
substantially exhausted (built, wired, and now operable, modulo one
external blocker), the next architecture review should reassess the
platform fresh rather than continue mining Part 9 specifically.

---

**FSI Phase 21 is complete: fully implemented, validated, and
documented.**
