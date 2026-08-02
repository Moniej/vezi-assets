# FSI Phase 19 — Implementation Log

*Per `docs/fre_runs/fsi_phase19_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Correction carried forward from pre-registration

Confirmed again, directly against `docs/fre/09_portfolio_reasoning.md`
line 39, that Part 9 names five Tier-1 capabilities, not three as
Phase 17/18's own docs stated. This phase closes the fourth of the
five (Qualitative correlation notes); Sector-coverage view remains the
one genuinely blocked item (`securities.sector_ngx` reconfirmed 0/320
populated this phase, via direct query against the real production
database).

## Entry 1 — `src/ngxrot/fre/correlation_notes.py`

`note_for_pair(con, ticker_a, ticker_b, as_of_date) -> CorrelationNote`.
Pairwise only — no ticker-list or all-pairs parameter exists anywhere
in the signature. Composes `entity_context.get_entity_context()`
(Phase 10, called unmodified, once per ticker) rather than issuing any
new SQL against `entities`/`entity_relationships`.

A shared exposure requires BOTH: the same `relation_type`, restricted
to the three names in `configs/relation_taxonomy.toml`'s
`[macro_exposure]` group (`exposed_to_commodity`, `exposed_to_fx`,
`exposed_to_policy`); AND the same `counterpart_entity_id`. Confirmed
via a dedicated test case that a shared counterpart with *differing*
relation_types does NOT match — same-type-and-same-counterpart is a
conjunction, not either condition alone.

`ticker_a == ticker_b` raises `ValueError` — a self-pair is not a
correlation question. An unknown/not-yet-graphed ticker is handled
identically to how `get_entity_context()` already handles it (empty
relationships, hence an empty note) — no new validation invented on
top of Phase 10's own behavior.

## Entry 2 — Real-data honest negative confirmed, not assumed

Queried the real production database directly before writing any test
assertion: `entity_relationships` currently holds exactly 5 rows (4
`renamed_from`, 1 `affects_order_1`) and 0 rows of any
`macro_exposure` type. `note_for_pair()` on two real tickers
(NASCON, CAP) against the live database therefore correctly returns an
empty `shared_exposures` list — an honest negative reflecting the
platform's actual current state, not a stub or a hardcoded empty
return.

## Entry 3 — Positive-match path proven on a disposable scratch copy

`db.new_scratch_db_path()` + `shutil.copy(db.DEFAULT_DB, scratch)`,
then a synthetic `commodity`-type entity ("Brent Crude") and two
`exposed_to_commodity` edges (NASCON→Brent Crude, CAP→Brent Crude)
were inserted only on the scratch copy. `note_for_pair()` correctly
returned exactly one `SharedExposureReason`, naming the right
`relation_type`, counterpart name, and both source `relationship_id`s
— proving the matching logic fires correctly once the data exists,
without ever touching the real database (confirmed at the end via
`snapshot_all_table_counts()`/`diff_table_counts()`, same pattern as
every prior write-adjacent test on this platform).

## Entry 4 — Mechanical guardrails

`CorrelationNote`/`SharedExposureReason` dataclass fields checked
against `{score, rank, weight, strength, priority, correlation,
coefficient}` — none present. `inspect.signature(note_for_pair)`
checked against `{limit, top_n, sort_by, rank_by, threshold, tickers}`
— none present. AST inspection of `correlation_notes.py` confirms zero
`INSERT`/`UPDATE`/`DELETE` string literals and no import of
`ngxrot.alpha_engine`/`ngxrot.registry`.

## Entry 5 — Full regression (complete)

`scripts/fre/test_correlation_notes.py` (new, 14/14). Full regression:
29 test files (was 28), all green — no existing test file needed any
change. `check_db_safety.py` PASS. `test_reasoning_pipeline.py` ALL
CHECKS PASSED. Phase 5 harness: all 4 components PASS — Component 3
still correctly reports 30 tables (unchanged; this phase adds no
table), unchanged before/after across the entire run including
Component 4's smoke coverage.

**No modification to any existing table, any frozen module, or
`entity_context.py`.** No schema change. The golden snapshot (137
facts / 267 conclusions) is unaffected.

**FSI Phase 19 is now complete, validated, and documented.** Part 9's
Tier 1 now stands at 4 of 5 built (Watchlist, Screening, Portfolio
memory, Qualitative correlation notes). Sector-coverage view remains
the sole, genuinely externally-blocked item.
