"""CLI for the Research Application Layer (Phase 4,
src/ngxrot/research_applications.py) -- thin wrapper, no new
infrastructure. Companion to scripts/ngxrot_research.py (Phase 2, query
layer) and scripts/ngxrot_research_workspace.py (Phase 3, workspace),
same argparse convention, one script per layer.

Usage:
  PYTHONPATH=src python scripts/ngxrot_research_apps.py investigate --title "..." --question "..." --entities GTCO --start 2023-01-01 --end 2024-01-01
  PYTHONPATH=src python scripts/ngxrot_research_apps.py company --symbol GTCO --start 2023-01-01 --end 2024-01-01 [--id RP-...]
  PYTHONPATH=src python scripts/ngxrot_research_apps.py sector --sector "CONSUMER GOODS" --as-of 2020-01-01,2025-01-01 [--id RP-...]
  PYTHONPATH=src python scripts/ngxrot_research_apps.py compare --symbols GTCO,ZENITHBANK --start 2023-01-01 --end 2024-01-01 [--id RP-...]
  PYTHONPATH=src python scripts/ngxrot_research_apps.py event --symbol CILEASING --date 2024-01-05 [--id RP-...]
  PYTHONPATH=src python scripts/ngxrot_research_apps.py quality-gate --id RP-...
  PYTHONPATH=src python scripts/ngxrot_research_apps.py conclude --id RP-... --statement "..." --state PARTIALLY_SUPPORTED
  PYTHONPATH=src python scripts/ngxrot_research_apps.py report --id RP-...
  PYTHONPATH=src python scripts/ngxrot_research_apps.py templates [--name event_investigation]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db, registry  # noqa: E402
from ngxrot import research_workspace as rw  # noqa: E402
from ngxrot import research_applications as ra  # noqa: E402


def cmd_investigate(con, reg, args) -> None:
    p = ra.create_investigation(
        reg, args.title, args.question,
        entities=args.entities.split(",") if args.entities else None,
        sectors=args.sectors.split(",") if args.sectors else None,
        start=args.start, end=args.end, as_of=args.as_of,
        research_objective=args.objective)
    print(f"created {p.research_id}")


def cmd_company(con, reg, args) -> None:
    profile = ra.company_profile(con, reg, args.symbol, start=args.start, end=args.end,
                                 research_id=args.id)
    print(json.dumps(profile, indent=2, default=str))


def cmd_sector(con, reg, args) -> None:
    profile = ra.sector_profile(con, reg, args.sector, args.as_of.split(","), research_id=args.id)
    print(json.dumps(profile, indent=2, default=str))


def cmd_compare(con, reg, args) -> None:
    result = ra.compare_entities(con, reg, args.symbols.split(","), args.start, args.end,
                                 research_id=args.id)
    print(json.dumps(result, indent=2, default=str))


def cmd_event(con, reg, args) -> None:
    result = ra.event_window(con, reg, args.symbol, args.date, pre_days=args.pre_days,
                             post_days=args.post_days, research_id=args.id)
    print(json.dumps(result, indent=2, default=str))


def cmd_quality_gate(con, reg, args) -> None:
    gate = ra.run_quality_gate(con, reg, args.id)
    print(json.dumps(gate, indent=2, default=str))


def cmd_conclude(con, reg, args) -> None:
    concl_id = ra.record_conclusion(reg, args.id, args.statement, args.state,
                                    uncertainties=args.uncertainties or "",
                                    limitations=args.limitations or "")
    print(f"conclusion {concl_id}")


def cmd_complete(con, reg, args) -> None:
    result = ra.complete_investigation(con, reg, args.id, args.statement, args.state,
                                       force=args.force)
    print(f"status={result['project'].status} gate_passed={result['quality_gate']['passed']} "
         f"snapshot={result['research_snapshot_id']}")


def cmd_report(con, reg, args) -> None:
    print(ra.generate_investigation_report(con, reg, args.id))


def cmd_templates(con, reg, args) -> None:
    if args.name:
        print(json.dumps(ra.get_template(args.name), indent=2))
    else:
        for name in ra.RESEARCH_TEMPLATES:
            print(name)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("investigate")
    sp.add_argument("--title", required=True)
    sp.add_argument("--question", required=True)
    sp.add_argument("--entities", default=None)
    sp.add_argument("--sectors", default=None)
    sp.add_argument("--start", default=None)
    sp.add_argument("--end", default=None)
    sp.add_argument("--as-of", dest="as_of", default=None)
    sp.add_argument("--objective", default=None)
    sp.set_defaults(func=cmd_investigate)

    sp = sub.add_parser("company")
    sp.add_argument("--symbol", required=True)
    sp.add_argument("--start", default=None)
    sp.add_argument("--end", default=None)
    sp.add_argument("--id", default=None, help="attach to an existing investigation")
    sp.set_defaults(func=cmd_company)

    sp = sub.add_parser("sector")
    sp.add_argument("--sector", required=True)
    sp.add_argument("--as-of", dest="as_of", required=True, help="comma-separated dates")
    sp.add_argument("--id", default=None)
    sp.set_defaults(func=cmd_sector)

    sp = sub.add_parser("compare")
    sp.add_argument("--symbols", required=True)
    sp.add_argument("--start", required=True)
    sp.add_argument("--end", required=True)
    sp.add_argument("--id", default=None)
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("event")
    sp.add_argument("--symbol", required=True)
    sp.add_argument("--date", required=True)
    sp.add_argument("--pre-days", dest="pre_days", type=int, default=10)
    sp.add_argument("--post-days", dest="post_days", type=int, default=10)
    sp.add_argument("--id", default=None)
    sp.set_defaults(func=cmd_event)

    sp = sub.add_parser("quality-gate")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_quality_gate)

    sp = sub.add_parser("conclude")
    sp.add_argument("--id", required=True)
    sp.add_argument("--statement", required=True)
    sp.add_argument("--state", required=True)
    sp.add_argument("--uncertainties", default=None)
    sp.add_argument("--limitations", default=None)
    sp.set_defaults(func=cmd_conclude)

    sp = sub.add_parser("complete")
    sp.add_argument("--id", required=True)
    sp.add_argument("--statement", required=True)
    sp.add_argument("--state", required=True)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_complete)

    sp = sub.add_parser("report")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("templates")
    sp.add_argument("--name", default=None)
    sp.set_defaults(func=cmd_templates)

    args = p.parse_args()
    con = db.connect()
    reg = registry.connect_registry()
    try:
        args.func(con, reg, args)
    except rw.WorkspaceError as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 1
    finally:
        con.close()
        reg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
