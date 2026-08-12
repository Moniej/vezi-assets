# NGX Rotation — Investment Operating System

## Complete Project Context & AI Handoff Specification

*Current state: August 2026. Read this before proposing new work in a fresh
context. It complements, not replaces, `docs/FUND_ALPHA_CHARTER.md` (the
governing priority/rules document) and `HANDOFF.md` (the chronological
session log) — this document is the comprehensive context primer.*

## 0. Verified layer status (2026-08-11) — read before trusting any BUILT/
NOT BUILT claim below or elsewhere

A later handoff draft claimed the Research Query Layer was unverified and
the Research Workspace was not built. Both claims were checked directly
against the code before being written down here, per this document's own
§66 rule ("never infer implementation from documentation alone"). The
corrected, code-verified status:

| Layer | Status | Evidence |
|---|---|---|
| Research Query Layer (price/market-data side) | **BUILT** | `src/ngxrot/research_query.py` — 6 query types (prices, cross-section, universe history, compare, metadata, entity lookup), look-ahead rejection, provenance, CLI (`scripts/ngxrot_research.py`), Python API, 29/29 tests (`scripts/test_research_query.py`), benchmarked performance table (`docs/research_query_layer.md`) |
| Research Workspace (price/market-data side) | **BUILT** | `src/ngxrot/research_workspace.py` (819 lines) — question -> scope -> queries -> evidence -> analysis -> findings -> conclusion -> reproducible snapshot -> export, `research_projects`/`research_findings`/`research_hypotheses` tables, dated 2026-08-10, 109/109 regression baseline before it was built (`docs/fre_runs/research_workspace_report.md`) |
| Document/Evidence query or workspace layer (FRE side) | **BUILT 2026-08-11** — was correctly identified as the real gap, now closed | `research_query.py` gained 4 new query types (`facts`, `events`, `entity_relationships`, `document_context`) wrapping the existing `documents/retrieval.py`/`context.py` primitives unmodified; `research_workspace.add_document_evidence()` records them as evidence (reusing `evidence_type='source_document'`, no schema change). CLI: `scripts/ngxrot_research.py facts\|events\|relationships\|context`. 12 new query-layer tests + 6 new workspace tests, all passing against the real production DB. Full detail: `docs/research_query_layer.md` §18a, `docs/research_workspace.md`. |
| Monitoring / alerting | **PARTIAL** | No scheduler, file-watcher, or trigger infrastructure exists anywhere on the platform (confirmed absent). But a real deterministic alert pipeline function already exists: `src/ngxrot/fre/continuous_intelligence.py` (Phase 18) — change detection -> materiality assessment -> alert/review-queue entry, structurally refusing to emit an alert below LOW materiality. The logic exists; only the thing that would call it on a schedule doesn't. |
| Financial-statement extraction | **BUILT 2026-08-11 (corrected)** — §21 below was wrong | `CoverageAssessment.has_financial_statements` was a hardcoded `False`, never actually computed — a bug, not a real gap. Real state confirmed directly against `data/ngx.sqlite`: FSI Phases 1-3 built a real, tested pipeline (`src/ngxrot/fre/financial_ratios.py`/`financial_health_flags.py`/`pit_financial_memory.py`), ~260 real extracted financial facts (revenue/net_profit/assets/liabilities/equity/cash-flow/EBITDA/EBIT/COGS/gross-profit) across 22 tickers, 267 already-computed lineage-tracked ratio/trend/flag conclusions. Fixed same day (see `HANDOFF.md`); recomputed mean coverage across the 20-ticker validation universe: 0.66 (was 0.595), 13/20 tickers now correctly show `has_financial_statements=True` (was 0/20). Genuine remaining gap is narrow coverage (22 of 300+ tickers platform-wide), not absence. Valuation (`valuation_engine.py`) remains correctly gated pending owner sign-off, unaffected. |
| Corporate-action data | **PARTIAL — dividends BUILT 2026-08-11, bonus/rights deferred** | Schema (`corporate_actions` table) supports 14 event types and is comprehensive. Was 31 synthetic test fixtures only (`docs/FACTOR_REGISTRY.md`'s H-017 entry). `scripts/load_real_corporate_actions_dividends.py` loaded 155 real, evidence-linked dividend rows from `extracted_facts` (not the CSV — that only has closure dates, no amounts). `markdown_date` deliberately left NULL on every row: `corporate_actions` is a live input to `engine_full.py`'s total-return overlay, which requires `markdown_date` to activate — left NULL per an explicit owner decision so real data is queryable without changing any Alpha Engine behavior. Bonus/rights/reconstruction facts NOT loaded (price-adjustment-factor semantics need dedicated parsing, some are proposed-only/cancelled) — a distinct, deferred item. |
| Entity mentions (`entity_mentions` table) | **BUILT/fixed 2026-08-11** | Existed in the schema since Phase C, never written to. `documents/entities.py`'s `resolve_or_create_entity` now records a mention on every call (idempotent); backfilled 74 historical mentions from existing entities/relationships (`scripts/backfill_entity_mentions.py`). Real, previously-undiscovered consequence: `documents/retrieval.py`'s `entity_name`-filtered `retrieve_documents` always silently returned 0 rows for every query until this fix — an existing, real, but completely untested code path. Pure mechanical bookkeeping, no LLM call, no fabrication risk. |
| Entity relationship semantics (`competitor_of`/`supplier_to` vs. the current honest `affects_order_N`) | **Deliberately NOT built** | TD11 (unchanged): inventing a semantic label the extraction prompt was never asked to produce would itself be fabrication. A real fix needs a prompt change — new LLM calls, cost, and quality validation — flagged as a decision point, not attempted. |
| Alpha | **Correctly untouched**, as it should be | 18 hypotheses tested (1 confirmed, capacity-constrained), Alpha Engine architecture frozen V1, unaffected by any OS/FRE work |

**Update 2026-08-11**: the document/evidence query and workspace gap
identified above has been closed (see the BUILT row above) — both the
price/market side and the document/FRE side now have query and workspace
coverage, via the same `QuerySpec`/`QueryResult`/`research_evidence`
contracts, not two parallel systems. Any future work item phrased as
"build the research query/workspace layer" is describing something that
already exists on both sides; the correctly-scoped next items are the
data-foundation gaps (financial statements, secondary sources, entity
graph depth) per the charter's priority table, not more query/workspace
plumbing.

## 1. Core framing — this is critical

The project is called NGX Rotation, but the project should now be
understood and described as an **Investment Operating System (Investment
OS)**.

It is **NOT** primarily an alpha model. It is **NOT** a trading strategy.
It is **NOT** a quant strategy. It is **NOT** simply a financial research
assistant.

It is an intelligence and infrastructure layer intended to organize,
understand, validate, monitor, and eventually operationalize investment
information across the Nigerian equity market, initially focused on the
NGX.

The fundamental idea: build an AI-native investment intelligence
infrastructure that continuously converts fragmented market/company
information into structured, evidence-backed, temporally aware investment
intelligence that can eventually feed human investment decisions, portfolio
processes, and multiple decision engines.

An alpha, strategy, screening model, valuation model, or portfolio strategy
can eventually sit **on top of** this infrastructure. The OS itself does
not need to discover a single alpha. The project owner is building the
infrastructure underneath investment decision-making, not trying to become
a quant.

## 2. The high-level vision

```text
                    INVESTMENT INFORMATION
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
      NGX filings       Market data        Secondary data
      Company docs      Prices/volume      News/industry
      Regulatory docs   Corporate actions   Research
          |                  |                  |
          +------------------+------------------+
                             v
                    DATA ACQUISITION
                             v
                    NORMALIZATION
                             v
                    PERSISTENT DATA LAYER
                             v
                +------------------------+
                | INVESTMENT KNOWLEDGE   |
                | MODEL                  |
                +------------------------+
                | Facts, Events,         |
                | Financials, Factors,   |
                | Entities, Relationships|
                | Market state,          |
                | Narratives             |
                +------------+-----------+
                             v
                  EVIDENCE / PROVENANCE
                             v
                    GROUNDING VALIDATION
                             v
                     SELF-CRITIQUE
                             v
                 CONFLICT / TRUST ANALYSIS
                             v
                   COVERAGE ASSESSMENT
                             v
                    CONFIDENCE CONTROL
                             v
                 INVESTMENT INTELLIGENCE
                             |
              +--------------+--------------+
              v              v              v
         Screening       Research       Monitoring
              |              |              |
              +--------------+--------------+
                             v
                   DECISION ENGINES
                             v
                 PORTFOLIO / FUND OPS
```

The current implementation is concentrated in the middle of this
architecture (persistence through confidence control). The edges —
comprehensive market/financial/secondary data on the input side, decision
engines and portfolio ops on the output side — are the acknowledged gaps
(§21 onward).

## 3. What has actually been built (verified against the repository)

This is a functioning backend/prototype, not merely a conceptual idea.
Verified present in the repository: `src/ngxrot/db.py`, `src/ngxrot/phase4.py`,
`src/ngxrot/documents/extract.py`, `schema/schema.sql`,
`scripts/validate_stabilization_e2e.py`, plus the full FRE module tree
(`src/ngxrot/fre/`) and Research OS tree (`src/ngxrot/research_*.py`).
The project has persistent state, document IDs, extraction, evidence,
implications, validation, and orchestration.

## 4. Current architectural layers

**Layer 1 — Acquisition.** Receives investment-related documents/data
(company filings, NGX disclosures, corporate documents). Has a
document-processing pipeline and document identifiers.

**Layer 2 — Persistence.** Persists information rather than treating every
LLM call as an isolated session (`src/ngxrot/db.py`, `schema/schema.sql`).
Tracks documents, document IDs, facts, evidence, implications, ticker
associations, processing state, validation-related information. An
Investment OS must maintain state over time — this is foundational.

**Layer 3 — Understanding.** Extracts structured investment-relevant
information: facts, events, factor exposures, implications, causal chains.
Both deterministic and LLM-based extraction components exist.

**Layer 4 — Evidence / Provenance.** Establishes Fact → Evidence → Source
document, instead of unattributed "AI says X." One of the strongest
aspects of the current implementation.

**Layer 5 — Reasoning / Validation.** Causal reasoning, self-critique,
conflict detection, evidence ranking, confidence, grounding, citation
integrity — designed to prevent unsupported AI reasoning from automatically
becoming investment intelligence.

**Layer 6 — Reliability / Coverage.** Evaluates not only "is this fact
grounded?" but "do we actually have enough information to support a strong
conclusion?" (`CoverageAssessment`, confidence ceilings, evidence ranking,
source tiers, conflict detection). **Evidence can be perfectly grounded
while the overall information environment is still incomplete** — this
distinction is fundamental to everything below.

