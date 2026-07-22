"""Run the Phase 4 validation suite.

  python scripts/run_phase4.py [configs/p4_validation_synthetic.toml]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import phase4  # noqa: E402

cfg = sys.argv[1] if len(sys.argv) > 1 else "configs/p4_validation_synthetic.toml"
phase4.run_phase4(cfg)
