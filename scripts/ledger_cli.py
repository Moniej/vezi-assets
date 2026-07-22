"""Minimal research-ledger CLI.

  python scripts/ledger_cli.py add <ID> "<description>" "<motivation>"
  python scripts/ledger_cli.py status <ID> <new_status> "<reason>" ["<conclusion>"]
  python scripts/ledger_cli.py list
  python scripts/ledger_cli.py log <ID>
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import ledger, registry  # noqa: E402

reg = registry.connect_registry()
cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

if cmd == "add":
    ledger.add_hypothesis(reg, sys.argv[2], sys.argv[3], sys.argv[4])
    print(f"added {sys.argv[2]} (untested)")
elif cmd == "status":
    ledger.set_status(reg, sys.argv[2], sys.argv[3], sys.argv[4],
                      sys.argv[5] if len(sys.argv) > 5 else None)
    print(f"{sys.argv[2]} -> {sys.argv[3]}")
elif cmd == "freeze":
    ledger.freeze(reg, sys.argv[2], sys.argv[3])
    print(f"{sys.argv[2]} FROZEN (permanent — no unfreeze exists)")
elif cmd == "log":
    print(pd.read_sql("SELECT * FROM hypothesis_status_log WHERE hypothesis_id = ? "
                      "ORDER BY log_id", reg, params=(sys.argv[2],)).to_string(index=False))
else:
    df = ledger.ledger(reg)
    print(df.to_string(index=False) if len(df) else "(ledger empty)")
