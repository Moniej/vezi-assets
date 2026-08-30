"""Gate 2, P3: tests for the duration-comparability guard in
trend_classification.py (found investigating ELLAHLAKES's real 17-month
period) and the trend-side tabular-unit-check quarantine filter (a
separate gap from the ratio-side fix -- _base_fact_points() reads raw
facts directly and had no quarantine filter at all until this pass).

  PYTHONPATH=src python scripts/fre/test_trend_duration_guard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.trend_classification import classify_trends_for_ticker  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


def _setup(con, ticker: str, doc_id: int) -> None:
    con.execute("INSERT OR IGNORE INTO sources (source_id, name, kind) VALUES (1, 'test', 'manual_entry')")
    con.execute("INSERT OR IGNORE INTO securities (ticker, name) VALUES (?, ?)", (ticker, ticker))
    con.execute(
        "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, filing_date, "
        "retrieved_date, local_path, source_id, as_of_date) "
        "VALUES (?,?,?, 'results_notice', '2025-12-31', '2025-12-31', 'x', 1, '2025-12-31')",
        (doc_id, ticker, ticker))


def _fact(con, doc_id, fact_type, value, ps, pe, tabular="not_run"):
    con.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
        "period_start, period_end, period_type, extraction_confidence, extracted_at, "
        "currency, tabular_unit_check) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, fact_type, "t", value, ps, pe, None, 0.3, "2025-12-31", "NGN", tabular))


# --- Case 1: the real ELLAHLAKES shape -- a 17-month period adjacent to a
# normal 12-month period -- must be REFUSED (insufficient_data), not
# silently pct_change'd ---
p1 = db.new_scratch_db_path()
con1 = db.init_db(p1)
_setup(con1, "TESTDUR", 9101)
_fact(con1, 9101, "revenue", 100_000_000.0, "2023-01-01", "2023-12-31")   # normal FY, 365d
_fact(con1, 9101, "revenue", 146_658_000.0, "2024-08-01", "2025-12-31")  # 17-month, ~518d
con1.commit()
results1 = classify_trends_for_ticker(con1, "TESTDUR")
rev_trend_1 = [r for r in results1 if r.metric == "revenue"]
check("17-month vs 12-month period pair: exactly one trend row produced (attempted, not "
     "silently skipped)", len(rev_trend_1) == 1)
check("17-month vs 12-month period pair: REFUSED as insufficient_data, not computed as "
     "a distorted pct_change", len(rev_trend_1) == 1 and rev_trend_1[0].status == "insufficient_data")
check("refusal reason names both durations explicitly", len(rev_trend_1) == 1 and
     rev_trend_1[0].limitations and "duration" in rev_trend_1[0].limitations.lower())
check("value_numeric is None on a refused pair -- never a fabricated/distorted percent",
     len(rev_trend_1) == 1 and rev_trend_1[0].value_numeric is None)

# --- Case 2 (control): two normal, same-duration FY periods -- MUST still compute ---
p2 = db.new_scratch_db_path()
con2 = db.init_db(p2)
_setup(con2, "TESTOK", 9102)
_fact(con2, 9102, "revenue", 100_000_000.0, "2023-01-01", "2023-12-31")
_fact(con2, 9102, "revenue", 120_000_000.0, "2024-01-01", "2024-12-31")
con2.commit()
results2 = classify_trends_for_ticker(con2, "TESTOK")
rev_trend_2 = [r for r in results2 if r.metric == "revenue"]
check("control (two normal FY periods): trend DOES compute -- proves the guard is "
     "specific to a real duration mismatch, not a blanket refusal",
     len(rev_trend_2) == 1 and rev_trend_2[0].status == "computed")
check("control: pct_change is numerically correct (20% increase)",
     len(rev_trend_2) == 1 and abs(rev_trend_2[0].value_numeric - 20.0) < 1e-9)

# --- Case 3: a leap-year FY (366d) vs a normal FY (365d) -- tiny, legitimate
# calendar variance -- must NOT be refused ---
p3 = db.new_scratch_db_path()
con3 = db.init_db(p3)
_setup(con3, "TESTLEAP", 9103)
_fact(con3, 9103, "revenue", 100_000_000.0, "2023-01-01", "2023-12-31")  # 365d
_fact(con3, 9103, "revenue", 110_000_000.0, "2024-01-01", "2024-12-31")  # 2024 is a leap year, 366d
con3.commit()
results3 = classify_trends_for_ticker(con3, "TESTLEAP")
rev_trend_3 = [r for r in results3 if r.metric == "revenue"]
check("leap-year FY (366d) vs normal FY (365d): small real calendar variance is NOT "
     "treated as a comparability defect", len(rev_trend_3) == 1 and rev_trend_3[0].status == "computed")

# --- Case 4: a quarantined (tabular_unit_check='flag') raw fact must NOT
# leak into a trend via _base_fact_points -- the gap this pass fixed ---
p4 = db.new_scratch_db_path()
con4 = db.init_db(p4)
_setup(con4, "TESTQTREND", 9104)
_fact(con4, 9104, "revenue", 100_000.0, "2023-01-01", "2023-12-31", tabular="flag")   # quarantined
_fact(con4, 9104, "revenue", 120_000_000.0, "2024-01-01", "2024-12-31", tabular="pass")
con4.commit()
results4 = classify_trends_for_ticker(con4, "TESTQTREND")
rev_trend_4 = [r for r in results4 if r.metric == "revenue"]
check("a quarantined raw fact produces ZERO trend rows for that fact_type -- only one "
     "real (non-quarantined) point remains, not enough to form a pair, so classify_trends_"
     "for_ticker correctly finds nothing to compare rather than trending against a "
     "quarantined figure", len(rev_trend_4) == 0)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
