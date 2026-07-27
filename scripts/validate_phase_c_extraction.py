"""Validate Phase C's LLM extraction against Phase B's deterministic ground
truth, and report schema/gate health. Rerunnable independent of the
pilot run, same convention as validate_extracted_facts.py.

  python -u scripts/validate_phase_c_extraction.py

Produces reports/phase_c_completion.md (precision/recall on the numeric
dividend figure, grounding-failure rate, self-critique fail/concern rates,
schema-completeness checks, and every disagreement listed explicitly, not
summarized away).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from ngxrot import db  # noqa: E402
from ngxrot.documents import pilot_summary, vocab  # noqa: E402


def main():
    con = db.init_db()

    llm_facts = pd.read_sql(
        "SELECT * FROM extracted_facts WHERE model_id IS NOT NULL", con)
    deterministic_facts = pd.read_sql(
        "SELECT * FROM extracted_facts WHERE model_id IS NULL", con)

    lines = [
        f"# Phase C Completion Report — {date.today().isoformat()}",
        "",
        f"- LLM-extracted `extracted_facts` rows: {len(llm_facts)}",
        f"- Deterministic (Phase B) `extracted_facts` rows: {len(deterministic_facts)}",
    ]

    if len(llm_facts) == 0:
        lines += [
            "",
            "**No LLM extraction has been run yet** — this report reflects "
            "an empty pilot. Run `scripts/run_phase_c_pilot.py` (provider/model "
            "come from `configs/llm_provider.toml`, currently Gemini — needs "
            "the configured provider's API key set, e.g. `GEMINI_API_KEY`) "
            "first, then rerun this script.",
        ]
        (ROOT / "reports/phase_c_completion.md").write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        pilot_summary.write_reports(
            con, ROOT / "reports/phase_c_pilot_summary.md", ROOT / "reports/phase_c_pilot_summary.json")
        return

    # --- Precision/recall on the numeric dividend figure, doc_id-matched
    # against Phase B (same discipline as validate_extracted_facts.py: never
    # match on symbol/fact_type alone, always doc_id) ---
    merged = llm_facts.merge(deterministic_facts, on="doc_id", suffixes=("_llm", "_det"),
                             how="left")
    both_have_value = merged[merged.numeric_value_det.notna() & merged.numeric_value_llm.notna()]
    agree = both_have_value[
        (both_have_value.numeric_value_llm - both_have_value.numeric_value_det).abs() < 1e-6]
    llm_found_det_missing = merged[merged.numeric_value_det.isna() & merged.numeric_value_llm.notna()]
    det_found_llm_missing = merged[merged.numeric_value_det.notna() & merged.numeric_value_llm.isna()]

    precision = len(agree) / len(both_have_value) if len(both_have_value) else float("nan")
    recall = len(agree) / (len(agree) + len(det_found_llm_missing)) if (len(agree) + len(det_found_llm_missing)) else float("nan")

    lines += [
        "",
        "## Precision/recall vs. Phase B deterministic ground truth "
        "(numeric dividend/rights/bonus figure, doc_id-matched)",
        "",
        f"- Documents where BOTH LLM and Phase B extracted a numeric value: {len(both_have_value)}",
        f"- Agree (within 1e-6): {len(agree)}",
        f"- LLM extracted a value Phase B did not (LLM found MORE than deterministic — "
        f"could be correct where the regex extractor missed, or a hallucination): "
        f"{len(llm_found_det_missing)}",
        f"- Phase B extracted a value the LLM missed (recall miss): {len(det_found_llm_missing)}",
        f"- **Precision (of LLM values with a ground-truth match, how many agree): "
        f"{precision:.1%}**" if both_have_value.size else "- Precision: N/A (no overlap)",
        f"- **Recall (of Phase B's known values, how many did the LLM reproduce): "
        f"{recall:.1%}**" if (len(agree) + len(det_found_llm_missing)) else "- Recall: N/A",
        "",
        "### Every disagreement (not summarized away)",
        "",
    ]
    disagree = both_have_value[
        (both_have_value.numeric_value_llm - both_have_value.numeric_value_det).abs() >= 1e-6]
    if len(disagree):
        lines.append("| doc_id | Phase B value | LLM value |")
        lines.append("|---|---|---|")
        for r in disagree.itertuples():
            lines.append(f"| {r.doc_id} | {r.numeric_value_det} | {r.numeric_value_llm} |")
    else:
        lines.append("(none)")

    # --- Grounding health ---
    n_failed_grounding = (llm_facts.grounding_check == "failed").sum()
    lines += [
        "",
        "## Grounding",
        "",
        f"- Facts with grounding_check='failed' (quote not found verbatim in "
        f"source, extraction_confidence forced to 0.0): {n_failed_grounding} / {len(llm_facts)} "
        f"({n_failed_grounding / len(llm_facts):.1%})",
    ]

    # --- Self-critique gate health ---
    critiques = pd.read_sql("SELECT * FROM self_critique_reviews", con)
    implications = pd.read_sql("SELECT * FROM investment_implications", con)
    lines += [
        "",
        "## Self-critique gate (Step 14)",
        "",
        f"- Implications drafted: {len(implications)}",
        f"- Status breakdown: {implications.status.value_counts().to_dict()}",
        f"- Critique rows: {len(critiques)} (expect {len(implications) * 8} = "
        f"8 per implication if the gate ran completely on every draft)",
        f"- Finding breakdown: {critiques.finding.value_counts().to_dict() if len(critiques) else '(none)'}",
        f"- Question types most often flagged: "
        f"{critiques[critiques.finding != 'pass'].question.value_counts().to_dict() if len(critiques) else '(none)'}",
    ]

    # --- Schema completeness checks ---
    impacts = pd.read_sql("SELECT * FROM impact_assessments", con)
    facts_with_13 = impacts.groupby("fact_id").size()
    incomplete = facts_with_13[facts_with_13 != 13]
    chains = pd.read_sql("SELECT * FROM causal_chain_steps", con)
    facts_with_chain = set(chains.fact_id.unique())
    facts_without_chain = set(llm_facts.fact_id) - facts_with_chain
    lines += [
        "",
        "## Schema completeness",
        "",
        f"- Facts missing a complete 13-category impact_assessments set: "
        f"{len(incomplete)} / {len(llm_facts)}",
        f"- LLM facts with zero causal_chain_steps rows (schema violation — "
        f"should be impossible if extract.py ran to completion): {len(facts_without_chain)}",
    ]

    (ROOT / "reports/phase_c_completion.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport written: reports/phase_c_completion.md")

    # 2026-07-22 hardening: machine-readable dashboard, alongside (not
    # instead of) the detailed narrative report above — same underlying
    # numbers, shared with run_phase_c_pilot.py via pilot_summary.py so the
    # two scripts can never silently disagree with each other.
    summary = pilot_summary.write_reports(
        con, ROOT / "reports/phase_c_pilot_summary.md", ROOT / "reports/phase_c_pilot_summary.json")
    print(f"\nMachine-readable summary written: reports/phase_c_pilot_summary.json "
         f"(+ .md). documents.processed={summary['documents']['processed']}, "
         f"extraction.precision={summary['extraction']['precision']}, "
         f"extraction.recall={summary['extraction']['recall']}")


if __name__ == "__main__":
    main()
