# Fund Alpha — Investment Intelligence Platform Architecture

*2026-07-21, expanded 2026-07-22 per owner's 9-module target architecture.
Nothing is rebuilt; every existing system maps into a module and is
extended, never replaced. Modules are marked LIVE, PARTIAL, or GATED —
GATED modules are not scaffolded speculatively; each waits for the
evidence precondition stated against it. Building a gated module before
its precondition holds would itself violate the platform's core rule
(never invent alpha; nothing downstream of a factor may exist before the
factor is validated).*

## 1. Data Layer — LIVE

Prices (3 validated sources, 320k+ rows), corporate actions, earnings
filings, dividend closure dates, market cap (`data/reference/`),
macro/events/index history, `daily_capture.py`. Every row carries
provenance (`source_id`), confidence, `as_of_date` (PIT timestamp), and
passes `run_equity_diagnostics.py` (D1–D4) before use. Coverage Gate v2
gates readiness (`configs/coverage_thresholds.toml`, PASSED 2026-07-21,
runner-enforced — `requires_coverage_gate=true` in every prereg).
Not yet acquired: financial statement values, shares outstanding
(float-adjusted size), analyst estimates, news, alternative data —
tracked in the Factor Registry's dataset→factor leverage map.

## 2. Research Layer — LIVE

Pre-registration (economic rationale, holding period, benchmark, costs,
OOS period, multiple-testing plan, all fixed before any run) →
`runner.run_resolved` (PIT reads, holdout guard, gate refusal) →
`phase4.py` (stability grid → Holm/BH → seeded placebo → walk-forward with
untouched final OOS) → mechanical verdict → IC memo (`ic_report.py`).
Two engines: `backtest_lite`/`engine_full` (index-level, sector era) and
`backtest_xs.py` (cross-sectional per-stock, built 2026-07-22 for
H-006/H-007 — rank and event-book modes). No discretionary changes survive
first results; a changed design is a new hypothesis ID.

**Statistical hardening (METH-001, added 2026-08-02)**: the per-hypothesis
inference layer (`stats.py::excess_ttest`, Holm, Benjamini-Hochberg,
placebo) is now supplemented, not replaced, by two cross-hypothesis-aware
additions: `newey_west_tstat` (HAC correction for daily-return
autocorrelation) and `deflated_sharpe_ratio`/`probabilistic_sharpe_ratio`
(Bailey & López de Prado — corrects a hypothesis's headline confidence for
the real, growing number of independent trials run against the same NGX
history; N is sourced from the ledger's actual resolved-hypothesis count,
not asserted). Full derivation and first real application (to H-011):
`docs/METH-001_STATISTICAL_HARDENING_REPORT_2026-08-02.md`. Every future
hypothesis's confirmation should report its DSR against the then-current
trial count alongside its per-hypothesis correction.

