# FRE-7 Valuation Engine v0 — Activation Report

**Date**: 2026-08-09
**Authorization**: Owner-authorized activation of `src/ngxrot/fre/valuation_engine.py`'s
`compute()` methods, explicitly scoped to: preserve the frozen quant research track
(hypothesis registry, `alpha_engine.py`, `runner.py`, `phase4.py`) and the existing
accounting core (`financial_ratios.py`, `pit_financial_memory.py`,
`period_normalization.py`, `restatement_detection.py`, `confidence_propagation.py`)
completely unmodified; never fabricate a missing input (explicit `UNKNOWN`/`DATA_GAP`
instead); test everything; report honestly; apply the FRE-7 roadmap gate exactly as
written, with no silent weakening.

**Bottom line: FRE-7's own pilot-validation gate FAILS on real data (2/7 = 29% bracket
rate, majority required). Per the explicit governance instruction, this report STOPS
here — no automatic advance to a further Investment OS stage.**

---

## 1. What was inspected before any code was written

Per the explicit instruction to inspect before implementing, the following was checked
against the real, live `data/ngx.sqlite` database (not assumed from documentation):

- **Full `extracted_facts.fact_type` inventory**: `dividend`, `rights_issue`,
  `bonus_issue`, `share_reconstruction`, `assets`, `equity`, `liabilities`,
  `net_profit`, `revenue`, `ebit`, `ebitda`, `cfo`, `gross_profit`, `cogs`, `cff`,
  `capex`, `cfi`, `fcf`. No `debt`/`total_debt`/`cash`/`cash_and_equivalents` concept
  has ever been extracted — confirmed directly, not assumed.
- **FCF availability**: a live query confirmed **zero** tickers, ever, have a `cfo`
  and a `capex` fact sharing the exact same `(period_start, period_end)` — a
  CFO-minus-CapEx derivation yields nothing on real data. Only **3** direct `fcf`
  facts exist platform-wide: CAP (NGN, complete period, `direct_reported`), GEREGU
  (NGN, `period_start=NULL`, `derived`), AIRTELAFRI (USD, `derived`).
- **`fx_rates` table**: 0 rows, platform-wide, confirmed by direct query — no currency
  conversion is possible without fabricating a rate.
