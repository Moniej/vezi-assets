# FSI Phase 19 — Final Report

*Qualitative Correlation Notes. Full narrative in
`docs/fre_runs/fsi_phase19_implementation_log.md`.*

## Executive summary

FSI Phase 19 built `src/ngxrot/fre/correlation_notes.py`, implementing
Part 9's "Qualitative correlation notes" Tier-1 capability
(`docs/fre/09_portfolio_reasoning.md`). A `CorrelationNote` states only
a narrative, evidenced shared-exposure reason between two named
tickers — never a numeric correlation coefficient, never a
shared-edge count, never an all-pairs ranking. This phase also
discloses and corrects a factual error in Phase 17/18's own
documentation: Part 9 names five Tier-1 capabilities, not three.

## Correction disclosed

Phase 17's and Phase 18's final reports both stated Part 9 has three
Tier-1 items and that Phase 18 "closes Part 9's Tier-1 list in full."
Part 9 actually names five: Watchlist, Screening, Sector-coverage
view, Qualitative correlation notes, Portfolio memory. Phases 14/15,
17, and 18 built three of the five; Sector-coverage view and
Qualitative correlation notes were never previously built or
mentioned. This report and its pre-registration state the correction
forward-looking, consistent with how this platform has always handled
a prior mis-statement (the Phase 9 `relation_taxonomy.toml` precedent)
rather than editing already-tagged, frozen phase docs.

## Files created/modified

- `src/ngxrot/fre/correlation_notes.py` (new): `note_for_pair()`,
  `CorrelationNote`, `SharedExposureReason`, `MACRO_EXPOSURE_RELATION_TYPES`.
- `scripts/fre/test_correlation_notes.py` (new, 14 assertions).
- This report, the implementation log, and the pre-registration.

**No modification to any existing table, any frozen module (including
`entity_context.py`), or the schema.**

## Results

- Reuses `entity_context.get_entity_context()` unmodified — no new SQL
  against `entities`/`entity_relationships`.
- A shared exposure requires the same `relation_type` (restricted to
  the `[macro_exposure]` taxonomy group) AND the same counterpart
  entity — verified both conditions are independently required (a
  same-counterpart-different-type case correctly does not match).
- Confirmed directly against the real database: `entity_relationships`
  holds 0 `macro_exposure`-type rows today, so every real ticker pair
  honestly returns an empty note — not a stub, a true reflection of
  current graph coverage.
- The positive-match path was proven on a disposable scratch copy with
  synthetic data; the real production database's row counts and
  integrity are confirmed unchanged.
- Full regression (29 test files, up from 28), `check_db_safety.py`,
  `test_reasoning_pipeline.py`, and Phase 5's harness (4 components,
  30 tables) all pass.

## Design decisions disclosed

- Pairwise-only (`note_for_pair`, two named tickers), deliberately
  never an all-pairs/matrix function — Part 9's own risk flag
  ("watchlist creep into de facto ranking," line 150) applies equally
  to an NxN correlation-notes grid, which would read as a ranked
  heatmap the moment it was displayed.
- `[macro_exposure]` relation types only (`exposed_to_commodity`,
  `exposed_to_fx`, `exposed_to_policy`) — `[corporate_structure]`,
  `[commercial]`, and `[governance]` types are excluded because they
  are either identity/lineage edges or direct commercial links between
  the pair itself, not a shared exposure to a common third party (Part
  9's own example is specifically third-party commodity exposure).
- No CLI wrapper in this phase — `note_for_pair()` is a two-argument
  function best consumed directly for now; a CLI wrapper (mirroring
  Phase 15's `screen_companies.py` pattern) is a natural, low-risk
  follow-on if operational access is wanted later.

## Status: Part 9 (Portfolio Reasoning Tier 1) — 4 of 5 built

Watchlist (Phase 18), Screening (Phase 14/15), Portfolio memory
(Phase 17), and Qualitative correlation notes (this phase) are built,
tested, and frozen. Sector-coverage view remains the sole unbuilt
item, correctly and permanently parked pending `securities.sector_ngx`
population — an external data dependency, not a code gap.

## Recommendations for the next phase

Sector-coverage view cannot proceed until `sector_ngx` is populated
(owner/vendor decision, outside this program's scope) — it belongs on
the final architecture audit's "Requires-external-data" list, not as
a candidate for the next phase. The next phase should come from a
fresh, full-platform architectural review rather than from Part 9,
which (modulo the one external blocker) is now closed.

---

**FSI Phase 19 is complete: fully implemented, validated, and
documented.**
