"""FSI Phase 22: Portfolio-Context Dossier CLI (docs/fre_runs/
fsi_phase22_preregistration.md).

A thin, read-only command-line wrapper around Phase 20's
`company_portfolio_context.as_of()`/`.render()`, called unmodified.
Mirrors Phase 12's `generate_research_dossier.py` pattern exactly. No
new reasoning, no new data, no LLM call, no database write of any
kind -- the optional `--output` flag writes only to a user-specified
file outside `data/ngx.sqlite`, never to the database itself.

  PYTHONPATH=src python scripts/fre/generate_portfolio_context_dossier.py --ticker NASCON --as-of 2026-08-02
  PYTHONPATH=src python scripts/fre/generate_portfolio_context_dossier.py --ticker NASCON --as-of 2026-08-02 --output dossier.md
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
from ngxrot.fre.company_portfolio_context import as_of, render  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Generate a deterministic, fully-cited institutional research "
                    "dossier for a single NGX ticker as of a given date, annotated with "
                    "its watchlist status and portfolio-memory cross-reference. "
                    "Read-only against the production database; writes nothing to it."
    )
    parser.add_argument("--ticker", required=True, help="NGX ticker symbol, e.g. NASCON")
    parser.add_argument("--as-of", required=True, dest="as_of_date",
                         help="Point-in-time cutoff date, YYYY-MM-DD. Only facts/"
                              "conclusions/relationships/watchlist entries publicly "
                              "known by this date are included. NOTE: the portfolio-"
                              "memory section is always LIVE, not point-in-time -- see "
                              "the rendered output's own disclosure.")
    parser.add_argument("--output", default=None,
                         help="Optional file path to also write the rendered dossier "
                              "to (Markdown). Without this flag, output goes to "
                              "stdout only -- no file is ever written.")
    args = parser.parse_args()

    try:
        date.fromisoformat(args.as_of_date)
    except ValueError:
        print(f"ERROR: --as-of {args.as_of_date!r} is not a valid date (expected YYYY-MM-DD).",
              file=sys.stderr)
        return 1

    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)

    ticker_exists = con.execute(
        "SELECT 1 FROM securities WHERE ticker = ?", (args.ticker,)
    ).fetchone()
    if ticker_exists is None:
        print(f"ERROR: unknown ticker {args.ticker!r} -- no matching row in securities.",
              file=sys.stderr)
        con.close()
        return 1

    annotated = as_of(con, args.ticker, args.as_of_date)
    rendered = render(annotated)
    con.close()

    print(rendered)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"\n(Dossier also written to: {output_path})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
