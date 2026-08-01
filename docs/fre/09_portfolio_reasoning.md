# FRE Part 9 — Portfolio Reasoning

*Design only. Everything in this document respects the existing gates in
`docs/PLATFORM_ARCHITECTURE.md` (Ranking Engine, Portfolio Construction,
Risk Engine, Performance Attribution) unchanged — this document does not
lower, reinterpret, or work around any of them. See
`docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Design ranking, position sizing, conviction, risk, sector exposure,
correlation, rotation, watchlists, screening, portfolio monitoring, and
portfolio memory — the owner's exact list — as FRE capabilities, while
drawing an explicit, load-bearing line between the pieces that are
**advisory/research-only and buildable today** and the pieces that **remain
correctly gated** behind the platform's existing, unchanged preconditions.

## Rationale — most of this list is gated by design, and that is correct

`docs/PLATFORM_ARCHITECTURE.md` states the preconditions plainly: Ranking
Engine requires "a return MODEL, which requires validated factors with
known expected-alpha intervals... Ranking on zero factors is
indistinguishable from ranking on noise"; Portfolio Construction requires
"≥2 validated independent factors — independence is exactly what the
'Expected Interaction with Existing Factors' prereg section exists to
establish in advance." **Today exactly one factor is confirmed** (H-011,
Size) — the platform is one factor short of Portfolio Construction's own
gate. This document does not treat that as an obstacle to design around; it
treats it as the correct, evidence-driven state, and designs the FRE's
portfolio-reasoning capabilities to be **honest about which side of that
gate each capability sits on** — the same discipline the charter's
"No Action is a first-class output" principle already requires of the
Alpha Engine itself, applied here to the *research layer that feeds it*.

## The split: two capability tiers

| Tier | Capabilities | Gate status | Why |
|---|---|---|---|
| **Tier 1 — Research/advisory, buildable now** | Watchlists, Screening, Sector-coverage view, Qualitative correlation notes, Portfolio memory (read-only cross-reference) | **Not gated** — these never claim an expected return or propose a position | Pure organization/filtering of already-produced, already-governed research (Company Intelligence, `CompanyThesis` from Part 7) — no new alpha claim, no portfolio action |
| **Tier 2 — Prescriptive** | Ranking by expected risk-adjusted return, Position sizing, Conviction-weighted allocation, Portfolio-level risk/correlation modeling, Rotation execution | **Gated, unchanged** | Directly the Ranking Engine / Portfolio Construction / Risk Engine preconditions from `docs/PLATFORM_ARCHITECTURE.md` — this document proposes no bypass |

## Tier 1 — designed in full

**Watchlist.** A `WatchlistEntry(ticker, added_at, rationale, source_thesis_ref,
review_cadence, entry_criteria)` — `rationale`/`source_thesis_ref` point
directly at a Part 7 `CompanyThesis` snapshot (never a bare ticker with no
evidence trail). `entry_criteria` states, in advance, **what would need to
be true for this to become portfolio-relevant** (e.g., "if Size or a future
factor validates on this segment") — this is deliberately the FRE's
version of pre-registration applied to watchlist membership: the criteria
are written down before they're met, not rationalized after.

**Screening.** A `ScreeningQuery` over existing, already-governed fields
(`CompanyThesis.financial_quality`, `.growth_quality`,
`.capital_allocation_quality`, Part 2's graph, Part 5's Company Memory) —
e.g., "flag companies whose `capital_allocation_quality` degraded across
the last two `CompanyThesis` snapshots AND whose debt-related
`impact_assessments` turned negative." This is descriptive filtering over
already-produced research, structurally identical to a SQL `WHERE` clause —
it never computes or implies an expected return, so it does not trip the
Ranking Engine's precondition.

**Sector-coverage view.** An aggregation of the current watchlist/research
pipeline **by sector** (once `securities.sector_ngx` is populated, Part 1/2's
shared blocker) — answers "how balanced is our research coverage across
sectors," a research-management question, not a portfolio-exposure
question (no positions exist for this to measure exposure *of*).

**Qualitative correlation notes.** Explicitly **not** a computed
correlation coefficient — that would be a quantitative claim requiring the
same statistical rigor as any other hypothesis on this platform, and
computing one informally inside the reasoning engine would bypass the
research engine's own methodology. Instead, a `CorrelationNote` states an
**evidenced shared-exposure reason** two companies might move together
(e.g., "both companies carry an `exposed_to_commodity` edge to Brent crude
per Part 2's graph") — a narrative hypothesis-generation surface, not a
number. If a real correlation estimate is wanted, it is computed by the
existing quant engine's own statistical machinery (read-only reuse,
one-directional, same boundary as everywhere else in this program), never
invented inside the FRE.

**Portfolio memory (read-only cross-reference).** The one Tier-1 capability
that touches something real: `alpha_engine.py`'s `H011SizeAdapter` already
produces 20 live, provenance-backed recommendations today (`HANDOFF.md`).
A `PortfolioMemory.cross_reference(ticker)` function may **read** (never
write) the current live sleeve and attach a note to a `CompanyThesis` or
watchlist entry ("this ticker is currently in the live Size sleeve, per
`H011SizeAdapter`, as of [date]") — purely informational, so a researcher
knows their qualitative thesis concerns a name the fund is actually
exposed to. This is the identical one-directional read pattern
`company_intelligence.build_profile()` already established for
`factor_exposures` — no new boundary crossing, no write path back into
`alpha_engine.py` or the registry.

## Tier 2 — explicitly designed to NOT execute, with a stated unlock condition

| Capability | What it would require | Unlock condition (unchanged from existing docs) |
|---|---|---|
| **Ranking by expected risk-adjusted return** | A return model built from validated factors with walk-forward expected-alpha intervals | `docs/PLATFORM_ARCHITECTURE.md`'s Ranking Engine precondition — more than the current 1 validated factor, per that document's own "factors" (plural) framing |
| **Position sizing / conviction-weighted allocation** | Portfolio Construction's capital-allocation layer | ≥2 validated independent factors (charter, unchanged) |
| **Portfolio-level risk/correlation modeling** | A real portfolio to measure risk *of* | Same ≥2-factor gate — `docs/PLATFORM_ARCHITECTURE.md`'s Risk Engine module is explicitly "GATED behind module 6 [Portfolio Construction] — there is no portfolio to measure risk on yet" |
| **Rotation execution** | The above, plus an execution layer (not designed anywhere in this program) | Same gate, plus a not-yet-scoped execution architecture |

This document's contribution for Tier 2 is deliberately limited to
**naming the interface each capability will need to consume once
unlocked** — e.g., Ranking will need `CompanyThesis.confidence` and Part
7's `validated_factor_exposure` field as inputs, so Part 7's design already
shapes correctly for this future consumer — without building any of the
ranking/sizing logic itself. This mirrors exactly how `docs/LIM_ARCHITECTURE.md`
named `LocalLIMProvider`'s eventual role without implementing it before
Phase LIM-0 was approved.

## Alternatives considered

1. **Build a "shadow ranking" that computes scores but is labeled
   experimental/non-live.** Rejected — a shadow ranking is still a ranking;
   producing a scored, ordered list creates exactly the same
   "indistinguishable from ranking on noise" problem
   `docs/PLATFORM_ARCHITECTURE.md` already names, regardless of a disclaimer
   label. Screening (an unordered filter) is the correct Tier-1 substitute:
   it can say "these five names meet criteria X" without ever implying
   criteria X predicts return.
2. **Compute qualitative correlation as a numeric score derived from shared
   ontology edges (e.g., count of shared exposures).** Rejected as a
   plausible-looking but ungrounded pseudo-statistic — a shared-exposure
   *count* is not a correlation, and presenting it with numeric precision
   would misrepresent its actual evidentiary weight (the same false
   -precision risk Part 8 raised for valuation triangulation, recurring
   here in a different form).
3. **Let Portfolio Memory write annotations back onto `alpha_engine.py`'s
   sleeve.** Rejected — a write path from the qualitative reasoning layer
   into the quantitative decision layer is the single hard boundary this
   entire platform has maintained since Phase A; even an "annotation-only"
   write would be a crack in that boundary and is refused categorically.

## Trade-offs

- Tier 1's discipline (screening/watchlisting only, no ranking) is less
  immediately useful to a portfolio manager than a ranked list would be —
  a deliberate, charter-mandated trade of usefulness for honesty, matching
  the charter's own "No Action is a first-class output" principle applied
  one layer earlier (research recommendations, not just trades).
- Qualitative correlation notes are weaker evidence than a computed
  statistic, by design — their value is as a **hypothesis-generation
  surface** (feeding the Discovery scanner, Part 12), not as a
  decision input in their own right.

## Risks

- **Watchlist creep into de facto ranking** — if watchlist entries are
  ever sorted or displayed in a way that implies an ordering by expected
  quality, that presentation itself becomes an informal ranking, defeating
  the Tier 1/Tier 2 distinction through UI rather than through logic. Flag
  for Part 11's evaluation framework: any watchlist display must be
  reviewed for implied ordering, not just for its underlying data model.
- **Portfolio Memory's read boundary being loosened over time** under
  convenience pressure ("it would be easier to just let the researcher
  flag a position change directly") — the same governance-erosion risk
  named in Part 8, recurring here; the enforcement is procedural (code
  review / import-graph lint, architecture doc §9) as much as architectural.

## Future extensions

- Once the Ranking Engine's own precondition is met (owner-directed,
  outside this document's scope to predict), Tier 2's named interfaces
  become buildable without re-deriving the FRE's qualitative inputs — Part
  7's `CompanyThesis` and this document's Tier-1 objects were shaped with
  that future consumer in mind from the start.
- A "coverage-gap-driven acquisition priority" report (which sector-coverage
  gaps, per Tier 1's view, most block a *future* ranking capability) —
  directly reuses the charter's own "priority test: does this increase the
  probability of the next validated factor" framing, applied to research
  coverage rather than data acquisition.

## Dependencies

- Part 7 (`CompanyThesis`, `validated_factor_exposure`). Part 2 (sector/
  exposure graph). Part 5 (Company Memory, for the sector-coverage view
  and staleness checks). `alpha_engine.py`'s `H011SizeAdapter` and
  `data/registry.sqlite` (read-only). `docs/FACTOR_REGISTRY.md`,
  `docs/PLATFORM_ARCHITECTURE.md` (the gates this document defers to,
  unchanged). `securities.sector_ngx` population (Tier 1's sector-coverage
  view specifically).
