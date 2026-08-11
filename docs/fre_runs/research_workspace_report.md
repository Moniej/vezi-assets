# Research Workspace -- Phase 3 Report

**Date**: 2026-08-10
**Follows**: `docs/fre_runs/research_query_layer_report.md` (Phase 2,
109/109 baseline passing before this phase started).
**Explicitly out of scope, and none of it was done**: momentum, relative
strength, alpha factors, sector-rotation signals, predictive models,
portfolio construction, trading signals, strategy optimization, alpha
backtests, performance optimization for trading strategies.

---

## 0. Phase 2 audit (performed before writing any Phase 3 code)

| Requirement | Status | Evidence |
|---|---|---|
| `research_query.py` (`QuerySpec`/`QueryResult`, 6 query types) | DONE | file present; `scripts/test_research_query.py`, 29/29 |
| `query_log` (immutable, logs every execution) | DONE | 3 real rows already in production `registry.sqlite` from prior CLI use; trigger-verified immutable |
| `research_dataset.py` / `dataset_snapshots` | DONE | Phase 1; `scripts/test_research_os.py`, 19/19 |
| `research_quality.py` | DONE | Phase 1, reused directly this phase |
| `lineage.py` | DONE | reused directly for evidence provenance this phase |
| `dataset_snapshots`/`research_runs` | DONE | Phase 1 tables, present and tested |
| `instrument_identity.py` | DONE | reused via Phase 2, unmodified this phase |
| SQLite PIT / existing universe/registry | DONE | untouched |
| **Full regression before Phase 3 work began** | DONE | 109/109 across all 5 prior suites, re-run and confirmed at the start of this phase |

No PARTIAL/MISSING items found. Proceeded to build directly on top per
the architecture diagram in the Phase 3 brief.

## 1. Where Phase 3 plugs in

One new module, `src/ngxrot/research_workspace.py`, sitting directly on
top of Phase 2 (`research_query.py`, `query_log`) and Phase 1
(`research_dataset.py`, `research_quality.py`, `lineage.py`,
`instrument_identity.py`). New tables live in the SAME
`data/registry.sqlite` (`schema/registry.sql`, new "Phase 3" section) --
no new database, no new provider, no new ingestion path, no new identity
or lineage system, no parallel project.

## 2. What was built

### 2a. `schema/registry.sql` (modified, additive)

12 new tables (`research_projects`, `research_project_queries`,
`research_notes`, `research_evidence`, `research_findings` +
`research_findings_status_log`, `research_hypotheses` +
`research_hypotheses_status_log`, `research_artifacts`,
`research_snapshots`, `research_timeline`) with guard triggers following
the platform's existing discipline: mutable objects (`research_projects`,
`research_findings`, `research_hypotheses`) get a frozen-identity guard
+ a status-log table (mirroring the pre-existing `hypotheses`/
`hypothesis_status_log` pattern); everything else is insert-only.
Verified the real production `registry.sqlite` (330 experiments, 3
query_log rows) still opens and migrates cleanly after this addition.

**`research_hypotheses` is deliberately separate** from the pre-existing
`hypotheses` table -- that one is alpha-backtest-shaped (status
vocabulary `untested`/`testing`/`confirmed`/`rejected`, linked to
`experiments`); this one is generic research-workflow tracking (`OPEN`/
`SUPPORTED`/`WEAKENED`/`REJECTED`/`UNRESOLVED`, linked to
`research_findings`). Same reasoning as Phase 1's `dataset_snapshots`/
`research_runs` vs `experiments`/`hypotheses` split.

### 2b. `src/ngxrot/research_workspace.py` (new)

Full project lifecycle (`create_project`/`get_project`/`list_projects`/
`update_project`/`archive_project`), query attachment (`attach_query`/
`list_queries`), notes (6 typed kinds), evidence (8 types, with
automatic `lineage.py`-based provenance resolution for
`dataset_observation` evidence), findings (status-tracked, evidence-
linked), hypotheses (status-tracked, finding-linked, generic), analysis
artifacts (`make_table_artifact`/`make_summary_artifact`/
`make_chart_spec` -- declarative chart specs, not rendered images),
reproducible snapshots (`snapshot`/`check_reproducibility`), an
integrity aggregator (`integrity_check`), a quality-summary composer
(`project_quality_summary`, pure reuse of `research_quality.py`), an
auto-populated timeline, and two deterministic exports (`export_json`/
`export_markdown`).

