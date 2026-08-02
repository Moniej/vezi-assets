# FSI Phase 20 — Implementation Log

*Per `docs/fre_runs/fsi_phase20_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Confirmed the composed functions' exact signatures before designing

Read `portfolio_memory.py` and `watchlist.py` directly rather than
assuming their signatures from memory. Confirmed `cross_reference
(ticker: str)` takes no `con`/`as_of_date` (always live/current — a
real, disclosed limitation carried forward, not fixed here). Confirmed
`list_active(con, as_of_date=None)` is the one PIT-correct watchlist
reader (`get_history_for_ticker()` returns live `removed_at`
regardless of any cutoff, which would leak future information into a
point-in-time dossier) — this determined which of the two Phase 18
functions to reuse.

## Entry 1 — `src/ngxrot/fre/company_portfolio_context.py`

`as_of(con, ticker, as_of_date) -> PortfolioAnnotatedDossier` composes
`company_research_dossier.build_dossier()` (Phase 11), `watchlist.
list_active()` filtered to one ticker in Python (Phase 18), and
`portfolio_memory.cross_reference()` (Phase 17) — each called exactly
once, none modified. `render()` reuses Phase 11's `render_dossier()`
verbatim, then appends two new template-only sections.

## Entry 2 — Real-data verification, both real combinations that exist today

Confirmed the real production `watchlist_entries` table is currently
empty (0 rows) before asserting "not on the watchlist" is a true
negative, not an assumed one. Tested AFRIPRUD (a real FSI ticker: not
on the watchlist, not in the live sleeve) and CAVERTON (a real ticker
confirmed via direct `AlphaEngine().recommendations()` query to
currently be in the live H-011 sleeve, hypothesis_id="H-011"; also not
on the watchlist). `build_dossier()` succeeds honestly for CAVERTON
even though it is outside the 10 hand-extracted FSI tickers, since
`company_thesis_360` draws on the broader `company_intelligence`
dataset — confirmed directly rather than assumed, since no FSI-ticker
∩ live-sleeve-ticker overlap currently exists (a real, disclosed
property of current data, same category as prior phases' honest
negatives).

## Entry 3 — Watchlist-active path proven on a disposable scratch copy

Real production `watchlist_entries` is empty, so the positive
"on-watchlist" path was proven on a scratch copy (`db.
new_scratch_db_path()` + `shutil.copy`): added a real entry for
AFRIPRUD with `added_at='2026-07-01'`, confirmed `as_of(con,
'AFRIPRUD', '2026-08-02')` shows it active, and confirmed `as_of(con,
'AFRIPRUD', '2026-06-01')` (before the entry's own `added_at`) shows
it correctly absent — PIT correctness verified directly, not assumed
from `list_active()`'s own prior test coverage.

## Entry 4 — Mechanical guardrails, including a direct diff check

`PortfolioAnnotatedDossier` dataclass fields checked against
`{score, rank, weight, strength, priority}` — none present.
`inspect.signature(as_of)` checked against `{limit, top_n, sort_by,
rank_by, threshold, tickers}` — none present. AST inspection confirms
zero `INSERT`/`UPDATE`/`DELETE` string literals in the new module.
Additionally, `git diff --stat` was run directly against
`company_research_dossier.py`, `watchlist.py`, and `portfolio_memory.py`
and confirmed empty — proving, not just asserting, that all three
composed modules are byte-for-byte unchanged by this phase.

## Entry 5 — Full regression and validation (complete)

`scripts/fre/test_company_portfolio_context.py` (new, 18/18). Full
regression: 30 test files (was 29), all green — no existing test file
needed any change. `check_db_safety.py` PASS. `test_reasoning_
pipeline.py` ALL CHECKS PASSED. Phase 5 harness: all 4 components
PASS — Component 3 still correctly reports 30 tables (unchanged; this
phase adds no table), unchanged before/after across the entire run.

**No modification to any existing table, or to any of the three frozen
modules this phase composes.** No schema change. The golden snapshot
(137 facts / 267 conclusions) is unaffected.

**FSI Phase 20 is now complete, validated, and documented.** This
closes the wiring gap Part 9 itself specified and that Phases 17 and
18 each explicitly deferred to "a future phase."
