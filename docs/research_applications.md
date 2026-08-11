# Research Applications (Phase 4)

**Status**: The first research-APPLICATION layer. Everything here is
descriptive: it answers "what happened, what evidence supports it, what
changed, what remains uncertain" -- never "what should I trade?". No
momentum/relative-strength/sector-rotation/alpha-factor/predictive-
model/trading-signal/portfolio-optimization/backtest code exists
anywhere in this module.

---

## 1. Architecture

```
Data Sources -> Providers -> DataProvider -> Ingestion -> SQLite PIT
    -> Identity -> Lineage -> Quality (Phase 1)
    -> Research Query Layer (Phase 2)
    -> Research Workspace (Phase 3)
    ══════════════════════════════════
     PHASE 4 -- RESEARCH APPLICATIONS
    ══════════════════════════════════
```

`src/ngxrot/research_applications.py` is the only new module. It calls
Phase 2's `research_query.execute()` for every data access and Phase 3's
`research_workspace.py` for every project/evidence/finding/hypothesis/
artifact/snapshot operation -- it runs no ad-hoc SQL against the market-
data DB except the same kind of thin, read-only composition Phase 1's
`research_quality.py`/`lineage.py`/`instrument_identity.py` already
established.

**Genuinely new** (schema/registry.sql, "Phase 4" section, additive):
`research_contradictions` (+ status log) and `research_conclusions`.
Everything else is either a direct reuse of Phase 3 objects or an
additive column on an existing Phase 3 table (`research_evidence.
claim_class`, `research_hypotheses.confidence`/`reason_for_
investigation`/`researcher_notes`).

## 2. An investigation IS a research_workspace project

`create_investigation()` is a thin wrapper around `rw.create_project()`
that structures `scope` consistently (`entities`/`sectors`/`universes`/
`indices`/`date_range`/`as_of`/`research_objective`) instead of leaving
it free-form. **No competing project model was built.**

`set_investigation_status()` maps the spec's 5-state vocabulary onto
Phase 3's existing `research_projects.status` CHECK constraint
(`DRAFT`/`ACTIVE`/`PAUSED`/`COMPLETED`/`ARCHIVED`). `REVIEW` is
deliberately **not** added as a real database state -- it is recorded as
an `ACTIVE` status plus a `decision`-type note ("investigation entered
REVIEW"), avoiding a CHECK-constraint rewrite for one extra transient
state. Documented, not hidden.

## 3. Research plan

`record_research_plan()` stores measurements/required-data/comparisons/
evidence-criteria/limitations as a structured `research_note` artifact
(Phase 3's existing artifact mechanism, `artifact_type='research_note'`,
tagged `{"kind": "research_plan"}`). This is immutable (artifacts are
insert-only) -- a later re-analysis records a NEW plan, never edits the
original. The project's own `research_question` field is separately
immutable at the database level (Phase 3's guard trigger), so no
analysis can silently drift the original question.

## 4. Evidence classification

`add_classified_evidence()` requires one of `FACT`/`OBSERVATION`/
`MEASUREMENT`/`DOCUMENT`/`CONTEXT`/`ASSUMPTION`/`INTERPRETATION`.
Implemented as an additive, nullable `claim_class` column directly on
Phase 3's `research_evidence` table (extended `rw.add_evidence()` to
accept it as an optional parameter) -- **not** a new evidence table.
Because `research_evidence` is immutable (insert-only, no UPDATE), the
class must be set at creation time; a first draft of this module tried
to classify evidence via `UPDATE` after the fact and was correctly
blocked by Phase 3's own immutability trigger (a real bug caught
immediately by a live smoke test, fixed by threading `claim_class`
through the original INSERT instead).

Worked example (`scripts/research_applications_integration_test.py`,
Investigation C): "Pre-event mean close 5.18 vs post-event mean close
4.03" is tagged `MEASUREMENT`; "This decline is consistent with, though
not proven to be solely caused by, the documented bonus issue" is tagged
`INTERPRETATION` -- explicitly kept as two separate evidence records,
never merged into one claim.

## 5. Hypotheses -- extended workflow, not extended alpha functionality

`add_researched_hypothesis()`/`set_hypothesis_confidence()` add
`reason_for_investigation`, `confidence` (0-1, validated), and
`researcher_notes` as additive nullable columns on Phase 3's existing
`research_hypotheses` table. Status transitions (`OPEN`/`SUPPORTED`/
`WEAKENED`/`REJECTED`/`UNRESOLVED`) reuse Phase 3's
`rw.update_hypothesis_status()` unchanged -- this module never
introduces a second status-transition mechanism.

