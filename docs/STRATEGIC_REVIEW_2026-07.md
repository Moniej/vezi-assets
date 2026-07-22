# Strategic Review — 2026-07-16

*Question under review: what is the fastest path from the current state to
multiple statistically valid, economically meaningful alpha sources?
Mandate: challenge every assumption; do not defend prior decisions.*

---

## 1. Audit of current state

**Platform** (built, working, sufficient): bitemporal PIT database; provider
DAL; immutable registry (**149 experiments**: 95 development, 34
walk-forward, 14 final-OOS, 6 placebo suites); ledger (5 hypotheses: 4
rejected — H-001 frozen — 1 queued); validation pipeline (stability grids,
Holm/BH, seeded placebo, walk-forward, IC memos, reproducibility reports);
alpha-engine shell (honest no-position); diagnostics; event pipeline with
restatement support.

**Data** (evidence-grade): 22,362 index-level rows (8 indices, 2012–2026,
ASI anchor-verified); Brent 4,181 rows (0.9); 94 curated events (80 MPC +
regulatory timeline); X-Issuer corporate-actions calendar **11,546 filings /
259 symbols** (2014–2026, 100% document URLs); 399 archived filing PDFs;
daily ephemeral capture (2 days old).

**Verdict record**: 4/4 rejections, all at sector-index level, long-only,
retail-max costs. Median idea-to-verdict time once data existed: same-day.

## 2. The central finding: we have a breadth problem, not a rigor problem

Quantitative alpha scales with breadth (IR ≈ IC × √N of independent bets).
Everything tested so far draws from **3–8 investable sector indices at
quarterly cadence ≈ 12–30 decisions/year**. At that breadth, even a genuine
edge with realistic skill is statistically undetectable and economically
unpayable after NGX costs — a conclusion our own four rejections keep
restating. H-001/003/004/005 are, in part, one result observed four times:
*the sector-index universe is too narrow to host discoverable alpha net of
~4% round trips.*

**Self-criticism (availability bias):** we tested index-level hypotheses
because index-level data was what we had — four times — while ranking
per-stock data #1 on the moat board and not acquiring it. The review's
verdict: no further sector-index hypotheses until per-stock breadth exists.

## 3. What changed and hasn't been exploited

Two discoveries this week invalidate the constraint that forced index-level
work:

- **investing.com's proven historical API serves individual Lagos equities**
  (IDs already resolved: ZENITHB 101753, GTCO 101690, UBA 101738, ACCESSCORP,
  SEPLAT, ARADEL, OANDO, AIICO…). The same endpoint that backfilled indices
  can backfill **per-stock OHLCV + volume** for the liquid cross-section,
  2012→. (Caveat: intermittent 403 since this afternoon — pace requests,
  retry window; history already banked proves the route.)
