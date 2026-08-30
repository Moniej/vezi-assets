"""LLM provider abstraction — mirrors providers/base.py's DataProvider shape
so the reasoning engine never talks to a specific vendor's SDK directly.
Swapping or adding a vendor means adding a new LLMProvider subclass and one
line in PROVIDER_REGISTRY; nothing in extract.py/self_critique.py/
reasoning.py/cache.py/prompts.py changes — none of them import a concrete
provider class, only the LLMProvider type.

Default provider/model is config-driven (configs/llm_provider.toml), never
hardcoded in the pipeline — see load_llm_config()/build_default_provider()
at the bottom of this file. Currently registered: GeminiProvider (default)
and MockProvider (tests only). Anthropic support was removed 2026-07-22
(owner directive: Gemini is now the default, Anthropic is no longer used
anywhere in the codebase) — re-adding it later is a ~20-line class in this
same shape, registered the same way, per the whole point of this
abstraction.

MockProvider is for engineering-correctness tests ONLY (prompt construction,
DB writes, grounding checks) — it returns a fixed canned response and must
NEVER be the source of anything reported as a real extraction result. Every
function that could produce user-facing output takes a provider as an
explicit argument specifically so a test can pass MockProvider and a real
pilot run cannot silently do so by accident (no default provider is wired
into the orchestration scripts' function signatures — they call
build_default_provider() explicitly).
"""

from __future__ import annotations

import json
import os
import re
import time
import tomllib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3]
LLM_CONFIG_PATH = PKG_ROOT / "configs" / "llm_provider.toml"


def _parse_retry_delay(error_text: str) -> float | None:
    """Best-effort extraction of the SDK's own suggested retry delay
    ('retryDelay': '12s' in the error body) — this is a short burst-limit
    hint, NOT the daily-quota reset time (Google's free-tier daily quotas
    do not reliably expose their reset time in the error response itself).
    Returns None if not found rather than guessing."""
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", error_text)
    return float(m.group(1)) if m else None


@dataclass(frozen=True)
class LLMProviderInfo:
    name: str          # unique, stable — becomes sources.name for provenance
    model_id: str       # EXACT version string, stored on every row this
                        # provider produces (never just a family name)
    notes: str = ""
    # 2026-08-13, AI Provider Expansion Phase 1A. All optional/defaulted so
    # every existing LLMProviderInfo construction (Gemini, LIM, Mock) keeps
    # working unchanged.
    base_url: str | None = None
    capabilities: tuple[str, ...] = ()   # e.g. ("chat", "structured_output")
    status: str = "experimental"         # "production" | "experimental" —
                                         # defaults to the SAFER value;
                                         # GeminiProvider is the only class
                                         # below that explicitly overrides
                                         # to "production". Nothing reads
                                         # this field to auto-route yet
                                         # (explicitly deferred to Phase 10).


@dataclass(frozen=True)
class LLMResponse:
    model_id: str
    system_prompt: str
    user_prompt: str
    response_text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    request_id: str | None
    latency_s: float
    cached: bool = False


class QuotaExceededError(RuntimeError):
    """Raised by a provider when it detects a rate/quota-limit response
    (e.g. Gemini's 429 RESOURCE_EXHAUSTED) — deliberately a DISTINCT
    exception type from a generic transient failure, so callers (cache.py's
    retry wrapper, run_phase_c_pilot.py's orchestration loop) can tell "this
    will not resolve itself in a few seconds of backoff" apart from "a
    normal transient network error, retry as usual." 2026-07-22 hardening,
    added after a real pilot run hit exactly this and tenacity's generic
    retry wasted 4 attempts on a daily quota that no amount of backoff
    within the same run could clear."""

    def __init__(self, message: str, retry_delay_seconds: float | None = None):
        super().__init__(message)
        self.retry_delay_seconds = retry_delay_seconds


