"""FSI Phase 5: freeze the golden snapshot
(docs/fre_runs/fsi_phase5_preregistration.md Area 1).

Writes `data/reference/fsi_pipeline_golden_snapshot.json` -- a canonical,
deterministically-ordered snapshot of Phase 1-4's real, current, frozen
output (106 financial-statement facts, 177 financial-reasoning
conclusions). This is a ONE-TIME freeze against
`fsi-phase4-baseline-2026-08-01` -- re-run only if a future,
owner-approved phase legitimately changes Phase 1-4's output (e.g. a
disclosed bug fix), never to silently paper over an unexplained
deviation.

Read-only against the production database -- this script writes only to
the repo's own `data/reference/` file, never to `data/ngx.sqlite`.

  PYTHONPATH=src python scripts/fre/fsi_phase5_freeze_golden_snapshot.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.pipeline_validation import compute_live_snapshot  # noqa: E402

OUTPUT_PATH = ROOT / "data" / "reference" / "fsi_pipeline_golden_snapshot.json"


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    snapshot = compute_live_snapshot(con)
    print(f"extracted_facts_total_financial: {snapshot['extracted_facts_total_financial']}")
    print(f"extracted_facts_by_type: {snapshot['extracted_facts_by_type']}")
    print(f"conclusions_total: {snapshot['conclusions_total']}")
    print(f"conclusions_by_type: {snapshot['conclusions_by_type']}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nGolden snapshot written to: {OUTPUT_PATH}")

    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    print(f"documents count unchanged: {doc_count_before == doc_count_after} "
          f"(this script has no write path to the production database)")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
