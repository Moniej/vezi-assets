# Fund Alpha — NGX Investment Operating System

**Fund Alpha is an Investment Operating System (Investment OS), not an alpha
model.** The product is the **intelligence infrastructure**: a continuously
updated, evidence-grounded, provenance-tracked representation of the
Nigerian equity investment universe, built from real documents and real
prices, before anyone asks it a question. The OS does not need to know the
alpha in advance — its job is to organize the universe so that different
investment processes (a quant hypothesis engine, an AI analyst layer, a
future portfolio-construction or risk engine) can be built *on top of it*.

```
NGX / Company Information
        │
        ▼
Data Acquisition → Document Store → Extraction Layer
        │
        ▼
Facts / Events / Factors / Relationships
        │
        ▼
Evidence / Grounding Layer → Self-Critique / Validation
        │
        ▼
       Investment Intelligence
        │
   ┌────┴─────────────────┐
   ▼                       ▼
Decision Engines      Human Investor
(Alpha Engine, FRE,
 future portfolio/risk)
```

(Repository name `ngx-rotation` is historical — the scope outgrew it long
before the scope outgrew "alpha engine" too.)

**Read [`docs/INVESTMENT_OS_SPECIFICATION.md`](docs/INVESTMENT_OS_SPECIFICATION.md)
first in a fresh context** — the complete Investment OS handoff spec:
current architecture layer-by-layer, verified numbers, what's built vs.
missing, priority order, and explicit "do not do this" guidance for any AI
picking up this project.

**This is a research/infrastructure tool. Nothing it outputs is investment
advice.**

## Today's two consumers of the OS

The OS currently has two things running on top of it. Neither one *is* the
product; both are proof the infrastructure is usable.

1. **Alpha Engine** (`src/ngxrot/` quant core) — the pre-registered
   hypothesis-testing track. **18 hypotheses tested: 1 confirmed (H-011,
   Size — capacity-constrained), 15 rejected, 1 abandoned untested (H-002),
   1 in first-look testing (H-019, news-events, currently negative).** Zero
   validated, capacity-feasible, deployable strategies exist today — see
   `docs/FACTOR_REGISTRY.md` for the full evidence trail. This track owns
   the backtest engine, the immutable experiment registry, and the
   placebo/Holm-BH/walk-forward validation gauntlet.
2. **FRE — Financial Reasoning Engine** (`src/ngxrot/fre/`,
   `src/ngxrot/documents/`) — the AI document-intelligence track. Reads real
   NGX filings, extracts facts with a self-critiquing LLM pipeline, and
   composes company intelligence. Its own Phase 19 self-assessment
   classifies it honestly as an **"Analyst Research Assistant, not
   institutional infrastructure"**: strong evidence grounding (100% citation
   integrity, 100% grounding agreement on the last live validation run) and
   PIT discipline, but structurally zero coverage of business description,
   revenue segments, management, or ownership for every ticker, and a
   valuation engine that is architecturally ready but deliberately not
   activated pending owner sign-off. Full detail:
   `docs/fre_runs/decision_intelligence_phase19_real_world_assessment.md`.

Both consumers read the *same* underlying OS layers below — data
acquisition, the document store, evidence/grounding, confidence ceilings —
rather than each maintaining its own. That shared foundation is the actual
asset. A third consumer (portfolio construction, risk, or any future
decision process) is additive, not a redesign, as long as it reads the OS
the same way.

## Status

| Layer | State |
|-------|-------|
| 1. Data architecture | ✅ Schema + bitemporal PIT layer, tested |
| 1b. Data Abstraction Layer | ✅ Provider interface + validating ingest + confidence scoring; CSV, Synthetic & ngxpulse providers live, remaining web providers stubbed pending per-source implementation |
| 1c. Research governance | ✅ Immutable experiment registry (SQL-trigger enforced), TOML-config-driven runner with holdout guard, hypothesis ledger (no-delete) |
| Document/evidence layer (FRE) | ✅ Document processing pipeline, deterministic + LLM extraction, evidence grounding, citation integrity, evidence ranking (trust tiers), conflict detection, self-critique gate — all engineering-tested; honest coverage/confidence-ceiling scoring exposes what's still missing per ticker |
| Research OS (`src/ngxrot/research_*.py`) | ✅ Read-only PIT dataset access, generic (non-alpha-shaped) experiment framework, instrument-identity/rename-chain resolution, lineage tracing — infrastructure under both consumers, does not touch the alpha registry |
| Alpha Engine (quant consumer) | ✅ `engine_full` cost/capacity-aware backtester; 18 hypotheses tested, 1 confirmed (capacity-constrained), architecture frozen V1 |
| FRE (AI-analyst consumer) | ✅ Phases A–19 built and tested; honestly self-assessed as partial coverage — see Phase 19 report |
| Portfolio construction / risk / other future consumers | ⛔ Correctly gated — needs ≥2 independent validated alpha sources (Alpha Engine) or an owner-approved mandate (any new consumer); do not scaffold early |

> **Before starting any new NGX momentum work, read
> [`reports/post_mortem_H-001.md`](reports/post_mortem_H-001.md) §8** — it
> states what has been ruled out, what is open, and what was never tested.

## The OS's job: completeness, not cleverness

