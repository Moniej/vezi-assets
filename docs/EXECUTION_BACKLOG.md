# Fund Alpha — Execution Backlog (V1 architecture, frozen)

*2026-07-22. The platform architecture is frozen as V1
(`docs/PLATFORM_ARCHITECTURE.md`,
`docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md`). This document does not
redesign, expand, or re-plan anything — it inventories every remaining
task against that frozen architecture and orders it for execution. C1
(Pooled Momentum) and C4 (Size) are APPROVED as the next research wave;
their pre-registration and execution are Critical items below.*

**Update 2026-07-22 (post-E1/E2/E3, platform capability review)**: R1/R2
are now fully unblocked (E1/E2/E3 done, see below) and remain the
recommended Wave 3 — considered and rejected the alternative of deferring
them for infrastructure work first (see below); they're ready, rehearsed,
and directly test the program's strongest open thread, and deferring
ready low-risk research to build infrastructure that wouldn't change
their outcome is delay, not platform-building. The review DID surface a
genuinely new, non-factor infrastructure gap (**E15**, below) — queued as
a parallel, non-gating track, positioned ahead of Wave 4's engineering
prep rather than ahead of Wave 3's already-ready pair.

---

## Research Tasks

### Critical

**R1 — Pre-register and run H-010 (Pooled Overlapping-Cohort Momentum)**
- Description: draft the full pre-registration for Wave-3 candidate C1
  (multi-cohort formation calendar, targeting the power gap H-009
  identified), get owner sign-off, run the unchanged gauntlet.
- Why it matters: APPROVED next research step; the strongest evidentiary
  lead in the program (H-009: right sign, clean plateau, positive in
  every regime including OOS, missing only statistical power).
- Dependencies: **E1 — DONE 2026-07-22.** UNBLOCKED. Prereg can now state
  the exact cohort design (`xs_rank_pooled`, n_cohorts, offset spacing)
  against real, working code.
- Engineering effort: LOW (prereg drafting only, once E1 exists).
- Research impact: HIGH — closes the program's most promising open
  thread either way (validates the first factor, or definitively rules
  out low-turnover momentum on NGX with a design that fairly tested it).
- Files/modules: `docs/PREREG_H-010.md` (new), `configs/h010_*.toml` (new).
- Completion criteria: mechanical verdict recorded in the ledger and
  `docs/FACTOR_REGISTRY.md`, IC memo generated.

**R2 — Pre-register and run H-011 (Size)**
- Description: draft the full pre-registration for Wave-3 candidate C4
  using the validated market-cap panel; get sign-off; run the gauntlet.
- Why it matters: APPROVED; zero new datasets needed; opens a genuinely
  untested family; explicitly expected to be capacity-constrained by its
  own economic logic (disclosed up front, not discovered after).
- Dependencies: **E2 — DONE 2026-07-22.** UNBLOCKED.
- Engineering effort: LOW (prereg drafting only, once E2 exists).
- Research impact: MODERATE-HIGH — best-readiness candidate in the
  program; even a rejection is informative (tests whether the
  capacity-constraint premium the platform's own capacity reports have
  implied across 9 hypotheses is real or not).
- Files/modules: `docs/PREREG_H-011.md` (new), `configs/h011_*.toml` (new).
- Completion criteria: mechanical verdict recorded, IC memo generated.

### High Priority

**R3 — Build and validate the regime-classification methodology (C2
infrastructure)**
- Description: define a pre-registered, look-ahead-free macro-regime
  classification rule (e.g., stable vs. FX-crisis/float-shock windows)
  using existing `macro_series`/`events` tables, BEFORE it is used to
  gate any factor.
- Why it matters: highest long-term platform-impact candidate scored in
  `docs/WAVE_3_RESEARCH_DIRECTIONS.md` — a reusable methodology, not a
  single-use factor. Directly motivated by two independent findings
  (H-004's regime reversal, H-008's regime-mismatched mechanism).
- Dependencies: none blocking — can proceed in parallel with R1/R2, but
  per the ≤2-active-hypotheses rule its FIRST APPLICATION (e.g., a
  regime-conditional H-008 retest) cannot become a live hypothesis until
  an R1/R2 slot frees up.
- Engineering effort: MODERATE (new classification logic + its own
  rehearsal/validation before any real use, matching every prior parser's
  pattern).
- Research impact: HIGH (methodology-level, compounds across future work).
- Files/modules: new module (e.g., `src/ngxrot/regime.py`), a validation
  script, a design note (not a new planning document — a short
  methodology spec co-located with the code, same pattern as parser
  docstrings).
- Completion criteria: regime rule pre-registered and frozen BEFORE any
  factor is tested against it; a synthetic rehearsal proves the rule
  doesn't leak future information.

### Medium Priority