class LLMProvider(ABC):
    info: LLMProviderInfo

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        """One request/response pair. Implementations own retry policy for
        their own transient failure modes; callers (cache.py) own the
        cache-then-call decision, not this method. Implementations SHOULD
        raise QuotaExceededError (not a generic exception) when they detect
        a rate/quota-limit response, so it can be special-cased upstream."""
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    """Real calls via the Google GenAI SDK (`google-genai`, `from google
    import genai`) — the current unified SDK, not the deprecated
    `google-generativeai` package. Requires GEMINI_API_KEY or GOOGLE_API_KEY
    (checked in that order) or an explicit api_key — raises at construction
    time if none is available, rather than failing confusingly on the
    first call (same discipline the removed AnthropicProvider used)."""

    def __init__(self, model_id: str, api_key: str | None = None):
        from google import genai  # local import: keeps this a soft
                                  # dependency for code paths that only
                                  # ever use MockProvider

        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError(
                "GeminiProvider requires GEMINI_API_KEY or GOOGLE_API_KEY "
                "(or an explicit api_key) — refusing to construct without "
                "one rather than failing on the first API call.")
        self._client = genai.Client(api_key=key)
        self.info = LLMProviderInfo(
            name=f"gemini:{model_id}", model_id=model_id,
            notes="Real Google GenAI (Gemini) API calls.",
            capabilities=("chat", "structured_output"), status="production")

    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        from google.genai import errors, types

        t0 = time.time()
        try:
            resp = self._client.models.generate_content(
                model=self.info.model_id,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt, max_output_tokens=max_tokens),
            )
        except errors.APIError as e:
            if getattr(e, "code", None) == 429 or getattr(e, "status", "") == "RESOURCE_EXHAUSTED":
                raise QuotaExceededError(str(e), retry_delay_seconds=_parse_retry_delay(str(e))) from e
            raise
        usage = resp.usage_metadata
        finish_reason = resp.candidates[0].finish_reason if resp.candidates else None
        if not resp.text and finish_reason is not None and "MAX_TOKENS" in str(finish_reason):
            # Gemini 3.x spends part of max_output_tokens on internal
            # "thinking" tokens (usage_metadata.thoughts_token_count) before
            # any visible text — confirmed empirically: a 20-token budget
            # produced 0 output text, entirely consumed by thinking. This
            # is not an error the caller should silently absorb as "no
            # facts in this document"; it means the budget was too small
            # for THIS response, distinct from "the model found nothing."
            raise RuntimeError(
                f"Gemini returned empty text with finish_reason=MAX_TOKENS "
                f"(thoughts_token_count={getattr(usage, 'thoughts_token_count', '?')}, "
                f"max_output_tokens={max_tokens}) — the token budget was "
                f"exhausted by internal reasoning before any output text "
                f"was produced. Raise max_tokens, not a silent empty result.")
        return LLMResponse(
            model_id=self.info.model_id, system_prompt=system_prompt,
            user_prompt=user_prompt, response_text=resp.text or "",
            input_tokens=usage.prompt_token_count or 0,
            output_tokens=usage.candidates_token_count or 0,
            stop_reason=finish_reason.name if finish_reason else "unknown",
            request_id=resp.response_id, latency_s=time.time() - t0)


class LIMQualityGateError(RuntimeError):
    """Raised when something tries to construct a LocalLIMProvider without
    the LIM quality gate having recorded a PASS verdict, and without the
    caller explicitly opting into unvalidated use. This is a DISTINCT
    exception type (not a generic RuntimeError) so nothing upstream can
    catch-and-continue past it by accident the way a broad `except
    Exception` might swallow a plain error — see docs/LIM_ECONOMIC_
    VIABILITY_AUDIT_2026-08-13.md for why this exists: LIM measured at
    2-25% teacher-agreement in its research-track evaluations, and
    silently routing real extraction to a model at that quality would
    produce confidently-wrong structured financial facts, not a visible
    failure. Fail loud, fail safe, never fall back silently to Gemini
    either (a caller catching this and retrying with Gemini is fine; this
    module doing that FOR the caller without saying so is not)."""


