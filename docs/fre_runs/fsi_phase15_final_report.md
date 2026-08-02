# FSI Phase 15 — Final Report

*Screening CLI. Full narrative in
`docs/fre_runs/fsi_phase15_implementation_log.md`.*

## Executive summary

FSI Phase 15 built `scripts/fre/screen_companies.py`, a thin CLI wrapper
around Phase 14's `screen_by_flag()`/`screen_by_trend()`, mirroring
Phase 12's proven CLI pattern exactly. Closes the "reachable only via
Python" gap Phase 14's own final report named as its top recommendation.
Zero new reasoning, zero new data, zero database writes.

## Files created

- `scripts/fre/screen_companies.py` (new).
- `scripts/fre/test_screen_companies.py` (new, 10 assertions).
- This report, the implementation log, and the pre-registration.

**No schema change. No modification to `screening.py` (Phase 14) or any
other frozen module.**

## Results

- CLI output byte-identical to direct Python calls, for both subcommands,
  verified via real subprocess invocation.
- Clean, non-crashing errors for every invalid input (unrecognized
  categorical value, malformed date, missing argument) — validated at
  two independent layers (argparse `choices=`, then `screening.py`'s own
  `ValueError` guard).
- Zero database writes confirmed across the entire test run, including
  every subprocess invocation.
- Full regression (25 test files, 360 assertions) and Phase 5's
  validation harness both pass; golden snapshot correctly unchanged.

## Design note disclosed

Imports a private constant (`_VALID_DIRECTIONS`) from the now-frozen
`screening.py` rather than modifying that module to make it public, or
duplicating the tuple locally — consistent with this program's standing
"never modify a frozen module" discipline (Phase 11 precedent), chosen
as the lesser of two departures from "reuse, don't duplicate."

## Recommendations for the next phase

Per the owner's standing continuous-execution authorization, proceeding
directly to Phase 16 (extending Phase 5's validation harness to cover
Phases 6-15) — a gap named in every architecture review since Phase 9,
now addressed.

---

**FSI Phase 15 is complete: fully implemented, validated, and
documented.**
