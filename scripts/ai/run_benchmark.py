"""AI Provider Expansion Phase 2 -- Nigerian Financial Document Benchmark
runner. Runs the SAME v3 draft-reasoning prompt (build_draft_prompt,
UNCHANGED -- reused, not duplicated) against 6 model identities for each
document in benchmark_gold_set.GOLD, using benchmark_complete() so all
traffic lands in benchmark_calls (scratch DB) and NEVER llm_calls/
extracted_facts/financial_reasoning_conclusions. Writes raw results to a
JSON file incrementally so a partial run is never lost.

Same document text + same task + same extraction schema + same max_tokens
(16384, matching production's own real value) for every model -- no
provider-specific prompt advantage.

  GEMINI_API_KEY=... GROQ_API_KEY=... CEREBRAS_API_KEY=... OPENROUTER_API_KEY=... \\
  PYTHONPATH=src python scripts/ai/run_benchmark.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.documents import llm_providers as lp  # noqa: E402
from ngxrot.documents.benchmark_cache import benchmark_complete  # noqa: E402
from ngxrot.documents.json_utils import parse_json_object  # noqa: E402
from ngxrot.documents.prompts import DRAFT_PROMPT_VERSION, build_draft_prompt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_gold_set import GOLD  # noqa: E402

RESULTS_PATH = ROOT / "data" / "staging" / "benchmark_results_2026-08-13.json"
MAX_TOKENS = 16384  # matches extract.py's real production call exactly (extract.py:172)

MODEL_IDENTITIES = [
    # (label, provider_name, model_id) -- provider_name resolves via
    # build_experimental_provider() for the three experimental providers, or
    # GeminiProvider directly for the control. "actual_model" is filled in
    # per-call from the response (OpenRouter especially can differ).
    ("gemini-control", "gemini", None),  # model_id filled from configs/llm_provider.toml
    ("groq-llama-3.3-70b-versatile", "groq", "llama-3.3-70b-versatile"),
    ("openrouter-llama-3.3-70b-instruct", "openrouter", "meta-llama/llama-3.3-70b-instruct"),
    ("cerebras-gemma-4-31b", "cerebras", "gemma-4-31b"),
    ("cerebras-zai-glm-4.7", "cerebras", "zai-glm-4.7"),
    ("cerebras-gpt-oss-120b", "cerebras", "gpt-oss-120b"),
]


def build_provider(provider_name: str, model_id: str | None):
    if provider_name == "gemini":
        cfg = lp.load_llm_config()
        return lp.GeminiProvider(model_id=model_id or cfg.model_id)
    return lp.build_experimental_provider(provider_name, model_id)


def load_results() -> list[dict]:
    if RESULTS_PATH.exists():
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return []


def save_results(results: list[dict]) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


def already_done(results: list[dict], doc_id: int, label: str) -> bool:
    return any(r["doc_id"] == doc_id and r["benchmark_identity"] == label for r in results)


def main() -> None:
    scratch_path = Path(tempfile.mkdtemp()) / "ngx_scratch.sqlite"
    shutil.copy2(ROOT / "data" / "ngx.sqlite", scratch_path)
    con = mdb.init_db(scratch_path)
    print(f"Scratch DB: {scratch_path} (production data/ngx.sqlite copied, read-only source, "
         f"never written back)")

    results = load_results()
    print(f"Resuming with {len(results)} prior results already recorded" if results else
         "Starting fresh")

    doc_ids = list(GOLD.keys())
    print(f"{len(doc_ids)} documents x {len(MODEL_IDENTITIES)} model identities = "
         f"{len(doc_ids) * len(MODEL_IDENTITIES)} total benchmark cases")

    for doc_id in doc_ids:
        spec = GOLD[doc_id]
        row = con.execute(
            "SELECT ticker, doc_type, filing_date, char_count FROM documents WHERE doc_id=?",
            (doc_id,)).fetchone()
        ticker, doc_type, filing_date, char_count = row
        doc_text_path = ROOT / "data" / "staging" / "document_text" / f"{doc_id}.txt"
        doc_text = doc_text_path.read_text(encoding="utf-8")
        system_prompt, user_prompt = build_draft_prompt(doc_text, ticker, doc_type, filing_date)

        for label, provider_name, model_id in MODEL_IDENTITIES:
            if already_done(results, doc_id, label):
                print(f"[skip, already done] doc={doc_id} ({ticker}) identity={label}")
                continue

            print(f"\n=== doc={doc_id} ({ticker}, {char_count} chars) identity={label} ===")
            t0 = time.time()
            entry = {
                "doc_id": doc_id, "ticker": ticker, "char_count": char_count,
                "benchmark_identity": label, "provider": provider_name,
                "requested_model": model_id, "prompt_version": DRAFT_PROMPT_VERSION,
                "max_tokens_configured": MAX_TOKENS, "timestamp": datetime.now().isoformat(),
            }
            try:
                provider = build_provider(provider_name, model_id)
            except Exception as e:
                entry.update(success=False, failure_reason=f"provider construction failed: "
                            f"{type(e).__name__}: {e}")
                results.append(entry)
                save_results(results)
                print(f"  FAILED (construction): {e}")
                continue

            try:
                resp = benchmark_complete(
                    con, provider, doc_id=doc_id, purpose="benchmark_draft_reasoning",
                    prompt_version=DRAFT_PROMPT_VERSION, system_prompt=system_prompt,
                    user_prompt=user_prompt, max_tokens=MAX_TOKENS,
                    cache_dir=ROOT / "data" / "staging" / "benchmark_cache")
            except Exception as e:
                entry.update(success=False, failure_reason=f"{type(e).__name__}: {e}",
                            latency_ms=int((time.time() - t0) * 1000))
                results.append(entry)
                save_results(results)
                print(f"  FAILED: {type(e).__name__}: {e}")
                continue

            parsed = parse_json_object(resp.response_text)
            entry.update(
                actual_model=resp.model_id, latency_ms=int(resp.latency_s * 1000),
                input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                served_from_cache=resp.cached, raw_response=resp.response_text,
                parsed_response=parsed, structured_output_success=parsed is not None,
                success=True, failure_reason=None,
            )
            results.append(entry)
            save_results(results)
            n_facts = len(parsed.get("facts", [])) if parsed else 0
            print(f"  OK actual_model={resp.model_id} latency={resp.latency_s:.1f}s "
                 f"out_tokens={resp.output_tokens} facts_returned={n_facts} "
                 f"structured_ok={parsed is not None}")

    print(f"\nDone. {len(results)} results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
