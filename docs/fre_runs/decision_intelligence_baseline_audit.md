# Decision Intelligence & Recommendation Engine — Phase 0 Baseline Audit

**Date**: 2026-08-09
**Status**: Audit complete. **Implementation has NOT started** — this audit surfaced a
direct conflict between the new request's Phase 5/8/10 (signal synthesis into a
combined call, BUY/AVOID recommendations, cross-sectional ranking) and an existing,
explicit, dated, multiply-cross-referenced architectural gate already on record in
this codebase (§6). Per the new task's own instruction to stop at genuine governance
gates and material architectural decisions, this report stops here pending an
explicit answer from the user on how to reconcile the two (see the question posed
immediately after this report, or if reading this later, the record of that
decision).

---

## 1. What already exists (by requested Phase 0 checklist item)

### 1.1 Intelligence-related modules (`src/ngxrot/fre/`, 23 modules)

| Module | Phase | What it does |
|---|---|---|
| `company_thesis.py` | FRE-5 | Bull/base/bear case, key risks, catalysts, competitive position, financial-signal summary, management/capital-allocation assessment, market-reaction cross-check, confidence + rationale — assembled verbatim from `investment_implications`, no numeric blending |
| `company_thesis_360.py` | FSI-8 | Joins the thesis above with financial-reasoning conclusions, classified into concern vs. supplementary evidence |
| `evidence_graph.py` | FRE-2 | The 9-stage Evidence→...→Missing-Evidence chain; `build_evidence_chain(fact_id)` is a ready-made, real evidence-traceability primitive |
| `company_memory.py` / `company_memory_360.py` | FRE-3 / FSI-6 | PIT-safe per-company longitudinal state: filing history, dividend/corporate-action history, financial-reasoning conclusions as of a date |
| `company_portfolio_context.py` | FSI-20 | Attaches watchlist status + live quant-sleeve cross-reference to a research dossier |
| `company_research_dossier.py` | FSI-11 | Full institutional-style Markdown dossier (memory + thesis + knowledge-graph context) — **this is most of requested Phase 13 already** |
| `reaction_check.py` | FRE-4 | Deterministic price-reaction cross-check against a fact's own qualitative direction verdict |
| `screening.py` | FSI-14 | Cross-ticker categorical filters (flag fired/not, trend direction) — deliberately unordered, no scores |
| `watchlist.py` | FSI-18 | Persistent, append-only, PIT-correct watchlist with a real write path (`watchlist_entries`) |
| `portfolio_memory.py` | FSI-17 | Read-only cross-reference into the live quant sleeve (`alpha_engine.py`) |
| `financial_health_flags.py` | FSI-3 | Three named, auditable flags: `leverage_increasing`, `cash_flow_earnings_divergence`, `margin_compression` |
| `entity_context.py` | FSI-10 | PIT-gated knowledge-graph read (entities + relationships) |
| `reasoning_context.py` | FSI-3 | Full structured evidence trail behind any one financial-reasoning conclusion |
| `correlation_notes.py` | FSI-19 | Pairwise, non-numeric shared-macro-exposure notes (0 real edges exist today) |
| `sector_coverage.py` / `sector_company_type_mapping.py` | FSI-24/26 | Sector-level coverage counts; sector→company_type taxonomy |
| `pipeline_validation.py` | FSI-5 | Regression/consistency harness over the whole FSI pipeline |
| `restatement_detection.py`, `confidence_propagation.py`, `period_normalization.py`, `pit_financial_memory.py`, `financial_ratios.py` | FSI-2/3/4 | The frozen accounting core (unmodified since FRE-7) |
| `valuation_engine.py`, `economic_peer_taxonomy.py`, `genuine_fact_universe.py` | FRE-6/7/7A/7B.1 | This session's own prior work — real but limited P/E/P/B/DCF coverage (7/24 tickers P/E-ready), FRE-7 pilot gate currently FAILING (0/1 bracket) |
| `trend_classification.py` | FSI-3 | Directional (increasing/decreasing/stable) classification across non-overlapping periods |
| `financial_reasoning_report.py` | FSI-7 | Deterministic Markdown rendering of a `CompanyMemory360Graph` |

