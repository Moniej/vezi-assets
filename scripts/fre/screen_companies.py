"""FSI Phase 15: Screening CLI (docs/fre_runs/fsi_phase15_preregistration.md).

A thin, read-only command-line wrapper around Phase 14's
`screen_by_flag()`/`screen_by_trend()`, called unmodified. No new
reasoning, no new data, no LLM call, no database write of any kind.
Mirrors Phase 12's `generate_research_dossier.py` pattern exactly
(UTF-8 stdout/stderr from the start, argparse `choices=` validation,
clear errors instead of raw tracebacks).

  PYTHONPATH=src python scripts/fre/screen_companies.py flag --metric leverage_increasing --fired true --as-of 2026-08-02
  PYTHONPATH=src python scripts/fre/screen_companies.py trend --metric net_profit --direction decreasing --as-of 2026-08-02
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.screening import (  # noqa: E402
    KNOWN_FLAG_METRICS, KNOWN_TREND_METRICS, _VALID_DIRECTIONS,
    screen_by_flag, screen_by_trend,
)


def _print_matches(matches) -> None:
    if not matches:
        print("No matches.")
        return
    for m in matches:
        period = f"{m.period_start}..{m.period_end}" if m.period_start else "(no period)"
        tier = m.confidence_tier if m.confidence_tier is not None else "NOT RECORDED"
        print(f"{m.ticker}: {m.metric}={m.value_text} period={period} "
              f"confidence_tier={tier} conclusion_id={m.conclusion_id}")
        print(f"    method: {m.method}")
        print(f"    limitations: {m.limitations}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Screen all real NGX tickers for a categorical financial-reasoning "
                    "criterion (a fired/not-fired health flag, or a trend direction), "
                    "as of a given point-in-time date. Read-only against the production "
                    "database; writes nothing to it. Descriptive filtering only -- never "
                    "a ranking, score, or recommendation."
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    flag_parser = sub.add_parser("flag", help="Screen by health-flag fired status")
    flag_parser.add_argument("--metric", required=True, choices=KNOWN_FLAG_METRICS)
    flag_parser.add_argument("--fired", required=True, choices=("true", "false"))
    flag_parser.add_argument("--as-of", required=True, dest="as_of_date")

    trend_parser = sub.add_parser("trend", help="Screen by trend direction")
    trend_parser.add_argument("--metric", required=True, choices=KNOWN_TREND_METRICS)
    trend_parser.add_argument("--direction", required=True, choices=_VALID_DIRECTIONS)
    trend_parser.add_argument("--as-of", required=True, dest="as_of_date")

    args = parser.parse_args()

    try:
        date.fromisoformat(args.as_of_date)
    except ValueError:
        print(f"ERROR: --as-of {args.as_of_date!r} is not a valid date (expected YYYY-MM-DD).",
              file=sys.stderr)
        return 1

    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)

    if args.mode == "flag":
        matches = screen_by_flag(con, args.metric, args.fired == "true", args.as_of_date)
    else:
        matches = screen_by_trend(con, args.metric, args.direction, args.as_of_date)

    con.close()
    _print_matches(matches)
    return 0


if __name__ == "__main__":
    sys.exit(main())
