"""Ingest an event batch through the H-003 event pipeline.

  python scripts/ingest_events.py [batch_root]

batch_root defaults to data/events_seed (CSV batches under <root>/events/).
Every run produces reports/event_quality_<date>.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db, event_pipeline  # noqa: E402
from ngxrot.providers import CSVProvider  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
batch_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "events_seed"

provider = CSVProvider(batch_root, name="manual_primary_verified",
                       base_confidence=0.7)

con = db.init_db()
report_path = event_pipeline.ingest_events(
    con, provider, start="2010-01-01", end="2026-07-15")
print(f"quality report: {report_path}\n")
print(report_path.read_text(encoding="utf-8"))
