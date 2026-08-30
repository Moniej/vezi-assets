"""One-document timing smoke test: how long does a real extract_document()
call take through LocalLIMProvider (allow_unvalidated=True, eval-harness
use only), before committing GPU time to the full gold-set run.

  PYTHONPATH=src python scripts/lim/smoketest_extraction.py <doc_id> <scratch_db_path>
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.extract import extract_document  # noqa: E402
from ngxrot.documents.llm_providers import LocalLIMProvider  # noqa: E402

doc_id = int(sys.argv[1])
scratch_path = sys.argv[2]

con = db.init_db(scratch_path)
provider = LocalLIMProvider(model_id="qwen3-4b-lim-rb3b-checkpoint40", allow_unvalidated=True)
print(f"provider: {provider.info}")

t0 = time.time()
result = extract_document(con, provider, doc_id=doc_id,
                          cache_dir=Path(scratch_path).parent / "llm_cache")
elapsed = time.time() - t0

print(f"elapsed={elapsed:.1f}s parse_ok={result.parse_ok} facts={len(result.fact_ids)} "
     f"warnings={result.warnings}")
facts = con.execute(
    "SELECT fact_type, numeric_value, period_start, period_end, period_type FROM "
    "extracted_facts WHERE doc_id=?", (doc_id,)).fetchall()
for f in facts:
    print(" fact:", f)
