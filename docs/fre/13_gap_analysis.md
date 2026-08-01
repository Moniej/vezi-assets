# FRE Part 13 — Gap Analysis

*Comparison only. No changes made. Synthesizes the current, real state of
the AI Intelligence Layer, LIM, and the quant engine against the FRE design
in Parts 1-12. See `docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

State plainly, for every FRE-relevant component: what already exists (and
is real/tested, not aspirational), what is partially built, what is
missing entirely, what must never be changed, what should be extended, and
what genuinely requires more research before it can be designed further —
so Part 12's roadmap is grounded in an honest current-state snapshot, not
an assumed one.

## LIM specifically — the owner's named comparison point

The owner's framing ("compare the current LIM against the desired FRE")
deserves a direct answer, not a buried table row: **LIM is not, today,
ready to serve as the FRE's reasoning provider, and this document does not
assume otherwise.** As of the most recent LIM research state
(`docs/lim_runs/lim_research_review.md`, RB-3c in progress, Phase 0
interrupted and not yet re-run): `self_critique_quality` remains exactly
0.0 in every completed evaluation; the RB-3b mode-collapse finding shows
the model's `self_critique` outputs achieve schema/value validity only via
near-total mode collapse (predicting `fail`/`unvalidated_ai_interpretation`
regardless of true label), not genuine per-example discrimination; RB-3c's
own step-count experiment (designed to distinguish "needs more training" vs
"dominated by a pretrained prior") has not yet produced a result. **Every
real reasoning call this platform has ever made against live NGX data —
the 90.0%/100.0% precision/recall, the 100% grounding/citation integrity,
every real self-critique block including the CILEASING case — was made by
Gemini, the external teacher, not LIM.** LIM remains, correctly, a
research program in progress (`docs/LIM_ARCHITECTURE.md`'s own explicit
non-goal: "LIM is never auto-promoted to the default provider"), and the
FRE design in Parts 1-12 is written to be **provider-agnostic** for exactly
this reason — every FRE capability sits on top of the existing
`LLMProvider` interface, unaffected by which concrete provider (Gemini
today, possibly LIM later) answers the call.

## Master gap table

| Component | Status | Detail | Disposition |
|---|---|---|---|
| Quant Data Layer, Research Engine, Factor Library (`runner.py`/`phase4.py`/`stats.py`/`registry.py`/`ledger.py`) | **Exists, validated, live** | H-011 confirmed; 320k+ price rows; Coverage Gate v2 passed | **Never change** — frozen V1, unaffected by anything in this program |
| Hard boundary (`ngxrot.documents` never imported by `alpha_engine.py`/`runner.py`) | **Exists, enforced** | Verified repeatedly across every phase's completion report | **Never change** — every FRE part in this program was explicitly designed to preserve this |
| AI Intelligence Layer Phase A (document ingestion) | **Exists, validated** | 11,533 documents, 7,399 native-text, 4,134 OCR-pending | **Extend** — Part 10's cheap dataset wins (sector/doc_type classification) build directly on this |
| Phase B (deterministic dividend/rights/bonus extraction) | **Exists, validated** | 143 `extracted_facts` rows, 0 validation issues | **Extend** — Part 5's Company Memory dividend history is a direct, ready-today consumer |
| Phase C (full reasoning pipeline: extraction, grounding, self-critique, Gemini provider) | **Exists, tested, run live** | 90.0%/100.0% precision/recall, 100% grounding+citation integrity on real filings (2026-07-27 stabilization pass) | **Never change** the core 14-step chain/gate logic; **extend** via Part 3's additive `implication_layer` column and Part 4's `reasoning_mode` column only |
| Phase E (retrieval, `ReasoningContext`, `reason_about_company()` orchestrator) | **Exists, tested** | 90/90 engineering tests, real live run | **Extend** — this program's `CompanyMemory` (Part 5) is this orchestrator's natural longitudinal sibling |
| Phase F (Industry Reasoning peer propagation) | **Exists, tested, disclosed limitation** | 106/106 tests; peer resolution is exact-name-match only; `relation_type` holds only `affects_order_N` | **Extend** — Part 2 directly targets and names this exact limitation for closure |
| Phase G (Company Intelligence + Discovery integration) | **Not started, explicitly paused** | `HANDOFF.md`: "Do not start Phase G... without fresh owner direction — this pass was explicitly a freeze" | **Research/owner-decision required** — several FRE parts (7, 9) assume Phase G-adjacent capabilities (`discovery_feed.py`) exist; they do not yet |
| `discovery_feed.py` (Discovery-candidate aggregation) | **Named in design docs, not confirmed built** | Architecture doc §9 describes it as consuming Phase G-era volume; not listed among Phase E/F's tested deliverables | **Missing** — a real gap this document surfaces; Part 12's roadmap should not assume it exists without verification before FRE-9 |
| `company_intelligence.py` / `CompanyProfile` | **Exists, partial** | Only Size (H-011) populated; every other vision field returns `UNAVAILABLE_FIELDS` | **Extend** directly — Part 7's `CompanyThesis` is designed as this module's qualitative-research sibling, not a replacement |
| Ranking Engine, Portfolio Construction, Risk Engine, Performance Attribution | **Correctly gated, not built** | `docs/PLATFORM_ARCHITECTURE.md`, unchanged preconditions (≥1-2 validated independent factors; only 1 exists) | **Never change the gate** — Part 9 designed Tier 1/Tier 2 specifically around this |
| LIM (`docs/LIM_ARCHITECTURE.md`, LIM-0 through LIM-6/RB-series) | **Mid-research, not production-ready** | See the dedicated section above | **Research required** — RB-3c and successors must reach a stable, evaluated state before any FRE-provider-swap conversation is even appropriate |
| **Part 1 — Financial Ontology** | **Missing entirely** | No `causal_chain_steps` mechanism-vocabulary exists today; every reasoning call improvises its own causal story | New build (FRE-1) |
| **Part 2 — Knowledge Graph typed relations** | **Partial** | `entities`/`entity_relationships`/`entity_mentions` schema exists; `entity_type` CHECK excludes commodity/macro_variable (a real inconsistency this document found, see Part 2); `relation_type` is not genuinely typed | New build (FRE-1/2), on existing schema |
| **Part 3 — Evidence Graph layering** | **Partial** | Every underlying table (`evidence`, `extracted_facts`, `causal_chain_steps`, `impact_assessments`, `investment_implications`, `research_task_candidates`) exists and is tested; the `implication_layer` narrative tag does not | New build (FRE-1), additive column only |
| **Part 4 — Reasoning modes** | **Missing entirely** | No mode tagging or mode-specific guardrail exists; the counterfactual/placebo-conflation risk is currently unmitigated by any mechanical check | New build (FRE-1/8) |
| **Part 5 — Company Memory** | **Missing as an aggregation object; substantially real underneath** | Dividend history (real, 141 facts), filing history (real, 11,533 documents), `events` (real) all exist; nothing aggregates them per-company today | New build (FRE-3), largely executable on existing real data |
| **Part 6 — Cross-document reasoning** | **Partial** | Corroboration/contradiction mechanism exists in the schema (`corroborates_implication_id`/`contradicts_implication_id`) and is used; the deterministic reaction-check module does not exist; `news_outlets` registry does not exist; only `XIssuerDocumentProvider` is confirmed real among the named providers | New build (FRE-4), reaction-check executable on existing real data today |
| **Part 7 — Investment Thesis Engine** | **Missing as an aggregation object** | The per-fact deltas it folds (`bull_case_delta` etc.) already exist and are populated on real data | New build (FRE-5) |
| **Part 8 — Valuation Engine** | **Missing entirely, correctly** | No financial-statements dataset exists | Blocked on FRE-6 (dataset acquisition) |
| **Part 9 — Portfolio Reasoning (Tier 1)** | **Missing** | No watchlist/screening object exists; `H011SizeAdapter`'s live sleeve exists and is a valid read target | New build (FRE-9) |
| **Part 10 — Dataset Strategy** | **Inventory only, mostly `not_started`** | See the dataset table in Part 10 itself — sector classification and `doc_type` splitting are the cheapest near-term wins | Sequenced across FRE-2 and FRE-6 |
| **Part 11 — Evaluation Framework** | **Partial** | Grounding/citation/hallucination-rate measurement exists and is validated on real data; causal-correctness, calibration, and longitudinal-consistency metrics cannot exist before their underlying objects (Parts 1, 5, 7) do | New build (FRE-10), phased to match its own prerequisites |

## What should never be changed (consolidated)

1. The frozen V1 quant architecture and the hard `ngxrot.documents`
   import boundary.
2. The 14-step reasoning chain's core semantics and the self-critique
   gate's eight mandatory questions (this program only ever proposes
   **additive** columns/mode-tags on top, never a redefinition).
3. The charter's honesty constraints, especially "the engine only speaks
   from validated models" — directly enforced in Part 7's Expected Return
   guardrail and Part 9's Tier 1/Tier 2 split.
4. PIT/append-only discipline across every table this program touches.
5. LIM's own non-goal: never auto-promoted to default provider.

## What should be extended (consolidated)

`entities`/`entity_relationships` (Part 2), `causal_chain_steps` (Parts 3
and 4's additive columns), `company_intelligence.py`/`CompanyProfile`
(Part 7), `context.py`/`ReasoningContext` (Part 5's natural sibling),
`coverage_assessment.py` (Part 5's historical-depth dimension),
`evidence_ranking.py` (Part 6's cross-source arbitration),
`industry_reasoning.py` (Part 2's real-relation-type upgrade to Phase F's
disclosed no-op filter).

## What research is still required (consolidated, cross-referenced to Part 12)

- LIM's own unresolved RB-series items (RB-4 learning rate, RB-5 batch
  size, RB-6 sequence length, RB-7 stop sequence, RB-8 eval context
  persistence, and — most materially — RB-3c's still-unresolved H1-vs-H2
  step-count question) must reach a stable conclusion before any
  LIM-as-FRE-provider conversation is appropriate; this document does not
  put a date on that, since the LIM program's own honest, evidence-driven
  pace has repeatedly produced negative and inconclusive results that were
  correctly reported as such rather than rushed.
- FRE-5's fold-weight parameter (Part 7) — genuinely unstudied.
- FRE-10's calibration-metric minimum-sample floor (Part 11) — genuinely
  unstudied, time-dependent, cannot be shortcut.
- The OCR-engine decision (open since 2026-07-16) and the
  financial-statements acquisition approach (Part 10/12's FRE-6) — both
  owner-level decisions with real cost implications, not resolved by any
  design document.
- Whether `discovery_feed.py` needs to be built from scratch or already
  exists in some partial form — a direct, concrete, low-cost verification
  task that should happen **before** FRE-9 assumes an answer either way.

## Alternatives considered

1. **Assume the architecture docs' descriptions of Phase E/F/G are fully
   accurate without re-verifying against `HANDOFF.md`'s actual completion
   reports.** Rejected — this document specifically cross-referenced the
   architecture doc's `discovery_feed.py` description against the Phase
   E/F completion reports and found it is not confirmed built, exactly the
   kind of gap a lazy gap analysis would have missed by trusting the design
   doc's narrative tense uncritically.
2. **Treat LIM's research maturity as "close enough" given how much work
   has gone into it.** Rejected — explicitly and directly contradicted by
   the RB-3b mode-collapse finding and RB-3c's incomplete status; effort
   invested is not the same as a validated result, the same distinction
   this entire platform's charter is built around for quant hypotheses,
   applied here to LIM.

## Trade-offs

- This gap analysis is only as current as the documents it was built
  from (as of this writing); several items (`discovery_feed.py`'s real
  status, LIM's RB-3c outcome) are explicitly flagged as needing a fresh,
  cheap verification pass before FRE-9/FRE-10 rather than being resolved
  here — a deliberate choice to flag uncertainty rather than guess.

## Risks

- **Stale-gap risk**: if this document is read much later without
  re-verification, its "exists/partial/missing" calls could themselves be
  out of date (e.g., if Phase G was later started, or LIM's RB-3c
  concluded) — every row above should be spot-checked against `HANDOFF.md`
  and the relevant `docs/lim_runs/` file before being relied upon for a
  real go/no-go decision, not treated as permanently authoritative.

## Future extensions

- A living version of this table, refreshed at each Part 12 phase
  checkpoint rather than written once — noted as a process improvement,
  not built here.

## Dependencies

- `HANDOFF.md`, `docs/LIM_ARCHITECTURE.md`, `docs/lim_runs/lim_research_review.md`,
  `docs/lim_runs/lim6_research_backlog.md`, `docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`,
  `docs/REASONING_ENGINE_SPECIFICATION.md`, `docs/PLATFORM_ARCHITECTURE.md`,
  `docs/FACTOR_REGISTRY.md` — every claim in this document traces to one of
  these, consistent with this program's "nothing asserted from memory"
  discipline.
