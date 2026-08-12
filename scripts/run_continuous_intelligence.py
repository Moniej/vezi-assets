"""Monitoring orchestration (2026-08-11, HANDOFF.md, Priority 6).

Wraps the EXISTING deterministic pipeline in
src/ngxrot/fre/continuous_intelligence.py (Phase 18: change detection ->
materiality assessment -> alert entry) with the persistence/scheduling
layer it never had. No change to that module's logic -- this script is
the "trigger that would call it" its own docstring says doesn't exist yet.

This platform has no job scheduler/file-watcher/webhook receiver, and
building one is out of scope (per the standing "don't overengineer"
instruction -- no cron daemon, no event bus). This script is the thing
an EXTERNAL scheduler (cron, Windows Task Scheduler, a CI job) would
invoke on a cadence -- reliability (idempotency, retry-safety, logging,
resumability) over complexity, matching every other operational script
on this platform (daily_capture.py, run_phase_c_pilot.py).

For each ticker:
  1. prior_date = the ticker's last successful monitoring_runs.as_of_date,
     or (as_of_date - lookback_days) if this is the ticker's first run.
  2. Skip (idempotent) if a run already exists for this exact
     (ticker, as_of_date, prior_date) triple -- enforced at the DB level
     too (UNIQUE constraint), this is just avoiding a noisy retry.
  3. Call process_new_information() -- pure, deterministic, no LLM call.
  4. Record the run (completed/failed) in monitoring_runs; a real error on
     one ticker is logged and the batch continues to the next ticker,
     never aborts (same pattern as run_phase_c_pilot.py).
  5. If alert_entry is not None (materiality >= MEDIUM), record it in
     alerts. LOW-materiality runs are logged in monitoring_runs but never
     become an alert -- continuous_intelligence.py's own structural rule.

  PYTHONPATH=src python scripts/run_continuous_intelligence.py [--tickers T1,T2] [--as-of YYYY-MM-DD] [--lookback-days 30] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.continuous_intelligence import process_new_information  # noqa: E402


def _default_universe(con) -> list[str]:
    """Tickers with real document coverage -- the same population every
    FRE coverage report has already been assessed against, not an
    arbitrary/invented list."""
    return [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM documents WHERE ticker IS NOT NULL "
        "ORDER BY ticker").fetchall()]


def _prior_date_for(con, ticker: str, as_of_date: str, lookback_days: int) -> str:
    row = con.execute(
        "SELECT MAX(as_of_date) FROM monitoring_runs WHERE ticker = ? AND status = 'completed' "
        "AND as_of_date < ?", (ticker, as_of_date)).fetchone()
    if row and row[0]:
        return row[0]
    fallback = (date.fromisoformat(as_of_date) - timedelta(days=lookback_days)).isoformat()
    return fallback


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tickers", default=None, help="comma-separated ticker list; "
                                                    "omit to use every ticker with real document coverage")
    p.add_argument("--as-of", dest="as_of", default=None,
                   help="YYYY-MM-DD; defaults to today (UTC)")
    p.add_argument("--lookback-days", type=int, default=30,
                   help="prior_date fallback for a ticker's first-ever run (default 30)")
    p.add_argument("--dry-run", action="store_true", help="report what would run, write nothing")
    args = p.parse_args()

    con = db.init_db()
    as_of_date = args.as_of or datetime.now(timezone.utc).date().isoformat()
    tickers = args.tickers.split(",") if args.tickers else _default_universe(con)

    # Shared across every ticker in this run (fixed 2026-08-11, HANDOFF.md):
    # process_new_information's own intelligence_cache parameter exists
    # specifically to amortize expensive shared computation (e.g. the
    # price panel) across a batch -- measured directly before this fix,
    # NASCON alone took ~84s with a fresh cache every call; with one cache
    # dict shared across the whole run, a second ticker dropped to ~3s.
    # Never passing a cache made every batch run pay the cold-cache cost
    # on every single ticker.
    intelligence_cache: dict = {}

    n_completed, n_failed, n_skipped, n_alerts = 0, 0, 0, 0
    for ticker in tickers:
        prior_date = _prior_date_for(con, ticker, as_of_date, args.lookback_days)

        existing = con.execute(
            "SELECT 1 FROM monitoring_runs WHERE ticker = ? AND as_of_date = ? AND prior_date = ?",
            (ticker, as_of_date, prior_date)).fetchone()
        if existing:
            n_skipped += 1
            continue

        if args.dry_run:
            print(f"would run: {ticker} prior={prior_date} as_of={as_of_date}")
            continue

        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            result = process_new_information(con, ticker, as_of_date, prior_date,
                                              intelligence_cache=intelligence_cache,
                                              include_portfolio_note=False)
            completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            run_id = con.execute(
                "INSERT INTO monitoring_runs (ticker, as_of_date, prior_date, status, "
                "max_materiality, n_changes, started_at, completed_at) VALUES (?,?,?,?,?,?,?,?)",
                (ticker, as_of_date, prior_date, "completed", result.max_materiality,
                 len(result.affected_fields), started_at, completed_at)).lastrowid
            if result.alert_entry is not None:
                a = result.alert_entry
                con.execute(
                    "INSERT INTO alerts (run_id, ticker, as_of_date, prior_date, max_materiality, "
                    "reason, requires_dossier_review, generated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (run_id, ticker, as_of_date, prior_date, a["max_materiality"], a["reason"],
                     int(a["requires_dossier_review"]), completed_at))
                n_alerts += 1
            con.commit()
            n_completed += 1
        except Exception as e:  # noqa: BLE001 -- one ticker's failure must never abort the batch
            con.rollback()
            completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            con.execute(
                "INSERT INTO monitoring_runs (ticker, as_of_date, prior_date, status, "
                "error_detail, started_at, completed_at) VALUES (?,?,?,?,?,?,?)",
                (ticker, as_of_date, prior_date, "failed",
                 f"{e!r}\n{traceback.format_exc(limit=3)}", started_at, completed_at))
            con.commit()
            n_failed += 1
            print(f"FAILED: {ticker} -- {e!r}", file=sys.stderr)

    print(f"\nmonitoring run as_of={as_of_date}: {n_completed} completed, {n_failed} failed, "
         f"{n_skipped} skipped (idempotent), {n_alerts} alerts generated")
    if not args.dry_run:
        n_unacked = con.execute(
            "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL").fetchone()[0]
        print(f"alerts: {n_unacked} total unacknowledged in the queue")

    con.close()
    return 1 if n_failed else 0


if __name__ == "__main__":
    sys.exit(main())
