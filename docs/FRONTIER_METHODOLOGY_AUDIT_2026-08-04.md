# Frontier Market Methodology Audit

*2026-08-04. Methodology review only — no implementation, no code, no
database writes, no new hypothesis registration, no H-017
pre-registration, no FSI expansion. Part 1 is sourced from a direct
read of `src/ngxrot/stats.py`, `metrics.py`, `costs.py`, `universe.py`,
`coverage.py`, `runner.py`, `phase4.py`, `backtest_xs.py`,
`failure_conditions.py`, `confidence_rating.py`, `riskfree.py`,
`ic_report.py`, `rng.py`, `signal.py`, plus a directory-wide grep for
`synchronous`, `stale`, `thin trading`, `Scholes`, `Dimson`,
`illiquidity`, `zero-return`, `bid-ask`, `microstructure`, `float`,
`survivorship`. Part 2 is sourced from external academic/institutional
literature retrieved this session (cited inline). Every claim below is
labeled as either **[Verified — code]**, **[Verified — literature]**,
or **[Judgment]**; nothing is stated as fact without one of these tags.*

---

## 1. Methodology Inventory

| # | Assumption | Where implemented | Origin / why commonly used | Developed-market origin? | Validated on NGX data? |
|---|---|---|---|---|---|
| 1 | Cross-sectional ranking | `backtest_xs.py` — z-score `(x-mean)/std` then `nlargest`/`nsmallest`, min-population guard `n≥10` **[Verified — code]**. `signal.py`'s index-level engine instead uses **percentile rank** (`rank(pct=True)`), with an explicit code comment: chosen because it is "robust to one sector's outlier return dominating a z-score" **[Verified — code]** | Standard cross-sectional factor-sort methodology (Fama-MacBeth / Fama-French portfolio-sort tradition) | Yes | **No** — the platform's own code contains an internal, undocumented inconsistency: the per-stock engine (used for the confirmed H-011 and every hypothesis since H-007) uses the LESS outlier-robust method, despite the platform's own other engine explicitly warning against exactly this risk |
| 2 | Rebalancing frequency | `REBALANCE_STEP_MONTHS = {monthly:1, quarterly:3, semiannual:6, annual:12}`, config-driven **[Verified — code]** | Standard backtest cadence choice | Yes (cadence itself is universal) | **Yes, indirectly** — H-007/H-009/H-010's own turnover-vs-power tradeoff finding is itself NGX-specific empirical evidence that cadence matters unusually much here |
| 3 | Volatility estimation | Daily simple returns, rolling window (config `vol_lookback_months`), `std() * sqrt(252)` annualization; explicit `obs`-mask excludes forward-filled (non-traded) days from the calculation, with a code comment stating ffilled closes "would understate vol for stale names by injecting zero-return days that never happened" **[Verified — code]** | Standard realized-volatility estimator; sqrt(252) annualization assumes i.i.d. daily returns | Yes | **Partially** — the stale-day exclusion is a real, if informal, non-trading-day-aware design choice; but no test exists confirming residual return series are still free of non-synchronous-trading-induced autocorrelation even after this mask |
| 4 | Transaction costs | Per-side bps schedule from a documented `cost_schedule` table (brokerage, CSCS fee, stamp duty, SEC/NGX statutory fees), VAT applied only to VAT-able lines, some rates marked `confidence="assumed"` **[Verified — code]** | Real-world retail cost-schedule modeling | Cost *categories* are NGX-specific; the *modeling approach* (flat per-side rate) is universal | **Yes, substantially** — this is one of the platform's most NGX-grounded assumptions, and its own registry (`LESSONS_LEARNED...md`) credits it with driving 5+ of the first 9 rejections |
| 5 | Benchmark construction | Equal-weighted over ALL IRU-eligible names at each formation date ("EW-IRU"), explicitly documented as "the investable null strategy, not an index"; **full-issue market cap used everywhere, not float-adjusted** — disclosed in code comments across `alpha_engine.py`, `backtest_xs.py`, `engine_full.py`, `list2_parser.py` as a known limitation **[Verified — code]** | Equal-weighting is standard for null/benchmark comparison in academic factor tests | Yes (equal-weight benchmarking is universal); float-adjustment is *also* universal institutional practice, and its absence here is the gap | **No** — no free-float dataset exists on this platform at all |
| 6 | Placebo/permutation methodology | Two distinct schemes: index-engine (`phase4.py`) reshuffles cross-sectional labels independently **per date**; per-stock engine (`backtest_xs.py`) uses **one fixed ticker-relabeling permutation applied across all formation dates** ("persistence-preserving placebo"), adopted specifically because per-date reshuffling was found (in a 2026-07-22 rehearsal) to destroy temporal persistence and produce false positives via turnover-cost differences rather than genuine information **[Verified — code]** | Randomization-inference / permutation testing, a standard non-parametric robustness check | Universal technique | **Yes** — the specific design (persistence-preserving) was itself empirically motivated by an NGX-specific false-positive the platform caught in its own rehearsal process |
| 7 | HAC / Newey-West inference | `stats.py newey_west_tstat()` — Bartlett-kernel HAC variance, automatic lag rule `lag = floor(4*(n/100)^(2/9))` per Newey & West (1994), explicitly chosen to avoid hand-tuning after seeing a result **[Verified — code]**. **Not called anywhere in `runner.py` or `phase4.py`'s main orchestration** — invoked only in supplementary, per-hypothesis scripts (e.g., H-016's `run_h016_phase4.py`) **[Verified — code]** | Standard robust-inference correction for serial correlation in return series | Yes | **Inconsistently** — applied as supplementary evidence for H-013 through H-016 only; the twelve earlier hypotheses (H-001–H-012) were never evaluated under it |
| 8 | Deflated Sharpe Ratio | `stats.py deflated_sharpe_ratio()` / `probabilistic_sharpe_ratio()` — custom implementation of Bailey & López de Prado (2014/2012), computed from scratch (no scipy dependency), with an explicit disclosed limitation that its trial-independence assumption is imperfect **[Verified — code]** | Multiple-testing / selection-effect correction for Sharpe ratios discovered via search over many trials | Yes | **Inconsistently** — same wiring gap as HAC: exists, is used for later hypotheses' supplementary context, not part of the automatic evaluation path, and never applied retroactively |
| 9 | Holm / Benjamini-Hochberg correction | `stats.py holm()` (step-down FWER) and `benjamini_hochberg()` (step-up FDR), both correctly implemented against per-cell `p_raw` from the stability grid, default α=0.05 **[Verified — code]** | Standard multiple-comparison corrections | Yes | **Yes** — applied consistently across the entire registry from Wave 1 onward; this is one of the platform's most consistently-applied statistical safeguards |
| 10 | Walk-forward validation | Regime-based, not rolling-window: each pre-declared regime (`development`, `walk_forward`, `final_oos`) is run once via `runner.run_resolved()`; a hard runtime guard (`run_resolved()`) prevents any `development`-stage run from touching dates ≥ the pre-declared holdout start; the `final_oos` regime's Sharpe is read exactly once and never reused across stability cells **[Verified — code]** | Out-of-sample validation discipline, standard in quant research to prevent look-ahead | Yes | **Yes** — the untouched-final-OOS discipline is enforced at the code level, not just by convention, and has been load-bearing in multiple rejections (e.g., H-004's final-OOS reversal) |
| 11 | Survivorship / universe construction | `universe.py iru_members()` — point-in-time membership computed from a trailing window ending exactly at the as-of date, no forward-looking filter; a name delisted after the as-of date remains eligible if it met trailing criteria as of that date; renames followed via a verified `rename_chain()` **[Verified — code]** | Point-in-time (PIT) universe construction, the standard fix for survivorship bias in backtesting | Universal best practice | **Architecturally yes, empirically unverified** — the design is structurally correct, but no audit has ever checked this against a real, known NGX delisting to confirm it behaves as intended in practice. The literal term "survivorship" does not appear anywhere in the codebase |
| 12 | Liquidity measurement | 60-session rolling mean of `value_traded` ("ADTV60"), then z-scored and signed by direction; explicitly cites **Amihud & Mendelson (1986)** for the illiquidity-premium direction rationale; no Amihud (2002) illiquidity RATIO, no bid-ask proxy **[Verified — code]** | ADTV (a turnover/value-traded measure) is a common practitioner liquidity proxy | Yes (as a technique; the specific choice of proxy is a live academic question — see Part 2) | **Yes, tested** (H-016), **but see Part 3/4** — the specific proxy chosen (value-traded ADTV) is not the proxy the most relevant emerging-market liquidity literature found most return-predictive |
| 13 | Capacity estimation | `capacity_report()` — per-rebalance leg rejected if implied trade value exceeds a participation-rate cap (`adtv_participation_cap_pct`, default 10%) against ADTV; **explicitly reported, not enforced, inside the simulation** (`phase4.py` comment) **[Verified — code]** | Standard capacity/participation-rate modeling for illiquid-name strategies | Yes | **Yes** — this is a genuinely institutional-grade practice (Economic Capacity Validation, introduced for H-016) applied to real NGX ADTV data |
| 14 | Return calculation | Simple (arithmetic) returns throughout; price-only, **no dividend reinvestment** — explicitly disclosed in module docstrings as a known/conservative bias for winner-tilted long strategies **[Verified — code]** | Standard return convention; dividend exclusion is a simplification | Yes | Disclosed, not corrected — a `tr_adjustments` capability exists in the separate "full" engine but is not used by the primary per-stock (`backtest_xs.py`) engine that produced H-011 and everything since |
| 15 | Risk-free rate | CBN Monetary Policy Rate history, point-in-time lookup, explicitly disclosed as a **nominal policy-corridor proxy, not the actual investable T-bill rate**; opt-in flag, default flat 0.0% still used unless explicitly enabled **[Verified — code]** | Standard practice is to use a real, investable short-term rate | The *need* for a real rf rate is universal; the specific choice (MPR vs T-bill) is an NGX-specific approximation, already self-disclosed as imperfect | Yes, as far as the proxy goes — but the proxy itself is one step removed from the ideal (FMDQ NAFEX/T-bill rate, not yet acquired per the Free Data Source Audit) |
| 16 | Confidence rating system | Rule-based additive score (0-12) across six criteria (data confidence, n_decisions, n_regimes, corrected p-value, plateau fraction, placebo pass), with a hard override forcing "Inconclusive" on synthetic data regardless of score **[Verified — code]** | Institutional practice of converting multi-criterion evidence into a single actionable rating | Universal technique | Not market-specific — no gap identified here |
| 17 | RNG / seeding | Mandatory seed (refuses to run unseeded), `PCG64` default, full reproducibility record persisted per experiment **[Verified — code]** | Reproducible-research discipline | Universal technique | Not market-specific — no gap identified here |

