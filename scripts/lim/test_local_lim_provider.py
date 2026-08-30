"""Tests for LocalLIMProvider isolation and safe rejection (LIM Economic
Viability Audit, Phase 1). Does NOT require CUDA/torch/unsloth or a real
subprocess call -- these test the SAFETY WRAPPER (gate check, registry
isolation, error typing), not inference quality (that's Phase 2's job).

  PYTHONPATH=src python scripts/lim/test_local_lim_provider.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.documents.llm_providers import (  # noqa: E402
    PROVIDER_REGISTRY, GeminiProvider, LIMQualityGateError, LocalLIMProvider,
    LLMConfig, build_default_provider, lim_quality_gate_status,
)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


# --- Registry isolation: local_lim must never be a lookup-by-name target ---
check("PROVIDER_REGISTRY contains exactly {'gemini'} -- local_lim is NOT registered",
     set(PROVIDER_REGISTRY.keys()) == {"gemini"})
check("PROVIDER_REGISTRY['gemini'] is still GeminiProvider (existing behavior unchanged)",
     PROVIDER_REGISTRY["gemini"] is GeminiProvider)

# --- build_default_provider must refuse local_lim explicitly, not silently fall back ---
cfg = LLMConfig(provider="local_lim", model_id="whatever", api_key_env_var="X")
try:
    build_default_provider(config=cfg)
    check("build_default_provider(provider='local_lim') raises", False)
except LIMQualityGateError:
    check("build_default_provider(provider='local_lim') raises LIMQualityGateError "
         "(not a silent fallback to Gemini, not a generic ValueError)", True)
except Exception as e:  # noqa: BLE001
    check(f"build_default_provider(provider='local_lim') raises the RIGHT error type "
         f"(got {type(e).__name__} instead)", False)

# --- an unrelated bad provider name still gets the original, unmodified error ---
cfg2 = LLMConfig(provider="totally_unknown_vendor", model_id="x", api_key_env_var="X")
try:
    build_default_provider(config=cfg2)
    check("build_default_provider with an unknown (non-LIM) provider raises", False)
except LIMQualityGateError:
    check("an unrelated unknown provider does NOT get mis-routed into the LIM error path", False)
except ValueError:
    check("build_default_provider with an unrelated unknown provider still raises "
         "plain ValueError (LIM special-case did not change other error paths)", True)

# --- lim_quality_gate_status: no file on disk -> NOT passed, never an unknown-default-True ---
missing_path = ROOT / "lim_training" / "quality_gate_status_DOES_NOT_EXIST.json"
status = lim_quality_gate_status(path=missing_path)
check("lim_quality_gate_status() with no file present returns passed=False (never assumes PASS)",
     status.get("passed") is False)
check("lim_quality_gate_status() with no file present names WHY in 'reason'",
     "reason" in status and "never been evaluated" in status["reason"])

# --- Direct construction: refuses without gate pass or explicit opt-in ---
try:
    LocalLIMProvider(model_id="test", gate_status={"passed": False, "reason": "test fixture"})
    check("LocalLIMProvider() with gate_status passed=False raises", False)
except LIMQualityGateError as e:
    check("LocalLIMProvider() with gate_status passed=False raises LIMQualityGateError",
         True)
    check("the raised error message references the actual failure reason, not a generic string",
         "test fixture" in str(e))

# --- Direct construction: gate PASS allows it through to the checkpoint-dir check ---
try:
    LocalLIMProvider(model_id="test", checkpoint_dir=str(ROOT),  # ROOT exists as a dir --
                     gate_status={"passed": True})               # only checking the gate short-circuits, not that ROOT is a real checkpoint
    check("LocalLIMProvider() with gate_status passed=True does NOT raise LIMQualityGateError", True)
except LIMQualityGateError:
    check("LocalLIMProvider() with gate_status passed=True does NOT raise LIMQualityGateError", False)

# --- allow_unvalidated=True bypasses the gate even when it has NOT passed ---
try:
    LocalLIMProvider(model_id="test", checkpoint_dir=str(ROOT),
                     gate_status={"passed": False}, allow_unvalidated=True)
    check("LocalLIMProvider(allow_unvalidated=True) bypasses an unpassed gate "
         "(the ONE legitimate escape hatch, for the eval harness itself)", True)
except LIMQualityGateError:
    check("LocalLIMProvider(allow_unvalidated=True) bypasses an unpassed gate", False)

# --- A nonexistent checkpoint dir still fails, even with the gate satisfied ---
try:
    LocalLIMProvider(model_id="test", checkpoint_dir=str(ROOT / "definitely_not_a_real_dir_xyz"),
                     gate_status={"passed": True})
    check("LocalLIMProvider() with a nonexistent checkpoint_dir raises", False)
except LIMQualityGateError:
    check("a nonexistent checkpoint_dir raises the right (non-gate) error, not LIMQualityGateError", False)
except RuntimeError:
    check("LocalLIMProvider() with a nonexistent checkpoint_dir raises RuntimeError "
         "(gate passing does not bypass basic existence checks)", True)

# --- The REAL gate file on disk today: confirm it reads as NOT passed ---
# (LIM has never cleared a real quality gate as of this audit -- if this
# flips to True unexpectedly, that's a real signal worth noticing, not a
# test to silently adjust.)
real_status = lim_quality_gate_status()
check("the REAL on-disk quality gate (lim_training/quality_gate_status.json) is NOT "
     "passed as of this test run -- LIM has not been promoted",
     real_status.get("passed") is not True)

# --- Confirm the real (ungated) path used by production scripts still refuses ---
try:
    LocalLIMProvider(model_id="qwen3-4b-lim")
    check("constructing LocalLIMProvider with the REAL on-disk gate (no override) raises", False)
except LIMQualityGateError:
    check("constructing LocalLIMProvider with the REAL on-disk gate (no override) "
         "raises LIMQualityGateError -- confirms the safety wrapper is live, not just "
         "testable in isolation", True)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
