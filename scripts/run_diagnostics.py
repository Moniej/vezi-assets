"""Run the full diagnostic suite against the market-data DB.

  python scripts/run_diagnostics.py [start] [end]

The synthetic dataset contains two PLANTED flaws; this suite must catch both:
  1. SYNINSA -33% on 2024-05-15 with no corporate action  -> unexplained_jump
  2. SYNCONB unchanged for 40 sessions from 2023-02-01    -> stale_price
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db, diagnostics  # noqa: E402

start = sys.argv[1] if len(sys.argv) > 1 else "2016-01-01"
end = sys.argv[2] if len(sys.argv) > 2 else "2026-06-30"

con = db.connect()
ctx = diagnostics.DiagContext(con, start, end)
results = diagnostics.run_all(ctx)

print(f"Diagnostics {start} .. {end}\n" + "=" * 70)
for r in results:
    print(r)
    if not r.passed and len(r.evidence):
        print(r.evidence.head(5).to_string(index=False))
        print(f"  -> action: {r.recommended_action}\n")

caught_jump = any(r.name == "unexplained_jump" and not r.passed
                  and "SYNINSA" in r.evidence.ticker.values for r in results)
caught_stale = any(r.name == "stale_price" and not r.passed
                   and "SYNCONB" in r.evidence.ticker.values for r in results)
print("=" * 70)
print(f"planted flaw 1 (SYNINSA unexplained jump): {'CAUGHT' if caught_jump else 'MISSED'}")
print(f"planted flaw 2 (SYNCONB stale stretch):    {'CAUGHT' if caught_stale else 'MISSED'}")
sys.exit(0 if (caught_jump and caught_stale) else 1)
