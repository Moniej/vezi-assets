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
            notes="Real Google GenAI (Gemini) API calls.")

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
    cls = PROVIDER_REGISTRY.get(cfg.provider)
    if cls is None:
        raise ValueError(f"Unknown llm provider {cfg.provider!r} in "
                         f"{LLM_CONFIG_PATH} — registered providers: "
                         f"{sorted(PROVIDER_REGISTRY)}")
    return cls(model_id=model_id or cfg.model_id)
