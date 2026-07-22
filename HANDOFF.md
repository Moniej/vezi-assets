# FUND ALPHA — SESSION HANDOFF (2026-07-22)

Read this first in a fresh context. Strategic history: `docs/` + auto-memory.
Working dir: `C:\Users\nonso\Desktop\vezi assets\ngx-rotation` (not a git repo).

**PROGRAM STATUS (2026-07-22): 9 hypotheses tested, 0 validated, 9
rejected. Architecture is FROZEN as V1 — do not redesign it. C1 (Pooled
Momentum) and C4 (Size) are APPROVED as the next research wave, but
BLOCKED on two small engineering tasks that don't exist yet (E1/E2 below)
— draft neither H-010 nor H-011 until those land.**

**START HERE: `docs/EXECUTION_BACKLOG.md`** — the current, actionable
task list (Critical/High/Medium/Low, research vs engineering, technical
debt ranked by risk, a 6-month execution sequence). Read it before
touching anything. Immediate next 3 items per its sequence: (1) `git
init` — this repo has NO version control, a present-tense risk,
(2) build the multi-cohort extension to `backtest_xs.py` (unblocks
H-010), (3) build the market-cap-panel loader + `xs_size` method
(unblocks H-011).

Background reading (all 2026-07-22, do not re-derive — cross-referenced
from the backlog): `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`
(per-hypothesis failure classification), `docs/WAVE_3_RESEARCH_DIRECTIONS.md`
(candidate scoring), `docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md`
(dependency map + maturity scores + 3-year roadmap),
`docs/PLATFORM_ARCHITECTURE.md` (short-form module summary).

## What this project is

**Fund Alpha**: an AI Investment Intelligence Platform for Nigerian equities
(owner directive 2026-07-21/22 — full 9-module target architecture in
`docs/PLATFORM_ARCHITECTURE.md`, modules 1-3 live, modules 4-9 explicitly
GATED behind having ≥1-2 validated factors — do not scaffold them early).
The existing research engine IS the platform core; the hypothesis workflow
is the Factor Validation Engine, unchanged. Success metric = validated
independent factors (currently **0**; 9 honest rejections — process
working, not stalling). Concurrency rule (owner): **never more than 2
active hypotheses at once**; each wave completes before the next begins.
Every prereg includes an "Expected Interaction with Existing Factors"
section; every completed experiment updates `docs/FACTOR_REGISTRY.md`
(the permanent knowledge base — READ IT before proposing anything, it has
full evidence trails and explicit successor-design guidance per
rejection). Charter: `docs/FUND_ALPHA_CHARTER.md`.

## WAVE 1 + WAVE 2 COMPLETE (2026-07-22): H-006 through H-009 all REJECTED

Full results in `docs/FACTOR_REGISTRY.md`. Summary, most informative first:

