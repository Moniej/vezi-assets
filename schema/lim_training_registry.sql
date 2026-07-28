-- ============================================================================
-- LIM training-run experiment registry (owner directive, 2026-07-28, LIM-2:
-- "record every training run in an immutable experiment registry so any
-- checkpoint can be traced back to the exact dataset versions used to
-- create it"). Lives in its OWN database file
-- (lim_training/training_registry.sqlite, gitignored -- this .sql schema
-- is the tracked source, same split as schema/registry.sql vs
-- data/registry.sqlite, and as schema/lim_dataset_registry.sql vs
-- lim_training/dataset_registry.sqlite). A THIRD separate registry,
-- deliberately never merged with either of the other two: the quant
-- engine's hypothesis ledger is a different domain; the dataset-version
-- registry answers "what data exists," this one answers "what was ever
-- trained, with what, and how."
--
-- Two-table split mirrors schema/registry.sql's hypotheses/
-- hypothesis_status_log pattern exactly, because a training run is a
-- long-running PROCESS (unlike a quant backtest that computes everything
-- then writes one row) -- training_runs is written ONCE, at start, with
-- every parameter already fixed (so even a run that crashes leaves an
-- honest permanent record of what was attempted); training_run_events is
-- append-only progress/outcome logging on top of that immutable base row.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS training_runs (
    run_id              TEXT PRIMARY KEY,          -- UUID4
    started_at          TEXT NOT NULL,             -- UTC ISO timestamp
    dataset_versions    TEXT NOT NULL,             -- JSON list of "type@version" strings
    dataset_content_hashes TEXT NOT NULL,          -- JSON {version: content_hash}, snapshotted
                                                    -- at run start -- proves exactly which
                                                    -- bytes were used even if a version's
                                                    -- file were ever touched later
    teacher_model_ids   TEXT NOT NULL,             -- JSON list, unioned from the dataset versions used
    base_model          TEXT NOT NULL,             -- e.g. 'unsloth/Qwen3-4B-unsloth-bnb-4bit'
    base_model_revision TEXT,                       -- HF revision/commit hash, if known
    quantization_config TEXT NOT NULL,              -- JSON: load_in_4bit, quant_type, compute_dtype, ...
    lora_config          TEXT NOT NULL,              -- JSON: r, alpha, dropout, target_modules, ...
    hyperparameters      TEXT NOT NULL,              -- JSON: lr, batch_size, grad_accum, max_steps, ...
    seed                 INTEGER NOT NULL,
    git_commit            TEXT,                      -- git commit of the training code at run time
    lim_venv_lock_hash     TEXT,                      -- SHA-256 of requirements.lock.txt (reference
                                                       -- environment fingerprint, per the owner's
                                                       -- "treat the current environment as reference"
                                                       -- instruction -- makes an environment drift
                                                       -- detectable, not just assumed unchanged)
    notes                  TEXT
);

CREATE INDEX IF NOT EXISTS ix_training_runs_started ON training_runs (started_at);

CREATE TRIGGER IF NOT EXISTS training_runs_no_update
BEFORE UPDATE ON training_runs
BEGIN SELECT RAISE(ABORT, 'training_runs rows are immutable — every parameter is fixed at run start; log progress in training_run_events instead'); END;

CREATE TRIGGER IF NOT EXISTS training_runs_no_delete
BEFORE DELETE ON training_runs
BEGIN SELECT RAISE(ABORT, 'training_runs rows are never deleted — a failed run is still a real record of what was attempted'); END;

CREATE TABLE IF NOT EXISTS training_run_events (
    event_id       INTEGER PRIMARY KEY,
    run_id         TEXT NOT NULL REFERENCES training_runs(run_id),
    event_type     TEXT NOT NULL CHECK (event_type IN
                     ('started', 'checkpoint', 'eval', 'completed', 'failed')),
    occurred_at    TEXT NOT NULL,
    step           INTEGER,
    metrics        TEXT,                      -- JSON: loss, eval_loss, etc., when applicable
    checkpoint_path TEXT                       -- set for event_type='checkpoint' -- the join key
                                                -- that lets a checkpoint directory be traced back
                                                -- to its run_id and, from there, to
                                                -- dataset_versions/teacher_model_ids/git_commit/seed
);

CREATE INDEX IF NOT EXISTS ix_training_events_run ON training_run_events (run_id);
CREATE INDEX IF NOT EXISTS ix_training_events_checkpoint ON training_run_events (checkpoint_path);

CREATE TRIGGER IF NOT EXISTS training_events_no_update
BEFORE UPDATE ON training_run_events
BEGIN SELECT RAISE(ABORT, 'training_run_events rows are immutable — append a new event instead of editing one'); END;

CREATE TRIGGER IF NOT EXISTS training_events_no_delete
BEFORE DELETE ON training_run_events
BEGIN SELECT RAISE(ABORT, 'training_run_events rows are never deleted — the full history of a run is kept, including failures'); END;
