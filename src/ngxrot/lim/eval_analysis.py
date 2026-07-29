"""LIM-6 (RB-1 follow-up, owner directive 2026-07-28): "Before continuing
with additional hyperparameter sweeps, strengthen the evaluation
protocol... quantify uncertainty for every metric where practical."

Bootstrap confidence intervals over the per-example scores already
recorded in the eval registry -- pure, deterministic (seeded), no new
dependency, no live model call, applicable retroactively to any existing
eval_run (every prior run already stored every per-example score in
`eval_examples`). This module answers exactly the question RB-1's result
left open: is an observed difference between two checkpoints real, or
indistinguishable from noise on a small held-out set?
"""

from __future__ import annotations

import random
import statistics


def bootstrap_ci(values: list[float], n_resamples: int = 2000, ci_level: float = 0.95,
                 seed: int = 42) -> dict:
    """Bootstrap CI for the mean of `values`. Deterministic given `seed`
    -- re-running this function twice on the same values reproduces the
    identical interval, so a reported CI is itself a reproducible
    artifact, not a one-off random draw."""
    if not values:
        return {"n": 0, "mean": None, "ci_low": None, "ci_high": None,
                "ci_level": ci_level, "n_resamples": n_resamples}
    n = len(values)
    if n == 1:
        return {"n": 1, "mean": round(values[0], 4), "ci_low": round(values[0], 4),
                "ci_high": round(values[0], 4), "ci_level": ci_level, "n_resamples": n_resamples,
                "note": "n=1 -- CI collapses to the point estimate, not a real interval"}
    rng = random.Random(seed)
    means = [statistics.mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(n_resamples)]
    means.sort()
    lo_idx = max(0, int((1 - ci_level) / 2 * n_resamples))
    hi_idx = min(n_resamples - 1, int((1 + ci_level) / 2 * n_resamples))
    return {
        "n": n, "mean": round(statistics.mean(values), 4),
        "ci_low": round(means[lo_idx], 4), "ci_high": round(means[hi_idx], 4),
        "ci_level": ci_level, "n_resamples": n_resamples,
    }


def metric_ci_from_eval_run(eval_run: dict, metric_name: str, dataset_type: str | None = None,
                            **kwargs) -> dict:
    """Pulls per-example scores for `metric_name` (optionally filtered to
    one dataset_type) out of an already-recorded eval_run dict (as
    returned by eval_registry.get_eval_run) and bootstraps a CI. Works on
    any historical eval_run without re-running the model."""
    values = [ex["scores"][metric_name] for ex in eval_run["examples"]
             if (dataset_type is None or ex["dataset_type"] == dataset_type)
             and ex["scores"].get(metric_name) is not None]
    return bootstrap_ci(values, **kwargs)


def paired_bootstrap_ci_of_difference(examples_a: list[dict], examples_b: list[dict],
                                      metric_name: str, dataset_type: str | None = None,
                                      **kwargs) -> dict:
    """PAIRED comparison of two eval_run['examples'] lists on the same
    metric: for each (dataset_type, unique_id) scored in BOTH runs,
    computes score_b - score_a, then bootstraps a CI on the mean
    difference. Paired, not independent-samples, because both runs are
    scored against the SAME held-out unique_ids (same registered dataset
    version) -- a within-example comparison is far more statistically
    informative than comparing two separate CIs and eyeballing overlap.
    `result["ci_excludes_zero"]` is the single answer to "is this
    difference distinguishable from noise": True only if the ENTIRE CI is
    on one side of zero."""
    by_id_a = {(ex["dataset_type"], ex["unique_id"]): ex["scores"].get(metric_name)
              for ex in examples_a if dataset_type is None or ex["dataset_type"] == dataset_type}
    by_id_b = {(ex["dataset_type"], ex["unique_id"]): ex["scores"].get(metric_name)
              for ex in examples_b if dataset_type is None or ex["dataset_type"] == dataset_type}
    diffs = [by_id_b[k] - by_id_a[k] for k in by_id_a
            if k in by_id_b and by_id_a[k] is not None and by_id_b[k] is not None]
    result = bootstrap_ci(diffs, **kwargs)
    result["ci_excludes_zero"] = bool(result["n"] > 1 and (result["ci_low"] > 0 or result["ci_high"] < 0))
    result["interpretation"] = (
        "CI excludes 0 -- statistically distinguishable difference" if result["ci_excludes_zero"]
        else "CI includes 0 -- NOT statistically distinguishable from no difference "
             "(observed gap may be noise)")
    return result
