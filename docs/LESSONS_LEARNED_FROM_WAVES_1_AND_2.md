# Lessons Learned from Waves 1 and 2 (H-001 through H-009)

*2026-07-22. Institutional research documentation, produced BEFORE any
H-010 work begins, per CIO-level program review. Nine hypotheses tested,
zero validated. This document treats that as accumulated evidence about
market structure, not as a shortfall — the value delivered is what we now
know, not what we found. All figures trace to the immutable registry
(`data/registry.sqlite`), the hypothesis ledger, and the IC memos in
`reports/`. Where an IC memo's "Hypothesis tested" text is wrong (a
hardcoded-description bug affecting H-003/004/005/006/007's memos,
discovered and fixed 2026-07-22 — quantitative content was never
affected), the correct hypothesis is taken from the ledger, not the memo
prose.*

---

## Phase 1 — Research Retrospective

For each hypothesis: the design, the precise reason it failed, and its
category tags (a hypothesis can carry more than one).

### H-001 — Sector price momentum (3-6M, price-only, sector indices)
- **Result**: Placebo p=0.55 (V1) — real Sharpe (0.81) BELOW the mean of
  100 shuffled-label strategies (0.84). 0/20 cells survived Holm/BH. 100%
  of positive excess from one event (the 2023-24 FX devaluation
  repricing). OOS −38.6%/−15.4% across two variants. Monthly rebalancing
  alone loses −8.1%/yr to costs before any signal question arises.
- **Categories**: No measurable economic effect (placebo decisive) ·
  Statistical power insufficient (~8 effective sector bets/yr) ·
  Incorrect economic assumption (persistent sector dispersion does NOT
  imply exploitable *price*-rank momentum — the dispersion is real, the
  proxy for capturing it was wrong) · Data limitations (5/9 indices had
  full history; NGX Premium never available).
- **Frozen** at the SQL level — no retest under this ID is possible.

### H-003 — Catalyst/event-driven sector rotation
- **Result**: Placebo p=0.198 (better than H-001, still fails). Gross
  excess +2.83%, net −2.29% (cost drag flips the sign). Single-sector
  concentration: NGXOILGAS alone contributed 49% of positive return —
  this was functionally an oil-sector bet dressed as a catalyst strategy.
  0/3 cells survived Holm. ~34 decisions total.
