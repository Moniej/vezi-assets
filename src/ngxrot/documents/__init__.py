"""AI Intelligence Layer — Phase C: LLM-powered reasoning over documents.

Package layout (docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md §9,
docs/REASONING_ENGINE_SPECIFICATION.md):

  vocab.py          fixed vocabularies (impact categories, duration/
                     magnitude buckets, critique questions, ...) — hardcoded
                     constants, same pattern as event_pipeline.py's
                     _DIRECTIONS/_SEVERITIES (stable, spec-fixed, not
                     user-extensible via config).
  llm_providers.py  LLMProvider ABC + ProviderInfo, mirrors
                     providers/base.py's DataProvider shape. Concrete:
                     GeminiProvider (real calls, default per
                     configs/llm_provider.toml) and MockProvider (fixed
                     canned responses, for engineering-correctness tests —
                     NEVER used to produce a result reported as real
                     extraction). build_default_provider() is the one
                     factory function that maps config -> concrete class;
                     adding a vendor is one new subclass + one registry
                     entry, nothing else in this package changes.
  cache.py          prompt+response caching (deterministic reprocessing) and
                     a retry wrapper.
  prompts.py        prompt construction, deliberately separate from model
                     execution.
  grounding.py      quote-grounding + banned-phrase checks (the
                     anti-hallucination / anti-vagueness gates).
  extract.py        Steps 1-13: builds one draft investment_implications
                     row (+ its extracted_facts/causal_chain_steps/
                     impact_assessments/effect_chains/research_task_
                     candidates) per document.
  self_critique.py  Step 14: the mandatory devil's-advocate gate, a
                     SEPARATE reasoning call from the one that drafted the
                     conclusion.
  reasoning.py      top-level entry point: financial_reasoning(doc_id, ...)
                     ties extract.py + self_critique.py together.
  retrieval.py      Phase E: structured (SQL-first) document/fact/event finders.
  context.py        Phase E: ReasoningContext + build_reasoning_context, the
                     single assembled view every reasoning module consumes.
  reasoning_engine.py  Phase E: reason_about_company(), the question-driven
                     orchestrator (retrieve-if-needed, then aggregate).
  industry_reasoning.py  Phase F: peer/competitor propagation via the
                     knowledge graph (entity_relationships).

Nothing here is imported by alpha_engine.py, runner.py, or any portfolio
-facing module — that boundary is a design requirement, not an accident.
"""
