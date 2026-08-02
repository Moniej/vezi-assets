# FSI Phase 7 — Deterministic Financial Reasoning Research Report (Pre-registration)

*Design only. No implementation, no schema change, no new fact type, no
new document, no LLM call, no valuation output, no alpha claim, no
portfolio ranking/allocation, no scoring, no buy/sell output, no
unsupported conclusion. Per instruction, written and frozen BEFORE any
execution begins. Builds on `fsi-phase6-baseline-2026-08-01` and
modifies nothing in Phases 1-6 — all six remain frozen, touched only for
future bug fixes.*

## 1. Review of the entire completed FRE and FSI architecture

**FRE track** (document-narrative reasoning, LLM-dependent where it
touches real inference): FRE-1 (schema/ontology foundation, additive) →
FRE-2 (Evidence Graph, mechanical classifier over existing causal
chains) → FRE-3 (`CompanyMemory.as_of()` — dividend/event/filing
history, PIT-safe, mechanical) → FRE-4 (reaction-check, mechanical) →
FRE-5 (`CompanyThesis` folding, pilot-scoped, LLM-derived deltas folded
mechanically) → FRE-6 (Valuation Engine architecture — scaffolding only,
`compute()` unconditionally refuses to run). All frozen.

**FSI track** (financial-statement facts and mechanical reasoning, zero
LLM calls anywhere): Phase 1 (pilot revenue/net_profit extraction, 30
facts) → Phase 2 (balance sheet/cash flow/EBITDA-EBIT, 76 more facts,
106 total) → Phase 3 (ratios/trends/flags, 177 conclusions) → Phase 4
(`pit_financial_memory.as_of()`, PIT-safe read access) → Phase 5
(regression/consistency validation harness, 0 deviations) → Phase 6
(`CompanyMemory360.as_of()`, unified read layer, 0 discrepancies vs.
both source modules). All frozen; 106 facts, 177 conclusions, 5 tickers.

**The concrete state this review finds**: six phases of engineering
discipline have produced a fully mechanical, fully auditable, fully
PIT-safe body of financial reasoning — but every one of its outputs is
consumable only as a Python dataclass, reached only by writing code and
calling a function directly. There is no artifact a human researcher can
open, read, and cite without first inspecting `KnowableConclusion`,
`SourceFactPIT`, and `CompanyMemory` object internals in a Python shell.
Six phases of correctness work has produced a correct engine with no
readable output.

## 2. Remaining capability gaps, ranked

| Gap | What it would add | Why it's not proposed here |
|---|---|---|
| **Human-readable research output** (proposed below) | Turns the existing, validated `CompanyMemory360` snapshot into a citable, structured document a researcher can actually read | — |
| Reasoning-mode rollout (FRE-8) | Tags/enforces `causal_chain_steps.reasoning_mode` in the LLM-based FRE track | Requires an LLM vendor/cost decision not resolved by this document; raises unsupported-inference risk the FSI track has deliberately avoided end to end |
| Cross-document/multi-source reasoning (Part 6) | A `news_outlets` registry, multi-source corroboration | Requires a new external data-source decision, owner-level, not an engineering design choice |
| Typed knowledge-graph relations (Part 2) | Genuinely typed `entity_relationships.relation_type` | Orthogonal to financial-statement reasoning; would not build on anything FSI Phase 1-6 produced |
| Extending Phase 3's rule set (more ratios/flags) | Current ratio, ROE, ROA, etc. | Incremental (more of the same capability), not a new one; Phase 3 is frozen; already rejected as Phase 5's and implicitly Phase 6's own scope |
| Scaling extraction to more tickers/filings | More breadth of coverage | A real, legitimate future need — but a DIFFERENT kind of gap (data volume, not capability) requiring manual filing-reading effort at the same intensity as Phase 1/2, not a design-only next step; and every one of Phase 1-6's outputs would still be unreadable by a human even with more of them |

**Why the human-readable research output ranks highest**: every other
row in this table either (a) requires an owner-level decision this
document cannot make (an LLM vendor, a new data source), (b) is
excluded by the standing constraints (ranking/scoring/comparison), or
(c) adds more of an existing capability rather than closing a real,
present gap. The reporting gap is unique: it requires no new decision,
no new data, no LLM call, and no rule-set change — it only requires
formatting what already exists, correctly and completely, into a form a
researcher can use. It is also the only gap that changes who can use
this system: today, only someone who can read the Python source and
query the database can use six phases of work; a deterministic report
changes that to any analyst.

