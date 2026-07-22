"""Print the alpha engine's current recommendations and pipeline status.

  python scripts/engine_status.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot.alpha_engine import AlphaEngine  # noqa: E402

print(AlphaEngine().report())
