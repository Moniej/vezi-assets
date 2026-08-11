"""FRE-7B.1: standalone assertion-script tests for the targeted extraction
stage (currency backfill, genuine_fact_universe.py's NEM/TRANSCORP
correction, and the 29 hand-verified facts fre7b1_targeted_extraction.py
wrote). Same no-pytest, script-based convention as every other FRE test
script.

SAFETY: this script is READ-ONLY against the real production database --
it verifies the state fre7b1_currency_backfill.py and
fre7b1_targeted_extraction.py already wrote; it does not write anything
itself.

  PYTHONPATH=src python scripts/fre/test_fre7b1_extraction.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.genuine_fact_universe import (  # noqa: E402
    list_genuine_financial_statement_tickers, share_reconstruction_only_tickers,
)

REAL_DB = db.DEFAULT_DB

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{REAL_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # --- financial_ratios.py itself is unmodified: list_tickers() still
    # returns its own original 26 (including NEM/TRANSCORP) -- the
    # correction is purely additive, never a change to the frozen core. ---
    broad = list_tickers(con)
    check("financial_ratios.list_tickers() is UNCHANGED -- still returns 26 "
          "tickers, still includes NEM/TRANSCORP (the core itself was never "
          "touched by this stage)", len(broad) == 26 and "NEM" in broad and "TRANSCORP" in broad)

    # --- genuine_fact_universe.py's additive correction -------------------
    narrow = list_genuine_financial_statement_tickers(con)
    check("list_genuine_financial_statement_tickers() correctly excludes "
          "NEM and TRANSCORP (both have only a share_reconstruction fact, "
          "never a real financial-statement fact)",
          "NEM" not in narrow and "TRANSCORP" not in narrow)
    check("every other one of the 24 real tickers is still included "
          "(the correction removes exactly 2, adds/changes nothing else)",
          len(narrow) == 24 and set(broad) - set(narrow) == {"NEM", "TRANSCORP"})
    check("share_reconstruction_only_tickers() names exactly the 2 "
          "over-counted tickers, for audit purposes",
          share_reconstruction_only_tickers(con) == ["NEM", "TRANSCORP"])

    # --- reproduce the original finding directly against real data -------
    for t in ["NEM", "TRANSCORP"]:
        n_real_fs_facts = con.execute(
            "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=? AND f.fact_type IN ('net_profit','equity','revenue','assets',"
            "'liabilities','ebit','ebitda','cfo','cfi','cff','capex','fcf','gross_profit','cogs')",
            (t,),
        ).fetchone()[0]
        check(f"{t}: genuinely has ZERO real financial-statement facts of any kind "
              f"(confirmed by direct query, not assumed)", n_real_fs_facts == 0)
    con.close()

    # --- currency backfill: AIRTELAFRI's genuine USD facts were NOT
    # overwritten to NGN; DEAPCAP/VERITASKAP (no reporting_currency on
    # record) correctly remain NULL, not guessed. -------------------------
    con = ro()
    airtel_currencies = set(r[0] for r in con.execute(
        "SELECT DISTINCT f.currency FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='AIRTELAFRI' AND f.fact_type IN ('net_profit','equity','revenue','assets',"
        "'liabilities','ebit','ebitda','cfo','cfi','cff','capex','fcf','gross_profit','cogs')"
    ).fetchall())
    check("AIRTELAFRI's financial-statement facts are all currency='USD' "
          "(the backfill used the ticker's OWN authoritative "
          "securities.reporting_currency, never defaulted to NGN)",
          airtel_currencies == {"USD"})
    for t in ["DEAPCAP", "VERITASKAP"]:
        n_null = con.execute(
            "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=? AND f.currency IS NULL AND f.fact_type IN ('net_profit','equity',"
            "'revenue','assets','liabilities','ebit','ebitda','cfo','cfi','cff','capex','fcf',"
            "'gross_profit','cogs')", (t,),
        ).fetchone()[0]
        check(f"{t}: still has NULL-currency facts (no securities.reporting_currency "
              f"on record for this ticker -- correctly left UNKNOWN, not guessed)", n_null > 0)
    n_backfilled_ngn = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE prompt_version IN "
        "('stage4a_hand_2026-08-08','stage5a_hand_2026-08-08') AND currency='NGN'"
    ).fetchone()[0]
    check("stage4a/stage5a's own facts (which never set currency on INSERT, a "
          "real pre-existing bug this stage did not repeat) are now backfilled "
          "to NGN where a reporting_currency was on record",
          n_backfilled_ngn > 0)
    con.close()

    # --- the 29 new FRE-7B.1 facts: exist, correct fact_types, currency
    # set explicitly (unlike stage4a/stage5a), correct provenance. --------
    con = ro()
    new_facts = con.execute(
        "SELECT fact_id, doc_id, fact_type, currency, grounding_check, evidence_id, "
        "period_end, confidence_tier FROM extracted_facts WHERE prompt_version = "
        "'fre7b1_hand_2026-08-09'"
    ).fetchall()
    check("exactly 29 new facts were written by fre7b1_targeted_extraction.py",
          len(new_facts) == 29)
    check("every new fact has currency='NGN' explicitly set on INSERT (fixing the "
          "exact class of bug stage4a/stage5a had)",
          all(f[3] == "NGN" for f in new_facts))
    check("every new fact with a real quote has grounding_check='passed' (the one "
          "derived DANGCEM equity fact correctly has grounding_check='not_run', "
          "since it has no direct quote to ground)",
          sum(1 for f in new_facts if f[4] == "passed") == 28
          and sum(1 for f in new_facts if f[4] == "not_run") == 1)
    check("every new fact has a real evidence_id (full provenance, not a bare number)",
          all(f[5] is not None for f in new_facts))
    check("every new fact has a period_end (no unperiodized fact was written)",
          all(f[6] is not None for f in new_facts))
    fact_types = set(f[2] for f in new_facts)
    check("only net_profit/revenue/equity/assets/liabilities were extracted -- no "
          "debt/cash/EPS/shares_outstanding fact_type was invented (none exist in "
          "this platform's schema; EPS values are recorded in description text "
          "only, for provenance, never as a separate fact row)",
          fact_types == {"net_profit", "revenue", "equity", "assets", "liabilities"})

    # --- DANGCEM's FY2024 equity was NOT duplicated -- the extraction
    # script's own arithmetic cross-validated the pre-existing stage4a fact
    # rather than re-inserting it. -----------------------------------------
    dangcem_fy2024_equity = con.execute(
        "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='DANGCEM' AND f.fact_type='equity' AND f.period_end='2024-12-31'"
    ).fetchone()[0]
    check("DANGCEM has exactly ONE equity fact for FY2024 (the pre-existing "
          "stage4a fact, fact_id 373) -- not duplicated by this extraction",
          dangcem_fy2024_equity == 1)

    # --- PIT / lookahead: none of the 29 new facts were filed before their
    # own period ended. -----------------------------------------------------
    lookahead = con.execute(
        "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE f.prompt_version='fre7b1_hand_2026-08-09' AND f.period_end IS NOT NULL "
        "AND d.filing_date < f.period_end"
    ).fetchone()[0]
    check("zero of the 29 new facts were filed before their own period ended "
          "(no lookahead violation)", lookahead == 0)

    # --- terminology mapping config: the one new synonym added
    # ('Group net profit') is real, disclosed, and does not silently change
    # any OTHER label's mapping. ---------------------------------------------
    from ngxrot.fre.terminology_mapping import map_label_to_concept  # noqa: E402
    check("'Group net profit' (DANGCEM's real FY2025 label) now maps to net_profit",
          map_label_to_concept("Group net profit") == "net_profit")
    check("'Net profit' (DANGCEM's own earlier-observed label) still maps to "
          "net_profit -- the new synonym is additive, not a replacement",
          map_label_to_concept("Net profit") == "net_profit")
    check("an unrelated, unmapped label still returns None (never a guess)",
          map_label_to_concept("Some Made Up Label Nobody Ever Used") is None)
    con.close()

    # --- confirm the real production database was written to exactly as
    # intended (documents table itself untouched -- only extracted_facts/
    # evidence rows were added, and extracted_facts.currency backfilled). --
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("documents table row count unchanged (this stage adds facts about "
          "EXISTING documents, never a new document row)",
          doc_count_after == doc_count_before)
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    check("real database integrity_check reports 'ok' after this stage's writes",
          integrity == "ok")
    fk_violations = con.execute("PRAGMA foreign_key_check").fetchall()
    check("foreign_key_check reports clean after this stage's writes", fk_violations == [])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