- **The X-Issuer feed gives 12 years of announcement-timestamped filings.**
  Critically, the earnings-event calendar requires **no OCR**: the filing's
  `Created` timestamp + `Type_of_Submission` ("Financial Statements", "Board
  Meeting") *is* the event. ~4 filings/yr × ~150 issuers × 12 yrs ≈ several
  thousand PIT-clean events.

Per-stock prices × filing events = the first genuinely powered hypothesis
families this project has had: ~100-name cross-sections and thousands of
events instead of 3 sectors and 10 events.

## 4. Bottlenecks, ranked

1. **Per-stock daily price/volume history** — blocks F2/F4/F5/F6/F8, the
   engine-full capacity machinery on real data, and the discovery module's
   power. THE bottleneck.
2. **OCR for scanned filings** — blocks structured dividends (TR truth, F6);
   decision pending user approval (tesseract install).
3. **Survivorship control for a backfilled equity universe** — investing.com
   lists current issuers; dead tickers may be missing. Mitigants we already
   hold: the 259-symbol filing universe (includes dead names),
   DelistedCompanies list, NGX daily ticker snapshot (forward). Universe
   definitions must come from the filing calendar, not from what the vendor
   happens to carry; names whose price history is unobtainable are recorded
   as coverage loss, never silently dropped.
4. **Economics ground truth** — every verdict leans on an *assumed* 3.8%
   retail round trip and rf=0%. One broker contract note + the CBN T-bill
   series would put both on evidence footing. (User-assist item; zero code.)

## 5. Process throughput review

The validation pipeline is **not** the constraint: verdicts take hours once
data exists (four in two days). Governance is sufficient; the engine shell
is sufficient. Throughput is gated by (a) dataset acquisition and (b)
credible-hypothesis supply — both addressed by the per-stock + filings
combination. **No platform work is justified right now** except what a live
hypothesis demands. The Discovery module (Q7): correct to automate
generation, wrong to build it against 8 index series — build it when
per-stock breadth lands, per its existing design doc; its scanners then have
real power (lead-lag across ~100 names, event-response across thousands of
filings, liquidity anomalies on real volume).

## 6. Assumptions challenged (Q10)

| Assumption | Verdict on the assumption |
|---|---|
| NGX *sector rotation* is the natural first structure | **Falsified in practice** — 4/4 rejections; breadth too small. The founding frame was the wrong altitude; single names are where dispersion and coverage gaps actually live. |
| Free data confines us to index level | **Obsolete** since equity-ID discovery. |
| Retail-max costs are the right base case | **Unverified** — most conservative, but viability conclusions inherit an assumption. Needs one contract note. |
| Direction labels must stay `unknown` | **Partially self-imposed.** Dividend *changes* (vs prior year) carry mechanical, non-hindsight signs once dividends are structured. Earnings "surprise" needs no analyst consensus if defined vs company's own history. |
| rf = 0% is a harmless placeholder | **Not harmless** at 15–25% T-bill yields; excess-vs-ASI framing contained the damage, but absolute claims and capacity economics need the curve. |
| Calendar-split OOS only | Adequate, but per-stock cross-sections enable held-out-names designs as a *supplement* (with correlated-market caveats) — more OOS power per year of data. |
| Placebo + Holm/BH + prereg regime | **Keep unchanged.** It is the platform's crown jewel and the reason the four rejections are trustworthy. |

## 7. Prioritized roadmap (by Δ long-term alpha-discovery rate)

| # | Action | Why first-order | Cost |
|---|---|---|---|
| 1 | **Per-stock OHLCV+volume backfill** (~50–100 liquid names, 2012→, investing.com API, paced; survivorship audit vs 259-symbol filing universe + DelistedCompanies) | Unlocks F2/F4/F5/F6/F8 breadth; converts the platform from 3-asset to ~100-asset research | days |
| 2 | **Earnings-event calendar** from filing metadata (no OCR) | Thousands of PIT events; pairs with #1 to power F5 | hours |
| 3 | **H-006: per-stock post-earnings drift (PEAD)** + **H-007: per-stock cross-sectional momentum** — pre-register both, run through the unchanged pipeline | First adequately-powered hypotheses in project history; both are documented EM anomalies (priority = efficiency + power, NOT expected success) | days |
| 4 | **OCR approval → structured dividends** (parallel track) | TR truth; F6; dividend-change directions; completes corp-actions DB | user decision + days |
| 5 | **Full 70k-filing archive** (background) + continue daily capture | Permanent asset; governance/sentiment corpora later | background |
| 6 | **T-bill curve + broker contract note** | Puts economics on evidence footing for all future verdicts | user assist |
| 7 | **Discovery module build** (existing design) after #1 lands | Automated candidate generation with real power | ~week, later |
| 8 | H-002 *as scoped* (sector TR momentum) | **Deprioritized with reasons**: per-stock TR momentum (H-007 + #4) strictly dominates — more breadth, same data needs, dividends matter more at stock level. H-002 stays queued; recommend re-scoping decision at IC when #4 completes | — |

## 8. Shortest path to the first validated source (Q8)

Path: #1 + #2 (data, ~days) → #3 (two powered preregs through the unchanged
gauntlet). If either validates, the engine wires its first model with full
provenance; if both reject, the platform will have finally tested
*adequately powered* hypotheses — and their rejections would, for the first
time, be informative about the market rather than about our sample size.
Rigor is unchanged: prereg before results, untouched OOS, placebo, Holm/BH,
honest verdicts. Speed comes from breadth, not shortcuts.
