# FRE Part 6 — Cross-document Reasoning

*Design only. Extends Steps 11-12 of the existing 14-step chain
(cross-reference / consistency) and `reasoning_engine.py`'s
`reason_about_company()` orchestrator (Phase E, unchanged). See
`docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Combine Annual Reports, Quarterly Reports, Corporate Actions, Dividend
Notices, Press Releases, Investor Presentations, Exchange Announcements,
Historical Filings, Macroeconomic Data, Market Prices, News, and (future)
Analyst Notes into **one company-level reasoning process** — without
building a new orchestrator, since the spec already names this exact
capability (§10: "Multiple-document synthesis... Steps 11-12 run ACROSS
documents rather than within one") and Phase E already built the
orchestrator (`reason_about_company()`) this document extends.

## Rationale — two structurally different evidence classes must merge

The owner's twelve source types split into two categories that this
platform already treats very differently, and cross-document reasoning's
real job is bridging them correctly, not treating them as interchangeable:

1. **Document-derived** (Annual/Quarterly Reports, Corporate Actions,
   Dividend Notices, Press Releases, Investor Presentations, Exchange
   Announcements, Historical Filings, News, future Analyst Notes) — each
   already has, or will have, a `DocumentProvider` (architecture doc §4.1)
   and flows through the standard Steps 1-14 pipeline.
2. **Series-derived** (Macroeconomic Data, Market Prices) — these are
   **not documents**; they are the quant Data Layer's existing structured
   tables (`macro_series`, the price panel). They were never meant to flow
   through document extraction at all.

Cross-document reasoning is therefore two related but distinct mechanisms:
**document corroboration/contradiction** (within category 1, reusing
Steps 11-12 exactly as specified) and a **quantitative reaction check**
(bridging category 1's conclusions against category 2's realized data) —
kept separate because conflating them would blur the hard architectural
boundary this platform has maintained since Phase A (`ngxrot.documents`
never writes to portfolio-facing modules; the quant Data Layer's tables may
be *read* by the documents layer, one direction only, the same precedent
already set by `company_intelligence.build_profile()` supplying
`factor_exposures` into `ReasoningContext`).

## Mechanism 1 — document corroboration/contradiction (category 1 only)

Exactly the existing Step 11/12 mechanism, generalized across source type
rather than restricted to same-type documents. A **synthesis unit** is
defined as a cluster of `investment_implications` rows sharing the same
`ticker` and overlapping `fact_type`/event within a rolling window, sourced
from **two or more distinct `documents.source_type` values** — e.g., an
Exchange Announcement of a dividend declaration, the subsequent Investor
Presentation restating it, and News coverage reporting the market's
reaction. This is not a new table: `corroborates_implication_id`/
`contradicts_implication_id` (already in the schema) is populated exactly
as today, just with the cross-source case as the primary intended use,
rather than an incidental one.

**Trust-tier arbitration on disagreement** reuses `evidence_ranking.py`
(built in the 2026-07-27 stabilization pass) directly — its
`assess_implication_conflict` function already recomputes a
trust-tier-aware preference between two disagreeing implications and
"discloses when [confidence-only and trust-tier assessments] disagree."
Cross-document reasoning's contribution is simply **ensuring this function
is always invoked when the two disagreeing sources have different
`source_type`s** (a filing vs. a news article disagreeing is a much more
common and higher-stakes case than two filings disagreeing) — a scheduling
guarantee, not new logic.

**Ordering discipline** (which source "wins" when trust tiers are equal,
before falling back to `evidence_ranking.py`'s arbitration): Exchange
Announcements and Corporate Filings first (primary, `source_confidence≈0.85`),
Investor Presentations and Dividend/Corporate-Action Notices next (same
primary feed), Press Releases third (company-authored but less formally
regulated than an exchange filing), News last and always per-outlet-tiered
(architecture doc §4.1's `news_outlets.reliability_tier`, owner-judged,
never AI-inferred), Analyst Notes not yet in scope (see below).

## Mechanism 2 — the quantitative reaction check (bridges category 1 and 2)

A **deterministic, non-LLM module** — not a reasoning call — that reads
realized price movement in a fixed post-filing window (reusing the
existing PIT price readers, read-only, same one-directional precedent as
`company_intelligence.build_profile()`) and populates
`investment_implications.market_reaction_assessment`
(`underreacting`/`overreacting`/`fairly_priced`/`unclear`, already a field
in the existing schema per §3 of the Reasoning Engine Specification, unused
until now) by comparing the reasoning engine's own
`direction`/`magnitude` verdict against the realized abnormal return over
the window.

```
reaction_check(implication_id) -> market_reaction_assessment:
    read investment_implications row (direction, magnitude, duration_bucket, event date)
    read realized price return over [event_date, event_date + window] via existing PIT price panel
    compare sign/magnitude bucket of realized return against the qualitative verdict
    -> deterministic classification, NOT a new LLM call
