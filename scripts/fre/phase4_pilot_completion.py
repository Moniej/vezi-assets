"""Completes the remaining 4 documents of the Phase 4 quality-fix re-pilot
(docs/alpha/FINANCIAL_EXTRACTION_QUALITY_FIX_REPORT.md, GO/MODIFY/STOP
decision, exact next action #1). Only TRANSCORP (doc_id=9485) completed
live against the corrected pipeline before the 2026-08-12 quota wall; this
completes the other 4 stratified cases:

  - STANBIC (doc_id=452)   -- messy/ambiguous, one qualitative fact previously
  - ELLAHLAKES (doc_id=11122) -- format-diverse, largest document (130,892 chars)
  - MORISON (doc_id=9530)  -- thin, hit the quota wall mid-extraction originally
  - ETI (doc_id=7867)      -- clean quarterly case, not in the original 5

Runs against a SCRATCH COPY of data/ngx.sqlite only -- production is never
opened for write by this script. Uses the same resumable_financial_
reasoning() entry point run_phase_c_pilot.py uses, so a quota failure mid-run
is handled the same way (recorded, not forced through).

  GEMINI_API_KEY=... PYTHONPATH=src python scripts/fre/phase4_pilot_completion.py
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.llm_providers import QuotaExceededError, build_default_provider  # noqa: E402
from ngxrot.documents.reasoning import resumable_financial_reasoning  # noqa: E402

DOC_IDS = [452, 11122, 9530, 7867]
LABELS = {452: "STANBIC-messy", 11122: "ELLAHLAKES-format-diverse",
          9530: "MORISON-thin", 7867: "ETI-clean-quarterly"}


def main() -> None:
    scratch_dir = Path.home() / "AppData/Local/Temp/claude" if False else None
    import tempfile
    scratch_path = Path(tempfile.mkdtemp()) / "ngx_scratch.sqlite"
    print(f"Copying production data/ngx.sqlite -> {scratch_path} (read source, write scratch only)")
    t0 = time.time()
    shutil.copy2(ROOT / "data" / "ngx.sqlite", scratch_path)
    print(f"  copied in {time.time() - t0:.1f}s")

    con = db.init_db(scratch_path)  # applies additive migrations (e.g. numeric_consistency_check)
    provider = build_default_provider()
    print(f"Using provider: {provider.info.name} / {provider.info.model_id}")

    for doc_id in DOC_IDS:
        label = LABELS[doc_id]
        row = con.execute(
            "SELECT ticker, filing_date, char_count FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        print(f"\n--- doc_id {doc_id} [{label}] ticker={row[0]} filing_date={row[1]} "
             f"char_count={row[2]} ---")
        t0 = time.time()
        try:
            result = resumable_financial_reasoning(con, provider, doc_id=doc_id)
        except QuotaExceededError as e:
            print(f"  QUOTA EXCEEDED after this point in the run: {e}")
            print("  Progress already committed to the scratch DB for documents processed "
                 "so far in this run. Re-run this script tomorrow to continue -- note this "
                 "script does NOT persist across runs (fresh scratch copy every invocation), "
                 "so a partial run's results must be recorded in the report before exiting, "
                 "not assumed to survive to the next invocation.")
            sys.exit(2)
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}")
            continue

        facts = con.execute(
            "SELECT fact_id, fact_type, numeric_value, period_start, period_end, period_type, "
            "numeric_consistency_check FROM extracted_facts WHERE doc_id=?", (doc_id,)).fetchall()
        print(f"  parse_ok={result.extraction.parse_ok} facts={len(facts)} "
             f"implications={len(result.extraction.implication_ids)} "
             f"warnings={len(result.extraction.warnings)} elapsed={time.time()-t0:.1f}s")
        for w in result.extraction.warnings:
            print(f"  WARNING: {w}")
        for f in facts:
            print(f"  fact: type={f[1]} value={f[2]} period=({f[3]},{f[4]},{f[5]}) "
                 f"consistency={f[6]}")
        for c in result.critiques:
            print(f"  critique: implication {c['implication_id']} -> {c['status']} "
                 f"({c['n_fail']} fail, {c['n_concern']} concern)")

    print(f"\nDone. Scratch DB (for inspection until this process/tempdir is cleaned up): {scratch_path}")


if __name__ == "__main__":
    main()
