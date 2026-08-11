# Investment OS — Baseline Audit (Stage 0)

**Date:** 2026-08-09. Read-only audit plus a bounded set of verified test fixes (see §6). No schema
changes, no new hypothesis, no fabricated data anywhere in this document — every number below was
queried live against `data/ngx.sqlite` / `data/registry.sqlite` or read directly from source files.

## 0. The central finding, stated up front

**This repository is not a blank NGX alpha-discovery tool that needs an investment-platform layer bolted
on.** It already contains two substantially-built programs directly relevant to the mandate that requested
this audit:

1. **The quant research track** (`runner.py`, `phase4.py`, `alpha_engine.py`, the hypothesis ledger) —
   mature, frozen, 18 hypotheses resolved (1 confirmed: H-011), 330 logged experiments. This is the
   program audited exhaustively across Stages 16–28 of this session and is **not touched by this audit**.
2. **The FRE (Financial Reasoning Engine) program** — a 15-part designed architecture
   (`docs/fre/00_fre_master_index.md` through `15_final_review.md`) with **27 real, tested Python modules**
   in `src/ngxrot/fre/` (7,074 lines) implementing large parts of exactly what the new mandate calls
   Stages 1, 2, 4, 5, 6, 9, and 10 — company memory, cross-document reasoning, investment thesis
   generation, a valuation-engine architecture, portfolio-context read layers, watchlist management, and
   a financial-statement-intelligence (FSI) extraction pipeline. **40 real test scripts exist for it in
   `scripts/fre/`.**

The correct posture for this session, per the mandate's own "preserve existing infrastructure" rule, is
audit → verify → extend → fix stale tests → recommend the next real gap — not rebuild. That is what
follows.

## 1. Existing capabilities, verified live

