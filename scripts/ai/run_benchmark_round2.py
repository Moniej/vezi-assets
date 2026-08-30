"""AI Provider Expansion -- Round 2 benchmark (2026-08-13), same gold set,
prompt version, schema, and methodology as Round 1 (scripts/ai/run_benchmark.py).
Separate results file so Round 1 is never overwritten/mutated.

Priority order per this round's authorization:
  1. cerebras-gemma-4-31b   (standard, max_tokens=16384, all 10 docs)
  2. openrouter-llama-3.3-70b-instruct (standard, max_tokens=16384, all 10 docs)
  3. gemini-control          (standard, max_tokens=16384, all 10 docs --
                              ONE probe call first; if still quota-exhausted,
                              skip the rest WITHOUT further polling)
  4. cerebras-gpt-oss-120b   (standard, max_tokens=16384, all 10 docs --
                              Round 1 already proved this budget sufficient
                              on 9/10 docs, so no separate probe needed)
  5. groq-llama-3.3-70b-versatile-REDUCED-BUDGET -- explicitly NOT the same
     task as the other identities. Round 1 showed Groq's 12,000 TPM cap
     rejects EVERY document at max_tokens=16384 (prompt tokens alone
     exceed 12,000 for MTNN and ELLAHLAKES). Per this round's explicit
     authorization ("only if the benchmark can operate within the
     confirmed 12,000 TPM limit"), this identity uses a PER-DOCUMENT
     reduced max_tokens computed from Round 1's own real request-size
     telemetry, and SKIPS documents that are mathematically infeasible
     regardless of max_tokens (prompt tokens alone >= 12,000) rather than
     firing a guaranteed-429 request. This is a deliberately different,
     clearly-labeled condition -- never conflated with the other
     identities' identical-task comparison.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngxrot import db as mdb  # noqa: E402
from ngxrot.documents import llm_providers as lp  # noqa: E402
from ngxrot.documents.benchmark_cache import benchmark_complete  # noqa: E402
from ngxrot.documents.json_utils import parse_json_object  # noqa: E402
from ngxrot.documents.prompts import DRAFT_PROMPT_VERSION, build_draft_prompt  # noqa: E402
from benchmark_gold_set import GOLD  # noqa: E402

RESULTS_PATH = ROOT / "data" / "staging" / "benchmark_results_round2_2026-08-13.json"
MAX_TOKENS_STANDARD = 16384

# From Round 1's real 413 error telemetry ("Requested X" at max_tokens=16384):
# prompt_tokens = X - 16384. Computed once from real data, not re-probed
# live (that would itself be a poll). Docs not listed here (5163 UACN,
# 10625 OANDO, 6393 MTNN, 11122 ELLAHLAKES) either have prompt_tokens
# already >= 12,000 alone (MTNN: ~13,680; ELLAHLAKES: ~36,112) or leave a
# margin too thin (<2,600 tokens, UACN/OANDO) to produce a meaningful
# structured-JSON response for this schema -- SKIPPED, not attempted, to
# avoid a guaranteed or near-guaranteed 429 poll.
GROQ_PROMPT_TOKENS = {
    452: 3213,    # STANBIC
    9530: 2678,   # MORISON
    9485: 3358,   # TRANSCORP
    4245: 5013,   # AFRIPRUD
    4508: 4409,   # CAP
    7793: 6374,   # UBA
}
GROQ_TPM_CAP = 12000
GROQ_SAFETY_MARGIN = 300


def groq_reduced_max_tokens(doc_id: int) -> int | None:
    if doc_id not in GROQ_PROMPT_TOKENS:
        return None
    budget = GROQ_TPM_CAP - GROQ_PROMPT_TOKENS[doc_id] - GROQ_SAFETY_MARGIN
    return max(budget, 0) if budget > 500 else None  # <500 tokens can't hold real JSON output


STANDARD_IDENTITIES = [
    ("cerebras-gemma-4-31b", "cerebras", "gemma-4-31b"),
    ("openrouter-llama-3.3-70b-instruct", "openrouter", "meta-llama/llama-3.3-70b-instruct"),
    ("gemini-control", "gemini", None),
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


def run_one(con, results, doc_id, ticker, doc_type, filing_date, doc_text,
           label, provider_name, model_id, max_tokens, round_note=""):
    if already_done(results, doc_id, label):
        print(f"[skip, already done] doc={doc_id} ({ticker}) identity={label}")
        return
    system_prompt, user_prompt = build_draft_prompt(doc_text, ticker, doc_type, filing_date)
    print(f"\n=== round2 doc={doc_id} ({ticker}) identity={label} max_tokens={max_tokens} "
         f"{round_note} ===")
    t0 = time.time()
    entry = {
        "doc_id": doc_id, "ticker": ticker, "benchmark_identity": label,
        "provider": provider_name, "requested_model": model_id,
        "prompt_version": DRAFT_PROMPT_VERSION, "max_tokens_configured": max_tokens,
        "round_note": round_note, "timestamp": datetime.now().isoformat(),
    }
    try:
        provider = build_provider(provider_name, model_id)
    except Exception as e:
        entry.update(success=False, failure_reason=f"provider construction failed: "
                    f"{type(e).__name__}: {e}")
        results.append(entry)
        save_results(results)
        print(f"  FAILED (construction): {e}")
        return
    try:
        resp = benchmark_complete(
            con, provider, doc_id=doc_id, purpose="benchmark_draft_reasoning_round2",
            prompt_version=DRAFT_PROMPT_VERSION, system_prompt=system_prompt,
            user_prompt=user_prompt, max_tokens=max_tokens,
            cache_dir=ROOT / "data" / "staging" / "benchmark_cache_round2")
    except Exception as e:
        entry.update(success=False, failure_reason=f"{type(e).__name__}: {e}",
                    latency_ms=int((time.time() - t0) * 1000))
        results.append(entry)
        save_results(results)
        print(f"  FAILED: {type(e).__name__}: {e}")
        return
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
         f"out_tokens={resp.output_tokens} facts_returned={n_facts} structured_ok={parsed is not None}")


def main() -> None:
    scratch_path = Path(tempfile.mkdtemp()) / "ngx_scratch.sqlite"
    shutil.copy2(ROOT / "data" / "ngx.sqlite", scratch_path)
    con = mdb.init_db(scratch_path)
    results = load_results()
    print(f"Round 2. Resuming with {len(results)} prior results" if results else "Round 2. Starting fresh")

    doc_ids = list(GOLD.keys())
    doc_meta = {}
    for doc_id in doc_ids:
        row = con.execute("SELECT ticker, doc_type, filing_date FROM documents WHERE doc_id=?",
                          (doc_id,)).fetchone()
        doc_text = (ROOT / "data" / "staging" / "document_text" / f"{doc_id}.txt").read_text(encoding="utf-8")
        doc_meta[doc_id] = (*row, doc_text)

    # --- Gemini: ONE probe call first, per "do not repeatedly poll" ---
    gemini_available = True
    probe_doc = doc_ids[0]
    if not already_done(results, probe_doc, "gemini-control"):
        ticker, doc_type, filing_date, doc_text = doc_meta[probe_doc]
        print("\n--- Gemini quota probe (single attempt, per doc, no retry loop) ---")
        run_one(con, results, probe_doc, ticker, doc_type, filing_date, doc_text,
               "gemini-control", "gemini", None, MAX_TOKENS_STANDARD,
               round_note="quota probe")
        last = results[-1]
        if not last["success"] and "QuotaExceededError" in (last.get("failure_reason") or ""):
            gemini_available = False
            print("Gemini quota probe failed (still exhausted) -- skipping remaining "
                 "9 Gemini calls WITHOUT further polling, per instruction.")

    for label, provider_name, model_id in STANDARD_IDENTITIES:
        if label == "gemini-control" and not gemini_available:
            for doc_id in doc_ids[1:]:
                if not already_done(results, doc_id, label):
                    results.append({
                        "doc_id": doc_id, "ticker": doc_meta[doc_id][0],
                        "benchmark_identity": label, "provider": provider_name,
                        "requested_model": model_id, "prompt_version": DRAFT_PROMPT_VERSION,
                        "max_tokens_configured": MAX_TOKENS_STANDARD,
                        "round_note": "not attempted -- quota confirmed exhausted by probe call, "
                                     "not polled further per instruction",
                        "timestamp": datetime.now().isoformat(), "success": False,
                        "failure_reason": "SKIPPED: quota probe on first document confirmed "
                                         "still exhausted; remaining calls not attempted to avoid "
                                         "polling an exhausted quota",
                    })
            save_results(results)
            continue
        for doc_id in doc_ids:
            ticker, doc_type, filing_date, doc_text = doc_meta[doc_id]
            run_one(con, results, doc_id, ticker, doc_type, filing_date, doc_text,
                   label, provider_name, model_id, MAX_TOKENS_STANDARD)

    # --- Groq, reduced-budget, subset of documents ---
    label = "groq-llama-3.3-70b-versatile-REDUCED-BUDGET"
    for doc_id in doc_ids:
        ticker, doc_type, filing_date, doc_text = doc_meta[doc_id]
        reduced = groq_reduced_max_tokens(doc_id)
        if reduced is None:
            if not already_done(results, doc_id, label):
                results.append({
                    "doc_id": doc_id, "ticker": ticker, "benchmark_identity": label,
                    "provider": "groq", "requested_model": "llama-3.3-70b-versatile",
                    "prompt_version": DRAFT_PROMPT_VERSION, "max_tokens_configured": None,
                    "round_note": "NOT ATTEMPTED -- prompt tokens alone leave <500 tokens of "
                                 "budget under the 12,000 TPM cap (computed from Round 1's real "
                                 "request-size telemetry); a live attempt would be a "
                                 "near-certain 429 poll, not a meaningful test",
                    "timestamp": datetime.now().isoformat(), "success": False,
                    "failure_reason": "SKIPPED: mathematically infeasible under confirmed TPM cap",
                })
                save_results(results)
            print(f"[skip, infeasible] doc={doc_id} ({ticker}) identity={label}")
            continue
        run_one(con, results, doc_id, ticker, doc_type, filing_date, doc_text,
               label, "groq", "llama-3.3-70b-versatile", reduced,
               round_note=f"REDUCED BUDGET ({reduced} tokens, not 16384) to fit the confirmed "
                          f"12,000 TPM cap -- NOT directly comparable to other identities' "
                          f"identical-task results")

    print(f"\nRound 2 done. {len(results)} results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
