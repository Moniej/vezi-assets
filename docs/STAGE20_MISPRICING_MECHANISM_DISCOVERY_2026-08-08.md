# Stage 20 — NGX Mispricing Mechanism Discovery Program

**Date:** 2026-08-08
**Status:** Research only. No hypothesis registered, no factor built, no backtest run, no strategy return
calculated, no threshold optimized. All mechanism selection below is on economic/structural/data-quality
grounds, verified directly against live DB schema and content — never on the basis of historical
return, which was never computed for any candidate here.

**Question:** what structural mechanism causes persistent, tradable mispricing in NGX equities, and can
we measure it without hindsight? Mechanism first, factor second.

---

## 0. Method

Every mechanism below was checked against: (a) the actual live `data/ngx.sqlite` schema and row counts
(read-only queries, reported verbatim), (b) real, dated, sourced NGX/PenCom/press material where DB
content was insufficient, and (c) the explicit checklist the user specified (economic rationale, why
arbitrage doesn't close it, exact measurable variable, historical availability, PIT-safety, survivorship,
independence from H-011/H-019/H-006, frequency, concentration, executability, falsifiability, existing
DB evidence, external data required). No mechanism was chosen or discarded by looking at its historical
return — that number was never computed for anything in this document.

**Ground truth on what already exists in the DB** (all counts verified live, 2026-08-08):

| Table | Rows | Relevance |
|---|---|---|
| `equity_prices` | 353,043 (320 tickers) | full daily OHLCV+volume, real, dense — already survives delisted names (Stage 19 §5) |
| `documents` | 11,533 filing-type rows (`ngx_xissuer_documents`, confidence 0.85) | first-party NGX X-Issuer disclosure repository, real, PIT-dated `filing_date` |
| — `doc_type='results_notice'` | 357 (64 tickers, 2015–2026) | earnings announcements |
| — `doc_type='closed_period'` | 590 (86 tickers, 2016–2026) | insider trading blackout notices |
| — `doc_type='dealing'` | 163 (29 tickers, 2020–2026) | **insider/substantial-shareholder share-dealing notices** |
| — `doc_type='rights_capital'` | 52 (28 tickers) | rights-issue related filings |
| — `doc_type='bonus_split'` | 17 | bonus/split filings |
| — `doc_type='other'` | 7,727 | uncategorized — large unmined pool |
| `corporate_actions` | 31 rows | `dividend_cash`(30) + `rights_issue`(1) only — thin, inconsistent with `extracted_facts` |
| `extracted_facts` | 461 rows | financial-statement line items; `restates_fact_id` column exists but **0 rows populated** |
| `index_membership` | 12 rows | **synthetic placeholder data** — fake tickers (`SYNBNKA` etc.), `confidence=0.0`, sourced from `synthetic_dev`. Not real. |
| `constituent_weights` | 0 rows | empty |
| `entity_relationships` | 22 rows | types are `affects_order_1/2`, `renamed_from` only — **no ownership/shareholding relationships captured** |
| `securities.board` | 320/320 NULL | no Premium/Main/Growth board tier data |

Two findings shape everything below: (1) the `ngx_xissuer_documents` filing corpus is a real, large,
first-party, PIT-dated, currently under-exploited asset — several mechanism families can be tested from
data already acquired, no new scraping required; (2) `index_membership`/`constituent_weights` are
**fabricated placeholders**, not real data — any index-mechanics mechanism starts from zero, not from
existing DB content, despite the table existing.

---

## 1. Information diffusion / reporting delay

- **Earnings-announcement drift** (results-notice filing → subsequent price drift): this is exactly
  H-006's PEAD construct (surprise proxy, drift window, `results_notice`-equivalent event set) — already
  tested and rejected. **Classification: D — redundant with H-006.**
- **"Stale information" / "delayed investor response" as a generic story**, not tied to a specific
  non-earnings disclosure type, collapses into the same construct once operationalized — there is no
  distinct measurable variable that isn't either H-006 or one of the more specific items below.
  **D — redundant / not independently specifiable.**
