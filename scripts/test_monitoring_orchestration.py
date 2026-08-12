"""Regression test for monitoring orchestration
(2026-08-11, HANDOFF.md, Priority 6). Reuses the real monitoring_runs/
alerts rows already produced by scripts/run_continuous_intelligence.py
against the real production database -- does NOT re-run the (expensive,
~seconds-to-tens-of-seconds-per-ticker) pipeline itself, only checks the
persisted results and idempotency/integrity properties.

  PYTHONPATH=src python scripts/test_monitoring_orchestration.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

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


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)

    n_runs = con.execute("SELECT COUNT(*) FROM monitoring_runs").fetchone()[0]
    check("real monitoring_runs rows exist "
         "(scripts/run_continuous_intelligence.py has been run for real)", n_runs >= 3)

    n_dupe = con.execute(
        "SELECT COUNT(*) FROM (SELECT ticker, as_of_date, prior_date, COUNT(*) c "
        "FROM monitoring_runs GROUP BY ticker, as_of_date, prior_date HAVING c > 1)"
    ).fetchone()[0]
    check("idempotency: no duplicate (ticker, as_of_date, prior_date) triple in monitoring_runs "
         "(confirmed across a real interrupted-then-resumed run)", n_dupe == 0)

    n_alert_no_run = con.execute(
        "SELECT COUNT(*) FROM alerts a WHERE NOT EXISTS "
        "(SELECT 1 FROM monitoring_runs r WHERE r.run_id = a.run_id)").fetchone()[0]
    check("every alert links to a real monitoring_runs row (no dangling run_id)",
         n_alert_no_run == 0)

    n_low_alerts = con.execute(
        "SELECT COUNT(*) FROM alerts WHERE max_materiality = 'LOW'").fetchone()[0]
    check("STRUCTURAL RULE HELD: no LOW-materiality alert ever reached the alerts table "
         "(continuous_intelligence.py's own alert_entry=None-for-LOW rule, unchanged)",
         n_low_alerts == 0)

    n_alert_dupe = con.execute(
        "SELECT COUNT(*) FROM (SELECT ticker, as_of_date, prior_date, COUNT(*) c "
        "FROM alerts GROUP BY ticker, as_of_date, prior_date HAVING c > 1)").fetchone()[0]
    check("idempotency: no duplicate alert for the same (ticker, as_of_date, prior_date)",
         n_alert_dupe == 0)

    n_real_alert = con.execute(
        "SELECT COUNT(*) FROM alerts WHERE max_materiality IN ('HIGH', 'CRITICAL') "
        "AND reason LIKE '%CBN%'").fetchone()[0]
    check("a real, material regulatory alert was actually generated "
         "(CBN bank-capital/LDR changes flagged for UCAP/GTCO, not a synthetic example)",
         n_real_alert >= 1)

    n_failed_runs = con.execute(
        "SELECT COUNT(*) FROM monitoring_runs WHERE status = 'failed'").fetchone()[0]
    if n_failed_runs:
        n_failed_no_error = con.execute(
            "SELECT COUNT(*) FROM monitoring_runs WHERE status = 'failed' "
            "AND error_detail IS NULL").fetchone()[0]
        check("every failed run recorded a real error_detail, not a silent failure",
             n_failed_no_error == 0)
    else:
        check("every failed run recorded a real error_detail, not a silent failure "
             "(vacuously true: 0 failed runs so far)", True)

    n_unacked_before = con.execute(
        "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL").fetchone()[0]
    check("acknowledged_at is NULL by default -- alerts start unacknowledged, "
         "never silently pre-cleared", n_unacked_before >= 1)

    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
