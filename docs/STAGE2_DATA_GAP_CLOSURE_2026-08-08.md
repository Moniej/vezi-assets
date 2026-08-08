# STAGE 2 — DATA GAP CLOSURE (2026-08-08)

Read-only investigation. No hypothesis created. No pipeline built beyond
what's noted as already-existing. `configs/h011_size.toml`,
`docs/PREREG_H-011.md`, H-011's signal/construction, and all frozen
experiment results are unmodified. All figures below are measured
directly against `data/ngx.sqlite` / the archive on disk, not carried
forward from prior documents without re-verification.

---

## Section 1 — Current Data Coverage (baseline)

- `documents` (X-Issuer disclosure archive): 210 distinct tickers, 12,533
  documents, by type: other 7,727, governance 915, agm 794, board_meeting
  590, closed_period 590, **results_notice 357**, dividend 328,
  **dealing 163**, **rights_capital 52**, **bonus_split 17**.
- `extracted_facts`: 329 facts, 64 tickers touched at all, but only
  **13 tickers have any `financial_statements`-taxonomy fact**.
- Current IRU (investable universe): **100 members** (as of 2026-06-30).
  320 securities tracked platform-wide, ever.
- `financial_ontology.toml`: definitional skeleton already covers
  income_statement (13 nodes incl. `cogs`, `gross_profit`, `opex`,
  `interest_expense`, `tax`, `shares_outstanding`, `eps`), balance_sheet
  (3 nodes), cash_flow (3 nodes) — **broader than what's currently
  extractable** (see Section 2/3).

## Section 2 — FSI Coverage Matrix

`fact_taxonomy.toml`'s `financial_statements` leaf has 12 extractable
types: revenue, net_profit, assets, liabilities, equity, cfo, cfi, cff,
capex, fcf, ebitda, ebit. (`pbt`/`eps` are visible in source filings per
the 2026-08-04 pilot but not yet valid fact_types — unchanged since.)

| ticker | fields (of 12) | periods | date range | currency | mean conf. | grounding | usable for factor research |
|---|---|---|---|---|---|---|---|
| AIRTELAFRI | 12/12 | 1 | 2025-03-31 | USD | 1.00 | 10 passed / 2 not_run (derived) | **No — single period, no history** |
| GEREGU | 12/12 | 1 | 2021-12-31 | NGN | 1.00 | 10 passed / 2 not_run (derived) | **No — single period, no history** |
| NASCON | 10/12 | 3 | 2024-06 to 2025-12 | NGN | 0.91 | 30/30 passed | **Marginal — best depth+breadth combo, still short of a real panel** |
| BUAFOODS | 9/12 | 3 | 2022-09 to 2024-12 | NGN | 0.89 | 23/23 passed | Marginal |
| CAP | 8/12 | 3 | 2020-12 to 2025-06 | NGN | 0.90 | 17/17 passed | Marginal |
| LASACO | 7/12 | 1 | 2022-12-31 | NGN | 1.00 | 7/7 passed | No |
| AFRIPRUD | 7/12 | 3 | 2020-09 to 2023-06 | NGN | 0.89 | 21/21 passed | Marginal |
| UCAP | 5/12 | 3 | 2020-09 to 2025-12 | NGN | 0.92 | 15/15 passed | No |
| DANGCEM | 4/12 | 2 | 2024-03 to 2025-03 | NGN | 0.90 | 8/8 passed | No |
| NESTLE | 4/12 | 2 | 2023-12 to 2024-12 | NGN | 0.90 | 7/7 passed | No |
| MTNN | 3/12 | 2 | 2023-12 to 2024-12 | NGN | 0.90 | 6/6 passed | No |
| OANDO | 3/12 | 2 | 2021-12 to 2024-12 | NGN | 0.90 | 6/6 passed | No |
| UBN | 2/12 | 2 | 2021-12 to 2022-12 | NGN | 0.90 | 4/4 passed | No |