LIM_QUALITY_GATE_PATH = PKG_ROOT / "lim_training" / "quality_gate_status.json"


def lim_quality_gate_status(path: Path = LIM_QUALITY_GATE_PATH) -> dict:
    """Reads the most recent LIM quality-gate verdict written by the
    evaluation harness (scripts/lim/run_quality_gate.py). Returns a dict
    with at least a `passed: bool` key. If the file does not exist, LIM has
    never been evaluated against the gate — treated as NOT passed, never
    as an unknown-but-probably-fine default."""
    if not path.exists():
        return {"passed": False, "reason": f"no quality-gate record found at {path} "
               "-- LIM has never been evaluated against the production gate"}
    return json.loads(path.read_text(encoding="utf-8"))


class LocalLIMProvider(LLMProvider):
    """Local, self-hosted inference against the LIM (Local Intelligence
    Model) LoRA checkpoints trained in lim_training/ — see
    docs/LIM_ARCHITECTURE.md. Runs as a SUBPROCESS against
    lim_training/venv's own Python (torch/unsloth/peft/CUDA live there,
    deliberately NOT added as a dependency of the main pipeline
    environment) via scripts/lim/infer_single.py, reusing the exact
    load pattern already proven in scripts/lim/verify_checkpoint_
    inference.py.

    NEVER the default provider: PROVIDER_REGISTRY does not map "local_lim"
    to this class (see comment below) — the ONLY way to get an instance is
    to construct it directly and explicitly, by design, so a typo'd or
    stale configs/llm_provider.toml can never silently route production
    extraction here.

    FAILS SAFE: construction raises LIMQualityGateError unless EITHER (a)
    the quality gate at lim_training/quality_gate_status.json records
    passed=True, or (b) the caller explicitly passes
    allow_unvalidated=True (for the evaluation harness itself to use
    LIM's own output to grade it — the one legitimate case for
    constructing an ungated LocalLIMProvider). No other code path may
    pass allow_unvalidated=True; this is deliberately not exposed via
    configs/llm_provider.toml at all.
    """

    def __init__(self, model_id: str, checkpoint_dir: str | None = None,
                python_exe: str | None = None, allow_unvalidated: bool = False,
                gate_status: dict | None = None, max_seq_length: int = 4096):
        # gate_status is an injectable override for tests ONLY -- real
        # callers must never pass it, so the gate is always read live from
        # disk (lim_quality_gate_status()) for anything that isn't a test
        # exercising the gate-check logic itself.
        gate = gate_status if gate_status is not None else lim_quality_gate_status()
        if not gate.get("passed") and not allow_unvalidated:
            raise LIMQualityGateError(
                f"Refusing to construct LocalLIMProvider: quality gate has not "
                f"recorded a PASS ({gate.get('reason', gate)}). LIM is a "
                f"research track, not a validated extraction engine — see "
                f"docs/LIM_ECONOMIC_VIABILITY_AUDIT_2026-08-13.md. If you are "
                f"the evaluation harness itself and need to grade LIM's raw "
                f"output, pass allow_unvalidated=True explicitly; no other "
                f"caller should ever do this.")
        ckpt = checkpoint_dir or _default_lim_checkpoint()
        if not Path(ckpt).is_dir():
            raise RuntimeError(f"LIM checkpoint directory does not exist: {ckpt}")
        self._checkpoint_dir = ckpt
        self._python_exe = python_exe or str(PKG_ROOT / "lim_training" / "venv" / "Scripts" / "python.exe")
        self._infer_script = str(PKG_ROOT / "scripts" / "lim" / "infer_single.py")
        self._max_seq_length = max_seq_length
        self.info = LLMProviderInfo(
            name=f"local_lim:{model_id}", model_id=model_id,
            notes=f"Local subprocess inference, checkpoint={ckpt}, "
                 f"quality_gate_passed={gate.get('passed')}")

    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        import subprocess

        req = json.dumps({
            "system_prompt": system_prompt, "user_prompt": user_prompt,
            "max_new_tokens": max_tokens, "checkpoint_dir": self._checkpoint_dir,
            "max_seq_length": self._max_seq_length,
        })
        t0 = time.time()
        proc = subprocess.run(
            [self._python_exe, self._infer_script], input=req, capture_output=True,
            text=True, timeout=600)
        wall_s = time.time() - t0
        if proc.returncode != 0:
            raise RuntimeError(f"LocalLIMProvider subprocess failed (exit {proc.returncode}): "
                               f"{proc.stderr[-2000:]}")
        try:
            resp = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as e:
            raise RuntimeError(f"LocalLIMProvider subprocess produced unparseable output: "
                               f"{proc.stdout[-1000:]!r}") from e
        return LLMResponse(
            model_id=self.info.model_id, system_prompt=system_prompt,
            user_prompt=user_prompt, response_text=resp["response_text"],
            input_tokens=resp["input_tokens"], output_tokens=resp["output_tokens"],
            stop_reason="unknown", request_id=None,
            latency_s=resp.get("latency_s", wall_s))


