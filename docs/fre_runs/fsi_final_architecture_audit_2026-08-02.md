# FSI/FRE Final Architecture Audit — 2026-08-02

*Produced at the natural stopping point reached under the owner's
standing continuous-execution authorization (Phases 14-22, no
per-phase approval checkpoint). This audit is the deliverable that
authorization requires once a stopping condition is objectively met.
It reviews the entire platform — FRE, FSI, LIM, Quant Engine, Knowledge
Graph, Research Engine, Validation Harness, Portfolio infrastructure,
CLI tools, and documentation — not just the FSI track this run
extended.*

## 1. Why this is a natural stopping point, not an arbitrary pause

The standing authorization names three stopping conditions. **All
three are independently satisfied by different parts of the remaining
work**, which is itself the signal that this is a real, not a
convenient, stopping point:

- **No remaining meaningful architectural gap** exists in the one area
  this run's authorization actually covers — Part 9 (Portfolio
  Reasoning) Tier 1. All five of its named capabilities are now either
  built-and-operable (Watchlist, Screening, Portfolio memory,
  Qualitative correlation notes — Phases 14/15/17/18/19/20/21/22) or
  genuinely blocked (Sector-coverage view). There is no sixth Tier-1
  capability to invent, and inventing one that Part 9 does not itself
  specify would be scope creep the authorization explicitly forbids
  ("do not create phases just to increase count").
- **Every other candidate surfaced by this run's own full-platform
  reviews requires an external dependency unresolvable internally**:
  Sector-coverage view (`securities.sector_ngx` 0/320 populated),
  the Evaluation Framework/FRE-10 (an analyst-authored gold set), a
  new financial-health flag on `cfo`/`cfi`/`cff`/`fcf` (real data
  checked directly this run: 0-1 computed trend conclusions exist
  today, too thin to build against honestly), and a news-source
  reliability-tier registry in `evidence_ranking.py` (requires
  real-world editorial judgment about specific Nigerian news outlets —
  a domain-research task, not a code gap).
- **Every remaining "obviously valuable" idea beyond that would
  violate a standing guardrail**: implementing an actual formula in
  `valuation_engine.py` (Part 8) would produce a valuation output —
  explicitly forbidden without a future, separate authorization;
  building Part 9 Tier 2 (ranking/sizing/risk/rotation) would violate
  the ≥2-validated-factor gate (`docs/PLATFORM_ARCHITECTURE.md`,
  unchanged, still 1/2); extending the Wave-3/H-0xx hypothesis
  research track would be alpha-generation work, categorically outside
  what "FRE/FSI architectural completion" authorizes.