**R4 — Scope corporate-action event counts by type**
- Description: count buyback/rights-issue/bonus-issue events with
  reliable dates in the classified corp-actions calendar, BEFORE
  attempting Wave-3 candidate C3.
- Why it matters: C3 was scored lowest of the five candidates
  specifically because its event set was never counted; this is the
  prerequisite research task that would let it be scored honestly.
- Dependencies: none.
- Engineering effort: LOW (a counting/summary script).
- Research impact: LOW directly, MODERATE as an unlock (turns an
  unscoped idea into a scoreable one).
- Files/modules: `data/staging/xissuer/corporate_actions_calendar_classified.csv`.
- Completion criteria: a per-type event count with date-reliability
  assessment, informing a go/no-go on drafting a C3 prereg.

**R5 — Total-return retest design (blocked)**
- Description: once dividend AMOUNT data exists (see E5), design a
  total-return retest applicable across the entire per-stock hypothesis
  family (H-002's original question, plus a legitimate total-return
  variant of any future momentum/size result).
- Why it matters: every per-stock hypothesis so far (H-006–H-011) uses
  price-only returns — a disclosed limitation in every one of them.
- Dependencies: **E5** (EPS/dividend parser retry) — not actionable
  before this lands.
- Engineering effort: N/A until unblocked.
- Research impact: MODERATE-HIGH if unblocked (retroactively strengthens
  or weakens multiple prior verdicts' robustness, not just one new test).
- Files/modules: TBD, pending E5.
- Completion criteria: N/A — tracked as blocked, not actionable now.

### Low Priority

**R6 — Dividend Payer-Status hypothesis (C5)**
- Description: the lowest-effort Wave-3 candidate; parked behind C1/C4
  per prioritization, viable anytime.
- Why it matters: cheapest possible addition to the research queue if
  program bandwidth ever exceeds the ≤2-active cap's current occupants.
- Dependencies: none.
- Engineering effort: LOW.
- Research impact: LOW-MODERATE (construct-validity risk vs size/quality
  flagged in Wave 3 doc).
- Files/modules: `data/reference/exdiv_closure_calendar.csv`.
- Completion criteria: N/A — queued, not scheduled.

**R7 — Retire or explicitly re-scope H-002**
- Description: H-002 ("total-return sector momentum") has sat `untested`
  in the ledger since 2026-07-15. The sector research family is
  deprioritized per the per-stock pivot; H-002 as originally worded will
  likely never run in its current form.
- Why it matters: research hygiene — a permanently-dangling `untested`
  entry is a small but real clarity cost in the ledger; either formally
  withdraw it with a reasoned note, or explicitly re-scope it as a
  per-stock total-return hypothesis once R5 unblocks.
- Dependencies: none (a ledger housekeeping decision, not code).
- Engineering effort: TRIVIAL (`ledger_cli.py status H-002 ...`).
- Research impact: NONE directly — pure hygiene.
- Files/modules: `data/registry.sqlite` (ledger tables).
- Completion criteria: H-002 has an explicit status (withdrawn, or
  re-scoped with a note) rather than an indefinite `untested`.

---

## Engineering Tasks

### Critical

**E1 — Multi-cohort target-blending extension for `backtest_xs.py`
— DONE 2026-07-22**
- Description: extend the cross-sectional rank engine to support
  multiple staggered formation cohorts blended into one target-weight
  series, with per-cohort AND aggregate turnover reporting.
- Resolution: implemented as `xs_rank_pooled` (return-level blend of N
  independent single-cohort sub-portfolios, not a unified partial-
  rebalance target vector — see module docstring for why). Rehearsed
  3/3 (`scripts/rehearse_xs_pooled.py`): planted momentum recovered, null
  panel stays null, cohort correlation measured directly (~0.57 mean
  off-diagonal on the planted panel — genuinely decorrelated, not
  assumed). H-010 is now unblocked.
- Why it matters: hard blocker for R1 (H-010) — the design cannot be
  pre-registered with real parameters until the mechanism exists to
  execute it.
- Dependencies: none (extends existing, validated `backtest_xs.py`).
- Engineering effort: MODERATE (new blending logic + a placebo design
  that correctly handles multi-cohort persistence — the SAME class of
  subtlety that caused the original xs_rank placebo bug found in
  rehearsal; do not skip a rehearsal step for this one).
- Research impact: enables R1 entirely; no impact on its own.
- Files/modules: `src/ngxrot/backtest_xs.py`, a new
  `scripts/rehearse_xs_engine_v3.py` (cohort-correlation-specific
  synthetic checks — directly testing the failure risk R1 already flags).
- Completion criteria: synthetic rehearsal passes (planted-signal
  recovery + null-panel check, matching the established bar), AND a
  direct test that cohort correlation is measured (not assumed) on a
  synthetic panel with KNOWN correlation, before any real config is run.

**E2 — Market-cap panel loader + size signal method — DONE 2026-07-22**
- Description: add a `load_market_cap_panel` loader and an `xs_size`
  signal method to `backtest_xs.py`, following the exact pattern
  `xs_vol` already established.
- Resolution: implemented; cap reconstructed via ffilled implied-share-
  count × dense close (reuses the invariant `market_cap_validation.md`
  already validated, rather than naively ffilling cap level). Rehearsed
  2/2 (`scripts/rehearse_xs_size.py`). H-011 is now unblocked.
- Why it matters: hard blocker for R2 (H-011).
- Dependencies: none (`data/reference/market_cap_panel.csv` already
  validated).
- Engineering effort: LOW (direct pattern reuse).
- Research impact: enables R2 entirely.
- Files/modules: `src/ngxrot/backtest_xs.py`.
- Completion criteria: same rehearsal bar as every prior signal method
  (`scripts/rehearse_xs_engine_v2.py`-style planted-effect + null checks)
  before any real config is run.

**E3 — Initialize version control — DONE 2026-07-22**
- Description: `git init`, commit the current repository state as the
  V1 baseline, establish a `.gitignore` for `data/archive/` and other
  large/binary paths (commit the DATABASE'S SCHEMA and small reference
  files; the multi-GB PDF archives and `ngx.sqlite` itself are better
  tracked by the existing PIT/vintage system than by git — this needs a
  deliberate decision, not a blanket `git add -A`).
- Why it matters: flagged as a PRESENT-TENSE gap in the Phase 6
  firm-readiness assessment, independent of the alpha roadmap. Every
  edit made across this entire multi-session program to date has zero
  rollback capability outside manual reconstruction. This is the single
  highest-risk item in the Technical Debt section (TD1) precisely because
  it compounds — the longer it's deferred, the more unrecoverable history
  accumulates.
- Dependencies: none. Should happen BEFORE E1/E2 land, so those two
  changes are the first ones captured with real version history.
- Engineering effort: LOW (mechanically), but requires one careful
  decision (what NOT to track — large binaries, the live sqlite database)
  before the first commit, not after.
- Research impact: none directly; risk-reduction only.
- Files/modules: repository root (`.git/`, `.gitignore`).
- Completion criteria: `git log` shows a baseline commit; a documented
  decision (in the commit message or a short `.gitignore` comment, not a
  new planning doc) on what is and isn't tracked.

### High Priority

**E4 — Daily capture scheduling**
- Description: put `scripts/daily_capture.py` on an actual recurring
  schedule (OS scheduler, cron-equivalent, or the platform's own
  scheduling tool if available) instead of manual, ad-hoc runs.
- Why it matters: flagged as a standing operational risk since the
  earliest sessions of this program — "each missed day is lost forever."
  This is pure downside risk accumulating silently every day it remains
  unscheduled, independent of any research question.
- Dependencies: none. User-gated only in the sense that a scheduling
  MECHANISM choice is the user's call, not in the sense that it needs
  research sign-off.
- Engineering effort: LOW (the script already exists and works; this is
  a scheduling/ops task, not new code).
- Research impact: preserves future data completeness; no impact on
  current research.
- Files/modules: `scripts/daily_capture.py`, OS-level scheduler config.
- Completion criteria: capture runs automatically on trading days without
  manual intervention, with a visible log of successful runs.

**E15 — Unified point-in-time company/security feature panel**
- Description: one PIT-correct join across price, market cap,
  dividend/closure events, earnings events, and corp-actions, keyed on
  (ticker, date) — NOT a factor, computes no score, asserts no alpha.
  Replaces the currently separate, overlapping loaders
  (`load_panel`, `load_market_cap_panel`, `event_selections`'s internal
  joins) with one shared substrate.
- Why it matters: identified in the 2026-07-22 platform capability review
  as the single highest-value gap that is NOT another factor. Every
  future family (Value, Dividend, Corporate-Actions, Regime-conditioning)
  currently requires its own bespoke data-wrangling; this makes all of
  them cheaper simultaneously, and is the literal prerequisite substrate
  for the eventual Company Intelligence Engine's schema.
- Dependencies: none blocking. Deliberately NOT retrofitted under H-010/
  H-011 — both are already built and rehearsed; disturbing working,
  validated code purely for architectural tidiness right before using it
  is the wrong sequencing. Queued for Wave 4's engineering prep instead.
- Engineering effort: MODERATE (consolidation, not new capability per se
  — the individual joins already exist and work; the task is unifying
  them behind one PIT-correct interface).
- Research impact: none directly; every future hypothesis's engineering
  readiness improves.
- Files/modules: likely `src/ngxrot/db.py` (a new `company_panel_asof`
  reader) or a new `src/ngxrot/panel.py`; `backtest_xs.py`'s loaders
  become callers of it, not owners of their own joins.
- Completion criteria: `xs_vol`/`xs_size`/momentum all reproduce their
  EXISTING rehearsal results unchanged when switched to the unified
  panel (a regression check, not a new validation bar) before any new
  factor family is built on top of it.

**E5 — DOL EPS/dividend parser retry, scoped as its own session**
- Description: per `reports/eps_pe_extraction_status.md`'s own
  recommendation — identify distinct DOL format eras precisely (probe
  header x-positions on a stratified sample spanning 2014-2026 FIRST),
  calibrate per era, THEN attempt bulk extraction. Do not repeat the
  two heuristics that already failed the validation bar.
- Why it matters: blocks R5 (total-return retest) and the entire
  Value/Dividend-Yield family; the highest-value blocked dataset on the
  platform per the Lessons Learned document.
- Dependencies: none technically; needs to be scheduled as dedicated
  effort rather than an incidental attempt (its own prior failure mode).
- Engineering effort: HIGH (per-era calibration is materially harder than
  either heuristic already tried; this is why it failed twice already).
- Research impact: HIGH if successful — unlocks two full factor families
  plus retroactive strengthening of every prior per-stock verdict.
- Files/modules: `src/ngxrot/dol_eps_parser.py` (rewrite), a new
  `scripts/validate_eps_pe_v2.py` matching the existing validation
  pattern.
- Completion criteria: ≥95% pass rate on the same EPS×P.E.≈Close
  cross-check, on ≥500 sampled rows, matching the bar already declared
  in `scripts/validate_eps_pe.py` — do not lower it.

**E6 — Validate or retire the corp-actions structured extraction**
- Description: either invest in validating
  `data/staging/xissuer/corporate_actions_extracted.csv` (397 rows, mostly
  unpopulated fields) to evidence grade, or explicitly mark it as
  non-authoritative in its own file header so a future researcher doesn't
  mistake staging presence for validation.
- Why it matters: blocks R4/C3 and the Corporate-Action family; currently
  the second-lowest-scoring piece of code in the platform's maturity
  assessment (evidence quality 1/5).
- Dependencies: R4 (scoping) should happen first — no point validating
  extraction for event types that turn out to have too few reliable
  dates to support a hypothesis anyway.
- Engineering effort: MODERATE-HIGH (same class of difficulty as E5 —
  extracting structured fields from scanned/templated NGX filings has
  twice now proven harder than initial estimates).
- Research impact: MODERATE (unlocks C3 specifically).
- Files/modules: `scripts/build_corp_actions_db.py`,
  `data/staging/xissuer/corporate_actions_extracted.csv`.
- Completion criteria: a stated, tested pass rate against known primary-
  source anchors (same discipline as every other parser), OR an explicit
  "not evidence-grade" marker if the investment isn't made.

### Medium Priority

**E7 — Triage the `vwap_inconsistent` warning backlog**
- Description: investigate the 469 flagged rows (incl. 2 unexplained
  zero-value days: 2015-05-28, 2017-07-12) from `run_equity_diagnostics.py`.
- Why it matters: open since the gate-remediation session; warn-level
  (not gate-blocking), but unexamined data-quality signal accumulating.
- Dependencies: none.
- Engineering effort: LOW-MODERATE (likely a mix of legitimate thin-
  trading days and a few parser edge cases; needs triage, not a rewrite).
- Research impact: LOW directly; protects future factor data quality.
- Files/modules: `scripts/run_equity_diagnostics.py`, `data_quality_log`.
- Completion criteria: every flagged row classified (legitimate /
  parser artifact / unexplained), with unexplained rows reduced or
  explicitly documented as a known residual.

**E8 — Verify or apply the 49 unverified candidate symbol renames**
- Description: `data/reference/symbol_renames.csv` has 4 verified renames
  applied and 49 candidates still marked "price/timing continuity
  detection — verify before use."
- Why it matters: affects IRU membership continuity precision for any of
  the 49 affected tickers across their rename boundary — a real, if
  currently unquantified, data-quality gap.
- Dependencies: none.
- Engineering effort: MODERATE (each candidate needs an independent
  verification, likely via primary-source cross-check, same discipline
  as the 4 already-verified renames).
- Research impact: LOW-MODERATE (protects universe construction quality
  for future hypotheses; no known CURRENT verdict depends on this).
- Files/modules: `data/reference/symbol_renames.csv`,
  `src/ngxrot/universe.py` (`rename_chain`).
- Completion criteria: each of the 49 candidates resolved to
  verified/rejected, not left in an unverified state indefinitely.

**E16 — Persist `result.attribution` for pooled/multi-cohort hypotheses;
fix `n_rebalances` undercount — DONE 2026-07-22**
- Resolution: `runner.py`'s xs branch now copies `result.attribution`
  into the persisted metrics JSON when non-empty (guarded to not reuse
  the `full` engine's flat-cost rounding transform, since this is a
  nested diagnostics dict). `pooled_rank_run` now builds `result.weights`
  from the real UNION of every cohort's own execution dates instead of
  an empty DataFrame — fixes `n_rebalances` (0 → 35 on re-test, matching
  the ~36 hand estimate) AND `hit_rate_vs_benchmark` (None → 0.457) as a
  bonus, since both read the same previously-empty field. `ic_report.py`
  gained a conditional "Cohort diagnostics" section (mean pairwise
  correlation, per-cohort turnover, full matrix) that appears only for
  pooled hypotheses. Verified end-to-end: re-ran H-010's base config
  (a plumbing check, not a new verdict attempt — H-010's rejection
  stands, unchanged; every verdict-relevant number — excess, turnover,
  cost drag — was byte-identical before and after) and confirmed the
  registry now holds `attribution.cohort_return_correlation` with mean
  off-diagonal 0.755 (matches the 0.75 recovered by hand for the
  Factor Registry writeup), and confirmed the IC memo template renders
  the new section without error.
- Description: two reporting gaps found while writing up H-010's verdict
  (2026-07-22), neither of which affected the mechanical verdict itself
  (both are reporting/wiring issues, not evidence issues), both worth
  fixing before the next `xs_rank_pooled`-based hypothesis: (1)
  `backtest_xs.pooled_rank_run`'s diagnostics (cohort return correlation,
  per-cohort turnover) are computed and attached to `result.attribution`
  but `runner.run_resolved`'s xs branch never persists `attribution` into
  the registry metrics JSON or the IC memo template — H-010's real
  cohort correlation (~0.75) had to be recovered by manually re-running
  the base config after the fact. (2) `metrics.compute`'s
  `n_rebalances` reads `len(result.weights.index)`, which is empty by
  construction for pooled results (blending happens at the return level,
  see the `pooled_rank_run` docstring) — H-010's confidence rating scored
  "sample: 0 decisions" when the true count is ~36 formation events
  across 4 cohorts.
