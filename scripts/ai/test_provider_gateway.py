"""Tests for the AI Provider Expansion Phase 1A/1B plumbing: Groq/Cerebras/
OpenRouter LLMProvider subclasses, the experimental registry, health_check,
and benchmark_cache.py. ALL HTTP is mocked (unittest.mock.patch on
requests.post) -- these tests never make a live network call and must
pass with zero API keys set. Live connectivity is verified separately by
scripts/ai/live_connectivity_check.py, not here.

  PYTHONPATH=src python scripts/ai/test_provider_gateway.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents import llm_providers as lp  # noqa: E402
from ngxrot.documents.benchmark_cache import benchmark_complete  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


def _mock_response(status_code=200, json_body=None, text="", headers=None):
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_body or {}
    m.text = text
    m.headers = headers or {}
    return m


FAKE_GROQ_KEY = "gsk_FAKE_TEST_KEY_never_a_real_secret_0000000000000000"
FAKE_CEREBRAS_KEY = "csk_FAKE_TEST_KEY_never_a_real_secret_0000000000000000"
FAKE_OPENROUTER_KEY = "sk-or-FAKE_TEST_KEY_never_a_real_secret_0000000000000000"

SUCCESS_BODY = {
    "id": "req-abc123",
    "model": "llama-3.3-70b-versatile",
    "choices": [{"message": {"content": "hello world"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 3},
}

# --- registry isolation (must hold before anything else) ---
check("groq NOT in PROVIDER_REGISTRY", "groq" not in lp.PROVIDER_REGISTRY)
check("cerebras NOT in PROVIDER_REGISTRY", "cerebras" not in lp.PROVIDER_REGISTRY)
check("openrouter NOT in PROVIDER_REGISTRY", "openrouter" not in lp.PROVIDER_REGISTRY)
check("PROVIDER_REGISTRY unchanged, still only gemini", list(lp.PROVIDER_REGISTRY) == ["gemini"])
check("all three registered in EXPERIMENTAL_PROVIDER_REGISTRY",
     set(lp.EXPERIMENTAL_PROVIDER_REGISTRY) == {"groq", "cerebras", "openrouter"})
try:
    lp.build_default_provider(config=lp.LLMConfig(provider="groq", model_id="x", api_key_env_var="GROQ_API_KEY"))
    check("build_default_provider rejects 'groq' (config-path isolation)", False)
except ValueError as e:
    check("build_default_provider rejects 'groq' (config-path isolation)", "groq" in str(e))

# --- construction without key fails closed ---
for name, cls, env_key in [("Groq", lp.GroqProvider, "GROQ_API_KEY"),
                           ("Cerebras", lp.CerebrasProvider, "CEREBRAS_API_KEY"),
                           ("OpenRouter", lp.OpenRouterProvider, "OPENROUTER_API_KEY")]:
    with patch.dict("os.environ", {}, clear=False):
        import os as _os
        saved = _os.environ.pop(env_key, None)
        try:
            cls(model_id="x")
            check(f"{name} refuses construction without {env_key}", False)
        except RuntimeError as e:
            check(f"{name} refuses construction without {env_key}",
                 env_key in str(e) and FAKE_GROQ_KEY not in str(e))
        finally:
            if saved is not None:
                _os.environ[env_key] = saved

# --- Groq: success path ---
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(200, SUCCESS_BODY)) as mock_post:
    groq = lp.GroqProvider(model_id="llama-3.3-70b-versatile", api_key=FAKE_GROQ_KEY)
    resp = groq.complete("sys", "user", max_tokens=100)
    check("Groq: response_text parsed", resp.response_text == "hello world")
    check("Groq: input/output tokens parsed", resp.input_tokens == 10 and resp.output_tokens == 3)
    check("Groq: request_id parsed", resp.request_id == "req-abc123")
    call_kwargs = mock_post.call_args.kwargs
    check("Groq: posts to correct base_url", mock_post.call_args.args[0] == f"{lp.GroqProvider.BASE_URL}/chat/completions")
    check("Groq: Authorization header sent", call_kwargs["headers"]["Authorization"] == f"Bearer {FAKE_GROQ_KEY}")
    check("Groq: status defaults experimental", groq.info.status == "experimental")

# --- Cerebras: success path ---
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(200, SUCCESS_BODY)):
    cer = lp.CerebrasProvider(model_id="llama-3.3-70b", api_key=FAKE_CEREBRAS_KEY)
    resp = cer.complete("sys", "user")
    check("Cerebras: response_text parsed", resp.response_text == "hello world")
    check("Cerebras: status defaults experimental", cer.info.status == "experimental")

# --- OpenRouter: actual-returned-model capture (the explicit requirement) ---
OR_BODY_DIFFERENT_MODEL = {**SUCCESS_BODY, "model": "anthropic/claude-instant-1"}  # served a DIFFERENT model
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(200, OR_BODY_DIFFERENT_MODEL)):
    orp = lp.OpenRouterProvider(model_id="meta-llama/llama-3.3-70b-instruct", api_key=FAKE_OPENROUTER_KEY)
    resp = orp.complete("sys", "user")
    check("OpenRouter: records the ACTUAL returned model, not the requested one",
         resp.model_id == "anthropic/claude-instant-1")
    check("OpenRouter: requested model still recoverable from provider.info",
         orp.info.model_id == "meta-llama/llama-3.3-70b-instruct")

# --- 429 -> QuotaExceededError, with Retry-After parsed ---
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(429, {}, text="rate limited", headers={"Retry-After": "17"})):
    groq2 = lp.GroqProvider(model_id="x", api_key=FAKE_GROQ_KEY)
    try:
        groq2.complete("sys", "user")
        check("429 raises QuotaExceededError", False)
    except lp.QuotaExceededError as e:
        check("429 raises QuotaExceededError", True)
        check("429: retry_delay_seconds parsed from Retry-After header", e.retry_delay_seconds == 17.0)
        check("429: API key never appears in exception message", FAKE_GROQ_KEY not in str(e))

# --- 500 -> RuntimeError, key never leaked ---
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(500, {}, text="internal error")):
    cer2 = lp.CerebrasProvider(model_id="x", api_key=FAKE_CEREBRAS_KEY)
    try:
        cer2.complete("sys", "user")
        check("500 raises RuntimeError", False)
    except RuntimeError as e:
        check("500 raises RuntimeError", True)
        check("500: API key never appears in exception message", FAKE_CEREBRAS_KEY not in str(e))

# --- health_check: never raises, structured result, no key leak ---
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(200, SUCCESS_BODY)):
    groq3 = lp.GroqProvider(model_id="llama-3.3-70b-versatile", api_key=FAKE_GROQ_KEY)
    hc = lp.health_check(groq3)
    check("health_check: ok=True on success", hc["ok"] is True)
    check("health_check: no key in result", FAKE_GROQ_KEY not in str(hc))

with patch("ngxrot.documents.llm_providers.requests.post",
          side_effect=RuntimeError("boom")):
    groq4 = lp.GroqProvider(model_id="x", api_key=FAKE_GROQ_KEY)
    hc = lp.health_check(groq4)
    check("health_check: never raises, ok=False on failure", hc["ok"] is False)
    check("health_check failure: no key in result", FAKE_GROQ_KEY not in str(hc))

# --- benchmark_complete: writes to benchmark_calls, NEVER llm_calls, scratch DB only ---
scratch_path = db.new_scratch_db_path()
con = db.init_db(scratch_path)
check("scratch db starts with zero benchmark_calls rows",
     con.execute("SELECT COUNT(*) FROM benchmark_calls").fetchone()[0] == 0)
check("scratch db starts with zero llm_calls rows",
     con.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 0)

with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(200, SUCCESS_BODY)):
    groq5 = lp.GroqProvider(model_id="llama-3.3-70b-versatile", api_key=FAKE_GROQ_KEY)
    resp = benchmark_complete(con, groq5, doc_id=None, purpose="benchmark_test",
                              prompt_version="test_v1", system_prompt="sys", user_prompt="user",
                              cache_dir=Path(ROOT / "data" / "staging" / "benchmark_cache_TEST"))
    check("benchmark_complete returns a real LLMResponse", resp.response_text == "hello world")

row = con.execute("SELECT provider, status, model_id_requested, model_id_returned, response_text "
                  "FROM benchmark_calls").fetchone()
check("benchmark_calls got exactly one row after one call",
     con.execute("SELECT COUNT(*) FROM benchmark_calls").fetchone()[0] == 1)
check("benchmark_calls row: provider recorded", row[0] == "groq")
check("benchmark_calls row: status success", row[1] == "success")
check("llm_calls STILL zero rows -- experimental traffic never touches the production audit trail",
     con.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 0)

full_row_text = str(con.execute("SELECT * FROM benchmark_calls").fetchall())
check("no API key anywhere in the written benchmark_calls row",
     FAKE_GROQ_KEY not in full_row_text)

# --- benchmark_complete: failure path also writes a row (status='failure'), then re-raises ---
with patch("ngxrot.documents.llm_providers.requests.post",
          return_value=_mock_response(429, {}, text="rate limited")):
    groq6 = lp.GroqProvider(model_id="x", api_key=FAKE_GROQ_KEY)
    try:
        benchmark_complete(con, groq6, doc_id=None, purpose="benchmark_test",
                          prompt_version="test_v1", system_prompt="sys2", user_prompt="user2",
                          cache_dir=Path(ROOT / "data" / "staging" / "benchmark_cache_TEST"))
        check("benchmark_complete re-raises on failure", False)
    except lp.QuotaExceededError:
        check("benchmark_complete re-raises on failure", True)

check("benchmark_calls now has 2 rows (success + failure both logged)",
     con.execute("SELECT COUNT(*) FROM benchmark_calls").fetchone()[0] == 2)
failure_row = con.execute(
    "SELECT status, error_message FROM benchmark_calls WHERE status='failure'").fetchone()
check("failure row recorded with status='failure' and a real error_message",
     failure_row is not None and failure_row[0] == "failure" and failure_row[1] is not None)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
