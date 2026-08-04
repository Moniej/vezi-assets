# Methodology Hardening — Phases M1-M5

*2026-08-04. No implementation, no database writes, no schema changes,
no extraction, no hypothesis registration, no H-017. This document
converts the Frontier Methodology Audit's (2026-08-04) code-level
findings into **empirical, database-verified evidence** by directly
querying `data/ngx.sqlite` (read-only, `mode=ro`) and running the
platform's own `universe.iru_members()` function against real historical
dates. Every claim is tagged **[Verified — empirical]** (measured
directly against the live database this session), **[Verified — code]**
(confirmed by reading source), **[Verified — literature]** (from the
prior audit's academic citations), or **[Judgment]** (informed
interpretation, not directly measured).*

---

## Phase M1 — Survivorship Validation

**The `securities.delisting_date` field is a dead field.** [Verified —
empirical]: 0 of 320 tracked securities have this field populated.
[Verified — code]: the only reference to `delisting_date` anywhere in
`src/` or `scripts/` is a single INSERT statement in
`scripts/phase1_smoke_test.py` — it is never read by `universe.py`,
`coverage.py`, or any hypothesis-facing code. **This means the
platform's survivorship-safety does not, and never has, depended on
this field** — a relevant clarification before assuming its emptiness
is itself the risk.

**141 of 320 tracked securities (44%) show a real, de facto
stale/suspended pattern**: their last recorded trade date is more than
365 days before the dataset's own overall maximum trade date
(2026-07-21) [Verified — empirical]. 82 of these 141 have a last trade
date in 2020 or later, meaning this is not purely a legacy-era
phenomenon. Only 4 of these apparent "disappearances" are explained by
a documented rename (`FO→ARDOVA`, `GUARANTY→GTCO`, `ACCESS→ACCESSCORP`,
`FBNH→FIRSTHOLDCO`, per `data/reference/symbol_renames.csv`) [Verified
— empirical: confirmed `GUARANTY`'s and `FO`'s raw price history
correctly stops exactly at their documented rename dates]. **The
remaining ~137 cases are either genuine delistings/suspensions or
undocumented renames — this audit could not distinguish which for each
individual name.** One specific case (`MOBIL`, last trade 2021-04-09,
1,655 rows of real history) was checked for a plausible successor
ticker (`ELF`, `11PLC`) and none was found in the dataset [Verified —
empirical: zero rows for either candidate ticker] — flagged as an
open, unresolved item, not a confirmed gap, since this audit did not
verify against an external NGX corporate-history source whether `MOBIL`
genuinely stopped trading or continues under an untracked symbol.

**The core empirical test — does the IRU correctly include/exclude
these names at the times it should, with no forward-looking leakage?**
Five real de facto stale/suspended tickers (`ASHAKACEM`, `CUSTODYINS`,
`7UP`, `EVANSMED`, `COSTAIN` — chosen as the oldest, most extreme
examples, a harder test than a randomly chosen recent one) were run
through the platform's actual `universe.iru_members()` function at 9
historical `as_of` dates each (45 total test points) [Verified —
empirical]. **Result: in every one of the 45 test points, each ticker
correctly appeared as IRU-eligible while it had sufficient recent
trading activity, and correctly disappeared from eligibility once its
trailing window went stale or infrequent — zero instances of
forward-looking survivorship leakage were found.** Example (`ASHAKACEM`):
eligible with rank 10-67 from 2015-06-30 through 2017-06-30, then
absent from 2017-09-01 onward, exactly tracking its real last-trade
date of 2017-07-03.

