"""One trivial live completion call per experimental provider, using
whichever of GROQ_API_KEY/CEREBRAS_API_KEY/OPENROUTER_API_KEY are present
in the environment. This is a CONNECTIVITY check only (Phase 1C) -- NOT
financial-extraction benchmarking (Phase 3, still deferred). Writes
nothing to any database. Never prints a key value.

  PYTHONPATH=src python scripts/ai/live_connectivity_check.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.documents import llm_providers as lp  # noqa: E402

CANDIDATES = [
    ("groq", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    ("cerebras", "CEREBRAS_API_KEY", "llama-3.3-70b"),
    ("openrouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct"),
]

for name, env_key, model_id in CANDIDATES:
    key = os.environ.get(env_key)
    if not key:
        print(f"{name}: SKIPPED -- {env_key} not present in this process's environment")
        continue
    try:
        provider = lp.build_experimental_provider(name, model_id, api_key=key)
    except Exception as e:
        print(f"{name}: CONSTRUCTION FAILED -- {type(e).__name__}: {e}")
        continue
    result = lp.health_check(provider)
    status = "OK" if result["ok"] else "FAILED"
    print(f"{name} ({model_id}): {status} -- latency={result['latency_s']:.2f}s "
         f"model_returned={result['model_id']} error={result['error']}")
