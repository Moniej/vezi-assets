# Pre-Registration — H-017: Dividend Payer-Status

*2026-08-04. Pre-registration only. No implementation, no results have
been viewed. Follows the same institutional methodology as
`docs/PREREG_H-016_liquidity.md`. Written under the platform's now
empirically-hardened methodology (`docs/METHODOLOGY_HARDENING_2026-08-04.md`)
— Section 9 below discloses, and does not modify, the four known
limitations that audit left open.*

---

## 0. What kind of investigation this is (stated up front)

This is a genuinely new hypothesis, first scoped as Wave 3 candidate C5
(`docs/WAVE_3_RESEARCH_DIRECTIONS.md`, 2026-07-22) and formally designed
as `docs/WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md §3`. It tests whether
a firm's **dividend payer status** (a binary characteristic — has this
firm paid a cash dividend in the trailing 12 months, not how much) is
associated with a different risk-adjusted return within the IRU than
non-payer status. This is deliberately narrower than the yield-based
literature it cites, because dividend YIELD magnitude (DPS/EPS) has
already been attempted and closed as a documented, validated negative
result on this platform (`reports/eps_pe_extraction_status.md` — the
DOL EPS/P.E. parser failed twice, 58.5% then 34.3% pass rate, both
below the pre-declared 95% bar). This hypothesis does not reopen that
question; it tests a coarser, binary characteristic that requires none
of the failed extraction.

---

## 1. Audit of all existing evidence relevant to Dividend Payer-Status

- **H-011 (Size, confirmed)**: the platform's only validated factor.
  Per its own Phase R2 forensic decomposition (H-013/014/015), it is
  concentrated in liquid, low-volatility small caps, with an unresolved
  relationship to momentum — not a clean, independent Size effect (see
  `docs/WAVE5_RESEARCH_STRATEGY_2026-08-04.md §1.2` for the corrected
  framing). **This matters directly for H-017**: established NGX
  dividend payers (banks, consumer staples) are disproportionately the
  LARGEST, most liquid names in the universe — the single largest risk
  named for this hypothesis since it was first scoped (§3.6,
  `WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`), and the reason Section 8
  below makes an orthogonality check mandatory rather than optional.
- **H-016 (Liquidity, rejected in full, both directions)**: no
  standalone liquidity premium found on NGX at whole-universe breadth.
  Relevant because payer-status could equally be explained by liquidity
  rather than size — a distinct decomposition path this pre-registration
  treats as co-equal to the Size check (Section 8), per this task's
  explicit instruction.
- **H-008 / H-012 (Low Volatility, both rejected, wrong-signed)**: rules
  out "payer status is a low-vol proxy" as a mechanism worth pursuing on
  its own terms (there is no confirmed low-vol effect on this platform
  to proxy for) — but does not rule out that payer names happen to be
  low-vol AND that characteristic correlates with something else. Not a
  primary decomposition axis for this hypothesis (per the operative
  task instructions, Size and Liquidity are the two mandatory checks;
  Volatility is noted here as context, not a third mandatory leg).
- **`reports/eps_pe_extraction_status.md`**: closes off yield-magnitude
  entirely, already discussed above.
- **`data/reference/exdiv_closure_calendar.csv`**: the data source this
  hypothesis depends on entirely — see Section 6 (data audit) for a full
  characterization, including a real coverage gap discovered during
  this pre-registration's own data-availability check.

---

## 2. Literature review

- **Bhattacharya (1979)**, *Bell Journal of Economics* — dividend
  signaling theory: dividends are a costly, hard-to-fake signal of
  sustained cash-generative capacity.
- **John & Williams (1985)**, *Journal of Finance* — extends signaling
  theory to a tax-cost framework; dividends remain informative despite
  their tax disadvantage precisely because they are costly to fake.
- **Fama & French (2001)**, *Journal of Financial Economics*,
  "Disappearing Dividends" — establishes payer/non-payer status as an
  economically meaningful characteristic split, separate from yield
  magnitude; the direct methodological precedent for this hypothesis's
  binary framing.
