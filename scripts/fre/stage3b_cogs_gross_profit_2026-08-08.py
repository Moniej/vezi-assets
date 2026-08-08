"""Stage 3B (2026-08-08) — COGS/Gross Profit extraction.

Adds exactly two fact_types (cogs, gross_profit) to
configs/fact_taxonomy.toml's [financial_statements] leaf (already done,
see that file's own Stage 3B comment) and extracts real values from
filings ALREADY open and hand-verified by the FSI Phase 1 pilot and the
2026-08-04 depth pilot — no new document acquisition, no new tickers.

Same hand-verification convention as scripts/fre/fsi_depth_pilot_2026-08-04.py:
every quote is checked against the real source text via check_grounding();
nothing is written if grounding fails. `cogs` is direct_reported wherever
a "Cost of Sales"/"Cost of sales" line is explicitly stated; two CAP
periods state Gross Profit directly but never break out Cost of Sales as
its own line — for those, cogs = revenue - gross_profit is recorded as
confidence_tier='derived' (a pure accounting identity, not an assumption,
matching the platform's own existing fcf/ebitda derivation convention).

Units: this script keeps EACH TICKER's OWN existing numeric_value scale
(see docs/STAGE3_EXECUTION_2026-08-08.md Section 3 for the platform-wide
inconsistency this exposed — GEREGU stores raw thousands, unconverted;
every other ticker here converts to full naira) rather than "fixing" it,
since a silent rescale would corrupt every existing GEREGU ratio
downstream. Disclosed, not fixed, per Stage 3's bounded scope.

Run: python -u scripts/fre/stage3b_cogs_gross_profit_2026-08-08.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "stage3b_hand_2026-08-08"

# (doc_id, ticker, fact_type, value, description, quote, period_end,
#  period_type, tier)
FACTS = [
    # --- GEREGU (doc 6555, FY2021) — raw thousands, matching this
    # ticker's own existing unconverted convention ---
    (6555, "GEREGU", "cogs", -37614052.0,
     "Cost of sales, FY2021 (raw N'000, unconverted — matches this "
     "ticker's own existing revenue/net_profit convention)",
     "Cost of sales (37,614,052) (30,835,415)", "2021-12-31", "FY", "direct_reported"),
    (6555, "GEREGU", "gross_profit", 33342812.0,
     "Gross profit, FY2021 (raw N'000, unconverted)",
     "Gross profit 33,342,812 22,841,251", "2021-12-31", "FY", "direct_reported"),

    # --- NASCON (docs 8801/9460/10929) — table in N'mn, x1e6 to match
    # this ticker's own existing revenue/net_profit convention ---
    (8801, "NASCON", "cogs", -28408000000.0,
     "Cost of sales, H1 2024 (table N'mn x1e6)",
     "Cost of sales (28,408) (19,204) 48%", "2024-06-30", "H1", "direct_reported"),
    (8801, "NASCON", "gross_profit", 22024000000.0,
     "Gross profit, H1 2024 (table N'mn x1e6)",
     "Gross profit 22,024 18,961 16%", "2024-06-30", "H1", "direct_reported"),
    (9460, "NASCON", "cogs", -64860000000.0,
     "Cost of sales, FY2024 (table N'mn x1e6)",
     "Cost of sales (64,860) (36,510) 78%", "2024-12-31", "FY", "direct_reported"),
    (9460, "NASCON", "gross_profit", 55527000000.0,
     "Gross profit, FY2024 (table N'mn x1e6)",
     "Gross profit 55,527 44,319 25%", "2024-12-31", "FY", "direct_reported"),
    (10929, "NASCON", "cogs", -78739000000.0,
     "Cost of sales, FY2025 (table N'mn x1e6)",
     "Cost of sales (78,739) (64,860) 21%", "2025-12-31", "FY", "direct_reported"),
    (10929, "NASCON", "gross_profit", 73948000000.0,
     "Gross profit, FY2025 (table N'mn x1e6)",
     "Gross profit 73,948 55,527 33%", "2025-12-31", "FY", "direct_reported"),

    # --- BUAFOODS (docs 6664/8009/9357) — table in N'000, x1000 to
    # match this ticker's own existing revenue/net_profit convention ---
    (6664, "BUAFOODS", "cogs", -195641326000.0,
     "Cost of Sales, 9M 2022 (table N'000 x1000)",
     "Cost of Sales 195,641,326 158,825,185 23.2% 159,203,255 109,825,155 45.0%",
     "2022-09-30", "9M", "direct_reported"),
    (6664, "BUAFOODS", "gross_profit", 94178499000.0,
     "Gross Profit, 9M 2022 (table N'000 x1000)",
     "Gross Profit 94,178,499 82,253,444 14.5% 62,447,138 56,176,674 11.2%",
     "2022-09-30", "9M", "direct_reported"),
    (8009, "BUAFOODS", "cogs", -477147433000.0,
     "Cost of Sales, FY2023 (table N'000 x1000)",
     "Cost of Sales 477,147,433 285,555,236 67%", "2023-12-31", "FY", "direct_reported"),
    (8009, "BUAFOODS", "gross_profit", 251329672000.0,
     "Gross Profit, FY2023 (table N'000 x1000)",
     "Gross Profit 251,329,672 132,792,534 89%", "2023-12-31", "FY", "direct_reported"),
    (9357, "BUAFOODS", "cogs", -984975683000.0,
     "Cost of Sales, FY2024 (table N'000 x1000)",
     "Cost of Sales 984,975,683 468,983,756 110%", "2024-12-31", "FY", "direct_reported"),
    (9357, "BUAFOODS", "gross_profit", 541708860000.0,
     "Gross Profit, FY2024 (table N'000 x1000)",
     "Gross Profit 541,708,860 260,459,599 108%", "2024-12-31", "FY", "direct_reported"),

    # --- CAP (docs 5911/10115) — table in N'mn, x1e6. No stated Cost of
    # Sales line in either filing; cogs is DERIVED (revenue - gross_profit,
    # an accounting identity) and marked as such. ---
    (5911, "CAP", "gross_profit", 4558000000.0,
     "Gross Profit, FY2021 (table N'mn x1e6)",
     "Gross Profit 4,558 3,742 22%", "2021-12-31", "FY", "direct_reported"),
    (5911, "CAP", "cogs", -9650000000.0,
     "Derived: revenue (14,208) - gross_profit (4,558), FY2021, N'mn x1e6 "
     "— this filing never states a Cost of Sales line", None,
     "2021-12-31", "FY", "derived"),
    (10115, "CAP", "gross_profit", 8719000000.0,
     "Gross Profit, H1 2025 (table N'mn x1e6)",
     "Gross Profit 4,316 2,521 71% 8,719 5,563 57%", "2025-06-30", "H1", "direct_reported"),
    (10115, "CAP", "cogs", -11374000000.0,
     "Derived: revenue (20,093) - gross_profit (8,719), H1 2025, N'mn x1e6 "
     "— this filing never states a Cost of Sales line", None,
     "2025-06-30", "H1", "derived"),

    # --- AFRIPRUD (doc 7540) — table in N'000, x1000, matching this
    # ticker's own existing convention ---
    (7540, "AFRIPRUD", "cogs", -554433000.0,
     "Cost of Sales, H1 2023 (table N'000 x1000) — AFRIPRUD is a share "
     "registrar; a stated 'Cost of Sales' line in this filing refers to "
     "direct registrar-service costs, not a manufacturing COGS concept",
     "Cost of Sales -554,433 -152,592", "2023-06-30", "H1", "direct_reported"),
    (7540, "AFRIPRUD", "gross_profit", 658382000.0,
     "Gross profit, H1 2023 (table N'000 x1000)",
     "Gross profit 658,382 775,518", "2023-06-30", "H1", "direct_reported"),
]


def main():
    con = db.init_db(PKG_ROOT / "data" / "ngx.sqlite")
    written, grounding_failed = 0, 0
    for doc_id, ticker, fact_type, value, desc, quote, period_end, period_type, tier in FACTS:
        text_path = con.execute(
            "SELECT text_path FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")

        if quote is not None:
            g = check_grounding(quote, doc_text)
            grounding_status = "passed" if g.passed else "failed"
            if not g.passed:
                grounding_failed += 1
                print(f"GROUNDING FAILED {ticker} {fact_type} {period_end}: {g.reason}")
                continue
        else:
            grounding_status = "not_run"

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
             period_type, tier))
        written += 1
        print(f"written  {ticker:10s} {fact_type:14s} {value:>18,.0f}  "
             f"{period_end}  grounding={grounding_status}  tier={tier}")

    con.commit()
    print(f"\n{written} facts written, {grounding_failed} grounding failures "
         f"(none written for a failed check).")


if __name__ == "__main__":
    main()
