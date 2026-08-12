"""CLI for the alert queue (schema.sql's `alerts` table, populated by
scripts/run_continuous_intelligence.py). Added 2026-08-11 (HANDOFF.md,
Priority 8: product/API exposure) -- the monitoring orchestration built
last phase had a write path but no way to view or acknowledge what it
produced except raw SQL.

Usage:
  PYTHONPATH=src python scripts/ngxrot_alerts.py list [--unacknowledged] [--ticker GTCO] [--limit 20]
  PYTHONPATH=src python scripts/ngxrot_alerts.py show --id 3
  PYTHONPATH=src python scripts/ngxrot_alerts.py acknowledge --id 3 --by "your name"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402


def cmd_list(con, args) -> None:
    clauses, params = [], []
    if args.unacknowledged:
        clauses.append("acknowledged_at IS NULL")
    if args.ticker:
        clauses.append("ticker = ?")
        params.append(args.ticker)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = con.execute(
        f"SELECT alert_id, ticker, as_of_date, max_materiality, requires_dossier_review, "
        f"acknowledged_at, reason FROM alerts {where} ORDER BY generated_at DESC LIMIT ?",
        (*params, args.limit)).fetchall()
    if not rows:
        print("(no alerts match)")
        return
    for alert_id, ticker, as_of_date, materiality, requires_review, ack, reason in rows:
        status = "ACKNOWLEDGED" if ack else "OPEN"
        review = " [dossier review required]" if requires_review else ""
        print(f"[{alert_id}] {ticker}  {as_of_date}  {materiality}  {status}{review}")
        print(f"    {reason[:200]}{'...' if len(reason) > 200 else ''}")


def cmd_show(con, args) -> None:
    row = con.execute(
        "SELECT alert_id, run_id, ticker, as_of_date, prior_date, max_materiality, reason, "
        "requires_dossier_review, generated_at, acknowledged_at, acknowledged_by "
        "FROM alerts WHERE alert_id = ?", (args.id,)).fetchone()
    if row is None:
        print(f"no alert {args.id}", file=sys.stderr)
        sys.exit(1)
    cols = ["alert_id", "run_id", "ticker", "as_of_date", "prior_date", "max_materiality", "reason",
           "requires_dossier_review", "generated_at", "acknowledged_at", "acknowledged_by"]
    for c, v in zip(cols, row):
        print(f"{c}: {v}")


def cmd_acknowledge(con, args) -> None:
    row = con.execute("SELECT acknowledged_at FROM alerts WHERE alert_id = ?", (args.id,)).fetchone()
    if row is None:
        print(f"no alert {args.id}", file=sys.stderr)
        sys.exit(1)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Conditional UPDATE + rowcount check, not a separate read-then-write
    # (fixed 2026-08-12, production-reliability audit): the prior SELECT-
    # then-UPDATE let two concurrent `acknowledge` calls for the same
    # alert_id both pass the None-check and the second would silently
    # overwrite the first's acknowledged_by/acknowledged_at with no
    # indication a race happened. This UPDATE only succeeds if
    # acknowledged_at is still NULL at the moment it runs.
    cur = con.execute(
        "UPDATE alerts SET acknowledged_at = ?, acknowledged_by = ? "
        "WHERE alert_id = ? AND acknowledged_at IS NULL",
        (now, args.by, args.id))
    con.commit()
    if cur.rowcount == 0:
        current = con.execute("SELECT acknowledged_at FROM alerts WHERE alert_id = ?",
                              (args.id,)).fetchone()[0]
        print(f"alert {args.id} already acknowledged at {current}", file=sys.stderr)
        sys.exit(1)
    print(f"alert {args.id} acknowledged by {args.by!r} at {now}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list", help="list alerts")
    sp.add_argument("--unacknowledged", action="store_true")
    sp.add_argument("--ticker", default=None)
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="show one alert in full")
    sp.add_argument("--id", type=int, required=True)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("acknowledge", help="mark an alert acknowledged")
    sp.add_argument("--id", type=int, required=True)
    sp.add_argument("--by", required=True)
    sp.set_defaults(func=cmd_acknowledge)

    args = p.parse_args()
    con = db.connect()
    try:
        args.func(con, args)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
