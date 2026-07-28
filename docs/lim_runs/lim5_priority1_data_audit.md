# LIM-5 Priority 1 — Training Data Quality Audit

Full per-type raw data: `docs/lim_runs/lim5_dataset_audit.json`
(`scripts/lim/audit_training_data.py`, read-only, reuses LIM-1's
`audit_report.json` for every existing dimension; adds two new ones this
run: token-length distribution and label consistency).

## Per-type summary

| Type | n_acc | n_rej | acc% | quality_score (mean) | dup% | tok mean/p95 | distinct ctx | inconsistent groups (worst) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| extraction | 159 | 2 | 98.8% | 0.988 | 0.6% | 116/138 | 152/159 | 6 (worst 2) |
| corporate_actions | 159 | 2 | 98.8% | 0.988 | 0.6% | 116/138 | 152/159 | 6 (worst 2) |
| evidence_ranking | 159 | 2 | 98.8% | 0.988 | 0.0% | 88/127 | **159/159** | **0** |
| self_critique | 128 | 16 | 88.9% | 0.787 | 0.0% | 130/168 | 120/128 | 2 (worst 2) |
| investment_decision_support | 16 | 2 | 88.9% | 0.787 | 0.0% | 145/157 | 15/16 | 1 (worst 2) |
| entity_recognition | 39 | 0 | 100% | 1.000 | 0.0% | 97/103 | 17/39 | **13 (worst 6)** |
| coverage_assessment | 12 | 0 | 100% | 0.733 | 0.0% | 293/303 | 12/12 | 0 |
| rag | 12 | 0 | 100% | 0.733 | 0.0% | 280/372 | 12/12 | 0 |
| retrieval | 12 | 0 | 100% | 1.000 | 0.0% | **444/700** | 12/12 | 0 |
| hallucination_detection | 2 | 0 | 100% | 0.5 | 0.0% | 98/92 | 2/2 | 0 |
| contradiction_detection / knowledge_graph_completion | 1 | 0 | 100% | ~1.0 | 0.0% | ~90 | 1/1 | 0 |
| event_understanding | 0 | 0 | — | — | — | — | — | — |

## Findings

### 1. `extraction` and `corporate_actions` are currently identical datasets

Every statistic matches exactly (159/2/98.8%/0.988/0.6%/116/138/152/6/2), and
spot-checking example 0 confirms it: same instruction, same context, same
`expected_output`. `corporate_actions`' taxonomy filter (`capital_and_
balance_sheet` + `corporate_events`) currently captures 100% of this
corpus's extracted facts. Treating these as two independent training
sources right now adds no real diversity — a genuine, disclosed finding,
not assumed.

### 2. `entity_recognition` — the type actually trained on in LIM-2/LIM-4 —
is the worst-suited of the viable options, and NOT because of size

13 of its 17 context-collision groups are label-*inconsistent* (the same
input context maps to different correct answers) — a 76% inconsistency
rate among collisions, worst group size 6. No other type comes close:
`extraction`/`corporate_actions` have 6 collision groups out of 152 (4%),
`self_critique` has 2 of 8 (25%, and smaller in absolute terms). This is
a direct, quantified confirmation of the owner's instruction not to assume
quantity is the bottleneck: `entity_recognition` (39 examples) is smaller
than `self_critique` (128) and `extraction` (159), but its dominant
problem is unresolved label ambiguity, not sample count — the LIM-4 fix
(adding filing metadata to context) measurably improved but did not
eliminate this.

### 3. `evidence_ranking` has a DIFFERENT, previously-uncaught defect: an
uninformative context

Zero collision groups, zero duplicate rate, excellent quality_score — by
the label-consistency check alone this looks like the cleanest large
dataset. But inspecting a real example: `context = {"fact_id": 1}` — a
bare, opaque database ID, carrying no actual evidence content, quote, or
company information. `expected_output` (tier ranking + rationale
referencing "governed X-Issuer/NGX pipeline, quote verified grounded")
requires information the model is never given. Every input DOES map to
exactly one consistent answer (hence 0 collisions), but the model cannot
plausibly learn a generalizing mapping from an opaque integer to a
substantive judgment — it could only memorize per-ID lookups, which
doesn't generalize to fact_ids outside the training set. **Label
consistency is necessary but not sufficient for a task to be learnable;
this dataset needed a third check (context informativeness) that the
consistency metric alone doesn't catch.**

### 4. `self_critique` and `extraction`/`corporate_actions` are the best
-evidenced candidates for LIM-5's training experiments

Both have informative, multi-field context (ticker/filing_date/fact_type
for extraction; ticker/draft_direction/draft_magnitude/confidence/question
for self_critique), substantive expected_output requiring real
extraction/reasoning, good size (128-159), high acceptance rates, and a
small, disclosed residual inconsistency rate (4-25% of collision groups,
not of all examples). `extraction`/`corporate_actions` is larger (159)
and has a tighter inconsistency ratio (4%); `self_critique` is smaller
(128) but is a genuinely different reasoning skill (contradiction
detection, not extraction) and its own inconsistency count (2 groups) is
tiny in absolute terms.

### 5. `retrieval`'s response format is fundamentally unsuited to
supervised fine-tuning as currently exported

Mean 444 / p95 700 tokens per example (`max_seq_length=256` used
throughout LIM-2/4 would truncate nearly every one), and the actual
target is a list of up to ~100 raw database `doc_id` integers. This is
not a prompt-wording problem (Priority 2) — no fine-tuned 4B model should
be expected to memorize/generate long ID lists at inference time; that is
a retrieval-index problem, not a next-token-prediction problem. Flagged
here as a dataset-design issue for a future retrieval-architecture
decision, not something Priority 2/3 prompt or curriculum changes can fix.

### 6. Small types (`coverage_assessment`, `rag`, `hallucination_detection`,
`contradiction_detection`, `knowledge_graph_completion`, `event_understanding`)
remain genuinely too small (0-12 examples) for any training experiment,
consistent with LIM-1/LIM-3's prior disclosures.

## Conclusion: which datasets are currently limiting model performance

Not `entity_recognition`'s size — its label-inconsistency rate. The
highest-confidence, evidence-backed choice for LIM-5's actual training
experiments is **`extraction`/`corporate_actions`** (159, cleanest large
set, informative context) or **`self_critique`** (128, different skill,
still clean) — not `entity_recognition`, and not `evidence_ranking`
(uninformative context) or `retrieval` (unsuited response format).