## 3. Objective

Build a **deterministic, template-based Financial Reasoning Research
Report generator** — a pure function that takes a `CompanyMemory360`
snapshot (Phase 6) and renders it into a structured, human-readable
document (Markdown) with every claim traceable to its own source
fact(s), confidence tier, and limitations, exactly as already stored —
adding no new claim, no new number, no new inference, and no synthesized
verdict of any kind.

## 4. Research question

Can the full richness of what Phases 1-6 already validated — provenance,
confidence tiers (including the `NULL`-tier legacy-fact signal),
per-metric limitations, PIT cutoff — survive being rendered into
readable prose/markdown without any of it being lost, simplified away,
or silently reinterpreted as something stronger than what the data
supports?

## 5. Hypothesis

A template-based (not LLM-based) renderer can preserve 100% of this
information by construction, because it never generates new text from a
model — it only substitutes already-existing field values into a fixed
template structure. Genuinely open: it is not yet verified whether a
purely template-based rendering can present `insufficient_data`
findings, `NULL`-tier conclusions, and mismatched-period-span trends
in a way that is actually READABLE (not just technically present) —
this phase's own evaluation will test that directly, not assume a
template automatically produces good prose.

## 6. Architectural rationale

This is deliberately the **inverse** of the deferred "optional narrative
reasoning layer" named in Phase 3's own Area 4 and repeatedly flagged
since as a future, separately-gated, LLM-based capability: that layer
would GENERATE new explanatory text via inference ("why did this
happen"); this phase RENDERS existing structured data via templating
("here is what we found, and where it came from"). No inference occurs
in this phase at all — every sentence the template produces is a
direct, mechanical substitution of a field already sitting in
`financial_reasoning_conclusions`, `extracted_facts`, or `CompanyMemory`.
This keeps the phase inside the same "zero LLM call, fully reproducible"
discipline the entire FSI track has held since Phase 3, while still
directly answering "institutional research capability" — a report is
what a research institution actually consumes, not a database.

## 7. Alternatives considered

1. **Reasoning-mode rollout (FRE-8).** Rejected — needs an LLM
   vendor/cost decision, and directly reintroduces the unsupported-
   inference risk this program has kept the FSI track free of for six
   consecutive phases.
2. **Cross-document/multi-source reasoning (Part 6).** Rejected — blocked
   on an external data-source decision (a `news_outlets` registry) this
   document cannot make.
3. **Scaling extraction to more tickers.** Rejected for THIS phase —
   a legitimate future need, but a data-acquisition effort (manual
   filing-reading at Phase 1/2's own intensity), not a design-only next
   engineering step; and it would not make the EXISTING 106 facts/177
   conclusions any more readable than they are today.
4. **Extending Phase 3's rule set.** Rejected — incremental, and Phase 3
   is frozen; already implicitly rejected in Phase 5 and Phase 6's own
   scope-selection reasoning.
5. **An LLM-generated narrative report** (i.e., building the deferred
   Area 4b narrative layer now, framed as "reporting"). Rejected
   explicitly — this would be the highest-risk possible interpretation
   of "report," reintroducing hallucination/unsupported-inference risk
   this document's whole point is to avoid; the template-based design
   below is the deliberate, safer alternative.
6. **A combined "company health" scoring dashboard.** Rejected outright
   — this is exactly the shape a hidden scoring system would take
   (aggregating multiple flags/trends into one number or rating),
   directly excluded by the owner's standing constraints; considered
   here only to state plainly why it is not what "report" means in this
   proposal.

## 8. Dependencies

`fsi-phase6-baseline-2026-08-01` in full (Phases 1-6 unmodified).
`CompanyMemory360.as_of()` (called, not forked) as the sole data source
for the report. No new schema, no new table, no new fact.

## 9. Risks

- **Template design could unintentionally imply a judgment through word
  choice or ordering** (e.g., listing `margin_compression` before a
  positive flag could read as emphasis) — mitigated by a disclosed,
  fixed section order (by conclusion_type and metric name, not by
  "severity"), and by using only the same neutral vocabulary
  (`increasing`/`decreasing`/`stable`, `fired`/`not_fired`) Phase 3
  already committed to, never new descriptive language.
- **A template covering only "the happy path" could silently omit
  `insufficient_data`/`NULL`-tier cases**, which would understate real
  data limitations exactly where they matter most — mitigated by an
  explicit success-criterion (Section 10) requiring every
  `insufficient_data` conclusion and every `NULL`-tier result to appear
  in the rendered output, not just `computed`/tiered ones.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## 10. Success criteria

- The renderer produces output for all 5 real tickers with zero
  exceptions/crashes.
- **100% field coverage**: every field in a `CompanyMemory360` snapshot
  (both `corporate` and `financial` sub-results) appears somewhere in
  the rendered output for at least one real ticker where that field is
  populated — verified by a mechanical coverage check, not eyeballing.
- Every rendered ratio/trend/flag conclusion includes its own
  `confidence_tier` (or an explicit "confidence unknown" phrase for
  `NULL`), `method`, and `limitations` — never a bare number with no
  context.
- Every `insufficient_data` conclusion is rendered with an explicit
  statement of what's missing, never silently omitted from the report.
- A mechanical single-ticker-scope guardrail holds: the renderer accepts
  exactly one `CompanyMemory360` snapshot (one ticker) and produces no
  comparative section.

## 11. Failure criteria

- Any field silently dropped from the rendered output (a real
  information-loss defect — must be reported and fixed, not shipped
  with a known gap).
- Any rendered sentence stating a conclusion more strongly than its own
  `confidence_tier`/`status` supports (e.g., presenting a `NULL`-tier
  result without flagging the unknown-confidence caveat) — a genuine,
  serious defect for this specific phase, since the whole point is
  lossless, not just readable, rendering.
- Any comparative or ranked output across tickers.

## 12. Evaluation methodology

Read-only against real production data (no scratch fixture needed — the
renderer never writes anything). For all 5 real tickers, at each
ticker's own latest real filing date (reusing the same real dates
already validated in Phases 4-6): (a) render the report, confirm no
exception; (b) run the field-coverage check (Section 10) across all 5
outputs combined; (c) for a deliberately chosen sample of conclusions
spanning all four `confidence_tier` states (`direct_reported`,
`mapped_equivalent`, `derived`, `NULL`) and both `status` states
(`computed`, `insufficient_data`), manually verify the rendered sentence
accurately reflects the underlying data, not merely that it "looks
plausible"; (d) the same `inspect.signature`-style single-ticker-scope
audit used in Phases 3-6.

## 13. Implementation boundary

**In scope**: one new, additive module (e.g. `src/ngxrot/fre/
financial_reasoning_report.py`) containing a single rendering function
(`CompanyMemory360 -> str`, Markdown) and its own test file;
documentation. **Out of scope, explicitly**: any modification to any of
the six frozen FSI phases or FRE-3; any LLM call of any kind; any new
fact, ratio, trend, or flag; any schema change or database write; any
narrative sentence not directly traceable to a specific existing field;
any cross-ticker section; any numeric or qualitative synthesis beyond
restating what `financial_reasoning_conclusions`/`CompanyMemory` already
contain.

## 14. Explicit statement of what will NOT be built

- No LLM-generated text of any kind — this is templating, not
  generation.
- No "why" narrative explaining causes (the deferred Area 4b layer,
  still not authorized).
- No overall health score, rating, grade, or summary verdict.
- No cross-company comparison, ranking, or peer-relative language.
- No valuation figure, expected return, target price, or price
  reaction.
- No buy/sell/hold or any other action-oriented recommendation.
- No new schema, table, or column — this phase reads `CompanyMemory360`
  and returns a string; nothing is persisted to the database.

## Stop condition

If a real case is found where the template cannot represent a
`NULL`-tier or `insufficient_data` conclusion without either omitting it
or overstating its confidence, stop and report this as a genuine
rendering-design limitation before proceeding — do not ship a template
that silently loses or inflates information to make the output read
more smoothly.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this is the scope the
owner intended — must be reviewed and approved before any implementation
begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
