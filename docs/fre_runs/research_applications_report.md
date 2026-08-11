# Research Applications -- Phase 4 Report

**Date**: 2026-08-10
**Follows**: `docs/fre_runs/research_workspace_report.md` (Phase 3,
156/156 baseline passing before this phase started; production
`registry.sqlite` backed up to a scratch location before any schema
change, per Section 27's mandate).
**Explicitly out of scope, and none of it was done**: momentum,
relative-strength, sector-rotation, alpha factors, predictive models,
trading signals, portfolio optimization, strategy optimization, alpha
backtests, automated buy/sell decisions.

---

## 0. Architectural assessment (performed before writing any code)

| Layer | Reuse as-is | Extend (additive) | New |
|---|---|---|---|
| Data Foundation (Phase 1) | `db.py`, `instrument_identity.py`, `lineage.py`, `research_quality.py`, `universe.py` | — | — |
| Research Query Layer (Phase 2) | `research_query.py` (all 6 query types, `query_log`) | — | — |
| Research Workspace (Phase 3) | `ResearchProject` = investigation, `research_evidence`, `research_findings`, `research_hypotheses`, `research_artifacts` (incl. `make_chart_spec`), `research_snapshots`, `export_markdown` | `research_evidence.claim_class`, `research_hypotheses.confidence`/`reason_for_investigation`/`researcher_notes` (both nullable columns, additive) | — |
| Phase 4 | — | — | `research_contradictions` (+status log), `research_conclusions`, `research_applications.py`, one new CLI script |

**Explicit decision, documented rather than implemented**: did NOT widen
`research_hypotheses`' status CHECK constraint to the spec's own
vocabulary (`UNTESTED`/`WEAKLY_SUPPORTED`/`INCONCLUSIVE`/
`CONTRADICTED`) -- SQLite cannot alter a CHECK constraint in place, and
Phase 3's existing 5-state vocabulary already covers the same semantic
space. A table-rebuild migration for a vocabulary difference was judged
not worth the risk.

Baseline regression re-confirmed clean before any Phase 4 code was
written: **156/156**. Production `registry.sqlite` backed up to a
scratch location before the schema change (Section 27, item 3).

## 1. What was built

### 1a. `schema/registry.sql` (modified, additive)

`research_contradictions` + `research_contradictions_status_log`,
`research_conclusions` (both new, insert-only-mostly-immutable, same
guard-trigger discipline as every prior table in this file); `claim_
class` added to `research_evidence`; `confidence`/`reason_for_
investigation`/`researcher_notes` added to `research_hypotheses`.
Verified migration-safe against the real production `registry.sqlite`
(330 experiments) both before writing tests and again after.

### 1b. `src/ngxrot/registry.py` (modified)

Four new `ALTER TABLE ... ADD COLUMN` migration entries, following the
file's own established pattern exactly.

### 1c. `src/ngxrot/research_workspace.py` (modified)

`add_evidence()` gained an optional `claim_class` parameter, threaded
into the original INSERT (see Section 2, bug #1) -- this was the one
change to Phase 3 code required to support Phase 4's evidence
classification without breaking `research_evidence`'s immutability.

### 1d. `src/ngxrot/research_applications.py` (new)

Investigation lifecycle (`create_investigation`/`set_investigation_
status`), research plans (structured `research_note` artifacts),
classified evidence, extended hypotheses (confidence/reasoning),
contradiction detection + recording (`detect_source_conflicts`,
`record_contradiction`, status transitions), a descriptive-analysis
toolkit (`descriptive_summary`/`growth_rate`/`group_comparison`/
`period_over_period_change`/`before_after_comparison`), company
research (`company_profile`), sector research (`sector_profile`), event
research (`event_window`), comparative research (`compare_entities`),
research tables (`make_entity_metric_table`), a quality gate (`run_
quality_gate`, `complete_investigation`), a conclusion framework
(`record_conclusion`/`current_conclusion`), a report generator
(`generate_investigation_report`), and 8 research templates.

### 1e. `scripts/ngxrot_research_apps.py` (new) -- CLI

10 subcommands (`investigate`, `company`, `sector`, `compare`, `event`,
`quality-gate`, `conclude`, `complete`, `report`, `templates`), same
argparse convention as Phase 2/3's CLIs.

### 1f. Documentation

`docs/research_applications.md` -- full architecture, every capability,
every design decision and its reasoning, limitations.

## 2. Real bugs found and fixed during development

1. **Evidence classification via `UPDATE` was correctly rejected by
   Phase 3's own immutability trigger.** The first draft of
   `add_classified_evidence()` inserted evidence via `rw.add_evidence()`
   then tried to `UPDATE research_evidence SET claim_class = ...`
   afterward -- `research_evidence` is insert-only by design (Phase 3),
   so this raised `sqlite3.IntegrityError` immediately on the first live
   smoke test. Fixed by extending `rw.add_evidence()` itself to accept
   an optional `claim_class` parameter set at INSERT time.
2. **`complete_investigation()` snapshotted before setting the final
   status**, so `check_reproducibility()` reported spurious drift
   immediately after completion (the frozen snapshot held a pre-
   completion status that no longer matched the live project). Caught
   by the test suite's own reproducibility check
   (`scripts/test_research_applications.py`), not by manual inspection.
   Fixed by reordering: set status to `COMPLETED`, THEN snapshot.
3. **A test's own wrong expectation, not a code bug**: `event_window()`
   on a nonexistent ticker was expected to return a soft
   `{"found": False}` result; it actually (correctly) raises
   `QueryValidationError`, inheriting Phase 2's existing "unknown entity
   is rejected outright" guardrail. The test was corrected to expect the
   exception, matching the platform's established philosophy of
   rejecting rather than silently returning empty results for genuinely
   invalid input.

## 3. Tests

`scripts/test_research_applications.py`, **53/53 passing**: investigation
lifecycle (create/status transitions/invalid-status rejection), research
plan recording (immutable, question-preserving), company research (real
identity chain, real metadata, explicit "not requested"/`None` for
unavailable fields -- never fabricated), evidence classification (distinct
MEASUREMENT vs INTERPRETATION, invalid-class rejection), hypothesis
extensions (confidence bounds-checked, status transitions reused from
Phase 3 unchanged), sector research (real snapshot counts, real entries/
exits, historical-classification disclosure), event research (real
CILEASING pre/post windows reproducing the known bonus-issue price drop,
no expected-return/signal/score field anywhere, unknown-ticker rejection),
comparative research (real per-entity summaries, comparability warning),
contradiction detection (real multi-source conflicts recorded OPEN,
manual recording + status transitions, invalid-status rejection),
descriptive-analysis-toolkit correctness, quality-gate blocking (zero
queries blocks completion; open contradictions block completion; `force=
True` completes but visibly logs a warning), conclusion framework (real,
non-forced-positive states, invalid-state rejection), report generation
(claim-class labels present, Contradictions/Quality-Gate/Conclusion
sections present, no investment-recommendation language, no API-key
leakage), templates (all 8 present, no hard-coded conclusion field,
unknown-template rejection), and reproducibility (snapshot freezes
immediately-matching state after the ordering-bug fix in Section 2).

`scripts/research_applications_integration_test.py` (Section 26 of the
spec): **three genuine, real-data investigations**, all COMPLETED, all
reproducible:

- **A -- Sector Composition**: CONSUMER GOODS 18->19 (+BUAFOODS),
  OIL AND GAS 5->7 (+ARADEL, +JAPAULGOLD) between 2020-01-01 and
  2025-01-01. Conclusion: `SUPPORTED`, with an explicit uncertainty that
  current-day-only classification cannot distinguish real listings from
  reclassification.
- **B -- Company Historical Profile (GTCO)**: real identity chain
  (GUARANTY->GTCO, 2021-06-24 rename), 732 real price observations,
  close range 16.85-58.75 over 2022-2024. A hypothesis about genuine
  value appreciation was explicitly `WEAKENED` on discovering this
  platform's own disclosed incomplete corporate-actions coverage.
  Conclusion: `PARTIALLY_SUPPORTED`.
- **C -- Event Investigation (CILEASING bonus issue)**: real pre-window
  mean close 5.18 -> real post-window mean close 4.03 around
  2024-01-05, cross-referenced against the real `extracted_facts` bonus-
  issue record. 159 legacy data-quality flags were recorded as a
  contradiction against this session's own prior finding and explicitly
  `RESOLVED` with a written note. Conclusion: `SUPPORTED`, with an
  explicit uncertainty that the raw/unadjusted price series cannot
  separate the mechanical markdown from real market movement.

All three: real research plan recorded, real evidence classified
(FACT/MEASUREMENT/DOCUMENT/INTERPRETATION all used across the three),
real findings, real quality-gate run, real conclusion with stated
uncertainties/limitations/further-research, real snapshot frozen,
reproducibility verified `unchanged=True` for all three.

**Regression** (all prior suites + integration tests re-run, unaffected):

| Suite | Result |
|---|---|
| `scripts/test_instrument_identity.py` | 20/20 |
| `scripts/test_lineage.py` | 10/10 |
| `scripts/test_ngxpulse_provider.py` | 31/31 |
| `scripts/test_research_os.py` | 19/19 |
| `scripts/test_research_query.py` | 29/29 |
| `scripts/test_research_workspace.py` | 47/47 |
| `scripts/test_research_applications.py` (new) | 53/53 |
| **Total** | **209/209** |

Plus 3 integration tests (`research_query_integration_test.py`,
`research_workspace_integration_test.py`,
`research_applications_integration_test.py`): all PASSED.

## 4. Files changed

New:
- `src/ngxrot/research_applications.py`
- `scripts/ngxrot_research_apps.py`
- `scripts/test_research_applications.py`
- `scripts/research_applications_integration_test.py`
- `docs/research_applications.md`
- `docs/fre_runs/research_applications_report.md` (this file)

Modified:
- `schema/registry.sql` (2 new tables + guard triggers, 4 new columns
  on existing tables -- all additive)
- `src/ngxrot/registry.py` (4 new `ALTER TABLE` migration entries)
- `src/ngxrot/research_workspace.py` (`add_evidence()` gained an
  optional `claim_class` parameter -- the one Phase-3 change required)

No provider, ingestion path, identity system, lineage system, Phase-2
query semantics, or backtest module was otherwise modified.

## 5. Architectural decisions worth flagging

- **REVIEW status is a note, not a database state** (Section 2 of
  `docs/research_applications.md`) -- avoids widening a CHECK constraint
  for one transient state.
- **Hypothesis status vocabulary not widened** -- same reasoning,
  documented mapping instead of a schema rebuild.
- **Contradiction detection never auto-resolves** -- `detect_source_
  conflicts()` only records candidates; every resolution requires an
  explicit `resolution_note` from the researcher (demonstrated in
  Investigation C).
- **Quality gate genuinely blocks, not just warns** -- `complete_
  investigation()` raises rather than silently completing an
  investigation with zero queries or unresolved contradictions, unless
  explicitly forced (and forcing is itself logged, never hidden).

## 6. Known limitations / future work (disclosed, not resolved)

- No automated detector exists yet for sector-classification or
  corporate-action contradictions -- only price-level source conflicts
  are auto-detected; everything else requires `record_contradiction()`.
- `event_window()`/windowed `company_profile()` calls inherit Phase 2's
  hard rejection of unknown tickers rather than a softer "not found"
  path -- consistent with platform philosophy, but a future UI layer
  may want to catch this and present it more gently.
- Sector/company historical-classification limitations (Phase 2 finding)
  remain unresolved -- surfaced via disclosure text in every relevant
  profile, not fixed (would require new source data).
- `RESEARCH_TEMPLATES` are pure metadata -- there is no automated
  "run this template" executor yet; a researcher still manually calls
  the composer functions the template names.

---

## STOP

This closes the requested Investment Research Application Layer. **No
alpha research was started** -- no momentum, relative-strength, factor,
sector-rotation, predictive-model, trading-signal, portfolio-
optimization, or backtesting code exists anywhere in this codebase as a
result of this phase. Three real, evidence-driven, non-alpha
investigations were completed and are independently reproducible. The
next phase should only begin after an explicit decision to proceed.
