# FRE-2 — Evidence Graph Implementation

*Implementation report. Builds on `fre-architecture-baseline-2026-08-01`
(commit `f6f4034`) and the infrastructure recovery in commit `4a1ad50`
(`docs/fre_runs/incident_2026-08-01_prod_db_wipe.md`). Additive only — no
change to the AI Intelligence Layer, LIM, the Quant Engine, the evaluation
framework, or any database schema beyond what FRE-1 already added and
approved.*

## Scope reconciliation (stated openly, not silently renamed)

`docs/fre/12_research_roadmap.md`'s own phase table names "FRE-2" as
sector-classification and dataset-scoping wins. The owner's actual
directive for this pass — "Transform extracted evidence into structured
reasoning using the pipeline: Evidence → Observation → Financial
Implication → Business Implication → Competitive Implication → Investment
Implication → Confidence → Missing Evidence" — is Part 3's **Evidence
Graph** design, not the roadmap document's literal FRE-2. This report
treats the owner's directive as the authoritative reprioritization (the
owner outranks a design document's own roadmap numbering) and implements
Part 3 under the "FRE-2" label as instructed, while flagging the
divergence explicitly rather than quietly relabeling either document. The
roadmap's original FRE-2 (sector classification, `doc_type` splitting)
remains queued, unstarted, for a future pass.

## Objective

Implement the Evidence Graph (`docs/fre/03_evidence_graph.md`) end to end,
against **real data** already produced by the AI Intelligence Layer — not
synthetic rehearsal data — as a read-mostly layer that (a) classifies each
existing `causal_chain_steps` row into `financial`/`business`/`competitive`
(the two nullable columns FRE-1 already added and approved), (b) assembles
the full Evidence→...→Missing-Evidence chain per fact from tables that
already exist, and (c) mechanically surfaces where a fact's own
`impact_assessments` verdicts aren't reflected in its causal chain.

## What was built

| Artifact | Role |
|---|---|
| `src/ngxrot/fre/__init__.py`, `src/ngxrot/fre/evidence_graph.py` | The module: `classify_step_layer`, `classify_causal_chain_layers`, `backfill_implication_layers`, `EvidenceChain`/`build_evidence_chain`, `layer_gap_report` |
| `scripts/fre/test_evidence_graph.py` | 29 assertion checks, script-based (no pytest, matching `scripts/test_reasoning_pipeline.py`'s convention) |
| `scripts/fre/backfill_implication_layers.py` | The one script that writes to the real database — dry-run by default, auto-backs-up before `--apply`, verifies row counts and `foreign_key_check` before/after |
| `scripts/fre/verify_evidence_graph.py` | Read-only demo: prints the full chain for all 18 real facts + the gap report |

No schema change. No modification to `extract.py`, `self_critique.py`,
`reasoning.py`, `grounding.py`, `retrieval.py`, `context.py`,
`reasoning_engine.py`, `industry_reasoning.py`, `coverage_assessment.py`,
or `evidence_ranking.py` — every one of those remains exactly as it was at
`ai-layer-stable-baseline-2026-07-27`. This module only reads their output
and writes to the two columns FRE-1 already added for exactly this
purpose.

## Rationale — why this is additive, not a blocker requiring AI-layer changes

The instruction for this pass required any architectural blocker to be
documented and justified before touching anything outside FRE's own
scope. **No such blocker was found.** Everything Part 3's design needs —
`evidence`, `extracted_facts`, `causal_chain_steps` (plus FRE-1's
`implication_layer` column), `impact_assessments`, `investment_implications`,
`research_task_candidates` — already exists, already holds real data, and
is already correctly populated by the frozen AI Intelligence Layer. The
classification and assembly logic lives entirely in a new, separate
package (`src/ngxrot/fre/`), the same "new namespace, not a fork"
precedent `src/ngxrot/lim/` already set for LIM. The one write this module
performs (`backfill_implication_layers`) targets exactly the two columns
FRE-1 already added and the owner already approved — it does not touch
any column, table, or file the AI Intelligence Layer itself owns.

## The classifier — grounded in real data, not assumed

Before writing any classification rule, all 18 real facts with a causal
chain (fact_ids 144–161) were read in full. Finding, stated plainly: **17
of 18 are simple `dividend` facts whose entire 2–4-step chain is genuinely
and exclusively financial** (cash/balance-sheet/liquidity mechanics) — a
routine dividend payment has no business-strategy or competitive-
positioning content to find, and a classifier that manufactured some would
be inventing signal that isn't there. Only fact 144 (GTCO's real ₦400.5bn
rights issue — the same case already on record in `HANDOFF.md` as a real
self-critique block) exercises the full financial→business→competitive
range.

