"""FRE-2 verification/demo: print the full Evidence Graph chain for every
real fact in the database, plus the layer_gap_report, against the (now
backfilled) real database. Read-only -- no writes.

  PYTHONPATH=src python scripts/fre/verify_evidence_graph.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.evidence_graph import build_evidence_chain, layer_gap_report  # noqa: E402


def main() -> int:
    con = db.connect(db.DEFAULT_DB)
    fact_ids = [r[0] for r in con.execute(
        "SELECT DISTINCT fact_id FROM causal_chain_steps ORDER BY fact_id"
    ).fetchall()]

    print(f"=== FRE-2 Evidence Graph: {len(fact_ids)} real facts ===\n")
    for fact_id in fact_ids:
        chain = build_evidence_chain(con, fact_id)
        print(f"--- fact_id {chain.fact_id} ({chain.fact_type}) ---")
        print(f"  Observation      : {chain.observation[:110]}")
        print(f"  Evidence quotes  : {len(chain.evidence_quotes)}")
        print(f"  Financial steps  : {len(chain.financial_steps)}")
        print(f"  Business steps   : {len(chain.business_steps)}")
        print(f"  Competitive steps: {len(chain.competitive_steps)}")
        print(f"  Unclassified     : {len(chain.unclassified_steps)}")
        print(f"  Investment impl. : status={chain.status}, "
              f"confidence={chain.confidence}, action={chain.action_recommendation}")
        print(f"  Missing evidence : {len(chain.missing_evidence)} open item(s)")
        print()

    print("=== layer_gap_report ===\n")
    gaps = layer_gap_report(con)
    print(f"{len(gaps)}/{len(fact_ids)} facts have at least one impact-active "
          f"layer missing from their own causal chain:\n")
    for g in gaps:
        print(f"  fact_id {g['fact_id']}: active={g['active_layers']} "
              f"represented={g['represented_layers']} "
              f"MISSING={g['missing_layers']}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
