# Factor Candidate Registry — Priority 1 Audit (Wave 2, Master Research Directive)

*2026-08-02. Permanent, living registry of every candidate factor family the
platform could plausibly test, per the Wave 2 directive's Factor Discovery
Program requirement. Distinct from `docs/FACTOR_REGISTRY.md`, which tracks
hypotheses that have actually been PRE-REGISTERED AND RUN (H-001…H-012). This
document tracks the wider universe of NAMED candidates, most of which have
never reached pre-registration, and states plainly which ones the data
supports today versus which do not exist yet.

**Method**: every "Current coverage" figure below was queried directly against
`data/ngx.sqlite` and `data/reference/*` on 2026-08-02, not assumed or carried
over from prior documentation. See the raw queries in this session's audit
trail. This mirrors standard academic asset-pricing practice — e.g.
Fama & French (1992, 1993) restricted their book-to-market/profitability
sorts to firms with usable COMPUSTAT balance-sheet coverage and explicitly
excluded financials for lack of comparable data, rather than assuming
coverage existed.

**Reference bar**: Investable Research Universe (IRU) v2, 100 members as of
2026-06-30 (`src/ngxrot/universe.py`). Every hypothesis validated or rejected
so far (H-001–H-012) tested at this breadth or a named subset of it. Any
candidate below whose usable ticker coverage is far below 100 is, by the
platform's own established precedent, not yet a fair test.

---

## Status vocabulary (per directive)

`Proposed` — named as a candidate, no feasibility check done.
`Data-Blocked` — feasibility checked; required data does not exist at usable breadth.
`Data-Partial` — some raw data exists but needs its own classification/validation pass before use.
`Available` — data exists at full/near-full IRU breadth today; ready for pre-registration.
`Pre-Registered` — prereg document frozen, not yet run.
`Running` — Phase 4 pipeline in progress.
`Confirmed` / `Rejected` — resolved, see `FACTOR_REGISTRY.md`.
`Archived` — permanently retired, no further tests planned.

---

## A. Available now — zero new data required

### A1. Liquidity (trading-activity variant)

- **Economic rationale**: Illiquid stocks command a return premium as
  compensation for higher transaction costs and slower execution
  (Amihud & Mendelson 1986 bid-ask-spread liquidity premium; Amihud 2002
  illiquidity-ratio literature: `ILLIQ = |return| / value_traded`).
- **Supporting literature**: Amihud & Mendelson (1986, *JFE*); Amihud (2002,
  *Journal of Financial Markets*); Pástor & Stambaugh (2003, *JPE*, liquidity
  as a priced risk factor) — all publicly documented, cited on the strength of
  their published methodology, not on any claim about a specific institution's
  internal implementation.
- **Expected mechanism**: cross-sectional sort on trailing average
  daily-value-traded (ADTV) or Amihud illiquidity ratio; expect the
  low-liquidity leg to earn a premium if the effect exists in NGX.
- **Required data**: daily `volume` / `value_traded`, no financial-statement
  data needed.
- **Current coverage**: `equity_prices` has 320 distinct tickers; 334,064 /
  353,043 rows (94.6%) have nonzero `value_traded`. At the 100-name IRU level
  this is effectively complete coverage — the same panel every prior
  hypothesis (H-001–H-012) has already used for costs/turnover/benchmark
  construction.
- **Testability**: fully testable today. `backtest_xs.py` already has the
  scoring/target/simulate/placebo machinery generalized across `xs_rank`/
  `xs_vol`/`xs_size` methods; an `xs_liquidity` variant is a same-shape
  addition (mirrors H-011's `xs_size` addition almost exactly — cap replaced
  with trailing ADTV or Amihud ratio).
  - **Caveat, stated plainly**: this is a distinct concept from
    *institutional-ownership* or *free-float* liquidity (no ownership data
    exists on this platform — see B7). This is a pure trading-activity
    liquidity premium.