- **Currency completeness**: many `equity`/`net_profit` facts (pre-MC-001 legacy rows)
  carry `currency=NULL`; these are excluded by the same currency guard
  `financial_ratios.py` already uses, re-implemented locally (not imported — the
  accounting core's private functions were not reached into).
- **Shares-outstanding coverage**: all 26 real fact-bearing tickers have at least one
  row in `data/reference/market_cap_panel.csv` (`implied_shares_m`), the platform's
  existing, previously-validated shares proxy — confirmed directly.
- **WACC / cost-of-equity source**: no config anywhere on the platform supplies a
  discount-rate assumption. Confirmed by directory listing of `configs/` — only
  unrelated NGX-rotation cost-sensitivity configs exist. This is why `dcf` requires
  the *caller* to supply `wacc`/`terminal_growth` explicitly; nothing is defaulted.
- **Peer-grouping data**: `classify_company_type()` (existing, unmodified) resolves
  19 of the 26 real tickers to `"general"`, 5 to `"insurance"`, 2 to `"holding_company"`,
  0 to `"bank"` among fact-bearing tickers. `"general"` is a coarse, sector-agnostic
  bucket (industrial goods, consumer goods, oil & gas, ICT, and conglomerates are all
  lumped together) — this is the only peer-grouping axis the existing architecture
  provides, and its coarseness turned out to matter (see §5).

## 2. What was implemented

All changes are confined to `src/ngxrot/fre/valuation_engine.py` and
`scripts/fre/test_valuation_engine.py`. No file in the accounting core, the frozen
quant research track, or the thesis/reasoning layer (`company_thesis.py`,
`evidence_graph.py`, `company_memory.py`, `reaction_check.py`) was touched. The
module's own isolation self-test (no import of those four modules) still passes.

| Deliverable | Status |
|---|---|
| Normalized financial statements | **Implemented** — `get_normalized_statement()`: per ticker/as-of-date, the most recent knowable FY period's flow items (revenue, net_profit, ebit, ebitda, cfo/cfi/cff, capex, fcf, gross_profit, cogs) plus the latest knowable balance-sheet snapshot (assets, liabilities, equity). Every line item is `'known'` (with a real `fact_id`) or an explicit `'DATA_GAP'` — never inferred. |
| Revenue/earnings/FCF metrics | Covered by the normalized statement above and by the P/E and DCF adapters' EPS/FCF extraction. |
| DCF | **Implemented**, narrowly — single-period Gordon Growth perpetuity (not a multi-year projection: the data does not support one). Requires the caller to explicitly supply `wacc`/`terminal_growth`; refuses (`DATA_GAP`) otherwise. Ready for exactly 3 tickers (CAP, GEREGU, AIRTELAFRI have direct `fcf` facts); AIRTELAFRI's is excluded at `compute()` time by the currency guard (USD, no `fx_rates`). |
| Trading comparables | **Implemented** for P/E and P/B — peer set = same `company_type` via the existing `classify_company_type()`, excluding self, requiring ≥2 peers with a computable positive multiple. |
| Valuation multiples | P/E and P/B implemented; **EV/EBITDA permanently gated NOT_READY** for every ticker — no debt/cash fact_type has ever been extracted, and fabricating a proxy was explicitly forbidden. |
| Scenario/sensitivity analysis | DCF: bear/base/bull via a fixed, disclosed ±1.5pp WACC / ±0.5pp terminal-growth band. P/E and P/B: bear/base/bull = peer 25th/50th/75th percentile multiples. |
| Intrinsic-value range | Every `ValuationResult` carries mandatory `range_low`/`range_high` (never a bare point estimate); `TriangulatedValuation.intrinsic_value_range` aggregates across all numeric methods for a ticker. |
| Valuation confidence | `TriangulatedValuation.valuation_confidence` ∈ `{no_data, single_method, low, medium, high}` — a disclosed heuristic based on numeric-method count and cross-method spread, not a statistical measure. |
| Full source/provenance lineage | `ValuationResult.input_fact_ids` (real `fact_id`s), `.peers_used` (real tickers), `.data_vintage` (real period/filing dates) on every result. |

`DDMAdapter`/`ResidualIncomeAdapter` were left **untouched** — still correctly gated
on the missing cost-of-equity ontology, as before.

## 3. Tests executed and results

### 3a. `scripts/fre/test_valuation_engine.py` (rewritten/extended for FRE-7)

**78/78 checks passed.** New coverage added: real P/E numeric outcomes with
provenance and peer disclosure (UCAP, BUAFOODS, NASCON, CAP), correct DATA_GAP for
AFRIPRUD/CILEASING (pe), CAP's DCF end-to-end (refuses with no assumptions, computes
with them, refuses again on `wacc <= terminal_growth`), AIRTELAFRI's currency-guard
refusal, `get_normalized_statement()` on both a data-rich (CAP) and data-empty
(TOTAL) ticker, LASACO's honest insufficient-peer DATA_GAP for P/B, the new
`intrinsic_value_range`/`valuation_confidence` fields, and a restated import-isolation
check confirming the only two new imports are the *public* `financial_ratios.list_tickers`
and `period_normalization.classify_period_type` — no accounting-core internals reached
into.

### 3b. Full FRE suite (35 other test scripts)

497/514 checks passed (96.7%) across 34 of the 36 scripts. Two scripts
(`test_generate_portfolio_context_dossier.py`, `test_portfolio_memory.py`) did not
finish within the time available in this run; `test_company_portfolio_context.py`
(a different script) completed cleanly at 18/18 on an earlier full pass. **All
17 pre-existing failures, across 10 scripts, were independently confirmed to be
unrelated to this work** — grepped directly for `valuation_engine` imports in each
failing file: none found. These are stale-count/content-drift assertions in
unrelated modules (`evidence_graph.py`, `entity_context.py`, `financial_ratios.py`'s
own test, `phase9_knowledge_graph.py`, dossier/watchlist vocabulary checks, etc.) —
the same "update, don't leave stale" pattern this codebase's own test-file comment
history already documents repeatedly (e.g. `test_valuation_engine.py`'s own
137→292 fact-count updates). Per this task's explicit scope boundary, none of these
unrelated failures were touched or fixed.

