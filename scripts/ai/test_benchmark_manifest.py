"""Tests for benchmark_manifest.py -- deterministic, no live calls.
Verifies the frozen ROUND3_MANIFEST is internally consistent, that its
content hash is tamper-evident, and that document_versions match the
REAL current document text (proving the manifest wasn't hand-typed wrong
and wasn't silently drifted from the actual gold-set files).

  PYTHONPATH=src python scripts/ai/test_benchmark_manifest.py
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot.documents.benchmark_manifest import (  # noqa: E402
    ROUND3_MANIFEST, ROUND3_MANIFEST_HASH, BenchmarkManifest, validate_documents_unchanged,
    validate_manifest_unchanged)
from ngxrot.documents.prompts import DRAFT_PROMPT_VERSION  # noqa: E402
from benchmark_gold_set import GOLD  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


# --- ROUND3_MANIFEST is internally consistent with the actual codebase ---
check("ROUND3_MANIFEST.prompt_version matches the REAL prompts.DRAFT_PROMPT_VERSION "
     "(frozen manifest must reflect the actual unchanged prompt, not a guess)",
     ROUND3_MANIFEST.prompt_version == DRAFT_PROMPT_VERSION)
check("ROUND3_MANIFEST.max_tokens matches production's real value (extract.py:172, 16384) "
     "and Round 1/2's own value -- frozen, not silently changed",
     ROUND3_MANIFEST.max_tokens == 16384)
check("ROUND3_MANIFEST document_ids is exactly the 10 gold-set documents, no more no less",
     set(ROUND3_MANIFEST.document_ids) == set(GOLD.keys()))
check("ROUND3_MANIFEST excludes Groq (DISABLED -- do not waste benchmark capacity)",
     "groq" not in ROUND3_MANIFEST.providers)
check("ROUND3_MANIFEST includes all 3 remaining EXPERIMENTAL candidates (openrouter, cerebras x2) "
     "plus the gemini control",
     set(ROUND3_MANIFEST.providers) == {"cerebras", "openrouter", "gemini"})
check("ROUND3_MANIFEST.models records 4 distinct model identities (2 Cerebras + OpenRouter + Gemini)",
     len(ROUND3_MANIFEST.models) == 4)

# --- content_hash is deterministic and tamper-evident ---
check("content_hash() is deterministic across repeated calls",
     ROUND3_MANIFEST.content_hash() == ROUND3_MANIFEST.content_hash())
check("ROUND3_MANIFEST_HASH matches a fresh content_hash() call",
     ROUND3_MANIFEST.content_hash() == ROUND3_MANIFEST_HASH)
check("validate_manifest_unchanged: the real manifest against its own real hash -> True",
     validate_manifest_unchanged(ROUND3_MANIFEST, ROUND3_MANIFEST_HASH) is True)

tampered = replace(ROUND3_MANIFEST, max_tokens=8192)  # simulates someone quietly
                                                       # lowering the budget to rescue a
                                                       # struggling provider after seeing results
check("validate_manifest_unchanged: a tampered copy (max_tokens changed) -> False, detected",
     validate_manifest_unchanged(tampered, ROUND3_MANIFEST_HASH) is False)

tampered_prompt = replace(ROUND3_MANIFEST, prompt_version="financial_reasoning_draft_v4_rescue")
check("validate_manifest_unchanged: a tampered prompt_version -> False, detected",
     validate_manifest_unchanged(tampered_prompt, ROUND3_MANIFEST_HASH) is False)

check("content_hash is insensitive to document_ids ORDER (same set, different order -> same hash)",
     replace(ROUND3_MANIFEST, document_ids=tuple(reversed(ROUND3_MANIFEST.document_ids))).content_hash()
     == ROUND3_MANIFEST.content_hash())

# --- validate_documents_unchanged against the REAL current document files ---
doc_texts = {d: (ROOT / "data" / "staging" / "document_text" / f"{d}.txt").read_text(encoding="utf-8")
            for d in ROUND3_MANIFEST.document_ids}
mismatches = validate_documents_unchanged(ROUND3_MANIFEST, doc_texts)
check("validate_documents_unchanged: ALL 10 real documents match the frozen manifest exactly "
     "(proves the manifest's hashes were computed correctly, not hand-typed wrong)",
     len(mismatches) == 0)

altered_texts = dict(doc_texts)
altered_texts[ROUND3_MANIFEST.document_ids[0]] += "\n[SILENTLY APPENDED TEXT]"
mismatches2 = validate_documents_unchanged(ROUND3_MANIFEST, altered_texts)
check("validate_documents_unchanged: detects a single altered document out of 10",
     len(mismatches2) == 1 and str(ROUND3_MANIFEST.document_ids[0]) in mismatches2[0])

missing_doc_texts = {d: t for d, t in doc_texts.items() if d != ROUND3_MANIFEST.document_ids[0]}
mismatches3 = validate_documents_unchanged(ROUND3_MANIFEST, missing_doc_texts)
check("validate_documents_unchanged: a document missing from the provided set is reported, not silently skipped",
     any("not provided" in m for m in mismatches3))

# --- BenchmarkManifest is frozen (immutable) ---
try:
    ROUND3_MANIFEST.max_tokens = 999  # type: ignore
    check("BenchmarkManifest instances are immutable (frozen dataclass)", False)
except Exception:
    check("BenchmarkManifest instances are immutable (frozen dataclass)", True)

# --- a minimal synthetic manifest round-trips correctly ---
synthetic = BenchmarkManifest(
    benchmark_version="test-v1", prompt_version="p1", schema_version="s1",
    document_ids=(1, 2), document_versions={1: "aaa", 2: "bbb"}, providers=("x",),
    models={"x": "model1"}, temperature="default", reasoning_settings="default",
    max_tokens=100, context_strategy="inline", grading_version="g1")
check("a minimal synthetic manifest computes a real, non-empty content_hash",
     isinstance(synthetic.content_hash(), str) and len(synthetic.content_hash()) == 64)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