## 5. Document processing (verified, `reports/stabilization_validation_raw.json`)

Latest pilot: 28 documents processed, 28 skipped on rerun, 0 failed, 0
quota-exceeded, 0 interrupted. Status breakdown: 24 completed, 4
`blocked_by_self_critique`. Documents have a lifecycle (newly processed /
already processed / failed / blocked / unretrieved), not blind reprocessing
— important for reproducibility and production architecture.

## 6. Deterministic extraction

Pilot: 447 deterministic facts, 48 LLM facts.

```text
Raw document -> Deterministic extraction -> Structured facts
             -> LLM semantic extraction -> Additional semantic facts
```

Pilot evaluation: precision 0.2069, recall 1.0, overlap with ground truth
58, agree 12, LLM found extra 33, recall misses 0. **Do not interpret this
as "the system has 20.69% accuracy."** 100% recall against the defined
ground-truth set is real; low precision reflects comparing two
fundamentally different extraction approaches and flags that extraction
evaluation needs deeper decomposition — separately measuring fact
extraction, event extraction, entity extraction, factor extraction,
evidence selection, causal reasoning, and implication quality, rather than
one aggregate number.

## 7. LLM extraction / orchestration

Live orchestrator: `provider: gemini:gemini-3.6-flash`,
`model_id: gemini-3.6-flash`. Processes ticker-specific documents and
generates structured investment intelligence (example: the live NASCON
run), reporting processing time, newly processed document IDs, fact count,
retrieval warnings, coverage, confidence ceiling, and breaches.