**The addition side was also tested.** `HBMNG` (listed 2026-07-09, only
9 trading days of history as of the dataset's end) is correctly
excluded from the current IRU snapshot; `FTGINSURE` and `ZICHIS` (101
and 103 trading days respectively — just past the 100-day frequency
floor) are correctly included [Verified — empirical]. No premature
inclusion of brand-new listings was found.

**Annual membership churn is plausible, not suspiciously stable.**
Year-end-to-year-end turnover (entries + exits, as a share of prior
membership) ranges 6.0%-12.2% across 2015-2025 [Verified — empirical],
with IRU size fluctuating between 79 (the first, partial year) and 100.
This is a real, non-trivial churn rate consistent with a
liquidity-rank-based universe genuinely responding to real market
change, not an artificially frozen or artificially smooth membership
list that might itself hint at a survivorship-favoring bug.

**M1 conclusion**: the IRU's point-in-time construction mechanism is
empirically verified, on a representative (not exhaustive) sample, to
be free of forward-looking survivorship leakage. This is real,
first-of-its-kind evidence for this platform — every prior document in
this series (the Wave 2 institutional audit, the Wave 5 strategic
review, the Frontier Methodology Audit) could only say this was
"architecturally correct but unverified." It is no longer unverified.
The residual open items — the ~137 unexplained stale tickers'
true cause, and whether the rename registry is complete — are real,
disclosed, and recommended (not fixed) below.

---

## Phase M2 — Return-Series Integrity

**Thin trading and zero-return clustering — the most significant new
finding of this document.** Measured directly on the current 100-member
IRU's real daily price data, 2021-2026 [Verified — empirical]:

- **Zero-volume days: 0.00%.** Every recorded trading day shows some
  nonzero volume figure — there is no simple "no trading occurred"
  signal in the data.
- **Zero-return days (close identical to prior close), despite nonzero
  volume: mean 52.7%, median 48.3% across the 100 current IRU members.**
  The top of the distribution is extreme: `NIDF` (97.2%), `TOTAL`
  (95.6%), `TRANSPOWER` (94.0%), `BETAGLAS` (92.8%), `AIRTELAFRI`
  (91.5%), `NESTLE` (90.2%), `CONOIL` (90.1%), `OKOMUOIL` (90.0%),
  `BUAFOODS` (89.6%), `GEREGU` (89.6%) — **all currently inside the
  investable, top-100-by-liquidity universe**, not marginal or excluded
  names.
- **Stale-price runs**: the longest consecutive run of an identical
  closing price, per ticker, has a median of 24.5 trading days and a
  maximum of 262 consecutive trading days (`GEREGU`) — over a full
  year of trading sessions with no recorded price change.
- **Cross-sectional non-synchronicity on actual formation dates**:
  sampled at six 2024-2025 quarterly formation dates, 92-99 of the 100
  IRU-eligible names have any price row at all on a given date, and
  **of those, only 45.2%-56.8% show a genuinely fresh (non-repeated)
  close.** On a typical cross-sectional ranking date, less than half
  the investable universe has a price that actually reflects that
  day's information.
- **Missing-observation gaps**: per-ticker row coverage against the
  full 622-session 2024-2026 market calendar mostly clusters at
  99-101%, but the minimum found was 16.2% for at least one ticker — a
  real, if isolated, mid-period gap (likely a suspension/relisting), not
  investigated further in this pass.

**This is a real, previously unquantified, and materially important
finding.** The platform's own code (`backtest_xs.py`) already contained
a comment acknowledging that forward-filled (no-row) days would
"understate vol for stale names by injecting zero-return days that
never happened" and masks those out. **What that mask does not catch is
exactly what this measurement found**: days where a price row DOES
exist, volume is nonzero, but the close is identical to the prior
close. These are not excluded from volatility, Sharpe, placebo, or HAC
calculations anywhere in the codebase. Given roughly half of all daily
observations for a typical current-IRU name are literal zeros, realized
volatility estimates for these names are very likely materially
compressed relative to their true underlying economic volatility, and
any statistic built from daily autocorrelation structure (HAC lag
selection, in particular) is operating on a return series with an
artificial "zero-zero-zero-then-jump" pattern baked in by market
structure, not investor behavior.

**Corporate-action adjustment — a real, structurally present gap not
previously disclosed anywhere in the platform's documentation.** The
`corporate_actions` table contains only 31 rows platform-wide: 30
`dividend_cash` and exactly 1 `rights_issue` [Verified — empirical].
**Erratum, added 2026-08-04 during H-017's pre-registration**: these 31
rows all belong to `SYNBNKA`/`SYNBNKB`/`SYNBNKC` — synthetic test
fixtures, not real NGX securities (confirmed via `securities.name ==
securities.ticker`, no real board/sector data). `corporate_actions`
therefore contains **zero rows of real platform dividend data** — this
section's original framing of the 31 rows as real platform data was
incorrect and is corrected here rather than left standing. This does
not change the section's core conclusion (the primary engine has no
bonus/scrip-issue adjustment mechanism regardless of what
`corporate_actions` contains) — see
`docs/PREREG_H-017_dividend_payer_status.md` Section 6 for the real,
usable dividend-closure data source
(`data/reference/exdiv_closure_calendar.csv`) this erratum was caught
while auditing. **Zero `bonus_issue` rows exist**, despite
`extracted_facts` narratively
confirming at least one real bonus-issue event occurred (`fact_id 27`,
AGM date 2021-06-24 — though with no usable numeric ratio or clean
ex-date for a direct spot-check) [Verified — empirical]. [Verified —
code]: `backtest_xs.py` — the engine that produced H-011 and every
per-stock hypothesis since — never queries `corporate_actions` at all;
only the separate `engine_full.py` (not used for any confirmed
hypothesis) has a `tr_adjustments` mechanism. **This means the
platform's primary engine has no dividend reinvestment (already
disclosed, a known bias) AND no bonus/scrip-issue price adjustment
(not previously disclosed anywhere).** This is a real, structurally
present risk category the same shape as the dividend gap, but
potentially larger in per-event magnitude — a bonus/scrip issue
mechanically resets price per share by a much bigger single-day factor
than a typical dividend yield, and if unadjusted would show up in a raw
return series as a large, spurious one-day negative return. **This
audit could not empirically quantify how many hypotheses' results this
affects**, because no usable bonus-issue event with a clean date/ratio
was available to spot-check directly against `equity_prices` — this is
disclosed as a real, identified risk, not a measured one.

