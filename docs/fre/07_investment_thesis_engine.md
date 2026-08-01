# FRE Part 7 — Investment Thesis Engine

*Design only. Aggregates existing `investment_implications` rows
(per-fact) into a new, append-only, company-level `CompanyThesis` object —
extends `company_intelligence.py`'s `CompanyProfile`, does not replace it.
See `docs/fre/00_fre_master_index.md` for standing rules, especially the
Expected Return guardrail below.*

## Objective

Produce, per company, a standing **Bull case / Bear case / Base case**
narrative with catalysts, key risks, competitive position, management
assessment, financial/growth/capital-allocation quality, intrinsic value
direction, expected return, confidence, and missing evidence — the owner's
exact thirteen fields — as a single coherent, evidence-traceable object,
not thirteen independently-invented judgments.

## Rationale — this is an aggregation layer, not a new fact-generation layer

`investment_implications` today stores **per-fact deltas**: "this specific
filing's fact changes the bull case *this much*, in *this direction*."
There is no standing, current "here is the thesis on this company right
now" object — each row is a delta against an implicit prior state that is
never itself materialized. The Investment Thesis Engine's actual job is
this materialization: an append-only `CompanyThesis` snapshot, rebuilt
whenever a new non-blocked `investment_implications` row lands for a
ticker, by folding the new delta into the most recent prior snapshot. This
is the same append-only-restatement pattern `events_asof`/`db.py`'s PIT
readers already use (latest-vintage-wins, never an UPDATE) — applied to a
narrative object instead of a data row.

```
CompanyThesis(ticker, generated_at, source_implication_ids: list[int]):
    bull_case: str           # cumulative, evidence-quoted narrative
    bear_case: str
    base_case: str
    catalysts: list[Catalyst]
    key_risks: list[str]
    competitive_position: str
    management_assessment: str
    financial_quality: QualityRating
    growth_quality: QualityRating
    capital_allocation_quality: QualityRating
    intrinsic_value_direction: str        # increase/decrease/unclear — UNCHANGED semantics
    expected_return: ExpectedReturnField  # see the guardrail below — NOT a numeric alpha estimate
    confidence: float
    missing_evidence: list[str]           # from research_task_candidates, Part 3
```

Every field cites the `investment_implications`/`extracted_facts`/`evidence`
rows it was built from (`source_implication_ids`), so `explain()`
(architecture doc §9, already a mandatory function for any report-rendering
code) can walk from a thesis field all the way back to a source document
exactly as it does for a single implication today — the aggregation layer
adds no new opacity.

## Field-by-field: source and status

| Owner's field | Source | Status | Design note |
|---|---|---|---|
| **Bull / Bear / Base case** | `investment_implications.bull_case_delta`/`bear_case_delta`/`base_case_delta`, folded across the ticker's full non-blocked history | Deltas exist today; the folding/aggregation is new | Folding must be append-only-narrated ("as of [date], [new evidence] strengthened the bull case because...") not a silent overwrite of the prior narrative — losing the history of *why* the thesis changed would itself violate the platform's append-only discipline |
| **Catalysts** | Two sub-classes, kept distinct | New | **Calendar-derived** (near-certain: next AGM date, next expected dividend-qualification date) reuses the quant engine's existing `earnings_calendar.csv`/`exdiv_closure_calendar.csv` — zero new extraction, a read-only join. **Evidence-derived** (uncertain: "management guided to a Q3 product launch") is a normal `extracted_facts`-sourced claim, carries its own `extraction_confidence`, never conflated with the calendar-certain kind |
| **Key risks** | `investment_implications.risk_profile_direction` + `impact_assessments` rows with `direction='negative'` across `execution_risk`/`regulatory_risk`/`liquidity` categories | Existing fields, new aggregation | A risk list is a filtered, deduplicated view — no new extraction |
| **Competitive position** | Part 2's `competitor_of` graph + `impact_assessments.competitive_advantage`/`long_term_moat` | Depends on Part 2/Part 4's comparative mode | Confidence-capped until Part 2's peer-resolution coverage improves (Phase F's disclosed exact-match-only limitation) |
| **Management assessment** | Part 1's `management_quality`/`corporate_governance_score` qualitative nodes + Part 5's management-history/strategy-narrative timeline | Softest field on this list | Inherits every caution already stated for qualitative ontology nodes (Part 1) and the strategy-narrative timeline (Part 5) — never above `unvalidated_ai_interpretation`, always evidence-quoted |
| **Financial / Growth / Capital-allocation quality** | Directly the same three concepts `company_intelligence.py`'s `CompanyProfile` already scaffolds as vision fields, currently returning `UNAVAILABLE_FIELDS` for all but Size | Blocked, honestly, until a financial-statements dataset exists | This document does not invent a new quality-scoring mechanism — it is the same blocked field, now with a defined *future* population path (Part 1's `sector_ratio` nodes once the dataset exists) |
| **Intrinsic value direction** | `investment_implications.intrinsic_value_direction`/`intrinsic_value_reasoning` | Existing, unchanged | Aggregated as "the most recent, highest-confidence, non-superseded reading," with dissenting older readings kept in history, not discarded |
| **Expected return** | See guardrail below | **New field, maximum-risk field on this entire list** | |
| **Confidence** | Existing `confidence` + `confidence_rationale` discipline, aggregated as a weighted function of the underlying implications' own confidences (weighted down for stale/superseded deltas) | Existing mechanism, new aggregation formula (TBD, not invented here — see Open Decisions) | |
| **Missing evidence** | `research_task_candidates`, unresolved, for this ticker | Existing, direct reuse | |

## The Expected Return guardrail — the single most important design decision in this document

