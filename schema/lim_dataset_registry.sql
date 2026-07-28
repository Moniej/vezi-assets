-- ============================================================================
-- LIM dataset-version registry (DATASET_GENERATION_AND_TRAINING_SPEC.md §5).
-- Lives in its OWN database file (lim_training/dataset_registry.sqlite,
-- gitignored -- this .sql schema definition is the tracked source, same
-- split as schema/registry.sql vs data/registry.sqlite) so it can never be
-- conflated with the quant engine's hypothesis ledger (different domain)
-- or touch the AI Intelligence Layer's own schema/schema.sql.
--
-- Immutability enforced at the SQL level, mirroring schema/registry.sql's
-- own experiments table exactly: no UPDATE, no DELETE, ever. A correction
-- is always a NEW version referencing its parent via parent_version.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dataset_versions (
    version              TEXT PRIMARY KEY,        -- e.g. 'financial_reasoning-v1.0.0'
    dataset_type         TEXT NOT NULL,            -- one of schema.TASK_TYPES
    content_hash         TEXT NOT NULL,            -- SHA-256 of the full exported JSONL
    generated_at         TEXT NOT NULL,            -- UTC ISO timestamp
    source_as_of         TEXT NOT NULL,            -- PIT vintage of the source tables read
    export_script_commit TEXT,                     -- git commit of the exporter, if known
    parent_version        TEXT REFERENCES dataset_versions(version),
                                                    -- NULL = full rebuild; set = incremental
    n_accepted            INTEGER NOT NULL,
    n_rejected             INTEGER NOT NULL,
    rejection_reason_counts TEXT NOT NULL,          -- JSON {code: count}
    teacher_model_ids      TEXT NOT NULL,            -- JSON list, e.g. ["gemini-3.6-flash"]
    changelog              TEXT NOT NULL,             -- human-authored: what changed and why
    accepted_path          TEXT NOT NULL,             -- relative path to the accepted-partition JSONL
    rejected_path           TEXT NOT NULL             -- relative path to the rejected-partition JSONL
);

CREATE INDEX IF NOT EXISTS ix_dataset_versions_type ON dataset_versions (dataset_type);

CREATE TRIGGER IF NOT EXISTS dataset_versions_no_update
BEFORE UPDATE ON dataset_versions
BEGIN SELECT RAISE(ABORT, 'dataset versions are immutable — cut a new version, referencing this one as parent_version if it supersedes it'); END;

CREATE TRIGGER IF NOT EXISTS dataset_versions_no_delete
BEFORE DELETE ON dataset_versions
BEGIN SELECT RAISE(ABORT, 'dataset versions are never deleted — a bad version is superseded, not erased'); END;

-- Lineage: every training example's unique_id, keyed to the version that
-- included it and the exact source row ids it traces back to. This is what
-- makes "which versions ever included fact_id=161" and "what does example
-- X trace back to" both answerable without re-parsing every JSONL file.
CREATE TABLE IF NOT EXISTS dataset_example_lineage (
    version        TEXT NOT NULL REFERENCES dataset_versions(version),
    unique_id      TEXT NOT NULL,
    acceptance_status TEXT NOT NULL CHECK (acceptance_status IN ('accepted','rejected')),
    source_fact_id       INTEGER,
    source_implication_id INTEGER,
    source_doc_ids        TEXT,                    -- JSON list
    PRIMARY KEY (version, unique_id)
);

CREATE INDEX IF NOT EXISTS ix_lineage_fact ON dataset_example_lineage (source_fact_id);
CREATE INDEX IF NOT EXISTS ix_lineage_implication ON dataset_example_lineage (source_implication_id);

CREATE TRIGGER IF NOT EXISTS lineage_no_update
BEFORE UPDATE ON dataset_example_lineage
BEGIN SELECT RAISE(ABORT, 'lineage rows are immutable, same as their parent dataset version'); END;

CREATE TRIGGER IF NOT EXISTS lineage_no_delete
BEFORE DELETE ON dataset_example_lineage
BEGIN SELECT RAISE(ABORT, 'lineage rows are never deleted'); END;