**Benchmark date alignment**: re-confirmed by direct code reading
(`backtest_xs.py`'s `benchmark_targets()` applies the identical
rebalance step and execution lag as the strategy legs) — no new issue
found; classified **addressed**.

**Which issues are real (measured today) vs. theoretical**:

| Issue | Status |
|---|---|
| Thin trading / zero-return clustering | **Real, measured, severe** — 48-97% of days, even inside the investable universe |
| Stale-price runs | **Real, measured** — up to 262 consecutive sessions |
| Non-synchronous cross-sectional trading on formation dates | **Real, measured** — under 57% of the universe has a fresh price on a typical formation date |
| Missing-observation gaps | **Real but isolated** — affects a small minority of tickers |
| Bonus/scrip-issue price-adjustment gap | **Real, structurally present, not numerically quantified** — a genuine risk this audit could not size |
| Dividend-reinvestment exclusion | **Real, but already known and disclosed** — not a new finding |
| Benchmark date-misalignment | **Checked, not found** — theoretical concern, addressed by existing code |
| Suspended securities as a distinct category | **Subsumed by the M1 stale-ticker finding** — the same 141 names are both "possibly delisted" and "possibly suspended"; this audit could not cleanly separate the two causes |

---

## Phase M3 — Liquidity Methodology Review

*Building directly on the Frontier Methodology Audit's literature
review (Amihud & Mendelson 1986, Lesmond-Ogden-Trzcinka 1999,
Bekaert-Harvey-Lundblad 2007), now sharpened by M2's own empirical
finding that NGX's zero-return-day rate is not a theoretical EM concern
but a measured, severe, present-day characteristic of this platform's
own investable universe.*

