"""FSI Depth-Scoping Audit -- READ-ONLY. No extraction, no database write,
no schema change. Directly answers the question the 2026-08-03 FSI
Coverage Expansion Decision Audit raised as its own top recommendation:
which of the archived native-text filings actually CONTAIN each major
financial-statement section (not just revenue/profit keywords), and how
consistent is the "results_notice" disclosure format across companies.

Nothing here writes a fact, a value, or a database row. Every check is a
presence/absence keyword or structural-pattern detector over already-
archived plain-text files, run against data already inside data/ngx.sqlite.

  PYTHONPATH=src python scripts/fre/fsi_depth_scoping.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

DB = ROOT / "data" / "ngx.sqlite"
CHAR_FLOOR = 3000

SECTION_PATTERNS = {
    "income_statement": re.compile(
        r"statement of profit or loss|statement of comprehensive income|"
        r"income statement", re.IGNORECASE),
    "balance_sheet": re.compile(
        r"statement of financial position|balance sheet", re.IGNORECASE),
    "cash_flow": re.compile(
        r"statement of cash ?flows?|cash ?flow statement", re.IGNORECASE),
    "changes_in_equity": re.compile(
        r"statement of changes in equity", re.IGNORECASE),
    "notes": re.compile(
        r"notes to the (?:financial statements|accounts)", re.IGNORECASE),
    "dividend": re.compile(
        r"dividend per share|dividend declared|proposed dividend|"
        r"interim dividend|final dividend", re.IGNORECASE),
    "share_count": re.compile(
        r"issued share capital|shares? in issue|authorised share capital|"
        r"number of (?:ordinary )?shares", re.IGNORECASE),
    "gross_profit": re.compile(r"gross profit", re.IGNORECASE),
    "ebitda_mention": re.compile(r"\bebitda\b", re.IGNORECASE),
    "segment_reporting": re.compile(r"segment (?:report|information|analysis)",
                                    re.IGNORECASE),
    "five_year_summary": re.compile(
        r"five[\s-]year (?:financial )?summary|5[\s-]year (?:financial )?summary",
        re.IGNORECASE),
}

# a "tabular comparison row": a label (words) followed by 2+ numeric fields
# and optionally a trailing percentage -- e.g. "Total assets 16,235,995
# 10,857,571 49.5%". READ-ONLY structural detector, not an extractor: does
# not capture or store any matched value, only counts how many such rows
# exist per document as a proxy for "this document has a deterministically
# -parseable tabular block."
TABULAR_ROW = re.compile(
    r"^[A-Za-z][A-Za-z\s\-/'.()]{2,45}\s+[\d,]{3,}(?:\.\d+)?\s+[\d,]{2,}(?:\.\d+)?"
    r"(?:\s+[\-\d.]+%)?\s*$", re.MULTILINE)


def load_docs(con: sqlite3.Connection, doc_type: str | None = None) -> list[tuple]:
    q = ("SELECT doc_id, ticker, doc_type, filing_date, char_count, text_path "
         "FROM documents WHERE source_confidence >= 0.8 AND char_count > ? "
         "AND text_path IS NOT NULL")
    params: list = [CHAR_FLOOR]
    if doc_type:
        q += " AND doc_type = ?"
        params.append(doc_type)
    return con.execute(q, params).fetchall()


def read_text(text_path: str) -> str | None:
    p = ROOT / text_path
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    print("=" * 70)
    print("PART 1 -- section-header presence, ALL native-text candidate docs")
    print("(source_confidence>=0.8, char_count>3000 -- same floor as the")
    print(" original fsi_scope_candidates.py scoping, for comparability)")
    print("=" * 70)
    all_docs = load_docs(con)
    print(f"population: {len(all_docs)} documents")

    section_doc_hits: dict[str, int] = Counter()
    section_ticker_hits: dict[str, set] = defaultdict(set)
    by_doctype_section: dict[str, Counter] = defaultdict(Counter)
    by_year_section: dict[str, Counter] = defaultdict(Counter)
    doc_texts: dict[int, str] = {}

    for doc_id, ticker, doc_type, filing_date, char_count, text_path in all_docs:
        text = read_text(text_path)
        if text is None:
            continue
        doc_texts[doc_id] = text
        year = (filing_date or "")[:4]
        for name, pat in SECTION_PATTERNS.items():
            if pat.search(text):
                section_doc_hits[name] += 1
                section_ticker_hits[name].add(ticker)
                by_doctype_section[doc_type][name] += 1
                by_year_section[year][name] += 1

    print(f"\n{'section':<22}{'docs':>8}{'pct_of_pop':>12}{'distinct_tickers':>18}")
    for name in SECTION_PATTERNS:
        n = section_doc_hits[name]
        pct = 100.0 * n / len(all_docs) if all_docs else 0.0
        print(f"{name:<22}{n:>8}{pct:>11.1f}%{len(section_ticker_hits[name]):>18}")

    print("\nSection presence by doc_type (top 6 doc_types by volume):")
    doctype_counts = Counter(d[2] for d in all_docs)
    for dt, _ in doctype_counts.most_common(6):
        print(f"  {dt}: {dict(by_doctype_section[dt])}")

    print("\nSection presence by filing year:")
    for year in sorted(by_year_section):
        print(f"  {year}: {dict(by_year_section[year])}")

    print()
    print("=" * 70)
    print("PART 2 -- results_notice format classification (tabular vs")
    print("narrative-bullet 'Financial highlights' style)")
    print("=" * 70)
    rn_docs = load_docs(con, doc_type="results_notice")
    print(f"population: {len(rn_docs)} results_notice documents, "
          f"{len({d[1] for d in rn_docs})} distinct tickers")

    tabular_docs = []
    narrative_docs = []
    neither_docs = []
    per_ticker_format: dict[str, list[str]] = defaultdict(list)
    for doc_id, ticker, doc_type, filing_date, char_count, text_path in rn_docs:
        text = doc_texts.get(doc_id) or read_text(text_path)
        if text is None:
            continue
        n_tabular_rows = len(TABULAR_ROW.findall(text))
        has_highlights_bullets = bool(
            re.search(r"financial highlights", text, re.IGNORECASE))
        if n_tabular_rows >= 5:
            tabular_docs.append((doc_id, ticker, n_tabular_rows))
            per_ticker_format[ticker].append("tabular")
        elif has_highlights_bullets:
            narrative_docs.append((doc_id, ticker))
            per_ticker_format[ticker].append("narrative")
        else:
            neither_docs.append((doc_id, ticker))
            per_ticker_format[ticker].append("neither")

    print(f"\nTabular-comparison-table format (>=5 label+2-number(+%) rows): "
          f"{len(tabular_docs)} docs, {len({t for _, t, _ in tabular_docs})} tickers")
    print(f"Narrative 'Financial highlights' bullet format: {len(narrative_docs)} docs, "
          f"{len({t for _, t in narrative_docs})} tickers")
    print(f"Neither pattern detected: {len(neither_docs)} docs, "
          f"{len({t for _, t in neither_docs})} tickers")

    print("\nSample tabular-format docs (doc_id, ticker, row_count):")
    for row in sorted(tabular_docs, key=lambda r: -r[2])[:15]:
        print(" ", row)

    print()
    print("=" * 70)
    print("PART 3 -- cross-reference vs the 50-ticker candidate pool from")
    print("the prior FSI Coverage Expansion audit")
    print("=" * 70)
    already_extracted = {"AFRIPRUD", "BUAFOODS", "CAP", "DANGCEM", "MTNN",
                         "NASCON", "NESTLE", "OANDO", "UBN", "UCAP"}
    # STRICT pool: same revenue+profit+money keyword filter as the original
    # fsi_scope_candidates.py / prior audit's 50-ticker figure -- NOT the
    # broader "any sufficiently long native-text doc" population used in
    # Part 1/2 above (that broader population is a different, larger set
    # and is kept separate to avoid conflating the two).
    REVENUE_TERMS = re.compile(r"revenue|turnover", re.IGNORECASE)
    PROFIT_TERMS = re.compile(r"profit after tax|net profit|\bpat\b", re.IGNORECASE)
    MONEY_TERMS = re.compile(r"₦|n\d|million|billion", re.IGNORECASE)
    strict_candidates = set()
    for doc_id, ticker, doc_type, filing_date, char_count, text_path in all_docs:
        if ticker is None:
            continue
        text = doc_texts.get(doc_id)
        if text is None:
            continue
        if REVENUE_TERMS.search(text) and PROFIT_TERMS.search(text) and MONEY_TERMS.search(text):
            strict_candidates.add(ticker)
    remaining = strict_candidates - already_extracted
    print(f"STRICT candidate pool (revenue+profit+money, same filter as the "
          f"prior audit): {len(strict_candidates)} tickers "
          f"(prior audit's re-run found 50; this pass restricted to the "
          f">3000-char population already loaded: {len(strict_candidates)})")

    depth_ready = set()  # remaining tickers with income+balance_sheet+cash_flow ALL present somewhere
    for doc_id, ticker, doc_type, filing_date, char_count, text_path in all_docs:
        if ticker not in remaining:
            continue
        text = doc_texts.get(doc_id)
        if text is None:
            continue
    # recompute per-ticker section coverage for the "remaining" set specifically
    ticker_sections: dict[str, set] = defaultdict(set)
    for doc_id, ticker, doc_type, filing_date, char_count, text_path in all_docs:
        if ticker not in remaining:
            continue
        text = doc_texts.get(doc_id)
        if text is None:
            continue
        for name, pat in SECTION_PATTERNS.items():
            if pat.search(text):
                ticker_sections[ticker].add(name)

    core3 = {"income_statement", "balance_sheet", "cash_flow"}
    full_depth = [t for t in remaining if core3 <= ticker_sections.get(t, set())]
    partial_depth = [t for t in remaining
                     if ticker_sections.get(t, set()) and not core3 <= ticker_sections[t]]
    no_depth = [t for t in remaining if not ticker_sections.get(t)]
    print(f"Of {len(remaining)} remaining (unextracted) candidate tickers:")
    print(f"  ALL of income+balance_sheet+cash_flow section headers detected "
          f"in at least one filing: {len(full_depth)} -> {sorted(full_depth)}")
    print(f"  PARTIAL section coverage: {len(partial_depth)} -> {sorted(partial_depth)}")
    print(f"  NO section header detected at all (only passed the "
          f"revenue/profit keyword filter): {len(no_depth)} -> {sorted(no_depth)}")

    print()
    print("=" * 70)
    print("PART 4 -- UNRESOLVED-ticker documents (data-quality check)")
    print("=" * 70)
    unresolved = con.execute(
        "SELECT doc_id, doc_type, filing_date, char_count, text_path FROM documents "
        "WHERE source_confidence>=0.8 AND char_count>3000 AND ticker IS NULL"
    ).fetchall()
    print(f"count, broader population (>3000 chars, any content): {len(unresolved)}")
    strict_unresolved = []
    for doc_id, doc_type, filing_date, char_count, text_path in unresolved:
        text = read_text(text_path)
        if text and REVENUE_TERMS.search(text) and PROFIT_TERMS.search(text) and MONEY_TERMS.search(text):
            strict_unresolved.append((doc_id, doc_type, filing_date, char_count, text_path))
    print(f"count, STRICT pool (revenue+profit+money, matches the prior "
          f"audit's '30 UNRESOLVED' figure): {len(strict_unresolved)}")
    print("\nSample of ALL unresolved docs (first lines, to spot-check "
          "whether the real company name is recoverable from the text):")
    seen_firstlines = set()
    shown = 0
    for doc_id, doc_type, filing_date, char_count, text_path in unresolved:
        text = read_text(text_path)
        first_line = (text or "").strip().splitlines()[0][:80] if text else "(unreadable)"
        if first_line in seen_firstlines:
            continue
        seen_firstlines.add(first_line)
        print(f"  doc_id={doc_id} type={doc_type} date={filing_date} "
              f"chars={char_count} first_line={first_line!r}")
        shown += 1
        if shown >= 15:
            break

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
