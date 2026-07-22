# Data Completeness Report — investing_com — 2026-07-15

Anchor cross-reference: NGXASI verified at 3 independently sourced year-end closes (Nairametrics, NGX Group). Sector indices have no independent anchor available — they receive structural checks only and their confidence remains 0.5 (aggregator grade).

| index | rows | first | last | wd-coverage | dup | jumps | gaps | excluded months | anchors | research-ready windows |
|---|---|---|---|---|---|---|---|---|---|---|
| NGX30 | 3577 | 2012-01-30 | 2026-07-15 | 94.8% | 0 | 0 | 0 | 0 | n/a | 2012-01-01..2026-07-31 |
| NGXASI | 3577 | 2012-01-30 | 2026-07-15 | 94.8% | 0 | 0 | 0 | 0 | PASS | 2012-01-01..2026-07-31 |
| NGXBNK | 3577 | 2012-01-30 | 2026-07-15 | 94.8% | 0 | 4 | 0 | 3 | n/a | 2012-01-01..2012-10-31; 2012-12-01..2023-05-31; 2023-07-01..2025-06-30; 2025-08-01..2026-07-31 |
| NGXCNSMRGDS | 1869 | 2018-12-21 | 2026-07-15 | 94.7% | 0 | 1 | 0 | 2 | n/a | 2019-01-01..2023-05-31; 2023-07-01..2026-07-31 |
| NGXINDUSTR | 1589 | 2020-02-10 | 2026-07-15 | 94.7% | 0 | 0 | 0 | 0 | n/a | 2020-02-01..2026-07-31 |
| NGXINS | 3577 | 2012-01-30 | 2026-07-15 | 94.8% | 0 | 1 | 0 | 1 | n/a | 2012-01-01..2023-05-31; 2023-07-01..2026-07-31 |
| NGXOILGAS | 3532 | 2012-03-29 | 2026-07-15 | 94.7% | 0 | 5 | 0 | 3 | n/a | 2012-03-01..2014-01-31; 2014-03-01..2014-03-31; 2014-05-01..2023-05-31; 2023-07-01..2026-07-31 |
| NGXPENSION | 1247 | 2021-06-30 | 2026-07-15 | 94.8% | 0 | 1 | 0 | 1 | n/a | 2021-06-01..2023-05-31; 2023-07-01..2026-07-31 |

## Anomaly detail

### NGXASI
- anchor 2022-12-30: expected 51,251.06, got 51251.06 — OK
- anchor 2023-12-29: expected 74,773.77, got 74773.85 — OK
- anchor 2024-12-31: expected 102,926.40, got 102926.4 — OK

### NGXBNK
- jump -25.6% on 2012-11-28 — month excluded pending explanation (rebase? vendor splice?)
- jump +26.5% on 2023-06-14 — month excluded pending explanation (rebase? vendor splice?)
- jump +18.0% on 2025-07-01 — month excluded pending explanation (rebase? vendor splice?)
- jump -15.2% on 2025-07-02 — month excluded pending explanation (rebase? vendor splice?)

### NGXCNSMRGDS
- jump +20.6% on 2023-06-14 — month excluded pending explanation (rebase? vendor splice?)

### NGXINS
- jump +23.0% on 2023-06-14 — month excluded pending explanation (rebase? vendor splice?)

### NGXOILGAS
- jump -41.4% on 2014-02-17 — month excluded pending explanation (rebase? vendor splice?)
- jump +78.8% on 2014-02-18 — month excluded pending explanation (rebase? vendor splice?)
- jump +752.8% on 2014-04-23 — month excluded pending explanation (rebase? vendor splice?)
- jump -88.3% on 2014-04-25 — month excluded pending explanation (rebase? vendor splice?)
- jump +16.0% on 2023-06-14 — month excluded pending explanation (rebase? vendor splice?)

### NGXPENSION
- jump +18.1% on 2023-06-14 — month excluded pending explanation (rebase? vendor splice?)

## Ingestion statistics

- rows_fetched: 22545
- rows_ingested_research_ready: 22361
- rows_excluded: 184
- source: investing_com
- base_confidence: 0.5
- as_of_date: 2026-07-15
- anchors_checked: 3

Periods not listed as research-ready are treated as UNAVAILABLE. No reconstruction, interpolation, or backfill was performed.