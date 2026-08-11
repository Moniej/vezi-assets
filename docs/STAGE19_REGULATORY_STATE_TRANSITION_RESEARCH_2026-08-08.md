# Stage 19 — Regulatory State-Transition Opportunity: Research Gate

**Date:** 2026-08-08
**Status:** Research only. No hypothesis registered. No H-011/H-019 modification. No backtest run.
**Objective (as given):** determine whether regulatory state *transitions* create persistent, tradable
mispricing on NGX after accounting for information already captured by H-011 — not whether regulatory
events in general are interesting.

---

## 1. H-011 confound / independence check

`size_scores()` (`src/ngxrot/backtest_xs.py:319`) was re-read directly. It consumes only
`panel["mcap"]` (from `load_market_cap_panel()` / `data/reference/market_cap_panel.csv`) and
price-panel-derived IRU eligibility. No event, regulatory, or personnel field is referenced anywhere in
the function or its call chain. **Mechanical independence from any regulatory-event table is confirmed.**

Economic/common-cause check: of H-011's 20-name universe, 5 tickers have a regulatory-state event
already on record (DEAPCAP, OMATEK, REGALINS, TANTALIZER, UNIVINSURE). Ranking all 20 by latest
available market cap (smallest → largest):

| Rank | Ticker | Mkt cap (₦m) | Flagged? |
|---|---|---|---|
| 1 | MCNICHOLS | 153.6 | |
| 2 | **DEAPCAP** | 2,850.0 | ✓ |
| 3 | NSLTECH | 4,786.8 | |
| 4 | **OMATEK** | 5,707.1 | ✓ |
| 5 | WAPIC | 8,790.0 | |
| 6 | LEGENDINT | 9,000.0 | |
| 7 | ROYALEX | 11,408.0 | |
| 8 | **REGALINS** | 14,404.5 | ✓ |
| 9 | RTBRISCOE | 14,998.5 | |
| 10 | **UNIVINSURE** | 15,040.0 | ✓ |
| 11–19 | (11 unflagged names) | 15,580–21,771 | |
| 20 | **TANTALIZER** | 22,000.0 | ✓ |

**Finding: mixed, not uniform.** 2 of 5 flagged names (DEAPCAP, OMATEK) sit in the bottom quintile,
partially supporting a small-cap/distress co-occurrence. But REGALINS and UNIVINSURE are mid-pack, and
TANTALIZER is the single **largest** name in the entire H-011 universe — directly contradicting a
simple "regulatory distress = small cap" story. There is no clean confound to correct for and no
evidence that H-011's size factor is silently proxying for regulatory-state distress. This does **not**
by itself validate a regulatory-transition factor — it only clears H-011 of being a hidden explanation
for it.

---

## 2. Corpus expansion — result: partial DATA GAP, partial success via a different channel

**Dead end (disclosed):** the current X-Compliance PDF (`wpdmdl=40533`) is a *rolling* download-manager
pointer — it always serves the report **as of the most recent Friday**, not a fixed, dated document.
Confirmed by re-fetch: the same URL previously cached by a search engine under a "27 February 2026"
description returned the 2026-08-07 report body when actually downloaded. There is no discoverable
dated-ID archive of past X-Compliance reports (`ngxgroup.com/exchange/data/delisted-companies/` and the
report-listing page are both JS-rendered with no static document links; targeted searches for other
`wpdmdl=` IDs surfaced only the same current ID or unrelated single-company NCCG reports). **Beyond the
two snapshots already in hand (2021-04-09, 2026-08-07), no further dated X-Compliance PDF snapshots
could be acquired. This sub-task is a genuine DATA GAP, not a smoothed-over absence.**

