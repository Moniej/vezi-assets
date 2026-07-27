"""AI Intelligence Layer — Phase A: populate `documents` from the already
-archived X-Issuer corporate-action PDFs (docs/AI_INTELLIGENCE_LAYER_
ARCHITECTURE.md, Phase A). No LLM calls. Extracts native text where
present; explicitly counts and flags the OCR-required (scanned) subset
without OCR-ing it (that decision is still pending, see the doc's open
decisions).

  python -u scripts/build_documents_table.py

Idempotent/resume-safe: skips local_paths already present in `documents`.
Ticker resolution: only VERIFIED renames (symbol_renames.csv) map an old
disclosure symbol to a current `securities.ticker`; everything else keeps
ticker=NULL, raw_symbol=<as disclosed> — never a guessed match.

Output: `documents` rows + `data/staging/document_text/<doc_id>.txt` for
every native-text doc + `reports/document_text_coverage.md`.
"""

from __future__ import annotations

import os
import re
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pdfplumber

from ngxrot import db

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive" / "xissuer_docs"
TEXT_STAGING = ROOT / "data" / "staging" / "document_text"
TEXT_STAGING.mkdir(parents=True, exist_ok=True)
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

CALENDAR = ROOT / "data/staging/xissuer/corporate_actions_calendar_classified.csv"
RENAMES = ROOT / "data/reference/symbol_renames.csv"

SOURCE_NAME = "ngx_xissuer_documents"
NATIVE_CONFIDENCE = 0.85
MIN_CHARS_FOR_NATIVE = 50  # below this, treat as a scanned/no-text PDF


def fname(r) -> str:
    """MUST match scripts/harvest_corpaction_docs.py's fname() exactly —
    this is how a calendar row is matched to its archived file."""
    return re.sub(r"[^A-Za-z0-9._-]", "_",
                  f"{int(r.sp_id)}_{str(r.url).rsplit('/', 1)[-1][:120]}")


def load_verified_renames() -> dict[str, str]:
    df = pd.read_csv(RENAMES)
    verified = df[df.status == "verified"]
    return dict(zip(verified.old_symbol, verified.new_symbol))


def extract_text(path: Path) -> tuple[str, int]:
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        return text, len(text)
    except Exception as e:  # noqa: BLE001 — corrupt/unreadable PDF, treat as no-text
        return "", -1  # -1 marks an extraction error distinctly from "0 chars, scanned"


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
            (SOURCE_NAME, "company_filing", "primary", NATIVE_CONFIDENCE,
             "X-Issuer corp-action filing archive, Phase A text-extraction pass"))
        source_id = cur.lastrowid
        con.commit()

    cal = pd.read_csv(CALENDAR)
    renames = load_verified_renames()
    securities = set(pd.read_sql("SELECT ticker FROM securities", con).ticker)
    existing_paths = set(pd.read_sql("SELECT local_path FROM documents", con).local_path)

    as_of = date.today().isoformat()
    stats = {
        "total_catalog_rows": len(cal), "file_missing": 0, "already_done": 0,
        "native": 0, "ocr_pending": 0, "extraction_error": 0,
        "ticker_resolved": 0, "ticker_unresolved": 0,
    }
    by_type: dict[str, dict[str, int]] = {}
    by_year: dict[str, dict[str, int]] = {}

    batch_limit = int(os.environ.get("DOC_BATCH_LIMIT", "0")) or None
    t0 = time.time()
    processed = 0
    for i, r in cal.iterrows():
        if batch_limit and processed >= batch_limit:
            print(f"Batch limit {batch_limit} reached — stopping cleanly "
                  f"(resume by rerunning, idempotent).", flush=True)
            break
        local_path = ARCHIVE / fname(r)
        rel_path = str(local_path.relative_to(ROOT))
        if rel_path in existing_paths:
            stats["already_done"] += 1
            continue
        if not local_path.exists() or local_path.stat().st_size < 100:
            stats["file_missing"] += 1
            continue

        raw_symbol = str(r.symbol)
        resolved = renames.get(raw_symbol, raw_symbol)
        ticker = resolved if resolved in securities else None
        if ticker:
            stats["ticker_resolved"] += 1
        else:
            stats["ticker_unresolved"] += 1

        doc_type = str(r.doc_class) if pd.notna(r.get("doc_class")) else "other"
        filing_date = str(r.created_date)[:10] if pd.notna(r.get("created_date")) else str(r.created)[:10]
        retrieved_date = datetime.fromtimestamp(local_path.stat().st_mtime).date().isoformat()

        text, char_count = extract_text(local_path)
        if char_count < 0:
            extraction_method, source_confidence, text_path = None, 0.0, None
            stats["extraction_error"] += 1
        elif char_count >= MIN_CHARS_FOR_NATIVE:
            extraction_method, source_confidence = "native", NATIVE_CONFIDENCE
            stats["native"] += 1
        else:
            extraction_method, source_confidence, text_path = None, 0.0, None
            stats["ocr_pending"] += 1

        yr = filing_date[:4]
        by_type.setdefault(doc_type, {"native": 0, "ocr_pending": 0, "extraction_error": 0})
        by_year.setdefault(yr, {"native": 0, "ocr_pending": 0, "extraction_error": 0})

        cur = con.execute(
            "INSERT INTO documents (ticker, raw_symbol, doc_type, source_type, "
            "filing_date, retrieved_date, source_url, local_path, text_path, "
            "extraction_method, char_count, source_confidence, source_id, as_of_date) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ticker, raw_symbol, doc_type, "filing", filing_date, retrieved_date,
             str(r.url), rel_path, None, extraction_method,
             char_count if char_count >= 0 else None, source_confidence,
             source_id, as_of))
        doc_id = cur.lastrowid

        if extraction_method == "native":
            text_path = f"data/staging/document_text/{doc_id}.txt"
            (ROOT / text_path).write_text(text, encoding="utf-8")
            con.execute("UPDATE documents SET text_path = ? WHERE doc_id = ?",
                       (text_path, doc_id))
            by_type[doc_type]["native"] += 1
            by_year[yr]["native"] += 1
        elif char_count < 0:
            by_type[doc_type]["extraction_error"] += 1
            by_year[yr]["extraction_error"] += 1
        else:
            by_type[doc_type]["ocr_pending"] += 1
            by_year[yr]["ocr_pending"] += 1

        processed += 1
        if processed % 500 == 0:
            con.commit()
            elapsed = time.time() - t0
            print(f"[{processed}] native={stats['native']} ocr_pending={stats['ocr_pending']} "
                  f"errors={stats['extraction_error']} elapsed={elapsed:.0f}s", flush=True)

    con.commit()
    total_time = time.time() - t0
    print(f"DONE: processed {processed} new docs in {total_time:.0f}s (this batch). "
          f"this-batch stats: {stats}", flush=True)

    write_coverage_report(con, len(cal))
    remaining = len(cal) - pd.read_sql(
        "SELECT COUNT(*) n FROM documents", con).n.iloc[0]
    print(f"Catalog rows not yet in `documents` (missing files + not-yet-processed): "
          f"~{remaining}", flush=True)


