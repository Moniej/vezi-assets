-- ============================================================================
-- LIM evaluation-run registry (owner directive, 2026-07-28, LIM-3: "Store
-- every evaluation in a versioned registry so results remain reproducible
-- and comparable across future model versions"). Lives in its OWN database
-- file (lim_training/eval_registry.sqlite, gitignored) -- a FOURTH registry,
-- deliberately separate from the quant hypothesis ledger, the dataset
-- -version registry, and the training-run registry. Each answers a
-- different question: what data exists, what was trained, and now, how did
-- a given model version actually perform against an objective benchmark.
--
-- Two-table split, same immutable-base + per-example-detail pattern as the
-- other registries: eval_runs is written ONCE, after scoring completes, with
-- the full summary (every requirement in the owner's metric list, plus
-- performance numbers); eval_examples holds one immutable row per scored
-- held-out example, so any aggregate number in eval_runs.metrics can be
-- traced back to the exact per-example scores that produced it.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS eval_runs (
    eval_run_id         TEXT PRIMARY KEY,          -- UUID4
    evaluated_at        TEXT NOT NULL,             -- UTC ISO timestamp
    subject             TEXT NOT NULL CHECK (subject IN ('local_checkpoint', 'teacher_reference')),
    training_run_id     TEXT,                       -- FK-ish to training_registry.training_runs.run_id;
                                                     -- NULL only for subject='teacher_reference'
    checkpoint_path     TEXT,                       -- the exact checkpoint evaluated; NULL for teacher
    base_model          TEXT NOT NULL,
    dataset_versions    TEXT NOT NULL,              -- JSON {dataset_type: "type-vX.Y.Z"}
    dataset_content_hashes TEXT NOT NULL,           -- JSON {version: content_hash}, snapshotted at eval time
    holdout_split       TEXT NOT NULL DEFAULT 'test',-- which split (from splits.json) was evaluated
    n_examples_evaluated INTEGER NOT NULL,
    metrics             TEXT NOT NULL,              -- JSON: full metrics dict (per-type + aggregate +
                                                     -- performance numbers + "not measurable" disclosures)
    git_commit          TEXT,                        -- ngx-rotation commit at eval time
    eval_harness_hash   TEXT,                        -- SHA-256 over eval_metrics.py + eval_dataset.py +
                                                     -- run_evaluation.py concatenated -- so a change to
                                                     -- HOW metrics are scored is itself detectable, not
                                                     -- just changes to the model/dataset being scored
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS ix_eval_runs_evaluated_at ON eval_runs (evaluated_at);
CREATE INDEX IF NOT EXISTS ix_eval_runs_training_run ON eval_runs (training_run_id);

CREATE TRIGGER IF NOT EXISTS eval_runs_no_update
BEFORE UPDATE ON eval_runs
BEGIN SELECT RAISE(ABORT, 'eval_runs rows are immutable — a re-scored evaluation is a NEW eval_run, never an edit to a past one'); END;

CREATE TRIGGER IF NOT EXISTS eval_runs_no_delete
BEFORE DELETE ON eval_runs
BEGIN SELECT RAISE(ABORT, 'eval_runs rows are never deleted — every benchmark result stays comparable across model versions'); END;

CREATE TABLE IF NOT EXISTS eval_examples (
    example_id          INTEGER PRIMARY KEY,
    eval_run_id         TEXT NOT NULL REFERENCES eval_runs(eval_run_id),
    dataset_type        TEXT NOT NULL,
    unique_id           TEXT NOT NULL,
    instruction         TEXT,
    expected_output     TEXT,                       -- JSON, the recorded teacher/ground-truth output
    model_output_raw    TEXT,
    model_output_parsed TEXT,                        -- JSON, or NULL if the model's output didn't parse
    scores              TEXT,                        -- JSON: per-example metric scores that applied
                                                     -- to this example (agreement_with_teacher, and any
                                                     -- type-conditional metric -- self_critique_quality,
                                                     -- grounding_accuracy, etc.)
    latency_s           REAL,
    input_tokens        INTEGER,
    output_tokens       INTEGER
);

CREATE INDEX IF NOT EXISTS ix_eval_examples_run ON eval_examples (eval_run_id);
CREATE INDEX IF NOT EXISTS ix_eval_examples_type ON eval_examples (dataset_type);

CREATE TRIGGER IF NOT EXISTS eval_examples_no_update
BEFORE UPDATE ON eval_examples
BEGIN SELECT RAISE(ABORT, 'eval_examples rows are immutable — append a new eval_run instead of editing a past one'); END;

CREATE TRIGGER IF NOT EXISTS eval_examples_no_delete
BEFORE DELETE ON eval_examples
BEGIN SELECT RAISE(ABORT, 'eval_examples rows are never deleted — full per-example auditability is kept for every benchmark run'); END;
