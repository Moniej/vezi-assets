# Fund Alpha — Charter

*Adopted 2026-07-15. This document sits above every other document in the
project. When any plan conflicts with it, this wins.*

## The objective

Build **Fund Alpha**: an institutional-quality alpha engine that
consistently identifies profitable investment opportunities and can answer,
at any time, with provenance:

- What should I buy? What should I sell?
- When should I enter? When should I exit?
- How much capital should I allocate?
- What is the expected return versus risk?
- What is the confidence level of the signal?
- Which opportunities should be ignored?

Everything else — database, providers, backtester, governance — is
supporting infrastructure, valuable exactly insofar as it improves those
answers.

## Hierarchy

```
Fund Alpha
└── Alpha Engine (decision-making layer)          ← the product
    └── Trading & Investment Models                ← validated alpha sources
        └── Research & Validation Framework        ← eliminates weak ideas fast
            └── Data Infrastructure                ← feeds model discovery
```

**The standing priority hierarchy for all proposed work (2026-07-15):**

1. Improves the Alpha Engine.
2. Enables multiple future hypothesis families.
3. Produces reusable datasets.
4. Accelerates testing of many ideas.
5. Only then: optimizes an individual hypothesis.

Work that only serves level 5 never outranks work at levels 1–4. Work that
expands infrastructure without touching any level gets built only when a
model demands it.

## Success metrics — the fund's KPIs (permanent, on every engine status report)

1. **Independent validated alpha sources** (the headline).
2. **Hypotheses tested per month** (discovery throughput — honest rejections
   count).
3. **Average time from idea to verdict.**
4. **Reusable evidence-grade datasets.**
5. **Candidate hypothesis discovery rate** — evidence-based hypotheses
   registered per quarter (human-generated now; Discovery-Engine-generated
   later).
6. **Alpha engine readiness** — models wired and able to emit
   provenance-backed recommendations the day a source validates.

The objective is never NGX sector rotation, or any single market or
strategy class. The competitive advantage is the repeatable machine —
discover, validate, deploy — pointed wherever alpha exists.

## The living pipeline (hypothesis generation is a platform function)

The queue is never a fixed backlog. New datasets continuously generate new
candidates, and every completed hypothesis — confirmed or rejected — is
mined for follow-on ideas. After every verdict and every major ingestion,
the platform asks, in writing (post-mortem, family map, or ledger entry):

- What patterns appeared during validation that deserve their own hypothesis?
- What unexpected relationships emerged from the data?
- Which datasets can be combined into entirely new research programs?
- Which rejected hypotheses suggest a different *mechanism* rather than a
  dead end?

Precedent: H-001's rejection generated H-002/H-003 (post-mortem §8); its
validation by-products generated H-004/H-005 (attribution showed Oil & Gas
dominance → F12; the walk-forward regime work → F11). That pattern is now
mandatory, not incidental.

## Language rule: priority ≠ predicted success

No hypothesis is ever described as "likely to validate" before testing.
Priority language must cite **research efficiency** only: acquisition cost,
dataset reuse, and time-to-verdict. "H-004 is the highest-priority candidate
because it has low acquisition cost, reuses existing datasets, and can reach
a statistically rigorous verdict quickly" — never "H-004 could be our first
confirmed alpha." Expected success is what the validation exists to measure;
assuming it corrupts the process.

## The queue, not the hypothesis

**The headline success metric is the number of independent, validated alpha
sources accumulated in the engine — never the fate of any single hypothesis.**
H-003 is the next candidate in the queue, nothing more. If it fails, the
platform moves to H-004 the same day; if H-004 fails, H-005. Rejections are
throughput, not setbacks — H-001's rejection was the platform working.

Operating rules:
- The ledger must always hold a stocked queue of registered candidates so a
  rejection immediately hands work to the next hypothesis.
- Data acquisitions are justified by how many *queued and future* candidates
  they feed (hierarchy level 2–3), never by one hypothesis's needs. Example:
  Sprint 1 (MPC history + CBN circulars + Brent) feeds H-003, H-004, and
  H-005 simultaneously — that is why it ranks, not because H-003 wants it.
