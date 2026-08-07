"""FSI Depth Pilot (2026-08-04), per docs/FSI_OWNER_DECISION_PACKAGE_2026-08-03.md
and the explicit owner instruction to execute it. Hybrid deterministic +
human-verification extraction on 3 previously-identified high-quality
candidate filings (AIRTELAFRI, LASACO, GEREGU -- the highest tabular-
row-count `results_notice` documents from
docs/FSI_DEPTH_SCOPING_AUDIT_2026-08-03.md's own Section 6.2 finding,
none previously in the 10-ticker extracted set).

This is NOT an LLM-drafted extraction (no ngxrot.documents.extract call)
-- every fact below was read and transcribed by hand from the actual
document text, cross-checked internally (statement-level arithmetic
identities), and is written here with extraction_confidence=1.0,
model_id=None, matching the platform's existing hand-verification
convention from FSI Phases 1/2/13. Every quoted_text is checked against
the real source file via the same check_grounding() used by the LLM
pipeline, not assumed to pass.

Run: python -u scripts/fre/fsi_depth_pilot_2026-08-04.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "hand_hybrid_pilot_2026-08-04"

# (doc_id, ticker, fact_type, numeric_value_ngn_thousands, description,
#  quoted_text, period_end, confidence_tier)
FACTS = [
    # --- LASACO (doc 7194, FY2022, all figures N'000) ---
    (7194, "LASACO", "net_profit", 1478894.0,
     "Profit for the year, FY2022",
     "Profit for the year 1,478,894 261,384", "2022-12-31", "direct_reported"),
    (7194, "LASACO", "assets", 26102029.0,
     "Total Assets, as at 31 Dec 2022",
     "Total Assets 26,102,029 23,958,247", "2022-12-31", "direct_reported"),
    (7194, "LASACO", "liabilities", 13113991.0,
     "Total Liabilities, as at 31 Dec 2022",
     "Total Liabilities 13,113,991 12,649,564", "2022-12-31", "direct_reported"),
    (7194, "LASACO", "equity", 12988038.0,
     "Shareholders' Funds, as at 31 Dec 2022",
     "Shareholders' Funds 12,988,038 11,308,683", "2022-12-31", "direct_reported"),
    (7194, "LASACO", "cfo", 542774.0,
     "Net cash generated from operating activities, FY2022",
     "Net cash generated/(absorbed) from operating activities 43 542,774 (216,618)",
     "2022-12-31", "direct_reported"),
    (7194, "LASACO", "cfi", -566309.0,
     "Net cash outflow from investing activities, FY2022",
     "Net cash (outflow)/inflow from investing activities (566,309) 1,326,310",
     "2022-12-31", "direct_reported"),
    (7194, "LASACO", "cff", 0.0,
     "Net cash from financing activities, FY2022 (explicit nil)",
     "Net cash inflow from financing activities - 2,916,641",
     "2022-12-31", "direct_reported"),

    # --- GEREGU (doc 6555, FY2021, all figures N'000) ---
    (6555, "GEREGU", "revenue", 70956864.0,
     "Revenue, FY2021", "Revenue 6. 70,956,864 53,676,666",
     "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "net_profit", 20550411.0,
     "Profit for the year from continuing operations, FY2021",
     "Profit for the year from continuing operations 20,550,411 14,125,357",
     "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "assets", 114821313.0,
     "Total assets, as at 31 Dec 2021",
     "Total assets 114,821,313 123,066,972", "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "liabilities", 54882678.0,
     "Total liabilities, as at 31 Dec 2021",
     "Total liabilities 54,882,678 46,093,950", "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "equity", 59938635.0,
     "Total equity, as at 31 Dec 2021",
     "Total equity 59,938,635 76,973,022", "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "cfo", 32907956.0,
     "Net cash from operating activities, FY2021",
     "Net cash from operating activities 32,907,956 2,929,713",
     "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "cfi", -634585.0,
     "Net cash from investing activities, FY2021",
     "Net cash from investing activities (634,585) 1,350,003",
     "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "cff", -33101275.0,
     "Net cash used in financing activities, FY2021",
     "Net cash used in financing activities (33,101,275) (683,644)",
     "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "capex", -599353.0,
     "Purchase of property, plant and equipment, FY2021",
     "Purchase of property, plant and equipment 13. (599,353) (173,569)",
     "2021-12-31", "direct_reported"),
    (6555, "GEREGU", "ebit", 29523435.0,
     "Operating profit, FY2021 (EBIT proxy)",
     "Operating profit 29,523,435 19,103,807", "2021-12-31", "direct_reported"),
    # Derived facts -- NOT independently stated as a single line; computed
    # per configs/fact_taxonomy.toml's own fcf convention (cfo - capex,
    # always confidence_tier="derived"). ebitda is derived here for the
    # same reason (no single stated EBITDA line existed in this filing) --
    # an extension of that convention, disclosed as such in the pilot
    # report, not a taxonomy change.
    (6555, "GEREGU", "fcf", 32308603.0,
     "Derived: cfo (32,907,956) - capex (599,353), FY2021", None,
     "2021-12-31", "derived"),
    (6555, "GEREGU", "ebitda", 34141258.0,
     "Derived: operating profit (29,523,435) + depreciation (4,611,308) "
     "+ amortization (6,515), FY2021", None, "2021-12-31", "derived"),
]


def main():
    con = db.init_db(PKG_ROOT / "data" / "ngx.sqlite")
    written, grounding_failed = 0, 0
    for doc_id, ticker, fact_type, value, desc, quote, period_end, tier in FACTS:
        text_path = con.execute(
            "SELECT text_path FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")

        if quote is not None:
            g = check_grounding(quote, doc_text)
            grounding_status = "passed" if g.passed else "failed"
            if not g.passed:
                grounding_failed += 1
                print(f"GROUNDING FAILED {ticker} {fact_type}: {g.reason}")
                continue
        else:
            grounding_status = "not_run"  # derived fact, no direct quote to ground

        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)",
            (doc_id, quote or f"[derived: {desc}]", 0.9)).lastrowid

        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, evidence_id, extraction_confidence, model_id, "
            "prompt_version, grounding_check, extracted_at, period_end, "
            "period_type, confidence_tier) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, fact_type, f"{ticker}: {desc}", value, evidence_id,
             1.0, None, PROMPT_VERSION, grounding_status, AS_OF, period_end,
             "FY", tier))
        written += 1
        print(f"written  {ticker:12s} {fact_type:12s} {value:>15,.0f}  "
             f"grounding={grounding_status}  tier={tier}")

    con.commit()
    print(f"\n{written} facts written, {grounding_failed} grounding failures "
         f"(none written for a failed check).")


if __name__ == "__main__":
    main()