def _default_lim_checkpoint() -> str:
    """The single best-evaluated checkpoint on record as of this writing
    (RB-3b, agreement_with_teacher=0.201 -- still far below any usable
    bar, see the viability audit). Named explicitly rather than picking
    "latest" so a new, unevaluated training run can never silently become
    the checkpoint LocalLIMProvider serves."""
    return str(PKG_ROOT / "lim_training" / "runs" /
              "8d265e59-3901-40e0-aa02-4a81df5dc86f" / "checkpoint-40")


class MockProvider(LLMProvider):
    """Fixed canned response for engineering tests. `responses` maps a
    substring of the user_prompt to a canned response_text (first match
    wins) so a test can distinguish a draft-reasoning call from a
    self-critique call by prompt content, without needing a real model."""

    def __init__(self, responses: dict[str, str], default: str | None = None):
        self._responses = responses
        self._default = default
        self.info = LLMProviderInfo(
            name="mock:test-fixture", model_id="mock-v1",
            notes="Canned responses for testing only — never a real result.")

    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        text = self._default
        for key, val in self._responses.items():
            if key in user_prompt:
                text = val
                break
        if text is None:
            raise KeyError(f"MockProvider: no canned response matched this "
                           f"prompt and no default was set: {user_prompt[:200]!r}")
        return LLMResponse(
            model_id=self.info.model_id, system_prompt=system_prompt,
            user_prompt=user_prompt, response_text=text,
            input_tokens=len(user_prompt) // 4, output_tokens=len(text) // 4,
            stop_reason="end_turn", request_id=None, latency_s=0.0)


# ---------------------------------------------------------------------------
# 2026-08-13, AI Provider Expansion Phase 1B. Three EXPERIMENTAL providers,
# all OpenAI-compatible chat-completions REST APIs (no new SDK dependency —
# `requests` is already pinned in requirements.txt). Deliberately NOT added
# to PROVIDER_REGISTRY (see EXPERIMENTAL_PROVIDER_REGISTRY below) — same
# "explicit construction only" discipline as LocalLIMProvider, so nothing
# in configs/llm_provider.toml can ever silently route production
# extraction to an unbenchmarked provider.
# ---------------------------------------------------------------------------

import requests