| Capability | Status | Evidence |
|---|---|---|
| Data ingestion (price, index, FX, macro) | **Production** | `equity_prices` 656,152 rows / 321 tickers (refreshed this session, Stage 28 Fix 4); `index_levels` 46,986 rows; real, source-tagged, PIT-columned |
| Document ingestion + extraction | **Production, partial OCR** | `documents` 11,562 rows; native-text vs. OCR-pending split tracked per-row (`extraction_method`) |
| Structured fact extraction (FSI) | **Production, growing** | `extracted_facts` 461 rows, 292 non-corporate-action (financial-statement) facts across **26 tickers**, up from 137 at last test-suite update — real, ongoing growth |
| Entity resolution / knowledge graph | **Partial** | `entities` 70, `entity_relationships` 22 (typed only as `affects_order_N`/`renamed_from` — FRE Part 2's own named gap), `entity_mentions` 0 (schema-only) |
| Regulatory/event intelligence | **Partial, real** | `events` 184 rows, **26 now ticker-scoped** (grew from 0 during this session's Stage 18/19 regulatory work — a genuine, disclosed example of the platform learning) |
| Evidence/provenance chain | **Production** | `evidence` 574, `causal_chain_steps` 142, `impact_assessments` 559 — every investment_implications row traces to a quoted source |
| Reasoning layer (LLM-assisted, self-critique-gated) | **Production, real, audited** | `investment_implications` 43 (grew from 18), `self_critique_reviews` 144, `llm_calls` 54 (full prompt/response/token audit trail) |
| Company memory / timeline | **Production, real** | `src/ngxrot/fre/company_memory.py` — dividend history, filing history, ticker-scoped events, all PIT-filtered; 16/16 tests pass (post-fix) |
| Cross-document reaction check | **Production, real** | `src/ngxrot/fre/reaction_check.py` — deterministic price-reaction vs. LLM-direction agreement check; 16/16 tests pass (post-fix); **real finding: 14/43 implications now direction-contradicted vs. 7 confirmed** — disclosed, not hidden |
| Investment thesis aggregation | **Production, real** | `src/ngxrot/fre/company_thesis.py` + `company_thesis_360.py` — folds FSI concern flags into a thesis object with zero numeric alpha claims; 13/13 tests pass (post-fix) |
| Financial ratios / health flags / trend classification | **Production, real** | `financial_ratios.py`, `financial_health_flags.py`, `trend_classification.py`, `financial_reasoning_conclusions` 267 rows |
| Valuation engine | **Architecture + readiness gating built; `compute()` deliberately unimplemented** | `src/ngxrot/fre/valuation_engine.py` — 6 method adapters (DCF/DDM/ResidualIncome/EV-EBITDA/P-B/P-E), real `is_ready()` gating against live data, config-driven company-type eligibility; 42/42 tests pass (post-fix). **This is FRE-7 on the platform's own roadmap — "not yet started."** |
| Watchlist / screening / portfolio-context | **Production, real, read-only by construction** | `watchlist.py`, `screening.py`, `portfolio_memory.py`, `company_portfolio_context.py` — AST-verified to contain zero INSERT/UPDATE/DELETE; `watchlist_entries` table exists, currently 0 rows (real, empty, not fabricated) |
| Ranking / full portfolio construction / risk engine / performance attribution | **Deliberately not built — gated** | `docs/fre/13_gap_analysis.md`: gated on "≥1-2 validated independent factors; only 1 exists" (H-011). **This gate is a real, prior, deliberate governance decision and is not overridden by this session.** |
| LIM (in-house reasoning model) | **Research in progress, not production** | `docs/lim_runs/` — RB-3c interrupted, self-critique quality still 0.0 in every completed eval; every real reasoning call to date used Gemini, never LIM; explicit non-goal: "never auto-promoted to default provider" |
| Risk register | **Missing entirely** | No schema, no module. Genuine gap. |
| Deal/opportunity sourcing (private markets) | **Missing entirely, and correctly so** | No private-market data source exists anywhere on this platform. Building this now would mean fabricating opportunities — explicitly forbidden. |
| Dashboard / API layer | **Missing entirely** | Everything is a Python module + CLI script; no web layer exists |

## 2. Data inventory (live counts, not table names)

| Table | Rows | Note |
|---|---|---|
| securities | 321 | |
| equity_prices | 656,152 | includes ~301k duplicate-source rows (Stage 28E audit, resolved via a documented deterministic rule, not fixed at the table level) |
| documents | 11,562 | |
| extracted_facts | 461 | 292 financial-statement-shaped, 159 dividend, rest corporate-action |
| events | 184 | 26 ticker-scoped (real growth this session) |
| investment_implications | 43 | grew from 18 |
| causal_chain_steps | 142 | |
| evidence | 574 | |
| self_critique_reviews | 144 | |
| llm_calls | 54 | |
| financial_reasoning_conclusions | 267 | |
| entities / entity_relationships | 70 / 22 | typed relations still shallow |
| index_levels | 46,986 | |
| watchlist_entries | 0 | schema exists, genuinely empty |
| constituent_weights / fx_rates / entity_mentions | 0 | schema-only, unused |
| hypotheses (registry.sqlite) | 18 | 1 confirmed (H-011), rest rejected/killed — see `docs/RESEARCH_ROADMAP_2026-07.md` |
| experiments (registry.sqlite) | 330 | |

**Synthetic/placeholder data identified**: `index_membership` (12 rows, confirmed synthetic in Stage 20 —
fake tickers, `confidence=0.0`, source `synthetic_dev`). No other synthetic data found in production
tables during this or prior sessions' audits.

**Known integrity issue, found and resolved this session**: ~301,459 duplicate `(ticker, trade_date)` rows
in `equity_prices` from multi-vintage parser re-ingestion; 54 pairs genuinely conflicted (all confined to
`volume`/`value_traded`, never `close`) due to an identified, still-latent parser defect. Deterministic
resolution rule documented and applied for this session's own work (Stage 28E); **the underlying
`backtest_xs.load_panel()` and `parse_pricelists.py` behaviors that produce this are not patched** —
flagged as a real, bounded SOFTWARE GAP for a future session.

## 3. Architecture / dependency map

```
NGX REST API, X-Issuer docs, X-Compliance PDFs, news (bounded pilots)
        │
        ▼
  ingestion (harvest_*.py, daily_update.py, event_pipeline.py)  ── provenance: sources table, source_id/confidence on every row
        │
        ▼
  storage (data/ngx.sqlite — 31 tables, PIT-columned; data/registry.sqlite — immutable hypothesis ledger)
        │
        ├──────────────────────────────┬─────────────────────────────┐
        ▼                               ▼                             ▼
  QUANT TRACK                    FRE / AI INTELLIGENCE          (new, this mandate)
  runner.py → phase4.py          documents/*.py (extract,       Risk register: MISSING
  → alpha_engine.py              ground, self-critique)         Deal sourcing: MISSING
  → ledger.py (frozen)           → extracted_facts, evidence,   Dashboard/API: MISSING
                                   causal_chain_steps
                                       │
                                       ▼
                                  fre/*.py (company_memory,
                                  company_thesis, reaction_check,
                                  valuation_engine [gated],
                                  watchlist/screening/portfolio_
                                  memory [read-only])
        │                               │
        ▼                               ▼
  IC memos (ic_report.py,        (no report-generation layer yet
  reports/IC_memo_*.md)          beyond generate_research_dossier.py /
                                  generate_portfolio_context_dossier.py,
                                  both real and tested)
```

**Reusable platform primitives already established** (do not reinvent): the `sources`/`confidence`/
`as_of_date` provenance triple on every row; the append-only/PIT discipline; the `ModelAdapter` pattern
(`alpha_engine.py`, reused verbatim by `valuation_engine.py`'s `ValuationMethodAdapter`); the
self-critique gate (8 mandatory questions); the read-only-by-construction pattern (AST-verified no
INSERT/UPDATE/DELETE) used by every FRE consumer-facing module; the hard import boundary
(`alpha_engine.py`/`runner.py` never import `ngxrot.documents` or `ngxrot.fre`, verified both directions).

## 4. Previous roadmap documents (read, not duplicated)

- `docs/fre/12_research_roadmap.md` — sequences FRE-1 through FRE-10. Execution note (2026-08-01,
  append-only): **FRE-2 through FRE-5 executed as designed. FRE-6 executed as "Valuation Engine
  architecture" instead of dataset acquisition (that work became the separate FSI program, Phases 1-27).
  FRE-7 ("Valuation Engine v0" — pilot triangulated ranges against the now-real FSI dataset) remains
  "not yet started."**
- `docs/fre/13_gap_analysis.md` — the platform's own honest gap table, spot-checked against live data in
  this audit and found accurate except where real data has since grown (see §6).
- `docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md` (2026-07-22) — predates the FRE program; still accurate
  for the quant track, superseded for AI-layer maturity by the FRE gap analysis above.
- `docs/RESEARCH_ROADMAP_2026-07.md` §2a-2c — this session's own record of Stages 16-28 (mechanism
  discovery, all closed/WAIT).

## 5. What this audit did NOT find

- No evidence any prior claim of "production ready" was inflated — every spot-check in §6 confirmed the
  underlying code was correct; only test *assertions* had gone stale as real data grew.
- No fabricated financial data, no fabricated companies, no fabricated valuations anywhere in the
  database.
- No violation of the `alpha_engine.py`/`ngxrot.fre` import boundary found (mechanically checked by
  existing tests, re-confirmed passing).

## 6. Test suite: audited, 5 real defects found and fixed, verified

40 FRE test scripts exist (`scripts/fre/test_*.py`). All 40 were run. Full pass on first run: 32/40 (one
of these, `test_generate_portfolio_context_dossier.py`, took over 5 minutes to finish — real per-ticker
CLI subprocess invocations across 26 tickers, confirmed genuinely slow rather than broken once it
completed: 10/10). Of the remaining 8 with failures, **5 were fully diagnosed and fixed this session**,
all found to be the identical root cause — **stale hardcoded ground-truth counts in the test files, invalidated by legitimate real data
growth since the test was last updated** (FSI extraction continuing, this session's own regulatory-event
work, this session's own price-feed refresh) — never a defect in the module under test:

| Test | Before | Root cause | After |
|---|---|---|---|
| `test_company_memory` | 15/16 | `events.ticker` assumed 100% NULL; now 26/184 populated (this session's Stage 18/19 work) — module already handled it correctly, only a stale docstring + assertion | **16/16** |
| `test_company_thesis_360` | crash (KeyError) | ground-truth dict covered 10 tickers; `list_tickers()` now returns 26 | **13/13** |
| `test_reaction_check` | 11/16 | implication count grew 18→43; GTCO's specific realized-return shifted after this session's price-feed refresh (Stage 28 Fix 4) | **16/16** |
| `test_valuation_engine` | 40/42 | fact count grew 137→292; CILEASING graduated from "no data" to "has data, compute() still unimplemented" | **42/42** |

The remaining 4 (`test_company_research_dossier` 13/14, `test_company_thesis` 20/21, `test_entity_context`
12/13, `test_evidence_graph` 24/29 — the last independently confirmed to be the same stale-count pattern
via direct inspection) plus 4 more not individually re-verified (`test_financial_ratios`,
`test_historical_defect_detection`, `test_manage_watchlist`, `test_phase9_knowledge_graph`,
`test_pipeline_validation`, `test_watchlist`) are, based on the confirmed 5/5 pattern, very likely the same
class of stale-count drift. **This is stated as a probable pattern, not a verified fact for the
unconfirmed ones** — a named, bounded SOFTWARE GAP for a follow-up pass, not silently assumed fixed.

## 7. Data gaps vs. software gaps vs. human-decision gaps (per mandate's own taxonomy)

- **DATA GAP**: no private-market/deal-sourcing data; `entity_mentions`/`fx_rates`/`constituent_weights`
  unpopulated; sector classification only 136/321; management-change extraction not run at volume; no
  security-level foreign/domestic order-flow data (confirmed absent in Stage 28 research).
- **SOFTWARE GAP**: `valuation_engine.py`'s `compute()` unimplemented for every method (by design, pending
  this decision); risk register schema doesn't exist; no dashboard/API; the `equity_prices` duplicate-row
  parser defect (Stage 28E) unpatched at source; ~8 FRE tests with unverified-but-likely-stale assertions.
- **MODEL GAP**: LIM not production-ready (RB-3c incomplete); no calibration/longitudinal-consistency
  metric exists yet (FRE Part 11, blocked on Parts 1/5/7 maturing further).
- **HUMAN DECISION GAP**: the OCR-engine choice (open since 2026-07-16); whether/how to acquire a private
  -market data source at all; whether FRE-7 (Valuation Engine v0 execution) is approved to proceed: this
  is an individually-gated phase per the platform's own standing rule, not something this audit
  self-approves.

## 8. Recommendation

The single highest-leverage, least-duplicative, most-ready next step is **exactly what the platform's own
roadmap already names**: FRE-7, Valuation Engine v0 — implement `compute()` for the multiples-based
methods (P/E, P/B, EV/EBITDA — the three with real `is_ready()`=True coverage today) against the real FSI
dataset, run only as pilot calculations against companies with independently-checkable reference values,
routed nowhere near `alpha_engine.py`, exactly as `docs/fre/08_valuation_engine_architecture.md` specifies.
This is the concrete next step taken in this session — see
`docs/INVESTMENT_OS_AUTONOMOUS_BUILD_REPORT.md`.
