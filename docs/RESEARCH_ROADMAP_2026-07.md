# Factor Research Roadmap — 2026-07-21

Author role: Head of Quantitative Research. Governance: every candidate
factor runs the UNCHANGED gauntlet (pre-registration → PIT → walk-forward →
placebo → Holm/BH → costs → capacity → untouched OOS). The Validated Factor
Library is empty and stays empty until evidence says otherwise. Data vintage
pinned: 2026-07-21 (`docs/DATA_FREEZE_2026-07-21.md`).

## 1. Current state (verified, not aspirational)

COMPLETE / production: PIT store (3 validated price sources, 320,159 rows /
2,933 days / 12 gate-ready years); IRU v2 (~100 names/yr, PIT,
rename-canonical); Coverage Gate PASS; earnings calendar (10,690 filings,
PIT `created`); ex-div closure calendar (1,044 events); gainers transitions
(official adjusted bases, 138k rows); official prev-close table; events DB
(MPC 80, regulatory 13); Brent; cost schedule (retail, 'assumed');
experiment registry + ledger + phase4 gauntlet + reproducibility (all
battle-tested across 4 honest rejections); diagnostics D1–D4.

IN FLIGHT: corp-actions PDF archive (~8.8k/11,546, background, resumable).

NOT AVAILABLE (blocks specific families): fundamentals VALUES (revenue,
margins, book value — needs statement parsing/OCR); shares outstanding
(harvest not built); dividend AMOUNTS (dates exist; amounts sit unparsed in
DOL dividend columns); analyst data (does not exist for NGX); intraday
data (never).

STRUCTURAL CONSTRAINTS every design must respect:
- No shorting on NGX → every factor is a LONG-ONLY tilt vs an investable
  benchmark. Benchmark must be defined ex-ante (see §4).
