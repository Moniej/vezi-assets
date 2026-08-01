# FRE-5 — Company Thesis: Pilot Case-Study Report

*Pilot report. Explicitly a case study, not a validated experiment — per
the approved pre-registration
(`docs/fre_runs/fre5_thesis_folding_preregistration.md`). Builds on
FRE-2/3/4 (`f7dd990`, `e7e210d`/`fre3-company-memory-baseline-2026-08-01`,
`e1dd1f9`). Additive only — no schema change, no write path, no
modification to any AI Intelligence Layer file or data.*

## What this is, stated plainly

`CompanyThesis` is an **explainable investment-research artifact**: bull
case, bear case, base case, key risks, catalysts, competitive position, a
financial signal summary, management assessment, capital-allocation
assessment, confidence, and missing evidence — composed entirely from
four already-verified FRE inputs (Evidence Graph, Company Memory,
cross-document corroboration/contradiction, Market Reaction Validation).
**It is not a statistically validated thesis-folding experiment.** Real
NGX implication data supports at most one meaningful multi-point ticker
(TOTAL), which is not enough to validate anything — the pre-registration
said so before any code was written, and this report holds to that.

## The synthesis rule (zero hidden weights)

Per the owner's explicit "no hidden scoring weights" constraint, this
pilot uses **exactly one, fully transparent rule** — the naive baseline
itself, not even a disclosed equal-weight mean: the current bull/bear/base
case is the **most recent non-`blocked_by_self_critique` implication's own
delta, verbatim**. `thesis_history` shows every prior implication in full,
unblended, so a reader can audit the whole trajectory themselves. There is
no numeric weight, decay factor, or blending formula anywhere in this
module — `confidence` is the most recent usable implication's own recorded
value, copied, never computed.

## Case study 1 — TOTAL (the one real multi-point ticker)

