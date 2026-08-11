# Research Workspace (Phase 3)

**Status**: Infrastructure. No alpha hypothesis, signal, factor,
ranking, or predictive model has been implemented anywhere in this
layer. All worked examples in this document and its tests are
deliberately descriptive.

**Document/evidence bridge (added 2026-08-11)**: `add_document_evidence()`
records one row of a `facts`/`events`/`entity_relationships`/
`document_context` `QueryResult` (the new query types documented in
`docs/research_query_layer.md` §18a) as `research_evidence`, using the
existing `evidence_type='source_document'` value -- no schema change, no
migration of the live registry.sqlite. Provenance comes straight from the
query result (already resolved against `documents`/`sources`), not a
second lookup. A research project can now cite market data AND
document/fact evidence side by side in the same evidence list, findings,
and exported report. See `scripts/test_research_workspace.py`'s
"document evidence" section for worked examples.

---

## 1. Architecture

```
                    RESEARCHER
                        |
                        v
              +--------------------+
              | Research Workspace |
              |      Phase 3       |
              +---------+----------+
                        |
              +---------+---------+
              |                   |
              v                   v
       Research Queries       Evidence
         Phase 2               Layer
              |                   |
              +---------+---------+
                        v
                Research Results
                        |
                        v
              +--------------------+
              |  Data Foundation   |
              |      Phase 1       |
              +---------+----------+
                        |
              +---------+---------+
              v                   v
          SQLite PIT          Provenance
              |
              v
       Validated NGX Data
```

`src/ngxrot/research_workspace.py` is the ONLY new module. It sits
directly on top of Phase 2 (`research_query.py`, `query_log`) and Phase
1 (`research_dataset.py`'s `dataset_snapshots`, `research_quality.py`,
`lineage.py`, `instrument_identity.py`). It copies **no** underlying
dataset: a project references `query_id`s (Phase 2) and, where relevant,
`snapshot_id`s (Phase 1) that already exist immutably elsewhere.

All new tables live in the SAME `data/registry.sqlite` used by Phase 1/2
(`schema/registry.sql`, "Phase 3" section) -- no new database.

## 2. Research project model

`ResearchProject`: `research_id`, `title`, `research_question`,
`description`, `status` (`DRAFT`\|`ACTIVE`\|`PAUSED`\|`COMPLETED`\|
`ARCHIVED`), `created_at`/`updated_at`, `owner`, `tags`, `scope`,
`dataset_snapshot_ids`, `code_fingerprint` (captured at creation),
`parent_research_id` (branching, Section 9).

Once `ARCHIVED`, a project is frozen -- enforced at the SQL level
(`research_projects_frozen_guard` trigger), same discipline as the
platform's pre-existing `hypotheses_frozen_guard`. `research_id`,
`title`, `research_question`, `created_at`, and `code_fingerprint` can
never change after creation (`research_projects_guard_immutable_fields`
trigger) -- only `status`/`description`/`tags`/`scope`/
`dataset_snapshot_ids`/`updated_at` are mutable, and only before
archiving.

## 3. The question/hypothesis/analysis/finding/conclusion distinction

The workspace deliberately keeps these as **separate objects**:

- **Question** (`research_question`, required at creation) -- may be
  purely descriptive, e.g. "How has NGX sector composition changed?"
  No hypothesis is required or auto-generated from it.
- **Hypothesis** (`research_hypotheses`, optional) -- a researcher's own
  claim, tracked `OPEN -> SUPPORTED`/`WEAKENED`/`REJECTED`/`UNRESOLVED`
  against recorded findings. Not every project needs one.
- **Analysis** (`research_artifacts`) -- descriptive computation
  (tables, summary statistics, comparisons, chart specs) over query
  results.