---

## 2. Frontier Market Literature Review

*Every claim in this section is tagged **[Verified — literature]** with
its source. Where a claim could not be substantiated by the search
performed, that is stated explicitly rather than left implicit.*

**Non-synchronous trading and beta bias.** Scholes and Williams (1977)
and Dimson (1979) show that OLS market-model betas are biased and
inconsistent under non-synchronous trading; Fowler and Rorke (1983)
extended this into the commonly-cited Dimson-Fowler-Rorke lead-lag
correction (summing coefficients on lagged, coincident, and leading
market-return terms) **[Verified — literature; Stata Statlist archive,
INSEAD working paper 82-02, ResearchGate summaries]**. This is
specifically documented as a live issue on African exchanges: a paper
titled *"Thin trading on African stock markets: implications for market
efficiency testing"* exists in the peer-reviewed literature, confirming
this is treated as an African-market-specific empirical concern, not
merely a theoretical curiosity **[Verified — literature; ResearchGate
publication 290792299]**. **Important qualification**: this correction
targets bias in a *market-model beta regression* specifically. Per
Part 1 row 1, this platform does not estimate beta anywhere — none of
its factor scores (`vol_scores`, `size_scores`, `rank_scores`,
`liquidity_scores`) run a market-model regression. The Scholes-
Williams/Dimson correction, as literally specified, therefore has **low
direct applicability** to this specific platform's architecture — see
the Frontier Market Academic's critique in the adversarial review below
for why this is flagged prominently.