- **Audited vs. unaudited filing re-rating** (a second, distinct re-pricing when audited accounts
  supersede an earlier unaudited release, as opposed to the earnings-surprise-vs-consensus mechanism
  H-006 tested): economically distinct — the information content is "these numbers changed on
  confirmation," not "these numbers beat/missed an ex-ante forecast." `results_notice` doc_type doesn't
  currently distinguish audited/unaudited status as a structured field; would require a deterministic
  (non-LLM-sentiment) text flag extracted from the existing 357 filings. Independent of H-006 (different
  trigger), H-011, H-019. **Classification: B — plausible, needs a missing structured flag, not new
  scraping.**
- **Sanctions-for-closed-period-trading disclosures** (Schedule 5 of X-Compliance) as an info-diffusion
  channel: the sanction itself lags the underlying trade by months and concerns rule compliance, not
  fundamentals — no plausible fresh information content at sanction date. **E — economically
  implausible.**

## 2. Liquidity segmentation

- **Illiquidity/staleness as a source of *predictable relative* mispricing** (not merely a risk premium):
  economic rationale is standard limits-to-arbitrage — thin names have infrequent trade-clearing prices,
  and professional capital won't commit to correcting small, illiquid mispricings because the cost of
  doing so (price impact, capacity) exceeds the edge. Crucially, this is a **different claim** from "risk
  premium for holding illiquid stock" (which would be compensation, not exploitable mispricing) — the
  next-stage question is specifically whether returns are predictable *conditional on* liquidity tier in
  a way that survives realistic trading costs, not whether illiquid stocks simply earn more on average.
  Measurable directly from `equity_prices` today: zero-return-day frequency, turnover ratio, volume
  shocks, price-impact proxies (Amihud-style |return|/volume) — all computable with zero new acquisition,
  and PIT-safe by construction (trailing rolling window). Survives delisted names (Stage 19 §5 already
  confirmed price history persists to last trade date). Independent of H-011 (H-011 is a pure market-cap
  rank; a name can be large-cap and still exhibit high staleness, or small-cap and liquid — this needs a
  test orthogonalized to mcap, not assumed). Independent of H-019/H-006 (no news or earnings dependency
  at all). Frequency: daily, for all 320 tickers — the densest candidate in this entire program.
  **Classification: A — strong structural candidate.** This is the single mechanism requiring **no**
  new data acquisition to begin a feasibility map.
- **Bid/ask proxies**: no quote data exists on this platform (confirmed — only OHLCV); any bid/ask proxy
  would itself have to be derived from the same price/volume series as above, so it is not a separate
  data source, just a refinement of the same candidate. Folded into the item above, not counted twice.

## 3. Institutional constraints

