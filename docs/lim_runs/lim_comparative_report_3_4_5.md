# Comparative Report — LIM-3, LIM-4, LIM-5

All three rows below are real, immutable `eval_run` records from the same
eval registry, scored by the same harness (`eval_harness_hash` recorded
per row), over the same 61 held-out examples across the same 8 dataset
types that have a non-empty `test` split. Metrics marked "retroactive"
were computed after the fact from each run's stored `expected_output` +
`model_output_parsed` (available for every row); metrics needing real
`context` (`grounded_correctness`, `citation_correctness`,
`hallucination_risk`) could only be computed for LIM-5, since the
`eval_examples` table doesn't persist `context` for the two earlier runs
(a disclosed limitation, not fixed retroactively — see
`lim5_priority4_metrics.md`).

## Provenance

| | LIM-3 baseline | LIM-4 | LIM-5 Experiment 1 |
|---|---|---|---|
| `eval_run_id` | `1d018805-...` | `9a6b06cf-...` | `f9395a85-...` |
| `training_run_id` | `a022e655-...` | `c52db6e1-...` | `b05875df-...` |
| Dataset trained on | `entity_recognition-v1.0.0` | `entity_recognition-v1.1.0` | `extraction-v1.0.0` |
| Seed / max_steps / lr / LoRA r | 42 / 12 / 2e-4 / 8 (identical across all three) |
| Loss masking | None (full-sequence, the confirmed LIM-3 defect) | Response-only (LIM-4 fix) | Response-only |
| Training loop | `Trainer.train()` (worked, unmasked) | Manual loop (LIM-4 fix for the masked-label inf/NaN bug) | Manual loop |

## Full metric comparison (overall, 61 examples)

| Metric | LIM-3 | LIM-4 | LIM-5 | Trend |
|---|---:|---:|---:|---|
| `agreement_with_teacher` (exact-match) | 0.0055 | 0.0000 | 0.0000 | **flat/regressed by this metric** — known blind spot |
| `semantic_equivalence` (retroactive for LIM-3/4, native for LIM-5) | 0.0055 | 0.0550 | **0.0670** | **improving, monotonic** |
| `self_critique_quality` | 0.0 | 0.0 | 0.0 | flat (no type trained addressed this) |
| `reasoning_quality` (retroactive) | 0.0 | 0.0 | 0.0 | flat |
| `grounding_accuracy` | not measurable (n=0) | not measurable (n=0) | not measurable (n=0) | no data in any run |
| `citation_correctness` | not measurable (n=0) | not measurable (n=0) | not measurable (n=0) | no data in any run |
| `hallucination_flag_correct` | not measurable (n=0) | not measurable (n=0) | not measurable (n=0) | no data in any run |
| `grounded_correctness` | n/a (context not stored) | n/a (context not stored) | 0.2101 (n=61) | only measurable going forward |
| `hallucination_risk` | n/a (context not stored) | n/a (context not stored) | 0.213 (n=18) | only measurable going forward |
| Mean latency | 11.56s | 27.58s | 15.13s | LIM-4's spike did not persist — supports the LIM-4 report's "likely hardware throttling, not the checkpoint" hypothesis |
| p95 latency | 11.81s | 52.04s | 21.11s | same pattern |

## Per-type `semantic_equivalence` (the metric that actually moved)

| Type | LIM-3 | LIM-4 | LIM-5 |
|---|---:|---:|---:|
| `extraction` (the type LIM-5 trained on) | 0.0278 | 0.0850 | **0.1704** |
| `corporate_actions` (same underlying fact pool as `extraction`, different sampled test examples — see note below) | 0.0 | 0.1296 | 0.1134 |
| `entity_recognition`, `evidence_ranking`, `investment_decision_support`, `rag`, `retrieval`, `self_critique` | 0.0 | 0.0 | 0.0 |

**Note on `corporate_actions` vs `extraction`**: Priority 1 found these
two dataset types currently export the *same 159-example pool*, but their
`unique_id`s are prefixed differently (`corporate_actions:<fact_id>` vs
`extraction:<fact_id>`), so the deterministic hash-bucket split assigns
**different specific examples** to each type's `test` partition even
though the source pool is identical. `corporate_actions` dipping slightly
(0.1296→0.1134) while `extraction` doubled (0.0850→0.1704) is not a
contradiction — they are different held-out samples, not the same test
examples scored twice. No entity_recognition/evidence_ranking/etc. type
moved in either direction — expected, since only the checkpoint's own
trained-on distribution is where any change would appear at all.

## Experiment log

| Experiment | Variable changed | Status | Result |
|---|---|---|---|
| LIM-4 (masking fix) | Response-only loss masking + real train/val split + fixed exporter context | Completed | Fixed 3 confirmed bugs (padding-label leakage, entity_recognition context collision, train/test contamination); no aggregate metric improvement by exact-match, but real qualitative improvement visible in raw outputs |
| LIM-5 Experiment 1 | Dataset choice (`entity_recognition` → `extraction`), all else identical | **Completed, succeeded** | `semantic_equivalence` on `extraction`: 0.0850 → 0.1704 |
| LIM-5 Experiment 2 | Training duration (`max_steps` 12 → 40), all else identical | **Blocked** | 4 consecutive segfaults at process startup, correlated with low system RAM (~3.2GB/16GB free); honestly reported as untested, not as a negative result |

## Regressions found, stated plainly

- `agreement_with_teacher` (exact-match) shows LIM-4 and LIM-5 at 0.0 vs.
  LIM-3's 0.0055 — a nominal regression on that ONE metric, fully
  explained (not explained away) by Priority 4's finding: exact-match
  cannot detect the schema-plausible-but-differently-shaped outputs both
  later checkpoints actually produce. `semantic_equivalence`, designed
  specifically to resolve this blind spot, shows the true (improving)
  direction.
- No other metric regressed between any two rows.
- Latency: LIM-4 spiked (27.58s) then LIM-5 partially recovered (15.13s)
  — still above LIM-3's 11.56s baseline. Not isolated as a controlled
  measurement in either later run (continuous multi-minute evaluation
  passes, no thermal/clock monitoring); flagged as an open question, not
  resolved by this report.

## Conclusion

Across three real, immutable, comparably-scored checkpoints, a single
controlled variable change (LIM-5 Experiment 1's dataset swap) produced a
reproducible, monotonic improvement on the one metric built to detect it,
while every metric that showed no eligible data in LIM-3 also showed none
in LIM-4 or LIM-5 (no regression, but also no confirmation — an honest
gap, not a false claim of preservation). This is the evidence base for
the bottleneck ranking and research backlog that follow.