**Stale-price / zero-return liquidity measurement.** Lesmond, Ogden &
Trzcinka (1999) propose the "LOT" measure: the proportion of zero-
return days in a period, used as an indirect proxy for illiquidity and
transaction costs, based on the logic that informed traders will not
trade (producing a zero-return day) when costs exceed expected trading
gains. This measure is described in the literature as "the most
effective spread proxy in most emerging markets" among liquidity-proxy
alternatives **[Verified — literature; Bayes Business School EMG
working paper WP-EMG-04-2007, comparative liquidity-proxy studies]**.

**Liquidity pricing in emerging markets — the specific, actionable
finding.** Bekaert, Harvey & Lundblad (2007), published in the *Review
of Financial Studies* (20(6), 1783-1831), find that a transformation of
the *zero-return-proportion* liquidity measure **significantly predicts
future returns in emerging markets**, while **turnover-based measures do
not** **[Verified — literature; NBER Working Paper 11413, RFS
publication record]**. This is the single most directly actionable
finding of this literature review: **the platform's own liquidity
measure (ADTV, a value-traded/turnover-style measure) is specifically
the type of proxy this literature found non-predictive, while it has
never tested the type of proxy (zero-return proportion) this literature
found predictive.**

**NGX-specific microstructure research exists and has not been engaged
with.** Multiple peer-reviewed papers apply Glosten-Milgrom-style
information-asymmetry models directly to NGX-listed stocks (e.g., "A
Test of Market Microstructure: Evidence from Nigerian Bourse"; a 2023
study applying the model to 105 NGX-listed companies), and separate
work directly studies the liquidity-volatility relationship on the
Nigerian Exchange Limited **[Verified — literature; ResearchGate
338567959, ABFR Journal, academia.edu NGX liquidity/volatility study]**.
**This platform's own documentation does not cite or engage with any of
this NGX-specific empirical literature** — its frontier-market framing
draws on general emerging-market literature (Amihud & Mendelson,
Bekaert-Harvey-Lundblad) rather than NGX-specific empirical findings.

