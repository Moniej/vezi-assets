# FSI/FRE Final Architecture Audit — 2026-08-02 (Revision 2)

*Produced at the natural stopping point reached under the owner's
standing continuous-execution authorization (Phases 14-25, no
per-phase approval checkpoint). Supersedes Revision 1 (produced after
Phase 22), which stopped one real step short: the owner subsequently
authorized introducing NGX's own official sector classification as an
external reference-metadata source, which unblocked three more phases
(23-25) and closed Part 9 in full. This revision reviews the entire
platform again — FRE, FSI, LIM, Quant Engine, Knowledge Graph, Research
Engine, Validation Harness, Portfolio infrastructure, CLI tools, and
documentation — from the new state, not just what changed.*

## 1. Why this is a natural stopping point, not an arbitrary pause

The standing authorization names three stopping conditions. As with
Revision 1, all three are independently satisfied by different parts
of the remaining work:

- **No remaining meaningful architectural gap** exists in Part 9
  (Portfolio Reasoning) — the area this run's authorization has
  concentrated on. All five of its named Tier-1 capabilities (Watchlist,
  Screening, Portfolio memory, Qualitative correlation notes,
  Sector-coverage view) are now built, tested, and operator-reachable
  from the command line — a state that did not exist even in Revision
  1, since Sector-coverage view was still externally blocked at that
  point. There is no sixth Tier-1 capability to invent.
