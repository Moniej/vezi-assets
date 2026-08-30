"""Tests for data_quality_monitoring.py -- real production data (copied
to scratch, never written back), plus synthetic cases for defect classes
that don't (yet, hopefully) exist in real production data.

  PYTHONPATH=src python scripts/fre/test_data_quality_monitoring.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.data_quality_monitoring import (  # noqa: E402
    check_conflicting_facts, check_duplicate_facts, check_pit_violations,
    check_quarantine_bypass, factor_eligible_tickers, run_all_checks, write_alerts)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


# --- real production data, copied to scratch, migrated ---
scratch_real = Path(tempfile.mkdtemp()) / "ngx_scratch.sqlite"
shutil.copy2(db.DEFAULT_DB, scratch_real)
con_real = db.init_db(scratch_real)

alerts_real = run_all_checks(con_real)
check("run_all_checks executes cleanly against real (copied) production data",
     isinstance(alerts_real, list))
print(f"  real-data alert count by check: "
     f"{ {c: sum(1 for a in alerts_real if a.check_name == c) for c in {a.check_name for a in alerts_real}} }")

critical_real = [a for a in alerts_real if a.severity == "critical"]
check("quarantine_bypass finds ZERO real violations against production data "
     "(the enforcement fix is actually holding, not just in unit tests)",
     sum(1 for a in alerts_real if a.check_name == "quarantine_bypass") == 0)
check("pit_violation finds ZERO real violations in production (period_end never "
     "after its own document's filing_date)",
     sum(1 for a in alerts_real if a.check_name == "pit_violation") == 0)

n_written = write_alerts(con_real, alerts_real)
check("write_alerts writes exactly len(alerts) rows", n_written == len(alerts_real))
check("written rows are queryable back from data_quality_alerts",
     con_real.execute("SELECT COUNT(*) FROM data_quality_alerts").fetchone()[0] == n_written)

eligible = factor_eligible_tickers(con_real)
computed_raw = {r[0] for r in con_real.execute(
    "SELECT DISTINCT ticker FROM financial_reasoning_conclusions WHERE status='computed'").fetchall()}
check("factor_eligible_tickers returns a subset of (or equal to) raw computed tickers",
     set(eligible) <= computed_raw)
print(f"  factor_eligible_tickers: {len(eligible)} / raw computed: {len(computed_raw)}")

# production untouched (this test only ever wrote to the scratch copy)
con_prod = db.connect()
check("production extracted_facts count unchanged (this test never opened production for write)",
     con_prod.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0] == 495)
check("production financial_reasoning_conclusions count unchanged",
     con_prod.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0] == 403)


# --- synthetic cases: duplicate facts ---
p2 = db.new_scratch_db_path()
con2 = db.init_db(p2)
con2.execute("INSERT OR IGNORE INTO sources (source_id, name, kind) VALUES (1,'t','manual_entry')")
con2.execute("INSERT OR IGNORE INTO securities (ticker, name) VALUES ('TESTDUP','TESTDUP')")
con2.execute("INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, filing_date, retrieved_date, "
            "local_path, source_id, as_of_date) VALUES (1,'TESTDUP','TESTDUP','results_notice',"
            "'2025-12-31','2025-12-31','x',1,'2025-12-31')")
for val in (100.0, 100.0):  # true duplicate, same value
    con2.execute("INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
                "period_start, period_end, period_type, extraction_confidence, extracted_at, currency) "
                "VALUES (1,'revenue','t',?,'2025-01-01','2025-12-31','FY',0.3,'2025-12-31','NGN')", (val,))
con2.commit()
dup_alerts = check_duplicate_facts(con2)
check("synthetic duplicate facts (same value, same period) detected", len(dup_alerts) == 1)

# --- synthetic: conflicting facts (different values, same period) ---
p3 = db.new_scratch_db_path()
con3 = db.init_db(p3)
con3.execute("INSERT OR IGNORE INTO sources (source_id, name, kind) VALUES (1,'t','manual_entry')")
con3.execute("INSERT OR IGNORE INTO securities (ticker, name) VALUES ('TESTCONF','TESTCONF')")
con3.execute("INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, filing_date, retrieved_date, "
            "local_path, source_id, as_of_date) VALUES (1,'TESTCONF','TESTCONF','results_notice',"
            "'2025-12-31','2025-12-31','x',1,'2025-12-31')")
for val in (100.0, 999.0):  # genuinely conflicting
    con3.execute("INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
                "period_start, period_end, period_type, extraction_confidence, extracted_at, currency) "
                "VALUES (1,'revenue','t',?,'2025-01-01','2025-12-31','FY',0.3,'2025-12-31','NGN')", (val,))
con3.commit()
conf_alerts = check_conflicting_facts(con3)
check("synthetic conflicting facts (different values, same period) detected",
     len(conf_alerts) == 1 and conf_alerts[0].severity == "critical")

# --- synthetic: PIT violation (period_end after filing_date) ---
p4 = db.new_scratch_db_path()
con4 = db.init_db(p4)
con4.execute("INSERT OR IGNORE INTO sources (source_id, name, kind) VALUES (1,'t','manual_entry')")
con4.execute("INSERT OR IGNORE INTO securities (ticker, name) VALUES ('TESTPIT','TESTPIT')")
con4.execute("INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, filing_date, retrieved_date, "
            "local_path, source_id, as_of_date) VALUES (1,'TESTPIT','TESTPIT','results_notice',"
            "'2025-06-30','2025-06-30','x',1,'2025-06-30')")
con4.execute("INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, "
            "period_start, period_end, period_type, extraction_confidence, extracted_at, currency) "
            "VALUES (1,'revenue','t',100.0,'2025-01-01','2025-12-31','FY',0.3,'2025-06-30','NGN')")
con4.commit()
pit_alerts = check_pit_violations(con4)
check("synthetic PIT violation (period_end after filing_date) detected",
     len(pit_alerts) == 1 and pit_alerts[0].severity == "critical")

# --- synthetic: quarantine bypass (the enforcement-of-enforcement check) ---
p5 = db.new_scratch_db_path()
con5 = db.init_db(p5)
con5.execute("INSERT OR IGNORE INTO sources (source_id, name, kind) VALUES (1,'t','manual_entry')")
con5.execute("INSERT OR IGNORE INTO securities (ticker, name) VALUES ('TESTBYPASS','TESTBYPASS')")
con5.execute("INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, filing_date, retrieved_date, "
            "local_path, source_id, as_of_date) VALUES (1,'TESTBYPASS','TESTBYPASS','results_notice',"
            "'2025-12-31','2025-12-31','x',1,'2025-12-31')")
fact_id = con5.execute(
    "INSERT INTO extracted_facts (doc_id, fact_type, description, numeric_value, period_start, "
    "period_end, period_type, extraction_confidence, extracted_at, currency, tabular_unit_check) "
    "VALUES (1,'revenue','t',100.0,'2025-01-01','2025-12-31','FY',0.3,'2025-12-31','NGN','flag')").lastrowid
conclusion_id = con5.execute(
    "INSERT INTO financial_reasoning_conclusions (ticker, conclusion_type, metric, status, "
    "value_numeric, method, limitations, rule_version, period_start, period_end, computed_at) VALUES "
    "('TESTBYPASS','ratio','net_margin','computed',0.5,'test','test','test_v1',"
    "'2025-01-01','2025-12-31','2025-12-31')"
).lastrowid
con5.execute("INSERT INTO financial_reasoning_conclusion_facts (conclusion_id, fact_id, role) "
            "VALUES (?,?,'numerator')", (conclusion_id, fact_id))
con5.commit()
bypass_alerts = check_quarantine_bypass(con5)
check("synthetic quarantine bypass (a flagged fact feeding a computed conclusion) IS detected "
     "-- proves this audit check actually works, not just that it finds nothing on clean data",
     len(bypass_alerts) == 1 and bypass_alerts[0].severity == "critical")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