**Successful alternate channel:** targeted news search (Nairametrics, african-markets.com) for
suspension/delisting *events* by name surfaces real, dated, independently-corroborated transitions that
supplement the PDF corpus — this is the same evidentiary channel Stage 17/18 already used successfully.
Nothing below has been ingested into `events`/`documents` (no pipeline run, per the "no backtest, no new
factor" constraint) — these are **documented research findings with source URLs**, presented as raw
material for the inventory in §3, not as platform-recognized events.

---

## 3. Transition inventory (state-level vs. transition, kept explicitly separate per Task 6)

**State levels** (a snapshot condition, e.g. "currently on DWL") are what Stage 18 mostly worked with.
**Transitions** (a discrete change in state, with its own announcement date) are the object of this
stage. The table below lists only genuine transitions, each with its own knowledge date.

| Ticker | Transition | Date (announced) | Source |
|---|---|---|---|
| Royal Exchange, C&I Leasing +7 others | normal → suspension (accounts default) | 2022-07-01 | [Nairametrics](https://nairametrics.com/2022/07/01/nigerian-exchange-suspends-royal-exchange-ci-leasing-7-others-for-default-in-audited-financial-statements/) |
| Mutual Benefits Assurance | normal → suspension (accounts default) | 2024-07-08 | Nairametrics (cited in the lift article) |
| Mutual Benefits Assurance | suspension → **lifted** | 2025-03-20 (announced 2025-03-23) | [Nairametrics](https://nairametrics.com/2025/03/23/ngx-lifts-suspension-on-mutual-benefits-assurance-shares-after-compliance-update/) |
| ASO Savings & Loans | suspension (2017) → **lifted** | 2025-10-21 | [Nairametrics](http://nairametrics.com/2025/10/23/ngx-lifts-eight-year-suspension-on-aso-savings-loans-shares-trading-resumes/) |
| ASO Savings & Loans | normal → **re-suspended** | 2025-11-22 | [Nairametrics](http://nairametrics.com/2025/11/22/ngx-suspends-trading-on-aso-savings-loans-this-is-why/) |
| International Energy Insurance (IEI) | suspension → **lifted** | 2025-10-07 | [Nairametrics](http://nairametrics.com/2025/10/07/ngx-lifts-suspension-on-iei-shares-as-active-trading-returns-in-october-2025/) |
| Zichis Agro-Allied | suspension → **lifted** | 2026-03-23 | [Nairametrics](http://nairametrics.com/2026/03/23/ngx-lifts-suspension-on-zichis-agro-allied-shares-after-regulatory-review/) |
| DN Tyre & Rubber, Greif Nigeria | restructuring/DWL → **final delisting** | 2026-04-09 (final notice originally served 2018) | [Nairametrics](http://nairametrics.com/2026/04/09/ngx-to-delist-greif-dn-tyre-over-compliance-failures-liquidation/), [Businessday](https://businessday.ng/companies/article/ngx-to-delist-dn-tyre-greif-nigeria-over-compliance-failures/) |
| Union Dicon Salt, DEAPCAP, Multi-Trex, STACO Insurance, Fortis Global Insurance | (current DWL state, per most recent X-Compliance report and corroborating press) | ongoing / 2026-08-07 snapshot | X-Compliance 2026-08-07; [african-markets.com](https://www.african-markets.com/en/stock-markets/ngse/5-companies-placed-on-ngx-delisting-watchlist-3-others-enter-final-stage) |
| (aggregate) | 8 companies delisted from NGX in 2025 | 2025, various | [african-markets.com](https://www.african-markets.com/en/stock-markets/ngse/eight-companies-exit-the-nigerian-exchange-in-2025-a-year-of-regulatory-discipline-and-market-consolidation) |

This is materially broader than Stage 18's 8-event corpus: it spans **2022–2026** (4 years, not one
snapshot pair) and separates cleanly into three transition *types*: (a) suspension-imposed, (b)
suspension-lifted, (c) final delisting. Per the user's explicit priority, suspension-lifted is examined
in most depth below.

---

## 4. Per-transition PIT / novelty / survivorship / redundancy notes

- **Knowledge timestamp**: for every row above, the cited article's publish date is the earliest
  confirmed public knowledge date. None of these have been cross-checked yet against an NGX first-party
  same-day circular (the X-Compliance report only captures a Friday snapshot of *state*, not the
  transition date itself, except where its own "REMARK" column names a board-meeting date). Treat the
  news date as the **outer bound** on `knowledge_timestamp`, not a verified NGX-corporate-action
  timestamp — a real, disclosed limitation of this research-only pass.
- **Novelty**: each transition above is a discrete, dated event distinct from mere state persistence
  (e.g., DEAPCAP's DWL membership has been continuously public since ≥2021 per Stage 18 — that is
  *state*, not a *transition*, and is excluded from "novel" treatment here).
- **Survivorship**: see §5 — resolved as a platform-level finding, applies to all rows.
- **Redundancy check**: none of these transitions is already captured by H-011 (confirmed §1) or by the
  existing H-019 GMC/CIR event families (management_change / corporate_restructuring / merger /
  ownership_change) — suspension and delisting are a structurally different `event_type` not covered by
  the frozen Stage 14 spec.

---

## 5. Survivorship bias — resolved, revises Stage 18's framing

Checked `equity_prices` against `securities` for 6 confirmed-delisted names (NOTORE, MRS, MEDVIEWAIR,
CAPOIL, TOURIST, ASOSAVINGS):

| Ticker | Price history range | Rows |
|---|---|---|
| NOTORE | 2018-08-02 → 2025-06-02 | 357 |
| ASOSAVINGS | 2014-07-02 → 2025-11-18 | 156 |
| (MRS, MEDVIEWAIR, CAPOIL, TOURIST — similar pattern, history retained through/near actual last-trade date) | | |

**Finding: `equity_prices` retains delisted/suspended names' history through or very near their actual
last trading date.** This is a materially more positive result than Stage 18's "high and structural"
survivorship-bias framing implied, and should be read as a **revision**, not an addition: the platform
is *not* silently dropping delisted names from its price panel. ASOSAVINGS is a direct hit on the new
inventory above — its price data ends 2025-11-18, four days before its 2025-11-22 re-suspension, exactly
as expected for a name that stopped trading.

**Separate, distinct, still-open gap**: `securities.delisting_date` and `securities.delisting_reason`
are NULL for all 6 checked tickers. This is a metadata-completeness gap, not a data-availability gap —
the underlying price history is present and usable; only the structured "this ticker is delisted, as
of X, for reason Y" flag is missing. Any future factor construction would need to derive delisting
status from price-data gaps or the transition inventory itself, not from `securities` fields, until this
metadata gap is separately remediated.

---

## 6. Adversarial stress test on the strongest candidate: ASOSAVINGS suspension-lift

This is the cleanest, most complete example in the new inventory — worth the same scrutiny Stage 18 gave
DEAPCAP.

Direct query of `equity_prices` for ASOSAVINGS around the 2025-10-21 lift:

| Date | Close | Volume |
|---|---|---|
| 2025-10-22 | 0.55 | 14,676,337 |
| 2025-10-23 | 0.60 | 11,300,155 |
| 2025-10-27 | 0.72 | 4,358,555 |
| 2025-10-31 | 1.03 | 20,034,749 |
| 2025-11-03 | 1.07 | 108,946,469 |
| 2025-11-18 (last recorded) | 1.07 | 5,262,202 |

Price nearly **doubled** (₦0.55 → ₦1.07) in the eight trading sessions following resumption, then held
near that level until the 2025-11-22 re-suspension (last recorded price 2025-11-18, four sessions before
the halt — consistent, not contradictory).

Adversarial checks, applied deliberately against this result:

1. **Is this genuine mispricing or a mechanical reopening-auction artifact?** After an 8-year halt there
   is no live market-clearing price; the first print is a repricing event by construction, not evidence
   of an exploitable signal. The daily ~+9-10% moves in the following days are consistent with
   exchange-imposed daily price-limit ratcheting toward a new equilibrium (a known NGX mechanical
   pattern for reopened suspended stocks) rather than gradual information absorption. **This weakens the
   "alpha" interpretation substantially** — a limit-up ratchet is not obviously capturable as an
   entry-at-close strategy either, since each day's close is already at the daily cap.
2. **Was the information already stale/telegraphed?** The lift itself was NGX-announced and
   simultaneously reported — no information edge existed at `eligible_from` beyond what every other
   market participant had. The prior 8-year suspension itself had been continuously public.
3. **Execution feasibility**: whether a real order could have been filled at the cited closing prices
   during a reopening-auction regime (which often uses special call auctions with volume/price
   constraints) is unverified — a real, disclosed uncertainty, not glossed over.
4. **Exit-side liquidity risk**: the position would have been marked at ₦1.07 on 2025-11-18 with **no
   further ability to trade** after the 2025-11-22 re-suspension — a concrete illustration of the
   platform-wide liquidity-lockup risk any suspension-lift strategy must model explicitly, not a
   hypothetical.
5. **Base rate of the ratchet pattern**: without checking IEI's and Mutual Benefits' price series the
   same way, it cannot yet be claimed this is a repeatable pattern rather than an ASOSAVINGS-specific
   outcome — **not yet checked, an open item**, not fabricated as confirmed.

**Net read**: this survives the DEAPCAP-class disproof (it is not a pre-existing unrelated price run
misattributed to the event) but is undermined by a *different* adversarial angle — the move looks more
like mechanical price-discovery/limit-ratchet behavior after a long halt than genuine information-driven
mispricing, and the entry/exit mechanics (auction fills, sudden re-halt) are largely unverified or
actively adverse.

---

## 7. No LLM sentiment used

All event/direction judgments above are derived from NGX's own regulatory action (suspend/lift/delist)
and dated news reporting of that action — never from Gemini `investment_implications.direction` or any
other LLM-derived sentiment field, consistent with the platform-wide standing rule.

---

## 8. Coverage / frequency quantification

Across the 2022–2026 window actually searched: **at least 9 distinct transition events** identified
(1 batch-suspension in 2022 covering multiple names, 2 suspension impositions, 4 suspension-lifts, 1
final-delisting batch, plus the aggregate "8 delistings in 2025" figure). Suspension-lift specifically:
**4 events in roughly a 6-month window** (Oct 2025 – Mar 2026: Mutual Benefits was earlier, IEI Oct
2025, ASOSAVINGS Oct 2025, Zichis Mar 2026) — call it one every 6–8 weeks at the current pace, though
this is a short observation window and may not be a stable rate. This is **far more frequent** than
H-019's GMC/CIR corpus (11 qualifying events total, only 2 executable) and clears a coverage bar worth
taking seriously — but the sample is still small enough (n≈4 clean lifts) that any factor built on it
would face the same "six-event" statistical-power caution the user raised for H-019, likely worse.

---

## 9. Verdict, by transition type

- **Suspension-lifted → tradable mispricing: CONDITIONAL GO, with a specific and serious caveat.**
  Real, recurring (~4 clean events, roughly bi-monthly recently), PIT-checkable, not redundant with
  H-011 or H-019, and the strongest example (ASOSAVINGS) shows a large, sustained price move. But §6's
  adversarial pass raises a real possibility that the move is mechanical reopening-auction price
  discovery rather than genuine information lag, and execution/exit-liquidity risk is severe and
  concretely demonstrated (ASOSAVINGS was re-suspended 4 sessions after the last observed price). The
  minimum next step, if authorized, is **not** a backtest — it is: (a) pull IEI's and Mutual Benefits'
  post-lift price series the same way as ASOSAVINGS to check whether the ratchet pattern repeats or was
  idiosyncratic; (b) determine whether reopening-day fills are realistically achievable given NGX's
  actual auction mechanics for resumed suspended stocks (this may require reading NGX Trading Manual
  provisions on suspension resumption, not yet done); (c) explicitly model exit-side suspension-lockup
  risk as a cost, not ignore it.

- **Suspension-imposed (normal → suspension): NO-GO as a long-side signal.** By construction this is a
  negative catalyst on a name about to become untradable — there is no long entry mechanism consistent
  with the platform's long-only constraint, and shorting is out of scope platform-wide.

- **Final delisting (DWL/restructuring → delisted): NO-GO.** The DN Tyre/Greif example shows these
  processes run 8–12 years from first notice to execution — the "transition" itself is the least novel,
  most telegraphed event in the entire inventory, and there is no post-transition price series to
  capture a reaction in (the ticker stops trading). This matches and reinforces Stage 18's DEAPCAP
  finding rather than contradicting it.

- **Corpus-depth beyond news search: DATA GAP**, disclosed in §2. This caps confidence in the frequency
  estimate in §8 — it is a lower bound from what a handful of targeted searches surfaced, not a
  systematic archive count.

**Overall**: the regulatory state-transition track is not dead, but it is narrower than it first
appears — only the suspension-lift sub-type clears the bar, and even there the strongest evidence (§6)
cuts against a clean "mispricing" story more than it supports one. This is consistent with the user's
own framing: a track worth one more bounded diagnostic pass, not proof of alpha, and specifically not
yet a basis for hypothesis registration or backtest.

**Minimum preregistration needed for the next stage, if authorized** (described here, not registered):
a frozen definition of "suspension-lift event," sourced only from NGX RegCo's own suspension/resumption
notices (not third-party news, to avoid the timestamp-uncertainty flagged in §4) with `eligible_from` at
the first post-resumption trading session's close; explicit modeling of exit-side suspension-lockup risk
via a maximum holding-period cap or forced mark-to-last-trade rule; and, before any of that, completion
of the two open adversarial items in §6 (IEI/Mutual Benefits post-lift series check; reopening-auction
fill-feasibility check) — both diagnostic, not backtests, and both should be run before drafting a
preregistration, exactly as the DEAPCAP price-series check was run before Stage 18's verdict.
