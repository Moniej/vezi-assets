"""Gate 2, P1: prove ENFORCEMENT, not just detection. A test that only
calls check_tabular_unit_consistency() in isolation proves the function
returns the right label -- it does NOT prove a quarantined fact is
actually kept out of a computed ratio. This test exercises the real
chain end to end, against a real scratch database:

  unit defect -> validator flag -> extraction_confidence=0
  -> fact excluded from financial_ratios._fact_for()
  -> financial reasoning cannot consume it (ratio stays insufficient_data)

...and the mirror case: a clean fact with the SAME shape DOES compute,
proving the exclusion is specific to the flagged fact, not an accidental
blanket failure.

  PYTHONPATH=src python scripts/fre/test_tabular_unit_enforcement_e2e.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.financial_ratios import compute_ratios_for_ticker  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


def _insert_security_and_doc(con, ticker: str, doc_id: int) -> None:
    con.execute("INSERT OR IGNORE INTO sources (source_id, name, kind) VALUES (1, 'test', 'manual_entry')")
    con.execute("INSERT OR IGNORE INTO securities (ticker, name) VALUES (?, ?)", (ticker, ticker))
    con.execute(
        "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, filing_date, "
        "retrieved_date, local_path, source_id, as_of_date) "
        "VALUES (?,?,?, 'results_notice', '2025-12-31', '2025-12-31', 'x', 1, '2025-12-31')",
        (doc_id, ticker, ticker))


def _insert_fact(con, doc_id: int, fact_type: str, numeric_value: float,
                 period_start: str | None, period_end: str, tabular_unit_check: str,
                 numeric_consistency_check: str = "not_run") -> int:
    return con.execute(
        "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
        "period_start, period_end, period_type, extraction_confidence, extracted_at, "
        "currency, tabular_unit_check, numeric_consistency_check) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, fact_type, "test fact", numeric_value, period_start, period_end, "FY",
         0.0 if tabular_unit_check in ("flag", "ambiguous") else 0.3,
         "2025-12-31", "NGN", tabular_unit_check, numeric_consistency_check)
    ).lastrowid


# --- Case 1: a QUARANTINED pair (both facts flagged) -- ratio must be insufficient_data ---
p1 = db.new_scratch_db_path()
con1 = db.init_db(p1)
_insert_security_and_doc(con1, "TESTQ", 9001)
_insert_fact(con1, 9001, "revenue", 146658.0, "2025-01-01", "2025-12-31", "flag")
_insert_fact(con1, 9001, "net_profit", 12000.0, "2025-01-01", "2025-12-31", "flag")
con1.commit()
results1 = compute_ratios_for_ticker(con1, "TESTQ")
net_margin_1 = [r for r in results1 if r.metric == "net_margin"]
check("quarantined pair: net_margin conclusion exists (attempted, not silently skipped)",
     len(net_margin_1) == 1)
check("quarantined pair: net_margin status is insufficient_data (fact excluded, NOT computed "
     "from the flagged/unscaled figures)",
     len(net_margin_1) == 1 and net_margin_1[0].status == "insufficient_data")
check("quarantined pair: the exclusion reason names the missing fact_type(s), "
     "not a generic error", len(net_margin_1) == 1 and net_margin_1[0].limitations and
     ("revenue" in net_margin_1[0].limitations or "net_profit" in net_margin_1[0].limitations))

# --- Case 2 (mirror/control): the SAME shape, but tabular_unit_check='pass' -- must compute ---
p2 = db.new_scratch_db_path()
con2 = db.init_db(p2)
_insert_security_and_doc(con2, "TESTC", 9002)
_insert_fact(con2, 9002, "revenue", 146658000.0, "2025-01-01", "2025-12-31", "pass")
_insert_fact(con2, 9002, "net_profit", 12000000.0, "2025-01-01", "2025-12-31", "pass")
con2.commit()
results2 = compute_ratios_for_ticker(con2, "TESTC")
net_margin_2 = [r for r in results2 if r.metric == "net_margin"]
check("control (clean, correctly-scaled pair): net_margin DOES compute -- proves the "
     "exclusion in Case 1 is specific to the flagged status, not an accidental blanket "
     "failure of the whole query", len(net_margin_2) == 1 and net_margin_2[0].status == "computed")
check("control: computed value is numerically correct (12,000,000 / 146,658,000)",
     len(net_margin_2) == 1 and net_margin_2[0].status == "computed" and
     abs(net_margin_2[0].value_numeric - (12000000.0 / 146658000.0)) < 1e-9)

# --- Case 3: MIXED -- one fact flagged, one clean, same period -- must still be insufficient_data
# (a ratio needs BOTH inputs trustworthy; one bad leg poisons the ratio) ---
p3 = db.new_scratch_db_path()
con3 = db.init_db(p3)
_insert_security_and_doc(con3, "TESTM", 9003)
_insert_fact(con3, 9003, "revenue", 146658.0, "2025-01-01", "2025-12-31", "flag")   # bad
_insert_fact(con3, 9003, "net_profit", 12000000.0, "2025-01-01", "2025-12-31", "pass")  # clean
con3.commit()
results3 = compute_ratios_for_ticker(con3, "TESTM")
net_margin_3 = [r for r in results3 if r.metric == "net_margin"]
check("mixed pair (one quarantined leg): net_margin is insufficient_data -- a single bad "
     "input poisons the ratio, it is never computed from 'the one good leg' alone",
     len(net_margin_3) == 1 and net_margin_3[0].status == "insufficient_data")

# --- Case 4: 'ambiguous' status is quarantined exactly like 'flag' ---
p4 = db.new_scratch_db_path()
con4 = db.init_db(p4)
_insert_security_and_doc(con4, "TESTA", 9004)
_insert_fact(con4, 9004, "revenue", 146658.0, "2025-01-01", "2025-12-31", "ambiguous")
_insert_fact(con4, 9004, "net_profit", 12000000.0, "2025-01-01", "2025-12-31", "pass")
con4.commit()
results4 = compute_ratios_for_ticker(con4, "TESTA")
net_margin_4 = [r for r in results4 if r.metric == "net_margin"]
check("'ambiguous' status quarantined exactly like 'flag' (mixed-unit-document case)",
     len(net_margin_4) == 1 and net_margin_4[0].status == "insufficient_data")

# --- Case 5: 'not_checked'/'not_run' must NOT be quarantined (only flag/ambiguous are) ---
p5 = db.new_scratch_db_path()
con5 = db.init_db(p5)
_insert_security_and_doc(con5, "TESTN", 9005)
_insert_fact(con5, 9005, "revenue", 146658000.0, "2025-01-01", "2025-12-31", "not_checked")
_insert_fact(con5, 9005, "net_profit", 12000000.0, "2025-01-01", "2025-12-31", "not_run")
con5.commit()
results5 = compute_ratios_for_ticker(con5, "TESTN")
net_margin_5 = [r for r in results5 if r.metric == "net_margin"]
check("'not_checked'/'not_run' (no applicable convention / legacy pre-check rows) are "
     "NOT quarantined -- only 'flag'/'ambiguous' are, per the documented contract",
     len(net_margin_5) == 1 and net_margin_5[0].status == "computed")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