def _openai_compatible_complete(*, base_url: str, api_key: str, model_id: str,
                               system_prompt: str, user_prompt: str, max_tokens: int,
                               provider_label: str, extra_headers: dict | None = None,
                               timeout: float = 300.0) -> tuple[LLMResponse, str]:
    """Shared request/response handling for Groq/Cerebras/OpenRouter — all
    three speak the same OpenAI chat-completions shape. Returns
    (LLMResponse, raw_returned_model_id) — the raw model id is surfaced
    separately because OpenRouter in particular can route a request to a
    DIFFERENT underlying model than requested, and the assignment requires
    recording the ACTUAL model, not the one asked for. NEVER include the
    Authorization header or api_key value in any exception message raised
    here — only the URL/status/body (which never contains the key we sent,
    only what the server sent back)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    t0 = time.time()
    try:
        resp = requests.post(f"{base_url}/chat/completions", headers=headers,
                             json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"{provider_label} request failed (network/timeout): {e}") from e
    latency_s = time.time() - t0

    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        delay = float(retry_after) if retry_after and retry_after.isdigit() else \
            _parse_retry_delay(resp.text)
        raise QuotaExceededError(
            f"{provider_label} rate/quota limit (429): {resp.text[:500]}",
            retry_delay_seconds=delay)
    if resp.status_code >= 400:
        raise RuntimeError(f"{provider_label} API error {resp.status_code}: {resp.text[:1000]}")

    body = resp.json()
    choice = body["choices"][0]
    returned_model = body.get("model", model_id)  # OpenRouter: the ACTUAL model used
    usage = body.get("usage", {})
    message = choice.get("message", {})
    content = message.get("content")
    finish_reason = choice.get("finish_reason") or "unknown"
    if not content and finish_reason == "length" and message.get("reasoning"):
        # Same failure class GeminiProvider already raises on explicitly:
        # a reasoning/"thinking" model (observed on Cerebras zai-glm-4.7 and
        # gpt-oss-120b) can spend the ENTIRE max_tokens budget on an
        # internal `reasoning` field and never populate `content` at all --
        # not even null, the key is simply absent. This is NOT "the model
        # found nothing" and must not be silently returned as empty text;
        # it means the token budget was too small for this response.
        reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens")
        raise RuntimeError(
            f"{provider_label} ({returned_model}) returned empty content with "
            f"finish_reason='length' and a non-empty 'reasoning' field "
            f"(reasoning_tokens={reasoning_tokens}, max_tokens={max_tokens}) -- the token "
            f"budget was exhausted by internal reasoning before any output text was "
            f"produced. Raise max_tokens, not a silent empty result.")
    return LLMResponse(
        model_id=returned_model, system_prompt=system_prompt, user_prompt=user_prompt,
        response_text=content or "",
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        stop_reason=choice.get("finish_reason") or "unknown",
        request_id=body.get("id"), latency_s=latency_s,
    ), returned_model


class GroqProvider(LLMProvider):
    """Groq's OpenAI-compatible API (LPU-hosted open models). Requires
    GROQ_API_KEY. EXPERIMENTAL — see module-level note above; never
    registered in PROVIDER_REGISTRY, never selected by
    build_default_provider()."""

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, model_id: str, api_key: str | None = None):
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GroqProvider requires GROQ_API_KEY (or an explicit api_key) — "
                               "refusing to construct without one.")
        self._api_key = key
        self.info = LLMProviderInfo(
            name=f"groq:{model_id}", model_id=model_id, base_url=self.BASE_URL,
            capabilities=("chat",), status="experimental",
            notes="Groq LPU-hosted OpenAI-compatible API. EXPERIMENTAL — not benchmarked yet.")

    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        resp, _ = _openai_compatible_complete(
            base_url=self.BASE_URL, api_key=self._api_key, model_id=self.info.model_id,
            system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens,
            provider_label="Groq")
        return resp


class CerebrasProvider(LLMProvider):
    """Cerebras' OpenAI-compatible inference API. Requires CEREBRAS_API_KEY.
    EXPERIMENTAL — see module-level note above."""

    BASE_URL = "https://api.cerebras.ai/v1"

    def __init__(self, model_id: str, api_key: str | None = None):
        key = api_key or os.environ.get("CEREBRAS_API_KEY")
        if not key:
            raise RuntimeError("CerebrasProvider requires CEREBRAS_API_KEY (or an explicit "
                               "api_key) — refusing to construct without one.")
        self._api_key = key
        self.info = LLMProviderInfo(
            name=f"cerebras:{model_id}", model_id=model_id, base_url=self.BASE_URL,
            capabilities=("chat",), status="experimental",
            notes="Cerebras wafer-scale OpenAI-compatible API. EXPERIMENTAL — not benchmarked yet.")

    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        resp, _ = _openai_compatible_complete(
            base_url=self.BASE_URL, api_key=self._api_key, model_id=self.info.model_id,
            system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens,
            provider_label="Cerebras")
        return resp


class OpenRouterProvider(LLMProvider):
    """OpenRouter's multi-vendor routing API. Requires OPENROUTER_API_KEY.
    EXPERIMENTAL — see module-level note above.

    IMPORTANT (explicit assignment requirement): OpenRouter can route a
    request to a DIFFERENT underlying model than the one requested (e.g. a
    provider-side fallback). The response body's own `model` field records
    what ACTUALLY served the request — this class surfaces that as
    `LLMResponse.model_id`, which is what benchmark_cache.py logs, so the
    audit trail always reflects the true model, never just the one asked
    for. `self.info.model_id` (the requested model) is preserved separately
    for comparison."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, model_id: str, api_key: str | None = None):
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OpenRouterProvider requires OPENROUTER_API_KEY (or an explicit "
                               "api_key) — refusing to construct without one.")
        self._api_key = key
        self.info = LLMProviderInfo(
            name=f"openrouter:{model_id}", model_id=model_id, base_url=self.BASE_URL,
            capabilities=("chat",), status="experimental",
            notes="OpenRouter multi-vendor routing API. EXPERIMENTAL — not benchmarked yet. "
                 "Actual served model may differ from the requested model_id; see class docstring.")

    def complete(self, system_prompt: str, user_prompt: str, *,
                max_tokens: int = 4096) -> LLMResponse:
        resp, returned_model = _openai_compatible_complete(
            base_url=self.BASE_URL, api_key=self._api_key, model_id=self.info.model_id,
            system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens,
            provider_label="OpenRouter",
            extra_headers={"HTTP-Referer": "https://ngx-rotation.local", "X-Title": "ngx-rotation-benchmark"})
        if returned_model != self.info.model_id:
            resp = LLMResponse(
                model_id=returned_model, system_prompt=resp.system_prompt,
                user_prompt=resp.user_prompt, response_text=resp.response_text,
                input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                stop_reason=resp.stop_reason, request_id=resp.request_id,
                latency_s=resp.latency_s, cached=resp.cached)
        return resp


