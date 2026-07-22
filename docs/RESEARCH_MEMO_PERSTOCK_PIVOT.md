# Research Memorandum — The Per-Stock Pivot

*2026-07-16. Purpose: defend, with numbers, the decision to move the research
universe from sector indices to individual equities before committing
engineering effort. All arithmetic reproducible from the formulas shown.
Companion: STRATEGIC_REVIEW_2026-07.md.*

---

## 1. Observations gained

| Dimension | Sector-index research (as run) | Per-stock research (proposed) | Gain |
|---|---|---|---|
| Daily price observations | 8 × ~2,200 = **17,600** | ~100 × ~2,500 = **250,000** | 14× |
| Cross-sectional width per rebalance | 3–5 assets | ~100 names (~40 after correlation clustering; see §2) | ~20× effective |
| Event observations (announcement-timestamped) | 10 sector-scoped events | ~4,800 earnings filings + 11,546 corporate-action filings (2014→) | ~10²–10³× |
| Decisions per year (quarterly) | ~12–30 | ~400–1,600 | ~40× |

## 2. Statistical power (the decisive argument)

Fundamental law of active management: IR ≈ IC × √(breadth/yr). Years of
track record needed to *detect* skill at t = 2 is (2/IR)². Effective breadth
uses ~2 independent bets per sector rebalance (3–5 highly correlated assets)
and ~40 per stock rebalance (~100 names shrunk for common-factor
correlation — a deliberately conservative haircut of 60%).

| Structure | Breadth/yr | Years to detect IC=0.03 | IC=0.05 | IC=0.10 |
|---|---|---|---|---|
| Sector, quarterly (what we ran) | 8 | 556 | 200 | 50 |
| Sector, monthly | 24 | 185 | 67 | 17 |
| **Stock, quarterly** | 160 | 28 | **10** | 2.5 |
| **Stock, monthly** | 480 | 9.3 | **3.3** | 0.8 |

Reading: with our ~10-year sample, sector-level research had **very low
statistical power to detect realistically sized effects** (a good quant IC
is 0.05; sector detection at that skill needs on the order of two
centuries). Per-stock research detects IC = 0.05 in roughly the sample we
already possess. **Therefore, rejection of the sector-level hypotheses
should not be interpreted as strong evidence that no exploitable
sector-level effects exist** — the rejections are informative about our
sample structure at least as much as about the market. (Wording per IC
direction, 2026-07-16: the earlier draft overstated this as "structurally
incapable of confirming anything real"; the rejections remain valid as
tested, and the power limitation cuts both ways.)

Event studies scale even better (t = mean-AR/σ·√N, σ≈6% for 5–20-day NGX
windows): 10 events detect only a 3.8% per-event abnormal return; 3,000
events detect **0.22%** — well inside plausible PEAD magnitudes documented
in emerging markets.

## 3. Hypothesis families unlocked

Directly enabled by per-stock prices + volume (+ filing calendar):
**F2** cross-sectional TR momentum · **F4** liquidity premia/thin-trading
effects (volume data) · **F5** PEAD (with the no-OCR earnings calendar) ·
**F8** execution/capacity alpha (engine-full finally runs on real ADTV) ·
**F9** governance events × single names · plus a new family to register,
**F13: classic cross-sectional anomalies** (size, low-vol, short-term
reversal) — each a separate future hypothesis. With OCR/dividends (parallel
track): **F6** dividend capture and dividend-change direction signals.
The Discovery module's scanners (lead-lag, event-response, liquidity) gain
their power precondition. Sector-level work enabled F1 and F11 — both now
tested and rejected at achievable power.

## 4. Throughput estimate

Post-backfill, immediately pre-registrable: H-006 (PEAD), H-007 (per-stock
momentum); within weeks (as dividends/OCR and volume-quality work complete):
F4, F6, F13 candidates. The validation pipeline has demonstrated same-day
idea-to-verdict once data exists. Sustainable throughput estimate: **2–4
evidence-grade verdicts/month** versus the current state (queue effectively
empty; 4 verdicts total, all power-limited). The binding input becomes
hypothesis quality, which is what the Discovery module (built after
breadth) addresses.

## 5. New risks introduced (with mitigations)

**Survivorship (the serious one).** A vendor backfill reflects today's
listings; the dead are missing (Diamond Bank, Skye Bank, Union Bank, GSK
Nigeria, Ardova and others delisted/failed within our window). Long-only
relative strategies are less exposed than short-side ones, but missing
losers biases universe returns upward and can flatter momentum.
Mitigations, mandatory before any H-006/H-007 run: universe defined from
the **259-symbol filing calendar** (which contains dead names), not from
vendor availability; per-year coverage report (% of filing-active symbols
with prices) published in the data-quality report; names without obtainable
history recorded as coverage loss with an estimated bias direction; the
DelistedCompanies list and NGX daily snapshots (forward) close the gap going
forward. If pre-2019 coverage of filing-active names falls below ~70%,
research windows shorten rather than pretend.

