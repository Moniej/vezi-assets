"""Shared pilot-run metrics (2026-07-22 hardening) — one place computing
every number requirement 5/6 asked for, so run_phase_c_pilot.py and
validate_phase_c_extraction.py report the identical figures instead of two
scripts drifting apart. Produces a plain dict (JSON-serializable directly)
plus a Markdown renderer.

All figures are computed from the DATABASE (document_processing_status,
extracted_facts, investment_implications, self_critique_reviews, impact_
assessments, causal_chain_steps, llm_calls) — this module never trusts a
single run's in-memory counters, so it stays correct regardless of how
many separate invocations of run_phase_c_pilot.py it took to get here
(exactly the same "cumulative, not just-this-run" fix Phase A/B's report
generators needed after their own idempotent-rerun bugs).
"""

from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path

import pandas as pd

from . import vocab

PKG_ROOT = Path(__file__).resolve().parents[3]
LLM_CONFIG_PATH = PKG_ROOT / "configs" / "llm_provider.toml"


def _cost_rates() -> dict:
    raw = tomllib.loads(LLM_CONFIG_PATH.read_text(encoding="utf-8"))
    return raw.get("llm", {}).get("cost_assumed", {
        "input_usd_per_1k_tokens": 0.0, "output_usd_per_1k_tokens": 0.0,
        "confidence": "assumed", "note": "no cost_assumed section in config"})


def build_summary(con) -> dict:
    status = pd.read_sql("SELECT * FROM document_processing_status", con)
    llm_facts = pd.read_sql("SELECT * FROM extracted_facts WHERE model_id IS NOT NULL", con)
    deterministic_facts = pd.read_sql("SELECT * FROM extracted_facts WHERE model_id IS NULL", con)
    implications = pd.read_sql("SELECT * FROM investment_implications", con)
    critiques = pd.read_sql("SELECT * FROM self_critique_reviews", con)
    impacts = pd.read_sql("SELECT * FROM impact_assessments", con)
    chains = pd.read_sql("SELECT * FROM causal_chain_steps", con)
    calls = pd.read_sql("SELECT * FROM llm_calls", con)

    status_counts = status.status.value_counts().to_dict() if len(status) else {}
    documents_processed = status_counts.get("completed", 0) + status_counts.get(
        "blocked_by_self_critique", 0)
    documents_skipped_on_rerun = documents_processed  # what a rerun would skip
    quota_failures_current = status_counts.get("quota_exceeded", 0)
    documents_failed = status_counts.get("failed", 0)
    documents_in_progress = status_counts.get("processing", 0)

    # --- Precision/recall vs. Phase B, doc_id-matched (never symbol
    # -matched — see reports/phase_b_completion.md's own documented bug fix
    # for why that matters) ---
    precision = recall = float("nan")
    n_overlap = n_agree = n_llm_extra = n_recall_miss = 0
    if len(llm_facts) and len(deterministic_facts):
        merged = llm_facts.merge(deterministic_facts, on="doc_id", suffixes=("_llm", "_det"),
                                 how="left")
        both = merged[merged.numeric_value_det.notna() & merged.numeric_value_llm.notna()]
        agree = both[(both.numeric_value_llm - both.numeric_value_det).abs() < 1e-6]
        llm_extra = merged[merged.numeric_value_det.isna() & merged.numeric_value_llm.notna()]
        recall_miss = merged[merged.numeric_value_det.notna() & merged.numeric_value_llm.isna()]
        n_overlap, n_agree = len(both), len(agree)
        n_llm_extra, n_recall_miss = len(llm_extra), len(recall_miss)
        precision = n_agree / n_overlap if n_overlap else float("nan")
        recall = n_agree / (n_agree + n_recall_miss) if (n_agree + n_recall_miss) else float("nan")

    n_grounding_failed = int((llm_facts.grounding_check == "failed").sum()) if len(llm_facts) else 0
    grounding_failure_rate = n_grounding_failed / len(llm_facts) if len(llm_facts) else float("nan")

    n_implications = len(implications)
    n_blocked = int((implications.status == "blocked_by_self_critique").sum()) if n_implications else 0
    self_critique_rejection_rate = n_blocked / n_implications if n_implications else float("nan")
    critique_finding_counts = critiques.finding.value_counts().to_dict() if len(critiques) else {}

    n_impact_complete = 0
    if len(impacts):
        per_fact = impacts.groupby("fact_id").size()
        n_impact_complete = int((per_fact == len(vocab.IMPACT_CATEGORIES)).sum())
    facts_missing_chain = 0
    if len(llm_facts):
        facts_with_chain = set(chains.fact_id.unique()) if len(chains) else set()
        facts_missing_chain = len(set(llm_facts.fact_id) - facts_with_chain)

    avg_latency_s = float(calls.latency_s.mean()) if len(calls) and calls.latency_s.notna().any() else None
    total_input_tokens = int(calls.input_tokens.sum()) if len(calls) else 0
    total_output_tokens = int(calls.output_tokens.sum()) if len(calls) else 0
    n_cache_hits = int((calls.served_from_cache == 1).sum()) if len(calls) else 0
    cache_hit_rate = n_cache_hits / len(calls) if len(calls) else float("nan")

    rates = _cost_rates()
    estimated_cost_usd = (
        total_input_tokens / 1000 * rates.get("input_usd_per_1k_tokens", 0.0)
        + total_output_tokens / 1000 * rates.get("output_usd_per_1k_tokens", 0.0))

    return {
        "generated_at": date.today().isoformat(),
        "documents": {
            "processed": documents_processed,
            "skipped_on_rerun": documents_skipped_on_rerun,
            "failed": documents_failed,
            "quota_exceeded_current": quota_failures_current,
            "in_progress_interrupted": documents_in_progress,
            "status_breakdown": status_counts,
        },
        "extraction": {
            "llm_facts_total": len(llm_facts),
            "deterministic_facts_total": len(deterministic_facts),
            "precision": None if pd.isna(precision) else round(precision, 4),
            "recall": None if pd.isna(recall) else round(recall, 4),
            "overlap_with_ground_truth": n_overlap,
            "agree": n_agree,
            "llm_found_extra": n_llm_extra,
            "recall_misses": n_recall_miss,
        },
        "grounding": {
            "failures": n_grounding_failed,
            "failure_rate": None if pd.isna(grounding_failure_rate) else round(grounding_failure_rate, 4),
        },
        "self_critique": {
            "implications_total": n_implications,
            "blocked": n_blocked,
            "rejection_rate": None if pd.isna(self_critique_rejection_rate)
                             else round(self_critique_rejection_rate, 4),
            "finding_counts": critique_finding_counts,
        },
        "schema_completeness": {
            "facts_with_complete_impact_categories": n_impact_complete,
            "facts_missing_causal_chain": facts_missing_chain,
        },
        "performance": {
            "avg_latency_s": None if avg_latency_s is None else round(avg_latency_s, 3),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_llm_calls": len(calls),
            "cache_hits": n_cache_hits,
            "cache_hit_rate": None if pd.isna(cache_hit_rate) else round(cache_hit_rate, 4),
            "estimated_api_cost_usd": round(estimated_cost_usd, 6),
            "cost_rate_confidence": rates.get("confidence", "assumed"),
            "cost_rate_note": rates.get("note", ""),
        },
    }


