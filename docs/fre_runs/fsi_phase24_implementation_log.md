# FSI Phase 24 — Implementation Log

*Per `docs/fre_runs/fsi_phase24_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Confirmed real current state before designing

Checked directly, not assumed: production `watchlist_entries` is still
empty (0 rows) — no CLI invocation in Phases 21/22/23 ever wrote to
it. `securities.sector_ngx` is 136/320 populated (Phase 23); `list_
tickers()` still returns the same 10 real FSI tickers. This determined
the test design: the watchlist-count dimension's real-data assertions
are honest negatives (0 for every sector today), with the positive
path proven separately on a scratch copy.

## Entry 1 — `src/ngxrot/fre/sector_coverage.py`

`coverage_by_sector(con, as_of_date) -> list[SectorCoverageRow]`.
Three plain counts per sector (`total_tickers`, `fsi_covered_tickers`,
`watchlist_tickers`) — no combined score, no percentage, no ratio,
matching Part 9's own explicit rejection of a "shadow ranking" applied
here to the aggregate-coverage case. Tickers with `sector_ngx IS NULL`
are grouped under an explicit `"UNKNOWN"` bucket, forced to sort last
regardless of alphabetical position, so the disclosure reads as
deliberate rather than an artifact of string sorting.

## Entry 2 — Real-data verification

Confirmed directly: all 320 real securities are accounted for exactly
once across the returned rows (including `UNKNOWN`); all 10 real FSI
tickers are counted exactly once across `fsi_covered_tickers` sums;
`CONSUMER GOODS` correctly reports 3 (NASCON, NESTLE, BUAFOODS); UBN
(the one FSI ticker with no known sector) is correctly counted under
`UNKNOWN`, not dropped. With the real, empty `watchlist_entries`
table, every sector row correctly reports `watchlist_tickers=0` — an
honest negative, confirmed rather than assumed.

## Entry 3 — Watchlist-count positive path, proven on a scratch copy

Added a real watchlist entry for NASCON (`added_at='2026-07-01'`) on a
disposable scratch copy; confirmed `CONSUMER GOODS`'s `watchlist_
tickers` becomes 1 as of `2026-08-02`, and correctly reverts to 0 as
of a date before the entry's own `added_at` — PIT correctness is
inherited for free from `watchlist.list_active()` (Phase 18, called
unmodified), not re-implemented.

## Entry 4 — Mechanical guardrails

`SectorCoverageRow` dataclass fields checked against `{score, rank,
weight, strength, priority, percentage, ratio, coverage_score}` — none
present. `inspect.signature(coverage_by_sector)` checked against
`{limit, top_n, sort_by, rank_by, threshold}` — none present. Output
order checked directly against Python's own `sorted()` (with
`UNKNOWN` forced last), never by any count. AST inspection confirms
zero `INSERT`/`UPDATE`/`DELETE` string literals in the new module.

## Entry 5 — Full regression and validation (complete)

`scripts/fre/test_sector_coverage.py` (new, 15/15). Full regression:
34 test files (was 33), all green — no existing test file needed any
change. `check_db_safety.py` PASS. `test_reasoning_pipeline.py` ALL
CHECKS PASSED. Phase 5 harness: all 4 components PASS — 31 tables,
unchanged before/after (this phase adds no table).

**No modification to any existing table, or to `financial_ratios.py`/
`watchlist.py`/`securities`.** No schema change. The golden snapshot
(137 facts / 267 conclusions) is unaffected.

**FSI Phase 24 is now complete, validated, and documented.** This
closes Part 9's Tier 1 in full: all five capabilities Part 9 names as
buildable-now (Watchlist, Screening, Sector-coverage view, Qualitative
correlation notes, Portfolio memory) are now built and tested, for the
first time in this program's history.
