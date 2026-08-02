# FSI Phase 25 — Pre-registration

*Sector-Coverage View CLI. Per the owner's standing continuous-
execution authorization: gap identified, alternatives considered,
implemented without an approval checkpoint.*

## Gap identified

Phase 24 built `sector_coverage.coverage_by_sector()` — the last of
Part 9's five Tier-1 capabilities — but, like every other "build"
phase's own pattern on this platform (Screening: Phase 14→15;
Research dossier: Phase 11→12; Watchlist: Phase 18→21;
Portfolio-context dossier: Phase 20→22), it shipped with no
command-line entry point. Phase 24's own final report named this
explicitly as the live next candidate.

## Why this is the single highest-leverage gap right now

A fresh full-platform review this phase considered the other
candidates on the table (recorded across Phases 22-24's own final
reports) and found none of them clear this bar yet:

- **Wiring `sector_ngx` into `valuation_engine.classify_company_type()`
  or `company_intelligence.py`'s Industry Exposure field** — both were
  explicitly investigated and deliberately deferred in Phase 23 as
  their own separate, non-trivial judgment call (mapping NGX's 13
  sector headings onto a different taxonomy each), not a quick
  follow-on. Rushing either now, right after the data-population
  phase, would violate the same "one dimension of risk at a time"
  discipline this session has held throughout.
- **A `cfo`/`cfi`/`cff`/`fcf`-based health flag** — re-checked against
  real data again this phase: still 0-1 computed trend conclusions per
  metric, unchanged since Phase 22's own finding. Still too thin.
- **Coverage expansion round 2** — re-considered again and rejected
  again for the same reason every phase since 19 has given: not a new
  capability.

The CLI wrapper for `coverage_by_sector()` is the only candidate that
is simultaneously a real, named gap (twice-cited), low-risk (pure
read-only wrapper, the platform's safest category of change), and
requires zero new judgment calls.

## Alternatives considered and rejected

1. **Wiring `sector_ngx` into `valuation_engine.py`/`company_
   intelligence.py` instead of a CLI.** Rejected for this phase — see
   above; each is its own separately-scoped design decision, not a
   quick win, and forcing one now would risk exactly the kind of
   rushed, under-considered judgment call this platform's discipline
   warns against.
2. **A `cfo`/`cfi`/`cff`/`fcf` health flag.** Rejected again, same
   real-data finding as Phase 22.
3. **Coverage expansion round 2.** Rejected again, not a new
   capability, per every prior phase's own review since 19.

## Design

- New script `scripts/fre/screen_sector_coverage.py`, mirroring Phase
  12/15/22's established CLI pattern exactly: UTF-8 stdout/stderr,
  `mode=ro` connection (read-only, matching every prior CLI wrapper
  except Phase 21's Watchlist CLI, which is write-capable for a
  different reason), a single `--as-of` argument with the same custom
  date-validation error message and exit code 1 convention.
- Calls `sector_coverage.coverage_by_sector()` unmodified, exactly
  once.
- Output: one line per sector (alphabetical, `UNKNOWN` last, inherited
  from `coverage_by_sector()`'s own ordering — no re-sorting in the
  CLI layer), showing the three plain counts, never a computed
  percentage or score.

## Guardrails (mechanically verified, not just asserted)

- Real subprocess invocation compared for exact equivalence against
  calling `coverage_by_sector()` directly.
- Malformed `--as-of` produces a clear error and exit code 1, never a
  raw traceback.
- Zero database writes across the entire test run (row-count diffing).
- Confirmed `sector_coverage.py` is byte-for-byte unchanged
  (`git diff --stat`) after this phase.

## Expected outcome

A new, additive, read-only operator tool; no schema change; no
modification to any frozen module. Every one of Part 9's five Tier-1
capabilities is now both built AND operator-reachable from the command
line (Screening, Research dossier composition, Watchlist,
Portfolio-context dossier, and now Sector-coverage view).
