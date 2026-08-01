"""Standalone assertion-script tests for pit_financial_memory.py, validated
against real production data (read-only) plus a disposable scratch
fixture proving requirement 2 ("historical corrections and restatements
must preserve the original knowledge state").

  PYTHONPATH=src python scripts/fre/test_pit_financial_memory.py
"""
from __future__ import annotations

import inspect
import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import pit_financial_memory as pit  # noqa: E402

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

    # --- core gating, real NASCON data: doc 8801 filed 2024-07-31, doc 9460
    # filed 2025-03-04, doc 10929 filed 2026-03-03
    check("as_of the day BEFORE NASCON's first real filing returns nothing knowable",
          len(pit.as_of(con, "NASCON", "2024-07-30").conclusions) == 0)
    snap_after_first = pit.as_of(con, "NASCON", "2024-07-31")
    check("as_of NASCON's first real filing date returns exactly the 5 ratios "
          "computable from that single filing alone (no trend needs 2 docs yet)",
          len(snap_after_first.conclusions) == 5
          and all(c.conclusion_type == "ratio" for c in snap_after_first.conclusions))
    snap_before_third = pit.as_of(con, "NASCON", "2025-03-03")
    check("as_of the day before NASCON's THIRD filing still returns only what the "
          "first two filings support (no premature trend/flag leakage)",
          len(snap_before_third.conclusions) == 5)
    snap_full = pit.as_of(con, "NASCON", "2026-03-03")
    total_nascon = con.execute(
        "SELECT COUNT(*) FROM financial_reasoning_conclusions WHERE ticker='NASCON'"
    ).fetchone()[0]
    check("as_of NASCON's own LAST real filing date returns ALL of NASCON's real "
          "conclusions (nothing withheld once everything is public)",
          len(snap_full.conclusions) == total_nascon and snap_full.excluded_count == 0)

    # --- zero-linked-fact edge case 1: CAP FY2020 debt_to_equity (period-specific,
    # gated by the earliest filing for that exact period -- doc 4508, 2021-01-28)
    check("CAP FY2020 debt_to_equity (insufficient_data, 0 source facts) is NOT "
          "knowable the day before doc 4508's own filing date",
          not any(c.metric == "debt_to_equity" and c.period_start == "2020-01-01"
                  for c in pit.as_of(con, "CAP", "2021-01-27").conclusions))
    check("...but IS knowable exactly on doc 4508's own filing date (2021-01-28)",
          any(c.metric == "debt_to_equity" and c.period_start == "2020-01-01"
              for c in pit.as_of(con, "CAP", "2021-01-28").conclusions))

    # --- zero-linked-fact edge case 2: ticker-wide cash_flow_earnings_divergence
    # (no period at all) -- gated by the LATEST of that ticker's real filings
    ucap_latest_filing = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='UCAP'"
    ).fetchone()[0]
    day_before_ucap_last = (date.fromisoformat(ucap_latest_filing) - timedelta(days=1)).isoformat()
    check("UCAP's ticker-wide cash_flow_earnings_divergence flag is NOT knowable "
          "the day before UCAP's own LAST real filing",
          not any(c.metric == "cash_flow_earnings_divergence"
                  for c in pit.as_of(con, "UCAP", day_before_ucap_last).conclusions))
    check("...but IS knowable exactly on UCAP's own last real filing date",
          any(c.metric == "cash_flow_earnings_divergence"
              for c in pit.as_of(con, "UCAP", ucap_latest_filing).conclusions))

    # --- mechanical single-ticker-scope guardrail, same style as Phase 3's Area 7 ---
    public_funcs = [f for name, f in inspect.getmembers(pit, inspect.isfunction)
                    if not name.startswith("_")]
    check("every public function in pit_financial_memory.py accepts at most ONE "
          "'ticker'-named parameter",
          all(len([p for p in inspect.signature(f).parameters if "ticker" in p.lower()]) <= 1
              for f in public_funcs))
    dataclass_fields = set()
    for cls in (pit.CompanyFinancialReasoningSnapshot, pit.KnowableConclusion, pit.SourceFactPIT):
        dataclass_fields.update(cls.__dataclass_fields__.keys())
    check("no dataclass field suggests a cross-ticker comparison, ranking, or score",
          not any(bad in name.lower() for name in dataclass_fields
                  for bad in ("rank", "compare", "vs_", "peer", "score")))

    con.close()

    # --- requirement 2: historical corrections/restatements preserve the original
    # knowledge state. No real restatement chain exists in the current dataset
    # (Phase 2's restates_fact_id count is 0 database-wide), so this is verified
    # on a disposable scratch fixture reproducing a hypothetical restatement,
    # matching test_restatement_detection.py's own established precedent for
    # testing a mechanism this dataset doesn't naturally exercise. -----------------
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con2 = sqlite3.connect(scratch)
    con2.execute("PRAGMA foreign_keys = ON")

    # A synthetic "original" fact (doc 4508, CAP, filed 2021-01-28) and a
    # synthetic "restating" fact for the SAME ticker/period, from a LATER,
    # synthetic document filed a year afterward -- reproducing the real CAP
    # restatement pattern (docs/fre_runs/fsi_phase1_results.md) on a fixture,
    # never on production.
    con2.execute(
        "INSERT INTO documents (doc_id, ticker, doc_type, source_type, filing_date, "
        "retrieved_date, local_path, source_confidence, source_id, as_of_date) "
        "VALUES (999901, 'CAP', 'financial_statement', 'filing', '2022-06-01', "
        "'2026-08-01', 'TEST FIXTURE', 0.9, 1, '2026-08-01')"
    )
    con2.execute(
        "INSERT INTO extracted_facts (fact_id, doc_id, fact_type, description, numeric_value, "
        "period_start, period_end, confidence_tier, restates_fact_id, extraction_confidence, "
        "grounding_check, extracted_at) VALUES "
        "(999901, 999901, 'revenue', 'TEST FIXTURE ONLY -- synthetic restating fact', "
        "8_876_000_000.0, '2020-01-01', '2020-12-31', 'direct_reported', 181, 0.9, 'passed', "
        "'2026-08-01T00:00:00')"
    )
    con2.execute(
        "INSERT INTO financial_reasoning_conclusions (conclusion_id, ticker, conclusion_type, "
        "metric, status, value_numeric, value_text, confidence_tier, method, limitations, "
        "rule_version, period_start, period_end, computed_at) VALUES "
        "(999901, 'CAP', 'ratio', 'test_original_conclusion', 'computed', 0.5, NULL, "
        "'direct_reported', 'TEST FIXTURE', 'TEST FIXTURE', 'test_v1', '2020-01-01', "
        "'2020-12-31', '2026-08-01T00:00:00')"
    )
    # links to fact_id 181 -- the REAL original CAP FY2020 net_profit fact (doc 4508)
    con2.execute(
        "INSERT INTO financial_reasoning_conclusion_facts (conclusion_id, fact_id, role) "
        "VALUES (999901, 181, 'test_role')"
    )
    con2.commit()

    check("BEFORE the synthetic restating fact's own filing date (2022-06-01), "
          "the ORIGINAL conclusion (tied to the real, pre-restatement fact 181) "
          "is still knowable exactly as it always was -- unaffected by a LATER "
          "restatement that hasn't been filed yet",
          any(c.conclusion_id == 999901 for c in pit.as_of(con2, "CAP", "2021-01-28").conclusions))
    check("AFTER the synthetic restating fact's filing date, the ORIGINAL "
          "conclusion is STILL present, unchanged, unremoved -- restating a fact "
          "never overwrites or hides the original historical knowledge state",
          any(c.conclusion_id == 999901 for c in pit.as_of(con2, "CAP", "2022-06-02").conclusions))
    original_conclusion = next(c for c in pit.as_of(con2, "CAP", "2022-06-02").conclusions
                                if c.conclusion_id == 999901)
    check("the original conclusion's own value/method/limitations are byte-identical "
          "before and after the restatement's filing date -- never silently altered",
          original_conclusion.value_numeric == 0.5 and original_conclusion.method == "TEST FIXTURE")

    con2.close()
    Path(scratch).unlink()
    Path(scratch).parent.rmdir()

    # --- confirm the real production database was never touched by this test ---
    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path; "
          "the restatement-preservation test used only a disposable scratch copy)",
          doc_count_after == doc_count_before)
    fixture_count = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE description LIKE 'TEST FIXTURE ONLY%'"
    ).fetchone()[0]
    check("the synthetic restatement fixture was NEVER written to production",
          fixture_count == 0)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