- **Litzenberger & Ramaswamy (1979)**, *Journal of Financial Economics*
  — the original yield-effect literature. **This is a stronger,
  different claim than H-017 makes** — cited for completeness and to be
  explicit that confirming or rejecting H-017 says nothing about the
  yield-magnitude question, which remains closed on this platform for
  data reasons, not theoretical ones.
- **Aivazian, Booth & Cleary (2003)**, *Journal of Financial Research* —
  emerging-market-specific dividend-policy evidence, the most directly
  relevant prior work to NGX's institutional context among the sources
  reviewed.

---

## 3. Frontier / emerging / developed market classification

**Emerging/frontier-market technique with a developed-market
theoretical root**, per `WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md §3.5`,
reaffirmed here. The signaling and clientele mechanisms are universal;
their expected relative STRENGTH is argued to be frontier-specific — in
a market with sparse institutional/analyst coverage and few alternative
yield-bearing retail instruments, payer-consistency as a quality signal
may carry more marginal information than in a developed market already
saturated with dividend-focused fund flows and analyst coverage. This
is stated as a plausible, citable, but **unproven** adaptation for NGX —
a hypothesis to test, not an assumed finding, exactly as the platform's
own frontier-market discipline (established across H-016's pre-
registration) requires.

---

## 4. Economic mechanism

**Why should the market misprice this?** Thin sell-side coverage means
payer-consistency as a quality/cash-generation signal may not be
systematically priced the way it would be in a market with dense
dividend-focused fund flows and analyst dividend-coverage initiation.

**Why would it persist?** Payer status changes rarely — a firm's
underlying cash-generative capacity is genuinely slow-moving, so any
mispricing would not be quickly arbitraged away in a thin,
retail-dominated market with limited institutional capital actively
hunting this specific characteristic.

**Why might it fail to appear at all, or appear for the wrong reason?**
Stated up front, not discovered after the fact: NGX dividend payers are
disproportionately the largest, most liquid names — Section 8's
mandatory orthogonality check exists specifically because a positive
result here could be entirely a relabeled Size or Liquidity effect
rather than new information.

---

## 5. Frontier-market confounds (identified before any data is touched)

- **Size/Liquidity entanglement** (above) — the dominant, explicitly
  pre-declared risk for this hypothesis.
- **Thin-trading/stale-price contamination of the return series feeding
  Sharpe/HAC/placebo** — per `docs/METHODOLOGY_HARDENING_2026-08-04.md`
  Phase M2, real and measured on this exact platform (48-97% zero-return
  days even within the current top-100 IRU). This is a real, present,
  disclosed limitation affecting every hypothesis, H-017 included — see
  Section 9.
- **PIT reliability of the underlying dividend-closure data**: the DOL
  ex-div band this hypothesis depends on is itself extracted from
  scanned/OCR'd or native-text daily official lists; `first_seen` is
  used throughout as the PIT-safe date (public knowledge no later than
  that date), per `scripts/build_exdiv_calendar.py`'s own design — this
  is the same PIT discipline used platform-wide, not a new mechanism.
- **A real, newly-discovered data-coverage gap** — see Section 6.

---

## 6. Data audit (re-verified directly against the live database this
session, not reused from prior documentation without re-checking)

**Correction to the record**: an earlier document in this series
(`docs/METHODOLOGY_HARDENING_2026-08-04.md`, Phase M2) characterized
the `corporate_actions` table's 31 rows (30 `dividend_cash`, 1
`rights_issue`) as real platform dividend data. **Re-verification this
session found this was wrong**: all 31 rows belong exclusively to
tickers `SYNBNKA`, `SYNBNKB`, `SYNBNKC` — confirmed via direct query
against `securities` and `corporate_actions` — which are synthetic test
fixtures (`securities.name = securities.ticker`, no real board/sector
data), not real NGX-listed companies. **`corporate_actions` therefore
contains zero rows of real platform dividend data.** This correction is
disclosed here per this program's standing discipline of catching and
disclosing its own prior overstatements rather than letting them stand
uncorrected; a corresponding erratum should be added to the Methodology
Hardening document.