No phase proposal satisfying all of "closes a real gap," "buildable
internally today," and "does not violate a guardrail" was found after
a genuine review (documented in Phase 22's own pre-registration and
this audit's §3-4 below). That absence — not fatigue, not an arbitrary
phase-count ceiling — is why this run stops here.

## 2. Every implemented phase

**Pre-existing FRE track** (built before this continuous run; unchanged
by it): FRE-2 (Evidence Graph), FRE-3 (Company Memory), FRE-4
(reaction-check), FRE-5 (Company Thesis, pilot case study), FRE-6
(Valuation Engine architecture — scaffolding + readiness-gating only,
deliberately not implemented). Ten reasoning modes (Part 4), the
14-step reasoning chain, the self-critique gate, confidence
propagation, restatement/historical-defect detection, terminology
mapping, and period normalization were all already real and tested.

**FSI track** (this session and its predecessor extended it from
Phase 1 through Phase 22):

| Phase | Deliverable | Tag |
|---|---|---|
| 1 | Pilot revenue/net_profit extraction, 5 tickers, 30 facts | `fsi-phase1-baseline-2026-08-01` |
| 2 | Balance sheet/cash flow/EBITDA/EBIT extraction, 106 facts total | `fsi-phase2-baseline-2026-08-01` |
| 3 | Financial reasoning (ratios/trends/flags), 177 conclusions | `fsi-phase3-baseline-2026-08-01` |
| 4 | Point-in-Time Financial Reasoning Memory | `fsi-phase4-baseline-2026-08-01` |
| 5 | Regression & Consistency Validation Harness | `fsi-phase5-baseline-2026-08-01` |
| 6 | Unified PIT Company Memory (`CompanyMemory360`) | `fsi-phase6-baseline-2026-08-01` |
| 7 | Deterministic Financial Reasoning Research Report | `fsi-phase7-baseline-2026-08-02` |
| 8 | Financial-Reasoning-Informed Investment Thesis | `fsi-phase8-baseline-2026-08-02` |
| 9 | Knowledge Graph Completeness (entities + renamed_from edges) | `fsi-phase9-baseline-2026-08-02` |
| 10 | Knowledge Graph Context Integration (`entity_context.py`) | `fsi-phase10-baseline-2026-08-02` |
| 11 | Complete Institutional Research Dossier | `fsi-phase11-baseline-2026-08-02` |
| 12 | Operational Research Dossier Generation (first CLI) | `fsi-phase12-baseline-2026-08-02` |
| 13 | Coverage Expansion, 5→10 tickers | `fsi-phase13-baseline-2026-08-02` |
| 14 | Evidence-Based Screening | `fsi-phase14-baseline-2026-08-02` |
| 15 | Screening CLI | `fsi-phase15-baseline-2026-08-02` |
| 16 | Composition-Layer Ticker Coverage Fix | `fsi-phase16-baseline-2026-08-02` |
| 17 | Portfolio-Memory Cross-Reference | `fsi-phase17-baseline-2026-08-02` |
| 18 | Watchlist Persistence | `fsi-phase18-baseline-2026-08-02` |
| 19 | Qualitative Correlation Notes | `fsi-phase19-baseline-2026-08-02` |
| 20 | Portfolio-Context-Annotated Research Dossier | `fsi-phase20-baseline-2026-08-02` |
| 21 | Watchlist CLI (first write-capable operator tool) | `fsi-phase21-baseline-2026-08-02` |
| 22 | Portfolio-Context Dossier CLI | `fsi-phase22-baseline-2026-08-02` |

Phases 14-22 (this continuous run) closed Part 9's entire Tier 1 —
four of five capabilities built, tested, wired together, and made
operable from the command line — plus fixed one real, disclosed
regression (Phase 16: six test files had silently stopped covering
Phase 13's five new tickers) and corrected one factual error in the
run's own documentation (Phase 19: Phase 17/18 had understated Part
9's Tier 1 as three items instead of five).

## 3. Remaining possible phases, categorized

### Can-implement-immediately
*None identified.* Every idea that passed the "closes a real gap" and
"doesn't violate a guardrail" filters this run applied is listed
below under a blocked category instead. This is the category whose
emptiness is this audit's central finding.

### Requires-owner-decision
- **Sector-coverage view CLI/logic** — trivial to build the moment
  `securities.sector_ngx` is populated (Part 9's own design is
  already written), but the population itself is a data-acquisition
  decision, not a code decision.
- **Evaluation Framework (FRE-10 / Part 11)** — needs an
  analyst-authored gold-standard label set; no amount of internal
  engineering substitutes for that judgment call.
- **News-source reliability-tier registry** (`evidence_ranking.py`,
  `TrustAssignment` for `source_type="news"`) — needs a real,
  owner-or-analyst-vetted list of Nigerian financial news outlets and
  their credibility tiers; fabricating one internally would be
  exactly the kind of invented-authority claim this platform's
  discipline forbids.
- **LIM Phase LIM-0 onward** — blocked on the exact Qwen3.x
  checkpoint/version to build against (`docs/LIM_ARCHITECTURE.md`
  §"Open questions," unchanged by this run).
- **Valuation Engine activation (Part 8)** — `compute()`'s
  formulas remain deliberately `NotImplementedError`. Financial-
  statement data now exists (137 facts, 10 tickers) where none did
  when Part 8 was written, so `is_ready()` correctly reports several
  methods as data-ready — but activating an actual formula is a
  valuation OUTPUT, explicitly named in this run's own guardrails as
  requiring a **future, separate, explicit architecture-revision
  authorization**, not something this run's mandate covers.

### Requires-external-data-or-vendor
- **Sector-coverage view's own underlying data**
  (`securities.sector_ngx`, 0/320 populated) — same root blocker as
  above, listed here for the data dependency itself rather than the
  decision to acquire it.
- **Coverage expansion beyond the current 10 tickers** — 39 of the
  original 49 already-scoped candidate tickers (349 candidate
  documents, Phase 1's own pool) remain hand-extraction labor, not a
  vendor gap per se, but bounded by the same native-text-only,
  no-OCR, no-vendor-data discipline every prior FSI phase has held to;
  listed here because further expansion's *ceiling* is the size of
  the free, hand-verifiable document pool, which is itself fixed
  external supply.
- **A working macro-conditioning factor** (referenced in
  `company_intelligence.py`'s `UNAVAILABLE_FIELDS`: H-004/H-005 both
  rejected) — outside FRE/FSI's scope entirely; belongs to the Wave-3
  quant research track.

### Requires-new-research
- **Any second validated factor** for Portfolio Construction's own
  ≥2-factor gate (`docs/PLATFORM_ARCHITECTURE.md`) — this is the
  Wave-3/H-0xx hypothesis-testing track's job, categorically separate
  from and never to be shortcut by the FRE/FSI reasoning layer per
  this run's own guardrails ("never invent alpha").
- **A `cfo`/`cfi`/`cff`/`fcf`-based financial-health flag** —
  architecturally straightforward (mirrors Phase 3's existing rule
  pattern exactly) but checked against real data this run: each
  metric has 0-1 computed trend conclusions across all 10 tickers
  today. Not "new research" in the scientific sense, but needs more
  real filing periods to exist before it would be more than a
  permanently-`insufficient_data` stub — effectively gated by the
  same document/labor supply as coverage expansion above.

### Not-currently-justified
- **A CLI wrapper for `correlation_notes.py` (Phase 19)** — the
  underlying data (`entity_relationships` macro_exposure edges) is
  100% empty on the real database today; a CLI for a function that
  can only ever say "no shared exposure known" has no real
  operational value yet. Revisit once macro-exposure edges exist in
  the graph — not "unbuildable," just not worth the file yet.
- **Extending `financial_health_flags.py`'s existing rules to also
  check `ebit_margin`** — real data exists (10 computed trend
  conclusions) but this widens an existing rule's coverage rather
  than adding a new analytical category, and would require modifying
  a frozen module. Not wrong to eventually consider, but doesn't meet
  this run's "genuinely new capability" bar today.
- **A second round of coverage expansion for its own sake** — this
  run's own repeated review (Phases 19, 20, 21, 22 each re-considered
  and rejected it) found no architectural gap it closes; Phase 13
  already proved the architecture generalizes across a ticker-count
  expansion. Purely a data-entry-labor exercise, correctly excluded
  by the standing authorization's own "don't create phases just to
  increase count" clause.

## 4. Remaining optional enhancements (non-blocking, low priority)

- A CLI wrapper mirroring Phase 15/21's pattern for any future
  read-only composition module, as a matter of course, the moment one
  is built (already the established norm for every phase this run
  produced).
- Wiring Watchlist/Portfolio-memory status into other existing
  reports where relevant (only `company_research_dossier.py`'s
  annotated variant does this today; `financial_reasoning_report.py`
  itself deliberately does not, and should not, since Part 9 content
  does not belong inside Part 5/6's own report).
- Tightening `valuation_engine.py`'s `is_ready()` per-adapter checks
  to test each method's own specific `required_inputs` (e.g., EV/EBITDA
  checking for real EBITDA facts specifically) rather than the shared
  coarse "any financial-statement fact exists" check — a precision
  improvement, not a capability change (`compute()` still refuses
  unconditionally either way), so it does not meet the "genuinely new
  capability" bar for its own phase, but is a reasonable future
  cleanup item.

## 5. Remaining technical debt

- **`valuation_engine.py`'s coarse readiness check** (§4, above) is
  the one disclosed precision gap in an otherwise-honest module — it
  never produces a wrong OUTPUT (compute() still always refuses), but
  its `ReadinessResult.reason` text is coarser than it could be.
- **39 of 49 originally-scoped tickers remain unextracted** — not
  urgent (the architecture has already been proven to generalize,
  Phase 13), but the real ceiling on how far Screening/Watchlist/
  Correlation-notes coverage can go until more filings are
  hand-extracted.
- **No test file yet exercises `manage_watchlist.py`'s `add`/`remove`
  against a ticker that also appears in `company_portfolio_context.py`
  end-to-end via the CLI** — covered indirectly (Phase 20/22's own
  tests use a scratch watchlist entry; Phase 21's own tests exercise
  the CLI directly) but no single test threads a CLI-added watchlist
  entry through the CLI-rendered annotated dossier. Low priority: the
  underlying composition (`list_active()` called by
  `company_portfolio_context.as_of()`) is the same function Phase 21's
  own tests already exercise via the CLI.

## 6. Remaining external dependencies (consolidated)

1. `securities.sector_ngx` population (0/320) — blocks Sector-coverage
   view (Part 9) and sector-based classification generally (Part 1/2's
   shared, long-disclosed blocker).
2. An analyst-authored evaluation gold-set — blocks Part 11/FRE-10.
3. A vetted news-source reliability-tier list — blocks
   `evidence_ranking.py`'s news-source trust tier from being anything
   but provisional.
4. The exact LIM checkpoint/version decision — blocks LIM-0 onward.
5. A second validated quant factor — blocks Portfolio Construction/
   Part 9 Tier 2 entirely; owned by the separate Wave-3/H-0xx research
   track, not by this program.
6. The remaining hand-extraction labor for 39 already-scoped, already-
   available candidate filings — not vendor-blocked, just
   labor-bounded, and correctly not rushed by fabricating shortcuts
   (no OCR, no vendor data, per this platform's standing discipline).

## 7. Long-term roadmap recommendations

- **Do not build Part 8 (valuation) or Part 9 Tier 2 (ranking/sizing/
  risk/rotation) reactively** just because data now technically
  supports `is_ready()`=True for some valuation methods. Both remain
  correctly gated by explicit, deliberate charter decisions
  (`docs/PLATFORM_ARCHITECTURE.md`, this run's own guardrails) that
  require a **separate, explicit, owner-approved architecture
  revision** — not an inference from "the data exists now."
- **When `securities.sector_ngx` is eventually populated**, Sector-
  coverage view can be built directly from Part 9's own already-
  written design (`docs/fre/09_portfolio_reasoning.md` lines 63-67) —
  no new design work needed, just execution, following this run's own
  established phase lifecycle.
- **When a second quant factor validates**, revisit Part 9 Tier 2 and
  Part 8 together as one deliberate, separately-authorized initiative
  — they were designed together and share the same precondition.
- **Coverage expansion should be driven by a real need** (a specific
  research question, a specific screening/watchlist use case that
  needs a ticker not yet covered), not run as a periodic, undirected
  "add more tickers" phase — this run's own repeated review found no
  standing architectural justification for expansion as an end in
  itself.
- **The next continuous-execution run, if one is authorized**, should
  start by re-checking whether any of §3's `Requires-external-data-or-
  vendor`/`Requires-new-research` items have since been resolved
  (particularly `sector_ngx` population and real filing-period growth
  for `cfo`/`cfi`/`cff`/`fcf`) before assuming the same stopping point
  still holds — this audit is a snapshot of 2026-08-02's real data
  state, not a permanent verdict.

## 8. Summary

This continuous run (Phases 14-22) took Part 9 (Portfolio Reasoning)
from zero built Tier-1 capabilities to four of five built, tested,
wired together, and operable from the command line — the fifth
(Sector-coverage view) is the one genuinely externally-blocked item.
Two real defects were found and fixed along the way (a stale-ticker-
list test regression in Phase 16; a factual error in this run's own
Phase 17/18 documentation, corrected in Phase 19), consistent with
this platform's standing discipline of disclosing rather than hiding
its own mistakes. A full-platform review conducted across Phases 19-22
(not just within Part 9) found no further buildable-now, guardrail-
compliant, genuinely-new capability — every remaining idea resolves to
an external dependency, an owner decision, or a guardrail this run is
not authorized to cross. That is the basis for stopping here.