- **Every other candidate surfaced by this run's own full-platform
  reviews requires an external dependency, an owner decision, or a
  separately-scoped design judgment call not yet made**: the
  Evaluation Framework/FRE-10 (an analyst-authored gold set), a
  news-source reliability-tier registry (needs a real vetted list), a
  `cfo`/`cfi`/`cff`/`fcf`-based health flag (re-checked again this
  revision: still 0-1 computed trend conclusions per metric, unchanged
  since Revision 1), the LIM checkpoint/version decision, and — new
  since Revision 1 — mapping NGX's 13 sector headings onto `valuation_
  engine.py`'s own company-type taxonomy, and wiring `sector_ngx` into
  `company_intelligence.py`'s Industry Exposure field. Both of the
  latter two were investigated during Phase 23 and deliberately
  deferred as their own distinct judgment calls (see §3).
- **Every remaining "obviously valuable" idea beyond that would
  violate a standing guardrail**: activating `valuation_engine.py`'s
  formulas (Part 8) would produce a valuation output; building Part 9
  Tier 2 (ranking/sizing/risk/rotation) would violate the
  ≥2-validated-factor gate (unchanged, still 1/2); extending the
  Wave-3/H-0xx hypothesis track is categorically outside this
  program's scope.

## 2. What changed since Revision 1

Revision 1 (after Phase 22) reported Sector-coverage view as
externally blocked and Part 9 at "4 of 5." The owner then explicitly
authorized introducing NGX's own official sector classification as a
reference-metadata source (distinct from this platform's analytical/
investment-data boundary), which this run used to:

- **Phase 23**: populate `securities.sector_ngx` for 136/320 real
  securities (9 of 10 FSI tickers) from NGX's own official "Daily
  Official List (Equities)," with a full provenance trail
  (`sector_ngx_provenance`, new table) — and, along the way, disclosed
  that `docs/fre/10_dataset_strategy.md`'s own assumption (sector
  labels as a "free side effect" of existing filings) was wrong,
  verified against a real filing rather than assumed.
- **Phase 24**: built Sector-coverage view itself
  (`sector_coverage.coverage_by_sector()`) — the last of Part 9's five
  Tier-1 capabilities, now genuinely real rather than a permanent
  "once populated" placeholder.
- **Phase 25**: gave it a CLI, closing the last operational gap in
  Part 9.

Three stale "0/320 populated" claims (in `valuation_engine.py`,
`lim/audit.py`, `company_intelligence.py`, plus a config comment and
`HANDOFF.md`) were corrected for factual accuracy during Phase 23,
each verified to change no function's actual behavior — no gated
functionality was silently activated by the data becoming available.

## 3. Every implemented phase

**Pre-existing FRE track** (unchanged by this run): FRE-2 through
FRE-6 (Evidence Graph, Company Memory, reaction-check, Company Thesis
pilot, Valuation Engine architecture). Ten reasoning modes, the
14-step reasoning chain, the self-critique gate, confidence
propagation, restatement/historical-defect detection, terminology
mapping, period normalization.

**FSI track**, Phase 1 through 25:

| Phase | Deliverable | Tag |
|---|---|---|
| 1-13 | (see Revision 1 / `docs/fre/00_fre_master_index.md` for the full 1-13 narrative — unchanged) | `fsi-phase1..13-baseline-2026-08-0{1,2}` |
| 14 | Evidence-Based Screening | `fsi-phase14-baseline-2026-08-02` |
| 15 | Screening CLI | `fsi-phase15-baseline-2026-08-02` |
| 16 | Composition-Layer Ticker Coverage Fix | `fsi-phase16-baseline-2026-08-02` |
| 17 | Portfolio-Memory Cross-Reference | `fsi-phase17-baseline-2026-08-02` |
| 18 | Watchlist Persistence | `fsi-phase18-baseline-2026-08-02` |
| 19 | Qualitative Correlation Notes | `fsi-phase19-baseline-2026-08-02` |
| 20 | Portfolio-Context-Annotated Research Dossier | `fsi-phase20-baseline-2026-08-02` |
| 21 | Watchlist CLI (first write-capable operator tool) | `fsi-phase21-baseline-2026-08-02` |
| 22 | Portfolio-Context Dossier CLI | `fsi-phase22-baseline-2026-08-02` |
| 23 | Sector Classification Data (`sector_ngx`, 136/320) | `fsi-phase23-baseline-2026-08-02` |
| 24 | Sector-Coverage View | `fsi-phase24-baseline-2026-08-02` |
| 25 | Sector-Coverage View CLI | `fsi-phase25-baseline-2026-08-02` |

Phases 14-25 took Part 9 from zero built Tier-1 capabilities to all
five built, tested, wired together where Part 9 itself specifies, and
operable from the command line. Real defects/errors found and
disclosed along the way: a stale-ticker-list test regression (Phase
16); a factual error in this run's own Phase 17/18 documentation
(corrected in Phase 19); a wrong assumption in `docs/fre/
10_dataset_strategy.md` about sector data being a filing-extraction
side effect (corrected in Phase 23); three stale "0/320" claims
(corrected in Phase 23).

## 4. Remaining possible phases, categorized

### Can-implement-immediately
*None identified.* As in Revision 1, this remains the category whose
emptiness is the audit's central finding — everything below resolves
to one of the other four categories.

### Requires-owner-decision
- **Sector-to-company-type mapping** (`valuation_engine.
  classify_company_type()`) — NGX's 13 sector headings do not map
  1:1 onto `configs/valuation_method_eligibility.toml`'s own company
  types (e.g., "bank," "insurer," "general"); which NGX sectors count
  as which company type is an owner-judgment call, the same
  "owner-judged, never AI-inferred" discipline `company_type_
  overrides.toml` already states for individual tickers. Now
  genuinely buildable in principle (the data exists) but deliberately
  not decided by this run.
- **Wiring `sector_ngx` into `company_intelligence.py`'s Industry
  Exposure field** — needs new logic (`build_profile()` currently has
  none) and a decision about what "Industry Exposure" should actually
  mean given only a top-level sector label, not a full exposure model.
- **Evaluation Framework (FRE-10 / Part 11)** — needs an
  analyst-authored gold-standard label set.
- **News-source reliability-tier registry** — needs a real,
  owner-or-analyst-vetted list of Nigerian financial news outlets.
- **LIM Phase LIM-0 onward** — blocked on the exact Qwen3.x
  checkpoint/version.
- **Valuation Engine activation (Part 8)** — `compute()`'s formulas
  remain deliberately unimplemented; activating one is a valuation
  OUTPUT requiring a future, separate, explicit authorization.

### Requires-external-data-or-vendor
- **Coverage expansion beyond the current 10 FSI tickers** — 39 of 49
  originally-scoped candidate tickers remain hand-extraction labor,
  bounded by the same native-text-only, no-OCR, no-vendor-data
  discipline.
- **The remaining 184 securities' `sector_ngx`** — NGX's own Daily
  Official List (Phase 23's source) covers equities actively trading
  on the Main/Premium/REITCEF boards; the unmatched securities are
  bonds/ETFs/synthetic placeholders (out of scope by nature) or real
  tickers absent from that specific document (most plausibly
  delisted/suspended, unconfirmed) — closing this further would need
  either a historical DOL archive or a different NGX document, not
  yet sourced.
- **A working macro-conditioning factor** — belongs to the Wave-3
  quant research track, outside FRE/FSI's scope.

### Requires-new-research
- **Any second validated factor** for Portfolio Construction's own
  ≥2-factor gate — the Wave-3/H-0xx track's job, never to be
  shortcut by the FRE/FSI reasoning layer.
- **A `cfo`/`cfi`/`cff`/`fcf`-based financial-health flag** — checked
  again this revision (Phase 25's own review): still 0-1 computed
  trend conclusions per metric across all 10 tickers. Unchanged since
  Revision 1 — still too thin to build against honestly.

### Not-currently-justified
- **A CLI wrapper for `correlation_notes.py` (Phase 19)** — the
  underlying `entity_relationships` macro_exposure data is still 100%
  empty. Unchanged since Revision 1.
- **Extending `financial_health_flags.py`'s rules to check
  `ebit_margin`** — would modify a frozen module and reads as
  coverage-expansion-in-disguise, not a new analytical category.
- **A second round of coverage expansion for its own sake** —
  re-considered and rejected again this revision (Phase 25's own
  review), for the same reason every phase since 19 has given.

## 5. Remaining optional enhancements (non-blocking, low priority)

- Wiring Watchlist/Portfolio-memory/Sector-coverage status into other
  existing reports where relevant (only `company_portfolio_context.py`
  does this today, deliberately, for the reasons its own phase
  disclosed).
- Tightening `valuation_engine.py`'s `is_ready()` per-adapter checks to
  test each method's own specific `required_inputs` rather than the
  shared coarse check — a precision improvement, not a capability
  change.
- A CLI wrapper for `correlation_notes.py`, the moment real
  macro-exposure edges exist in the graph.

## 6. Remaining technical debt

- `valuation_engine.py`'s coarse `is_ready()` readiness check (§5).
- 39 of 49 originally-scoped tickers remain unextracted.
- A pre-existing `FIRSTHOLDCO`/`FirstHoldCo` duplicate-case ticker row
  in `securities`, found during Phase 23 and disclosed, not resolved —
  a data-quality question for a future phase.
- No single test threads a CLI-added watchlist entry through the
  CLI-rendered annotated dossier end-to-end (covered indirectly by
  separate tests of each half).

## 7. Remaining external dependencies (consolidated)

1. An analyst-authored evaluation gold-set — blocks Part 11/FRE-10.
2. A vetted news-source reliability-tier list — blocks `evidence_
   ranking.py`'s news-source trust tier from being anything but
   provisional.
3. The exact LIM checkpoint/version decision — blocks LIM-0 onward.
4. A second validated quant factor — blocks Portfolio Construction/
   Part 9 Tier 2 entirely; owned by the separate Wave-3/H-0xx track.
5. The remaining hand-extraction labor for 39 already-scoped filings.
6. An owner decision on the sector-to-company-type mapping, and a
   design decision on Industry Exposure logic — both newly
   buildable-in-principle since Phase 23, neither yet made.

## 8. Long-term roadmap recommendations

- **Do not build Part 8 (valuation) or Part 9 Tier 2 reactively** just
  because `sector_ngx` and financial-statement data now exist. Both
  remain correctly gated by explicit charter decisions requiring a
  separate, owner-approved architecture revision.
- **The sector-to-company-type mapping and Industry Exposure wiring**
  are the two most promising near-term candidates this revision
  surfaced — both are now data-ready for the first time, but each
  needs its own dedicated pre-registration (what taxonomy mapping is
  owner-judged correct; what "Industry Exposure" should actually
  state) rather than being rushed as a quick follow-on to Phase 23's
  data population.
- **When a second quant factor validates**, revisit Part 9 Tier 2 and
  Part 8 together as one deliberate, separately-authorized initiative.
- **Coverage expansion should be driven by a real need**, not run
  periodically for its own sake.
- **The next continuous-execution run, if one is authorized**, should
  re-check whether `cfo`/`cfi`/`cff`/`fcf` filing-period growth or new
  `entity_relationships` macro-exposure edges have since appeared
  before assuming the same stopping point still holds.

## 9. Summary

This continuous run (Phases 14-25) closed Part 9 (Portfolio Reasoning)
in full — all five Tier-1 capabilities built, tested, and operable
from the command line, including Sector-coverage view, which this
revision's own predecessor (after Phase 22) had reported as externally
blocked. The owner's explicit authorization to introduce NGX's own
official sector classification (Phase 23) was the specific unlock;
this run then built the capability it enabled (Phase 24) and its CLI
(Phase 25) before re-auditing the whole platform again. A fresh
full-platform review found no further buildable-now, guardrail-
compliant, genuinely-new capability that does not also require its own
separate owner decision or design judgment call — that is the basis
for stopping here, again, with the same honesty that produced Revision
1: this is a snapshot of 2026-08-02's real state, not a permanent
verdict.
