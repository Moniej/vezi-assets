"""Tests for provider_reliability.py -- all deterministic, scratch DB,
explicit `now` timestamps (never live datetime.now()) so cooldown-window
assertions are exact and reproducible.

  PYTHONPATH=src python scripts/ai/test_provider_reliability.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.provider_reliability import (  # noqa: E402
    MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE, MAX_CONSECUTIVE_STRUCTURAL_FAILURES_BEFORE_DISABLE,
    ProviderDisabledError, ProviderInCooldownError, can_call_now, call_with_reliability_guard,
    classify_failure, health_state, record_failure, record_success, reset_provider,
    retry_budget_remaining)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


T0 = datetime(2026, 8, 14, 12, 0, 0)

# --- classify_failure ---
check("classify_failure: Groq 413 -> structural (even though it mentions TPM)",
     classify_failure("Groq API error 413: Request too large ... tokens per minute (TPM)",
                      "RuntimeError") == "structural")
check("classify_failure: Cerebras 429 'tokens per minute limit exceeded' -> rate_limit",
     classify_failure("Cerebras rate/quota limit (429): Tokens per minute limit exceeded",
                      "QuotaExceededError") == "rate_limit")
check("classify_failure: Gemini daily quota 429 RESOURCE_EXHAUSTED -> rate_limit",
     classify_failure("429 RESOURCE_EXHAUSTED. quota exceeded", "QuotaExceededError") == "rate_limit")
check("classify_failure: Cerebras 402 payment_required -> structural",
     classify_failure("Cerebras API error 402: Payment required to access this resource",
                      "RuntimeError") == "structural")
check("classify_failure: unrelated network error -> other",
     classify_failure("Connection reset by peer", "RuntimeError") == "other")

# --- record_failure: exponential backoff, no retry_after given ---
p = db.new_scratch_db_path()
con = db.init_db(p)
state = record_failure(con, "testprov", "m1", "429 rate_limit_exceeded", "QuotaExceededError", now=T0)
check("1st rate_limit failure -> cooldown", state == "cooldown")
hs = health_state(con, "testprov", "m1")
check("1st failure: cooldown_until = T0 + 30s (base backoff)",
     hs.cooldown_until == (T0 + timedelta(seconds=30)).isoformat())

state = record_failure(con, "testprov", "m1", "429 rate_limit_exceeded", "QuotaExceededError", now=T0)
hs = health_state(con, "testprov", "m1")
check("2nd failure: cooldown_until = T0 + 60s (2x backoff)",
     hs.cooldown_until == (T0 + timedelta(seconds=60)).isoformat())

# --- record_failure: retry_after_s from provider is honored over computed backoff ---
p2 = db.new_scratch_db_path()
con2 = db.init_db(p2)
record_failure(con2, "testprov", "m2", "429", "QuotaExceededError", retry_after_s=17.0, now=T0)
hs2 = health_state(con2, "testprov", "m2")
check("provider-supplied retry_after_s is honored exactly",
     hs2.cooldown_until == (T0 + timedelta(seconds=17)).isoformat())

# --- structural failures disable fast (2 consecutive) ---
p3 = db.new_scratch_db_path()
con3 = db.init_db(p3)
record_failure(con3, "groq", "m3", "413 Request too large", "RuntimeError", now=T0)
state = record_failure(con3, "groq", "m3", "413 Request too large", "RuntimeError", now=T0)
check(f"2 consecutive structural failures -> disabled (threshold={MAX_CONSECUTIVE_STRUCTURAL_FAILURES_BEFORE_DISABLE})",
     state == "disabled")
hs3 = health_state(con3, "groq", "m3")
check("disabled reason mentions structural failures", "structural" in hs3.disabled_reason)

# --- any-class failures disable after MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE ---
p4 = db.new_scratch_db_path()
con4 = db.init_db(p4)
for i in range(MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE - 1):
    state = record_failure(con4, "cerebras", "m4", "429 tokens per minute", "QuotaExceededError", now=T0)
check(f"{MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE - 1} consecutive rate_limit failures -> still cooldown, not disabled",
     state == "cooldown")
state = record_failure(con4, "cerebras", "m4", "429 tokens per minute", "QuotaExceededError", now=T0)
check(f"{MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE}th consecutive failure -> disabled",
     state == "disabled")

# --- record_success resets counters but does NOT clear disabled ---
p5 = db.new_scratch_db_path()
con5 = db.init_db(p5)
record_failure(con5, "groq", "m5", "413 Request too large", "RuntimeError", now=T0)
record_failure(con5, "groq", "m5", "413 Request too large", "RuntimeError", now=T0)
check("disabled after 2 structural failures", health_state(con5, "groq", "m5").state == "disabled")
result = record_success(con5, "groq", "m5", now=T0)
check("a success does NOT auto-clear a disabled provider", result == "disabled")
check("state remains disabled after the success", health_state(con5, "groq", "m5").state == "disabled")

reset_provider(con5, "groq", "m5", reason="test: manual reset after tier upgrade", now=T0)
check("explicit reset_provider clears disabled -> healthy",
     health_state(con5, "groq", "m5").state == "healthy")
check("reset reason is recorded", "manual reset" in (health_state(con5, "groq", "m5").last_failure_reason or ""))

# --- record_success on a healthy/cooldown provider resets to healthy ---
p6 = db.new_scratch_db_path()
con6 = db.init_db(p6)
record_failure(con6, "openrouter", "m6", "timeout", "RuntimeError", now=T0)
check("in cooldown after 1 'other' failure", health_state(con6, "openrouter", "m6").state == "cooldown")
record_success(con6, "openrouter", "m6", now=T0)
hs6 = health_state(con6, "openrouter", "m6")
check("success resets cooldown -> healthy", hs6.state == "healthy")
check("success resets consecutive_failures to 0", hs6.consecutive_failures == 0)

# --- can_call_now respects cooldown_until timing exactly ---
p7 = db.new_scratch_db_path()
con7 = db.init_db(p7)
record_failure(con7, "cerebras", "m7", "429 tokens per minute", "QuotaExceededError", now=T0)
ok, reason = can_call_now(con7, "cerebras", "m7", now=T0 + timedelta(seconds=10))
check("still in cooldown 10s after a 30s backoff", ok is False and "cooldown" in reason)
ok, reason = can_call_now(con7, "cerebras", "m7", now=T0 + timedelta(seconds=31))
check("cooldown has expired 31s after a 30s backoff", ok is True and reason is None)

# unknown (never-seen) provider is healthy by default
ok, reason = can_call_now(con7, "brand_new_provider", "m0")
check("an unknown provider defaults to healthy/allowed", ok is True and reason is None)

# --- retry_budget_remaining ---
p8 = db.new_scratch_db_path()
con8 = db.init_db(p8)
check("fresh provider has full retry budget",
     retry_budget_remaining(con8, "x", "y") == MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE)
record_failure(con8, "x", "y", "timeout", "RuntimeError", now=T0)
check("budget decrements by 1 after a failure",
     retry_budget_remaining(con8, "x", "y") == MAX_CONSECUTIVE_FAILURES_BEFORE_DISABLE - 1)

# --- call_with_reliability_guard: single-attempt semantics, no internal retry loop ---
p9 = db.new_scratch_db_path()
con9 = db.init_db(p9)
calls = {"n": 0}


def failing_call():
    calls["n"] += 1
    raise RuntimeError("429 rate_limit_exceeded")


try:
    call_with_reliability_guard(con9, failing_call, provider="testg", model_id="m9")
    check("guard re-raises the original exception on failure", False)
except RuntimeError as e:
    check("guard re-raises the original exception on failure", "429" in str(e))
check("guard made exactly ONE call attempt (never an internal retry loop)", calls["n"] == 1)
check("guard recorded the failure into provider_reliability_state",
     health_state(con9, "testg", "m9").state == "cooldown")

# a second guarded call while in cooldown must NOT even attempt the underlying call
try:
    call_with_reliability_guard(con9, failing_call, provider="testg", model_id="m9")
    check("guard blocks a call while in cooldown (ProviderInCooldownError)", False)
except ProviderInCooldownError:
    check("guard blocks a call while in cooldown (ProviderInCooldownError)", True)
check("blocked call did NOT invoke the underlying call_fn again", calls["n"] == 1)

# a disabled provider raises ProviderDisabledError, not ProviderInCooldownError
p10 = db.new_scratch_db_path()
con10 = db.init_db(p10)
record_failure(con10, "groq", "m10", "413 Request too large", "RuntimeError", now=T0)
record_failure(con10, "groq", "m10", "413 Request too large", "RuntimeError", now=T0)
try:
    call_with_reliability_guard(con10, lambda: (_ for _ in ()).throw(RuntimeError("should not run")),
                                provider="groq", model_id="m10")
    check("guard raises ProviderDisabledError for a disabled provider", False)
except ProviderDisabledError:
    check("guard raises ProviderDisabledError for a disabled provider", True)

# --- call_with_reliability_guard: success path records success ---
p11 = db.new_scratch_db_path()
con11 = db.init_db(p11)
result = call_with_reliability_guard(con11, lambda: "ok", provider="good", model_id="m11")
check("guard returns the call's real result on success", result == "ok")
check("guard records success", health_state(con11, "good", "m11").state == "healthy")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
