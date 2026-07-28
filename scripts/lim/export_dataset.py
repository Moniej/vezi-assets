"""LIM-1: dataset export CLI (DATASET_GENERATION_AND_TRAINING_SPEC.md
§§2-6). Orchestrates one dataset type (or all 17) through the full
pipeline: export -> audit -> threshold gate -> write versioned JSONL ->
register in the immutable registry -> record lineage -> write
train/val/test split reports.

Read-only against the AI Intelligence Layer's real database (ngx.sqlite);
writes only to lim_training/ (gitignored) and the dataset registry (also
under lim_training/). No training happens here -- that's Phase LIM-2.

  lim_training/venv/Scripts/python.exe scripts/lim/export_dataset.py --task financial_reasoning --changelog "initial export"
  lim_training/venv/Scripts/python.exe scripts/lim/export_dataset.py --all --changelog "initial export, all types"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.lim import audit, quality_report, registry  # noqa: E402
from ngxrot.lim.exporters import EXPORTERS  # noqa: E402
from ngxrot.lim.schema import TASK_TYPES  # noqa: E402

DATASETS_ROOT = ROOT / "lim_training" / "datasets"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001 -- git metadata is informational, never fatal to export
        return None


def _teacher_model_ids(con, examples: list) -> list[str]:
    """Derived automatically from the exported facts' own model_id column --
    never asked of the caller, so nothing about this depends on manual
    bookkeeping (satisfies "regenerable without manual intervention")."""
    fact_ids = {fid for ex in examples for fid in (ex.retrieved_facts or [])}
    if not fact_ids:
        return []
    placeholders = ",".join("?" * len(fact_ids))
    rows = con.execute(
        f"SELECT DISTINCT model_id FROM extracted_facts WHERE fact_id IN ({placeholders}) "
        f"AND model_id IS NOT NULL", list(fact_ids)).fetchall()
    return sorted(r[0] for r in rows)


def export_one(con, con_lim, task: str, *, limit: int | None, changelog: str,
              parent_version: str | None) -> dict:
    if task not in EXPORTERS:
        raise ValueError(f"unknown task {task!r}; must be one of {TASK_TYPES}")

    examples = EXPORTERS[task](con, limit=limit)
    audit_result = audit.compute_audit(examples, con)
    violations = audit.check_thresholds(audit_result, dataset_type=task)

    version = registry.next_version(con_lim, task)
    version_dir = DATASETS_ROOT / task / version
    version_dir.mkdir(parents=True, exist_ok=True)

    accepted = [e for e in examples if e.acceptance_status == "accepted"]
    rejected = [e for e in examples if e.acceptance_status == "rejected"]
    for e in examples:
        e.dataset_version = version

    accepted_path = version_dir / "accepted.jsonl"
    rejected_path = version_dir / "rejected.jsonl"
    accepted_path.write_text("\n".join(e.to_json_line() for e in accepted), encoding="utf-8")
    rejected_path.write_text("\n".join(e.to_json_line() for e in rejected), encoding="utf-8")

    splits = audit.make_splits(examples)
    split_rep = audit.split_report(splits)
    (version_dir / "splits.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")

    audit_md = audit.render_markdown(task, audit_result, split_rep, violations)
    (version_dir / "audit_report.md").write_text(audit_md, encoding="utf-8")
    (version_dir / "audit_report.json").write_text(
        json.dumps({"audit": audit_result, "splits": split_rep, "violations": violations},
                  indent=2, default=str), encoding="utf-8")

    result = {"task": task, "version": version, "n_accepted": len(accepted),
             "n_rejected": len(rejected), "violations": violations, "registered": False}

    if violations:
        # Per spec §6.1/§6.3: training must be REFUSED on a threshold breach.
        # The export artifacts are still written (so the audit is
        # inspectable), but the version is NOT registered as usable --
        # an unregistered version can't be referenced by any future
        # training-config lookup.
        result["status"] = "AUDIT FAILED — not registered, not usable for training"
        return result

    teacher_ids = _teacher_model_ids(con, examples)
    rejection_counts = audit_result["rejection_reason_distribution"]
    registry.register_version(
        con_lim, version=version, dataset_type=task, accepted_path=accepted_path,
        rejected_path=rejected_path, source_as_of=date.today().isoformat(),
        export_script_commit=_git_commit(), parent_version=parent_version,
        n_accepted=len(accepted), n_rejected=len(rejected),
        rejection_reason_counts=rejection_counts, teacher_model_ids=teacher_ids,
        changelog=changelog)
    registry.record_lineage(con_lim, con, version, examples)
    quality_report.write_quality_report(con_lim, version)
    result["status"] = "registered"
    result["registered"] = True
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", help=f"one of {sorted(EXPORTERS)}")
    ap.add_argument("--all", action="store_true", help="export every dataset type")
    ap.add_argument("--limit", type=int, default=None, help="cap rows per type (testing only)")
    ap.add_argument("--changelog", required=True, help="what this export version is / why")
    ap.add_argument("--parent-version", default=None,
                   help="set for an incremental version building on a prior one")
    args = ap.parse_args()

    if not args.task and not args.all:
        ap.error("pass --task <name> or --all")

    con = db.init_db()
    con_lim = registry.init_registry()

    tasks = sorted(EXPORTERS) if args.all else [args.task]
    results = []
    for task in tasks:
        print(f"\n=== Exporting {task} ===")
        r = export_one(con, con_lim, task, limit=args.limit, changelog=args.changelog,
                       parent_version=args.parent_version)
        print(f"  {r['status']} -- version={r['version']} "
             f"accepted={r['n_accepted']} rejected={r['n_rejected']}")
        if r["violations"]:
            for v in r["violations"]:
                print(f"  VIOLATION: {v}")
        results.append(r)

    print("\n=== Summary ===")
    for r in results:
        print(f"{r['task']:32s} {r['version']:32s} {r['status']}")

    n_failed = sum(1 for r in results if not r["registered"])
    if n_failed:
        print(f"\n{n_failed} of {len(results)} dataset type(s) FAILED the audit gate "
             f"and were not registered.")
        sys.exit(1)


if __name__ == "__main__":
    main()
