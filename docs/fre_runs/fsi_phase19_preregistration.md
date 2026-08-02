# FSI Phase 19 — Pre-registration

*Qualitative Correlation Notes. Per the owner's standing
continuous-execution authorization: gap identified, alternatives
considered, implemented without an approval checkpoint.*

## Correction to Phase 17/18's own documentation (disclosed, not silently fixed)

Phase 17's and Phase 18's final reports/implementation logs both state
that Part 9 (`docs/fre/09_portfolio_reasoning.md`) names **three**
Tier-1 capabilities ("Watchlist, Screening, Portfolio memory") and that
Phase 18 "closes Part 9's Tier-1 capability list in full."

Re-reading `docs/fre/09_portfolio_reasoning.md` line 39 directly during
this phase's own gap analysis shows this is wrong. Part 9's Tier 1 row
names **five** items: Watchlists, Screening, **Sector-coverage view**,
**Qualitative correlation notes**, and Portfolio memory. Phases 14/15
(Screening), 17 (Portfolio memory), and 18 (Watchlist) built three of
the five. Sector-coverage view and Qualitative correlation notes were
never built, and were never mentioned in Phase 17/18's docs at all.

This correction is stated here, forward-looking, rather than by editing
Phase 17/18's own frozen, already-committed, already-tagged reports —
consistent with how this platform has always handled a prior
mis-statement (Phase 9's `relation_taxonomy.toml` correction is the
precedent: disclosed in the next phase's own docs, not retroactively
rewritten into a already-tagged commit).

## Gap identified

Of Part 9's two remaining, unbuilt Tier-1 items:

