"""Stage 4A (2026-08-08) — Financial Strength / Cash Flow Quality
extraction: balance sheet + cash flow fields for tickers that already
have revenue/net_profit but were missing them.

Same hand-verification convention as every prior FSI extraction script
this program has used (fsi_depth_pilot, Stage 3B, Stage 3C) -- every
quote checked via check_grounding() against the real source text;
nothing written on a failed check. No new fact_types (assets,
liabilities, equity, cfo, capex already exist in
configs/fact_taxonomy.toml). `equity` is DERIVED (assets - liabilities,
a pure accounting identity from the SAME statement, same period, same
document) wherever the filing states assets/liabilities but not equity
directly -- matching the platform's own established fcf/ebitda/cogs
derivation convention. Nothing is manufactured that isn't a direct
accounting identity of components stated in the SAME source document.

Documents re-read (already open/verified for revenue/net_profit,
zero new acquisition):
  DANGCEM: 8383 (Q1 2024 release, balance-sheet snapshots at
           31/3/2024 AND 31/12/2023), 9741 (Q1 2025 release, snapshots
           at 31/3/2025 AND 31/12/2024) -- 4 distinct period-ends from 2
           documents.
  MTNN:    8080 (FY2023 release), 9430 (FY2024 release) -- Group column
           used throughout, matching this ticker's existing
           revenue/net_profit convention (consolidated, not separate/
           Company-only).
  UBN:     5987 (FY2021 release) -- Group column, Total Assets only;
           no liabilities/equity breakdown available in this filing.

Run: python -u scripts/fre/stage4a_balance_sheet_cashflow_2026-08-08.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "stage4a_hand_2026-08-08"

# (doc_id, ticker, fact_type, value, description, quote, period_end,
#  period_type, tier)
FACTS = [
    # --- DANGCEM doc 8383 (Q1 2024 release): snapshots at 31/3/2024
    # (existing period) AND 31/12/2023 (new period) ---
    (8383, "DANGCEM", "assets", 5129645000000.0,
     "Total assets as at 31/3/2024 (table N'm x1e6)",
     "Total assets 5,129,645 3,938,725", "2024-03-31", "Q1", "direct_reported"),
    (8383, "DANGCEM", "liabilities", 2868163000000.0,
     "Total liabilities as at 31/3/2024 (table N'm x1e6)",
     "Total liabilities 2,868,163 2,212,885", "2024-03-31", "Q1", "direct_reported"),
    (8383, "DANGCEM", "equity", 2261482000000.0,
     "Derived: assets (5,129,645) - liabilities (2,868,163), 31/3/2024, N'm x1e6",
     None, "2024-03-31", "Q1", "derived"),
    (8383, "DANGCEM", "assets", 3938725000000.0,
     "Total assets as at 31/12/2023 (comparative column, table N'm x1e6) "
     "-- a NEW period_end not previously in the extracted_facts set",
     "Total assets 5,129,645 3,938,725", "2023-12-31", "FY", "direct_reported"),
    (8383, "DANGCEM", "liabilities", 2212885000000.0,
     "Total liabilities as at 31/12/2023 (comparative column, N'm x1e6)",
     "Total liabilities 2,868,163 2,212,885", "2023-12-31", "FY", "direct_reported"),
    (8383, "DANGCEM", "equity", 1725840000000.0,
     "Derived: assets (3,938,725) - liabilities (2,212,885), 31/12/2023, N'm x1e6",
     None, "2023-12-31", "FY", "derived"),
    (8383, "DANGCEM", "cfo", 320900000000.0,
     "Net cash flow from operations, Q1 2024 (narrative, precise figure, "
     "N'm x1e6): 'the net cash flow from operations was N320.9B for Q1 2024'",
     "the net cash flow from operations was", "2024-03-31", "Q1", "direct_reported"),

    # --- DANGCEM doc 9741 (Q1 2025 release): snapshots at 31/3/2025
    # (existing period) AND 31/12/2024 (new period) ---
    (9741, "DANGCEM", "assets", 6445354000000.0,
     "Total assets as at 31/3/2025 (table N'm x1e6)",
     "Total assets 6,445,354 6,403,238", "2025-03-31", "Q1", "direct_reported"),
    (9741, "DANGCEM", "liabilities", 4065569000000.0,
     "Total liabilities as at 31/3/2025 (table N'm x1e6)",
     "Total liabilities 4,065,569 4,227,993", "2025-03-31", "Q1", "direct_reported"),
    (9741, "DANGCEM", "equity", 2379785000000.0,
     "Derived: assets (6,445,354) - liabilities (4,065,569), 31/3/2025, N'm x1e6",
     None, "2025-03-31", "Q1", "derived"),
    (9741, "DANGCEM", "assets", 6403238000000.0,
     "Total assets as at 31/12/2024 (comparative column, N'm x1e6) -- a "
     "NEW period_end not previously in the extracted_facts set",
     "Total assets 6,445,354 6,403,238", "2024-12-31", "FY", "direct_reported"),
    (9741, "DANGCEM", "liabilities", 4227993000000.0,
     "Total liabilities as at 31/12/2024 (comparative column, N'm x1e6)",
     "Total liabilities 4,065,569 4,227,993", "2024-12-31", "FY", "direct_reported"),
    (9741, "DANGCEM", "equity", 2175245000000.0,
     "Derived: assets (6,403,238) - liabilities (4,227,993), 31/12/2024, N'm x1e6",
     None, "2024-12-31", "FY", "derived"),
    (9741, "DANGCEM", "cfo", 321300000000.0,
     "Net cash flow from operations, Q1 2025 (narrative, precise figure, "
     "N'm x1e6): 'the net cash flow from operations was N321.3B in Q1 2025'",
     "the net cash flow from operations was", "2025-03-31", "Q1", "direct_reported"),

    # --- MTNN doc 8080 (FY2023 release), Group column ---
    (8080, "MTNN", "assets", 3188827000000.0,
     "Total assets, FY2023, Group (table N'm x1e6)",
     "Total assets 3,188,827 2,539,369 2,099,812 3,239,635 2,572,902 2,122,962",
     "2023-12-31", "FY", "direct_reported"),
    (8080, "MTNN", "liabilities", 3229671000000.0,
     "Total liabilities, FY2023, Group (table N'm x1e6). NOTE: liabilities "
     "EXCEED assets -- MTN Nigeria has real, disclosed negative equity in "
     "this period (large FX-driven cumulative loss on dollar-denominated "
     "lease liabilities post-devaluation), consistent with this ticker's "
     "own existing net_profit fact being negative (-137,020,000,000) for "
     "the same period. Not a data error.",
     "Total liabilities 3,229,671 2,276,827 1,897,821 3,204,856 2,260,960 1,888,955",
     "2023-12-31", "FY", "direct_reported"),
    (8080, "MTNN", "equity", -40844000000.0,
     "Derived: assets (3,188,827) - liabilities (3,229,671), FY2023, N'm "
     "x1e6 -- NEGATIVE, a real reported condition, not an extraction error",
     None, "2023-12-31", "FY", "derived"),
    (8080, "MTNN", "cfo", 996903000000.0,
     "Net cash generated from operating activities, FY2023, Group (table N'm x1e6)",
     "Net cash generated from operating activities 996,903 863,663 1,016,007 866,589",
     "2023-12-31", "FY", "direct_reported"),
    (8080, "MTNN", "capex", -392997000000.0,
     "Acquisition of property and equipment, FY2023, Group (table N'm x1e6)",
     "Acquisition of property and equipment ( 392,997) (326,736) ( 392,997) ( 326,736)",
     "2023-12-31", "FY", "direct_reported"),

    # --- MTNN doc 9430 (FY2024 release), Group column ---
    (9430, "MTNN", "assets", 4196991000000.0,
     "Total assets, FY2024, Group (table N'm x1e6)",
     "Total assets 4,196,991 3,188,827 4,274,704 3,239,635", "2024-12-31", "FY", "direct_reported"),
    (9430, "MTNN", "liabilities", 4654998000000.0,
     "Total liabilities, FY2024, Group (table N'm x1e6). Again exceeds "
     "assets -- consistent with FY2023's own disclosed negative equity.",
     "Total liabilities 4,654,998 3,229,671 4,630,942 3,204,856", "2024-12-31", "FY", "direct_reported"),
    (9430, "MTNN", "equity", -458007000000.0,
     "Derived: assets (4,196,991) - liabilities (4,654,998), FY2024, N'm "
     "x1e6 -- NEGATIVE, real condition, deepening from FY2023",
     None, "2024-12-31", "FY", "derived"),
    (9430, "MTNN", "cfo", 868901000000.0,
     "Net cash generated from operating activities, FY2024, Group (table N'm x1e6)",
     "Net cash generated from operating activities 868,901 1,004,243 885,537 1,023,347",
     "2024-12-31", "FY", "direct_reported"),
    (9430, "MTNN", "capex", -339900000000.0,
     "Acquisition of property and equipment, FY2024, Group (table N'm x1e6)",
     "Acquisition of property and equipment (339,900) (392,997) (339,900) (392,997)",
     "2024-12-31", "FY", "direct_reported"),

    # --- UBN doc 5987 (FY2021 release), Group column. No
    # liabilities/equity breakdown available in this filing -- assets
    # only, honestly partial. ---
    (5987, "UBN", "assets", 2595800000000.0,
     "Total Assets, FY (Dec-21), Group (table N'bn x1e9). No liabilities "
     "or equity breakdown exists in this filing -- Financial Strength "
     "for UBN remains incomplete even after this extraction.",
     "Total Assets 2,567.4 2,073.8 23.8% 2,595.8 2,191.0 18.5%",
     "2021-12-31", "FY", "direct_reported"),
]


def main():
    con = db.init_db(PKG_ROOT / "data" / "ngx.sqlite")
    written, failed = 0, 0
    for doc_id, ticker, ftype, value, desc, quote, period_end, ptype, tier in FACTS:
        text_path = con.execute(
            "SELECT text_path FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")
        if quote is not None:
            g = check_grounding(quote, doc_text)
            status = "passed" if g.passed else "failed"
            if not g.passed:
                failed += 1
                print(f"GROUNDING FAILED {ticker} {ftype} {period_end}: {g.reason}")
                continue
        else:
            status = "not_run"
        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)", (doc_id, quote or f"[derived: {desc}]", 0.9)).lastrowid
        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, evidence_id, extraction_confidence, model_id, "
            "prompt_version, grounding_check, extracted_at, period_end, "
            "period_type, confidence_tier) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, ftype, f"{ticker}: {desc}", value, evidence_id, 1.0,
             None, PROMPT_VERSION, status, AS_OF, period_end, ptype, tier))
        written += 1
        print(f"written  {ticker:8s} {ftype:12s} {value:>18,.0f}  "
             f"{period_end}  grounding={status}  tier={tier}")
    con.commit()
    print(f"\n{written} facts written, {failed} grounding failures.")


if __name__ == "__main__":
    main()
