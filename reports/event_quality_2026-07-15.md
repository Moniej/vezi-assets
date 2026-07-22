# Event Ingestion Quality Report — manual_primary_verified — 2026-07-15

- batch rows: 3
- accepted: 2
- rejected: 1
- issues: 1

| severity | event | message |
|---|---|---|
| REJECT | vibes_shift@2024-01-15 | event_type 'vibes_shift' not in taxonomy |

## Events in database by category (post-ingest)

- banking: 1
- macro: 1

Chronology, duplicate, and conflict rules: see `src/ngxrot/event_pipeline.py` docstring. Unknown fields remain NULL — nothing in this table is inferred from later summaries.