**Point-in-time risk-free rate (METH-002, added 2026-08-02)**: fixes the
`metrics.py::compute()` `rf_annual_pct=0.0` placeholder every hypothesis
through H-012 silently used. `src/ngxrot/riskfree.py` provides a
look-ahead-safe as-of lookup against `data/reference/cbn_mpr_history.csv`
(50 hand-verified CBN Monetary Policy Rate decisions, 2015-07-23 to
2026-07-21); `metrics.compute()` gained an additive `rf_series` parameter
(reports `sharpe_vs_real_rf` alongside, never replacing, the existing
`sharpe_vs_rf`); `runner.py` gained an opt-in `validation
.use_real_risk_free_rate` config flag (default `False` — every existing
frozen config's behavior is exactly unchanged). Applied read-only to all
11 resolved hypotheses: `docs/METH-002_RISK_FREE_RATE_REPORT_2026-08-02.md`.
Uses MPR as a disclosed proxy for the true NGN T-bill rate (a real, stated
limitation, not resolved by this phase — see the design record's rejected
alternatives).

**Size interaction forensics (Phase R2, H-013/H-014/H-015, added
2026-08-03)**: a double-sort extension to `backtest_xs.py` — new
`liquidity_scores()` (reuses `panel["adtv60"]`, already loaded for
capacity reporting; no new data), `interaction_bucket_members()`,
`targets_from_bucketed_size()`, `benchmark_targets_bucket()`, and an
`xs_size_interaction` signal method — tests whether H-011's Size premium
survives independently of Liquidity, Momentum, or Volatility via a median
split + bucket-scoped benchmark, reusing `size_scores()`/`rank_scores()`/
`vol_scores()` completely unmodified. Real finding: the premium does not
survive fully independently of any of the three — concentrated among
liquid, low-volatility, (partially) low-momentum small caps. Full
derivation: `docs/PHASE_R2_SIZE_INTERACTIONS_REPORT_2026-08-03.md`. Does
not change H-011's own Validated status; narrows how it should be
understood. No standalone Liquidity/Momentum/Volatility factor claim is
made.

## 3. Factor Library — LIVE (structure), EMPTY (contents, by design)

`docs/FACTOR_REGISTRY.md` — the permanent knowledge base. Every completed
experiment updates it: status, validation date, holding horizon, capacity,
turnover, cost, economic rationale, evidence, limitations, and interaction
with every other entry. 0 validated / 6 rejected as of 2026-07-22, all
rejections carrying specific successor guidance (this is the intended
mode of progress, not a shortfall — see charter: a rejection that
increases future discovery efficiency is a successful outcome).

## 4. Company Intelligence Engine — GATED

Precondition: at least one validated factor to compute an exposure from.
A per-company profile with zero validated factors would be either empty
or fabricated — neither is acceptable. Scaffolding (schema, refresh
cadence) can be designed once the first factor validates; not before.

## 5. Ranking Engine — GATED

Same precondition, stronger version: ranking by "expected risk-adjusted
return" requires a return MODEL, which requires validated factors with
known expected-alpha intervals (from walk-forward evidence). Ranking on
zero factors is indistinguishable from ranking on noise.

## 6. Portfolio Construction — GATED

Charter milestone rule (unchanged): begins at ≥2 validated independent
factors — independence is exactly what the "Expected Interaction with
Existing Factors" prereg section (added 2026-07-22) exists to establish
in advance, so this module's eventual trigger is evidence-based, not a
head-count.

## 7. Risk Engine — PARTIAL

Per-experiment risk measurement already exists inside the gauntlet
(drawdown, capacity distribution, sector/regime concentration, failure
conditions in `failure_conditions.py`). A portfolio-level Risk Engine
(cross-factor exposure, tail risk, beta) is GATED behind module 6 — there
is no portfolio to measure risk on yet.

## 8. Performance Attribution — GATED

Same precondition as module 6; attribution decomposes a live portfolio's
realized return, which does not exist yet.

## 9. Continuous Learning — PARTIAL (design), GATED (operation)

Design precedent exists: `docs/HYPOTHESIS_DISCOVERY_DESIGN.md` (scanner
plug-ins → BH-corrected candidates → human promotion, never auto-touches
the engine). Decay monitoring is a per-factor commitment made AT
validation time (prereg field, per owner directive 2026-07-22) — it
activates when the first factor enters the library. Never auto-changes
weights; generates research proposals only, per instruction.

## Governing rules (unchanged, reaffirmed 2026-07-22)

1. No factor enters the library without the full gauntlet; rejected
   factors are archived forever. No arbitrary weights, ever.
2. The gate blocks factor research when data quality regresses.
3. Append-only PIT with restatement vintages is the source of truth;
   research pins a vintage (`docs/DATA_FREEZE_2026-07-21.md`).
4. Priority test for new work: does it increase the probability of the
   next validated, INDEPENDENT factor? (Independence, not just validity,
   per 2026-07-22 refinement — a factor's value includes what it adds to
   the library, not only whether it works alone.)
5. ≤2 active hypotheses at any time; each wave completes before the next
   begins. Never optimize for positive results — optimize for truthful
   ones; false positives are treated as more costly than false negatives.

## Status (2026-07-22)

9 hypotheses tested, 0 validated, 9 rejected (2 near-misses: H-004
p=0.079, H-009 p=0.069). Program retrospective, module-by-module maturity
scoring, dependency map, and 3-year roadmap:
`docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md` (supersedes this document's
layer map for anything more detailed than the module list above — this
file remains the short-form summary). Per-hypothesis evidence:
`docs/FACTOR_REGISTRY.md`. Program lessons:
`docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`. Candidate next hypotheses
(not yet pre-registered): `docs/WAVE_3_RESEARCH_DIRECTIONS.md`.
