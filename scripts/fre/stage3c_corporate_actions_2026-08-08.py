"""Stage 3C (2026-08-08) — corporate-action archive extraction.

Extracts real, sourced bonus-issue / share-reconstruction events from the
17-document `bonus_split` archive category (already harvested, see
Stage 2/docs/STAGE2_DATA_GAP_CLOSURE_2026-08-08.md Section 7). Uses the
SAME extracted_facts + evidence tables and hand-verification convention
as scripts/fre/fsi_depth_pilot_2026-08-04.py and Stage 3B — no new
schema, no new pipeline, one new taxonomy leaf (`share_reconstruction`,
already added to configs/fact_taxonomy.toml).

Every ratio here is read directly from the source document (all 8 texts
already extracted at data/staging/document_text/, no OCR needed for
these particular ones) — nothing invented. `numeric_value` stores the
PRICE ADJUSTMENT FACTOR (post-event theoretical price / pre-event price
implied by the mechanical dilution/consolidation alone): for a bonus of
`b` new shares per `h` held, factor = h/(h+b); for a reconstruction of
`n` old shares -> 1 new share, factor = n. This is the single number a
future price-adjustment layer would need; the raw ratio is preserved in
`description` for full transparency and independent verification.

CILEASING and LASACO were already confirmed in Stage 2 (read by hand from
the same archive); included here for the first time as STRUCTURED,
queryable facts rather than only prose in a report.

Run: python -u scripts/fre/stage3c_corporate_actions_2026-08-08.py
"""
from datetime import date
from pathlib import Path

from ngxrot import db
from ngxrot.documents.grounding import check_grounding

PKG_ROOT = Path(__file__).resolve().parents[2]
AS_OF = date.today().isoformat()
PROMPT_VERSION = "stage3c_hand_2026-08-08"

