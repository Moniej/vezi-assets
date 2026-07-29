"""LIM-6 (RB-1 follow-up): engineering-correctness tests for bootstrap
confidence-interval computation. Matches this project's no-pytest,
assertion-script convention.

  lim_training/venv/Scripts/python.exe scripts/lim/test_eval_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.lim import eval_analysis as ea  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def test_bootstrap_ci_basic_properties():
    values = [1.0] * 20
    r = ea.bootstrap_ci(values)
    check("bootstrap_ci: constant values give a zero-width CI at the constant",
         r["ci_low"] == r["ci_high"] == r["mean"] == 1.0)

    r2 = ea.bootstrap_ci([0.0, 1.0] * 10)
    check("bootstrap_ci: mean of alternating 0/1 values is 0.5", r2["mean"] == 0.5)
    check("bootstrap_ci: CI contains the true mean for a large, balanced sample",
         r2["ci_low"] <= 0.5 <= r2["ci_high"])

    r3 = ea.bootstrap_ci([])
    check("bootstrap_ci: empty input returns n=0, mean=None, no crash",
         r3["n"] == 0 and r3["mean"] is None)

    r4 = ea.bootstrap_ci([0.7])
    check("bootstrap_ci: n=1 collapses to the point estimate with a note",
         r4["n"] == 1 and r4["ci_low"] == r4["ci_high"] == 0.7 and "note" in r4)


def test_bootstrap_ci_deterministic():
    values = [0.1, 0.5, 0.9, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.0]
    r1 = ea.bootstrap_ci(values, seed=42)
    r2 = ea.bootstrap_ci(values, seed=42)
    check("bootstrap_ci: identical seed reproduces an identical CI (reproducible artifact)",
         r1 == r2)
    r3 = ea.bootstrap_ci(values, seed=99)
    check("bootstrap_ci: a different seed is allowed to (but need not) differ",
         True)  # just confirming no crash with a different seed; not asserting inequality


def test_narrower_ci_with_more_data():
    small = ea.bootstrap_ci([0.3, 0.7, 0.5, 0.4, 0.6], seed=1)
    large = ea.bootstrap_ci([0.3, 0.7, 0.5, 0.4, 0.6] * 20, seed=1)
    check("bootstrap_ci: CI narrows with more (repeated) data at the same mean",
         (large["ci_high"] - large["ci_low"]) < (small["ci_high"] - small["ci_low"]))


def test_paired_comparison_detects_real_difference():
    examples_a = [{"dataset_type": "extraction", "unique_id": f"extraction:{i}",
                  "scores": {"m": 0.2}} for i in range(20)]
    examples_b = [{"dataset_type": "extraction", "unique_id": f"extraction:{i}",
                  "scores": {"m": 0.8}} for i in range(20)]
    r = ea.paired_bootstrap_ci_of_difference(examples_a, examples_b, "m")
    check("paired CI: a large, consistent difference is detected (CI excludes 0)",
         r["ci_excludes_zero"] is True)
    check("paired CI: mean difference is correct", abs(r["mean"] - 0.6) < 1e-9)


def test_paired_comparison_null_when_no_real_difference():
    import random
    rng = random.Random(7)
    examples_a = [{"dataset_type": "extraction", "unique_id": f"extraction:{i}",
                  "scores": {"m": 0.5 + rng.uniform(-0.05, 0.05)}} for i in range(8)]
    examples_b = [{"dataset_type": "extraction", "unique_id": f"extraction:{i}",
                  "scores": {"m": 0.5 + rng.uniform(-0.05, 0.05)}} for i in range(8)]
    r = ea.paired_bootstrap_ci_of_difference(examples_a, examples_b, "m")
    check("paired CI: small noisy difference on a small n is NOT falsely flagged as real",
         r["ci_excludes_zero"] is False, detail=str(r))


def test_paired_comparison_only_uses_shared_ids():
    examples_a = [{"dataset_type": "extraction", "unique_id": "extraction:1", "scores": {"m": 0.5}},
                 {"dataset_type": "extraction", "unique_id": "extraction:2", "scores": {"m": 0.5}}]
    examples_b = [{"dataset_type": "extraction", "unique_id": "extraction:1", "scores": {"m": 0.9}},
                 {"dataset_type": "extraction", "unique_id": "extraction:99", "scores": {"m": 0.1}}]
    r = ea.paired_bootstrap_ci_of_difference(examples_a, examples_b, "m")
    check("paired CI: only the shared unique_id (extraction:1) is compared",
         r["n"] == 1 and abs(r["mean"] - 0.4) < 1e-9)


if __name__ == "__main__":
    test_bootstrap_ci_basic_properties()
    test_bootstrap_ci_deterministic()
    test_narrower_ci_with_more_data()
    test_paired_comparison_detects_real_difference()
    test_paired_comparison_null_when_no_real_difference()
    test_paired_comparison_only_uses_shared_ids()

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
