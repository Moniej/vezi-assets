-- ============================================================================
-- Research governance: experiment registry + hypothesis ledger.
-- Lives in its OWN database file (data/registry.sqlite) so rebuilding the
-- market-data DB can never touch the research record.
--
-- Immutability is enforced at the SQL level, not by convention:
--   - experiments: no UPDATE, no DELETE, ever. A rerun is a new row.
--   - hypotheses: no DELETE ever (negative findings are preserved); UPDATE
--     may only touch status / resolved_at / conclusion, and every status
--     change is appended to hypothesis_status_log by the ledger code.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id    TEXT PRIMARY KEY,          -- UUID4
    created_at       TEXT NOT NULL,             -- UTC ISO timestamp
    code_fingerprint TEXT NOT NULL,             -- SHA256 over src/ + schema/ (no git repo yet)
    git_commit       TEXT,                      -- populated if/when repo exists
    config_path      TEXT,
    config_hash      TEXT NOT NULL,             -- SHA256 of resolved config JSON
    config_json      TEXT NOT NULL,             -- full resolved config (reproduce from this)
    hypothesis_id    TEXT,
    stage            TEXT NOT NULL CHECK (stage IN
                       ('plumbing','development','walk_forward','final_oos','placebo')),
    provider         TEXT NOT NULL,             -- sources.name list, comma-joined
    min_confidence   REAL NOT NULL,
    vintage          TEXT,                      -- NULL = latest captures
    sim_start        TEXT NOT NULL,
    sim_end          TEXT NOT NULL,
    lookbacks_months TEXT NOT NULL,             -- JSON list
    top_n            INTEGER NOT NULL,
    rebalance        TEXT NOT NULL,
    construction     TEXT NOT NULL,
    cost_assumptions TEXT NOT NULL,             -- JSON: line items + overrides + confidence
    liquidity_constraints TEXT,                 -- JSON (recorded now, enforced Phase 3)
    seed             INTEGER,
    metrics          TEXT NOT NULL,             -- JSON: ann_return, sharpe, max_dd, ...
    validation_flags TEXT NOT NULL,             -- JSON: pass/fail booleans + caveats
    notes            TEXT
);

CREATE TRIGGER IF NOT EXISTS experiments_no_update
BEFORE UPDATE ON experiments
BEGIN SELECT RAISE(ABORT, 'experiments are immutable — rerun as a new experiment'); END;

CREATE TRIGGER IF NOT EXISTS experiments_no_delete
BEFORE DELETE ON experiments
BEGIN SELECT RAISE(ABORT, 'experiments are immutable — results are never deleted'); END;

CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id TEXT PRIMARY KEY,             -- 'H-001', ...
    description   TEXT NOT NULL,
    motivation    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'untested'
                    CHECK (status IN ('untested','testing','confirmed','rejected')),
    created_at    TEXT NOT NULL,
    resolved_at   TEXT,
    conclusion    TEXT,                         -- REQUIRED when confirmed/rejected
    frozen        INTEGER NOT NULL DEFAULT 0    -- 1 = permanently closed: no
                                                -- status change, no new
                                                -- experiments under this ID
);

CREATE TRIGGER IF NOT EXISTS hypotheses_frozen_guard
BEFORE UPDATE ON hypotheses
WHEN OLD.frozen = 1
BEGIN SELECT RAISE(ABORT, 'hypothesis is FROZEN - start a new hypothesis ID with fresh validation windows'); END;