Zero database writes occurred in any test run (verified: production
`documents` row count unchanged before/after; `test_valuation_engine.py`'s own
integrity/foreign-key checks pass).

## 4. Companies that can currently be valued (as of 2026-08-09)

| Ticker | Method(s) with a real number | Notes |
|---|---|---|
| CAP | pe (15.9x, real), dcf (requires caller wacc/g) | Only ticker with both pe and dcf available |
| BUAFOODS | pe (176x) | |
| NASCON | pe (143x) | |
| OANDO | pe (83x) | |
| UBN | pe (21x) | |
| UCAP | pe (25x) | |
| GEREGU | dcf (requires caller wacc/g) | pe blocked — no NGN net_profit/shares match |

**19 of the 26 real tickers currently produce zero numeric valuation** (explicit
DATA_GAP, not silence) — most commonly because fewer than 2 real comparable peers
have a computable positive multiple, or because no currency-clean net_profit/equity
fact exists as of the query date. `LASACO` (the one insurance ticker with usable book
equity) correctly reports a P/B DATA_GAP: it has zero comparable insurance peers with
their own usable book equity.

## 5. The FRE-7 gate: pilot validation, and why this report stops here

The FRE-7 roadmap entry's own literal success criterion
(`docs/fre/12_research_roadmap.md`, row FRE-7): *"Pilot triangulated ranges bracket
the independent reference value in a majority of pilot cases, with disagreement-width
reported, not hidden."*

Using each ticker's real, independently-observed NGX closing price as the reference
value (the most natural real, non-fabricated reference available — not itself a
"valuation," but a genuine external check on whether these multiples are in the right
neighborhood), the 7 real numeric results as of 2026-08-09 were checked directly:

| Ticker | Method | Point est. | Range | Reference (market close) | Brackets? |
|---|---|---|---|---|---|
| UCAP | pe | 24.58 | [10.61, 86.51] | 18.00 | **Yes** |
| NASCON | pe | 142.82 | [84.20, 686.46] | 195.00 | **Yes** |
| BUAFOODS | pe | 175.83 | [103.66, 240.07] | 845.10 | No |
| CAP | pe | 15.87 | [9.35, 21.66] | 115.45 | No |
| OANDO | pe | 82.80 | [60.64, 291.46] | 35.75 | No |
| UBN | pe | 21.16 | [15.50, 74.48] | 6.65 | No |
| CAP | dcf (wacc=0.22, g=0.06, illustrative) | 8.33 | [7.37, 9.57] | 115.45 | No |

**Result: 2/7 pilot cases (29%) bracket the independent reference value — a minority,
not the required majority. The gate fails.**

This is disclosed exactly as observed, not adjusted. Per the explicit governance
instruction ("never silently skip a gate or weaken a requirement to obtain a pass"),
no parameter was retuned and no peer set was hand-picked to flip this result — that
would itself be the forbidden "assumption laundering" the FRE-7 design doc already
named as a risk. The disagreement width is reported above, not hidden.

**This is a real, legitimate finding, not a code defect**: this platform's only
peer-grouping axis (`company_type`) is coarse — `"general"` spans industrial goods,
consumer goods, oil & gas, ICT, and conglomerates in one bucket. A peer P/E built from
an oil & gas major and a food conglomerate is not a meaningful comparable set for a
paints company (CAP) or a bank-adjacent lender (UBN). The roadmap's own risk column
anticipated exactly this: *"Genuinely open — this is the first real test of whether
the sector-eligibility table and assumption-disclosure design actually produce sane
output."* It did not.