This directly shaped the design: `classify_step_layer()` is a small,
disclosed, three-lexicon keyword classifier (financial/business/
competitive terms, each drawn from Part 1's ontology node families and the
`impact_assessments` category vocabulary) applied per `causal_chain_steps`
row. A step is assigned the layer with a **strict majority** of keyword
hits; a tie or zero hits leaves it **unclassified (`NULL`)**, never
guessed — the same "unknown stays unknown" discipline this platform has
used since Phase A, applied to a new mechanical classifier instead of a
data-quality gap.

**Verified against real data, not asserted:**

- Fact 144's own 5 steps classify as `financial, business, business, None
  (a genuine 4-4 keyword tie), financial` — matching a step-by-step manual
  reading of the real text exactly.
- **Competitive never fires from step text alone, on any of the 18 real
  facts.** Fact 144's `competitive_advantage`/`long_term_moat`
  `impact_assessments` are genuinely `positive` (non-neutral, real
  content) — but the supporting reasoning lives entirely in
  `impact_assessments.explanation`, never in a `causal_chain_steps.statement`.
  This is a real, disclosed property of how the existing (frozen,
  unmodified) AI Intelligence Layer currently writes its causal chains,
  not a classifier shortfall — and it is exactly the kind of gap
  `layer_gap_report()` was built to surface mechanically (see below).
- A known, disclosed false positive: the step "*On 31 July 2019, dividends
  will be paid electronically to mandated shareholders registered as of
  12 July 2019*" ties 1–1 (financial: "dividend"; business: "mandate", from
  "**mandated** shareholders" — an e-dividend registration detail, not a
  regulatory mandate) and is correctly left unclassified rather than
  mis-labeled. Documented here rather than quietly tuned away, since
  chasing every such artifact risks overfitting the lexicon to this
  session's 18 facts.

**Full backfill result (real data, `--apply` run against the production
database, 2026-08-01):** of 60 real steps, **56 classified financial, 2
business, 0 competitive, 2 left unclassified** — an honest, unforced
reflection of a dataset that is overwhelmingly simple dividend facts plus
one complex corporate action.

## `layer_gap_report` — a real finding, not a synthetic demonstration

Part 3's original design sketched a bare `COUNT(DISTINCT implication_layer)
< 3` completeness check. Building against real data surfaced a better
signal: that bare check would also flag every simple dividend fact for
"only having one layer," which is **not a gap** — a dividend genuinely has
no business or competitive content to find. `layer_gap_report()` instead
cross-references each fact's **genuinely active** (non-neutral, non-
`unknown`) `impact_assessments` categories against which layers are
actually represented in its (backfilled) causal chain, flagging only a
real mismatch.

**Run against the real, backfilled database, 2026-08-01 — every one of the
18 facts is flagged, for one of exactly two reasons:**

1. **Fact 144** is missing only `competitive` — its business and financial
   content ARE represented in its chain; only the competitive-positioning
   reasoning (real in `impact_assessments`, per above) never made it into
   a distinct causal-chain step.
2. **All 17 dividend facts** are missing `business` specifically — every
   one of them has `capital_allocation = 'positive'` (paying a dividend
   *is* a capital-allocation act, correctly assessed as such), but not one
   of their causal-chain steps reads as business language; the chain stays
   in financial-mechanics phrasing throughout ("reduces cash... retained
   earnings... delivering yield").
3. **No fact is ever missing `financial`** — every real chain has at least
   one financial-classified step, consistent with financial-statement
   mechanics being the one thing every corporate-action fact touches.

This is a genuine, mechanically-discovered, disclosed property of the
existing (frozen, unmodified) AI Intelligence Layer's causal-chain writing
style — 18/18 real facts have at least one gap between what their
`impact_assessments` say is materially true and what their causal chain
actually walks through. It is presented as a finding for future review,
not as something this pass fixes (fixing it would mean changing
`extract.py`'s prompt/generation behavior, squarely the AI Intelligence
Layer, out of scope here).

## Alternatives considered

1. **Step-order-based classification** (early steps = financial, later =
   business/competitive, per Part 3's original sketch). Rejected after
   reading fact 144's real chain: its actual business content (steps 1–2)
   comes immediately after the raw-fact restatement, and its final step is
   financial/valuation-flavored, not competitive — a step-order rule would
   have been wrong on the one real case that matters most for testing it.
2. **A whole-fact classifier using `impact_assessments` category presence
   alone** (no step-text analysis). Rejected — every fact's schema-required
   completeness (`impact_assessments` covers all 13 categories for every
   fact, mostly `neutral` where irrelevant) means "category present"
   barely discriminates at all; the real signal has to come from what the
   causal chain's own text says, not from which categories exist.
3. **Tune the lexicon to maximize classification rate on these 18 facts.**
   Rejected — deliberately not done. A lexicon tuned to eliminate every
   observed tie/false-positive on exactly this dataset would be
   overfitting to 18 facts, the same risk this platform's LIM research has
   repeatedly guarded against with held-out data and pre-registration.
   The classifier is disclosed in full, small, and left honestly imperfect.
4. **Have `extract.py` populate `implication_layer` at generation time**
   (Part 4's eventual design intent). Rejected for THIS pass — it would
   touch the frozen AI Intelligence Layer without a documented blocker,
   and no blocker was found: the standalone backfill approach fully
   satisfies FRE-2's stated objective using only already-existing data.

## Trade-offs

- A standalone backfill (not generation-time tagging) means every future
  new fact needs the backfill script re-run — an operational step, not
  automatic. Acceptable for now; automating it would require touching
  `extract.py`, deferred per the alternatives above.
- The classifier's honest ~3% unclassified rate (2/60 steps) and 0%
  competitive-classification rate on this dataset are real limitations of
  a small, disclosed lexicon — not hidden, and not chased down with added
  complexity that risks overfitting.

## Risks

- **Lexicon overfitting to 18 facts** — the current dataset is small and
  dividend-dominated; a much larger or differently-shaped future dataset
  (e.g., many more corporate actions like fact 144) could reveal the
  lexicon needs real expansion, not just re-validation. Flagged for
  re-evaluation once dataset volume grows (Part 10/12's roadmap).
- **The "0% competitive" finding could be misread as a classifier defect**
  if this report isn't read carefully — restated here for emphasis: it
  reflects a real property of the existing causal-chain text, verified by
  direct inspection of fact 144's `impact_assessments.explanation` text
  containing the actual competitive reasoning that its `causal_chain_steps`
  never restates.
- **Backfill is a one-time operational step**, not wired into any ongoing
  pipeline — a future new fact will show `implication_layer IS NULL` until
  the script is re-run manually. Documented, not automated, in this pass.

## Future extensions

- Feed `layer_gap_report()`'s findings back as a candidate prompt-design
  observation for a future, separately-reviewed AI Intelligence Layer
  change (never done silently or as a side effect of this pass).
- Re-run the backfill and gap report once dataset volume grows past this
  session's 18 facts, to see whether the classifier's ~94%-financial
  distribution is a property of dividend-heavy real data specifically, or
  would hold at scale.
- Part 4's reasoning-mode tagging (the `reasoning_mode` column FRE-1 also
  added) remains explicitly out of scope for this pass, per the owner's
  own 8-stage pipeline description (which does not mention reasoning
  modes) — left for a future, separately-scoped phase.

## Verification performed

| Check | Result |
|---|---|
| `scripts/fre/test_evidence_graph.py` | **29/29 PASS** (classifier correctness on real fact 144, `EvidenceChain` assembly against real data, `layer_gap_report` correctness, backfill dry-run/apply/idempotency, all mutation testing confined to a disposable scratch copy). One real bug found and fixed while testing: the test initially assumed production always starts fully unbackfilled, which broke the moment the real `--apply` backfill was actually run against production later in this same pass — fixed by resetting the scratch copy to a known state before the dry-run/apply/idempotency assertions, and by comparing production's row counts before/after THIS test run rather than asserting a hardcoded absolute state |
| `scripts/test_reasoning_pipeline.py` (pre-existing suite) | **154/154 PASS**, unchanged |
| `scripts/check_db_safety.py` | **PASS**, 0 violations (one false-positive self-flag from this pass's own test script was fixed by using `db.DEFAULT_DB` instead of a re-hardcoded literal path, not by weakening the check) |
| Production DB row counts, all 27 tables | Unchanged except `causal_chain_steps` (58/60 rows gained a non-NULL `implication_layer`; no row inserted or deleted anywhere) |
| `PRAGMA foreign_key_check` after the real `--apply` backfill | Clean |
| Backup before the real write | `data/ngx.sqlite.pre_fre2_backup_2026-08-01` created automatically by the backfill script itself before writing |

## Dependencies

`docs/fre/03_evidence_graph.md` (the design this implements), FRE-1's
`causal_chain_steps.implication_layer` column (the write target),
`evidence`/`extracted_facts`/`impact_assessments`/`investment_implications`/
`research_task_candidates` (all existing, unchanged, read-only), the
infrastructure safeguards from commit `4a1ad50` (`db.new_scratch_db_path()`,
`scripts/check_db_safety.py`), used throughout this implementation's own
testing.

---

*Per the standing instruction, this concludes FRE-2. Stopping here and
awaiting review before beginning FRE-3.*
