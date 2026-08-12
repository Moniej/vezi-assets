"""Regression test for scripts/ngxrot_alerts.py (2026-08-11, HANDOFF.md,
Priority 8). Tests the CLI's command functions directly (not via
subprocess against the real database) using a SCRATCH sqlite connection
-- alert acknowledgment is a one-way, real-world-meaningful state change
(it means "a human reviewed this") and must never be exercised against
real alerts (a real alert was accidentally acknowledged and had to be
manually reverted while building this feature -- see HANDOFF.md; this
test exists specifically so that mistake is never repeated).

  PYTHONPATH=src python scripts/test_alerts_cli.py
"""
from __future__ import annotations

import argparse
import io
import sqlite3
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import ngxrot_alerts as cli  # noqa: E402

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


def make_scratch_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE alerts (
        alert_id INTEGER PRIMARY KEY, run_id INTEGER, ticker TEXT, as_of_date TEXT,
        prior_date TEXT, max_materiality TEXT, reason TEXT, requires_dossier_review INTEGER,
        generated_at TEXT, acknowledged_at TEXT, acknowledged_by TEXT)""")
    con.execute("INSERT INTO alerts VALUES (1,1,'TESTCO','2026-08-01','2026-07-01','HIGH',"
               "'test reason A',1,'2026-08-01T00:00:00',NULL,NULL)")
    con.execute("INSERT INTO alerts VALUES (2,1,'OTHERCO','2026-08-01','2026-07-01','CRITICAL',"
               "'test reason B',0,'2026-08-01T00:00:00','2026-08-02T00:00:00','a reviewer')")
    con.commit()
    return con


def main() -> int:
    con = make_scratch_db()

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.cmd_list(con, argparse.Namespace(unacknowledged=False, ticker=None, limit=20))
    out = buf.getvalue()
    check("list: shows both alerts", "TESTCO" in out and "OTHERCO" in out)
    check("list: correctly labels the unacknowledged one OPEN", "[1] TESTCO" in out and "OPEN" in out)
    check("list: correctly labels the acknowledged one ACKNOWLEDGED", "ACKNOWLEDGED" in out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.cmd_list(con, argparse.Namespace(unacknowledged=True, ticker=None, limit=20))
    out = buf.getvalue()
    check("list --unacknowledged: shows only the open alert", "TESTCO" in out and "OTHERCO" not in out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.cmd_show(con, argparse.Namespace(id=1))
    out = buf.getvalue()
    check("show: prints every real field for the requested alert",
         "ticker: TESTCO" in out and "max_materiality: HIGH" in out)

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.cmd_acknowledge(con, argparse.Namespace(id=1, by="test-reviewer"))
    row = con.execute("SELECT acknowledged_at, acknowledged_by FROM alerts WHERE alert_id=1").fetchone()
    check("acknowledge: sets acknowledged_at/acknowledged_by on the scratch DB",
         row[0] is not None and row[1] == "test-reviewer")

    try:
        cli.cmd_acknowledge(con, argparse.Namespace(id=1, by="someone-else"))
        check("acknowledge: re-acknowledging an already-acknowledged alert is rejected (exits)", False)
    except SystemExit as e:
        check("acknowledge: re-acknowledging an already-acknowledged alert is rejected (exits)",
             e.code == 1)

    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