| Proxy | Literature support | Feasible with existing platform data? | New data needed? | Architectural change needed? |
|---|---|---|---|---|
| **ADTV (currently used, H-016)** | Practitioner-standard; but [Verified — literature] Bekaert-Harvey-Lundblad (2007) found turnover-style measures do **not** significantly predict emerging-market returns | Yes — already implemented | No | No |
| **Turnover (volume / shares outstanding)** | Same paper: turnover-type measures underperform as EM return predictors regardless | **No** — [Verified — empirical: zero hits for `shares_outstanding`/`free_float` anywhere in the codebase] no shares-outstanding data exists on this platform at all | Yes (the same free-float dataset already gated elsewhere, per the Free Data Source Audit) | No |
| **Amihud (2002) illiquidity ratio** (\|return\|/value traded) | Well-established, widely used in both DM and EM contexts | Yes — computable directly from existing `equity_prices` close/value_traded columns | No | No |
| **LOT (Lesmond-Ogden-Trzcinka 1999)** — zero-return-day proportion | [Verified — literature] the specific measure Bekaert-Harvey-Lundblad found **most** predictive of EM returns | Yes — **this audit's own M2 measurement is already most of the raw computation** | No | No |
| **Corwin-Schultz high-low spread estimator** | Literature-established bid-ask-spread proxy designed specifically for markets without direct quote data, using only daily high/low prices | Yes — `equity_prices` already has `high`/`low`/`close` columns for every session | No | No |
| **Free-float-adjusted ADTV/turnover** | Institutional standard (MSCI/S&P/FTSE frontier-index practice, per the Frontier Methodology Audit) | No | Yes (NGX X-Compliance, already an open owner decision elsewhere) | No |

**The central finding of this phase**: two genuinely promising
liquidity-proxy alternatives — LOT and the Corwin-Schultz estimator —
require **zero new data acquisition and zero architectural change**.
Both are computable today from columns the platform already ingests.
The LOT measure in particular is now doubly supported: by external
literature (Bekaert-Harvey-Lundblad's EM-wide finding) and by this
document's own direct measurement that NGX's zero-return-day rate is
real, severe, and present even within the top-100 investable universe
— meaning the raw signal LOT is built from is abundant on this exact
platform's own data, not merely theoretically available.

**Should H-016 eventually be revisited?** This is flagged here as a
**future research idea**, not a hypothesis being proposed or
registered now. [Judgment]: a re-test using LOT or Amihud would not be
"the same null test with extra steps" — turnover/ADTV and zero-return-
proportion are related but economically distinct constructs (one
reflects trading activity level, the other reflects price-discovery
friction/transaction-cost intensity), and the literature specifically
documents these two proxy families behaving differently in emerging
markets. **Whether NGX's liquidity premium (if any) loads on the LOT
construct rather than the ADTV construct is genuinely unknown and would
require an actual test to resolve** — this document does not predict
the outcome, only that the question is well-motivated and cheap to ask.

---

## Phase M4 — Methodology Consistency Audit

**Cross-sectional ranking — confirmed inconsistency, now more
consequential given M2.** [Verified — code, re-confirmed this session]:
`backtest_xs.py`'s `rank_scores()` (and every other `xs_*_scores()`
function) computes a z-score `(x-mean)/std`; `signal.py`'s index-level
engine instead uses percentile rank (`rank(pct=True)`), with its own
code comment explaining this was chosen specifically because it is
"robust to one sector's outlier return dominating a z-score." **No
comment anywhere in `backtest_xs.py` explains or defends its choice of
z-score.** Given M2's own finding that NGX return distributions are
dominated by long stale-price stretches punctuated by occasional large
jumps (exactly the return-distribution shape z-scores are most
vulnerable to), this inconsistency is more consequential than it
appeared before this session's empirical work.

