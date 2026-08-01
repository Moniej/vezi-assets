"""Standalone assertion-script tests for period_normalization.periods_overlap(),
validated against the real NASCON H1-2024-vs-FY2024 case (the same real
periods that exposed the restatement-detection false positive fixed in
FSI Phase 2 Entry 4/5).

  PYTHONPATH=src python scripts/fre/test_periods_overlap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.fre.period_normalization import periods_overlap  # noqa: E402

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def main() -> int:
    # Real NASCON periods: H1 2024 (doc 8801), FY2024 (doc 9460), FY2025 (doc 10929)
    check("NASCON's real H1 2024 and FY2024 periods overlap (nested, must be skipped by trend classification)",
          periods_overlap("2024-01-01", "2024-06-30", "2024-01-01", "2024-12-31"))
    check("NASCON's real FY2024 and FY2025 periods do NOT overlap (adjacent, a valid trend pair)",
          not periods_overlap("2024-01-01", "2024-12-31", "2025-01-01", "2025-12-31"))
    check("NASCON's real H1 2024 and FY2025 periods do NOT overlap",
          not periods_overlap("2024-01-01", "2024-06-30", "2025-01-01", "2025-12-31"))
    check("identical periods overlap (a restatement-style case, not a trend pair)",
          periods_overlap("2020-01-01", "2020-12-31", "2020-01-01", "2020-12-31"))
    check("order-independence: swapping the two periods gives the same answer",
          periods_overlap("2024-01-01", "2024-12-31", "2024-01-01", "2024-06-30")
          == periods_overlap("2024-01-01", "2024-06-30", "2024-01-01", "2024-12-31"))
    check("adjacent, touching periods (one ends exactly where the next begins) do NOT overlap",
          not periods_overlap("2023-01-01", "2023-12-31", "2024-01-01", "2024-12-31"))

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