- **Sector-coverage view** — remains genuinely blocked. Confirmed again
  this phase: `securities.sector_ngx` is still 0/320 populated (checked
  directly against the real production database). This is an external
  data dependency (Part 9's own line 64: "once `securities.sector_ngx`
  is populated, Part 1/2's shared blocker"), not something resolvable by
  writing more code. It stays on the roadmap's "Requires-external-data"
  list.
- **Qualitative correlation notes** — **not** blocked by any stated
  precondition. Part 9 designs this capability in full (lines 69-80)
  and pre-specifies exactly what it must and must not be. This is
  therefore the correct, highest-leverage next phase: it closes the
  only remaining buildable-now gap in Part 9, using a design the
  architecture document has already fully specified and already
  pre-rejected three unsafe variants of.

## Why this is the single highest-leverage gap right now

- It is the last non-blocked item in an already-frozen architecture
  section (Part 9) that this program has been actively closing out
  since Phase 14 — finishing it converts Part 9 from "three of five
  built" to "four of five built, one externally blocked," an honest and
  complete state rather than a partially-closed one.
  Sector-coverage view cannot be started (external blocker), so this is
  the only Tier-1 item left that qualifies as "can implement
  immediately."
- It reuses, rather than duplicates, Phase 10's `entity_context.
  get_entity_context()` — the platform's only existing reader of
  `entity_relationships` — so implementation risk is low and no new
  read pattern against the knowledge graph needs to be invented.
- It has a real, verifiable "honest negative" property, matching this
  platform's "unknown stays unknown" discipline throughout: checked
  directly this phase, `entity_relationships` currently holds exactly 5
  rows (4 `renamed_from`, 1 `affects_order_1`) and precisely 0 rows of
  any `macro_exposure` type (`exposed_to_commodity`/`exposed_to_fx`/
  `exposed_to_policy`, per `configs/relation_taxonomy.toml`). This means
  the new capability will correctly report "no evidenced shared
  exposure known" for every real ticker pair today — a true, honest
  answer, not a stub — and will start returning real notes the moment a
  future extraction pass populates a macro-exposure edge, with zero
  code change required.

## Alternatives considered and rejected

1. **Sector-coverage view instead.** Rejected for this phase — genuinely
   blocked on `securities.sector_ngx` population (0/320 rows, confirmed
   again just now), an external data dependency outside this program's
   control. Building it now would mean either inventing sector
   assignments (fabricating data, a hard platform violation) or shipping
   a function that can never return a non-empty result — neither is
   real, useful, mechanically-testable capability. Deferred to the
   final architecture audit's "Requires-external-data" category.
2. **A numeric correlation/co-exposure score derived from shared-edge
   count.** This is Part 9's own explicitly pre-rejected alternative
   #2 (lines 123-129): "a plausible-looking but ungrounded
   pseudo-statistic." Re-rejected here for the same reason — a count of
   shared edges is not a correlation and would misrepresent its own
   evidentiary weight with false numeric precision.
3. **All-pairs / matrix computation (every ticker against every other
   ticker).** Rejected — Screening (Phase 14) is the platform's one
   sanctioned all-tickers-at-once function, justified by Part 9's own
   text because it is a pure categorical filter with no pairwise
   comparison. A correlation-notes matrix would silently produce an
   NxN grid that reads as a ranked/scored heatmap the moment it is
   displayed (the same "watchlist creep into de facto ranking" risk
   Part 9 itself flags at line 150, recurring in matrix form). This
   phase implements a strictly pairwise (two named tickers in, one note
   out) function only — never all-pairs.
4. **Extending `entity_context.py` itself with a new "find shared
   counterpart" method**, rather than a new module. Rejected —
   `entity_context.py` is Phase 10's frozen composition layer connecting
   the graph to Company Memory; correlation notes are a distinct
   capability (Part 9, not Part 2/6) with their own guardrails (no
   numeric field, pairwise-only). A new module composing
   `get_entity_context()` (calling it unmodified, twice, once per
   ticker) keeps Phase 10's module frozen and keeps this phase's own
   blast radius to one new file, matching every prior Tier-1 phase's
   own discipline (Phase 14, 17, 18 each added a new module rather than
   extending a frozen one).

## Design (per Part 9 lines 69-80, applied exactly)

- New module `src/ngxrot/fre/correlation_notes.py`.
- `note_for_pair(con, ticker_a, ticker_b, as_of_date) -> CorrelationNote`
  — pairwise only, two named tickers, never a ticker list or "all
  pairs" mode.
- Reuses `entity_context.get_entity_context()` unmodified, called once
  per ticker, to get each ticker's own PIT-correct relationship list —
  no new graph-reading SQL, no new traversal logic.
- A shared exposure is recognized only when both tickers carry an edge
  of the **same** `relation_type`, drawn only from
  `configs/relation_taxonomy.toml`'s `[macro_exposure]` group
  (`exposed_to_commodity`, `exposed_to_fx`, `exposed_to_policy`), to the
  **same** counterpart entity — exactly Part 9's own example ("both
  companies carry an `exposed_to_commodity` edge to Brent crude").
  `[corporate_structure]`/`[commercial]`/`[governance]`/
  `[graph_provenance]` relation types are deliberately excluded: they
  are either direct identity/lineage edges (not a third-party shared
  exposure) or direct commercial links between the pair itself, a
  different concept Part 9 does not ask for here.
- `CorrelationNote` carries a `shared_exposures: list[SharedExposureReason]`
  field and nothing else numeric — no score, no strength, no count
  exposed as a headline field. `SharedExposureReason` states the
  `relation_type`, the counterpart's `canonical_name`, and both source
  `relationship_id`s (so the note is always traceable back to the two
  underlying graph rows) — a narrative, evidenced reason, never a
  number.
- No write path anywhere — read-only against `entities`/
  `entity_relationships` via `entity_context.py`, no write to any table,
  no import of `alpha_engine.py`/`registry.py`.
- If `ticker_a == ticker_b`, raises `ValueError` — a self-pair is not a
  correlation question. Unknown tickers are handled exactly as
  `get_entity_context()` already handles them (an entity that is not
  yet known as of the given date yields zero relationships, hence zero
  shared exposures, not an error) — no new validation is invented on
  top of Phase 10's own established behavior.

## Guardrails (mechanically verified, not just asserted)

- `CorrelationNote`/`SharedExposureReason` dataclass fields checked
  against `{"score", "rank", "weight", "strength", "priority",
  "correlation", "coefficient"}` — none present.
- `inspect.signature(note_for_pair)` checked against
  `{"limit", "top_n", "sort_by", "rank_by", "threshold", "tickers"}` —
  none present (confirms pairwise-only, not a plural/list parameter).
- AST inspection of the module's source confirms no `INSERT`/`UPDATE`/
  `DELETE` string literal anywhere, and no import of
  `ngxrot.alpha_engine` or `ngxrot.registry`.
- Real-data correctness: confirmed this phase, via direct query, that
  `entity_relationships` holds 0 `macro_exposure`-type rows today, so
  `note_for_pair()` on any two real tickers must return an empty
  `shared_exposures` list — tested explicitly, an honest negative, not
  assumed.

## Expected outcome

A new, additive, read-only module and its test file; no schema change;
no modification to `entity_context.py` or any other frozen module; the
golden snapshot (137 facts / 267 conclusions) is unaffected since this
phase adds no `extracted_facts`/`financial_reasoning_conclusions` rows.
Part 9's Tier 1 will then stand at 4 of 5 built (Watchlist, Screening,
Portfolio memory, Qualitative correlation notes), with Sector-coverage
view the sole remaining item, correctly and permanently parked on the
"Requires-external-data" list until `securities.sector_ngx` is
populated by an owner/vendor decision outside this program's scope.