- Why it matters: the cohort-correlation number is exactly the evidence
  that explained WHY H-010 failed (0.75 real vs 0.57 synthetic) — it
  should be in the permanent, queryable record, not recovered by hand
  each time. The decision-count bug systematically understates
  confidence ratings for every future pooled hypothesis.
- Dependencies: none.
- Engineering effort: LOW (both are small, localized fixes).
- Research impact: none directly; improves the accuracy of every future
  pooled-momentum-family IC memo.
- Files/modules: `src/ngxrot/runner.py` (persist `result.attribution`
  when non-empty), `src/ngxrot/metrics.py` or `backtest_xs.py`
  (`pooled_rank_run` should populate a synthetic `weights`-equivalent, or
  `metrics.compute` should accept an explicit decision count).
- Completion criteria: a future `xs_rank_pooled` IC memo shows the real
  cohort correlation without manual recovery, and its confidence
  rating's decision count is not 0.

**E9 — DOL-day close precision restatement via gainers cross-check**
- Description: the 177 single-source recovered days (DOL/LIST2 fallback)
  could have their close precision improved using the gainers
  transitions table's 'prev' column (unadjusted official close) as an
  independent cross-check — noted as a scoped fix during gate remediation
  but never executed.
- Why it matters: modest precision improvement on an already-disclosed,
  already-flagged (`single_source_day`) subset of the panel.
