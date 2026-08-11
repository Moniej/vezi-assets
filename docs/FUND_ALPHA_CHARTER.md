# Fund Alpha — Charter

*Adopted 2026-07-15. Revised 2026-08-11: repositions Fund Alpha as an
Investment Operating System — the previous version defined the product as
the Alpha Engine and everything else as its supporting infrastructure; this
version inverts that. The intelligence infrastructure is the product; the
Alpha Engine, FRE, and any future decision engine are consumers of it. This
document sits above every other document in the project. When any plan
conflicts with it, this wins.*

## The objective

Build the **Investment OS**: a continuously updated, evidence-grounded,
provenance-tracked representation of the Nigerian equity investment universe
— documents, facts, events, factors, relationships, prices, corporate
actions — organized so that *any* investment decision process can be run on
top of it, without that process needing to be known in advance.

The OS itself never decides what to buy. It answers a narrower, harder
question honestly at any time, with provenance:

- What is actually known about this company or market, and from what source?
- How complete is what's known — and how much should that limit confidence?
- What contradicts what, and which source should win?
- What changed, and does it matter?

Consumers built on top of the OS — today the **Alpha Engine** (quant
hypothesis testing) and **FRE** (AI document/company intelligence), later
portfolio construction, risk, or other decision processes — are the ones
that answer buy/sell/enter/exit/size/risk questions. They are valuable
exactly insofar as the OS beneath them is complete, grounded, and honest.

## Hierarchy

```
Investment OS
├── Intelligence Infrastructure                    ← the product
│   (data acquisition, document store, extraction,
│    facts/events/factors/relationships, evidence/
│    grounding, self-critique, coverage & confidence)
├── Alpha Engine (quant hypothesis-testing consumer)
├── FRE (AI analyst / company-intelligence consumer)
└── [future consumers: portfolio construction, risk,
     other decision processes — additive, not a redesign]
```

**The standing priority hierarchy for all proposed work (revised
2026-08-11):**

1. Increases the OS's information completeness or grounding integrity
   (closes a coverage gap, adds a source, strengthens provenance).
2. Improves an existing consumer's decision quality (Alpha Engine or FRE)
   using infrastructure that already exists.
3. Enables multiple future hypothesis families or consumer capabilities.
4. Produces reusable datasets or evidence-grade corpora.
5. Accelerates testing of many ideas within an existing consumer.
6. Only then: optimizes a single hypothesis or a single company's coverage.

Work that only serves level 6 never outranks work at levels 1–5. Work that
expands infrastructure nobody has asked for gets built only when a consumer
or a measured coverage gap demands it — the OS grows by evidence of need,
same discipline the Alpha Engine already applies to itself.

## Success metrics — permanent, on every status report