- **Dependencies**: none. No owner decision, no vendor, no OCR.
- **Current status**: **Rejected** (2026-08-03, both directions tested —
  H-016, `docs/H016_LIQUIDITY_REPORT_2026-08-03.md`). Neither a long-
  illiquid (classic Amihud & Mendelson) nor a long-liquid whole-universe
  tilt produced a credible standalone premium against the EW-IRU
  benchmark. See `docs/FACTOR_REGISTRY.md`'s H-016 entry for full
  evidence. Liquidity appears to matter on this platform only as a
  conditioning characteristic on Size (per H-013), not as an independent
  factor.

### A2. Dividend Yield — **payer-status (binary) variant only**

- **Economic rationale**: dividend-paying firms are, on average, more mature,
  cash-generative, and lower-risk; a "payer vs. non-payer" tilt is a
  well-documented, simpler cousin of the yield-magnitude anomaly (Fama &
  French 2001, "Disappearing dividends"; Naranjo, Nimalendran & Ryngaert 1998
  dividend-yield/return studies).
- **Supporting literature**: Fama & French (2001, *JFE*); Litzenberger &
  Ramaswamy (1979, *JFE*, dividend-yield effect); note these establish a
  *yield-magnitude* effect — the payer/non-payer binary tested here is a
  narrower, data-constrained proxy, not the same claim.
- **Expected mechanism**: sort into payer vs. non-payer cohorts using
  confirmed ex-dividend closure events; expect payers to show
  lower-volatility, possibly lower-return characteristics (a risk-tilt test,
  not a yield-carry test).
- **Required data**: dates on which a company went ex-dividend (payer
  identification only — not the yield amount).
