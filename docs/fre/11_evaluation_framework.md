# FRE Part 11 — Evaluation Framework

*Design only. Extends `docs/LIM_ARCHITECTURE.md` §6's evaluation table and
reuses `grounding.py`/`pilot_summary.py`/the LIM eval harness's
methodology (bootstrap CIs, live re-verification) rather than inventing new
statistical machinery. See `docs/fre/00_fre_master_index.md` for standing
rules.*

## Objective

Define measurable, reproducible metrics for reasoning quality, financial
correctness, causal correctness, grounding, citations, uncertainty,
calibration, hallucination resistance, portfolio usefulness, investment
usefulness, and longitudinal consistency — the owner's exact eleven
dimensions — as concrete extensions of methodology this platform has
already built and validated, not a parallel evaluation philosophy.

## Rationale — this program already has a working evaluation methodology; extend it, don't replace it

Two evaluation systems already exist and already work: (1) the AI
Intelligence Layer's live-data validation (2026-07-27 stabilization pass:
90.0% precision / 100.0% recall vs. Phase B ground truth, 100% grounding +
citation integrity on live re-verification, measured on real NGX filings,
not a synthetic rehearsal); (2) the LIM research program's statistical
discipline (bootstrap CIs, seed=42, 2000 resamples, paired significance
tests, applied consistently across RB-1 through RB-3c). Every metric below
is built by extending one of these two, not by inventing a third
methodology.

## Metric table