- **PenCom pension-fund eligibility (NGX Pension Broad Index) threshold effects**: real, external,
  well-documented mechanism. Confirmed via web search: PenCom-eligible universe requires (a) taxable
  profit in ≥3 of the last 5 years, (b) a dividend or bonus issue in ≥1 of the last 5 years, (c) free
  float ≥5%, reviewed **semi-annually** ([PensionNigeria](https://www.pensionnigeria.com/pension-news/pencom-nigeria-stock-exchange-ngx-launch-pension-broad-index/), [Vanguard](https://www.vanguardngr.com/2026/01/ngx-pension-broad-index-surpasses-all-share-index-with-59-72-return-in-2025/)).
  Economic rationale: pension fund administrators (PFAs) are legally constrained, not
  return-optimizing at the margin — a stock crossing into/out of eligibility faces mechanical,
  price-insensitive institutional flow that ordinary arbitrageurs cannot easily front-run without
  knowing the eligibility test result in advance, and cannot necessarily absorb quickly given PFA size.
  This is structurally different from H-011 (pure mcap rank, no eligibility threshold or institutional
  flow story), H-019 (not news-driven), H-006 (not earnings-driven). The `indices` table already carries
  a placeholder `NGXPENSION` row ("40 stocks meeting PenCom criteria (verify)" — the note itself flags
  this as unverified) but **no membership history exists anywhere in the DB.** A dated add/drop history
  would need first-party acquisition (PenCom or NGX publication) or a news-search reconstruction similar
  to what worked for Stage 19's suspension-lift inventory. **Classification: B — plausible, strong
  rationale, but the eligibility-history data does not yet exist in usable form and its acquisition
  difficulty is unverified.**
- **Foreign portfolio investor (FPI) participation / FX-repatriation frictions**: real, well-documented
  macro phenomenon (NGX foreign investor access was disrupted for years by FX scarcity/multiple exchange
  rates). This is a market-wide regime variable, not a per-security cross-sectional signal — no
  security-level foreign-vs-domestic order-flow data is published or present in this DB (`fx_rates` and
  `macro_series` are macro-level only). **Classification: C — plausible macro friction, not currently
  operationalizable as a stock-selection mechanism without data NGX does not appear to publish at
  security granularity.**
- **Board-tier minimum-size rules (Premium/Main/Growth)**: `securities.board` is 100% NULL across all
  320 tickers — this data doesn't exist on the platform at all, and board-tier rules (free-float minimums
  differ by board, confirmed in the X-Compliance Schedule 7 text already extracted in Stage 18/19) would
  need to be joined against an as-yet-absent board classification. **Classification: C — real rule
  differences exist, but the join key (board tier per ticker, historically) is entirely missing.**

## 4. Ownership and control structure

- **Insider / substantial-shareholder "dealing" notices**: 163 real, first-party filings (`doc_type=
  'dealing'`, `ngx_xissuer_documents`, confidence 0.85), 29 tickers, 2020–2026, e.g.
  `UNIONDAC` 2020-02-27, `NB` 2020-06-29 (verified directly from `documents.source_url`). Economic
  rationale: insider purchases/sales reflect private information not available to the general market;
  arbitrage doesn't immediately correct the resulting price-relevant signal partly *because* these are
  low-attention, mandatory-disclosure PDF filings, not press-covered news — the same information-friction
  logic the user's own framing anticipates (item 1's "delayed investor response," applied to a genuinely
  distinct trigger). PIT-safe: `filing_date` is the actual disclosure timestamp. Independent of H-011
  (ownership-transaction based, not size), H-019 (not in the existing `events` taxonomy — no
  `event_type` in the DB corresponds to insider dealing), H-006 (not earnings-related). These filings
  exist as raw PDFs; **the buy/sell direction, share quantity, and price have not yet been extracted into
  structured fields** — this is real extraction work (deterministic field parsing of a "Notification of
  Share Dealing" form, not LLM sentiment/direction judgment) rather than new scraping, since the source
  documents are already acquired. **Classification: A — strong structural candidate**, subject to
  confirming the extraction is tractable (the two sample filings above have a fairly standard NGX/SEC
  disclosure-form structure, which is a good sign but not yet verified across all 163).
- **Free-float changes / concentrated ownership generally** (beyond discrete insider transactions):
  would require mining `governance`(915)/`agm`(794) doc_types for ownership-percentage disclosures — no
  structured field exists yet, uncertain extraction yield, not yet attempted.
  **Classification: B — plausible, unverified extraction yield.**

## 5. Corporate-action mechanics (only where mechanism differs demonstrably from H-011/H-019)

- **Rights-issue mechanical mispricing** (rights-price discount vs. ex-rights market price, or
  post-issue price-adjustment lag): genuinely distinct mechanism from H-019's CIR family (mechanical
  share-count dilution + investor confusion about the ex-rights adjusted reference price, not a
  discretionary "restructuring" news classification). But volume is very thin: `corporate_actions` has
  exactly 1 `rights_issue` row; `extracted_facts` has 4. **Classification: C — mechanism is plausible but
  current observation count (≤5) is far too small to support "sufficient historical observations"; a
  data/design problem, not disproof.**
- **Bonus-issue "free lunch" mispricing** (literature-documented retail behavioral mispricing around
  bonus issues in markets with high retail participation — treating bonus shares as free wealth,
  producing temporary overpricing that reverses): mechanistically distinct from H-019 (not about the
  restructuring/ownership-change label; purely share-count-mechanics + cognitive bias). Data: `bonus_split`
  doc_type has 17 filings, `extracted_facts.bonus_issue` has 6 — again thin.
  **Classification: C — same data-volume problem as rights issues.**
