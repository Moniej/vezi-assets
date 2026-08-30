"""Frozen benchmark manifest (2026-08-14, Round 3 planning). A manifest is
declared and content-hashed BEFORE a benchmark round begins. Changing any
field in a round's manifest after seeing that round's results would be
exactly the "optimize the test instead of measuring reality" failure mode
this whole layer exists to prevent -- so `content_hash()` makes the
manifest itself tamper-evident: if any field changes, the hash changes,
and `validate_manifest_unchanged()` can prove a manifest was (or wasn't)
altered between declaration and execution.

`document_versions` uses `cache.document_text_hash()` -- REUSED, not
duplicated -- so a manifest can also detect if a benchmark document's
underlying text silently changed on disk between planning and execution.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class BenchmarkManifest:
    benchmark_version: str
    prompt_version: str
    schema_version: str
    document_ids: tuple[int, ...]
    document_versions: dict[int, str]      # doc_id -> sha256(document text), via cache.document_text_hash
    providers: tuple[str, ...]
    models: dict[str, str]                 # provider -> model_id
    temperature: str                       # see ROUND3_MANIFEST's note -- currently unpluggable, not silently unset
    reasoning_settings: str                # same caveat
    max_tokens: int
    context_strategy: str
    grading_version: str

    def content_hash(self) -> str:
        """Sha256 of a canonical (sorted-key) JSON representation -- the
        manifest's own tamper-evidence mechanism. Tuples/dicts sorted
        deterministically so field ORDER never changes the hash, only
        field VALUES do."""
        payload = asdict(self)
        payload["document_ids"] = sorted(payload["document_ids"])
        payload["providers"] = sorted(payload["providers"])
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_manifest_unchanged(manifest: BenchmarkManifest, recorded_hash: str) -> bool:
    """True iff `manifest` still hashes to `recorded_hash` -- i.e. nothing
    was edited since the hash was first recorded (e.g. at plan-approval
    time). False means the manifest drifted and the round it governs
    should NOT be treated as having run under frozen conditions."""
    return manifest.content_hash() == recorded_hash


def validate_documents_unchanged(manifest: BenchmarkManifest, doc_text_by_id: dict[int, str]) -> list[str]:
    """Recomputes document_text_hash for each doc_id in doc_text_by_id and
    compares against the manifest's frozen document_versions. Returns a
    list of human-readable mismatch descriptions (empty list = all
    documents match the frozen manifest, i.e. real evidence, not
    something quietly re-sourced after planning)."""
    from .cache import document_text_hash  # local import -- keeps this
                                           # module import-light for tests
                                           # that don't need the full
                                           # cache.py dependency chain
    mismatches = []
    for doc_id in manifest.document_ids:
        if doc_id not in doc_text_by_id:
            mismatches.append(f"doc_id {doc_id}: not provided for validation")
            continue
        actual_hash = document_text_hash(doc_text_by_id[doc_id])
        expected_hash = manifest.document_versions.get(doc_id)
        if actual_hash != expected_hash:
            mismatches.append(f"doc_id {doc_id}: hash mismatch (manifest={expected_hash}, "
                             f"actual={actual_hash}) -- document text changed since the manifest was frozen")
    return mismatches


# ---------------------------------------------------------------------------
# ROUND 3 -- the actual frozen manifest for the plan in
# docs/ai/AI_PROVIDER_BENCHMARK_ROUND3_PLAN_2026-08-14.md. Real document
# hashes, computed from the real files at data/staging/document_text/.
# providers/models restricted to the 4 identities still worth spending
# benchmark capacity on (Groq excluded -- DISABLED; zai-glm-4.7 excluded --
# not in this round's authorized scope, see the plan doc).
# ---------------------------------------------------------------------------

ROUND3_DOCUMENT_VERSIONS = {
    452: "6ad6d1f4c0c2b8dee77ce938adcd6e04eb9bad42e8ee39c3ebd85452a6af4c76",
    9530: "d2099cf746b5602c4f5876f52a1b0df3328701c267f73b39ab4dcb07b023b70d",
    9485: "fa788086c2784753446b35457e130dc7d6311b7e97dc96bc4174807c6095359d",
    4245: "c8a7f878560edcb55de34f7f7d4c88efc1e8308a21976637082ef8f2460cfa00",
    4508: "065cdabe4fb6055a775570265a42a961b0a3fb38623b8708419c37784503e12a",
    5163: "bd0adee729e8f0812e311229ed682165497cb500d25b98299059b9c9616b225d",
    10625: "2a38530d8d74ef21de8c672ca2aed649503a8382e83621e504de936bf7523200",
    7793: "f3ddfda9c1310357eacd93d70f09bb96bb361b9861611a1e22fb147a53a02009",
    6393: "6a88d8c4a4453bcb8305620c744733604ef46725f23787811a894db3417da858",
    11122: "fd761a8dadb1c8b59a08f0b93e35bc130c0d8591f1de5960f3127c97d8261577",
}

ROUND3_MANIFEST = BenchmarkManifest(
    benchmark_version="round3-plan-2026-08-14",
    prompt_version="financial_reasoning_draft_v3",  # prompts.DRAFT_PROMPT_VERSION, UNCHANGED
    schema_version="draft_schema_v3_pilot_fact_types",  # the _DRAFT_SCHEMA_INSTRUCTIONS shape in
                                                        # prompts.py as of this manifest's freeze --
                                                        # UNCHANGED from Rounds 1-2
    document_ids=(452, 9530, 9485, 4245, 4508, 5163, 10625, 7793, 6393, 11122),
    document_versions=ROUND3_DOCUMENT_VERSIONS,
    providers=("cerebras", "cerebras", "openrouter", "gemini"),
    models={"cerebras_gemma": "gemma-4-31b", "cerebras_gptoss": "gpt-oss-120b",
           "openrouter": "meta-llama/llama-3.3-70b-instruct", "gemini": "gemini-3.6-flash"},
    temperature="provider default (unspecified) -- IDENTICAL to Round 1/2. Adding explicit "
               "temperature control to llm_providers.py would itself be a provider-behavior "
               "change requiring separate authorization; NOT built as part of this planning task. "
               "This is a named execution blocker, not a silent gap -- see the plan doc's "
               "'execution prerequisites' section.",
    reasoning_settings="provider default (unspecified) -- same caveat as temperature; no "
                       "reasoning-effort control currently implemented for gpt-oss-120b/zai-glm-4.7.",
    max_tokens=16384,  # matches production (extract.py:172) and Rounds 1-2 exactly
    context_strategy="full document text inline in the user prompt (build_draft_prompt's actual, "
                     "only behavior -- no chunking/retrieval strategy exists in this codebase)",
    grading_version="grade_benchmark_v3_round3",  # grade_benchmark.py's matcher-fix version (the
                                                  # AFRIPRUD/CAP period-matching corrections made
                                                  # during Round 1) PLUS the new schema_compliance_check
                                                  # and evidence-fidelity line-citation check added
                                                  # for Round 3 -- see the plan doc
)

ROUND3_MANIFEST_HASH = ROUND3_MANIFEST.content_hash()