- **Categories**: Statistical power insufficient (inherited the sector
  family's breadth problem; only 3 param cells existed to test) ·
  Ranking/selection methodology weak evidence (33% of cells positive is
  not a plateau) · Gross alpha exists but costs destroy it · Market
  structure incompatible (sector-level catalyst exposure concentrates in
  whichever single sector has active catalysts, defeating
  diversification by construction).

### H-004 — Oil-to-equity lead-lag (Brent → NGXOILGAS)
- **Result**: Placebo p=0.079 — the FIRST near-miss pattern in the
  program (recurs at H-009). Gross +17.02%, net +6.63% — the only
  sector-era hypothesis with POSITIVE NET excess, yet still rejected.
  Single-regime dependency: pre-2023 contributed 100% of positive excess;
  the relationship reversed sign in both post-float regimes
  (shock_2023_24 −11.8%, bull_2025_26 −11.9%). 0/8 cells survived Holm.
- **Categories**: Statistical power insufficient / borderline (placebo
  near-miss under thin sample) · Market structure incompatible /
  regime-dependent (the oil-equity transmission mechanism that held
  pre-2023 did not survive the FX float — a genuine regime break, not
  noise) · Incorrect economic assumption in its UNCONDITIONAL form (a
  lead-lag relationship that only exists in one FX regime is not "no
  relationship," it is a mis-specified one).

### H-005 — MPC announcement-window effects
- **Result**: Placebo p=1.00 — the single most decisive null result in
  the program; the real strategy did not beat a single one of 100 random
  shuffles. Gross excess essentially zero (−0.14%); net excess −39.84%
  — nearly the ENTIRE loss is turnover cost (~11 full-NAV switches/yr at
  ~1.9%/side). 3/3 cells were Holm-significant — but significantly
  NEGATIVE, a robust result, just the wrong sign.
- **Categories**: Gross alpha exists but costs destroy it — the CLEAREST
  example in the program (gross ≈ 0, cost ≈ entire loss) · No measurable
  economic effect (placebo=1.00 leaves no ambiguity) · Implementation
  limitations (11 switches/yr is inherently unworkable at retail costs;
  the design itself, not just the signal, was cost-incompatible).

### H-006 — PEAD (filing-window reaction, ranked, capped event book)
- **Result**: Placebo p=0.842. Gross excess +16.69% (highly significant,
  4/4 cells survive Holm, corrected p=0.000 — the underlying event-driven
  return pattern is REAL). Net excess −20.49% (turnover ~10× the
  pre-registered estimate). Confidence rating **High** — the placebo
  proved specifically that the reaction-magnitude RANKING carries zero
  selection skill: shuffled draws from the same event pool matched the
  real ranking's Sharpe.
- **Categories**: Ranking methodology ineffective — the CLEANEST example
  in the program of this category; the population-level effect is real
  and statistically overwhelming, but the specific ranking rule adds
  nothing · Gross alpha exists but costs destroy it (capped-slot book
  turnover was badly under-estimated) · Implementation limitations
  (construction, not signal, drove the cost overrun).

### H-007 — Cross-sectional 12-1 momentum (per-stock, quarterly)
- **Result**: Placebo p=0.644. Gross +2.18%, net −6.26% (turnover
  1.83×/yr vs 1.2-1.6× estimated). 1/6 cells positive; 0/6 survive Holm.
  OOS −30.3% (the 2025-26 window was a broad bull run in which the
  benchmark itself compounded fastest).
- **Categories**: No measurable economic effect (placebo fails outright,
  so the positive gross number cannot be attributed to selection skill
  with any confidence) · Gross alpha exists but costs destroy it (as a
  SEPARATE, compounding problem even if the effect were real) ·
  Statistical power moderate (35 decisions — adequate breadth, per-stock
  pivot working as designed, but not adequate SIGNAL).

### H-008 — Low volatility (bottom-vol quintile, quarterly)
- **Result**: Placebo p=0.822. 0/6 cells positive; GROSS excess itself
  negative (−8.70%) — not a cost story at all. 6/6 cells Holm-significant
  IN THE WRONG DIRECTION: a statistically robust negative tilt. OOS
  −28.9%.
- **Categories**: Incorrect economic assumption — the calm-market
  precondition behind the low-vol anomaly (leverage-constrained investors
  overpaying for high-beta names) does not describe NGX's 2016-2026
  history, which was dominated by violent regime transitions (2016 FX
  crisis, 2020 COVID crash/recovery, 2023 float/devaluation) that reward
  risk-taking/recovery names instead · Market structure incompatible (an
  unconditional low-vol tilt in a regime-shock-prone market is
  structurally the wrong tool, not an implementation problem).

### H-009 — Turnover-budgeted momentum (12-1, annual/semiannual)
- **Result**: Placebo p=0.069 — near-miss #2, and the closest of the
  program. Net excess FLIPPED POSITIVE (gross +6.10%, net +2.66%). 6/6
  cells positive (100% plateau, best-median gap 1.9% — clean, not a
  spike). Positive in all 3 regimes including untouched OOS (+9.4%). But
  0/6 cells survive Holm (corrected p=0.572); only ~9 independent
  decisions existed in the 9-year dev window at annual cadence.
- **Categories**: Statistical power insufficient — the CLEANEST example
  in the program of this category; sign, plateau, and regime-consistency
  are all correct, only the number of independent bets is inadequate ·
  This hypothesis directly CONFIRMS (not just hypothesizes) that turnover
  reduction fixes H-007's cost problem — the binding constraint simply
  moved from cost to power.

### H-002 — Total-return sector momentum (never tested)
- Still blocked on dividend/total-return data 0 experiments run. Not a
  rejection — a standing gap. Relevant now: EVERY per-stock hypothesis
  (H-006–H-009) used price-only returns; a total-return retest remains
  untested across the entire per-stock program, not just H-002
  specifically.

---

## Phase 2 — Lessons Learned

### What do we now know about NGX?

1. **Transaction costs (~3.8%/round trip retail) are the single most
   validated finding in the program.** They directly contributed to
   rejecting H-001, H-003, H-005, H-006, and H-007 — five of nine
   hypotheses, spanning both sector and per-stock eras, spanning
   momentum, event, and macro-window mechanisms. No factor design on
   this platform is credible without a turnover budget stated up front.
2. **Placebo testing is the program's single most powerful and most
   validated safeguard.** It was the decisive rejection reason (alone or
   jointly) in H-001, H-003, H-005, H-007, H-008, and the specific
   selection-skill question in H-006; both near-misses (H-004, H-009)
   also lived or died on it. Every other check (Holm/BH, regime
   attribution, capacity) is secondary evidence next to this one.
3. **NGX's realized returns are event/regime-concentrated, not smoothly
   distributed.** Every hypothesis with a "single X dependency" flag
   found ONE thing carrying most of the positive return: H-001 (one
   macro event, 100%), H-003 (one sector, 49%), H-004 (one regime, 100%),
   H-005 (one index, 87%), H-009 (one regime, 73%). This is not
   incidental — it is a structural trait of this market across nine
   independent tests spanning six years of data and two very different
   universes (sector indices, per-stock). Any factor design that assumes
   stationary, smoothly-distributed exposure is fighting the market's
   actual behavior.
4. **Statistical power and turnover trade off directly, and this program
   has now empirically demonstrated BOTH failure modes.** Quarterly
   per-stock momentum (H-007) has enough decisions (35) but too much
   turnover cost. Annual per-stock momentum (H-009) fixed the turnover
   cost but fell to only 9 decisions. The "sweet spot" is not at either
   extreme — it likely requires a design that keeps turnover low while
   generating MORE independent bets than a single reconstitution
   calendar allows (e.g., staggered/overlapping cohorts).
5. **The per-stock pivot (breadth ~100 names vs ~8 sector effective bets)
   was the correct structural fix**, but breadth alone does not
   guarantee a testable signal — H-006/H-007/H-008 all had adequate
   per-stock breadth and still failed on selection-skill or
   economic-assumption grounds. Breadth fixes power; it does not
   manufacture alpha.
6. **Regime dependence is not a footnote — it may be the primary
   structural feature of NGX to design around.** H-004's relationship
   reversed sign after the 2023 float. H-008's mechanism required a calm
   regime NGX has not had. H-009's excess concentrated 73% in the
   float-shock regime. A regime-CONDITIONAL research paradigm (rather
   than nine independent unconditional tests) may be a higher-value
   redirection than any single new factor.

### Which assumptions proved false?

- "Persistent sector dispersion implies exploitable price momentum"
  (H-001) — false as a *proxy* claim; the dispersion itself may still be
  real and catalyst-driven (H-003 tried to test the mechanism directly
  and also failed, but for breadth/concentration reasons, not because the
  catalyst premise was disproven outright).
- "The oil-equity relationship is stable enough to trade unconditionally"
  (H-004) — false; it existed pre-2023 and reversed after the float.
- "NGX's leverage-constrained, no-shorting structure guarantees a
  low-volatility premium" (H-008) — false, or at least false
  unconditionally; the mechanism's own precondition (a calm market) does
  not describe NGX's realized history.
- "A capped-slot event book is a low-turnover construction" (H-006) —
  false; continuous entry/exit competition among ranked candidates
  churns far more than a naive per-event cost estimate suggests.
- "Reaction magnitude predicts continuation" (H-006's specific ranking
  claim) — false, decisively (placebo indistinguishable from random
  draws from the same pool).

### Which assumptions remain plausible (not disproven, only untested or
inconclusively tested)?

- Momentum's underlying gross effect at LOW turnover (H-009: sign right,
  plateau clean, only power was missing — this is the strongest
  "plausible, not disproven" finding in the program).
