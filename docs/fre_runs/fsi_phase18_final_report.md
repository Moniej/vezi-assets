# FSI Phase 18 — Final Report

*Watchlist Persistence. Full narrative in
`docs/fre_runs/fsi_phase18_implementation_log.md`.*

## Executive summary

FSI Phase 18 built `src/ngxrot/fre/watchlist.py` and a new
`watchlist_entries` table, implementing the last of Part 9's three
Tier-1 capabilities. This closes Part 9's entire Tier-1 list: Watchlist
(this phase), Screening (Phase 14/15), Portfolio memory (Phase 17).
`entry_criteria` is required, non-empty, and schema-enforced — this
platform's own pre-registration discipline (declare success/failure
criteria in advance) applied for the first time to watchlist membership.

## Files created/modified

- `schema/schema.sql`: one new table, `watchlist_entries` (additive).
- `src/ngxrot/fre/watchlist.py` (new): `add_entry()`, `remove_entry()`,
  `get_history_for_ticker()`, `list_active()`.
- `scripts/fre/test_watchlist.py` (new, 18 assertions).
- This report, the implementation log, and the pre-registration.

**No modification to any existing table or frozen module.**

## Results

- `add_entry()` validates the ticker and the thesis-snapshot pointer
  before writing; rejects empty rationale/criteria.
- `entry_criteria` enforced `NOT NULL` at the schema level, independent
  of the Python-layer check (confirmed via a raw `INSERT` bypass attempt).
- Append-only confirmed: no `DELETE` statement anywhere (AST-verified);
  a removed entry cannot be removed twice or un-removed.
- `list_active()` is PIT-correct (an entry shows active before its own
  removal date, excluded on/after it) and holds the same guardrails as
  Screening (alphabetical order, no score/rank field, no threshold
  parameter).
- All test writes happened on a disposable scratch copy; the real
  production database's row counts and integrity are confirmed
  unchanged.
- Full regression (28 test files) and Phase 5's harness (now correctly
  reporting 30 tables) both pass.

## Design decisions disclosed

- `source_thesis_as_of_date` is a reproducible pointer (ticker + date),
  never a stored copy of thesis data — consistent with how every other
  PIT object on this platform is referenced.
- No CLI wrapper and no wiring into `company_research_dossier.py` in
  this phase — deliberately deferred, keeping this phase's own risk
  surface (the platform's first new table and first write-capable FSI
  module since Phase 3) to one dimension.

## Status: Part 9 (Portfolio Reasoning Tier 1) fully closed

Every capability Part 9 named as buildable-now (Watchlist, Screening,
Portfolio memory) is now built, tested, and frozen.

## Recommendations for the next phase

A CLI wrapper for Watchlist (mirroring Phase 15's pattern) is the
natural, low-risk next step if operational access is wanted. Beyond
that, the next architecture review should reassess the platform fresh —
Part 9 being closed removes it as a candidate category entirely.

---

**FSI Phase 18 is complete: fully implemented, validated, and
documented.**
