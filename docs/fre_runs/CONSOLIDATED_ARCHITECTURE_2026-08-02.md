# Fund Alpha / NGX Platform — Consolidated Architecture (v1.0)

*Frozen as the stable production baseline, 2026-08-02 — **v1.0**, the
platform's first versioned release point (tags
`platform-baseline-2026-08-02-stable` and `v1.0`, same commit). This
document describes
the complete implemented system as of this date across every
subsystem: Quant Engine, AI Intelligence Layer, Financial Reasoning
Engine (FRE), Financial Statement Intelligence (FSI), Local
Intelligence Model (LIM). It supersedes no prior architecture
document — each subsystem's own design docs remain the authoritative
reference for that subsystem's own history and rationale; this
document's job is to describe how they now fit together as one
system, in one place.*

## 1. What this platform is

A research-grade, long-only sector-rotation and single-stock research
platform for the Nigerian Exchange (NGX) — not a general finance
assistant, not multi-exchange (yet), and not an execution system.
Every layer obeys the same charter: **never invent alpha, never
fabricate data, unknown stays unknown, no downstream module treats an
unvalidated signal as predictive.** The platform is organized as four
layers, each with its own gate for what it is allowed to claim:

1. **Quant Engine** — the original, frozen backtesting/factor-
   validation core. Speaks only in pre-registered hypotheses,
   validated factors, and disclosed rejections.
2. **AI Intelligence Layer / Company Intelligence** — structured,
   evidence-cited company/document intelligence. Speaks only from
   data that actually exists; explicitly discloses what it cannot
   say yet.
3. **Financial Reasoning Engine (FRE) / Financial Statement
   Intelligence (FSI)** — deterministic financial-statement reasoning
   and portfolio-adjacent research tooling (screening, watchlists,
   sector coverage) built on top of extracted filing facts. Tier-1
   (research/advisory) only; Tier-2 (ranking/sizing/risk) remains
   gated behind the Quant Engine's own validated-factor precondition.
4. **Local Intelligence Model (LIM)** — the (partially built)
   fine-tuned local model intended to eventually power reasoning
   generation; currently blocked on an owner checkpoint decision.

## 2. Quant Engine (pre-existing, unchanged by this program)

- **Core files**: `alpha_engine.py` (MODEL_ADAPTERS registry, live
  recommendations), `runner.py`, `backtest_xs.py`/`backtest_lite.py`,
  `registry.py` (SQLite-backed experiment ledger), `signal.py`,
  `universe.py` (IRU membership rules), `costs.py`, `stats.py`.
- **Governance**: every hypothesis is pre-registered
  (`docs/PREREG_H-00N.md`), tested against placebo/statistical-power
  gates, and recorded in `docs/FACTOR_REGISTRY.md` as `confirmed` or
  `rejected` — never silently dropped. **H-011 (Size) is the one
  confirmed factor** as of this writing; H-001/H-006/H-007/H-008/
  H-009/H-010 are rejected (real, disclosed negative results).
  Portfolio Construction requires ≥2 validated independent factors —
  currently 1/2, so Portfolio Construction and Risk Engine remain
  correctly gated, unchanged, for the entire duration of this program.
- **Hard boundary, maintained since Phase A of the AI Intelligence
  Layer and never crossed**: no import of `ngxrot.documents`/
  `ngxrot.fre` may ever appear in `alpha_engine.py`/`runner.py`, and
  no write path exists from either the AI Intelligence Layer or FRE/
  FSI back into `registry.py` or `alpha_engine.py`. Every FRE/FSI
  module that reads the live sleeve (`portfolio_memory.py`, Phase 17)
  does so read-only, verified via AST inspection.

## 3. AI Intelligence Layer (`ngxrot.documents`, `company_intelligence.py`)

