# LIM-1 Completion Report — Dataset Generation Pipeline (2026-07-27)

**Verdict: LIM-1 COMPLETE.** The full dataset pipeline designed in
`docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` is built, tested, and has
been run for real against the live AI Intelligence Layer database
(`ngx.sqlite`, read-only throughout). 13 of 17 dataset types produced a
registered, immutable, versioned dataset; the other 4 were **correctly
refused** by the audit gate for genuine, disclosed real-data-quality
reasons — not pipeline defects. Two real bugs were found during
validation and fixed (below). **No fine-tuning has occurred. The AI
Intelligence Layer received zero writes and zero behavior changes.**

## 1. What was built

Per `docs/LIM_ARCHITECTURE.md` §1.2's designated layout:

| Component | File | Role |
|---|---|---|
| Canonical schema | `src/ngxrot/lim/schema.py` | `TrainingExample` — one shape for all 17 dataset types (spec §3) |
| Quality/acceptance pipeline | `src/ngxrot/lim/quality.py` | Hard exclusions + deterministic weighted `quality_score` (spec §4) |
| Versioning registry | `src/ngxrot/lim/registry.py` + `schema/lim_dataset_registry.sql` | Immutable, SQL-trigger-enforced, separate from the quant engine's hypothesis ledger (spec §5) |
| Exporters | `src/ngxrot/lim/exporters.py` | One function per dataset type, read-only, reusing `grounding.py`/`evidence_ranking.py`/`coverage_assessment.py`/`context.py` rather than reimplementing them (spec §2) |
| Audit framework | `src/ngxrot/lim/audit.py` | Duplicate detection, contradiction rate, integrity checks, distributions, train/val/test splits, threshold enforcement (spec §6 + this session's split-report addition) |
| CLI orchestration | `scripts/lim/export_dataset.py` | export → audit → gate → write JSONL → register → record lineage, one command, fully automated |
| Configs | `configs/dataset_quality_weights.toml`, `configs/dataset_quality_thresholds.toml` | The TOML files are the real source of truth (code constants are only the fallback), matching `pilot_summary.py`/`coverage.py`'s existing pattern |
| Tests | `scripts/lim/test_dataset_pipeline.py` | 32 checks, synthetic DB fixture, no real API/model call anywhere in this package |

Every stage is read-only against `ngx.sqlite` and writes only to
`lim_training/` (gitignored) and the new dataset registry (also under
`lim_training/`). No column was added to any AI Intelligence Layer table.

## 2. Reference environment respected

Per the owner's instruction, the LIM-0 environment (`lim_training/
requirements.lock.txt`) was treated as frozen. **One genuinely new
dependency** was added, not a version upgrade: `tenacity==9.1.4` (matching
the exact version already used by the main ngx-rotation project) — required
because `coverage_assessment.py`'s lazy import of `extract.py` (for a
single float constant) transitively imports `cache.py`, which imports
`tenacity`. This surfaced only when exporters legitimately reuse
`build_reasoning_context` (avoiding duplicate functionality, per the
engineering requirements) — a verified blocker, not a discretionary
upgrade. No other package version changed. `pip check` confirms zero
dependency conflicts after the addition.

## 3. Real results (13 registered, 4 correctly refused)

| Dataset type | Accepted | Rejected | Status | Teacher model(s) |
|---|---|---|---|---|
| extraction | 159 | 2 | **registered** | gemini-3.6-flash |
| corporate_actions | 159 | 2 | **registered** | gemini-3.6-flash |
| evidence_ranking | 159 | 2 | **registered** | gemini-3.6-flash |
| self_critique | 128 | 16 | **registered** | gemini-3.6-flash |
| investment_decision_support | 16 | 2 | **registered** | gemini-3.6-flash |
| entity_recognition | 39 | 0 | **registered** | (deterministic, no LLM) |
| coverage_assessment | 12 | 0 | **registered** | (descriptive, no LLM) |
| retrieval | 12 | 0 | **registered** | (descriptive, no LLM) |
| rag | 12 | 0 | **registered** | gemini-3.6-flash |
| hallucination_detection | 2 | 0 | **registered** | gemini-3.6-flash |
| contradiction_detection | 1 | 0 | **registered** | gemini-3.6-flash |
| knowledge_graph_completion | 1 | 0 | **registered** | (descriptive, no LLM) |
| event_understanding | 0 | 0 | **registered** (honestly empty) | n/a |
| financial_reasoning | 16 | 2 | **AUDIT FAILED** | — |
| citation_grounding | 16 | 2 | **AUDIT FAILED** | — |
| confidence_estimation | 16 | 2 | **AUDIT FAILED** | — |
| portfolio_reasoning | 1 | 0 | **AUDIT FAILED** | — |

**724 lineage rows** recorded across all 13 registered versions (every
`unique_id` traceable back to its exact source `fact_id`/`implication_id`).
Total real data processed: **~1.2 MB** of JSONL across all types; the
dataset registry itself is 164 KB.

## 4. The 4 audit-gate refusals are genuine, correct, and disclosed

None of these are pipeline bugs — each is the gate doing exactly what
`docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` §6.1 designed it to do:
**refuse, not warn**, when real data doesn't yet clear a threshold.

- **financial_reasoning** (`grounding_integrity 0.9459 < 0.95`) and
  **citation_grounding** (`0.8889 < 0.95`): both trace to the same 2 real,
  already-known grounding failures (fact_id 147/148, TOTAL Nigeria Plc's
  interim dividend claim — found during the 2026-07-22 Phase C pilot,
  confirmed again during the 2026-07-27 stabilization pass's live
  re-verification). Out of a currently-small real corpus (18-37
  citations), 2 failures is enough to fall just under the 95% bar. This
  will resolve naturally as more real documents are processed, or the
  owner can adjust the threshold — a real, disclosed open decision, not
  patched here.
- **confidence_estimation** (`duplicate_rate 0.8333 > 0.05`): today's real
  data is genuinely homogeneous on this dataset type's only two input
  fields — nearly every implication shares
  `stated_confidence=0.3` (the platform-wide `UNREVIEWED_LLM_CONFIDENCE_
  FLOOR` ceiling) and one of two `status` values, so many examples'
  *content* (not their `unique_id`) collides. This is an accurate
  reflection of a real, disclosed limitation (confidence is currently a
  fixed engineering ceiling, not yet empirically earned — exactly what
  `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` §8.2/calibration already
  flagged as "not yet measurable" for the same underlying reason).
- **portfolio_reasoning** (`max_single_ticker_share 1.0 > 0.6`): there is
  exactly **one** real row for this dataset type today
  (`portfolio_sizing_note` is populated on only 1 of 18 real
  implications) — 100% concentration is mathematically unavoidable at
  n=1. Matches `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` §11's own
  flagged open decision about whether this dataset type is even worth
  building at today's scale.

Audit artifacts (`audit_report.md`/`.json`) were still written for all 4
refused types — inspectable, never hidden, per spec §4.3's "never silently
repair or discard" rule.

## 5. Two real bugs found during validation, fixed

**Bug 1 — mislabeled grounding status in citations.** `_fact_citations()`
originally set `citations[].grounding_check` to `evidence_ranking`'s
human-readable `tier_rationale` string instead of the real `passed`/
`failed`/`not_run` enum from `extracted_facts.grounding_check`. This made
`audit.py`'s `grounding_integrity` metric a silent false positive (always
≈1.0, since a rationale sentence never exactly equals the string
`"failed"`). Caught by manually cross-checking a known real result against
the metric's output before trusting it — the same "never just trust a
computed number, re-verify against known ground truth" discipline used
throughout this project. Fixed in three exporters
(`extraction`/`financial_reasoning` via `_fact_citations`,
`citation_grounding`, `hallucination_detection`); re-verified against the
real database (`grounding_integrity` moved from a false `1.0` to the
correct `0.9459`, matching the known 2/37 real failures exactly).

**Bug 2 — `hallucination_detection` could never register anything.** The
grounding hard-exclusion in `quality.py` (correctly rejects any
grounding-failed claim from *positive* datasets like `financial_reasoning`)
was being applied uniformly to `hallucination_detection` too — whose
entire purpose is to contain grounding failures as intentional, valuable
*negative* training examples. Every example this dataset type could ever
produce was being hard-excluded by the very check meant to keep bad claims
out of *other* datasets. Fixed with an explicit, narrow, disclosed
exemption (`GROUNDING_EXCLUSION_EXEMPT_TASKS` in `quality.py`,
`PER_TASK_THRESHOLD_OVERRIDES` in `audit.py`) — re-verified: went from
`0/2 accepted, AUDIT FAILED` to `2/2 accepted, registered`.

## 6. Reproducibility ("regenerable without manual intervention")

`scripts/lim/export_dataset.py --all --changelog "..."` is the single
command that reproduces every dataset version from the current database
state — no manual step, no hand-edited file. `teacher_model_ids` is
derived automatically from the exported facts' own `model_id` column
(never asked of the operator). `export_script_commit` is captured
automatically from `git rev-parse HEAD`. Re-running the exact same command
against an unchanged database produces byte-identical `unique_id`s (they
are deterministic functions of source row IDs, never random) and would be
flagged by the registry's `content_hash` if anything about the export
logic silently changed the output.

## 7. Test suite

`scripts/lim/test_dataset_pipeline.py` — 32 checks, all passing, covering:
schema validation (task-type/rejection-reason enforcement), both quality
hard exclusions (grounding failure, contradiction-vs-higher-tier-evidence),
registry immutability (`UPDATE`/`DELETE` both confirmed blocked by SQL
trigger) and versioning (auto-increment, round-trip), reverse lineage
lookup, duplicate detection, threshold enforcement (both the violation
path and the clean path), split-assignment stability as a dataset grows,
exporter correctness against a synthetic fixture, and full CLI
orchestration end-to-end — including a dedicated test proving the audit
gate **correctly refuses** a deliberately bad (100%-concentrated) synthetic
dataset, not just that it accepts good ones.

## 8. Hard boundaries verified

- `git diff --stat -- src/ngxrot/documents/ schema/schema.sql` is empty —
  the AI Intelligence Layer has zero changes from this phase.
- No training occurred. No model weights were touched. `lim_training/
  qwen3_4b_model/`, the LoRA/checkpoint directories from LIM-0, are
  untouched by this phase.
- Everything new lives under `src/ngxrot/lim/`, `scripts/lim/`,
  `schema/lim_dataset_registry.sql`, `configs/dataset_quality_*.toml`, and
  `lim_training/` (gitignored data) — isolated per
  `docs/LIM_ARCHITECTURE.md` §1.2's design.
- Reference training environment (`lim_training/requirements.lock.txt`)
  changed by exactly one line (a new, non-upgrade dependency, justified
  and documented in §2 above).

## 9. Open items for the owner (not resolved here)

1. Whether to relax `min_grounding_integrity` (0.95) given the real
   corpus's current small size makes 2 known failures disproportionately
   costly — or wait for more data to dilute the ratio naturally.
2. Whether `portfolio_reasoning` should continue to be exported at all at
   n=1, per `docs/DATASET_GENERATION_AND_TRAINING_SPEC.md` §11's own
   flagged question, deferred there and still deferred here.
3. `confidence_estimation`'s duplicate-rate failure will not resolve until
   real confidence values diversify beyond the current engineering
   ceiling — worth revisiting once calibration work (spec §8.2) has real
   signal to work with.

**LIM-1 is complete, tested, and stopped here for review — no fine-tuning
begins until this report is reviewed and approved, per the owner's
instruction.**