- No hypothesis may consume the roadmap: when in doubt, prefer the
  acquisition or tool that shortens time-to-verdict for *many* ideas.

## Long-term engine vision (build milestones, not upfront)

The engine grows into an institutional investment intelligence system
combining many validated model families simultaneously — event-driven,
factor, statistical arbitrage, mean reversion, momentum, ML, alternative
data, sentiment, macro allocation, liquidity/flow, execution optimization.
Milestone-gated so the engine never outruns its evidence:

- **≥1 validated source:** single-model recommendations with provenance
  (adapter wiring, already designed).
- **≥2 validated sources:** signal-combination and capital-allocation layer
  (correlation of alpha sources, dynamic weighting) — built THEN, not now.
- **Ongoing:** risk monitoring and full-provenance explanation attach to
  every recommendation from day one; they are schema, not add-ons.

## What the engine is

A continuously running decision layer that ingests current data, runs every
**validated** model, and emits ranked recommendations — each one carrying:
instrument, action, size, horizon, expected risk-adjusted return, a
confidence rating from the existing rating machinery, a plain-language
rationale, and provenance (hypothesis ID + experiment IDs) tracing the
recommendation to immutable research records.

Scope is deliberately broad: equities, macro, event-driven, sentiment,
ML/statistical models, statistical arbitrage, portfolio construction, and
execution optimization are all admissible model classes. The hypothesis
family map (`HYPOTHESIS_FAMILY_MAP.md`) is open-ended by design; new
families join it before signal work starts.

## The engine's honesty constraints (non-negotiable)

1. **The engine only speaks from validated models.** A model becomes a
   recommendation source only when its hypothesis is `confirmed` in the
   ledger on evidence-grade data, having survived the full validation
   gauntlet (placebo, multiple-testing correction, walk-forward, OOS,
   capacity, costs). No exceptions for promising-looking development
   results.
2. **"No position" is a first-class output.** When no validated edge covers
   a decision, the engine says so and explains what is in the pipeline and
   what blocks it. An engine that always has a trade is broken.
3. **Every recommendation is explainable and reproducible** down to
   experiment IDs. If the provenance chain is missing, the recommendation is
   invalid.
4. **Capacity and cost are part of the recommendation**, not footnotes:
   sizing respects the validated capacity analysis; expected returns are
   net of the modeled cost stack.
5. The engine outputs *model-generated signals for the fund's own research
   and decision process* — it is decision support with full provenance, not
   a substitute for the fund's judgment or its compliance obligations.

## Current honest state (2026-07-15)

- Validated alpha sources: **0** (H-001 rejected & frozen; H-003 blocked on
  event-data acquisition; F2–F12 families blocked mostly on data).
- Therefore the engine's current correct output is: *no positions
  recommended; benchmark/cash is the default; pipeline status attached.*
- The bottleneck to a non-empty engine is **validated models**, and the
  bottleneck to validated models is **decision-relevant data** — which is
  why the acquisition core (price lists, membership PIT, dividend calendar,
  event database) remains the active work, now justified in engine terms:
  each dataset exists to raise the probability that some model graduates
  into the engine.

## Priority test applied to the current queue

| Work item | Engine justification | Verdict |
|---|---|---|
| Daily ephemeral capture | Feeds F3–F8 model families; time-gated | keep (must run daily) |
| H-003 Sprint 1 (MPC + circulars + Brent) | First candidate model class for the engine | **top priority** |
| Membership PIT + dividend calendar | Precondition for constituent-level model families + TR truth | keep, high |
| Wayback price-list probe | Historical depth for 5 families | keep, after Sprint 1 |
| More governance/platform features | Engine-neutral | **deprioritized — build nothing here unless a model demands it** |
| Engine decision layer (schema + status) | The product itself; grows only as models validate | built minimal today; expands per validated model |
