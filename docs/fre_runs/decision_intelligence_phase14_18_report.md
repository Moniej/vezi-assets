# Decision Intelligence — Phases 14-18 Build Report

**Date**: 2026-08-09
**Status**: All five requested phases (14 Economic Company Intelligence, 15
Information Fusion, 16 Institutional Research Dossier, 17 Research Question
Engine, 18 Continuous Intelligence) built and tested. No governance gate was
hit requiring a stop — every blocked capability named in this task's own
Governance section (quantitative recommendation engine, BUY/SELL/AVOID
vocabulary, cross-sectional ranking, conviction weighting, automatic
allocation, FRE-7 activation) was correctly left untouched, and none of the
new work required crossing any of those lines.

---

## 1. Every stage attempted

All five phases were attempted and completed. No phase was skipped, no phase
was left partially built without disclosure (see §11 for the two features
that were explicitly scoped narrower than the literal request, and why).

## 2. Capabilities built

| Module | Phase | Purpose |
|---|---|---|
| `company_economic_profile.py` | 14 | 15-field economic company profile, each field `KNOWN`/`UNKNOWN` with real provenance |
| `company_intelligence_bundle.py` | 15 | Single fusion object wiring state→changes→materiality→confidence→portfolio-memory together; `what_is_happening()` renders a deterministic, evidence-cited narrative |
| `company_research_report.py` (rebuilt on the bundle) | 16 | 24-section institutional dossier — added Capital Allocation, Management & Insider Activity, Data-Quality Assessment, Evidence Timeline, Open Questions, and "What Would Change The Current Assessment" |
| `research_questions.py` | 17 | 7 fixed structured questions + a same-ticker snapshot-to-snapshot diff question, each answer citing real evidence and flagging fact-vs-inference |
| `continuous_intelligence.py` | 18 | The deterministic pipeline function (`process_new_information()`) a real trigger would call; never manufactures an alert below MEDIUM materiality |

Every module is purely additive and read-only against `ngx.sqlite`. `company_state.py` gained two new public function aliases (`known_point`/`unknown_point`, non-breaking) so `company_economic_profile.py` could construct `DataPoint`s without reaching into another module's underscore-prefixed internals — the only edit to a Phase-1-13 file this pass; no accounting-core or quant-registry file was touched.

## 3. Files changed

**New**: `src/ngxrot/fre/company_economic_profile.py`, `company_intelligence_bundle.py`, `research_questions.py`, `continuous_intelligence.py`; `scripts/fre/test_company_economic_profile.py`, `test_company_intelligence_bundle.py`, `test_research_questions.py`, `test_continuous_intelligence.py`; this report.

**Modified**: `src/ngxrot/fre/company_state.py` (additive aliases only, §2); `src/ngxrot/fre/company_research_report.py` (rebuilt on top of the new fusion bundle, per Phase 16's explicit "upgrade the existing" instruction); `scripts/fre/test_company_research_report.py` (updated to match the rebuilt module's new section names).

**Unmodified**: everything else, including all of Phases 1-13's other modules (`change_detection.py`, `materiality.py`, `confidence_engine.py`, `scorecard.py`, `market_intelligence.py`, `portfolio_decision_support.py`), the frozen accounting core, and the quant registry track.

## 4. Tests written and results

| Test file | Checks passed |
|---|---|
| `test_company_economic_profile.py` (new) | 25/25 |
| `test_company_intelligence_bundle.py` (new) | 16/16 |
| `test_company_research_report.py` (rewritten) | 61/61 |
| `test_research_questions.py` (new) | 16/16 |
| `test_continuous_intelligence.py` (new) | 9/9 |
| **New/rewritten this pass** | **127/127** |
| `test_company_state.py` (regression re-run) | 40/40 |
| `test_scorecard.py` (regression re-run) | 42/42 |
| `test_change_detection_materiality.py` (regression re-run) | 31/31 |
| `test_confidence_engine.py` (regression re-run) | 62/62 |
| **Total confirmed passing this pass** | **302/302** |

