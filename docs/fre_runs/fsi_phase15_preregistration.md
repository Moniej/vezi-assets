# FSI Phase 15 — Screening CLI (Pre-registration)

*Per the owner's standing continuous-execution authorization (2026-08-02):
no approval checkpoint. Builds on `fsi-phase14-baseline-2026-08-02`;
modifies nothing in Phases 1-14.*

## Architectural gap

`src/ngxrot/fre/screening.py` (Phase 14) is reachable only via direct
Python calls. Every other FSI research capability that reached this same
state (Phase 7's `render_report()`, Phase 11's `render_dossier()`) later
got a CLI wrapper (Phase 12) — Screening is the one capability built
since then that has NOT.

## Why highest-priority now

Screening's own value is "find candidates without already knowing which
ticker to check" — but today that still requires writing a Python script
to call it, which is exactly the friction Phase 12 eliminated for the
single-ticker dossier. Phase 14's own final report named this explicitly
as its top recommendation. Zero new reasoning, zero new data — purely
closing an access gap on an already-validated, already-tested capability,
the same low-risk profile as Phase 12 itself.

## Alternatives considered and rejected

1. **Phase 16 (validation-harness extension) first.** Real gap, but
   Screening's CLI is smaller, faster to ship, and has zero dependency
   on anything else — sequencing it first yields a usable artifact sooner
   without blocking the harness work at all (independent gaps, no
   ordering constraint between them).
2. **Watchlist persistence.** Requires a new table and an `entry_criteria`
   workflow design — larger surface, and arguably premature before
   Screening itself has an operational entry point (a watchlist's own
   natural population mechanism would be "save a screening result").
3. **Portfolio-memory cross-reference.** Reads `alpha_engine.py`'s live
   sleeve — a different, larger risk surface (crossing into quant-engine
   data) than a CLI wrapper over an already-frozen, already-tested
   read-only module. Smaller, safer work should not wait behind it.

## Why this fits the long-term architecture

Directly mirrors Phase 12's own proven pattern (thin CLI, zero new logic,
UTF-8-safe I/O, ticker/argument validation, tested via real subprocess
invocation) — extending an established, low-risk convention rather than
inventing a new one. Screening remains read-only; the CLI adds no write
path, no new reasoning, no schema change.

## Design decision (conservative, no pause)

Mirrors `generate_research_dossier.py` exactly: `argparse`, UTF-8
`reconfigure()` on stdout/stderr from the start (Phase 12's own two real
bugs — console encoding and subprocess-capture mojibake — are now a
known, avoidable class, so both fixes are applied proactively here
rather than re-discovered). Output: one line per match, plain text,
deterministic order (inherits Screening's own alphabetical-ticker
guarantee). Two subcommands: `flag --metric --fired --as-of` and
`trend --metric --direction --as-of`. An unrecognized categorical value
produces a clear CLI error (argparse `choices=`), never a raw traceback
— the CLI enforces this at the argument-parsing layer, on top of
`screening.py`'s own `ValueError` guard, giving the user the earliest,
clearest failure point.

## Success criteria

Output matches direct `screen_by_flag()`/`screen_by_trend()` calls
exactly, for real data, via a real subprocess invocation (not just an
in-process call). Zero database writes. Clean error for an invalid
`--metric`/`--fired`/`--direction`/malformed `--as-of`. Full regression
+ Phase 5 harness still pass.

---
*Implementation proceeds immediately.*
