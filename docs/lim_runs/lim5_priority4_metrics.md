# LIM-5 Priority 4 — Next-Generation Evaluation Metrics

Implements the metrics designed (not coded) in LIM-4's validation report,
in `src/ngxrot/lim/eval_metrics.py`. Tested in
`scripts/lim/test_eval_metrics.py` (27 checks, all passing).

## Backward compatibility (verified, not assumed)

All 4 original LIM-3 metrics (`agreement_with_teacher`, `self_critique_
quality`, `grounding_accuracy`, `hallucination_flag_correct`) are
**unchanged** — same functions, same behavior, covered by regression
tests. Every future `eval_run` still carries these exact keys, so it
remains directly comparable to `lim3-eval-baseline-2026-07-28` and the
LIM-4 baseline on those dimensions. New metrics are additive keys only.

## New metrics

| Metric | What it measures | Applicability |
|---|---|---|
| `semantic_equivalence` | Unwraps common single-key wrappers (e.g. `{"dividend": {...}}`) and known field-name aliases, then fuzzy (token-overlap) string matching instead of exact — designed to score `>=` `agreement_with_teacher` always, never below | Any example with non-empty `expected_output` |
| `grounded_correctness` | Containment check: are the model's output values traceable to the example's own `context`/`citations`, independent of matching the expected answer | Examples with non-empty context/citations |
| `citation_correctness` | Does the model's output reference the example's real citation/doc ids | Only when the example has real citation ids AND the output references an id field (honestly `None` almost everywhere in the current corpus — no dataset type asks for this yet, a disclosed LIM-3 gap, not fabricated here) |
| `hallucination_risk` | Task-agnostic: extracts ticker-shaped values from output, flags the fraction absent from the example's own context/citations/expected_output | Examples where the output contains at least one ticker-shaped value |
| `reasoning_quality` | Lexical overlap between the model's free-text explanation/rationale and the teacher's | Task types with a free-text reasoning field (`self_critique`, `contradiction_detection`) |
| `partial_credit_tier` | Reporting bucket (`correct`/`partial`/`incorrect`) over `agreement_with_teacher`/`semantic_equivalence` | Reporting layer, not a new computation |

## Real validation

Unit tests reproduce the exact real cases found in LIM-3/LIM-4/LIM-5:
`semantic_equivalence` scores the real `extraction:41` wrapped output
(`{"dividend": {...}}`) at 0.667 vs. `agreement_with_teacher`'s 0.0;
`hallucination_risk` correctly distinguishes a real fabricated ticker
("KO", absent from context) from a real grounded one ("GTCO", present in
context) — the exact LIM-3 "Coca-Cola" scenario, now quantifiable rather
than requiring manual raw-output inspection.

One real bug was found and fixed while writing these tests:
`citation_correctness` used a string-only leaf extractor, so a model
outputting a real JSON *number* (`{"doc_id": 123}`, as this corpus's real
doc_ids are integers) was invisible to it. Fixed with a
number-aware leaf extractor used only by that metric (the others stay
string-only deliberately, since they're about text/ticker content, not
numeric ids).

## Known limitation (disclosed, not fixed)

`grounded_correctness`/`hallucination_risk`/`citation_correctness` all
need the example's real `context`/`citations` to score. The
`eval_examples` registry table does not persist `context` (only
`instruction`/`expected_output`/raw+parsed output), so these three
metrics **cannot be retroactively computed** against LIM-3/LIM-4's
already-recorded rows — only `semantic_equivalence`/`agreement_with_
teacher`/`self_critique_quality`/`grounding_accuracy` (which need only
`expected_output`) can be. This was used directly in LIM-5 Priority 5's
Experiment 1 comparison. Recommended for LIM-6: add `context` to
`eval_examples` so future re-analysis isn't limited this way.
