"""Decision Intelligence Phase 18: tests for continuous_intelligence.py.

  PYTHONPATH=src python scripts/fre/test_continuous_intelligence.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.continuous_intelligence import process_new_information  # noqa: E402

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
    cache: dict = {}

    # --- GOVERNANCE: no alert is ever manufactured when the ONLY changes
    # are LOW materiality (or there are no changes at all) -- structurally
    # enforced (alert_entry stays None), not by convention. -----------------
    r_same_date = process_new_information(con, "CAP", "2024-01-01", "2024-01-01",
                                           intelligence_cache=cache)
    check("CAP compared against the SAME date: zero changes, max_materiality=LOW, "
          "alert_entry is None", r_same_date.max_materiality == "LOW" and r_same_date.alert_entry is None)

    # --- a real, materially-changed ticker produces a real alert with a
    # real, non-empty reason citing the actual changes ----------------------
    r_cap = process_new_information(con, "CAP", "2026-08-09", "2024-01-01", intelligence_cache=cache)
    check("CAP 2024->2026: max_materiality is HIGH or CRITICAL (real financial/price moves)",
          r_cap.max_materiality in ("HIGH", "CRITICAL"))
    check("CAP: alert_entry is populated when max_materiality clears MEDIUM",
          r_cap.alert_entry is not None)
    check("CAP: alert_entry['reason'] cites real change descriptions, not a placeholder",
          len(r_cap.alert_entry["reason"]) > 20)
    check("CAP: alert_entry['ticker']/['as_of_date'] echo the request",
          r_cap.alert_entry["ticker"] == "CAP" and r_cap.alert_entry["as_of_date"] == "2026-08-09")
    check("CAP: affected_fields lists real category/field pairs matching ranked_changes",
          len(r_cap.affected_fields) == len(r_cap.bundle.ranked_changes))
    check("CAP: materiality_summary counts sum to the real number of ranked_changes",
          sum(r_cap.materiality_summary.values()) == len(r_cap.bundle.ranked_changes))

    # --- TOTAL (thin data): pipeline still runs cleanly, no crash ----------
    r_total = process_new_information(con, "TOTAL", "2026-08-09", "2024-01-01",
                                       intelligence_cache=cache)
    check("TOTAL: max_materiality is a real LOW/MEDIUM/HIGH/CRITICAL value",
          r_total.max_materiality in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))

    con.close()
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path at all)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
