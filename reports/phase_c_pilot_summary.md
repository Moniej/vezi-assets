# Phase C Pilot Summary — 2026-07-26

## Documents
- Processed (terminal, would be skipped on a rerun): 17
- Failed: 0
- Quota-exceeded (current status, not yet retried): 0
- Interrupted mid-processing (status='processing', needs retry): 0
- Full status breakdown: {'completed': 14, 'blocked_by_self_critique': 3}

## Extraction precision/recall (vs. Phase B deterministic ground truth)
- LLM facts: 17 | Deterministic (Phase B) facts: 143
- Overlap with ground truth: 10 | Agree: 9
- Precision: 0.9 | Recall: 1.0
- LLM found extra (not in Phase B): 6 | Recall misses: 0

## Grounding
- Failures: 2 | Failure rate: 0.1176

## Self-critique gate (Step 14)
- Implications: 17 | Blocked: 3 | Rejection rate: 0.1765
- Finding counts: {'concern': 68, 'pass': 61, 'fail': 7}

## Schema completeness
- Facts with all 13 impact categories: 17
- Facts missing a causal chain (should be 0): 0

## Performance / cost
- Avg latency: 15.629s | Total LLM calls: 34
- Tokens — input: 63564, output: 40634
- Cache hit rate: 0.0882 (3 hits)
- Estimated API cost: $0.0 (rate confidence: assumed — Placeholder zero rate — free-tier pilot cost is genuinely $0. Replace with confirmed paid-tier pricing before this figure is used for budgeting.)