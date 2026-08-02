# FUND ALPHA — SESSION HANDOFF (2026-07-27)

**STABILIZATION PASS COMPLETE (2026-07-27), owner-mandated pause before
Phase G.** Owner asked for CoverageAssessment/EvidenceRanking (verify or
build per spec — a full codebase/docs/memory search found neither had
actually been specified anywhere before; owner confirmed treating the
request's own bullet points as the spec), a complete real-data end-to-end
validation, high-priority tech-debt fixes, and a stable, committed,
tagged baseline before any new phase starts. Full report:
`reports/stabilization_validation_report.md`.

Built `src/ngxrot/documents/coverage_assessment.py` (10-dimension mechanical
coverage checklist -> `coverage_score`, a `confidence_ceiling` that scales
`UNREVIEWED_LLM_CONFIDENCE_FLOOR` down further via owner-adjustable bands,
and named reasons) and `evidence_ranking.py` (trust tiers per evidence
source; `assess_implication_conflict` recomputes a trust-tier-aware
preference for every contradiction `extract.py`'s `_cross_reference` already
recorded on a confidence-only basis, and discloses when the two disagree).
Both are read-only/descriptive — neither mutates a stored confidence or any
existing gate. Wired additively into `ReasoningContext`/`ReasoningResult`.
No schema migration. 28 new tests (154/154 total pass).

Ran the Phase E/F orchestrator (`reason_about_company`) LIVE against real
NGX filings for the first time ever (TD13/TD16 had flagged this as
untested) — 6 new real documents across 4 tickers, real Gemini calls: 5
correctly abstained (no material fact, not fabricated), 1 (a real CILEASING
dividend filing) ran the full chain for real and was correctly
`blocked_by_self_critique` on a genuine `insufficient_information` fail.
Full-corpus real-data metrics: 90.0% extraction precision / 100.0% recall,
100% grounding + citation integrity on live re-verification, 22.2%
self-critique rejection rate, coverage scores 0.5-0.6 across all 12 real
tickers (both permanent gaps — no financial-statements dataset, no
news/analyst ingestion — correctly capping every ceiling at 0.225 today).

Found and fixed one real gap during validation: `reasoning_engine.py`'s
orchestrator never wrote to `document_processing_status` (only
`run_phase_c_pilot.py` did), so `pilot_summary.py`'s processed/failed
counters silently under-counted real orchestrator-driven work. Fixed
(observability only — `should_skip()`/`resume_point()` never depended on
this table) and backfilled the 6 documents this pass processed before the
fix landed. No other finding rose to high-priority; TD12 (entity-resolution
merge-queue gap) remains disclosed, unchanged, MEDIUM.

Real database backed up before any live run:
`data/ngx.sqlite.pre_stabilization_backup_2026-07-27` (untracked, local
safety copy). All AI Intelligence Layer work (Phases A-F, never committed
incrementally, plus this pass) is now committed with a phase-by-phase
history; this milestone is tagged `ai-layer-stable-baseline-2026-07-27`.
**Do not start Phase G or any new AI Intelligence Layer capability without
fresh owner direction — this pass was explicitly a freeze, not a new phase.**

**PHASE F BUILT AND TESTED (2026-07-26): Industry Reasoning Engine —
peer/competitor propagation via the knowledge graph, stopped for review
as instructed.** Continues the A→G roadmap (architecture doc §4.5) on top
of Phase E's `entity_relationships`. Two design premises from the
original doc didn't hold once inspected, both disclosed not silently
patched around: (1) `relation_type` holds `affects_order_N`, not a
classified `competitor_of` — propagation filters on the object entity's
`entity_type='competitor_mention'` instead (a no-op filter today, real
once entity typing gets more precise); (2) peer entities never resolved
to a ticker before this pass — added `entities._exact_name_match_ticker`
(exact, case-insensitive match against `securities.name` only, no fuzzy
guessing — most real mentions won't resolve, an accepted coverage
limitation). **Larger, deliberate scope decision**: no algorithmic
direction-inversion was built (the architecture doc's own example implies
inferring whether a peer is helped or hurt — that's an economic-mechanism
judgment this platform has never let a hardcoded rule make). Propagated
implications copy the source's direction/magnitude unchanged, get a
discounted confidence (`vocab.INDUSTRY_PROPAGATION_CONFIDENCE_DISCOUNT=0.5`,
the architecture doc's own flagged-open decision #6, picked and
disclosed), `status='under_review'` (never `unvalidated_ai_interpretation`
— no self-critique ran on them), and a mandatory paired research task
asking a future pass to actually assess peer direction. One-hop-only
(never chains), idempotent, refuses `blocked_by_self_critique` sources.
New: `src/ngxrot/documents/industry_reasoning.py`
(`propagate_implication`), `retrieval.find_peer_propagations`,
`ReasoningContext.peer_propagations`, `reasoning_engine.py` wiring
(`propagated_implication_ids`/`peer_propagations_received` on
`ReasoningResult`). No schema migration —
`investment_implications.propagated_from_implication_id` already existed,
unused until now; propagated rows reuse the source fact's `fact_id`, so
every propagation is fully auditable back to the real document.
**106/106 tests pass** (90 + 16 new). One real cross-test cache-pollution
bug found and fixed while testing (`cached_complete`'s `force=True` path
overwrites the on-disk cache, not just bypasses it — a latent property of
the existing Phase C cache, not a new bug this phase introduced). 3 new
disclosed technical-debt items (TD14-TD16, `docs/EXECUTION_BACKLOG.md`).
Full report: `reports/phase_f_completion.md`. Stopped here per the
standing instruction — self-critique redesign and any local/Qwen model
work remain explicitly out of scope.


**AI-1 CLOSED (2026-07-26): Phase C pilot complete, 9 remaining documents
run.** `scripts/run_phase_c_pilot.py` resumed cleanly (owner re-supplied
`GEMINI_API_KEY` via a persistent env var; no quota errors this run).
Full-pilot validation (`scripts/validate_phase_c_extraction.py`):
precision 90.0% / recall 100.0% vs. Phase B ground truth, self-critique
gate ran completely on every draft (3/17 `blocked_by_self_critique`), one
real disagreement disclosed not resolved (doc 10788 MOFIREIF). Detail in
`docs/EXECUTION_BACKLOG.md`'s AI-1 entry and `reports/phase_c_completion.md`.

**PHASE E BUILT AND TESTED (2026-07-26): Financial Reasoning Engine
extensions on top of Phase C ("Knowledge Layer") — done, stopped for
review as instructed.** Owner directive: extend, do not rebuild. Gap
analysis (presented and approved) found Phase C already satisfies most
of Phase E's requirements (model-agnostic provider factory, structured
non-free-text reasoning schema, evidence/grounding, confidence,
alternative-hypothesis interrogation, contradiction cross-referencing,
factor-exposure integration via `company_intelligence.build_profile`) —
four genuine, additive gaps, all now built:

1. `src/ngxrot/documents/retrieval.py` — SQL-first structured retrieval
   (`RetrievalQuery`/`retrieve_documents` is the seam a future semantic
   retriever would sit behind; no embeddings added).
2. `src/ngxrot/documents/context.py` — `ReasoningContext` +
   `build_reasoning_context`, the single object every reasoning module
   now consumes instead of issuing its own queries. Also
   `historical_event_reaction()` — a deliberate, disclosed deviation from
   the letter of the spec (which named `signal.event_window_scores`,
   whose output is portfolio target weights, not a citable descriptive
   stat — reuses the same underlying PIT primitives instead).
3. `src/ngxrot/documents/reasoning_engine.py` — `reason_about_company()`,
   the question-driven orchestrator: loads the context, retrieves +
   extracts unprocessed documents only when needed (capped at 5/call),
   assembles a `ReasoningResult` purely by aggregating already-governed
   rows — no new ungated LLM call.
4. `entities.py`'s new `record_relationship()`, wired into `extract.py`'s
   effect_chains loop — `entity_relationships` existed since Phase C but
   nothing had ever written to it until now; evidence-backed only,
   `relation_type` is the literal `affects_order_N` fact, never an
   invented taxonomy label.

**90/90 engineering tests pass** (68 pre-existing + 22 new,
`scripts/test_reasoning_pipeline.py`). One real bug found and fixed while
testing: `context.py` originally called `company_intelligence.
build_profile()` unconditionally, which crashes on a database/ticker with
no quant equity panel — fixed to degrade to an empty `factor_exposures` +
an explicit coverage note instead of propagating the exception. Full
report + 5 new disclosed technical-debt items (TD11-TD13 range in
`docs/EXECUTION_BACKLOG.md`): `reports/phase_e_completion.md`. Hard
boundary reconfirmed unchanged (no import of `ngxrot.documents` in
`alpha_engine.py`/`runner.py`); no vector search added; grounding and
self-critique untouched — every new module either calls the existing
gated pipeline or aggregates rows that already passed it.

**Stopped here per owner instruction** — self-critique redesign and any
local/Qwen model work are explicitly OUT of scope for this pass (the
existing `LLMProvider` factory pattern already makes a future
`QwenProvider` a small additive class when that work starts).

Read this first in a fresh context. Strategic history: `docs/` + auto-memory.
Working dir: `C:\Users\nonso\Desktop\vezi assets\ngx-rotation`.
**This IS now a git repository** (E3, `git init` 2026-07-22) — `git log`
before assuming anything is uncommitted or lost. `.gitignore` excludes
`data/archive/`, `data/staging/`, `data/capture/`, and all `*.sqlite`
(rationale in the `.gitignore` file itself and the E3 commit message).