- The oil-equity relationship WITHIN a single FX regime (never tested
  conditionally — only the unconditional pooled version was tested and
  rejected).
- The catalyst/event premise generally (H-003's sector-level
  operationalization failed on breadth/concentration grounds, not
  because catalysts don't move NGX prices — they demonstrably do, per
  the diagnostics work finding officially-adjusted moves throughout the
  price history).
- Total-return effects across the entire per-stock family — genuinely
  untested, not rejected (dividends are invisible to every per-stock
  hypothesis run so far).
- Value, Size, Dividend, Quality, and Corporate-Action families — zero
  hypotheses have touched these; nothing has been learned about them
  either way.

### Which ideas became stronger because of previous failures?

- **Pooled/overlapping-cohort momentum**: directly motivated by H-009 —
  not a hopeful retry, but a design that targets the SPECIFIC, precisely
  diagnosed gap (power) left by a result that got everything else right.
- **Regime-conditional design**: motivated by the cross-cutting
  concentration pattern (see lesson 3/6 above) plus H-004's explicit
  regime reversal and H-008's regime-mismatched mechanism. Two
  independent hypotheses now point at the same structural fix.
- **Total-return retest**: every per-stock hypothesis flagged price-only
  returns as a limitation; this is now a backlog item with real weight
  behind it (banking-sector dividend yields in NGX are large — 8-12%
  historically noted in earlier program memos — and invisible to every
  test run so far).

