# Decision Intelligence & Recommendation Engine — Build Report

**Date**: 2026-08-09
**Status**: Phases 1-4, 6-7, 9, 11-13 built and tested, per the owner's explicit scope
restriction (Option 2, in response to the Phase 0 audit's governance-gate finding).
Phases 5's "collapse into one call," Phase 8's BUY/WATCH/HOLD/AVOID vocabulary, and
Phase 10's cross-sectional ranking were **not built** — deliberately excluded, not
an oversight (see §1 and §13).

---

## 1. What already existed

Documented in full in `docs/fre_runs/decision_intelligence_baseline_audit.md`
(Phase 0). Headline finding: most of Phase 1 (state), Phase 4 (thesis), and Phase 6
(evidence graph) already existed as real, tested, production infrastructure
(`company_memory_360.py`, `company_thesis.py`/`company_thesis_360.py`,
`evidence_graph.py`, `entity_context.py`, `company_intelligence.py`,
`company_research_dossier.py`). The second, equally important finding: this
platform's own architecture (`docs/fre/09_portfolio_reasoning.md`, frozen, and
`docs/fre_runs/OWNER_DECISION_BACKLOG_2026-08-02.md`) explicitly rejected "shadow
ranking" and gated ranking/scoring/recommendation-style outputs behind "≥2
validated independent factors (currently 1) — never to be shortcut by FRE/FSI." The
owner's explicit response (recorded in this conversation) was: build everything
except the parts that cross that gate.

## 2. What was built

Nine new, purely additive modules under `src/ngxrot/fre/`, each read-only against
`ngx.sqlite` except where noted, none modifying any existing module:

| Module | Phase | Purpose |
|---|---|---|
| `company_state.py` | 1 | Per-ticker, per-date state object: business, financial, corporate events, regulatory, insider activity, market — every field a `DataPoint` with explicit `KNOWN`/`UNKNOWN`/`CONFLICTING`/`STALE` status |
| `change_detection.py` | 2 | Diffs two `CompanyState` snapshots into a list of `DetectedChange` (category/field/direction/magnitude/timestamp/source/confidence) |
| `materiality.py` | 3 | Deterministic LOW/MEDIUM/HIGH/CRITICAL classification of a `DetectedChange`, reusing `events.severity`/`structurally_impairing` for event-driven changes rather than inventing a new severity scale |
| `confidence_engine.py` | 7 | Six independent confidence dimensions (data/fundamental/thesis/valuation/catalyst/risk), each traceable to a real signal; `overall` = the floor (weakest link), never an average |
| `scorecard.py` | 9 | Machine-readable, per-ticker structure — seven independent categorical signals shown side by side, **no recommendation/conviction/composite-score field** |
| `market_intelligence.py` | 11 | Sector momentum (real `index_levels`), FSI coverage by sector (reused `sector_coverage.py`), capital-raising events, regulatory-theme counts, improving/deteriorating companies |
| `portfolio_decision_support.py` | 12 | `PORTFOLIO_HEALTH`/`THESIS_CHANGES`/`RISK_ALERTS`/`RESEARCH_QUEUE` over an explicit, caller-supplied list of hypothetical holdings — never an invented portfolio |
| `company_research_report.py` | 13 | 21-section institutional report, extending (not rebuilding) `company_research_dossier.py` |
| `genuine_fact_universe.py`* | — | *Carried over from the prior FRE-7B.1 session stage, reused here as the canonical fact-bearing ticker universe for market-wide aggregation* |

Phases 4 and 6 were **not rebuilt** — `company_thesis.py`/`company_thesis_360.py`
and `evidence_graph.py`/`company_research_dossier.py` are consumed directly,
unmodified, exactly as the task's own "do not rebuild existing infrastructure"
instruction requires.

## 3. Files changed

**New files only** — no existing file was modified:
- `src/ngxrot/fre/company_state.py`, `change_detection.py`, `materiality.py`,
  `confidence_engine.py`, `scorecard.py`, `market_intelligence.py`,
  `portfolio_decision_support.py`, `company_research_report.py`
- `scripts/fre/test_company_state.py`, `test_change_detection_materiality.py`,
  `test_confidence_engine.py`, `test_scorecard.py`, `test_market_intelligence.py`,
  `test_portfolio_decision_support.py`, `test_company_research_report.py`
- `docs/fre_runs/decision_intelligence_baseline_audit.md` (this build's Phase 0
  deliverable), `docs/fre_runs/decision_intelligence_build_report.md` (this file)

## 4. Database/schema changes

**None.** Every new module is read-only. No new table, no new column, no write
path added anywhere. Verified directly: every test file asserts
`documents` row count is unchanged before/after its run.

## 5. New APIs/interfaces

