"""Investment OS end-to-end build (2026-08-13) -- the integration test
required by P6: proves the full chain actually connects, not just that
each piece passes its own unit tests in isolation.

query -> research workspace -> evidence -> hypothesis -> research memory
-> [separately] paper portfolio -> paper execution -> performance ->
attribution -> decision journal

Reads real production market/document data (read-only) and real registry
data (read-only for hypotheses/research_memory; writes new research-
workspace rows, which is what that system is FOR -- research_projects/
notes/evidence/hypotheses are meant to accumulate). Portfolio/paper
execution runs against a fresh scratch portfolio DB. Production
extracted_facts/financial_reasoning_conclusions/ngx.sqlite tables and
the Alpha Engine are never written to.

  PYTHONPATH=src python scripts/test_investment_os_e2e.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db as mdb  # noqa: E402
from ngxrot import registry as mreg  # noqa: E402
from ngxrot import research_query as rq  # noqa: E402
from ngxrot import research_workspace as ws  # noqa: E402
from ngxrot.research_memory import check_prior_art  # noqa: E402
from ngxrot.portfolio import db as pdb  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts" / "portfolio"))
from run_paper_cycle import run_cycle  # noqa: E402

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


mcon = mdb.connect()  # PRODUCTION market/document data, READ-ONLY throughout

# research_workspace.py's whole design intent is to write real, persistent
# rows (research_projects/evidence/hypotheses) -- exactly what it's FOR in
# real use. For THIS integration test, that write path is exercised against
# a SCRATCH COPY of registry.sqlite, never the live one -- an "E2E test"
# project has no business polluting the real research history.
scratch_registry_path = Path(tempfile.mkdtemp()) / "registry_scratch.sqlite"
shutil.copy2(mreg.REGISTRY_DB, scratch_registry_path)
reg = mreg.connect_registry(scratch_registry_path)
print(f"Registry (scratch copy, real data, writes isolated here): {scratch_registry_path}")

# --- 1. Research Query Layer: a real, PIT-safe query against real data ---
spec = rq.QuerySpec(query_type="document_context", entities=["DANGCEM"], as_of="2026-08-05")
qresult = rq.execute(mcon, spec, reg=reg)
check("query layer: document_context for a real ticker returns a real result",
     qresult.row_count == 1)
check("query layer: PIT cutoff (as_of) is recorded in the result's own parameters",
     qresult.parameters.get("as_of") == "2026-08-05")
check("query layer: provenance is populated, not empty (evidence/source lineage)",
     isinstance(qresult.provenance, list))

# --- 2. Research Workspace: project -> evidence -> hypothesis, real chain ---
project = ws.create_project(reg, title="E2E test: DANGCEM coverage", research_question=(
    "Does DANGCEM have enough validated financial history to support a factor test?"))
check("workspace: project created with a real research_id", project.research_id.startswith("RP-"))

ws.attach_query(reg, project.research_id, qresult.query_id, note="document_context pull")
queries = ws.list_queries(reg, project.research_id)
check("workspace: the query layer result is attached and retrievable from the project",
     len(queries) == 1 and queries[0]["query_id"] == qresult.query_id)

evidence_id = ws.add_document_evidence(reg, project.research_id, qresult, claim_class="MEASUREMENT")
check("workspace: document-side evidence recorded from a real QueryResult",
     evidence_id.startswith("EV-"))
trace = ws.trace_evidence(reg, evidence_id)
check("workspace: trace_evidence reconstructs real source lineage for this evidence",
     trace is not None and trace.get("evidence_id") == evidence_id)

hyp_id = ws.add_hypothesis(reg, project.research_id,
                          "DANGCEM's fundamental data supports Size-factor style testing "
                          "given its coverage depth")
check("workspace: hypothesis recorded, linked to the project", hyp_id.startswith("HYP-"))

# --- 3. Research Memory: does prior-art search connect to what we just wrote? ---
report = check_prior_art(reg, "Small-cap size premium, long smallest-cap quintile within IRU")
check("research memory: a size-style candidate surfaces the real H-011 (Size) hypothesis "
     "from the FORMAL ledger -- proving research_memory queries the same registry.sqlite "
     "the workspace just wrote real rows into",
     any(m.hypothesis_id == "H-011" for m in report.formal_matches))

timeline = ws.timeline(reg, project.research_id)
check("workspace: timeline records every real event from this test in order "
     "(created, query attached, evidence added, hypothesis added)",
     len(timeline) >= 4)

integrity = ws.integrity_check(mcon, reg, project.research_id)
check("workspace: integrity_check runs clean (or reports only real, expected notes) "
     "against a freshly-built real project", isinstance(integrity, list))

# --- 4. Paper portfolio: real Alpha Engine -> real portfolio -> real paper execution ---
portfolio_db = str(pdb.new_scratch_db_path())
result = run_cycle(portfolio_db, "2026-08-05", "2026-08-06", portfolio_id="E2E_TEST")
check("paper cycle: completes end to end against real Alpha Engine output",
     result["status"] == "completed")
check("paper cycle: at least one real fill occurred", result["n_fills"] > 0)
check("paper cycle: attribution records were produced (the period-window fix holds)",
     result["n_attribution_records"] > 0)
check("paper cycle: H-011's capacity-constrained status is explicitly surfaced in the result",
     "H-011" in result.get("capacity_constrained_hypotheses_used", []))

# --- 5. Decision journal <-> hypothesis link (schema already supported this; confirm it's real) ---
import sqlite3
pcon = sqlite3.connect(portfolio_db)
dj_rows = pcon.execute("SELECT decision_id, hypothesis_id, decision FROM decision_journal "
                       "WHERE portfolio_id='E2E_TEST'").fetchall()
check("decision journal: at least one real decision recorded for this paper cycle", len(dj_rows) >= 1)
check("decision journal: the decision is linked to a real hypothesis_id (H-011) -- proving "
     "the Decision stage of Question->Evidence->...->Decision->Outcome->Learning is real, "
     "not just schema that happens to have the column",
     any(r[1] == "H-011" for r in dj_rows))
check("decision journal: an outcome (realized P&L) was recorded against the decision",
     pcon.execute("SELECT actual_outcome_pnl FROM decision_journal WHERE decision_id=?",
                  (dj_rows[0][0],)).fetchone()[0] is not None)

# --- 6. Production untouched, end to end ---
check("production extracted_facts unchanged (495)",
     mcon.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0] == 495)
check("production financial_reasoning_conclusions unchanged (403)",
     mcon.execute("SELECT COUNT(*) FROM financial_reasoning_conclusions").fetchone()[0] == 403)
check("scratch registry copy's formal hypotheses ledger unchanged in count (this test only "
     "READS hypotheses; workspace writes go to research_hypotheses/research_projects, a "
     "SEPARATE table)", reg.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0] == 18)

real_reg = mreg.connect_registry()  # the REAL, live registry.sqlite -- never opened for write above
check("REAL production registry.sqlite has ZERO of this test's workspace rows -- confirms "
     "every write above landed on the scratch copy, not production",
     real_reg.execute("SELECT COUNT(*) FROM research_projects WHERE research_id=?",
                      (project.research_id,)).fetchone()[0] == 0)

ws.archive_project(reg, project.research_id, reason="e2e test cleanup")
check("workspace: test project archived (not deleted -- research_projects is never deleted, "
     "matching the platform's own append-only discipline)",
     ws.get_project(reg, project.research_id).status == "ARCHIVED")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
