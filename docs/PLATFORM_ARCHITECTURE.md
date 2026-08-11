# Fund Alpha — Alpha Engine Module Architecture

*2026-07-21, expanded 2026-07-22 per owner's 9-module target architecture.
**Revised 2026-08-11 (Investment OS reframe, see `README.md`,
`docs/FUND_ALPHA_CHARTER.md`, `docs/INVESTMENT_OS_SPECIFICATION.md`): this
document's title changed from "Investment Intelligence Platform
Architecture" to "Alpha Engine Module Architecture" because that is what
it actually describes — the module structure of the quant hypothesis-
testing consumer, not the OS itself.** The OS's own architecture (data
acquisition → document store → extraction → evidence/grounding →
self-critique → coverage/confidence) is documented in
`docs/INVESTMENT_OS_SPECIFICATION.md`; this document remains the correct,
authoritative reference for how the Alpha Engine specifically is
structured and gated. Nothing is rebuilt; every existing system maps into
a module and is extended, never replaced. Modules are marked LIVE,
PARTIAL, or GATED — GATED modules are not scaffolded speculatively; each
waits for the evidence precondition stated against it. Building a gated
module before its precondition holds would itself violate the platform's
core rule (never invent alpha; nothing downstream of a factor may exist
before the factor is validated).*

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

**Standalone Liquidity factor test (H-016, added 2026-08-03)**: a new
`xs_liquidity_scores()` and `xs_liquidity` signal method (additive,
reuses the existing `xs_rank`/`xs_vol`/`xs_size` dispatch path unchanged;
Phase R2's own `liquidity_scores()` untouched) tested whether a
whole-universe ADTV sort carries a return premium independent of Size, in
either pre-registered direction (illiquid, classic Amihud & Mendelson
1986; or liquid, the direction Phase R2's own evidence hinted at).
**Rejected in full** — neither direction produced a credible premium
(Leg B, long-liquid, was rejected more decisively than Leg A: placebo
p=1.000, negative excess in every regime including OOS). Full derivation:
`docs/H016_LIQUIDITY_REPORT_2026-08-03.md`. Closes
`docs/FACTOR_CANDIDATE_REGISTRY.md`'s Liquidity (A1) candidate with a
disclosed, both-directions-tested answer: liquidity appears to matter on
this platform only as a conditioning characteristic on Size (per H-013),
not as an independent source of return. The pre-registration's Economic
Capacity Validation section (a filter-ladder robustness check for
whichever leg might have confirmed) was not run, since neither leg
cleared confirmation.

**Dividend Payer-Status factor test (H-017, added 2026-08-04)**: a new
`payer_status_scores()` and `xs_payer_status` signal method (additive,
reuses `targets_from_scores`/`simulate`/the placebo scheme unchanged) —
the first characteristic-MEMBERSHIP test on this platform (long ALL
eligible payers, not a top-N rank selection), using the real DOL-derived
`data/reference/exdiv_closure_calendar.csv`. **Rejected, cleanly** — 0/4
grid cells positive, placebo p=0.366, untouched final-OOS excess -12.2%.
A mandatory orthogonality assessment against Size and Liquidity
(Spearman correlation every formation date, plus a bucket decomposition)
found the base effect was never positive to begin with in any subset —
classified as a genuine null result, not a construct-validity failure.
Full derivation: `docs/H017_DIVIDEND_PAYER_STATUS_REPORT_2026-08-04.md`.

## 3. Factor Library — LIVE (structure), EMPTY (contents, by design)

`docs/FACTOR_REGISTRY.md` — the permanent knowledge base. Every completed
experiment updates it: status, validation date, holding horizon, capacity,
turnover, cost, economic rationale, evidence, limitations, and interaction
with every other entry. 0 validated / 6 rejected as of 2026-07-22, all
rejections carrying specific successor guidance (this is the intended
mode of progress, not a shortfall — see charter: a rejection that
increases future discovery efficiency is a successful outcome).

## 4. Company Intelligence Engine — GATED (this Alpha-Engine module
specifically; see naming note below)

Precondition: at least one validated factor to compute an exposure from.
A per-company profile with zero validated factors would be either empty
or fabricated — neither is acceptable. Scaffolding (schema, refresh
cadence) can be designed once the first factor validates; not before.

**Naming note (added 2026-08-11)**: a separate, differently-scoped
"company intelligence" capability has since been built as part of FRE
(`src/ngxrot/fre/company_intelligence_bundle.py`,
`company_economic_profile.py`, etc.) — it does NOT fulfill this module's
gate and is not the same thing. FRE's company intelligence is built from
document evidence and coverage-capped confidence (grounded facts about a
company), not from validated factor exposures (this module's actual
precondition). The two can coexist and eventually compose, but this
module's GATED status is unaffected by FRE's existence — factor exposure
still requires ≥1 validated, independent factor per the charter, and
still has only H-011.

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

## Status (revised 2026-08-11 — was stale at "0 validated" despite this
document's own §3 already describing H-011 as confirmed the same day it
was written)

**18 hypotheses tested: 1 confirmed (H-011, Size — severely
capacity-constrained), 15 rejected, 1 abandoned untested (H-002, pending
formal retirement per `docs/EXECUTION_BACKLOG.md` R7), 1 in first-look
testing (H-019, news-events, currently negative — not yet
confirmation-eligible).** Per-hypothesis evidence: `docs/FACTOR_REGISTRY.md`
(current through H-017; H-019's status is tracked in the ledger and
`HANDOFF.md`, not yet written up as a full Factor Registry entry pending
its verdict). Program retrospective, module-by-module maturity scoring,
dependency map, and 3-year roadmap (dated 2026-07-22, itself now stale on
the hypothesis count above but still the right reference for maturity
scoring methodology): `docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md`.
Program lessons: `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`.

Since this document's original 2026-07-22 status line, a large parallel
research push ("Project 1," Stages 16-28, see `HANDOFF.md`'s 2026-08-11
entry) tested and closed the fundamentals and insider-dealing tracks
(both NO-GO) without registering new hypothesis IDs — that work is
Alpha-Engine-adjacent discovery/diagnostic work, correctly excluded from
this module architecture and the Factor Registry by the same "no
hypothesis ID, no evidence-grade claim" discipline this document already
enforces. The FRE and Research OS builds described in
`docs/INVESTMENT_OS_SPECIFICATION.md` are a different consumer entirely,
not part of this Alpha Engine module count.
