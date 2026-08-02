# FSI Phase 15 — Implementation Log

*Per `docs/fre_runs/fsi_phase15_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Built exactly as pre-registered

`scripts/fre/screen_companies.py`: two subcommands (`flag`, `trend`),
each mapping 1:1 to Phase 14's `screen_by_flag()`/`screen_by_trend()`.
`argparse(choices=...)` validates every categorical value at the
argument-parsing layer, using the SAME constants (`KNOWN_FLAG_METRICS`,
`KNOWN_TREND_METRICS`) `screening.py` itself uses for its own `ValueError`
guard — two independent layers agreeing on the same source of truth, not
a separately-maintained list that could drift. UTF-8 `reconfigure()` on
stdout/stderr applied proactively from the start (Phase 12's own two real
bugs are now a known, avoidable class).

## Entry 1 — Design note: importing a private constant from a frozen module

`screen_companies.py` imports `_VALID_DIRECTIONS` from `screening.py`
(a private, underscore-prefixed name) rather than duplicating the tuple
`("increasing", "decreasing", "stable")` locally. Per this program's
standing "never modify a frozen module, not even for a cosmetic rename"
discipline (established explicitly in Phase 11, which kept duplicate
local copies of Phase 7's formatting helpers rather than touch Phase 7),
`screening.py` (frozen as of Phase 14) was not edited to make this
constant public. Python does not enforce the underscore convention at
runtime, so the import works correctly; this is disclosed as a minor,
deliberate exception to "reuse existing modules instead of duplicating
logic," chosen over EITHER modifying a frozen module OR duplicating a
constant that could silently drift out of sync with it.

## Entry 2 — Validation and full regression (complete)

`scripts/fre/test_screen_companies.py` (10/10): CLI stdout for both
subcommands is byte-identical to calling `screen_by_flag()`/`screen_by_
trend()` directly, via a real subprocess invocation; a real, correctly-
empty result (a far-past `--as-of`, before any conclusion is knowable)
prints "No matches.", never a blank output or a crash; unrecognized
`--metric`/`--direction` values and a malformed `--as-of` all produce
clear errors (argparse usage errors or the script's own date-format
check), never a raw traceback; zero database writes across every
subprocess invocation.

Full regression: 25 test files (was 24), 360 assertions (350 + 10), all
green. `check_db_safety.py` PASS. `test_reasoning_pipeline.py` ALL CHECKS
PASSED. Phase 5's own harness: golden snapshot UNCHANGED (137/267,
correctly — a CLI wrapper introduces no new fact or conclusion), cross-
phase consistency PASS, database immutability PASS.

**No schema change. No modification to `screening.py` or any other
frozen module.**

**FSI Phase 15 is now complete, validated, and documented.**
