# Phase F Completion Report — Industry Reasoning Engine (2026-07-26)

Owner directive: continue the A→G AI Intelligence Layer roadmap, Phase F
(architecture doc §4.5) — peer/competitor propagation via the knowledge
graph, building on Phase E's `entity_relationships` edges. Additive only;
no schema migration; hard boundary (`ngxrot.documents` never imported by
`alpha_engine.py`/`runner.py`) unchanged; no vector search; grounding and
self-critique untouched.

## Two premises in the original design that didn't hold once inspected

The architecture doc's §4.5 sketch was written before Phase E actually
populated `entity_relationships`, and made two assumptions that turned
out not to match what got built. Both are documented deviations, not
silent substitutions:

1. **Assumed `relation_type` would already hold classified values like
   `competitor_of`.** Phase E populated it with the literal
   `affects_order_{1,2,3}` fact instead — the extraction prompt never
   asks the model to classify relationship *nature*, only to name an
   affected entity (see `entities.py`'s docstring). Propagation
   (`industry_reasoning._peer_tickers`) walks any `affects_order_*` edge
   whose object entity has `entity_type='competitor_mention'` — today
   that is every such edge by construction (`extract.py` types every
   non-self affected entity that way), so the filter is currently a
   no-op in practice but becomes a real one the moment entity typing
   gets more precise (a genuine `regulator`/`sector` distinction, say).
2. **Assumed peer entities would resolve to a real ticker.** They never
   did — nothing before this pass attempted to map a free-text mention
   like "ZENITHBANK PLC" to `securities.ticker`. Added
   `entities._exact_name_match_ticker`: exact, case-insensitive,
   trimmed match against `securities.name` only. Deliberately NOT fuzzy
   — this platform's standing rule is "never guess a match"
   (`data/reference/symbol_renames.csv`'s verified-only discipline,
   Phase A's `raw_symbol` resolution). **Disclosed coverage limitation**:
   most real mentions ("GTBank" for GTCO, "Zenith" for ZENITHBANK) will
   NOT resolve under this rule, so propagation volume will be low until/
   unless a verified alias table is built — an accepted trade-off, not a
   bug to silently paper over with fuzzy matching.

## The third, larger deviation: no algorithmic direction inversion

The architecture doc's own illustrative example ("Company A cuts prices"
→ "Company B may face margin pressure") implies inferring the *direction*
of the effect on the peer — i.e., a rule that a competitor's implication
should sometimes invert. This was deliberately **not** built. Inferring
whether a peer is helped or hurt by another company's action is an
economic-mechanism judgment, and this platform has never allowed that
kind of inference to come from a hardcoded rule instead of an
evidence-grounded, self-critiqued reasoning pass — building one now would
be the same category of fabrication risk the self-critique gate exists to
catch. Propagated implications therefore:

- copy the source's `direction`/`magnitude`/`duration_bucket` **unchanged**,
- get `confidence = source.confidence × vocab.INDUSTRY_PROPAGATION_CONFIDENCE_DISCOUNT`
  (default 0.5 — architecture doc's own open decision #6, "TBD with
  owner before Phase F"; picked a reasonable default and disclosed it
  here, same pattern as `CONFIDENCE_DISCOUNT_PER_CONCERN`; owner-adjustable
  in `vocab.py`),
- get `status='under_review'` — never `unvalidated_ai_interpretation`,
  because that status implies the self-critique gate ran on *this*
  implication, which it did not (there is no new LLM output to critique;
  propagation makes zero new LLM calls),
- always come with a mandatory `research_task_candidates` row asking a
  future pass to actually determine the peer-specific direction.

Propagation is a **flagging mechanism** ("this peer may be relevant to
this event, here is the evidence trail back to the source"), not a
directional call. This is a narrower interpretation of the architecture
doc than its own example suggests — flagged here explicitly so the owner
can decide whether a future LLM-driven peer-direction assessment pass is
worth building, rather than that gap being invisible.

## What was built

- **`entities.py`**: `_exact_name_match_ticker()` (above), wired into
  `resolve_or_create_entity()`.
- **`src/ngxrot/documents/industry_reasoning.py`**: `propagate_implication()`
  — one-hop-only (refuses to propagate an implication that is itself a
  propagation — no chains), idempotent (reruns return the same
  implication_ids, never duplicate rows), refuses `blocked_by_self_critique`
  sources, bounded fan-out (`MAX_PEERS_PER_IMPLICATION=10`).
- **`retrieval.py`**: `find_peer_propagations(ticker)` — implications a
  ticker received *as a peer*, distinct from `find_prior_implications`
  (implications a ticker's own facts produced).
- **`context.py`**: `ReasoningContext.peer_propagations`.
- **`reasoning_engine.py`**: `reason_about_company` now propagates any
  implication that came from a document *this call* newly processed (not
  the whole graph's history on every call), recording
  `propagated_implication_ids` on the `ReasoningResult`; also surfaces
  `peer_propagations_received`.
- **`vocab.py`**: `INDUSTRY_PROPAGATION_CONFIDENCE_DISCOUNT = 0.5`.

No schema migration: `investment_implications.propagated_from_implication_id`
already existed (added at Phase C build time, unused until now). Propagated
rows reuse the **source fact's `fact_id`** (not a new fact) — fully
auditable back to the real extracted fact/document via
`propagated_from_implication_id` → source implication → its `fact_id`.

## Tests

`scripts/test_reasoning_pipeline.py`: **106/106 checks pass** (90
pre-existing + 16 new: ticker-resolution match/no-match, propagation core
mechanics — targeting, status, discounted confidence, unchanged direction,
paired research task, one-hop guard, idempotency — blocked-implication
exclusion, and orchestrator wiring both directions (a company propagating
out, a peer receiving it via its own `reason_about_company` call).

One real bug found while writing these tests: two new tests reused
identical document/draft content (by design, to isolate the propagation
logic from extraction), and `cached_complete`'s `force=True` path
**overwrites** the on-disk cache entry, not just bypasses reading it — a
later force=True test with a *different* canned critique response
silently poisoned a subsequent non-forced test that shared the same cache
key. Fixed by adding `force=True` to the affected test call, with the
mechanism documented inline (this is a property of the existing
`cache.py`, not something Phase F changed — a latent cross-test hazard
that happened to get triggered by this session's specific test content
reuse, not a new bug introduced by this phase).

## New technical debt

| item | risk | why |
|---|---|---|
| Peer ticker resolution is exact-match-only, so propagation coverage will likely be low in practice | LOW-MEDIUM | Disclosed trade-off (never guess a match) rather than a defect. A verified alias table (mirroring `symbol_renames.csv`) would raise coverage without violating the no-guessing rule — not built now, no trigger yet (zero real propagations have been observed against production data). |
| No LLM-driven peer-direction assessment exists yet | LOW | The mandatory research_task per propagation is the intended queue for this; nothing consumes that queue automatically yet. Same "Discovery-candidate, not authoritative" pattern as the rest of this package — by design, not an oversight. |
| `industry_reasoning.propagate_implication` untested against real production data (MockProvider/synthetic DB only) | LOW | Same class of caveat already carried by `historical_event_reaction` (Phase E) and every pre-real-pilot Phase C module — engineering-correctness proven, real-world behavior not yet observed. |

## Explicitly out of scope, per prior owner instruction (unchanged)

Self-critique redesign and any local/Qwen model work. Not touched.

Stopping here for review.