- **Finding** (`research_findings`) -- a recorded, evidenced statement.
  **Not an alpha signal.** A finding can just as easily *invalidate* a
  hypothesis or describe a data-quality problem (worked examples: "two
  providers disagree on 0.62% of observations", "sector membership data
  has no historical versioning before a given date") as support one.
- **Conclusion** -- the researcher's own synthesis, written into the
  project `description`/notes/exported report. This module never
  generates one automatically (Section 10).

## 4. Scope

`scope` is a free-form dict referencing the EXISTING universe/PIT/
identity systems -- e.g. `{"sectors": [...], "tickers": [...],
"start": ..., "end": ..., "as_of": ..., "sources": [...], "fields": [...]}`.
It is not validated against those systems at creation time; validation
happens naturally the moment a query is executed, since Phase 2's
`research_query.validate_spec()` already enforces every guardrail (date
validity, known entities/fields, look-ahead rejection). No second
validation layer was built.

## 5. Workflow objects

| Object | Table | Mutability |
|---|---|---|
| Query attachment | `research_project_queries` | insert-only |
| Note | `research_notes` | insert-only |
| Evidence | `research_evidence` | insert-only |
| Finding | `research_findings` | `status`/`supporting_evidence` mutable, statement frozen, every transition logged |
| Hypothesis | `research_hypotheses` | `status`/supporting+contradicting findings mutable, statement frozen, every transition logged |
| Artifact | `research_artifacts` | insert-only |
| Snapshot | `research_snapshots` | insert-only |
| Timeline event | `research_timeline` | insert-only, auto-populated |

`research_findings_status_log`/`research_hypotheses_status_log` mirror
the platform's pre-existing `hypothesis_status_log` pattern.

## 6. Query attachments

`attach_query(reg, research_id, query_id, note)` references an EXISTING
`query_log` row (Phase 2) -- rejects an unknown `query_id` outright. No
dataset is duplicated; `list_queries()` joins back to `query_log` for
the full `QuerySpec`/result metadata/provenance every time.

## 7. Evidence

`add_evidence(con, reg, research_id, evidence_type, source_reference,
description)` supports the 8 types requested (`query_result`,
`dataset_observation`, `source_document`, `company_metadata`,
`corporate_action`, `historical_event`, `calculation`, `chart_table`).
For `dataset_observation` evidence with a `ticker`/`trade_date`,
provenance is resolved via the EXISTING `lineage.
trace_equity_observation()` -- no second lineage system. If provenance
cannot be resolved, it is left explicitly `NULL`, never fabricated, and
`integrity_check()` surfaces this as a warning (Section 12).

`trace_evidence(reg, evidence_id)` answers "what supports this
statement": evidence -> query -> data sources, composed from existing
tables.

## 8. Findings and hypotheses -- NOT alpha signals

A finding's `status` (`PRELIMINARY`/`SUPPORTED`/`CONTESTED`/`REJECTED`/
`UNRESOLVED`) and a hypothesis's `status` (`OPEN`/`SUPPORTED`/
`WEAKENED`/`REJECTED`/`UNRESOLVED`) describe the RESEARCHER's own
judgment about a claim -- no statistical hypothesis-testing framework,
scoring, or ranking exists anywhere in this module. The end-to-end test
(`scripts/research_workspace_integration_test.py`) records findings
about sector *constituent counts*, never a trading recommendation.

## 9. Branching

`create_project(..., parent_research_id=...)` -- a new, independent
project that records its parent. This is NOT git: there is no merge, no
diff, no branch-local mutation of the parent's data (the parent remains
exactly as it was; a "branch" is simply a new project with a
`parent_research_id` pointer). Sufficient for "start a narrower/deeper
investigation from where an earlier one left off" without introducing
version-control machinery.

## 10. Analysis artifacts / charts / tables

`make_table_artifact()`, `make_summary_artifact()` (count/mean/median/
min/max/std per group -- descriptive only), `make_chart_spec()`
(`time_series`/`cross_sectional`/`sector_composition`/`missingness`, a
**declarative spec** -- data + axis mapping as JSON, not a rendered
image; this is not a BI platform). Every artifact carries
`source_query_id` (traces back to the originating `QuerySpec`) and a
`content_hash` (Phase-1-style deterministic hashing, `_hash_json`) --
`Chart -> Query ID -> QuerySpec -> underlying observations` stays
auditable end to end.

## 11. Reproducible snapshot

`snapshot(con, reg, research_id)` freezes the CURRENT state: the project
row plus every note/evidence/finding/hypothesis/artifact/query-
attachment id and content hash -- not the underlying datasets themselves
(already immutable via Phase 1/2). `check_reproducibility(reg,
research_snapshot_id)` re-derives the current state and compares hashes:
`unchanged=True` immediately after a freeze; `unchanged=False` the
moment anything real changes (verified live in both test suites --
adding one note after a freeze flips this to `False`).

## 12. Integrity guardrails

`integrity_check(con, reg, research_id)` aggregates:

- **Look-ahead**: already REJECTED, not just warned, at query execution
  time by Phase 2's `validate_spec` -- nothing look-ahead-contaminated
  can ever reach `query_log`, so nothing look-ahead-contaminated can
  ever be attached to a project.
- **Survivorship**: warnings carried forward from every attached query's
  own `warnings` (Phase 2 already generates these for historical sector/
  cross-section queries).
- **Missing provenance**: any `dataset_observation` evidence whose
  provenance could not be resolved.
- **Unresolved data-quality issues**: unresolved `data_quality_log`
  flags on every ticker actually referenced by the project's attached
  queries (via `project_quality_summary`, Section 13).

**A real, honest finding from the end-to-end test**: a 3-sector, 2-date
composition study surfaced **3,104** integrity warnings -- almost
entirely legacy `unexplained_jump` flags accumulated by the platform's
older `corporate_action_audit.py` tool (one ticker, CILEASING, alone
carries 150+ such entries from repeated historical runs, as already
disclosed in `docs/fre_runs/ngxpulse_data_foundation_gaps_report.md`).
This is not a bug in this phase -- it is this phase correctly surfacing
a pre-existing data-quality backlog that no prior tool had aggregated
across a whole research project's ticker set before.

Automatic transformation guardrails (no silent price adjustment, no
forward-fill, no sector reclassification) are inherited unchanged from
Phase 2 -- this layer performs no data transformation of its own at all.

