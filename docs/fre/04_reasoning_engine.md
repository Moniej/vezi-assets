# FRE Part 4 — Reasoning Engine Internals

*Design only. Adds reasoning MODES on top of the existing 14-step chain
(`docs/REASONING_ENGINE_SPECIFICATION.md`) — does not replace any step,
table, or gate. See `docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

The 14-step chain specifies **what** every reasoning call must produce
(identification → facts → causal chain → impact → duration → magnitude →
confidence → ... → self-critique). It does not specify **how** a call
reasons about *causal, counterfactual, historical, trend, comparative,
sector, macro, valuation, uncertainty,* and *portfolio* questions
differently — each of these is a distinct reasoning *mode* with its own
failure modes, its own evidence requirements, and (critically) its own
guardrail against overclaiming. This document defines ten reasoning modes
as **named, reusable sub-routines invoked at specific points in the
existing 14-step chain**, not a parallel process.

## Design principle: modes are invoked, not new steps

Every mode below is a way of constructing a `causal_chain_steps` entry
(Steps 3/8) or an `investment_implications` field (Step 9) — it does not
add a 15th step. A single fact's reasoning may invoke two or three modes in
sequence (e.g., a dividend cut fact might invoke `causal` reasoning, then
`historical` reasoning to check "has this company cut before," then
`comparative` reasoning to check "are peers also cutting"). The mode used
for each step is recorded (`causal_chain_steps.reasoning_mode`, one new
additive column, CHECK-constrained to the ten values below) so a reviewer —
or a future eval script — can ask "which mode produced this claim" and
apply the mode-specific guardrail retroactively.

## The ten modes

| Mode | Definition | Invoked at | Reuses (never rebuilt) | Guardrail — what it must NEVER claim |
|---|---|---|---|---|
| **Causal** | "A caused B" via a named mechanism | Steps 3/8, primary mode | Part 1's ontology edges (`definitional`/`causal`) | Never asserts a mechanism absent from the ontology without flagging it as a novel, lower-confidence claim (a mechanism not in the ontology is not forbidden — it just cannot claim the ontology's evidence-status backing) |
| **Counterfactual** | "What would have happened without event X" | Step 9 (thesis deltas), only when a comparison baseline exists | The existing research engine's placebo/synthetic-comparison *concept* (§4.5's cross-reference reuse of event-study machinery) — but see the explicit disclosure below | **Never presented as a statistical placebo test** — this is a qualitative narrative comparison ("peers without this event moved differently"), not the research engine's rigorous resampled placebo (`phase4.py`). Conflating the two would misrepresent an unvalidated narrative as validated statistics — an explicit, named risk (§ Risks) |
| **Historical** | "Has this happened before at this company, and what followed" | Step 11 (cross-reference) | `context.historical_event_reaction()` (built in Phase E specifically to reuse existing PIT primitives instead of the portfolio-facing `event_window_scores`) and Part 5's Company Memory | Never treats n=1-3 historical repeats as a statistically powered base rate — states the count explicitly, defers to the Historical/Trend confidence discipline below |
| **Trend** | Multi-period directional pattern (margin trend, leverage trend) | Step 9, feeds `intrinsic_value_reasoning` | Part 5's Company Memory time series | Never extrapolates a trend past the evidenced window — an explicit "trend observed over N periods, not a forecast" framing is mandatory text, not optional |
| **Comparative** | Company-vs-peer, using Part 2's `competitor_of`/sector edges | Step 11, and the Industry Reasoning Engine's existing propagation (Phase F, unchanged) | Phase F's `industry_reasoning.py` | Never inverts the direction of a peer effect algorithmically — Phase F's own explicit scope decision (no auto direction-inversion) is inherited unchanged, restated here for emphasis since comparative reasoning is exactly where the temptation to auto-infer "helps vs. hurts a peer" is strongest |
| **Sector** | Sector-wide pattern reasoning (e.g., "banking sector NIMs are compressing") | Step 4 (impact categories), aggregated across companies sharing a `sector` entity | Part 2's sector node + Part 1's sector-conditioned ontology edges | Never asserted from a single company's filing — requires evidence from ≥2 companies in the same sector node before a `sector`-level claim is made (a mechanical floor, same pattern as the self-critique gate's evidence-count checks) |
| **Macro** | Macro variable → company/sector transmission | Step 3/8, sourced from Part 1's macro ontology edges | Macroeconomic Reasoning Engine (architecture doc §4.5), unchanged | Must cite `evidence_status` (`ngx_confirmed`/`ngx_rejected`/`theoretical`) from the invoked ontology edge in `confidence_rationale` — mechanically checkable (Part 1) |
| **Valuation** | Direction/mechanism of intrinsic-value change | Step 9 | Part 8's Valuation Engine Architecture (design-only until a financial-statements dataset exists) | Never produces a numeric estimate absent the dataset dependency — the existing non-goal (Reasoning Engine Spec §13) is unchanged and restated |
| **Uncertainty** | Explicit treatment of what is NOT known | Step 7 (confidence) and Step 14 (self-critique) | `confidence_rationale` (already `NOT NULL`), `self_critique_reviews` | Never collapses "don't know" into a numeric confidence without the accompanying rationale text — already enforced mechanically (§11 of the spec), restated as this mode's home |
| **Portfolio** | What this implication would mean for sizing/positioning | Step 9's `portfolio_sizing_note` | Part 9's Portfolio Reasoning design | **Hard-gated**: qualitative note only, same restriction as the spec's existing non-goal; this mode's output is explicitly NEVER computed while Portfolio Construction remains gated (`docs/PLATFORM_ARCHITECTURE.md` §6, currently 0/2 validated independent factors) |

## Why counterfactual reasoning needs its own explicit disclosure

This is the one mode with a real, easy-to-make mistake: the platform
already has a rigorous, statistically-grounded counterfactual mechanism —
the research engine's **placebo test** (`phase4.py`, comparing a real
Sharpe ratio against a distribution of resampled/shuffled draws, e.g.
H-011's placebo p=0.0099). A reasoning engine that says "if this filing
hadn't happened, the stock would likely have done X" is doing something
categorically different — a single-instance, LLM-narrated comparison, not
a resampled statistical test. Using the word "placebo" or implying
statistical rigor for the reasoning engine's counterfactual mode would be a
direct, disclosed violation of the charter's "never invent alpha" /
"nothing bypasses pre-registration" principles, since it would let a
narrative conclusion borrow the *authority* of a mechanism it did not
actually run. **Mechanical enforcement**: any `causal_chain_steps` row with
`reasoning_mode='counterfactual'` is automatically appended with a fixed
disclaimer sentence in its `confidence_rationale` ("qualitative comparison,
not a statistical placebo test") — the same "don't just trust the model to
self-disclose" mechanical-check pattern used everywhere else on this
platform.

## Alternatives considered

1. **One undifferentiated "reasoning" step, no mode taxonomy.** This is
   the status quo (Steps 3/8 today). Rejected as the long-term design
   because it is exactly what makes counterfactual/statistical conflation
   possible — without a named mode, there is nothing to attach the
   mandatory disclaimer to, and nothing for a future eval script to
   group by when measuring mode-specific quality (Part 11).
2. **A separate LLM call per mode (ten calls instead of one reasoning
   pass).** Rejected on cost and latency grounds specific to this
   platform's LIM constraint (a 6GB-VRAM local model, per
   `docs/LIM_ARCHITECTURE.md` §2.3, cannot afford ten sequential calls per
   fact) — modes are a **tagging and guardrail discipline** applied within
   the existing single-pass draft + separate self-critique call structure,
   not a new call-volume multiplier.
3. **Let counterfactual reasoning directly invoke `phase4.py`'s real
   placebo machinery per-implication.** Rejected — `phase4.py` operates on
   registered, pre-registered hypotheses with defined holding periods and
   benchmarks; running it ad hoc per qualitative implication would be
   exactly the "reuse the query result as evidence, not a shortcut around
   validation" boundary violation the architecture doc's §7 already warns
   against for Step 11's cross-reference. Counterfactual reasoning stays
   qualitative and disclosed as such.

## Trade-offs

- Mode-tagging is metadata overhead (one more field, one more thing to get
  slightly wrong) in exchange for retroactive queryability and a concrete
  attachment point for guardrail text — judged worthwhile given how cheap
  the column is relative to the risk it manages (counterfactual/placebo
  conflation).
- Sector-mode's "≥2 companies" evidence floor will initially block almost
  every sector-level claim, since sector coverage is currently thin
  (`sector_ngx` unpopulated) — this is a deliberate, disclosed
  under-triggering in favor of never asserting a sector pattern from n=1.

## Risks

- **Mode misclassification** (tagging a genuinely causal claim as
  "historical" to dodge the causal mode's ontology-citation requirement) —
  mitigated the same way as Part 3's layer-skipping risk: a mechanical
  audit query, not solely trust in self-tagging.
- **Historical mode's small-n base rates being read as more informative
  than they are** — this is a known, general LLM failure mode (treating 2-3
  anecdotes as a trend); the guardrail text (state the count explicitly) is
  necessary but not sufficient — Part 11's evaluation framework should
  specifically test for this failure pattern, not assume the guardrail
  text alone prevents it.
- **Comparative mode inheriting Phase F's already-disclosed limitation**:
  peer resolution today is exact-name-match only (Phase F's completion
  report), so most real peer mentions won't resolve — comparative-mode
  reasoning will be sparse in practice until Part 2's entity resolution
  improves, not a new limitation this document introduces.

## Future extensions

- A per-mode confidence-calibration study (Part 11) once enough real mode
  -tagged output exists — do certain modes systematically over- or
  under-state confidence relative to later-realized accuracy?
- Mode-specific self-critique sub-questions (today's eight questions, §12.1
  of the spec, are mode-agnostic) — e.g., a counterfactual-specific
  question ("did this compare against a real baseline or an assumed one?")
  — deferred until real mode-tagged volume justifies the added review cost.

## Dependencies

- Part 1 (ontology, for causal/macro modes' evidence-status citations),
  Part 2 (entity graph, for comparative/sector modes), Part 5 (Company
  Memory, for historical/trend modes), Part 8 (Valuation Engine, for
  valuation mode), Part 9 (Portfolio Reasoning, for portfolio mode — hard
  -gated identically to the existing Portfolio Construction precondition).
- `context.historical_event_reaction()` (Phase E, existing, unchanged).
- `industry_reasoning.py` (Phase F, existing, unchanged) for comparative
  mode's propagation mechanics.
- The self-critique gate (`self_critique_reviews`, unchanged) as the
  enforcement point for every mode's guardrail text.