- **Tender offers / mergers**: already covered by H-019's CIR family (`merger`, `ownership_change` event
  types were explicitly in scope and tested). **Classification: D — redundant.**

## 6. Accounting / reporting frictions

- **Restatements**: `extracted_facts.restates_fact_id` exists in the schema specifically for this but has
  **zero populated rows**. However, this is *derivable* without new acquisition: the same
  ticker/period_end/fact_type combination filed at two different dates with two different
  `numeric_value`s (already present in `extracted_facts`, 461 rows) would itself constitute a detectable
  restatement, purely from data already in hand — no new scraping needed, just a comparison query that
  hasn't been run yet. **Classification: B — plausible, and closer to feasible than the empty column
  suggests; the derivation query itself is the next concrete step, not a new acquisition pilot.**
- **Audit qualification / going-concern language**: real, literature-grounded mechanism (qualified/going-
  concern opinions are associated with elevated distress risk and documented underreaction in several
  markets). The `documents` table's underlying filings likely include audited-account PDFs with such
  language, but no structured flag exists. Any extraction must be a **deterministic keyword/rule-based
  flag** (e.g., presence of "going concern," "qualified opinion" in the filing text), explicitly **not**
  an LLM sentiment/direction judgment, to stay inside the platform's standing no-LLM-signal rule.
  **Classification: B — plausible, needs rule-based text extraction on already-acquired filings.**
- **Reporting-period mismatches / unusual accounting changes**: too underspecified to treat as a separate
  mechanism from the above two; folds into the restatement/audit-quality bucket rather than adding a
  third item.

## 7. Market microstructure

- **Zero-return frequency / staleness / turnover shocks**: this is the same variable as the liquidity-
  segmentation item in §2 — not counted twice. **A**, already covered.
