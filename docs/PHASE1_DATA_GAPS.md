# Phase 1 — Open Data Questions & Gap Analysis

Status: **ANSWERED 2026-07-15** — no premium data available; system designed
free/open-first with a provider-based Data Abstraction Layer (see README
"Data Abstraction Layer"). Retail fee assumptions retained and marked
`assumed`. Transaction costs are treated as an experimental variable in
Phases 2–4, not a fixed input. Sections below kept for the record; per-source
feasibility notes added.

## Feasibility probe results (2026-07-15)

| Source | Probe result | Implication |
|--------|-------------|-------------|
| ngxgroup.com indices page | Reachable; 30-min delayed CURRENT values; history behind paid X-DataPortal | Use for forward daily collection (conf 0.9); not a history source |
| investing.com NSE Banking historical page | Freely accessible daily OHLC + volume, no login wall; default view ~1 month, 52-week range shown; deeper history via date-range/download | Primary candidate for backfilled index history (conf 0.5); depth & adjustment policy still to verify per index |
| TradingView / Wayback archives | Not yet probed | Cross-check & membership reconstruction respectively |

## A. Open data-access questions (blocking)

### A1. Index level history — what do you actually have access to?
NGX has no public Yahoo-style API. Realistic options, in order of quality:
1. **Paid vendor terminal/export** (Bloomberg, Refinitiv, or a Nigerian vendor
   such as Meristem/CardinalStone research portals, Proshare archives) — do you
   have any of these?
2. **NGX Group website** (daily index summary / market data pages) — gives
   *current* values; deep history requires either their paid Market Data
   portal (X-DataPortal) or scraping archived pages. Do you have an
   X-DataPortal or similar NGX data subscription?
3. **Third-party aggregators** (investing.com, TradingView) carry some NGX
   sector indices with patchy history and unknown adjustment quality —
   acceptable as a cross-check, risky as the primary source.
4. **Manual CSVs** you already hold from a broker or prior work.

**Question:** which of the above (possibly several) can you provide? For each:
how far back, and in what format?

### A2. Constituent prices, volume and value traded
The ADTV/capacity model (Phase 3) needs per-stock daily **value traded**, not
just closes. NGX's daily price list publishes volume/value/deals per stock.
**Question:** do you have historical daily price lists (even as PDFs/Excel from
a broker mailing list), or only index levels? If only index levels, Phase 3's
capacity analysis degrades to sector-aggregate approximations — I will flag
that clearly rather than fake precision.

### A3. Historical index constituents & weights (the hard one)
NGX publishes constituent lists at semi-annual reviews (circulars/PDFs), but a
clean historical membership file likely doesn't exist publicly.
**Question:** do you have access to NGX review circulars, factsheets, or a
vendor constituents feed? If not, the fallback is reconstructing membership
from archived circulars/Wayback captures — slow, and any period we cannot
document gets **excluded from constituent-level claims** rather than backfilled
with today's membership (which would be survivorship bias by construction).

### A4. Corporate actions
**Question:** source for dividends/bonuses/rights with qualification &
markdown dates? Candidates: NGX X-Issuer announcements, company IR pages,
registrars (e.g. Meristem/GTL/Africa Prudential notices). Without this there is
no total-return series and momentum on price-only indices will *understate*
high-dividend sectors (Banking especially — this materially biases the signal,
it is not a rounding error).

### A5. Broker economics
**Question:** your actual negotiated brokerage rate and a sample contract note
(fee lines) to replace the assumed schedule below.

### A6. Budget/appetite
**Question:** is paying for a data source (NGX market data licence or vendor)
on the table, or is this strictly free/scraped/manually-held data?

## B. Assumptions made (correct me)

| # | Assumption | Confidence |
|---|-----------|------------|
| 1 | Brokerage max 1.35%, both sides | assumed |
| 2 | SEC fee 0.30% buy-only; NGX fee 0.30% sell-only | assumed (sides unverified) |
| 3 | CSCS fee 0.06% both sides | low |
| 4 | Stamp duty 0.08% both sides | assumed |
| 5 | VAT 7.5% on commission+fees (5% pre-Feb-2020) | assumed |
| 6 | Dividend withholding tax 10% for individuals/local | assumed |
| 7 | NGX marks price down on qualification date (its ex-date analogue) | medium |
| 8 | Sector indices launched ~2009 (Banking/Insurance/Oil&Gas/Consumer/Industrial), Premium & Pension ~2015 | approximate — verify |
| 9 | Sector indices are capped float-adjusted mcap; ASI is full mcap | verify per methodology docs |
| 10 | Published sector indices are **price** indices, not total-return | verify |

## C. Gap analysis — what's missing and what it threatens

| Gap | Threatens | Mitigation in schema |
|-----|-----------|----------------------|
| No confirmed source for deep index history | Everything | Blocked on A1; no scraper written until answered |
| Historical constituents likely unreconstructable for parts of pre-2020 | Survivorship-bias defense; capacity model | `index_membership.announced_date` + rule: undocumented periods are excluded, not backfilled |
| Dividend/TR data availability unknown | Momentum ranking bias against high-yield sectors | `corporate_actions` table ready; if unfillable, run price-only variant with an explicit yield-bias caveat |
| Per-stock value-traded history unknown | ADTV capacity constraint (Phase 3) | `equity_prices.value_traded`; degrade to sector-aggregate ADTV with a flag if missing |
| Fee schedule unverified | Entire cost realism of Phase 3 | `cost_schedule.confidence='assumed'`; backtest report will watermark results "costs unconfirmed" until confirmed |
| Reconstructed history has `as_of_date` = capture date, not historical knowledge date | PIT guarantees weaken for scraped history | Honest limitation, documented in schema header; announcement dates are the real defense |

## D. Statistical-power warning (flagging now, before any backtest exists)

With ~7–9 sector indices, monthly rebalancing, and realistically ~2009/2015 →
2026 of usable history, a top-N rotation makes roughly **130–200 rebalance
decisions total**, spanning only 2–3 macro regimes — and the 2023–24
devaluation repriced *everything* at once, so regimes are not independent
samples. Any Sharpe ratio from this sample has enormous error bars. The
validation phase (walk-forward + placebo) mitigates but cannot eliminate this.
If the strategy "works", the honest claim ceiling is *"consistent with an
edge, insufficient data to prove one."* Expect that sentence in the final
report even in the good case.

## E. Cost hurdle warning

At the assumed max-brokerage fee stack, a round trip costs **~3.8%** of trade
value. A monthly top-3-of-9 rotation that turns over even one sector slot per
month pays ~10–15%/yr in costs; full monthly turnover would pay ~23%/yr.
Quarterly rebalancing or negotiated institutional brokerage (~0.5–0.75%) is
likely *required*, not optional, for viability. Phase 2's turnover/cost
sensitivity table will make this decision explicit.
