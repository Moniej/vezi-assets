# Incident — Production Database Wipe During FRE-2 Regression Checks (2026-08-01)

**Classification: infrastructure incident, not a research or architecture
result.** No FRE-2 research conclusion is affected by anything in this
document — this is a record of an operational mistake made during
regression testing, its recovery, and the permanent safeguard put in place
so it cannot recur. FRE-1's architecture and results
(`fre-architecture-baseline-2026-08-01`) are unaffected.

## What happened

While starting FRE-2 (before any new code was written), an extra
regression check was run against the real database as a "belt and braces"
verification following FRE-1's schema migration:
`PYTHONPATH=src python scripts/phase1_smoke_test.py`. This script,
unchanged since early in the project's life, contained:

```python
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ngx.sqlite"
DB_PATH.unlink(missing_ok=True)
con = db.init_db(DB_PATH)
```

`data/ngx.sqlite` is the literal, real production database path
(`ngxrot.db.DEFAULT_DB`). The script unconditionally deleted it and
recreated a fresh, minimally-seeded database, then inserted synthetic
PIT-trap rows. The real database — 11,533 documents, 353,043 equity-price
rows, 320 securities, every AI Intelligence Layer table populated by six
months of real work — was reduced to a ~278KB file with almost every table
at 0 rows.

## Root cause

Two scripts, both written before the production database held any real
data, hardcode the literal production path and unconditionally call
`.unlink()` on it before recreating a fresh, synthetic-only database:

1. `scripts/phase1_smoke_test.py` (the one actually run) — a Phase 1
   quant-engine smoke test verifying the PIT (point-in-time) guards, from
   before any real price/document data existed.
2. `scripts/dal_demo.py` — a Data Access Layer demonstration script, same
   vintage, same pattern, found during the root-cause sweep below (not
   itself run this session, but an equally live landmine).

Both scripts were correct and harmless when written — there was nothing to
lose. Neither was ever updated once `data/ngx.sqlite` became the shared,
irreplaceable production database. Contributing factor: `ngxrot.db
.DEFAULT_DB` was a single hardcoded constant with no environment-level
override and no structural distinction between "the real database" and "a
path a script might safely destroy" — nothing prevented a script from
targeting the production path directly instead of an isolated one, and the
one existing safe convention (`tempfile.mkdtemp()`, correctly used by
`scripts/test_reasoning_pipeline.py` and `scripts/rehearse_xs_engine.py`,
per that script's own docstring: "never data/ngx.sqlite") was not
consistently applied.

**Full repository sweep performed** (not just the one script that fired):
searched all of `scripts/` for the literal `"ngx.sqlite"` string combined
with `.unlink(`, and separately for `os.remove`/`shutil.rmtree`/`.rename(`
near any database reference. Confirmed exactly these two scripts matched
the dangerous pattern; five other files reference `ngx.sqlite` legitimately
(read-only LIM dataset export, an explicitly-synthetic-temp-DB test
docstring, and `parse_dol_exdiv_all.py`'s real, non-destructive ingestion
write) and were left unchanged.

## Impact

- **Duration**: the production database was in its wiped state from
  approximately 12:11 to 14:00 (local) on 2026-08-01.
- **Data loss: zero, permanent.** Only read-only `SELECT` queries were run
  against the database in that window (checking table counts to diagnose
  the problem) — no new legitimate data was ever written to the wiped
  database, confirmed by reviewing the exact command sequence executed in
  that window before the restore.
- **FRE-1's schema migration** (`entities.entity_type` widened,
  `causal_chain_steps.implication_layer`/`.reasoning_mode` added) was
  re-applied cleanly after recovery — no rework needed beyond re-running
  the already-tested, idempotent migration path.
- **No commit was affected.** The wipe and recovery both happened entirely
  within the local, gitignored `data/ngx.sqlite` file; nothing was ever
  staged or committed in the wiped state.

## Recovery procedure performed

1. Restored `data/ngx.sqlite` from `data/ngx.sqlite.pre_fre1_backup_20260801_120725`
   (an 84.5MB backup taken immediately before FRE-1's schema migration was
   first applied) — confirmed via full per-table row counts that this
   backup held the complete, real dataset across all 27 tables before
   restoring.
2. Re-applied the FRE-1 migration (`ngxrot.db.init_db(seed=False)`) to the
   restored database.
3. Full integrity re-verification:
   - Per-table row counts identical before/after migration, across all 27
     tables (`causal_chain_steps` 60, `documents` 11,533, `equity_prices`
     353,043, `entities` 39, `investment_implications` 18, etc.).
   - Byte-for-byte content check (not just counts) on every column of
     `entities`, `entity_relationships`, and `causal_chain_steps`'
     pre-existing columns — identical.
   - `causal_chain_steps.implication_layer`/`.reasoning_mode` present, all
     NULL (as expected, unpopulated by FRE-1 by design).
   - `entities.entity_type`'s widened CHECK (`'commodity'` present in the
     table's `sqlite_master` SQL text) confirmed present.
   - `PRAGMA foreign_key_check` clean (no dangling references).