Unlocked 2026-07-22 by H-011 reaching `confirmed` status (the
platform's Year-1 exit condition). Pipeline:
`Document → Entities → Events → Evidence → Reasoning → Investment
Implications`, with the 14-step reasoning chain (identify → extract →
recursive "why" → impact categories → duration/magnitude buckets →
confidence with mandatory uncertainty rationale → causal chain →
bull/bear/base case → action classification → cross-reference → self-
critique gate → structured output), a mandatory Step-14 self-critique
gate (a draft implication is unusable until it clears 8 fixed
adversarial questions, each paired with a mechanical check, not just
a model self-report), and full LLM-call audit logging (`llm_calls`
table). Provider: Gemini (`gemini-3.6-flash`, config-driven via
`configs/llm_provider.toml`), swapped in from an original Anthropic
design without touching the provider-agnostic reasoning pipeline.

`company_intelligence.py`'s `CompanyProfile` is the v0 scaffolding
consumer of this layer — every field is populated ONLY from evidence
that exists, with an explicit `unavailable` dict (reason-per-field)
for everything else. As of this baseline: `industry_exposure` (FSI
Phase 27) is the most recently activated field, populated for 136/320
tickers from NGX's own official sector classification (FSI Phase 23).
Financial Quality, Valuation (EPS/P.E. parser failed validation
twice), Growth, Competitive Position, Macro Sensitivity, and Ownership
remain disclosed as unavailable — no evidence-grade dataset exists for
any of them yet.

## 4. Financial Reasoning Engine (FRE) — the 15-part frozen design

`docs/fre/01_financial_ontology.md` through `15_final_review.md`
(frozen, tag `fre-architecture-baseline-2026-08-01`) is the original
architectural reference — retained unmodified as execution diverged
from its own roadmap table (see `docs/fre_runs/roadmap_review_
financial_statement_intelligence.md`). Built, individually gated:
**FRE-2** (Evidence Graph), **FRE-3** (Company Memory), **FRE-4**
(reaction-check — a deterministic market-reaction cross-check reusing
the Quant Engine's own event-study machinery, read-only), **FRE-5**
(Company Thesis, a pilot case study — bull/bear/base case, permanently
barred from ever outputting a numeric expected return), **FRE-6**
(Valuation Engine architecture — DCF/DDM/Residual Income/EV-EBITDA/PE/
PB adapters, sector-eligibility-typed; `compute()` unconditionally
raises `NotImplementedError` on every adapter, verified continuously
throughout this program; no valuation output has ever been produced).

Ten reasoning modes (causal, counterfactual, historical, trend,
comparative, sector, macro, valuation, uncertainty, portfolio), each
with its own guardrail (e.g., counterfactual reasoning is mechanically
appended with a disclaimer distinguishing it from the Quant Engine's
own statistically-rigorous placebo test), were designed in Part 4 and
realized via the reasoning pipeline described in §3.

## 5. Financial Statement Intelligence (FSI) — Phases 1-27

Inserted as a dedicated track when a roadmap review found the
financial-statements dataset FRE-6/Part 10 anticipated did not exist.
Built phase-by-phase (Phases 1-13 individually owner-approved; Phases
14-27 executed under the owner's standing continuous-execution
authorization, described in §6). Full narrative for every phase is in
`docs/fre_runs/`; the complete list is in
`docs/fre_runs/IMPLEMENTATION_TIMELINE_2026-08-02.md`. In summary, the
FSI track built, in dependency order:

- **Extraction** (Phases 1-2, 13): hand-verified revenue/net_profit/
  balance-sheet/cash-flow/EBITDA/EBIT facts for 10 real NGX tickers
  (137 facts total), native-text-only, no OCR, no vendor data.
- **Reasoning** (Phase 3): ratios, trend classifications, rule-based
  health flags (267 conclusions), fully provenance-linked to source
  facts.
- **Point-in-time memory and validation** (Phases 4-6): PIT-safe
  `as_of(ticker, date)` reads, a regression/consistency harness with
  3/3 historical-defect injection tests confirmed detectable.
- **Reporting and thesis integration** (Phases 7-8, 11-12): a
  deterministic Markdown report renderer, connection to the Investment
  Thesis Engine, a complete institutional research dossier, and the
  platform's first operational CLI.
- **Knowledge graph** (Phases 9-10, 19): entity/relationship
  population from the Quant Engine's own verified rename data, PIT-
  gated graph context composition, and qualitative correlation notes
  (currently an honest "no shared exposure known" for every real
  ticker pair, since no `macro_exposure` edges exist yet).
- **Part 9 (Portfolio Reasoning) Tier 1, built and CLI-operable in
  full** (Phases 14-15, 17-18, 20-22, 24-25): Screening, Portfolio-
  Memory Cross-Reference, Watchlist Persistence (append-only, the
  platform's first new table since Phase 3, and its first write-
  capable operator CLI), a Portfolio-Context-Annotated Research
  Dossier, and Sector-Coverage View — the fifth and last Tier-1
  capability, unblocked by Phase 23's data population.
- **Sector data and its two real consumers** (Phases 23, 26-27):
  `securities.sector_ngx` populated for 136/320 real securities from
  NGX's own official Daily Official List (an owner-authorized
  external reference-metadata source); wired into the Valuation
  Engine's company-type taxonomy (Phase 26) and Company Intelligence's
  Industry Exposure field (Phase 27) — both deterministic translation
  layers, zero inference, zero valuation/analytical output activated.
- **A regression fix and a documentation correction** (Phases 16, 19):
  a real, disclosed test-coverage regression (6 test files had
  silently stopped covering Phase 13's 5 new tickers) found and fixed;
  a factual error in this program's own Phase 17/18 documentation
  (understating Part 9's Tier-1 count) found and corrected.

**Part 9 Tier 1 is closed in full** as of this baseline — every
capability Part 9 names as buildable-now exists, tested, and
operator-reachable from the command line. Part 9 Tier 2 (ranking,
sizing, risk, rotation) remains correctly gated behind the Quant
Engine's own ≥2-validated-factor precondition, untouched throughout.

## 6. The continuous-execution program (Phases 14-27)

The owner temporarily suspended the per-phase approval checkpoint that
governed Phases 1-13, authorizing a pre-register → implement →
validate → document → commit/tag → auto-continue cycle. Every phase
in this range still followed the full lifecycle (gap analysis with
≥3 rejected alternatives, implementation, full regression + database-
integrity + immutability verification, implementation log, final
report, master-index update, git commit, annotated tag) — only the
per-phase pause was removed. The run reached three successive natural
stopping points (documented in `docs/fre_runs/
fsi_final_architecture_audit_2026-08-02.md`, now at Revision 3), each
time because no further phase satisfied all of "closes a real gap,"
"buildable internally today," and "does not violate a guardrail." Two
of those stopping points were followed by an owner decision that
genuinely unblocked further work (Phase 23's sector-data-source
authorization; Phases 26-27's explicit follow-on instructions) — the
third (after Phase 27) was accepted by the owner as the platform's
architecturally complete state within current constraints, and this
document is part of the close-out that decision requested.

## 7. Local Intelligence Model (LIM) — status, unchanged by this program

`docs/LIM_ARCHITECTURE.md` describes a planned fine-tuned local model
(Qwen3.x family) to eventually generate reasoning narratives locally
rather than via a hosted provider. Status as of this baseline:
`self_critique_quality` still 0.0 (never exercised for real), blocked
on an exact checkpoint/version decision — an owner decision this
program does not make. LIM's own evaluation/training scaffolding
(`ngxrot.lim`: `eval_dataset.py`, `eval_metrics.py`, `training.py`,
`audit.py`, etc.) exists and is real, but no training run or
evaluation against a real gold set has occurred.

## 8. Database (production `data/ngx.sqlite`)

31 tables as of this baseline (schema.sql, additive-only migrations
throughout — no table has ever been dropped or renamed). Every
migration was preceded by a full backup (`data/ngx.sqlite.pre_*`
files) and followed by an integrity/foreign-key check. Point-in-time
correctness is enforced on two independent axes throughout (`sim_date`
for market knowledge, `vintage`/filing-date for the platform's own
knowledge) — see `db.py`'s own module docstring for the canonical
statement of this discipline.

## 9. Guardrails enforced mechanically, not just documented, throughout

- **No hidden scoring/ranking**: every cross-ticker function
  (Screening, Watchlist's `list_active()`, Sector-Coverage View) is
  checked, via `inspect.signature()` and dataclass-field introspection,
  to carry no `limit`/`sort_by`/`rank_by`/`score`/`weight` parameter or
  field, and to return results in alphabetical order only.
- **No import-boundary violations**: AST-based import inspection
  (never substring matching, after a real false-positive taught this
  lesson in Phase 15) confirms FRE/FSI modules never import
  `alpha_engine.py`/`runner.py`, and are never imported by them.
- **No write path where none is claimed**: AST inspection confirms the
  absence of `INSERT`/`UPDATE`/`DELETE` SQL string literals in every
  module documented as read-only.
- **No fabricated data**: every external-data introduction (NGX's own
  sector classification, Phase 23) was verified against a genuine
  primary source before use, with full retrieval provenance recorded;
  unverifiable values are left `NULL`, disclosed, never guessed.
