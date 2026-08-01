# FRE Part 8 — Valuation Engine Architecture

*Architecture only. No formulas, no numeric implementation, no financial
-statements dataset acquired. Modeled on `alpha_engine.py`'s existing
`ModelAdapter` pattern. See `docs/fre/00_fre_master_index.md` for standing
rules.*

## Objective

Define the **structure** — interfaces, data preconditions, method-selection
logic, output contract — for a Valuation Engine capable of DCF, Dividend
Discount, Residual Income, and Comparable Multiples (EV/EBITDA, P/E, P/B)
analysis, correctly specialized for Banks, Insurance, Holding Companies,
Growth Companies, and Turnaround Companies. No formula is written here, no
method executes, and — restated because it is easy to lose sight of — **no
method can execute today**, because every one of them requires a
financial-statements dataset this platform has not yet acquired.

## Rationale — why architecture now, execution later, is the correct order

The Reasoning Engine Specification already commits to a non-goal ("No
numeric intrinsic-value/DCF output... because the platform has not
acquired a financial-statements dataset yet") and frames building a
valuation-model output before that dataset exists as itself "inventing
alpha from nothing." This document does not relax that non-goal. It exists
because **designing the architecture now, while explicitly refusing to run
it, is different from building it now** — the same "Design → owner review →
Implementation" gate this project has applied to every other module, and
the same reasoning that let `docs/LIM_ARCHITECTURE.md` be written and
reviewed well before any GPU cycle executed.

## A critical distinction: a valuation CALCULATION is not a reasoning-engine CLAIM

This document draws a line that the existing non-goal, read literally,
could be misread as blurring: the prohibition is on the **reasoning
engine** (an LLM call) asserting a numeric intrinsic value as if it were a
grounded fact. A **deterministic valuation calculation**, run against real,
sourced, disclosed financial-statement inputs with explicit assumptions
attached, is architecturally the same *kind* of thing as the platform's
existing deterministic dividend/EPS extractors (Phase B) — a calculation,
not an inference. The Valuation Engine described here is deterministic
code, not an LLM judgment call; **its output is legitimate as a
calculation once the required inputs exist**, but — and this is the
non-negotiable part — **it is still not a validated alpha signal or a
portfolio input** until it passes through the same pre-registration/
placebo/walk-forward gauntlet as any other candidate, for exactly the
reason quant research discipline already distrusts DCF-style outputs in
general: **a DCF's output is dominated by its assumptions, and a
plausible-looking number computed from disclosed assumptions is not
evidence that those assumptions are correct.** A Valuation Engine number is
therefore always presented as a **conditional calculation** ("under these
stated assumptions, the implied value is X"), routed into the Investment
Thesis Engine (Part 7) as *directional, assumption-disclosed evidence*, and
into the Discovery-candidate pipeline like any other signal — never
directly into `alpha_engine.py`.

## Architecture: `ValuationMethodAdapter`, one per method, self-describing readiness

Directly modeled on `alpha_engine.py`'s existing `ModelAdapter` pattern
(the same interface shape `H011SizeAdapter` already implements for a
validated factor) — proven, minimal, no new abstraction invented:

```
ValuationMethodAdapter(ABC):
    method_name: str                       # "dcf" | "ddm" | "residual_income" |
                                            # "ev_ebitda" | "pe" | "pb"
    required_inputs: list[str]             # e.g. ["revenue_ts", "fcf_ts", "wacc_assumption"]
    applicable_company_types: list[str]    # see the eligibility table below

    def is_ready(self, con, ticker) -> ReadinessResult:
        # Checks whether every required_inputs field is actually populated
        # for this ticker, TODAY. Returns NOT_READY with a named reason
        # (e.g. "no financial-statements dataset") far more often than
        # READY, honestly, for as long as that remains true.

    def compute(self, con, ticker, as_of, assumptions: dict) -> ValuationResult:
        # Deterministic. Refuses to run if is_ready() is NOT_READY —
        # mirrors training.py's refusal to start on a non-gate-passing
        # dataset version (LIM-2's discipline, same shape, different domain).
```

```
ValuationResult:
    method_name: str
    point_estimate: float | None
    range_low: float | None
    range_high: float | None            # NEVER a point estimate alone — a range or
                                         # explicit sensitivity band is mandatory output shape,
                                         # mirroring this platform's bootstrap-CI discipline
                                         # applied to a deterministic calculation instead of a
                                         # statistical estimate
    assumptions_used: dict              # every assumption disclosed, never implicit
    data_vintage: str                   # as_of date of the underlying financial-statement inputs
    confidence_note: str                # method-specific caveats (e.g. DCF's terminal-value
                                         # sensitivity), mandatory, same NOT-NULL-explanation
                                         # discipline as impact_assessments.explanation
```

## Method-to-company-type eligibility (architecture, not formulas)

The owner's explicit ask — Banks, Insurance, Holding Companies, Growth
Companies, Turnaround Companies each need different applicable methods —
is enforced by a config-driven eligibility table
(`configs/valuation_method_eligibility.toml`, same pattern as every other
taxonomy on this platform), not hardcoded per-method logic:

| Company type | Eligible methods | Why (architecture rationale, not a formula) |
|---|---|---|
| **Bank** | Dividend Discount, Residual Income (excess-return-style), P/B | A bank's "revenue" and "debt" are its raw materials, not comparable line items to a non-financial DCF — EV/EBITDA is architecturally inapplicable (interest income/expense are operating, not financing, for a bank); P/B is the standard sector convention because book equity is closer to economically meaningful for a leveraged balance-sheet business |
| **Insurance** | Residual Income / embedded-value-adjacent methods, P/B | Standard DCF is a poor fit for float-driven earnings timing; this document does not invent an embedded-value formula, only reserves the method slot and flags it as needing insurance-specific actuarial inputs this platform does not currently ingest |
| **Holding Company** | Sum-of-the-parts (a composite method: value each subsidiary via its own applicable method, aggregate, apply a disclosed holdco discount) | Requires Part 2's `subsidiary_of` lineage edges to even enumerate the parts — a direct, concrete dependency on this program's own Part 2 |
| **Growth Company** | DCF (wide, explicitly disclosed sensitivity bands), revenue/EV multiples | High terminal-value sensitivity is exactly why the `ValuationResult.range_low/range_high` mandatory-range requirement matters most here — a growth-company DCF's single point estimate is close to meaningless without its band |
| **Turnaround Company** | Normalized-earnings multiples (post-stabilization only), asset-based floor value | A turnaround's trailing earnings are typically non-representative — this method family explicitly requires a `normalization_assumptions` sub-field distinguishing "as reported" from "as normalized," never silently substituting one for the other |
| **General industrial/consumer/agriculture/oil&gas/telecom/utilities/healthcare** | DCF, EV/EBITDA, P/E — the "standard" set | Sector-specific WACC/margin assumptions come from Part 1's `sector_ratio` ontology nodes once populated, not invented per-valuation-call |

`company_type` classification itself reuses `securities.sector_ngx` (Part
1/Part 2's same disclosed 0/320-populated blocker) plus a bank/insurance/
holdco override list (a small, owner-confirmable table, same "owner
-judged, never AI-inferred" discipline as the `news_outlets` registry) —
this document does not invent an automatic company-type classifier.

## Triangulation, not selection — the output contract for a company

A `ValuationEngine.value_company(ticker, as_of)` call runs **every eligible
adapter that reports READY**, not just one, and returns a
`TriangulatedValuation` object holding every method's `ValuationResult`
side by side plus an explicit disagreement note ("DCF implies X, P/B
implies Y — a Z% gap") rather than collapsing multiple methods into one
number. This mirrors the platform's own instinct never to hide disagreement
(the exact same discipline `investment_implications.contradicts_implication_id`
already applies to conflicting qualitative implications, applied here to
conflicting valuation methods) — the Investment Thesis Engine (Part 7)
consumes the *disagreement itself* as a confidence signal (wide
inter-method disagreement should *lower* `CompanyThesis.confidence`, not be
silently averaged away).

## Alternatives considered

1. **Build one universal valuation formula parametrized by company type.**
   Rejected — conflates architecturally distinct methods (a bank's excess
   -return model and a growth company's DCF do not share a formula
   skeleton) in a way that would produce a false sense of one consistent
   methodology; the adapter pattern keeps methods honestly separate.
2. **Skip the readiness-gating and let each adapter degrade gracefully with
   partial data.** Rejected for now — silent degradation ("compute
   *something* even with missing inputs") is exactly the fabrication risk
   this platform's "unknown stays unknown" discipline exists to prevent;
   an adapter either has what it needs or reports `NOT_READY` with a named
   reason, never a best-effort guess presented as a real estimate.
3. **Present a single blended "fair value" number per company (weighted
   average across methods).** Rejected — collapsing disagreement into one
   number is precisely the false-precision failure this document's
   triangulation design exists to avoid; every prior document in this
   program (bootstrap CIs, TVD, mode-collapse investigation) has treated
   "show the disagreement, don't average it away" as a hard-won
   methodological lesson, restated here for a new domain.

## Trade-offs

- Method-per-adapter is more code surface than one parametrized function,
  in exchange for each method's assumptions and failure modes staying
  legible and independently auditable — judged worthwhile given how easy
  DCF-style calculations are to get subtly, silently wrong.
- Mandatory ranges (never point estimates) are less satisfying to read but
  directly prevent the single most common valuation-model misuse pattern
  (treating a DCF's point output as if it were precise).

## Risks

- **Assumption laundering**: a `ValuationResult.assumptions_used` dict
  that is technically populated but effectively a rubber stamp (e.g., a
  WACC assumption copied unchanged from a generic default rather than
  company-specific) would defeat the whole disclosure design while
  appearing compliant. Mitigation direction (not solved here): assumptions
  sourced from Part 1's ontology's `evidence_status` should themselves
  carry a provenance tag distinguishing "company-specific, evidenced" from
  "sector-default, unverified" — flagged for the eventual implementation
  phase, not resolved architecturally here.
- **Sum-of-the-parts double-counting** for holding companies if Part 2's
  subsidiary lineage is incomplete or a subsidiary is also independently
  listed — a real, disclosed risk inherited directly from Part 2's own
  lineage-accuracy caveats.
- **Premature trust in a "calculation" framing.** Restating the core
  distinction as an explicit risk: even though this document argues a
  Valuation Engine output is architecturally a calculation rather than an
  LLM inference, a consumer who is not reading this document carefully
  could still treat a computed DCF number as if it were validated alpha.
  The mandatory routing through the Discovery-candidate pipeline (never
  direct-to-`alpha_engine.py`) is the actual enforcement mechanism, not the
  framing alone — restated here because this is the most likely single
  point of governance erosion in the entire FRE design if implemented
  carelessly.

## Future extensions

- Sector-specific WACC/discount-rate ontology nodes (Part 1), once
  populated, replace any placeholder default assumptions.
- A per-method historical-accuracy retrospective (did this method's implied
  direction, historically, precede realized price convergence) — itself a
  future hypothesis candidate, not asserted informally.

## Dependencies

- A financial-statements dataset (not yet acquired — the single hard
  blocker on every method's `is_ready()` today; this is the same
  dependency named throughout Parts 1, 3, 5, and 7).
- Part 1 (sector-conditioned assumption inputs), Part 2 (holding-company
  subsidiary lineage). `securities.sector_ngx` population. The existing
  `alpha_engine.py`/`ModelAdapter` pattern (reused for interface shape
  only — this engine's outputs never flow into that module directly, per
  the hard-boundary restatement above).