## 8. Grounding (one of the strongest validated capabilities)

Latest real-data verification: `n_checked: 48, n_agree: 48, n_disagree: 0,
n_missing_source_text: 0, citation_accuracy: 1.0` — **100% agreement, 0
disagreements, 0 missing source text.** Pilot grounding failures: 2 (4.17%
failure rate) — but the architecture correctly rejected the unsupported
evidence rather than keeping it (`quoted_evidence not grounded, dropped`
in the live run log). Unsupported LLM-generated evidence must not survive
merely because the model generated it confidently — this behavior must be
preserved.

## 9. Citation integrity

Latest validation: `n_facts: 48, n_missing_evidence_row: 0,
n_doc_id_mismatch: 0, citation_integrity_rate: 1.0` — 48 facts, 0 missing
evidence rows, 0 document-ID mismatches, 100% citation integrity. Strong
Fact → Evidence → Document traceability is a significant OS component.

## 10. Evidence ranking

Tiers: `primary_filing`, `secondary_reputable`, `ai_derived_or_ungrounded`.
Aggregate: primary_filing 207, secondary_reputable 72,
ai_derived_or_ungrounded 4. Principle: primary authoritative evidence >
reputable secondary evidence > AI-derived/unsupported information. Needs to
grow into a fuller source-quality model (authority, directness, recency,
specificity, independence, historical reliability) — see §35.

