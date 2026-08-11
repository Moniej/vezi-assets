"""Tests for the Research OS infrastructure layer: research_dataset.py,
research_quality.py, research_experiment.py. Read-only against the real
production DB for dataset/quality checks; experiment recording is tested
against a scratch copy of registry.sqlite (never the real one) using a
deliberately DESCRIPTIVE research question, not an alpha hypothesis.

  PYTHONPATH=src python scripts/test_research_os.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db, registry  # noqa: E402
from ngxrot.research_dataset import get_equity_dataset, get_index_dataset  # noqa: E402
from ngxrot.research_experiment import (  # noqa: E402
    ExperimentResult, ExperimentSpec, load_research_run, record_research_run)
from ngxrot.research_quality import (  # noqa: E402
    corporate_action_notes, missing_observations, quality_flags, quality_report,
    source_conflicts, ticker_identity_notes)

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)

    # --- research_dataset.py -------------------------------------------
    ds = get_equity_dataset(con, "2024-01-01", "2024-01-10", tickers=["CILEASING"])
    check("get_equity_dataset: real rows returned for a real ticker/window", ds.row_count > 0)
    check("get_equity_dataset: manifest carries query_params + content_hash + code_fingerprint",
          set(ds.manifest()) >= {"dataset_kind", "query_params", "row_count", "content_hash",
                                  "captured_at", "code_fingerprint"})
    ds2 = get_equity_dataset(con, "2024-01-01", "2024-01-10", tickers=["CILEASING"])
    check("get_equity_dataset: identical query -> identical content_hash (deterministic)",
          ds.content_hash == ds2.content_hash)
    ds_universe = get_equity_dataset(con, "2024-06-01", "2024-06-30", universe_as_of="2024-06-30")
    check("get_equity_dataset: universe_as_of resolves a real IRU ticker set (>0 tickers used)",
          ds_universe.query_params["tickers"] and len(ds_universe.query_params["tickers"]) > 0)
    check("get_equity_dataset: universe_version is populated when IRU is used",
          ds_universe.universe_version is not None)

    idx = get_index_dataset(con, "2024-01-01", "2024-01-31", index_codes=["NGXASI"])
    check("get_index_dataset: real NGXASI rows returned", idx.row_count > 0)

    # snapshot recording against a SCRATCH registry db, never the real one
    scratch_dir = Path(tempfile.mkdtemp())
    scratch_registry = scratch_dir / "registry.sqlite"
    reg = registry.connect_registry(scratch_registry)
    snap_id = ds.record_snapshot(reg, notes="test run")
    check("record_snapshot: returns a real snapshot_id", bool(snap_id))
    row = reg.execute("SELECT row_count, content_hash FROM dataset_snapshots WHERE snapshot_id=?",
                      (snap_id,)).fetchone()
    check("record_snapshot: row actually persisted with matching row_count/content_hash",
          row is not None and row[0] == ds.row_count and row[1] == ds.content_hash)
    try:
        reg.execute("UPDATE dataset_snapshots SET row_count = 0 WHERE snapshot_id = ?", (snap_id,))
        check("dataset_snapshots is immutable: UPDATE was unexpectedly allowed", False)
    except sqlite3.IntegrityError:
        check("dataset_snapshots is immutable: UPDATE correctly raised (trigger fired)", True)
    reg.rollback()

    # --- research_quality.py --------------------------------------------
    qf = quality_flags(con, ["CILEASING"], "2024-01-01", "2024-01-10")
    check("quality_flags: finds the real unadjusted_jump entry logged this session",
          (qf.check_name == "unadjusted_jump").any())

    mo = missing_observations(con, ["CILEASING", "DANGCEM"], "2024-01-01", "2024-03-31")
    check("missing_observations: returns one row per ticker with real counts",
          len(mo) == 2 and (mo.days_present + mo.days_missing == mo.trading_days_in_calendar).all())

    sc = source_conflicts(con, ["CILEASING", "NESTLE"], "2025-01-01", "2025-12-31", tolerance_pct=0.01)
    check("source_conflicts: returns a well-formed DataFrame (empty or populated, never crashes)",
          list(sc.columns) if not sc.empty else True)

    idn = ticker_identity_notes(con, ["GTCO", "CAP"])
    check("ticker_identity_notes: GTCO correctly flagged as having rename history",
          bool(idn[idn.ticker == "GTCO"].has_rename_history.iloc[0]))
    check("ticker_identity_notes: CAP correctly flagged as NOT having rename history",
          not bool(idn[idn.ticker == "CAP"].has_rename_history.iloc[0]))

    can = corporate_action_notes(con, ["CILEASING"])
    check("corporate_action_notes: finds the real CILEASING bonus_issue fact from extracted_facts",
          ((can.source_table == "extracted_facts") & (can.action_type == "bonus_issue")).any())

    report = quality_report(con, ["CILEASING"], "2024-01-01", "2024-01-10")
    check("quality_report: composes all five sections", set(report) >= {
        "tickers", "period", "quality_flags", "missing_observations",
        "source_conflicts", "identity_notes", "corporate_action_notes"})

    # --- research_experiment.py -- DESCRIPTIVE run only, not alpha -------
    spec = ExperimentSpec(
        research_question="What does the CILEASING data-quality profile look like for "
                          "2024-01-01..2024-01-10? (infrastructure smoke test, not a trading hypothesis)",
        dataset_snapshot_ids=[snap_id],
        observation_period_start="2024-01-01", observation_period_end="2024-01-10",
        transformations=[],  # no transformation applied -- purely descriptive
        analysis_method="research_quality.quality_report composition",
    )
    result = ExperimentResult(spec=spec, results=report, notes="Research OS infrastructure test")
    run_id = record_research_run(reg, result)
    check("record_research_run: returns a real run_id", bool(run_id))
    loaded = load_research_run(reg, run_id)
    check("load_research_run: round-trips research_question and dataset_snapshot_ids",
          loaded is not None and loaded["research_question"] == spec.research_question
          and loaded["dataset_snapshot_ids"] == [snap_id])
    try:
        reg.execute("DELETE FROM research_runs WHERE run_id = ?", (run_id,))
        check("research_runs is immutable: DELETE was unexpectedly allowed", False)
    except sqlite3.IntegrityError:
        check("research_runs is immutable: DELETE correctly raised (trigger fired)", True)
    reg.rollback()

    reg.close()
    con.close()
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