- Dependencies: none.
- Engineering effort: LOW-MODERATE.
- Research impact: LOW (marginal precision gain on 177/2,933 days, ~6%).
- Files/modules: `data/reference/gainers_transitions.csv`,
  `scripts/ingest_dol_prices.py`.
- Completion criteria: restated closes cross-checked against the gainers
  table; discrepancy rate reported.

**E10 — Minimal regression-test harness, starting with `db.py`'s PIT
readers**
- Description: the repository has ZERO automated tests (confirmed by
  search — no `tests/` directory exists anywhere). Every correctness
  guarantee to date comes from bespoke, one-off validation scripts run
  manually per feature. Start with the single most load-bearing, hardest-
  to-manually-verify module: `db.py`'s `*_asof` bitemporal readers
  (vintage pinning, latest-as-of-date-wins logic) — a silent regression
  here would corrupt every hypothesis silently.
- Why it matters: this is the one Repository Health finding that
  materially improves the platform (per the "recommend only if material"
  instruction) — the validation-script culture is genuinely strong, but
  it is a PROCESS control substituting for an automated one, which does
  not scale past a single disciplined researcher and leaves the most
  critical module (PIT correctness) without a regression safety net.
- Dependencies: E3 (version control) should exist first, so test
  additions have real history.
- Engineering effort: MODERATE to start (a handful of targeted PIT
  look-ahead tests, not a full suite — do not over-scope this).
