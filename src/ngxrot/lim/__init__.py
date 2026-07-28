"""Local Intelligence Model (LIM) — dataset generation and (eventually)
training library. Design: docs/LIM_ARCHITECTURE.md,
docs/DATASET_GENERATION_AND_TRAINING_SPEC.md.

Package layout:
  schema.py      Canonical TrainingExample — one shape for every dataset
                 type; task-specific content lives inside its generic
                 fields (spec §3).
  quality.py     Teacher-generation acceptance pipeline: hard exclusions +
                 a deterministic, disclosed quality_score formula (spec §4).
  registry.py    Immutable, append-only dataset-version registry — a
                 separate SQLite database from the quant engine's
                 data/registry.sqlite hypothesis ledger (different domain,
                 not conflated), enforced the same way: SQL triggers block
                 UPDATE/DELETE (spec §5).
  exporters.py   Declarative per-dataset-type export specs (source query +
                 field mapping into the canonical schema) for the 17
                 dataset types (spec §2). Read-only against the AI
                 Intelligence Layer's schema; reuses existing modules
                 (grounding.py, coverage_assessment.py, evidence_ranking.py,
                 retrieval.py, context.py) rather than reimplementing them.
  audit.py       Pre-training dataset audit (spec §6): duplicate rate,
                 contradiction rate, citation/grounding integrity,
                 distributions, acceptance rate — enforced against
                 configurable thresholds, plus train/val/test split
                 generation and reports.

Everything in this package is READ-ONLY against `src/ngxrot/documents/`
and the rest of the AI Intelligence Layer — no table gains a column, no
existing pipeline behavior changes. This package's own outputs (JSONL
datasets, the dataset registry, audit reports) live entirely under
`lim_training/` (gitignored) and are never written back into the source
database.

No training code lives here — Phase LIM-1 (this package's current scope)
is the dataset pipeline only. Training begins at Phase LIM-2, a separate,
later, explicitly-gated phase.
"""
