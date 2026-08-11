"""CLI for the Research Workspace (Phase 3, src/ngxrot/research_workspace.py)
-- thin wrapper, no new infrastructure. Companion to scripts/
ngxrot_research.py (Phase 2's query CLI); a separate script/file rather
than adding subcommands to that one, matching this repo's existing
pattern of one focused CLI per layer (e.g. ngxpulse_ingest.py vs
ngxrot_research.py itself).

Usage:
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py create --title "..." --question "..."
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py list [--status ACTIVE]
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py show --id RP-...
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py attach-query --id RP-... --query-id ...
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py evidence --id RP-... --type query_result --query-id ... --description "..."
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py finding --id RP-... --title "..." --statement "..."
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py snapshot --id RP-...
  PYTHONPATH=src python scripts/ngxrot_research_workspace.py export --id RP-... --format markdown
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db, registry  # noqa: E402
from ngxrot import research_workspace as rw  # noqa: E402


def cmd_create(con, reg, args) -> None:
    p = rw.create_project(reg, args.title, args.question, description=args.description or "",
                          owner=args.owner, tags=args.tags.split(",") if args.tags else None)
    print(f"created {p.research_id}")


def cmd_list(con, reg, args) -> None:
    for p in rw.list_projects(reg, status=args.status):
        print(f"{p.research_id}  [{p.status}]  {p.title}")


def cmd_show(con, reg, args) -> None:
    p = rw.get_project(reg, args.id)
    if p is None:
        print(f"no project {args.id}", file=sys.stderr)
        sys.exit(1)
    print(f"{p.research_id}  [{p.status}]")
    print(f"title: {p.title}")
    print(f"question: {p.research_question}")
    print(f"scope: {p.scope}")
    print(f"queries: {len(rw.list_queries(reg, p.research_id))}")
    print(f"evidence: {len(rw.list_evidence(reg, p.research_id))}")
    print(f"findings: {len(rw.list_findings(reg, p.research_id))}")
    print(f"hypotheses: {len(rw.list_hypotheses(reg, p.research_id))}")
    print(f"artifacts: {len(rw.list_artifacts(reg, p.research_id))}")


def cmd_attach_query(con, reg, args) -> None:
    rw.attach_query(reg, args.id, args.query_id, note=args.note or "")
    print("attached")


def cmd_evidence(con, reg, args) -> None:
    source_ref = {}
    if args.query_id:
        source_ref["query_id"] = args.query_id
    if args.symbol and args.date:
        source_ref["ticker"] = args.symbol
        source_ref["trade_date"] = args.date
    evidence_id = rw.add_evidence(con, reg, args.id, args.type, source_ref, args.description)
    print(f"evidence {evidence_id}")


def cmd_note(con, reg, args) -> None:
    note_id = rw.add_note(reg, args.id, args.type, args.content)
    print(f"note {note_id}")


def cmd_finding(con, reg, args) -> None:
    finding_id = rw.add_finding(reg, args.id, args.title, args.statement,
                                supporting_evidence=args.evidence.split(",") if args.evidence else None,
                                status=args.status)
    print(f"finding {finding_id}")


def cmd_hypothesis(con, reg, args) -> None:
    hypothesis_id = rw.add_hypothesis(reg, args.id, args.statement)
    print(f"hypothesis {hypothesis_id}")


def cmd_snapshot(con, reg, args) -> None:
    snap_id = rw.snapshot(con, reg, args.id)
    print(f"snapshot {snap_id}")


def cmd_export(con, reg, args) -> None:
    if args.format == "json":
        print(rw.export_json(reg, args.id))
    else:
        print(rw.export_markdown(con, reg, args.id))


def cmd_quality(con, reg, args) -> None:
    import json
    print(json.dumps(rw.project_quality_summary(con, reg, args.id), indent=2, default=str))


def cmd_integrity(con, reg, args) -> None:
    for w in rw.integrity_check(con, reg, args.id):
        print(f"- {w}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("create")
    sp.add_argument("--title", required=True)
    sp.add_argument("--question", required=True)
    sp.add_argument("--description", default=None)
    sp.add_argument("--owner", default=None)
    sp.add_argument("--tags", default=None)
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("list")
    sp.add_argument("--status", default=None)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("attach-query")
    sp.add_argument("--id", required=True)
    sp.add_argument("--query-id", required=True)
    sp.add_argument("--note", default=None)
    sp.set_defaults(func=cmd_attach_query)

    sp = sub.add_parser("evidence")
    sp.add_argument("--id", required=True)
    sp.add_argument("--type", required=True)
    sp.add_argument("--query-id", default=None)
    sp.add_argument("--symbol", default=None)
    sp.add_argument("--date", default=None)
    sp.add_argument("--description", required=True)
    sp.set_defaults(func=cmd_evidence)

    sp = sub.add_parser("note")
    sp.add_argument("--id", required=True)
    sp.add_argument("--type", required=True)
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_note)

    sp = sub.add_parser("finding")
    sp.add_argument("--id", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--statement", required=True)
    sp.add_argument("--evidence", default=None, help="comma-separated evidence_id(s)")
    sp.add_argument("--status", default="PRELIMINARY")
    sp.set_defaults(func=cmd_finding)

    sp = sub.add_parser("hypothesis")
    sp.add_argument("--id", required=True)
    sp.add_argument("--statement", required=True)
    sp.set_defaults(func=cmd_hypothesis)

    sp = sub.add_parser("snapshot")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_snapshot)

    sp = sub.add_parser("export")
    sp.add_argument("--id", required=True)
    sp.add_argument("--format", choices=["json", "markdown"], default="markdown")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("quality")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_quality)

    sp = sub.add_parser("integrity")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_integrity)

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
