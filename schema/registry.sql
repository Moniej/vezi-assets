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

CREATE TABLE IF NOT EXISTS hypothesis_experiments (
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses(hypothesis_id),
    experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
    PRIMARY KEY (hypothesis_id, experiment_id)
);