## 11. Conflict detection

Aggregate: 3 conflicts detected, 0 trust/confidence disagreements (NASCON:
2 conflicts, 0 disagreements). Compares confidence-based preference against
trust-tier-based preference; the system should determine which evidence has
stronger support, not simply prefer the newest statement.

## 12. Self-critique

Pilot: 48 implications, 4 blocked (8.33% rejection rate). Critique results:
concern 89, pass 87, fail 8.

```text
Extract facts -> Generate implication -> Critique implication -> PASS / BLOCK
```

Not every generated investment interpretation is accepted automatically.

## 13. Causal chains

Pilot: `facts_with_complete_impact_categories: 48,
facts_missing_causal_chain: 0`.

```text
Event -> Immediate effect -> Economic mechanism -> Company impact -> Investment implication
```

Significantly different from document summarization — the objective is
understanding *why* an event could matter economically.

## 14. Event history

`has_event_history` is tracked in `CoverageAssessment` — the beginning of
company state/history rather than treating every document independently.
Intended evolution: company → historical events → current state → state
changes → emerging patterns, i.e. a temporal investment knowledge system.

## 15. Factor exposures

`has_factor_exposures` tracked. Intended to connect company events to
broader economic/investment variables (FX, interest rates, commodities,
inflation, energy costs, demand, regulation, input costs, consumer
spending, credit conditions, industry cycles). This layer needs significant
expansion.

## 16. Coverage assessment

`CoverageAssessment` is one of the most important concepts in the
architecture — it evaluates whether enough information exists to support
strong conclusions. Dimensions: `has_facts`, `has_grounded_evidence`,
`has_multiple_source_documents`, `has_multiple_fact_types`,
`has_entity_relationships`, `has_event_history`, `has_factor_exposures`,
`has_cross_ticker_corroboration`, `has_financial_statements`,
`has_secondary_sources`. Latest aggregate: 20 tickers assessed, mean
coverage score 0.595 (**59.5% average mechanical coverage**).

## 17. Confidence ceilings

Confidence is intentionally limited by measured information completeness.
Example: NASCON coverage 0.60 → confidence ceiling 0.225; some tickers at
coverage 0.70 → ceiling 0.30. **A perfectly grounded conclusion should not
automatically receive high confidence if the information environment
itself is incomplete.** The system distinguishes evidence reliability from
information completeness — this is a very important, non-negotiable
Investment OS principle.

## 18. Current 20-ticker coverage

Assessed: BUAFOODS, CAVERTON, CILEASING, CUTIX, GTCO, LASACO, LIVINGTRUST,
MCNICHOLS, MOFIREIF, NASCON, NCR, NGXGROUP, PRESTIGE, REDSTAREX,
STANBICETF30, TOTAL, UCAP, UNILEVER, UNIVINSURE, VERITASKAP. Coverage
ranges approximately 0.5–0.7 depending on ticker and available information;
some have entity relationships or cross-ticker corroboration, others don't.

## 19. Current information model

```text
Company
 |- Documents
 |- Facts
 |- Evidence
 |- Events
 |- Factors
 |- Implications
 |- Causal chains
 |- Conflicts
 |- Confidence
 |- Coverage
 `- Some cross-company relationships
