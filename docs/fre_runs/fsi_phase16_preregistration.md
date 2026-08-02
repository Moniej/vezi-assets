# FSI Phase 16 — Composition-Layer Ticker Coverage Fix (Pre-registration)

*Per the owner's standing continuous-execution authorization. Builds on
`fsi-phase15-baseline-2026-08-02`.*

## Architectural gap (found via direct inspection, not assumed)

Investigated "extend Phase 5's harness to cover Phases 6-14" as
originally planned, and found a more precise, more consequential real
gap via direct grep: **every one of the 6 dedicated per-phase test files
for Phase 6, 7, 8, 10, 11, 12 still hardcodes the ORIGINAL 5-ticker list**
(`["UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON"]`), never updated after
Phase 13 grew the real roster to 10. Phase 13's own implementation log
documented that all 6 composition layers were manually verified to
generalize to the 5 new tickers — but that verification was a one-off
ad-hoc script, never captured into the permanent, mechanically-
reproducible regression suite. Every regression run since Phase 13 has
been silently exercising only half the real tickers while its own
assertion text still says "for all 5 tickers."

## Why highest-priority now

This is validation debt with a real, demonstrated failure mode: it
ALREADY let a legitimate data-expansion phase (13) complete without its
own generalization claim being captured as a reproducible test. Any
future ticker-coverage-expansion phase (a near-certain future event, per
Phase 13's own report naming 39 unused candidate tickers) would repeat
this exact gap unless the root cause — hardcoded ticker lists instead of
dynamic discovery — is fixed, not just patched once.

## Alternatives considered and rejected

1. **A new, separate "Phase 6-15 coverage" test file.** Rejected — would
   duplicate each phase's own existing, detailed equivalence logic rather
   than fixing the actual defect (a stale list) in place; violates
   "reuse existing modules instead of duplicating logic."
2. **Just hardcode the list as 10 tickers.** Rejected as the ONLY fix —
   it would silently go stale again at the next coverage-expansion phase,
   reproducing the identical defect. The root cause is "hardcoded" itself,
   not "hardcoded to the wrong number."
3. **A new Phase 5 harness Component 4 duplicating each composition
   layer's own smoke test.** Considered as a supplementary addition (see
   below) but rejected as the PRIMARY fix for the same duplication reason
   as (1).

## Selected fix (conservative, additive, test-only)

Change all 6 files' `tickers = [...]` (or `fsi_tickers = (...)`) to derive
the list dynamically via `financial_ratios.list_tickers(con)` — the same
function every production composition module already uses internally to
discover tickers. This makes the test suite self-updating: any future
ticker addition is automatically covered by every dedicated test file
without a manual edit, closing the root cause, not just its current
symptom. Message strings ("for all 5 tickers") are updated to state the
count is dynamic, not hardcoded to a number that will itself go stale.

**One real behavioral wrinkle found while designing this fix**: `test_
entity_context.py`'s "output equivalence" check (`get_entity_context()`
fields vs. a direct query) currently requires a matching non-NULL
`entities` row (`direct is None -> equivalence_ok = False`) — correct
for the original 5 tickers (all have a real `entities` row since Phase
9), but WRONG once the 5 Phase-13 tickers are included, since NONE of
them has an `entities` row yet (Phase 13's own disclosed, deferred gap).
The correct behavior is "both empty" counts as equivalence (`ctx.
entity_id is None AND direct is None`), not a mismatch — `entity_
context.py` itself already returns `entity_id=None` for exactly this
case ("no graph presence yet KNOWN" is a valid, honest result, not an
error). Fixed in the TEST's own comparison logic, not in `entity_
context.py` (frozen, and already behaving correctly).

**Supplementary addition**: Phase 5's own `fsi_phase5_validate_pipeline.
py` gains a 4th component, "composition-layer smoke coverage" — for every
real ticker (from `list_tickers()`), confirm `company_memory_360.as_of()`,
`financial_reasoning_report.render_report()`, `company_thesis_360.
as_of()`, `entity_context.get_entity_context()`, and `company_research_
dossier.build_dossier()`/`render_dossier()` all execute without exception.
This is deliberately a coarse smoke check (no exception across every
real ticker), not a re-implementation of each phase's own detailed
equivalence assertions — the exact class of check that would have
caught, at the platform level, that Phase 13 added tickers no composition
layer had ever been smoke-tested against by name.

## Why this fits the long-term architecture

Removes a concrete, demonstrated single point of silent staleness rather
than adding a parallel validation surface. Reuses `list_tickers()`
(already the production modules' own source of truth for "which tickers
exist") instead of a second, independently-maintained list. Preserves
every existing assertion's own specific, ticker-named checks (e.g.
NASCON's leverage flag, GTCO's rename) untouched — only the loop-driving
ticker list becomes dynamic.

## Success criteria

All 6 test files pass with the dynamic ticker list (now exercising 10
tickers, not 5) with zero regression in their own existing ticker-
specific assertions. Phase 5 harness's new Component 4 passes for all 10
real tickers. Full regression + Phase 5 harness both still pass overall.

## Implementation boundaries

**In scope**: the 6 test files' ticker-list source (test-only change);
Phase 5 harness's new Component 4 (`pipeline_validation.py` addition,
read-only, no schema/data change). **Out of scope**: any modification to
Phase 6/7/8/9/10/11/12/14/15's own production modules.

---
*Implementation proceeds immediately.*
