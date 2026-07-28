"""Registry-only training data loader (owner directive, LIM-2, 2026-07-28):
"Train only from immutable, registered dataset versions. Never train
directly from database tables or intermediate files." This module is the
ONE place training code is allowed to read example data from -- it never
opens `ngx.sqlite`, never calls an exporter, never reads a file that isn't
the exact `accepted_path` recorded in the dataset-version registry.

Every load re-verifies, rather than trusts, that a version is safe to
train on:
  1. it must exist in the registry (proves it passed the export-time audit
     gate -- `export_dataset.py` never registers a version that failed);
  2. the file on disk must still hash to the value recorded at
     registration time (catches tampering/corruption after the fact);
  3. its own `audit_report.json` (co-located, written at export time) must
     show zero threshold violations -- a second, independent confirmation,
     not just trusting step 1's implication.
Any failure raises `DatasetNotReadyError` with the exact reason -- training
is refused, never silently downgraded to "use it anyway."
"""

from __future__ import annotations

import json
from pathlib import Path

from ngxrot.lim import registry

PKG_ROOT = Path(__file__).resolve().parents[3]


class DatasetNotReadyError(Exception):
    """Raised whenever a requested dataset version is not safe to train
    on -- the caller (training.py) must treat this as a hard refusal, per
    the owner's "refuse to start training" instruction."""


def resolve_version(con_lim, dataset_type: str, version: str | None = None) -> str:
    """version=None resolves to the most recently registered version for
    that type -- still an explicit, logged choice (training.py records the
    resolved version string, never just "latest")."""
    versions = registry.list_versions(con_lim, dataset_type)
    if not versions:
        raise DatasetNotReadyError(
            f"no registered version exists for dataset_type={dataset_type!r} -- "
            f"run scripts/lim/export_dataset.py first")
    if version is None:
        return versions[-1]["version"]
    if not any(v["version"] == version for v in versions):
        raise DatasetNotReadyError(
            f"{version!r} is not a registered version of {dataset_type!r}")
    return version


def verify_dataset_ready(con_lim, dataset_type: str, version: str) -> None:
    """Raises DatasetNotReadyError with a precise reason on any failure;
    returns None (silently) only when every check passes."""
    meta = registry.get_version(con_lim, version)
    if meta is None or meta["dataset_type"] != dataset_type:
        raise DatasetNotReadyError(
            f"{version!r} is not registered as a {dataset_type!r} dataset version")

    accepted_path = Path(meta["accepted_path"])
    if not accepted_path.exists():
        raise DatasetNotReadyError(
            f"{version}: registered accepted_path {accepted_path} no longer exists on disk")

    current_hash = registry.content_hash(accepted_path)
    if current_hash != meta["content_hash"]:
        raise DatasetNotReadyError(
            f"{version}: on-disk content_hash ({current_hash[:12]}...) no longer matches "
            f"the hash recorded at registration ({meta['content_hash'][:12]}...) -- the file "
            f"has been modified or corrupted since it was registered; refusing to train on it")

    audit_path = accepted_path.parent / "audit_report.json"
    if not audit_path.exists():
        raise DatasetNotReadyError(
            f"{version}: no audit_report.json found alongside the dataset -- cannot "
            f"independently reconfirm it cleared the quality gate")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    violations = audit.get("violations", [])
    if violations:
        raise DatasetNotReadyError(
            f"{version}: audit_report.json records {len(violations)} unresolved "
            f"violation(s): {violations} -- a version with recorded violations must never "
            f"have been registered; refusing to train on it regardless")


def load_examples(con_lim, dataset_type: str, version: str | None = None) -> tuple[str, list[dict]]:
    """The only function allowed to actually read example rows. Verifies
    readiness first (raises on any failure), then reads ONLY the
    registered accepted.jsonl -- never rejected.jsonl (training data is
    exclusively the accepted partition, by construction), never the source
    database. Returns (resolved_version, examples)."""
    resolved = resolve_version(con_lim, dataset_type, version)
    verify_dataset_ready(con_lim, dataset_type, resolved)
    meta = registry.get_version(con_lim, resolved)
    accepted_path = Path(meta["accepted_path"])
    examples = [json.loads(line) for line in accepted_path.read_text(encoding="utf-8")
               .splitlines() if line.strip()]
    return resolved, examples


def load_training_set(con_lim, specs: list[tuple[str, str | None]]) -> dict:
    """specs: [(dataset_type, version_or_None), ...]. Loads and verifies
    every requested dataset, refusing the WHOLE call if any one of them
    isn't ready (never silently proceeds with a partial set). Returns a
    manifest the caller (training.py) records verbatim in the training-run
    registry: resolved versions, content hashes, teacher model ids, and
    the flattened example list.

    LIM-4 fix (docs/lim_runs/lim4_completion.md): partitions examples by
    the REAL registered splits.json train/validation/test assignment
    (LIM-1's deterministic hash-bucket split), and structurally EXCLUDES
    every `test`-split unique_id here, before anything is returned to the
    caller -- training and validation examples are the only things
    training.py ever sees. This replaces training.py's previous ad hoc
    `examples[:len//10]` in-training "eval" slice, which (verified in
    LIM-4's diagnosis) silently trained on the SAME unique_ids
    (entity_recognition:21/25/33) that scripts/lim/run_evaluation.py later
    scored as "held out" -- a real train/test contamination bug in the
    first LIM-2 run, not a hypothetical risk. Splitting here, once, in the
    one function both training and (indirectly, via the registered
    splits.json) evaluation both trust, makes that contamination
    structurally impossible to repeat rather than just documented against."""
    resolved_versions: dict[str, str] = {}
    content_hashes: dict[str, str] = {}
    teacher_model_ids: set[str] = set()
    train_examples: list[dict] = []
    validation_examples: list[dict] = []

    for dataset_type, version in specs:
        resolved, examples = load_examples(con_lim, dataset_type, version)
        meta = registry.get_version(con_lim, resolved)
        splits_path = Path(meta["accepted_path"]).parent / "splits.json"
        if not splits_path.exists():
            raise DatasetNotReadyError(
                f"{resolved}: no splits.json found -- cannot separate train/validation from the "
                f"held-out test split; refusing to train (this would risk train/test contamination)")
        splits = json.loads(splits_path.read_text(encoding="utf-8"))
        train_ids = set(splits.get("train", []))
        val_ids = set(splits.get("validation", []))
        test_ids = set(splits.get("test", []))

        resolved_versions[dataset_type] = resolved
        content_hashes[resolved] = meta["content_hash"]
        teacher_model_ids.update(meta["teacher_model_ids"])
        for ex in examples:
            uid = ex["unique_id"]
            if uid in test_ids:
                continue  # never returned to the caller, under any circumstance
            elif uid in train_ids:
                train_examples.append(ex)
            elif uid in val_ids:
                validation_examples.append(ex)
            # an accepted example matching none of the three sets can't occur --
            # make_splits() partitions every accepted unique_id into exactly one

    all_examples = train_examples + validation_examples
    return {
        "dataset_versions": [f"{t}@{v}" for t, v in resolved_versions.items()],
        "content_hashes": content_hashes,
        "teacher_model_ids": sorted(teacher_model_ids),
        "examples": all_examples,
        "train_examples": train_examples,
        "validation_examples": validation_examples,
        "n_examples": len(all_examples),
    }
