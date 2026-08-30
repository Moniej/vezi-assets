"""P4 -- Investment OS Value Test (CAPITAL ALLOCATION MODE, 2026-08-13).

Measures whether the Investment OS materially improves research over the
manual/ad-hoc baseline, on representative tasks. Read-only against
production throughout (mcon never written to; registry opened read-only
for the memory-search task; scratch DB used only for the DQ task copy).

  PYTHONPATH=src python scripts/p4_os_value_test.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot import registry as mreg  # noqa: E402
from ngxrot import research_query as rq  # noqa: E402
from ngxrot.research_memory import check_prior_art  # noqa: E402
from ngxrot.fre.data_quality_monitoring import run_all_checks  # noqa: E402

mcon = mdb.connect()
reg = mreg.connect_registry()

results = []


def record(task, approach, elapsed, steps, pit_captured, lineage_captured,
           reproducible_by_construction, errors_found):
    results.append(dict(task=task, approach=approach, elapsed_s=round(elapsed, 3),
                         manual_steps=steps, pit_captured=pit_captured,
                         lineage_captured=lineage_captured,
                         reproducible_by_construction=reproducible_by_construction,
                         errors_found=errors_found))


# ---------------------------------------------------------------------------
# Task 1: "What financial facts exist for DANGCEM, PIT-safe as of 2026-08-05?"
# ---------------------------------------------------------------------------

# Baseline: hand-written SQL, no PIT filter built in -- the researcher has to
# remember to add it themselves, and nothing records that they did.
t0 = time.time()
raw = mcon.execute(
    "SELECT f.fact_id, f.fact_type, f.numeric_value, f.period_end, d.filing_date, d.doc_id "
    "FROM extracted_facts f JOIN documents d ON f.doc_id = d.doc_id "
    "WHERE d.ticker = 'DANGCEM' AND d.filing_date <= '2026-08-05'"
).fetchall()
# researcher must manually re-derive "what's the source/evidence trail" --
# a second, separate query, easy to skip under time pressure
sources = mcon.execute(
    "SELECT DISTINCT d.doc_id, d.local_path, d.source_id FROM documents d "
    "WHERE d.ticker='DANGCEM' AND d.filing_date <= '2026-08-05'"
).fetchall()
t1 = time.time()
record("DANGCEM facts as-of 2026-08-05", "baseline_manual_sql", t1 - t0,
       steps=2, pit_captured="manual, easy to omit", lineage_captured="separate query required",
       reproducible_by_construction=False, errors_found="none (no validation run)")

# OS-assisted: one call, PIT + provenance + reproducibility built in
t0 = time.time()
spec = rq.QuerySpec(query_type="document_context", entities=["DANGCEM"], as_of="2026-08-05")
qres = rq.execute(mcon, spec, reg=reg)
t1 = time.time()
record("DANGCEM facts as-of 2026-08-05", "os_query_layer", t1 - t0,
       steps=1, pit_captured="structural (as_of param)", lineage_captured="qres.provenance, built-in",
       reproducible_by_construction=True, errors_found="none new (same underlying data)")

print(f"Task 1: baseline row_count={len(raw)}, OS row_count={qres.row_count}, "
      f"provenance_entries={len(qres.provenance)}")

# ---------------------------------------------------------------------------
# Task 2: "Have we tested a small-cap size-premium hypothesis before?"
# ---------------------------------------------------------------------------

# Baseline: the researcher greps markdown files and hypothesis descriptions
# by hand, hoping they remember/find the right file names and keywords.
t0 = time.time()
rows = reg.execute("SELECT hypothesis_id, description, status, conclusion FROM hypotheses").fetchall()
manual_hits = [r for r in rows if "size" in (r[1] or "").lower() or "small" in (r[1] or "").lower()]
t1 = time.time()
record("prior art: size-premium hypothesis", "baseline_manual_grep", t1 - t0,
       steps=1, pit_captured="n/a", lineage_captured="none (just full-text substring match)",
       reproducible_by_construction=True,
       errors_found=f"{len(manual_hits)} substring matches, unranked, no family classification")

# OS-assisted: deterministic ranked prior-art search
t0 = time.time()
report = check_prior_art(reg, "Small-cap size premium, long smallest-cap quintile within IRU")
t1 = time.time()
record("prior art: size-premium hypothesis", "os_research_memory", t1 - t0,
       steps=1, pit_captured="n/a", lineage_captured="ranked by shared factor family + overlap score",
       reproducible_by_construction=True,
       errors_found=f"{len(report.formal_matches)} ranked formal matches "
                    f"(top: {report.formal_matches[0].hypothesis_id if report.formal_matches else 'none'})")

print(f"Task 2: baseline substring hits={len(manual_hits)}, "
      f"OS ranked formal matches={len(report.formal_matches)}, "
      f"top match={report.formal_matches[0].hypothesis_id if report.formal_matches else None}")

# ---------------------------------------------------------------------------
# Task 3: "Are there data-quality issues affecting UACN's facts?"
# ---------------------------------------------------------------------------

# Baseline: the researcher would have to know to check for each failure
# class individually and write bespoke SQL for each (duplicates, conflicts,
# unit-scale, entity mismatch, PIT) -- in practice, this basically never
# gets done exhaustively by hand. Approximate the realistic baseline: one
# eyeball query for outright duplicate (doc_id, fact_type, period) rows.
t0 = time.time()
dupe_check = mcon.execute(
    "SELECT doc_id, fact_type, period_end, COUNT(*) c FROM extracted_facts "
    "WHERE doc_id IN (SELECT doc_id FROM documents WHERE ticker='UACN') "
    "GROUP BY doc_id, fact_type, period_end HAVING c > 1"
).fetchall()
t1 = time.time()
record("UACN data-quality check", "baseline_manual_sql_dupes_only", t1 - t0,
       steps=1, pit_captured="n/a", lineage_captured="n/a",
       reproducible_by_construction=True,
       errors_found=f"{len(dupe_check)} dup groups -- ONLY checks duplicates; unit-scale/entity/"
                    f"conflict/PIT classes not checked at all under this baseline")

# OS-assisted: full 10-check sweep, scratch copy (read-only against prod)
scratch = Path(tempfile.mkdtemp()) / "ngx_scratch.sqlite"
shutil.copy2(mdb.DEFAULT_DB, scratch)
scon = mdb.init_db(scratch)
t0 = time.time()
alerts = [a for a in run_all_checks(scon) if a.ticker == "UACN"]
t1 = time.time()
record("UACN data-quality check", "os_data_quality_monitoring", t1 - t0,
       steps=1, pit_captured="n/a (checked as one of the 10 classes)",
       lineage_captured="each alert carries fact_id + check_name",
       reproducible_by_construction=True,
       errors_found=f"{len(alerts)} alerts across ALL 10 failure classes "
                    f"({sorted({a.check_name for a in alerts})})")

print(f"Task 3: baseline dup groups={len(dupe_check)}, OS total alerts (10 classes)={len(alerts)}")

# ---------------------------------------------------------------------------
print("\n=== P4 results table ===")
for r in results:
    print(r)

# production untouched
assert mcon.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0] == 495
assert mcon.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0] == 403
print("\nProduction unchanged: extracted_facts=495, financial_reasoning_conclusions=403")