| Dimension | Metric | Method | Reuses | Status |
|---|---|---|---|---|
| **Grounding** | Grounding accuracy | Fresh, live re-verification of every quote against on-disk source text | `grounding.py`, `_fresh_grounding_reverify` (existing, validated on real data) | Buildable now |
| **Citations** | Citation accuracy | Evidence row resolves; `doc_id` matches the citing fact's own document | `validate_stabilization_e2e.py`'s `_citation_integrity` (existing) | Buildable now |
| **Hallucination resistance** | Hallucination rate | Fraction of claims with no supporting quote or `grounding_check='failed'` | `grounding.py` (existing, model-agnostic) | Buildable now |
| **Financial correctness** | Numeric cross-check rate | Extracted numeric facts vs. an independently-sourced anchor (same pattern as the existing GTCO/Zenith dividend cross-checks) | Phase B/C's existing numeric-fact validation pattern | Buildable now for existing fact types; blocked for statement-level line items until Part 10's financial-statements dataset exists |
| **Causal correctness** | Ontology-edge citation validity | For every `causal_chain_steps` row with `reasoning_mode` requiring an ontology citation (Part 4's causal/macro modes): does the cited edge exist in Part 1's ontology, and does the row's `confidence_rationale` correctly surface the edge's `evidence_status` (especially `ngx_rejected`)? | **New, but entirely mechanical** — a direct extension of the spec's existing §11 banned-phrase-style checks | Buildable once Part 1's ontology has real edges (small initial core, see Part 1) |
| **Reasoning quality (general)** | Mechanical-proxy score + periodic human rubric | (a) reuse `self_critique.py`'s own `unevidenced_inference`/`correlation_vs_causation` mechanical checks as automated signals; (b) a human rubric pass on a gold set, reported honestly, never faked as a single automated number | `docs/LIM_ARCHITECTURE.md` §6, unchanged | Buildable now for (a); (b) requires the strategy-narrative gold set (Part 10) for the hardest reasoning modes |
| **Layer completeness** | `implication_layer` coverage | `HAVING COUNT(DISTINCT implication_layer) < 3` audit query (Part 3) | New, mechanical | Buildable once Part 3's `implication_layer` column exists |
| **Uncertainty / calibration** | Reliability diagram: stated `confidence` bucket vs. later-realized correctness | Bucket every `investment_implications.confidence` value into deciles; for each bucket, compute the fraction later confirmed correct by Part 6's quantitative reaction-check or Part 7's thesis-accuracy retrospective; a well-calibrated engine's bucket-fraction should track the bucket's own stated confidence | **New — the single hardest metric on this list, see below** | **Maturity-gated**: requires enough *time* to elapse for outcomes to be observable, not just enough data volume |
| **Self-critique effectiveness** | Regression-style replay against known real teacher blocks (e.g. the CILEASING `insufficient_information` fail) | `docs/LIM_ARCHITECTURE.md` §6, unchanged | Buildable now |
| **Longitudinal consistency** | `CompanyThesis` fold-stability score: does confidence/direction whipsaw between consecutive snapshots without new corroborating evidence? | New — an audit over Part 7's append-only thesis history, counting direction reversals not backed by a `source_implication_ids` delta of sufficient magnitude/confidence | New, mechanical once Part 7 exists | Buildable once Part 7's fold history has enough snapshots per ticker to measure |
| **Investment usefulness** | Deliberately qualitative, low-frequency owner/analyst side-by-side review | `docs/LIM_ARCHITECTURE.md` §6, unchanged — explicitly **not** assigned a synthetic numeric score | Existing precedent, reused verbatim | Process, not automatable |
| **Portfolio usefulness** | Same qualitative process, scoped to Part 9's Tier-1 capabilities only (screening/watchlist relevance) — **never** evaluated as if it were Tier-2 ranking/sizing usefulness, since that would misrepresent a gated capability as live | New scoping of the existing process | Process, gated identically to Part 9 |

## Calibration — why this is the hardest metric, and how it must be gated

Calibration is the one metric in this framework that cannot be rushed: it
requires a stated confidence *and* enough elapsed time for a real-world
outcome to be observable (Part 6's reaction-check window, or Part 7's
thesis-accuracy retrospective). Measuring calibration too early — on a
gold set with no realized outcomes yet — would produce a number that looks
like a real metric but measures nothing. **This document explicitly forbids
reporting a calibration score before a minimum realized-outcome sample size
is reached** (the exact floor value is a decision for whoever implements
this, following the platform's own "don't invent a threshold with no
evidence behind it" discipline — the same restraint already applied to
duration/magnitude buckets in the Reasoning Engine Specification §6, and to
the self-critique gate's not-yet-set `insufficient_information` floor).
Reporting "calibration: not yet measurable, N outcomes observed, minimum M
required" is a legitimate, expected interim state — not a gap to paper
over with an early, misleading number.

## The gating criterion — reused directly from LIM

`docs/LIM_ARCHITECTURE.md` §6: *"LIM must match the Gemini baseline within
an owner-agreed tolerance across every row above before it is even
considered as a swappable option."* This document adopts the identical
structure for the FRE: **before any FRE reasoning output is read by any
Tier-1 portfolio capability (Part 9), it must match a human-analyst gold
-set baseline within an owner-agreed tolerance across every applicable row
in the table above** — grounding, citation, hallucination, causal
correctness, and layer completeness at minimum, since those are
measurable without waiting on calibration's time-dependent floor. This is
a **disclosed, deliberate gate**, never an automatic cutover — same
language as every other gate in this program.

## Alternatives considered

1. **Invent a single composite "FRE quality score" blending all eleven
   dimensions into one number.** Rejected — this is the exact
   false-precision failure this whole program has repeatedly refused
   elsewhere (Part 8's valuation triangulation, Part 9's correlation notes)
   applied to evaluation itself; a blended score would hide which specific
   dimension is weak, defeating the point of measuring eleven dimensions
   separately.
2. **Measure calibration immediately using a synthetic/simulated outcome
   proxy instead of waiting for real realized outcomes.** Rejected — a
   simulated proxy is exactly the kind of ungrounded evaluation this
   platform's "never fabricate" discipline forbids; an honestly-labeled
   "not yet measurable" beats a fabricated early number.
3. **Skip periodic human rubric review in favor of fully-automated
   reasoning-quality scoring.** Rejected — `docs/LIM_ARCHITECTURE.md` §6
   already disclosed this cannot be fully mechanized and refused to fake it
   as a single number; this document inherits that refusal rather than
   relaxing it under FRE's larger scope.

## Trade-offs

- Mechanical proxies (banned-phrase checks, layer-completeness audits) are
  cheap and always-on but only catch *structural* failures, not subtle
  reasoning errors — the human rubric pass remains necessary precisely
  because the mechanical checks cannot substitute for it, only reduce how
  often it's needed.
- Gating every Tier-1 portfolio capability behind the full metric suite
  slows down how quickly Part 9's screening/watchlist features could go
  live — a deliberate trade-off favoring correctness over speed, consistent
  with the charter's "never optimize for positive results — optimize for
  truthful ones."

## Risks

- **Metric gaming via mechanical-check-shaped output** — a reasoning call
  could learn to produce text that passes the banned-phrase/layer
  -completeness checks without genuinely improving underlying reasoning
  (a known general risk with any mechanical proxy metric). Mitigation is
  the same one already used for LIM's own metrics: never rely on a single
  proxy alone, always pair with periodic human review, and treat a
  mechanical-metric improvement with no corresponding human-rubric movement
  as a signal to investigate, not celebrate — directly analogous to how
  this program already caught `exact-match` being "a known blind spot, not
  a true regression signal" for LIM (`lim_research_review.md` finding 5).
- **Small-sample instability** in causal-correctness and longitudinal
  -consistency metrics until real ontology/thesis volume accumulates —
  report sample sizes and confidence intervals alongside every number,
  never a bare point estimate (the same bootstrap-CI discipline used
  throughout the LIM program).

## Future extensions

- Once calibration is measurable, a per-`reasoning_mode` (Part 4)
  calibration breakdown — are causal-mode claims better calibrated than
  comparative-mode claims? A genuinely new, high-value question once the
  data exists.
- A "gold-set drift" check — does the human-analyst gold set itself need
  periodic refreshing as NGX market conditions change (the same regime
  -sensitivity concern already documented for H-008's low-vol rejection)?

## Dependencies

- `grounding.py`, `self_critique.py`'s mechanical checks, `pilot_summary.py`,
  the LIM eval harness's bootstrap-CI conventions (all existing, unchanged).
- Part 1 (ontology, for causal correctness), Part 3 (`implication_layer`),
  Part 6 (reaction-check, for calibration's outcome signal), Part 7
  (`CompanyThesis` fold history, for longitudinal consistency and
  thesis-accuracy retrospectives), Part 9 (Tier-1 scoping for portfolio
  -usefulness evaluation), Part 10 (the strategy-narrative gold set).
- A defined, owner-agreed tolerance for the gating criterion — explicitly
  not set by this document, the same open-decision pattern already used
  for every other unresolved threshold in this program.