**Deliberately not done**: widening `research_hypotheses`' status CHECK
constraint to the spec's own vocabulary (`UNTESTED`/`WEAKLY_SUPPORTED`/
`INCONCLUSIVE`/`CONTRADICTED`). SQLite cannot `ALTER` a CHECK
constraint in place; doing so would require the same table-rebuild
migration pattern used elsewhere in this codebase (e.g. `db.py`'s
`_migrate_entities_table`) for what is ultimately a cosmetic vocabulary
difference. Phase 3's existing 5 statuses cover the same semantic space
(`OPEN`~`UNTESTED`, `WEAKENED`~`WEAKLY_SUPPORTED`, `UNRESOLVED`~
`INCONCLUSIVE`, `REJECTED`~`CONTRADICTED`/`REJECTED`) and remain
authoritative.

## 6. Contradiction detection -- genuinely new

`research_contradictions` records `item_a`/`item_b` (each `{source,
claim, ...}`), a `status` (`OPEN`/`INVESTIGATED`/`RESOLVED`), and a
`resolution_note`. **Never auto-resolves**: `detect_source_conflicts()`
reuses Phase 1's `research_quality.source_conflicts()` to find real
multi-source price disagreements among a project's attached-query
tickers and records each as an `OPEN` contradiction -- it does not pick
a "winning" source. `record_contradiction()` supports manual recording
for anything not detectable purely from `equity_prices` (e.g. a sector-
classification disagreement between two named sources).

Worked example (Investigation C): 159 legacy, pre-existing
`data_quality_log` `unexplained_jump` flags for CILEASING's 2024-01-05
window were recognized as a real contradiction against this session's
own Phase-1 `unadjusted_jump` finding (which explains the same price
move) -- recorded, then explicitly `RESOLVED` with a written
resolution note, rather than silently ignored or silently trusted.

## 7. Descriptive analysis toolkit

`descriptive_summary` (count/mean/median/std/min/max/q25/q75),
`growth_rate`, `group_comparison`, `period_over_period_change`,
`before_after_comparison` -- pure functions over pandas
Series/DataFrames. None of these produce a ranking, score, or signal;
`group_comparison`'s test explicitly asserts no `rank`/`score` column
ever appears in its output.

## 8. Company research

`company_profile(con, reg, ticker, start=, end=, research_id=)` composes:
real identity/rename chain (`instrument_identity.py`), real
`securities` metadata, real price/volume descriptive statistics (via a
Phase-2 `prices` query, auto-attached to the investigation if
`research_id` is given), real corporate-action notes and data-quality
flags (`research_quality.py`), real universe/index membership, and
(if `research_id` given) the investigation's own findings mentioning
this ticker. **Every unavailable field is explicitly `None` or a
descriptive "not requested"/"not available" string** -- verified live:
`securities.metadata` is `None` for a nonexistent ticker, and
`price_history` is the literal string `"not requested -- pass
start/end to include"` when no window is given, never a fabricated
empty-looking structure.

## 9. Sector research

`sector_profile(con, reg, sector, as_of_dates, research_id=)` -- one
Phase-2 `cross_section` query per as-of date, plus real entries/exits
computed by set-differencing consecutive snapshots. Every profile
carries an explicit disclosure: `sector_ngx` has no historical
versioning in this schema, so every snapshot uses today's classification
-- entries/exits reflect membership changes under a constant, current-
day taxonomy, not a changing historical one.

## 10. Event research -- descriptive only

`event_window(con, reg, ticker, event_date, pre_days=, post_days=,
research_id=)` pulls a real price/volume window (via a Phase-2 `prices`
query), computes descriptive before/after statistics, counts missing
observations against the real NGX trading calendar, and surfaces
data-quality flags for the window. **No `expected_return`/`signal`/
`alpha_score` field exists anywhere in its output** -- asserted directly
in the test suite. Worked live on CILEASING's real 2024-01-05 bonus
issue: pre-window mean close 5.18 -> post-window mean close 4.03, a real,
disclosed, unadjusted price effect (Section 6's contradiction-resolution
example).

## 11. Comparative research

`compare_entities()` wraps Phase 2's `compare` query type and adds a
comparability check: if data availability (`n_observations`) differs by
more than 10% across the compared entities, an explicit warning is
attached rather than silently presenting an apples-to-oranges
comparison.

## 12. Research tables

`make_entity_metric_table()` pivots a query result (date x ticker) and
stores it as a Phase-3 `table` artifact, traceable back to
`source_query_id`.

## 13. Charts

Not rebuilt -- Phase 3's `rw.make_chart_spec()` (declarative, data +
axis mapping, not a rendered image) is reused directly wherever a Phase
4 composer wants one; no second charting mechanism was introduced.

## 14. Quality gate -- actually gates completion

`run_quality_gate(con, reg, research_id)` checks: zero attached queries
(blocking), any `OPEN` contradictions (blocking), plus every integrity
warning `rw.integrity_check()` already surfaces (survivorship, missing
provenance, unresolved data-quality flags -- carried forward as
warnings, not blocking). `complete_investigation()` **refuses** to mark
an investigation `COMPLETED` while blocking issues remain, unless
`force=True` -- and forcing always writes a `warning`-type note that
survives into the final report. Verified live: an investigation with
zero queries fails the gate and is refused completion; force-completing
it still leaves the warning visible.