# (doc_id, ticker, fact_type, price_factor, description, quote,
#  qualification_date, closure_date, tier)
FACTS = [
    (7837, "CILEASING", "bonus_issue", 0.6,
     "2-for-3 bonus (2 new ordinary shares for every 3 held); price "
     "adjustment factor = 3/5 = 0.60. CONFIRMED — matches the observed "
     "2024-01-05 price move (5.13->3.38, ratio 0.659) within expected "
     "range of a mechanical markdown plus real market movement.",
     "A Bonus issue of two (2) ordinary shares for every three (3) ordinary shares held",
     "2024-01-04", "2024-01-05", "direct_reported"),

    (4513, "LASACO", "share_reconstruction", 4.0,
     "1-for-4 share reconstruction (consolidation): one new ordinary "
     "share for every four previously held; price adjustment factor = "
     "4.0. Trading suspended 2021-02-01 to 2021-02-12 per this notice "
     "(actual resumption in price data was 2021-02-22). CONFIRMED — "
     "matches the observed jump (0.42->1.52, ratio 3.62) within expected "
     "range.",
     "reconstruct its issued and fully paid-up Share Capital",
     None, "2021-02-01", "direct_reported"),

    (6682, "NB", "bonus_issue", 0.8,
     "1-for-4 bonus (1 new share for every 4 held); price adjustment "
     "factor = 4/5 = 0.80. CONFIRMED EXECUTED — doc 6997 (same ticker, "
     "2023-03-13) confirms SEC registered 2,055,226,476 bonus shares and "
     "credited shareholders on this exact basis.",
     "Proposed Bonus 1 (one) new share for every 4 (four) shares",
     "2022-12-06", "2022-12-07", "direct_reported"),

    (8390, "CHAMPION", "bonus_issue", 0.875,
     "1-for-7 bonus (1 new share for every 7 held); price adjustment "
     "factor = 7/8 = 0.875. Same standardized NGX corporate-actions "
     "announcement format as CILEASING/NB.",
     "Proposed Bonus 1 (one) new share for every 7 (seven) shares",
     "2024-05-10", "2024-05-13", "direct_reported"),

    (4000, "CHIPLC", "bonus_issue", 0.9375,
     "1-for-15 bonus (1 new share for every 15 held), 677,500,000 shares "
     "from retained earnings. PROPOSED ONLY as of this document — a "
     "board resolution explicitly 'subject to the approval of the "
     "Regulator(s) and the shareholders at the forthcoming AGM', not yet "
     "confirmed executed. Lower confidence than the others in this batch.",
     "distributed at the ratio of one (1) new share for every fifteen",
     None, "2020-08-19", "mapped_equivalent"),

    (5531, "NEM", "share_reconstruction", 2.0,
     "2-for-1 share reconsolidation (every 2 shares held -> 1 share; "
     "nominal value N0.50 -> N1.00); price adjustment factor = 2.0. "
     "Trading suspended 2021-12-10 to 2021-12-23. This is the real "
     "mechanism behind the previously-narrative-only 'fact_id 27' bonus "
     "note in docs/METHODOLOGY_HARDENING_2026-08-04.md (AGM 2021-06-24) "
     "-- it is a reconsolidation, not a bonus issue; recorded here under "
     "the correct taxonomy leaf.",
     "consolidation of every two (2) shares held by each shareholder into",
     None, "2021-12-10", "direct_reported"),

    (9057, "TRANSCORP", "share_reconstruction", 4.0,
     "4-for-1 share reconsolidation (40.6bn issued shares -> 10.2bn); "
     "price adjustment factor = 4.0. CONFIRMED EXECUTED -- this document "
     "is a post-completion press release, not a proposal (dated "
     "2024-10-28, 'has announced the successful completion').",
     "consolidation of the total number of issued shares at a ratio of 1 to 4",
     None, None, "direct_reported"),

    (6930, "ENAMELWA", "bonus_issue", 1.0,
     "[PROPOSED THEN CANCELLED -- NO PRICE ADJUSTMENT SHOULD BE APPLIED, "
     "numeric_value=1.0 is a deliberate no-op, not a measured factor] "
     "3-for-2 bonus proposed 2023-02-28 (qualification date 2023-03-13), "
     "explicitly cancelled by the company's own notice dated 2023-03-09 "
     "(doc 6987) before the qualification date was ever reached.",
     "Proposed Divldend 3 new shores for every 2 shores held",
     "2023-03-13", None, "direct_reported"),
]


def main():
    con = db.init_db(PKG_ROOT / "data" / "ngx.sqlite")
    written, grounding_failed = 0, 0
    for (doc_id, ticker, fact_type, value, desc, quote, qual_date,
         closure_date, tier) in FACTS:
        text_path = con.execute(
            "SELECT text_path FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        doc_text = Path(text_path[0]).read_text(encoding="utf-8", errors="replace")

        g = check_grounding(quote, doc_text)
        grounding_status = "passed" if g.passed else "failed"
        if not g.passed:
            grounding_failed += 1
            print(f"GROUNDING FAILED {ticker} {fact_type}: {g.reason}")
            continue

        evidence_id = con.execute(
            "INSERT INTO evidence (doc_id, quoted_text, source_confidence) "
            "VALUES (?,?,?)", (doc_id, quote, 0.9)).lastrowid

        con.execute(
            "INSERT INTO extracted_facts (doc_id, fact_type, description, "
            "numeric_value, qualification_date, closure_date, evidence_id, "
            "extraction_confidence, model_id, prompt_version, "
            "grounding_check, extracted_at, confidence_tier) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, fact_type, f"{ticker}: {desc}", value, qual_date,
             closure_date, evidence_id, 1.0, None, PROMPT_VERSION,
             grounding_status, AS_OF, tier))
        written += 1
        print(f"written  {ticker:10s} {fact_type:20s} factor={value}  "
             f"qual={qual_date}  closure={closure_date}  tier={tier}")

    con.commit()
    print(f"\n{written} facts written, {grounding_failed} grounding failures.")


if __name__ == "__main__":
    main()
