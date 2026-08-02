# FSI Phase 20 — Final Report

*Portfolio-Context-Annotated Research Dossier. Full narrative in
`docs/fre_runs/fsi_phase20_implementation_log.md`.*

## Executive summary

FSI Phase 20 built `src/ngxrot/fre/company_portfolio_context.py`,
composing Phase 11's research dossier, Phase 18's watchlist, and
Phase 17's portfolio-memory cross-reference into one object — the
exact integration Part 9 itself specifies (`docs/fre/
09_portfolio_reasoning.md` lines 82-93) and that Phases 17 and 18 each
explicitly named as deferred to "a future phase," never before
scheduled. A researcher generating a ticker's full context now sees,
in one place, whether it is on the watchlist (point-in-time-correctly)
and whether the fund is currently exposed to it — with zero new
reasoning, zero write path, and zero modification to any of the three
composed modules.

## Files created/modified

- `src/ngxrot/fre/company_portfolio_context.py` (new): `as_of()`,
  `render()`, `PortfolioAnnotatedDossier`.
- `scripts/fre/test_company_portfolio_context.py` (new, 18 assertions).
- This report, the implementation log, and the pre-registration.

**No modification to `company_research_dossier.py`, `watchlist.py`,
`portfolio_memory.py`, or any other existing table/module** — confirmed
directly via `git diff --stat`, not just asserted.

## Results

- Reuses `watchlist.list_active()` (not `get_history_for_ticker()`)
  specifically because it is the one watchlist reader that is already
  point-in-time-correct — verified directly that an entry added after
  the dossier's own `as_of_date` is correctly excluded.
- Tested against the two real combinations that exist in production
  today: AFRIPRUD (FSI ticker, not on the watchlist, not in the live
  sleeve) and CAVERTON (confirmed via direct query to be in the live
  H-011 sleeve today; also not on the watchlist — the real
  production `watchlist_entries` table is currently empty).
- The watchlist-active path (and its PIT-correctness) was proven on a
  disposable scratch copy, since the real table has no rows yet; the
  real production database's row counts and integrity are confirmed
  unchanged.
- Full regression (30 test files, up from 29), `check_db_safety.py`,
  `test_reasoning_pipeline.py`, and Phase 5's harness (4 components,
  30 tables) all pass.

## Design decisions disclosed

- `portfolio_memory.cross_reference()`'s always-live (non-PIT) nature
  is an inherited limitation from Phase 17, not something this phase
  introduces or attempts to fix — `AlphaEngine.recommendations()` has
  no historical query capability. The rendered output labels this
  section explicitly as "NOT point-in-time" so a reader is never
  misled into treating it as historically accurate.
- A new module was written rather than modifying
  `company_research_dossier.py` in place — consistent with this
  platform's standing discipline (established since Phase 8) of never
  editing a previously frozen, already-tagged module when composition
  suffices.

## Status: Part 9's named integration point is now closed

The exact wiring Part 9 describes for Portfolio Memory ("attach a note
to a CompanyThesis or watchlist entry") is now built, tested, and
frozen — twice-deferred, now delivered.

## Recommendations for the next phase

Per the owner's standing continuous-execution authorization, live
candidates for the next architecture review (to be evaluated fresh,
not assumed) include: a CLI wrapper for Watchlist (`add`/`remove`/
`list`, mirroring Phase 15's pattern — the one remaining Watchlist
operational gap); a CLI wrapper for this phase's own
`company_portfolio_context.py` (mirroring Phase 12's pattern); or a
fresh full-platform review now that Part 9 is fully closed except for
the externally-blocked Sector-coverage view.

---

**FSI Phase 20 is complete: fully implemented, validated, and
documented.**
