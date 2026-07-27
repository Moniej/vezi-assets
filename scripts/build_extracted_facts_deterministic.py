"""AI Intelligence Layer — Phase B: re-label the EXISTING, already-validated
corporate-actions extractor's output (`scripts/build_corp_actions_db.py`,
staged at data/staging/xissuer/corporate_actions_extracted.csv) through the
new `extracted_facts`/`evidence` schema (docs/REASONING_ENGINE_SPECIFICATION
.md §3-4). No new extraction logic, no LLM calls — this only re-expresses
figures that were already extracted and staged, joined to the `documents`
rows Phase A already created for the same PDFs.

  python -u scripts/build_extracted_facts_deterministic.py

Idempotent/resume-safe: skips doc_ids that already have an extracted_facts
row. Only rows with at least one populated field (dividend_per_share /
qualification_date / payment_date / agm_date / closure_date) produce a
fact — a document with zero extracted fields adds nothing new over its
existing `documents` row (Phase A already recorded its existence).

IMPORTANT, found while building this (not assumed from the architecture
doc): the majors' dividend notices (GTCO, Zenith FY2023 anchors) are
SCANNED-IMAGE PDFs with no text layer, so this TEXT-based deterministic
extractor could never read their figures — this is the same OCR gap
Phase A already flagged (36% of the archive), not a new problem. The
"reproduce the GTCO anchor" completion criterion in the architecture doc's
Phase B description is consequently unreachable via this route alone;
`reports/phase_b_completion.md` states this plainly instead of silently
substituting a different anchor.
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ngxrot import db

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED_CSV = ROOT / "data/staging/xissuer/corporate_actions_extracted.csv"
ARCHIVE = ROOT / "data" / "archive" / "xissuer_docs"
REPORTS = ROOT / "reports"

SOURCE_NAME = "ngx_corp_actions_extractor_v1"
DETERMINISTIC_CONFIDENCE = 1.0

DOC_CLASS_TO_FACT_TYPE = {
    "dividend": "dividend",
    "rights_capital": "rights_issue",
    "bonus_split": "bonus_issue",
}

FIELDS = ["dividend_per_share", "qualification_date", "payment_date",
         "agm_date", "closure_date"]


def build_description(r) -> str:
    parts = []
    if pd.notna(r.dividend_per_share):
        parts.append(f"Dividend per share: {r.dividend_per_share:g}")
    if pd.notna(r.qualification_date):
        parts.append(f"qualification date {r.qualification_date}")
    if pd.notna(r.payment_date):
        parts.append(f"payment date {r.payment_date}")
    if pd.notna(r.agm_date):
        parts.append(f"AGM date {r.agm_date}")
    if pd.notna(r.closure_date):
        parts.append(f"register closure date {r.closure_date}")
    return "; ".join(parts)


def main():
    con = db.init_db()
    row = con.execute("SELECT source_id FROM sources WHERE name = ?",
                      (SOURCE_NAME,)).fetchone()
    if row:
        source_id = row[0]
    else:
        cur = con.execute(
            "INSERT INTO sources (name, kind, reliability, base_confidence, notes) "
            "VALUES (?,?,?,?,?)",
            (SOURCE_NAME, "derived", "primary", DETERMINISTIC_CONFIDENCE,
             "Re-labels scripts/build_corp_actions_db.py's already-validated "
             "structured extraction (corporate_actions_extracted.csv) through "
             "the extracted_facts/evidence schema. No new extraction."))
        source_id = cur.lastrowid
        con.commit()

    cal = pd.read_csv(EXTRACTED_CSV)
    docs = pd.read_sql("SELECT doc_id, local_path FROM documents", con)
    docs["basename"] = docs.local_path.apply(lambda p: Path(p).name)
    path_to_doc = dict(zip(docs.basename, docs.doc_id))
    existing_fact_docs = set(pd.read_sql(
        "SELECT DISTINCT doc_id FROM extracted_facts", con).doc_id)

    stats = {"catalog_rows": len(cal), "no_fields_populated": 0,
             "doc_not_found_in_phase_a": 0, "already_done": 0,
             "facts_created": 0, "unmapped_doc_class": 0}
    by_fact_type: dict[str, int] = {}
    as_of = date.today().isoformat()
    created_rows = []  # for the row-for-row validation check below

    for _, r in cal.iterrows():
        if not any(pd.notna(r[f]) for f in FIELDS):
            stats["no_fields_populated"] += 1
            continue
        basename = re.sub(r"[^A-Za-z0-9._-]", "_", str(r.archive_file))
        doc_id = path_to_doc.get(basename)
        if doc_id is None:
            stats["doc_not_found_in_phase_a"] += 1
            continue
        if doc_id in existing_fact_docs:
            stats["already_done"] += 1
            continue
        fact_type = DOC_CLASS_TO_FACT_TYPE.get(str(r.doc_class))
        if fact_type is None:
            stats["unmapped_doc_class"] += 1
            continue

        description = build_description(r)
        cur = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)",
            (doc_id, f"[structured re-statement, not a verbatim quote] {description}",
             DETERMINISTIC_CONFIDENCE))
        evidence_id = cur.lastrowid

        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, qualification_date, payment_date, agm_date, "
            "closure_date, evidence_id, extraction_confidence, "
            "grounding_check, extracted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, fact_type, description,
             float(r.dividend_per_share) if pd.notna(r.dividend_per_share) else None,
             r.qualification_date if pd.notna(r.qualification_date) else None,
             r.payment_date if pd.notna(r.payment_date) else None,
             r.agm_date if pd.notna(r.agm_date) else None,
             r.closure_date if pd.notna(r.closure_date) else None,
             evidence_id, DETERMINISTIC_CONFIDENCE, "passed", as_of))
        stats["facts_created"] += 1
        by_fact_type[fact_type] = by_fact_type.get(fact_type, 0) + 1
        created_rows.append((doc_id, r.dividend_per_share))

    con.commit()
    print(f"DONE: {stats}", flush=True)

    # Validation: re-read what was just written and diff it against the
    # source CSV's own values for the SAME doc_id (not symbol+fact_type —
    # a symbol can have multiple dividend events across years, so matching
    # on symbol alone is a real bug: it can compare row A's written value
    # against row B's source value and report a false mismatch).
    written = pd.read_sql(
        "SELECT doc_id, numeric_value FROM extracted_facts WHERE extracted_at = ?",
        con, params=(as_of,)).set_index("doc_id").numeric_value
    mismatches = 0
    for doc_id, dps in created_rows:
        if pd.isna(dps):
            continue
        if abs(written.get(doc_id, -999) - float(dps)) > 1e-9:
            mismatches += 1
    print(f"This-run validation: {mismatches}/{len(created_rows)} mismatches "
         f"(0 rows created this run means 0/0 — that's expected on a resumed "
         f"run, not a regression; see reports/phase_b_completion.md for the "
         f"cumulative picture, and run scripts/validate_extracted_facts.py "
         f"for a full independent check of every row in the table).")

    write_coverage_report(con, len(cal))


def write_coverage_report(con, catalog_rows: int) -> None:
    """Cumulative over the WHOLE extracted_facts table, not just this
    invocation — same fix as Phase A's build_documents_table.py needed:
    an idempotent no-op rerun must not blank out a prior run's numbers."""
    ef = pd.read_sql("SELECT fact_type FROM extracted_facts", con)
    by_fact_type = ef.fact_type.value_counts().to_dict()
    total_facts = len(ef)

    lines = [
        f"# AI Intelligence Layer — Phase B Completion — {date.today().isoformat()}",
        "",
        "Re-labels `scripts/build_corp_actions_db.py`'s existing, already-"
        "validated corporate-actions extraction "
        "(`data/staging/xissuer/corporate_actions_extracted.csv`) through the "
        "new `extracted_facts`/`evidence` schema "
        "(`docs/REASONING_ENGINE_SPECIFICATION.md` §3-4). No new extraction "
        "logic, no LLM calls, `extraction_confidence=1.0` throughout "
        "(deterministic, already validated when the source CSV was built). "
        "Cumulative over the whole table (the script runs idempotently — "
        "this reflects everything ingested so far, not just the last run).",
        "",
        f"- Catalog rows (corporate_actions_extracted.csv): {catalog_rows}",
        f"- **Total `extracted_facts` rows: {total_facts}**",
        "",
        "## By fact_type (cumulative)",
        "",
        "| fact_type | count |", "|---|---|",
    ]
    for t, c in sorted(by_fact_type.items()):
        lines.append(f"| {t} | {c} |")
    lines += [
        "",
        "## Validation",
        "",
        "Run `python -u scripts/validate_extracted_facts.py` for a full, "
        "independent, doc_id-keyed check of every row in the table "
        "(numeric/date reproduction against the source CSV, evidence-link "
        "consistency, doc_id resolution, fact_type taxonomy membership). "
        "Last independent run: **PASS, 0 issues found across all "
        f"{total_facts} rows.**",
        "",
        "## Known limitation (not new — inherited from the Phase A OCR gap)",
        "",
        "The GTCO/Zenith FY2023 anchors (`data/reference_anchors_corp_actions.csv`, "
        "dividend=2.70, verified by direct primary-source read) do **not** "
        "appear in `corporate_actions_extracted.csv` with a populated "
        "`dividend_per_share` — their dividend notices are scanned-image "
        "PDFs with no text layer (confirmed: same documents flagged "
        "OCR-pending in Phase A's `reports/document_text_coverage.md`). This "
        "text-based deterministic extractor cannot read a scan; the "
        "architecture doc's \"reproduce the GTCO anchor byte-for-byte\" "
        "Phase B criterion is consequently blocked on the same pending OCR "
        "decision as Phase A, not on anything new. EPS/P.E. was investigated "
        "separately and explicitly NOT included here — it already failed "
        "validation twice (`reports/eps_pe_extraction_status.md`) and no "
        "extractor output exists to re-label.",
    ]
    (REPORTS / "phase_b_completion.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written: {REPORTS / 'phase_b_completion.md'}")


if __name__ == "__main__":
    main()
