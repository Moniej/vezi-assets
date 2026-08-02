# FSI Phase 22 — Final Report

*Portfolio-Context Dossier CLI. Full narrative in
`docs/fre_runs/fsi_phase22_implementation_log.md`.*

## Executive summary

FSI Phase 22 built `scripts/fre/generate_portfolio_context_dossier.py`,
a read-only CLI wrapper around Phase 20's `company_portfolio_context.
as_of()`/`.render()`, mirroring Phase 12's established pattern
exactly. A fresh full-platform review this phase also investigated a
new financial-health-flag candidate and set it aside with real data
(see below) rather than assumed reasoning.

## Files created/modified

- `scripts/fre/generate_portfolio_context_dossier.py` (new).
- `scripts/fre/test_generate_portfolio_context_dossier.py` (new, 10
  assertions).
- This report, the implementation log, and the pre-registration.

**No modification to `company_portfolio_context.py` or any other
frozen module, and no schema change.**

## Results

- CLI output confirmed byte-identical to calling `as_of()`/`render()`
  directly, for all 10 real FSI tickers plus CAVERTON (confirmed via
  direct query to be in the live H-011 sleeve today — exercises the
  "currently in the live sleeve" rendering path through the real CLI).
- `--output`, unknown-ticker, malformed-date, and missing-argument
  paths all behave identically to Phase 12's own precedent.
- Zero database writes across the entire test run, confirmed via
  row-count diffing.
- Full regression (32 test files, up from 31), `check_db_safety.py`,
  `test_reasoning_pipeline.py`, and Phase 5's harness (4 components,
  30 tables) all pass.

## Investigated and set aside this phase (disclosed, not silently dropped)

A new financial-health flag using an under-used already-computed trend
metric (`cfo`/`cfi`/`cff`/`fcf`) was considered as this phase's
candidate instead. Querying the real `financial_reasoning_conclusions`
table directly showed `fcf` has zero computed trend conclusions today
and `cfo`/`cfi`/`cff` each have exactly one — a flag built on this data
would be `insufficient_data` for nearly every real ticker. Set aside as
a live future candidate rather than built now with weak real backing;
see the pre-registration's alternatives section for the full reasoning
and why extending Phase 3's existing `margin_compression` rule instead
was also rejected (would modify a frozen module and reads as
coverage-expansion-in-disguise, not a new analytical category).

## Status: Part 9's composition views are now both operator-reachable

Screening (Phase 15), the base research dossier (Phase 12), the
Watchlist (Phase 21), and now the portfolio-annotated dossier (this
phase) are all reachable from the command line. Sector-coverage view
remains the sole unbuilt Tier-1 item, genuinely blocked on
`securities.sector_ngx` population.

## Recommendations for the next phase

Per the owner's standing continuous-execution authorization: the
health-flag candidate above remains open, pending more `cfo`/`cfi`/
`cff`/`fcf` data. With Part 9 now essentially exhausted (built, wired,
and operable, modulo one external blocker), and no other buildable-now
architectural gap surfaced by this phase's full-platform review, the
next step should be a comprehensive fresh audit of the entire platform
to determine whether a genuine stopping point (per the standing
authorization's own three stated conditions) has been reached.

---

**FSI Phase 22 is complete: fully implemented, validated, and
documented.**
