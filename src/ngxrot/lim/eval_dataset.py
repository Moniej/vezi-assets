"""LIM-3 held-out evaluation set loader. Reuses dataset_loader.py's
readiness checks verbatim (registered, content-hash-verified, audit-gate
-passed) -- an evaluation must never score a model against data that
wouldn't have been trustworthy enough to train on either. The ONE thing
this module adds on top: filtering down to the `splits.json` "test"
partition (LIM-1's deterministic, hash-bucket split, computed at export
time and never consulted by training.py, which does its own ad hoc
in-training eval slice) -- so LIM-3 always scores against examples that
were never used in any training step, real held-out evaluation rather than
training-time validation loss.
"""

from __future__ import annotations

import json
from pathlib import Path

from ngxrot.lim import dataset_loader, registry

PKG_ROOT = Path(__file__).resolve().parents[3]


def load_holdout_set(con_lim, dataset_type: str, version: str | None = None,
                     split: str = "test") -> dict:
    """Returns a dict describing the held-out set for one registered
    dataset type/version:
      {"dataset_type", "version", "content_hash", "split", "examples",
       "n_total_accepted", "n_in_split"}
    `examples` is the list of accepted-partition example dicts whose
    unique_id falls in the requested split. Raises
    dataset_loader.DatasetNotReadyError if the version isn't registered,
    tampered, or has recorded audit violations -- identical refusal
    semantics to training. Returns n_in_split=0 (empty examples list,
    never an exception) when the split legitimately has zero examples --
    e.g. a very small dataset type where the deterministic hash-bucket
    split happened to place nothing in "test"; the caller must report
    that honestly as NOT MEASURABLE, not substitute train/validation data."""
    resolved, all_examples = dataset_loader.load_examples(con_lim, dataset_type, version)
    meta = registry.get_version(con_lim, resolved)
    splits_path = Path(meta["accepted_path"]).parent / "splits.json"
    if not splits_path.exists():
        raise dataset_loader.DatasetNotReadyError(
            f"{resolved}: no splits.json found alongside the dataset -- cannot resolve a held-out set")
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    if split not in splits:
        raise dataset_loader.DatasetNotReadyError(
            f"{resolved}: splits.json has no {split!r} partition (has: {list(splits)})")
    split_ids = set(splits[split])
    holdout = [ex for ex in all_examples if ex["unique_id"] in split_ids]
    return {
        "dataset_type": dataset_type, "version": resolved, "content_hash": meta["content_hash"],
        "split": split, "examples": holdout, "n_total_accepted": len(all_examples),
        "n_in_split": len(holdout),
    }


def load_all_holdout_sets(con_lim, dataset_types: list[str], split: str = "test") -> dict[str, dict]:
    """One load_holdout_set() call per requested type. A type whose latest
    version fails readiness (unregistered, tampered, gate-violating) is
    recorded with its failure reason rather than aborting the whole batch --
    unlike training's all-or-nothing refusal, an evaluation run's job is to
    report what CAN be measured and disclose what can't, not to refuse
    outright over one type's data-quality problem."""
    out = {}
    for dataset_type in dataset_types:
        try:
            out[dataset_type] = load_holdout_set(con_lim, dataset_type, split=split)
        except dataset_loader.DatasetNotReadyError as e:
            out[dataset_type] = {"dataset_type": dataset_type, "error": str(e), "n_in_split": 0,
                                 "examples": []}
    return out
