"""Standalone assertion-script tests for confidence_propagation.py.

  PYTHONPATH=src python scripts/fre/test_confidence_propagation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.fre.confidence_propagation import propagate_confidence_tier  # noqa: E402

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
    check("all direct_reported -> direct_reported",
          propagate_confidence_tier(["direct_reported", "direct_reported"]) == "direct_reported")
    check("direct_reported + mapped_equivalent -> mapped_equivalent (weakest wins)",
          propagate_confidence_tier(["direct_reported", "mapped_equivalent"]) == "mapped_equivalent")
    check("direct_reported + derived -> derived",
          propagate_confidence_tier(["direct_reported", "derived"]) == "derived")
    check("mapped_equivalent + derived -> derived",
          propagate_confidence_tier(["mapped_equivalent", "derived"]) == "derived")
    check("any None input -> None, even alongside direct_reported (the floor, not a mid-point)",
          propagate_confidence_tier(["direct_reported", None]) is None)
    check("all None -> None",
          propagate_confidence_tier([None, None]) is None)
    check("empty input -> None",
          propagate_confidence_tier([]) is None)
    check("single direct_reported -> direct_reported",
          propagate_confidence_tier(["direct_reported"]) == "direct_reported")
    check("three-way mixed, weakest (None) wins",
          propagate_confidence_tier(["direct_reported", "derived", None]) is None)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
