"""Round 3 benchmark execution -- authorized 2026-08-14. Runs under
ROUND3_MANIFEST (frozen, content-hashed, validated against real document
text before this script does anything else). Same prompt/schema/max_tokens
as Rounds 1-2 (identical task, no rescue-tuning). Two differences from
Round 1/2's structure, both process/scheduling changes, NOT changes to the
task itself:

  1. Same-provider calls are throttled to a minimum 60s gap (Category F --
     Round 2's diagnosed cause of the Cerebras/Groq operational collapse
     was back-to-back same-provider requests exhausting a rolling
     per-minute token window, not document size or model quality).
  2. ELLAHLAKES (the mandatory case) is attempted FIRST for every
     identity, before any other document can consume a provider's
     rolling-window budget.

Every call goes through call_with_reliability_guard() -- real cooldown/
disabled state, exactly one attempt per invocation, no internal retry
loop. Groq is excluded entirely (DISABLED, confirmed unsuitable across
two independent configurations in Rounds 1-2 -- not re-tested here).
Gemini gets exactly one probe call (on ELLAHLAKES, since it's first),
matching Round 2's "do not poll an exhausted quota" discipline.

Category A (reproducibility repeats) runs AFTER the standard 10-document
pass, using force=True to bypass the on-disk cache -- 3 documents x 3
identities (cerebras-gemma, cerebras-gptoss, openrouter -- Gemini
excluded, its quota won't support 9 more calls) x 3 repeats.
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
from ngxrot.documents.benchmark_manifest import ROUND3_MANIFEST, validate_documents_unchanged  # noqa: E402
from ngxrot.documents.json_utils import parse_json_object  # noqa: E402
from ngxrot.documents.prompts import build_draft_prompt  # noqa: E402
from ngxrot.documents.provider_reliability import (  # noqa: E402
    ProviderDisabledError, ProviderInCooldownError, call_with_reliability_guard)

RESULTS_PATH = ROOT / "data" / "staging" / "benchmark_results_round3_2026-08-14.jsonl"  # JSONL, see load_results()
MIN_PROVIDER_GAP_S = 60.0

# ELLAHLAKES FIRST, then the rest in the original gold-set order.
DOC_ORDER = [11122, 452, 9530, 9485, 4245, 4508, 5163, 10625, 7793, 6393]
assert set(DOC_ORDER) == set(ROUND3_MANIFEST.document_ids)

STANDARD_IDENTITIES = [
    ("cerebras-gemma-4-31b", "cerebras", "gemma-4-31b"),
    ("cerebras-gpt-oss-120b", "cerebras", "gpt-oss-120b"),
    ("openrouter-llama-3.3-70b-instruct", "openrouter", "meta-llama/llama-3.3-70b-instruct"),
]
REPRO_DOCS = [11122, 9485, 4508]  # ELLAHLAKES, TRANSCORP, CAP
REPRO_REPEATS = 3

_last_call_at: dict[str, float] = {}


def throttle(provider: str) -> None:
    last = _last_call_at.get(provider)
    if last is not None:
        elapsed = time.time() - last
        if elapsed < MIN_PROVIDER_GAP_S:
            wait = MIN_PROVIDER_GAP_S - elapsed
            print(f"  [throttle] waiting {wait:.1f}s before next {provider} call "
                 f"(min gap {MIN_PROVIDER_GAP_S}s)")
            time.sleep(wait)
    _last_call_at[provider] = time.time()


def build_provider(provider_name: str, model_id: str | None):
    if provider_name == "gemini":
        cfg = lp.load_llm_config()
        return lp.GeminiProvider(model_id=model_id or cfg.model_id)
    return lp.build_experimental_provider(provider_name, model_id)


def load_results() -> list[dict]:
    """Append-only JSONL, not a single rewritten JSON array -- 2026-08-14
    durability fix. A rewrite-the-whole-file save() truncates the file
    FIRST, then writes; any interruption (crash, disk full, kill) during
    ANY save -- not just the last one -- destroys every prior result, not
    just the newest. Confirmed the hard way this round: a disk-full error
    mid-write wiped 28+ real results that had already been safely on disk
    for many prior saves. One JSON object per line, opened in append mode
    and flushed immediately, means the worst a mid-write crash can do is
    lose the ONE line in progress -- every previously-completed line is
    already durably on disk."""
    if not RESULTS_PATH.exists():
        return []
    results = []
    for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            results.append(json.loads(line))
    return results


def save_results(results: list[dict]) -> None:
    """Appends ONLY the newest entry (results[-1]) -- called after every
    single result, same call sites as before, but no longer rewrites
    history. Safe to call with an empty list (no-op)."""
    if not results:
        return
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(results[-1], default=str))
        f.write("\n")
        f.flush()


def already_done(results, doc_id, label, phase, repeat_index=None) -> bool:
    return any(r["doc_id"] == doc_id and r["benchmark_identity"] == label
              and r.get("phase") == phase and r.get("repeat_index") == repeat_index
              for r in results)


def run_one(con, results, *, doc_id, ticker, doc_type, filing_date, doc_text, label,
           provider_name, model_id, phase, repeat_index=None, force=False):
    if already_done(results, doc_id, label, phase, repeat_index):
        print(f"[skip, already done] doc={doc_id} identity={label} phase={phase} repeat={repeat_index}")
        return
    system_prompt, user_prompt = build_draft_prompt(doc_text, ticker, doc_type, filing_date)
    tag = f"repeat={repeat_index}" if repeat_index is not None else ""
    print(f"\n=== round3 [{phase}] doc={doc_id} ({ticker}) identity={label} {tag} ===")
    entry = {
        "doc_id": doc_id, "ticker": ticker, "benchmark_identity": label, "provider": provider_name,
        "requested_model": model_id, "prompt_version": ROUND3_MANIFEST.prompt_version,
        "max_tokens_configured": ROUND3_MANIFEST.max_tokens, "phase": phase,
        "repeat_index": repeat_index, "manifest_hash": ROUND3_MANIFEST.content_hash(),
        "timestamp": datetime.now().isoformat(),
    }
    try:
        provider = build_provider(provider_name, model_id)
    except Exception as e:
        entry.update(success=False, failure_reason=f"provider construction failed: {type(e).__name__}: {e}")
        results.append(entry)
        save_results(results)
        print(f"  FAILED (construction): {e}")
        return
    resolved_model_id = provider.info.model_id  # never None -- e.g. Gemini's real
                                                # config-resolved model_id, not the
                                                # possibly-None model_id parameter
                                                # (provider_reliability_state.model_id
                                                # is NOT NULL; a raw None here would
                                                # crash the guard before any API call)

    throttle(provider_name)

    def call_fn():
        return benchmark_complete(
            con, provider, doc_id=doc_id, purpose=f"benchmark_round3_{phase}",
            prompt_version=ROUND3_MANIFEST.prompt_version, system_prompt=system_prompt,
            user_prompt=user_prompt, max_tokens=ROUND3_MANIFEST.max_tokens, force=force,
            cache_dir=ROOT / "data" / "staging" / "benchmark_cache_round3")

    try:
        resp = call_with_reliability_guard(con, call_fn, provider=provider_name, model_id=resolved_model_id)
    except (ProviderDisabledError, ProviderInCooldownError) as e:
        entry.update(success=False, failure_reason=f"{type(e).__name__}: {e}",
                    blocked_before_attempt=True)
        results.append(entry)
        save_results(results)
        print(f"  BLOCKED (not attempted): {type(e).__name__}: {e}")
        return
    except Exception as e:
        entry.update(success=False, failure_reason=f"{type(e).__name__}: {e}",
                    blocked_before_attempt=False)
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
         f"out_tokens={resp.output_tokens} facts={n_facts} structured_ok={parsed is not None}")


def main() -> None:
    doc_texts = {d: (ROOT / "data/staging/document_text" / f"{d}.txt").read_text(encoding="utf-8")
                for d in ROUND3_MANIFEST.document_ids}
    mismatches = validate_documents_unchanged(ROUND3_MANIFEST, doc_texts)
    if mismatches:
        print("MANIFEST VALIDATION FAILED -- refusing to run:")
        for m in mismatches:
            print(f"  {m}")
        sys.exit(1)
    print("Manifest validated: all documents match the frozen ROUND3_MANIFEST.")
    print(f"Manifest hash: {ROUND3_MANIFEST.content_hash()}")

    # Proactively clean up leftover scratch copies from EARLIER invocations
    # first -- atexit (below) doesn't fire on a hard kill, which is exactly
    # what has been happening to this script repeatedly this session, so
    # relying only on this run's own exit handler isn't enough.
    tmp_root = Path(tempfile.gettempdir())
    for old_dir in tmp_root.glob("tmp*"):
        if (old_dir / "ngx_scratch.sqlite").exists():
            shutil.rmtree(old_dir, ignore_errors=True)

    scratch_dir = Path(tempfile.mkdtemp())
    scratch_path = scratch_dir / "ngx_scratch.sqlite"
    shutil.copy2(ROOT / "data" / "ngx.sqlite", scratch_path)
    import atexit
    atexit.register(shutil.rmtree, scratch_dir, ignore_errors=True)  # 2026-08-14 disk-full
    # incident: every prior run of this family of scripts left its ~150MB scratch
    # copy behind forever -- 24 of them accumulated across this session alone
    # (~3.6GB) and were a real contributor to a genuine disk-full crash mid-run.
    # Clean up on exit (including on sys.exit()/most exceptions) so repeated
    # resume invocations don't keep accumulating.
    con = mdb.init_db(scratch_path)
    results = load_results()
    print(f"Resuming with {len(results)} prior results" if results else "Starting fresh")

    doc_meta = {}
    for doc_id in DOC_ORDER:
        row = con.execute("SELECT ticker, doc_type, filing_date FROM documents WHERE doc_id=?",
                          (doc_id,)).fetchone()
        doc_meta[doc_id] = row

    # --- Standard pass: 3 identities x 10 documents ---
    for label, provider_name, model_id in STANDARD_IDENTITIES:
        for doc_id in DOC_ORDER:
            ticker, doc_type, filing_date = doc_meta[doc_id]
            run_one(con, results, doc_id=doc_id, ticker=ticker, doc_type=doc_type,
                   filing_date=filing_date, doc_text=doc_texts[doc_id], label=label,
                   provider_name=provider_name, model_id=model_id, phase="standard")

    # --- Gemini: single probe, on ELLAHLAKES (first in DOC_ORDER) ---
    gemini_doc = DOC_ORDER[0]
    ticker, doc_type, filing_date = doc_meta[gemini_doc]
    if not already_done(results, gemini_doc, "gemini-control", "standard"):
        run_one(con, results, doc_id=gemini_doc, ticker=ticker, doc_type=doc_type,
               filing_date=filing_date, doc_text=doc_texts[gemini_doc], label="gemini-control",
               provider_name="gemini", model_id=None, phase="standard")
    last_gemini = [r for r in results if r["benchmark_identity"] == "gemini-control"]
    gemini_ok = bool(last_gemini) and last_gemini[-1]["success"]
    if not gemini_ok:
        print("Gemini probe failed or blocked -- not attempting further Gemini calls this round, "
             "per the standing no-poll discipline.")
    else:
        for doc_id in DOC_ORDER[1:]:
            ticker, doc_type, filing_date = doc_meta[doc_id]
            run_one(con, results, doc_id=doc_id, ticker=ticker, doc_type=doc_type,
                   filing_date=filing_date, doc_text=doc_texts[doc_id], label="gemini-control",
                   provider_name="gemini", model_id=None, phase="standard")

    # --- Category A: reproducibility repeats (3 docs x 3 identities x 3 repeats) ---
    for label, provider_name, model_id in STANDARD_IDENTITIES:
        for doc_id in REPRO_DOCS:
            ticker, doc_type, filing_date = doc_meta[doc_id]
            for i in range(1, REPRO_REPEATS + 1):
                run_one(con, results, doc_id=doc_id, ticker=ticker, doc_type=doc_type,
                       filing_date=filing_date, doc_text=doc_texts[doc_id], label=label,
                       provider_name=provider_name, model_id=model_id, phase="repro_repeat",
                       repeat_index=i, force=True)

    print(f"\nRound 3 done. {len(results)} results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