**Frontier/African factor-model horse races.** A study using monthly
returns of 375 blue-chip firms across 8 African equity markets over 23
years finds the Fama-French five/six-factor frameworks have the highest
explanatory power among tested multi-factor models **[Verified —
literature; ScienceDirect S1057521924006847, "Asset pricing in African
frontier equity markets"]**. A separate, larger study replicating over
160 anomalies across 23 frontier countries (1996-2017) finds Carhart's
four-factor model outperforms both Fama-French five-factor and q-factor
models **[Verified — literature; QuantPedia summary of frontier-market
anomaly replication]**. **This is a genuine tension worth naming
explicitly**: these results show that developed-market-style multi-
factor models, using largely conventional (non-microstructure-adjusted)
construction, already demonstrate real explanatory power in frontier/
African contexts — evidence against a blanket claim that "developed-
market technique simply doesn't work here." See the Asset Pricing
Researcher's critique below for how this tempers, without eliminating,
this audit's liquidity-proxy finding.

**Low-volatility effect, specifically in African frontier markets.** A
2024 study examines the low-volatility anomaly in a pooled sample of
nine African frontier equity markets (March 2004–July 2023), explicitly
testing whether any low-vol premium survives controls for transaction
costs, liquidity, sector, country, holding period, and size, and
whether it differs across bull/bear regimes and local-currency returns,
using bootstrap-based monotonicity tests rather than simple linear
sorts **[Verified — literature; Tandfonline 10.1080/10293523.2024.2361986]**.
**This audit could not retrieve the paper's directional finding** (only
its research questions and methodology were returned by the search
performed) — this is stated explicitly as an open item rather than
inferred. It is nonetheless directly relevant as a *methodological*
comparison: this paper's approach (multi-control, bootstrap
monotonicity testing) is more rigorous on the "isolate the true effect"
dimension than this platform's H-008/H-012 (simple quintile sort plus
placebo/Holm), even though the platform's placebo methodology is
arguably more rigorous on the "guard against false discovery" dimension.

**Small-sample / distribution-free inference.** Frontier-market factor
literature commonly uses bootstrap-based monotonicity tests across
sorted portfolios specifically because they require no linear-
relationship assumption and no distributional assumption about returns
— a property valuable exactly where sample sizes are small, as in
several of this platform's own registered near-misses (H-004, H-009)
**[Verified — literature; same Tandfonline 2024 paper's methodology
section, cross-referenced against frontier-market anomaly literature]**.

**Survivorship bias magnitude (illustrative, not NGX-specific).** A
study of an emerging-market small-cap index (India's NIFTY Smallcap
250) finds survivor-only backtesting overstates annual returns by 4.94
percentage points (23.3% relative) and Sharpe ratios by 0.097 (9.1%
relative), and separately reports emerging-market index turnover
comprising 16.1% delistings and 33%+ each of "graduated" and "demoted"
constituents — a materially higher churn rate than developed-market
indices typically show **[Verified — literature; SSRN working paper,
Harjot Singh Ranse]**. **This is cited as an illustrative magnitude from
a different emerging market, not as an NGX measurement** — it establishes
that survivorship effects in EM small-cap contexts can be large enough
to matter, not that they are this large on NGX specifically.

**Free-float adjustment in frontier-index construction.** MSCI, S&P,
and FTSE frontier-market index methodologies all apply an explicit
free-float adjustment (S&P's "Investable Weight Factor," MSCI's free-
float-adjusted market cap coverage target of ~85% per country) even at
the frontier-index level, and index-provider documentation explicitly
notes that markets "with limited free float or lower turnover may be
represented less fully" **[Verified — literature; S&P Dow Jones Indices
Frontier methodology document, MSCI Frontier Markets Africa Index
factsheet]**. This confirms free-float adjustment is standard
institutional practice even at the frontier-market tier, not a
developed-market-only refinement.

**Corporate-action handling in frontier markets — not independently
verified this session.** This audit did not perform a dedicated
external literature search on frontier-market corporate-action-handling
practice specifically. What is available is the platform's own internal
evidence from the FSI audit series (e.g., OANDO's 15-month reporting
lag, board-approval-vs-public-release PIT date discipline, the
discovery that a real share of NGX filings are legally "abridged" and
omit cash-flow statements) — this is internal, already-audited platform
evidence, not external literature, and is labeled **[Judgment, informed
by internal platform evidence]** rather than a literature-verified claim.

---

## 3. Gap Analysis