EXPERIMENTAL_PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "groq": GroqProvider,
    "cerebras": CerebrasProvider,
    "openrouter": OpenRouterProvider,
}
# Deliberately a SEPARATE dict from PROVIDER_REGISTRY (below) — see
# build_experimental_provider(). PROVIDER_REGISTRY / build_default_provider()
# never look at this dict; configs/llm_provider.toml's `provider` value
# cannot resolve here even by typo, matching the LocalLIMProvider precedent.


def build_experimental_provider(name: str, model_id: str, api_key: str | None = None) -> LLMProvider:
    """Explicit-construction-only factory for experimental providers —
    mirrors LocalLIMProvider's discipline: there is no config-file path
    that reaches this function, so a benchmark run always required a
    deliberate, named call, never an implicit default."""
    cls = EXPERIMENTAL_PROVIDER_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown experimental provider {name!r} — registered: "
                         f"{sorted(EXPERIMENTAL_PROVIDER_REGISTRY)}")
    return cls(model_id=model_id, api_key=api_key)


def health_check(provider: LLMProvider, *, timeout_s: float = 30.0) -> dict:
    """Minimal, cheap connectivity probe — a single short completion call.
    NEVER raises: any failure (network, auth, quota, malformed response) is
    captured and returned as a structured result instead, so a health check
    can never crash a caller that's just trying to report provider status.
    NEVER includes the API key in the returned dict."""
    t0 = time.time()
    try:
        resp = provider.complete("You are a health check.", "Reply with the single word: ok",
                                 max_tokens=16)
        return {"provider": provider.info.name, "model_id": provider.info.model_id,
               "status": provider.info.status, "ok": True, "latency_s": time.time() - t0,
               "response_preview": resp.response_text[:50], "error": None}
    except QuotaExceededError as e:
        return {"provider": provider.info.name, "model_id": provider.info.model_id,
               "status": provider.info.status, "ok": False, "latency_s": time.time() - t0,
               "response_preview": None, "error": f"quota_exceeded: {e}"}
    except Exception as e:  # noqa: BLE001 -- health check must never raise
        return {"provider": provider.info.name, "model_id": provider.info.model_id,
               "status": provider.info.status, "ok": False, "latency_s": time.time() - t0,
               "response_preview": None, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Config-driven default provider. This is the ONLY place in the codebase
# that maps a config value to a concrete class — extract.py, self_critique
# .py, reasoning.py, cache.py, prompts.py never import GeminiProvider (or
# any concrete provider) by name. Adding a new vendor later means one new
# class above plus one new entry in PROVIDER_REGISTRY; nothing else changes.
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
}
# MockProvider is deliberately NOT registered here: it takes a different
# constructor shape (responses/default, not model_id/api_key) because it
# needs canned responses supplied by the test that constructs it — it is
# always instantiated directly by tests, never looked up by name from
# configs/llm_provider.toml. This is intentional, not an oversight: a
# config-driven mock would risk a typo'd config silently routing a real
# pilot run to canned responses.
#
# LocalLIMProvider is likewise deliberately NOT registered here (2026-08-13,
# LIM Economic Viability Audit). Unlike MockProvider, LIM COULD in principle
# be config-driven the way LIM_ARCHITECTURE.md §1.1 originally sketched --
# but doing so today would mean a single typo/stale value in
# configs/llm_provider.toml could silently route real production extraction
# to a model measured at 2-25% teacher-agreement in its own evaluations.
# build_default_provider() below explicitly rejects "local_lim" with a
# named, actionable error instead of doing this by omission. Re-adding it
# to this registry is a one-line, explicit, reviewable change to make ONLY
# after the quality gate (lim_training/quality_gate_status.json) records a
# real PASS -- not before.


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model_id: str
    api_key_env_var: str