- **H-009 (turnover-budgeted momentum, annual/semiannual)**: the wave's
  most nuanced result. Turnover reduction WORKED — net excess flipped
  positive (+2.66%/yr vs H-007's −6.26%/yr), 6/6 grid cells positive,
  positive in all 3 regimes incl. OOS. But placebo p=0.069, a NEAR-MISS
  against the 0.05 bar (no threshold relaxed). Diagnosis: annual cadence
  over 9 years yields only ~9 independent decisions — a POWER problem,
  not a sign or cost problem. Do NOT rerun this exact design; pool
  multiple staggered momentum implementations or use an overlapping-
  cohort design to raise bet-count while keeping turnover low (new ID).
- **H-006 (PEAD)**: High-confidence rejection (862 decisions, corrected
  p=0.000 on the gross effect) — the reaction-magnitude RANKING carries
  no selection skill over any cohort event; capped-slot book turnover
  ~10x the estimate. Successor: event-MEMBERSHIP-only design (new ID).
- **H-007 (quarterly momentum)**: gross effect real but ~3x smaller than
  its own cost; statistically noise (placebo p=0.644). Directly
  motivated H-009.
- **H-008 (low-volatility)**: the cleanest, simplest rejection — a
  STATISTICALLY ROBUST NEGATIVE tilt (6/6 cells Holm-significant in the
  wrong direction), not merely an absent effect. Likely cause: NGX
  2016-2026 has had violent regime transitions (FX crisis, COVID, float)
  that reward risk-taking over the calm backdrop low-vol needs. A
  regime-CONDITIONAL retest (e.g. post-2023 stabilization only) would be
  a legitimate new hypothesis; an unconditional retest is not.

Built this wave: `src/ngxrot/backtest_xs.py` — cross-sectional per-stock
engine (rank/vol/event-book modes), `engine.type = "cross_sectional"` in
`runner.run_resolved`/`phase4.py`, inheriting every guard unchanged.
Extended mid-wave: `xs_vol` signal method + annual/semiannual rebalance
cadence, both synthetically rehearsed before real use
(`scripts/rehearse_xs_engine.py`, `scripts/rehearse_xs_engine_v2.py`).
The v2 rehearsal caught a bug in my OWN test design, not the engine: a
"vol-neutral null panel" wasn't actually neutral because variance drag
creates a real link between volatility and compounded return that the
test hadn't compensated for — fixed before trusting the result. Also
fixed this session: `ic_report.py` had H-001's hypothesis text hardcoded
into every memo since H-003 (quantitative content always correct; only
the prose was wrong) — now pulls the ledger description live.

## PARALLEL ENGINEERING THIS SESSION (owner-approved, ran alongside research)

- **Corp-actions archive: DONE**, 11,187/11,546 (97%; remainder are
  permanent 404s, same pattern as the pricelist gaps).
- **Market-cap panel: DONE, validated** —
  `data/reference/market_cap_panel.csv` (328,023 rows / 218 symbols /
  2,182 days, 2016–2026, from PRICES_LIST2). Implied-share-count stability
  check clean (0.39% day-over-day jumps >2%). Unlocks Size factor +
  eventual cap-weighted benchmark. Full-issue cap only (not float-adjusted
  — shares-outstanding/free-float remains a separate backlog item).
- **EPS/P.E. parser: ATTEMPTED, NOT VALIDATED, deprioritized.** Two
  extraction heuristics tried against the DOL's crowded trailing columns;
  neither cleared the 95%-pass validation bar (58% and 34%). High-price
  names (DANGCEM, NESTLE, MTNN, TOTAL...) have blank fields on many days
  that both heuristics silently misread. Full writeup + exact failure
  modes: `reports/eps_pe_extraction_status.md`. Also found: the DOL's
  "Div" column contradicts the verified GTCO FY2023 anchor (real payout
  ₦2.70; naive read returned ₦0.50 — the par-value column bleeding
  through) — do not trust that region for dividend cash amounts; the
  corp-actions PDF pipeline remains correct for that.

## MILESTONE: COVERAGE GATE v2 PASSED (2026-07-21)

**12 ready years (2015–2026), no threshold changes.** Freeze doc:
`docs/DATA_FREEZE_2026-07-21.md` — preregs pin `vintage_date=2026-07-21`,
`requires_coverage_gate=true`, IRU v2. Panel: 320,159 rows / 308 tickers /
2,933 days @ conf 0.9 across 3 validated sources (ngx_pricelist_v1;
ngx_dol_v1 = 170 close-only gap days; ngx_list2_v1 = 7 days).
Pricelist parser is now v2 (2026-07-21: glued VOLUME/VALUE token repair —
see pricelist_parser.py docstring); daily --delta ingests land as
ngx_pricelist_v2. Historical v1 rows stand (54 glued rows restated via
scripts/restate_glued_volumes.py, verified identical to v2 reparse).
Day-completeness 95.1–100% every full year. Equity jump residue: 3 flags in
12 years (the other 113 are ETFs/sukuk — outside the ±10% band premise and
outside the IRU).

## Non-negotiable rules (unchanged — SQL/config-enforced, do not soften)

1. Every hypothesis/factor: pre-registered (criteria + untouched OOS before
   any run), unique ID, mechanical verdicts.
2. Immutable registry (`data/registry.sqlite`); experiments ONLY via
   configs (`scripts/run_experiment.py` / `runner.run_resolved`).
3. Gate thresholds: IC decision only. The gate re-evaluates on every equity
   ingest; runner refuses gated configs if it regresses.
4. Unknown stays unknown; never fabricate; primary sources for dates;
   archive-first; append-only PIT with restatement vintages (readers:
   `db.*_asof`, latest-vintage-wins — diagnostics dedupe the same way).
5. Priority test for ANY work: "does this increase the probability of the
   next validated factor?"

## IMMEDIATE NEXT STEPS (wave 3 — not started, awaiting owner direction)

9 hypotheses tested, 0 validated, 9 rejected — every rejection carries
specific successor guidance in `docs/FACTOR_REGISTRY.md`. Do NOT rerun any
prior design unchanged (esp. H-009 — its near-miss placebo is a power
problem, not a coin flip worth retrying). Live successor candidates:
- **Pooled/overlapping-cohort momentum** (H-009 successor): raise
  independent bet-count while keeping per-implementation turnover low —
  the most directly evidence-motivated candidate in the whole program so
  far (H-009 showed the SIGN and PLATEAU are right; only power is missing).
- Event-MEMBERSHIP-only PEAD (H-006 successor, unranked, turnover-costed
  differently from the capped-slot book).
- Regime-conditional low-vol (H-008 successor, e.g. post-2023 only, as
  its own hypothesis with its own OOS split — NOT the same unconditional
  design).
- A genuinely new family not yet touched: Value (E/P) or Dividend Yield
  once the DOL EPS/dividend parser is re-attempted and validated (see
  backlog); Size using the now-validated market-cap panel.
Draft as full pre-registrations (economic rationale + Expected Interaction
section) and show the owner before running, per convention. Consider
whether "pooled momentum" deserves priority given how close H-009 came —
it's the strongest lead this program has produced to date.

## Backlog (priority order)

- PRICES1 parser v2: fix glued VOLUME+VALUE at source (done 2026-07-21;
  monitor for recurrence on new daily ingests).
- DOL-day close precision restatement via gainers cross-check (177
  single-source days; gainers 'prev' column = unadjusted official close).
- vwap_inconsistent warn backlog (469 rows incl. zero-value days
  2015-05-28 / 2017-07-12 — chips pending).
- Verify/apply 49 candidate renames (`data/reference/symbol_renames.csv`).
- EPS/P.E. parser retry as its own scoped session (per-format-era
  calibration needed — see `reports/eps_pe_extraction_status.md`).
- Shares Outstanding harvest (capacity, float-adjusted Size); T-bill curve.
- Daily-capture scheduling (user-gated): `scripts/daily_capture.py` MUST
  run every trading day; each missed day is lost forever.
- Corp-actions OCR decision (user-gated; archive itself is now 97% done).

## Key machinery + hard-won parsing facts

`src/ngxrot/`: db (bitemporal) · runner · phase4 · ic_report · universe
(IRU v2) · coverage (gate) · page_layout (char-level) · pricelist_parser ·
**dol_price_parser** ('Market Price' col = official close, calibrated per
page by header x1; DOL 'Qty' = LAST TRADE size, NEVER daily volume) ·
**list2_parser** (sector-format price list; name→ticker via era-matched DOL
security names) · **gainers_parser** (officially ADJUSTED bases printed in
parentheses; zip naming unreliable — index by INTERNAL start/end dates) ·
event_pipeline · alpha_engine (honest no-position shell).

- pdfplumber `page.chars` DRAW ORDER preserves text runs — use it over
  geometric chaining for interleaved columns (some bd dates even live in a
  vertically offset glyph band; match page-wide date runs to rows by top-y).
- Some DOLs are intraday prints (2022-03-16: 34% of closes differ from
  final; ~1.7% of days, undetectable per-file) — documented risk on
  single-source days (`data_quality_log` 'single_source_day').
- index_levels contains HOLIDAY PADDING (carry-forward rows on Dec 25
  etc.) — the verified market calendar = index days whose value CHANGED.
- PRICES1 PCLOSE = officially adjusted base → close/pclose is the official
  within-band return (jump-scan certification source b).
- PRICES1 glued-token bug: wide VOLUME+VALUE merge into one word (volume
  ~1e17+, value NULL). Diagnostics: `implausible_volume` (>1e12) +
  `vwap_inconsistent` ([0.25,4]×close), computed on latest vintage.
- Jump scan evidence hierarchy: (a) spans verified missing market day →
  legal multi-session; (b) NGX-certified within-band off adjusted base
  (gainers OR pclose); (c) closure/earnings ±3bd.
- Reference calendars: `exdiv_closure_calendar.csv` (1,044 closure events) ·
  `gainers_transitions.csv` (138k mover rows, 5,338 adjusted bases) ·
  `official_prev_close.csv` (2,763 days) · `earnings_calendar.csv`.
- Sector-level research is DEAD (breadth math:
  `docs/RESEARCH_MEMO_PERSTOCK_PIVOT.md`). Never propose sector variants.
- NGX doclib SharePoint is OPEN (OData), primary source:
  `_api/Web/Lists/GetByTitle('XFinancial_News'|'DownloadsContent')`;
  files at `doclib.ngxgroup.com/DownloadsContent/<Title>.<ext>`.
  investing.com: rate-limited; cross-check only.
- Launch python via PowerShell (`python -u`), NOT Git Bash (exit 127).
- Pending user decisions: tesseract OCR; daily-capture scheduling;
  parallel-FX + broker research (ethics/licensing-gated).
- Open queue behind H-006/H-007: F4 liquidity premia, F6 dividend capture,
  F13 size/low-vol/reversal, Discovery module (post-breadth, per design doc).
