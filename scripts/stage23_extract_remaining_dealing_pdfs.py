"""Stage 23 step 1 -- extract text for the 40 dealing-notice PDFs that lack
text_path, using pdfplumber (same tool/approach as Stage 18's X-Compliance
PDFs). Writes to data/staging/document_text/{doc_id}.txt, matching the
existing naming convention for already-extracted dealing filings. No writes
to ngx.sqlite -- text cache only, staging area.

  PYTHONPATH=src python scripts/stage23_extract_remaining_dealing_pdfs.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ROOT / "data" / "staging" / "document_text"
TEXT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    rows = con.execute(
        "SELECT doc_id, local_path FROM documents WHERE doc_type='dealing' "
        "AND (text_path IS NULL OR text_path='')"
    ).fetchall()
    print(f"n_to_extract={len(rows)}")
    ok, fail = 0, 0
    for doc_id, local_path in rows:
        pdf_path = ROOT / local_path.replace("\\", "/")
        out_path = TEXT_DIR / f"{doc_id}.txt"
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            out_path.write_text(text, encoding="utf-8")
            ok += 1
            print(f"[OK] doc_id={doc_id} chars={len(text)} -> {out_path}")
        except Exception as e:
            fail += 1
            print(f"[FAIL] doc_id={doc_id} path={pdf_path} error={e}")
    print(f"\nok={ok} fail={fail}")


if __name__ == "__main__":
    main()
