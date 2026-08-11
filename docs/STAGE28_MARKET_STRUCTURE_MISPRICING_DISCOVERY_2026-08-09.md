# Stage 28 — NGX Market-Structure Mispricing Discovery Program

**Date:** 2026-08-09 (platform price data current through 2026-07-21)
**Status:** Discovery only. No hypothesis registered, no factor built, no backtest, no strategy return
calculated. Per instruction, this program does **not** revisit insider dealing, H-011, H-019, staleness,
regulatory transitions, PEAD, or any other previously-rejected mechanism — those remain closed
(`docs/RESEARCH_ROADMAP_2026-07.md` §2a-2c).

**Question:** what structural feature of the NGX market itself can create persistent, economically
meaningful mispricing that survives realistic transaction costs and execution constraints? Mechanism
first — the chain required for any candidate to survive is: information arrives → an identifiable
participant cannot/will not immediately incorporate it → a measurable distortion forms → it persists long
enough to trade → gross opportunity exceeds round-trip costs → it isn't just compensation for size/
liquidity/distress risk.

---

## 1. Mechanism map — NGX market structure, researched from first principles

| Structural feature | State as of 2026-08 | Source |
|---|---|---|
| **Price-movement rule** | Historically: a single uniform 100,000-share cumulative-volume threshold before the quoted price could move at all, regardless of stock price — described by market commentary as "a friction tax on price discovery." **SEC approved a tiered replacement on 2026-06-16, effective 2026-08-17**: ≥₦1,000/share → 10,000 shares; ₦500–999.99 → 50,000 shares; <₦500 → unchanged at 100,000 shares. | [Nairametrics 2026-05-30](https://nairametrics.com/2026/05/30/the-price-band-problem-why-ngxs-%C2%B110-cap-needs-a-proper-farewell/), [Nairametrics 2026-06-18](http://nairametrics.com/2026/06/18/ngx-introduces-new-thresholds-for-share-price-changes/), [Nairametrics 2026-06-20](http://nairametrics.com/2026/06/20/ngx-changes-how-stock-prices-move-how-it-affects-your-returns/) |
| **Daily price band** | ±10% cap, not a pause-and-reopen circuit breaker like NYSE/LSE — a stock simply stops trading for the day at the cap, unrelated to the volume-threshold rule above. | [Nairametrics 2026-05-30](https://nairametrics.com/2026/05/30/the-price-band-problem-why-ngxs-%C2%B110-cap-needs-a-proper-farewell/) |
| **Settlement cycle** | T+3 → **T+2 effective 2025-11-28** → **T+1 effective 2026-06-01**. Reduces counterparty/settlement risk and shortens capital lockup. | [CSCS](https://www.cscs.ng/ngt2/), [CSCS 2026 T+1 notice](https://www.cscs.ng/2026/05/nigerian-capital-market-set-for-transition-to-t1-settlement-cycle-on-1-june-2026/), [SEC Nigeria](https://sec.gov.ng/for-investors/keep-track-of-circulars/transition-to-t1-settlement-cycle-in-the-nigerian-capital-market/) |
| **Domestic vs. foreign participation** | Domestic investors ≈88–91% of equity turnover through H1 2026 (Jan–Jun: 87.93% domestic / 12.07% foreign cumulative; monthly range 86.9–91%); foreign participation itself volatile month to month (e.g. -26% MoM in May 2026). | [Nairametrics Jan-Jun 2026 roundups](http://nairametrics.com/2026/07/03/ngx-foreign-investors-participation-slumps-26-to-n183-61-billion-in-may-worst-decline-in-2026/) |
| **Free float requirements** | Currently tiered by board (verified directly from X-Compliance Schedule 7 in Stage 18/19: Growth Board 10-15%, Main Board 20%, Premium Board 20%). A **mandatory 20% minimum-across-the-board reform is under public discussion** as of 2026-07-19 — not yet enacted. | [Nairametrics 2026-07-19](http://nairametrics.com/2026/07/19/ngx-free-float-why-a-mandatory-20-rule-would-deepen-nigerias-stock-market/) |
| **Opening/closing auction mechanics** | No NGX-specific documentation of auction design (reference-price window, order-entry window, matching algorithm) was located in this research pass — search results returned only NSE India's 2026 Closing Auction Session as a comparator, not NGX's own mechanics. **Genuine research gap**, not filled with assumption. | (none found) |
| **Index reconstitution** | Real, rules-based, semi-annual (Jan 1 / Jul 1) review across 13 indices — already researched in depth in Stage 20 §8 (rated B: plausible, real, but `index_membership`/`constituent_weights` DB tables are synthetic placeholders, real history would need a news-search reconstruction). Not re-derived here; carried forward unchanged. | Stage 20 |
| **Tick size / price discreteness** | Already assessed in Stage 20 §7 (rated E: economically implausible net of NGX's own cost floor). Not re-derived here. | Stage 20 |
| **FX/capital-flow constraints** | Already assessed in Stage 20 §3 (rated C: real macro friction, not operationalizable at security level without granular FPI flow data NGX doesn't publish). Not re-derived here. | Stage 20 |
| **Corporate-action processing** | Already assessed in Stage 20 §5/§6 (rated C: thin `corporate_actions` table, ≤5 rights-issue observations). Not re-derived here. | Stage 20 |
| **Institutional ownership constraints (PenCom)** | Already assessed in Stage 20 §3 (rated B: real eligibility criteria, no historical constituent-history data located). Not re-derived here. | Stage 20 |

---

## 2. Candidate mechanisms — full scoring

### A. Volume-threshold price-stickiness reform (2026-08-17 regime change) — **strongest candidate**

| Dimension | Assessment |
|---|---|
| Economic mechanism | Pre-reform, the exchange's own matching/quoting system would not reflect a new price until 100,000 cumulative shares traded, *regardless of stock price*. For a ₦1,000+ name, that threshold represents ≥₦100m of trade value — far larger than what many individual orders represent. Genuine buy/sell pressure existed but was **mechanically prevented from appearing in the quoted price** by exchange rule, not by any participant's unwillingness or inability to trade. |
| Information source | Not an information event at all — a **rule change**, applied uniformly and mechanically to price formation itself. This is the cleanest possible "why arbitrage doesn't close it" story: it's not a behavioral or informational lag, it's a binding regulatory constraint on the price-formation process. |
| Delay mechanism | The delay was *by design* — the exchange itself withheld price updates below the volume threshold. Post-reform, that constraint is relaxed by 10x for ₦1,000+ names. |
| Persistence | Bounded and exogenous: the old regime persisted until 2026-08-17 by rule, not by market dynamics — a genuine regime break, not a fading effect. |
| Measurability | High, from data already on the platform: `equity_prices` (close, volume) supports exactly the zero-return-frequency diagnostic Stage 21 already built (`scripts/stage21_illiquidity_diagnostic.py`, reusable framework) — comparing pre- vs. post-2026-08-17 zero-return frequency for the ≥₦1,000 tier against the <₦500 tier (whose threshold didn't change) as a natural control group. |
| PIT integrity | Excellent — the effective date (2026-08-17) and exact rule (SEC-approved 2026-06-16) are public, dated, and exogenous. No return-dependent selection risk: the diagnostic design can be fully specified *before* any post-reform data exists. |
| Execution | Unclear yet, and this is the open question — the reform is designed to make prices *more* responsive, which could mean less exploitable staleness (working against a mispricing story) or could mean a one-time repricing/adjustment period across ₦1,000+ names as the new threshold takes hold (a genuine, once-off structural-break opportunity, if real). Cannot be assessed until post-reform data exists. |
| Cost headroom | Unknown pending the diagnostic — but the mechanism, if real, plausibly does not require repeated trading (a regime-transition effect, not a recurring signal), which changes the cost calculus from what killed the staleness track (Stage 21C failed specifically on a *recurring* small-edge-vs-cost basis). |
| H-011 independence | Mechanical: none — `size_scores()` uses only `market_cap_panel.csv`, untouched by trading-rule regime. Economic: this mechanism is explicitly price-level-tiered (₦1,000+ vs. sub-₦500), which correlates with but is conceptually distinct from market-cap — a large-float, low-priced stock and a small-float, high-priced stock would be treated identically by size but oppositely by this rule. Needs explicit orthogonalization against price level *and* mcap before any conclusion, exactly as prior stages did for size. |
| Data completeness | The *rule* is fully documented (dated, sourced). The *effect* cannot be measured yet — platform price data ends 2026-07-21, three weeks before the reform takes effect. |
| Survivorship risk | Low for this specific diagnostic — it's a market-wide structural comparison, not concentrated in a small set of names that could delist. |
| Concentration risk | To be determined — depends on how many names actually sit in the ₦1,000+ tier (a real, checkable question once addressed). |
| Falsifiability | Very clean: if zero-return frequency for the ₦1,000+ tier does **not** measurably drop after 2026-08-17 relative to the untreated <₦500 control tier, the mechanism is falsified outright. |
| Acquisition burden | **Currently a hard DATA GAP** — the platform's price feed must be extended past 2026-08-17 before this diagnostic can run at all. Not a design problem, a timing problem. |
| **Priority** | **85/100** — highest economic-mechanism clarity and PIT cleanliness of anything found in this program, penalized only for being not-yet-testable. |

### B. Settlement-cycle acceleration (T+2 → T+1)

| Dimension | Assessment |
|---|---|
| Economic mechanism | Faster settlement reduces counterparty exposure and capital lockup — this **reduces** frictions, working against a mispricing story on its own. No plausible "information cannot be incorporated" channel. |
| Information source | None — a pure market-plumbing change. |
| Delay mechanism | N/A — this shortens delay across the board, it doesn't create a differential one. |
| Persistence | N/A |
| Measurability | The rule and its effective date (2026-06-01) are well documented, but there's no proposed observable distortion to measure. |
| PIT integrity | N/A (no signal proposed) |
| Execution | N/A |
| Cost headroom | Plausibly *relevant as a cost input* to any other strategy (faster settlement could someday lower financing/margin costs embedded in `cost_schedule`'s brokerage assumption), but not itself a source of gross edge. |
| H-011 independence | N/A |
| Data completeness | Rule fully documented; no relevant NGX-side data gap since no signal is proposed. |
| Survivorship / Concentration risk | N/A |
| Falsifiability | Cannot be falsified because no distortion is claimed to exist. |
| Acquisition burden | N/A |
| **Priority** | **10/100 — immediate NO-GO as a standalone mechanism.** No economic channel for mispricing; relevant only as background context for cost modeling elsewhere. |

### C. Free-float mandatory-minimum reform (proposed, not yet enacted)

| Dimension | Assessment |
|---|---|
| Economic mechanism | If enacted, a forced free-float increase would require some issuers to sell down concentrated holdings, creating genuine forced, price-insensitive supply — a real, literature-precedented mechanism (similar logic to the index-inclusion/PenCom-eligibility mechanical-flow story already scoped in Stage 20). |
| Information source | A regulatory mandate, not firm-specific information. |
| Delay mechanism | Forced sellers are compliance-driven, not return-optimizing — same "not really an arbitrageur" logic as PenCom/index flows. |
| Persistence | Would depend on compliance-deadline structure, not yet specified since the rule doesn't exist yet. |
| Measurability | Not yet — this is a **proposal under public discussion**, not an approved rule. No effective date, no affected-issuer list exists. |
| PIT integrity | N/A until the rule is actually approved with a dated announcement. |
| Execution / Cost headroom | Cannot be assessed pre-rule. |
| H-011 independence | Plausibly independent (a compliance/float mechanism, not a size-rank mechanism) but unverified. |
| Data completeness | `securities` has no free-float field at all currently — a real, disclosed gap, consistent with Stage 20's finding that free-float data doesn't exist on this platform beyond what's manually extracted from X-Compliance PDFs. |
| Survivorship / Concentration risk | Unknown pending rule details. |
| Falsifiability | Cannot be specified pre-rule. |
| Acquisition burden | High even if the rule passes — would require building a free-float panel from scratch (no existing table). |
| **Priority** | **25/100 — not yet a real mechanism, only a live policy discussion.** Worth a calendar flag for future monitoring, not present-tense discovery work. |

### D. Domestic-participation dominance / information segmentation

| Dimension | Assessment |
|---|---|
| Economic mechanism | The claim would need to be: domestic and foreign participants process information at different speeds or with different information sets, and the ~88-91% domestic share creates a systematic bias in whose information gets incorporated first. This is plausible in the abstract (documented in some frontier-market microstructure literature) but requires a specific, falsifiable channel — "domestic dominance" alone is a *description of market composition*, not a mechanism. |
| Information source | Unclear — would need to identify what specific information domestic vs. foreign participants react to differently. |
| Delay mechanism | Not specified without a concrete channel (e.g., FX-conversion lag for foreign investors, information-source-language asymmetry, or index-fund foreign-flow rebalancing lag). |
| Persistence | Unknown without a channel. |
| Measurability | NGX does not appear to publish security-level domestic/foreign trade breakdowns (only aggregate market-level monthly figures were found) — the platform has no such field, and none was found publicly at the individual-stock level. |
| PIT integrity | N/A without security-level data. |
| Execution / Cost headroom | Cannot be assessed. |
| H-011 independence | Cannot be assessed without a concrete signal. |
| Data completeness | **Hard gap** — no security-level foreign/domestic flow data exists on the platform or, as far as this research found, publicly at all. |
| Survivorship / Concentration risk | N/A |
| Falsifiability | Not specifiable without a concrete channel — currently unfalsifiable, which is itself disqualifying. |
| Acquisition burden | Would require data NGX does not appear to publish at the granularity needed. |
| **Priority** | **15/100 — immediate NO-GO as currently specified.** A real, well-documented market-composition *fact*, correctly treated as a research input per the task's own framing, not evidence of a tradable mechanism. Would need a specific, falsifiable information-channel hypothesis and security-level flow data neither of which currently exist. |

### E–H. Carried forward from Stage 20 (not re-derived, not resurrected as new discoveries)

| Mechanism | Stage 20 rating | Status here |
|---|---|---|
| Index reconstitution (semi-annual, 13 indices) | B | Unchanged — real mechanism, real data gap (`index_membership` is synthetic) |
| PenCom eligibility flows | B | Unchanged — real criteria, no constituent-history data |
| Tick-size / price discreteness | E | Unchanged — economically implausible net of costs |
| FX/capital-flow constraints | C | Unchanged — macro-level only, no security-level data |
| Corporate-action processing | C | Unchanged — thin data (`corporate_actions`, ≤5 observations for the relevant types) |

---

## 3. Immediate NO-GOs, with reasons

- **Settlement-cycle acceleration (B)** — no economic channel for mispricing; it reduces friction rather than creating it.
- **Domestic-participation dominance (D)**, as currently specified — no concrete, falsifiable information-delay channel, and no security-level data exists to test one even if specified.
- **Tick-size/price discreteness** (carried forward) — already found economically implausible net of NGX's own cost floor.

## 4. Top 5 surviving mechanisms (ranked by mechanism plausibility × measurability × PIT integrity × execution feasibility × independence × falsifiability — **not** by expected return, none was calculated)

1. **Volume-threshold price-stickiness reform (A)** — cleanest mechanism, cleanest PIT story, currently blocked only by data timing, not design.
2. **Index reconstitution (carried forward, B)** — real, dated, rules-based; blocked by a genuine data-acquisition gap (synthetic `index_membership`), not a design flaw.
3. **PenCom eligibility flows (carried forward, B)** — real, dated criteria; blocked by the same class of missing constituent-history data.
4. **Free-float mandatory reform (C)** — real economic logic, but not yet an enacted rule; a monitoring item, not an active candidate.
5. **FX/capital-flow constraints (carried forward, C)** — real macro friction, unlikely to ever clear the security-level-data bar given what NGX publishes.

## 5. Single strongest candidate

**The 2026-08-17 volume-threshold price-movement reform.** It is the only candidate in this entire
program (including everything examined in Stages 16–27) with a **mechanical, rule-level, non-behavioral
explanation for why a distortion could exist and why it wasn't simply arbitraged away** — the exchange's
own system, not any participant's choice, prevented price updates below the old uniform threshold. That
is a fundamentally different and cleaner claim than every previously-tested mechanism (which all
ultimately reduced to "some participant was slow" — the family of stories that produced the fragile,
outlier-dependent, cost-failing results across Stages 18–27).

## 6. Exact diagnostic required to falsify it

**Frozen in advance, to be run only once post-reform data exists (no threshold-shopping after the fact):**

- **Treatment group**: all tickers whose most recent pre-reform closing price (as of 2026-08-14, the last
  trading session before the reform) is ≥₦1,000 — the tier whose threshold drops 10x (100,000→10,000
  shares).
- **Control group**: all tickers priced <₦500 as of the same date — the tier whose threshold is
  **unchanged** by the reform, serving as a natural placebo/control for any market-wide confound
  (e.g. a broad volatility regime shift coinciding with the reform date).
- **Metric**: zero-return-session frequency (Stage 21's own definition, reused verbatim: `close ==
  previous close`), computed over a fixed 40-trading-session window before 2026-08-17 and a fixed
  40-trading-session window after, for both groups.
- **Falsification rule, stated now**: if the treatment group's post-reform zero-return frequency does not
  drop by a materially larger amount than the control group's (a difference-in-differences test, plain
  and pre-specified — no covariate-shopping), the mechanical price-stickiness story is **rejected**. If it
  does drop as predicted, that establishes the *mechanism* is real — it does **not** by itself establish a
  tradable signal, which would require the full adversarial gauntlet this program has applied everywhere
  else (market-relative returns, cost gate, clustering, leave-one-ticker-out, extreme-observation checks)
  before any hypothesis could be considered.

## 7. Required data and platform status

| Requirement | Platform status |
|---|---|
| Daily close/volume through and past 2026-08-17 | **Not yet available** — `equity_prices` currently ends 2026-07-21. This is the single blocking gap. |
| Ticker price-tier classification as of 2026-08-14 | Computable immediately from existing `equity_prices` once that date's data exists — no new acquisition needed. |
| Confirmation of the rule's exact affected-securities scope (equities only? all boards?) | Not fully confirmed in this pass — the sourced articles describe the rule as applying to "equities trading" generally; board-level or index-tier exceptions, if any, were not found and should be checked directly against an NGX circular before the diagnostic is finalized. |
| Index-membership / PenCom-eligibility history (for candidates #2-3) | Still absent (Stage 20's finding stands) — would need a dedicated acquisition pilot, not attempted here. |

## 8. Recommended next stage

**Wait, don't build.** This is a genuine case where the correct next action is scheduled monitoring, not
further research effort now: once the platform's price feed is extended past 2026-08-17 (plus a ~40
session post-reform window, so roughly mid-to-late October 2026), run exactly the pre-specified
difference-in-differences diagnostic in §6 — unmodified from what's written here — as the next discovery
stage. Do not begin any preregistration or backtest work before that diagnostic exists and is evaluated
against its own pre-stated falsification rule. In the meantime, if any bounded research capacity is
available, confirming the reform's exact scope (which boards/security types) directly against NGX's own
circular (not yet done here) would sharpen the diagnostic's treatment/control group definitions before
data arrives — a research task, not a data-acquisition one, and safe to do without any hindsight risk
since it doesn't touch returns.
