"""Deterministic reprocessing: every LLM call is cached to disk keyed by
(model_id, prompt_version, system_prompt, user_prompt) and logged to the
`llm_calls` table regardless of whether it was served from cache or a live
request — the table is the audit trail ("store every prompt, response,
token usage and model version"); the on-disk cache is what makes rerunning
the pipeline free and byte-identical instead of re-billing the API.

Retries wrap only the live-call path (tenacity, exponential backoff on
transient errors) — a cache hit never retries anything, there's nothing to
retry. QuotaExceededError is DELIBERATELY excluded from the retry policy
(2026-07-22 hardening): a daily quota does not clear within a few seconds
of backoff, so retrying it wastes attempts and time for no benefit — it
propagates on the FIRST occurrence so the caller (run_phase_c_pilot.py)
can stop gracefully and save progress immediately, per the same principle
that already governs every other "don't paper over a real problem" rule
on this platform.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from .llm_providers import LLMProvider, LLMResponse, QuotaExceededError

PKG_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = PKG_ROOT / "data" / "staging" / "llm_cache"


def document_text_hash(text: str) -> str:
    """Sha256 of the document text ALONE (distinct from the full-prompt
    cache key) — an explicit, queryable answer to "has this document's
    text changed since it was last processed", stored on llm_calls
    .document_hash. Public (not `_`-prefixed): extract.py computes this
    from the same document text it reads, for auditability."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_key(model_id: str, prompt_version: str, system_prompt: str,
              user_prompt: str) -> str:
    h = hashlib.sha256()
    for part in (model_id, prompt_version, system_prompt, user_prompt):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30),
      retry=retry_if_not_exception_type(QuotaExceededError), reraise=True)
def _call_with_retry(provider: LLMProvider, system_prompt: str, user_prompt: str,
                     max_tokens: int) -> LLMResponse:
    return provider.complete(system_prompt, user_prompt, max_tokens=max_tokens)


def cached_complete(con, provider: LLMProvider, *, doc_id: int | None,
                   purpose: str, prompt_version: str, system_prompt: str,
                   user_prompt: str, max_tokens: int = 4096,
                   force: bool = False, cache_dir: Path | None = None,
                   document_hash: str | None = None) -> LLMResponse:
    """Cache-then-call. `purpose` in {'draft_reasoning', 'self_critique'} —
    matches the llm_calls.purpose CHECK constraint. Every call (cached or
    live) gets one llm_calls row, so the audit trail is complete regardless
    of cache state. `cache_dir` defaults to the real, shared
    data/staging/llm_cache/ — tests MUST override it with an isolated
    tempdir so test fixtures never pollute the real pilot's cache (this
    was a real bug the first time this pipeline was tested: two tests
    with identical prompts silently shared a cache entry across test
    runs). `document_hash` (optional) is stored on the llm_calls row for
    explicit cache-invalidation auditability (see invalidate_cache_for_doc
    below) — callers that don't pass one (e.g. self_critique.py, whose
    input is a draft summary rather than raw document text) simply get
    NULL there, which is honest (there is no single "document" for that
    call to hash).

    QuotaExceededError propagates immediately (not retried, see module
    docstring) and writes NO llm_calls row — there is no response to log,
    and the caller is expected to record the failure at the
    document_processing_status level instead."""
    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(provider.info.model_id, prompt_version, system_prompt, user_prompt)
    cache_path = cache_dir / f"{key}.json"

    served_from_cache = False
    if cache_path.exists() and not force:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        resp = LLMResponse(
            model_id=payload["model_id"], system_prompt=system_prompt,
            user_prompt=user_prompt, response_text=payload["response_text"],
            input_tokens=payload["input_tokens"], output_tokens=payload["output_tokens"],
            stop_reason=payload["stop_reason"], request_id=payload.get("request_id"),
            latency_s=payload.get("latency_s", 0.0), cached=True)
        served_from_cache = True
    else:
        resp = _call_with_retry(provider, system_prompt, user_prompt, max_tokens)
        cache_path.write_text(json.dumps({
            "model_id": resp.model_id, "response_text": resp.response_text,
            "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens,
            "stop_reason": resp.stop_reason, "request_id": resp.request_id,
            "latency_s": resp.latency_s, "document_hash": document_hash,
            "cached_at": datetime.now().isoformat(),
        }, indent=2), encoding="utf-8")

    con.execute(
        "INSERT INTO llm_calls (doc_id, purpose, model_id, prompt_version, "
        "document_hash, system_prompt, user_prompt, response_text, input_tokens, "
        "output_tokens, stop_reason, request_id, cache_key, "
        "served_from_cache, latency_s, called_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, purpose, resp.model_id, prompt_version, document_hash, system_prompt,
         user_prompt, resp.response_text, resp.input_tokens, resp.output_tokens,
         resp.stop_reason, resp.request_id, key, int(served_from_cache), resp.latency_s,
         date.today().isoformat()))
    con.commit()
    return resp


def invalidate_cache_for_doc(con, cache_dir: Path | None, doc_id: int,
                            reason: str) -> int:
    """Explicit, auditable cache invalidation (requirement: 'make cache
    invalidation explicit and auditable', 2026-07-22). Deletes on-disk
    cache entries whose cache_key was ever recorded against this doc_id in
    llm_calls, and logs the invalidation event to data_quality_log (the
    platform's existing audit-log table — reused, not duplicated) rather
    than silently deleting with no trace. Does NOT touch extracted_facts/
    investment_implications rows already produced from the invalidated
    cache entry — those remain the historical record; invalidation only
    affects whether a FUTURE call with the same prompt hits the cache or
    calls the API again. Returns the number of cache files removed."""
    cache_dir = cache_dir or CACHE_DIR
    keys = [r[0] for r in con.execute(
        "SELECT DISTINCT cache_key FROM llm_calls WHERE doc_id = ?", (doc_id,)).fetchall()]
    removed = 0
    for key in keys:
        path = cache_dir / f"{key}.json"
        if path.exists():
            path.unlink()
            removed += 1
    con.execute(
        "INSERT INTO data_quality_log (check_name, entity_type, entity_code, "
        "severity, detail) VALUES ('llm_cache_invalidation', 'ticker', ?, 'info', ?)",
        (str(doc_id), f"Invalidated {removed} cache file(s) for doc_id={doc_id}: {reason}"))
    con.commit()
    return removed