```

This is the beginning of an investment knowledge graph.

## 20. The most important current limitation

The largest weakness is **not** primarily hallucination. It is
**information coverage**. The system can have 100% grounded evidence and
100% citation integrity and still not know enough (current average
coverage: 59.5%). The OS itself identifies the missing information — that
is desirable behavior: "what I have is traceable, but I don't yet have a
sufficiently complete representation of the investment universe." That is
the problem the next phase needs to solve.

## 21. CORRECTED 2026-08-11 — financial statements: narrow, not missing

**This section was wrong when written.** `has_financial_statements = false`
was a hardcoded default in `coverage_assessment.py`, never actually
computed from `extracted_facts` — a code bug, not a real absence. Checked
directly against `data/ngx.sqlite`: real financial-statement extraction
already exists (FSI Phases 1-3, `src/ngxrot/fre/financial_ratios.py` and
siblings) — revenue, net_profit, assets, liabilities, equity, cfo/cfi/cff,
capex, fcf, ebitda, ebit, cogs, gross_profit are all real, extracted
fact_types with real rows (~260 facts across 22 tickers), plus 267
already-computed, lineage-tracked ratio/trend/flag conclusions in
`financial_reasoning_conclusions`, and a PIT-safe historical-memory layer
(`pit_financial_memory.py`, gates on source-document filing date). Fixed
same day — `has_financial_statements` is now correctly computed per
ticker (see `HANDOFF.md` for the fix and `scripts/
test_coverage_assessment_financial_statements.py` for the regression
test).

**The real, remaining gap**: coverage is narrow — 22 of 300+ tracked
tickers, 1-5 facts per metric per ticker, income statement/balance sheet/
cash flow but no longitudinal multi-year history yet, and valuation
(`valuation_engine.py`'s `compute()`) remains correctly gated pending
owner sign-off. Priority is now *extending* the existing FSI Phase 1-3
pipeline to more tickers/periods, not building financial extraction from
scratch — a materially smaller, cheaper task than this section originally
described.

## 22. Missing — secondary intelligence

`has_secondary_sources = false` for many tickers — no news/analyst
ingestion exists platform-wide yet. Should eventually ingest financial
news, industry news, reputable market commentary, management commentary,
regulatory developments, industry developments, legally accessible
research. The point is not to trust secondary sources more — it's primary
+ secondary + source ranking + independent corroboration determining
evidence strength.

## 23. Missing — entity relationship graph

Not yet sufficiently comprehensive or persisted. Intended: company →
competitors/suppliers/customers/subsidiaries/parents/strategic
partners/sector peers/industry/related securities, enabling propagation
(Company A → competitor B → supplier C).

## 24. Missing — cross-ticker intelligence

`has_cross_ticker_corroboration` exists for some tickers but isn't
comprehensive. Future system should understand second-order effects (e.g.
Company A's capacity expansion rippling to supplier B, competitor C,
distributor D, industry E, commodity F). This is one of the major ways the
OS becomes more valuable than a document research assistant.

## 25. Missing — market data

Current implementation is heavily document/intelligence oriented. Needs a
canonical, normalized market-data layer independent of raw source
documents: OHLCV, price, volume, market cap, shares outstanding, free
float, corporate actions, dividends, splits, rights issues,
listings/delistings, index membership, sector classification, trading
activity.

## 26. Missing — corporate-action normalization

Dividends, rights issues, bonus issues, splits, new listings, share
cancellations, employee share schemes, acquisitions, disposals, mergers,
restructurings, changes in shares outstanding — all need to become
structured, machine-readable events, because they materially change market
cap, EPS, ownership, dilution, and valuation ratios. The OS needs to
understand these mechanically, not incidentally.

## 27. Missing — valuation

No complete valuation engine yet. Eventually: P/E, forward P/E, P/B,
EV/EBITDA, EV/Sales, dividend yield, FCF yield, PEG, ROE, ROIC, and
eventually DCF, DDM, residual income, sum-of-the-parts, earnings power.
**Valuation is a consumer of the OS's clean intelligence/data, not the
fundamental identity of the OS.**

## 28. Missing — portfolio operating layer

Per position: security, size, entry, current price, thesis, supporting
evidence, catalysts, risks, invalidation conditions, expected horizon,
factor exposures, portfolio contribution. Flow: company intelligence →
portfolio relevance → risk/exposure → monitoring.

## 29. Missing — decision engine

OS intelligence → screening → research → ranking → scenario analysis →
decision. The OS does not need one universal "AI investment score" — better
to provide structured intelligence multiple decision engines can consume.

## 30. Missing — temporal intelligence

Needs to know: when did the event happen, when was it published, when was
it ingested, when did it become known, what period does it affect. Every
important data point should eventually carry `event_time`,
`publication_time`, `ingestion_time`, `effective_period`, `source` — this
prevents historical contamination.

## 31. Missing — point-in-time data

Needs point-in-time snapshots so a 2026 financial statement can never
influence a simulated 2024 investment decision. Mandatory for serious
historical evaluation — same discipline the price/PIT layer already
enforces (`ngxrot.db`'s `*_asof` readers), extended to documents/facts.

## 32. Missing — full data lineage

Current: Fact → Evidence → Document. Future: raw source → extracted data →
normalized data → derived metric → fact → event → factor → implication →
decision → portfolio action — a full end-to-end audit trail.

## 33. Missing — data quality framework

Grounding ≠ data quality. Needs automated checks: freshness, completeness,
duplicates, outliers, schema violations, missing periods, ticker
mismatches, currency mismatches, unit mismatches, corporate-action
inconsistencies, source conflicts. Every dataset should carry a quality
status.

## 34. Missing — source freshness

A source can be authoritative but old. Needs `source_age`, `last_updated`,
`publication_date`, `ingestion_date` — freshness should influence
relevance.

## 35. Missing — source independence

NGX filing → news article A → news article B → aggregator C are not four
independent confirmations. The OS needs to detect source relationships and
avoid fake corroboration.

## 36. Missing — narrative tracking

Track investment narratives (e.g. "margins are structurally improving")
with supporting evidence, contradicting evidence, and current state
(strengthening/weakening/unresolved) that evolves as new evidence arrives.

## 37. Missing — thesis management

Company → investment thesis → assumptions → catalysts → risks →
invalidation conditions → monitoring signals, so the OS can continuously
answer: is the thesis still intact?

## 38. Missing — alerting

Proactively notify on: new filing, earnings surprise, margin
deterioration, management change, major corporate action, regulatory
event, factor shock, peer event, thesis invalidation. Desired behavior:
"something changed that matters," not "ask the AI to research again."

## 39. Missing — product/UI

The backend is considerably further developed than the user-facing product
layer. Eventually a dashboard: market/sector intelligence, per-company
coverage/intelligence/valuation/risk/recent events, cross-company
intelligence feed, portfolio positions/thesis/risk/catalysts/alerts — every
conclusion traceable back to evidence.

## 40. Missing — API

Structured intelligence should eventually be exposed via endpoints such as
`/company/{ticker}`, `/company/{ticker}/events|facts|evidence|financials|
factors|relationships`, `/sector/{sector}`, `/market/events|factors`,
`/signals` — so future applications and decision engines can consume the
OS.

## 41. Missing — production orchestration

Current orchestrator is functional but needs production-grade scheduling:
scheduler → new-document detector → retrieval → processing queue →
extraction → validation → database → quality checks → intelligence update →
alerts, with retries, idempotency, rate limiting, failure recovery,
observability, logging, job status, dead-letter handling.

## 42. Current performance

One live NASCON run: 5 documents in 209.57 seconds. Pilot: average latency
17.932s, total input tokens 171,451, total output tokens 92,708, total LLM
calls 65, cache hits 4, cache hit rate 6.15%. Reported cost: $0 — **this is
explicitly a placeholder/free-tier assumption, not a real production cost
estimate.** Before production budgeting, calculate cost/document,
cost/company/month, cost/universe/month, tokens/document, LLM
calls/document, cache savings, retrieval cost, storage cost.

## 43. Current retrieval behavior

The system correctly exposes unretrieved documents (e.g. "50 additional
unretrieved candidate documents exist beyond max_new_documents=5 — not
fetched this call, not silently ignored"), distinguishing "not retrieved"
from "does not exist." Preserve this.

## 44. Current validation status

Citation accuracy 100%, citation integrity 100%, grounding disagreements 0,
missing source text 0, document-ID mismatches 0, trust/confidence
conflicts 0. Mean coverage 59.5%; 3 conflicts detected across the broader
real-ticker assessment. **The evidence/provenance mechanisms are strong;
investment-information coverage remains incomplete.**

## 45. Current ticker-level example — NASCON

Coverage 0.60, confidence ceiling 0.225. Present: facts, grounded evidence,
multiple source documents, multiple fact types, event history, factor
exposures. Missing: entity relationships, cross-ticker corroboration,
financial statements, secondary sources. This pattern repeats across many
tickers; some reach 0.7 coverage via extra relationship/corroboration data,
others sit at 0.5 for lacking multiple fact types or other dimensions.

## 46. What the 59.5% coverage score means

**Do not** describe this as "the OS is 59.5% complete" or as prediction
accuracy. It means: the current `CoverageAssessment` reports an average of
59.5% of its defined mechanical coverage dimensions as satisfied across
assessed tickers. The system is deliberately penalizing itself for missing
important datasets. Objective: 59.5% → 70% → 80% → 90%+, while maintaining
evidence integrity — never trade one for the other.

## 47. Current system strengths

Document persistence, document processing, deterministic extraction, LLM
extraction, evidence grounding, citation integrity, evidence ranking,
conflict detection, self-critique, causal chains, event history, factor
exposure, coverage assessment, confidence ceilings, multi-ticker operation,
automated E2E validation. Strongest demonstrated technical properties:
provenance, grounding (rejects unsupported evidence), self-awareness of
incomplete coverage, confidence control (never lets low coverage produce
high confidence), and persistent state across runs.

## 48. Current system weaknesses

Financial data, market data, corporate actions, entity graph, secondary
intelligence, comprehensive cross-ticker intelligence, temporal/PIT
architecture, valuation, portfolio management, decision engines, historical
investment evaluation, user interface, API, production orchestration, cost
modeling, human expert evaluation. **Do not try to solve all of these
simultaneously.**

## 49. Priority order (recommended build order)

1. Financial data — canonical financial-statement dataset.
2. Market data — clean historical/current price and volume infrastructure.
3. Corporate actions — normalize dividends, rights, splits, share changes.
4. Entity graph — company/peer/competitor/supplier/customer relationships.
5. Secondary intelligence — reputable news/industry information.
6. Temporal/PIT architecture — make information timestamp-aware.
7. Unified investment knowledge model — bring everything together.
8. Data quality framework — automate completeness/freshness/consistency
   checks.
9. Product/UI — build the Investment OS interface.
10. Decision engines — screening, ranking, scenario, portfolio workflows.

(This ordering matches, and is the source for, the priority table in
`docs/FUND_ALPHA_CHARTER.md`'s "Priority test applied to the current
queue.")

## 50. What should NOT be prioritized yet

More elaborate LLM prompts, another "smart" AI agent, a magical investment
score, a trading bot, an alpha model, complex quant strategies, fancy
visualizations. **The bottleneck is currently information infrastructure,
not model intelligence.** More intelligence applied to incomplete data does
not solve the fundamental problem.

## 51. The potential moat

Not Gemini, GPT, or prompt engineering — those are replaceable. The moat is
NGX-specific historical data + normalized financial data + market data +
corporate-action history + company knowledge graph + event history + factor
relationships + evidence provenance + temporal state + investment reasoning
+ evaluation history. Over time this becomes proprietary investment
intelligence infrastructure.

## 52. What the OS should eventually answer

Company intelligence ("what materially changed at NASCON?"), evidence
("show exactly where that conclusion came from"), historical state ("what
did we know about NASCON on June 1, 2025?"), financials (margin/cash
flow/leverage/earnings trends over five years), factors (FX/energy/
commodity/demand exposure), relationships (which companies are likely
affected), market (has this already been priced in?), narrative
(strengthening or weakening?), portfolio (which holdings are exposed?),
monitoring (what changed today that matters?), decision support (what
evidence supports or contradicts the current thesis?). These are
Investment OS questions.

## 53. The OS vs. an alpha model

An alpha model says "BUY NASCON." The Investment OS instead provides:
financial state, market state, recent events, historical events, factors,
peers, relationships, evidence, conflicting evidence, narratives, valuation
inputs, risk, coverage, confidence — then an alpha/strategy/portfolio
engine decides what to do with that information. **The OS is upstream of
investment strategies.**

## 54. The OS vs. a research assistant

A research assistant answers "tell me about NASCON" — reactive. The
Investment OS continuously maintains NASCON's state + historical state +
new information + evidence + relationships + financials + market state +
factors + narratives + thesis + portfolio relevance — persistent, stateful,
continuously updated, evidence-backed, operational.

## 55. The OS vs. a quant system

A quant system primarily operates on structured market data to generate
signals/decisions. The Investment OS is broader: structured market data +
unstructured documents + financial statements + corporate actions + news +
entities + events + factors + evidence + reasoning + temporal state. It can
eventually feed quantitative systems but is not itself defined by being
quantitative.

## 56. Core design principle #1

**The OS should never confuse confidence in an observation with
completeness of the information environment.** A 100%-grounded fact with
financial statements, market data, peer relationships, and secondary
sources all missing does not earn a high investment-conclusion confidence.
`CoverageAssessment` and the confidence ceiling exist to enforce exactly
this.

## 57. Core design principle #2

Every meaningful intelligence object should be traceable: decision →
implication → causal chain → fact → evidence → source → original
document/data. The deeper the audit trail, the more trustworthy the OS.

## 58. Core design principle #3

The OS must be temporal. It should eventually answer "what did the system
know at that time?" rather than "what do we know now about what happened
then?" — critical for investment evaluation.

## 59. Core design principle #4

The OS should distinguish source authority, source freshness, source
independence, source relevance, and source completeness as separate
dimensions — a source can be authoritative but old, recent but secondary,
relevant but not independent.

## 60. Core design principle #5

The system should fail conservatively: unsupported evidence → DROP;
insufficient coverage → LOWER CONFIDENCE; conflicting sources → SURFACE
CONFLICT; unretrieved documents → SHOW RETRIEVAL GAP. Never silently
manufacture certainty.

## 61. Current project maturity

The project should be described as: **a functioning prototype of the
intelligence, evidence, reasoning, and reliability layers of an AI-native
Investment Operating System for the NGX.** It is not yet a complete
production Investment OS — meaningful backend capabilities are
demonstrated, but major data and operational layers remain to be built.
Maintain this distinction when presenting the project to investors,
developers, advisors, or other AI systems.

## 62. What a future Investment OS could look like

```text
                         INVESTMENT OS
                               |
       +-----------------------+------------------------+
       |                       |                        |
       v                       v                        v
  DATA ENGINE            KNOWLEDGE ENGINE         MARKET ENGINE
       |                  Facts/Events                   |
       |                  Entities                  Prices/Volume
       |                  Relationships             Liquidity
       |                  Factors                   Corporate actions
       +-----------------------+------------------------+
                               v
                       EVIDENCE ENGINE
                    (Grounding / Provenance)
                               v
                     REASONING ENGINE
                    (Causal / Narrative)
                               v
                    COVERAGE ENGINE
              (Completeness / Confidence)
                               v
                  INVESTMENT INTELLIGENCE
                               |
          +--------------------+--------------------+
          v                    v                    v
      Research             Screening            Monitoring
          +--------------------+--------------------+
                               v
                    DECISION ENGINES
                               v
                    PORTFOLIO ENGINE
                               v
                     FUND OPERATIONS