**Winsorization: absent everywhere, and the absence has never been a
deliberate, documented decision.** [Verified — code, directory-wide
grep this session]: no scoring function anywhere in `src/ngxrot/`
winsorizes or clips a return or score distribution for outlier control
— the only `.clip()` calls found are for trade-size/capacity capping
(`backtest_xs.py:183-184`, `engine_full.py:151,250,259-260,263`),
unrelated to outlier treatment of returns or scores.

**Normalization/scaling: only two patterns exist platform-wide** — mean/
std z-scoring and percentile ranking. No min-max scaling or other
scheme was found anywhere.

**Classification — is the inconsistency intentional, historically
inherited, theoretically justified, or accidental?** [Judgment,
grounded in the code evidence above]: `signal.py`'s percentile-rank
choice is **theoretically justified** — a real, on-the-record
engineering rationale exists. `backtest_xs.py`'s z-score choice is
**not** theoretically justified anywhere in its own code, and
`backtest_xs.py` (the per-stock engine, built later for the "breadth
pivot" per this program's own history) does not appear to have
consulted or re-applied the reasoning already on record in the
platform's own older engine. The most accurate classification is
**historically inherited without re-examination, not a deliberate,
defended choice** — closer to accidental than intentional, given the
platform had already written down the correct concern in one place and
did not carry it to the other.

**Is winsorization's absence itself a gap, or a defensible choice?**
[Judgment]: this document does not conclude winsorization should
necessarily be adopted — genuine large one-day returns following a long
stale-price stretch may be real, economically meaningful information in
a market with this structure, and forcibly clipping them could destroy
signal rather than protect it. The finding is narrower and more
defensible: **no evidence exists that this platform ever made this
decision deliberately** — there is no code comment, design document, or
disclosed rationale addressing winsorization one way or the other, in
contrast to the percentile-rank decision, which is explicitly
documented.

**Recommendation**: a unified cross-sectional scoring convention is
warranted, converging the per-stock engine onto percentile rank (or an
explicitly-decided winsorized z-score alternative) to match the
platform's own already-justified precedent — and a deliberate,
documented decision on winsorization, whichever way it goes, rather
than its current undocumented absence. **Per instruction, no
implementation is proposed here — this is a recommendation for a future,
separately-authorized change.**

---

## Phase M5 — Research Readiness Review

**1. Is the methodology now sufficiently hardened for another wave of
factor discovery?**

**Substantially more hardened than before this session, but not fully
closed.** M1 converted the platform's single most-repeated,
longest-unresolved self-criticism (survivorship, flagged in the Wave 2
audit, flagged again in Wave 5, flagged again in the Frontier
Methodology Audit) from "architecturally correct, empirically
unverified" to **"architecturally correct, empirically verified on a
representative sample, zero leakage found."** That is real, meaningful
progress, not a restatement. Two new, real, previously-undisclosed gaps
were also found in the process (the bonus-issue adjustment gap in M2,
the ranking-inconsistency's now-sharper consequence in M4) — both are
cheap, well-scoped, zero-new-data engineering items, not open-ended
research questions.

**2. Is H-017 now justified?**

**Yes.** The survivorship concern — the item most directly relevant to
"is the universe H-017 would be tested on trustworthy" — now has real,
direct, empirical support, the strongest produced anywhere in this
audit series. The two open M2/M4 items (bonus-issue adjustment,
ranking consistency) are not specific to H-017 — they apply equally to
every hypothesis already run, including the confirmed H-011 — so
holding H-017 back specifically because of them would be an
inconsistent standard. **Recommend H-017 proceed, with both open items
disclosed explicitly in its own pre-registration's limitations section**,
consistent with this platform's existing disclosure discipline (the
same way H-011 discloses its own full-issue-cap limitation).

**3. Should H-016 ever be revisited?**

**Yes — as a genuinely well-motivated future research idea, not a
promise of a different outcome.** M3's finding that LOT and Amihud-style
proxies are computable today with zero new data, combined with M2's own
direct measurement that NGX's zero-return rate is severe and present
even in the investable universe, makes this a stronger, better-evidenced
case for revisiting H-016 than existed in the prior Frontier
Methodology Audit — but this document explicitly does not predict
confirmation. This is logged here as an idea for the next hypothesis
wave, not registered as a hypothesis under this document's own
no-registration constraint.

**4. What remains before the platform is genuinely frontier-market-
native, rather than developed-market methodology applied to frontier
data?**

Three concrete items, in order of readiness: (a) a deliberate design
decision and implementation for bonus/scrip-issue price adjustment in
the primary engine (M2); (b) unifying cross-sectional scoring onto the
platform's own already-justified percentile-rank precedent, and making
an explicit, documented winsorization decision (M4); (c) implementing
and testing a LOT or Corwin-Schultz-based liquidity/friction measure
alongside the existing ADTV measure (M3). All three require zero new
data acquisition and no owner decision beyond authorizing the
engineering work itself — the free-float/X-Compliance item remains
gated on a separate, already-open data-acquisition decision outside
this audit's scope.

---

## Institutional Adversarial Review

### Frontier Market Academic

**Criticism**: "Your 48-97% zero-return-day finding is remarkable, but
have you ruled out that this is a data-quality artifact rather than
genuine market thinness — e.g., a stale quote being carried forward
while volume is independently (and possibly wrongly) populated from a
different feed? You checked zero-volume-days=0.00%, but that's
consistent with either a real explanation or an artifact."

**Response**: A fair and important limit to state explicitly, not
paper over. This audit cannot fully rule out the artifact explanation
with the checks performed — confirming zero-volume-days are absent is
consistent with genuine thin trading (real trades clearing at an
unchanged price) and with a data-pipeline artifact (volume/value_traded
populated independently of price staleness). **The qualitative
direction of this finding — that NGX exhibits severe thin-trading/
zero-return characteristics — is well-supported independently by the
external African-market microstructure literature cited in the prior
Frontier Methodology Audit**, so this is very unlikely to be entirely
an artifact. But the **exact magnitude** (48% median, 97% for the worst
name) should be treated as provisional pending a direct spot-check —
e.g., manually cross-referencing a handful of `GEREGU`'s 262
consecutive identical-close sessions against NGX's own published daily
bulletins — which this audit did not perform. This is added here
explicitly as the recommended next verification step before this
number is used for anything beyond directional evidence.

### Quant Research Director

**Criticism**: "Your M1 'complete empirical audit' actually tested 5
hand-picked tickers plus a population-level churn check. That is real
evidence, but it is not the complete audit the task asked for. What is
your actual confidence this generalizes to the other 136 stale
tickers you didn't individually test?"

**Response**: Accepted directly — "complete" overstates what was
delivered, and this is corrected here rather than left as an implied
overclaim. What was actually done: a deliberately extreme, non-random
sample (the oldest, most clear-cut de facto delisted/stale names,
arguably a harder test than a randomly chosen recent case) tested at 9
dates each, plus a full-population, all-year churn sanity check. **The
structural reason to expect this generalizes** is that `iru_members()`
is generic trailing-window code with no per-ticker special-casing
anywhere in it — the same logic that correctly handled `ASHAKACEM`
mechanically applies identically to every other ticker. But this is
stated as [Judgment, grounded in a representative but partial sample],
not as a claim that all 141 candidates were individually verified —
a full, individual verification of every stale ticker was not
performed and would be the natural next step if a fully exhaustive
audit were later required.

### Asset Pricing Researcher

**Criticism**: "You recommend eventually revisiting H-016 with a
different liquidity proxy, but H-016 already tested a liquidity effect
and found nothing. Why would swapping proxies be expected to find
something different, rather than just re-running the same null result
with extra steps?"

**Response**: A legitimate check, and the honest answer is that this
document does not predict a different result — it explicitly declines
to. The reason a re-test is still worth flagging as a future idea,
rather than dismissed, is specific and narrower than "try again and
hope": Bekaert-Harvey-Lundblad's finding is not a vague preference for
one proxy over another, it documents a specific behavioral divergence
between turnover-type measures (which failed to predict EM returns in
that study) and zero-return-proportion measures (which succeeded) —
two economically distinct constructs that happen to share the word
"liquidity." H-016 tested the first construct. Whether the second
construct behaves differently on NGX is a genuinely open, unanswered
question, not a foregone one — this document's role is to note that
testing it would be cheap (zero new data) and well-motivated, not to
claim it would succeed.

### Statistical Methodologist

**Criticism**: "You list 'no winsorization anywhere' as a finding, but
winsorization has real costs too — it mechanically distorts the true
distribution and can destroy genuinely meaningful extreme-return
information, especially in a market where large one-day repricings
after a long stale stretch may be real economic news, not noise. Isn't
flagging this as a gap presuming an answer that isn't obviously
correct?"

**Response**: Accepted, and the framing is corrected here to avoid
that presumption. The finding is not "winsorization should be added" —
it is narrower: **no evidence exists that this platform ever made a
deliberate decision on winsorization either way.** The percentile-rank
choice in `signal.py` is explicitly documented and defended; nothing
comparable exists for the winsorization question in either engine. The
recommendation is for a documented decision, not a directional one —
the reviewer's own point (that clipping large post-stale-stretch
repricings could destroy real information) is a legitimate, on-the-
record argument that any future decision on this question should
weigh, not a reason to skip making one.

