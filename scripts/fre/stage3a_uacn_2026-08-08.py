"""Stage 3A (2026-08-08) — first new-ticker FSI extraction of this round.

UACN was the top-ranked target in the Stage 3A queue: highest
results_notice document count (27) among IRU names not yet in the
13-ticker FSI set, with real financial-statement text (not a procedural
notice, unlike SEPLAT — see docs/STAGE3_EXECUTION_2026-08-08.md Section
2's "document count is not document usefulness" finding).

Doc 5163 (H1 2021 earnings release) has clean, exact tabular revenue/
gross-profit/net-profit figures. It does NOT include a balance sheet or
cash-flow statement (a P&L-only interim press release) — recorded
honestly as such, not padded with an estimate. `ebit` is skipped: only
rounded narrative figures ("~N1.7 billion") exist for Operating Profit,
not an exact table line, and this pipeline's own established convention
(see AFRIPRUD's disclosed precision caveats) is to not extract a fact at
narrative-only precision.

Run: python -u scripts/fre/stage3a_uacn_2026-08-08.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "stage3a_hand_2026-08-08"

FACTS = [
    (5163, "UACN", "revenue", 46499000000.0,
     "Revenue, H1 2021 (table N'm x1e6)",
     "Revenue 24,478 17,085 43.3% 46,499 36,633 26.9%", "2021-06-30", "H1", "direct_reported"),
    (5163, "UACN", "gross_profit", 8324000000.0,
     "Gross Profit, H1 2021 (table N'm x1e6)",
     "Gross Profit 4,313 2,759 56.3% 8,324 6,993 19.0%", "2021-06-30", "H1", "direct_reported"),
    (5163, "UACN", "net_profit", 763000000.0,
     "Profit for the period (total, incl. discontinued operations), H1 2021 "
     "(table N'm x1e6). METRIC MAPPING JUDGMENT: distinct from this "
     "filing's separately-narrated 'profit after tax from CONTINUING "
     "operations' of N765m -- net_profit here uses the TOTAL bottom-line "
     "table figure, consistent with every other ticker's net_profit "
     "convention on this platform.",
     "Profit for the period 94 (684) n/m 763 1,158 (34.1%)", "2021-06-30", "H1", "direct_reported"),
]


def main():
    con = db.init_db(PKG_ROOT / "data" / "ngx.sqlite")
    written, failed = 0, 0
    for doc_id, ticker, ftype, value, desc, quote, period_end, ptype, tier in FACTS:
        text_path = con.execute(
            "SELECT text_path FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")
        g = check_grounding(quote, doc_text)
        status = "passed" if g.passed else "failed"
        if not g.passed:
            failed += 1
            print(f"GROUNDING FAILED {ticker} {ftype}: {g.reason}")
            continue
        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)", (doc_id, quote, 0.9)).lastrowid
        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, evidence_id, extraction_confidence, model_id, "
            "prompt_version, grounding_check, extracted_at, period_end, "
            "period_type, confidence_tier) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, ftype, f"{ticker}: {desc}", value, evidence_id, 1.0,
             None, PROMPT_VERSION, status, AS_OF, period_end, ptype, tier))
        written += 1
        print(f"written  {ticker:6s} {ftype:12s} {value:>15,.0f}  grounding={status}")
    con.commit()
    print(f"\n{written} facts written, {failed} grounding failures.")


if __name__ == "__main__":
    main()
