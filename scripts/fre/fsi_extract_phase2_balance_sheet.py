"""FSI Phase 2, Stage 2: Balance Sheet Intelligence
(docs/fre_runs/fsi_phase2_execution_plan.md, docs/fre_runs/
fsi_phase2_implementation_log.md). Writes assets/liabilities/equity facts
for the 15 real Phase 1 filings, using the shared infrastructure
(period_normalization, terminology_mapping, restatement_detection) built
in Stage 1.

Every figure below was re-read directly from the real archived filing
text (data/staging/document_text/<doc_id>.txt), the same discipline as
Phase 1. Two real, disclosed findings from this reading:

  - CAP's FY2020 filing (doc 4508) has NO extractable balance-sheet
    absolute figures at all -- only a leverage RATIO ("Total Assets /
    Equity: 2.3x / 2.7x") is given, no absolute Naira amounts. This is a
    genuine document-content limitation, not an extraction failure --
    no fact is written for this doc_id/fact_type combination, and this
    is disclosed here rather than silently skipped with no trace.
  - AFRIPRUD's 2020 filing (doc 4245) has a real PDF-to-text line-wrap
    artifact: "TOTAL LIABILITIES"/"TOTAL EQUITY" each appear on their own
    line, with the two comparative-period values wrapped onto the
    following line in an order that does NOT match the stated column
    headers ("30-September-20 31-December-19"). Resolved by cross-
    referencing the filing's own narrative highlights bullets (e.g.
    "Total Liabilities: N11.11 Billion... N10.37 Billion as at FY 2019"),
    and INDEPENDENTLY CONFIRMED by the accounting identity itself
    (11,109,828 + 8,269,150 = 19,378,978, an EXACT match to the cleanly
    -stated TOTAL ASSETS figure) -- the identity match is strong evidence
    the disambiguation is correct, not merely a guess.

Every other filing's balance-sheet triple is a clean, unambiguous read,
independently confirmed by the accounting identity (assets = liabilities
+ equity) holding exactly or within trivial (<=N1mn) rounding in every
case -- a real, positive validation result this stage was specifically
designed to be able to produce (docs/fre_runs/fsi_phase2_execution_plan.md
section 5).

  PYTHONPATH=src python scripts/fre/fsi_extract_phase2_balance_sheet.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_extract_phase2_balance_sheet.py --apply    # writes for real
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.period_normalization import classify_period_type  # noqa: E402
from ngxrot.fre.restatement_detection import find_restatement_conflicts  # noqa: E402
from ngxrot.fre.terminology_mapping import map_label_to_concept  # noqa: E402

STAGE = "balance_sheet"

# Each entry: one filing's balance-sheet triple, as literally read from
# the source filing text. observed_label is the EXACT label the source
# document used (fed through terminology_mapping for provenance, per the
# "no silent metric substitution" constraint) -- None means "no data for
# this doc" (CAP 4508's disclosed gap).
FACTS = [
    dict(doc_id=4248, ticker="UCAP", period_start="2020-01-01", period_end="2020-09-30",
         assets=211_525_338_000, liabilities=191_447_532_000, equity=20_077_806_000,
         label_assets="TOTAL ASSETS", label_liabilities="TOTAL LIABILITIES", label_equity="TOTAL SHAREHOLDERS' FUND",
         note="clean, unambiguous single-line table; cross-validated against highlights narrative"),
    dict(doc_id=6911, ticker="UCAP", period_start="2022-01-01", period_end="2022-12-31",
         assets=601_915_211_000, liabilities=568_927_920_000, equity=32_987_291_000,
         label_assets="TOTAL ASSETS", label_liabilities="TOTAL LIABILITIES", label_equity="TOTAL SHAREHOLDERS FUND",
         note="clean, unambiguous single-line table; cross-validated against highlights narrative"),
    dict(doc_id=10772, ticker="UCAP", period_start="2025-01-01", period_end="2025-12-31",
         assets=1_761_337_130_000, liabilities=1_611_340_186_000, equity=149_996_944_000,
         label_assets="TOTAL ASSETS", label_liabilities="TOTAL LIABILITIES", label_equity="TOTAL SHAREHOLDERS FUND",
         note="clean, unambiguous single-line table; cross-validated against highlights table (N'bn figures) and narrative"),
    dict(doc_id=6664, ticker="BUAFOODS", period_start="2022-01-01", period_end="2022-09-30",
         assets=630_397_972_000, liabilities=423_918_046_000, equity=206_479_925_000,
         label_assets="Total assets", label_liabilities="Total liabilities", label_equity="Total equity",
         note="Group column of the compact 'Key Financial Highlights' table; cross-validated against body-prose narrative restatement"),
    dict(doc_id=8009, ticker="BUAFOODS", period_start="2023-01-01", period_end="2023-12-31",
         assets=734_071_883_000, liabilities=472_573_707_000, equity=261_498_176_000,
         label_assets="Total assets", label_liabilities="Total liabilities", label_equity="Total equity",
         note="Group column of the compact highlights table; cross-validated against narrative"),
    dict(doc_id=9357, ticker="BUAFOODS", period_start="2024-01-01", period_end="2024-12-31",
         assets=1_056_872_234_000, liabilities=618_867_421_000, equity=438_004_813_000,
         label_assets="Total Assets", label_liabilities="Total Liabilities", label_equity="Total Equity",
         note="THREE-WAY cross-validated: compact highlights table + narrative prose + a separate, "
              "cleanly-extracted detailed 'Statement of Financial Position' table (unlike this same "
              "filing's P&L table, which was garbled, per Phase 1's finding -- the balance-sheet table "
              "in this specific document extracted cleanly)"),
    dict(doc_id=4245, ticker="AFRIPRUD", period_start="2020-01-01", period_end="2020-09-30",
         assets=19_378_978_000, liabilities=11_109_828_000, equity=8_269_150_000,
         label_assets="TOTAL ASSETS", label_liabilities="TOTAL LIABILITIES", label_equity="TOTAL EQUITY",
         note="REAL NUMERICAL EXTRACTION DIFFICULTY: TOTAL LIABILITIES/TOTAL EQUITY each extracted with "
              "their two comparative-period values wrapped onto a separate line, in an order that does "
              "NOT match the stated column headers. Resolved via the filing's own narrative highlights "
              "bullets, and independently confirmed correct by the accounting identity itself "
              "(11,109,828 + 8,269,150 = 19,378,978, an exact match to the cleanly-stated TOTAL ASSETS)"),
    dict(doc_id=6349, ticker="AFRIPRUD", period_start="2022-01-01", period_end="2022-06-30",
         assets=38_178_545_000, liabilities=29_488_005_000, equity=8_690_540_000,
         label_assets="TOTAL ASSESTS", label_liabilities="TOTAL LIABILITIES", label_equity="TOTAL EQUITY",
         note="clean, unambiguous single-line table (unlike doc 4245); cross-validated against highlights "
              "narrative. Note the real, verbatim source typo 'TOTAL ASSESTS' (sic), kept literal per "
              "configs/financial_statement_terminology.toml's own disclosed note"),
    dict(doc_id=7540, ticker="AFRIPRUD", period_start="2023-01-01", period_end="2023-06-30",
         assets=20_477_166_000, liabilities=11_550_671_000, equity=8_926_495_000,
         label_assets="TOTAL ASSETS", label_liabilities="TOTAL LIABILITIES", label_equity="TOTAL EQUITY",
         note="clean, unambiguous single-line table; cross-validated against both the compact highlights "
              "table (N'mn figures) and narrative bullets"),
    dict(doc_id=4508, ticker="CAP", period_start="2020-01-01", period_end="2020-12-31",
         assets=None, liabilities=None, equity=None,
         label_assets=None, label_liabilities=None, label_equity=None,
         note="NO extractable balance-sheet absolute figures exist in this filing -- only a leverage "
              "ratio ('Total Assets / Equity: 2.3x / 2.7x') is disclosed, no absolute Naira amounts. "
              "A genuine document-content limitation, disclosed rather than silently skipped; no fact "
              "is written for this doc_id/metric combination."),
    dict(doc_id=5911, ticker="CAP", period_start="2021-01-01", period_end="2021-12-31",
         assets=12_116_000_000, liabilities=7_706_000_000, equity=4_410_000_000,
         label_assets="Total Assets", label_liabilities="Total Liabilities", label_equity="Equity",
         note="clean, unambiguous table; accounting identity holds EXACTLY (7,706 + 4,410 = 12,116mn); "
              "no separate narrative restatement of these absolute figures exists in this filing, so "
              "validation here rests on the identity check rather than a second independent narrative source"),
    dict(doc_id=10115, ticker="CAP", period_start="2025-01-01", period_end="2025-06-30",
         assets=20_424_000_000, liabilities=9_213_000_000, equity=11_211_000_000,
         label_assets="Total Assets", label_liabilities="Total Liabilities", label_equity="Equity",
         note="clean, unambiguous table; accounting identity holds EXACTLY (9,213 + 11,211 = 20,424mn); "
              "same single-source-plus-identity-check validation as doc 5911"),
    dict(doc_id=8801, ticker="NASCON", period_start="2024-01-01", period_end="2024-06-30",
         assets=84_784_000_000, liabilities=52_468_000_000, equity=32_317_000_000,
         label_assets="Total Assets", label_liabilities="Total Liabilities", label_equity="Total Equity",
         note="clean, unambiguous table; accounting identity holds within N1mn rounding "
              "(52,468 + 32,317 = 84,785mn vs. stated 84,784mn) -- a trivial, disclosed rounding "
              "difference from independently-rounded table components, not a real conflict"),
    dict(doc_id=9460, ticker="NASCON", period_start="2024-01-01", period_end="2024-12-31",
         assets=78_502_000_000, liabilities=35_447_000_000, equity=43_055_000_000,
         label_assets="Total Assets", label_liabilities="Total Liabilities", label_equity="Total Equity",
         note="clean, unambiguous table; accounting identity holds EXACTLY; cross-validated against "
              "the highlights bullet 'Total assets up 20% at N78.5B'"),
    dict(doc_id=10929, ticker="NASCON", period_start="2025-01-01", period_end="2025-12-31",
         assets=135_266_000_000, liabilities=64_086_000_000, equity=71_180_000_000,
         label_assets="Total Assets", label_liabilities="Total Liabilities", label_equity="Total Equity",
         note="clean, unambiguous table; accounting identity holds EXACTLY"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase2_balance_sheet_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("extracted_facts", "evidence", "documents")}

    now = datetime.now(timezone.utc).isoformat()
    written = 0
    skipped_no_data = 0
    identity_checks = []

    for entry in FACTS:
        if entry["assets"] is None:
            skipped_no_data += 1
            print(f"doc={entry['doc_id']} ticker={entry['ticker']}: SKIPPED, no balance-sheet "
                  f"data in this filing ({entry['note'][:60]}...)")
            continue

        period_type = classify_period_type(entry["period_start"], entry["period_end"])
        identity_diff = entry["liabilities"] + entry["equity"] - entry["assets"]
        identity_note = (
            f"accounting identity check: liabilities+equity-assets = {identity_diff:,.0f} "
            f"({'EXACT' if identity_diff == 0 else 'within rounding' if abs(identity_diff) <= 2_000_000 else 'MISMATCH -- FLAG FOR REVIEW'})"
        )
        identity_checks.append((entry["doc_id"], identity_diff))

        for metric, value, label in [
            ("assets", entry["assets"], entry["label_assets"]),
            ("liabilities", entry["liabilities"], entry["label_liabilities"]),
            ("equity", entry["equity"], entry["label_equity"]),
        ]:
            mapped_concept = map_label_to_concept(label)
            assert mapped_concept == metric, f"terminology mapping mismatch for doc {entry['doc_id']}: {label!r} -> {mapped_concept!r}, expected {metric!r}"
            confidence_tier = "direct_reported"  # every value here is a literal stated figure, never derived

            restatement_conflicts = find_restatement_conflicts(
                con, entry["ticker"], metric, entry["period_start"], entry["period_end"], float(value)
            ) if args.apply else []

            description = (
                f"{entry['ticker']} {metric} for period {entry['period_start']} to {entry['period_end']} "
                f"(period_type={period_type}): NGN {value:,}. Source label: '{label}' (mapped via "
                f"configs/financial_statement_terminology.toml). Confidence tier: {confidence_tier}. "
                f"{identity_note}. {entry['note']}. FSI Phase 2 pilot extraction, stage={STAGE}, "
                f"manually read and cross-checked against the archived filing's own text (no external "
                f"/vendor source used)."
            )
            print(f"{'[DRY RUN] ' if not args.apply else ''}doc={entry['doc_id']} ticker={entry['ticker']} "
                  f"metric={metric} value={value:,} tier={confidence_tier} period_type={period_type} "
                  f"restatement_conflicts={restatement_conflicts}")

            if args.apply:
                cur = con.execute(
                    "INSERT INTO evidence (doc_id, quoted_text, page_number, char_start, char_end, "
                    "source_confidence) VALUES (?,?,?,?,?,?)",
                    (entry["doc_id"], f"Source label '{label}' -> {value:,} (NGN)", None, None, None, 0.85),
                )
                evidence_id = cur.lastrowid
                con.execute(
                    "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
                    "period_start, period_end, period_type, confidence_tier, restates_fact_id, "
                    "evidence_id, extraction_confidence, model_id, prompt_version, grounding_check, "
                    "extracted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (entry["doc_id"], metric, description, float(value), entry["period_start"],
                     entry["period_end"], period_type, confidence_tier,
                     restatement_conflicts[0] if restatement_conflicts else None,
                     evidence_id, 0.9, None, None, "passed", now),
                )
                written += 1

    if args.apply:
        con.commit()

    after_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("extracted_facts", "evidence", "documents")}
    print(f"\nBefore: {before_counts}")
    print(f"After:  {after_counts}")
    print(f"documents count unchanged: {before_counts['documents'] == after_counts['documents']}")
    print(f"filings with no balance-sheet data (disclosed, skipped): {skipped_no_data}")
    print(f"accounting-identity checks: {identity_checks}")
    if args.apply:
        print(f"Wrote {written} new extracted_facts + {written} new evidence rows.")
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
