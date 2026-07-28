"""Canonical per-dataset-version quality report (owner directive, LIM-2,
2026-07-28). Merges two things that already exist separately -- the
audit computed at export time (audit.py, written to audit_report.json)
and the provenance recorded in the dataset-version registry
(registry.py) -- into ONE document with every field the owner specified.
Nothing here recomputes an audit metric; it only reads what already exists
and assembles it, so this can never drift from the numbers that actually
gated registration.
"""

from __future__ import annotations

import json
from pathlib import Path

from ngxrot.lim import registry


def build_quality_report(con_lim, version: str) -> dict:
    meta = registry.get_version(con_lim, version)
    if meta is None:
        raise ValueError(f"{version!r} is not a registered dataset version")

    accepted_path = Path(meta["accepted_path"])
    audit_path = accepted_path.parent / "audit_report.json"
    audit_data = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    audit = audit_data.get("audit", {})

    filing_dates_by_year = audit.get("temporal_distribution_by_year", {})
    date_coverage = {
        "years_present": sorted(filing_dates_by_year),
        "n_years_spanned": len(filing_dates_by_year),
    } if filing_dates_by_year else {"years_present": [], "n_years_spanned": 0,
                                    "note": "no filing_date present in this dataset type's context"}

    return {
        "dataset_type": meta["dataset_type"],
        "version": meta["version"],
        "dataset_version_hash": meta["content_hash"],
        "git_commit": meta["export_script_commit"],
        "teacher_model_version": meta["teacher_model_ids"],
        "generated_at": meta["generated_at"],
        "source_as_of": meta["source_as_of"],
        "parent_version": meta["parent_version"],
        "changelog": meta["changelog"],

        "example_count": meta["n_accepted"] + meta["n_rejected"],
        "n_accepted": meta["n_accepted"],
        "n_rejected": meta["n_rejected"],
        "acceptance_rate": audit.get("acceptance_rate"),
        "rejection_rate": audit.get("rejection_rate"),
        "rejection_reason_distribution": meta["rejection_reason_counts"],

        "duplicate_rate": audit.get("duplicate_detection", {}).get("duplicate_rate"),
        "grounding_integrity": audit.get("grounding_integrity"),
        "citation_integrity": audit.get("citation_integrity"),
        "confidence_distribution": audit.get("confidence_distribution"),
        "class_balance": audit.get("class_balance_by_fact_type"),
        "company_coverage": audit.get("company_distribution"),
        "date_coverage": date_coverage,

        "threshold_violations": audit_data.get("violations", []),
        "gate_status": "PASSED (registered)" if not audit_data.get("violations") else "FAILED",
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# Dataset Quality Report — {report['dataset_type']} / {report['version']}",
        "",
        f"- **Dataset version hash:** `{report['dataset_version_hash']}`",
        f"- **Git commit (exporter):** `{report['git_commit']}`",
        f"- **Teacher model version(s):** {report['teacher_model_version']}",
        f"- **Generated at:** {report['generated_at']} (source as-of {report['source_as_of']})",
        f"- **Parent version:** {report['parent_version']}",
        f"- **Gate status:** {report['gate_status']}",
        "",
        "## Volume",
        f"- Example count: {report['example_count']} "
        f"(accepted {report['n_accepted']}, rejected {report['n_rejected']})",
        f"- Acceptance rate: {report['acceptance_rate']} | Rejection rate: {report['rejection_rate']}",
        f"- Rejection reasons: {report['rejection_reason_distribution']}",
        "",
        "## Integrity",
        f"- Duplicate rate: {report['duplicate_rate']}",
        f"- Grounding integrity: {report['grounding_integrity']}",
        f"- Citation integrity: {report['citation_integrity']}",
        "",
        "## Coverage",
        f"- Confidence distribution: {report['confidence_distribution']}",
        f"- Class balance: {report['class_balance']}",
        f"- Company coverage: {report['company_coverage']}",
        f"- Date coverage: {report['date_coverage']}",
        "",
        "## Threshold violations",
        (f"- {report['threshold_violations']}" if report["threshold_violations"]
        else "- None — all configured thresholds passed at registration time."),
        "",
        f"Changelog: {report['changelog']}",
    ]
    return "\n".join(lines)


def write_quality_report(con_lim, version: str) -> Path:
    """Writes quality_report.{json,md} alongside the dataset's own
    accepted.jsonl/audit_report -- co-located with what it describes, same
    placement convention as audit_report.json/.md."""
    report = build_quality_report(con_lim, version)
    meta = registry.get_version(con_lim, version)
    version_dir = Path(meta["accepted_path"]).parent
    (version_dir / "quality_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    (version_dir / "quality_report.md").write_text(render_markdown(report), encoding="utf-8")
    return version_dir / "quality_report.md"
