# FSI Phase 20 — Pre-registration

*Portfolio-Context-Annotated Research Dossier. Per the owner's standing
continuous-execution authorization: gap identified, alternatives
considered, implemented without an approval checkpoint.*

## Gap identified

Part 9 (`docs/fre/09_portfolio_reasoning.md`, lines 82-93) does not
just name "Portfolio memory" as a capability — it names the exact
integration point: *"A `PortfolioMemory.cross_reference(ticker)`
function may... attach a note to a `CompanyThesis` or watchlist entry
('this ticker is currently in the live Size sleeve...')... purely
informational, so a researcher knows their qualitative thesis concerns
a name the fund is actually exposed to."* Phase 17 built
`cross_reference()`, Phase 18 built the watchlist, and Phase 11/12
built the research-dossier composition view — but no phase has ever
actually wired any of the three together. A researcher reading a
ticker's institutional research dossier today (`generate_research_
dossier.py`) sees Company Memory, Investment Thesis Evidence, and
Knowledge Graph Context — but not whether the ticker is on the
watchlist, or whether the fund is actually exposed to it — despite
both being one function call away. This is the named, un-closed loop
Part 9 itself describes, not a newly-invented idea.

This is not a new observation: Phase 17's own final report states, of
this exact wiring, "A future phase could add this wiring as a small,
separately-tested step" (line 42), and Phase 18's final report
likewise deferred it. It has now been named twice and never
scheduled — this phase schedules it.

## Why this is the single highest-leverage gap right now

- It is Part 9's own explicitly pre-specified design (not a new
  invention this phase is proposing) — the lowest-uncertainty kind of
  gap to close, since the architecture document already states exactly
  what the composed output should say.
- It closes a twice-named, twice-deferred item rather than leaving it
  permanently deferred with no phase ever picking it up.
- It requires zero new SQL, zero new reasoning, and zero modification
  to any of the three frozen modules it composes
  (`company_research_dossier.py`, `watchlist.py`, `portfolio_memory.py`)
  — pure composition, the platform's lowest-risk category of change.
- It materially increases the usefulness of the one artifact a
  researcher actually reads end-to-end (the research dossier) without
  adding any new claim, score, or recommendation — squarely inside
  Tier 1's "research/advisory, buildable now" boundary.

## Alternatives considered and rejected

1. **Modify `company_research_dossier.py` directly to add the two new
   sections in place**, rather than writing a new module. Rejected —
   violates this platform's own standing discipline of never modifying
   a previously frozen, already-tagged module when composition
   suffices (Phase 11 itself never modified Phases 7/8/10; every
   subsequent phase composed on top instead). A new module keeps
   Phase 11's `build_dossier()`/`render_dossier()` byte-identical and
   independently re-verifiable forever — the same reasoning Phase 11's
   own docstring gives for calling Phase 7's `render_report()`
   verbatim rather than editing it.
2. **A CLI wrapper for Watchlist** (`add`/`remove`/`list` from the
   command line, mirroring Phase 15's pattern), instead of this phase.
   Real and valuable — Phase 18's own final report names it as the
   natural next step — but lower leverage than closing a gap Part 9
   itself designed and that has now been deferred twice. Not
   competing: recorded as a live candidate for a near-future phase,
   not rejected outright.
3. **Coverage expansion round 2** (39 of 49 already-scoped tickers
   remain unextracted). Rejected as this phase's focus — it does not
   close an architectural gap or unlock new capability; Phase 13
   already proved the architecture generalizes across a ticker-count
   expansion, and a second round would repeat that already-answered
   question with more data-entry labor, not new design. Matches the
   standing instruction's own exclusion ("do not create phases just to
   increase count... justified only by closing a real architectural
   gap"). Belongs in the final audit's optional-enhancements list.
4. **Retrofit `portfolio_memory.cross_reference()` to accept an
   `as_of_date` and become point-in-time-correct**, rather than
   accepting its existing always-live semantics. Rejected — Phase 17's
   function is frozen, and `AlphaEngine.recommendations()` itself has
   no historical "as of a past date" query capability (only a
   current/live sleeve) — building that would mean new capability
   inside `alpha_engine.py`, outside this program's read-only boundary
   and its own scope. This phase instead disclosed the limitation
   explicitly (see Design, below) rather than silently working around
   it.

## Design

- New module `src/ngxrot/fre/company_portfolio_context.py`.
- `as_of(con, ticker, as_of_date) -> PortfolioAnnotatedDossier` —
  composes three calls, each to an existing frozen function, each
  called exactly once, none modified:
  - `company_research_dossier.build_dossier()` (Phase 11) — unchanged.
  - `watchlist.list_active(con, as_of_date=as_of_date)` (Phase 18),
    filtered in Python to this one ticker — reused specifically
    *instead of* `get_history_for_ticker()` because `list_active()` is
    the one function in `watchlist.py` that already implements
    point-in-time correctness (an entry only counts as active if
    `added_at <= as_of_date` and not yet removed as of that date);
    `get_history_for_ticker()` returns the entry's live
    `removed_at`/`removal_reason` regardless of `as_of_date`, which
    would leak future information (e.g., a removal that happens after
    the dossier's own `as_of_date`) into a supposedly point-in-time
    view. No new SQL is written — this phase reuses `list_active()`'s
    own already-correct WHERE clause verbatim.
  - `portfolio_memory.cross_reference(ticker)` (Phase 17) — unchanged.
    **Disclosed limitation, inherited, not introduced by this phase**:
    this call has no `as_of_date` parameter and always reflects the
    live/current sleeve, regardless of the dossier's own PIT cutoff.
    `PortfolioAnnotatedDossier` surfaces this honestly by carrying the
    note under a field that is documented as always-live, never
    presented as if it were point-in-time.
- `render(annotated) -> str` reuses Phase 11's `render_dossier()`
  verbatim for the existing three sections, then appends two new,
  equally template-only sections: "Watchlist Status" and "Portfolio
  Memory Cross-Reference" — no new reasoning, no synthesized
  conclusion across sections, no combined score/rating/recommendation.
- No write path anywhere; no import of `alpha_engine.py`/`registry.py`
  beyond what `portfolio_memory.py` itself already imports internally.

## Guardrails (mechanically verified, not just asserted)

- `PortfolioAnnotatedDossier` dataclass fields checked against
  `{score, rank, weight, strength, priority}` — none present.
- `inspect.signature(as_of)` checked against
  `{limit, top_n, sort_by, rank_by, threshold, tickers}` — none
  present (single-ticker only).
- AST inspection confirms no `INSERT`/`UPDATE`/`DELETE` string literal
  anywhere in the new module.
- Confirmed `company_research_dossier.py`, `watchlist.py`, and
  `portfolio_memory.py` are byte-for-byte unchanged (git diff empty)
  after this phase.
- Real-data correctness: tested against a real ticker with an active
  watchlist entry, a real ticker with none, and CAVERTON (in the live
  H-011 sleeve) vs. a ticker that is not — all four combinations of
  {on-watchlist, not-on-watchlist} x {in-sleeve, not-in-sleeve}
  produce the correct composed object.

## Expected outcome

A new, additive, read-only module and its test file; no schema
change; no modification to any of the three composed frozen modules;
the golden snapshot is unaffected. This closes the wiring gap Part 9
itself specified and that Phases 17/18 both explicitly deferred,
without introducing any new reasoning, scoring, or write path.
