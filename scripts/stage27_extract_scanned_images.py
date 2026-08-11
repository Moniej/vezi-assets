"""Stage 27 step 1a -- extract the raw embedded JPEG image from each of the
40 scanned-image dealing-notice PDFs (confirmed DCTDecode/JPEG XObjects,
one per page, in Stage 23/this stage's own inspection). This is pure
byte-level extraction of the already-embedded image stream -- no
rasterization/rendering engine needed, no new heavy dependency required.
OCR itself (a separate step) is applied afterward.

  PYTHONPATH=src python scripts/stage27_extract_scanned_images.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "data" / "staging" / "stage27_ocr_images"
IMG_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    rows = con.execute(
        "SELECT doc_id, local_path FROM documents WHERE doc_type='dealing' "
        "AND (text_path IS NULL OR text_path='')"
    ).fetchall()
    print(f"n_scanned_pdfs={len(rows)}")
    ok, fail = 0, 0
    for doc_id, local_path in rows:
        pdf_path = ROOT / local_path.replace("\\", "/")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    if not page.images:
                        continue
                    for img_idx, im in enumerate(page.images, start=1):
                        data = im["stream"].get_data()
                        ext = "jpg" if data[:3] == b"\xff\xd8\xff" else "bin"
                        out_path = IMG_DIR / f"{doc_id}_p{page_idx}_i{img_idx}.{ext}"
                        out_path.write_bytes(data)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"[FAIL] doc_id={doc_id}: {e}")
    print(f"ok={ok} fail={fail}")
    print(f"images written to {IMG_DIR}")


if __name__ == "__main__":
    main()