**A real ordering bug found and fixed**: the first implementation
snapshotted the project's state, then set its status to `COMPLETED` --
meaning `check_reproducibility()` immediately reported spurious drift
right after completion, since the frozen snapshot didn't match the
just-changed live status. Fixed by setting status to `COMPLETED` first,
snapshotting second, so the frozen state genuinely matches the final
state.

## 15. Conclusion framework

`research_conclusions` is a point-in-time, insert-only record (a
superseding conclusion is a NEW row, never an edit) with a required
`state` (`SUPPORTED`/`PARTIALLY_SUPPORTED`/`INCONCLUSIVE`/
`CONTRADICTED`/`INSUFFICIENT_DATA`) plus free-text `uncertainties`/
`limitations`/`further_research`. **Never forced positive**: all three
end-to-end demonstration investigations recorded `PARTIALLY_SUPPORTED`
or `SUPPORTED` states with explicit, real caveats (unadjusted prices,
incomplete corporate-action coverage, current-day-only sector
classification) rather than a clean, confident-sounding but unearned
conclusion.

## 16. Research report generator

`generate_investigation_report()` extends Phase 3's `export_markdown`
shape with Contradictions, Quality Gate, and Conclusion sections, and
labels every statement `[FACT/ANALYSIS]`, `[<claim_class>]`, or
`[CONCLUSION, <state>]` inline. Verified: never contains "buy"/"sell"/
investment-recommendation language, never leaks the NGX Pulse API key,
in every one of the 4 test/demonstration reports generated this phase.

## 17. Research templates

`RESEARCH_TEMPLATES` (8, as required): `company_profile`,
`sector_composition`, `sector_change`, `company_comparison`,
`historical_universe_analysis`, `event_investigation`,
`data_quality_investigation`, `market_structure_investigation`. Each is
pure metadata (`questions`/`required_data`/`analysis`/
`expected_outputs`/`quality_checks`) -- verified no template contains a
`conclusion` field; nothing is hard-coded toward a particular outcome.

## 18. CLI

`scripts/ngxrot_research_apps.py` (companion to Phase 2's
`ngxrot_research.py` and Phase 3's `ngxrot_research_workspace.py`, same
argparse convention): `investigate`, `company`, `sector`, `compare`,
`event`, `quality-gate`, `conclude`, `complete`, `report`, `templates`.
Every command routes through `research_applications.py`, which itself
routes through Phase 2's query layer and Phase 3's workspace -- no
command bypasses either with direct SQL.

## 19. Python API

```python
from ngxrot import db, registry
from ngxrot import research_applications as ra

con, reg = db.connect(), registry.connect_registry()
p = ra.create_investigation(reg, "title", "question", entities=["GTCO"], start="2023-01-01", end="2024-01-01")
profile = ra.company_profile(con, reg, "GTCO", start="2023-01-01", end="2024-01-01", research_id=p.research_id)
gate = ra.run_quality_gate(con, reg, p.research_id)
result = ra.complete_investigation(con, reg, p.research_id, "conclusion statement", "SUPPORTED")
report = ra.generate_investigation_report(con, reg, p.research_id)
```

## 20. Reproducibility

Every investigation's completion freezes a real Phase-3 snapshot
(content-hash based) -- verified for all three end-to-end demonstration
investigations: `check_reproducibility()` reports `unchanged=True`
immediately after `complete_investigation()` returns. A future
researcher reconstructs the investigation from: the recorded research
question (immutable), the research plan (artifact), every attached
`query_id` (Phase 2's own `query_log`, independently reproducible by
content hash), every evidence/finding/hypothesis/contradiction id, and
the code fingerprint captured at project creation.

## 21. Limitations (disclosed, not resolved this pass)

- `REVIEW` is not a real database status (Section 2) -- represented via
  a note, not a state transition.
- `research_hypotheses`' status vocabulary was not widened to match this
  phase's spec text (Section 5) -- documented mapping instead.
- `event_window()`/`company_profile()` (with a window) inherit Phase 2's
  hard rejection of unknown tickers (`QueryValidationError`) rather than
  returning a soft "not found" result -- consistent with the rest of
  the platform's guardrail philosophy, verified in tests.
- `detect_source_conflicts()` only checks price disagreement; sector-
  classification or corporate-action conflicts must still be recorded
  manually via `record_contradiction()` (no automated detector exists
  for those yet).
- No AI/LLM dependency anywhere in this module (unchanged from Phase 3's
  own commitment).

## 22. Examples

`scripts/research_applications_integration_test.py` runs THREE real,
descriptive investigations end to end (sector composition, company
profile, event study) -- see `docs/fre_runs/
research_applications_report.md` for full output.