```

## 63. The project's strategic position

Investment information is fragmented across filings, documents, financial
statements, market data, news, corporate actions, company relationships,
industry information, historical events. Humans and traditional systems
often treat these as separate datasets. The Investment OS aims to create
**one continuously updated, evidence-backed investment intelligence layer
connecting all of them.** That is the strategic thesis.

## 64. How to interpret the current validation

Good: grounding 100%, citation integrity 100%, document processing stable,
0 failures in pilot, self-critique/conflict detection/coverage
assessment/multi-ticker assessment all operational. Not yet solved:
information completeness, financial dataset, market dataset, entity graph,
secondary intelligence, temporal/PIT architecture, portfolio operations,
decision infrastructure. **The system's reliability architecture is ahead
of its information coverage architecture — that is the key diagnosis.**

## 65. What the next AI must NOT do

- Do NOT assume Investment OS = alpha model.
- Do NOT redesign the project into a quant strategy.
- Do NOT assume the objective is to predict stock prices or produce
  BUY/SELL signals.
- Do NOT discard the existing grounding/provenance architecture in favor
  of a generic RAG chatbot.
- Do NOT add LLM complexity merely for the sake of AI sophistication.
- Do NOT treat the 59.5% coverage score as prediction accuracy.
- Do NOT treat 100% citation accuracy as proof that investment conclusions
  are correct.
- Do NOT claim that financial statements, portfolio management, valuation,
  or comprehensive entity relationships already exist unless verified
  directly in the repository.

## 66. How the next AI should work on this project

1. Inspect the actual repository.
2. Map every existing module.
3. Inspect the database schema.
4. Inspect document ingestion.
5. Inspect extraction.
6. Inspect evidence handling.
7. Inspect grounding.
8. Inspect self-critique.
9. Inspect `CoverageAssessment`.
10. Inspect `EvidenceRanking`.
11. Inspect orchestration.
12. Inspect all validation scripts.
13. Compare implementation against this specification.
14. Identify what is actually implemented versus merely planned.
15. Never infer implementation from documentation alone.
16. Produce a gap analysis.
17. Prioritize missing infrastructure based on Investment OS requirements.
18. Preserve existing correctness guarantees.
19. Add tests before changing core architecture.
20. Avoid unnecessary rewrites.

## 67. The immediate engineering objective

Not "make the AI smarter." It is: **increase the information coverage of
the Investment OS while preserving evidence integrity and temporal
correctness.** Immediate target: financial statements + market data +
corporate actions + entity relationships + secondary sources + temporal
metadata, unified into the existing facts/evidence/events/factors/
implications/coverage/confidence architecture.

## 68. Final project definition (canonical)

> NGX Rotation is an AI-native Investment Operating System designed to
> continuously ingest, normalize, structure, validate, and reason over
> fragmented investment information across the Nigerian equity market. Its
> current implementation provides persistent document processing,
> deterministic and LLM-based extraction, evidence grounding, citation
> integrity, evidence ranking, conflict detection, self-critique, causal
> reasoning, event history, factor exposure, coverage assessment, and
> confidence control. The system's current strength is provenance and
> reasoning reliability; its primary limitation is incomplete
> investment-information coverage. The next stage is to build comprehensive
> financial, market, corporate-action, entity, secondary-source, and
> temporal data infrastructure, then connect the resulting intelligence
> layer to research, screening, portfolio, and investment decision
> workflows.

The project should be thought of as **the intelligence infrastructure
underneath an investment organization** — not the strategy, not the alpha,
not the trader, not the quant. The operating system.