This is the one field with a real, catastrophic-if-wrong failure mode: the
charter's honesty constraints (§"The engine's honesty constraints") state
flatly that **"the engine only speaks from validated models... a model
becomes a recommendation source only when its hypothesis is `confirmed` in
the ledger."** Today exactly **one** factor is confirmed (H-011, Size,
`docs/FACTOR_REGISTRY.md`) — everything else in this entire FRE design
program, including every reasoning-engine output described across these
fifteen documents, is explicitly **not** validated alpha.

`CompanyThesis.expected_return` is therefore **not a number**:

```
ExpectedReturnField:
    qualitative_direction: str        # "favorable" / "unfavorable" / "unclear" — narrative only
    validated_factor_exposure: dict   # DIRECTLY reused, unchanged, from
                                       # company_intelligence.CompanyProfile.factor_exposures —
                                       # the ONLY place a real, provenance-backed number may appear,
                                       # and ONLY for tickers with an actual H-011 (or future
                                       # confirmed-factor) exposure
    reasoning_engine_view: str        # the qualitative bull/bear/base synthesis, explicitly
                                       # labeled 'unvalidated_ai_interpretation', never a return figure
```

**Any design, prompt, or future implementation that lets a reasoning-engine
call output a numeric expected-return percentage is a direct violation of
this program's own governing charter** and must be rejected on sight,
regardless of how well-reasoned the qualitative narrative behind it sounds
— this is the same "never invent alpha" principle stated as the very first
enforcing-mechanism row in the AI Intelligence Layer Architecture's §1
table, applied here at the one point in the FRE design most likely to
accidentally cross it (a "thesis" naturally wants to end in a number, and
that temptation must be designed against explicitly, not left to prompt
discipline alone).

## Alternatives considered

1. **Let the reasoning engine directly output an expected-return estimate,
   labeled "unvalidated," as a compromise.** Rejected outright — a labeled
   number is still a number, and institutional consumers of a research
   product reliably anchor on numbers regardless of disclaimers (a
   well-documented behavioral-finance failure mode, not a hypothetical).
   The field is qualitative-only, full stop, matching the existing
   `portfolio_sizing_note` precedent (TEXT, never a number, per the
   Reasoning Engine Specification §3).
2. **Skip thesis aggregation; let consumers read the raw
   `investment_implications` delta history directly.** Rejected as
   impractical for the stated use case (an analyst wants "what's the
   current thesis," not "here are 40 deltas, please fold them yourself") —
   but the raw history remains fully accessible via `explain()`, so nothing
   is hidden, only additionally summarized.
3. **Version `CompanyThesis` as mutable rows (UPDATE in place).** Rejected
   — breaks this platform's append-only discipline and would make "why did
   the thesis change" unanswerable after the fact, exactly the failure this
   design's folding mechanism exists to avoid.

## Trade-offs

- Folding logic (how much weight a new delta gets vs. the accumulated
  prior narrative) is a real, unresolved design parameter — deliberately
  left open for Part 12's roadmap rather than invented here, since getting
  it wrong either makes the thesis flip on every new filing (noisy) or
  barely move (stale); this is exactly the kind of threshold this
  platform's discipline says should be evidence-derived, not guessed.
- Calendar-derived catalysts are cheap and reliable; evidence-derived
  catalysts are valuable but carry real false-positive risk (management
  guidance is frequently vague or later abandoned) — the two are kept in
  visibly separate sub-fields specifically so a consumer can weight them
  differently without the engine doing that weighting silently.

## Risks

- **Thesis "staleness drift"**: if folding under-weights new contradicting
  evidence, a thesis could persist past the point its foundational facts
  are no longer current — mitigated by requiring every `CompanyThesis`
  snapshot to explicitly list its `source_implication_ids`' own `generated_at`
  range, so a consumer (or an automated staleness check) can flag a thesis
  built mostly from >N-month-old deltas.
- **Narrative aggregation smoothing over a real self-critique block**: if
  one of the deltas folded into a thesis was later `blocked_by_self_critique`,
  the folding logic must exclude it retroactively (a thesis rebuild
  triggered by a status change, not just by new evidence arriving) —
  a concrete implementation requirement flagged here, not resolved.
- **Restated Expected Return risk** (see guardrail): the single highest
  -consequence risk in this whole document if not enforced mechanically —
  Part 11's evaluation framework should include an explicit automated check
  that no `CompanyThesis.reasoning_engine_view` text contains a
  percentage-formatted numeric return claim (a regex-style banned-pattern
  check, same mechanism class as the spec's existing §11 banned-phrase
  check).

## Future extensions

- Once ≥2 validated independent factors exist (the charter's own
  `Portfolio Construction` trigger), `validated_factor_exposure` grows from
  one entry (Size) to a real multi-factor exposure profile — no redesign
  needed, the field is already shaped for it.
- A thesis-accuracy retrospective (did a "favorable" qualitative direction
  precede outperformance more often than a "unfavorable" one, measured
  honestly, including all misses) — itself a candidate hypothesis for the
  Discovery scanner, never asserted informally first.

## Dependencies

- `investment_implications`, `impact_assessments`, `research_task_candidates`
  (existing, unchanged). `company_intelligence.py`'s `CompanyProfile`
  (existing, extended not replaced). Part 1 (qualitative ontology nodes),
  Part 2 (competitive graph), Part 5 (Company Memory, management/strategy
  history), Part 3 (missing-evidence mechanism). The existing
  `earnings_calendar.csv`/`exdiv_closure_calendar.csv` quant-engine
  calendars (read-only reuse). `docs/FACTOR_REGISTRY.md` as the sole source
  of truth for `validated_factor_exposure` — never computed independently
  by this engine.
