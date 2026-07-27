"""Validate `extracted_facts` (Phase B, deterministic rows ONLY) against
its source, independent of the build script — same discipline as
validate_dol_prices.py/validate_eps_pe.py: a rerunnable check, not just an
inline assertion.

  python -u scripts/validate_extracted_facts.py

Checks, all doc_id-keyed (never symbol-keyed — a symbol can have multiple
dividend events across years, so symbol-only matching is unsound):
  1. every extracted_facts row's numeric_value/dates reproduce the source
     CSV's values for the SAME doc_id, byte-for-byte;
  2. every extracted_facts row has exactly one evidence row, and that
     evidence row's doc_id matches;
  3. every extracted_facts.doc_id resolves to a real `documents` row;
  4. fact_type is always a taxonomy leaf from configs/fact_taxonomy.toml.

2026-07-22 bug fix: this script MUST filter to `model_id IS NULL` (Phase
B's deterministic rows) — Phase C added LLM-sourced rows to the SAME
`extracted_facts` table, and this validator's source-of-truth is
`corporate_actions_extracted.csv`, which only Phase B rows were ever built
from. Without the filter, every Phase C row looks like a "failure" here
(no matching CSV row) even though it's correct — that's not a Phase B
regression, it's this script checking rows outside its own scope. Phase
C's LLM rows are validated by validate_phase_c_extraction.py instead.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pandas as pd

from ngxrot import db

ROOT = Path(__file__).resolve().parents[1]


def load_fact_taxonomy_leaves() -> set[str]:
    raw = tomllib.loads((ROOT / "configs/fact_taxonomy.toml").read_text(encoding="utf-8"))
    return {t for spec in raw.values() for t in spec.get("types", [])}


def main():
    con = db.connect()
    ef = pd.read_sql("SELECT * FROM extracted_facts WHERE model_id IS NULL", con)
    ev = pd.read_sql("SELECT * FROM evidence", con)
    docs = pd.read_sql("SELECT doc_id, local_path FROM documents", con)
    src = pd.read_csv(ROOT / "data/staging/xissuer/corporate_actions_extracted.csv")

    print(f"extracted_facts rows (Phase B deterministic only, model_id IS NULL): {len(ef)}")
    failures = []

    # 1. numeric/date reproduction, doc_id-keyed
    docs = docs.assign(basename=docs.local_path.apply(lambda p: Path(p).name))
    src = src.assign(basename=src.archive_file.apply(
        lambda s: re.sub(r"[^A-Za-z0-9._-]", "_", str(s))))
    src_by_doc = src.merge(docs[["doc_id", "basename"]], on="basename", how="left").set_index("doc_id")

    for r in ef.itertuples():
        if r.doc_id not in src_by_doc.index:
            failures.append(f"fact {r.fact_id}: doc_id {r.doc_id} not in source CSV join")
            continue
        s = src_by_doc.loc[r.doc_id]
        if pd.notna(r.numeric_value) and abs(r.numeric_value - s.dividend_per_share) > 1e-9:
            failures.append(f"fact {r.fact_id}: numeric_value {r.numeric_value} != "
                            f"source {s.dividend_per_share}")
        for col in ("qualification_date", "payment_date", "agm_date", "closure_date"):
            r_val = getattr(r, col)
            s_val = s[col] if pd.notna(s[col]) else None
            if r_val != s_val:
                failures.append(f"fact {r.fact_id}: {col} {r_val!r} != source {s_val!r}")

    # 2. one evidence row per fact, doc_id-consistent
    ev_by_id = ev.set_index("evidence_id")
    for r in ef.itertuples():
        if r.evidence_id not in ev_by_id.index:
            failures.append(f"fact {r.fact_id}: evidence_id {r.evidence_id} missing")
            continue
        if ev_by_id.loc[r.evidence_id].doc_id != r.doc_id:
            failures.append(f"fact {r.fact_id}: evidence doc_id mismatch")

    # 3. doc_id resolves
    valid_docs = set(docs.doc_id)
    bad_docs = set(ef.doc_id) - valid_docs
    if bad_docs:
        failures.append(f"doc_ids not in documents table: {bad_docs}")

    # 4. fact_type taxonomy membership
    leaves = load_fact_taxonomy_leaves()
    bad_types = set(ef.fact_type) - leaves
    if bad_types:
        failures.append(f"fact_type not in configs/fact_taxonomy.toml: {bad_types}")

    if failures:
        print(f"FAIL: {len(failures)} issue(s)")
        for f in failures[:50]:
            print(" -", f)
        raise SystemExit(1)
    print("PASS: all extracted_facts rows reproduce their source doc_id-for-doc_id, "
         "all evidence links consistent, all doc_ids resolve, all fact_types "
         "are valid taxonomy leaves.")


if __name__ == "__main__":
    main()