**PROGRAM STATUS (2026-07-22): 11 hypotheses tested. 1 CONFIRMED
(H-011, Size), 9 rejected, 1 untested (H-002, still blocked on dividend
data). THE FACTOR LIBRARY HAS ITS FIRST ENTRY.** Full writeup:
`docs/FACTOR_REGISTRY.md`'s Validated section. Short version: long the
smallest-cap quintile in IRU v2, quarterly, net excess +15.02% dev /
+53.0% untouched OOS, placebo p=0.0099 (real Sharpe beats even the max
of 100 shuffled draws), confidence rating High (10/12, highest in the
program's history) — BUT capacity is the worst measured on this
platform (median leg ~₦694k, 100% legs rejected at ₦1bn AUM). This is a
REAL, valid, SMALL-AUM effect, not a broadly scalable strategy — the
severe capacity constraint is consistent with the factor's own
friction-compensation rationale, not a contradiction of it.

**H-010 (pooled momentum) was REJECTED**, decisively — placebo p=0.386,
*worse* than H-009's near-miss (0.069). Real-data cohort correlation
measured at ~0.75 (vs ~0.57 on the synthetic rehearsal) — pooling didn't
add the independent bets it was designed to add. This closes the
"pool more cohorts" successor path for NGX momentum; see
`docs/FACTOR_REGISTRY.md` for the full diagnosis (calendar-alignment
artifact hypothesis for H-009's original near-miss).

**Architecture remains FROZEN as V1 — do not redesign it.**

**Immediate next steps:**
1. ~~Wire a `ModelAdapter` for H-011~~ — **DONE 2026-07-22.**
   `H011SizeAdapter` in `src/ngxrot/alpha_engine.py`, reuses
   `backtest_xs.size_scores`/`load_market_cap_panel` UNCHANGED at the
   exact validated config (top_n=20, quarterly). Verified end-to-end via
   `scripts/engine_status.py`: 20 actionable recommendations, correct
   provenance, correct latest-formation date. Vintage semantics: the
   VALIDATION is pinned to 2026-07-21 (immutable); this LIVE adapter
   reads the latest available data — the model is frozen, the data it
   reads is current. Headline expected-excess/drawdown figures use the
   dev/full-evaluation numbers (+15.02%/-32.81%), not the flashier
   untouched-OOS figure (+53.0%) — that's disclosed in caveats instead
   of quoted as the headline, to avoid cherry-picking. The severe
   capacity constraint (median leg ~₦694k) is the FIRST caveat listed.
2. ~~E16: persist `result.attribution` / fix `n_rebalances`~~ — **DONE
   2026-07-22.** `runner.py` now persists cohort diagnostics into the
   registry; `pooled_rank_run` builds real per-cohort execution-date
   weights (fixes `n_rebalances` 0→35 and `hit_rate_vs_benchmark`
   None→0.457 as a bonus, same root cause). `ic_report.py` shows a
   "Cohort diagnostics" section for pooled hypotheses. Reconfirmed on a
   direct re-run of H-010's base config — verdict unchanged (every
   verdict-relevant number was byte-identical before/after).
3. ~~Company Intelligence Engine v0 scaffolding~~ — **STARTED 2026-07-22.**
   `src/ngxrot/company_intelligence.py` (`CompanyProfile` dataclass +
   `build_profile()`), CLI: `python scripts/company_profile.py TICKER
   [TICKER...]`. Scaffolds every vision field (Financial Quality,
   Valuation, Growth, Momentum, Risk, Corporate Events, Competitive
   Position, Macro Sensitivity, Industry Exposure, Ownership, Factor
   Exposures, Expected Return, Confidence) but populates ONLY from
   evidence-grade data — everything else returns an explicit blocking
   reason via `unavailable` (e.g. Industry Exposure: `securities.
   sector_ngx` is now populated for 136/320 tickers as of FSI Phase 23,
   2026-08-02, but `build_profile()` has no logic wired to consume it
   yet, so the field remains `unavailable`, disclosed as such rather
   than silently activated). Cites REJECTED factor families too
   (Momentum/Low-Vol/PEAD, each with its finding) — a rejection is
   evidence, not silence. Only Size (H-011) has a real computed value,
   via the SAME `backtest_xs.size_scores` construction, unchanged, for
   EVERY company (not just the current sleeve — that distinction from
   `alpha_engine`'s adapter is deliberate). Verified: this module's
   `in_current_sleeve` agrees exactly with `H011SizeAdapter`'s 20 actual
   recommendations; a nonexistent ticker degrades gracefully with an
   honest note, no crash. Portfolio Construction stays correctly GATED
   (needs ≥2 validated INDEPENDENT factors; only 1 exists) — do not
   start it.
4. Wave 4 candidates and prioritization: unchanged from
   `docs/EXECUTION_BACKLOG.md`'s R3 (regime-conditioning) and the
   momentum/PEAD successor notes — re-evaluate in light of H-010's
   result before drafting anything new.

**START HERE: `docs/EXECUTION_BACKLOG.md`** — the current, actionable
task list (now includes E16 above). `docs/FACTOR_REGISTRY.md` for the
full evidence trail on every hypothesis, especially H-011.

**NEW (2026-07-22, revision 2): `docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`**
— design-only doc (no code written against it), expanded per owner
follow-up from a single Document Intelligence module into a full AI
Intelligence Layer: Entities → Events → Evidence → Reasoning → Investment
Implications pipeline, with four specialized reasoning engines (Financial,
News, Macroeconomic, Industry). Key continuity decision: AI-detected
events (CEO change, guidance revision, debt refinancing, etc.) are
ingested into the EXISTING `events` table/taxonomy via the unchanged
`event_pipeline.validate_batch` — not a forked table — with a new additive
`event_ai_provenance` companion table carrying model/prompt/review
metadata. Three-axis confidence model (source / extraction / per
-reasoning-question), never merged. Hard boundary unchanged and restated
as a code-level fact: no import of the new `ngxrot.documents` package may
ever appear in `alpha_engine.py`/`runner.py`/any future portfolio module —
only a fully pre-registered, gauntlet-passed hypothesis (H-012+) can turn
a Discovery-fed candidate into something a portfolio reads. Explicit
scope limit: no numeric intrinsic-value/DCF output until a
financial-statements dataset is acquired — directional, evidence-cited
reasoning only. Phased A→G (Foundation → deterministic re-labeling →
entity/event pilot → Financial reasoning v0 → scale + News/Macro engines
→ Industry propagation → Company Intelligence/Discovery integration), each
gated on owner review. 7 open decisions flagged (LLM vendor/cost, OCR
engine, news-outlet reliability roster, analyst-research licensing,
NGX transcript availability, propagation confidence-discount factor,
review staffing). Nothing beyond Phase A should be built without
sign-off; frozen V1 architecture and the validated research engine are
untouched.

**PHASE A COMPLETE (2026-07-22).** `schema/schema.sql` gained `documents`/
`entities`/`entity_mentions` (additive, entities/entity_mentions still
empty — populated starting Phase C). `configs/document_taxonomy.toml`
added (reuses the existing corp-actions `doc_class` classifier output as
its leaves — no new classification work needed). `scripts/
build_documents_table.py` (idempotent, resumable via `DOC_BATCH_LIMIT` env
var — background runs kept getting killed by the environment past
~600-1800s for unclear reasons, foreground bounded batches were reliable)
processed all 11,546 rows of `corporate_actions_calendar_classified.csv`:
**11,533 documents rows** (13 skipped — archived file missing/undersized,
logged not fabricated), **7,399 native-text** (source_confidence=0.85),
**4,134 OCR-pending** (source_confidence=0.0, correctly NOT OCR'd — engine
choice still an open decision), **0 extraction errors**, **11,134 tickers
resolved** via the 4 verified renames, **399 unresolved** (raw_symbol kept
verbatim, ticker NULL, no guessed matches). Full breakdown by doc_type and
filing year: `reports/document_text_coverage.md`. No LLM calls made
anywhere in Phase A. **NEXT: owner reviews the coverage report and decides
the OCR engine (open decision 2 in the architecture doc) before Phase B**
(re-labeling the existing deterministic dividend/EPS extractors' output
into this schema) starts — do not proceed further without that review.

**NEW (2026-07-22): `docs/REASONING_ENGINE_SPECIFICATION.md`** —
design-only doc (no code, no LLM calls) operationalizing the owner's
detailed "institutional analyst" reasoning mandate into a fixed 13-step
process every reasoning-engine call must execute (identify → extract
facts → recursive-why causal chain → 14-category impact assessment →
duration/magnitude buckets → confidence-with-rationale → full causal
chain → thesis/valuation deltas → action classification →
cross-reference against history → contradiction/consistency check →
structured output). Supersedes the architecture doc's §4.5 schema sketch
(safe to do — those tables held zero rows). Key points: (1) new tables
`extracted_facts`, `causal_chain_steps`, `impact_assessments`,
`effect_chains`, `research_task_candidates`, plus a much richer
`investment_implications`; (2) Step 11 ("has this happened before, did
similar announcements move price") explicitly reuses the EXISTING
event-study machinery (`signal.event_window_scores`, built for H-003/
H-005) rather than inventing new pattern-search — the query result is
evidence, not a shortcut around validation; (3) Step 12 (contradiction
handling) reuses `event_pipeline.py`'s existing append-only
conflict-preservation pattern, never overwrites; (4) "never say X without
explaining" is enforced MECHANICALLY — `NOT NULL` explanation columns
everywhere a verdict exists, plus a planned banned-phrase/chain
-completeness validator, not just a prompt instruction; (5) "Hypotheses
Created" and "Portfolio Implications" outputs are explicitly restated as
non-authoritative (Discovery-candidate row only; qualitative note only —
Portfolio Construction remains GATED). Nothing implemented — still
blocked on the same open decisions (LLM vendor, OCR engine) before Phase
D can execute any of this for real.

**REVISION 2 (2026-07-22): added a mandatory self-critique gate (Step
14)** — every reasoning draft (`investment_implications`, now written
initially with `status='draft_pending_self_critique'`) must clear 8
adversarial questions (unevidenced inference? correlation-vs-causation?
ignored alternative explanation? single-document overreaction?
contradicts prior evidence? enough information? what would raise
confidence? just noise?) before it becomes readable by ANY downstream
consumer — a `fail` sets `status='blocked_by_self_critique'` (excluded
everywhere, same as `rejected_by_review`); a `concern` still advances the
row but mechanically discounts confidence and appends the concern to
`confidence_rationale`, never silently. New table:
`self_critique_reviews`. Each question pairs the model's own verdict with
a MECHANICAL check that runs regardless of what the model reports (e.g.
single-document-overreaction is auto-flagged if a `large`/
`transformational` implication traces to exactly one `doc_id`, no matter
what the model says). Key design call: the critique pass must be a
SEPARATE model call from the one that drafted the conclusion (ideally a
different `model_id`, recorded on the row) — a model critiquing its own
same-context output is a known-weak check. Explicitly restated: passing
self-critique does NOT mean validated — it's still
`unvalidated_ai_interpretation`, never cited as if it cleared the
pre-registration/placebo/walk-forward gauntlet. Still design-only, still
blocked on the same open decisions plus two new ones (confidence-discount
-per-concern value, insufficient-information evidence-count floor).

**PHASE C BUILT, TESTED, BLOCKED ON CREDENTIALS (2026-07-22)** — see
`reports/phase_c_completion.md` for the full report; `docs/
EXECUTION_BACKLOG.md`'s new AI-1 item is the single remaining task.
Owner said "start building... follow the architecture exactly... stop
after Phase C and wait for review." Built the FULL reasoning pipeline
(`src/ngxrot/documents/`: providers/prompts/grounding/caching/extraction/
self-critique, ~9 modules) combining what the architecture docs labeled
Phase C (entity/event pilot) + Phase D (reasoning v0) + the Step 14
self-critique gate, since the owner's requirements list spanned all
three. New schema: `causal_chain_steps`, `impact_assessments`,
`investment_implications` (fact_id-keyed, extended with `direction`/
`assumptions` beyond the spec's sketch), `effect_chains`,
`research_task_candidates`, `self_critique_reviews`, `llm_calls` (full
prompt/response/token/model audit trail), plus Step-1 identification
columns on `documents`. **Engineering-tested**: 32/32 checks pass
(`scripts/test_reasoning_pipeline.py`, MockProvider only, isolated
temp DB + cache dir — no pytest anywhere in this project, matched the
existing script-based test convention). Found and fixed 2 real bugs
during this work (cache-key collision between tests sharing identical
prompts; pilot-selection stride sampler silently dropping the sole
`rights_issue` fact to a `.head()` truncation) — both disclosed in the
completion report, not hidden. Also confirmed during pilot-set selection:
the architecture doc's named GTCO/Zenith FY2023 anchor documents have
ZERO native-text coverage (same OCR gap Phase A flagged) — substituted an
18-document stratified sample from the Phase A ∩ Phase B intersection,
documented in `reports/phase_c_completion.md` §3, not silently swapped.
Nothing beyond this combined Phase C scope was built (no News/Macro/
Industry engines, no discovery_feed wiring, no Company Intelligence
integration).

**PROVIDER SWAP: ANTHROPIC → GEMINI (2026-07-22).** Owner directive: use
Google Gemini as the default reasoning-engine provider
(`gemini-3.6-flash`), config-driven, Anthropic dependency removed since
nothing uses it anymore. Changed: `src/ngxrot/documents/llm_providers.py`
(`AnthropicProvider` replaced by `GeminiProvider`, using the `google-genai`
SDK — the current unified SDK, not the deprecated `google-generativeai`
package; added `PROVIDER_REGISTRY`/`LLMConfig`/`load_llm_config`/
`build_default_provider` — the ONE place that maps a config value to a
concrete class), new `configs/llm_provider.toml` (single source of truth
for provider+model — nothing else hardcodes either), `scripts/
run_phase_c_pilot.py` (now calls `build_default_provider()` instead of
constructing `AnthropicProvider` directly; `--model` still overrides for
one run without touching the config file). Zero changes to `extract.py`,
`self_critique.py`, `reasoning.py`, `cache.py`, `prompts.py`, `grounding.py`,
`entities.py`, `json_utils.py`, `vocab.py`, or any schema/table — none of
them ever imported a concrete provider class, confirming the architecture
was already provider-agnostic by construction, not just in name. Added 5
new tests for the config/factory path (`test_provider_config_and_factory`
in `scripts/test_reasoning_pipeline.py`) — **37/37 checks pass**.

**REAL PILOT RUN EXECUTED (2026-07-22), partial: 7/18 documents, quota
-limited.** Owner supplied `GEMINI_API_KEY` directly. Found + fixed 2 real
bugs via a no-DB-writes smoke test before touching real data: (1) Gemini
3.x consumes part of `max_output_tokens` on internal "thinking" tokens
before any visible text — a 20-token budget produced 0 output text with
`finish_reason=MAX_TOKENS`; `GeminiProvider.complete()` now raises
clearly instead of returning empty text as a false "nothing here" signal;
`extract.py`/`self_critique.py` bumped to 16384/8192 tokens. (2)
`stop_reason` was storing the raw Python enum repr — fixed to a clean
string. **Real results, 7 documents**: 100% precision/recall on the
numeric figure vs. Phase B ground truth (3/3 overlapping cases agreed
exactly); 2 real, grounded values found that Phase B's deterministic
extractor had missed entirely; 1 suspect value correctly caught by the
grounding check (quote not verbatim in source → forced to 0 confidence);
1 pre-existing Phase B misclassification surfaced (NEM's 2-for-1 share
reconsolidation was mislabeled `bonus_split` — the model correctly
declined to force-fit it into the pilot's 3 fact types rather than
fabricate a match). **Most important result: the self-critique gate
blocked a real reasoning flaw** — GTCO's ₦400.5bn dilutive share offer
was drafted `bullish`/`large`, and the critique pass (a separate call)
returned 3 fails (wrong corporate-action classification, ignored
regulatory-recap alternative, asserted bullish without assessing 23%+
dilution) → `status='blocked_by_self_critique'`, correctly excluded from
every consumer. **Stopped at document 7 of 18**: hit Google's free-tier
quota (20 `generate_content` requests/day/project for `gemini-3.6-flash`
— confirmed via the API's own 429 response, not a guess). `tenacity`
retried correctly before honestly re-raising; nothing was fabricated to
paper over the gap. Full detail, including the exact self-critique
explanations and every disagreement: `reports/phase_c_completion.md`.

**PIPELINE HARDENED (2026-07-22, same day)** — owner directive after
seeing the quota interruption: resumability, quota handling, cache
auditability, prompt-version tracking, and machine-readable metrics.
68/68 engineering tests pass (was 32 at Phase C start → 37 after the
Gemini swap → 68 now).

- **New table `document_processing_status`** (doc_id PK, status ∈
  {pending, processing, completed, failed, quota_exceeded,
  blocked_by_self_critique}, fact_count, implication_count, error_detail,
  model_id, prompt_version, started_at, updated_at) — the fast resume
  signal, backed by `src/ngxrot/documents/pipeline_status.py`. Never
  trusted alone: `should_skip()`/`resume_point()` cross-check the actual
  `extracted_facts`/`investment_implications` rows, so a stale status
  (e.g. process killed between "mark processing" and "mark completed")
  can never cause a document to be silently re-extracted.
- **New table `llm_calls.document_hash`** column (sha256 of the source
  document text alone, distinct from the full-prompt `cache_key`) — an
  explicit, queryable "has this document's text changed" signal.
  `cache.py` gained `invalidate_cache_for_doc()` (deletes the on-disk
  cache files tied to a doc_id, logs the invalidation to the existing
  `data_quality_log` table — auditable, never silent).
- **New columns `investment_implications.model_id`/`prompt_version`** —
  this table previously had NEITHER (only `extracted_facts` and
  `self_critique_reviews` did); backfilled the 8 existing rows from their
  parent fact. A future prompt version change is still always a NEW row
  (append-only, unchanged) — this addition is about queryability, not a
  new guarantee (the "never overwrite historical results" guarantee was
  already structurally true).
- **`QuotaExceededError`** (new exception in `llm_providers.py`):
  `GeminiProvider` now catches Gemini's 429/RESOURCE_EXHAUSTED response
  and raises this specific type; `cache.py`'s tenacity retry wrapper
  explicitly excludes it (`retry_if_not_exception_type`) so a daily quota
  failure propagates on the FIRST occurrence instead of burning 4 retry
  attempts that can't possibly help. `run_phase_c_pilot.py` catches it at
  the per-document level, marks that doc `quota_exceeded`, prints how many
  documents remain, prints a best-effort/clearly-labeled resume-time
  estimate (the SDK's own short retryDelay hint if present, plus an
  EXPLICITLY UNCONFIRMED "commonly resets near UTC midnight" guess — never
  asserted as Google's documented behavior), writes the pilot summary, and
  exits with code 2 (not a raw traceback).
- **`reasoning.resumable_financial_reasoning()`** (new, additive —
  `financial_reasoning()` itself is UNCHANGED so its existing callers/
  tests keep their exact behavior): checks `pipeline_status.resume_point()`
  before doing anything; if this document already has model-sourced
  `extracted_facts` (from a prior run interrupted after extraction but
  before/during critique — exactly what the real UCAP quota failure left
  behind), extraction is skipped entirely and only implications still
  `draft_pending_self_critique` are critiqued. Proven by a real test that
  simulates exactly this interruption and asserts `extracted_facts` count
  stays at 1, never 2, across repeated calls.
- **`run_phase_c_pilot.py` rewritten**: resumable end-to-end
  (`--force` bypasses this deliberately, not by default), prints
  already-done/remaining counts up front, marks status transitions before
  each risky step (durable independent of whatever transaction extract.py
  has open), catches per-document non-quota exceptions and continues to
  the next document (marks `failed`, doesn't abort the whole batch),
  writes the pilot summary after every exit path (natural completion,
  quota exit, or "nothing to do").
- **`src/ngxrot/documents/pilot_summary.py`** (new, shared by both
  `run_phase_c_pilot.py` and `validate_phase_c_extraction.py` so they can
  never silently disagree): computes documents processed/failed/quota
  -exceeded, precision/recall, grounding-failure rate, self-critique
  rejection rate, avg latency, token totals, cache-hit rate, and an
  **assumed-rate** cost estimate (0.0 placeholder, `configs/
  llm_provider.toml`'s new `[llm.cost_assumed]` section, `confidence
  ="assumed"` — same discipline as the quant engine's `cost_schedule`
  table for unconfirmed retail brokerage rates; free-tier pilot cost is
  genuinely $0, this only matters on a paid tier). Writes both
  `reports/phase_c_pilot_summary.json` (machine-readable) and `.md`.
- **Backfilled `document_processing_status`** for the 7 documents
  processed before this hardening pass existed (the table didn't exist
  yet when they ran) — verified `remaining_doc_ids` now correctly reports
  9 remaining (the interrupted UCAP doc, which needs only its critique
  step re-run, plus 8 never-touched documents), not 17.
- **Found and fixed a real, PRE-EXISTING bug during this work** (not new
  hardening code — a scope bug in `scripts/validate_extracted_facts.py`,
  written when only Phase B facts existed): it queried ALL `extracted_facts`
  rows with no `model_id IS NULL` filter, so once Phase C added LLM
  -sourced rows to the same table, this Phase-B-only validator started
  reporting them as false failures (no matching row in
  `corporate_actions_extracted.csv`, which Phase C rows were never built
  from). Fixed the filter; also found and repaired REAL damage from an
  earlier session action: cleaning up two Gemini smoke-test documents
  (doc_id 5531/8714) had deleted `evidence` rows `WHERE doc_id=?` without
  scoping to LLM-sourced facts only — those two doc_ids ALSO had their own
  independent Phase B facts (27, 81) whose evidence got deleted as
  collateral damage. Repaired by reconstructing both evidence rows from
  the facts' own `description` field (the exact format
  `build_extracted_facts_deterministic.py` originally used) and
  re-pointing `extracted_facts.evidence_id`. Both validators pass clean
  now (`validate_extracted_facts.py`: 143/143 Phase B rows; `validate_
  phase_c_extraction.py`: 8/8 LLM rows, schema-complete).
- **Governance preserved, verified not just asserted**: grounding.py,
  self_critique.py's mechanical checks, vocab.py's fixed vocabularies, and
  extract.py's core Steps 1-13 logic are UNCHANGED (diffed against the
  pre-hardening version — the only edits to extract.py were adding
  `document_hash` to the existing draft call and two new columns to the
  existing `investment_implications` INSERT, no logic change). No import
  of `ngxrot.documents` anywhere in `alpha_engine.py`/`runner.py` (checked
  again). Confidence scoring axes, the unreviewed-LLM floor, and the
  append-only "never overwrite" discipline are all unchanged.

**Owner decision needed**: wait for quota reset, reduce pilot size, or
upgrade tier to process the remaining 9 documents — the resumability is
now in place so whichever is chosen, rerunning `scripts/
run_phase_c_pilot.py` will pick up exactly where it left off.

**PHASE B IMPLEMENTED AND COMPLETE (2026-07-22)**, per owner's "start
building, follow the architecture exactly, extend rather than duplicate"
directive. Inspected the codebase first (as instructed) and found the
architecture doc's Phase B description didn't quite match reality:
EPS/P.E. extraction was already attempted and REJECTED
(`reports/eps_pe_extraction_status.md`, both heuristics failed the 95%
bar — no output exists to relabel), and the only real per-document
deterministic dividend/date extractor output is
`data/staging/xissuer/corporate_actions_extracted.csv` (397 filings, from
`scripts/build_corp_actions_db.py`, already validated when built) — NOT
the larger `exdiv_closure_calendar.csv` (2,829 DOL snapshots), which is an
aggregated closure-date-RANGE calendar built from a DIFFERENT archive
(`data/archive/dol_equities/`) not yet represented in `documents` (Phase A
only covered the xissuer corp-actions archive) — scoped Phase B to the
former only and flagged the latter as a follow-on decision rather than
silently expanding scope. Built: `evidence`/`extracted_facts` tables added
to `schema/schema.sql` (additive; `extracted_facts` gained
`numeric_value`/`qualification_date`/`payment_date`/`agm_date`/
`closure_date` columns beyond the design doc's sketch — a real gap
surfaced by actually building it, since the sketch had nowhere to put a
regex-extracted number). `configs/fact_taxonomy.toml` created for real
(previously only sketched inside the spec doc's markdown — never
materialized as an actual file; added a missing `bonus_issue` leaf while
at it). `scripts/build_extracted_facts_deterministic.py` joins
`corporate_actions_extracted.csv` to the SAME `documents` rows Phase A
created (via the identical `archive_file`/`local_path` filename
convention — confirmed exact match, 0 join misses) and writes
143 `extracted_facts` + `evidence` rows (141 dividend, 1 rights_issue, 1
bonus_issue) at `extraction_confidence=1.0`. **Validated**:
`scripts/validate_extracted_facts.py` (new, standalone, rerunnable —
matches this project's existing validate_*.py convention rather than a
pytest suite) — PASS, 0 issues across all 143 rows (doc_id-keyed
numeric/date reproduction, evidence-link consistency, doc_id resolution,
fact_type taxonomy membership). Caught and fixed a real bug during this
work: the build script's first inline validation pass matched
symbol+fact_type instead of doc_id and produced 28 false-positive
mismatches (a ticker with dividends in multiple years collided) — fixed
to doc_id-keyed matching, confirmed 0 true mismatches; also fixed the
completion report to show CUMULATIVE table state instead of
just-this-run counters (same bug class Phase A's report had — an
idempotent no-op rerun was blanking the numbers). Confirmed idempotent:
rerunning after completion correctly processes 0 new rows. **Documented,
honest limitation**: the GTCO/Zenith FY2023 dividend anchors are
scanned-image PDFs with no text layer (same OCR gap Phase A already
flagged) — this text-based extractor structurally cannot reach them, so
the architecture doc's "reproduce the GTCO anchor" Phase B completion
criterion is blocked on the same pending OCR decision, not a new problem.
Full detail: `reports/phase_b_completion.md`. **Stopping here for
review, per instruction, before Phase C** (which needs the LLM vendor
decision — still open — and is a bigger jump: the first real LLM
extraction pilot).

Background reading (all 2026-07-22, do not re-derive — cross-referenced
from the backlog): `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`
(per-hypothesis failure classification), `docs/WAVE_3_RESEARCH_DIRECTIONS.md`
(candidate scoring), `docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md`
(dependency map + maturity scores + 3-year roadmap),
`docs/PLATFORM_ARCHITECTURE.md` (short-form module summary).

## What this project is

**Fund Alpha**: an AI Investment Intelligence Platform for Nigerian equities
(owner directive 2026-07-21/22 — full 9-module target architecture in
`docs/PLATFORM_ARCHITECTURE.md`, modules 1-3 live, modules 4-9 explicitly
GATED behind having ≥1-2 validated factors — do not scaffold them early).
The existing research engine IS the platform core; the hypothesis workflow
is the Factor Validation Engine, unchanged. Success metric = validated
independent factors (currently **0**; 9 honest rejections — process
working, not stalling). Concurrency rule (owner): **never more than 2
active hypotheses at once**; each wave completes before the next begins.
Every prereg includes an "Expected Interaction with Existing Factors"
section; every completed experiment updates `docs/FACTOR_REGISTRY.md`
(the permanent knowledge base — READ IT before proposing anything, it has
full evidence trails and explicit successor-design guidance per
rejection). Charter: `docs/FUND_ALPHA_CHARTER.md`.

## WAVE 1 + WAVE 2 COMPLETE (2026-07-22): H-006 through H-009 all REJECTED

Full results in `docs/FACTOR_REGISTRY.md`. Summary, most informative first:

- **H-009 (turnover-budgeted momentum, annual/semiannual)**: the wave's
  most nuanced result. Turnover reduction WORKED — net excess flipped
  positive (+2.66%/yr vs H-007's −6.26%/yr), 6/6 grid cells positive,
  positive in all 3 regimes incl. OOS. But placebo p=0.069, a NEAR-MISS
  against the 0.05 bar (no threshold relaxed). Diagnosis: annual cadence
  over 9 years yields only ~9 independent decisions — a POWER problem,
  not a sign or cost problem. Do NOT rerun this exact design; pool
  multiple staggered momentum implementations or use an overlapping-
  cohort design to raise bet-count while keeping turnover low (new ID).
- **H-006 (PEAD)**: High-confidence rejection (862 decisions, corrected
  p=0.000 on the gross effect) — the reaction-magnitude RANKING carries
  no selection skill over any cohort event; capped-slot book turnover
  ~10x the estimate. Successor: event-MEMBERSHIP-only design (new ID).
- **H-007 (quarterly momentum)**: gross effect real but ~3x smaller than
  its own cost; statistically noise (placebo p=0.644). Directly
  motivated H-009.
- **H-008 (low-volatility)**: the cleanest, simplest rejection — a
  STATISTICALLY ROBUST NEGATIVE tilt (6/6 cells Holm-significant in the
  wrong direction), not merely an absent effect. Likely cause: NGX
  2016-2026 has had violent regime transitions (FX crisis, COVID, float)
  that reward risk-taking over the calm backdrop low-vol needs. A
  regime-CONDITIONAL retest (e.g. post-2023 stabilization only) would be
  a legitimate new hypothesis; an unconditional retest is not.

Built this wave: `src/ngxrot/backtest_xs.py` — cross-sectional per-stock
engine (rank/vol/event-book modes), `engine.type = "cross_sectional"` in
`runner.run_resolved`/`phase4.py`, inheriting every guard unchanged.
Extended mid-wave: `xs_vol` signal method + annual/semiannual rebalance
cadence, both synthetically rehearsed before real use
(`scripts/rehearse_xs_engine.py`, `scripts/rehearse_xs_engine_v2.py`).
The v2 rehearsal caught a bug in my OWN test design, not the engine: a
"vol-neutral null panel" wasn't actually neutral because variance drag
creates a real link between volatility and compounded return that the
test hadn't compensated for — fixed before trusting the result. Also
fixed this session: `ic_report.py` had H-001's hypothesis text hardcoded
into every memo since H-003 (quantitative content always correct; only
the prose was wrong) — now pulls the ledger description live.

## PARALLEL ENGINEERING THIS SESSION (owner-approved, ran alongside research)

- **Corp-actions archive: DONE**, 11,187/11,546 (97%; remainder are
  permanent 404s, same pattern as the pricelist gaps).
- **Market-cap panel: DONE, validated** —
  `data/reference/market_cap_panel.csv` (328,023 rows / 218 symbols /
  2,182 days, 2016–2026, from PRICES_LIST2). Implied-share-count stability
  check clean (0.39% day-over-day jumps >2%). Unlocks Size factor +
  eventual cap-weighted benchmark. Full-issue cap only (not float-adjusted
  — shares-outstanding/free-float remains a separate backlog item).
- **EPS/P.E. parser: ATTEMPTED, NOT VALIDATED, deprioritized.** Two
  extraction heuristics tried against the DOL's crowded trailing columns;
  neither cleared the 95%-pass validation bar (58% and 34%). High-price
  names (DANGCEM, NESTLE, MTNN, TOTAL...) have blank fields on many days
  that both heuristics silently misread. Full writeup + exact failure
  modes: `reports/eps_pe_extraction_status.md`. Also found: the DOL's
  "Div" column contradicts the verified GTCO FY2023 anchor (real payout
  ₦2.70; naive read returned ₦0.50 — the par-value column bleeding
  through) — do not trust that region for dividend cash amounts; the
  corp-actions PDF pipeline remains correct for that.

## MILESTONE: COVERAGE GATE v2 PASSED (2026-07-21)

**12 ready years (2015–2026), no threshold changes.** Freeze doc:
`docs/DATA_FREEZE_2026-07-21.md` — preregs pin `vintage_date=2026-07-21`,
`requires_coverage_gate=true`, IRU v2. Panel: 320,159 rows / 308 tickers /
2,933 days @ conf 0.9 across 3 validated sources (ngx_pricelist_v1;
ngx_dol_v1 = 170 close-only gap days; ngx_list2_v1 = 7 days).
Pricelist parser is now v2 (2026-07-21: glued VOLUME/VALUE token repair —
see pricelist_parser.py docstring); daily --delta ingests land as
ngx_pricelist_v2. Historical v1 rows stand (54 glued rows restated via
scripts/restate_glued_volumes.py, verified identical to v2 reparse).
Day-completeness 95.1–100% every full year. Equity jump residue: 3 flags in
12 years (the other 113 are ETFs/sukuk — outside the ±10% band premise and
outside the IRU).

## Non-negotiable rules (unchanged — SQL/config-enforced, do not soften)

1. Every hypothesis/factor: pre-registered (criteria + untouched OOS before
   any run), unique ID, mechanical verdicts.
2. Immutable registry (`data/registry.sqlite`); experiments ONLY via
   configs (`scripts/run_experiment.py` / `runner.run_resolved`).
3. Gate thresholds: IC decision only. The gate re-evaluates on every equity
   ingest; runner refuses gated configs if it regresses.
4. Unknown stays unknown; never fabricate; primary sources for dates;
   archive-first; append-only PIT with restatement vintages (readers:
   `db.*_asof`, latest-vintage-wins — diagnostics dedupe the same way).
5. Priority test for ANY work: "does this increase the probability of the
   next validated factor?"

## IMMEDIATE NEXT STEPS (wave 3 — not started, awaiting owner direction)

9 hypotheses tested, 0 validated, 9 rejected — every rejection carries
specific successor guidance in `docs/FACTOR_REGISTRY.md`. Do NOT rerun any
prior design unchanged (esp. H-009 — its near-miss placebo is a power
problem, not a coin flip worth retrying). Live successor candidates:
- **Pooled/overlapping-cohort momentum** (H-009 successor): raise
  independent bet-count while keeping per-implementation turnover low —
  the most directly evidence-motivated candidate in the whole program so
  far (H-009 showed the SIGN and PLATEAU are right; only power is missing).
- Event-MEMBERSHIP-only PEAD (H-006 successor, unranked, turnover-costed
  differently from the capped-slot book).
- Regime-conditional low-vol (H-008 successor, e.g. post-2023 only, as
  its own hypothesis with its own OOS split — NOT the same unconditional
  design).
- A genuinely new family not yet touched: Value (E/P) or Dividend Yield
  once the DOL EPS/dividend parser is re-attempted and validated (see
  backlog); Size using the now-validated market-cap panel.
Draft as full pre-registrations (economic rationale + Expected Interaction
section) and show the owner before running, per convention. Consider
whether "pooled momentum" deserves priority given how close H-009 came —
it's the strongest lead this program has produced to date.

## Backlog (priority order)

- PRICES1 parser v2: fix glued VOLUME+VALUE at source (done 2026-07-21;
  monitor for recurrence on new daily ingests).
- DOL-day close precision restatement via gainers cross-check (177
  single-source days; gainers 'prev' column = unadjusted official close).
- vwap_inconsistent warn backlog (469 rows incl. zero-value days
  2015-05-28 / 2017-07-12 — chips pending).
- Verify/apply 49 candidate renames (`data/reference/symbol_renames.csv`).
- EPS/P.E. parser retry as its own scoped session (per-format-era
  calibration needed — see `reports/eps_pe_extraction_status.md`).
- Shares Outstanding harvest (capacity, float-adjusted Size); T-bill curve.
- Daily-capture scheduling (user-gated): `scripts/daily_capture.py` MUST
  run every trading day; each missed day is lost forever.
- Corp-actions OCR decision (user-gated; archive itself is now 97% done).

## Key machinery + hard-won parsing facts

`src/ngxrot/`: db (bitemporal) · runner · phase4 · ic_report · universe
(IRU v2) · coverage (gate) · page_layout (char-level) · pricelist_parser ·
**dol_price_parser** ('Market Price' col = official close, calibrated per
page by header x1; DOL 'Qty' = LAST TRADE size, NEVER daily volume) ·
**list2_parser** (sector-format price list; name→ticker via era-matched DOL
security names) · **gainers_parser** (officially ADJUSTED bases printed in
parentheses; zip naming unreliable — index by INTERNAL start/end dates) ·
event_pipeline · alpha_engine (honest no-position shell).

- pdfplumber `page.chars` DRAW ORDER preserves text runs — use it over
  geometric chaining for interleaved columns (some bd dates even live in a
  vertically offset glyph band; match page-wide date runs to rows by top-y).
- Some DOLs are intraday prints (2022-03-16: 34% of closes differ from
  final; ~1.7% of days, undetectable per-file) — documented risk on
  single-source days (`data_quality_log` 'single_source_day').
- index_levels contains HOLIDAY PADDING (carry-forward rows on Dec 25
  etc.) — the verified market calendar = index days whose value CHANGED.
- PRICES1 PCLOSE = officially adjusted base → close/pclose is the official
  within-band return (jump-scan certification source b).
- PRICES1 glued-token bug: wide VOLUME+VALUE merge into one word (volume
  ~1e17+, value NULL). Diagnostics: `implausible_volume` (>1e12) +
  `vwap_inconsistent` ([0.25,4]×close), computed on latest vintage.
- Jump scan evidence hierarchy: (a) spans verified missing market day →
  legal multi-session; (b) NGX-certified within-band off adjusted base
  (gainers OR pclose); (c) closure/earnings ±3bd.
- Reference calendars: `exdiv_closure_calendar.csv` (1,044 closure events) ·
  `gainers_transitions.csv` (138k mover rows, 5,338 adjusted bases) ·
  `official_prev_close.csv` (2,763 days) · `earnings_calendar.csv`.
- Sector-level research is DEAD (breadth math:
  `docs/RESEARCH_MEMO_PERSTOCK_PIVOT.md`). Never propose sector variants.
- NGX doclib SharePoint is OPEN (OData), primary source:
  `_api/Web/Lists/GetByTitle('XFinancial_News'|'DownloadsContent')`;
  files at `doclib.ngxgroup.com/DownloadsContent/<Title>.<ext>`.
  investing.com: rate-limited; cross-check only.
- Launch python via PowerShell (`python -u`), NOT Git Bash (exit 127).
- Pending user decisions: tesseract OCR; daily-capture scheduling;
  parallel-FX + broker research (ethics/licensing-gated).
- Open queue behind H-006/H-007: F4 liquidity premia, F6 dividend capture,
  F13 size/low-vol/reversal, Discovery module (post-breadth, per design doc).