- Research impact: none directly; protects every future hypothesis's
  foundational correctness guarantee.
- Files/modules: `src/ngxrot/db.py`, new `tests/test_db_pit.py`.
- Completion criteria: automated tests exist that would have caught the
  three lookahead traps the original H-001 post-mortem said were
  "demonstrated blocked" manually (restated value, late-announced
  membership, future event) — turning a documented manual demonstration
  into a regression-proof one.

### Low Priority

**E11 — Corp-actions OCR pipeline (tesseract)**
- User-gated; scanned filings (mostly majors' dividend notices) remain
  text-unextractable without it. No action until the user decides.

**E12 — Shares-outstanding / float-adjusted size harvest**
- Enables a float-adjusted successor to R2/H-011 and a proper cap-
  weighted benchmark. No current trigger; worth scoping only after
  H-011's full-issue-cap version has a verdict.

**E13 — Performance optimization of bulk parse/build scripts**
- Several scripts (`build_market_cap_panel.py`,
  `parse_dol_exdiv_all.py`, etc.) run for many minutes via brute-force
  archive scans. Acceptable at current (one-time, infrequent) usage
  patterns. Only becomes worth doing if re-run frequency increases
  (e.g., daily incremental re-parsing) — no current trigger.

**E14 — Monitoring/alerting for scheduled jobs**
- Moot until E4 (scheduling) exists. Do not build ahead of the thing it
  would monitor.

---

## Technical Debt (ranked by risk)

| # | item | risk | why |
|---|---|---|---|
| TD1 | No version control | **HIGH** | Every change across the entire program to date is unversioned; compounds daily; no rollback path except manual reconstruction. Addressed by E3. |
| TD2 | Corp-actions structured extraction sits in `data/staging/` alongside validated files, unmarked | **MEDIUM** | Risk is a future researcher (or future session of this same researcher) mistaking staging presence for validation. File itself is inert until used. Addressed by E6. |
| TD3 | `dol_eps_parser.py` kept in tree as a documented negative result | **MEDIUM** | Same class of risk as TD2 — inert unless imported and trusted without reading its caveats. Mitigated by an explicit docstring; residual risk is someone skipping the docstring. |
| TD4 | `xs_event` capped-slot book construction proven to under-estimate turnover ~10× (H-006 finding) | **MEDIUM** | The SIMULATOR is correct; the CONSTRUCTION PATTERN is a trap for a future event hypothesis that reuses it without re-deriving turnover expectations. Documented in `docs/FACTOR_REGISTRY.md`; residual risk is someone not reading it. |
| TD5 | 49 unverified candidate symbol renames unapplied | **MEDIUM** | Could subtly affect IRU continuity for any of 49 tickers; no known current verdict depends on it, but unquantified. Addressed by E8. |
| TD6 | 177 single-source recovered days, incl. ~1.7% intraday-print risk that is undetectable per-file by construction | **MEDIUM** | Disclosed in every relevant IC memo's data-limitations section; risk is a future AGGREGATE analysis that doesn't inherit that per-hypothesis disclosure discipline. |
| TD7 | Zero automated tests | **MEDIUM** (elevated from LOW specifically for `db.py`) | Mitigated by strong manual-validation culture; does not scale past one disciplined researcher. Addressed by E10. |
| TD8 | `vwap_inconsistent` 469-row backlog, 2 unexplained zero-value days | **LOW** | Warn-level, small relative to 320k-row panel. Addressed by E7. |
| TD9 | Full-issue (not float-adjusted) market cap | **LOW** | Disclosed limitation, not a bug; a known simplification with a clear upgrade path (E12) if ever needed. |
| TD10 | rf=0% Sharpe placeholder throughout every IC memo | **LOW** | Disclosed consistently everywhere; no rejection verdict in the program has hinged on a marginal Sharpe threshold this would flip. |
| TD11 | `entity_relationships.relation_type` is a literal `affects_order_N` label, not a semantic taxonomy (competitor_of/supplier_to/...) | **LOW-MEDIUM** | Honest given the draft prompt never asks the model to classify relationship nature; limits graph queries to "named as affected" rather than "is a competitor of." Upgrading needs a prompt change first. See `reports/phase_e_completion.md`. |
| TD12 | Entity resolution (exact case-insensitive name match, no merge queue, inherited from Phase C) now has a higher blast radius since Phase E persists a relationship graph on top of it | **MEDIUM** | A wrong non-merge now fragments/wrongly-consolidates the persisted graph, not just a mention count. Worth revisiting before real-scale use. See `entities.py`'s docstring. |
| TD13 | `historical_event_reaction` (Phase E) is new, single-purpose, and untested against any real NGX anchor | **LOW** | Engineering-correctness tested only (synthetic price series). Evidence-only, never feeds `alpha_engine`/`runner`, so the validation bar is lower than a quant parser's — but no real sanity check has been run yet. See `reports/phase_e_completion.md`. |
| TD14 | Peer ticker resolution (Phase F) is exact-match-only against `securities.name`, so propagation coverage will likely be low against real filings | **LOW-MEDIUM** | Disclosed trade-off, not a defect — "never guess a match." A verified alias table (mirroring `symbol_renames.csv`) would raise coverage; not built, no trigger yet. See `reports/phase_f_completion.md`. |
| TD15 | Industry propagation (Phase F) never assesses peer-specific direction — every propagated implication copies the source's direction unchanged, paired with a research task instead | **LOW** | Deliberate: direction inversion is an economic-mechanism inference this platform has never allowed a hardcoded rule to make. The research-task queue this creates has no automated consumer yet. See `reports/phase_f_completion.md`. |
| TD16 | `industry_reasoning.propagate_implication` untested against real production data | **LOW** | Same class of caveat as TD13 — MockProvider/synthetic-DB tested only, real-world behavior (actual entity-name match rate, real propagation volume) not yet observed. |

---

## Repository Health

- **Documentation**: STRONG. Every parser and engine carries an inline
  rationale docstring explaining WHY, not just what; `HANDOFF.md` has
  been kept current across every session boundary; the `docs/` directory
  now holds a complete, cross-referenced research history. Watch item
  only (not a recommended action, per "architecture is frozen, no new
  planning documents"): the `docs/` directory has grown to 20+ files —
  fine today because it's well cross-referenced, but worth a light index
  pass if it keeps growing, NOT a reorganization now.
- **Code organization**: GOOD. Clean `src/ngxrot` package boundary;
  `scripts/` as thin CLI entry points; no hardcoded experiment parameters
  in source (verified pattern — everything runs through `configs/*.toml`).
  One minor, material fix (not a reorg): `dol_parser.py` vs
  `dol_price_parser.py` vs `dol_eps_parser.py` naming is close enough to
  confuse a future contributor — worth a one-line cross-reference comment
  in each file's docstring pointing to the others, nothing more.
- **Testing**: WEAK — the one dimension genuinely below institutional bar
  with a clear, bounded fix. See E10. This is the single Repository
  Health recommendation that materially improves the platform; every
  other health dimension is already strong enough that further
  investment there would be polish, not repair.
- **Maintainability**: GOOD given current scale. `scripts/` has grown to
  40+ files, many single-purpose one-off harvest/build scripts. No
  cleanup action recommended now — consolidating them would be scope
  creep against "disciplined execution," and every one of them remains
  independently re-runnable (idempotent, resume-safe) per the platform's
  established pattern, which is the property that actually matters.
- **Reproducibility**: EXCELLENT — the platform's standout strength.
  Seed registry with bit-identical rerun verification, immutable
  experiment registry, bitemporal PIT vintages, config-driven (never
  hardcoded) experiment parameters. No improvement recommended; this
  dimension is already ahead of typical practice.

---

## Six-Month Execution Sequence

Ordered for realistic, disciplined execution — Critical items unblock
before the things they gate, not by calendar month.

1. ~~**E3** (version control)~~ — DONE 2026-07-22.
2. ~~**E1** and **E2** (engine extensions for C1/C4)~~ — DONE 2026-07-22,
   both rehearsed.
3. **R1** and **R2** (pre-register and run H-010, H-011) — UNBLOCKED,
   the approved research wave, confirmed as the right next step after
   the 2026-07-22 capability review (deferring them for E15 was
   considered and rejected — see the update note at the top of this
   document). Sequential per the ≤2-active-hypotheses rule if both are
   drafted together, or run one first if bandwidth is tight.
4. **E4** (daily capture scheduling) — can and should happen any time in
   parallel with the above; pure operational risk reduction, zero
   research dependency.
5. **E15** (unified PIT company/security panel) — parallel, non-gating
   infrastructure track; positioned for Wave 4's engineering prep, not
   before Wave 3.
6. **R3** (regime-classification methodology) — begins once an R1/R2
   slot frees up, or immediately as INFRASTRUCTURE work (the code and
   its own validation) even before it becomes a live hypothesis. Highest
   long-term platform-value item identified across both reviews.
7. **E10** (minimal PIT regression tests) — after E3, opportunistically;
   does not block research and should not be allowed to.
8. **E5 / E6** (EPS-dividend parser retry; corp-actions extraction
   validation) — scheduled as their own dedicated efforts when bandwidth
   allows; both have already failed once under-scoped, so do not squeeze
   them into leftover time between research waves.
9. **R4** (corp-action event scoping) — a short task, can run any time
   before a C3 decision is needed.
10. **E7, E8, E9** (vwap triage, rename verification, DOL precision
    restatement) — medium-priority hygiene, fill-in work between the
    above.
11. **R7** (H-002 ledger hygiene) — trivial, do whenever convenient.
12. **E11, E12, E13, E14, R5, R6** — low priority / explicitly blocked;
    revisit only after the above clears or a trigger condition (stated
    against each) is met.

## AI Intelligence Layer Tasks (2026-07-22, separate track — not a V1
architecture change; the quantitative research engine above is unaffected)

**AI-1 — Resume the Phase C pilot past Gemini's free-tier quota — DONE
2026-07-26.** Resumed cleanly via `scripts/run_phase_c_pilot.py` (registry
-sourced `GEMINI_API_KEY`, no quota errors this run — daily limit had
reset): all 9 remaining documents processed, 0 new quota hits.
`scripts/validate_phase_c_extraction.py` regenerated
`reports/phase_c_completion.md` against the FULL pilot set (17 documents
with LLM-extracted facts): **precision 90.0%, recall 100.0%** vs. Phase
B's deterministic ground truth (9/10 overlapping numeric values agree
exactly; every disagreement disclosed, not summarized away — doc 10788
MOFIREIF: Phase B 3.7468 vs LLM 9.7192, unresolved, flagged for human
review, not silently picked one). Self-critique gate ran completely on
every draft (136/136 expected critique rows = 17 × 8): 3/17 implications
`blocked_by_self_critique`, 14/17 `unvalidated_ai_interpretation`. 2/17
facts failed grounding (forced to 0.0 confidence, kept not discarded).
Full numbers: `reports/phase_c_completion.md`,
`reports/phase_c_pilot_summary.{md,json}`. No further action needed on
this item — closed.