**The real, usable data source is
`data/reference/exdiv_closure_calendar.csv`** (1,044 rows, 217 distinct
symbols pre-rename-canonicalization, 214 post-canonicalization),
DOL-derived per `scripts/build_exdiv_calendar.py`: each row is a
distinct (symbol, closure-of-register date) pair, with `first_seen`
recording the earliest Daily Official List that publicly showed the
closure — a genuinely PIT-safe field, used throughout this design.

**Active-payer breadth, measured directly this session** (not assumed,
per Wave 4's own flagged-but-unmeasured gap): running the actual
`universe.iru_members()` function at 41 quarterly formation dates from
2016-03-31 through 2026-03-31, counting symbols with a closure event
within the trailing 365 days (via `first_seen`, PIT-safe) intersected
with IRU membership:

| Period | Payers within IRU (range) | Non-payers within IRU (range) |
|---|---|---|
| 2016-Q1 – 2018-Q1 | 53-66 | 29-47 |
| 2018-Q2 – 2019-Q2 (thinning) | 5-61 | 39-95 |
| **2019-Q3 – 2021-Q2 (coverage gap, see below)** | **0** | **92-100** |
| 2021-Q3 – 2026-Q1 | 55-65 | 35-49 |

**A real, previously undocumented data-coverage gap was found and
diagnosed during this pre-registration**: from 2019-Q3 through
2021-Q2 (7 consecutive quarterly formation dates), the measured
active-payer count is exactly zero. Investigation of the raw DOL
staging files (`data/staging/dol_exdiv/*.csv`) for this window confirms
the underlying files exist (720 files present for 2019-2021) and
contain populated `ex_div` values — but those values are **stale,
historical closure dates already on record from 2018 or earlier**
(spot-checked: `2020-03-16.csv` shows `ex_div` values ranging from
1992 to 2018, none newer), not new 2019-2021 closures. **This means the
DOL's ex-div band appears to have stopped reflecting NEW closure events
for roughly 21 months, not that NGX-listed companies collectively
stopped paying dividends** — a market-wide, universal 21-month dividend
freeze across all ~217 tracked payers is not a plausible economic
explanation. The root cause (a real source-side reporting gap, vs. a
platform-side extraction miss) was **not** further diagnosed in this
pre-registration — that would be its own audit, out of scope here.

**Design response to the coverage gap (mechanical, not a hand-picked
carve-out)**: the signal implementation applies the platform's own
standard minimum-breadth eligibility floor (≥10 eligible names,
matching `_eligible()`'s convention used by every other `xs_*` method)
to the payer-status count specifically. This **automatically and
mechanically excludes** every formation date inside the coverage gap
(payer count of exactly 0) without requiring a specially-chosen date
range — the same generic rule that would exclude any other
low-breadth date, applied consistently. This is disclosed here as a
design decision made BEFORE implementation, not discovered after
seeing a result.

**Required data**:

| Dataset | Status |
|---|---|
| `data/reference/exdiv_closure_calendar.csv` (real, 217 symbols) | Already Available |
| `equity_prices` panel | Already Available |
| IRU v2 eligibility rules | Already Available |
| `data/reference/market_cap_panel.csv` (for the mandatory Size orthogonality check) | Already Available |
| ADTV60 panel (for the mandatory Liquidity orthogonality check) | Already Available (`panel["adtv60"]`, reused unmodified) |
| Dividend YIELD magnitude (DPS/EPS) | Not Feasible — documented, closed negative result; explicitly out of scope |
| Free-float / shares-outstanding | Not required |

---

## 7. Statistical plan

The full standard suite, identical in kind to H-011 and H-016:
persistence-preserving placebo (fixed ticker relabeling, one permutation
per iteration, applied across all formation dates — the same scheme
`backtest_xs.py` already uses for `xs_rank`/`xs_vol`/`xs_size`/
`xs_liquidity`), HAC/Newey-West inference (supplementary context, per
the Frontier Methodology Audit's finding that this is not part of the
automatic `phase4` orchestration — invoked explicitly in this
hypothesis's run script, consistent with how H-016 was evaluated),
Deflated Sharpe Ratio against the existing real-rf trial pool
(`experiments/dsr_realrf_evidence_2026-08-02.json`), Holm/Benjamini-
Hochberg correction across the stability grid, walk-forward validation
with an untouched final-OOS regime, and the standard failure-condition
checks (`cost_drag_eliminates_excess`, `placebo_performs_similarly`,
`oos_performance_collapses`, `single_regime_dependency`,
`single_sector_dependency`).

**One hypothesis-specific addition, made mandatory per this task's
explicit instruction**: a full orthogonality assessment against BOTH
H-011's Size score and the ADTV Liquidity score, run BEFORE any
interpretation of a positive base-test result is offered (Section 8).
A positive result that is not meaningfully independent of Size or
Liquidity must be reported as such, not claimed as new information —
this is not a lighter-weight courtesy check, it is a required gate on
interpretation.

**Portfolio construction, a genuine departure from every prior `xs_*`
hypothesis**: payer-status is a binary characteristic, not a ranked
continuous score. The long leg holds **every** IRU-eligible active
payer, equal-weighted (not a fixed top-N) — matching the
characteristic-portfolio convention of Fama & French (2001), not the
rank-portfolio convention of H-007/H-011/H-016. This is implemented by
returning a score Series containing ONLY eligible-payer tickers
(each valued identically) and setting `portfolio.top_n` large enough
(200, above the IRU's own 100-member cap) that it never binds — the
existing `targets_from_scores()` selection code is reused completely
unmodified.

---

## 8. Mandatory orthogonality assessment against Size and Liquidity

*Required by this task's explicit instruction, and consistent with
Wave 4's own original design note that this be "a lighter-weight
version of the interaction-forensics discipline Phase R2 established,
applied prospectively rather than retrospectively."*

**8.1 Correlation check (unconditional, reported regardless of the base
result).** At every formation date, compute the Spearman rank
correlation between (a) the binary payer-status flag and (b) the
continuous Size z-score (from `size_scores()`, unmodified) restricted
to the same IRU-eligible population; repeat for (c) the continuous
Liquidity (ADTV) z-score. Report the full cross-date distribution
(mean, median, IQR), not a single pooled number — disclosed regardless
of its value, per Wave 4's own instruction, whether the base result is
positive, negative, or null.

**8.2 Bucket decomposition (run only if the base single-sort test
clears the confirmation bar in Section 10 — an unconditional null does
not need decomposing, though the correlation check in 8.1 is still
reported).** At every formation date, split the IRU-eligible population
into Size-bucket halves (median split on the Size z-score) and,
independently, into Liquidity-bucket halves (median split on the ADTV
z-score). Within EACH half separately, re-run the identical
payer-status long-only test (long eligible payers within that half,
vs. an EW benchmark of that half) and evaluate placebo/Sharpe/HAC
within each half, mirroring the Phase R2 (H-013/014/015) double-sort
discipline, applied here prospectively rather than retrospectively.

**8.3 Decision rule — the four-category classification this task
requires**:

| Outcome pattern | Classification |
|---|---|
| Base test rejects (fails Section 10's confirmation bar) | **Null result** — no decomposition needed beyond the unconditional correlation report (8.1) |
| Base test confirms; effect holds in BOTH Size-bucket halves AND both Liquidity-bucket halves, with correlations in 8.1 not concentrated at the extremes (no |ρ| consistently ≥0.6, the same threshold H-016 §11.1 used against H-011) | **Genuinely independent dividend effect** |
| Base test confirms; effect present ONLY in one Size-bucket half (or correlation with Size is consistently strong, |ρ|≥0.6) | **Dividend effect explained by Size** |
| Base test confirms; effect present ONLY in one Liquidity-bucket half (or correlation with Liquidity is consistently strong, |ρ|≥0.6) | **Dividend effect explained by Liquidity** |
| Base test confirms; mixed pattern (holds in one Size half AND fails the Liquidity decomposition, or vice versa, or partial/ambiguous per-bucket significance, mirroring H-014's own disclosed ambiguity) | **Partially explained — reported honestly as ambiguous, not forced into a clean bucket, per the same practice used for H-013–H-015's nuanced verdicts** |

This decision rule is fixed now, before any data is viewed for this
hypothesis's own test.

---

## 9. Disclosed methodology limitations (per
`docs/METHODOLOGY_HARDENING_2026-08-04.md` — treated as disclosed
limitations only; methodology is **not** modified for H-017)

1. **Bonus/scrip-issue price adjustment is not implemented** in the
   primary engine. If any current IRU-eligible name underwent an
   unadjusted bonus issue during the sample window, its raw return
   series could carry a spurious one-day repricing not reflecting
   actual investor experience. Not fixed here, per explicit
   instruction; disclosed as a standing limitation affecting this
   hypothesis exactly as it affects every prior one.
2. **Cross-sectional ranking methodology remains mixed** (z-score in
   `backtest_xs.py`'s continuous-score functions vs. percentile rank in
   `signal.py`'s index-level engine). **Not directly applicable to
   H-017's own score function**, since payer-status is a binary
   membership flag, not a ranked continuous score — there is no
   z-score/percentile-rank choice to make for the payer-status
   selection itself. It IS applicable to the Size and Liquidity scores
   used in Section 8's decomposition (both use `backtest_xs.py`'s
   z-score convention, unmodified, per this task's explicit
   instruction not to change methodology mid-hypothesis).
3. **No winsorization exists anywhere on the platform.** Not applicable
   to the payer-status flag itself (a binary 0/1 has no outliers to
   winsorize); applicable to the Size/Liquidity continuous scores used
   in the decomposition, disclosed and unmodified.
4. **Thin-trading measurement remains an open research area** — no
   LOT/Amihud/Corwin-Schultz proxy has been implemented; the existing
   ADTV-based Liquidity score (used in Section 8's decomposition) is
   the same proxy tested and found non-confirming in H-016, disclosed
   as a known, unresolved measurement-choice limitation rather than
   silently assumed adequate.

---

## 10. Confirmation criteria (all required)

Matching H-011/H-016's six-criterion template exactly, applied to the
single long-payers-vs-EW-IRU leg:

1. Base-cell (quarterly rebalance, standard config) net-of-cost excess
   return is positive in the development window.
2. Stability-grid plateau: a majority of the pre-registered grid cells
   (rebalance × any secondary grid dimension specified in the executable
   config) show the same sign as the base cell.
3. At least one grid cell survives Holm OR Benjamini-Hochberg correction
   at α=0.05.
4. Placebo p-value ≤ 0.05 (persistence-preserving, fixed relabeling).
5. Final-OOS regime excess return is positive and not sign-reversed
   from development (per `failure_conditions.oos_performance_collapses`,
   retention floor 0.25).
6. No single regime or single sector accounts for more than the
   platform's standard failure-condition share thresholds
   (`max_single_regime_share=0.8`, `max_single_sector_share`, per the
   executable config).

**Plus the mandatory seventh requirement (Section 8)**: the Spearman
correlations against Size and Liquidity must be reported and disclosed
regardless of value, and confirmation must be accompanied by the
explicit four-category classification from Section 8.3 — a positive
base result classified as "explained by Size" or "explained by
Liquidity" is **not** treated as a confirmed independent factor,
regardless of how cleanly it clears criteria 1-6.

---

## 11. Rejection criteria (any one suffices)

- Placebo p ≥ 0.05.
- Final-OOS excess negative or sign-reversed from development.
- Base result is nominally positive but Section 8.3 classifies it as
  fully "explained by Size" or fully "explained by Liquidity" — recorded
  as a distinct, separately logged rejection reason ("construct validity
  failure"), not conflated with "no effect found," per the same
  practice used for H-013–H-015.
- Fewer than 10 eligible active payers at a majority of grid-cell
  formation dates (a structural breadth failure, distinct from a
  signal-quality rejection) — per the platform's `capacity_below_minimum`
  vs. signal-quality distinction in `failure_conditions.py`.

---

## 12. Comparison against every previously tested hypothesis — independence check

| Hypothesis | Relationship to H-017 |
|---|---|
| H-001–H-010 (Momentum/Event/Macro family, all rejected) | No mechanistic overlap — H-017 is a characteristic-tilt claim, not a price-momentum or event-timing claim |
| H-011 (Size, confirmed) | **Primary decomposition target** — Section 8 |
| H-012 (Regime-gated Low-Vol, rejected) | No direct overlap; low-vol is not a primary decomposition axis for H-017 per this task's explicit two-axis (Size, Liquidity) instruction |
| H-013/014/015 (Size interactions, Phase R2) | Methodological precedent for Section 8's double-sort design, applied here prospectively |
| H-016 (Liquidity, rejected in full) | **Secondary decomposition target** — Section 8; also the source of the ADTV score reused unmodified in the decomposition |

**Could H-017 simply be a proxy for H-011?** This is the single
largest, most explicitly disclosed risk for this hypothesis (Section
4, Section 8) — not a rhetorical question but the entire reason Section
8 exists as a mandatory, not optional, gate.

---

## 13. Rejected alternatives

- **Dividend yield magnitude** — rejected as infeasible per the closed,
  documented DOL EPS/P.E. parser failure; not reattempted here.
- **Dividend-change events (initiation/omission)** — a genuinely
  different, event-study-shaped hypothesis (more similar in structure
  to H-006's PEAD design than to a characteristic tilt); not pursued
  here because Wave 4's own risk assessment (§3.9) flagged that
  status changes are rare enough to create a temporal-power problem
  distinct from a breadth-ceiling problem — a separate hypothesis, not
  in scope for H-017.
- **Total-return sector momentum (H-002)** — dormant, not revived here;
  a distinct hypothesis using dividend data for a different purpose
  (total-return index construction, not characteristic classification).

---

## 14. Multiple-testing treatment

H-017 is treated as an additional trial in the platform's cumulative
multiple-testing pool exactly as every prior hypothesis has been —
Holm/BH correction is applied within its own stability grid (Section
10, criterion 3), and its Deflated Sharpe Ratio is computed against the
same existing real-rf trial pool used for H-013 through H-016
(`experiments/dsr_realrf_evidence_2026-08-02.json`), not a fresh,
more lenient pool.

---

## 15. Known limitations (pre-declared)

- **L1**: Binary-flag information content is coarser than any
  yield-based literature cited — if the true effect exists only at the
  yield-magnitude level, this test is structurally unable to detect it
  and would produce a false negative, not evidence against dividends
  mattering at all. This must be stated in the final report regardless
  of verdict.
- **L2**: The 2019-Q3–2021-Q2 data-coverage gap (Section 6) reduces the
  effective sample by roughly 7 quarters out of a ~40-quarter window —
  a real, if mechanically-handled, power reduction.
- **L3**: Payer status changes rarely by construction — genuine
  transition events (payer↔non-payer) within the sample may be too few
  to separately analyze, a temporal-power concern distinct from the
  cross-sectional breadth already measured adequate in Section 6.
- **L4**: The four disclosed methodology limitations in Section 9,
  carried forward unmodified per explicit instruction.
- **L5**: No independent/external validation of the
  `exdiv_closure_calendar.csv` construction exists — it has been used
  as a diagnostic input before (jump re-matching) but this is its first
  use as a research signal input; internal PIT-consistency was checked
  in Section 6, external validation was not attempted.

---

## Status

Registered as **untested** in `data/registry.sqlite` upon completion of
this document. No experiment has been run. No results have been viewed.
Implementation begins only after this document is complete and
internally reviewed against the checklist above.
