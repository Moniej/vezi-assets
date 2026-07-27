# Document Text-Extraction Coverage — Phase A — 2026-07-22

AI Intelligence Layer, Phase A (`docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`). No LLM calls made. Cumulative over every `documents` row populated so far (the ingestion script runs in resumable batches — this reflects the whole table, not just the most recent batch). Counts what has usable native text vs. what needs OCR (not yet run — pending owner decision on OCR engine).

- Catalog rows (corporate_actions_calendar_classified.csv): 11546
- Rows in `documents` so far: 11533
- Native text extracted (source_confidence=0.85): 7399
- OCR-pending (no usable text layer, source_confidence=0.0 until OCR'd): 4134
- Extraction error (unreadable/corrupt PDF): 0
- Ticker resolved (verified rename or direct match): 11134
- Ticker unresolved (raw_symbol kept, ticker NULL): 399

## By doc_type (cumulative)

| doc_type | native | ocr_pending | extraction_error |
|---|---|---|---|
| agm | 551 | 243 | 0 |
| board_meeting | 411 | 179 | 0 |
| bonus_split | 13 | 4 | 0 |
| closed_period | 397 | 193 | 0 |
| dealing | 123 | 40 | 0 |
| dividend | 244 | 84 | 0 |
| governance | 586 | 329 | 0 |
| other | 4699 | 3028 | 0 |
| results_notice | 335 | 22 | 0 |
| rights_capital | 40 | 12 | 0 |

## By filing year (cumulative)

| year | native | ocr_pending | extraction_error |
|---|---|---|---|
| 2014 | 80 | 44 | 0 |
| 2015 | 86 | 84 | 0 |
| 2016 | 138 | 172 | 0 |
| 2017 | 180 | 456 | 0 |
| 2018 | 275 | 593 | 0 |
| 2019 | 382 | 665 | 0 |
| 2020 | 783 | 494 | 0 |
| 2021 | 771 | 381 | 0 |
| 2022 | 810 | 365 | 0 |
| 2023 | 838 | 332 | 0 |
| 2024 | 1079 | 241 | 0 |
| 2025 | 1069 | 201 | 0 |
| 2026 | 908 | 106 | 0 |

Unresolved tickers keep their `raw_symbol` verbatim in `documents` — no guessed matches. Next step (Phase A completion): review this report, then decide the OCR engine (open decision in the architecture doc) before Phase B.