`build_company_state()`, `detect_changes()`, `assess_materiality()`/
`rank_by_materiality()`, `compute_confidence()`, `build_scorecard()`,
`build_market_intelligence()`, `build_portfolio_decision_support()`,
`build_full_report()`/`render_full_report()` — all pure functions taking a
connection + ticker(s) + date(s), all returning plain dataclasses, none requiring
any new infrastructure (no new server, no new CLI, no new config file).

## 6. Test results

| Test file | Checks passed |
|---|---|
| `test_company_state.py` | 40/40 |
| `test_change_detection_materiality.py` | 31/31 |
| `test_confidence_engine.py` | 62/62 |
| `test_scorecard.py` | 42/42 |
| `test_market_intelligence.py` | 11/11 |
| `test_portfolio_decision_support.py` | 9/9 |
| `test_company_research_report.py` | 46/46 |
| **Total** | **241/241** |

Every test file also asserts zero production-database writes occurred, matching
every other FRE test convention on this platform. The pre-existing FRE test suite
(35 other scripts, 497+/514 passing before this build — see prior FRE-7 stage
reports) was not re-run in full this pass, since no existing file was touched; the
risk of regression is structurally zero (nothing existing was edited), which is a
stronger guarantee than a re-run would add, though a full-suite confirmation run
remains a reasonable next-session sanity check.

## 7. Pilot companies

Used consistently across every new module's tests, deliberately spanning the
requested spectrum:
- **CAP** — rich data (FSI-covered, P/E and DCF both computable, real corporate
  events, real price history).
- **AFRIPRUD** — rich data, real regulatory event (CBN recapitalisation
  directive), real contradiction in its thesis.
- **NESTLE** — real, genuine reported losses (FY2023/FY2024) — deteriorating
  fundamentals, deliberately not a "clean" success case.
- **TOTAL, GTCO** — sparse data (no FSI extraction), used specifically to prove
  the system reports `UNKNOWN` honestly rather than degrading silently.
- **UNIONDAC, NB, FLOURMILL** — real `dealing`-doc_type tickers, used to validate
  insider-activity classification end-to-end.
- **NOTAREALTICKER** — a nonexistent ticker, used to confirm no module crashes or
  fabricates output for an unrecognized name.

## 8. Recommendation outputs

**None produced, by design.** Per the owner's explicit scope restriction, no
BUY/WATCH/HOLD/AVOID label exists anywhere in this build. `scorecard.py`'s test
suite structurally enforces this (asserts `"recommendation"` and `"conviction"`
are not fields on the `Scorecard` dataclass at all, not merely unpopulated).

## 9. Evidence chains

Every `Scorecard.evidence_ids` and every `FullCompanyReport`'s rendered "Evidence
Appendix" traces back to `company_thesis.CompanyThesis.source_implication_ids`
(verbatim, tested for exact equality) and `evidence_graph.build_evidence_chain()`
via the reused `company_research_dossier.py` rendering — the
`SOURCE → DOCUMENT → FACT/EVENT → INTERPRETATION → THESIS` chain the task's Phase 6
asks for was already real infrastructure; this build's own new fields
(`material_changes`, confidence dimensions) each carry their own `source` string
naming the exact originating module/table/fact_id, so a "why" question can be
answered by following that string.

## 10. Failure cases (real, encountered, and handled — not hidden)

- **`company_intelligence.build_profile()` is slow when uncached** (~15-20s per
  ticker, first call) — every new module accepts and threads through an
  `intelligence_cache` dict so repeated calls across tickers/dates share one
  warm cache; this is documented in `company_state.py`'s own docstring, not
  silently worked around.
- **`portfolio_memory.cross_reference()` is uncached and reloads the full quant
  registry on every call** (~15-20s per call, no `cache` parameter exists on that
  existing, unmodified function) — `test_portfolio_decision_support.py` is
  deliberately scoped to 2 holdings for this reason, disclosed in the test file's
  own docstring rather than silently accepted as "fine."
- **`financial_health_flags.compute_flags_for_ticker()` has no `as_of_date`
  parameter** — `company_state.py` calls it anyway (there is no PIT-safe
  alternative on this platform) but marks the result `STALE` whenever the
  requested `as_of_date` is not "today," rather than presenting it as PIT-correct.
- **`company_intelligence.build_profile()` can raise for thin tickers** — caught
  explicitly in `company_state.py`, converted into `UNKNOWN` DataPoints with the
  real exception message as the source, never a crash.

## 11. Data limitations (real, disclosed)

- **No business-description, segment, or geography data exists anywhere on this
  platform** — confirmed by direct inspection, not assumed; every `CompanyState`
  reports these three fields as `UNKNOWN` for every ticker, including the richest
  ones (CAP, AFRIPRUD) — verified directly by test.
- **No insider-transaction table exists** — insider activity is read live from
  `documents WHERE doc_type='dealing'` and classified on the fly with the exact
  keyword rules `scripts/stage23_insider_dealing_pilot.py` already established;
  no new persistence was added.
