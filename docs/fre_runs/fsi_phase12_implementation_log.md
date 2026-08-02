# FSI Phase 12 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase12_preregistration.md`
(approved) and the owner's implementation instruction. Append-only.*

## Entry 0 — Design decision before coding: light ticker-existence validation

`build_dossier()` (Phase 11) does not error on an unknown ticker — it
returns a near-empty, correctly-honest dossier (empty corporate/
financial/thesis/graph data), matching this platform's own established
"unknown stays unknown, never fabricate" discipline. Left entirely as
is, a CLI user who mistypes a ticker would see a mostly-blank report
with no clear signal that anything went wrong, rather than the "clear,
honest error message" the pre-registration's own success criteria
requires. Resolved by adding ONE light, disclosed existence check in
the script itself (not in any frozen module): before calling `build_
dossier()`, confirm the ticker exists in `securities` — a simple
existence check, not a new reasoning capability, mirroring the same
class of integrity check already used everywhere else on this platform
(e.g. `entities.ticker REFERENCES securities(ticker)`). An unknown
ticker now produces a clear, immediate CLI error instead of a
confusing, silently-near-empty report.

## Entry 1 — A real bug found and fixed during test development: console encoding

Running the CLI as a real subprocess (matching how an actual user would
invoke it, not just calling the underlying Python functions directly)
surfaced a real, genuine bug for BUAFOODS specifically: a
`UnicodeEncodeError` on the `charmap` codec. BUAFOODS's real filing
text (the Stage 4 EBITDA narrative, extracted in FSI Phase 2) contains
the literal Naira currency sign (U+20A6), and a subprocess launched
under Windows' default console codepage (`cp1252`) cannot `print()` it
-- `cp1252` has no mapping for that character. This is a real,
disclosed finding: eleven prior phases' own tests all called
`render_report()`/`render_dossier()` directly in-process (inheriting
whatever encoding the test harness itself already used) and never
exercised a genuine subprocess/console boundary, so this exact failure
mode had never been triggered before Phase 12 built the platform's
first real CLI entry point.

Fixed by forcing UTF-8 on `sys.stdout`/`sys.stderr` at the top of
`main()` via `reconfigure(encoding="utf-8")`, regardless of the calling
environment's own console codepage -- the correct, general fix for a
script that may be invoked from any terminal, not a workaround specific
to BUAFOODS's own data.

## Entry 2 — A second real bug found while building the test suite: mojibake in the test's own subprocess capture

Fixing Entry 1 (forcing UTF-8 on the child process) surfaced a SECOND
real bug, this time in the test harness itself, not the script: the
em-dash and `±` characters arrived at the test as mojibake
(`â€”` in place of `—`) even though the child process's own bytes were
correct UTF-8. Root cause: `subprocess.run(..., text=True)` with no
explicit `encoding=` argument decodes the child's stdout bytes using
`locale.getpreferredencoding()` (`cp1252` on this Windows environment)
-- a real mismatch between what the child writes (UTF-8, after Entry
1's fix) and what the parent assumes it wrote (the OS locale default).
Confirmed precisely via a byte-level `diff` between the direct
in-process render and the subprocess-captured output, isolating the
exact corrupted characters rather than guessing. Fixed by passing
`encoding="utf-8"` explicitly to `subprocess.run()` in the test's own
`run_cli()` helper, matching the encoding the script itself now
guarantees. Both this and Entry 1 are disclosed as real, genuine
findings from testing a real subprocess/console boundary for the first
time in this program -- every one of the prior eleven phases' own
tests called rendering functions directly in-process and never
exercised this boundary, so neither failure mode could have been found
earlier.

## Entry 3 — Validation and full regression (complete)

`scripts/fre/test_generate_research_dossier.py` (9/9): the CLI's own
stdout output is byte-identical to calling `build_dossier()`/`render_
dossier()` directly, for all 5 real tickers, via a real subprocess
invocation (not an in-process function call); `--output` writes a file
byte-identical to the direct render while stdout still shows the same
content; running without `--output` creates no file anywhere; an
unknown ticker and a malformed date each produce a clear, honest error
(exit code 1, no traceback, no fabricated report); a missing required
argument produces argparse's own clear usage error; the entire test
run (including every real CLI subprocess invocation) leaves all 29
tables' row counts, `integrity_check`, and `foreign_key_check`
unchanged.

Full regression: `check_db_safety.py` PASS, `test_reasoning_
pipeline.py` ALL CHECKS PASSED, every prior FSI Phase 1-11 test file
unchanged and passing (17 files, 232 assertions), plus the new
`test_generate_research_dossier.py` (9/9), FRE-2 29/29, FRE-3 16/16,
FRE-4 16/16, FRE-5 21/21, FRE-6 40/40 (unchanged). Phase 5's own
`fsi_phase5_validate_pipeline.py` harness re-run and still reports PASS
on all three components.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents`
(11,533), `extracted_facts` (267), `entities` (50), and `entity_
relationships` (5) row counts all unchanged — this phase has zero
write path to the production database, under any invocation, with or
without `--output`.

**FSI Phase 12 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