*(Original description, for history:)* Resume the Phase C pilot past Gemini's free-tier quota (pipeline
now fully resumable, 2026-07-22 — the resume-skip gap noted below is CLOSED)
- Description: owner supplied `GEMINI_API_KEY`; the pilot ran for real and
  produced real results (100% precision/recall on the numeric overlap with
  Phase B, a real self-critique catch on GTCO's dilutive offer, a
  pre-existing Phase B misclassification surfaced on NEM — full detail
  `reports/phase_c_completion.md`), then hit Google's free-tier quota (20
  `generate_content` requests/day/project for `gemini-3.6-flash`,
  confirmed via the API's 429 response) partway through document 7 of 18
  (8 documents' worth of data actually landed — one, UCAP, mid-critique).
  **Hardened same day**: `run_phase_c_pilot.py` is now fully resumable
  (`document_processing_status` table + `pipeline_status.py`, cross-
  checked against real data so a stale status can never cause duplicate
  extraction), `QuotaExceededError` is detected and fails fast (no wasted
  retries), and a JSON+Markdown pilot summary is written after every run.
  Backfilled status for the 7/8 pre-hardening documents — `remaining_
  doc_ids` now correctly reports 9 remaining (1 resume — UCAP just needs
  its critique step — plus 8 never-touched).
- Why it matters: closes out the real precision/recall/consistency
  numbers on the full 18-document sample instead of a partial 8, and the
  hardening means every FUTURE quota-limited run (this will recur on the
  free tier) resumes cleanly with no manual intervention.
- Dependencies: owner decision — wait for daily quota reset, upgrade to a
  paid tier, or reduce further via `-n`. No engineering blocker remains.
- Engineering effort: NONE remaining for resumability itself — just
  running `python -u scripts/run_phase_c_pilot.py` again once quota allows.
- Files: `scripts/run_phase_c_pilot.py`, `scripts/validate_phase_c_extraction.py`,
  `src/ngxrot/documents/pipeline_status.py`, `src/ngxrot/documents/pilot_summary.py`,
  `reports/phase_c_completion.md`, `reports/phase_c_pilot_summary.{md,json}`.
- Completion criteria: real precision/recall/consistency statistics in
  `reports/phase_c_completion.md`, reviewed by the owner before Phase D
  (which per the architecture doc's own phasing is now partially absorbed
  into what was just built — remaining Phase D/E/F/G scope needs
  re-scoping once real pilot numbers exist, not before).

**AI-2 — OCR engine decision** (inherited, unresolved since 2026-07-16):
blocks the 36% of the Phase A archive with no usable text layer,
including the specific GTCO/Zenith FY2023 anchors named in the
architecture doc (confirmed OCR-blocked during Phase C's pilot-set
selection — see `reports/phase_c_completion.md` §3).

*No new hypothesis ID beyond H-010/H-011 is created by this document. No
architecture change is proposed. This is the complete remaining task
inventory against the frozen V1 architecture as of 2026-07-22.*
