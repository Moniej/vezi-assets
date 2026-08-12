"""CLI for the Research Workspace (src/ngxrot/research_workspace.py) --
thin wrapper, no new logic. Same convention as scripts/ngxrot_research.py
(argparse, operates on the real production DB/registry by default).

Added 2026-08-11 (HANDOFF.md, Priority 8: product/API exposure). Audit
finding: research_workspace.py had a full, tested Python API but ZERO
CLI -- a researcher could only use it from a Python REPL/script. No HTTP
server is built here (no demonstrated multi-user need yet, per the
standing "don't introduce an API simply because APIs are fashionable"
instruction) -- this completes the CLI-first pattern the query layer
already established.

Usage:
  PYTHONPATH=src python scripts/ngxrot_workspace.py create --title "..." --question "..."
  PYTHONPATH=src python scripts/ngxrot_workspace.py list [--status ACTIVE]
  PYTHONPATH=src python scripts/ngxrot_workspace.py show --id RP-...
  PYTHONPATH=src python scripts/ngxrot_workspace.py note --id RP-... --type observation --content "..."
  PYTHONPATH=src python scripts/ngxrot_workspace.py market-evidence --id RP-... --type dataset_observation \
      --ref '{"ticker":"GTCO","trade_date":"2026-01-05"}' --description "..."
  PYTHONPATH=src python scripts/ngxrot_workspace.py doc-evidence --id RP-... --query-type facts --symbol NASCON
  PYTHONPATH=src python scripts/ngxrot_workspace.py finding --id RP-... --title "..." --statement "..."
  PYTHONPATH=src python scripts/ngxrot_workspace.py hypothesis --id RP-... --statement "..."
  PYTHONPATH=src python scripts/ngxrot_workspace.py completeness --id RP-...
  PYTHONPATH=src python scripts/ngxrot_workspace.py integrity --id RP-...
  PYTHONPATH=src python scripts/ngxrot_workspace.py snapshot --id RP-...
  PYTHONPATH=src python scripts/ngxrot_workspace.py export --id RP-... --format markdown [--out report.md]
  PYTHONPATH=src python scripts/ngxrot_workspace.py archive --id RP-... --reason "..."
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
from ngxrot.research_query import QuerySpec, execute  # noqa: E402


def cmd_create(con, reg, args) -> None:
    scope = json.loads(args.scope) if args.scope else None
    p = rw.create_project(reg, args.title, args.question, description=args.description or "",
                          owner=args.owner, scope=scope, parent_research_id=args.parent)
    print(f"created {p.research_id} (status={p.status})")


def cmd_list(con, reg, args) -> None:
    for p in rw.list_projects(reg, status=args.status):
        print(f"{p.research_id}  [{p.status}]  {p.title}")


def cmd_show(con, reg, args) -> None:
    p = rw.get_project(reg, args.id)
    if p is None:
        print(f"no project {args.id!r}", file=sys.stderr)
        sys.exit(1)
    print(f"{p.research_id}  [{p.status}]\n{p.title}\nQ: {p.research_question}\n")
    print(f"queries attached: {len(rw.list_queries(reg, args.id))}")
    print(f"evidence recorded: {len(rw.list_evidence(reg, args.id))}")
    print(f"findings: {len(rw.list_findings(reg, args.id))}")
    print(f"hypotheses: {len(rw.list_hypotheses(reg, args.id))}")


def cmd_note(con, reg, args) -> None:
    note_id = rw.add_note(reg, args.id, args.type, args.content)
    print(note_id)


def cmd_market_evidence(con, reg, args) -> None:
    ref = json.loads(args.ref)
    ev_id = rw.add_evidence(con, reg, args.id, args.type, ref, args.description,
                            claim_class=args.claim_class)
    print(ev_id)


def cmd_doc_evidence(con, reg, args) -> None:
    spec = QuerySpec(query_type=args.query_type, entities=[args.symbol], as_of=args.as_of,
                     filters={"fact_type": args.fact_type} if args.fact_type else {})
    result = execute(con, spec, reg=reg)
    rw.attach_query(reg, args.id, result.query_id)
    if result.observations.empty:
        print("query returned no rows -- nothing to record as evidence", file=sys.stderr)
        sys.exit(1)
    ev_id = rw.add_document_evidence(reg, args.id, result, row_index=args.row)
    print(f"query_id={result.query_id}  evidence_id={ev_id}")


def cmd_finding(con, reg, args) -> None:
    evidence = args.evidence.split(",") if args.evidence else None
    finding_id = rw.add_finding(reg, args.id, args.title, args.statement,
                                supporting_evidence=evidence, status=args.status)
    print(finding_id)


def cmd_hypothesis(con, reg, args) -> None:
    hyp_id = rw.add_hypothesis(reg, args.id, args.statement)
    print(hyp_id)


def cmd_completeness(con, reg, args) -> None:
    print(json.dumps(rw.document_completeness_summary(reg, args.id), indent=2, default=str))


def cmd_integrity(con, reg, args) -> None:
    for w in rw.integrity_check(con, reg, args.id):
        print(f"- {w}")


def cmd_snapshot(con, reg, args) -> None:
    print(rw.snapshot(con, reg, args.id))


def cmd_export(con, reg, args) -> None:
    text = rw.export_markdown(con, reg, args.id) if args.format == "markdown" \
        else rw.export_json(reg, args.id)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written to {args.out}")
    else:
        print(text)


def cmd_archive(con, reg, args) -> None:
    p = rw.archive_project(reg, args.id, reason=args.reason or "")
    print(f"{p.research_id} archived")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("create", help="create a new DRAFT research project")
    sp.add_argument("--title", required=True)
    sp.add_argument("--question", required=True)
    sp.add_argument("--description", default=None)
    sp.add_argument("--owner", default=None)
    sp.add_argument("--scope", default=None, help="JSON object")
    sp.add_argument("--parent", default=None, help="parent research_id for a branched project")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("list", help="list projects")
    sp.add_argument("--status", default=None)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="summarize one project")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("note", help="add a typed note")
    sp.add_argument("--id", required=True)
    sp.add_argument("--type", required=True, choices=["observation", "interpretation", "question",
                                                       "assumption", "decision", "warning"])
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_note)

    sp = sub.add_parser("market-evidence", help="record market-data-side evidence")
    sp.add_argument("--id", required=True)
    sp.add_argument("--type", required=True, choices=["query_result", "dataset_observation",
                                                       "source_document", "company_metadata",
                                                       "corporate_action", "historical_event",
                                                       "calculation", "chart_table"])
    sp.add_argument("--ref", required=True, help="JSON object, e.g. "
                                                  "'{\"ticker\":\"GTCO\",\"trade_date\":\"2026-01-05\"}'")
    sp.add_argument("--description", required=True)
    sp.add_argument("--claim-class", dest="claim_class", default=None)
    sp.set_defaults(func=cmd_market_evidence)

    sp = sub.add_parser("doc-evidence", help="run a document/FRE-side query and record one row as evidence")
    sp.add_argument("--id", required=True)
    sp.add_argument("--query-type", dest="query_type", required=True,
                    choices=["facts", "events", "entity_relationships", "document_context"])
    sp.add_argument("--symbol", required=True)
    sp.add_argument("--as-of", dest="as_of", default=None)
    sp.add_argument("--fact-type", dest="fact_type", default=None)
    sp.add_argument("--row", type=int, default=0)
    sp.set_defaults(func=cmd_doc_evidence)

    sp = sub.add_parser("finding", help="record a finding")
    sp.add_argument("--id", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--statement", required=True)
    sp.add_argument("--evidence", default=None, help="comma-separated evidence_id list")
    sp.add_argument("--status", default="PRELIMINARY")
    sp.set_defaults(func=cmd_finding)

    sp = sub.add_parser("hypothesis", help="record a (generic, non-alpha) hypothesis")
    sp.add_argument("--id", required=True)
    sp.add_argument("--statement", required=True)
    sp.set_defaults(func=cmd_hypothesis)

    sp = sub.add_parser("completeness", help="document/FRE-side research completeness summary")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_completeness)

    sp = sub.add_parser("integrity", help="integrity/limitation warnings for this project")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_integrity)

    sp = sub.add_parser("snapshot", help="freeze the current project state, return a snapshot_id")
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_snapshot)

    sp = sub.add_parser("export", help="export the project as a report")
    sp.add_argument("--id", required=True)
    sp.add_argument("--format", choices=["markdown", "json"], default="markdown")
    sp.add_argument("--out", default=None, help="write to this file instead of stdout")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("archive", help="freeze a project, rejecting further mutation")
    sp.add_argument("--id", required=True)
    sp.add_argument("--reason", default=None)
    sp.set_defaults(func=cmd_archive)

    args = p.parse_args()
    con = db.connect()
    reg = registry.connect_registry()
    try:
        args.func(con, reg, args)
    except rw.WorkspaceError as e:
        print(f"WORKSPACE ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        con.close()
        reg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
