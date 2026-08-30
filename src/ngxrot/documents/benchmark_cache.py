"""Cache-then-call for EXPERIMENTAL providers (2026-08-13, AI Provider
Expansion Phase 1A) -- deliberately the same shape as cache.py's
cached_complete(), but writes to benchmark_calls (never llm_calls) and a
separate on-disk cache dir (never data/staging/llm_cache/). This keeps
experimental/benchmark traffic structurally unable to land in the
production extraction audit trail, satisfying the "never silently mix
outputs from different models in the same financial fact lineage"
requirement by construction rather than by convention.

Unlike cached_complete(), a failed call DOES get a row here (status=
'failure', error_message set) -- benchmarking explicitly needs failure
rate as a first-class metric (Phase 5), so failures must be visible in the
same table as successes, not silently dropped.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from .llm_providers import LLMProvider, LLMResponse, QuotaExceededError

PKG_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_CACHE_DIR = PKG_ROOT / "data" / "staging" / "benchmark_cache"


def _cache_key(provider_name: str, model_id: str, prompt_version: str,
              system_prompt: str, user_prompt: str) -> str:
    h = hashlib.sha256()
    for part in (provider_name, model_id, prompt_version, system_prompt, user_prompt):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def benchmark_complete(con, provider: LLMProvider, *, doc_id: int | None,
                      purpose: str, prompt_version: str, system_prompt: str,
                      user_prompt: str, max_tokens: int = 4096,
                      force: bool = False, cache_dir: Path | None = None,
                      document_hash: str | None = None) -> LLMResponse:
    """Cache-then-call against an EXPERIMENTAL provider. No retry wrapper
    (unlike cached_complete) -- a benchmark explicitly wants to observe a
    provider's own real failure/latency behavior, not a smoothed-over
    retried version of it. Raises QuotaExceededError / the underlying
    exception to the caller in both cases, but ALWAYS writes a
    benchmark_calls row first (status='failure') before re-raising, so the
    failure itself is part of the audit trail -- this is the one
    deliberate divergence from cached_complete()'s "QuotaExceededError
    writes no row" behavior, because failure rate is a benchmark metric
    here, not noise to skip logging."""
    cache_dir = cache_dir or BENCHMARK_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(provider.info.name, provider.info.model_id, prompt_version,
                     system_prompt, user_prompt)
    cache_path = cache_dir / f"{key}.json"

    served_from_cache = False
    error_message = None
    status = "success"
    resp: LLMResponse | None = None
    caught: Exception | None = None

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
        try:
            resp = provider.complete(system_prompt, user_prompt, max_tokens=max_tokens)
        except Exception as e:  # noqa: BLE001 -- must record then re-raise, not swallow
            status = "failure"
            error_message = f"{type(e).__name__}: {e}"
            caught = e
        else:
            cache_path.write_text(json.dumps({
                "model_id": resp.model_id, "response_text": resp.response_text,
                "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens,
                "stop_reason": resp.stop_reason, "request_id": resp.request_id,
                "latency_s": resp.latency_s, "document_hash": document_hash,
                "cached_at": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")

    con.execute(
        "INSERT INTO benchmark_calls (doc_id, provider, purpose, model_id_requested, "
        "model_id_returned, prompt_version, document_hash, system_prompt, user_prompt, "
        "response_text, input_tokens, output_tokens, stop_reason, request_id, cache_key, "
        "served_from_cache, latency_s, status, error_message, called_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, provider.info.name.split(":")[0], purpose, provider.info.model_id,
         resp.model_id if resp else provider.info.model_id, prompt_version, document_hash,
         system_prompt, user_prompt, resp.response_text if resp else None,
         resp.input_tokens if resp else None, resp.output_tokens if resp else None,
         resp.stop_reason if resp else None, resp.request_id if resp else None, key,
         int(served_from_cache), resp.latency_s if resp else None, status, error_message,
         date.today().isoformat()))
    con.commit()

    if caught is not None:
        raise caught
    return resp