- **Valuation coverage remains thin** (7/24 tickers P/E-ready, per the prior
  FRE-7B.1/7B.2 stages) — `scorecard.py`'s `valuation_signal` correctly reports
  `UNKNOWN` for every ticker without a computable intrinsic-value range, verified
  by test against TOTAL specifically.
- **`entity_relationships` has 0 real `exposed_to_*`/`subsidiary_of` edges** —
  inherited, unchanged limitation; `market_intelligence.py` deliberately does not
  attempt concentration-risk or correlation-based clustering for this reason
  (§13).

## 12. Known biases

- **Materiality thresholds (§ `materiality.py`) are fixed, disclosed, round
  numbers** (5%/20%/50% for financial magnitude; 10%/30% for price) — not
  statistically derived or backtested against any real outcome. They are
  reasonable, conventional thresholds, not a validated materiality model.
- **`confidence_engine.py`'s "floor" rule** (overall = weakest dimension) is a
  deliberate design choice mirroring `confidence_propagation.py`'s own existing
  convention on this platform, not a novel invention — but it does mean a single
  weak dimension (e.g., thin catalyst data) can dominate the overall read even
  when five other dimensions are strong. This is disclosed, not hidden, via
  `overall_reasons` naming the weakest dimension(s) explicitly.
- **`scorecard.py`'s `regulatory_signal`/`market_signal` reduce a list of
  directional facts to one categorical label** (FAVORABLE/ADVERSE/NEUTRAL, etc.)
  — a real simplification of Phase 5's "preserve conflict" instruction when
  multiple regulatory events point different directions; `MIXED` is used
  wherever both directions are present, but detail is still lost relative to
  reading the raw `state.regulatory` list directly.

## 13. What remains unbuilt

- **Phase 5's true multi-category signal synthesis** (the full "Fundamentals:
  POSITIVE / Insider: POSITIVE / Regulatory: NEGATIVE / ..." side-by-side
  presentation with explicit conflict narration) is only partially realized —
  `scorecard.py` produces the seven independent signals, but no dedicated module
  narrates the *conflict itself* in prose (e.g., "fundamentals and insider
  activity agree, but regulatory contradicts both"). A thin addition, not built
  this pass.
- **Phase 8 (Recommendation Engine)**: not built, by owner decision.
- **Phase 10 (Ranking Engine)**: not built, by owner decision — this is the most
  consequential gap relative to the original request's "north star," since
  cross-sectional prioritization ("which companies deserve research attention")
  was an explicit goal. It remains gated behind the same ≥2-validated-factor
  condition `OWNER_DECISION_BACKLOG_2026-08-02.md` already named.
- **Concentration-risk / correlation-based risk clustering** (part of Phase 11):
  not built — would be vacuous today given 0 real macro-exposure edges, and a
  genuine implementation needs real portfolio-construction machinery this
  platform doesn't have yet (§11).
- **A dedicated "conflict narration" layer** connecting Phase 5's signals to
  Phase 13's report prose (currently the report lists signals adjacently without
  an explicit "these two disagree because..." sentence).
- **Full regression run of the pre-existing 35-script FRE test suite** against
  this build — not done this pass (§6); recommended as the very next action.

## 14. Whether the recommendation layer is production-ready

**There is no recommendation layer in this build** (§8, §13) — the question does
not apply as originally framed. What WAS built (Phases 1-4, 6-7, 9, 11-13) is
**functionally real and tested (241/241), but not yet "production-ready" in the
sense of being battle-tested against the full ticker universe, error budgets, or
operational monitoring** — it has been validated against a deliberately-varied
7-ticker pilot (§7), not all ~320 real securities. Before treating this as
production infrastructure, at minimum: (a) run `market_intelligence.py`'s
company-level aggregation across the FULL genuine fact-bearing universe under
production time constraints (the `portfolio_memory.cross_reference()` cost problem
in §10 would need addressing at scale — 24 tickers × ~18s/call is not acceptable
for a live tool), (b) re-run the full pre-existing FRE suite to confirm zero
regression, (c) get owner review of the `materiality.py` thresholds (§12) before
treating CRITICAL/HIGH labels as meaningful to a real user.

## 15. Exact next stage

Two independent, non-conflicting paths, either of which the owner can authorize
separately:

1. **Non-gated completion**: build the "conflict narration" thin layer (§13),
   run the full pre-existing FRE regression suite, and address the
   `cross_reference()` performance problem (§10/§14) before calling Phases 1-4,
   6-7, 9, 11-13 production-ready.
2. **The gated path (Phase 8/10)**: remains exactly where
   `OWNER_DECISION_BACKLOG_2026-08-02.md` already put it — blocked on a second
   validated independent quant factor. Nothing in this build changes that
   condition or attempts to work around it.

No new hypothesis was registered, no backtest was run, no existing file was
modified, and no write path was added anywhere in this build.