## 13. Quality summary

`project_quality_summary(con, reg, research_id)` composes
`research_quality.quality_report()` (Phase 1, unmodified) over the union
of tickers referenced by every attached query. No quality-detection
logic is duplicated.

## 14. Timeline

`research_timeline` is populated automatically by every state-changing
function in this module (`_log_event`) -- never fabricated, never
backfilled. `timeline(reg, research_id)` returns it in order.

## 15. Reproducibility, end to end

1. Attach queries (each with its own Phase-2 `content_hash` already in
   `query_log`).
2. Record evidence/notes/findings/hypotheses/artifacts as the
   investigation proceeds.
3. `snapshot()` freezes the whole thing with one project-level content
   hash referencing every child object's own id/hash.
4. `check_reproducibility()` at any later point re-derives the current
   hash and reports drift -- normal for an `ACTIVE` project, a red flag
   for a `COMPLETED` one.

## 16. CLI

`scripts/ngxrot_research_workspace.py` (companion to Phase 2's
`ngxrot_research.py`, same argparse convention):

```bash
PYTHONPATH=src python scripts/ngxrot_research_workspace.py create --title "..." --question "..."
PYTHONPATH=src python scripts/ngxrot_research_workspace.py list --status ACTIVE
PYTHONPATH=src python scripts/ngxrot_research_workspace.py show --id RP-...
PYTHONPATH=src python scripts/ngxrot_research_workspace.py attach-query --id RP-... --query-id ...
PYTHONPATH=src python scripts/ngxrot_research_workspace.py evidence --id RP-... --type query_result --query-id ... --description "..."
PYTHONPATH=src python scripts/ngxrot_research_workspace.py note --id RP-... --type observation --content "..."
PYTHONPATH=src python scripts/ngxrot_research_workspace.py finding --id RP-... --title "..." --statement "..."
PYTHONPATH=src python scripts/ngxrot_research_workspace.py hypothesis --id RP-... --statement "..."
PYTHONPATH=src python scripts/ngxrot_research_workspace.py snapshot --id RP-...
PYTHONPATH=src python scripts/ngxrot_research_workspace.py export --id RP-... --format markdown
PYTHONPATH=src python scripts/ngxrot_research_workspace.py quality --id RP-...
PYTHONPATH=src python scripts/ngxrot_research_workspace.py integrity --id RP-...
```

## 17. Python API

```python
from ngxrot import db, registry
from ngxrot import research_workspace as rw
from ngxrot.research_query import QuerySpec, execute

con, reg = db.connect(), registry.connect_registry()
project = rw.create_project(reg, "title", "research question", scope={...})
result = execute(con, QuerySpec(...), reg=reg)
rw.attach_query(reg, project.research_id, result.query_id)
ev = rw.add_evidence(con, reg, project.research_id, "query_result", {"query_id": result.query_id}, "...")
finding = rw.add_finding(reg, project.research_id, "title", "statement", supporting_evidence=[ev])
snap = rw.snapshot(con, reg, project.research_id)
report = rw.export_markdown(con, reg, project.research_id)
```

## 18. Exports

`export_json()`, `export_markdown()`. The Markdown report assembles
Question -> Scope -> Dataset -> Queries -> Evidence -> Analysis
Artifacts -> Findings -> Hypotheses -> Limitations/Integrity Warnings ->
Reproducibility -> Timeline, entirely from the researcher's own recorded
data. **No investment recommendation is generated** -- verified by an
explicit test asserting "buy"/"sell"/"recommend" never appear in an
export. **No LLM dependency anywhere** (Section 19) -- both exports are
pure Python string/JSON formatting.

## 19. No AI dependency

Every function in `research_workspace.py` is deterministic, local
(SQLite), and testable without network access or an API key. AI-assisted
report writing, if ever added, would sit strictly ABOVE this layer (e.g.
summarizing an already-exported Markdown report) -- it must never become
required for the underlying research record to exist or be correct.

## 20. Limitations (disclosed, not resolved this pass)

- `scope` is not independently validated at project-creation time (only
  when a query is actually executed against it) -- a researcher can
  record an internally inconsistent scope and only discover the mismatch
  when they attach a query.
- The historical-sector-classification gap (no versioning anywhere in
  this schema) is inherited from Phase 2 and surfaces here as an
  integrity warning on every relevant query, not resolved.
- `project_quality_summary`/`integrity_check` can be slow/verbose for a
  project spanning many tickers with a long legacy data-quality backlog
  (Section 12's 3,104-warning example) -- this is an honest reflection
  of real platform state, not a performance defect (benchmarked
  operations are all sub-50ms; see `docs/fre_runs/
  research_workspace_report.md`).
- Branching (Section 9) is intentionally minimal -- no merge, no diff
  between branches.

## 21. Examples

See `scripts/research_workspace_integration_test.py` for a full worked,
passing example (a genuine descriptive research investigation into NGX
sector composition change), and `docs/fre_runs/
research_workspace_report.md` for its output and the performance
benchmarks.