- **Trading halts / non-trading days (formal suspension)**: this is Stage 19's already-closed suspension-
  lift/impose track. **D — already tested and killed.** Generic *informal* sparse-trading (a listed,
  non-suspended stock that simply doesn't trade some days) is a milder version of the same illiquidity
  construct in §2, not a separate mechanism.
- **Price discreteness / tick-size effects**: real microstructure phenomenon but the resulting predictable
  component is typically smaller than NGX's own bid/ask spread and documented transaction-cost hurdle
  (this platform's cost schedule has been a binding constraint throughout the project). **Classification:
  E — economically implausible as a net-of-cost exploitable signal**, without even needing a backtest to
  see this — the effect size class is below the platform's own known cost floor.
- **Opening/closing auction behavior, order-flow proxies**: no intraday/order-level data exists on this
  platform (daily OHLCV only), and there's no evidence NGX publishes historical auction-level data for
  free. **Classification: C — data/design problem, not disproof.**

## 8. Index / benchmark mechanics

- **NGX-30 / sectoral index semi-annual reconstitution effects**: confirmed via direct search that NGX
  formally reviews its cap-weighted indices **twice yearly, on the first business day of January and
  July**, across 13 indices, with mechanical inclusion/exclusion driven by market cap and liquidity
  rules, and that changes are reliably covered by name in the financial press at each review (e.g. the
  2026-07-01 review dropping Oando/Transcorp and adding NASCON/Unilever from NGX-30 —
  [Nairametrics](https://nairametrics.com/2026/07/01/ngx-drops-oando-transcorp-from-ngx-30-index-in-half-year-2026-rebalancing-heres-why/);
  a prior H1-2025 review dropping Conoil/Julius Berger and adding Aradel/Wema —
  [Dabafinance](https://dabafinance.com/en/news/ngx-30-index-rebalancing-h1-2025)). Economic rationale:
  classic, internationally well-documented index-inclusion/exclusion mechanical-flow effect — passive
  and institutional mandates rebalance around a known, price-insensitive, calendar-fixed date, distinct
  in kind from H-011 (continuous mcap rank, no discrete threshold/calendar event) and from H-019/H-006
  (not news- or earnings-triggered). The in-DB `index_membership`/`constituent_weights` tables are
  **not usable** (synthetic placeholders, confirmed §0) — but unlike a dead end, the semi-annual review
  dates are fixed and known in advance, and press coverage of each review's actual name-level changes
  is real and searchable the same way the Stage 19 suspension-lift inventory was built, without needing
  a bulk first-party archive. **Classification: B — plausible, strong rationale, requires a bounded
  acquisition pilot (reconstructing ~10 years of semi-annual review outcomes via press coverage) before
  any feasibility map can be finalized, but the acquisition path is now identified and looks more
  tractable than the PenCom-index case above.**
- **NGX Pension Broad Index rebalance**: covered under §3 (institutional constraints) — same table, same
  classification (B), not double-counted here.

## Search-broadly mandate: mechanisms outside the 8 named families

Explicitly considered and rejected/deferred:

- **Settlement mechanics (T+2/T+3 CSCS clearing delays)**: no evidence found of a security-level,
  measurable settlement-friction variable distinct from ordinary illiquidity; folds into §2.
  **D/overlap.**
- **Circuit breakers / daily price limits**: NGX's price-movement limit mechanics were already directly
  observed in Stage 19B's ASOSAVINGS diagnostic (daily ~9–10% ratchet moves after reopening) — this is
  the same discreteness/limit-ratchet phenomenon flagged there as *undermining*, not supporting, a
  persistence story. Not a new independent mechanism; already weighed against the suspension-lift
  candidate and found unhelpful. **D — already addressed, not separately promising.**
- **Mandatory take-over / control-transaction thresholds (SEC Nigeria Rule on substantial acquisition of
  shares)**: conceptually a sharper version of the ownership-structure mechanism in §4 (a discrete
  regulatory threshold, not just any insider transaction) — no historical threshold-crossing data
  identified in the DB or via search in the time available. **Classification: C — plausible refinement
  of §4's A-rated mechanism, not yet independently evidenced; worth folding into the insider-dealing
  extraction work rather than pursuing separately.**

No mechanism outside the 8 named families was found with a stronger claim than what's already captured
above; the search did not surface a hidden ninth mechanism.

---

## Data feasibility maps — A/B candidates only

### A1. Illiquidity/staleness → predictable relative mispricing (§2)

| Item | Status |
|---|---|
| Core variable | Zero-return-day frequency, turnover ratio, Amihud-style price-impact ratio — all computable from `equity_prices` |
| Historical availability | 353,043 rows, 320 tickers, 2014–2026 (varies by ticker) — no acquisition needed |
| PIT-safety | Trivial — trailing rolling window over already-dated daily bars |
| Survivorship | Confirmed clean (Stage 19 §5) |
| Independence from H-011/H-019/H-006 | Needs an explicit orthogonalization test against mcap (H-011) before use — not yet done, flagged as the first required step, not assumed |
| Frequency/concentration | Daily, all 320 tickers — no coverage problem |
| Executability | The mechanism's own tradability is the open question (illiquid-by-definition names may not support meaningful size) — this is not a side issue, it *is* the research question per the user's own framing in item 2 |
| Falsifiability | If illiquidity-tier-conditional returns show no predictability once properly risk-adjusted and cost-adjusted, or the effect disappears once orthogonalized to size, the mechanism is falsified |
| External data required | None |

### A2. Insider "dealing" notice disclosures (§4)

| Item | Status |
|---|---|
| Core variable | Buy/sell direction, quantity, price from 163 first-party `dealing` filings |
| Historical availability | 29 tickers, 2020–2026 — real but modest |
| PIT-safety | `filing_date` is the actual disclosure timestamp — clean |
| Survivorship | Not yet checked against delisted tickers specifically — open item |
| Independence from H-011/H-019/H-006 | Structurally independent — no overlapping construct in any of the three |
| Frequency/concentration | 163 filings / 6 years / 29 tickers — modest; concentration by ticker not yet profiled |
| Executability | Not yet assessable — depends on extracted transaction size vs. ticker liquidity, unknown until extraction is done |
| Falsifiability | If extracted buy/sell direction shows no measurable association with subsequent liquidity-adjusted returns, or the filings turn out to be dominated by routine/small transactions, the mechanism is falsified |
| External data required | None — filings already acquired; needs deterministic field extraction (not LLM sentiment) from existing PDFs/text |

### B1. Audited-vs-unaudited re-rating, B2. Restatement detection, B3. Audit-qualification/going-concern flag (§1, §6)

All three share the same feasibility profile: data (11,533 filings, much of it likely already
text-extracted per the `documents.text_path` field used in earlier stages) is already acquired; the
missing piece in each case is a **deterministic structured flag**, not new scraping. B2 (restatement) is
the cheapest — derivable purely from existing `extracted_facts` rows without touching PDF text at all.
B1 and B3 require rule-based text parsing of already-downloaded filings.

### B4. PenCom Pension Broad Index eligibility history, B5. NGX-30/sectoral index semi-annual reconstitution (§3, §8)

Both require a genuinely new, bounded acquisition pilot before a feasibility map can be finalized — the
in-DB `index_membership` table is unusable synthetic data. B5 is more tractable: review dates are fixed
(Jan 1 / Jul 1) and outcomes are reliably press-covered (verified for the 2025-H1 and 2026-H1 reviews),
so a ~10-year reconstruction via the same news-search method that built Stage 19's suspension-lift
inventory is plausible. B4 (PenCom criteria) has clear eligibility *rules* but no located historical
add/drop archive yet — acquisition difficulty is genuinely unverified, not just unattempted.

---

## Answers to the seven questions

1. **What structural frictions actually exist in NGX?** Real, evidenced ones: thin/illiquid-name
   staleness (directly measurable), a large under-exploited first-party disclosure archive (insider
   dealing notices, results notices, governance/AGM filings), a semi-annual rules-based index
   reconstitution process with real mechanical-flow potential, and (weaker, macro-level) FX/FPI
   repatriation friction. Several textbook EM frictions (restatement, audit qualification, PenCom
   eligibility) are economically real but currently unmeasured on this platform, not because they don't
   exist but because the structured extraction hasn't been done.
2. **Which frictions can plausibly create persistent mispricing?** Illiquidity/staleness (§2, A) and
   insider-dealing disclosure lag (§4, A) have the clearest, most direct "why arbitrage doesn't close it"
   stories. Index reconstitution (§8) and PenCom eligibility (§3) have the clearest "why it's mechanical/
   forced, not information-driven" stories, which is a different but equally valid persistence argument.
3. **Which can we objectively measure — today?** Only illiquidity/staleness (§2), from data already
   fully in hand. Everything else needs either extraction work on already-acquired filings (B-tier) or a
   new acquisition pilot (B4/B5).
4. **Which are independent of H-011/H-019/H-006?** All of the A/B candidates are — that independence was
   a gating requirement applied before anything was classified above, not an afterthought.
5. **Which have enough historical observations?** Illiquidity/staleness clearly does (daily, all 320
   tickers). Insider dealing is modest but real (163 filings). Restatement/audit-quality volume is
   unknown until the extraction is run. Rights-issue and bonus-issue mechanics do **not** (≤17
   observations each) — correctly classified C, not pursued further.
6. **Which are realistically executable?** Genuinely unresolved for every A/B candidate — this is
   deliberately an open research question for the next stage, not answered here, per the instruction not
   to calculate strategy returns.
7. **Which mechanism deserves the next research stage?** **Illiquidity/staleness (§2/A1)**, on the
   strength of needing zero new data acquisition, having no coverage or survivorship problem, and having
   the cleanest available test for independence from H-011. **Insider dealing (§4/A2)** is the second
   priority — comparable structural strength, but gated on a real extraction effort (parsing 163 PDF
   notices into buy/sell/quantity/price) before anything else can be assessed.

**No hypothesis is proposed here and none is warranted yet.** The recommended next step for A1 is a pure
measurement/diagnostic stage — computing the illiquidity variable, orthogonalizing it against H-011's
mcap rank, and checking whether *conditional* return predictability survives basic cost/capacity
constraints — exactly the same diagnostic-before-preregistration discipline used in Stage 19B, and
explicitly not a backtest or portfolio construction.