**Extraction quality is genuinely excellent** — grounding pass rate is
100% everywhere it was attempted (the only "not_run" entries are
correctly-flagged derived `fcf` values), mean confidence 0.89-1.00. The
gap is **breadth and depth, not quality.**

**Answering the gate question directly: the 15-25 full-depth ticker
target has NOT been reached.** Two tickers reach 12/12 fields; neither
has more than one period. Zero tickers combine full-statement depth with
multi-year history. NASCON is the platform's best case at 10/12 fields ×
3 periods, and even that is one ticker, not fifteen.

**Items 4-10 of the audit checklist** (announcement dates, period-end
dates, knowledge dates, currency, restatement handling, PIT
reconstruction, confidence/grounding): all mechanically supported by the
schema already (`period_start`/`period_end`/`period_type`,
`documents.filing_date` as the knowledge-date proxy, `currency`,
`restates_fact_id`, `grounding_check`, `extraction_confidence`,
`confidence_tier`) — **infrastructure is not the blocker; extraction
volume is.**

**Item 11 (universe coverage)**: 13/100 current IRU names have any FS
fact (13%); 2/100 have full depth (2%). **Item 12 (ontology fit)**: the
ontology's `income_statement` node family already includes `cogs`,
`gross_profit`, `opex`, `interest_expense`, `tax`, `shares_outstanding`,
`eps` — none of which are yet valid `fact_taxonomy.toml` leaves. **The
ontology can represent MORE than the taxonomy currently extracts** — no
ontology redesign needed to go deeper, only taxonomy leaves + extraction
volume.

## Section 3 — Fundamental Factor Readiness

Required fields mapped against Section 2's actual coverage (not the
ontology's aspirational coverage).

