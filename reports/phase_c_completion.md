# Phase C Completion Report — 2026-07-26

- LLM-extracted `extracted_facts` rows: 17
- Deterministic (Phase B) `extracted_facts` rows: 143

## Precision/recall vs. Phase B deterministic ground truth (numeric dividend/rights/bonus figure, doc_id-matched)

- Documents where BOTH LLM and Phase B extracted a numeric value: 10
- Agree (within 1e-6): 9
- LLM extracted a value Phase B did not (LLM found MORE than deterministic — could be correct where the regex extractor missed, or a hallucination): 6
- Phase B extracted a value the LLM missed (recall miss): 0
- **Precision (of LLM values with a ground-truth match, how many agree): 90.0%**
- **Recall (of Phase B's known values, how many did the LLM reproduce): 100.0%**

### Every disagreement (not summarized away)

| doc_id | Phase B value | LLM value |
|---|---|---|
| 10788 | 3.7468 | 9.7192 |

## Grounding

- Facts with grounding_check='failed' (quote not found verbatim in source, extraction_confidence forced to 0.0): 2 / 17 (11.8%)

## Self-critique gate (Step 14)

- Implications drafted: 17
- Status breakdown: {'unvalidated_ai_interpretation': 14, 'blocked_by_self_critique': 3}
- Critique rows: 136 (expect 136 = 8 per implication if the gate ran completely on every draft)
- Finding breakdown: {'concern': 68, 'pass': 61, 'fail': 7}
- Question types most often flagged: {'ignored_alternative_explanation': 17, 'unevidenced_inference': 16, 'insufficient_information': 12, 'confidence_improving_information': 11, 'market_noise_check': 8, 'contradicts_prior_evidence': 6, 'single_document_overreaction': 4, 'correlation_vs_causation': 1}

## Schema completeness

- Facts missing a complete 13-category impact_assessments set: 0 / 17
- LLM facts with zero causal_chain_steps rows (schema violation — should be impossible if extract.py ran to completion): 0