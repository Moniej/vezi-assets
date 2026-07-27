# Phase E Completion Report — Financial Reasoning Engine extensions (2026-07-26)

Owner-approved scope (2026-07-26): four additive extensions on top of Phase
C's "Knowledge Layer" (`src/ngxrot/documents/`), plus a `ReasoningContext`
abstraction. Nothing rebuilt; nothing in the hard boundary
(`ngxrot.documents` never imported by `alpha_engine.py`/`runner.py`)
touched. No vector search introduced. Grounding and self-critique are
unchanged — every new module either calls the existing gated pipeline
(`resumable_financial_reasoning`) or aggregates rows that already passed
through it.

## What was built

**`src/ngxrot/documents/retrieval.py` — structured (SQL-first) retrieval.**
`RetrievalQuery` + `retrieve_documents()` is the one seam a future semantic
retriever would sit behind — every other finder (`find_facts`,
`find_events`, `find_entity_relationships`, `find_prior_implications`)
is a convenience wrapper. `find_events` is a thin filter over the
existing, unchanged `db.events_asof` — no new event-reading logic.

**`src/ngxrot/documents/context.py` — `ReasoningContext` +
`build_reasoning_context`.** One object holding: documents, facts,
evidence, events, event_reaction_stats, entity_relationships,
factor_exposures (via `company_intelligence.build_profile`, reused not
reimplemented), historical_implications, coverage_notes. Every new
reasoning module consumes this instead of issuing its own queries, per
the owner's explicit requirement.

Also here: `historical_event_reaction()` — "has this happened before, did
it move price," computed from `db.events_asof` + `db.equity_prices_asof`
directly. **Deliberate deviation from the letter of the approved spec**,
disclosed here rather than silently substituted: the spec named
`signal.event_window_scores` as the mechanism to reuse. Reading that
function during implementation showed it builds PORTFOLIO TARGET WEIGHTS
(enter=1.0/exit=0.0 rows for the backtest engine) — a different output
shape than something citable as evidence in a `ReasoningResult`. Rather
than force that mismatch, `historical_event_reaction` reuses the same
underlying PIT primitives `event_window_scores` itself is built from and
produces a descriptive statistic (mean/median reaction, per-event
breakdown) instead. Same data, no second event-study engine, just a
different summary for a different purpose.

**`src/ngxrot/documents/reasoning_engine.py` — question-driven
orchestrator.** `reason_about_company(con, provider, ticker, ...)`:
loads a `ReasoningContext` → checks for unextracted candidate documents
→ if any exist (capped at `max_new_documents=5` per call, to bound API
spend), runs them through the UNCHANGED `resumable_financial_reasoning`
→ reloads the context → assembles a `ReasoningResult` (one `FactSummary`
per fact: causal chain, all 13 impact categories, the implication row,
effects by order 1/2/3, principal risks, alternative explanations and
contradicting evidence surfaced from the existing self-critique rows,
confidence-improving info from `research_task_candidates`,
factor_exposures, event_reaction_stats). This assembly step makes **no
new LLM call** — it aggregates rows that already passed grounding and
self-critique when they were created, so there is nothing new to gate.

**`entities.py`: `record_relationship()`, wired into `extract.py`'s
effect_chains loop.** `entity_relationships` existed since Phase C but
nothing ever wrote to it (confirmed by grep before starting). Now: every
`effect_chains` row with a grounded quote (`eff_evidence_id is not None`)
AND a real, non-self affected entity also persists a durable
`entity_relationships` edge — evidence-backed, confidence-scored (capped
at the same unreviewed-LLM floor as everything else), reproducible
(idempotent on the same evidence_id). Ungrounded effects create **no**
edge — "never infer relationships without supporting evidence" is
enforced at this one call site, not left to convention.
`relation_type` is deliberately the literal `affects_order_{1,2,3}` fact
already computed, never an invented taxonomy label (`competitor_of`,
`supplier_to`) the model was never asked to classify — inventing a more
specific relationship type than the evidence supports would itself have
been a small fabrication.

