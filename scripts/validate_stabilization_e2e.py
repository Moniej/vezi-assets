"""Stabilization-pass end-to-end validation (2026-07-27, owner-mandated —
see HANDOFF.md). Exercises the FULL real pipeline against the real database
and real NGX filings, something no prior session had done end-to-end via the
Phase E/F orchestrator (`reasoning_engine.reason_about_company`) — the
original Phase C pilot (run_phase_c_pilot.py) only ever called the
lower-level `resumable_financial_reasoning` directly, one document at a
time, never the retrieval-triggered orchestrator path. TD13/TD16 explicitly
flagged `historical_event_reaction`/`industry_reasoning.propagate_implication`
as untested against real production data — this run closes that gap for the
orchestrator as a whole, plus validates the new CoverageAssessment/
EvidenceRanking modules against real accumulated data.

Two parts:
  1. LIVE run: reason_about_company() for a small number of real tickers
     that already have real prior implications AND have unprocessed native
     -text documents of their own — deliberately small (max_new_documents
     capped) to respect Gemini's free-tier daily quota. A genuinely NEW,
     never-before-exercised code path (retrieval -> extraction -> grounding
     -> self-critique -> aggregation -> coverage/ranking), on real filings.
  2. AGGREGATE analysis over the WHOLE real database (all 17+ pre-existing
     real implications plus whatever this run adds): precision/recall
     (reuses pilot_summary's existing methodology), a FRESH mechanical
     re-verification of every grounding_check='passed' row (never trust the
     stored flag alone — same "don't just trust the model" principle as
     grounding.py itself), CoverageAssessment/EvidenceRanking distributions
     across every ticker with real implications.

Writes reports/stabilization_validation_report.json (machine-readable) —
scripts/write_stabilization_report.py turns this into the Markdown narrative
report deliverable.

  GEMINI_API_KEY=... python -u scripts/validate_stabilization_e2e.py [--skip-live] [--max-new-docs N] [--tickers T1,T2]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents import reasoning_engine  # noqa: E402
from ngxrot.documents.coverage_assessment import assess_coverage  # noqa: E402
from ngxrot.documents.context import build_reasoning_context  # noqa: E402
from ngxrot.documents.evidence_ranking import evidence_ranking_summary  # noqa: E402
from ngxrot.documents.grounding import check_grounding  # noqa: E402
from ngxrot.documents.llm_providers import QuotaExceededError, build_default_provider  # noqa: E402

DEFAULT_TICKERS = ["UCAP", "UNILEVER"]   # already have real prior implications
                                        # AND real unprocessed native-text
                                        # documents of their own (checked
                                        # against the live DB before picking)


def run_live(con, tickers: list[str], max_new_docs: int) -> dict:
    provider = build_default_provider()
    out = {"provider": provider.info.name, "model_id": provider.info.model_id,
          "tickers": {}, "errors": []}
    for ticker in tickers:
        print(f"\n=== LIVE orchestrator run: {ticker} (max_new_documents={max_new_docs}) ===")
        t0 = time.time()
        try:
            result = reasoning_engine.reason_about_company(
                con, provider, ticker, max_new_documents=max_new_docs)
        except QuotaExceededError as e:
            print(f"  QUOTA EXCEEDED for {ticker}: {e}")
            out["errors"].append({"ticker": ticker, "error": "quota_exceeded", "detail": str(e)})
            continue
        except Exception as e:  # noqa: BLE001 — a single ticker's failure must not
                                # abort the whole validation run; captured, not hidden
            print(f"  FAILED for {ticker}: {e!r}")
            out["errors"].append({"ticker": ticker, "error": "exception",
                                  "detail": repr(e), "traceback": traceback.format_exc()})
            continue
        elapsed = time.time() - t0
        ca = result.coverage_assessment
        print(f"  elapsed={elapsed:.1f}s newly_processed={result.newly_processed_doc_ids} "
             f"n_facts={len(result.facts)} coverage_score={ca.coverage_score if ca else None} "
             f"confidence_ceiling={ca.confidence_ceiling if ca else None} "
             f"breaches={len(result.confidence_ceiling_breaches)}")
        for w in result.retrieval_warnings:
            print(f"    warning: {w}")
        out["tickers"][ticker] = {
            "elapsed_s": round(elapsed, 2),
            "newly_processed_doc_ids": result.newly_processed_doc_ids,
            "n_facts": len(result.facts),
            "n_retrieval_warnings": len(result.retrieval_warnings),
            "retrieval_warnings": result.retrieval_warnings,
            "coverage_assessment": ca.__dict__ if ca else None,
            "evidence_ranking_summary": result.evidence_ranking_summary,
            "confidence_ceiling_breaches": result.confidence_ceiling_breaches,
            "propagated_implication_ids": result.propagated_implication_ids,
            "peer_propagations_received": len(result.peer_propagations_received),
        }
    return out


def _fresh_grounding_reverify(con) -> dict:
    """Never trust the stored grounding_check column alone — re-run the same
    whitespace-tolerant substring check LIVE against the actual on-disk
    source text for every LLM-sourced fact with a real evidence quote, and
    compare against what's stored. A mismatch would mean either the source
    file changed on disk since extraction or a bug in how grounding_check
    was persisted — either way, a real finding worth catching."""
    rows = con.execute(
        "SELECT ef.fact_id, ef.doc_id, ef.grounding_check, e.quoted_text, d.text_path "
        "FROM extracted_facts ef "
        "JOIN evidence e ON e.evidence_id = ef.evidence_id "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.model_id IS NOT NULL").fetchall()
    n_checked = n_agree = n_disagree = n_missing_text = 0
    disagreements = []
    for fact_id, doc_id, stored_status, quoted_text, text_path in rows:
        if not text_path:
            n_missing_text += 1
            continue
        full_path = ROOT / text_path
        if not full_path.exists():
            n_missing_text += 1
            continue
        doc_text = full_path.read_text(encoding="utf-8")
        fresh = check_grounding(quoted_text, doc_text)
        fresh_status = "passed" if fresh.passed else "failed"
        n_checked += 1
        if fresh_status == stored_status:
            n_agree += 1
        else:
            n_disagree += 1
            disagreements.append({"fact_id": fact_id, "doc_id": doc_id,
                                  "stored": stored_status, "fresh_recheck": fresh_status})
    return {"n_checked": n_checked, "n_agree": n_agree, "n_disagree": n_disagree,
           "n_missing_source_text": n_missing_text, "disagreements": disagreements,
           "citation_accuracy": round(n_agree / n_checked, 4) if n_checked else None}


def _citation_integrity(con) -> dict:
    """Every fact/implication's citation must actually resolve: evidence_id
    exists, and the evidence row's own doc_id matches the fact's doc_id
    (catches a citation accidentally pointing at the wrong document)."""
    rows = con.execute(
        "SELECT ef.fact_id, ef.doc_id AS fact_doc_id, ef.evidence_id, e.doc_id AS evidence_doc_id "
        "FROM extracted_facts ef LEFT JOIN evidence e ON e.evidence_id = ef.evidence_id "
        "WHERE ef.model_id IS NOT NULL").fetchall()
    n_total = len(rows)
    n_no_evidence = sum(1 for r in rows if r[2] is None)
    n_doc_mismatch = sum(1 for r in rows if r[2] is not None and r[1] != r[3])
    n_correct = n_total - n_no_evidence - n_doc_mismatch
    return {"n_facts": n_total, "n_missing_evidence_row": n_no_evidence,
           "n_doc_id_mismatch": n_doc_mismatch,
           "citation_integrity_rate": round(n_correct / n_total, 4) if n_total else None}


def aggregate_coverage_and_ranking(con) -> dict:
    tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM investment_implications WHERE ticker IS NOT NULL").fetchall()]
    per_ticker = {}
    score_sum = 0.0
    tier_totals: dict[str, int] = {}
    n_conflicts_total = n_disagree_total = 0
    for ticker in tickers:
        ctx = build_reasoning_context(con, ticker)
        ca = ctx.coverage_assessment
        summary = ctx.evidence_ranking_summary
        per_ticker[ticker] = {
            "coverage_score": ca.coverage_score, "confidence_ceiling": ca.confidence_ceiling,
            "dimensions_present": ca.dimensions_present, "dimensions_missing": ca.dimensions_missing,
            "tier_distribution": summary.get("tier_distribution", {}),
            "n_conflicts_detected": summary.get("n_conflicts_detected", 0),
            "n_conflicts_disagree": summary.get("n_conflicts_where_trust_and_confidence_disagree", 0),
        }
        score_sum += ca.coverage_score
        for label, n in summary.get("tier_distribution", {}).items():
            tier_totals[label] = tier_totals.get(label, 0) + n
        n_conflicts_total += summary.get("n_conflicts_detected", 0)
        n_disagree_total += summary.get("n_conflicts_where_trust_and_confidence_disagree", 0)
    return {
        "n_tickers_assessed": len(tickers),
        "mean_coverage_score": round(score_sum / len(tickers), 4) if tickers else None,
        "platform_tier_distribution": tier_totals,
        "n_conflicts_detected_total": n_conflicts_total,
        "n_conflicts_where_trust_and_confidence_disagree_total": n_disagree_total,
        "per_ticker": per_ticker,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-live", action="store_true",
                   help="skip the live-LLM orchestrator run; analyze existing real data only")
    ap.add_argument("--max-new-docs", type=int, default=2)
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    args = ap.parse_args()

    con = db.init_db()
    report: dict = {"generated_at": time.strftime("%Y-%m-%d"), "live_run": None}

    if not args.skip_live:
        report["live_run"] = run_live(con, args.tickers.split(","), args.max_new_docs)
    else:
        print("Skipping live run (--skip-live) — analyzing existing real data only.")

    print("\n=== Fresh grounding re-verification (real data) ===")
    report["grounding_reverification"] = _fresh_grounding_reverify(con)
    print(json.dumps(report["grounding_reverification"], indent=2)[:2000])

    print("\n=== Citation integrity (real data) ===")
    report["citation_integrity"] = _citation_integrity(con)
    print(json.dumps(report["citation_integrity"], indent=2))

    print("\n=== CoverageAssessment + EvidenceRanking, aggregated across every real ticker ===")
    report["coverage_and_ranking"] = aggregate_coverage_and_ranking(con)
    print(json.dumps({k: v for k, v in report["coverage_and_ranking"].items() if k != "per_ticker"},
                     indent=2))

    from ngxrot.documents import pilot_summary
    report["pilot_summary"] = pilot_summary.build_summary(con)

    out_path = ROOT / "reports" / "stabilization_validation_raw.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nRaw validation data written to {out_path}")


if __name__ == "__main__":
    main()
