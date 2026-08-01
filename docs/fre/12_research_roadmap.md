# FRE Part 12 — Research Roadmap

*Design only. No phase below begins execution as a result of this
document. Every phase requires its own explicit owner approval, per the
standing rule already used for every other roadmap on this platform
(LIM's Phase LIM-0..8, the AI Intelligence Layer's Phase A..G). See
`docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Sequence Parts 1-11's designs into concrete, individually-gated phases —
named `FRE-1` through `FRE-10` to avoid colliding with the existing
`LIM-N`/Phase-`A..G` numbering — each with an objective, research
question, hypothesis, success criteria, dependencies, risks, deliverables,
estimated effort, stop conditions, and review checkpoint. **No phase may
automatically proceed into implementation**, and no phase begins before
this document itself is reviewed.

## Rationale — sequencing by leverage and cost, not by document order

The fifteen-part design is not a build order. Part 8 (Valuation) is
completely blocked on a dataset Part 10 hasn't acquired yet; Part 5
(Company Memory) is *substantially buildable today* because Phase B's
dividend extractor already produced 141 real facts. Sequencing follows the
charter's own priority test — "does this increase the probability of the
next validated finding, and how cheaply" — applied to FRE capabilities
instead of quant hypotheses.

## Phase table

| Phase | Objective | Research question | Hypothesis | Success criteria | Dependencies | Risks | Deliverables | Effort | Stop condition | Review checkpoint |
|---|---|---|---|---|---|---|---|---|---|---|
| **FRE-1** | Additive schema/config foundation: widen `entity_type`, add `relation_taxonomy.toml`, `causal_chain_steps.implication_layer`/`.reasoning_mode` columns, seed `configs/financial_ontology.toml` with the accounting-identity skeleton only (Parts 1-2-3-4's schema pieces) | Can these additions land as pure additive changes with zero behavior change to existing pipelines? | Yes — every existing table/column/test is untouched by construction | 106/106+ existing tests still pass after migration; new config files reviewed and approved by owner before any row references them | None beyond the existing, frozen AI Intelligence Layer schema | Low — schema-only, no LLM calls, no new data | Migration script, populated skeleton ontology, updated test suite | S | Any existing test regression halts the phase immediately | Owner reviews the migration diff and config files before anything reads them |
| **FRE-2** | Cheap, high-leverage dataset wins: `securities.sector_ngx` population, investor-presentation `doc_type` split, press-release coverage scoping (Part 10's three lowest-cost rows) | Can sector classification reach useful coverage purely as a byproduct of re-processing the *existing* 11,533-document archive, with zero new document source? | Yes for the majority of native-text filings; OCR-pending documents remain unresolved and honestly reported as such | ≥X% of 320 tickers classified and human-review-approved (X set by owner, not invented here); `doc_type` re-classification spot-checked against a manually-labeled sample | Phase A's existing archive, the existing entity-resolution queue | Low-medium — misclassification risk, mitigated by the existing human-review queue | Updated `securities.sector_ngx`, `doc_type` labels, a coverage report matching the existing `document_text_coverage.md` convention | S-M | A classification precision below an owner-set floor on the spot-check sample halts the rollout, not just flags it | Owner reviews the coverage report before Part 1/2/6/9's sector-conditioned features are allowed to consume it |
| **FRE-3** | Company Memory read layer (Part 5), built and tested against **real, already-existing data** (Phase B's 141 dividend facts, the existing `events` table) | Does PIT-filtered, append-only-source aggregation correctly answer "what is this company's 5-year capital-allocation pattern," and fast enough for interactive use? | Yes for dividend history (real data exists today); management/strategy-narrative components remain `not_started` per Part 10, honestly scoped out of this phase | A `CompanyMemory.as_of()` query, run against ≥5 real tickers with multi-year dividend history, reproduces a manually-verified pattern with zero look-ahead violations (a mechanical audit: no returned fact/event postdates `as_of_date`) | FRE-1's schema additions (`implication_layer` not required here, only the read-object pattern) | Look-ahead bias is the single named catastrophic risk (Part 5) — the PIT audit above is the direct mitigation, not a formality | `CompanyMemory` module, PIT-audit test suite, a worked-example report for owner review | M | Any detected look-ahead violation halts the phase — this is treated with the same severity as a data-integrity bug in the quant Data Layer | Owner reviews the worked-example report and the PIT-audit results specifically |
| **FRE-4** | Cross-document reaction-check module (Part 6, Mechanism 2) — deterministic, reusing the existing PIT price panel | Does a deterministic price-reaction classification, run against the 6 real documents already processed live in the 2026-07-27 stabilization pass (including the CILEASING case), match a human-labeled expectation? | Yes, since the mechanism is arithmetic over already-validated PIT price data, not a new inference | 100% mechanical reproducibility on the pilot set (this is a deterministic calculation, not a statistical claim — the bar is correctness, not a confidence interval) | Existing PIT price panel (validated, Coverage Gate v2 passed), the 6 real stabilization-pass documents | Illiquid-name noise (Part 6's named risk) — flagged in the deliverable, not solved in this phase | `reaction_check()` module, a pilot report on the 6 real documents | S | A reproducibility failure on the pilot set halts rollout | Owner reviews the pilot report, specifically the illiquid-name caveat handling |
| **FRE-5** | `CompanyThesis` folding experiment (Part 7), single-variable design matching the LIM program's own discipline: the fold-weight parameter is the one independent variable, held against a frozen baseline (a fixed, naive "always show the most recent delta only" fold rule) | Does append-only folding with a tunable weight parameter produce a thesis that is more stable (Part 11's longitudinal-consistency metric) than the naive baseline, without becoming unresponsive to genuinely new evidence? | The fold-weight parameter has a value that improves stability without materially increasing staleness lag — genuinely open, no prior signal, stated honestly as such (mirrors RB-4/RB-5's "no observed symptom implicates this, genuinely open" framing) | Pre-registered before running: longitudinal-consistency score improves vs. baseline with no more than a stated staleness-lag regression | FRE-3 (Company Memory, for the real-fact history to fold over), Part 11's longitudinal-consistency metric definition | A fold-weight tuned to look stable on a small pilot set may not generalize — same overfitting risk this platform already treats seriously in every LoRA-rank/step-count experiment | A pre-registration document (same format as `rb3a_phase2_preregistration.md`), then a results report | M | If no fold-weight setting beats the naive baseline, stop and report a negative result honestly — do not force a conclusion (directly mirrors RB-1's "inconclusive/mixed" handling) | Owner reviews the pre-registration BEFORE this phase runs, then the results separately |
| **FRE-6** | Financial-statements dataset acquisition (Part 10's highest-leverage, highest-cost item) — its own dedicated, owner-scoped phase | What is the real achievable coverage, and cross-check accuracy vs. independent anchors, for a native-text-first extraction approach vs. a vendor cross-check? | Not a single hypothesis — an acquisition/feasibility phase, evaluated on coverage and accuracy, not a pass/fail hypothesis test | Coverage and cross-check-accuracy numbers reported honestly, whatever they are — no target pre-committed here (an acquisition phase's "success" is a feasibility finding, not a validated result) | OCR-engine decision (existing open item since 2026-07-16), possibly a vendor relationship decision (new, owner-level) | Cost, OCR accuracy, potential vendor dependency — flagged in full in Part 14 | A dataset completion report matching the existing `reports/phase_*.md` convention | L (large — this is the single most expensive item in the whole program) | If coverage/accuracy falls below a level Parts 1/7/8 can usefully consume, report that honestly and do not silently lower Part 8's own `is_ready()` bar to compensate | Owner reviews before Part 8's Valuation Engine adapters are permitted to move past `NOT_READY` |
| **FRE-7** | Valuation Engine v0 (Part 8) — adapters built, run ONLY as calculations against companies with independently-known reference valuations (e.g., a cross-listed or heavily-covered name) for sanity-checking, never as a live signal | Do the triangulated method outputs (Part 8's `TriangulatedValuation`) produce a range that contains a reasonable independent reference value on a small pilot set? | Genuinely open — this is the first real test of whether the sector-eligibility table and assumption-disclosure design actually produce sane output | Pilot triangulated ranges bracket the independent reference value in a majority of pilot cases, with disagreement-width reported, not hidden | FRE-6 (the dataset), Part 1's sector-conditioned assumptions, Part 2's subsidiary lineage (for any holdco pilot case) | False precision, assumption laundering (Part 8's named risks) | A pilot validation report | M | Systematic bracket failure (reference value outside every method's range on most pilot cases) halts rollout for redesign, not silent parameter tweaking | Owner reviews before any triangulated output reaches Part 7's `CompanyThesis` |
| **FRE-8** | Reasoning-mode rollout + guardrail enforcement (Part 4) — `reasoning_mode` tagging live in production calls, counterfactual/placebo disclaimer and macro `evidence_status` citation checks wired into the self-critique gate | Does mechanical mode-guardrail enforcement measurably reduce the specific failure patterns it targets (placebo conflation, unexplained rejected-mechanism citation)? | Yes, since these are deterministic checks, not probabilistic ones — the open question is real-world trigger frequency, not whether the check works | Zero occurrences of an un-disclaimed counterfactual claim or an un-cited `ngx_rejected` macro claim in a post-rollout audit sample | FRE-1 (schema), Part 1 (ontology evidence_status), existing self-critique gate | Guardrail text becoming boilerplate that reviewers stop reading (a known general risk with mandatory disclaimers) — flagged, not solved | An audit report | S | n/a — this phase is itself an audit/verification step | Owner reviews the audit sample |
| **FRE-9** | Portfolio Reasoning Tier 1 (Part 9) — watchlist/screening objects live, `PortfolioMemory` read-only cross-reference to `alpha_engine.py`'s `H011SizeAdapter` wired | Does read-only cross-referencing correctly avoid any write path into the alpha engine, verifiable by the same import-graph check the architecture doc already proposes? | Yes by construction — verified by a mechanical import-graph check (architecture doc §9), not merely asserted | Zero imports of FRE watchlist/screening modules found inside `alpha_engine.py`/`runner.py`; a manual audit of watchlist UI/display confirms no implied ranking (Part 9's named risk) | Part 7 (`CompanyThesis`), the existing `H011SizeAdapter` | Watchlist-creep-into-ranking (Part 9's named risk) | Screening/watchlist modules, an import-graph audit report | M | Any detected import violation halts the phase immediately, treated as a governance breach, not a bug | Owner reviews the import-graph audit and a sample watchlist display for implied ordering |
| **FRE-10** | Evaluation framework operationalization (Part 11) — `fre_eval` harness built, strategy-narrative gold set (Part 10) created, owner-agreed tolerance set for the Tier-1 gating criterion | Does the gold-set-based evaluation actually discriminate between a deliberately-degraded reasoning configuration and the real one (a sanity check on the evaluation harness itself, mirroring how LIM's own eval harness was validated before being trusted)? | Yes — an evaluation harness that cannot detect a known-injected degradation is not yet trustworthy | The harness correctly flags a deliberately-injected regression (e.g., a grounding check disabled) before being trusted for real gating decisions | Parts 3, 6, 7's mechanical checks; the strategy-narrative gold set (analyst-authored, small) | A harness that passes everything regardless of quality (a false-negative eval, the single worst failure mode for an evaluation system) | `fre_eval` harness, a harness-validation report | M | If the injected-regression sanity check fails, the harness itself is not trusted until fixed — no gating decision may use it until this passes | Owner reviews the harness-validation report before FRE-9's Tier-1 rollout is gated by it |

## Alternatives considered

1. **Sequence by document part order (1 through 15).** Rejected — would
   force Part 8 (Valuation) before its dataset dependency is even scoped,
   and would delay Part 5 (Company Memory) despite it being buildable
   almost immediately on real existing data. Leverage/cost sequencing is
   strictly more informative.
2. **One large "Phase FRE-1" bundling schema + cheap datasets + Company
   Memory together.** Rejected — bundling would violate the same
   single-variable-per-phase discipline this platform has enforced
   throughout the LIM program (RB-series); each phase above has one
   dominant risk surface and one clear stop condition, which a bundled
   phase would blur.
3. **Delay all implementation until the financial-statements dataset
   (FRE-6) is acquired, on the theory that "nothing really works without
   it."** Rejected — Parts 3/5/6's real, already-existing data (dividend
   facts, price panel, the 6 real stabilization-pass documents) make
   several phases genuinely executable today, and delaying them would
   waste that existing evidence for no real reason.

## Trade-offs

- Leverage-based sequencing puts the single most expensive phase (FRE-6)
  in the middle of the roadmap rather than first or last — this is
  deliberate: early enough that later phases (Valuation, full Financial
  -quality scoring) aren't perpetually blocked, late enough that cheaper,
  faster-feedback phases (FRE-1 through FRE-5) validate the program's
  foundational design choices first, so FRE-6's real cost is spent only
  after the surrounding architecture has already been sanity-checked on
  cheaper phases.
- Several phases (FRE-3, FRE-4, FRE-5) are explicitly scoped to run on
  *already-existing* real data rather than waiting for a "complete"
  dataset — this yields smaller, honestly-caveated pilot results rather
  than comprehensive ones, consistent with this platform's preference for
  an honest small result over a delayed comprehensive one.

## Risks

- **Phase-ordering assumes owner approval lands roughly in sequence** — if
  the owner approves phases out of order (e.g., wants Valuation work before
  the dataset exists), the dependency table above is the mechanism for
  surfacing that conflict explicitly rather than silently proceeding.
- **Effort estimates (S/M/L) are qualitative, not measured** — consistent
  with this platform's own disclosed practice elsewhere (LIM's "Estimated
  effort: S (~10 min)" style estimates were frequently wrong in practice,
  e.g. RB-3c's Phase 0 infrastructure interruption); these are planning
  aids, not commitments.

## Future extensions

- Once FRE-6 (dataset) and FRE-7 (Valuation) complete, a natural FRE-11+
  sequence (sector-specific valuation refinement, Part 9 Tier-2 unlock
  tracking, LIM-as-FRE-provider integration once LIM's own RB-series
  reaches a production-viable checkpoint) — deliberately not planned in
  detail here, since planning past the next dataset-dependent phase before
  that phase's real findings exist would itself violate this program's own
  "don't assume success before testing" discipline.

## Dependencies

- Every dependency named per-phase above. At the document level: this
  roadmap depends on Parts 1-11's designs being approved as designs (not
  necessarily as final) before their corresponding phase starts, and on
  Part 13's gap analysis (next) for an honest accounting of what today's
  codebase actually already provides toward each phase.

## Execution note, added 2026-08-01 (append-only — the table above is

left as originally designed, not rewritten)

Actual execution diverged from this table in one respect, disclosed here
rather than silently reconciled: **FRE-2 through FRE-5 executed as
designed**, but **FRE-6 executed as "Valuation Engine architecture"**
(scaffolding + readiness-gating only) rather than this table's original
FRE-6 ("Financial-statements dataset acquisition"). The dataset-
acquisition work this table's FRE-6 row describes was instead carried out
as a separately-tracked **Financial Statement Intelligence (FSI)**
program (Phases 1-2, see `docs/fre_runs/`), inserted via an explicit
roadmap review conducted before FRE-7 began
(`docs/fre_runs/roadmap_review_financial_statement_intelligence.md`).
Net effect: this table's FRE-7 ("Valuation Engine v0", pilot triangulated
ranges against a now-real dataset) remains the next roadmap item exactly
as designed and is **not yet started**. Separately, the owner has since
directed a **Phase 3** (`docs/fre_runs/fsi_phase3_preregistration.md`,
once written) focused on financial reasoning over the FSI dataset rather
than valuation specifically — this is additive to, not a replacement for,
FRE-7-as-designed; both remain individually gated, and neither begins
without its own separate owner approval.
