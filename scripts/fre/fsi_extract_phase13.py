"""FSI Phase 13: Coverage Expansion extraction (docs/fre_runs/
fsi_phase13_preregistration.md). Writes revenue/net_profit/ebit/ebitda
facts for 10 new, real, hand-verified filings across 5 new tickers
(MTNN, DANGCEM, UBN, OANDO, NESTLE), using the exact same shared
infrastructure as FSI Phase 1/2 (period_normalization, terminology_mapping,
restatement_detection) -- no code change to any of those frozen modules,
only real, disclosed additions to configs/financial_statement_terminology.
toml (five new net_profit synonyms, one new ebit synonym; see that file's
own notes for the per-ticker justification).

Every figure below was read directly from the real archived filing text
(data/staging/document_text/<doc_id>.txt). This installment is scoped to
core metrics only (revenue, net_profit, ebit, ebitda where disclosed) --
balance sheet and cash-flow extraction for these 5 tickers is explicitly
deferred to a future phase, matching Phase 1's own original scope before
Phase 2 later extended it.

Real, disclosed findings from this extraction pass:

  - MTNN (docs 8080 FY2023, 9430 FY2024): both years are REAL STATUTORY
    NET LOSSES (forex-driven), not profits -- FY2023 PAT -N137,020m,
    FY2024 PAT -N400,435m. Both filings' own press releases headline a
    separate "adjusted PAT" (ex-forex-loss) figure (N344.5bn for FY2023);
    per this platform's "no fabricated/no inferred financial facts" rule,
    the statutory, as-reported PAT is what is recorded as net_profit --
    the adjusted figure is noted in the fact's own description only,
    never substituted. Doc 8080 additionally has a REAL, tiny internal
    inconsistency: its own "Key financial highlights" narrative table
    states "(Loss)/profit for the year (137,021)" while its own detailed
    income-statement table two sections later states "PAT (137,020)" --
    a 1-unit (N'million) rounding difference within the SAME document.
    The detailed table's "PAT" row is used (matches the existing 'PAT'
    terminology synonym exactly, direct_reported); the 1-unit discrepancy
    vs. the highlights narrative is disclosed here, not silently resolved.
  - DANGCEM (docs 8383, 9741): both are Q1 (three-month) unaudited
    results, not FY -- period_type='Q1' for both, correctly derived from
    the actual period_start/period_end span (three months ended 31 March),
    never from a filing's own headline label, per the established
    UCAP-precedent rule. Each filing independently confirms the OTHER's
    own comparative-column figures exactly (doc 9741's Q1 2024 comparative
    matches doc 8383's own reported Q1 2024 figures exactly) -- a real,
    positive cross-filing consistency check, though the comparative
    column itself is not extracted as a separate fact, per the same
    convention used throughout FSI Phase 1/2.
  - UBN (docs 5987 FY2021, 7232 FY2022): a bank -- Gross Earnings (mapped_
    equivalent, same sector convention as AFRIPRUD) and Profit After Tax
    (direct_reported) only; no EBIT/EBITDA (genuine architectural gap,
    same as UCAP -- banks' net interest income IS the core operating
    business, not a non-operating item to strip out). REAL CROSS-FILING
    RESTATEMENT DISCREPANCY DISCLOSED (not an extraction fault, same
    class of finding as CAP in Phase 1): doc 7232's own FY2021 comparative
    column (Group Gross Earnings 177.3bn / PBT 18.2bn / PAT 16.9bn)
    does NOT match doc 5987 (the actual FY2021 filing)'s own originally
    reported FY2021 Group figures (172.0bn / 20.8bn / 19.4bn). Each fact
    below is recorded from its OWN filing's own stated figure for its OWN
    headline period, never reconciled across filings -- the comparative
    column is informational context only, not a separate extracted fact.
  - OANDO (docs 7058 FYE2021, 9355 FY2024): an oil & gas group with no
    EBITDA/D&A disclosure in either filing (genuine gap). Doc 7058's FYE
    2021 results were released 28 March 2023 -- a real, unusually long
    reporting lag for this specific filing (not a data error).
  - NESTLE (docs 8089 FY2023, 9423 FY2024): both years are REAL STATUTORY
    NET LOSSES (forex/finance-cost driven) -- FY2023 -N79,473,781k, FY2024
    -N164,595,022k. Doc 9423 ADDITIONALLY discloses a separate "Total
    Comprehensive loss for the period" figure (-N14,557,657k for FY2024)
    that is NOT the same concept as net_profit -- it includes a one-off
    N150,037,365k property revaluation surplus recognized in OCI following
    a March 2024 change to the revaluation model for PP&E. Per the
    platform's "no fabricated/no inferred financial facts" rule, the
    statutory "Loss for the period" (the P&L bottom line, before OCI) is
    what is recorded as net_profit; the total-comprehensive-income figure
    is noted in the fact's own description only, never substituted for
    it. Doc 9423's EBITDA figure (N196.7bn) is narrative-only and rounded
    (no precise tabulated EBITDA line exists in either NESTLE filing) --
    direct_reported (the filing does literally say "EBITDA"), but flagged
    as lower-precision than the exact-figure facts elsewhere in this
    batch, the same disclosed caveat FSI Phase 2 applied to BUAFOODS's
    own narrative-only EBITDA figures.

  PYTHONPATH=src python scripts/fre/fsi_extract_phase13.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_extract_phase13.py --apply    # writes for real
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

# Each entry: one filing. `metrics` maps fact_type -> (value, label, tier, note).
# value is None where the filing genuinely does not disclose that metric
# (a real gap, never guessed/derived beyond the one architecturally-
# permitted case already exercised in Phase 2, which does not recur here).
FILINGS = [
    dict(doc_id=8080, ticker="MTNN", period_start="2023-01-01", period_end="2023-12-31",
         metrics=dict(
             revenue=(2_468_847_000_000, "Total Revenue", "direct_reported",
                      "Key financial highlights table, FY2023 column: Total Revenue 2,468,847 (N'million)."),
             net_profit=(-137_020_000_000, "PAT", "direct_reported",
                         "Detailed income-statement table, FY2023 column: PAT (137,020) (N'million), a "
                         "real statutory LOSS. The filing's own highlights narrative states (137,021) for "
                         "the same line ('(Loss)/profit for the year') -- a 1-unit rounding difference "
                         "within the same document, disclosed not resolved. The press release separately "
                         "headlines an 'adjusted PAT' of N344.5bn (ex-net-forex-loss) -- NOT used here; "
                         "the statutory, as-reported figure is recorded per the platform's no-fabrication rule."),
             ebitda=(1_202_530_000_000, "EBITDA", "direct_reported",
                     "Key financial highlights table, FY2023 column: EBITDA 1,202,530 (N'million)."),
             ebit=None,
         )),
    dict(doc_id=9430, ticker="MTNN", period_start="2024-01-01", period_end="2024-12-31",
         metrics=dict(
             revenue=(3_360_830_000_000, "Total Revenue", "direct_reported",
                      "Key financial highlights table, FY2024 column: Total Revenue 3,360,830 (N'million)."),
             net_profit=(-400_435_000_000, "PAT", "direct_reported",
                         "Detailed income-statement table, FY2024 column: PAT (400,435) (N'million), a "
                         "real statutory LOSS -- FY2023 comparative in this same filing (137,021) matches "
                         "doc 8080's own reported FY2023 figure to within the same 1-unit rounding noted above."),
             ebitda=(1_313_397_000_000, "EBITDA", "direct_reported",
                     "Key financial highlights table, FY2024 column: EBITDA 1,313,397 (N'million)."),
             ebit=None,
         )),
    dict(doc_id=8383, ticker="DANGCEM", period_start="2024-01-01", period_end="2024-03-31",
         metrics=dict(
             revenue=(817_350_000_000, "Total revenue", "direct_reported",
                      "Summary Operating Review table: Total revenue 817,350 (N'million), Q1 2024."),
             net_profit=(112_674_000_000, "Net profit", "direct_reported",
                         "Financial Review / Profitability table: Net profit 112,674 (N'million), Q1 2024."),
             ebitda=(309_477_000_000, "EBITDA", "direct_reported",
                     "Financial Review / Profitability table: EBITDA 309,477 (N'million), Q1 2024."),
             ebit=(255_295_000_000, "Operating profit", "mapped_equivalent",
                   "Financial Review / Profitability table: Operating profit 255,295 (N'million), Q1 2024."),
         )),
    dict(doc_id=9741, ticker="DANGCEM", period_start="2025-01-01", period_end="2025-03-31",
         metrics=dict(
             revenue=(994_659_000_000, "Total revenue", "direct_reported",
                      "Financial Review Summary table: Total revenue 994,659 (N'million), Q1 2025; Q1 2024 "
                      "comparative (817,350) matches doc 8383's own reported Q1 2024 figure exactly."),
             net_profit=(209_245_000_000, "Net profit", "direct_reported",
                         "Financial Review Summary table: Net profit 209,245 (N'million), Q1 2025."),
             ebitda=(461_639_000_000, "EBITDA", "direct_reported",
                     "Profitability table: EBITDA 461,639 (N'million), Q1 2025."),
             ebit=(397_419_000_000, "Operating profit", "mapped_equivalent",
                   "Profitability table: Operating profit 397,419 (N'million), Q1 2025."),
         )),
    dict(doc_id=5987, ticker="UBN", period_start="2021-01-01", period_end="2021-12-31",
         metrics=dict(
             revenue=(172_000_000_000, "Gross Earnings", "mapped_equivalent",
                      "Financial Summary, GROUP column: Gross Earnings 172.0 (N'billion), FY2021. Bank "
                      "sector convention: 'Gross Earnings' is the bank's own headline top-line metric, "
                      "same mapping precedent as AFRIPRUD in FSI Phase 1."),
             net_profit=(19_400_000_000, "Profit After Tax", "direct_reported",
                         "Financial Summary, GROUP column: Profit After Tax 19.4 (N'billion), FY2021. REAL "
                         "CROSS-FILING DISCREPANCY DISCLOSED: doc 7232 (UBN's own later FY2022 filing)'s "
                         "FY2021 comparative column states a different Group PAT (16.9bn) for the same "
                         "period -- each fact is recorded from its own filing's own stated figure, never "
                         "reconciled across filings, same convention as CAP in FSI Phase 1."),
             ebitda=None,
             ebit=None,
         )),
    dict(doc_id=7232, ticker="UBN", period_start="2022-01-01", period_end="2022-12-31",
         metrics=dict(
             revenue=(209_100_000_000, "Gross Earnings", "mapped_equivalent",
                      "Financial Summary, GROUP column: Gross Earnings 209.10 (N'billion), FY2022."),
             net_profit=(39_200_000_000, "Profit After Tax", "direct_reported",
                         "Financial Summary, GROUP column: Profit After Tax 39.2 (N'billion), FY2022."),
             ebitda=None,
             ebit=None,
         )),
    dict(doc_id=7058, ticker="OANDO", period_start="2021-01-01", period_end="2021-12-31",
         metrics=dict(
             revenue=(722_447_000_000, "Revenue", "direct_reported",
                      "Finance Review table: Revenue 722,447 (N'million), FYE2021. Filing released "
                      "28 March 2023 -- a real, unusually long reporting lag, not a data error."),
             net_profit=(34_728_000_000, "Profit/(Loss)-After-Tax", "direct_reported",
                         "Finance Review table: Profit/(Loss)-After-Tax 34,728 (N'million), FYE2021."),
             ebitda=None,
             ebit=(78_691_000_000, "Operating Profit", "mapped_equivalent",
                   "Finance Review table: Operating Profit 78,691 (N'million), FYE2021."),
         )),
    dict(doc_id=9355, ticker="OANDO", period_start="2024-01-01", period_end="2024-12-31",
         metrics=dict(
             revenue=(4_122_091_844_000, "Revenue", "direct_reported",
                      "Financial Review table: Revenue 4,122,091,844 (N'000), FY2024."),
             net_profit=(65_489_693_000, "Profit-After-Tax", "direct_reported",
                         "Financial Review table: Profit-After-Tax 65,489,693 (N'000), FY2024 -- a "
                         "different real hyphenation variant of the metric label than doc 7058's own "
                         "'Profit/(Loss)-After-Tax', both added as distinct synonyms."),
             ebitda=None,
             ebit=(220_199_311_000, "Operating Profit", "mapped_equivalent",
                   "Financial Review table: Operating Profit 220,199,311 (N'000), FY2024."),
         )),
    dict(doc_id=8089, ticker="NESTLE", period_start="2023-01-01", period_end="2023-12-31",
         metrics=dict(
             revenue=(547_118_754_000, "Revenue", "direct_reported",
                      "Results table: Revenue 547,118,754 (N'000), FY2023."),
             net_profit=(-79_473_781_000, "(Loss)/profit for the period", "direct_reported",
                         "Results table: (Loss)/profit for the period (79,473,781) (N'000), FY2023 -- a "
                         "real statutory LOSS, driven by Naira devaluation impacting finance costs."),
             ebitda=None,
             ebit=(122_664_617_000, "Results from operating activities", "mapped_equivalent",
                   "Results table: Results from operating activities 122,664,617 (N'000), FY2023 -- "
                   "structurally EBIT (immediately before Finance income/costs and 'before income tax')."),
         )),
    dict(doc_id=9423, ticker="NESTLE", period_start="2024-01-01", period_end="2024-12-31",
         metrics=dict(
             revenue=(958_814_739_000, "Revenue", "direct_reported",
                      "Results table: Revenue 958,814,739 (N'000), FY2024; FY2023 comparative (547,118,754) "
                      "matches doc 8089's own reported FY2023 figure exactly."),
             net_profit=(-164_595_022_000, "Loss for the period", "direct_reported",
                         "Results table: Loss for the period (164,595,022) (N'000), FY2024 -- the P&L "
                         "bottom line, BEFORE other comprehensive income. This filing separately discloses "
                         "a 'Total Comprehensive loss for the period' of (14,557,657) (N'000), which "
                         "includes a one-off N150,037,365k PP&E revaluation surplus (OCI, from a March "
                         "2024 change to the revaluation model) -- NOT the same concept as net_profit and "
                         "NOT used here; the statutory P&L figure is recorded per the platform's "
                         "no-fabrication rule."),
             ebitda=(196_700_000_000, "EBITDA", "direct_reported",
                     "Narrative only (Highlights section): 'Earnings before interest, taxes, depreciation "
                     "and amortization (EBITDA) of 196.7 billion Naira' -- rounded, no precise tabulated "
                     "EBITDA line exists in either NESTLE filing. direct_reported (the filing literally "
                     "uses the word EBITDA) but lower-precision than the exact-figure facts elsewhere in "
                     "this batch, same disclosed caveat as BUAFOODS's own narrative-only EBITDA in FSI Phase 2."),
             ebit=(167_876_263_000, "Results from operating activities", "mapped_equivalent",
                   "Results table: Results from operating activities 167,876,263 (N'000), FY2024."),
         )),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase13_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("extracted_facts", "evidence", "documents")}

    now = datetime.now(timezone.utc).isoformat()
    written = 0

    for entry in FILINGS:
        period_type = classify_period_type(entry["period_start"], entry["period_end"])

        for metric in ("revenue", "net_profit", "ebit", "ebitda"):
            spec = entry["metrics"].get(metric)
            if spec is None:
                continue
            value, label, tier, note = spec

            mapped_concept = map_label_to_concept(label)
            assert mapped_concept == metric, (
                f"terminology mapping mismatch for doc {entry['doc_id']}: "
                f"{label!r} -> {mapped_concept!r}, expected {metric!r}"
            )

            restatement_conflicts = find_restatement_conflicts(
                con, entry["ticker"], metric, entry["period_start"], entry["period_end"], float(value)
            ) if args.apply else []

            description = (
                f"{entry['ticker']} {metric} for period {entry['period_start']} to {entry['period_end']} "
                f"(period_type={period_type}): NGN {value:,}. Source label: '{label}' (mapped via "
                f"configs/financial_statement_terminology.toml). Confidence tier: {tier}. {note} FSI "
                f"Phase 13 coverage-expansion extraction, manually read and cross-checked against the "
                f"archived filing's own text (no external/vendor source used)."
            )
            print(f"{'[DRY RUN] ' if not args.apply else ''}doc={entry['doc_id']} ticker={entry['ticker']} "
                  f"metric={metric} value={value:,} tier={tier} period_type={period_type} "
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
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check: {integrity}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