Per the roadmap's own stage rule (*"Systematic bracket failure... halts rollout for
redesign, not silent parameter tweaking"*) and the owner's explicit instruction (*"fix
only what is permitted by the stage rules, retest, and report"*), the only legitimate
fix available at this stage is a genuine architectural one (finer-grained,
sector-level peer comparables, not a same-`company_type` bucket) — not something this
task's scope authorizes implementing unilaterally, since it touches the
peer-eligibility design the owner would need to re-approve. **This report stops here.
No automatic advance to a further Investment OS stage occurs.**

## 6. Data gaps (explicit, disclosed, not fabricated around)

- **EV/EBITDA**: permanently blocked for every ticker — no `debt`/`cash` fact_type
  has ever been extracted.
- **DCF**: only 2 tickers (CAP, GEREGU) have a usable FCF input at all; the formula
  itself is a single-period perpetuity, not a real multi-year projection, because no
  ticker has a real multi-year FCF time series.
- **DDM / Residual Income**: still blocked platform-wide on a missing cost-of-equity
  ontology (unchanged from FRE-6's architecture-only state).
- **P/E and P/B**: blocked for the majority of real tickers by either insufficient
  comparable peers (<2 with a computable positive multiple) or a missing/non-NGN
  currency match.
- **`sum_of_the_parts`** (TRANSCORP, UACN's only eligible method): still has no
  adapter implementation at all — correctly disclosed as such by `value_company()`,
  unchanged; out of scope for this task (needs subsidiary-lineage data that does not
  exist).

## 7. Architectural weaknesses surfaced by this activation

1. **Peer-grouping granularity is the binding constraint**, not data volume — the
   §5 finding shows the gate fails even where real numeric multiples exist, because
   the comparable set is too heterogeneous. A future stage should build a genuine
   sector-level (not company-type-level) comparable-set mechanism before re-attempting
   the pilot.
2. **`market_cap_panel.csv` is a silent single point of failure** for every per-share
   calculation (P/E, P/B, DCF) — it is read-only and previously validated, but no
   FRE module currently checks it for staleness at the point of use; a future stage
   should add an explicit vintage/staleness disclosure for this input specifically.
3. **The "independent reference value" used for this pilot (market close price) is
   itself a market efficiency assumption**, not a professionally-produced independent
   valuation — a more rigorous FRE-7 re-attempt would use analyst price targets or a
   cross-listed comparable's own multiple, neither of which exists on this platform
   today.
4. **`TriangulatedValuation.disagreement_note`/`valuation_confidence` are per-ticker
   heuristics**, not calibrated against any historical outcome — they should not be
   read as validated confidence scores until FRE-10's evaluation framework exists.

## 8. Recommended next Investment OS stage

**Not FRE-8/FRE-9 as originally sequenced.** Given the gate failure's specific,
diagnosed cause (§5, §7.1), the recommended next step is a narrowly-scoped
**peer-grouping redesign** for the comparables methods specifically (sector-level,
not company-type-level, comparable-set construction), followed by a **re-run of
this exact same pilot** — not a larger one, not a different one — before FRE-7 is
considered passed. This keeps the gate meaningful rather than moving past it on a
technicality. This recommendation, and any implementation of it, requires the
owner's separate authorization per this stage's own governance rule.

## 9. Explicit scope confirmations

- No new trading hypothesis was registered.
- No backtest was run.
- No missing financial input was fabricated or defaulted — every gap in this report
  is a real, disclosed `DATA_GAP`/`None`, traceable to a specific missing fact,
  currency mismatch, or insufficient peer count.
- `financial_ratios.py`, `pit_financial_memory.py`, `period_normalization.py`,
  `restatement_detection.py`, `confidence_propagation.py`, the hypothesis
  registry, `alpha_engine.py`, `runner.py`, and `phase4.py` were not modified.
- `valuation_engine.py` still imports nothing from, and is imported by nothing in,
  `company_thesis.py`/`evidence_graph.py`/`company_memory.py`/`reaction_check.py`.
