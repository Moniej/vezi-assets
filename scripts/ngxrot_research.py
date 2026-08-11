"""CLI for the Research Query Layer (src/ngxrot/research_query.py) --
thin wrapper, no new infrastructure. Follows this repo's own established
convention of operational scripts living under scripts/ (e.g.
scripts/ngxpulse_ingest.py), not a new package-level CLI framework.

Reads the REAL production database (data/ngx.sqlite) read-only, and logs
every execution to the REAL registry.sqlite by default -- pass --no-log
to skip logging (e.g. for a rehearsal/demo run).

Usage:
  PYTHONPATH=src python scripts/ngxrot_research.py prices --symbol GTCO --from 2023-01-01 --to 2025-01-01
  PYTHONPATH=src python scripts/ngxrot_research.py sector --sector "CONSUMER GOODS" --as-of 2025-01-01
  PYTHONPATH=src python scripts/ngxrot_research.py compare --symbols GTCO,ZENITHBANK,ACCESSCORP --from 2023-01-01 --to 2025-01-01
  PYTHONPATH=src python scripts/ngxrot_research.py universe --as-of 2024-06-30
  PYTHONPATH=src python scripts/ngxrot_research.py universe --index NGXBNK --as-of 2024-06-30
  PYTHONPATH=src python scripts/ngxrot_research.py lookup --symbol GTCO
  PYTHONPATH=src python scripts/ngxrot_research.py metadata --symbol GTCO
  (add --format json|csv to any command; default is a terminal table)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db, registry  # noqa: E402
from ngxrot.research_query import QuerySpec, QueryValidationError, execute  # noqa: E402


def _print_result(r, fmt: str) -> None:
    if fmt == "json":
        print(r.to_json())
        return
    if fmt == "csv":
        print(r.to_csv())
        return
    print(f"query_id={r.query_id}  query_type={r.query_type}  rows={r.row_count}")
    if r.warnings:
        for w in r.warnings:
            print(f"  WARNING: {w}")
    if r.data_sources:
        print(f"  sources: {', '.join(r.data_sources)}")
    if not r.observations.empty:
        print(r.observations.to_string(index=False, max_rows=50))
        if len(r.observations) > 50:
            print(f"  ... ({len(r.observations) - 50} more rows; use --format csv/json for the full result)")
    else:
        print("  (no rows)")
    if r.execution_metadata.get("comparison_summary"):
        print()
        print("comparison summary:")
        for row in r.execution_metadata["comparison_summary"]:
            print(f"  {row}")


def cmd_prices(con, reg, args) -> None:
    spec = QuerySpec(query_type="prices", entities=args.symbol.split(","), start=args.from_, end=args.to,
                     as_of=args.as_of, fields=args.fields.split(","), min_confidence=args.min_confidence,
                     limit=args.limit)
    _print_result(execute(con, spec, reg=reg, log=not args.no_log), args.format)


def cmd_sector(con, reg, args) -> None:
    spec = QuerySpec(query_type="cross_section", entity_kind="sector", filters={"sector": args.sector},
                     as_of=args.as_of, fields=args.fields.split(","), min_confidence=args.min_confidence,
                     limit=args.limit)
    _print_result(execute(con, spec, reg=reg, log=not args.no_log), args.format)


def cmd_compare(con, reg, args) -> None:
    spec = QuerySpec(query_type="compare", entities=args.symbols.split(","), start=args.from_, end=args.to,
                     as_of=args.as_of, fields=args.fields.split(","), min_confidence=args.min_confidence,
                     limit=args.limit)
    _print_result(execute(con, spec, reg=reg, log=not args.no_log), args.format)


def cmd_universe(con, reg, args) -> None:
    if args.index:
        spec = QuerySpec(query_type="universe_history", entities=[args.index], entity_kind="index",
                         as_of=args.as_of, limit=args.limit)
    else:
        spec = QuerySpec(query_type="universe_history", filters={"universe": "iru"}, as_of=args.as_of,
                         limit=args.limit)
    _print_result(execute(con, spec, reg=reg, log=not args.no_log), args.format)


def cmd_lookup(con, reg, args) -> None:
    spec = QuerySpec(query_type="entity_lookup", entities=args.symbol.split(","), entity_kind=args.kind)
    _print_result(execute(con, spec, reg=reg, log=not args.no_log), args.format)


def cmd_metadata(con, reg, args) -> None:
    spec = QuerySpec(query_type="metadata", entities=args.symbol.split(","), limit=args.limit)
    _print_result(execute(con, spec, reg=reg, log=not args.no_log), args.format)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--as-of", dest="as_of", default=None,
                        help="information-availability cutoff (YYYY-MM-DD); rejects queries whose "
                             "date range would look past this date")
        sp.add_argument("--min-confidence", dest="min_confidence", type=float, default=0.0)
        sp.add_argument("--limit", type=int, default=None)
        sp.add_argument("--format", choices=["table", "json", "csv"], default="table")
        sp.add_argument("--no-log", action="store_true", help="skip writing to query_log")

    sp = sub.add_parser("prices", help="time-series query for one or more tickers")
    sp.add_argument("--symbol", required=True, help="comma-separated ticker(s)")
    sp.add_argument("--from", dest="from_", required=True)
    sp.add_argument("--to", required=True)
    sp.add_argument("--fields", default="close")
    common(sp)
    sp.set_defaults(func=cmd_prices)

    sp = sub.add_parser("sector", help="cross-sectional snapshot of a sector as of a date")
    sp.add_argument("--sector", required=True)
    sp.add_argument("--fields", default="close")
    common(sp)
    sp.set_defaults(func=cmd_sector)

    sp = sub.add_parser("compare", help="side-by-side time series + descriptive comparison stats")
    sp.add_argument("--symbols", required=True, help="comma-separated tickers")
    sp.add_argument("--from", dest="from_", required=True)
    sp.add_argument("--to", required=True)
    sp.add_argument("--fields", default="close")
    common(sp)
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("universe", help="historical universe/index membership as of a date")
    sp.add_argument("--index", default=None, help="a real NGX index code (e.g. NGXBNK); "
                                                   "omit to use the rule-based IRU instead")
    common(sp)
    sp.set_defaults(func=cmd_universe)

    sp = sub.add_parser("lookup", help="resolve an entity identifier (ticker/sector/index)")
    sp.add_argument("--symbol", required=True, help="comma-separated identifier(s)")
    sp.add_argument("--kind", choices=["ticker", "sector", "index"], default="ticker")
    common(sp)
    sp.set_defaults(func=cmd_lookup)

    sp = sub.add_parser("metadata", help="security metadata + identity for one or more tickers")
    sp.add_argument("--symbol", required=True, help="comma-separated ticker(s)")
    common(sp)
    sp.set_defaults(func=cmd_metadata)

    args = p.parse_args()
    con = db.connect()
    reg = registry.connect_registry()
    try:
        args.func(con, reg, args)
    except QueryValidationError as e:
        print(f"QUERY REJECTED: {e}", file=sys.stderr)
        return 1
    finally:
        con.close()
        reg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