The single most important thing the last research cycle found (FRE Phase 19,
Investment OS baseline audit) is that the current weak point is **coverage,
not hallucination**. The system is unusually honest about what it doesn't
know — confidence ceilings are mechanically capped by measured information
coverage (e.g. 0.60 coverage → 0.225 confidence ceiling, never the reverse)
— and evidence grounding/citation integrity have tested at 100% on the most
recent live validation run. **Correction (2026-08-11)**: the Phase 19 report's
"no financial-statements dataset exists platform-wide" claim was traced to a
hardcoded `False` in `coverage_assessment.py`, not real absence — real
financial-statement extraction (revenue/net_profit/assets/liabilities/
equity/cash-flow, FSI Phases 1-3) already exists for a subset of tickers,
confirmed directly against the database and fixed the same day (see
`HANDOFF.md`). The bottleneck is that the OS does not yet have comprehensive
secondary-source, entity-relationship, real corporate-action data (the
schema exists; the table holds synthetic fixtures), or temporal/
point-in-time infrastructure beyond financials — and financial-statement
extraction, while real, is still narrow (needs to reach more tickers).
**Priority is closing those gaps, not adding more reasoning on top of an
incomplete world model.** See `docs/INVESTMENT_OS_BASELINE_AUDIT.md` for
the maturity scorecard (predates this correction).

## Layout

```
schema/schema.sql            # SQLite DDL — PIT views, confidence columns, documents/facts/evidence
schema/seed_reference.sql    # index registry + ASSUMED fee schedule
src/ngxrot/db.py             # init + bitemporal PIT readers (sim_date × vintage × min_confidence)
src/ngxrot/contracts.py      # dataset contracts every provider must emit
src/ngxrot/ingest.py         # sole write path: validate -> stamp lineage/confidence -> DB
src/ngxrot/providers/        # DAL: base.py, csv_provider.py, synthetic.py, ngxpulse.py, web_stubs.py
src/ngxrot/documents/        # FRE document pipeline: extract, grounding, self-critique, reasoning_engine
src/ngxrot/fre/              # FRE consumer: company state, coverage, confidence, valuation (gated)
src/ngxrot/research_*.py     # Research OS: PIT datasets, generic experiment framework, lineage
scripts/phase1_smoke_test.py # builds DB, proves 3 lookahead traps are blocked
scripts/dal_demo.py          # end-to-end DAL demo incl. reject handling & confidence floors
docs/PHASE1_DATA_GAPS.md     # data questions (answered), assumptions, feasibility probes
docs/FUND_ALPHA_CHARTER.md   # governing document — OS-first framing, consumer honesty constraints
data/ngx.sqlite              # generated (git-ignore if repo is created)
```

## Run

```
python scripts/phase1_smoke_test.py                     # PIT lookahead traps
python scripts/dal_demo.py                               # DAL end-to-end
python scripts/run_experiment.py configs/<cfg>.toml      # run experiment(s) — Alpha Engine consumer
python scripts/ledger_cli.py [list|add|status|log]       # research ledger
python scripts/engine_status.py                          # Alpha Engine's current recommendations
```

Requires Python 3.10+ (3.11+ for tomllib) and pandas. Launch via
PowerShell (`python -u`), not Git Bash.

## Governance

- **Experiment registry** (`data/registry.sqlite` + `experiments/*.json`):
  every run inserts one immutable record (UPDATE/DELETE blocked by SQL
  triggers) containing the full resolved config, code fingerprint, data
  provenance (provider/confidence/vintage), all parameters, metrics, and
  validation flags. Reruns are new rows, never edits.
- **Config-driven**: no research parameter lives in source code. An
  experiment is a TOML file; an optional `[sweep]` table expands into a grid,
  each cell its own experiment. `stage="development"` runs are refused (not
  clamped) if they touch dates past `validation.holdout_start`.
- **Research ledger**: hypotheses with status lifecycle
  untested→testing→confirmed/rejected; deletions blocked at SQL level,
  resolution requires a written conclusion, every status change logged.
- **Self-critique gate (FRE)**: every AI-drafted implication must clear 8
  adversarial questions before any downstream consumer can read it; a
  `fail` blocks the row (`blocked_by_self_critique`), excluded everywhere.
- Synthetic (confidence-0.0) data forces `counts_as_evidence: false` in the
  experiment record regardless of how good the numbers look.

## Data Abstraction Layer

Every source is a `DataProvider` (`src/ngxrot/providers/base.py`) declaring
capabilities out of {index_levels, equity_prices, corporate_actions,
index_membership, events} and emitting DataFrames matching the contracts in
`contracts.py`. `ingest.ingest()` is the only write path: it validates rows
against the contract (rejecting, never repairing), blocks future-dated
observations, auto-registers skeleton reference rows, and stamps every
accepted row with `source_id`, `confidence`, `as_of_date`. Adding a premium
vendor later = one new provider class; every OS consumer is untouched.

Confidence convention: 0.9 exchange-official · 0.5 aggregator · 0.4 manual ·
0.3 archive reconstruction · **0.0 synthetic (may exercise machinery, may
never feed a research conclusion)**. PIT readers accept `min_confidence`.

## Design invariants (all layers, all consumers must respect these)

1. Consumers read data **only** through the PIT helpers in `ngxrot.db`
   (`*_asof(knowledge_date)`) or the Research OS dataset layer, never raw
   tables.
2. Every observational row has `source_id` + `as_of_date`; corrections append,
   never overwrite.
3. Information is usable from its **announcement** date, not its effective date.
4. Undocumented history is excluded, never backfilled from current data.
5. All cost/fee rates are effective-dated and overridable; results computed on
   `confidence='assumed'` rates are watermarked as such.
6. Every AI-generated fact carries evidence back to a source document; an
   implication with no grounded citation is not a fact, it's a draft.
7. Confidence never exceeds what measured information coverage justifies —
   a confidence ceiling is a first-class output, not a footnote.
