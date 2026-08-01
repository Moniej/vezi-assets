"""FSI Phase 2, Stage 3: Cash Flow Intelligence
(docs/fre_runs/fsi_phase2_execution_plan.md, docs/fre_runs/
fsi_phase2_implementation_log.md). Writes cfo/cfi/cff/capex/fcf facts for
whichever of the 15 real Phase 1/Stage-2 anchor filings actually contain
extractable cash-flow-statement figures, using the shared infrastructure
(period_normalization, terminology_mapping, restatement_detection) built
in Stage 1.

Every figure below was re-read directly from the real archived filing
text (data/staging/document_text/<doc_id>.txt), the same discipline as
Stages 1-2. The central, disclosed finding of this stage: cash-flow data
is far SPARSER than balance-sheet data across these 15 filings. Most of
them are abridged "results highlights" press releases that never include
a cash-flow statement at all -- confirmed by direct re-reading, not
assumed:

  - UCAP (docs 4248, 6911, 10772): NO cash-flow data in any of the 3
    filings.
  - AFRIPRUD (docs 4245, 6349, 7540): NO cash-flow data in any of the 3
    filings.
  - CAP (docs 5911, 10115): NO cash-flow data (doc 4508 is the sole CAP
    exception, see below).
  - BUAFOODS (docs 8009, 9357): NO cash-flow data. Doc 6664 is the sole
    BUAFOODS exception (narrative-only, partial: cfo and cff stated,
    cfi and capex NOT given).
  - NASCON (docs 8801, 9460, 10929): the ONLY ticker with a full,
    tabulated CASH FLOWS section (cfo/cfi/cff) in every one of its 3
    filings. No separate capex line is broken out anywhere in NASCON's
    own tables -- cfi is an aggregate investing total, not a capex
    figure, and is never treated as one.

Only 5 of the 15 filings (6664, 4508, 8801, 9460, 10929) yield any
cash-flow fact at all; the other 10 are disclosed here as genuine
document-content gaps, not extraction failures -- the same class of
finding as CAP doc 4508's own balance-sheet gap in Stage 2.

CAP doc 4508 is a genuine edge case: its "Key Financial Highlights" table
states "Free Cash Flow" as a literal line item (1,025mn FY2020), and its
narrative separately states "net capital expenditure ... N113 million in
FY 2020". Phase 2's own design treated fcf as DERIVED-only (fcf = cfo -
capex); this filing makes fcf a DIRECT, literally-reported value instead
-- confidence_tier='direct_reported' per the hierarchy's priority rule
(see the new [fcf] entry in configs/financial_statement_terminology.toml,
added for this real discovery). The capex figure is the filing's own
stated "net" capital expenditure (net of disposals), not a gross
purchase-of-PP&E figure -- kept literal and disclosed, not silently
normalized to a different figure. No derived fcf occurs anywhere in this
pilot: no filing provides BOTH an explicit cfo AND an explicit capex
value for the same period, so the derivation path (fcf = cfo - capex),
though architecturally supported, is never actually exercised by real
data here -- disclosed honestly rather than manufactured.

  PYTHONPATH=src python scripts/fre/fsi_extract_phase2_cash_flow.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_extract_phase2_cash_flow.py --apply    # writes for real
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

STAGE = "cash_flow"

# Each entry: one filing's available cash-flow metrics, as literally read
# from the source filing text. A metric/label pair of (None, None) means
# "this filing does not report this metric" -- disclosed by omission from
# the written facts, never guessed or derived from an unrelated figure.
FACTS = [
    dict(doc_id=6664, ticker="BUAFOODS", period_start="2022-01-01", period_end="2022-09-30",
         cfo=103_700_000_000, label_cfo="Net cash from operating activities",
         cfi=None, label_cfi=None,
         cff=93_700_000_000, label_cff="Net cash from financing activities",
         capex=None, label_capex=None, fcf=None, label_fcf=None,
         note="Narrative-only figures ('Review of statement of financial position' section), not a "
              "tabulated cash-flow statement. No investing-activities or capex figure is given anywhere "
              "in this filing -- disclosed as a gap, not derived from the other two."),
    dict(doc_id=4508, ticker="CAP", period_start="2020-01-01", period_end="2020-12-31",
         cfo=None, label_cfo=None, cfi=None, label_cfi=None, cff=None, label_cff=None,
         capex=113_000_000, label_capex="Capital expenditure",
         fcf=1_025_000_000, label_fcf="Free Cash Flow",
         note="FCF is a literal 'Key Financial Highlights' table line item (direct_reported, not derived "
              "-- see configs/financial_statement_terminology.toml's [fcf] entry, added for this real "
              "discovery). Capex is the filing's own narrative-stated 'net capital expenditure' figure "
              "(net of disposals) -- kept literal, not normalized to a gross purchase-of-PP&E figure. No "
              "cfo/cfi/cff figures are given anywhere in this filing."),
    dict(doc_id=8801, ticker="NASCON", period_start="2024-01-01", period_end="2024-06-30",
         cfo=-10_038_000_000, label_cfo="Net cash from operating activities",
         cfi=-1_240_000_000, label_cfi="Net cash from investing activities",
         cff=-2_042_000_000, label_cff="Net cash from financing activities",
         capex=None, label_capex=None, fcf=None, label_fcf=None,
         note="Full tabulated 'CASH FLOWS' section. No separate capex line is broken out from the "
              "aggregate investing-activities total -- cfi is not treated as a capex proxy."),
    dict(doc_id=9460, ticker="NASCON", period_start="2024-01-01", period_end="2024-12-31",
         cfo=4_023_000_000, label_cfo="Net cash from operating activities",
         cfi=-421_000_000, label_cfi="Net cash from investing activities",
         cff=-4_217_000_000, label_cff="Net cash from financing activities",
         capex=None, label_capex=None, fcf=None, label_fcf=None,
         note="Full tabulated 'CASH FLOWS' section. Same-filing FY2023 comparative cfo/cfi (20,050 / "
              "-894) are NOT extracted, per Phase 2's established convention of never extracting a "
              "filing's own comparative prior-period column (docs/fre_runs/fsi_phase2_implementation_"
              "log.md Entry 2)."),
    dict(doc_id=10929, ticker="NASCON", period_start="2025-01-01", period_end="2025-12-31",
         cfo=43_906_000_000, label_cfo="Net cash from operating activities",
         cfi=-17_871_000_000, label_cfi="Net cash from investing activities",
         cff=-9_207_000_000, label_cff="Net cash from financing activities",
         capex=None, label_capex=None, fcf=None, label_fcf=None,
         note="Full tabulated 'CASH FLOWS' section. DISCLOSED REAL ANOMALY, not extracted: this filing's "
              "own FY2024 comparative column states cfo=4,165mn/cfi=-562mn, which do NOT match doc 9460's "
              "own reported FY2024 figures (cfo=4,023mn/cfi=-421mn) for the identical period -- a real, "
              "observed inter-filing inconsistency in comparative-column reporting. Per the same "
              "comparative-column convention as above, neither comparative figure is extracted as a fact, "
              "so this inconsistency does not surface as a restatement conflict in the written data; it is "
              "recorded here for transparency rather than silently absorbed or resolved by picking one."),
]

# Documents confirmed, by direct re-reading, to contain NO extractable
# cash-flow-statement data at all -- listed here so the gap is visible in
# code, not just in the module docstring.
NO_CASH_FLOW_DATA = {
    4248: "UCAP", 6911: "UCAP", 10772: "UCAP",
    4245: "AFRIPRUD", 6349: "AFRIPRUD", 7540: "AFRIPRUD",
    5911: "CAP", 10115: "CAP",
    8009: "BUAFOODS", 9357: "BUAFOODS",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase2_cash_flow_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("extracted_facts", "evidence", "documents")}

    now = datetime.now(timezone.utc).isoformat()
    written = 0

    print(f"Filings confirmed to have NO cash-flow data (disclosed gap): {NO_CASH_FLOW_DATA}")

    for entry in FACTS:
        period_type = classify_period_type(entry["period_start"], entry["period_end"])

        for metric in ("cfo", "cfi", "cff", "capex", "fcf"):
            value = entry[metric]
            label = entry[f"label_{metric}"]
            if value is None:
                continue

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
                f"{entry['note']}. FSI Phase 2 pilot extraction, stage={STAGE}, manually read and "
                f"cross-checked against the archived filing's own text (no external/vendor source used)."
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
    if args.apply:
        print(f"Wrote {written} new extracted_facts + {written} new evidence rows.")
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
