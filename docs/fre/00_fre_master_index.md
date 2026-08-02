# Financial Reasoning Engine (FRE) — Master Index

*Program status, UPDATED 2026-08-01: the 15-part design below is frozen
(tag `fre-architecture-baseline-2026-08-01`) and has since been
implemented through several individually-approved phases: **FRE-2**
(Evidence Graph), **FRE-3** (Company Memory), **FRE-4** (reaction-check),
**FRE-5** (Company Thesis, scoped to a pilot case study), and **FRE-6**
(Valuation Engine architecture — scaffolding + readiness-gating only,
`compute()` still unconditionally refuses to run on real data; no
valuation activation has occurred). A roadmap review conducted before
FRE-7 (`docs/fre_runs/roadmap_review_financial_statement_intelligence.md`)
found the dataset this program's Part 10/FRE-6-in-the-original-roadmap-
table anticipated did not yet exist, and inserted a dedicated **Financial
Statement Intelligence (FSI)** track to build it: **FSI Phase 1** (pilot
revenue/net_profit extraction, 30 facts, 5 tickers, tag
`fsi-phase1-baseline-2026-08-01`), **FSI Phase 2** (balance sheet, cash
flow, EBITDA/EBIT — 76 more facts, 106 total, tag
`fsi-phase2-baseline-2026-08-01`), and **FSI Phase 3** (Financial
Reasoning over the validated dataset — 177 mechanically-derived
conclusions: ratios, trend classifications, rule-based health flags,
plus a read-only evidence-linking layer; no new fact types, no valuation
output, no cross-company scoring; tag
`fsi-phase3-baseline-2026-08-01`), and **FSI Phase 4** (Point-in-Time
Financial Reasoning Memory — a read-only `as_of(ticker, date)` layer over
Phase 3's conclusions, gated by public filing dates rather than
financial period dates, with a mechanical 30-point look-ahead audit
finding 0 violations; tag `fsi-phase4-baseline-2026-08-01`), and **FSI
Phase 5** (Regression & Consistency Validation Harness — golden-snapshot
reproducibility, Phase 3/4 cross-consistency, and 3/3 historical
defects confirmed detectable via scratch-copy/isolated-function
injection, 0 deviations found in the real pipeline; tag
`fsi-phase5-baseline-2026-08-01`), and **FSI Phase 6** (Unified
Point-in-Time Company Memory — `CompanyMemory360.as_of()`, a pure
composition of FRE-3's `CompanyMemory` and Phase 4's
`pit_financial_memory`, neither underlying module modified, 0
discrepancies vs. both, 0 PIT leakage violations; tag
`fsi-phase6-baseline-2026-08-01`), and **FSI Phase 7** (Deterministic
Financial Reasoning Research Report — `render_report()`, a pure,
template-based Markdown renderer over Phase 6's snapshots, zero LLM
calls, zero new reasoning/scoring/ranking, determinism and sentence-to-
field traceability verified directly; tag
`fsi-phase7-baseline-2026-08-02`), and **FSI Phase 8** (Financial-
Reasoning-Informed Investment Thesis — `CompanyThesis360.as_of()`, a
pure composition of FRE-5's `CompanyThesis` and FSI Phase 6's
`CompanyMemory360`, neither modified, connecting the Investment Thesis
Engine to the FSI track's validated financial reasoning for the first
time; real fired concern flags surfaced as cited evidence, zero
scoring/weighting/ranking/synthesized-strength field; tag
`fsi-phase8-baseline-2026-08-02`), and **FSI Phase 9** (Knowledge Graph
Completeness — populated `entities` rows for all 5 FSI tickers (was
1/5, NASCON only) and 4 real, typed `renamed_from` `entity_
relationships` edges from the quant engine's own owner-verified
`symbol_renames.csv` (was 0 real relations, 1 `effect_chains`
artifact), closing Part 2's own long-standing, self-disclosed gap with
zero new extraction and zero LLM call; tag
`fsi-phase9-baseline-2026-08-02`), and **FSI Phase 10** (Knowledge
Graph Context Integration — `entity_context.py`, connecting Phase 9's
graph nodes to `CompanyMemory360` for the first time via a PIT-gated,
read-only composition; zero new data, zero writes, zero LLM calls; tag
`fsi-phase10-baseline-2026-08-02`), and **FSI Phase 11** (Complete
Institutional Research Dossier — `CompanyResearchDossier`/`render_
dossier()`, closing the reporting gap between Phase 6/7 (Company
Memory) and Phase 8/10 (Thesis Evidence, Knowledge Graph Context) by
reusing `render_report()` verbatim and appending two new sections;
zero new data, zero writes, zero LLM calls; tag
`fsi-phase11-baseline-2026-08-02`), and **FSI Phase 12** (Operational
Research Dossier Generation — `scripts/fre/generate_research_dossier.
py`, the platform's first real CLI entry point, wrapping Phase 11's
`build_dossier()`/`render_dossier()` unmodified; two real bugs found
and fixed, both genuine first-exercised-boundary findings (console
UTF-8 encoding, subprocess-capture mojibake); zero new reasoning, zero
database writes; tag `fsi-phase12-baseline-2026-08-02`), and **FSI
Phase 13** (Coverage Expansion — real-ticker roster grown from 5 to 10:
MTNN, DANGCEM, UBN, OANDO, NESTLE added via Phase 1/2's own
hand-verified extraction methodology, 31 new revenue/net_profit/ebit/
ebitda facts across 10 real filings; Phases 3-12, nine frozen modules,
re-run against the expanded dataset with ZERO code modification and
confirmed to generalize; one real bug found and fixed, introduced by
this phase's own execution rather than a pre-existing defect — Phase 3's
frozen compute scripts, re-run against the expanded ticker set,
duplicated the 5 original tickers' financial-reasoning conclusions
(no dedup check had ever been needed before); golden snapshot re-frozen
at 137 facts / 267 conclusions; tag `fsi-phase13-baseline-2026-08-02`),
and **FSI Phase 14** (Evidence-Based Screening — `src/ngxrot/fre/
screening.py`'s `screen_by_flag()`/`screen_by_trend()`, the platform's
first function to legitimately operate across all tickers at once,
implementing Part 9's own long-frozen Tier-1 "Screening" design;
categorical filters only, no numeric threshold; alphabetical-ticker
ordering enforced mechanically; no score/rank field; verified to never
import/be-imported-by `alpha_engine.py`/`runner.py`; zero writes, zero
schema change, zero LLM calls; tag `fsi-phase14-baseline-2026-08-02`),
and **FSI Phase 15** (Screening CLI — `scripts/fre/screen_companies.py`,
a thin wrapper around Phase 14's `screen_by_flag()`/`screen_by_trend()`,
mirroring Phase 12's CLI pattern exactly; zero writes, zero schema
change; tag `fsi-phase15-baseline-2026-08-02`), and **FSI Phase 16**
(Composition-Layer Ticker Coverage Fix — found and fixed 6 dedicated
per-phase test files that had silently stopped covering Phase 13's 5
new tickers, switching them to dynamic ticker discovery
(`list_tickers()`) so a future coverage-expansion phase cannot silently
under-test again; added a 4th "composition-layer smoke coverage"
component to Phase 5's validation harness; zero modification to any
production module; tag `fsi-phase16-baseline-2026-08-02`), and **FSI
Phase 17** (Portfolio-Memory Cross-Reference — `src/ngxrot/fre/
portfolio_memory.py`'s `cross_reference()`, one of Part 9's five
Tier-1 capabilities; reuses `AlphaEngine().recommendations()` verbatim, zero
modification to `alpha_engine.py`/`registry.py`, zero write path
anywhere (AST-verified); deliberately not wired into `company_research_
dossier.py` in this phase; tag `fsi-phase17-baseline-2026-08-02`), and
**FSI Phase 18** (Watchlist Persistence — one new table,
`watchlist_entries`, and `src/ngxrot/fre/watchlist.py`
(`add_entry()`/`remove_entry()`/`get_history_for_ticker()`/
`list_active()`), another of Part 9's five Tier-1 capabilities;
append-only (no DELETE anywhere, AST-verified), `entry_criteria`
required and schema-enforced NOT NULL; all test writes confined to a
scratch copy, real production database confirmed unchanged; tag
`fsi-phase18-baseline-2026-08-02`), and **FSI Phase 19** (Qualitative
Correlation Notes — `src/ngxrot/fre/correlation_notes.py`'s
`note_for_pair()`, the fourth of Part 9's five Tier-1 capabilities;
this phase also disclosed and corrected Phase 17/18's own
documentation, which had incorrectly stated Part 9 names only three
Tier-1 items -- it names five: Watchlist, Screening, Sector-coverage
view, Qualitative correlation notes, Portfolio memory; narrative-only
shared-exposure reasons via `[macro_exposure]`-taxonomy edges to a
common counterpart entity, reusing `entity_context.
get_entity_context()` unmodified, never a numeric score or shared-edge
count (Part 9's own pre-rejected alternative #2); pairwise-only, never
an all-pairs/matrix mode; zero write path anywhere (AST-verified);
confirmed against real data that `entity_relationships` holds 0
`macro_exposure` rows today, so every real ticker pair honestly
returns an empty note; tag `fsi-phase19-baseline-2026-08-02`), and
**FSI Phase 20** (Portfolio-Context-Annotated Research Dossier —
`src/ngxrot/fre/company_portfolio_context.py`'s `as_of()`/`render()`,
closing the exact integration Part 9 itself specifies for Portfolio
Memory ("attach a note to a CompanyThesis or watchlist entry") and
that Phases 17/18 each explicitly deferred to "a future phase";
composes `build_dossier()` (Phase 11), `list_active()` (Phase 18,
reused specifically for its already-PIT-correct semantics), and
`cross_reference()` (Phase 17) -- each called once, none modified,
confirmed via `git diff --stat`; discloses that the portfolio-memory
section is inherently non-PIT (always-live), an inherited Phase 17
limitation, not fixed here; tag `fsi-phase20-baseline-2026-08-02`).
Part 9's Tier 1 now stands at 4 of 5 built and fully wired together --
only Sector-coverage view remains, genuinely blocked on
`securities.sector_ngx` population (0/320, an external data
dependency), and **FSI Phase 21** (Watchlist CLI --
`scripts/fre/manage_watchlist.py`'s `add`/`remove`/`list`/`history`
subcommands, a thin wrapper around Phase 18's own functions, called
unmodified; the platform's FIRST standing operator tool able to write
to the real production database -- every prior CLI is read-only by
construction; the new risk is disclosed and mitigated structurally
(no new write logic, every write routes through Phase 18's own
already-validated, append-only functions); every write-path test
invocation targets a disposable scratch copy via an NGXROT_DB_PATH
override, confirmed via real-database row-count diffing; tag
`fsi-phase21-baseline-2026-08-02`). Part 9's Tier 1 is now fully
built AND fully operable from the command line (modulo Sector-coverage
view's external blocker), and **FSI Phase 22** (Portfolio-Context
Dossier CLI -- `scripts/fre/generate_portfolio_context_dossier.py`, a
read-only wrapper around Phase 20's `as_of()`/`render()`, mirroring
Phase 12's pattern exactly; also investigated and set aside, with real
queried data rather than assumption, a candidate new financial-health
flag using `cfo`/`cfi`/`cff`/`fcf` trend data -- each has 0-1 computed
trend conclusions on the real database today, too thin to justify a
phase yet; tag `fsi-phase22-baseline-2026-08-02`).
All 22 phases are complete and frozen. Full
implementation history, results, and an architectural-defect
discovery-and-fix precedent are in `docs/fre_runs/`. No further phase has
been approved or started as of this writing. Everything below this line is
the original, frozen design document and describes the program as first
conceived; it is retained unmodified as the architectural reference, not
updated in place as execution has diverged from it (see the roadmap
review above for the specific divergence).*

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