### 2c. `scripts/ngxrot_research_workspace.py` (new) -- CLI

12 subcommands (`create`, `list`, `show`, `attach-query`, `evidence`,
`note`, `finding`, `hypothesis`, `snapshot`, `export`, `quality`,
`integrity`), same argparse convention as Phase 2's `ngxrot_research.py`.

### 2d. Documentation

`docs/research_workspace.md` -- architecture, project model, the
question/hypothesis/analysis/finding/conclusion distinction, scope,
workflow objects, query attachments, evidence, findings/hypotheses (with
an explicit "not alpha signals" section), branching, artifacts,
snapshots, integrity guardrails, quality summary, timeline,
reproducibility, CLI, Python API, exports, no-AI-dependency statement,
limitations, examples.

## 3. Real bug found and fixed during development

**`entities_requested` was missing from `query_log`, breaking the exact
sector-research use case the spec's own example describes.**
`project_quality_summary()` initially read `entities` from
`query_log.parameters_json` -- but a `cross_section` query's
`QuerySpec.entities` field is empty (its tickers are *resolved* from a
sector filter, not passed in by the caller). A live smoke test of
`project_quality_summary()` on a CONSUMER GOODS sector project returned
**zero tickers** instead of 19. Fixed with a small, additive migration:
added `entities_requested_json` to `query_log` (via the existing
`ALTER TABLE ... ADD COLUMN` migration pattern in `registry.py`,
verified safe against the real production database), populated from
`QueryResult.entities_requested` (the actually-resolved set) rather than
the raw request. Re-verified live: the same project now correctly
resolves all 19 real tickers. Permanently covered by
`scripts/test_research_workspace.py`.

## 4. Tests

`scripts/test_research_workspace.py`, **47/47 passing**: project
create/retrieve/update/archive (including the frozen-after-archive
guard), query attachment (including rejecting an unknown `query_id`,
and the `entities_requested` bug fix), evidence create/retrieve/trace-to-
source (including a deliberately unresolvable-provenance case,
correctly left `NULL`), typed notes, findings (status transitions
including an explicitly `UNRESOLVED`/negative-style finding, invalid-
status rejection), hypotheses (`OPEN` -> `SUPPORTED` -> `WEAKENED` ->
`REJECTED`, both directions of evidence linkage), artifacts (table/
summary/chart, content-hash presence, chart-as-declarative-spec),
quality-summary composition, integrity-check aggregation (missing-
provenance and survivorship warnings both actually surfaced),
snapshot/reproducibility (unchanged immediately after freeze, correctly
flips to changed after a real mutation), deterministic JSON/Markdown
export, an explicit no-investment-recommendation-language check, an
explicit NGX-Pulse-API-key-never-leaks check (both export formats), and
branching (parent linkage, rejecting a nonexistent parent).