```

**Why this must be deterministic, not another reasoning call**: an LLM
asked "did the market over/underreact" would be reasoning about market
efficiency from its own priors, which is exactly the kind of unfalsifiable,
ungrounded claim the self-critique gate's `unevidenced_inference` question
exists to catch. A deterministic comparison against the *realized* price
series is evidence; an LLM's opinion about market efficiency is not. This
also directly reuses, rather than reinvents, the exact mechanism the News
Understanding Engine's `market_reaction_assessment` field already
presupposes (architecture doc §4.5) — this document specifies *how* that
field actually gets populated, which was previously unspecified.

**Macro data** plugs into the same reaction-check pattern one level up: a
Macroeconomic Reasoning Engine implication (e.g., "MPR hike compresses bank
margins") can be reaction-checked against the *sector's* realized return
window the same way, and — critically — against Part 1's ontology
`evidence_status` for that specific mechanism (was this edge
`ngx_confirmed` or `ngx_rejected`?). A macro implication invoking a
`ngx_rejected` edge should have its reaction-check result treated as
*expected to show no clean pattern*, not as a new surprising finding each
time — the ontology's own rejection history is itself part of the prior.

## Source-type-specific notes

| Source type | Cross-document role | Status |
|---|---|---|
| Annual/Quarterly Reports, Exchange Announcements, Historical Filings | Primary evidence backbone | Existing `XIssuerDocumentProvider`, real archive |
| Corporate Actions / Dividend Notices | Primary, plus Part 5's Company Memory feed | Existing, partially deterministic (Phase B) |
| Investor Presentations | Primary, same archive/feed, different `doc_type` — not yet separately classified | Present in archive, unclassified by type (architecture doc §4.1, disclosed gap) |
| Press Releases | Primary-ish, company-authored — needs its own `DocumentProvider` if not already covered by the xissuer feed | Not separately confirmed as covered — flag for Part 13's gap analysis |
| News | Secondary, per-outlet-tiered, requires the `news_outlets` registry (owner-judged, not yet built) | Not yet built (architecture doc §13, open decision #3) |
| Analyst Notes | Secondary, licensing-dependent | **Explicitly future** — architecture doc §13 open decision #4 (legal/licensing question, not engineering); this document does not resolve it, only reserves the `AnalystResearchProvider` extension point already named |
| Macroeconomic Data | Series-derived, quantitative reaction-check bridge | Existing `macro_series`, unchanged |
| Market Prices | Series-derived, quantitative reaction-check bridge | Existing PIT price panel, unchanged |

## Alternatives considered

1. **A single "mega-context" call that ingests all source types for a
   company at once and reasons over everything simultaneously.** Rejected
   — directly conflicts with the retrieval-first design already committed
   to in `docs/LIM_ARCHITECTURE.md` §5.3 (training and inference operate at
   retrieval-passage scale, not whole-corpus scale) and would make Step
   11/12's per-pair corroboration/contradiction reasoning untraceable (which
   specific two sources agreed or disagreed becomes unrecoverable from one
   giant undifferentiated context).
2. **Let an LLM directly assess market reaction from price data described
   in the prompt.** Rejected (see Mechanism 2's rationale above) —
   deterministic comparison is strictly more reliable and auditable for a
   question that has an actual right answer computable from data already on
   the platform.
3. **Give News and Analyst Notes the same trust tier as primary filings by
   default.** Rejected — directly contradicts the architecture doc's
   existing `single_source_news` stricter-review-bar rule and the
   `news_outlets.reliability_tier` owner-judgment requirement; treating an
   unverified news claim as equally authoritative to a regulatory filing
   would be a governance regression, not a synthesis improvement.

## Trade-offs

- The ordering discipline (exchange filings > presentations > press
  releases > news) is a reasonable default but not infallible — a press
  release can sometimes be more current than a delayed filing. Handled by
  `evidence_ranking.py`'s existing per-case arbitration rather than a rigid
  rule, at the cost of some non-determinism in edge cases (disclosed, not
  eliminated).
- The reaction-check window length is a real, unresolved parameter (too
  short misses delayed market digestion, e.g. thin-liquidity NGX names;
  too long picks up unrelated news) — deliberately left as an open decision
  for Part 12's roadmap rather than guessed here, matching this platform's
  "don't invent a threshold with no evidence behind it" discipline (the
  same restraint the Reasoning Engine Specification already applied to
  magnitude buckets, §6).

## Risks

- **Illiquid-name noise in the reaction check** — many NGX names trade
  thinly (the platform's own capacity-analysis findings, e.g. H-011's
  median leg ~₦694k, are direct evidence of this), meaning a "no price
  reaction" reading could reflect illiquidity, not market efficiency. The
  `market_reaction_assessment` classification must therefore be paired with
  a liquidity-context caveat (a `notes` field addition, or reuse of
  existing `single_source_day`-style diagnostic flags from the quant
  layer) — flagged, not yet designed in full.
- **Cross-source corroboration inflating false confidence** — three sources
  restating the *same* underlying company-authored claim (filing → investor
  presentation → company's own press release) is not independent
  corroboration, it is one source echoed three times. The corroboration
  mechanism must distinguish **independent** confirmation (a different,
  arm's-length source, e.g. real News coverage or a regulator filing) from
  **repetition** (the same originating party restating itself) —
  `evidence_ranking.py`'s trust-tier model should be extended (not by this
  document) to tag `source_type` provenance chains so repetition isn't
  silently double-counted as corroboration. Flagged as a concrete,
  named risk for Part 13/14, not solved here.

## Future extensions

- A `press_release` `DocumentProvider`/`doc_type` if Part 13's gap analysis
  confirms it isn't already covered by the existing xissuer feed.
- `AnalystResearchProvider`, once licensing is resolved (owner-gated,
  unchanged from the architecture doc).
- Liquidity-aware reaction-check confidence discounting (noted above).

## Dependencies

- `evidence_ranking.py`, `coverage_assessment.py` (existing, stabilization
  pass). Existing PIT price panel and `macro_series` (quant Data Layer,
  unchanged, read-only). Part 1's ontology (`evidence_status` for macro
  reaction-check framing). Part 5's Company Memory (corporate-action
  corroboration history). The `news_outlets` registry (not yet built,
  owner-gated, architecture doc §13).
