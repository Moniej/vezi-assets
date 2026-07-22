"""Print a Company Intelligence profile for one or more tickers.

  python scripts/company_profile.py ZENITHBANK
  python scripts/company_profile.py ZENITHBANK GTCO MCNICHOLS

v0 scaffolding (2026-07-22) — see src/ngxrot/company_intelligence.py for
what is and isn't populated, and why.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import company_intelligence, db  # noqa: E402

if __name__ == "__main__":
    tickers = sys.argv[1:]
    if not tickers:
        sys.exit("usage: python scripts/company_profile.py TICKER [TICKER ...]")
    con = db.connect()
    cache: dict = {}
    for t in tickers:
        profile = company_intelligence.build_profile(con, t, cache=cache)
        print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")
        print(json.dumps(asdict(profile), indent=2, default=str))