**OS-level (new headline metrics):**
1. **Mean coverage score across the tracked universe** — the OS's own
   measured information completeness (the last 20-ticker validation pass
   reported 59.5%, but that figure is now known stale — see "Current
   honest state" below for the 2026-08-11 correction; `docs/
   INVESTMENT_OS_BASELINE_AUDIT.md` predates the fix).
2. **Grounding / citation integrity rate** — currently 100% on the last live
   validation run; must never regress to grow coverage faster.
3. **Coverage dimensions closed platform-wide** (financial statements,
   secondary sources, entity relationships, cross-ticker corroboration,
   temporal/point-in-time integrity) — tracked explicitly as ⛔/🟡/✅ per
   dimension, not folded into a single vague score.

**Consumer-level (existing metrics, now scoped per consumer):**
4. **Alpha Engine: independent validated alpha sources** (currently 1,
   capacity-constrained) and **hypotheses tested per month** (honest
   rejections count as throughput).
5. **FRE: coverage-justified confidence** — implications whose confidence
   ceiling is honestly capped by measured coverage, not asserted past it.
6. **Time from idea/gap to verdict**, for either consumer.

The objective is never NGX sector rotation, or any single market, strategy,
or reasoning technique. The competitive advantage is the OS itself —
an increasingly complete, provenance-tracked model of the investment
universe that any well-governed consumer can be pointed at.

## The living pipeline (gap-discovery is a platform function)

The queue is never a fixed backlog. Every completed piece of work — a
hypothesis verdict, a coverage assessment, a document ingestion run — is
mined for what it reveals is still missing, on both sides of the hierarchy:

- What OS-level gap does this consumer's result expose (missing data class,
  ungrounded claim, low-coverage ticker)?
- What patterns appeared during validation that deserve their own
  hypothesis or their own extraction taxonomy entry?
- Which datasets can be combined into entirely new research or intelligence
  programs?
- Which rejected hypotheses or capped-confidence implications suggest a
  different *mechanism*, or a different *missing input*, rather than a dead
  end?

Precedent: H-001's rejection generated H-002/H-003; FRE's Phase 19
self-assessment generated the current OS coverage-gap priority list
(financial statements, secondary sources, entity graph, temporal/PIT
integrity — see `docs/fre_runs/decision_intelligence_phase19_real_world_assessment.md`).
That pattern is mandatory on both sides of the hierarchy, not incidental to
either.

## Language rule: priority ≠ predicted success

No hypothesis is ever described as "likely to validate" before testing. No
coverage-gap closure is ever described as "will unlock alpha" before it's
built and measured. Priority language must cite **research/infrastructure
efficiency** only: acquisition cost, dataset reuse, coverage-dimensions
unlocked, and time-to-verdict. Expected success is what validation and
coverage measurement exist to determine; assuming it corrupts the process
on either side of the hierarchy.

## The queue, not the hypothesis (or the ticker)

**The headline success metrics are the OS's measured coverage/grounding
and the Alpha Engine's count of independent validated alpha sources — never
the fate of any single hypothesis or the completeness of any single
ticker.** A hypothesis or a low-coverage company is the next item in the
queue, nothing more. Rejections and coverage gaps are throughput, not
setbacks.

Operating rules:
- The hypothesis ledger must always hold a stocked queue of registered
  candidates so a rejection immediately hands work to the next hypothesis.
- The coverage backlog must always name its worst-covered dimension
  platform-wide (today: secondary sources at genuinely 0%, and real
  corporate-action data — the table exists but holds synthetic fixtures
  only; financial statements are built but narrow, not empty — see
  "Current honest state" below) so gap-closing work has an unambiguous
  next target.
- Data acquisitions are justified by how many *queued and future*
  candidates or coverage dimensions they feed, never by one hypothesis's or
  one ticker's needs.
- No hypothesis, and no single company's coverage push, may consume the
  roadmap: when in doubt, prefer the acquisition or tool that shortens
  time-to-verdict, or closes a coverage dimension, for *many* items at once.

## Long-term OS vision (build milestones, not upfront)

The OS grows into infrastructure comprehensive enough to support many
consumers simultaneously — quant factor families, AI company research,
portfolio construction, risk monitoring, execution optimization —
without redesigning itself for each one. Milestone-gated so the OS never
outruns its evidence, and no consumer outruns the OS beneath it:

- **Today:** two consumers (Alpha Engine, FRE), both explicitly
  self-limited by what they can honestly claim — 0 deployable alpha
  sources, coverage-capped confidence.
- **≥1 validated alpha source (already true, capacity-constrained):**
  single-model recommendations with provenance — built, minimal.
- **≥2 validated alpha sources:** signal-combination and capital-allocation
  layer — built THEN, not now.
- **OS coverage crosses meaningful thresholds** (financial statements live,
  secondary sources live, entity graph populated, temporal/PIT integrity
  platform-wide): each crossing is evaluated for what new consumer
  capability it unlocks, not treated as an end in itself.
- **Ongoing:** every consumer's output carries full-provenance explanation
  and an honest confidence ceiling from day one; these are OS schema, not
  consumer add-ons.

## What a consumer is (generalizing "what the engine is")

A consumer is anything built on top of the OS that turns intelligence into
a decision-relevant output — a ranked trade recommendation (Alpha Engine),
a grounded company research report (FRE), eventually a portfolio action or
a risk flag. Every consumer output carries: the claim, a confidence rating
honestly capped by OS-measured coverage, a plain-language rationale, and
provenance (hypothesis/experiment IDs for the Alpha Engine; fact/evidence/
document IDs for FRE) tracing it to immutable, inspectable records.

Scope is deliberately broad and open-ended on both sides: the Alpha Engine
admits equities, macro, event-driven, sentiment, ML/statistical, and
execution-optimization model classes (`HYPOTHESIS_FAMILY_MAP.md`); FRE
admits any reasoning question the OS's evidence can actually support, and
refuses (via self-critique and coverage-capped confidence) the ones it
can't. New consumer classes join by the same discipline — evidence of need,
never speculative scaffolding.

## The honesty constraints (non-negotiable, apply to every consumer)

1. **A consumer only speaks from validated or coverage-justified evidence.**
   Alpha Engine: a model becomes a recommendation source only when its
   hypothesis is `confirmed` in the ledger on evidence-grade data, having
   survived the full validation gauntlet (placebo, multiple-testing
   correction, walk-forward, OOS, capacity, costs). FRE: an implication's
   confidence may never exceed the mechanical coverage-based ceiling, and
   must clear the 8-question self-critique gate before any downstream
   consumer can read it. No exceptions for promising-looking results.
2. **"No position" / "insufficient information" is a first-class output.**
   When no validated edge covers a decision, or the OS's coverage is too
   thin to support a claim, the consumer says so and explains what's
   missing and what's in the pipeline. A consumer that always has an answer
   is broken.
3. **Every output is explainable and reproducible** down to experiment IDs
   (Alpha Engine) or fact/evidence/document IDs (FRE). If the provenance
   chain is missing, the output is invalid, full stop.
4. **Capacity, cost, and coverage are part of the output**, not footnotes:
   Alpha Engine sizing respects validated capacity analysis and nets out
   the modeled cost stack; FRE confidence respects the measured coverage
   ceiling. Neither gets rounded up.
5. Every consumer outputs *decision support with full provenance for the
   fund's own research and judgment* — never a substitute for that judgment
   or the fund's compliance obligations, and never packaged or represented
   as investment advice.

## Current honest state (2026-08-11, corrected same day)

- **OS coverage**: mean 59.5% was reported by the last 20-ticker validation
  pass (`docs/fre_runs/decision_intelligence_phase19_real_world_assessment.md`),
  but that figure relied on `CoverageAssessment.has_financial_statements`,
  which was found to be a **hardcoded `False`, never actually computed**
  from real data — a genuine bug, not a genuine gap (fixed same day; see
  `HANDOFF.md`). Real financial-statement extraction already exists
  platform-wide (FSI Phases 1-3: revenue/net_profit/assets/liabilities/
  equity/cash-flow/EBITDA facts, 267 already-computed, lineage-tracked
  ratio/trend/flag conclusions) for a subset of tickers — confirmed
  directly against `data/ngx.sqlite`, not inferred. **Recomputed mean
  across the same 20-ticker universe after the fix: 0.66 (was 0.595); 13/20
  tickers now correctly show `has_financial_statements=True` (was 0/20)**
  — NASCON, UCAP, and 11 others. Grounding/citation integrity: 100% on the
  last live run (unaffected by this fix). **Genuinely remaining,
  still-verified-empty**: secondary/news sources (0% platform-wide, no
  ingestion pipeline exists at all) and real corporate-action data (the
  `corporate_actions` table's schema supports 14 event types but its 31
  rows are synthetic test fixtures, not real data — confirmed against
  `docs/FACTOR_REGISTRY.md`'s H-017 entry).
- **Alpha Engine**: 18 hypotheses tested — 1 confirmed (H-011, Size,
  severely capacity-constrained: median tradeable leg ~₦694k), 15 rejected,
  1 abandoned untested (H-002, needs formal retirement), 1 in first-look
  testing (H-019, news-events, currently negative). **Zero deployable,
  capacity-feasible alpha sources.** Architecture frozen V1.
- **FRE**: Phases A–19 built and engineering-tested. Self-assessed as an
  "Analyst Research Assistant, not institutional infrastructure" — strong
  provenance and PIT discipline, structurally zero coverage of business
  description/segments/management/ownership for every ticker, valuation
  engine architecturally ready but deliberately gated pending owner
  sign-off.
- Therefore the OS's current correct output, end to end, is: *here is what
  is known, here is how complete that knowledge is, here is what would
  need to be true for a consumer to act — no consumer should currently
  claim more than that.*
- The bottleneck is **OS coverage breadth** — genuinely: secondary/news
  sources (0%), real corporate-action data (schema ready, table holds
  synthetic fixtures only), entity relationships (thin, 22 rows), temporal/
  PIT integrity beyond financials — not reasoning sophistication on either
  consumer. Financial statements are BUILT but NARROW (real data for a
  subset of the universe, not all 20+ tracked tickers) — expanding
  coverage, not building from zero. Per the priority hierarchy above,
  coverage-closing work now outranks new consumer features unless a
  consumer surfaces a specific, evidenced gap.

## Priority test applied to the current queue

| Work item | OS/consumer justification | Verdict |
|---|---|---|
| Expand financial-statement extraction to more tickers/periods (FSI Phases 1-3 already built and working — this is coverage expansion, not new infrastructure) | Real data exists for a subset of tickers only; unlocks FRE valuation activation and Alpha Engine Value/Dividend-Yield families as coverage grows | **top priority** |
| Load real corporate-action data into the existing `corporate_actions` table (schema already supports 14 event types; table currently holds synthetic test fixtures only, per `docs/FACTOR_REGISTRY.md`'s H-017 entry) | Real source data already exists (`data/reference/exdiv_closure_calendar.csv`); no schema work needed, only ingestion | **top priority** |
| Secondary-source (news/analyst) ingestion with strict provenance | Closes a genuinely empty (0%) platform-wide coverage gap; raises coverage score for every ticker at once | **top priority** |
| Entity relationship graph (competitor/supplier/customer/subsidiary) | Unlocks cross-ticker propagation for FRE and pooled/cohort hypothesis design for Alpha Engine | high — after the two data gaps above |
| Temporal / point-in-time integrity extension to documents & facts | Non-negotiable precondition for any future historical evaluation of FRE outputs, same discipline the Alpha Engine already enforces on prices | high, structural |
| Daily ephemeral price capture | Feeds OS coverage and Alpha Engine model families; time-gated, must run daily | keep |
| FRE-7 valuation-engine activation | Architecture ready; blocked on owner sign-off, not on more building | awaiting decision, not queued work |
| New consumer scaffolding (portfolio construction, risk, etc.) | No consumer-level need demonstrated yet; Alpha Engine still has only 1 validated source | **deprioritized — build nothing here until a specific gap or ≥2 validated sources demands it** |
