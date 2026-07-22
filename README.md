# Fund Alpha — NGX Alpha Engine & Research Platform

The product is the **alpha engine** ([charter](docs/FUND_ALPHA_CHARTER.md)):
a decision layer that answers buy/sell/enter/exit/size/risk questions from
**validated models only**, with provenance to immutable experiment records.
Run `python scripts/engine_status.py` for its current recommendations and
pipeline. Hierarchy: Fund Alpha → Alpha Engine → Models → Research &
Validation → Data Infrastructure. Every work item is tested against:
*"How does this improve the alpha engine?"*

(Repository name `ngx-rotation` is historical — the scope outgrew it.)

**This is a research tool. Nothing it outputs is investment advice.**

## Status

| Phase | State |
|-------|-------|
| 1. Data architecture | ✅ Schema + bitemporal PIT layer, tested |
| 1b. Data Abstraction Layer | ✅ Provider interface + validating ingest + confidence scoring; CSV & Synthetic providers live, web providers stubbed pending per-source implementation |
| 1c. Research governance | ✅ Immutable experiment registry (SQL-trigger enforced), TOML-config-driven runner with holdout guard, hypothesis ledger (no-delete) |
| 2. Signal construction | ✅ Momentum ranking + catalyst filter + lite engine, developed on synthetic conf-0.0 data (plumbing only, counts_as_evidence=false) |
| 1d. Institutional safeguards | ✅ Seed registry (bit-identical reruns verified), extensible diagnostic engine (7 checks, caught both planted flaws + 2 emergent ones), capacity-as-distribution, line-item cost attribution, auto-evaluated failure conditions |
| 3. Backtest engine (per-line-item costs, ADTV caps, total return, capacity) | ✅ `engine_full` on synthetic data; single-day execution assumption noted below |
| 4. Validation (stability map, Holm/BH correction, placebo, walk-forward, IC memo) | ✅ Run on synthetic (rehearsal) AND real data (both pre-registered variants) |
| 5. Reporting | IC memos + completeness + reproducibility reports auto-generated (`reports/`); charts deferred |
| Real data (investing.com provider + staging validation) | ✅ 22,361 research-ready rows, 8 indices, 2012–2026; ASI anchor-verified; see `reports/data_completeness_2026-07-15.md` |

> **Before starting any new NGX momentum work, read
> [`reports/post_mortem_H-001.md`](reports/post_mortem_H-001.md) §8** — it
> states what has been ruled out, what is open, and what was never tested.
> H-001 is frozen (SQL-enforced); successors H-003 (priority,
> catalyst-driven) and H-002 (total-return momentum) are registered and
> blocked on data acquisition.

## Strategic frame: Data Moat Program (2026-07-15)

**Objective: maximize the decade-rate of alpha discovery.** The database is
the permanent asset; hypotheses are temporary. Acquisitions are justified by
generativity — the future hypothesis families they enable, mapped in
[docs/HYPOTHESIS_FAMILY_MAP.md](docs/HYPOTHESIS_FAMILY_MAP.md). See
[docs/DATA_MOAT_STRATEGY.md](docs/DATA_MOAT_STRATEGY.md) (five-question gate,
three moat mechanisms) and
[reports/data_moat_ranking.md](reports/data_moat_ranking.md) (scored priority
ranking, regenerable from `configs/dataset_priorities.toml`).
**`scripts/daily_capture.py` must run every trading day** — it archives
ephemeral NGX data (raw, timestamped) that can never be backfilled.

## Current program: Event-Driven Alpha (H-003) — data acquisition stage

The PIT event database is being built as a standalone asset before any H-003
signal work. See [docs/DATA_ACQUISITION_PLAN.md](docs/DATA_ACQUISITION_PLAN.md)
(all datasets: purpose, fields, sources, coverage, confidence, method) and
[reports/data_gap_report_H-003.md](reports/data_gap_report_H-003.md) (ranked
gaps; Sprint 1 = CBN MPC history + Brent + recapitalisation timeline).
Event ingestion runs only through `src/ngxrot/event_pipeline.py`
(taxonomy-validated, chronology-checked, append-only, quality report per
batch); taxonomy is configurable in `configs/event_taxonomy.toml`.

