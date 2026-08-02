"""FSI Phase 12: Operational Research Dossier Generation
(docs/fre_runs/fsi_phase12_preregistration.md,
docs/fre_runs/fsi_phase12_implementation_log.md).

A thin, read-only command-line wrapper around Phase 11's
`build_dossier()`/`render_dossier()`, called unmodified. No new
reasoning, no new data, no LLM call, no database write of any kind --
the optional `--output` flag writes only to a user-specified file
outside `data/ngx.sqlite`, never to the database itself.

  PYTHONPATH=src python scripts/fre/generate_research_dossier.py --ticker NASCON --as-of 2026-08-02
  PYTHONPATH=src python scripts/fre/generate_research_dossier.py --ticker NASCON --as-of 2026-08-02 --output dossier.md
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
from ngxrot.fre.company_research_dossier import build_dossier, render_dossier  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic, fully-cited institutional research "
                    "dossier for a single NGX ticker as of a given date. Read-only "
                    "against the production database; writes nothing to it."
    )
    parser.add_argument("--ticker", required=True, help="NGX ticker symbol, e.g. NASCON")
    parser.add_argument("--as-of", required=True, dest="as_of_date",
                        help="Point-in-time cutoff date, YYYY-MM-DD. Only facts/"
                             "conclusions/relationships publicly known by this date "
                             "are included.")
    parser.add_argument("--output", default=None,
                        help="Optional file path to also write the rendered dossier "
                             "to (Markdown). Without this flag, output goes to "
                             "stdout only -- no file is ever written.")
    args = parser.parse_args()

    # Real filing text contains non-ASCII characters (the Naira sign, U+20A6,
    # appears verbatim in several real source documents -- e.g. BUAFOODS's
    # own filings). A subprocess launched under Windows' default console
    # codepage (cp1252) cannot print these via a plain print() call, raising
    # UnicodeEncodeError -- a real bug found while testing this script,
    # fixed by forcing UTF-8 on stdout/stderr regardless of the calling
    # environment's own console codepage.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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

    dossier = build_dossier(con, args.ticker, args.as_of_date)
    rendered = render_dossier(dossier)
    con.close()

    print(rendered)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"\n(Dossier also written to: {output_path})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
