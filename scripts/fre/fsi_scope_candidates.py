"""FSI Phase 1, Step 1: document-scoping (docs/fre_runs/fsi_phase1_
preregistration.md, "Document scoping"). READ-ONLY -- scans native-text
document bodies for real, disclosed keyword/structure criteria and writes
a scoping report. No database write. No extraction. No metric beyond
revenue/net_profit is searched for.

Recorded selection criteria (fixed BEFORE running, per the pre-
registration):
  1. documents.source_confidence >= 0.8 (native-text only -- excludes the
     4,134 OCR-pending documents AND, as a direct consequence, the known
     GTCO/Zenith FY2023 anchors, which are confirmed scanned-image/OCR
     -pending, per Phase B/C's own prior finding).
  2. char_count > 3000 -- the real, inspected char_count distribution
     (median 2054, most native-text documents are short corporate-action
     notices, e.g. a 243-character dividend notice) shows that a full
     income-statement-bearing filing is necessarily longer than a routine
     notice; 3000 is a disclosed, reasoned-but-not-validated floor (a bit
     above the median), not a proven cutoff.
  3. document body contains, case-insensitive, AT LEAST ONE revenue term
     ("revenue" or "turnover") AND AT LEAST ONE profit term ("profit after
     tax", "net profit", or "PAT") -- both classes required, not just one,
     specifically to reduce false positives from documents that mention
     one concept in an unrelated context.
  4. document body contains at least one Naira monetary indicator (the
     Naira sign, or "N" immediately followed by a digit, or "million"/
     "billion" nearby) -- a proxy for "this document states an actual
     monetary figure," not just narrative discussion.

  PYTHONPATH=src python scripts/fre/fsi_scope_candidates.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

CHAR_COUNT_FLOOR = 3000
REVENUE_TERMS = re.compile(r"revenue|turnover", re.IGNORECASE)
PROFIT_TERMS = re.compile(r"profit after tax|net profit|\bpat\b", re.IGNORECASE)
MONEY_TERMS = re.compile(r"₦|n\d|million|billion", re.IGNORECASE)


def main() -> int:
    con = db.connect(db.DEFAULT_DB)
    con.execute("PRAGMA query_only = ON")  # read-only, extra safety on top of the URI-based tests elsewhere

    rows = con.execute(
        "SELECT doc_id, ticker, doc_type, filing_date, char_count, text_path FROM documents "
        "WHERE source_confidence >= 0.8 AND char_count > ? AND text_path IS NOT NULL "
        "ORDER BY char_count DESC",
        (CHAR_COUNT_FLOOR,),
    ).fetchall()
    print(f"Step 1 filter (source_confidence>=0.8 AND char_count>{CHAR_COUNT_FLOOR}): "
          f"{len(rows)} candidate documents before keyword scoping.")

    candidates = []
    for doc_id, ticker, doc_type, filing_date, char_count, text_path in rows:
        full_path = ROOT / text_path
        if not full_path.exists():
            continue
        text = full_path.read_text(encoding="utf-8", errors="replace")
        if REVENUE_TERMS.search(text) and PROFIT_TERMS.search(text) and MONEY_TERMS.search(text):
            candidates.append((doc_id, ticker, doc_type, filing_date, char_count, text_path))

    print(f"Step 2 filter (revenue term AND profit term AND money term, all required): "
          f"{len(candidates)} candidate documents.")
    print()
    print("Candidates by ticker:")
    by_ticker: dict[str, int] = {}
    for _, ticker, *_ in candidates:
        by_ticker[ticker or "UNRESOLVED"] = by_ticker.get(ticker or "UNRESOLVED", 0) + 1
    for ticker, n in sorted(by_ticker.items(), key=lambda kv: -kv[1]):
        print(f"  {ticker}: {n}")

    print()
    print("Full candidate list (doc_id, ticker, doc_type, filing_date, char_count):")
    for doc_id, ticker, doc_type, filing_date, char_count, _ in candidates:
        print(f"  {doc_id}\t{ticker}\t{doc_type}\t{filing_date}\t{char_count}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
