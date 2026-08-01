# FRE Part 3 — Evidence Graph

*Design only. Reuses `evidence`/`extracted_facts`/`causal_chain_steps`/
`impact_assessments`/`investment_implications` (Reasoning Engine
Specification, unchanged) rather than adding parallel tables. See
`docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Operationalize the owner's exact evidence-to-decision chain — **Evidence →
Observation → Financial implication → Business implication → Competitive
implication → Valuation implication → Investment implication → Confidence →
Missing evidence** — for every major section of an NGX financial
disclosure, as a concrete instantiation of the existing 14-step reasoning
chain rather than a new pipeline. This document answers "which existing
table holds each of the owner's nine stages, and what does a real worked
example look like per statement type."

## Rationale — nine stages map onto five existing tables plus one new tag

The owner's nine-stage chain is not a new information architecture; it is a
**finer-grained narrative label** for stages the reasoning spec's schema
already stores, mostly inside `causal_chain_steps`' `step_order` sequence
and `investment_implications`' fields. Building five new tables for nine
narrative stages would violate this platform's repeated "extend, don't
duplicate" discipline (the exact framing Phase E's completion report used
to justify its own four additive modules). The mapping:

| Owner's stage | Existing table / field | New addition needed |
|---|---|---|
| **Evidence** | `evidence` (quoted_text, page_number, char_start/end, source_confidence) | none |
| **Observation** | `extracted_facts` (fact_type, description, extraction_confidence) — Step 2 | none |
| **Financial implication** | `causal_chain_steps`, `step_order` 0-1, plus `impact_assessments` rows for the `revenue`/`margins`/`cash_flow`/`balance_sheet` categories | a new `implication_layer` column on `causal_chain_steps` (see below) |
| **Business implication** | `causal_chain_steps`, `step_order` 2+, plus `impact_assessments` for `capital_allocation`/`growth`/`execution_risk` | same column, value `business` |
| **Competitive implication** | `causal_chain_steps` + `impact_assessments.competitive_advantage`/`long_term_moat`, plus `effect_chains` (peer propagation, Part 2's `competitor_of` edges) | same column, value `competitive` |
| **Valuation implication** | `investment_implications.intrinsic_value_direction`/`intrinsic_value_reasoning`/`target_multiple_direction` | none — already a dedicated field group |
| **Investment implication** | `investment_implications.action_recommendation`/`bull_case_delta`/`bear_case_delta`/`base_case_delta` | none |
| **Confidence** | `investment_implications.confidence` + `confidence_rationale` (already `NOT NULL`) | none |
| **Missing evidence** | `research_task_candidates` + `coverage_assessment.py`'s 10-dimension checklist (built in the 2026-07-27 stabilization pass) | none — already exists and already runs |

**The one real addition**: `causal_chain_steps.implication_layer TEXT CHECK
(implication_layer IN ('financial','business','competitive'))` — an
additive column letting a single fact's causal chain be read back *segmented
by the owner's own layer names*, instead of as one undifferentiated
`step_order` sequence. This is a small, precise schema change, not a new
architecture — and it directly strengthens the self-critique gate's
existing `ignored_alternative_explanation` and `unevidenced_inference`
checks, since a chain that jumps straight from `financial` to `competitive`
with no `business` link in between is now a **queryable, mechanically
detectable gap** (`SELECT fact_id FROM causal_chain_steps GROUP BY fact_id
HAVING COUNT(DISTINCT implication_layer) < 3` flags every under-reasoned
chain), not something a reviewer has to notice by reading prose.

## Worked examples per major statement section

Each row shows what evidence realistically exists **today** on this
platform (native-text NGX filings, no financial-statements dataset yet)
versus what remains blocked, disclosed honestly rather than glossed over.

| Statement section | Evidence (real, extractable today) | Observation | Financial impl. | Business impl. | Competitive impl. | Valuation impl. | Investment impl. | Missing evidence (typical) |
|---|---|---|---|---|---|---|---|---|
| **Income Statement** | "Revenue grew from ₦X to ₦Y" (a filing sentence, native-text) | `extracted_facts`: revenue growth fact | `impact_assessments.revenue = positive` | Growth implies either volume, price, or new-market expansion — filing rarely says which | Only competitive if peers' growth is also known (needs peer filings, often blocked by the same OCR gap) | Needs a margin trend and a multiple — blocked without the financial-statements dataset (numbers-only filings are mostly scanned, per Phase A's OCR finding) | `action_recommendation='research_task'` typically, pending the valuation blocker | "What drove the growth (price vs. volume)?" — `research_task_candidates` row |
| **Balance Sheet** | "Total debt increased to ₦X" | `extracted_facts`: debt-level fact | `impact_assessments.balance_sheet = negative` (leverage up) | Debt-funded capex vs. debt-funded distress are opposite business stories — filing context (capex line vs. going-concern language) usually disambiguates | Peer leverage comparison, same blocker as above | `risk_profile_direction` — increases without a stated use-of-proceeds | Often `watchlist`, rarely `immediate_review` on a single filing (per the self-critique gate's `single_document_overreaction` check) | "What is the debt for?" |
| **Cash Flow Statement** | "Operating cash flow was ₦X vs. Net profit ₦Y" | `extracted_facts`: CFO-vs-NI divergence fact | `impact_assessments.cash_flow` — divergence flagged `mixed` pending explanation | A large NI-CFO gap is a classic quality-of-earnings flag — Financial Reasoning Engine's own §4.5 scope ("hidden positives/negatives," "one-off vs. recurring") | Rarely competitive on its own | Quality-of-earnings concerns should *lower* confidence in any multiple-based valuation implication, not silently pass through | Correctly triggers a stricter self-critique review — this is exactly the `insufficient_information`/`unevidenced_inference` pattern the gate exists to catch | "Reconcile the NI-CFO gap" |
| **Statement of Changes in Equity** | Dividend/buyback/rights-issue lines | `extracted_facts`: corporate-action fact (already a working deterministic extractor, Phase B) | `impact_assessments.capital_allocation` | Capital-allocation *pattern* over multiple periods (Part 5's Company Memory) is the real signal — a single period is weak evidence | n/a | `portfolio_sizing_note` (qualitative only, per the spec's non-goals) | Usually `no_action`/`watchlist` on a single instance | "How does this compare to the company's 5-year capital-allocation pattern?" — directly depends on Part 5 |
| **Notes to the Financial Statements** | Contingent liabilities, related-party transactions, segment breakdowns (when native-text) | `extracted_facts`: contingency/related-party fact | `impact_assessments.execution_risk`/`regulatory_risk` | Related-party transactions intersect Part 2's ownership graph (`major_shareholder_of`) — a genuinely cross-cutting evidence type | If a related party is also a disclosed competitor, this is a real governance flag | n/a directly, but should discount confidence on any adjacent valuation claim | Typically `flagged_for_human_review`-adjacent | "Resolve the related-party counterparty's identity" — feeds Part 2's entity-resolution queue |
| **Chairman's/MD's Statement (narrative)** | Forward-looking qualitative language ("we expect continued growth in...") | `extracted_facts` with a lower `extraction_confidence` (qualitative claims are inherently softer than a numeric line item) | Weakest financial-implication evidence class on this list — forward guidance is not a fact, it is a claim about the future | Business-implication reasoning here must explicitly flag "management's own framing," never launder guidance as verified fact | n/a typically | `intrinsic_value_reasoning` must state that this is management's own claim, not independently verified | Confidence capped low by construction | "Cross-reference against realized results from prior guidance" — a Company Memory (Part 5) query, not a new extraction |
| **Auditor's Report** | Qualified opinion / going-concern paragraph (rare, high-signal when present) | `extracted_facts`: audit-opinion fact | `impact_assessments.balance_sheet`/`liquidity` — auto-escalates | Going-concern language should mechanically force `action_recommendation='immediate_review'`, not leave it to model judgment | n/a | Any valuation implication under a going-concern qualification should be capped at low confidence — a mechanical rule, not a prompted preference | `immediate_review`, mechanically forced | Rare — an auditor's qualification is itself unusually complete evidence |

## Alternatives considered

1. **A dedicated `evidence_graph` table replicating the nine stages as nine
   columns/rows per fact.** Rejected — duplicates data already captured by
   `causal_chain_steps`/`impact_assessments`/`investment_implications`,
   creating exactly the "two sources of truth that can silently disagree"
   risk this platform's `db.py`/`event_pipeline.py` conventions are built
   to avoid. The one-column addition (`implication_layer`) achieves the
   same narrative segmentation without a parallel structure.
2. **Treat "Missing evidence" as a new concept requiring a new mechanism.**
   Rejected — `research_task_candidates` and `coverage_assessment.py`'s
   10-dimension checklist (already built, already running against real
   NGX filings as of the 2026-07-27 stabilization pass, coverage scores
   0.5-0.6 across 12 real tickers) already are this. This document cites
   them, it does not reinvent them.
3. **A single, undifferentiated "implication" free-text field instead of
   layered stages.** Rejected as exactly the vague-conclusion failure mode
   the reasoning spec's mechanical anti-vagueness checks (§11) already
   exist to prevent — layering the implication forces each layer's
   reasoning to be stated and separately evidenced, which is the entire
   point of the owner's nine-stage design.

## Trade-offs

- Segmenting `causal_chain_steps` by `implication_layer` adds one more
  mandatory field per step, meaning one more thing a reasoning call can get
  "wrong" (mis-tag a step's layer) — mitigated by making mis-tagging a
  low-cost, easily-correctable metadata error (it doesn't change the
  underlying evidence or reasoning text, only its narrative bucket), unlike
  a wrong `direction`/`confidence` value.
- The "financial → business → competitive" layering is a genuine ordering
  discipline (each layer should build on the one before it), but not every
  fact has all three layers available — a filing rarely gives enough
  information to reach a competitive implication. **This is expected, not a
  gap to force-fill**: an incomplete layer chain with an honest
  `research_task_candidates` row explaining *why* it stops there is a
  correct outcome, mirroring the platform's "unknown stays unknown"
  discipline (architecture doc §11).

## Risks

- **Layer-skipping under time/token pressure** — a reasoning call under
  token budget constraints could be tempted to jump straight from Observation
  to Investment implication, skipping the middle layers' discipline. The
  `HAVING COUNT(DISTINCT implication_layer) < 3` mechanical check (above)
  exists specifically to catch this without relying on the model to
  self-report completeness.
- **Narrative-only sections (Chairman's Statement) risk being over-weighted**
  relative to their actual evidentiary value if a reasoning call doesn't
  correctly discount guidance-vs-fact — this is why the table above
  explicitly caps confidence for that row; making this a mechanical rule
  (a fixed confidence ceiling for `extracted_facts` sourced from a
  `doc_type` tagged as narrative/guidance) is a concrete candidate for
  `grounding.py`'s existing mechanical-check family, not a new module.
- **Going-concern / audit-qualification auto-escalation is high-stakes and
  currently proposed as a hardcoded mechanical rule** (not a model
  judgment) — deliberately, because this is exactly the class of
  bright-line signal where a mechanical floor is safer than trusting a
  probabilistic model call every time; but a hardcoded rule can also be
  wrong if a filing's language is ambiguous (a "material uncertainty"
  paragraph short of a full qualification) — flagged as a genuine edge
  case requiring careful wording in the eventual detection prompt/regex,
  not resolved here.

## Future extensions

- A **layer-completeness score** per implication (0-3, how many of the
  three implication layers are populated) as a queryable Company
  Intelligence field — "how well-reasoned is this conclusion," distinct
  from `confidence` (which measures uncertainty *within* the reasoning
  produced, not how much reasoning was attempted).
- Segment-level evidence graphs (a multi-segment company's Notes disclosure
  could support a per-segment financial→business→competitive chain,
  separate from the company-level one) — deferred until segment-reporting
  extraction is itself a validated capability.

## Dependencies

- `causal_chain_steps` (existing, unchanged except the one additive
  column), `impact_assessments`, `investment_implications`,
  `research_task_candidates`, `coverage_assessment.py` (all existing,
  built and tested as of the 2026-07-27 stabilization pass).
- A financial-statements dataset for any Valuation-implication row that
  needs a real multiple or margin trend, not just a direction — same
  disclosed blocker as Part 1 and the Reasoning Engine Specification's
  §13 non-goals.
- Part 1's ontology for the *mechanism* text inside each layer's causal
  step (this document defines *where* the reasoning is stored; Part 1
  defines *what mechanisms are permitted to be cited* inside it).
- Part 5's Company Memory for any "compare to historical pattern" missing
  -evidence resolution (flagged in the Statement of Changes in Equity and
  Chairman's Statement rows above) — a cross-reference, not a blocking
  dependency, since the missing-evidence task can be logged today and
  resolved once Part 5 exists.