### Which parts of the engine were validated?

- The **cost model** (retail schedule, per-side rates, VAT/fee stack)
  produced internally consistent, predictable results across TWO
  independently-built engines (sector-level `backtest_lite`/`engine_full`
  and per-stock `backtest_xs`) and NINE hypotheses. This is strong,
  repeated validation of a piece of infrastructure the whole platform
  depends on.
- **Placebo testing** correctly discriminated real-looking-but-fake
  results from genuinely different ones across every hypothesis — most
  visibly in H-006, where it caught a specific methodological flaw
  (ranking adds nothing) that raw significance testing alone (4/4 Holm)
  would have missed entirely.
- **Multiple-testing correction** (Holm/BH) consistently prevented any
  hypothesis from claiming victory off a single lucky grid cell — 0/6,
  0/8, 0/3, 0/6, 0/6 across the rejected hypotheses is the correction
  doing exactly its job.
- **Regime/sector concentration checks** surfaced the single-driver
  problem in every case it existed, which is now recognized (lesson 3/6)
  as a market-level pattern rather than noise, precisely because the
  check fired reliably and consistently.

### Which parts of the engine needed improvement (and were fixed this
session)?

- The FIRST placebo design for the cross-sectional engine (per-formation-
  date score shuffling) was WRONG — it destroyed temporal persistence and
  produced false positives on null synthetic panels, caught during
  rehearsal before touching real data. Fixed via persistence-preserving
  fixed-relabeling. This is a durable methodological lesson: any placebo
  design for a signal with cross-time persistence must preserve that
  persistence structure, or it tests turnover-cost noise instead of
  selection skill.
- A test-design bug (not an engine bug) in the H-008 rehearsal: a
  "vol-neutral null panel" wasn't actually neutral because variance drag
  creates a genuine link between volatility and compounded return that
  the synthetic panel hadn't compensated for. Lesson: even NULL synthetic
  panels need their own correctness check.
- `ic_report.py` had H-001's hypothesis description hardcoded since
  H-003 — quantitative content was always correct, but every memo's
  prose was wrong until fixed 2026-07-22. Lesson: even "just the text"
  parts of a research-reporting pipeline need the same scrutiny as the
  numbers, since institutional memos are read as a whole.

### Which datasets became more valuable after these experiments?

- **Earnings calendar** (10,690 filings): used, and informative in a
  negative way (ranking within it failed) — but event TIMING itself
  remains untested for anything other than reaction-ranking (e.g., a
  membership-only design, or as a regime/catalyst input elsewhere).
- **Market-cap panel** (328,023 rows, validated 2026-07-22): built, never
  yet used in a hypothesis — now the highest-readiness untested dataset
  in the platform (Size family).
- **Ex-div closure calendar** (1,044 events, validated): used for gate
  remediation only — a payer-status signal is buildable from it today;
  dividend AMOUNTS are not (the corp-actions DPS extraction remains thin,
  ~397 rows, mostly unpopulated, never promoted to evidence grade).
- **Corp-actions archive** (11,546 filings, 97% PDF-complete as of this
  session): complete enough to support a corporate-action EVENT-TIMING
  design (buybacks, rights issues, bonus issues) even without the
  amount-level OCR work — a genuinely untested family.
- **Macro/events tables** (MPC decisions, regulatory timeline, FX
  events): used only for H-005 (rejected) — but now a candidate INPUT for
  regime-conditioning other factors, a role never tried.

---

*Continuation: gap analysis, wave-3 candidates, prioritization, and
platform perspective are in `docs/WAVE_3_RESEARCH_DIRECTIONS.md`.*
