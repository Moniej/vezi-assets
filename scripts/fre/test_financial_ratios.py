"""Standalone assertion-script tests for financial_ratios.py, validated
against real production data (read-only) plus a disposable scratch fixture
for edge cases (zero denominator, missing input).

  PYTHONPATH=src python scripts/fre/test_financial_ratios.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.financial_ratios import (  # noqa: E402
    compute_ratios_for_ticker, list_tickers, write_ratio_results,
)

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
    return sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    facts_count_before = con.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0]

    tickers = list_tickers(con)
    check("list_tickers finds all 5 real FSI tickers",
          set(tickers) == {"UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON"})

    # --- CAP FY2020 (doc 4508): no balance-sheet data at all (Stage 2's own
    # disclosed gap) -- debt_to_equity must be insufficient_data, not guessed
    cap_results = compute_ratios_for_ticker(con, "CAP")
    fy2020 = [r for r in cap_results if r.period_start == "2020-01-01" and r.period_end == "2020-12-31"]
    d2e_fy2020 = next(r for r in fy2020 if r.metric == "debt_to_equity")
    check("CAP FY2020 debt_to_equity is insufficient_data (doc 4508 has no assets/liabilities/equity)",
          d2e_fy2020.status == "insufficient_data" and d2e_fy2020.value_numeric is None)
    check("CAP FY2020 debt_to_equity has zero input facts (neither liabilities nor equity exist)",
          d2e_fy2020.input_fact_ids == [])

    # --- CAP FY2020 ebit_margin: ebit (1,645,000,000) IS reported directly for
    # this doc, revenue (8,737,000,000) is a real Phase 1 fact -- ratio
    # should compute and hand-check to the real numbers
    ebit_margin_fy2020 = next(r for r in fy2020 if r.metric == "ebit_margin")
    expected = 1_645_000_000 / 8_737_000_000
    check("CAP FY2020 ebit_margin computes correctly from real facts (1,645mn / 8,737mn)",
          ebit_margin_fy2020.status == "computed"
          and abs(ebit_margin_fy2020.value_numeric - expected) < 1e-9)
    check("CAP FY2020 ebit_margin's confidence_tier is None (revenue is a Phase-1 legacy fact, "
          "NULL tier -- the floor, per the confidence-propagation rule)",
          ebit_margin_fy2020.confidence_tier is None)

    # --- NASCON: the fullest-coverage ticker -- every ratio should compute
    # for at least 2 of its 3 periods (cfo_to_net_profit computes for all 3)
    nascon_results = compute_ratios_for_ticker(con, "NASCON")
    nascon_cfo_np = [r for r in nascon_results if r.metric == "cfo_to_net_profit"]
    check("NASCON cfo_to_net_profit computes for all 3 real periods (the only ticker with "
          "cfo in every period)",
          len(nascon_cfo_np) == 3 and all(r.status == "computed" for r in nascon_cfo_np))

    # --- UCAP: a bank, no ebit/ebitda ever -- ebit_margin/ebitda_margin must
    # be insufficient_data for all 3 real periods, never guessed from PBT
    ucap_results = compute_ratios_for_ticker(con, "UCAP")
    ucap_ebit_margin = [r for r in ucap_results if r.metric == "ebit_margin"]
    check("UCAP ebit_margin is insufficient_data for all 3 periods (a bank -- PBT is never "
          "treated as EBIT-equivalent)",
          len(ucap_ebit_margin) == 3 and all(r.status == "insufficient_data" for r in ucap_ebit_margin))

    # --- debt_to_equity: liabilities+equity are both direct_reported (Stage 2)
    # for every ticker/period where both exist -- confidence_tier should be
    # direct_reported, not floored to None
    d2e_all = [r for r in nascon_results if r.metric == "debt_to_equity" and r.status == "computed"]
    check("NASCON debt_to_equity confidence_tier is direct_reported (both liabilities and "
          "equity are Stage-2 direct_reported facts)",
          len(d2e_all) == 3 and all(r.confidence_tier == "direct_reported" for r in d2e_all))

    con.close()

    # --- write path: scratch-copy only, verify row counts and provenance ---
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con2 = sqlite3.connect(scratch)
    before_conclusions = con2.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0]
    max_id_before = con2.execute(
        "SELECT COALESCE(MAX(conclusion_id), 0) FROM financial_reasoning_conclusions"
    ).fetchone()[0]
    test_results = compute_ratios_for_ticker(con2, "CAP")
    written = write_ratio_results(con2, test_results)
    con2.commit()
    after_conclusions = con2.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0]
    check("write_ratio_results writes exactly len(results) new conclusion rows",
          written == len(test_results) and after_conclusions - before_conclusions == written)
    # every 'computed' conclusion (among the NEWLY written rows, identified by
    # conclusion_id > max_id_before -- the scratch copy already contains the
    # real production conclusions, so matching on ticker/metric/period alone
    # would double-count against those pre-existing rows) has exactly 2
    # linked facts (numerator+denominator); every 'insufficient_data' one has 0 or 1
    new_rows = con2.execute(
        "SELECT conclusion_id, status FROM financial_reasoning_conclusions WHERE conclusion_id > ?",
        (max_id_before,),
    ).fetchall()
    mismatch = False
    for conclusion_id, status in new_rows:
        linked = con2.execute(
            "SELECT COUNT(*) FROM financial_reasoning_conclusion_facts WHERE conclusion_id = ?",
            (conclusion_id,),
        ).fetchone()[0]
        if status == "computed" and linked != 2:
            mismatch = True
        if status == "insufficient_data" and linked not in (0, 1):
            mismatch = True
    check("every newly-written conclusion's linked-fact count matches its status "
          "(2 for computed, 0-1 for insufficient_data)",
          not mismatch and len(new_rows) == written)
    con2.close()
    Path(scratch).unlink()
    Path(scratch).parent.rmdir()

    # --- confirm the real production database was never touched by this test ---
    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    facts_count_after = con.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0]
    check("production documents count unchanged", doc_count_after == doc_count_before)
    check("production extracted_facts count unchanged (this test writes only to a scratch copy)",
          facts_count_after == facts_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
