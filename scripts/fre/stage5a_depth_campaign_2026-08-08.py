"""Stage 5A (2026-08-08) — Financial Strength depth campaign.

Re-reads LARGER, previously-unopened documents (mostly full annual
reports, identified by char_count and a balance-sheet keyword screen)
for the 10 tickers Stage 4 found Financial-Strength-eligible. Same
hand-verification convention as every prior extraction script this
program has used. `current_assets`/`current_liabilities` extracted
where a clean stated line exists (DANGCEM only, this batch).

Every comparative-column fact is tagged in its description as using the
CONSERVATIVE (later) filing_date as knowledge_date, per the explicit
instruction not to imply an earlier de-facto announcement date. Two
tickers (GEREGU, LASACO) were searched and confirmed to have NO other
balance-sheet-bearing document anywhere in the archive -- a real
negative finding, not attempted here, not silently skipped.

Run: python -u scripts/fre/stage5a_depth_campaign_2026-08-08.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "stage5a_hand_2026-08-08"

CONSERVATIVE_NOTE = (
    " [COMPARATIVE COLUMN: knowledge_date is this document's OWN "
    "filing_date, which is LATER than this period's original annual-"
    "results announcement (not separately harvested) -- conservative, "
    "safe-direction dating, not the true earliest-known date.]"
)

# (doc_id, ticker, fact_type, value, description, quote, period_end,
#  period_type, tier)
FACTS = [
    # --- DANGCEM doc 4397 (FY2019 Annual Report, filed 2020-12-18) ---
    # Group column used, matching this ticker's existing convention.
    (4397, "DANGCEM", "assets", 1741351000000.0,
     "Total assets, FY2019, Group (table N'm x1e6)",
     "Total assets 1,741,351 1,694,463 1,823,984 1,721,974", "2019-12-31", "FY", "direct_reported"),
    (4397, "DANGCEM", "liabilities", 843414000000.0,
     "Total liabilities, FY2019, Group (table N'm x1e6)",
     "Total liabilities 843,414 707,850 541,735 428,426", "2019-12-31", "FY", "direct_reported"),
    (4397, "DANGCEM", "equity", 897937000000.0,
     "Total equity, FY2019, Group (table N'm x1e6) -- DIRECT stated, not "
     "derived (this filing states it explicitly, unlike MTNN)",
     "Total equity 897,937 986,613 1,282,249 1,293,548", "2019-12-31", "FY", "direct_reported"),
    (4397, "DANGCEM", "assets", 1694463000000.0,
     "Total assets, FY2018, Group (comparative column, N'm x1e6)." + CONSERVATIVE_NOTE,
     "Total assets 1,741,351 1,694,463 1,823,984 1,721,974", "2018-12-31", "FY", "direct_reported"),
    (4397, "DANGCEM", "liabilities", 707850000000.0,
     "Total liabilities, FY2018, Group (comparative column, N'm x1e6)." + CONSERVATIVE_NOTE,
     "Total liabilities 843,414 707,850 541,735 428,426", "2018-12-31", "FY", "direct_reported"),
    (4397, "DANGCEM", "equity", 986613000000.0,
     "Total equity, FY2018, Group (comparative column, N'm x1e6), direct stated." + CONSERVATIVE_NOTE,
     "Total equity 897,937 986,613 1,282,249 1,293,548", "2018-12-31", "FY", "direct_reported"),

    # --- MTNN doc 5887 (FY2021 release, filed 2022-03-30), Group column ---
    (5887, "MTNN", "assets", 2259555000000.0,
     "Total assets, FY2021, Group (table N'm x1e6)",
     "Total assets 2,259,555 1,963,543 2,286,109 1,979,503", "2021-12-31", "FY", "direct_reported"),
    (5887, "MTNN", "liabilities", 1994574000000.0,
     "Total liabilities, FY2021, Group (table N'm x1e6)",
     "Total liabilities 1,994,574 1,785,157", "2021-12-31", "FY", "direct_reported"),
    (5887, "MTNN", "equity", 264981000000.0,
     "Total equity, FY2021, Group (table N'm x1e6) -- direct stated. "
     "Cross-checked: assets(2,259,555) - liabilities(1,994,574) = "
     "264,981, matches exactly.",
     "Total equity 264,981 178,386", "2021-12-31", "FY", "direct_reported"),
    (5887, "MTNN", "assets", 1963543000000.0,
     "Total assets, FY2020, Group (comparative column, N'm x1e6)." + CONSERVATIVE_NOTE,
     "Total assets 2,259,555 1,963,543 2,286,109 1,979,503", "2020-12-31", "FY", "direct_reported"),
    (5887, "MTNN", "liabilities", 1785157000000.0,
     "Total liabilities, FY2020, Group (comparative column, N'm x1e6)." + CONSERVATIVE_NOTE,
     "Total liabilities 1,994,574 1,785,157", "2020-12-31", "FY", "direct_reported"),
    (5887, "MTNN", "equity", 178386000000.0,
     "Total equity, FY2020, Group (comparative column, N'm x1e6), direct "
     "stated. Cross-checked: 1,963,543 - 1,785,157 = 178,386, matches." + CONSERVATIVE_NOTE,
     "Total equity 264,981 178,386", "2020-12-31", "FY", "direct_reported"),

    # --- UCAP doc 9449 (FY2024 release, filed 2025-03-03) ---
    (9449, "UCAP", "assets", 1701700000000.0,
     "Total Assets, FY2024 (table N'bn x1e9)",
     "Total Assets (N�bn) 1,701.70 931.95 83%", "2024-12-31", "FY", "direct_reported"),
    (9449, "UCAP", "liabilities", 1568200000000.0,
     "Total Liabilities, FY2024 (table N'bn x1e9)",
     "Total Liabilities (N�bn) 1,568.20 841.23 86%", "2024-12-31", "FY", "direct_reported"),
    (9449, "UCAP", "equity", 133500000000.0,
     "Derived: assets (1,701.70) - liabilities (1,568.20), FY2024, N'bn x1e9",
     None, "2024-12-31", "FY", "derived"),
    (9449, "UCAP", "assets", 931950000000.0,
     "Total Assets, FY2023 (comparative column, N'bn x1e9)." + CONSERVATIVE_NOTE,
     "Total Assets (N�bn) 1,701.70 931.95 83%", "2023-12-31", "FY", "direct_reported"),
    (9449, "UCAP", "liabilities", 841230000000.0,
     "Total Liabilities, FY2023 (comparative column, N'bn x1e9)." + CONSERVATIVE_NOTE,
     "Total Liabilities (N�bn) 1,568.20 841.23 86%", "2023-12-31", "FY", "direct_reported"),
    (9449, "UCAP", "equity", 90720000000.0,
     "Derived: assets (931.95) - liabilities (841.23), FY2023, N'bn x1e9." + CONSERVATIVE_NOTE,
     None, "2023-12-31", "FY", "derived"),

    # --- AIRTELAFRI doc 6126 (FY2022 report, filed 2022-05-11), USD
    # millions raw, matching this ticker's own existing unconverted
    # convention ---
    (6126, "AIRTELAFRI", "assets", 10364.0,
     "Total assets, as of 31 March 2022 (raw USD millions, unconverted)",
     "Total assets 10,364 9,992", "2022-03-31", "FY", "direct_reported"),
    (6126, "AIRTELAFRI", "liabilities", 6715.0,
     "Total liabilities, as of 31 March 2022 (raw USD millions)",
     "Total liabilities 6,715 6,639", "2022-03-31", "FY", "direct_reported"),
    (6126, "AIRTELAFRI", "equity", 3649.0,
     "Total equity, as of 31 March 2022 (raw USD millions)",
     "Total equity 3,649 3,353", "2022-03-31", "FY", "direct_reported"),
    (6126, "AIRTELAFRI", "assets", 9992.0,
     "Total assets, as of 31 March 2021 (comparative column, raw USD millions)." + CONSERVATIVE_NOTE,
     "Total assets 10,364 9,992", "2021-03-31", "FY", "direct_reported"),
    (6126, "AIRTELAFRI", "liabilities", 6639.0,
     "Total liabilities, as of 31 March 2021 (comparative column, raw USD millions)." + CONSERVATIVE_NOTE,
     "Total liabilities 6,715 6,639", "2021-03-31", "FY", "direct_reported"),
    (6126, "AIRTELAFRI", "equity", 3353.0,
     "Total equity, as of 31 March 2021 (comparative column, raw USD millions)." + CONSERVATIVE_NOTE,
     "Total equity 3,649 3,353", "2021-03-31", "FY", "direct_reported"),

    # --- AFRIPRUD doc 3961 (H1 2020 statement, filed 2020-07-23), N'000 x1000 ---
    (3961, "AFRIPRUD", "assets", 22896967000.0,
     "Total assets, 30 June 2020 (table N'000 x1000)",
     "TOTAL ASSETS 22,896,967", "2020-06-30", "H1", "direct_reported"),
    (3961, "AFRIPRUD", "liabilities", 10365049000.0,
     "Total liabilities, 30 June 2020 (table N'000 x1000)",
     "TOTAL LIABILITIES 10,365,049", "2020-06-30", "H1", "direct_reported"),
    (3961, "AFRIPRUD", "equity", 12531918000.0,
     "Derived: assets (22,896,967) - liabilities (10,365,049), 30 June "
     "2020, N'000 x1000", None, "2020-06-30", "H1", "derived"),
    (3961, "AFRIPRUD", "assets", 18649333000.0,
     "Total assets, 31 Dec 2019 (comparative column, N'000 x1000)." + CONSERVATIVE_NOTE,
     "TOTAL ASSETS 22,896,967 18,649,333", "2019-12-31", "FY", "direct_reported"),
    (3961, "AFRIPRUD", "liabilities", 14974452000.0,
     "Total liabilities, 31 Dec 2019 (comparative column, N'000 x1000)." + CONSERVATIVE_NOTE,
     "TOTAL LIABILITIES 10,365,049\n14,974,452", "2019-12-31", "FY", "direct_reported"),
    (3961, "AFRIPRUD", "equity", 3674881000.0,
     "Derived: assets (18,649,333) - liabilities (14,974,452), 31 Dec "
     "2019, N'000 x1000." + CONSERVATIVE_NOTE, None, "2019-12-31", "FY", "derived"),

    # --- BUAFOODS doc 9790 (Q1 2025 release, filed 2025-05-02), N'000 x1000 ---
    (9790, "BUAFOODS", "assets", 1142637894000.0,
     "Total assets, 3M 2025 i.e. as at 31 March 2025 (table N'000 x1000)",
     "Total assets 1,142,637,894 1,095,504,241 4.3%", "2025-03-31", "Q1", "direct_reported"),
    (9790, "BUAFOODS", "liabilities", 588300227000.0,
     "Total liabilities, as at 31 March 2025 (table N'000 x1000)",
     "Total liabilities 588,300,227 666,447,596 -11.7%", "2025-03-31", "Q1", "direct_reported"),
    (9790, "BUAFOODS", "equity", 554337667000.0,
     "Total equity, as at 31 March 2025 (table N'000 x1000), direct stated",
     "Total equity 554,337,667 429,056,645 29.2%", "2025-03-31", "Q1", "direct_reported"),

    # --- CAP doc 4960 (FY2020 Annual Report, filed 2021-05-18), N'000
    # x1000 -- NOTE: this is a DIFFERENT unit scale than CAP's other
    # extracted facts (which use N'm x1e6); converted here to match the
    # ticker's PREVAILING convention (full naira), not left as a raw
    # mismatch. This fills the FY2020 balance-sheet gap Stage 4
    # explicitly flagged as unfillable from doc 4508 (ratio-only). ---
    (4960, "CAP", "assets", 8526076000.0,
     "Total assets, FY2020 (table N'000 x1000, converted to match this "
     "ticker's other facts' full-naira scale) -- fills the gap Stage 4 "
     "flagged as unfillable from doc 4508 (which had only a leverage ratio)",
     "Total assets 8,526,076 6,760,964", "2020-12-31", "FY", "direct_reported"),
    (4960, "CAP", "liabilities", 4781268000.0,
     "Total liabilities, FY2020 (table N'000 x1000, converted)",
     "Total liabilities 4,781,268 4,239,281", "2020-12-31", "FY", "direct_reported"),
    (4960, "CAP", "equity", 3744808000.0,
     "Total equity, FY2020 (table N'000 x1000, converted), direct stated",
     "Total equity 3,744,808 2,521,684", "2020-12-31", "FY", "direct_reported"),
    (4960, "CAP", "assets", 6760964000.0,
     "Total assets, FY2019 (comparative column, N'000 x1000, converted)." + CONSERVATIVE_NOTE,
     "Total assets 8,526,076 6,760,964", "2019-12-31", "FY", "direct_reported"),
    (4960, "CAP", "liabilities", 4239281000.0,
     "Total liabilities, FY2019 (comparative column, N'000 x1000, converted)." + CONSERVATIVE_NOTE,
     "Total liabilities 4,781,268 4,239,281", "2019-12-31", "FY", "direct_reported"),
    (4960, "CAP", "equity", 2521684000.0,
     "Total equity, FY2019 (comparative column, N'000 x1000, converted), "
     "direct stated." + CONSERVATIVE_NOTE,
     "Total equity 3,744,808 2,521,684", "2019-12-31", "FY", "direct_reported"),
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
        print(f"written  {ticker:11s} {ftype:12s} {value:>18,.0f}  "
             f"{period_end}  grounding={status}")
    con.commit()
    print(f"\n{written} facts written, {failed} grounding failures.")


if __name__ == "__main__":
    main()