def write_coverage_report(con, total_catalog_rows: int) -> None:
    """Cumulative report over the WHOLE `documents` table so far, not just
    the current batch — correct regardless of how many DOC_BATCH_LIMIT
    batches it took to populate it."""
    doc = pd.read_sql(
        "SELECT doc_type, filing_date, extraction_method, char_count, ticker "
        "FROM documents", con)
    doc["year"] = doc.filing_date.astype(str).str[:4]
    doc["status"] = doc.extraction_method.fillna(
        doc.char_count.apply(lambda c: "extraction_error" if pd.notna(c) and c < 0
                             else "ocr_pending"))
    doc.loc[doc.extraction_method == "native", "status"] = "native"

    totals = doc.status.value_counts()
    ticker_resolved = int(doc.ticker.notna().sum())
    ticker_unresolved = int(doc.ticker.isna().sum())

    lines = [
        f"# Document Text-Extraction Coverage — Phase A — {date.today().isoformat()}",
        "",
        "AI Intelligence Layer, Phase A (`docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`). "
        "No LLM calls made. Cumulative over every `documents` row populated so far "
        "(the ingestion script runs in resumable batches — this reflects the whole "
        "table, not just the most recent batch). Counts what has usable native text "
        "vs. what needs OCR (not yet run — pending owner decision on OCR engine).",
        "",
        f"- Catalog rows (corporate_actions_calendar_classified.csv): {total_catalog_rows}",
        f"- Rows in `documents` so far: {len(doc)}",
        f"- Native text extracted (source_confidence={NATIVE_CONFIDENCE}): "
        f"{int(totals.get('native', 0))}",
        f"- OCR-pending (no usable text layer, source_confidence=0.0 until OCR'd): "
        f"{int(totals.get('ocr_pending', 0))}",
        f"- Extraction error (unreadable/corrupt PDF): {int(totals.get('extraction_error', 0))}",
        f"- Ticker resolved (verified rename or direct match): {ticker_resolved}",
        f"- Ticker unresolved (raw_symbol kept, ticker NULL): {ticker_unresolved}",
        "",
        "## By doc_type (cumulative)",
        "",
        "| doc_type | native | ocr_pending | extraction_error |",
        "|---|---|---|---|",
    ]
    piv = doc.pivot_table(index="doc_type", columns="status", values="filing_date",
                          aggfunc="count", fill_value=0)
    for t in sorted(piv.index):
        row = piv.loc[t]
        lines.append(f"| {t} | {row.get('native', 0)} | {row.get('ocr_pending', 0)} "
                     f"| {row.get('extraction_error', 0)} |")
    lines += ["", "## By filing year (cumulative)", "",
             "| year | native | ocr_pending | extraction_error |", "|---|---|---|---|"]
    piv_y = doc.pivot_table(index="year", columns="status", values="filing_date",
                            aggfunc="count", fill_value=0)
    for y in sorted(piv_y.index):
        row = piv_y.loc[y]
        lines.append(f"| {y} | {row.get('native', 0)} | {row.get('ocr_pending', 0)} "
                     f"| {row.get('extraction_error', 0)} |")
    lines += ["", "Unresolved tickers keep their `raw_symbol` verbatim in `documents` — "
             "no guessed matches. Next step (Phase A completion): review this report, "
             "then decide the OCR engine (open decision in the architecture doc) before "
             "Phase B."]
    (REPORTS / "document_text_coverage.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written: {REPORTS / 'document_text_coverage.md'}")


if __name__ == "__main__":
    main()
