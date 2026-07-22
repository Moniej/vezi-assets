# Event Ingestion Quality Report — manual_primary_verified — 2026-07-16

- batch rows: 11
- accepted: 11
- rejected: 0
- issues: 0


## Events in database by category (post-ingest)

- banking: 5
- commodity: 2
- insurance: 3
- macro: 3
- monetary: 81

Chronology, duplicate, and conflict rules: see `src/ngxrot/event_pipeline.py` docstring. Unknown fields remain NULL — nothing in this table is inferred from later summaries.