Four real implications, 2016–2022, `bullish, bullish, bullish, neutral`.
The AI layer's own cross-document reasoning had **already** flagged the
final transition as a contradiction (`contradicts_implication_id=3`, a
real, pre-existing `consistency_note`: *"Disagrees with prior implication
#3... 'bullish' vs this implication's 'neutral'... this new implication
has higher stated confidence (0.30 vs 0.00) — both rows preserved, neither
overwritten."*). `CompanyThesis` surfaces this verbatim as
`contradiction_note` — **the thesis does not silently present the most
recent "neutral" verdict as if it were uncontested; it explicitly tells
the reader an earlier bullish call was walked back, and why.**

| Field | Result |
|---|---|
| `bull_case` (current) | *"Confirms strong cash flow generation capable of sustaining regular dividend payments."* (verbatim, implication #7, 2022-10-27) |
| `contradiction_note` | Present — surfaces the real bullish→neutral disagreement |
| `confidence` | 0.0 (verbatim, real, not fabricated — every one of TOTAL's four implications was recorded at confidence 0.0) |
| `capital_allocation_assessment` | Real, non-neutral evidence found: *"Distributing dividends returns excess cash to equity holders according to corporate policy..."* |
| `financial_signal_summary` | Real evidence found: balance_sheet/cash_flow both assessed `negative` (a dividend payout mechanically reduces cash/equity — correctly captured) |
| `competitive_position` | **No evidence found** — 0/60 real causal-chain steps ever classify as competitive (FRE-2's own finding, holding here too) |
| `management_assessment` | **No evidence found** — `management_history` is empty platform-wide |
| `missing_evidence` | 11 real, open research tasks (e.g., *"Cross-reference recent earnings and cash flow statements to evaluate dividend payout ratio and coverage"*) — genuine gaps the AI layer itself already flagged, not invented here |

## Case study 2 — CILEASING (a clean corroborating chain, contrasted with TOTAL)

Three real implications; 2 usable + 1 excluded
(`blocked_by_self_critique`, the same governance already confirmed in
FRE-3). No contradiction — a clean corroborating chain
(`corroborates_implication_id` set on both, no `contradicts_implication_id`
anywhere). This is the deliberate contrast case: **the same mechanism, on
different real data, correctly produces a quiet, uncontested thesis
instead of a flagged one** — the contradiction machinery only fires when
there is a real contradiction to report.

## Case study 3 — GTCO (the correct-empty-thesis case)

GTCO's *only* real implication (the ₦400.5bn rights issue) is
`blocked_by_self_critique`. `CompanyThesis` for GTCO is **empty by
design** — `bull_case`/`bear_case`/`base_case`/`confidence` are all
`None`, `thesis_history` has zero entries, and `missing_evidence` states
exactly why: *"The only 1 real implication(s) for this ticker were
blocked_by_self_critique — correctly declining to synthesize a bull/bear
/base narrative from a rejected implication, pending human review."*
**This is the single most important result in this pilot**: the mechanism
does not manufacture a plausible-sounding thesis when the platform's own
governance has already rejected the only evidence available. An empty,
honest result is the correct output here, not a defect.

## What works

- The four-input composition (Evidence Graph + Company Memory +
  cross-document corroboration/contradiction + Market Reaction Validation)
  functions correctly end to end on real data, with zero write path and
  zero schema change.
- The `blocked_by_self_critique` exclusion (inherited from Company Memory,
  FRE-3) correctly propagates into the thesis layer — verified on two
  independent real cases (CILEASING's partial exclusion, GTCO's total
  exclusion).
- The real, pre-existing contradiction-tracking mechanism (Part 6) is
  successfully surfaced, not re-invented — this module reads
  `contradicts_implication_id`/`consistency_note`, it does not compute
  agreement/disagreement itself.
- Every generated field either cites real, sourced text (a quoted
  `impact_assessments.explanation`, a real `causal_chain_steps.statement`,
  a real `research_task_candidates.description`) or an explicit "No
  evidence found" statement — never a vague, uncited summary.

## What data is missing (stated honestly, per ticker and structurally)

- **Competitive position**: structurally near-absent across the entire
  real dataset — a direct, confirmed continuation of FRE-2's finding
  (0/60 causal-chain steps ever classify competitive).
- **Management assessment**: structurally absent for every ticker — no
  `management_change` extraction has been run at any volume (a real,
  disclosed, systemic gap, not specific to any one company).
- **Financial signal summary**: real but shallow — derived from
  `impact_assessments`' qualitative verdicts only, explicitly *not* the
  same as a true financial-statements-based quality score (still blocked
  on the same unacquired dataset named throughout this whole program).
- **Catalysts**: real (structured `qualification_date`/`payment_date`
  columns), but every date in this historical dataset is necessarily in
  the past — disclosed explicitly as "historical reference date, not a
  forecast" in every catalyst entry, never presented as forward-looking.

## What cannot yet be validated

- **Whether the naive-baseline folding rule is "good."** With one real
  multi-point ticker, there is no comparison to run and no baseline to
  beat — this pilot demonstrates the mechanism runs correctly and
  transparently, nothing more.
- **Longitudinal consistency as a scored metric** (Part 11) — not
  computed this pass, per the pre-registration; two real snapshots
  (TOTAL, CILEASING) is not enough volume to report a metric rather than
  a single anecdote.
- **Generalizability beyond these three tickers.** Every finding above is
  reported as a real, disclosed observation about three specific real
  cases, not a claim about NGX companies in general.

## Future requirements for a true thesis-validation experiment

Restated, concretely, from the pre-registration: **≥5 tickers, each with
≥3 real, non-blocked implications spanning meaningfully different
dates**, before a fold-weight comparison or a longitudinal-consistency
score becomes statistically meaningful rather than anecdotal. This is a
direct function of dataset growth (more real documents processed through
the existing, unmodified AI Intelligence Layer pipeline), not a code
change — no part of this module needs to be rebuilt to support that
future experiment; it needs more real data to run on.

## Constraints honored (restated, verified against the actual code and tests)

- No expected-return prediction, no alpha claim, no valuation output —
  confirmed: no function in `company_thesis.py` computes a return or
  numeric forecast of any kind.
- No hidden scoring weights — confirmed: the synthesis rule is
  "most-recent-verbatim plus full transparent history," zero numeric
  blending.
- No fabricated confidence — confirmed: `confidence` is always either a
  real, copied `investment_implications.confidence` value or `None`
  (never invented when no usable implication exists, as in GTCO's case).
- Every thesis statement traces to evidence — confirmed by construction:
  every field is either a quoted/cited real value or an explicit "No
  evidence found" statement.

## Verification performed

| Check | Result |
|---|---|
| `scripts/fre/test_company_thesis.py` | **21/21 PASS** (TOTAL's real contradiction surfaced correctly, CILEASING's clean corroboration, GTCO's correct-empty-thesis behavior, PIT-filtering correctness, graceful degradation on a nonexistent ticker, no numeric alpha claim in generated text) |
| `scripts/test_reasoning_pipeline.py` (pre-existing) | 154/154 PASS, unchanged |
| `scripts/fre/test_evidence_graph.py` (FRE-2) | 29/29 PASS, unchanged |
| `scripts/fre/test_company_memory.py` (FRE-3) | 16/16 PASS, unchanged |
| `scripts/fre/test_reaction_check.py` (FRE-4) | 16/16 PASS, unchanged |
| `scripts/check_db_safety.py` | PASS, 0 violations |
| Production DB row counts, all 27 tables | Unchanged — this module has no write path at all |

## Dependencies

`docs/fre/07_investment_thesis_engine.md` (the design, narrowed per the
approved pre-registration), `docs/fre_runs/fre5_thesis_folding_preregistration.md`
(this pilot's governing scope document), FRE-2's `evidence_graph.py`,
FRE-3's `company_memory.py`, FRE-4's `reaction_check.py` (all imported
directly, composed rather than re-implemented).

---

*Per the standing instruction, this concludes FRE-5. Stopping here and
awaiting review before beginning FRE-6.*
