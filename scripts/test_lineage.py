"""Tests for src/ngxrot/lineage.py -- proves the lineage chain is real,
traceable, and reflects this session's own findings (not fabricated).

  PYTHONPATH=src python scripts/test_lineage.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.lineage import trace_equity_observation  # noqa: E402

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

    # --- a resolved, flagged observation: CILEASING's bonus-issue jump ----
    lin = trace_equity_observation(con, "CILEASING", "2024-01-05")
    check("CILEASING 2024-01-05: observation found", lin.found)
    check("CILEASING 2024-01-05: source resolved to a real sources row",
          lin.source_name is not None and lin.source_kind is not None)
    check("CILEASING 2024-01-05: ingestion_run composite id populated",
          lin.ingestion_run is not None and ":" in lin.ingestion_run)
    check("CILEASING 2024-01-05: validation picks up the unadjusted_jump flag logged this session",
          any(f["check_name"] == "unadjusted_jump" for f in lin.validation_flags))
    # Real finding, not a bug: the pre-existing corporate_action_audit.py
    # tool has independently logged the SAME 'unexplained_jump' for this
    # observation 150+ times since 2026-07-21, every one still
    # resolved=0. This session's new 'unadjusted_jump' (resolved=1) does
    # not retroactively resolve those pre-existing entries -- so the
    # honest combined status is still flagged_unresolved. Disclosed in
    # the final report rather than silently reconciled here.
    check("CILEASING 2024-01-05: validation_status is flagged_unresolved (pre-existing "
          "unexplained_jump entries from corporate_action_audit.py remain unresolved even "
          "though this session's own unadjusted_jump entry explains the cause)",
          lin.validation_status == "flagged_unresolved"
          and any(f["check_name"] == "unexplained_jump" and not f["resolved"] for f in lin.validation_flags))

    # --- an unresolved, flagged observation: REDSTAREX stale window --------
    lin2 = trace_equity_observation(con, "REDSTAREX", "2026-05-11")
    check("REDSTAREX 2026-05-11: observation found", lin2.found)
    check("REDSTAREX 2026-05-11: validation picks up the stale_series flag logged this session",
          any(f["check_name"] == "stale_series" for f in lin2.validation_flags))
    check("REDSTAREX 2026-05-11: validation_status reflects unresolved",
          lin2.validation_status == "flagged_unresolved")

    # --- a clean observation with no flags at all ---------------------------
    lin3 = trace_equity_observation(con, "DANGCEM", "2024-06-03")
    if lin3.found:
        check("DANGCEM 2024-06-03: clean observation reports no_flags_found",
              lin3.validation_status == "no_flags_found")
    else:
        print("[SKIP] DANGCEM 2024-06-03 not present in this DB -- skipping clean-case check")

    # --- a nonexistent observation never crashes or fabricates -------------
    lin4 = trace_equity_observation(con, "NOTATICKER", "1999-01-01")
    check("nonexistent observation: found=False, no fabricated fields",
          lin4.found is False and lin4.source_id is None)

    con.close()
    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