`test_market_intelligence.py` (11/11) and `test_portfolio_decision_support.py`
(9/9) were not re-run this pass — neither imports anything changed this pass
(`company_research_report.py` or the new aliases), so risk of regression is
structurally zero; their last confirmed results stand. A full re-run remains
a reasonable next-session sanity check, same disclosure as the prior stage's
report.

## 5. Real data inspected (not just schema/counts)

- `entity_relationships.relation_type`: confirmed exactly 3 real values
  (`affects_order_1`, `affects_order_2`, `renamed_from`) — zero
  `subsidiary_of` rows, zero populated `competitor_mention` edges (the
  `entity_type` exists; no row uses it as a real relationship).
- `causal_chain_steps.statement` / `impact_assessments.explanation` /
  `extracted_facts.description`: keyword-searched directly for `customer`,
  `supplier`, `subsidiary`, `strategic priorit[y]`, `major shareholder`,
  `ownership` — found exactly 2 `customer` hits (both unrelated narrative,
  not concentration disclosures) and 0 hits for every other term.
- `company_memory.py`'s `management_history` field: confirmed (by reading
  that module's own code, not assumed) to always return empty — an
  inherited, disclosed FRE-3 gap, not reintroduced or worked around here.
- Every pilot ticker's rendered report/bundle/answer set was read in full,
  not just asserted on — e.g. CAP's real `+154.2%` equity change and
  AFRIPRUD's real CBN recapitalisation-directive alert (both produced by
  this build, verified against the real underlying facts in the prior
  Decision-Intelligence session).

## 6. Coverage achieved

- **Phase 14**: of the 15 requested fields, 5 have real, sourced evidence
  for at least some tickers (business_model, industry/sub_industry,
  competitive/peer context — disclosed explicitly as a sector-level proxy,
  never a real competitor list — capital structure, regulatory exposure)
  plus historical corporate events; 9 are confirmed `UNKNOWN`
  platform-wide for every ticker, including the richest ones (verified by
  test against CAP and AFRIPRUD specifically, not just asserted in
  general).
- **Phase 15**: the full named chain (`company_state → ... → portfolio
  memory`) is realized in one function call (`build_intelligence_bundle()`)
  with an optional, cost-disclosed `include_portfolio_note` flag for the
  expensive final hop.
- **Phase 16**: 24 sections rendered, all 24 present and non-empty (or
  explicitly `UNKNOWN`) for both a data-rich pilot ticker (CAP) and a thin
  one (TOTAL) — verified by test, not just for one favorable case.
- **Phase 17**: 7 fixed questions + 1 snapshot-diff question, all answered
  with real evidence citations traced back to the exact `DetectedChange`/
  `DataPoint` source strings (verified by exact-set-equality test against
  CAP's real evidence, not a loose substring check).
- **Phase 18**: the pipeline runs cleanly end-to-end for both a rich and a
  thin ticker; the "no LOW-materiality alerts" rule is enforced
  structurally (`alert_entry is None`), verified by test against a
  same-date (zero-change) comparison.

## 7. Data gaps (honestly recorded, not worked around)

Unchanged from the Phase 0/1 findings, reconfirmed by direct query this
pass: no business description, products/services, revenue segments,
geography, customer concentration, supplier dependencies, management/
ownership, or subsidiary-lineage data exists ANYWHERE on this platform for
ANY ticker. This is the dominant limitation on Phase 14's real coverage,
and it propagates into Phase 16's dossier (those same fields render
`UNKNOWN` there too) and into Phase 17's "missing information" answer
(which correctly names them). No inference or LLM guess was substituted
for any of these — every `UNKNOWN` traces to a real, reproducible query
result named in the relevant module's own docstring.

## 8. Architectural weaknesses

