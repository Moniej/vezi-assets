"""Financial Reasoning Engine (FRE) — read-mostly layer on top of the
existing, frozen AI Intelligence Layer (docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md,
docs/REASONING_ENGINE_SPECIFICATION.md) and the FRE-1 architectural baseline
(docs/fre/, tag fre-architecture-baseline-2026-08-01).

Lives in its own package, parallel to `ngxrot.documents` (the AI Intelligence
Layer's pipeline code) and `ngxrot.lim` (the Local Intelligence Model
research track) -- never imports from, and is never imported by,
`alpha_engine.py`/`runner.py` (the same hard boundary every other module in
this project keeps). Nothing here calls an LLM; every function is a
deterministic, mechanical read (or, for evidence_graph.backfill_
implication_layers, a narrowly-scoped write to two already-existing,
already-approved nullable columns) over tables that already exist.
"""
