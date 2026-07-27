# AI Intelligence Layer — Phase B Completion — 2026-07-22

Re-labels `scripts/build_corp_actions_db.py`'s existing, already-validated corporate-actions extraction (`data/staging/xissuer/corporate_actions_extracted.csv`) through the new `extracted_facts`/`evidence` schema (`docs/REASONING_ENGINE_SPECIFICATION.md` §3-4). No new extraction logic, no LLM calls, `extraction_confidence=1.0` throughout (deterministic, already validated when the source CSV was built). Cumulative over the whole table (the script runs idempotently — this reflects everything ingested so far, not just the last run).

- Catalog rows (corporate_actions_extracted.csv): 397
- **Total `extracted_facts` rows: 143**

## By fact_type (cumulative)

| fact_type | count |
|---|---|
| bonus_issue | 1 |
| dividend | 141 |
| rights_issue | 1 |

## Validation

Run `python -u scripts/validate_extracted_facts.py` for a full, independent, doc_id-keyed check of every row in the table (numeric/date reproduction against the source CSV, evidence-link consistency, doc_id resolution, fact_type taxonomy membership). Last independent run: **PASS, 0 issues found across all 143 rows.**

## Known limitation (not new — inherited from the Phase A OCR gap)

The GTCO/Zenith FY2023 anchors (`data/reference_anchors_corp_actions.csv`, dividend=2.70, verified by direct primary-source read) do **not** appear in `corporate_actions_extracted.csv` with a populated `dividend_per_share` — their dividend notices are scanned-image PDFs with no text layer (confirmed: same documents flagged OCR-pending in Phase A's `reports/document_text_coverage.md`). This text-based deterministic extractor cannot read a scan; the architecture doc's "reproduce the GTCO anchor byte-for-byte" Phase B criterion is consequently blocked on the same pending OCR decision as Phase A, not on anything new. EPS/P.E. was investigated separately and explicitly NOT included here — it already failed validation twice (`reports/eps_pe_extraction_status.md`) and no extractor output exists to re-label.