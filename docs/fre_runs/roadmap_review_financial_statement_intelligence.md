# Roadmap Review — Is a Financial Statement Intelligence Phase Required Before Portfolio Reasoning?

*Assessment and proposal only. No implementation. Per instruction, this
document stops after the assessment and proposed phase design — nothing
below is built, and no code/schema/config change accompanies this pass.
Builds on `fre-architecture-baseline-2026-08-01`,
`fre3-company-memory-baseline-2026-08-01`, `fre5-company-thesis-baseline-2026-08-01`,
`fre6-valuation-architecture-baseline-2026-08-01`.*

## Question being answered

Before FRE-7 (portfolio reasoning) begins: does the current evidence layer
— everything FRE-2 through FRE-6 built (Evidence Graph, Company Memory,
Market Reaction Validation, Company Thesis, Valuation Architecture) —
provide sufficient **normalized financial data** for (1) valuation inputs,
(2) financial-quality analysis, (3) portfolio ranking, (4) risk
assessment? If not, what phase closes the gap, and what does it need?

## Method

Every claim below is re-verified directly against the real database in
this pass, not cited from memory of earlier FRE work. Confirmed just now:
`extracted_facts.fact_type` has exactly three values across all real rows
— `dividend` (158), `rights_issue` (2), `bonus_issue` (1); `numeric_value`
is populated on 104 rows, but every one of those is a corporate-action
figure (a dividend-per-share amount, a rights-issue price) — never a
revenue, EBITDA, balance-sheet, or cash-flow figure. `securities.sector_ngx`
is confirmed 0/320 populated. `docs/FACTOR_REGISTRY.md`: exactly one
validated factor exists (H-011, Size). `docs/PLATFORM_ARCHITECTURE.md`:
Ranking Engine is GATED, Portfolio Construction is GATED (both require
more validated factors than currently exist), Risk Engine is PARTIAL (a
portfolio-level version is GATED behind Portfolio Construction).

## Assessment, per downstream need

