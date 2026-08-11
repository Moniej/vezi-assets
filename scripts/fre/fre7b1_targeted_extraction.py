"""FRE-7B.1: targeted, hand-verified extraction from the un-mined
results_notice backlog FRE-7B identified
(docs/fre_runs/fre7b_accounting_data_depth_audit.md).

Same production write pattern as every prior FSI hand-extraction script
(stage3a/3b/3c, stage4a, stage5a) -- deterministic label matching via the
EXISTING, unmodified `configs/financial_statement_terminology.toml` /
`terminology_mapping.map_label_to_concept()` (no LLM invoked; every label
below was matched against that config's own synonym lists, not invented),
a mechanical `check_grounding()` verification that the exact quoted text
appears verbatim in the source document (whitespace-normalized) before
any fact is written, and a currency column explicitly set on INSERT this
time (see fre7b1_currency_backfill.py's own docstring: stage4a/stage5a's
omission of this column was a real, disclosed bug this script does not
repeat).

## Scope actually covered (disclosed honestly, not overstated)

FRE-7B found 307 un-mined results_notice documents with real, retrieved
text. This script does NOT claim to have processed all 307 -- it
processed a validation sample of 10 documents across the Financials/
Industrials/ICT/Other priority groups (per the authorization's own
priority order), of which 3 yielded genuine, clean, structured financial
statements (AFRIPRUD doc 6921, UCAP doc 5740, DANGCEM doc 10758); the
other 7 (LASACO x2, DEAPCAP, CAVERTON, NCR, TRANSCORP, PRESTIGE) were
hand-verified and found to contain NO extractable numeric facts (delay
notices, a discrepancy correction notice, and one prose-only conglomerate
press release without table-precision figures) -- a real ~30% document-
level yield rate on this sample, reported honestly in
docs/fre_runs/fre7b1_targeted_accounting_extraction_report.md Section on
extraction validation, not silently omitted.

## Data integrity rules applied

- Every period is tagged FY explicitly (both years in each source table
  are genuine full-year, audited figures -- confirmed by each document's
  own "AUDITED RESULTS FOR THE YEAR ENDED..."/"FULL YEAR...AUDITED
  RESULTS" heading, itself preserved in each fact's description).
- Comparative (prior-year) columns use the CONSERVATIVE later filing_date
  as their own knowledge_date (same convention as stage5a) -- never
  implying an earlier de-facto announcement date than what this specific
  document's own filing_date actually is.
- DANGCEM's FY2025 equity is DERIVED (assets - liabilities); its FY2024
  equity is NOT re-inserted -- an identical value (2,175,245,000,000)
  already exists in the database (fact_id 373, stage4a), cross-validating
  this extraction's own arithmetic rather than duplicating it.
- currency='NGN' is set explicitly for every fact below (all 3 tickers
  are confirmed NGN domestic reporters per securities.reporting_currency).
- No debt/cash/EPS/shares_outstanding fact_type exists in this platform's
  schema (unchanged, out of scope to add) -- EPS values observed in the
  source text (AFRIPRUD 75/71 kobo, UCAP 188/130 kobo) are recorded in
  each fact's own description for provenance/cross-check purposes only,
  not written as a separate fact row.

  PYTHONPATH=src python scripts/fre/fre7b1_targeted_extraction.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.grounding import check_grounding  # noqa: E402
from ngxrot.fre.terminology_mapping import map_label_to_concept  # noqa: E402

AS_OF = date.today().isoformat()
PROMPT_VERSION = "fre7b1_hand_2026-08-09"

CONSERVATIVE_NOTE = (
    " [COMPARATIVE COLUMN: knowledge_date is this document's OWN filing_date, "
    "which is LATER than this period's original annual-results announcement "
    "(not separately harvested) -- conservative, safe-direction dating.]"
)

# (doc_id, ticker, observed_label, fact_type, value, description, quote,
#  period_start, period_end, period_type, tier)
FACTS = [
    # === AFRIPRUD doc 6921 -- AUDITED RESULTS FOR THE YEAR ENDED 31ST
    # DECEMBER 2022, filed 2023-03-02, amounts "In thousands of Nigerian
    # Naira" (x1000 applied below) ===
    (6921, "AFRIPRUD", "Profit after tax", "net_profit", 1493249000.0,
     "Profit after tax, FY2022, audited (table, N'000)",
     "Profit after tax 1,493,249 1,414,667",
     "2022-01-01", "2022-12-31", "FY", "direct_reported"),
    (6921, "AFRIPRUD", "Profit after tax", "net_profit", 1414667000.0,
     "Profit after tax, FY2021, audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "Profit after tax 1,493,249 1,414,667",
     "2021-01-01", "2021-12-31", "FY", "direct_reported"),
    (6921, "AFRIPRUD", "Gross earnings", "revenue", 4132848000.0,
     "Gross earnings (AFRIPRUD's own established revenue synonym, per "
     "configs/financial_statement_terminology.toml), FY2022, audited (N'000)",
     "Gross earnings 4,132,848 3,521,254",
     "2022-01-01", "2022-12-31", "FY", "direct_reported"),
    (6921, "AFRIPRUD", "Gross earnings", "revenue", 3521254000.0,
     "Gross earnings, FY2021, audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "Gross earnings 4,132,848 3,521,254",
     "2021-01-01", "2021-12-31", "FY", "direct_reported"),
    (6921, "AFRIPRUD", "TOTAL EQUITY", "equity", 9385588000.0,
     "Total equity, FY2022 audited (N'000). Cross-check: EPS 75 kobo, "
     "proposed dividend N0.50/share stated in same release.",
     "TOTAL EQUITY 9,385,588 8,770,790",
     None, "2022-12-31", None, "direct_reported"),
    (6921, "AFRIPRUD", "TOTAL EQUITY", "equity", 8770790000.0,
     "Total equity, FY2021 audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "TOTAL EQUITY 9,385,588 8,770,790",
     None, "2021-12-31", None, "direct_reported"),
    (6921, "AFRIPRUD", "TOTAL ASSETS", "assets", 19270686000.0,
     "Total assets, FY2022 audited (N'000)",
     "TOTAL ASSETS 19,270,686 15,764,176",
     None, "2022-12-31", None, "direct_reported"),
    (6921, "AFRIPRUD", "TOTAL ASSETS", "assets", 15764176000.0,
     "Total assets, FY2021 audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "TOTAL ASSETS 19,270,686 15,764,176",
     None, "2021-12-31", None, "direct_reported"),
    (6921, "AFRIPRUD", "TOTAL LIABILITIES", "liabilities", 9885098000.0,
     "Total liabilities, FY2022 audited (N'000)",
     "TOTAL LIABILITIES 9,885,098 6,993,386",
     None, "2022-12-31", None, "direct_reported"),
    (6921, "AFRIPRUD", "TOTAL LIABILITIES", "liabilities", 6993386000.0,
     "Total liabilities, FY2021 audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "TOTAL LIABILITIES 9,885,098 6,993,386",
     None, "2021-12-31", None, "direct_reported"),

    # === UCAP doc 5740 -- AUDITED RESULTS FOR THE YEAR ENDED DECEMBER 31,
    # 2021, filed 2022-02-18, amounts in =N='000 ===
    (5740, "UCAP", "Profit for the year", "net_profit", 11258738000.0,
     "Profit for the year, FY2021, audited (N'000)",
     "Profit for the year 11,258,738 7,811,178",
     "2021-01-01", "2021-12-31", "FY", "direct_reported"),
    (5740, "UCAP", "Profit for the year", "net_profit", 7811178000.0,
     "Profit for the year, FY2020, audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "Profit for the year 11,258,738 7,811,178",
     "2020-01-01", "2020-12-31", "FY", "direct_reported"),
    (5740, "UCAP", "Total Revenue", "revenue", 18065183000.0,
     "Total Revenue, FY2021, audited (N'000)",
     "Total Revenue 18,065,183 12,873,897",
     "2021-01-01", "2021-12-31", "FY", "direct_reported"),
    (5740, "UCAP", "Total Revenue", "revenue", 12873897000.0,
     "Total Revenue, FY2020, audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "Total Revenue 18,065,183 12,873,897",
     "2020-01-01", "2020-12-31", "FY", "direct_reported"),
    (5740, "UCAP", "TOTAL SHAREHOLDERS FUND", "equity", 30546793000.0,
     "Total shareholders fund, FY2021 audited (N'000). Cross-check: EPS "
     "188 kobo stated in same release.",
     "TOTAL SHAREHOLDERS FUND 30,546,793 24,426,479",
     None, "2021-12-31", None, "direct_reported"),
    (5740, "UCAP", "TOTAL SHAREHOLDERS FUND", "equity", 24426479000.0,
     "Total shareholders fund, FY2020 audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "TOTAL SHAREHOLDERS FUND 30,546,793 24,426,479",
     None, "2020-12-31", None, "direct_reported"),
    (5740, "UCAP", "TOTAL ASSETS", "assets", 453597954000.0,
     "Total assets, FY2021 audited (N'000)",
     "TOTAL ASSETS 453,597,954 222,748,295",
     None, "2021-12-31", None, "direct_reported"),
    (5740, "UCAP", "TOTAL ASSETS", "assets", 222748295000.0,
     "Total assets, FY2020 audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "TOTAL ASSETS 453,597,954 222,748,295",
     None, "2020-12-31", None, "direct_reported"),
    (5740, "UCAP", "TOTAL LIABILITIES", "liabilities", 423051161000.0,
     "Total liabilities, FY2021 audited (N'000)",
     "TOTAL LIABILITIES 423,051,161 198,321,816",
     None, "2021-12-31", None, "direct_reported"),
    (5740, "UCAP", "TOTAL LIABILITIES", "liabilities", 198321816000.0,
     "Total liabilities, FY2020 audited (comparative column, N'000)." + CONSERVATIVE_NOTE,
     "TOTAL LIABILITIES 423,051,161 198,321,816",
     None, "2020-12-31", None, "direct_reported"),

    # === DANGCEM doc 10758 -- FULL YEAR 2025 AUDITED RESULTS, filed
    # 2026-02-28, amounts in ₦mn (x1e6 applied below) ===
    (10758, "DANGCEM", "Group net profit", "net_profit", 1014921000000.0,
     "Group net profit, FY2025, audited (₦mn table)",
     "Group net profit 1,014,921 503,247 101.7%",
     "2025-01-01", "2025-12-31", "FY", "direct_reported"),
    (10758, "DANGCEM", "Group net profit", "net_profit", 503247000000.0,
     "Group net profit, FY2024, audited (comparative column, ₦mn table)." + CONSERVATIVE_NOTE,
     "Group net profit 1,014,921 503,247 101.7%",
     "2024-01-01", "2024-12-31", "FY", "direct_reported"),
    (10758, "DANGCEM", "Total revenue", "revenue", 4306704000000.0,
     "Total revenue, FY2025, audited (₦mn table)",
     "Total revenue 4,306,704 3,580,550 20.3%",
     "2025-01-01", "2025-12-31", "FY", "direct_reported"),
    (10758, "DANGCEM", "Total revenue", "revenue", 3580550000000.0,
     "Total revenue, FY2024, audited (comparative column, ₦mn table)." + CONSERVATIVE_NOTE,
     "Total revenue 4,306,704 3,580,550 20.3%",
     "2024-01-01", "2024-12-31", "FY", "direct_reported"),
    (10758, "DANGCEM", "Total assets", "assets", 6040727000000.0,
     "Total assets, FY2025 audited (₦mn table)",
     "Total assets 6,040,727 6,403,238",
     None, "2025-12-31", None, "direct_reported"),
    (10758, "DANGCEM", "Total assets", "assets", 6403238000000.0,
     "Total assets, FY2024 audited (comparative column, ₦mn table)." + CONSERVATIVE_NOTE,
     "Total assets 6,040,727 6,403,238",
     None, "2024-12-31", None, "direct_reported"),
    (10758, "DANGCEM", "Total liabilities", "liabilities", 3420591000000.0,
     "Total liabilities, FY2025 audited (₦mn table)",
     "Total liabilities 3,420,591 4,227,993",
     None, "2025-12-31", None, "direct_reported"),
    (10758, "DANGCEM", "Total liabilities", "liabilities", 4227993000000.0,
     "Total liabilities, FY2024 audited (comparative column, ₦mn table)." + CONSERVATIVE_NOTE,
     "Total liabilities 3,420,591 4,227,993",
     None, "2024-12-31", None, "direct_reported"),
    (10758, "DANGCEM", None, "equity", 2620136000000.0,
     "Derived: assets (6,040,727) - liabilities (3,420,591), FY2025, ₦mn. "
     "FY2024 equity NOT re-inserted here: an identical derived value "
     "(2,175,245,000,000 = 6,403,238 - 4,227,993) already exists in the "
     "database as fact_id 373 (stage4a) -- this arithmetic cross-validates "
     "that existing fact rather than duplicating it.",
     None, None, "2025-12-31", None, "derived"),
]


def main() -> int:
    con = db.init_db(ROOT / "data" / "ngx.sqlite")
    written, failed, mapping_mismatches = 0, 0, 0

    for doc_id, ticker, observed_label, fact_type, value, desc, quote, period_start, period_end, ptype, tier in FACTS:
        if observed_label is not None:
            mapped = map_label_to_concept(observed_label)
            if mapped != fact_type:
                mapping_mismatches += 1
                print(f"MAPPING MISMATCH {ticker} label={observed_label!r} -> "
                      f"{mapped!r}, expected {fact_type!r}")
                continue

        text_path = con.execute(
            "SELECT text_path FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")

        if quote is not None:
            g = check_grounding(quote, doc_text)
            status = "passed" if g.passed else "failed"
            if not g.passed:
                failed += 1
                print(f"GROUNDING FAILED {ticker} {fact_type} {period_end}: {g.reason}")
                continue
        else:
            status = "not_run"

        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) VALUES (?,?,?)",
            (doc_id, quote or f"[derived: {desc}]", 0.9)
        ).lastrowid
        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
            "evidence_id, extraction_confidence, model_id, prompt_version, grounding_check, "
            "extracted_at, period_start, period_end, period_type, confidence_tier, currency) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, fact_type, f"{ticker}: {desc}", value, evidence_id, 1.0, None,
             PROMPT_VERSION, status, AS_OF, period_start, period_end, ptype, tier, "NGN"),
        )
        written += 1
        print(f"written  {ticker:10s} {fact_type:12s} {value:>20,.0f}  "
              f"{period_end}  grounding={status}")

    con.commit()
    print(f"\n{written} facts written, {failed} grounding failures, "
          f"{mapping_mismatches} terminology-mapping mismatches.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