- Retail costs ~4% per full round trip → sub-quarterly holding is dead on
  arrival (H-005's lesson); low-turnover designs strongly favored.
- Breadth ~100 investable names; dev window 2015-2024, untouched OOS
  2025-26. Pivot-memo power math: per-stock quarterly detection of IC≈0.05
  needs ~10 years — we have exactly that. Power is adequate, not lavish:
  maximize breadth per test, no sub-slicing.

## 2. Factor family readiness

### Ready now — zero new engineering

**H-007 — Cross-sectional momentum (12-1)** — PRIORITY 1
- Rationale: slow information diffusion + investor underreaction; the most
  replicated cross-sectional effect in EM/frontier markets; NGX retail
  dominance and absence of shorting mean overpricing corrects slowly but
  underpricing persists — long-only momentum harvests the latter.
- Data: price panel + IRU (both frozen). Holding: quarterly rebalance,
  monthly-overlapping portfolios (power without turnover). Turnover: ~60-100%
  /yr one-way → ~2.5-4%/yr cost drag at retail rates — the binding hurdle.
- Capacity: top-quintile ADTV concentration; report distribution per
  standard protocol. Frontier momentum lives in mid-liquidity names — watch
  the capacity-signal tradeoff explicitly.
- Risks/failure modes: crash risk at regime turns (2023 float, 2020);
  band-limited price discovery may smear formation returns (12-1 skip
  month helps); stale prices inflate measured momentum (staleness filter
  ex-ante: exclude names stale >N sessions in formation window — rule set
  in prereg, not after).
- Power: ~40 quarters × ~100 names. Adequate.

**H-006 — Post-earnings-announcement drift (PEAD)** — PRIORITY 2
- Rationale: underreaction to earnings news; no analyst coverage and
  slow retail information processing on NGX should PROLONG drift; filing
  timestamps are true PIT (SharePoint `created`).
- Surprise proxy (no fundamentals values): market-reaction PEAD — the
  abnormal return over the filing window (t0..t0+2) classifies the news;
  drift measured t0+3 → t0+60. Standard where estimates don't exist.
- Data: earnings calendar × price panel (both frozen). ~10,690 filings →
  ~5-6k usable IRU events in dev window. Holding: ~3 months. Turnover:
  event-driven, capped by design.
- Risks/failure modes: 4% round trip vs. realistic drift magnitude — the
  honest failure mode is "signal real, net dead" (that outcome still feeds
  the library design: PEAD as tilt inside another portfolio shares costs);
  thin trading contaminates the reaction window (min-liquidity filter
  ex-ante); filing-type heterogeneity (audited vs interim — pooled first,
  no sub-slicing without pre-registered hierarchy).
- Power: thousands of events — best-powered event test available to us.

**F13a — Low volatility** — wave 2 (prereg after H-006/H-007 verdicts)
- Rationale: leverage-constraint/lottery-preference anomaly; strongest in
  markets where shorting is impossible (ours literally is). Long-only
  friendly, LOW turnover → cost hurdle is minimal (~1%/yr) — structurally
  the best-suited factor for NGX costs.
- Data: price panel only. Holding: quarters-years. Failure modes: vol
  estimates corrupted by stale prices (require trading-frequency floor);
  low-vol ≈ large-liquid on NGX → may collapse into beta/size confound
  (pre-register the orthogonality check).

**F13b — Short-term reversal**: monthly horizon → killed by costs with
near-certainty. Deprioritized; test only if a cost-shared implementation
(overlay on rebalance trades) is designed. Knowledge value low relative to
slot cost.

**F4 — Liquidity premium**: measurable now (ADTV/Amihud from value_traded).
Paradox: validating it certifies a premium we cannot harvest at scale
(capacity IS the factor). Research value = risk-model input more than
standalone alpha. Wave 3, as infrastructure for the Risk Engine.

### One parser extension away (moderate engineering, no OCR)

**F6/FV — Dividend yield + Value (E/P)** — the DOL dividend region prints
Interim/Final dividend AMOUNTS + EPS + P/E per stock per day; only the
DATE bands were parsed for the gate. One char-level extension of the
validated exdiv parser yields a daily PIT dividend/EPS panel 2014→2026 →
unlocks dividend-yield and E/P value factors, plus total-return
construction for every other factor's benchmark. HIGHEST-VALUE ENGINEERING
ITEM. (Validation: GTCO/Zenith anchors + cross-era spot checks, same
protocol as the gate parsers.)

**Market-cap layer from LIST2** — PRICES_LIST2 prints market cap per stock
per day across ~2,800 archived days; the LIST2 parser already regexes the
column and discards it. Unlocks: SIZE factor, cap-weighted investable
benchmark, capacity refinement (float proxy). Small engineering step.

### Blocked (do not schedule yet)

Quality / Growth / earnings-revision / accruals: need statement VALUES →
OCR + financial-statement parsing (user-gated tesseract decision; scanned
majors). Event-driven corp-actions detail: needs the same OCR. Revisit
after wave 2.

## 2a. Post-2026-07-21 hypothesis/mechanism history — Stages 16–21C (CLOSED)

This roadmap's §1–§2 predate H-011's confirmation and everything below; kept as-written for the
historical record rather than rewritten. Per §4 rule 4 ("every rejection updates this roadmap's family
table before the next prereg is drafted"), this section records the full arc since: H-011 (size/rotation)
reached CONFIRMED status but with a losing live-forward read; H-019 (news-event factor, GMC/CIR families)
completed n=2 executable backtest, net negative; both left "what's actually driving NGX mispricing, if
anything" open. Stages 16–21C were a dedicated, sequential mechanism-discovery program to answer that
question directly (mechanism-first, factor-second), run 2026-08-08 to 2026-08-09. **All of it is now
closed** — no hypothesis was registered, no factor was built, no backtest was run at any point in this
program; every stage was diagnostic-only per its own gate.

| Stage | Track | Verdict | Reason |
|---|---|---|---|
| 16–17 | Broad alpha-discovery sweep (regulatory, structural, ownership, microstructure candidates) | Scoping only | Produced the candidate list Stages 18–21C then tested |
| 18 | Delisting-Watchlist distress mispricing | Disproven (as evidenced) | DEAPCAP — the lead case — ran ~400% on an earlier, unrelated MoU and was already 34% off-peak by the H-019 event date; not a fresh reaction |
| 19 | Regulatory state-transitions (suspension-imposed, suspension-lifted, final-delisting) | Suspension-imposed & final-delisting: **NO-GO**. Suspension-lift: CONDITIONAL GO pending 19B | Suspension-imposed has no long-side entry mechanism; final-delisting (e.g. DN Tyre, 12-year process) is fully telegraphed years in advance, no post-transition price series exists |
| 19B | Suspension-lift persistence/liquidity | **NO-GO — killed** | Post-lift returns don't survive excluding the first 2 sessions (one event outright reverses sign by T+22); 2 of 4 events show *below*-baseline post-lift liquidity; the largest apparent mover (ASOSAVINGS) was forcibly re-suspended before a full window could be observed |
| 20 | Structural mispricing mechanism scan (8 families: info diffusion, liquidity segmentation, institutional constraints, ownership/control, corporate-action mechanics, accounting frictions, microstructure, index mechanics) | Scoping/classification only | Classified every candidate A–E; `index_membership`/`constituent_weights` found to be **synthetic placeholder data**, not real — a standing data gap for any future index-mechanics work. Illiquidity/staleness and insider-dealing disclosures rated the two strongest (A) candidates |
| 21 | Illiquidity/staleness — calendar-time forward-return diagnostic | CONDITIONAL GO → superseded by 21B | Mechanism (persistent per-ticker staleness, r≈0.76 stable; 3× larger \|return\| after inactivity) real; but the calendar-time forward-return sort was confounded — stale names mechanically stay stale in the forward window too, compressing measured returns toward zero |
| 21B | Illiquidity/staleness — trade-conditional redesign | CONDITIONAL GO → superseded by 21C | Confound resolved (returns measured only on genuinely traded sessions); effect survives but splits into an unexecutable T0 reopening jump (ambiguous between information and mechanical liquidity-impact) plus a small, weak post-T0 drift |
| 21C | Illiquidity/staleness — drift-only, market-relative, cost-gated | **NO-GO — killed** | T0 jump discarded per hard decision. Market-relative excess drift fails to clear a single round-trip transaction cost (3.79%, from the live `cost_schedule`) at *every* horizon tested (3/5/10/20 traded sessions); median excess drift ≈0; fewer than half of episodes even move in the "expected" direction — mean was carried by a skewed few, not a typical, repeatable effect |

**Net result of Stages 16–21C: no surviving mechanism.** Every structural candidate examined — regulatory
distress, suspension lifecycle, and illiquidity/price-staleness — was killed on the evidence, not
assumed away. The one substantive open thread this program surfaced but did not pursue at the time:
insider/substantial-shareholder "dealing" notice disclosures (Stage 20 §4, rated A — 163 real first-party
NGX filings, 29 tickers, 2020–2026, structurally independent of H-011/H-019/H-006). Stages 22–23 (below)
picked this thread up.

## 2b. Insider-dealing-notice track — Stages 22–23 (PILOT COMPLETE, CONDITIONAL GO)

| Stage | Scope | Verdict | Key finding |
|---|---|---|---|
| 22 | Feasibility scoping (no extraction run) | Feasible, as a bounded pilot only | Corpus isn't uniform — 12/163 filenames are vesting notices (not trades, must be excluded); extraction of the open-market subset is deterministic and tractable; 40/163 filings had no text yet, 15/163 had no ticker, format variety unverified beyond 2 sampled documents |
| 23 | Bounded pilot — full extraction, classification, dedup, format audit, concentration/PIT/survivorship/H-011-independence checks | **CONDITIONAL GO** | 109 genuine transactions (83 purchase / 26 sale) after excluding vesting notices; the 40 missing-text filings are confirmed **scanned images** (0 native characters), blocked on the same pending OCR/tesseract decision already flagged in §2 above, not resolved here; null-ticker resolution is structurally impossible via existing tables (`securities.name` == `securities.ticker` for all 320 rows, `isin` 0% populated platform-wide — no company-name-to-ticker mapping exists anywhere on the platform); an initial 27-filing "duplicate" signal was a parser artifact (true duplicate count: 1, confirmed by exact source URL); severe concentration (top 3 tickers = 59% of observations, 64% of all transactions from a single year, 2020); real common-cause risk with H-011 — no mechanical overlap, but 16/18 corpus tickers (89%) sit above the platform median market cap, a likely governance/compliance-culture confound, not a trading signal |

**Named conditions before any return diagnostic** (from Stage 23's own gate): the OCR/scanned-PDF
decision; formal resolution or permanent exclusion of the 15 quarantined null-ticker filings; mandatory
size-orthogonalization in any future test given the 89% large-cap skew; explicit treatment of the cleaned
corpus as a small, clustered ~5–6-name sample, not 109 independent observations. Stage 24 (below) is the
return diagnostic these conditions gated — the null-ticker item is now resolved; the rest carry forward.

## 2c. Insider-dealing-notice track — Stage 24 (RETURN DIAGNOSTIC, CONDITIONAL GO)

The first return-bearing diagnostic in this track, run against Stage 23's cleaned corpus plus a
self-referential null-ticker resolution (all 15 resolved deterministically — 14 filings' stated issuer
"Nigerian Breweries Plc" and 1 "Airtel Africa Plc" exact-matched against already-ticked rows in the same
corpus; no external knowledge used). 109 raw genuine filings collapsed to **67 independent events**
(insider × ticker × direction × month) — 53 PURCHASE / 14 SALE — confirming Stage 23's concentration
finding was real, not a parsing artifact.

| Direction | k=20 (≈1 month) result | Verdict |
|---|---|---|
| PURCHASE | Mean excess return (vs. NGXASI) +5.74%, median +5.15%, 77% positive — clears the 3.79% round-trip cost | Only PURCHASE is tradable (platform is long-only) |
| SALE | Consistently negative (mean -13.09%) but magnitude highly unstable between raw and aggregated filings (2-4x swing) — corroborates the mechanism but not usable as an estimate, and untradeable regardless (no shorting) | Diagnostic support only |

**H-011 independence**: no mechanical overlap (`size_scores()` reconfirmed to use only `panel["mcap"]`);
correlationally, excess return vs. market cap is weakly *positive* (Spearman +0.13) — not a disguised
small-cap effect.

**Adversarial testing (the core of this stage)**: PURCHASE survives winsorization (mean +5.74%→+5.28%,
not outlier-driven) and survives the raw-vs-aggregated sensitivity check (~unchanged, unlike SALE). It
weakens under leave-top-3-out (UCAP/UBA/SEPLAT: k=20 mean +5.74%→+3.60%, dropping just under the cost
floor) — a real, disclosed concentration caveat. Only 1 of 5 pre-specified horizons (5/10/20/40/60
sessions) clears costs.

**Follow-up check, same day**: excluding SEPLAT and AIRTELAFRI — the two corpus tickers independently
flagged as high-staleness by Stage 21's own metric, raising a contamination risk with the already-killed
illiquidity mechanism — the effect **survived and strengthened** (n=44: mean +6.24%, median +5.59%, 91%
positive, winsorization-stable, naive t=4.18). This rules out the staleness mechanism as the explanation
and **makes insider-PURCHASE-at-k≈20 the strongest candidate the Stages 16–24 mechanism-discovery program
has produced.**

**Still open, not resolved**: UCAP alone is 45% of the ex-staleness subsample (n=20/44); only k=20 of 5
horizons clears costs; t-stats are naive/uncorrected for clustering; the 40-filing OCR gap (Stage 23)
still caps corpus size. **No hypothesis registered, no factor built, no backtest run** — this remains
diagnostic work. Full detail: `docs/STAGE24_INSIDER_DEALING_ADVERSARIAL_DIAGNOSTIC_2026-08-09.md`.

## 3. Roadmap to the first validated strategy

- **R0 (now, zero engineering)**: draft H-006 + H-007 preregs (pattern
  PREREG_H-005; vintage/gate/IRU pinned; staleness + liquidity filters and
  benchmark defined ex-ante) → owner review → gauntlet → mechanical
  verdicts. Two shots on goal with the two best-powered ready families.
- **R1 (parallel with R0 runs)**: DOL dividend/EPS layer parse + LIST2
  market-cap layer (both validated before use). No new hypotheses run
  until R0 verdicts are in — concurrency cap = 2 preregs.
- **R2**: wave-2 preregs from {low-vol, E/P value, dividend yield},
  informed by R0 *process* learnings (never by peeking at OOS).
- **R3**: first `confirmed` factor → Stock Scoring Engine speaks its first
  non-empty output (alpha_engine adapter, provenance-checked). Second
  confirmed factor → Portfolio Construction + Risk Engine build begins
  (charter milestone rule).
- **Continuous**: factor-decay monitoring design lands WITH the first
  confirmed factor (rolling IC vs validation-era IC, alarm thresholds
  pre-registered in the factor's library entry); corp-actions harvest
  completes in background; daily capture scheduling remains a pending
  owner decision — every missed day is unrecoverable.

## 4. Program-level rules (new, additive — no governance relaxed)

1. Benchmark ex-ante: until the LIST2 cap layer is validated, the
   investable benchmark is the equal-weighted IRU portfolio at quarterly
   rebalance with the same cost model, reported alongside ASI. Cap-weighted
   benchmark replaces it (new prereg field) once validated.
2. Concurrency cap: ≤2 open preregs; program multiple-testing tracked in
   the ledger (family-level count reported in every IC memo).
3. A factor enters the library only with: validation history, expected-alpha
   interval from walk-forward, capacity distribution, stability metrics,
   decay-monitoring spec, and an economic-rationale paragraph written at
   prereg time (not post hoc).
4. Every rejection updates this roadmap's family table before the next
   prereg is drafted.
