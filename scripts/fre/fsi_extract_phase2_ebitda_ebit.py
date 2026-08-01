"""FSI Phase 2, Stage 4: EBITDA/EBIT Intelligence
(docs/fre_runs/fsi_phase2_execution_plan.md, docs/fre_runs/
fsi_phase2_implementation_log.md). Writes ebit/ebitda facts for whichever
of the 15 real anchor filings actually support them, using the shared
infrastructure (period_normalization, terminology_mapping,
restatement_detection, now corrected per Entry 4/5) built in Stages 1-3.

Every figure below was re-read directly from the real archived filing
text (data/staging/document_text/<doc_id>.txt), the same discipline as
Stages 1-3. Central, disclosed governing rule for this stage, per the
owner's explicit constraint: "Never assume Operating Profit, Operating
Income, EBIT, EBITDA, PBT, or EBT are equivalent unless explicitly
supported by the filing or the approved terminology mapping." Applied
per ticker as follows:

  - UCAP (docs 4248, 6911, 10772): a bank/merchant-banking group. Its
    filings report ONLY "Profit Before Tax" (and an internal "Operating
    profit before income tax" line that is itself PBT under a different
    name, not EBIT/EBITDA) -- for a bank, net interest income/expense IS
    the core operating business, not a non-operating item to strip out
    the way EBIT excludes finance costs for a manufacturer. No filing
    ever uses the word EBIT or EBITDA. NO fact is written for UCAP in
    this stage -- a genuine, disclosed scope gap for financial
    institutions, not an extraction failure.
  - CAP (docs 4508, 5911, 10115): a manufacturer. Doc 4508 states a
    literal "EBIT" line (direct_reported). Docs 5911/10115 use "Operating
    Profit" instead (structurally identical position in the same
    company's own income statement, but mapped via the terminology
    config's existing 'mapped_equivalent' rule, never upgraded to
    direct_reported just because it's the same company). NO EBITDA
    anywhere -- CAP never discloses a depreciation/amortisation figure
    in any of its three filings, so EBITDA cannot be derived either;
    disclosed as a genuine gap, not guessed.
  - AFRIPRUD (docs 4245, 6349, 7540): reports "Profit Before Finance
    Cost(s) and Tax" -- structurally EBIT by its own definition (before
    finance cost, before tax), added as a new mapped_equivalent synonym
    (configs/financial_statement_terminology.toml). All three filings
    ALSO disclose depreciation-of-PP&E + depreciation-of-ROU-assets +
    amortisation-of-intangibles as separate income-statement lines,
    enabling a DERIVED EBITDA (= EBIT + D&A) for all three -- the one
    architecturally-permitted derivation
    (configs/financial_ontology.toml's ebit/d_and_a -> ebitda edges),
    exercised here for the first time in this pilot.
  - BUAFOODS (docs 6664, 8009, 9357): a manufacturer reporting Group-
    level "Operating Profit" (mapped_equivalent) in a precise thousands-
    denominated table, AND a literal "EBITDA" figure, but ONLY as a
    rounded narrative statement ("~N86.4 billion"), never in the precise
    table -- direct_reported, but disclosed as lower-precision than the
    table-sourced figures elsewhere in this pilot.
  - NASCON (docs 8801, 9460, 10929): reports both "Operating profit"
    (mapped_equivalent) and a literal "EBITDA" figure, both in the same
    precise, tabulated "CASH FLOWS"-adjacent highlights table -- the
    highest-precision EBITDA source in this stage.

  PYTHONPATH=src python scripts/fre/fsi_extract_phase2_ebitda_ebit.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_extract_phase2_ebitda_ebit.py --apply    # writes for real
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

STAGE = "ebitda_ebit"

# Each entry: one filing's ebit/ebitda facts. `tier` is set per-metric
# (never assumed uniform), since the same filing can carry a
# direct_reported ebit alongside a derived ebitda, etc. `derivation` is
# populated only for the one architecturally-permitted derived case
# (AFRIPRUD's ebitda = ebit + d_and_a), recording every input value used,
# so the derivation is fully traceable, never silent.
FACTS = [
    dict(doc_id=4508, ticker="CAP", period_start="2020-01-01", period_end="2020-12-31",
         ebit=1_645_000_000, label_ebit="EBIT", tier_ebit="direct_reported",
         ebitda=None, label_ebitda=None, tier_ebitda=None, derivation_ebitda=None,
         note="Literal 'EBIT' line, FY2020 column of the Key Financial Highlights table. No EBITDA "
              "or depreciation/amortisation figure is disclosed anywhere in this filing -- genuine gap, "
              "not derived from an assumption."),
    dict(doc_id=5911, ticker="CAP", period_start="2021-01-01", period_end="2021-12-31",
         ebit=1_555_000_000, label_ebit="Operating Profit", tier_ebit="mapped_equivalent",
         ebitda=None, label_ebitda=None, tier_ebitda=None, derivation_ebitda=None,
         note="'Operating Profit' (not literally 'EBIT' in this filing, unlike doc 4508 -- same company, "
              "different year's label; mapped via the terminology config's existing rule, not upgraded to "
              "direct_reported on the basis of company identity alone). No D&A disclosed; no EBITDA."),
    dict(doc_id=10115, ticker="CAP", period_start="2025-01-01", period_end="2025-06-30",
         ebit=3_175_000_000, label_ebit="Operating Profit", tier_ebit="mapped_equivalent",
         ebitda=None, label_ebitda=None, tier_ebitda=None, derivation_ebitda=None,
         note="H1 2025 column of a Q2/H1 comparative table (H1, not the Q2-only column). No D&A "
              "disclosed; no EBITDA."),
    dict(doc_id=4245, ticker="AFRIPRUD", period_start="2020-01-01", period_end="2020-09-30",
         ebit=1_570_712_000, label_ebit="Profit Before Finance cost and Tax", tier_ebit="mapped_equivalent",
         ebitda=1_633_268_000, label_ebitda=None, tier_ebitda="derived",
         derivation_ebitda="EBITDA = EBIT (1,570,712k) + D&A (Depreciation of PP&E 40,792k + "
                            "Depreciation of ROU assets 4,268k + Amortisation of intangibles 17,496k "
                            "= 62,556k) = 1,633,268k",
         note="'Profit Before Finance cost and Tax' is AFRIPRUD's own literal line, structurally EBIT by "
              "definition (immediately precedes 'Finance costs' and 'Profit Before Tax'). D&A is disclosed "
              "as three separate lines in the same statement, enabling the one derivation the approved "
              "architecture permits (configs/financial_ontology.toml's ebit/d_and_a -> ebitda edges)."),
    dict(doc_id=6349, ticker="AFRIPRUD", period_start="2022-01-01", period_end="2022-06-30",
         ebit=1_155_807_000, label_ebit="Profit before finance costs and tax", tier_ebit="mapped_equivalent",
         ebitda=1_196_830_000, label_ebitda=None, tier_ebitda="derived",
         derivation_ebitda="EBITDA = EBIT (1,155,807k) + D&A (23,359k + 2,845k + 14,819k = 41,023k) "
                            "= 1,196,830k",
         note="Same structure as doc 4245, plural 'costs' label variant (AFRIPRUD's own real wording "
              "differs across its filings, both added to the terminology config)."),
    dict(doc_id=7540, ticker="AFRIPRUD", period_start="2023-01-01", period_end="2023-06-30",
         ebit=597_848_000, label_ebit="Profit Before Finance Cost and Tax", tier_ebit="mapped_equivalent",
         ebitda=631_582_000, label_ebitda=None, tier_ebitda="derived",
         derivation_ebitda="EBITDA = EBIT (597,848k) + D&A (18,208k + 2,082k + 13,444k = 33,734k) "
                            "= 631,582k",
         note="Same structure as docs 4245/6349; this filing's own comparative column (30-Jun-22) "
              "independently confirms doc 6349's own reported EBIT (1,155,807k) exactly -- a real, "
              "positive cross-filing consistency check, though the comparative column itself is not "
              "extracted as a fact, per the established convention."),
    dict(doc_id=6664, ticker="BUAFOODS", period_start="2022-01-01", period_end="2022-09-30",
         ebit=79_336_575_000, label_ebit="Operating Profit", tier_ebit="mapped_equivalent",
         ebitda=86_400_000_000, label_ebitda="EBITDA", tier_ebitda="direct_reported", derivation_ebitda=None,
         note="Operating Profit is the GROUP column of the 'Key Financial Highlights' table (a separate "
              "Company-only column also exists and is deliberately not used, consistent with the same "
              "Group-vs-Company choice already made for this doc's balance-sheet/cash-flow facts). "
              "EBITDA is a narrative-only, rounded figure ('~N86.4 billion') -- LOWER PRECISION than the "
              "exact-thousands table figures used elsewhere in this stage; disclosed, not treated as "
              "equally precise."),
    dict(doc_id=8009, ticker="BUAFOODS", period_start="2023-01-01", period_end="2023-12-31",
         ebit=213_290_870_000, label_ebit="Operating Profit", tier_ebit="mapped_equivalent",
         ebitda=223_300_000_000, label_ebitda="EBITDA", tier_ebitda="direct_reported", derivation_ebitda=None,
         note="Group-only table (no separate Company column in this filing). EBITDA narrative-only, "
              "rounded ('~N223.3 billion'), same precision caveat as doc 6664."),
    dict(doc_id=9357, ticker="BUAFOODS", period_start="2024-01-01", period_end="2024-12-31",
         ebit=489_190_986_000, label_ebit="Operating Profit", tier_ebit="mapped_equivalent",
         ebitda=499_400_000_000, label_ebitda="EBITDA", tier_ebitda="direct_reported", derivation_ebitda=None,
         note="Group-only table. EBITDA narrative-only, rounded ('~N499.4 billion'), same precision "
              "caveat as docs 6664/8009."),
    dict(doc_id=8801, ticker="NASCON", period_start="2024-01-01", period_end="2024-06-30",
         ebit=7_198_000_000, label_ebit="Operating profit", tier_ebit="mapped_equivalent",
         ebitda=10_112_000_000, label_ebitda="EBITDA", tier_ebitda="direct_reported", derivation_ebitda=None,
         note="Both figures read from the same precise, tabulated highlights table (₦M) -- the highest-"
              "precision EBITDA source in this stage, unlike BUAFOODS's narrative-only figures."),
    dict(doc_id=9460, ticker="NASCON", period_start="2024-01-01", period_end="2024-12-31",
         ebit=23_037_000_000, label_ebit="Operating profit", tier_ebit="mapped_equivalent",
         ebitda=27_414_000_000, label_ebitda="EBITDA", tier_ebitda="direct_reported", derivation_ebitda=None,
         note="Same tabulated highlights table as doc 8801."),
    dict(doc_id=10929, ticker="NASCON", period_start="2025-01-01", period_end="2025-12-31",
         ebit=42_896_000_000, label_ebit="Operating profit", tier_ebit="mapped_equivalent",
         ebitda=46_446_000_000, label_ebitda="EBITDA", tier_ebitda="direct_reported", derivation_ebitda=None,
         note="Same tabulated highlights table as docs 8801/9460."),
]

# Confirmed, by direct re-reading, to have NO extractable EBIT/EBITDA
# data at all for the stated architectural reason (not a code gap).
NO_EBIT_DATA = {
    4248: "UCAP (bank -- PBT only, never EBIT/EBITDA; see module docstring)",
    6911: "UCAP (bank -- PBT only)",
    10772: "UCAP (bank -- PBT only)",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase2_ebitda_ebit_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("extracted_facts", "evidence", "documents")}

    now = datetime.now(timezone.utc).isoformat()
    written = 0

    print(f"Filings confirmed to have NO EBIT/EBITDA data (disclosed gap): {NO_EBIT_DATA}")

    for entry in FACTS:
        period_type = classify_period_type(entry["period_start"], entry["period_end"])

        for metric in ("ebit", "ebitda"):
            value = entry[metric]
            if value is None:
                continue
            label = entry.get(f"label_{metric}")
            tier = entry[f"tier_{metric}"]
            derivation = entry.get(f"derivation_{metric}")

            if label is not None:
                mapped_concept = map_label_to_concept(label)
                assert mapped_concept == metric, f"terminology mapping mismatch for doc {entry['doc_id']}: {label!r} -> {mapped_concept!r}, expected {metric!r}"
            else:
                assert tier == "derived", f"doc {entry['doc_id']} {metric}: no source label given but tier is not 'derived'"
                assert derivation is not None, f"doc {entry['doc_id']} {metric}: derived value missing its derivation trace"

            restatement_conflicts = find_restatement_conflicts(
                con, entry["ticker"], metric, entry["period_start"], entry["period_end"], float(value)
            ) if args.apply else []

            description = (
                f"{entry['ticker']} {metric} for period {entry['period_start']} to {entry['period_end']} "
                f"(period_type={period_type}): NGN {value:,}. "
                + (f"Source label: '{label}' (mapped via configs/financial_statement_terminology.toml). "
                   if label is not None else f"Derivation: {derivation}. ")
                + f"Confidence tier: {tier}. {entry['note']}. FSI Phase 2 pilot extraction, stage={STAGE}, "
                  f"manually read and cross-checked against the archived filing's own text (no external"
                  f"/vendor source used)."
            )
            print(f"{'[DRY RUN] ' if not args.apply else ''}doc={entry['doc_id']} ticker={entry['ticker']} "
                  f"metric={metric} value={value:,} tier={tier} period_type={period_type} "
                  f"restatement_conflicts={restatement_conflicts}")

            if args.apply:
                cur = con.execute(
                    "INSERT INTO evidence (doc_id, quoted_text, page_number, char_start, char_end, "
                    "source_confidence) VALUES (?,?,?,?,?,?)",
                    (entry["doc_id"],
                     f"Source label '{label}' -> {value:,} (NGN)" if label is not None else f"{derivation}",
                     None, None, None, 0.85),
                )
                evidence_id = cur.lastrowid
                con.execute(
                    "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
                    "period_start, period_end, period_type, confidence_tier, restates_fact_id, "
                    "evidence_id, extraction_confidence, model_id, prompt_version, grounding_check, "
                    "extracted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (entry["doc_id"], metric, description, float(value), entry["period_start"],
                     entry["period_end"], period_type, tier,
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
    if args.apply:
        print(f"Wrote {written} new extracted_facts + {written} new evidence rows.")
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