| Gap | Classification | Why |
|---|---|---|
| **Non-synchronous-trading beta correction (Scholes-Williams/Dimson)** | **Not applicable, as literally specified** — but see the related gap below | The correction targets market-model beta regression bias; this platform runs no beta regression anywhere. Applying it as literally described would be a solution in search of a problem this architecture doesn't have **[Judgment, grounded in Part 1's code-verified absence of any beta estimation]** |
| **Stale-price / non-synchronous-trading contamination of raw return series feeding vol/Sharpe/placebo** | **Partially addressed** | The `obs`-masking of forward-filled closes out of volatility calculations is a real, code-verified, non-trivial safeguard **[Verified — code]**. But this only protects the volatility calculation specifically — Sharpe ratios, placebo statistics, and HAC standard errors elsewhere in the pipeline still consume raw close-to-close returns that may carry stale-price-induced spurious patterns, and this has never been tested |
| **Liquidity-proxy choice (ADTV/turnover vs. zero-return/LOT measure)** | **Not addressed** | Code-verified: only ADTV is implemented. Literature-verified: Bekaert-Harvey-Lundblad (2007) find turnover-style measures do NOT significantly predict EM returns, while zero-return-proportion measures do. H-016 (the platform's only standalone Liquidity test) used exactly the type of proxy this literature found non-predictive, and never tested the type found predictive |
| **Survivorship / universe-construction verification** | **Partially addressed** | Architecturally correct by design (PIT, no forward-looking filter) **[Verified — code]**, but never empirically audited against a known real case **[Verified — code: no test/audit script for this exists; literal term "survivorship" absent from the entire codebase]** |
| **HAC/Newey-West and Deflated Sharpe Ratio — consistency of application** | **Partially addressed** | Both are correctly implemented **[Verified — code]** but applied only supplementally to hypotheses from H-013 onward, never wired into the shared `runner.py`/`phase4.py` orchestration, and never retroactively applied to H-001–H-012 |
| **Cross-sectional ranking method (z-score vs. percentile rank)** | **Not addressed, for the per-stock engine specifically** | Code-verified inconsistency: the index-level engine deliberately avoided z-scores for outlier-robustness reasons that the per-stock engine (used for every hypothesis since H-007, including the confirmed H-011) does not apply |
| **Free-float-adjusted benchmark/market-cap construction** | **Not addressed** | No free-float dataset exists anywhere on the platform **[Verified — code: repeated, consistent disclosure across 6+ files]**. Literature confirms free-float adjustment is standard even at the frontier-index tier (MSCI/S&P/FTSE) |
| **Transaction cost realism (bid-ask spread / slippage)** | **Partially addressed** | The commission/statutory-fee schedule is real and NGX-sourced **[Verified — code]**, a genuine strength; but no bid-ask-spread component exists, and the separate "full" engine's slippage constants are explicitly self-disclosed in code as "assumed, not estimated from NGX fill data" |
| **Dividend/total-return handling** | **Not addressed, disclosed** | Price-only returns throughout the primary engine, explicitly disclosed as a conservative known bias, not corrected |
| **Corporate-event PIT discipline (filing dates, reporting lags)** | **Addressed** | The FSI audit series already demonstrates real, careful PIT handling (OANDO's 15-month-lag case, release-vs-approval-date discipline) — this is a genuine strength, distinct from the return-series dividend-adjustment gap above |
| **Multiple-testing correction (Holm/BH)** | **Addressed** | Consistently implemented and applied across the full registry since Wave 1 |
| **Walk-forward / look-ahead discipline** | **Addressed** | Enforced at the code level (runtime guard), not merely by convention |
| **Turnover/cadence realism** | **Addressed** | The platform's own H-007→H-009→H-010 sequence is itself NGX-specific empirical evidence this was taken seriously and institutionalized into the codebase's rebalance-frequency options |
| **Capacity/participation-rate modeling** | **Addressed (as a report), not applicable as an enforcement mechanism yet** | `capacity_report()` is genuinely institutional-grade; it is disclosed as report-only, not enforced in simulation, which is a reasonable design choice for a research (not execution) platform, not a gap per se |
| **NGX-specific microstructure literature engagement** | **Not addressed** | Real, published NGX-specific microstructure research (Glosten-Milgrom applications, liquidity-volatility studies) exists and has never been cited, reviewed, or compared against in any platform document |

---

## 4. Impact Assessment

*Per instruction, this section does not revisit any hypothesis's
outcome — it assesses which hypotheses' underlying methodology could be
affected by each gap, and whether closing that gap would plausibly make
conclusions stronger, weaker, or simply more reliable. Where direction
cannot be determined without actually running the analysis, that is
stated as such.*

**Liquidity-proxy gap (ADTV vs. LOT zero-return measure).** Most
directly affects **H-016** (standalone Liquidity, the only hypothesis
built entirely around a liquidity proxy) and **H-013** (Size × Liquidity
interaction) and the capacity-estimation machinery more broadly (which
also uses ADTV). **[Judgment]**: retesting with a zero-return-proportion
measure could not be predicted to move the result in either direction
without actually running it — but per Bekaert-Harvey-Lundblad, it would
make the test's *proxy choice* more consistent with what the most
relevant EM literature found predictive, which would make any resulting
conclusion (confirm or reject) **more reliable**, not merely different.

**Cross-sectional z-score/percentile-rank inconsistency.** Affects
every per-stock hypothesis using `backtest_xs.py` — practically the
entire program since H-007, including H-011 (confirmed) and its
interaction decomposition (H-013/014/015) and H-016. **[Judgment]**:
given the platform's own documented rationale for preferring percentile
rank (outlier-robustness in small, thin cross-sections — exactly NGX's
characteristic), switching would plausibly make results **more
reliable** in low-breadth stability cells specifically, where a single
outlier return could disproportionately affect a z-score-based
selection. This is unlikely to reverse H-011's clean confirmation but
could matter for any hypothesis whose stability grid showed partial
(not full) plateau — which includes H-014's already-disclosed ambiguous
result.

**Stale-price contamination of Sharpe/placebo/HAC inputs.** Potentially
relevant to any hypothesis using volatility-based selection (**H-008,
H-012**) or any near-miss where statistical precision was decisive
(**H-004**, placebo p=0.079; **H-009**, placebo p=0.069). **[Judgment]**:
H-008 and H-012's rejections were unambiguous and wrong-signed with
strong significance — unlikely to be reversed by this fix. H-004 and
H-009's near-misses are exactly the cases where a stale-price-aware
return correction could plausibly shift the reported p-value in either
direction; this cannot be resolved without actually running the
correction.

**HAC/DSR retroactive application to H-001–H-012.** **[Judgment]**:
given most of these twelve rejections were decisive under simpler tests
(e.g., H-005's placebo p=1.00), retroactive HAC/DSR application is very
unlikely to overturn any of them — the practical value is in **firming
up** (not reversing) the two disclosed near-misses (H-004, H-009) and in
closing the internal-consistency gap the Wave 5 review already flagged.

**Survivorship-verification.** Affects the underlying sample for **all
sixteen** registered hypotheses, since every one draws on `iru_members()`.
**[Judgment]**: given the code-level design is already PIT-correct in
principle, the realistic expected outcome of running this audit is
confirming existing conclusions rather than overturning them — but the
asymmetry matters: this is the cheapest possible check, sitting directly
upstream of a much larger planned investment (FSI/fundamentals
expansion), where an undiscovered universe-construction bug would be
far more costly to find later.

**Free-float benchmark/cap construction.** Affects **H-011** directly
(already self-disclosed as a construct-validity limitation) and any
future Size-related or composite-factor work. **[Judgment]**: direction
unknown without the data; the platform's own H-011 report already treats
this as an open question, and this audit adds no new information beyond
confirming it matches broader institutional (MSCI/S&P/FTSE) practice.

**NGX-specific microstructure literature engagement.** Does not
directly affect any specific hypothesis's statistics, but represents a
missed opportunity to cross-validate the platform's own frontier
confound assumptions (e.g., H-016's non-synchronous-trading discussion)
against locally-published empirical findings rather than only general
EM literature. **[Judgment]**: would make future frontier-confound
discussions more evidenced, not change any existing numeric result.

---

## 5. Prioritization

| Rank | Improvement | Research impact | Implementation effort | Data dependency | Owner-decision dependency |
|---|---|---|---|---|---|
| 1 | Survivorship/universe-construction empirical verification | High (foundational — affects all 16 hypotheses) | Low (read-only check against known cases) | None | None |
| 2 | HAC/DSR consistency: (a) re-check H-004 and H-009 specifically, (b) wire both into shared orchestration going forward | Medium-High (firms up the two genuine near-misses; fixes a disclosed internal-consistency gap) | Low (functions already exist and are validated) | None | None |
| 3 | Liquidity-proxy comparison (zero-return/LOT measure vs. ADTV) | High (directly bears on the platform's only standalone Liquidity result and its Size decomposition) | Medium (derivable from existing daily price data; no new acquisition) | None | Low (a methodology choice) |
| 4 | Cross-sectional ranking standardization (percentile rank in the per-stock engine) | Medium (affects precision of every per-stock hypothesis, unlikely to flip clear verdicts) | Low (the pattern already exists elsewhere in the same codebase) | None | Low |
| 5 | Stale-price/non-synchronous-trading contamination check on return series feeding vol/Sharpe/placebo | Medium (most relevant to near-miss cases and future volatility-based work) | Medium (no off-the-shelf beta-based correction applies; needs a bespoke design) | None | Medium (requires a design decision, since the standard SW/Dimson recipe doesn't directly transfer) |
| 6 | NGX-specific microstructure literature review and citation | Low-Medium (evidentiary grounding, not a numeric change) | Low | None | None |
| 7 | Monotonicity/bootstrap portfolio-sort test as supplementary confirmation criterion | Low-Medium (adds robustness, unlikely to overturn existing verdicts) | Medium (new statistical method requiring its own validation) | None | Low |
| 8 | Free-float-adjusted benchmark/cap construction | High (resolves H-011's own disclosed limitation; matches institutional frontier-index practice) | Medium-High (requires NGX X-Compliance extraction, not yet even scoped for feasibility) | High (new data acquisition) | High (the X-Compliance acquisition decision, already open per the Free Data Source Audit) |
| 9 | Bid-ask-spread/slippage realism specific to NGX fills | Low-Medium (existing commission schedule is already real and NGX-sourced; the gap is narrower than it first appears) | Medium-High | High (real NGX fill/order-book data likely not freely available) | Medium |
| 10 | Capacity-constraint enforcement (vs. report-only) in simulation | Low (mostly formalizes an already-disclosed, already-understood limitation of H-011) | Low-Medium | None | Low |

No implementation is recommended for any of these — this ranking is
informational, per instruction.

---

## 6. Decision

**1. Is the current methodology sufficient for another wave of factor
discovery?**

**No, not without closing the top 1-2 items first — but this is a
narrow, bounded gate, not a broad indictment.** Most of the platform's
statistical machinery — placebo-first testing, Holm/BH correction, PIT
walk-forward discipline, the transaction-cost schedule, and the
Economic Capacity Validation concept — is sound, and per the literature
reviewed here, arguably more rigorous in several respects (persistence-
preserving placebo design, mandatory-seed reproducibility, hard
look-ahead guards) than what is typically documented in academic
frontier-market factor papers. The specific reason methodology should
close first is narrower: two cheap, foundational items (survivorship
verification, HAC/DSR consistency) sit directly upstream of the next
planned, much larger investment (FSI-driven fundamentals research per
Wave 5's own roadmap), and the cost of skipping them is asymmetric —
cheap to check now, expensive to discover wrong later.

**2. Which methodological weakness is now the highest priority?**

**Survivorship/universe-construction empirical verification.** It is
foundational (every hypothesis ever run depends on `iru_members()`
being correct), it is the cheapest possible fix (read-only, no new
data, no owner decision required), it sits directly upstream of a much
larger planned investment, and it is the platform's own most-repeated
unresolved self-criticism — flagged in the Wave 2 institutional audit,
flagged again in the Wave 5 strategic review, still not empirically
checked as of this document.

**3. Should methodology improvement come before H-017?**

**Yes, but only the top two cheap items — not a full methodology
overhaul.** H-017 does not depend on the liquidity-proxy question or
free-float data, so it is not blocked by most of this list. But it
would be built on the same unverified `iru_members()` universe as every
other hypothesis, and running the survivorship check first (a matter of
days, not weeks) before adding one more hypothesis on top of an
unverified foundation is the correct, minimal sequencing — this
sharpens, rather than contradicts, Wave 5's own recommendation.

**4. Which improvements are prerequisites for becoming a genuinely
frontier-market research platform, rather than a developed-market
framework applied to Nigerian data?**

**The liquidity-proxy correction and the stale-price/non-synchronous-
trading contamination fix** are the two that most directly change
*which statistics are computed*, not merely verify existing ones —
these are the ones that would make the platform's econometrics
genuinely adapted rather than borrowed. Free-float benchmark
construction also qualifies in principle, but it is gated on a data-
acquisition decision (NGX X-Compliance) that is already open elsewhere
in the research program, not a pure methodology fix available today.

---

## Institutional Adversarial Review

*Five reviewers, each required to find a real weakness and attempt to
invalidate the conclusions; each answered directly below.*

### Frontier Market Academic

**Criticism**: "You spend real space in Part 2 on Scholes-Williams and
Dimson, then admit in Part 3 that it doesn't apply because the platform
never estimates beta. That reads like literature-review padding — citing
the most famous frontier-microstructure correction because it's expected,
not because it's relevant. Doesn't this undercut the credibility of the
rest of the audit?"

**Response**: A fair critique of emphasis, and it's corrected here
rather than defended. The SW/Dimson literature is included because Part
2 explicitly required a review of frontier-vs-developed-market technique
differences, and the audit needed to show *why* the reflexive "just add
Scholes-Williams" recommendation would be the wrong prescription for
this specific, beta-free architecture — not to pad the citation list.
But the reviewer is right that this could read as padding if not
sharpened, so it is sharpened here: **the actionable version of this
concern is not "add a beta correction," it is "the same underlying
stale-price/non-synchronous-trading phenomenon that motivates SW/Dimson
still contaminates this platform's raw return series wherever they feed
Sharpe ratios, placebo statistics, or HAC standard errors — regardless
of whether a beta regression is involved."** That reframed version (Part
3's second row, Part 5's rank-5 item) is the real, applicable finding;
the SW/Dimson discussion exists to explain why the *literal* textbook
correction is not it.

### Quant Research Director

**Criticism**: "Your top recommendation is a survivorship audit, but
your own code review already found the design is correctly point-in-time
with no forward-looking filter. If you believe the design is already
right, recommending this as the #1 priority looks more like theater —
'audit for the sake of auditing' — than a response to actual evidence
something is wrong."

**Response**: A useful distinction to make explicit rather than leave
implied. This is not a claim that something is believed broken — it is
a claim that something structurally important **has never been
empirically checked against a single real, known case** (e.g.,
confirming a specific NGX name known to have delisted mid-sample
correctly appears IRU-eligible before its delisting and correctly
disappears after). A well-designed piece of code being unverified is
not the same as it being verified — and per the external literature
cited in Part 2 (the ~4.94-percentage-point/9.1%-relative Sharpe
overstatement found in an analogous EM small-cap index example), this
is exactly the class of check where the cost of skipping is asymmetric:
cheap to run now, expensive to have silently wrong once a much larger
research program (Wave 6's fundamentals work) is built on top of it.
The recommendation stands, with this asymmetric-cost framing made
explicit rather than implied, precisely to avoid it reading as
theater.

### Asset Pricing Researcher

**Criticism**: "Your liquidity-proxy critique implies H-016's null
result might just be an artifact of using the wrong proxy — but you also
cite African/frontier horse-race literature showing Fama-French-style
models, built on fairly conventional data construction, already have
real explanatory power in these markets. Aren't you cherry-picking the
literature that supports 'this platform is under-adapted' while
downplaying the literature suggesting conventional approaches already
work reasonably well?"

**Response**: A legitimate check on selection bias in the literature
review, and the two findings are not actually in the tension the
critique implies once the claims are stated precisely. The horse-race
papers test whether developed-market **factor definitions** (value,
size, momentum, profitability) have return-predictive power in
frontier/African markets, generally using conventional return/liquidity
construction — they do not test whether a microstructure-corrected
version of the same factor would perform differently. This audit's
claim is deliberately narrower than "developed-market models don't work
in Africa": it is specifically that **the platform's chosen liquidity
proxy (ADTV/turnover) is the type Bekaert-Harvey-Lundblad found
non-predictive in emerging markets, while it has never tested the type
(zero-return proportion) that paper found predictive** — a claim that
stands on its own regardless of what the broader multi-factor
horse-race literature finds about factor existence in general. The two
literatures answer different questions, and this audit's claim is
scoped to the narrower, better-supported one.

### Statistical Methodologist

**Criticism**: "You flag HAC/DSR as 'inconsistently applied,' but for
the platform's cleanest rejections (H-005's placebo p=1.00, H-008's
Holm-significant wrong-signed result) tightening the standard errors
changes nothing — you're recommending effort be spent on results that
are already about as decisive as a rejection can be. Isn't this a
low-value, box-checking recommendation dressed up as rigor?"

**Response**: Partially accepted, and the scoping in Part 5 already
reflects this (it explicitly targets H-004 and H-009 — the two disclosed
near-misses — not a blanket re-run of all twelve pre-METH-001
hypotheses), but the reviewer's point is fair enough that it should be
even more explicit: **decisive rejections do not need retroactive
HAC/DSR treatment; only the near-misses do.** The more valuable half of
this recommendation is forward-looking, not backward-looking: wiring
HAC/DSR into the shared `runner.py`/`phase4.py` orchestration so future
hypotheses get this treatment automatically, rather than requiring a
researcher to remember to add a supplementary script call — a process
fix, not a re-audit of already-settled results.

### Portfolio Manager

**Criticism**: "Every recommendation in this document produces zero
investable output, and two of your top items (survivorship audit,
thin-trading correction) were *already* named in Wave 5's own roadmap.
Isn't this just re-auditing the audit? At what point does methodology
review stop and actual research resume?"

**Response**: A legitimate and important challenge to sequencing
fatigue, and it deserves a direct, bounded answer rather than another
open-ended review. This document does not add new methodology work
beyond what Wave 5 already scoped — it is the deeper, code-level dive
INTO exactly the two items Wave 5 named at a strategic altitude
(survivorship, thin-trading), plus two genuinely new findings this
code-level pass surfaced that Wave 5's higher-level review could not
have found (the z-score/percentile-rank inconsistency in Part 3, and
the ADTV-vs-LOT liquidity-proxy mismatch in Part 2/4). Part 6's own
answer to "is methodology sufficient for another wave" is **"no, but
only pending the top 1-2 cheap items"** — not an indefinite "no." The
concrete, bounded scope is: run the survivorship check and the HAC/DSR
near-miss re-check (a matter of days, not weeks) — then resume H-017
and the FSI pilot immediately after, exactly as Wave 5 already proposed.
This document does not extend the delay Wave 5 already introduced; it
specifies precisely where that delay should end.

---

## Final Recommendation, After Review

The five critiques converge on a single needed correction to how this
audit's findings should be read: **the highest-value items here are
narrow, cheap, and bounded — not a call for a general methodology
overhaul.** Incorporating the review: the Scholes-Williams/Dimson
framing is de-emphasized in favor of the more applicable "stale-price
contamination of return series" finding (Frontier Market Academic); the
survivorship audit is justified by asymmetric cost, not suspicion of an
actual defect (Quant Research Director); the liquidity-proxy claim is
scoped to the specific, literature-supported version rather than a
broad "developed-market technique fails here" claim (Asset Pricing
Researcher); the HAC/DSR recommendation is narrowed to the two genuine
near-misses plus a forward-looking process fix, not a blanket re-audit
(Statistical Methodologist); and the sequencing is stated with an
explicit, bounded timeline — days, not weeks — before H-017 and the FSI
pilot resume exactly as Wave 5 already proposed (Portfolio Manager).
Methodology review closes here; nothing in this document proposes
extending it further.