## AI-1 (unrelated pilot resume, done first per owner instruction)

Resumed and completed the remaining 9/18 pilot documents before this
work started (see `docs/EXECUTION_BACKLOG.md`'s AI-1 entry): precision
90.0%, recall 100.0% vs. Phase B ground truth, self-critique gate ran
completely on every draft, 3/17 implications `blocked_by_self_critique`.
Confirmed independent of this Phase E work, as instructed.

## Tests

`scripts/test_reasoning_pipeline.py`: **90/90 checks pass** (68 pre-existing
+ 22 new — retrieval layer, context assembly and coverage detection,
entity-relationship population from a grounded effect, `record_relationship`'s
self-relationship/duplicate rejection, `historical_event_reaction`'s
sufficient/insufficient-sample paths, and the orchestrator's end-to-end +
idempotent-second-call behavior). All new tests use `MockProvider` against
an isolated temp database, same convention as every existing test — no
real API calls, no real database touched.

One real bug found and fixed while writing tests, not after: `context.py`'s
first version called `company_intelligence.build_profile()` unconditionally,
which internally requires the full quant equity panel (`backtest_xs.
load_panel`) to be non-empty — this crashes on the synthetic test database
(and would crash on any ticker outside panel coverage in the real one too).
Fixed by wrapping the call in `context.py` and degrading to an empty
`factor_exposures` dict plus an explicit coverage note on failure, instead
of propagating the exception — "unknown stays unknown" applied to factor
exposures the same way it's applied everywhere else in this codebase.

## New technical debt (for `docs/EXECUTION_BACKLOG.md`'s TD table)

| item | risk | why |
|---|---|---|
| `evidence.event_id` remains permanently unpopulated | LOW | Event evidence flows through `ReasoningContext.events`/`event_reaction_stats` instead, which have their own provenance (`events.source_id`/`source_url`) and don't need document-quote grounding — `evidence.doc_id NOT NULL` makes the reserved column structurally unfit for event-only evidence. Intentional, documented here so a future reader doesn't treat the empty column as an oversight to "finish." |
| `entity_relationships.relation_type` is a literal `affects_order_N` label, not a semantic taxonomy | LOW-MEDIUM | Honest given what the model is actually asked to produce today (no relationship-type classification in the draft prompt), but limits graph traversal — "which entities are TESTCO's competitors" cannot be queried directly, only "which entities has TESTCO's reasoning ever named as affected." Upgrading this needs a prompt change (ask the model to classify the relationship nature) before the schema value would mean anything more specific. |
| Entity resolution's known Phase C limitation (exact case-insensitive name match, no merge queue — see `entities.py`'s original docstring) now has a higher blast radius | MEDIUM | Previously a wrong non-merge only fragmented a `canonical_name`'s mention count; now it also fragments (or wrongly consolidates) the persisted relationship graph. Same mitigation as before (small pilot scale) — worth revisiting before this graph is used at real scale. |
| `historical_event_reaction` is new, single-purpose, and unvalidated against any real anchor | LOW | Engineering-correctness tested only (synthetic price series, MockProvider-free). It never feeds `alpha_engine`/`runner` (evidence-only, same hard boundary as everything else in this package) so the validation bar is lower than a quant-engine parser's — but a real sanity check against a known NGX event (e.g., an MPC hike and GTCO's actual reaction) hasn't been run. |
| `reason_about_company`'s retrieval trigger can cost up to `max_new_documents` × 2 real LLM calls per call | LOW | Capped (default 5 → ≤10 calls), and every triggered document goes through the same quota-aware, resumable pipeline as the pilot — but a caller invoking this per-ticker across many tickers should be aware it's not a free/local operation. |

## Explicitly out of scope, per owner's stop instruction

Self-critique redesign and any local/Qwen model work. `LLMProvider`'s
existing factory pattern already makes a future `QwenProvider` a small,
additive class (see `llm_providers.py`'s module docstring) — no
architecture change is needed there when that work starts, but no such
provider was added in this pass.

Stopping here for review, as instructed.
