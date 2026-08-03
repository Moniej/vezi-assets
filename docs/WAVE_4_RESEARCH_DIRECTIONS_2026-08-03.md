# Wave 4 — Next Quant Hypothesis Discovery

*2026-08-03. Written per an explicit owner directive to audit everything
before proposing anything, propose only hypotheses that are theoretically
motivated, falsifiable, and actually testable with data the platform holds
today, and to say "insufficient evidence" rather than invent a candidate to
keep the phase count moving. This document is a research-DIRECTION review
(same status as `docs/WAVE_3_RESEARCH_DIRECTIONS.md`), not itself a
pre-registration — the selected candidate(s) still require their own full
prereg, owner review, and Phase 4 gauntlet before any run, per unbroken
platform convention.*

---

## 0. Ground truth, checked directly (not recalled) before writing anything below

Queried `data/registry.sqlite` directly on 2026-08-03:

| ID | Status | Family |
|---|---|---|
| H-001 | rejected (frozen) | sector momentum |
| H-002 | **untested** (blocked-on-data, never run) | total-return momentum / dividend effects |
| H-003 | rejected | event catalyst rotation |
| H-004 | rejected | oil lead-lag |
| H-005 | rejected | MPC window |
| H-006 | rejected | PEAD |
| H-007 | rejected | cross-sectional momentum |
| H-008 | rejected | low volatility |
| H-009 | rejected | turnover-budgeted momentum |
| H-010 | rejected | pooled overlapping-cohort momentum |
| H-011 | **confirmed** | Size |
| H-012 | rejected | regime-gated low volatility |
| H-013 | rejected | Size × Liquidity (forensic, not standalone) |
| H-014 | rejected | Size × Momentum (forensic, not standalone) |
| H-015 | rejected | Size × Volatility (forensic, not standalone) |

**15 hypothesis IDs exist: 1 confirmed, 13 rejected, 1 still untested/data-blocked.**
This corrects the "12+ registered" framing in the prompt to the precise
number, per the platform's own standing discipline of verifying counts
before restating them (the same correction was made, for the same reason,
in `docs/ARCHITECTURAL_GAP_AUDIT_2026-08-02.md` and the Wave 2 audit before
it).

The next available sequential ID is **H-016**.

---

## 1. Required audit (per directive, items 1–10)

### 1.1 Every existing dataset

Checked `data/reference/` directly: `cbn_mpr_history.csv` (CBN MPR, 50
decisions, powers METH-002), `market_cap_panel.csv` (328,023 rows, powers
H-011), `exdiv_closure_calendar.csv` (1,044 rows / 217 symbols, unused as a
research input), `official_prev_close.csv`, `symbol_renames.csv`,
`gainers_transitions.csv`, `fsi_pipeline_golden_snapshot.json`. Plus the
core `equity_prices` table (320+ tickers, 320k+ rows, used by everything)
and `extracted_facts`/`documents` (FSI structured-financials extraction).

### 1.2 Every computed factor / score series

