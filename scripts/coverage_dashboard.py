"""Manually refresh the Data Coverage Dashboard + prereg gate.

  python scripts/coverage_dashboard.py

(Also runs automatically at the end of every equity ingestion.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import coverage, db  # noqa: E402

gate = coverage.generate(db.connect())
print(f"gate {gate.get('gate_version', '')} (IRU {gate.get('iru_version', '?')}): "
      f"{'PASS' if gate['gate_pass'] else 'FAIL'}")
print(f"ready years: {gate['ready_years']}")
print(f"covered stocks: {gate['covered_stocks']}")
print("artifact: reports/data_coverage_dashboard.md")