def load_llm_config(path: Path = LLM_CONFIG_PATH) -> LLMConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))["llm"]
    return LLMConfig(provider=raw["provider"], model_id=raw["model_id"],
                     api_key_env_var=raw["api_key_env_var"])


def build_default_provider(model_id: str | None = None,
                          config: LLMConfig | None = None) -> LLMProvider:
    """The single factory every orchestration script should call instead of
    constructing a provider class directly. `model_id` overrides the
    config file's value (e.g. a CLI --model flag) without touching the
    config-loading path — the config file remains the single source of
    truth for the DEFAULT, while still allowing a one-off override."""
    cfg = config or load_llm_config()
    if cfg.provider == "local_lim":
        raise LIMQualityGateError(
            f"{LLM_CONFIG_PATH} requests provider='local_lim', but "
            f"LocalLIMProvider is intentionally not config-selectable "
            f"through build_default_provider() (see PROVIDER_REGISTRY's "
            f"comment) -- construct ngxrot.documents.llm_providers."
            f"LocalLIMProvider directly, and only after confirming "
            f"lim_quality_gate_status().passed is True. This is not a "
            f"missing feature; it is a deliberate refusal to let a config "
            f"file silently route production extraction to an unvalidated "
            f"local model.")
    cls = PROVIDER_REGISTRY.get(cfg.provider)
    if cls is None:
        raise ValueError(f"Unknown llm provider {cfg.provider!r} in "
                         f"{LLM_CONFIG_PATH} — registered providers: "
                         f"{sorted(PROVIDER_REGISTRY)}")
    return cls(model_id=model_id or cfg.model_id)
