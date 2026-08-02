# FSI Phase 18 — Implementation Log

*Per `docs/fre_runs/fsi_phase18_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Schema addition and migration

Added `watchlist_entries` to `schema/schema.sql` (one new table,
`CREATE TABLE IF NOT EXISTS`, zero modification to any existing table).
Applied to the real production database via the established `db.
init_db(db.DEFAULT_DB, seed=False)` mechanism (the same mechanism that
originally materialized Phase 3's `financial_reasoning_conclusions`
table), with an automatic pre-write backup
(`ngx.sqlite.pre_fsi_phase18_schema_backup_2026-08-02`). Confirmed after:
`integrity_check` ok, all pre-existing tables' row counts unchanged
(`extracted_facts` 298, `documents` 11533, `financial_reasoning_
conclusions` 267), `foreign_key_check` clean.

## Entry 1 — `src/ngxrot/fre/watchlist.py`

`add_entry()`, `remove_entry()`, `get_history_for_ticker()`,
`list_active()`. `add_entry()` validates the ticker exists in
`securities` and that `source_thesis_as_of_date` resolves via `company_
thesis_360.as_of()` (raises if not, rather than silently accepting an
unresolvable pointer) before writing. `rationale`/`entry_criteria` are
required non-empty at the Python layer AND `entry_criteria` is enforced
`NOT NULL` at the schema layer — confirmed both hold independently (a
raw `INSERT` bypassing `add_entry()` entirely still fails the schema
constraint).

## Entry 2 — Append-only enforced, not just documented

`remove_entry()` only ever `UPDATE`s `removed_at`/`removal_reason` — no
`DELETE` statement exists anywhere in the module (confirmed via AST
inspection of every string literal, not a substring match). A
double-removal attempt, or removal of a nonexistent entry, both raise —
an entry, once removed, is permanently closed; the row itself is never
deleted, so `get_history_for_ticker()` always shows the complete history.

## Entry 3 — `list_active()` guardrails, same discipline as Screening

Alphabetical-ticker order (mechanically checked against Python's own
`sorted()`); no `limit`/`sort_by`/`rank_by`/`weight`/`threshold`
parameter; `WatchlistEntryRecord` carries no score/rank/weight field.
PIT correctness verified directly: a real entry added then removed shows
as active on a date BEFORE its own removal date, and correctly excluded
on/after it.

## Entry 4 — Validation and full regression (complete)

`scripts/fre/test_watchlist.py` (18/18): all writes happen only on a
disposable scratch copy of the real database (`db.new_scratch_db_path()`
+ `shutil.copy`, the same pattern `test_restatement_detection.py` already
established) — the real production database's row counts and
`integrity_check` are confirmed unchanged at the end, proving this test
never wrote to `data/ngx.sqlite` despite exercising a genuinely
write-capable module for the first time since Phase 3.

Full regression: 28 test files (was 27), all green. `check_db_safety.py`
PASS. `test_reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5 harness:
all 4 components PASS — Component 3 now correctly reports 30 tables
(was 29, the new `watchlist_entries` table included), still unchanged
before/after.

**No modification to any existing table or frozen module.**

**FSI Phase 18 is now complete, validated, and documented.** This closes
Part 9's Tier-1 capability list in full (Watchlist, Screening, Portfolio
memory all built).