`backtest_xs.py` currently computes, as reusable score functions:
`rank_scores` (momentum), `vol_scores` (low-vol), `size_scores` (Size),
`liquidity_scores` (built 2026-08-03 for Phase R2 — **explicitly documented
in its own docstring as "NOT... a standalone tradeable Liquidity factor
method (that remains a separate, not-yet-run candidate)"**). This is the
single most direct, code-level confirmation that a standalone Liquidity
factor has never been tested — the scoring function to do so already
exists, built, unit-tested (I1-I5), and used in production, but only as an
input to a *different* hypothesis's bucket split.

### 1.3 Every free data source

`docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md` (23 sources across
macro/rates, corporate/governance, and alternative/frontier data,
independently web-verified 2026-08-02). Headline finding of that audit
(CBN risk-free rate) is already closed (METH-002). Two "Near-term"
sources remain un-acted-on: **NGX X-Compliance Report** (free-float
data — real gap-filler for H-011's own disclosed full-issue-cap
limitation) and **DMO/FMDQ** (term-structure depth for the risk-free rate,
lower urgency, not a new factor family). Both require new PDF/HTML
extraction work, not a re-read of data already held.

### 1.4 Every available signal

Per `docs/FACTOR_CANDIDATE_REGISTRY.md` (2026-08-02, re-verified against
today's registry state): of 16 named candidate families, exactly **3 are
"Available" (zero new data)** — Liquidity (A1), Dividend payer-status
(A2), and Interaction Factors (A3, now resolved as H-013/014/015). That
audit's own closing recommendation was to pre-register A3 next; that step
is done. **A1 and A2 are the only two remaining zero-acquisition-cost,
fully-available candidates left in that registry.**

### 1.5 Every unresolved research finding

The single largest unresolved finding on the platform, as of the last
completed phase: **Phase R2's disclosed liquidity-direction tension**
(`docs/PHASE_R2_SIZE_INTERACTIONS_REPORT_2026-08-03.md`, "Outstanding
Observation"). H-011's own capacity report found its historically
strongest CONTRIBUTORS were thin/illiquid names; H-013's bucket-level
double sort of the whole universe found the Size premium concentrated in
the LIQUID half, with the illiquid half a clean statistical null (placebo
p=0.703, real Sharpe below its own placebo mean). Both facts are true and
both are on permanent record — the platform explicitly declined to force
them into one story. **This is a genuine, unresolved empirical puzzle,
not a closed question**, and it is the strongest single piece of evidence
motivating what to test next.

### 1.6 Every rejected hypothesis

H-001, H-003–H-010, H-012–H-015 (13 total). Read via
`docs/FACTOR_REGISTRY.md` and `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`.
Cross-cutting lessons already extracted and not re-derived here: (a)
sub-quarterly rebalancing is cost-doomed on NGX (H-001/H-004/H-005/H-007);
(b) five of thirteen rejections trace to structural breadth ceilings
(Grinold's Law — thin universe caps statistical power regardless of
signal quality), not necessarily absent economic effects; (c) H-008 (low
volatility) and H-012 (regime-gated low volatility) both failed on their
OWN terms as standalone/conditioned vol factors — this is a DIFFERENT
mechanism and a DIFFERENT dataset construction from a trading-ACTIVITY
liquidity factor and must not be conflated with it.

### 1.7 Every validated hypothesis

One: H-011 (Size), confirmed 2026-07-22, capacity-caveated, since narrowed
by Phase R2 to a liquid/low-vol/(partially) low-momentum small-cap
subset. No other factor has ever validated.

### 1.8 Every interaction study

H-013/014/015 (Size × Liquidity/Momentum/Volatility, Phase R2, 2026-08-03)
— the platform's only interaction program to date. All three: Size does
NOT survive fully independently. No OTHER interaction (e.g., a future
Liquidity × Momentum, or Dividend × Size) has ever been tested, and none
should be until each component has a standalone verdict of its own — the
same "no composite before ≥2 validated independents" rule in
`docs/FACTOR_CANDIDATE_REGISTRY.md §D1` applies with equal force to
interactions built on an untested component.

### 1.9 Every remaining architectural gap

Per `docs/ARCHITECTURAL_GAP_AUDIT_2026-08-02.md` (re-verified, nothing
material changed since except the addition of METH-001b and Phase R2,
neither of which touches this list): the single largest gap remains **a
second validated, independent factor** — Portfolio Construction's ≥2-factor
gate is exactly one short, and every Tier-2 module (Ranking, Portfolio
Construction, Risk Engine, Attribution) is designed and waiting on it. A
regime-conditional methodology now exists (H-012, built and rejected on its
own specific application) but has not been retried on a different base
signal. Float-adjusted market cap remains externally blocked (no
shares-outstanding data acquired yet — see 1.3). FSI statement extraction
remains capped at 10 tickers (unchanged since 2026-08-02), which is the
single root cause blocking 11 of the 16 named candidate families in the
Factor Candidate Registry (Value, Quality, Growth, Profitability, and
every accrual/balance-sheet-based family).

### 1.10 What data is actually available — not what could theoretically exist

Confirmed directly against `data/reference/` and `equity_prices`/
`extracted_facts` (not assumed from prior documentation): ADTV (`adtv60`,
already loaded by every cross-sectional hypothesis via `load_panel`),
market cap (already used, H-011), realized volatility (already used,
H-008/H-012), trailing return (already used, H-007/H-009/H-010), and the
ex-dividend closure calendar (never used as a research input, only as
data-quality/gate context) are **actually present in the database at full
IRU breadth today**. Financial-statement line items (`net_profit`,
`revenue`, `assets`, `equity`, `cfo`, etc.) are actually present for only
**10 distinct tickers** each — confirmed via direct query, unchanged since
the last audit — a fact that immediately and permanently disqualifies
Value, Quality, Growth, Profitability, Investment, Accruals, and Financial
Strength from consideration in this wave. Free-float/shares-outstanding
data does not exist anywhere in the platform yet — it would require a new
extraction pass on the NGX X-Compliance Report (PDF), an owner decision on
extraction labor, not a re-read of anything already held.

**Bottom line of the audit**: exactly two candidate families clear the
data-availability bar today with zero new acquisition — **standalone
Liquidity** and **Dividend payer-status**. A third, real, well-motivated
direction (free-float-adjusted size / free-float governance signal) exists
but is **not yet feasible** without new extraction work; it is named below
as a data-acquisition priority, not proposed as a testable hypothesis this
wave, consistent with the directive's instruction to reject anything that
"cannot actually be tested with existing data."

---

## 2. Candidate H-016 — Standalone Liquidity Premium

### 2.1 Hypothesis ID
**H-016**

### 2.2 Research Question
Within the Investable Research Universe, does a cross-sectional sort on
trailing average daily value traded (ADTV) — independent of any Size
conditioning — produce a return premium, and in which direction (illiquid
or liquid) does that premium run on NGX?

### 2.3 Economic Theory
Two competing, both economically legitimate, mechanisms are in tension
here and the test is designed to distinguish them, not assume one:

- **Classic illiquidity-premium mechanism** (Amihud & Mendelson 1986):
  investors demand compensation for the higher transaction costs and
  slower execution of illiquid securities; the compensation should show up
  as a return premium to holding the LESS liquid names, priced in at
  purchase and realized over the holding period. Amihud (2002) operationalizes
  this via `ILLIQ = |return| / value_traded` in a framework the platform's
  own `adtv60` panel can directly proxy.
- **Liquidity/limits-to-arbitrage mechanism observed empirically in
  Phase R2** (`docs/PHASE_R2_SIZE_INTERACTIONS_REPORT_2026-08-03.md`):
  H-011's own confirmed Size premium was found concentrated in the LIQUID
  half of the universe, with the illiquid half a clean statistical null.
  If illiquid NGX names are dominated by stale/non-synchronous pricing
  (thin trading producing artificially smoothed, autocorrelated return
  series rather than a genuine risk premium), a naive illiquidity sort
  could show an apparent premium that is a **microstructure artifact**,
  not compensated risk — or, as Phase R2 suggests, no premium at all in
  the illiquid leg.

This hypothesis is explicitly designed to adjudicate between these two
readings using data the platform already holds, rather than assume either
one.

### 2.4 Academic Support
Amihud & Mendelson (1986, *JFE*) — original bid-ask-spread liquidity
premium; Amihud (2002, *Journal of Financial Markets*) — illiquidity ratio
as a priced characteristic; Pástor & Stambaugh (2003, *JPE*) — liquidity as
a systematic priced risk factor; Bekaert, Harvey & Lundblad (2007, *Review
of Financial Studies*, "Liquidity and Expected Returns: Lessons from
Emerging Markets") — direct emerging-market precedent showing the
illiquidity premium is measurable but sensitive to microstructure
corrections in thin markets, precisely the concern in 2.3; Lesmond, Ogden &
Trzcinka (1999, *Review of Financial Studies*) — zero-return-days as a
transaction-cost/staleness proxy, used here as a required robustness check
(§2.8), not as the primary signal. **Where this differs from existing
work**: none of the above tests NGX specifically, and — critically — this
is the first test on this platform of Liquidity as its OWN factor rather
than as a conditioning bucket on Size (H-013 tested "does Size survive
controlling for Liquidity," a materially different question from "does
Liquidity itself carry a premium").

### 2.5 Frontier-Market Classification
**Frontier-market technique, with a genuinely Nigeria-specific empirical
question layered on top.** The underlying illiquidity-premium literature
is universal (developed and emerging markets both test it), but NGX's own
documented characteristics — a ~100-name investable universe, capacity
reports across every prior hypothesis showing 90%+ of trade legs rejected
at ₦1bn AUM, and H-011's own median leg capacity of ₦694,336 — make
illiquidity a first-order, not marginal, feature of this specific market's
cross-section. The Bekaert/Harvey/Lundblad emerging-market precedent is the
closest analogue; NGX (a frontier, not emerging, market by most
classifications) has not, to this audit's knowledge, been directly tested
this way. Institutional frontier-market investors would very plausibly
consider a correctly-measured (staleness-corrected) illiquidity premium a
differentiated source of alpha specifically because thin frontier markets
are exactly where the mechanism (and its confounds) are strongest — but
this audit takes no position on whether NGX's own effect, once measured,
will confirm or reject that prior.

### 2.6 Expected Edge
**Why should the market misprice this?** Thin NGX trading and low
institutional participation mean fewer arbitrageurs are positioned to bid
away an illiquidity discount even if noticed — the classic limits-to-
arbitrage argument, amplified by frontier-market thinness. **Why would it
persist?** As long as NGX's market structure remains thin and
retail-dominated (a multi-year, slow-moving structural feature, not
something likely to change within the sample), the friction is structural,
not a transient information gap. **Why might it disappear or run the
"wrong" way?** Phase R2's finding is the reason to take this risk
seriously here rather than as boilerplate: if illiquid-name "returns" are
partly an artifact of stale/non-synchronous pricing rather than a true
premium, a naive sort could show a spurious illiquid-leg premium, OR (per
Phase R2) actually show the reverse — a premium concentrated in liquid
names — either of which would falsify the classic Amihud direction on this
specific market.

### 2.7 Required Data
| Dataset | Status |
|---|---|
| `equity_prices` (close, volume/value_traded) | Already Available |
| `adtv60` (trailing 60-day ADTV, computed by `load_panel`) | Already Available |
| IRU v2 eligibility rules | Already Available |
| Zero-return-day counts per ticker (staleness proxy, Lesmond et al.) | Already Available (derivable directly from existing `equity_prices`, no new source) |
| CBN real risk-free rate (METH-002) | Already Available |
| Free-float / shares-outstanding | Not required for this test |

**No dataset in this hypothesis is Free-but-Missing, Owner-Decision-Required,
or Not Feasible — this is the single cleanest data-availability case of
any candidate audited.**

### 2.8 Statistical Plan
- **Signal construction**: new `xs_liquidity` method in `backtest_xs.py`,
  reusing `liquidity_scores()` (already built and unit-tested, I1-I5) —
  wired as a standalone `scores_for_method`/`targets_from_scores` path,
  NOT the bucket-split machinery Phase R2 built. Both directions (long-
  illiquid per classic Amihud, and long-liquid per Phase R2's empirical
  hint) will be run and reported, pre-registered as two named legs rather
  than chosen after seeing results.
- **Placebo testing**: joint ticker-permutation placebo (same seeded
  methodology as every prior xs_* hypothesis), 100 iterations minimum.
- **HAC/Newey-West**: `stats.newey_west_tstat` on daily excess-vs-benchmark
  returns, automatic Bartlett bandwidth.
- **Deflated Sharpe Ratio**: computed against the existing 15-hypothesis
  trial pool (real-rf basis, per METH-001b's established convention) —
  context only, consistent with how Phase R2 treated its own DSR figures.
- **Multiple-testing treatment**: Holm and Benjamini-Hochberg across the
  stability grid (rebalance × top_n/quantile-width cells), same convention
  as every prior hypothesis.
- **Out-of-sample validation**: full walk-forward with an untouched final
  OOS window — **unlike Phase R2's disclosed scoping reduction**, this is
  a standalone factor candidate for the Factor Registry, not a forensic
  decomposition, so it must clear the SAME full gauntlet H-011 cleared, not
  a reduced one.
- **Look-ahead audit**: standard PIT discipline (formation-date-only data,
  no walk-forward leakage) — identical machinery to every existing
  hypothesis.
- **Robustness checks (specific to this hypothesis, beyond the standard
  suite)**: (a) zero-return-day / staleness ratio computed per bucket —
  if the illiquid leg's apparent premium correlates with a materially
  higher zero-return-day rate, this must be reported as a stale-pricing
  confound, not a clean premium; (b) explicit rank correlation (Spearman)
  between the Liquidity score and the Size score at every formation date —
  quantifies exactly how entangled this factor is with H-011's own signal
  before any interpretation is attempted; (c) a lagged-return sensitivity
  check (compare same-day vs. 1-day-lagged illiquid-leg returns) as a
  direct, disclosed test for non-synchronous-trading bias (Scholes-Williams
  effect), the single most important frontier-market-specific robustness
  check this candidate requires that none of H-001–H-015 needed in the
  same way.
- **Sensitivity analysis**: ADTV lookback window (60d base, 20d/120d
  sensitivity), consistent with how every prior score-construction
  hypothesis has been stress-tested.

### 2.9 Risks
- Entanglement with Size: illiquid names and small-cap names substantially
  overlap on NGX by construction; a positive result could simply be
  re-discovering H-011 under a different label rather than an independent
  effect — the Spearman check in §2.8 is designed to surface this
  explicitly, not paper over it.
- Stale/non-synchronous pricing could manufacture a spurious premium in
  either direction — this is the single largest risk specific to this
  candidate and is the reason the staleness/lag robustness checks are
  mandatory, not optional.
- Breadth ceiling: an illiquid-leg sort may retain fewer eligible names
  per formation date than the whole-universe IRU bar every confirmed/
  rejected hypothesis has used — must be scoped (count eligible names per
  quantile per formation date) before the prereg is finalized, exactly as
  Wave 3's own C1 candidate was required to do.
- Capacity: if the "long-illiquid" leg direction is confirmed, it will
  almost certainly inherit or exceed H-011's own severe capacity
  constraint (₦694,336 median leg) — should be disclosed prominently, not
  softened, per the platform's established convention for exactly this
  situation.
- Phase R2's own evidence is a genuine prior AGAINST the classic
  illiquidity-premium direction on NGX specifically — this hypothesis
  should not be pre-registered with an expectation that the classic
  direction will confirm; the null (or reversed-direction) result is a
  live, real possibility that must be treated as a legitimate outcome, not
  a failure of design.

### 2.10 Confirmation Criteria
Pre-registered, fixed before any run, mirroring H-011's own six criteria
exactly (same bar, no relaxation): (1) placebo p < 0.05 on the chosen base
cell; (2) positive net excess return in BOTH development and untouched
final OOS; (3) plateau — majority of stability-grid cells directionally
positive, no single spike-cell result; (4) survives Holm OR
Benjamini-Hochberg correction on at least one grid cell; (5) no single
regime carrying >80% of positive excess; (6) zero triggered failure
conditions per `failure_conditions.py`. Direction (long-illiquid vs.
long-liquid) is decided by whichever leg, if either, meets these criteria
— not chosen in advance and not chosen after seeing results beyond the
two pre-declared legs.

### 2.11 Rejection Criteria
Permanent rejection if: placebo p ≥ 0.05 in both directions; OOS excess
return is negative or reverses sign from development in either surviving
leg; the staleness/lag robustness check shows the apparent premium is not
robust to a 1-day return lag (i.e., disappears under a synchronous-trading
correction) — this specific criterion is unique to this hypothesis and
must be honored even if the naive (unlagged) result looks confirmatory,
per the same "document honestly regardless of outcome" standard applied
throughout Phase R2.

### 2.12 Research Priority (discussed separately, not combined)
- **Expected information gain**: High — directly resolves the Phase R2
  liquidity-direction tension, the single largest unresolved finding on
  the platform.
- **Implementation cost**: Low — reuses an already-built, already-tested
  scoring function (`liquidity_scores`); the single-sort scaffolding
  (`xs_rank`/`xs_vol`/`xs_size`) generalizes directly; no new data
  acquisition.
- **Scientific novelty**: Medium-High as a standalone claim (the mechanism
  itself, Amihud/Mendelson, is well-established globally) but High in this
  platform's own context (first-ever standalone test; directly extends,
  not repeats, Phase R2).
- **Alpha potential**: Uncertain by design — Phase R2's own evidence is a
  real prior against the classic direction; a null result here is a
  legitimate, valuable, and arguably MORE likely outcome than confirmation,
  and should not be treated as a lesser finding if it occurs.
- **Data availability**: Highest of any candidate in this document —
  zero new acquisition, reuses existing computed panels.
- **Robustness potential**: Genuinely uncertain given the staleness
  confound — this is the candidate's central open question, not a settled
  strength.

---

## 3. Candidate H-017 — Dividend Payer-Status Tilt

### 3.1 Hypothesis ID
**H-017**

### 3.2 Research Question
Within the IRU, do firms with a consistent dividend-paying track record
(payer status, not yield magnitude) exhibit different risk-adjusted
returns than non-payers or inconsistent payers?

### 3.3 Economic Theory
Dividend-paying status is a costly, hard-to-fake signal of sustained
cash-generative capacity and management's confidence in future earnings
(Bhattacharya 1979 dividend-signaling theory; John & Williams 1985).
Separately, in a retail-dominated market with limited alternative
income-generating financial assets, a dividend-clientele effect can create
persistent demand for payer-status stocks distinct from any price-momentum
or size-based mechanism (Aivazian, Booth & Cleary 2003, emerging-market
dividend policy evidence). This is explicitly a **risk/quality-tilt claim**
(payers may exhibit different volatility/drawdown characteristics), not a
yield-carry claim — the platform has no reliable yield-magnitude data
(DPS/EPS extraction failed validation twice, `reports/eps_pe_extraction_status.md`),
and this hypothesis is scoped narrowly and deliberately to avoid overclaiming
what a binary payer/non-payer flag can support.

### 3.4 Academic Support
Fama & French (2001, *JFE*, "Disappearing Dividends") — establishes the
payer/non-payer characteristic split as economically meaningful separate
from yield magnitude; Litzenberger & Ramaswamy (1979, *JFE*) — original
yield-effect literature (a DIFFERENT, stronger claim than this hypothesis
makes); Aivazian, Booth & Cleary (2003, *Journal of Financial Research*) —
emerging-market-specific dividend-policy evidence. **Where this differs**:
narrower than the cited literature by construction (binary status, not
yield size) due to a real, disclosed, already-documented NGX data
limitation, not a design preference; first application of NGX's ex-dividend
closure calendar as a research INPUT rather than a data-quality tool.

### 3.5 Frontier-Market Classification
**Emerging/frontier-market technique with a developed-market theoretical
root.** The signaling and clientele mechanisms are universal
(developed-market literature originates them), but their expected relative
strength is argued here to be frontier-specific: in a market with sparse
institutional coverage and few alternative yield-bearing retail
instruments, a payer-status signal may carry more marginal information
than in a developed market already saturated with analyst dividend
coverage and yield-focused funds. This is a plausible, citable, but
UNPROVEN adaptation for NGX specifically — stated as a hypothesis to test,
not a confirmed frontier-market finding.

### 3.6 Expected Edge
**Why should the market misprice this?** Thin sell-side coverage means
payer-consistency as a quality signal may not be systematically priced the
way it would be in a market with dense dividend-focused fund flows.
**Why would it persist?** Payer status changes rarely — the underlying
information (a firm's sustained cash-generative capacity) is genuinely
slow-moving, so any mispricing would not be quickly arbitraged away by a
thin, retail-dominated market. **Why might it disappear or fail to
appear at all?** The single largest risk, stated up front rather than
discovered after the fact: established NGX dividend payers (banks,
consumer staples) are also disproportionately the LARGEST, most liquid
names in the universe — this could make the signal a pure proxy for
size/quality/low-volatility characteristics already tested (and, for size,
confirmed; for volatility, rejected) rather than independent information.

### 3.7 Required Data
| Dataset | Status |
|---|---|
| `data/reference/exdiv_closure_calendar.csv` (1,044 rows, 217 symbols) | Already Available |
| `equity_prices` panel | Already Available |
| IRU v2 eligibility rules | Already Available |
| Dividend YIELD magnitude (DPS/EPS) | Not Feasible (documented, closed negative result — `reports/eps_pe_extraction_status.md`) — explicitly excluded from this hypothesis's scope, not silently assumed available |
| Free-float / shares-outstanding | Not required |

### 3.8 Statistical Plan
Same full standard suite as H-016 (§2.8's placebo/HAC/DSR/multiple-testing/
OOS/look-ahead framework applies identically) with one hypothesis-specific
addition: a **mandatory orthogonality check against H-011's Size score and
H-008/H-012's Volatility score** (Spearman rank correlation of
payer-status against both, at every formation date) — required BEFORE any
interpretation of a positive result is offered, given the construct-validity
risk named in §3.6. A positive result that is not meaningfully orthogonal
to Size must be reported as such, not claimed as independent information.

### 3.9 Risks
- Construct-validity: may simply proxy for size/quality rather than
  carrying independent information (§3.6) — the single largest risk,
  already disclosed in `docs/WAVE_3_RESEARCH_DIRECTIONS.md` when this
  candidate (C5) was first scoped in 2026-07-22 and still unresolved.
  Active-payer subset breadth needs scoping (how many of the 217 historical
  payer symbols are actual payers AT any given formation date, not merely
  ever-payers across 2016–2026) before pre-registration — not yet measured.
- Binary-flag information content: a payer/non-payer split is a coarser
  signal than any yield-based literature this hypothesis cites; if the
  effect exists only at the yield-magnitude level, this test is
  structurally unable to detect it and would produce a false negative, not
  evidence against dividends mattering at all — this distinction must be
  stated in the final report regardless of verdict.
- Slow-moving status changes could mean very few genuine "events" (payer
  → non-payer or vice versa) within the sample, limiting power in a
  different way from a breadth ceiling — a temporal-power concern specific
  to this hypothesis.

### 3.10 Confirmation Criteria
Same six-criterion bar as H-016/H-011 (§2.10's template, applied to the
payer-status tilt), **plus** a seventh, hypothesis-specific requirement:
the Spearman correlation against Size must be reported and disclosed
regardless of its value, and any confirmation must be accompanied by an
explicit statement of whether the effect survives directionally once size
is controlled for (a lighter-weight version of the interaction-forensics
discipline Phase R2 established, applied prospectively rather than
retrospectively this time).

### 3.11 Rejection Criteria
Permanent rejection if: placebo p ≥ 0.05; OOS excess negative or sign-
reversed from development; OR the effect is found to be fully explained by
its Size/Volatility correlation per the mandatory orthogonality check (a
positive but non-independent result is recorded honestly as "construct
validity failure," a distinct and separately logged rejection reason from
"no effect found," per the same practice used for H-013–H-015's nuanced
verdicts).

### 3.12 Research Priority (discussed separately, not combined)
- **Expected information gain**: Medium — a genuinely new information
  channel (ownership/cash-generation signal vs. price-based factors), but
  real doubt (§3.6) about whether it's truly independent tempers this.
- **Implementation cost**: Lowest of any named candidate — simplest
  data-loading task (a binary flag vs. a continuous score), reuses
  existing `xs_rank`-style eligibility machinery.
- **Scientific novelty**: Medium — new family, but a narrower, more
  constrained version (payer status only) of a well-known effect (yield),
  not a novel mechanism.
- **Alpha potential**: Uncertain, capped by the construct-validity concern
  even in the event of a nominally positive result.
- **Data availability**: Tied-highest (with H-016) — zero new acquisition.
- **Robustness potential**: Genuinely low-turnover if confirmed (payer
  status changes rarely) — the strongest capacity/turnover story of any
  candidate in this document, IF the effect is independent, which is the
  open question.

---

## 4. Named but explicitly NOT proposed this wave: free-float / NGX X-Compliance data acquisition

Per the directive's own instruction — "if a hypothesis cannot actually be
tested with existing data, reject it immediately" — **free-float-adjusted
size and free-float-deficiency governance signals are not proposed as
hypotheses in this wave.** The NGX X-Compliance Report (identified in
`docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md §B1` as a "Near-term" free,
structured, official source) would directly address H-011's own disclosed
full-issue-cap limitation and open a genuinely new governance-signal
family, but no extraction has been performed and no structured free-float
table exists anywhere in the platform today. This is named here as the
**highest-value data-acquisition priority for a future wave** — not
ranked alongside H-016/H-017, and not force-fit into a third hypothesis
slot to satisfy a "top three" quota the evidence does not support at equal
readiness. Proposing it as a testable hypothesis today would violate the
directive's own falsifiability/data-availability discipline.

---

## 5. Final Ranking

### Rank 1 — H-016 (Standalone Liquidity Premium)

**Why it ranks first**: it is the only candidate directly motivated by a
LIVE, unresolved, real empirical tension already on the platform's own
permanent record (Phase R2's liquidity-direction puzzle) rather than a
generic gap-fill. Data availability is the best of any candidate audited
(reuses an already-built, already-unit-tested scoring function).
Engineering cost is low. It is also the candidate most likely to
MEANINGFULLY REVISE the platform's understanding of its own only
confirmed factor (H-011), regardless of which direction it resolves in.

**Evidence supporting pursuit now**: `liquidity_scores()` already exists,
already validated (I1-I5), and its own docstring flags this exact gap.
Phase R2 was completed one day before this audit and its unresolved
tension is fresh, not stale.

**Evidence against**: real risk that a positive result simply
re-discovers H-011 under a different label (Size/Liquidity entanglement is
expected to be substantial on NGX) — mitigated, not eliminated, by the
mandatory Spearman/orthogonality check built into the statistical plan.
Real risk of a stale-pricing artifact rather than a genuine premium —
mitigated by the mandatory lagged-return robustness check, which is a
genuinely new addition to this platform's standard statistical suite (no
prior hypothesis needed it in the same way).

**Does it advance the platform more than refining existing factors?**
Yes, directly — it either produces the platform's second validated,
independent factor (clearing the single largest architectural gap
identified in §1.9, opening Portfolio Construction/Ranking/Risk Engine),
or it produces a rejection that, per the platform's own standing
convention, sharpens institutional knowledge of exactly why and how the
Size premium concentrates the way Phase R2 found — a valuable outcome
either way, not contingent on confirmation.

### Rank 2 — H-017 (Dividend Payer-Status Tilt)

**Why it ranks second**: genuinely available today, lowest engineering
cost of any candidate, and opens an entirely new information channel
(cash-generation/ownership signal) distinct from every price-based factor
tested so far. Ranked below H-016 because its economic distinctiveness is
less certain (real, disclosed, still-unresolved risk that it merely proxies
Size or Volatility) and because it responds to a general gap rather than a
specific, fresh, unresolved finding the way H-016 does.

**Evidence supporting pursuit now**: data has been sitting ready and
unused since at least 2026-07-22 (Wave 3's own C5); lowest implementation
cost means it can run in parallel with H-016 without materially straining
research bandwidth, subject to the platform's own ≤2-active-hypotheses
rule — which this pairing exactly saturates, appropriately, rather than
exceeds.

**Evidence against**: the construct-validity risk is real and specific,
not boilerplate — established NGX dividend payers are very plausibly the
same large-cap, low-vol names already implicated (positively for size,
negatively for standalone low-vol) in the platform's existing factor
results. A confirmation here would need to survive the mandatory
orthogonality check to mean anything beyond what the platform already
knows.

**Does it advance the platform more than refining existing factors?**
Yes, but more provisionally than H-016 — a genuinely independent
confirmation would be valuable, but a construct-validity failure (a real,
live possibility) would mean this wave's marginal contribution is smaller
than H-016's regardless of outcome.

### Not ranked third: free-float/X-Compliance acquisition (§4)

Explicitly not force-ranked as a third hypothesis. It is real, well-
motivated, and plausibly high-value — but it fails the directive's own
data-availability bar today (no extraction performed, no structured table
exists) and is instead logged as the platform's next data-acquisition
priority, to be revisited as a hypothesis candidate only once that
extraction work is done and reviewed as its own deliverable, exactly as
Wave 3 correctly deferred Corporate-Action Event Drift (C3) for the same
reason (classification pipeline never promoted to evidence grade).

---

## 6. Explicit statement per the directive's final instruction

**This wave does NOT conclude "no new hypothesis should be tested."**
Two candidates — H-016 (Standalone Liquidity) and H-017 (Dividend
Payer-Status) — clear the full bar: theoretically motivated, falsifiable,
economically explained (including failure conditions and confounders
stated in advance), and testable today with zero new data acquisition.
The platform's own ≤2-active-hypotheses governance rule caps this wave at
exactly these two, which is a natural, not a strained, fit. **H-016 is
recommended to go first**, given its direct evidentiary link to Phase R2's
still-open finding; H-017 is a legitimate, lower-engineering-cost parallel
candidate if research bandwidth allows both, subject to owner decision.
Neither is pre-registered by this document — per unbroken convention,
full pre-registrations (exact universe, cost model, validation plan,
Expected Interaction section) are drafted and shown to the owner
separately, before any run.