4. Full existing regression suite re-run against the restored, re-migrated
   database: `scripts/test_reasoning_pipeline.py` — **154/154 checks
   pass** — with production row counts (`documents`=11,533) confirmed
   identical immediately before and immediately after the test run.

## Permanent mitigation (configuration isolation, not developer discipline)

Three layers, in `src/ngxrot/db.py` and `scripts/`:

1. **`DEFAULT_DB` now honors an `NGXROT_DB_PATH` environment override**
   (`Path(os.environ.get("NGXROT_DB_PATH", str(PKG_ROOT / "data" / "ngx.sqlite")))`).
   Any script relying on the default path (via `connect()`/`init_db()`
   with no explicit argument) can be redirected to a scratch location by
   **configuration** — e.g. in a CI or sandboxed test run — with zero code
   change. This does not, by itself, protect a script that hardcodes its
   own literal path instead of using `DEFAULT_DB` (both incident scripts
   did exactly that), which is why layers 2 and 3 exist.
2. **`db.new_scratch_db_path()`** — a new helper returning a fresh
   `tempfile.mkdtemp()`-based path, guaranteed never to collide with
   `DEFAULT_DB`. This is now the one sanctioned way to get "a fresh, empty
   database for a smoke test/demo/rehearsal script," replacing the
   dangerous hand-rolled `ROOT / "data" / "ngx.sqlite"` + `.unlink()`
   pattern. Both `scripts/phase1_smoke_test.py` and `scripts/dal_demo.py`
   were rewritten to use it — re-run after the fix and confirmed to (a)
   still pass their own assertions correctly, and (b) leave the real
   production database's row counts completely unchanged.
   `db.assert_not_default_db(path)` was also added as an explicit,
   reusable guard function for any future script that must destructively
   operate on a path and wants a cheap, direct check before doing so.
3. **`scripts/check_db_safety.py`** — a new, permanent, automated audit
   (no pytest on this project; matches the existing script-based
   convention) that scans every `.py` file under `scripts/` for the
   specific dangerous shape (a literal `"ngx.sqlite"` string co-occurring
   with `.unlink(` in the same file) and fails with a named list of
   violations if found. Run now: **PASS, zero violations** (the two known
   culprits are fixed; nothing else matches). This exists specifically so
   a *third* instance of this exact mistake is caught mechanically instead
   of depending on a person noticing it, or re-discovering it the same way
   this one was found (by accident, after the damage was already done).
   **Disclosed limitation**: this is a pattern/substring check, not a
   semantic analyzer — a sufficiently indirect reconstruction of the
   production path (e.g., string concatenation split across variables)
   could in principle evade it. It is a mechanical safety net layered on
   top of, not a replacement for, layers 1 and 2 above.

## Verification performed (summary)

| Check | Result |
|---|---|
| Per-table row counts, restored vs. pre-wipe backup | Identical across all 27 tables |
| Byte-for-byte content, `entities`/`entity_relationships`/`causal_chain_steps` | Identical |
| `PRAGMA foreign_key_check` | Clean |
| FRE-1 schema additions present after re-migration | Confirmed (`implication_layer`/`reasoning_mode` columns, widened `entity_type` CHECK) |
| `scripts/test_reasoning_pipeline.py` | 154/154 PASS |
| `scripts/check_db_safety.py` (new) | PASS, 0 violations |
| Fixed `scripts/phase1_smoke_test.py` re-run | Passes its own 3 PIT-trap assertions; production DB row counts unchanged before/after |
| Fixed `scripts/dal_demo.py` re-run | Runs to completion on its own scratch DB; production DB row counts unchanged before/after |
| Full repository sweep for the same dangerous pattern elsewhere | No further instances found |

## What this incident does and does not affect

- Does **not** affect FRE-1's architecture, its commit (`f6f4034`), or its
  tag (`fre-architecture-baseline-2026-08-01`) — those are unchanged and
  remain the approved baseline.
- Does **not** affect any LIM research result, the AI Intelligence Layer's
  code, the quant Data Layer, the Research Engine, or `docs/FACTOR_REGISTRY.md`
  — nothing in the recovery or the safeguard touched any of them, per the
  standing instruction for this recovery pass.
- **Does** change two pre-existing, unrelated smoke/demo scripts
  (`scripts/phase1_smoke_test.py`, `scripts/dal_demo.py`) and add three new,
  additive safety primitives to `src/ngxrot/db.py` plus one new standalone
  check script — all infrastructure changes, none of which alter any
  production behavior, schema, or research conclusion.
- FRE-2 (the Evidence Graph implementation, per the owner's approved
  redirection of the roadmap) resumes only after this document and the
  underlying recovery are reviewed, per the standing instruction that this
  incident be treated as infrastructure recovery, not a research milestone.