- **`compute_confidence()` reused inside `continuous_intelligence.py`'s
  `confidence_changed` check calls `compute_confidence(prior_state, None)`**
  — it does not fetch the THESIS as it stood at `prior_date` (thesis is
  only fetched for the current `as_of_date`), so the "did confidence
  change" comparison holds thesis constant while state varies. This is a
  real simplification, disclosed here, not silently presented as a
  full historical-thesis comparison — building a true PIT thesis-at-date-X
  reader was out of this pass's scope (`company_thesis.py` itself is
  already `as_of_date`-parameterized and could support this in a future
  pass without modification).
- **`portfolio_memory.cross_reference()`'s ~15-20s uncached cost**
  (inherited limitation, previously disclosed) means Phase 15's fusion and
  Phase 18's continuous-intelligence pipeline both default
  `include_portfolio_note`/equivalent to `False` for anything beyond a
  single-ticker query — a real, load-bearing scaling constraint on any
  future batch/continuous use of this pipeline, not yet resolved.
- **Phase 18 has no actual trigger** (§ "What this module does NOT do" in
  `continuous_intelligence.py`'s own docstring) — this is a genuine,
  disclosed scope boundary (no scheduler/webhook infrastructure exists on
  this platform to wire into), not an oversight.
- **`research_questions.py`'s "strongest positive/negative developments"
  and "requires monitoring" use a fixed top-3/MEDIUM-plus cutoff** — a
  disclosed, non-tuned convention, same category of simplification as
  `materiality.py`'s own fixed thresholds.

## 9. Capabilities still missing

- A true PIT "thesis as it stood at an earlier date" reader (§8).
- Automated triggering infrastructure for Phase 18 (a scheduler/file-watcher
  wiring `process_new_information()` to real new filings as they arrive).
- Any narrower version of a "conflict narration" layer (named as missing in
  the prior Decision-Intelligence report, still not built) — Phase 17's
  question-answering partially substitutes for this (a user can ask "what
  contradicts the thesis" directly) but there is no automatic prose
  synthesis of cross-category disagreement.
- Everything explicitly gated: quantitative recommendation engine, BUY/
  SELL/AVOID vocabulary, cross-sectional ranking, conviction weighting,
  automatic allocation (§10).

## 10. Governance gates encountered

**None required a stop.** The task's own Governance section pre-named
every blocked capability, and none of Phases 14-18 as specified required
building any of them — Phase 16 explicitly reiterated "Do NOT create BUY/
SELL/AVOID labels... cross-sectional rankings... a unified conviction
score," and this build's own `company_research_report.py` Section 23
explicitly states this in the rendered output itself (verified by test),
matching the same disclosure pattern the prior Phase 9/13 build already
established. FRE-7 activation was not touched or reconsidered — its own
gate (`docs/fre_runs/fre7b2_peer_coverage_recovery_feasibility.md`) remains
exactly where the prior session left it (STOP FRE-7 — DATA CONSTRAINT).

## 11. Recommended next stage

Two independent, non-conflicting paths:

1. **Close the disclosed weaknesses (§8/§9)** before treating this as
   production infrastructure: build a true PIT thesis-at-date-X capability
   (small, `company_thesis.py` already supports the parameter), address
   `cross_reference()`'s scaling cost if continuous/batch use is intended,
   and re-run the full pre-existing FRE regression suite (not done this
   pass either, same disclosure as the prior report) to confirm zero
   drift across the whole platform.
2. **The gated path remains exactly where it was**: Phase 8/10
   (recommendation/ranking) stay blocked on a second validated independent
   quant factor (`OWNER_DECISION_BACKLOG_2026-08-02.md`); FRE-7 activation
   stays blocked on the peer-coverage-recovery finding from the prior
   session. Nothing in this pass changes either condition or attempts to
   route around it.

No new hypothesis was registered, no backtest was run, no existing frozen
file was modified, and no write path was added anywhere in this build.