**Liquidity/data quality.** Many of the 259 names barely trade: zero-volume
stretches, NGX price floors (stale prints), ±10% daily limits, bid-ask
bounce in kobo-priced stocks — all can fabricate momentum/reversal.
Mitigations: existing diagnostics (stale_price, liquidity_anomaly) run on
every name; investable-universe filter by trailing ADTV **pre-registered
per hypothesis** (top ~40–60 names likely carry >90% of value traded —
estimate to be verified in the backfill audit, not assumed); price-limit
days flagged. Vendor adjustment policy unknown (splits/bonuses): the
unexplained-jump diagnostic + corporate-actions calendar cross-check every
>25% move; symbol changes (GUARANTY→GTCO, ACCESS→ACCESSCORP…) require a
symbol-mapping table maintained with the universe. investing.com
rate-limiting (403s observed) requires paced acquisition over days, not
hours.

**Process risk.** More breadth = more scans = more false-discovery surface.
Unchanged countermeasures: pre-registration, scan-wide BH, placebo, frozen
OOS. No relaxation.

## 6. Steelman: the case AGAINST the pivot, answered

1. *"Sector research failed for fixable reasons (10 events); fix events
   first."* Even with perfect events, sector breadth caps at ~24/yr —
   detection of IC=0.05 needs 67 years (table above). Power, not events,
   was the binding constraint. **Stands.**
2. *"Per-stock IC will be lower — idiosyncratic noise eats the breadth
   gain."* Breadth wins unless IC degrades by √20 ≈ 4.5×, i.e. unless
   stock-level IC is <25% of sector-level IC. Cross-sectional anomalies
   (momentum, PEAD) are documented at the stock level in emerging and
   frontier markets; the premise that sector aggregation *concentrates*
   signal was our founding assumption and is now 0-for-4. **Pivot favored.**
3. *"Costs and capacity are worse in single names."* Partly true: impact is
   worse in small names. But (a) turnover as %NAV — the cost driver — is
   structure-comparable; (b) capacity is measurable by machinery we already
   built (engine-full/ADTV) and per-stock volume data is precisely what
   makes those measurements real; (c) a capacity-capped genuine edge is a
   finding, per the charter — scalability never vetoes validity. **Pivot
   favored, capacity reported honestly.**
4. *"Index data is professionally computed; raw stock data is dirtier →
   false discoveries."* True and priced in: the diagnostics suite exists,
   anchors will be spot-verified, and the validation gauntlet is unchanged.
   Dirty data produces rejections under our regime, not false confirms —
   the placebo and OOS guards bind. **Manageable.**
5. *"Sector indices were at least simple to trade."* Actually false — no
   investable NGX sector-index instrument exists; every sector backtest
   carried the "trades index levels" caveat. Per-stock strategies are what
   real execution looks like. The pivot *reduces* implementation fiction.

## 7. Industry comparison

The canonical quant-equity progression (visible across systematic funds and
the academic replication literature) is: (1) survivorship-clean point-in-time
universe and prices → (2) corporate-actions/total-return truth → (3)
event & fundamental data → (4) cross-sectional factor library → (5) cost/
impact-aware portfolio construction → (6) combination and production. Two
observations: (a) established practice fixes the **universe and breadth
first** — signals only after; our project inverted this and paid with four
underpowered cycles; (b) our platform already has stages 5's machinery and
an unusually strong validation layer for a project this size — the missing
pieces are exactly stages 1–3 at the stock level, which is what this pivot
acquires. We are not deviating from the proven path; we are correcting
back onto it.

## 8. Expected-return comparison of the alternatives

| Option | Eng. cost | Power outcome |
|---|---|---|
| **Per-stock backfill + earnings calendar** | ~2–4 days | First adequately-powered tests in project history (table §2) |
| OCR/dividends first | ~2–4 days | TR truth but still 3-asset breadth until prices exist — power unchanged |
| More sector-event curation | weeks | Breadth ceiling remains ~24/yr — power unchanged |
| Discovery module now | ~week | Scanners over 8 series — false-discovery factory |

The pivot is the only option that moves the detection frontier. Recommend
proceeding, with the survivorship audit as a **gating deliverable**: no
hypothesis pre-registers on the new universe until the coverage report is
published and the investable-universe filter is fixed per prereg.