- **Current coverage**: `data/reference/exdiv_closure_calendar.csv` — 1,044
  rows, **217 distinct symbols**, validated/closure-calendar quality (this is
  the same file Wave-3's own C5 candidate cites). This comfortably covers the
  100-name IRU.
  - **Yield MAGNITUDE remains blocked**: the DOL EPS/P.E. parser was tried
    twice (naive last-two-tokens: 58.5% pass; header-calibrated banding:
    34.3% pass, new failure mode) and is a documented, already-closed
    negative result (`reports/eps_pe_extraction_status.md`, 2026-07-22). No
    structured dividend-per-share or yield figure exists anywhere in the
    database.
- **Testability**: testable today as a binary payer/non-payer tilt only.
- **Dependencies**: none for the binary variant. Yield-magnitude variant is
  blocked pending a materially different extraction approach (owner/vendor
  decision) — this is the SAME blocker already disclosed and closed on
  2026-07-22, not a new finding.
- **Current status**: **Available** (payer-status variant) — not yet
  Pre-Registered. This is Wave-3's own Candidate C5, still open.

### A3. Interaction Factors — Size × Volatility, Size × Momentum, Size × Liquidity

- **Economic rationale**: factor interactions test whether a premium is
  concentrated in a sub-population (e.g., "small-cap low-vol" effects
  documented in developed markets, Asness/Frazzini/Pedersen-style
  size-adjusted factor research at AQR — citing their *published* work, e.g.
  Asness, Frazzini, Israel & Moskowitz (2018, "Size Matters, If You Control
  Your Junk", *JFE*) — not any claim about undisclosed proprietary
  implementation).
- **Supporting literature**: Asness et al. (2018, *JFE*); Fama & French
  (1993, *JFE*, original size×value double-sort methodology) — double-sorting
  on two characteristics is standard academic practice, not a novel
  technique.
- **Expected mechanism**: two-way sort (e.g., small-cap AND low-vol
  simultaneously) rather than single-characteristic sort; tests whether
  H-011's confirmed size premium and H-008's rejected vol premium interact.
- **Required data**: market cap (already used, H-011), realized volatility
  (already used, H-008), trailing return (already used, H-007/H-009/H-010),
  ADTV (see A1) — all already computed at full IRU breadth inside
  `backtest_xs.py`.
- **Current coverage**: complete — every required input is an existing,
  already-validated score series.
- **Testability**: fully testable today, zero new data acquisition. Requires
  new double-sort scoring logic (additive, same pattern as every prior
  extension) but no new data source.
- **Dependencies**: none.
- **Current status**: **Available** — not yet Pre-Registered. Directly
  answers the earlier directive's Phase 30 ask (Factor Interaction Research).

---

## B. Data-Blocked — same root cause (FSI extraction ceiling)

All of the following require financial-statement line items. Real coverage,
verified 2026-08-02 via `extracted_facts` joined to `documents`:

| fact_type | distinct tickers | rows |
|---|---:|---:|
| dividend | 60 | 152 |
| net_profit | 10 | 25 |
| revenue | 10 | 25 |
| ebit | 7 | 18 |
| ebitda | 6 | 14 |
| assets | 5 | 14 |
| equity | 5 | 14 |
| liabilities | 5 | 14 |
| cff | 2 | 4 |
| cfo | 2 | 4 |
| cfi | 1 | 3 |
| capex | 1 | 1 |
| fcf | 1 | 1 |
| bonus_issue | 1 | 1 |
| rights_issue | 1 | 2 |

**For every non-corporate-action fact type, `COUNT(DISTINCT ticker) = 10`.**
No `cogs`, `cost_of_sales`, or `gross_profit` fact_type exists at all (full
distinct-type list confirmed by direct query: assets, bonus_issue, capex,
cff, cfi, cfo, dividend, ebit, ebitda, equity, fcf, liabilities, net_profit,
revenue, rights_issue — nothing else).

10 tickers is roughly a tenth of the 100-name IRU bar every tested hypothesis
has used. A factor test at this breadth would be a fundamentally
underpowered, non-comparable design — the same "breadth ceiling" failure
category the Phase 28 audit already identified for H-001/H-003/H-005/H-007/
H-009. Testing any of the below today would be a methodology error, not a
legitimate research step.

| Candidate | Required fact_type(s) | Coverage | Literature (for future reference) | Status |
|---|---|---|---|---|
| Value (earnings yield / book-to-market) | net_profit, equity | 10 tickers | Fama & French (1992, *JF*) | **Data-Blocked** |
| Value (cash-flow yield) | cfo, fcf | 2 tickers | Lakonishok, Shleifer & Vishny (1994, *JF*) | **Data-Blocked** |
| Quality (profitability composite) | net_profit, revenue, equity | 10 tickers | Asness, Frazzini & Pedersen (2019, *Review of Finance*, "Quality Minus Junk") | **Data-Blocked** |
| Growth (revenue/earnings acceleration) | revenue, net_profit (multi-period) | 10 tickers | La Porta (1996, *JF*, growth expectations) | **Data-Blocked** |
| Profitability (operating margin) | ebit/ebitda, revenue | 6–7 tickers | Novy-Marx (2013, *JFE*, "The Other Side of Value") | **Data-Blocked** |
| Gross Profitability | (gross_profit / revenue — fact_type does not exist) | 0 tickers | Novy-Marx (2013, *JFE*) | **Data-Blocked** (worse than others — no fact_type at all) |
| Investment (asset growth) | assets (multi-period) | 5 tickers | Cooper, Gulen & Schill (2008, *JF*, "Asset Growth and Stock Returns") | **Data-Blocked** |
| Asset Growth | assets | 5 tickers | Cooper, Gulen & Schill (2008) | **Data-Blocked** |
| Earnings Quality | net_profit vs. cfo (accrual gap) | 2 tickers (cfo) | Sloan (1996, *Accounting Review*, accruals anomaly) | **Data-Blocked** |
| Cash Flow Quality | cfo, cff, cfi | 1–2 tickers | Dechow, Sloan & Sweeney (1995) | **Data-Blocked** |
| Financial Strength | assets, liabilities, equity | 5 tickers | Piotroski (2000, *Journal of Accounting Research*, F-Score) | **Data-Blocked** — explicitly named in the directive as "buildable using existing FSI"; audit shows this framing was optimistic. The 10-ticker (5 for balance-sheet items) ceiling is the SAME root blocker as every other statement-based candidate. Not ready. |
| Accruals | net_profit, cfo | 2 tickers | Sloan (1996) | **Data-Blocked** |
| Asset Turnover | revenue, assets | 5 tickers | Soliman (2008, *Accounting Review*, DuPont decomposition) | **Data-Blocked** |

**Root cause is singular**: FSI's hand-verified extraction pipeline has only
ever processed structured financials for 10 tickers. This is a labor/OCR
coverage-expansion problem already logged in the v1.0 Owner Decision Backlog
("coverage expansion beyond 10 FSI tickers — labor-bounded, not
vendor-blocked"), not a new finding. Every candidate in this section shares
that one dependency; expanding FSI coverage would unlock all of them
simultaneously, not one at a time.

---

## C. Data-Partial — raw data exists, needs its own validation pass

### C1. Share Issuance

- **Economic rationale**: firms that issue new shares (rights issues, private
  placements) tend to subsequently underperform (a financing/market-timing
  signal); firms that reduce share count (buybacks) tend to outperform
  (Loughran & Ritter 1995, *JF*, "The New Issues Puzzle"; Pontiff & Woodgate
  2008, *JF*, share issuance and cross-section of returns).
- **Required data**: a per-event classification of corporate-action TYPE
  (rights issue vs. bonus issue vs. buyback vs. other), keyed to date and
  ticker.
- **Current coverage**: `data/staging/xissuer/corporate_actions_calendar_classified.csv`
  has broad symbol breadth — 11,546 rows, **260 distinct symbols** — well
  above the IRU bar. However, its `doc_class` field is **not** a real
  per-event-type classification: value distribution is `{'Corporate Actions':
  11439, 'Corporate Action': 104, 'CORPORATE ACTIONS': 2, 'CORPORATE ACTION':
  1}` — a generic filing-category label, not "rights issue" vs. "bonus" vs.
  "buyback." This corrects an earlier working assumption in this session
  (that broad symbol count implied usable Share-Issuance data); on inspecting
  actual column contents rather than row/symbol counts, the field does not
  support this factor as-is.
- **Testability**: NOT testable today. Would require a new classification
  pass over `submission_type`/filing text to derive real event types — this
  is exactly Wave-3's own prior (2026-07-22) assessment of Candidate C3
  ("needs its own scoping/validation pass"), now independently reconfirmed.
- **Dependencies**: an internal classification/labeling task (not an external
  vendor or data source — the raw filings already exist); scope and effort
  not yet estimated.
- **Current status**: **Data-Partial**.

---

## D. Not yet applicable — transitively blocked

### D1. Composite Factors

Requires ≥2 independently validated component factors. Currently only H-011
(Size) is Confirmed. Liquidity (A1) and Dividend payer-status (A2) are real
candidates but untested. A composite cannot be responsibly built until at
least a second component is validated — building one now would combine one
proven signal with unproven ones, which is not a composite, it is
speculation dressed as one.

**Current status**: **Proposed**, blocked pending ≥1 additional Confirmed
factor.

### D2. Interaction Factors involving blocked fundamentals

(e.g., Size × Value, Quality × Momentum) — blocked transitively by Section B;
the momentum/size/vol/liquidity side is available, but any interaction
requiring a statement-based factor inherits that factor's Data-Blocked
status.

**Current status**: **Data-Blocked** (inherits Section B's root cause).

---

## Summary table

| Family | Status | Blocker (if any) |
|---|---|---|
| Liquidity (trading-activity) | **Rejected** (H-016, 2026-08-03, both directions) | none — resolved |
| Dividend Yield (payer-status) | **Available** | none (yield-magnitude sub-variant separately blocked, already disclosed) |
| Interaction (Size×Vol/Mom/Liquidity) | **Available** | none |
| Value | Data-Blocked | FSI 10-ticker ceiling |
| Quality | Data-Blocked | FSI 10-ticker ceiling |
| Growth | Data-Blocked | FSI 10-ticker ceiling |
| Profitability | Data-Blocked | FSI 10-ticker ceiling |
| Gross Profitability | Data-Blocked | no fact_type exists at all |
| Investment / Asset Growth | Data-Blocked | FSI 10-ticker ceiling (5 for `assets`) |
| Earnings Quality | Data-Blocked | FSI 10-ticker ceiling (2 for `cfo`) |
| Cash Flow Quality | Data-Blocked | FSI 10-ticker ceiling (1–2) |
| Financial Strength | Data-Blocked | FSI 10-ticker ceiling — directive's own framing was optimistic; corrected here |
| Accruals | Data-Blocked | FSI 10-ticker ceiling |
| Asset Turnover | Data-Blocked | FSI 10-ticker ceiling |
| Share Issuance | Data-Partial | needs event-type classification pass, not new source |
| Composite Factors | Proposed / blocked | needs ≥2 validated components (only 1 exists) |
| Interaction × blocked fundamentals | Data-Blocked | inherits Section B |

**Bottom line (updated 2026-08-03)**: of 16 named candidates, the 3 that
were genuinely ready to pre-register as of this audit's original writing
(Liquidity, Dividend payer-status, Interaction factors) have now been
resolved for 2 of the 3: Interaction Factors ran as H-013/H-014/H-015
(rejected as standalone claims, per their own forensic scope) and
Liquidity ran standalone as H-016 (rejected in full, both directions —
`docs/H016_LIQUIDITY_REPORT_2026-08-03.md`). **Only Dividend payer-status
(A2) remains untested and ready.** **11 share one single root blocker**
(FSI's 10-ticker statement extraction ceiling — already a known,
disclosed, labor-bounded backlog item, not a new discovery), **1 needs an
internal classification pass** (Share Issuance), and **1 is transitively
gated** on validating a second factor first (Composite Factors).

## Methodology note on this audit itself

Auditing data availability before forming a hypothesis — rather than
hypothesizing first and discovering a data gap during backtesting — is
standard practice in empirical asset pricing (e.g. Fama & French's own
COMPUSTAT-coverage-driven scope decisions, cited above). This is not a novel
technique; it is applying an existing, well-established research discipline
to a new, small, frontier-market dataset. No claim of originality is made
for the audit method itself — the specific factual findings above (NGX's
particular data-coverage shape) are original to this platform's own
archive, not to any technique.

## Next step (Priority 2, pending owner review) — original 2026-08-02 text, superseded, kept for audit trail

Recommend pre-registering the Interaction Factors program (A3) next: it
requires no new data whatsoever (100% already-computed inputs), directly
tests whether H-011's only confirmed signal interacts with the two rejected
ones (H-007 momentum, H-008 vol) in a way neither alone revealed, and
directly answers the earlier directive's Phase 30 request. Liquidity (A1)
and Dividend payer-status (A2) remain available as parallel low-cost
candidates. No hypothesis has been pre-registered or run as part of this
audit — this document reports availability only, per Priority 1's scope.

## Status as of 2026-08-03

A3 ran as H-013/H-014/H-015 (rejected as standalone claims per their own
forensic scope — Phase R2). A1 ran standalone as H-016 (rejected in
full, both directions). **A2 (Dividend payer-status) is now the only
remaining zero-acquisition-cost, fully-available candidate from this
audit's original list** — see `docs/WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`
(named there as H-017, not yet pre-registered) for its full research-value
writeup and ranking rationale.
