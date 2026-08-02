# Owner Decision Backlog — 2026-08-02 Stable Baseline

*Every remaining capability this platform's own architecture has
already designed or scoped, together with the exact external
dependency or owner decision required to unlock it. Nothing in this
list is a code gap — every item is blocked on an input only the owner
(or a party the owner designates) can supply. Compiled from
`fsi_final_architecture_audit_2026-08-02.md` (Revision 3) and every
phase's own final report. This is a live document: re-check each row
against real data before assuming it still holds (see each row's own
"how to re-check" note).*

## How to use this document

Each row names: the capability, exactly what unlocks it, which
existing design already covers it (so no new design work is needed
once unlocked), and how to verify the blocker still holds before
assuming it does.

## 1. Data acquisition decisions

| Capability | Exact unlock needed | Already designed in | How to re-check |
|---|---|---|---|
| Coverage expansion beyond 10 FSI tickers | Owner decision to allocate hand-extraction labor to more of the 39 remaining already-scoped candidate tickers (349-document pool, Phase 1's own scoping) | Phase 1/2/13's own hand-verification methodology, reusable unmodified | `SELECT COUNT(*) FROM extracted_facts` and compare ticker roster against `docs/fre_runs/fsi_phase1_preregistration.md`'s original 49-ticker candidate list |
| Remaining 184 securities' `sector_ngx` | A different/historical NGX document (the Daily Official List used in Phase 23 covers only actively-traded equities on a given date) or owner confirmation of delisting status for absent tickers | Phase 23's own population script, `scripts/fre/populate_sector_ngx.py`, directly extensible with a new source | `SELECT COUNT(*) FROM securities WHERE sector_ngx IS NULL` (currently 184) |
| `cfo`/`cfi`/`cff`/`fcf`-based financial-health flag | More real filing periods for these specific line items — either from coverage expansion (above) or from extracting additional periods for the existing 10 tickers | `financial_health_flags.py`'s own existing rule pattern, directly extensible | `SELECT metric, COUNT(*) FROM financial_reasoning_conclusions WHERE conclusion_type='trend' AND metric IN ('cfo','cfi','cff','fcf') AND status='computed' GROUP BY metric` (currently 1/1/1/0) |
| `correlation_notes.py` CLI / broader use | Real `macro_exposure`-type (`exposed_to_commodity`/`exposed_to_fx`/`exposed_to_policy`) edges in `entity_relationships` — requires a new extraction pass over filings for shared-exposure language | `correlation_notes.py` itself already handles real data the moment it exists, zero code change needed | `SELECT COUNT(*) FROM entity_relationships WHERE relation_type LIKE 'exposed_to_%'` (currently 0) |
| `subsidiary_of` lineage edges (unlocks `sum_of_the_parts` valuation adapter) | A new extraction pass identifying real parent/subsidiary relationships from filings | Part 2 of the frozen FRE design (`02_knowledge_graph_expansion.md`) already names this exact need | `SELECT COUNT(*) FROM entity_relationships WHERE relation_type='subsidiary_of'` (currently 0) |

## 2. Vendor/provider decisions

| Capability | Exact unlock needed | Already designed in | How to re-check |
|---|---|---|---|
| OCR-dependent filings (36% of the document archive) | Owner selection of an OCR engine/vendor — flagged as pending since 2026-07-16, unresolved through this entire program | `docs/EXECUTION_BACKLOG.md`'s own AI-2 item | `reports/document_text_coverage.md` — 4,134 of 11,533 documents flagged not-OCR'd |
| LIM training/deployment | Exact Qwen3.x checkpoint/version to build against | `docs/LIM_ARCHITECTURE.md`'s own Phase LIM-0 through LIM-8 roadmap, fully designed, none built | `docs/LIM_ARCHITECTURE.md` §"Open questions" |
| Analyst research ingestion (Part 6's Analyst Notes source) | A licensing decision — explicitly legally gated, not an engineering question | `docs/REASONING_ENGINE_SPECIFICATION.md` §13, `AnalystResearchProvider` named but not built | Check whether a licensing agreement has since been reached |
| Macro/industry report ingestion (NBS/SEC/sector-body documents) | Confirmation the `MacroDocumentProvider` probe (2026-07-15) should proceed to a real harvest | `docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md` §4.1 | Check `MacroDocumentProvider`'s own build status |

## 3. Human-judgment / gold-set decisions

| Capability | Exact unlock needed | Already designed in | How to re-check |
|---|---|---|---|
| Evaluation Framework (FRE-10 / Part 11) | An analyst-authored gold-standard label set — cannot be substituted by more engineering | `docs/fre/11_evaluation_framework.md`, fully designed | Check whether a gold-set has been authored/delivered |
| News-source reliability-tier registry | A real, owner-or-analyst-vetted list of Nigerian financial news outlets and their credibility tiers | `evidence_ranking.py`'s own `TrustAssignment` mechanism, ready to consume it the moment it exists | `configs/` — check for a `news_outlets` registry file; none exists as of this baseline |
| Sector-to-company-type mapping's 3 unresolved Financial-Services sub-industries (Micro-Finance Banks, Mortgage Carriers, "Other Financial Institutions") | An owner ruling on whether any of these should map to `"bank"`/`"general"`/a new company_type, given the genuine internal heterogeneity Phase 26 found | `configs/sector_company_type_mapping.toml`'s own disclosed comments name exactly which 12 real tickers are affected | `sector_ngx_provenance` table, filtered to these 3 sub-industry values |
| A `reit` company_type (for `CONSTRUCTION/REAL ESTATE`'s 4 REIT tickers) | An owner decision to add a new company_type + its own NAV/FFO-style valuation-method set to `valuation_method_eligibility.toml` | Not yet designed at all — would need its own Part-8-style design pass first | `configs/valuation_method_eligibility.toml` — confirm `reit` is still absent |

## 4. Architecture-revision authorizations (guardrail-gated, not data-gated)

| Capability | Exact unlock needed | Already designed in | How to re-check |
|---|---|---|---|
| Valuation Engine activation (`compute()` producing a real number) | A future, separate, explicit architecture-revision authorization — the standing guardrail this entire program enforced throughout ("never invent alpha... unless explicitly authorized in a future architecture revision") | `docs/fre/08_valuation_engine_architecture.md`, `valuation_engine.py`'s own six adapters, fully scaffolded | `grep NotImplementedError src/ngxrot/fre/valuation_engine.py` — confirm still present |
| Part 9 Tier 2 (ranking, position sizing, conviction-weighted allocation, portfolio-level risk, rotation) | ≥2 validated independent factors (currently 1: H-011/Size) — a Quant Engine research outcome, never to be shortcut by FRE/FSI | `docs/fre/09_portfolio_reasoning.md` §"Tier 2," interfaces already named for the eventual consumer | `docs/FACTOR_REGISTRY.md` — count `confirmed` entries |
| A second validated quant factor | New hypothesis research (Wave-3/H-0xx track) — pre-registration, gauntlet, placebo/power tests, the Quant Engine's own unchanged process | `docs/WAVE_3_RESEARCH_DIRECTIONS.md` | `docs/FACTOR_REGISTRY.md` |
| A working macro-conditioning factor | H-004/H-005 were both rejected; a new hypothesis would be required | Wave-3 candidate C2, not yet built | `docs/FACTOR_REGISTRY.md` |

## 5. Low-priority / cosmetic-only (not blocked, just not valuable enough to warrant a phase alone)

| Item | Why it's here, not above | Owner call needed |
|---|---|---|
| `sum_of_the_parts`/`normalized_earnings_multiple`/`asset_based_floor` adapter stubs | Building empty, always-`NOT_READY` classes changes no real behavior — the existing "adapter is None" disclosure already states "not yet built" correctly | Whether cosmetic disclosure precision is worth a phase on its own |
| `valuation_engine.py`'s coarse `is_ready()` per-adapter check | Tightening it to check each method's own specific `required_inputs` is a precision improvement, not a capability change | Whether worth a phase on its own |
| `FIRSTHOLDCO`/`FirstHoldCo` duplicate-case ticker row in `securities` | A pre-existing data-quality question, found and disclosed during Phase 23, not caused by this program | Which row (if either) should be corrected/removed |
