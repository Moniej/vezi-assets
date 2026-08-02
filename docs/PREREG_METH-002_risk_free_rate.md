# Pre-Registration / Design Record — METH-002: Point-in-Time CBN Risk-Free Rate

*2026-08-02. Not a factor hypothesis — a data-acquisition and statistical-
infrastructure fix to a previously self-disclosed placeholder
(`src/ngxrot/metrics.py`'s `rf_annual_pct` default of 0.0, flagged in its
own docstring as "WRONG for Nigeria"). Identified as the **Immediate**-
priority item in `docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`'s headline
finding. Per the mandatory benchmarking requirement, this document includes
Frontier/Emerging/Developed Market Assessments and a Statistical Robustness
review. Unlike a factor hypothesis, the *data-feasibility check* had to
come before this document could be written at all — one cannot pre-register
a plan around a data series whose real existence and extractability is
unknown in advance — so Section 1 records what was verified before design
decisions were frozen, exactly as METH-001 recorded its own trial-count
sourcing before computing any DSR value.

## 1. Data feasibility check (performed before any design decision was frozen)

Live web verification (2026-08-02) confirmed CBN's official MPC decisions
page (`https://www.cbn.gov.ng/MonetaryPolicy/decisions.html`) publishes a
complete, dated history of every Monetary Policy Rate (MPR) decision, each
carrying a sequential meeting number. Three separate fetches (a wide
2008–2026 pull, a narrow 2018–2023 pull, and a narrow 2023–2024 pull
requesting verbatim quotes) were cross-checked against each other's stated
meeting numbers. **This caught a real extraction error**: the wide pull's
"September 22-23, 2023" row was, per the narrow verbatim pull, actually the
**302nd meeting**, dated **September 22-23, 2025** — a summarization
artifact, not a real 2023 decision. It was excluded, not silently kept.
Cross-checking against meeting-number sequence (285th–288th, 292nd,
295th–297th, 302nd all landing on internally consistent dates and rates)
gives real confidence in the remaining 50 rows without asserting perfection.

**Known, disclosed real gap, not a scraping failure**: no MPC meeting is
recorded between the 292nd meeting (Jul 2023, MPR 18.75%) and the next
captured decision (Feb 2024, MPR 22.75%). This corresponds to a real,
historically documented event — the CBN leadership transition following
the suspension of the previous governor in June 2023 and confirmation of a
new governor in September 2023 — during which the MPC did not convene.
This is disclosed as a factual gap in the *calendar*, not a defect in the
extraction.

## 2. Design decisions and rejected alternatives

**Use MPR, not the actual NGN Treasury-Bill stop rate, as the risk-free
proxy.** Rejected alternative: pursue FMDQ or DMO's actual T-bill/bond
auction stop rates instead, which would be a truer "rate an investor could
actually earn." Rejected for this implementation because reliably
reconstructing a *complete, gap-free, decade-long* T-bill series through
the same fetch-and-cross-check process demonstrated above would require
materially more fetches with the same per-fetch reliability risk already
observed once — and MPR, while an imperfect proxy, is completely and
verifiably reconstructible with the effort actually available this
session. **This is a disclosed proxy choice, not a claim that MPR equals
the T-bill yield** — real T-bill stop rates track MPR with a variable
spread; a future METH-003 could replace this with the true T-bill series
without changing the architecture built here (the lookup interface is
rate-source-agnostic).

**Store decisions at `decision_date` (the meeting's last day), not a
later "effective" date.** Rejected alternative: use the meeting's first
day, or a fixed lag (e.g., +1 business day). MPR changes are communicated
and take effect at the close of the MPC meeting; using the last day is the
earliest date at which the new rate could be considered public information,
which is the conservative (no-look-ahead) choice.

**`NaN` before the earliest verified decision (2015-07-23), never
back-filled or estimated.** Rejected alternative: assume the rate held
constant at 13.0% (the earliest known value) further into the past, or use
a rough historical estimate. Both would be inventing data outside the
verified record — explicitly forbidden.

**Additive, opt-in wiring (`validation.use_real_risk_free_rate`, default
`False`), not a change to the existing default.** Rejected alternative:
change `_DEFAULTS["validation"]["risk_free_annual_pct"]` to some non-zero
constant, "fixing" the placeholder for every future run automatically.
Rejected because (a) a single non-zero constant is *still* not
point-in-time correct — real MPR ranged 11.5%–27.5% across the sample, so
any single flat number is simply a smaller version of the same error being
fixed — and (b) changing existing defaults would alter the recorded
behavior of every config that doesn't explicitly override it, which is not
"additive" in the sense this platform's convention requires. Instead, a new
optional parameter and a new opt-in config flag were added; every existing
frozen config and every historical registry row is completely unaffected.

**Report `sharpe_vs_real_rf` alongside, never in place of, the existing
`sharpe_vs_rf`.** Consistent with METH-001's own convention (report both
the existing and the new, more rigorous number, not a silent replacement).

