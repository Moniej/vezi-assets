"""Standalone assertion-script tests for watchlist.py (FSI Phase 18).
All writes happen only on a disposable scratch copy of the real database
-- the production database (data/ngx.sqlite) is never written to by
this test, confirmed explicitly at the end.

  PYTHONPATH=src python scripts/fre/test_watchlist.py
"""
from __future__ import annotations

import ast
import inspect
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import watchlist as wl  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

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
    # Production immutability is checked against the REAL database, opened
    # read-only, separately from the scratch copy every write in this test
    # actually happens against.
    real_ro = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(real_ro)

    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)

    latest_nascon = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='NASCON'"
    ).fetchone()[0]

    # --- 1. add_entry() writes correctly, with a real, resolvable thesis pointer
    entry_id = wl.add_entry(
        con, "NASCON", rationale="Real leverage_increasing flag fired (Phase 3, conclusion 172).",
        source_thesis_as_of_date=latest_nascon,
        entry_criteria="Would become portfolio-relevant if a second, independent validated "
                       "factor confirms exposure to this sector (per Part 9's own Tier-2 gate).",
        review_cadence="on-next-filing",
    )
    check("add_entry() returns a real watchlist_entry_id", isinstance(entry_id, int) and entry_id > 0)

    history = wl.get_history_for_ticker(con, "NASCON")
    check("get_history_for_ticker() returns exactly the one entry just added, with "
          "removed_at/removal_reason both None (active)",
          len(history) == 1 and history[0].watchlist_entry_id == entry_id
          and history[0].removed_at is None and history[0].removal_reason is None)

    # --- 2. add_entry() validation: unknown ticker, empty rationale/criteria,
    # unresolvable thesis pointer all raise -------------------------------------
    try:
        wl.add_entry(con, "NOTAREALTICKER", rationale="x", source_thesis_as_of_date=latest_nascon,
                     entry_criteria="x")
        unknown_raised = False
    except ValueError:
        unknown_raised = True
    check("add_entry() raises ValueError for an unknown ticker", unknown_raised)

    try:
        wl.add_entry(con, "NASCON", rationale="   ", source_thesis_as_of_date=latest_nascon,
                     entry_criteria="x")
        empty_rationale_raised = False
    except ValueError:
        empty_rationale_raised = True
    check("add_entry() raises ValueError for an empty rationale", empty_rationale_raised)

    try:
        wl.add_entry(con, "NASCON", rationale="x", source_thesis_as_of_date=latest_nascon,
                     entry_criteria="   ")
        empty_criteria_raised = False
    except ValueError:
        empty_criteria_raised = True
    check("add_entry() raises ValueError for an empty entry_criteria "
          "(must be stated in advance, per Part 9's own design)", empty_criteria_raised)

    # --- 3. schema-level NOT NULL is the real backstop, not just the Python
    # function's own check -- confirmed by attempting a raw INSERT that bypasses
    # add_entry() entirely -------------------------------------------------------
    try:
        con.execute(
            "INSERT INTO watchlist_entries (ticker, added_at, rationale, source_thesis_as_of_date, "
            "review_cadence, entry_criteria) VALUES ('NASCON', '2026-08-02', 'x', '2026-08-02', NULL, NULL)"
        )
        schema_enforced = False
    except sqlite3.IntegrityError:
        schema_enforced = True
    check("entry_criteria is enforced NOT NULL at the SCHEMA level (a raw INSERT "
          "bypassing add_entry() entirely still fails)", schema_enforced)

    # --- 4. remove_entry(): append-only -- marks removed, never deletes --------
    before_remove_count = con.execute("SELECT COUNT(*) FROM watchlist_entries").fetchone()[0]
    wl.remove_entry(con, entry_id, removed_at="2026-08-03", removal_reason="Test removal.")
    after_remove_count = con.execute("SELECT COUNT(*) FROM watchlist_entries").fetchone()[0]
    check("remove_entry() does NOT delete the row -- row count unchanged",
          before_remove_count == after_remove_count)
    removed_record = wl.get_history_for_ticker(con, "NASCON")[0]
    check("the removed entry's removed_at/removal_reason are now populated",
          removed_record.removed_at == "2026-08-03" and removed_record.removal_reason == "Test removal.")

    try:
        wl.remove_entry(con, entry_id, removed_at="2026-08-04", removal_reason="Second attempt.")
        double_remove_raised = False
    except ValueError:
        double_remove_raised = True
    check("remove_entry() raises if called again on an already-removed entry "
          "(cannot be removed twice or 'un-removed')", double_remove_raised)

    try:
        wl.remove_entry(con, 999999, removed_at="2026-08-03", removal_reason="x")
        nonexistent_raised = False
    except ValueError:
        nonexistent_raised = True
    check("remove_entry() raises for a nonexistent watchlist_entry_id", nonexistent_raised)

    # --- 5. list_active(): correctly excludes the now-removed NASCON entry,
    # correctly includes a second, still-active entry for a different ticker ---
    latest_cap = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='CAP'"
    ).fetchone()[0]
    wl.add_entry(con, "CAP", rationale="Tracking for real coverage.", source_thesis_as_of_date=latest_cap,
                 entry_criteria="Would matter once a second validated factor exists.")
    active = wl.list_active(con, as_of_date="2026-08-05")
    active_tickers = [e.ticker for e in active]
    check("list_active() correctly excludes the removed NASCON entry and "
          "includes the still-active CAP entry",
          "NASCON" not in active_tickers and "CAP" in active_tickers)
    check("list_active() results are in strict alphabetical-ticker order, "
          "never value-sorted", active_tickers == sorted(active_tickers))

    # PIT correctness: as of a date BEFORE NASCON's entry was removed, it
    # should still show as active.
    active_before_removal = wl.list_active(con, as_of_date="2026-08-02")
    check("as of a date before the removal, NASCON's entry still shows as active "
          "(PIT-correct: removal takes effect only from removed_at onward)",
          "NASCON" in [e.ticker for e in active_before_removal])

    # --- 6. mechanical guardrails -----------------------------------------------
    record_fields = set(wl.WatchlistEntryRecord.__dataclass_fields__)
    check("WatchlistEntryRecord carries no score/rank/weight field of any kind",
          record_fields.isdisjoint({"score", "rank", "weight", "strength", "priority"}))
    list_active_params = set(inspect.signature(wl.list_active).parameters)
    check("list_active() accepts no limit/sort/rank/threshold-style parameter",
          list_active_params.isdisjoint({"limit", "top_n", "sort_by", "rank_by", "weight", "threshold"}))

    tree = ast.parse((ROOT / "src" / "ngxrot" / "fre" / "watchlist.py").read_text(encoding="utf-8"))
    delete_found = any(
        isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.strip().upper().startswith("DELETE")
        for node in ast.walk(tree)
    )
    check("watchlist.py contains no DELETE SQL statement anywhere (confirmed "
          "via AST inspection of every string literal) -- append-only by construction",
          not delete_found)

    con.close()

    # --- 7. the REAL production database was never touched ---------------------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged -- "
          "every write in this test happened only on a disposable scratch copy",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
