# Implementation Timeline — 2026-08-02 Stable Baseline

*Every completed phase across FRE, FSI, Portfolio Reasoning, Knowledge
Graph, CLI, and Validation, in execution order, with its tag. Dates
are the real dates work happened, not backfilled. Pre-FRE/FSI
milestones (Quant Engine H-011 confirmation, AI Intelligence Layer
unlock) are included for context since later phases depend on them.*

## Pre-program context

| Date | Milestone |
|---|---|
| 2026-07-15 | H-001 (NGX momentum) rejected on real data — post-mortem informs all later hypothesis discipline |
| 2026-07-22 | H-011 (Size) reaches `confirmed` — unlocks Company Intelligence Engine v0 scaffolding |
| 2026-07-22 | AI Intelligence Layer designed (Phase A-G roadmap), Phase A implemented (documents/entities/entity_mentions tables, 11,533 real documents processed) |
| 2026-07-22 | Phase B (deterministic dividend/corporate-action fact extraction, 143 facts) |
| 2026-07-22 | Phase C (full reasoning pipeline: extraction, self-critique gate, 32/32 engineering tests) built; blocked on LLM credentials |
| 2026-07-22 | Provider swapped Anthropic → Gemini (`gemini-3.6-flash`), reasoning pipeline confirmed provider-agnostic by construction |

## FRE track (individually owner-gated)

| Tag | Phase | Deliverable |
|---|---|---|
| `fre-architecture-baseline-2026-08-01` | — | 15-part FRE design frozen |
| — | FRE-2 | Evidence Graph |
| — | FRE-3 | Company Memory |
| — | FRE-4 | Reaction-check (deterministic market-reaction cross-check) |
| — | FRE-5 | Company Thesis (pilot case study, no numeric expected return) |
| — | FRE-6 | Valuation Engine architecture (scaffolding + readiness-gating only) |

## FSI track, Phases 1-13 (individually owner-approved)

| Tag | Phase | Deliverable |
|---|---|---|
| `fsi-phase1-baseline-2026-08-01` | 1 | Pilot revenue/net_profit extraction — 30 facts, 5 tickers |
| `fsi-phase2-baseline-2026-08-01` | 2 | Balance sheet/cash flow/EBITDA/EBIT — 106 facts total |
| `fsi-phase3-baseline-2026-08-01` | 3 | Financial reasoning (ratios/trends/flags) — 177 conclusions |
| `fsi-phase4-baseline-2026-08-01` | 4 | Point-in-Time Financial Reasoning Memory |
| `fsi-phase5-baseline-2026-08-01` | 5 | Regression & Consistency Validation Harness |
| `fsi-phase6-baseline-2026-08-01` | 6 | Unified PIT Company Memory (`CompanyMemory360`) |
| `fsi-phase7-baseline-2026-08-02` | 7 | Deterministic Financial Reasoning Research Report |
| `fsi-phase8-baseline-2026-08-02` | 8 | Financial-Reasoning-Informed Investment Thesis |
| `fsi-phase9-baseline-2026-08-02` | 9 | Knowledge Graph Completeness |
| `fsi-phase10-baseline-2026-08-02` | 10 | Knowledge Graph Context Integration |
| `fsi-phase11-baseline-2026-08-02` | 11 | Complete Institutional Research Dossier |
| `fsi-phase12-baseline-2026-08-02` | 12 | Operational Research Dossier Generation (first CLI) |
| `fsi-phase13-baseline-2026-08-02` | 13 | Coverage Expansion, 5→10 tickers |

## FSI track, Phases 14-27 (owner's standing continuous-execution authorization)

| Tag | Phase | Deliverable |
|---|---|---|
| `fsi-phase14-baseline-2026-08-02` | 14 | Evidence-Based Screening (Part 9 Tier 1, #1 of 5) |
| `fsi-phase15-baseline-2026-08-02` | 15 | Screening CLI |
| `fsi-phase16-baseline-2026-08-02` | 16 | Composition-Layer Ticker Coverage Fix (regression found + fixed) |
| `fsi-phase17-baseline-2026-08-02` | 17 | Portfolio-Memory Cross-Reference (Part 9 Tier 1, #2 of 5) |
| `fsi-phase18-baseline-2026-08-02` | 18 | Watchlist Persistence (Part 9 Tier 1, #3 of 5; new table) |
| `fsi-phase19-baseline-2026-08-02` | 19 | Qualitative Correlation Notes (Part 9 Tier 1, #4 of 5; docs correction) |
| `fsi-phase20-baseline-2026-08-02` | 20 | Portfolio-Context-Annotated Research Dossier |
| `fsi-phase21-baseline-2026-08-02` | 21 | Watchlist CLI (first write-capable operator tool) |
| `fsi-phase22-baseline-2026-08-02` | 22 | Portfolio-Context Dossier CLI |
| — | — | **Architecture audit, Revision 1** — stopping point after Phase 22 |
| `fsi-phase23-baseline-2026-08-02` | 23 | Sector Classification Data (`sector_ngx`, 136/320; owner-authorized external source) |
| `fsi-phase24-baseline-2026-08-02` | 24 | Sector-Coverage View (Part 9 Tier 1, #5 of 5 — **Tier 1 closed in full**) |
| `fsi-phase25-baseline-2026-08-02` | 25 | Sector-Coverage View CLI |
| — | — | **Architecture audit, Revision 2** — stopping point after Phase 25 |
| `fsi-phase26-baseline-2026-08-02` | 26 | Sector-to-Company-Type Mapping (owner-directed) |
| `fsi-phase27-baseline-2026-08-02` | 27 | Industry Exposure Integration (owner-directed) |
| — | — | **Architecture audit, Revision 3** — stopping point after Phase 27, accepted by owner as final |
| `platform-baseline-2026-08-02-stable` | — | **This close-out: consolidated docs, final verification, stable production baseline** |

## Real defects/errors found and fixed during this program (disclosed, not hidden)

| Phase found | Defect | Resolution |
|---|---|---|
| Phase 2 (2026-08-01) | `restatement_detection.py` flagged nested reporting periods as false restatements | Stopped, documented, owner-authorized fix applied |
| Phase 13 | Re-running Phase 3's frozen compute scripts against the expanded ticker set duplicated 5 original tickers' conclusions (no dedup check had ever been needed) | Dedicated cleanup script, backup, confirmed byte-for-byte restoration |
| Phase 15 | Substring-based import-boundary check false-positived on `screening.py`'s own docstring prose | Fixed to AST-based import inspection; pattern reused in every later phase |
| Phase 16 | 6 dedicated test files had silently stopped covering Phase 13's 5 new tickers (hardcoded ticker lists) | Switched to dynamic `list_tickers()` discovery |
| Phase 19 | Phase 17/18's own documentation understated Part 9's Tier-1 capability count (3 instead of 5) | Corrected forward-looking, in Phase 19's own docs (frozen phase docs not retroactively edited) |
| Phase 23 | `docs/fre/10_dataset_strategy.md` assumed sector labels were a free filing-extraction side effect | Verified false against a real filing; real external source found and used instead |
| Phase 23 | Three stale "0/320 populated" claims in `valuation_engine.py`/`lim/audit.py`/`company_intelligence.py` | Corrected for factual accuracy; verified zero behavior change in each case |