`scripts/research_workspace_integration_test.py` (Section 26 of the
spec): a genuine end-to-end descriptive investigation -- "How has the
composition of the NGX equity universe (by sector) changed over a
defined historical period?" -- across 3 sectors x 2 dates, through
create -> scope -> 6 real queries -> 6 evidence items -> 6 table
artifacts -> 3 findings -> integrity/quality check -> snapshot -> export
-> reproduce. **PASSED.** Real output: CONSUMER GOODS 18->19,
FINANCIAL SERVICES 33->38, OIL AND GAS 5->7 constituents between
2020-01-01 and 2025-01-01 (current-day sector classification, disclosed
per Section 12's historical-versioning limitation).

**Regression** (all prior suites re-run, unaffected):

| Suite | Result |
|---|---|
| `scripts/test_instrument_identity.py` | 20/20 |
| `scripts/test_lineage.py` | 10/10 |
| `scripts/test_ngxpulse_provider.py` | 31/31 |
| `scripts/test_research_os.py` | 19/19 |
| `scripts/test_research_query.py` | 29/29 |
| `scripts/test_research_workspace.py` (new) | 47/47 |
| **Total** | **156/156** |

Plus both integration tests (`research_query_integration_test.py`,
`research_workspace_integration_test.py`): PASSED.

## 5. Performance (measured)

| operation | time |
|---|---|
| project creation | ~24ms |
| query attachment | ~3ms |
| evidence retrieval (20 items) | ~0.3ms |
| finding retrieval (10 items) | ~0.1ms |
| snapshot creation | ~42ms |
| Markdown report generation | ~43ms |
| JSON export | ~2ms |

All comfortably interactive. **No PostgreSQL/Redis/distributed workers
justified** -- SQLite remains adequate, per the spec's own instruction
to document rather than solve hypothetically.

## 6. A genuine finding surfaced by this phase (not fabricated)

Running `integrity_check()` on the 3-sector, 2-date end-to-end
investigation produced **3,104** warnings -- overwhelmingly legacy
`unexplained_jump` entries from the platform's older
`corporate_action_audit.py` tool repeatedly logging the same
observations across many historical runs (already disclosed for
CILEASING specifically in `docs/fre_runs/
ngxpulse_data_foundation_gaps_report.md`; this phase is the first time
that backlog has been aggregated across a whole research project's
ticker set). This is disclosed as real platform state, not treated as a
defect in this phase's own code.

## 7. Files changed

New:
- `src/ngxrot/research_workspace.py`
- `scripts/ngxrot_research_workspace.py`
- `scripts/test_research_workspace.py`
- `scripts/research_workspace_integration_test.py`
- `docs/research_workspace.md`
- `docs/fre_runs/research_workspace_report.md` (this file)

Modified:
- `schema/registry.sql` (12 new tables + guard triggers, additive; one
  new column on the existing `query_log` table)
- `src/ngxrot/registry.py` (one new `ALTER TABLE` migration entry,
  following the file's own existing pattern)
- `src/ngxrot/research_query.py` (`_log_query` now also records
  `entities_requested`, fixing the bug in Section 3)

No existing provider, ingestion path, identity system, lineage system,
Phase-2 query semantics, or backtest module was otherwise modified.

## 8. Architectural decisions worth flagging

- **Two hypothesis tables, deliberately unmerged** (Section 2a) -- same
  reasoning as Phase 1's dataset_snapshots/research_runs split; alpha-
  shaped and generic-research-shaped concepts stay separate rather than
  forcing one schema to serve both.
- **Charts are declarative specs, not images** -- keeps this a data
  structure (`{chart_kind, x, y, data}`) traceable back to its source
  query, not a rendered artifact that would need its own storage/
  versioning strategy.
- **No scope validation at project-creation time** -- scope is validated
  implicitly the moment a query is executed against it (Phase 2 already
  does this work); adding a second, earlier validation pass would be
  duplicated logic for marginal benefit.
- **Snapshotting an ARCHIVED project is explicitly allowed** -- freezing
  final state should never be blocked by the same guard that blocks
  further *mutation*.

## 9. Known limitations / future work (disclosed, not resolved)

- Historical sector-classification gap (Phase 2 finding) surfaces here
  as an integrity warning on every relevant query; not fixable without
  new source data.
- Branching has no merge/diff -- a "branch" is just a new project with a
  parent pointer, by design (spec explicitly said not to build git).
- `integrity_check()`/`project_quality_summary()` can return very large
  warning counts on wide-scope projects (Section 6) -- correct behavior,
  but a future UI layer would likely want pagination/summarization
  rather than a flat list.
- AI-assisted report writing was explicitly not built (Section 19 of
  `docs/research_workspace.md`) -- both exports are pure deterministic
  formatting, as required.

---

## STOP

This closes the requested Research Workspace & Workflow Layer. **No
alpha research was started** -- no momentum, relative-strength, factor,
sector-rotation, predictive-model, portfolio-construction, trading-
signal, or strategy-optimization code exists anywhere in this codebase
as a result of this phase. The next phase should only begin after an
explicit decision to proceed.