**Compute the real-rate Sharpe from daily excess returns (portfolio return
minus that day's compounding-consistent daily-equivalent MPR), not from
`ann_return - mean(rf)`.** This is the technically correct treatment of a
time-varying risk-free rate (Sharpe = mean/std of the actual excess-return
series), not an approximation applied after the fact.

## 3. Validation plan

Synthetic + structural checks (`scripts/rehearse_riskfree.py`, T1–T6),
mirroring the platform's rehearsal convention:
- No look-ahead across a known real rate-change boundary (the day before a
  decision must see the OLD rate; the decision day itself sees the NEW
  rate).
- Dates before verified coverage return `NaN`, never a filled value.
- `coverage_status()` correctly distinguishes a fully-covered date range
  from one including an uncovered date.
- `metrics.compute()` is byte-for-byte identical to its pre-METH-002
  behavior when `rf_series` is omitted (backward compatibility, not just
  asserted — checked by direct dict equality against the pre-change
  function signature's output).
- The real-rate Sharpe is materially different from the flat-rate Sharpe
  on a synthetic window with known nonzero real rates (sanity check that
  the new code path actually does something, not a no-op).
- A window predating verified coverage correctly returns `None`
  (never a fabricated number) with a nonzero `real_rf_coverage_gap`.

Only after all synthetic/structural checks pass, and the existing R1–R12
rehearsal suite is re-run to confirm no regression, is the method applied
to real hypothesis evidence (Section 4 of the final report).

## 4. Benchmarking (mandatory, per the standing directive)

**Frontier Market Assessment** — *Current adoption*: no evidence found, in
this pass, of NGX-focused published research explicitly correcting Sharpe
ratios for a point-in-time-varying local policy rate rather than a flat
assumption; this is stated as absence of evidence in this review, not
absence in the wider literature. *Practicality*: high — the platform
already has the permanent reference-table pattern (`exdiv_closure_calendar
.csv`, `market_cap_panel.csv`) this fix reuses. *Strengths*: uses a free,
official, completely verifiable source. *Weaknesses*: MPR-as-proxy
diverges from the true investable T-bill rate by an unquantified spread —
disclosed, not resolved, in this phase.

**Emerging Market Assessment** — *Adoption*: using a central bank's own
policy rate as a risk-free proxy when a clean local T-bill series isn't
readily available is common pragmatic practice in EM-focused research
generally; not verified here against any specific published EM study.
*Academic support*: the underlying practice (risk-free rate = local
short-term government/policy rate, not a foreign rate or zero) is standard
finance methodology, not novel. *Known failures*: none documented; this is
a correction of a previously disclosed error, not a retest of a failed
technique. *Required adjustments*: none beyond what's disclosed (MPR/
T-bill spread).

**Developed Market Assessment** — *Institutional usage*: using the
relevant local risk-free rate (e.g., US Treasury bills for USD strategies)
is universal, non-controversial institutional practice; the *absence* of
this in the platform prior to today was itself the anomaly relative to
developed-market norms, not the presence of it now. *Evidence quality*:
strong — it is definitionally correct that Sharpe ratios require a real
risk-free rate; the only open question was data availability, not
methodology. *Implementation complexity*: low once the data exists (a
per-day lookup and a daily-return subtraction).

**Statistical Robustness** — HAC/Newey-West: unaffected by this phase
(orthogonal fix, both now available). Multiple hypothesis correction:
unaffected. Deflated Sharpe Ratio: **directly interacts** — every DSR
computation in METH-001 used the flat-0.0-rf Sharpe ratios; Section 5
below states plainly that those DSR figures should eventually be
recomputed against real-rf Sharpe ratios too, not left stale. Survivorship
bias: not addressed by this phase. Selection bias: not addressed by this
phase. Look-ahead bias: **directly addressed** — this phase's entire design
is built around eliminating a specific look-ahead risk (using a rate that
wouldn't have been known at the time). Data snooping: not addressed by
this phase.

## 5. Interaction with METH-001 (disclosed, not left implicit)

METH-001's Deflated Sharpe Ratio calculations used each hypothesis's
**flat-0.0-risk-free** daily excess-vs-benchmark Sharpe ratio as the input
to `deflated_sharpe_ratio()`. This phase computes a **different** Sharpe
(excess vs. the real risk-free rate, not vs. the benchmark) — the two are
not directly interchangeable inputs, and recomputing DSR using real-rf
Sharpe ratios is a distinct, separate exercise from what's reported here.
This is named as a follow-on item, not performed in this document, to
avoid conflating two different corrections in one number.
