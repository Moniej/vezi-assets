"""Stage 23 -- Bounded Insider-Dealing Pilot (2026-08-09).

Feasibility pilot only. No hypothesis, no factor, no return calculation, no
backtest. Classifies all 163 doc_type='dealing' filings, deterministically
extracts transaction fields (regex only -- no LLM used to infer direction,
dates, prices, or economic meaning), resolves null-ticker rows from
deterministic sources only, flags duplicates, and reports concentration/PIT/
survivorship facts needed for the final GO/CONDITIONAL GO/NO-GO gate.

  PYTHONPATH=src python scripts/stage23_insider_dealing_pilot.py
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ROOT / "data" / "staging" / "document_text"
OUT = ROOT / "data" / "staging" / "stage23"
OUT.mkdir(parents=True, exist_ok=True)

VESTING_MARKERS = [
    r"not a purchase or sale",
    r"vesting of shares",
    r"restricted shares? performance plan",
    r"notification on vesting",
    r"notification of vesting",
]
PURCHASE_MARKERS = [r"\bPURCHASE\b", r"\bBOUGHT\b", r"\bACQUISITION\b", r"\bACQUIRED\b"]
SALE_MARKERS = [r"\bSALE\b", r"\bSOLD\b", r"\bDISPOSAL\b", r"\bDISPOSED\b"]


def load_text(doc_id: int) -> str:
    p = TEXT_DIR / f"{doc_id}.txt"
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def classify_and_extract(doc_id: int, ticker: str | None, text: str) -> dict:
    row = dict(doc_id=doc_id, ticker=ticker)
    if len(text.strip()) < 20:
        row["classification"] = "unusable/ambiguous"
        row["unusable_reason"] = "no_native_text (scanned image PDF, OCR required, not run in this pilot)"
        return row

    low = text.lower()
    if any(re.search(m, low) for m in VESTING_MARKERS):
        row["classification"] = "vesting/non-trade"
        return row

    # Nature-of-transaction: whole-document keyword-dominance count (deterministic,
    # robust to layout variation across issuers -- narrower zone-based capture was
    # tried first and found too format-fragile to generalize, see format-variety audit).
    whole_purchase = len(re.findall(r"|".join(PURCHASE_MARKERS), text, re.IGNORECASE))
    whole_sale = len(re.findall(r"|".join(SALE_MARKERS), text, re.IGNORECASE))
    if whole_purchase > 0 and whole_sale == 0:
        nature = "PURCHASE"
    elif whole_sale > 0 and whole_purchase == 0:
        nature = "SALE"
    else:
        nature = "UNKNOWN"

    if nature == "UNKNOWN":
        row["classification"] = "unusable/ambiguous"
        row["unusable_reason"] = (
            "both_purchase_and_sale_keywords_present_or_neither_found "
            f"(purchase_hits={whole_purchase}, sale_hits={whole_sale})"
        )
        return row

    row["classification"] = f"genuine insider {nature}"
    row["transaction_type"] = nature

    def window_after(label_pattern: str, span: int = 120) -> str:
        m = re.search(label_pattern, text, re.IGNORECASE)
        return text[m.end():m.end() + span] if m else ""

    # Insider name -- two template variants confirmed by hand audit (see Sec.5
    # report): "a) Name\n<NAME>" (next line) and "a) Name <NAME>" (same line).
    name_win = window_after(r"Name\s+of\s+(?:the\s+)?(?:Director|Insider)|a\)\s*Name")
    name_m = re.search(r"([A-Z][A-Za-z\.\s,\-']{3,60})", name_win)
    row["insider_name"] = name_m.group(1).strip() if name_m else "UNKNOWN"

    # Position/role
    role_win = window_after(r"Position/status")
    role_m = re.search(r"([A-Za-z][A-Za-z /\-]{2,60})", role_win)
    row["insider_role"] = role_m.group(1).strip() if role_m else "UNKNOWN"

    # ISIN (ticker cross-check aid)
    isin_m = re.search(r"ISIN[:\s]*([A-Z]{2}[A-Z0-9]{8,10})", text)
    row["isin"] = isin_m.group(1) if isin_m else "UNKNOWN"

    # Date of Transaction -- three confirmed template variants by hand audit:
    # "14 JANUARY 2020" (plain), "26th June, 2020" (ordinal suffix),
    # "Tuesday, September 22, 2020" (weekday-prefixed). Likely not exhaustive
    # of every variant in the corpus -- see Sec.5 format-variety audit.
    date_win = window_after(r"Date of Transaction", span=100)
    date_m = re.search(
        r"([0-9]{1,2}(?:st|nd|rd|th)?\s*[A-Za-z]+,?\s*[0-9]{4}"
        r"|[A-Za-z]+,?\s+[A-Za-z]+\s+[0-9]{1,2},?\s*[0-9]{4})",
        date_win,
    )
    row["transaction_date_raw"] = date_m.group(1).strip() if date_m else "UNKNOWN"

    # Aggregate volume -- accept "UNITS" and "shares" (both confirmed present),
    # with or without comma separators.
    agg_vol_m = re.search(r"Aggregat\w*\s*volume\D{0,40}?([\d,]{4,})\s*(?:UNITS?|shares?)", text, re.IGNORECASE)
    if not agg_vol_m:
        agg_vol_m = re.search(r"([\d,]{4,})\s*(?:UNITS?|shares?)\s*(?:@|at)", text, re.IGNORECASE)
    row["shares"] = agg_vol_m.group(1).replace(",", "") if agg_vol_m else "UNKNOWN"

    # Price -- accept "@N0.21", "@ N5.99", and "N5.9999 per share" styles.
    price_m = re.search(r"Aggregat\w*.{0,80}?Price\D{0,20}?N?\s*([\d]+\.?\d*)", text, re.IGNORECASE | re.DOTALL)
    if not price_m:
        price_m = re.search(r"@\s*N?\s*([\d]+\.?\d*)", text)
    if not price_m:
        price_m = re.search(r"N\s*([\d]+\.?\d*)\s*per\s*share", text, re.IGNORECASE)
    row["price"] = price_m.group(1) if price_m else "UNKNOWN"

    if row.get("shares") not in (None, "UNKNOWN") and row.get("price") not in (None, "UNKNOWN"):
        try:
            row["consideration"] = float(row["shares"]) * float(row["price"])
        except ValueError:
            row["consideration"] = "UNKNOWN"
    else:
        row["consideration"] = "UNKNOWN"

    return row


def resolve_null_ticker(text: str, isin: str | None, securities_by_isin: dict, securities_by_name: dict) -> tuple[str, str]:
    """Deterministic resolution only: ISIN match against securities.isin, or
    exact/near-exact issuer-name match against securities.name, scoped to the
    'Details of the issuer' section of the form (both field-orderings seen in
    the corpus -- 'Name...a)...NAME' and 'a) Name NAME' -- are tried). Returns
    (resolved_ticker_or_UNKNOWN, method)."""
    if isin and isin != "UNKNOWN" and isin in securities_by_isin:
        return securities_by_isin[isin], "isin_match"

    m = re.search(r"Details of the issuer", text, re.IGNORECASE)
    if m:
        window = text[m.end():m.end() + 200]
        name_m = re.search(r"Name\s*\n*\s*(?:a\)\s*)?\n*\s*([A-Z][A-Za-z0-9 &\.\-']{3,70})", window)
        if name_m:
            candidate = re.sub(r"\s+", " ", name_m.group(1)).strip().upper()
            candidate = re.sub(r"\bPLC\.?$", "", candidate).strip()
            for sec_name, tick in securities_by_name.items():
                sec_clean = re.sub(r"\bPLC\.?$", "", sec_name).strip()
                if candidate == sec_clean or candidate in sec_clean or sec_clean in candidate:
                    return tick, "issuer_name_match"
    return "UNKNOWN", "unresolved"


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    docs = con.execute(
        "SELECT doc_id, ticker, filing_date, source_url, local_path FROM documents WHERE doc_type='dealing' ORDER BY filing_date"
    ).fetchall()

    securities = con.execute("SELECT ticker, isin, name FROM securities").fetchall()
    securities_by_isin = {isin: t for t, isin, name in securities if isin}
    securities_by_name = {name.upper(): t for t, isin, name in securities if name}

    print(f"=== Step 1 recap: total filings={len(docs)} ===")

    records = []
    for doc_id, ticker, filing_date, source_url, local_path in docs:
        text = load_text(doc_id)
        rec = classify_and_extract(doc_id, ticker, text)
        rec["filing_date"] = filing_date
        rec["source_url"] = source_url
        rec["document_id"] = doc_id
        rec["disclosure_date"] = filing_date  # first defensible public disclosure date (filing_date), see PIT audit below
        rec["char_count"] = len(text)

        if ticker is None:
            resolved, method = resolve_null_ticker(text, rec.get("isin"), securities_by_isin, securities_by_name)
            rec["ticker_resolved"] = resolved
            rec["ticker_resolution_method"] = method
        else:
            rec["ticker_resolved"] = ticker
            rec["ticker_resolution_method"] = "already_present"

        records.append(rec)

    df = pd.DataFrame(records)
    df.to_csv(OUT / "all_filings_classified.csv", index=False)

    print("\n=== Classification counts ===")
    print(df["classification"].value_counts(dropna=False).to_string())

    print("\n=== Step 3: null-ticker resolution ===")
    null_ticker_df = df[df["ticker"].isna()]
    print(f"n_null_ticker={len(null_ticker_df)}")
    print(null_ticker_df[["doc_id", "classification", "ticker_resolved", "ticker_resolution_method"]].to_string())
    n_resolved = (null_ticker_df["ticker_resolution_method"] != "unresolved").sum()
    print(f"resolved={n_resolved}  unresolved={len(null_ticker_df) - n_resolved}")

    print("\n=== Step 4: duplicate/reissue audit ===")
    print("Authoritative check: exact source_url duplicates (independent of field extraction quality) --")
    url_counts = df["source_url"].value_counts()
    url_dupes = url_counts[url_counts > 1]
    print(f"n_exact_url_duplicate_groups={len(url_dupes)}  covering {url_dupes.sum()} filings")
    for url, n in url_dupes.items():
        ids = df[df["source_url"] == url]["doc_id"].tolist()
        print(f"  n={n} doc_ids={ids} url={url}")

    genuine = df[df["classification"].str.startswith("genuine", na=False)].copy()
    dup_key_cols = ["ticker_resolved", "transaction_date_raw", "insider_name", "shares", "transaction_type"]
    genuine["dup_key"] = genuine[dup_key_cols].astype(str).agg("|".join, axis=1)
    dup_counts = genuine["dup_key"].value_counts()
    dup_groups = dup_counts[dup_counts > 1]
    print(f"\nSecondary, exploratory check: exact field-value duplicate keys (ticker|date|name|shares|type) --")
    print("CAVEAT: this collapses rows where extraction returned UNKNOWN for multiple fields, producing "
          "false-positive groups (distinct filings that merely share unresolved placeholder values), not "
          "necessarily genuine duplicates. Treat as a lead for manual review, not a count.")
    print(f"n_field_key_duplicate_groups={len(dup_groups)}  covering {dup_groups.sum()} filings")
    for key, n in dup_groups.items():
        sub = genuine[genuine["dup_key"] == key][["doc_id", "filing_date", "source_url"]]
        print(f"-- key={key} n={n} --")
        print(sub.to_string(index=False))
    genuine.to_csv(OUT / "genuine_transactions_with_dupkey.csv", index=False)

    print("\n=== Step 6: concentration analysis (genuine, non-duplicate-collapsed) ===")
    print(f"total_filings={len(df)}")
    print(f"genuine_transactions={len(genuine)}")
    print(f"unique_tickers={genuine['ticker_resolved'].nunique()}")
    by_ticker = genuine["ticker_resolved"].value_counts()
    print("\ntransactions per ticker:")
    print(by_ticker.to_string())
    top3 = by_ticker.head(3).sum()
    top5 = by_ticker.head(5).sum()
    print(f"\ntop3_share={top3}/{len(genuine)}={top3/len(genuine):.1%}")
    print(f"top5_share={top5}/{len(genuine)}={top5/len(genuine):.1%}")
    genuine["year"] = pd.to_datetime(genuine["filing_date"]).dt.year
    print("\ntransactions per year:")
    print(genuine["year"].value_counts().sort_index().to_string())
    print("\npurchase/sale counts:")
    print(genuine["transaction_type"].value_counts().to_string())
    print(f"\neffective breadth (unique tickers / total genuine): {genuine['ticker_resolved'].nunique()}/{len(genuine)}")

    print("\n=== Step 7: PIT audit -- transaction_date_raw UNKNOWN rate ===")
    unk_txn_date = (genuine["transaction_date_raw"] == "UNKNOWN").sum()
    print(f"genuine transactions with UNKNOWN transaction_date: {unk_txn_date}/{len(genuine)}")
    print("disclosure_date (filing_date) is populated for all rows by construction "
          "(documents.filing_date is NOT NULL per schema).")

    print("\n=== Step 8: survivorship audit (cross-check against equity_prices, not delisting_date) ===")
    tickers = [t for t in genuine["ticker_resolved"].unique() if t and t != "UNKNOWN"]
    for t in sorted(tickers):
        r = con.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM equity_prices WHERE ticker=?", (t,)).fetchone()
        if r[2] == 0:
            print(f"  {t}: NO PRICE DATA AT ALL")
    print("(tickers with price data are listed only if missing entirely; see report for narrative)")


if __name__ == "__main__":
    main()
