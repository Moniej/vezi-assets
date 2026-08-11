# Event Ingestion Quality Report — ngx_xcompliance_regco — 2026-08-08

- batch rows: 8
- accepted: 8
- rejected: 0
- issues: 0


## Events in database by category (post-ingest)

- banking: 5
- commodity: 2
- corporate: 26
- insurance: 3
- macro: 3
- monetary: 82

Chronology, duplicate, and conflict rules: see `src/ngxrot/event_pipeline.py` docstring. Unknown fields remain NULL — nothing in this table is inferred from later summaries.