-- hypothesis_experiments must exist before the trigger below (it fires ON
-- hypothesis_experiments) -- moved up from its original later position,
-- 2026-08-10, a real pre-existing ordering bug: this only ever worked
-- against an already-populated registry.sqlite where the table already
-- existed from an earlier version of this script; building a FRESH
-- registry.sqlite from this file (e.g. Research OS's scratch-DB tests)
-- failed with "no such table: main.hypothesis_experiments". CREATE TABLE
-- IF NOT EXISTS makes this move a no-op against any existing database.
CREATE TABLE IF NOT EXISTS hypothesis_experiments (
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(hypothesis_id),
    experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
    PRIMARY KEY (hypothesis_id, experiment_id)
);

CREATE TRIGGER IF NOT EXISTS no_experiments_on_frozen
BEFORE INSERT ON hypothesis_experiments
WHEN (SELECT frozen FROM hypotheses
      WHERE hypothesis_id = NEW.hypothesis_id) = 1
BEGIN SELECT RAISE(ABORT, 'hypothesis is FROZEN - new experiments require a new hypothesis ID'); END;

CREATE TRIGGER IF NOT EXISTS hypotheses_no_delete
BEFORE DELETE ON hypotheses
BEGIN SELECT RAISE(ABORT, 'ledger entries are never deleted — negative findings are findings'); END;

CREATE TRIGGER IF NOT EXISTS hypotheses_guard_immutable_fields
BEFORE UPDATE ON hypotheses
WHEN OLD.hypothesis_id != NEW.hypothesis_id
  OR OLD.description   != NEW.description
  OR OLD.motivation    != NEW.motivation
  OR OLD.created_at    != NEW.created_at
BEGIN SELECT RAISE(ABORT, 'only status/resolved_at/conclusion may change on a hypothesis'); END;

CREATE TRIGGER IF NOT EXISTS hypotheses_resolution_needs_conclusion
BEFORE UPDATE ON hypotheses
WHEN NEW.status IN ('confirmed','rejected')
 AND (NEW.conclusion IS NULL OR NEW.conclusion = '')
BEGIN SELECT RAISE(ABORT, 'confirmed/rejected requires a written conclusion'); END;

CREATE TABLE IF NOT EXISTS hypothesis_status_log (
    log_id        INTEGER PRIMARY KEY,
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(hypothesis_id),
    old_status    TEXT,
    new_status    TEXT NOT NULL,
    changed_at    TEXT NOT NULL,
    reason        TEXT
);

-- ============================================================================
-- Research OS, 2026-08-10 (docs/RESEARCH_OS_ARCHITECTURE.md): generic
-- dataset/run reproducibility, deliberately NOT alpha/backtest-specific
-- (no signal/portfolio/costs columns, unlike `experiments` above). A
-- `research_run` may be purely descriptive ("what is the IRU's data
-- coverage profile") -- it does not require or imply a trading hypothesis.
-- Same immutability discipline as `experiments`/`hypotheses`: insert-only,
-- trigger-enforced, in the SAME registry.sqlite file (no new database).
-- ============================================================================

CREATE TABLE IF NOT EXISTS dataset_snapshots (
    snapshot_id       TEXT PRIMARY KEY,          -- UUID4
    created_at        TEXT NOT NULL,             -- UTC ISO timestamp
    code_fingerprint  TEXT NOT NULL,
    git_commit        TEXT,
    dataset_kind      TEXT NOT NULL,              -- e.g. 'equity_prices_range'
    query_params_json TEXT NOT NULL,              -- exact params used (reproduce the query from this)
    row_count         INTEGER NOT NULL,
    content_hash      TEXT NOT NULL,              -- SHA256 over the returned rows, deterministic
    universe_version  TEXT,                       -- IRU version, if a universe filter was applied
    notes             TEXT
);

CREATE TRIGGER IF NOT EXISTS dataset_snapshots_no_update
BEFORE UPDATE ON dataset_snapshots
BEGIN SELECT RAISE(ABORT, 'dataset snapshots are immutable — requery to get a new snapshot'); END;

CREATE TRIGGER IF NOT EXISTS dataset_snapshots_no_delete
BEFORE DELETE ON dataset_snapshots
BEGIN SELECT RAISE(ABORT, 'dataset snapshots are immutable — never deleted'); END;

CREATE TABLE IF NOT EXISTS research_runs (
    run_id                    TEXT PRIMARY KEY,   -- UUID4
    created_at                TEXT NOT NULL,
    code_fingerprint          TEXT NOT NULL,
    git_commit                TEXT,
    hypothesis_id             TEXT,               -- optional link into hypotheses; NULL for
                                                    -- purely descriptive/infrastructure runs
    research_question         TEXT NOT NULL,       -- free text; may be descriptive, not necessarily alpha
    dataset_snapshot_ids_json TEXT NOT NULL,       -- JSON list of dataset_snapshots.snapshot_id used
    universe_version          TEXT,
    observation_period_start  TEXT,
    observation_period_end    TEXT,
    transformations_json      TEXT NOT NULL,       -- JSON list of named transformation steps (may be [])
    analysis_method           TEXT,                -- free text description, nullable
    results_json              TEXT NOT NULL,       -- JSON: whatever the analysis produced
    notes                     TEXT
);

CREATE TRIGGER IF NOT EXISTS research_runs_no_update
BEFORE UPDATE ON research_runs
BEGIN SELECT RAISE(ABORT, 'research runs are immutable — rerun as a new run'); END;

CREATE TRIGGER IF NOT EXISTS research_runs_no_delete
BEFORE DELETE ON research_runs
BEGIN SELECT RAISE(ABORT, 'research runs are immutable — never deleted'); END;

-- ============================================================================
-- Research OS, 2026-08-10, Phase 2 (docs/research_query_layer.md): a
-- lightweight, automatic log of every executed research_query.py
-- QuerySpec -- reproducibility of "what did I ask", NOT a duplicate data
-- store. Deliberately does NOT store the observations DataFrame itself.
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_log (
    query_id           TEXT PRIMARY KEY,          -- UUID4, matches QueryResult.query_id
    executed_at        TEXT NOT NULL,
    code_fingerprint   TEXT NOT NULL,
    query_type         TEXT NOT NULL,
    parameters_json    TEXT NOT NULL,              -- full QuerySpec, reproduce the query from this
    row_count          INTEGER NOT NULL,
    date_range_start   TEXT,
    date_range_end     TEXT,
    data_sources_json  TEXT NOT NULL,
    warnings_json      TEXT NOT NULL,
    content_hash       TEXT NOT NULL,              -- SHA256 over the result rows, deterministic
    entities_requested_json TEXT                    -- QueryResult.entities_requested (may differ from
                                                      -- parameters_json's requested entities for
                                                      -- cross_section queries, whose tickers are
                                                      -- RESOLVED from a sector filter, not passed in)
);

CREATE TRIGGER IF NOT EXISTS query_log_no_update
BEFORE UPDATE ON query_log
BEGIN SELECT RAISE(ABORT, 'query_log is immutable — every execution is a new row'); END;

CREATE TRIGGER IF NOT EXISTS query_log_no_delete
BEFORE DELETE ON query_log
BEGIN SELECT RAISE(ABORT, 'query_log is immutable — never deleted'); END;

-- ============================================================================
-- Research OS, 2026-08-10, Phase 3 (docs/research_workspace.md): a complete
-- research investigation as a first-class, reproducible object. Sits ON TOP
-- of query_log/dataset_snapshots (Phase 2/1) -- references their ids, never
-- copies their data. All in the SAME registry.sqlite (no new database).
--
-- NOTE on `research_hypotheses` vs the pre-existing `hypotheses` table
-- above: deliberately separate, same reasoning as dataset_snapshots/
-- research_runs vs experiments/hypotheses in Phase 1. `hypotheses` is
-- alpha-backtest-shaped (status vocabulary untested/testing/confirmed/
-- rejected, linked to `experiments` via hypothesis_experiments).
-- `research_hypotheses` is generic research-workflow tracking (status
-- vocabulary OPEN/SUPPORTED/WEAKENED/REJECTED/UNRESOLVED, linked to
-- `research_findings`, not to any alpha experiment). Not merged.
-- ============================================================================

CREATE TABLE IF NOT EXISTS research_projects (
    research_id       TEXT PRIMARY KEY,               -- UUID4
    title             TEXT NOT NULL,
    research_question TEXT NOT NULL,
    description       TEXT,
    status            TEXT NOT NULL DEFAULT 'DRAFT'
                        CHECK (status IN ('DRAFT','ACTIVE','PAUSED','COMPLETED','ARCHIVED')),
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    owner             TEXT,
    tags_json         TEXT NOT NULL DEFAULT '[]',
    scope_json        TEXT,                            -- universe/securities/sectors/date range/as_of/sources/fields
    dataset_snapshot_ids_json TEXT NOT NULL DEFAULT '[]',  -- references Phase-1 dataset_snapshots.snapshot_id
    code_fingerprint  TEXT NOT NULL,                    -- fingerprint AT CREATION time
    parent_research_id TEXT REFERENCES research_projects(research_id)  -- branching (Section 17)
);

-- Once ARCHIVED, a project is frozen -- no field may change again (same
-- "frozen" discipline as hypotheses_frozen_guard above). Before that,
-- status/description/tags/scope/dataset_snapshot_ids/updated_at may
-- change; research_id/title/research_question/created_at/owner/
-- code_fingerprint/parent_research_id may not (guarded below).
CREATE TRIGGER IF NOT EXISTS research_projects_frozen_guard
BEFORE UPDATE ON research_projects
WHEN OLD.status = 'ARCHIVED'
BEGIN SELECT RAISE(ABORT, 'research project is ARCHIVED — frozen, start a new project (optionally with parent_research_id set)'); END;

CREATE TRIGGER IF NOT EXISTS research_projects_guard_immutable_fields
BEFORE UPDATE ON research_projects
WHEN OLD.research_id != NEW.research_id
  OR OLD.title != NEW.title
  OR OLD.research_question != NEW.research_question
  OR OLD.created_at != NEW.created_at
  OR OLD.code_fingerprint != NEW.code_fingerprint
BEGIN SELECT RAISE(ABORT, 'only status/description/tags/scope/dataset_snapshot_ids/updated_at may change on a research project'); END;

CREATE TRIGGER IF NOT EXISTS research_projects_no_delete
BEFORE DELETE ON research_projects
BEGIN SELECT RAISE(ABORT, 'research projects are never deleted — archive instead'); END;

CREATE TABLE IF NOT EXISTS research_project_queries (
    research_id  TEXT NOT NULL REFERENCES research_projects(research_id),
    query_id     TEXT NOT NULL REFERENCES query_log(query_id),
    attached_at  TEXT NOT NULL,
    note         TEXT,
    PRIMARY KEY (research_id, query_id)
);

CREATE TRIGGER IF NOT EXISTS research_project_queries_no_update
BEFORE UPDATE ON research_project_queries
BEGIN SELECT RAISE(ABORT, 'a query attachment is immutable — its note is fixed at attach time'); END;

CREATE TRIGGER IF NOT EXISTS research_project_queries_no_delete
BEFORE DELETE ON research_project_queries
BEGIN SELECT RAISE(ABORT, 'a query attachment is never deleted — it is part of the audit trail'); END;

CREATE TABLE IF NOT EXISTS research_notes (
    note_id      TEXT PRIMARY KEY,
    research_id  TEXT NOT NULL REFERENCES research_projects(research_id),
    note_type    TEXT NOT NULL CHECK (note_type IN
                   ('observation','interpretation','question','assumption','decision','warning')),
    content      TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS research_notes_no_update
BEFORE UPDATE ON research_notes
BEGIN SELECT RAISE(ABORT, 'research notes are immutable — add a new note instead of editing'); END;

CREATE TRIGGER IF NOT EXISTS research_notes_no_delete
BEFORE DELETE ON research_notes
BEGIN SELECT RAISE(ABORT, 'research notes are never deleted'); END;

CREATE TABLE IF NOT EXISTS research_evidence (
    evidence_id     TEXT PRIMARY KEY,
    research_id     TEXT NOT NULL REFERENCES research_projects(research_id),
    evidence_type   TEXT NOT NULL CHECK (evidence_type IN
                      ('query_result','dataset_observation','source_document','company_metadata',
                       'corporate_action','historical_event','calculation','chart_table')),
    source_reference_json TEXT NOT NULL,     -- e.g. {"query_id":...} or {"ticker":...,"trade_date":...}
    description     TEXT NOT NULL,
    provenance_json  TEXT,                    -- populated via lineage.py where resolvable; NULL is disclosed, not hidden
    created_at      TEXT NOT NULL,
    claim_class     TEXT                       -- Phase 4: FACT/OBSERVATION/MEASUREMENT/DOCUMENT/CONTEXT/
                                                 -- ASSUMPTION/INTERPRETATION, validated in Python (not a DB
                                                 -- CHECK, to avoid a table-rebuild migration); NULL = unclassified
);

CREATE TRIGGER IF NOT EXISTS research_evidence_no_update
BEFORE UPDATE ON research_evidence
BEGIN SELECT RAISE(ABORT, 'evidence is immutable — record new evidence instead of editing'); END;

CREATE TRIGGER IF NOT EXISTS research_evidence_no_delete
BEFORE DELETE ON research_evidence
BEGIN SELECT RAISE(ABORT, 'evidence is never deleted'); END;

CREATE TABLE IF NOT EXISTS research_findings (
    finding_id      TEXT PRIMARY KEY,
    research_id     TEXT NOT NULL REFERENCES research_projects(research_id),
    title           TEXT NOT NULL,
    statement       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PRELIMINARY'
                      CHECK (status IN ('PRELIMINARY','SUPPORTED','CONTESTED','REJECTED','UNRESOLVED')),
    supporting_evidence_json TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS research_findings_guard_immutable_fields
BEFORE UPDATE ON research_findings
WHEN OLD.finding_id != NEW.finding_id OR OLD.title != NEW.title
  OR OLD.statement != NEW.statement OR OLD.created_at != NEW.created_at
BEGIN SELECT RAISE(ABORT, 'only status/supporting_evidence/updated_at may change on a finding'); END;

CREATE TRIGGER IF NOT EXISTS research_findings_no_delete
BEFORE DELETE ON research_findings
BEGIN SELECT RAISE(ABORT, 'findings are never deleted — a finding can be REJECTED, not erased'); END;

CREATE TABLE IF NOT EXISTS research_findings_status_log (
    log_id       INTEGER PRIMARY KEY,
    finding_id   TEXT NOT NULL REFERENCES research_findings(finding_id),
    old_status   TEXT,
    new_status   TEXT NOT NULL,
    changed_at   TEXT NOT NULL,
    reason       TEXT
);

CREATE TABLE IF NOT EXISTS research_hypotheses (
    hypothesis_id   TEXT PRIMARY KEY,
    research_id     TEXT NOT NULL REFERENCES research_projects(research_id),
    statement       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OPEN'
                      CHECK (status IN ('OPEN','SUPPORTED','WEAKENED','REJECTED','UNRESOLVED')),
    supporting_finding_ids_json    TEXT NOT NULL DEFAULT '[]',
    contradicting_finding_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    confidence                REAL,             -- Phase 4: researcher's own 0-1 confidence, optional
    reason_for_investigation  TEXT,              -- Phase 4: why this hypothesis was worth investigating
    researcher_notes          TEXT               -- Phase 4: free-text researcher commentary
);

CREATE TRIGGER IF NOT EXISTS research_hypotheses_guard_immutable_fields
BEFORE UPDATE ON research_hypotheses
WHEN OLD.hypothesis_id != NEW.hypothesis_id OR OLD.statement != NEW.statement
  OR OLD.created_at != NEW.created_at
BEGIN SELECT RAISE(ABORT, 'only status/supporting/contradicting findings/updated_at may change on a hypothesis'); END;

CREATE TRIGGER IF NOT EXISTS research_hypotheses_no_delete
BEFORE DELETE ON research_hypotheses
BEGIN SELECT RAISE(ABORT, 'research hypotheses are never deleted — a hypothesis can be REJECTED, not erased'); END;

CREATE TABLE IF NOT EXISTS research_hypotheses_status_log (
    log_id         INTEGER PRIMARY KEY,
    hypothesis_id  TEXT NOT NULL REFERENCES research_hypotheses(hypothesis_id),
    old_status     TEXT,
    new_status     TEXT NOT NULL,
    changed_at     TEXT NOT NULL,
    reason         TEXT
);

CREATE TABLE IF NOT EXISTS research_artifacts (
    artifact_id     TEXT PRIMARY KEY,
    research_id     TEXT NOT NULL REFERENCES research_projects(research_id),
    artifact_type   TEXT NOT NULL CHECK (artifact_type IN
                      ('table','summary_statistics','comparison','chart','data_extract',
                       'calculation','research_note')),
    source_query_id TEXT REFERENCES query_log(query_id),
    parameters_json TEXT NOT NULL DEFAULT '{}',
    content_hash    TEXT NOT NULL,
    payload_json    TEXT,                     -- inline for small artifacts (table/chart spec); large results stay referenced by source_query_id instead
    created_at      TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS research_artifacts_no_update
BEFORE UPDATE ON research_artifacts
BEGIN SELECT RAISE(ABORT, 'artifacts are immutable — a re-analysis is a new artifact'); END;

CREATE TRIGGER IF NOT EXISTS research_artifacts_no_delete
BEFORE DELETE ON research_artifacts
BEGIN SELECT RAISE(ABORT, 'artifacts are never deleted'); END;

CREATE TABLE IF NOT EXISTS research_snapshots (
    research_snapshot_id TEXT PRIMARY KEY,
    research_id       TEXT NOT NULL REFERENCES research_projects(research_id),
    created_at        TEXT NOT NULL,
    code_fingerprint  TEXT NOT NULL,
    git_commit        TEXT,
    project_state_json TEXT NOT NULL,          -- full frozen copy: project row + note/evidence/finding/hypothesis/artifact ids+hashes
    content_hash      TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS research_snapshots_no_update
BEFORE UPDATE ON research_snapshots
BEGIN SELECT RAISE(ABORT, 'research snapshots are immutable — freeze a new one instead'); END;

CREATE TRIGGER IF NOT EXISTS research_snapshots_no_delete
BEFORE DELETE ON research_snapshots
BEGIN SELECT RAISE(ABORT, 'research snapshots are never deleted'); END;

CREATE TABLE IF NOT EXISTS research_timeline (
    event_id     INTEGER PRIMARY KEY,
    research_id  TEXT NOT NULL REFERENCES research_projects(research_id),
    event_type   TEXT NOT NULL,   -- 'created'|'question_defined'|'scope_defined'|'query_attached'|
                                   -- 'evidence_added'|'note_added'|'finding_recorded'|
                                   -- 'finding_status_changed'|'hypothesis_added'|
                                   -- 'hypothesis_status_changed'|'artifact_added'|
                                   -- 'snapshot_created'|'status_changed'|'exported'
    detail       TEXT,
    occurred_at  TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS research_timeline_no_update
BEFORE UPDATE ON research_timeline
BEGIN SELECT RAISE(ABORT, 'the research timeline is immutable — it is an audit trail, not editable history'); END;

CREATE TRIGGER IF NOT EXISTS research_timeline_no_delete
BEFORE DELETE ON research_timeline
BEGIN SELECT RAISE(ABORT, 'the research timeline is never deleted'); END;

-- ============================================================================
-- Research OS, 2026-08-10, Phase 4 (docs/research_applications.md): the
-- first two genuinely NEW capabilities Phases 1-3 did not provide --
-- contradiction tracking and a formal conclusion object -- plus additive
-- columns on Phase 3's evidence/hypothesis tables (claim classification,
-- confidence/reasoning). An "investigation" is simply a `research_projects`
-- row (Phase 3) with a structured `scope_json` -- NOT a new project table.
-- ============================================================================

CREATE TABLE IF NOT EXISTS research_contradictions (
    contradiction_id  TEXT PRIMARY KEY,
    research_id       TEXT NOT NULL REFERENCES research_projects(research_id),
    description       TEXT NOT NULL,
    item_a_json       TEXT NOT NULL,             -- {"source":..., "claim":..., "evidence_id":...}
    item_b_json       TEXT NOT NULL,              -- the conflicting counterpart
    status            TEXT NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN','INVESTIGATED','RESOLVED')),
    resolution_note   TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS research_contradictions_guard_immutable_fields
BEFORE UPDATE ON research_contradictions
WHEN OLD.contradiction_id != NEW.contradiction_id OR OLD.description != NEW.description
  OR OLD.item_a_json != NEW.item_a_json OR OLD.item_b_json != NEW.item_b_json
  OR OLD.created_at != NEW.created_at
BEGIN SELECT RAISE(ABORT, 'only status/resolution_note/updated_at may change on a contradiction -- the conflicting claims themselves are never edited, only annotated'); END;

CREATE TRIGGER IF NOT EXISTS research_contradictions_no_delete
BEFORE DELETE ON research_contradictions
BEGIN SELECT RAISE(ABORT, 'contradictions are never deleted -- a RESOLVED one still records that a conflict existed and how it was addressed'); END;

CREATE TABLE IF NOT EXISTS research_contradictions_status_log (
    log_id            INTEGER PRIMARY KEY,
    contradiction_id  TEXT NOT NULL REFERENCES research_contradictions(contradiction_id),
    old_status        TEXT,
    new_status        TEXT NOT NULL,
    changed_at        TEXT NOT NULL,
    reason            TEXT
);

CREATE TABLE IF NOT EXISTS research_conclusions (
    conclusion_id      TEXT PRIMARY KEY,
    research_id        TEXT NOT NULL REFERENCES research_projects(research_id),
    statement          TEXT NOT NULL,
    state              TEXT NOT NULL CHECK (state IN
                         ('SUPPORTED','PARTIALLY_SUPPORTED','INCONCLUSIVE','CONTRADICTED',
                          'INSUFFICIENT_DATA')),
    supporting_evidence_json    TEXT NOT NULL DEFAULT '[]',
    contradicting_evidence_json TEXT NOT NULL DEFAULT '[]',
    uncertainties      TEXT,                      -- "what remains uncertain"
    limitations        TEXT,                       -- "what data limitations exist"
    further_research   TEXT,                       -- "what additional research would be required"
    created_at         TEXT NOT NULL
);

-- A conclusion is a POINT-IN-TIME record, not a mutable "current answer" --
-- superseding a conclusion means recording a NEW one (same append-only
-- discipline as everything else); the latest by created_at is the current
-- one. Never edited in place.
CREATE TRIGGER IF NOT EXISTS research_conclusions_no_update
BEFORE UPDATE ON research_conclusions
BEGIN SELECT RAISE(ABORT, 'conclusions are immutable -- record a new conclusion instead of editing'); END;

CREATE TRIGGER IF NOT EXISTS research_conclusions_no_delete
BEFORE DELETE ON research_conclusions
BEGIN SELECT RAISE(ABORT, 'conclusions are never deleted'); END;
