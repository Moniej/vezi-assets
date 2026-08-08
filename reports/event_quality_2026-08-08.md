# Event Ingestion Quality Report — stage10c_news_pilot — 2026-08-08

- batch rows: 16
- accepted: 5
- rejected: 11
- issues: 16

| severity | event | message |
|---|---|---|
| WARN | management_change@2026-04-11 | effective_date 2026-04-01 precedes announced_date 2026-04-11 — verify (retroactive policy?) |
| WARN | management_change@2025-01-17 | effective_date 2025-01-10 precedes announced_date 2025-01-17 — verify (retroactive policy?) |
| WARN | management_change@2025-11-03 | effective_date 2025-10-31 precedes announced_date 2025-11-03 — verify (retroactive policy?) |
| WARN | management_change@2025-09-02 | effective_date 2025-07-29 precedes announced_date 2025-09-02 — verify (retroactive policy?) |
| WARN | corporate_restructuring@2025-09-24 | effective_date 2025-09-18 precedes announced_date 2025-09-24 — verify (retroactive policy?) |
| REJECT | corporate_restructuring@2026-03-17 | already ingested from this source with identical payload |
| REJECT | merger@2026-03-24 | already ingested from this source with identical payload |
| REJECT | ownership_change@2025-09-21 | already ingested from this source with identical payload |
| REJECT | capital_raise@2026-07-06 | already ingested from this source with identical payload |
| REJECT | regulatory_action@2026-02-24 | already ingested from this source with identical payload |
| REJECT | capital_raise@2026-08-04 | already ingested from this source with identical payload |
| REJECT | capital_raise@2026-03-28 | already ingested from this source with identical payload |
| REJECT | management_change@2026-04-11 | already ingested from this source with identical payload |
| REJECT | management_change@2025-01-17 | already ingested from this source with identical payload |
| REJECT | management_change@2025-11-03 | already ingested from this source with identical payload |
| REJECT | capital_raise@2026-02-11 | already ingested from this source with identical payload |

## Events in database by category (post-ingest)

- banking: 5
- commodity: 2
- corporate: 18
- insurance: 3
- macro: 3
- monetary: 82

Chronology, duplicate, and conflict rules: see `src/ngxrot/event_pipeline.py` docstring. Unknown fields remain NULL — nothing in this table is inferred from later summaries.