# Data Moat Priority Ranking — 2026-07-15

Objective: maximize decade-rate of alpha discovery. Priority = GENERATIVITY x Uniqueness x Replication-difficulty x Maintenance (inverted cost) x Coverage, each 1-5. Generativity must trace to named hypothesis families in `docs/HYPOTHESIS_FAMILY_MAP.md`. Scores and rationale live in `configs/dataset_priorities.toml`; edit there and rerun this script.

| # | dataset | mech | GEN | families | U | R | M | C | score | necessity |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Historical index membership + announcement dates (review circulars, archives) | M2 | 4 | F2,F3 | 5 | 5 | 4 | 3 | **1200** |  |
| 2 | Historical NGX price lists via web archives (one-off reconstruction) | M2 | 5 | F2,F3,F4,F5,F8 | 5 | 4 | 5 | 2 | **1000** |  |
| 3 | NGX per-stock daily price list (volume, value, deals) — forward capture | M1 | 5 | F2,F3,F4,F5,F6,F8 | 4 | 5 | 4 | 2 | **800** | yes |
| 4 | PIT regulatory/macro event database with verification trails | M3 | 4 | F1,F7,F11 | 4 | 4 | 3 | 4 | **768** | yes |
| 5 | Dividend/earnings calendar incl. qualification dates (registrars, X-Issuer) | M3 | 5 | F2,F5,F6 | 4 | 4 | 3 | 3 | **720** | yes |
| 6 | Full-text NGX company disclosure archive (forward + best-effort backfill) | M1 | 4 | F5,F9 | 3 | 4 | 4 | 3 | **576** |  |
| 7 | CBN circulars/directives, taxonomy-classified (banking, FX, prudential) | M3 | 3 | F1,F7 | 3 | 3 | 3 | 4 | **324** | yes |
| 8 | Parallel-market NGN/USD daily history + official spread | M1 | 3 | F7,F12 | 5 | 5 | 2 | 2 | **300** |  |
| 9 | NAICOM insurance + PenCom pension regulatory event histories | M3 | 2 | F1 | 3 | 3 | 4 | 3 | **216** |  |
| 10 | AGM dates/outcomes, board & CEO changes, auditor changes | M3 | 2 | F9 | 4 | 4 | 2 | 2 | **128** |  |
| 11 | Nigerian broker research/analyst notes archive | M1 | 2 | F10 | 4 | 4 | 2 | 2 | **128** |  |
| 12 | NBS inflation/GDP releases with release-date PIT | M2 | 2 | F1,F11 | 2 | 2 | 4 | 3 | **96** |  |
| 13 | CBN MPC decision history (MPR/CRR, communiques) | table_stakes | 3 | F1,F11 | 1 | 1 | 5 | 5 | **75** | yes |
| 14 | Brent daily series + derived shock events | table_stakes | 2 | F1,F12 | 1 | 1 | 5 | 5 | **50** | yes |
| 15 | SEC Nigeria directives/circulars | M3 | 1 | F1 | 2 | 2 | 4 | 3 | **48** |  |

## Gates and notes

- **index_membership_pit**: gen=4 not 2: correctness PRECONDITION for every constituent-level family (F4-F6, F8) — survivorship defense.
- **pricelist_wayback_backfill**: Keystone's historical half. Probe density; commit if >40% of days recoverable.
- **ngx_daily_pricelist_forward**: KEYSTONE (6 families) + time-gated. The single most valuable acquisition.
- **pit_event_database**: Also the context/conditioning layer for every other family. Under construction.
- **dividend_earnings_calendar**: gen=5: three families directly + total-return construction feeds ALL return-based research.
- **xissuer_disclosure_archive**: gen=4: raw substrate for future NLP/tone families not yet conceived — cheap optionality. Blocked on endpoint discovery.
- **fx_parallel_market_history**: ETHICS/LEGAL GATE before acquisition: politically sensitive. Review first.
- **broker_research_archive**: LICENSING GATE: acquire only with written permission. Speculative family.

## Reading the ranking

- Moat assets (M1/M2/M3) are ranked by score and acquired top-down.
- `necessity` rows are table stakes for active research: acquired early regardless of score, never mistaken for edge.
- Coverage for forward-capture assets (M1) rises mechanically with time — their scores are understated today and grow every trading day the capture job runs. This is the argument for starting them immediately.