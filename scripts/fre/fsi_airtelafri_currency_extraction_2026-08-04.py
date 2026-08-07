"""AIRTELAFRI re-extraction under MC-001 (2026-08-04), per
docs/MULTI_CURRENCY_FINANCIAL_ARCHITECTURE_REVIEW_2026-08-04.md and the
implementation authorization for Phase MC-001. Previously blocked by
docs/FSI_DEPTH_PILOT_EXECUTION_2026-08-04.md -- doc 9809 was fully read
and hand-verified clean in that pilot, but could not be written because
`extracted_facts` had no currency field and Airtel Africa plc reports in
US$ millions, not NGN. Now written with currency='USD', explicit and
grounded, using the same hand-verification methodology and
check_grounding() discipline as every other FSI extraction phase.

securities.reporting_currency='USD' was set for AIRTELAFRI directly
(confirmed via the filing's own text: "(All amounts are in US$ millions
unless stated otherwise)") before this script ran.

Run: python -u scripts/fre/fsi_airtelafri_currency_extraction_2026-08-04.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "hand_hybrid_pilot_2026-08-04"
DOC_ID = 9809
TICKER = "AIRTELAFRI"
CURRENCY = "USD"

# All figures US$ millions, FY ended 31 March 2025, per doc 9809's own
# "(All amounts are in US$ millions unless stated otherwise)" header.
# Every quote below is verbatim from data/staging/document_text/9809.txt,
# read directly in the FSI Depth Pilot (lines 948-1206).
FACTS = [
    ("revenue", 4955.0, "Revenue, FY ended 31 March 2025",
     "Revenue 5 4,955 4,979", "2025-03-31", "direct_reported"),
    ("net_profit", 328.0, "Profit for the year, FY ended 31 March 2025",
     "Profit/ (loss) for the year 328 (89)", "2025-03-31", "direct_reported"),
    ("ebit", 1457.0, "Operating profit, FY ended 31 March 2025 (EBIT proxy)",
     "Operating profit 1,457 1,640", "2025-03-31", "direct_reported"),
    ("assets", 12023.0, "Total assets, as of 31 March 2025",
     "Total assets 12,023 9,861", "2025-03-31", "direct_reported"),
    ("liabilities", 9248.0, "Total liabilities, as of 31 March 2025",
     "Total liabilities 9,248 7,561", "2025-03-31", "direct_reported"),
    ("equity", 2775.0, "Total equity, as of 31 March 2025",
     "Total equity 2,775 2,300", "2025-03-31", "direct_reported"),
    ("cfo", 2266.0, "Net cash generated from operating activities, FY2025",
     "Net cash generated from operating activities (a) 2,266 2,259",
     "2025-03-31", "direct_reported"),
    ("cfi", -562.0, "Net cash used in investing activities, FY2025",
     "Net cash used in investing activities (b) (562) (1,228)",
     "2025-03-31", "direct_reported"),
    ("cff", -1543.0, "Net cash used in financing activities, FY2025",
     "Net cash used in financing activities (c) (1,543) (844)",
     "2025-03-31", "direct_reported"),
    ("capex", -736.0,
     "Purchase of property, plant and equipment and capital work-in-progress, FY2025",
     "Purchase of property, plant and equipment and capital work-in-progress (736) (868)",
     "2025-03-31", "direct_reported"),
    # Derived, not independently stated as a single line -- same convention
    # as GEREGU's own derived fcf/ebitda in the FSI Depth Pilot.
    ("fcf", 1530.0, "Derived: cfo (2,266) - capex (736), FY2025", None,
     "2025-03-31", "derived"),
    ("ebitda", 2288.0,
     "Derived: operating profit (1,457) + depreciation and amortisation (831), FY2025",
     None, "2025-03-31", "derived"),
]


def main():
    con = db.init_db(PKG_ROOT / "data" / "ngx.sqlite")
    rc = con.execute(
        "SELECT reporting_currency FROM securities WHERE ticker=?", (TICKER,)
    ).fetchone()
    assert rc and rc[0] == CURRENCY, (
        f"securities.reporting_currency for {TICKER} must be {CURRENCY!r} "
        f"before this script writes any fact -- found {rc!r}")

    text_path = con.execute(
        "SELECT text_path FROM documents WHERE doc_id=?", (DOC_ID,)).fetchone()
    doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")

    written, grounding_failed = 0, 0
    for fact_type, value, desc, quote, period_end, tier in FACTS:
        if quote is not None:
            g = check_grounding(quote, doc_text)
            grounding_status = "passed" if g.passed else "failed"
            if not g.passed:
                grounding_failed += 1
                print(f"GROUNDING FAILED {TICKER} {fact_type}: {g.reason}")
                continue
        else:
            grounding_status = "not_run"

        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)",
            (DOC_ID, quote or f"[derived: {desc}]", 0.9)).lastrowid

        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, evidence_id, extraction_confidence, model_id, "
            "prompt_version, grounding_check, extracted_at, period_end, "
            "period_type, confidence_tier, currency) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (DOC_ID, fact_type, f"{TICKER}: {desc}", value, evidence_id,
             1.0, None, PROMPT_VERSION, grounding_status, AS_OF, period_end,
             "FY", tier, CURRENCY))
        written += 1
        print(f"written  {TICKER:12s} {fact_type:12s} {value:>10,.0f} {CURRENCY}  "
             f"grounding={grounding_status}  tier={tier}")

    con.commit()
    print(f"\n{written} facts written, {grounding_failed} grounding failures "
         f"(none written for a failed check).")


if __name__ == "__main__":
    main()
