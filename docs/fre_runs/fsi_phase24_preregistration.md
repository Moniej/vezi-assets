# FSI Phase 24 — Pre-registration

*Sector-Coverage View. Per the owner's standing continuous-execution
authorization: gap identified, alternatives considered, implemented
without an approval checkpoint.*

## Gap identified

Part 9 (`docs/fre/09_portfolio_reasoning.md` lines 63-67) names Sector-
coverage view as one of its five Tier-1 capabilities: *"An aggregation
of the current watchlist/research pipeline by sector (once securities.
sector_ngx is populated...) — answers 'how balanced is our research
coverage across sectors,' a research-management question, not a
portfolio-exposure question (no positions exist for this to measure
exposure of)."* It has sat on the externally-blocked list through every
phase since Phase 14 because `securities.sector_ngx` was 0/320
populated. Phase 23 populated it for 136/320 real securities from NGX's
own official classification. This is therefore the first phase in this
program's history where Sector-coverage view is genuinely buildable,
not just designed.

## Why this is the single highest-leverage gap right now

- It is the only remaining unbuilt item in Part 9's Tier 1 — closing
  it means every Tier-1 capability Part 9 names is now built, tested,
  and (where a CLI makes sense) operable.
- It was blocked for the entire duration of this program until last
  phase; building it immediately, rather than letting the newly-
  unblocked capability sit unbuilt, matches the standing authorization's
  own instruction to close a real gap the moment it becomes buildable.
- It reuses three already-frozen sources of truth (`securities.
  sector_ngx`, `financial_ratios.list_tickers()` for FSI coverage, and
  `watchlist.list_active()` for curation coverage) with zero new
  extraction and zero new write path.

## Alternatives considered and rejected

1. **Wait for `sector_ngx` coverage to grow past 136/320 before
   building this.** Rejected — Part 9's own design does not set a
   coverage-percentage threshold; a coverage view is exactly the tool
   that makes coverage GAPS visible in the first place ("how balanced
   is our research coverage" is itself a question about gaps). Waiting
   for completeness before building the tool that reports on
   incompleteness is circular.
2. **A single combined "coverage score" per sector** (e.g., a 0-1
   composite of FSI coverage + watchlist density). Rejected —
   this is exactly Part 9's own already-named risk (a "shadow ranking,"
   alternatives #1 in `09_portfolio_reasoning.md`) recurring in
   aggregate form: a composite score across sectors would read as an
   implied ranking of which sectors matter most, which this platform's
   guardrails forbid. This phase reports raw counts per sector only,
   alphabetically ordered, never sorted by magnitude.
3. **Extending `screening.py` (Phase 14) to accept a `sector` filter
   parameter**, rather than a new module. Rejected — `screening.py` is
   frozen, and its own scope is per-ticker categorical filtering
   (fired/not-fired, trend direction), a different shape of question
   than "aggregate counts across all tickers grouped by sector." A new
   module keeps Phase 14 untouched and keeps this capability's own
   guardrails (no numeric score) independently auditable.
4. **Including a CLI wrapper in this same phase.** Rejected for this
   phase specifically — mirrors this session's own established
   build-then-CLI separation (Screening: Phase 14→15; Watchlist: Phase
   18→21) — the aggregation logic is built and tested first; a CLI is
   a natural, low-risk follow-on if wanted.

## Design

- New module `src/ngxrot/fre/sector_coverage.py`.
- `SectorCoverageRow` dataclass: `sector_ngx` (str, or the literal
  string `"UNKNOWN"` for tickers with `sector_ngx IS NULL` — disclosed
  as its own row, never silently dropped), `total_tickers`,
  `fsi_covered_tickers` (tickers in this sector with at least one real
  `extracted_facts` row, i.e. genuinely researched, not just
  listed), `watchlist_tickers` (tickers in this sector currently
  active on the watchlist as of the given date). No score, no rank,
  no weight, no percentage/ratio field — three plain counts only.
- `coverage_by_sector(con, as_of_date) -> list[SectorCoverageRow]` —
  iterates every distinct `sector_ngx` value in `securities` (including
  the `NULL`/`"UNKNOWN"` bucket), counts total tickers, cross-references
  `financial_ratios.list_tickers()` (Phase 3, unmodified) for FSI
  coverage, and `watchlist.list_active(con, as_of_date)` (Phase 18,
  unmodified, already PIT-correct) for watchlist coverage. Always
  returned in alphabetical order by `sector_ngx` (`"UNKNOWN"` sorts
  last, explicitly forced there rather than wherever it happens to
  alphabetize, so it reads as a deliberate disclosure row, not a
  buried anomaly) — never sorted by any count, matching every other
  cross-ticker function on this platform (Screening, Watchlist's
  `list_active()`).
- No write path anywhere; no new SQL beyond simple `GROUP BY`-style
  counting queries against `securities`/`extracted_facts`/
  `watchlist_entries`.

## Guardrails (mechanically verified, not just asserted)

- `SectorCoverageRow` dataclass fields checked against
  `{score, rank, weight, strength, priority, percentage, ratio,
  coverage_score}` — none present.
- `inspect.signature(coverage_by_sector)` checked against
  `{limit, top_n, sort_by, rank_by, threshold}` — none present.
- Output order checked directly against Python's own `sorted()` (with
  `"UNKNOWN"` forced last), never by any count value.
- AST inspection confirms no `INSERT`/`UPDATE`/`DELETE` SQL statement
  anywhere in the new module.
- Real-data correctness: verified against the real, current state —
  9 of 10 FSI tickers have a known sector (UBN does not, correctly
  counted under `"UNKNOWN"`); the real production `watchlist_entries`
  table's current state (whatever it holds at run time) is reflected
  exactly, not assumed empty.

## Expected outcome

A new, additive, read-only module and its test file; no schema
change; no modification to any frozen module (`financial_ratios.py`,
`watchlist.py`, `securities` table itself). This closes Part 9's Tier
1 in full — all five capabilities Part 9 names as buildable-now
(Watchlist, Screening, Sector-coverage view, Qualitative correlation
notes, Portfolio memory) are now built and tested, for the first time
in this program's history.
