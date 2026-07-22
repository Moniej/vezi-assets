"""Run experiment(s) from a config file: the ONLY way to run a backtest.

  python scripts/run_experiment.py configs/p2_baseline_synthetic.toml [more.toml ...]
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import runner  # noqa: E402

pd.set_option("display.width", 200)

if len(sys.argv) < 2:
    sys.exit(__doc__)

all_rows = []
for cfg_path in sys.argv[1:]:
    print(f"\n=== {cfg_path} ===")
    df = runner.run_config(cfg_path)
    all_rows.append(df)
    print(df.to_string(index=False))

if len(all_rows) > 1:
    print("\n=== combined ===")
    print(pd.concat(all_rows, ignore_index=True).to_string(index=False))
