"""Phase C pilot runner — runs the Financial Reasoning Engine (Steps 1-14)
over a small, stratified sample of REAL documents, using a REAL LLM
provider. This is the one script in this package that costs real money and
sends real document text to a third-party API.

2026-07-22 hardening: fully resumable. Rerunning this script after a quota
failure, an interruption (Ctrl-C), or a crash skips every document already
in a terminal state (`completed`/`blocked_by_self_critique`, tracked in
`document_processing_status` AND cross-checked against the actual
extracted_facts/investment_implications rows — see pipeline_status.py) and
resumes exactly where it left off. `extract_document` is not idempotent by
design (it always inserts), so this script never calls it a second time
for a document that already has model-sourced facts — see
`reasoning.resumable_financial_reasoning`.

Pilot set (docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md's named GTCO/Zenith
FY2023 anchors are scanned PDFs with no text layer — confirmed 0 native-
text GTCO dividend filings and no native-text Zenith FY2023 filings exist
in `documents`; see reports/phase_c_completion.md for the check).
Substituted: a stratified sample of the intersection of Phase A native-text
documents and Phase B extracted_facts (deterministic ground truth) —
chosen for the identical reason the original pilot set was chosen: real
ground truth to measure precision/recall against.

Provider/model come from configs/llm_provider.toml (currently: Gemini,
gemini-3.6-flash) via build_default_provider() — this script never
constructs a concrete provider class itself, so it is unaffected by any
future provider swap in that config.

  GEMINI_API_KEY=... python -u scripts/run_phase_c_pilot.py [--model MODEL_ID] [-n N]
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from ngxrot import db  # noqa: E402
from ngxrot.documents import pilot_summary  # noqa: E402
from ngxrot.documents import pipeline_status as pstatus  # noqa: E402
from ngxrot.documents.llm_providers import QuotaExceededError, build_default_provider  # noqa: E402
from ngxrot.documents.reasoning import resumable_financial_reasoning  # noqa: E402

PILOT_SIZE = 18


def select_pilot(con) -> pd.DataFrame:
    q = """
    SELECT d.doc_id, d.ticker, d.raw_symbol, d.filing_date, ef.fact_type
    FROM documents d
    JOIN extracted_facts ef ON ef.doc_id = d.doc_id
    WHERE d.extraction_method = 'native'
    ORDER BY d.filing_date
    """
    pool = pd.read_sql(q, con)
    # Stratify across fact_type and across time (not just the most recent
    # filings) — a simple deterministic stride sample, not random, so a
    # rerun with the same pool picks the same documents. Smallest groups
    # first: a final budget cutoff must trim the LARGEST group (dividend),
    # never crowd out a minority fact_type (bonus_issue/rights_issue each
    # have only 1 row in Phase B — losing them silently would make the
    # pilot look dividend-only when the taxonomy covers more).
    groups = sorted(pool.groupby("fact_type"), key=lambda kv: len(kv[1]))
    by_type, budget = [], PILOT_SIZE
    for ftype, grp in groups:
        remaining_groups = len(groups) - len(by_type)
        n = max(1, min(len(grp), budget // remaining_groups))
        stride = max(1, len(grp) // n)
        picked = grp.iloc[::stride].head(n)
        by_type.append(picked)
        budget -= len(picked)
    sample = pd.concat(by_type).drop_duplicates(subset="doc_id")
    return sample


def _estimate_resume_time(retry_delay_seconds: float | None) -> str:
    """Best-effort only — Google's free-tier daily quota does not reliably
    expose its true reset time in the 429 response. Two numbers, both
    explicitly labeled as estimates, never asserted as fact:
      - the SDK's own short retryDelay hint (a burst-limit hint, NOT the
        daily cap clearing) if one was present in the error;
      - the next UTC midnight, a COMMON but UNCONFIRMED convention for
        Google API daily quota resets — flagged as unconfirmed, not stated
        as Google's documented behavior (it isn't, universally)."""
    lines = []
    if retry_delay_seconds is not None:
        lines.append(f"  - API-suggested retry delay: {retry_delay_seconds:.0f}s "
                     f"(a short burst-limit hint, NOT the daily quota reset)")
    now = datetime.now(timezone.utc)
    next_utc_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    lines.append(f"  - UNCONFIRMED ESTIMATE: daily free-tier quotas commonly reset "
                f"around UTC midnight — next one is {next_utc_midnight.isoformat()} "
                f"({(next_utc_midnight - now)}) from now. This is a guess, not a "
                f"documented guarantee from Google — verify at "
                f"https://ai.dev/rate-limit before relying on it.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="overrides configs/llm_provider.toml's "
                   "model_id for this run only; omit to use the configured default")
    ap.add_argument("-n", type=int, default=PILOT_SIZE)
    ap.add_argument("--force", action="store_true",
                   help="bypass BOTH the resume-skip logic and the prompt cache — "
                        "reprocesses every pilot document from scratch, duplicating "
                        "any already-existing facts. Use deliberately, not by default.")
    args = ap.parse_args()

    con = db.init_db()
    provider = build_default_provider(model_id=args.model)
    print(f"Using provider: {provider.info.name}")

    pilot = select_pilot(con).head(args.n)
    pilot_doc_ids = pilot.doc_id.tolist()
    todo_ids = pilot_doc_ids if args.force else pstatus.remaining_doc_ids(con, pilot_doc_ids)
    already_done = len(pilot_doc_ids) - len(todo_ids)

    print(f"Pilot set: {len(pilot_doc_ids)} documents "
         f"({already_done} already completed, {len(todo_ids)} remaining)")
    if not todo_ids:
        print("Nothing to do — every pilot document is already in a terminal state.")
        pilot_summary.write_reports(
            con, ROOT / "reports/phase_c_pilot_summary.md", ROOT / "reports/phase_c_pilot_summary.json")
        return

    completed_this_run = 0
    for doc_id in todo_ids:
        row = pilot.loc[pilot.doc_id == doc_id].iloc[0]
        print(f"\n--- doc_id {doc_id} ({row.raw_symbol}, {row.fact_type}, "
             f"{row.filing_date}) ---")
        pstatus.mark_status(con, doc_id, "processing",
                           model_id=provider.info.model_id, prompt_version=None)
        t0 = time.time()
        try:
            result = resumable_financial_reasoning(con, provider, doc_id=doc_id, force=args.force)
        except QuotaExceededError as e:
            pstatus.mark_status(con, doc_id, "quota_exceeded", error_detail=str(e)[:500])
            remaining = todo_ids[todo_ids.index(doc_id):]  # this one + everything after it
            print(f"\nQUOTA EXCEEDED after {completed_this_run} document(s) this run "
                 f"({len(remaining)} remaining, including this one, out of "
                 f"{len(pilot_doc_ids)} total in the pilot set).")
            print("Progress already saved (document_processing_status + all facts/"
                 "implications committed so far) — rerun this exact command later to "
                 "resume from here; already-completed documents will be skipped.")
            print(_estimate_resume_time(e.retry_delay_seconds))
            summary = pilot_summary.write_reports(
                con, ROOT / "reports/phase_c_pilot_summary.md",
                ROOT / "reports/phase_c_pilot_summary.json")
            print(f"Summary written (reflects quota-exit state): "
                 f"reports/phase_c_pilot_summary.json — "
                 f"processed={summary['documents']['processed']}, "
                 f"quota_exceeded={summary['documents']['quota_exceeded_current']}")
            sys.exit(2)
        except Exception as e:  # noqa: BLE001 — genuinely any failure mode; log and move on
            pstatus.mark_status(con, doc_id, "failed", error_detail=str(e)[:500])
            print(f"  FAILED: {e}")
            continue

        final_status = pstatus.determine_final_status(con, result.extraction.fact_ids)
        pstatus.mark_status(con, doc_id, final_status,
                           fact_count=len(result.extraction.fact_ids),
                           implication_count=len(result.extraction.implication_ids),
                           model_id=provider.info.model_id)
        completed_this_run += 1
        print(f"  parse_ok={result.extraction.parse_ok} "
             f"facts={len(result.extraction.fact_ids)} "
             f"implications={len(result.extraction.implication_ids)} "
             f"warnings={len(result.extraction.warnings)} "
             f"elapsed={time.time() - t0:.1f}s -> status={final_status}")
        for w in result.extraction.warnings:
            print(f"  WARNING: {w}")
        for c in result.critiques:
            print(f"  critique: implication {c['implication_id']} -> {c['status']} "
                 f"({c['n_fail']} fail, {c['n_concern']} concern)")

    summary = pilot_summary.write_reports(
        con, ROOT / "reports/phase_c_pilot_summary.md", ROOT / "reports/phase_c_pilot_summary.json")
    print(f"\nDONE this run: {completed_this_run} document(s) processed. "
         f"Summary written: reports/phase_c_pilot_summary.json (+ .md) — "
         f"precision={summary['extraction']['precision']}, "
         f"recall={summary['extraction']['recall']}, "
         f"self_critique_rejection_rate={summary['self_critique']['rejection_rate']}. "
         f"Run scripts/validate_phase_c_extraction.py for the full narrative report.")


if __name__ == "__main__":
    main()