def render_markdown(summary: dict) -> str:
    d, e, g, s, sc, p = (summary["documents"], summary["extraction"], summary["grounding"],
                        summary["self_critique"], summary["schema_completeness"],
                        summary["performance"])
    lines = [
        f"# Phase C Pilot Summary — {summary['generated_at']}",
        "",
        "## Documents",
        f"- Processed (terminal, would be skipped on a rerun): {d['processed']}",
        f"- Failed: {d['failed']}",
        f"- Quota-exceeded (current status, not yet retried): {d['quota_exceeded_current']}",
        f"- Interrupted mid-processing (status='processing', needs retry): {d['in_progress_interrupted']}",
        f"- Full status breakdown: {d['status_breakdown']}",
        "",
        "## Extraction precision/recall (vs. Phase B deterministic ground truth)",
        f"- LLM facts: {e['llm_facts_total']} | Deterministic (Phase B) facts: {e['deterministic_facts_total']}",
        f"- Overlap with ground truth: {e['overlap_with_ground_truth']} | Agree: {e['agree']}",
        f"- Precision: {e['precision']} | Recall: {e['recall']}",
        f"- LLM found extra (not in Phase B): {e['llm_found_extra']} | Recall misses: {e['recall_misses']}",
        "",
        "## Grounding",
        f"- Failures: {g['failures']} | Failure rate: {g['failure_rate']}",
        "",
        "## Self-critique gate (Step 14)",
        f"- Implications: {s['implications_total']} | Blocked: {s['blocked']} | "
        f"Rejection rate: {s['rejection_rate']}",
        f"- Finding counts: {s['finding_counts']}",
        "",
        "## Schema completeness",
        f"- Facts with all {len(vocab.IMPACT_CATEGORIES)} impact categories: "
        f"{sc['facts_with_complete_impact_categories']}",
        f"- Facts missing a causal chain (should be 0): {sc['facts_missing_causal_chain']}",
        "",
        "## Performance / cost",
        f"- Avg latency: {p['avg_latency_s']}s | Total LLM calls: {p['total_llm_calls']}",
        f"- Tokens — input: {p['total_input_tokens']}, output: {p['total_output_tokens']}",
        f"- Cache hit rate: {p['cache_hit_rate']} ({p['cache_hits']} hits)",
        f"- Estimated API cost: ${p['estimated_api_cost_usd']} "
        f"(rate confidence: {p['cost_rate_confidence']} — {p['cost_rate_note']})",
    ]
    return "\n".join(lines)


def write_reports(con, md_path: Path, json_path: Path) -> dict:
    import json
    summary = build_summary(con)
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