## Research outcome (2026-07-15)

**H-001 REJECTED as tested** on evidence-grade data (111 experiments, 62 on
real data, all reproducible from the immutable registry):
placebo p=0.55 in both pre-registered variants (real Sharpe below the mean of
100 shuffled-label strategies); 0/20 parameter cells survive Holm/BH; alpha
concentrated in the 2023–24 devaluation regime; negative excess in the
untouched 2025–26 out-of-sample window. Monthly rebalancing is separately
unviable on costs alone (−8.1% excess at retail-max brokerage).
Scope limits: price-only indices (no dividends), no constituent/capacity
data, catalyst filter untested. Total-return or catalyst-driven variants are
new hypotheses requiring new IDs and fresh OOS. Full detail:
`reports/reproducibility_H-001.md`, `reports/IC_memo_*`.

**Validation protocol decision (from the AUM contrast experiment):** regime
attribution and signal-quality failure conditions are evaluated at a
capacity-feasible AUM (so under-deployment doesn't masquerade as signal
failure); scalability is assessed separately via the capacity report and the
`capacity_below_minimum` condition. This is a config choice
(`engine.aum_ngn`), not a code path.

**Known modeling assumption (Phase 3):** each rebalance must execute within a
single session; institutional practice works orders over several days, which
multiplies capacity roughly by the execution horizon. A configurable
`execution_horizon_days` is a planned refinement — until then, capacity
figures are per-session lower bounds given the ADTV-proxy weights (which cut
the other way; see engine_full docstring).

## Layout

```
schema/schema.sql            # SQLite DDL — 12 tables, PIT views, confidence columns
schema/seed_reference.sql    # index registry + ASSUMED fee schedule
src/ngxrot/db.py             # init + bitemporal PIT readers (sim_date × vintage × min_confidence)
src/ngxrot/contracts.py      # dataset contracts every provider must emit
src/ngxrot/ingest.py         # sole write path: validate -> stamp lineage/confidence -> DB
src/ngxrot/providers/        # DAL: base.py, csv_provider.py, synthetic.py, web_stubs.py
scripts/phase1_smoke_test.py # builds DB, proves 3 lookahead traps are blocked
scripts/dal_demo.py          # end-to-end DAL demo incl. reject handling & confidence floors
docs/PHASE1_DATA_GAPS.md     # data questions (answered), assumptions, feasibility probes
data/ngx.sqlite              # generated (git-ignore if repo is created)
```

## Run

```
python scripts/phase1_smoke_test.py                     # PIT lookahead traps
python scripts/dal_demo.py                              # DAL end-to-end
python scripts/run_experiment.py configs/<cfg>.toml     # run experiment(s)
python scripts/ledger_cli.py [list|add|status|log]      # research ledger
```

Requires Python 3.10+ (3.11+ for tomllib) and pandas.

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
vendor later = one new provider class; the research engine is untouched.

Confidence convention: 0.9 exchange-official · 0.5 aggregator · 0.4 manual ·
0.3 archive reconstruction · **0.0 synthetic (may exercise machinery, may
never feed a research conclusion)**. PIT readers accept `min_confidence`, and
Phase 4 will sweep this floor as a robustness test.

## Design invariants (all phases must respect these)

1. Backtest code reads data **only** through the PIT helpers in `ngxrot.db`
   (`*_asof(knowledge_date)`), never raw tables.
2. Every observational row has `source_id` + `as_of_date`; corrections append,
   never overwrite.
3. Information is usable from its **announcement** date, not its effective date.
4. Undocumented history is excluded, never backfilled from current data.
5. All cost/fee rates are effective-dated and overridable; results computed on
   `confidence='assumed'` rates are watermarked as such.