| Family | Required fields | Available (any ticker) | Securities w/ sufficient coverage | Hist. depth | PIT feasible | Missing fields | Testable now | Rationale | Independent of H-011? | Priority |
|---|---|---|---|---|---|---|---|---|---|---|
| **Profitability** (gross/op margin) | revenue, cogs or gross_profit, ebit/ebitda | revenue, ebit, ebitda (no cogs/gross_profit extracted) | 0 with full field set | n/a | Yes (mechanism exists) | cogs, gross_profit | **No** | Margin-quality premium plausible on NGX given wide cross-sector margin dispersion | Likely yes (fundamental, not price-derived) | **High** — closest to testable, one taxonomy addition away |
| **Financial Strength** (leverage, solvency) | assets, liabilities, equity | assets, liabilities, equity (13 tickers) | 2 full-depth, ~11 partial | 1-3 periods | Yes | none structurally | **No** — coverage too thin | Distress/leverage discount plausible given NGX bank/insurer capital stress episodes | Yes | **High** |
| **Cash Flow Quality** (accruals vs. cash earnings) | net_profit, cfo | both present (13 tickers) | 2 full-depth | 1-3 periods | Yes | none | **No** — coverage too thin | Accrual-quality anomaly is one of the most robust EM findings | Yes | **High** |
| **Value** (P/B, P/E) | net_profit or equity + market cap | present for FS tickers; market cap panel already exists (H-011's own) | 2 full-depth (12/12), 5-6 partial | 1-3 periods | Yes | none structurally | **No** | Classic value premium, untested on NGX at all | Yes | **High** |
| **Growth** | revenue/net_profit, ≥2 periods | present where ≥2 periods exist (8 tickers) | 8 (2-3 periods) | 2-3 periods, still short | Yes | none, but need more periods | **No** — need ≥4-8 periods for a real growth measure | Plausible but generic | Yes | Medium |
| **Accruals** | net_profit, cfo, assets (working-capital detail ideally) | net_profit, cfo, assets present; no working-capital line items | 2 full-depth | 1 period | Yes (mechanism) | receivables/payables detail (not in taxonomy) | **No** | Well-documented EM anomaly | Yes | Medium |
| **Asset Turnover** | revenue, assets | both present (13 tickers) | 2 full-depth | 1-3 periods | Yes | none | **No** — coverage too thin | Plausible efficiency signal | Yes | Medium |
| **Gross Profitability** (Novy-Marx) | revenue, cogs/gross_profit, assets | revenue, assets present; cogs/gross_profit missing | 0 | n/a | Yes (mechanism) | cogs, gross_profit | **No** | Strong, well-replicated academic factor | Yes | **High** — same one-field gap as Profitability |
| **Earnings Quality** | net_profit, cfo, accruals detail | net_profit, cfo present | 2 full-depth | 1 period | Yes | accruals detail | **No** | Plausible | Yes | Medium |
| **Quality** (composite: ROE, leverage, earnings stability) | net_profit, equity, assets, liabilities, multi-period | all core fields present | 2 full-depth | 1-3 periods | Yes | none structurally, needs periods | **No** | Standard, high-conviction family | Yes | **High** |
| **Investment** (asset growth) | assets, ≥2 periods | present where ≥2 periods (8 tickers) | 8 | 2-3 periods | Yes | none | **No** — depth too thin for a clean growth-rate signal | Plausible (over-investment anomaly) | Yes | Medium |

**Bottom line for Phase 2B**: **zero of eleven families are testable
today.** None fail on missing fields alone — most (Financial Strength,
Cash Flow Quality, Value, Quality, Asset Turnover, Earnings Quality) fail
purely on **coverage** (2-13 tickers vs. a 15-25 minimum breadth floor
this platform's own code enforces — `_eligible()`'s `len(elig) < 10`
guard, the same floor Wave 6 already flagged). Two families
(Profitability, Gross Profitability) are additionally missing exactly
one field each (`cogs`/`gross_profit`) that is already visible in every
filing read so far and already has an ontology node — **the single
cheapest fundamental-factor unlock available**, cheaper than closing the
coverage gap itself.

## Section 4 — Free-Float / X-Compliance Assessment

Re-confirmed, not newly discovered: **no free-float dataset exists on
this platform** (zero hits for `shares_outstanding`/`free_float` in code
or data, per `docs/METHODOLOGY_HARDENING_2026-08-04.md`, re-verified —
`extracted_facts` has no free-float fact type, `documents` has no
X-Compliance doc_type). NGX X-Compliance (the exchange's own recurring
free-float report, tied to the Listing Rules' 20% minimum free-float
requirement for Main/Premium boards) remains the best-scoped candidate
source per `docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md` — **not
acquired**, historical archive depth **still unscoped** (never actually
probed for how far back it goes).

Per your explicit purpose statement (does H-011's Size effect survive
float-adjustment, not "build a new hypothesis"): **infrastructure
prep is premature** — there is no float data to adjust against yet.
What IS reasonable to prepare, and costs nothing: `backtest_xs.py`'s
`load_market_cap_panel` already documents its full-issue-cap method
precisely enough that a float-adjusted variant would be a **parallel
function**, not a rewrite (mirrors how `xs_liquidity_scores` was added
alongside `liquidity_scores` without touching either). **Recommendation:
do not build this function yet — there is nothing to feed it.** The
correct next action is scoping the X-Compliance archive's actual
historical depth (a single research task, zero engineering), not writing
adjustment code against a dataset that doesn't exist locally.

## Section 5 — Insider/Director Data Investigation

**This is the single largest surprise of Stage 2.** The archive already
contains **163 "dealing" documents** (`documents.doc_type='dealing'`),
titled things like *"NOTIFICATION OF SHARE DEALING BY INSIDER"*, spanning
**2020-02-27 to 2026-07-10** (6.4 years) across **29 distinct tickers**
(23 of which are in the current 100-name IRU). Zero of these have been
extracted into structured facts — `extracted_facts` has no dealing/
insider fact_type at all.

Visually inspected one at full resolution (Flour Mills of Nigeria,
2020-06-29 transaction, filed 2020-06-30 — a **1-day filing lag**,
excellent for PIT purposes): it is a **standardized, structured
disclosure form** (matches the international PDMR-notification template)
with explicit, machine-extractable fields:
- Name and position/status of the insider (**"Director" or "Substantial
  Shareholder"** — both categories use the same form, see Section 6)
- Issuer name + Legal Entity Identifier
- Nature of transaction (purchase/sale)
- Volume and price per share
- Aggregated volume/price
- **Date of Transaction** (distinct from filing date — the correct PIT
  anchor) and place of transaction

| dimension | finding |
|---|---|
| Legal/access status | Public NGX regulatory disclosures, already legally harvested (same `xissuer_docs` pipeline as every other document type here) |
| Historical depth | 2020-02 to 2026-07 (6.4 years); **front-loaded — 103/163 (63%) in 2020 alone**, tapering to single digits/year after 2022. Not yet established whether this is a genuine filing-volume decline or a harvest-completeness gap for 2021+ — **needs verification before trusting the trend** |
| Coverage | 29 tickers, uneven; not yet checked against IRU PIT-membership at each event date |
| Timestamps | Transaction date + filing date both present, ~1-day lag observed in the one sample read | 
| PIT feasibility | Yes — filing_date is a genuine knowledge-date, transaction date is the economic event date, exactly the two-date structure this platform's PIT machinery already expects (`first_seen`/event-date pattern from `exdiv_closure_calendar.csv`) |
| Reliability | High — official NGX regulatory filings, standardized form |
| Extraction difficulty | Low-Medium — same hand-read/grounded-quote methodology already proven on FSI, but the documents are scanned images (char_count=0 on every one checked), so OCR/vision extraction is required, not plain-text `pdfplumber` |
| New information? | **Yes** — nothing else on the platform captures insider/substantial-shareholder transactions |
| Supports a future hypothesis family? | **Yes, plausibly** — subject to resolving the 2021+ coverage-completeness question first |

**Classification: A — genuine new alpha information**, conditional on
(a) confirming the post-2020 taper is a real filing pattern and not a
harvest gap, and (b) a small extraction pilot (mirroring the FSI pilot's
own depth-first, few-tickers-first discipline) before any breadth claim.
This is evidence-based, not asserted because "insider data sounds
interesting" — the standardized form and clean date fields are the
actual reason it clears the bar the other candidates (ownership
registers, governance filings) do not.

## Section 6 — Ownership/Shareholding Investigation

Kept separate from free-float per your instruction. Two distinct
findings:

1. **Static beneficial-ownership registers / shareholding-concentration
   snapshots: still not found.** Re-confirms `docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`
   item B5 — no adequate free source for full ownership registers was
   identified then, and nothing in this session's direct database/archive
   inspection changes that. **Classification: D (not worth pursuing
   now)** — there is no evidence a reconstructable historical panel
   exists, static or PIT.
2. **Ownership CHANGE events are partially available** — via the exact
   same "dealing" document category as Section 5. The sample read was a
   *"Substantial Shareholder"* notification (Excelsior Shipping Limited,
   2,000,000 shares, ₦21/share) — the standardized form does not
   distinguish "Director" from "Substantial Shareholder" at the document-
   type level; both live in `doc_type='dealing'`. **This means Phase 2D
   and 2E are not two separate datasets — they are two different
   QUESTIONS asked of the same 163-document archive** (director dealing
   vs. ownership-concentration change), separable only after extraction
   by reading the "Position/status" field.

**Do not force a standalone Ownership hypothesis family.** What exists is
a transaction-level ownership-change feed, not a point-in-time
concentration panel — useful for an event-style signal (does a
substantial-shareholder purchase predict returns), not for a
cross-sectional "ownership concentration" characteristic sort. Classify
the register/snapshot question as **D**; classify the transaction-event
question as the same **A** as Section 5, sharing one extraction task, not
two.

## Section 7 — Corporate-Action Resolution (Stage 1 A-3 follow-up)

All five Stage 1 overlaps re-investigated with real archive documents,
not re-guessed. Two of five are now **CONFIRMED with sourced ratio/date
evidence** — a material upgrade from Stage 1's "unresolved":

### CILEASING — 2024-01-05 — **CONFIRMED genuine corporate action**
- Source: `data/archive/xissuer_docs/21671_…BONUS_ISSUE_ANNOUNCEMENT…NOVEMBER_2023.pdf` (read directly, real text layer)
- **Ratio: 2-for-3 bonus** (2 new shares per 3 held)
- **Qualification date: Thursday, 4 January 2024. Register closed from
  Friday, 5 January 2024** — matches the observed jump date exactly.
- Theoretical mechanical markdown: 3/5 = 0.600 of prior price. Observed:
  3.38/5.13 = 0.659. Close, not exact (real market move layered on the
  mechanical dilution, expected) — **this is the corporate action Stage
  1 could not confirm; now it is.**

### LASACO — 2021-02-22 — **CONFIRMED genuine corporate action; Stage 1's "thin-trading" read was WRONG, corrected here**
- Source: `data/archive/xissuer_docs/11502_…NOTICE_OF_SHARE_RECONSTRUCTION…pdf` (scanned, read via vision)
- **1-for-4 share reconstruction (reverse split)**: "reconstruct its
  issued and fully paid-up Share Capital... in the ratio One (1) new
  Ordinary share for every Four (4) Ordinary shares previously held"
- Trading suspended **1-12 February 2021** per the notice (actual
  resumption in the price data was 2021-02-22 — roughly a week later
  than announced, plausible for a real regulatory-approval delay)
- Theoretical mechanical repricing: 4.0x. Observed: 1.52/0.42 = 3.62x.
  Close. **Stage 1 speculated this was a thin-trading artifact — that
  was the wrong read; it is a real, sourced corporate action.**

### PRESTIGE — 2018-06-08 — **Genuinely ambiguous, resolved as far as evidence allows**
- Source: `data/archive/xissuer_docs/5075_…CORPORATE_ACTIONS_JUNE_2018.pdf` — a **48th AGM notice** (visually read: scanned image, no text layer). Resolution 7 proposes **a bonus issue of 41 new shares for every 100 held**, register closure **4-8 June 2018**.
- The closure window brackets the observed jump date, but the observed
  move is **+45.7% (UP)**, the opposite direction a bonus-dilution
  markdown implies (÷1.41 ≈ -29%). This is a genuinely proposed (not yet
  necessarily executed/listed) bonus at AGM stage, and the up-move is
  more consistent with post-closure repricing/illiquidity than a clean
  mechanical bonus markdown. **Left as: a real corporate-action period
  coincides with this date, but the specific one-day move's cause is not
  confirmed** — reported honestly rather than forced into either bucket.

### PRESTIGE — 2018-11-28 — **Unresolved, real corroborating context found**
- Source: `data/archive/xissuer_docs/5744_…CORPORATE_ACTIONS_OCTOBER_2018.pdf` — a board meeting notice (29 Oct 2018) with agenda item **"Update on restructuring of the Balance Sheet"**, ~1 month before the observed -35.3% two-day decline.
- No ratio, no ex-date, no bonus/scrip mechanism disclosed. **More
  consistent with a genuine negative market reaction to disclosed
  financial distress than an unadjusted corporate action** — but this is
  inference from qualitative context, not a confirmed causal link. Left
  unresolved by design (A-6: no fabrication).

### IMG — 2023-12-29 — **Unchanged from Stage 1: no relevant document found nearby**
- Best remaining explanation: thin-trading price-discovery gap, not a
  corporate action.

**Immediate, low-cost implication**: the platform has **17 `bonus_split`
and 52 `rights_capital` documents already harvested and completely
unextracted**. Two of five Stage 1 "unresolved" cases were resolved
simply by reading two of these documents by hand. Extracting this
existing backlog (not a new acquisition) is very likely the cheapest,
highest-confidence way to close the platform-wide bonus/scrip-adjustment
gap Stage 1 disclosed — cheaper than the FSI pilot, since the raw
material is already on disk.

## Section 8 — Dataset Decision Matrix

| Dataset | Info added | Duplicates | Family enabled | Hist. depth | Coverage | PIT | Reliability | Confidence | Acquisition difficulty | Integration difficulty | Research value | Class | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FSI depth expansion (existing pilot, more tickers) | Fundamentals (Value/Quality/Financial Strength/Cash Flow Quality/Asset Turnover) | None | 5+ families | Currently 1-3 periods; grows with each new filing extracted | 13/100 IRU now; needs 15-25 full-depth | Yes (schema already supports it) | High (100% grounding to date) | High | Low (already-archived filings, zero new acquisition) | None (schema exists) | **Highest** | A | **BUILD NOW** (extraction labor, not engineering) |
| `cogs`/`gross_profit` taxonomy leaves | Unlocks Profitability + Gross Profitability specifically | None | 2 families | Same as above | Same as above | Yes | High | High | Very low (config change + re-extraction of already-open filings) | Trivial | High, cheap | A | **BUILD NOW** — cheapest unlock on this entire list |
| Bonus/scrip extraction (17 `bonus_split` + 52 `rights_capital` docs already archived) | Closes Stage-1-disclosed platform-wide return-series risk | None | 0 new families — data-quality/PIT correctness | 2016-2024 (per docs seen) | Unknown until extracted; likely dozens of tickers | Yes (filing_date = knowledge date) | High (official NGX notices) | High | Very low (already on disk) | Low (new fact_types under `capital_and_balance_sheet`, already taxonomy-ready: `bonus_issue`, `rights_issue`) | High (protects EVERY existing and future hypothesis's return series) | B | **BUILD NOW** |
| Insider/director + substantial-shareholder dealing (163 docs already archived) | Genuinely new signal dimension | None | 1 new family (candidate) | 2020-2026, front-loaded | 29 tickers, 23 in current IRU | Yes (txn date + filing date both present) | High (official form) | High for fields, unverified for coverage completeness | Low-Medium (scanned images — needs vision/OCR extraction, not plain text) | Low (new doc category, same pipeline) | High | A | **INVESTIGATE** — verify 2021+ coverage completeness, then a small depth-first pilot (5-10 docs), before any breadth claim |
| Free-float / NGX X-Compliance | Improves H-011 construct validity | None | 0 new families | Unscoped | Unscoped | Unknown | Official source | Unknown until scoped | Unscoped (not yet acquired) | Medium | Medium (fixes 1 factor's known limitation) | B | **INVESTIGATE** (scope historical depth only — no code yet, nothing to feed it) |
| Beneficial-ownership registers (static) | Would be new, IF it existed | None | Unknown | N/A — not found | N/A | N/A | N/A | N/A | No adequate free source identified (re-confirmed) | N/A | N/A | D | **REJECT** (not until a real source is found) |
| CBN/NBS/FX/Brent | Macro regime context | Partially already ingested (`ingest_mpc.py`, `ingest_brent.py`) | 0 directly (conditioning only) | Good (CBN MPR history already used in METH-002) | N/A | Yes, already proven | High | High | Low (already partially built) | Low | Low-Medium, secondary per your own instruction | B | **BACKLOG** — secondary to company-level work per your standing priority |
| NGX Pulse / NGN Market APIs | Cross-check only | Duplicates existing primary price/disclosure sources | 0 | N/A | N/A | Unclear | Secondary | Medium | Free-tier call caps | Low | Low | C | **BACKLOG** |
| NEITI / GDELT / nightlights / Google Trends | Frontier-native signals | None | ≤1 each | Varies | Varies | Risky (thin-trading pipeline not yet adapted) | Medium | Low-Medium | High | High | Low now, later high | C | **BACKLOG** — explicitly sequenced last, unchanged from Wave 6 |

## Section 9 — Highest-Value Remaining Data Gaps (ranked)

1. **FSI breadth/depth** (13→15-25+ full-depth tickers) — still the
   single largest blocker, now with a proven, cheap, on-disk extraction
   path, not a hypothetical one.
2. **`cogs`/`gross_profit` taxonomy leaves** — smaller in scope but
   higher ROI per unit of effort than #1: unlocks 2 families from a
   config change plus re-reading filings already open in the FSI pilot.
3. **Bonus/scrip extraction from the existing 69-document backlog** —
   protects every hypothesis's return series (H-011 included), already
   proven valuable (2 of 5 Stage 1 mysteries solved by reading 2 files).
4. **Insider/substantial-shareholder dealing** — the one genuinely new
   information dimension with real, standardized, dated evidence behind
   it; needs a completeness check before a breadth claim, then a pilot.
5. Free-float historical-depth scoping — cheap, narrow, improves H-011's
   construct validity but unlocks no new family.

## Section 10 — What Is Now Testable

**Nothing new, honestly.** No fundamental factor family clears its
coverage bar today (Section 3). H-011 remains the platform's only
testable, confirmed factor. This is not a negative result for Stage 2 —
Stage 2's job was readiness, not new tests, and it found three concrete,
low-cost paths to readiness that did not visibly exist before this
session (the taxonomy-leaf shortcut, the bonus/scrip backlog, and the
already-harvested insider-dealing archive).

## Section 11 — What Is Still Blocked

- Every fundamental factor family (Section 3) — blocked on FSI breadth,
  not on infrastructure or ontology design.
- Float-adjusted H-011 retest — blocked on X-Compliance acquisition,
  which is itself blocked on a historical-depth scoping question no one
  has answered yet.
- A standalone insider-trading hypothesis — blocked on verifying whether
  2021+ "dealing" coverage is a real decline or a harvest gap, and on
  actually extracting the 163 documents (currently zero extracted).
- A standalone ownership-concentration hypothesis — blocked, likely
  permanently absent a new source (Section 6, classification D).

## Section 12 — Recommended Stage 3

**Answering your one question directly: the single highest-value thing
Project 1 should do next is extracting the `cogs`/`gross_profit` fields
from the filings the FSI pilot has ALREADY opened and hand-verified
(GEREGU, LASACO, AIRTELAFRI, plus NASCON/BUAFOODS/CAP/AFRIPRUD), while in
parallel scaling FSI breadth toward the 15-25 ticker floor using the same
proven methodology.**

Why this beats the alternatives concretely, not generically:
- It is not a new acquisition — the documents are open, already read,
  already grounded at 100% pass rate.
- It is the cheapest of every option in Section 8's matrix (a taxonomy
  config addition + re-reading files already in hand) and it is the
  ONLY action that unlocks a full factor family (Gross Profitability, a
  well-replicated academic factor never tested here) in one step rather
  than incrementally building toward a breadth floor.
- It runs in parallel with, not instead of, continued FSI breadth
  expansion — same labor pool, same methodology, no resource conflict
  (mirrors Wave 6's own finding that Milestones A and B could run
  concurrently).
- The bonus/scrip extraction (Section 7/9 #3) should run alongside it,
  not after — different documents, same low-cost "read what's already
  archived" pattern, and it protects H-011's own return series while FSI
  work continues.

**Do not start the insider-dealing pilot yet.** It is real (Class A,
Section 5) but it is the least de-risked of the four live options —
verify the 2021+ coverage question first (a single query/read task, not
mentioned lightly: if it turns out to be a harvest gap rather than a
genuine decline, re-harvesting is needed before any pilot is meaningful).

**No H-018.** Nothing in this audit produces a dataset that is
simultaneously available, sufficiently historical, PIT-reconstructable,
sufficiently covered, and economically defensible today. That remains
correctly gated behind Stage 3's FSI/bonus-extraction work.
