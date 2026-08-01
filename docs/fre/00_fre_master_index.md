# Financial Reasoning Engine (FRE) — Master Index

*Program status: DESIGN ONLY, complete, awaiting owner review. No code
written, no schema migrated, no config file created, no dependency
installed, no experiment run, nothing committed, no branch created, as of
this pass. Repository state outside `docs/fre/` is unmodified.*

## What this program is

The Financial Reasoning Engine is the layer that will eventually sit on
top of the Local Intelligence Model (`docs/LIM_ARCHITECTURE.md`) and the
existing AI Intelligence Layer (`docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`,
`docs/REASONING_ENGINE_SPECIFICATION.md`) to transform extracted NGX
evidence into institutional-grade investment reasoning — scoped
exclusively to the Nigerian Exchange, not a general finance assistant.
Every document in this program **extends** existing, tested, real
infrastructure; none of them propose replacing, forking, or bypassing it.
The frozen quant architecture, the hard `ngxrot.documents` import boundary,
the 14-step reasoning chain, the self-critique gate, and PIT/append-only
discipline are treated as non-negotiable throughout — see Part 13's
consolidated "never change" list and Part 14's risk assessment for the
governance risks this program is most careful about.

## Reading order

| # | Document | One-line summary |
|---|---|---|
| 1 | [`01_financial_ontology.md`](01_financial_ontology.md) | Causal (not dictionary) vocabulary of NGX financial mechanisms, tied directly to `docs/FACTOR_REGISTRY.md`'s own confirmed/rejected evidence |
| 2 | [`02_knowledge_graph_expansion.md`](02_knowledge_graph_expansion.md) | Typed entity relationships, lineage, ownership — closes two real gaps found in the existing `entities`/`entity_relationships` schema |
| 3 | [`03_evidence_graph.md`](03_evidence_graph.md) | The owner's 9-stage Evidence→...→Missing-evidence chain, mapped onto existing tables, worked per financial-statement section |
| 4 | [`04_reasoning_engine.md`](04_reasoning_engine.md) | Ten reasoning modes (causal, counterfactual, historical, trend, comparative, sector, macro, valuation, uncertainty, portfolio) with mode-specific guardrails |
| 5 | [`05_company_memory.md`](05_company_memory.md) | PIT-safe, per-company longitudinal memory — filings, dividends, management, strategy narrative, cyclicality |
| 6 | [`06_cross_document_reasoning.md`](06_cross_document_reasoning.md) | Synthesizing filings, presentations, news, macro data, and market prices into one process, incl. a deterministic reaction-check |
| 7 | [`07_investment_thesis_engine.md`](07_investment_thesis_engine.md) | Bull/bear/base case aggregation into a standing `CompanyThesis` — with a hard guardrail against ever outputting a numeric expected return |
| 8 | [`08_valuation_engine_architecture.md`](08_valuation_engine_architecture.md) | DCF/DDM/Residual Income/Comparables architecture, sector-eligibility-typed, blocked entirely on a financial-statements dataset |
| 9 | [`09_portfolio_reasoning.md`](09_portfolio_reasoning.md) | Watchlists/screening (buildable now) vs. ranking/sizing/risk (correctly gated, unchanged preconditions) |
| 10 | [`10_dataset_strategy.md`](10_dataset_strategy.md) | Every dataset this program needs, prioritized by leverage and cost, not by hope |
| 11 | [`11_evaluation_framework.md`](11_evaluation_framework.md) | Metrics for all eleven owner-named quality dimensions, extending the existing LIM/AI-layer evaluation methodology |
| 12 | [`12_research_roadmap.md`](12_research_roadmap.md) | Phases FRE-1 through FRE-10, each individually gated, none auto-proceeding |
| 13 | [`13_gap_analysis.md`](13_gap_analysis.md) | What exists, what's partial, what's missing — including a direct answer to "how ready is LIM for this" |
| 14 | [`14_risk_assessment.md`](14_risk_assessment.md) | Consolidated + new cross-cutting risks by category |
| 15 | [`15_final_review.md`](15_final_review.md) | The consolidated report — maturity, readiness, priorities, risks, roadmap, moat |

## Standing rules for this entire program

1. **No implementation.** Every document above is architecture/research
   only — no code, no schema migration, no dependency installation, no
   experimental run, no commit, no tag, no branch.
2. **Extend, never fork.** Every design builds on a named, existing,
   real component — the AI Intelligence Layer's schema, `company_intelligence.py`,
   `context.py`, `industry_reasoning.py`, `evidence_ranking.py`,
   `coverage_assessment.py`, `alpha_engine.py`'s adapter pattern — never a
   parallel system.
3. **Never invent alpha.** Every document that touches anything
   portfolio-adjacent (Parts 7, 8, 9 especially) restates and enforces the
   charter's "the engine only speaks from validated models" rule with a
   concrete mechanism, not just a promise.
4. **Honest disclosure over polish.** Negative results, unresolved
   questions, and genuine gaps (LIM's `self_critique_quality` still 0.0,
   the `discovery_feed.py` build-status uncertainty, the OCR gap) are
   stated plainly, matching this platform's established discipline
   throughout the LIM research program.
5. **This program authorizes nothing.** No phase in Part 12's roadmap
   begins as a result of these documents existing — each requires its own
   explicit, separate owner approval, exactly like every other phase gate
   on this platform.