### Portfolio Manager

**Criticism**: "This is the third document in a row telling me not to
expect a deployable strategy yet, and this one adds two MORE findings
(the bonus-issue gap, the sharpened ranking-inconsistency concern) that
could theoretically affect past results. When does this stop
generating new reasons to wait?"

**Response**: A legitimate fatigue check that deserves a bounded,
concrete answer, not another hedge. Per M5 §1, this document does
**not** recommend further open-ended methodology research — it
recommends closing two specific, small, zero-new-data engineering items
(a bonus-issue adjustment mechanism, a unified ranking convention) and
explicitly states **H-017 is cleared to proceed now**, with both items
disclosed as known limitations rather than used as a blocking gate.
This is narrower in scope than the items the Frontier Methodology Audit
already asked for (the survivorship check, now done; the HAC/DSR
near-miss re-check) — it closes that loop rather than opening a new
one. Nothing in this document proposes another methodology-only wave
after this.

---

## Final Recommendation, After Review

Incorporating the review: the zero-return-clustering finding's exact
magnitude is now explicitly flagged as provisional pending a direct
spot-check against an independent source, while its qualitative
direction stands on independent literature support (Frontier Market
Academic); the M1 survivorship evidence is described honestly as a
representative, structurally-generalizable sample rather than an
exhaustive individual audit of all 141 candidates (Quant Research
Director); the H-016 revisit is stated strictly as a well-motivated
open question, not a predicted reversal (Asset Pricing Researcher); the
winsorization finding is reframed as "no documented decision exists,"
neutral on which decision is correct (Statistical Methodologist); and
the sequencing is stated with an explicit, bounded conclusion — H-017
is cleared to proceed now, two small engineering items are recommended
alongside or after it, and no further methodology-only wave is being
requested (Portfolio Manager).

**Owner decision: methodology is sufficiently hardened for H-017 to
proceed.** The bonus-issue adjustment mechanism and the unified
cross-sectional scoring convention should be scheduled as
separately-authorized engineering work, disclosed as known limitations
in H-017's own pre-registration in the meantime — exactly as the
platform has always disclosed comparable limitations (full-issue
market cap, no dividend reinvestment) in every prior hypothesis rather
than treating them as blockers.