| Need | Sufficient today? | Evidence |
|---|---|---|
| **Valuation inputs** | **No** | FRE-6 verified directly: all six `ValuationMethodAdapter`s report `NOT_READY` for every real ticker, because zero revenue/EBITDA/balance-sheet/cash-flow line items exist anywhere in `extracted_facts`. This is not a coverage gap on some tickers — it is a total absence of the input class, platform-wide. |
| **Financial-quality analysis** | **No, only a shallow qualitative proxy exists** | `company_intelligence.py`'s own `UNAVAILABLE_FIELDS` already discloses "Financial Quality: no financial-statement/fundamentals dataset acquired," "Growth: no financial-statement dataset acquired (same blocker)." FRE-5's `financial_signal_summary` is real but explicitly and deliberately labeled as **not** a substitute — it derives only from `impact_assessments`' qualitative directions (`revenue=positive/negative/mixed`, no magnitude), which is evidence of *sentiment about* a financial dimension, not a measurement of it. |
| **Portfolio ranking** | **No, and independently gated regardless** | `docs/PLATFORM_ARCHITECTURE.md`'s Ranking Engine is GATED behind "a return MODEL, which requires validated factors with known expected-alpha intervals" — only 1 factor (H-011) is validated today, short of that gate's own precondition. Even if the factor-count gate opened, ranking would still need comparable per-company financial metrics (e.g., margin trend, leverage) that do not exist, so this need has **two independent blockers**, not one. |
| **Risk assessment** | **Partial — qualitative only, no quantitative basis** | Real signals exist today: `impact_assessments.execution_risk`/`regulatory_risk`/`liquidity` directions (FRE-5's `key_risks`), and FRE-4's `reaction_check()` thin-liquidity flag (a real, price-data-based risk signal). Both are genuine and evidence-grounded — but neither substitutes for quantitative risk measures (leverage ratios, interest coverage, earnings volatility) that require financial-statement data. The quant engine's own portfolio-level Risk Engine remains correctly GATED behind Portfolio Construction (module 6), unaffected by anything in the FRE program. |

**Conclusion: yes, a Financial Statement Intelligence phase is required**
before valuation, financial-quality analysis, or portfolio ranking can
move beyond today's qualitative-only ceiling. This is not a new finding —
it is the same gap `docs/fre/10_dataset_strategy.md` already named as the
single highest-leverage, highest-cost, still-unacquired dataset across the
whole FRE program, and the same blocker FRE-6 verified concretely by
running real adapters against real data and watching every one refuse.
This review's contribution is confirming, freshly and specifically, that
the gap is not just a Valuation Engine problem — it independently blocks
three of the four capabilities named in this review, for different (if
overlapping) reasons.

## Proposed phase: Financial Statement Intelligence (FSI)

### Objective

Acquire and structure a per-company, per-period financial-statements
dataset (income statement, balance sheet, cash-flow line items) sufficient
to (a) populate Part 1's `income_statement`/`balance_sheet`/`cash_flow`
ontology nodes with real values, (b) unlock at least one Valuation Engine
adapter's `is_ready()` gate for at least one real ticker, and (c) give
Company Thesis's `financial_signal_summary` a quantitative basis instead
of only qualitative `impact_assessments` directions.

### Required datasets

Directly reuses `docs/fre/10_dataset_strategy.md`'s existing, already
-scoped "Financial statements (structured line items)" row — this review
does not invent a new dataset requirement, it re-confirms the existing one
with fresh, specific evidence:

- **Primary source**: native-text NGX annual/quarterly filings already in
  the Phase A archive (7,399 native-text documents, per Phase A's own
  completion figures) — the same primary-source-first discipline as every
  extractor on this platform.
- **Cross-check source**: a commercial financial-data vendor, used
  *only* to validate the primary extraction, never as the sole source of
  truth (the same discipline already applied to price-data cross-checks
  in the quant Data Layer).
- **Blocked on**: the OCR-engine decision (open since 2026-07-16, the
  single oldest unresolved item this whole program inherits) for the
  ~36% of the archive that is scanned/OCR-pending — coverage will be
  capped at the native-text subset until this resolves, exactly as every
  other text-dependent FRE dataset already is.

### Architecture (design only, not built)

- **No new table.** `extracted_facts` is already generic enough (`fact_id`,
  `doc_id`, `fact_type`, `description`, `numeric_value`) to hold one row
  per (document, line-item) — a new `[financial_statements]` group in
  `configs/fact_taxonomy.toml` (leaves named to match Part 1's ontology
  node identifiers exactly: `revenue`, `cogs`, `gross_profit`, `opex`,
  `operating_profit`, `d_and_a`, `ebitda`, `ebit`, `interest_expense`,
  `tax`, `net_profit`, `eps`, `assets`, `liabilities`, `equity`, `cfo`,
  `capex`, `fcf`) is the only taxonomy change needed, deliberately
  1:1 with `configs/financial_ontology.toml`'s node names so extraction
  output maps directly onto the ontology with no translation layer.
- **One genuine, additive schema need, flagged but not built here**:
  `extracted_facts` has no notion of a fiscal *period* (only
  `qualification_date`/`payment_date`/`agm_date`/`closure_date`, all
  corporate-action-specific). A financial-statement line item needs
  `period_start`/`period_end` (e.g., "FY2024" or "Q3 2024") to be
  meaningful — two new nullable columns, additive, following the exact
  `ALTER TABLE ... ADD COLUMN` + `try/except OperationalError` pattern
  FRE-1 already established and tested. Not implemented in this pass, per
  instruction — named here as the one concrete schema change this future
  phase will need.
- **Extraction method**: deterministic table/regex parsing as the first
  pass (mirroring Phase B's proven dividend-extractor approach — financial
  statements in NGX filings are fairly structured tabular layouts), with
  LLM-assisted extraction as a fallback for narrative-adjacent figures,
  always routed through the existing, unmodified `grounding.py` check —
  no new grounding mechanism.
- **Validation**: cross-check against at least one independently-sourced
  anchor per sector, the same discipline already used for the GTCO/Zenith
  dividend anchors in Phase B/C.
- **Downstream wiring** (once real data exists — not built now): Part 8's
  `is_ready()` checks already look for exactly this data shape
  (`_financial_statement_line_items_exist()` in `valuation_engine.py`
  already checks `fact_type NOT IN ('dividend','rights_issue','bonus_issue')`
  — this FSI phase's output would flip that check from always-`False` to
  real, per-ticker readiness with zero change to the adapters themselves).

### Success criteria (to be pre-registered properly before execution, not invented here)

- Coverage and cross-check-accuracy numbers reported honestly, whatever
  they are — per `docs/fre/12_research_roadmap.md`'s own standing rule for
  acquisition phases ("a target coverage/accuracy bar is not pre-committed
  here — an acquisition phase's 'success' is a feasibility finding, not a
  validated result").
- At minimum, verified before declaring the phase complete: **at least one
  Valuation Engine adapter transitions from `NOT_READY` to `READY` for at
  least one real ticker**, checked the same mechanical way FRE-6 checked
  the opposite (every adapter, every real ticker, `NOT_READY`).
- A cross-check against at least one independently-verifiable real
  anchor value per sector attempted, before this phase's output is trusted
  for anything downstream.

### Dependencies

The OCR-engine decision (open, owner-level). Possibly a vendor-relationship
decision (cost, owner-level). Part 1's ontology (target node/leaf naming).
The two new `extracted_facts` columns named above (additive, FRE-1-pattern,
not yet applied). `docs/fre/08_valuation_engine_architecture.md`'s already
-built `is_ready()` gates (the consumer this phase unlocks, unmodified).

### Risks

- **Cost and OCR accuracy** — the single most expensive, highest-uncertainty
  item across the entire FRE dataset strategy (`docs/fre/10_dataset_strategy.md`
  already flagged this; restated here because this review's job is to
  confirm it's still the right next step, not to under-state its cost).
- **Sector heterogeneity** — banks, insurers, and industrials report under
  materially different line-item structures; a single extraction template
  will not work uniformly across sectors, compounding with `sector_ngx`'s
  own unpopulated state (classifying *which* template applies to which
  company has the same blocker this whole program has named repeatedly).
- **Disclosure-quality heterogeneity across NGX issuers** (Part 14's named
  risk) — some filings will yield much richer structured data than
  others, unevenly, not uniformly across the market.
- **A false sense of readiness** — a small number of tickers reaching
  `READY` should not be read as "the Valuation Engine works now"; it would
  be exactly the premature-trust risk Part 8's own design already named
  ("assumption laundering... a plausible-looking number... is not evidence
  that those assumptions are correct"), restated here because this new
  dataset is precisely what would make that risk newly live rather than
  hypothetical.

## Recommendation

Approve Financial Statement Intelligence as a distinct, dedicated,
owner-scoped phase — matching `docs/fre/12_research_roadmap.md`'s own
FRE-6 (financial-statements dataset acquisition, in that document's
original numbering) — before any further work on valuation execution,
financial-quality scoring, or portfolio ranking. Portfolio reasoning's own
**Tier 1** capabilities (watchlists, screening — `docs/fre/09_portfolio_reasoning.md`)
remain buildable independent of this gap, since they operate on already
-available qualitative research rather than financial-statement data; only
Tier 2 (ranking) and any real valuation execution are blocked on FSI.

---

*Per the standing instruction, this concludes the roadmap review. Stopping
here — no implementation performed, awaiting direction on whether to
proceed with a full pre-registration for the Financial Statement
Intelligence phase.*