**Top-level (`src/ngxrot/`)**: `company_intelligence.py` (a DIFFERENT, older, price/liquidity/factor-exposure-centric per-ticker profile — `build_profile()`, explicit `UNAVAILABLE_FIELDS` for financial quality/growth/valuation/macro/ownership), `corporate_action_audit.py`, `event_pipeline.py` (real event ingestion with a write path), `confidence_rating.py` (quant-track confidence rater, 0-12 rule-based score), `ic_report.py` (quant-track IC memo generator), `coverage.py` (price-data coverage gate).

**`src/ngxrot/documents/`**: `reasoning_engine.py`, `self_critique.py`, `reasoning.py`, `industry_reasoning.py`, `evidence_ranking.py`, `coverage_assessment.py`, `entities.py` — the per-document LLM-reasoning pipeline that produces `investment_implications`/`causal_chain_steps`/`impact_assessments` in the first place.

**Frozen, separate track**: `registry.py`/`ledger.py` back a *different* database (`data/registry.sqlite`) — the immutable quant hypothesis/experiment ledger. Not part of the FRE/FSI schema at all.

### 1.2 Existing tables/schema (`data/ngx.sqlite`, 31 tables)

Full inventory in the audit transcript; the ones most relevant to this task:
`securities`, `sector_ngx_provenance`, `equity_prices`, `index_levels`/`indices`/
`index_membership` (real NGX market-level data — Phase 11's own scope item),
`corporate_actions`, `documents`, `extracted_facts` (490 rows), `evidence` (603),
`causal_chain_steps` (142, with `implication_layer`), `impact_assessments` (559),
`investment_implications` (43 — **already has an `action_recommendation` column**,
but its real values are workflow actions — `model_update`/`no_action`/
`research_task`/`immediate_review`/`watchlist` — not an investment BUY/HOLD/SELL
vocabulary; not a duplicate of what's requested), `entities`/`entity_relationships`,
`events` (184, real event taxonomy), `financial_reasoning_conclusions`/
`financial_reasoning_conclusion_facts`, `watchlist_entries` (0 rows — built,
unused), `llm_calls`.

**No insider-transaction table exists.** Grep across the schema found no
`insider_dealing`/`insider_transactions` table. Top-level scripts
(`stage23_insider_dealing_pilot.py`, `stage24_insider_dealing_diagnostic.py`) exist
but were not deeply inspected this pass — flagged as a real, likely-partial existing
asset to check before building Phase 1's insider-activity section.

### 1.3 Existing event taxonomy

`configs/event_taxonomy.toml` (used by `event_pipeline.py`) and
`configs/fact_taxonomy.toml`/`document_taxonomy.toml` already define the
categorical vocabularies this task's Phase 1/2 (corporate events, regulatory
events, change categories) should consume, not reinvent.

### 1.4 Existing financial-fact structures

`extracted_facts` (`fact_type`, `period_start/end/type`, `confidence_tier`,
`currency`, `restates_fact_id`) is the single source of truth, already governed by
the frozen accounting core (§1.1). `financial_reasoning_conclusions` holds derived
ratios/trends/flags. Both are read-only inputs to any new layer — never to be
written to except via the existing, frozen extraction/computation paths.

### 1.5 Existing provenance structures

`evidence` (quoted_text, page_number, char range, source_confidence) +
`causal_chain_steps`/`impact_assessments`/`investment_implications`'s own
fact/evidence linkage + `financial_reasoning_conclusion_facts` (conclusion→fact
role linkage) together already implement almost exactly the
`SOURCE → DOCUMENT → FACT/EVENT → INTERPRETATION → THESIS` chain this task's Phase
6 asks for. `evidence_graph.build_evidence_chain(fact_id)` is a ready-made,
directly reusable read for "why" queries — this task's Phase 6 should extend this,
not rebuild it.

### 1.6 Existing valuation outputs

This session's own prior work (`valuation_engine.py` + `economic_peer_taxonomy.py`):
7 of 24 real tickers are P/E-ready, 8 are P/B-ready; the frozen FRE-7 pilot gate is
currently **FAILING** (0/1 bracket cases, per `fre7b1_targeted_accounting_extraction_report.md`
and `fre7b2_peer_coverage_recovery_feasibility.md`). This is directly what the new
task's own "Core Principle" anticipates: *"If valuation cannot be computed... the
system must explicitly report `VALUATION_CONFIDENCE = LOW`."* No new valuation work
is needed to honor this — the existing `TriangulatedValuation.valuation_confidence`
field (`no_data`/`single_method`/`low`/`medium`/`high`) already provides exactly
this signal and should be read, not recomputed.

### 1.7 Existing company profiles

Two, serving different purposes, both real: `company_intelligence.build_profile()`
(price/liquidity/factor-exposure axis) and `company_memory_360.as_of()` +
`company_thesis_360.as_of()` (filing/evidence/reasoning axis). This task's "Company
State Engine" (Phase 1) should compose both, not replace either.

### 1.8 Existing research/hypothesis structures

`registry.py`/`ledger.py` (separate DB, immutable, quant hypothesis track) —
completely out of scope for this task per the frozen-core rule; `research_task_candidates`
table (FRE side) is a lighter-weight, already-real "needs more research" queue that
directly overlaps Phase 10's "Needs More Research" ranking output.

### 1.9 Existing tests

Every module in §1.1 has a corresponding `scripts/fre/test_*.py` script (same
no-pytest, assertion-script convention used throughout this session's own prior
FRE-7/7A/7B/7B.1/7B.2 work). Any new module must follow this exact convention.

### 1.10 Frozen files (must not be modified)

- **Accounting core** (per this session's own standing instruction, still in
  force): `financial_ratios.py`, `pit_financial_memory.py`, `period_normalization.py`,
  `restatement_detection.py`, `confidence_propagation.py`.
- **Quant research track**: `alpha_engine.py`, `runner.py`, `phase4.py`,
  `registry.py`, `ledger.py`, and everything under `data/registry.sqlite`.
- **The 15-part FRE architecture design itself** is explicitly frozen
  (`docs/fre/00_fre_master_index.md`: tag `fre-architecture-baseline-2026-08-01`,
  "No further phase begins until a trigger named in
  `OWNER_DECISION_BACKLOG_2026-08-02.md` actually occurs").
- **`valuation_engine.py`'s adapters, `economic_peer_taxonomy.py`'s taxonomy/
  peer-selection rules, and the frozen FRE-7 activation criterion** — per this
  session's own FRE-7A/7B/7B.1/7B.2 work, explicitly not to be modified further
  without separate authorization.

### 1.11 Existing APIs/services/interfaces to reuse

`build_company_memory()`, `build_company_thesis()`, `company_thesis_360.as_of()`,
`build_evidence_chain()`, `reaction_check()`, `value_company()`/
`get_normalized_statement()`, `screen_by_flag()`/`screen_by_trend()`,
`watchlist.add_entry()`/`list_active()`, `sector_coverage.coverage_by_sector()`,
`compute_flags_for_ticker()` — all read-only (except `watchlist.py`'s own append-only
writes and `financial_health_flags.py`'s own conclusion writes), all directly
importable, none requiring modification for a new composing layer to consume them.

## 2. What can be reused

Nearly everything needed for Phase 1 (Company State), Phase 4 (Thesis), and Phase 6
(Evidence Graph) as specified in the new request **already exists and is real,
tested, production infrastructure** — not a gap. `company_memory_360.py` +
`company_thesis_360.py` + `entity_context.py` + `company_intelligence.py` together
cover the large majority of Phase 1's "Business/Financial condition/Corporate
events/Regulatory/Market behavior" sections. `evidence_graph.py` already implements
Phase 6. `company_thesis.py` already implements most of Phase 4 (bull/bear/base,
catalysts, risks, contradiction_note, missing_evidence).

## 3. What is missing (genuine new-build territory)

- **Phase 1's insider-activity section**: no insider-transaction table/module
  confirmed to exist cleanly (needs a closer look at the two `stage23`/`stage24`
  scripts before building this from scratch).
- **A unified KNOWN/UNKNOWN/CONFLICTING/STALE state object** spanning both existing
  profile axes (§1.7) — genuinely new, but a thin composition layer, not new data
  work.
- **Phase 2 (general change detection)**: `trend_classification.py` only covers
  financial-metric direction; a cross-category "what changed" detector (events,
  regulatory, insider, management) does not exist.
- **Phase 3 (Materiality Engine)**: does not exist in any form. `impact_assessments`
  has category/direction/explanation but no LOW/MEDIUM/HIGH/CRITICAL magnitude
  classification.
- **Phase 5 (Signal Synthesis)**: does not exist — see §6, this is where the
  architectural conflict lives.
- **Phase 7 (multi-dimensional Confidence Engine)**: the pieces exist
  (`confidence_tier`, `company_thesis.confidence`, `TriangulatedValuation.
  valuation_confidence`) but are not unified into the 6 named dimensions.
- **Phases 8-13 (Recommendation Engine, Scorecard, Ranking Engine, Market-Wide
  Intelligence, Portfolio Decision Support, Automated Report)**: do not exist as
  specified — Phase 13 is the closest to already-covered (`company_research_dossier.py`
  is ~70% of it), Phase 10 is where the sharpest conflict with existing charter
  lives (§6).

## 4. What must not be changed

Everything in §1.10, plus: no new write path into `alpha_engine.py`/the quant
registry (explicitly, repeatedly forbidden — "the single hard boundary this entire
platform has maintained since Phase A"); no numeric composite score presented as
if it were statistically validated; no fabricated peer/WACC/debt/cash/EPS input
(unchanged from every prior FRE-7 stage this session).

## 5. Proposed architecture (pending §6's resolution)

A new, additive `src/ngxrot/fre/` module family, composing (never modifying)
existing modules:

```
company_state.py       -- Phase 1: composes company_intelligence + company_memory_360
                           + entity_context (+ insider module, once located/built)
change_detection.py    -- Phase 2: diffs two company_state snapshots
materiality.py          -- Phase 3: deterministic LOW/MEDIUM/HIGH/CRITICAL rules
signal_synthesis.py     -- Phase 5: per-category direction/strength/reliability,
                           conflict-preserving (NOT a blended score)
confidence_engine.py    -- Phase 7: 6 named dimensions, each traceable to a real input
recommendation_engine.py -- Phase 8: BUY/WATCH/HOLD/AVOID/INSUFFICIENT_DATA --
                           SCOPE PENDING §6
scorecard.py            -- Phase 9: machine-readable structure over the above
ranking_engine.py       -- Phase 10 -- SCOPE PENDING §6 (direct conflict, see below)
market_intelligence.py  -- Phase 11: sector/market-wide aggregation
portfolio_decision_support.py -- Phase 12: composes scorecard + watchlist + portfolio_memory
company_research_report.py -- Phase 13: extends company_research_dossier.py, not a rebuild
```

Each new module: read-only against `ngx.sqlite` (no new write path except possibly
a `decision_scorecards` table for Phase 9's own audit trail, itself additive), its
own `scripts/fre/test_*.py`, own docstring stating exactly which existing modules
it composes and confirming (via import-line check, the established pattern) that
it does not import from or get imported by the frozen accounting core or the quant
registry track.

## 6. THE CRITICAL RISK: Phase 5/8/10 conflict with an existing, explicit, dated charter gate

This is the one finding this audit treats as blocking further autonomous progress.

**`docs/fre/09_portfolio_reasoning.md`** (frozen, part of the tagged
`fre-architecture-baseline-2026-08-01`) explicitly designed and then **rejected** a
"shadow ranking" capability:

> *"Build a 'shadow ranking' that computes scores but is labeled experimental/
> non-live.' Rejected — a shadow ranking is still a ranking; producing a scored,
> ordered list creates exactly the same 'indistinguishable from ranking on noise'
> problem `docs/PLATFORM_ARCHITECTURE.md` already names, regardless of a
> disclaimer label."*

Its own Tier-2 table gates **ranking, position sizing, conviction-weighted
allocation, portfolio-level risk modeling, and rotation** — the exact capabilities
this new task's Phase 5 (combined directional signal), Phase 8 (BUY/AVOID
recommendation), and Phase 10 (cross-sectional Ranking Engine: "Highest Conviction,"
"Most Attractive Opportunity," "Needs More Research") ask for — behind: **"≥2
validated independent factors (currently 1: H-011/Size) — a Quant Engine research
outcome, never to be shortcut by FRE/FSI."**

This exact sentence is repeated, dated 2026-08-02, in
**`docs/fre_runs/OWNER_DECISION_BACKLOG_2026-08-02.md`** under "Architecture-revision
authorizations (guardrail-gated, not data-gated)":

> *Part 9 Tier 2 (ranking, position sizing, conviction-weighted allocation,
> portfolio-level risk, rotation) | ≥2 validated independent factors (currently 1:
> H-011/Size) — a Quant Engine research outcome, never to be shortcut by FRE/FSI*

This is not a stale or ambiguous note — it is a standing, explicit, cross-referenced
architectural decision, reinforced independently in at least six modules
(`screening.py`, `watchlist.py`, `sector_coverage.py`, `correlation_notes.py`,
`portfolio_memory.py`, `company_thesis.py`/`company_thesis_360.py`, per the audit),
each of which deliberately chose an unordered/categorical output specifically to
avoid crossing this line.

**Why this matters for the new task specifically**: the new task's own governance
section explicitly forbids "silently alter frozen methodologies" and "weaken gates
to obtain positive results," and its own execution rules say to "Stop only at
genuine governance gates or when a material architectural decision requires owner
authorization." Building Phase 5's combined signal, Phase 8's BUY/AVOID
recommendation labels, and especially Phase 10's cross-sectional ranking
("deserves the most research attention," ranked by "thesis strength... risk-adjusted
attractiveness... confidence") **is** the exact capability this platform's own
charter named and refused to build until a second validated quant factor exists.
Building it now, even carefully, even with every disclosure/evidence-chain safeguard
this new task also asks for, would cross a line this codebase's own governing
documents drew on purpose.

This could be read three ways, and only the owner can say which is intended:

1. **The new instructions are a deliberate, explicit supersession** — the owner
   (via this new message) is knowingly authorizing exactly the capability
   `OWNER_DECISION_BACKLOG_2026-08-02.md` said "never to be shortcut," because the
   evidentiary/governance rigor demanded this time (mandatory evidence chains,
   INSUFFICIENT_DATA as a first-class output, no fabrication, multi-dimensional
   confidence) is different in kind from the "shadow ranking" that was rejected —
   a genuinely qualitative, evidence-graded BUY/WATCH/HOLD/AVOID call is arguably
   not the same thing as "ranking by expected risk-adjusted return."
2. **Scope should be restricted** to what doesn't cross the gate: build Phases
   1-4, 6-7, 9 (a scorecard is not inherently a ranking), 11-13 in full, but keep
   Phase 5's signal synthesis strictly qualitative/conflict-preserving (never
   collapsed into one BUY/AVOID call) and skip Phase 8's recommendation vocabulary
   and Phase 10's cross-sectional ranking entirely until the gate's own stated
   unlock condition (a second validated factor) is met.
3. **Pause entirely** on Phases 5/8/10 pending a formal architecture-revision
   authorization matching the process `docs/fre/00_fre_master_index.md` itself
   names, and build only what's unambiguously safe (Phases 1-4, 6-7, 9-13 minus
   ranking) in the meantime.

## 7. Dependencies

Phase 1 depends on locating/evaluating the insider-dealing scripts (§3). Phases
2-13 each depend on Phase 1's state object being real and tested first, per the
task's own pipeline (`RAW DATA → ... → COMPANY STATE → CHANGE DETECTION → ...`).
Phase 9's scorecard and Phase 13's report both depend on Phases 1-8 being real
first (no scorecard field should be populated before its underlying computation
exists).

## 8. Risks

- **The §6 conflict**, if resolved by proceeding without explicit owner
  confirmation, risks silently crossing a deliberate charter boundary — exactly
  what this task's own governance rules forbid.
- **Insider-activity data**: unclear real coverage; risk of the Phase 1 section
  being mostly `UNKNOWN` (which is the correct, honest output if so, not a bug to
  work around).
- **Valuation coverage remains thin** (7/24 P/E-ready): any recommendation/thesis
  work must continue to honor `VALUATION_CONFIDENCE = LOW` rather than pushing
  through a low-confidence number, exactly as this task's own Core Principle
  requires — consistent with, not a new risk beyond, this session's own FRE-7
  findings.
- **Scope size**: Phases 1-13 as fully specified are a multi-week build in a
  mature codebase of this size; a single session should scope honestly to what is
  actually built and tested (per the task's own "do not claim completion" rule),
  not attempt superficial coverage of all 13 phases.
