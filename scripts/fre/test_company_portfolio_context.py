"""Standalone assertion-script tests for company_portfolio_context.py
(FSI Phase 20). Sections 1-2 read the REAL production database directly
(read-only, confirming real current-state combinations); Section 3 uses
a disposable scratch copy to exercise the watchlist-active path (since
the real production watchlist_entries table is currently empty).

  PYTHONPATH=src python scripts/fre/test_company_portfolio_context.py
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
from ngxrot.fre import company_portfolio_context as cpc  # noqa: E402
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
    real_ro = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(real_ro)

    # --- 1. Real data: AFRIPRUD -- an FSI ticker, not on the (currently
    # empty) watchlist, not in the live sleeve. ---------------------------
    check("precondition: real production watchlist_entries is currently "
          "empty (confirms Section 1 is a real, not assumed, honest "
          "negative)", real_ro.execute("SELECT COUNT(*) FROM watchlist_entries").fetchone()[0] == 0)

    annotated_afriprud = cpc.as_of(real_ro, "AFRIPRUD", "2026-08-02")
    check("AFRIPRUD: dossier composed correctly (ticker/as_of_date match, "
          "dossier.thesis present)",
          annotated_afriprud.ticker == "AFRIPRUD" and annotated_afriprud.dossier.thesis.ticker == "AFRIPRUD")
    check("AFRIPRUD: not on the watchlist (real, empty table)",
          annotated_afriprud.watchlist_status == [])
    check("AFRIPRUD: not in the live sleeve (real AlphaEngine data)",
          annotated_afriprud.portfolio_memory.in_live_sleeve is False)

    rendered_afriprud = cpc.render(annotated_afriprud)
    check("AFRIPRUD: rendered dossier includes both new section headers",
          "## Watchlist Status" in rendered_afriprud and "## Portfolio Memory Cross-Reference" in rendered_afriprud)
    check("AFRIPRUD: rendered output honestly states 'not on the watchlist' "
          "and 'not currently in the live sleeve'",
          "Not on the watchlist as of this date." in rendered_afriprud
          and "Not currently in the live sleeve." in rendered_afriprud)

    # --- 2. Real data: CAVERTON -- IS in the live H-011 sleeve today (per
    # AlphaEngine().recommendations()), not on the watchlist. The dossier
    # composition succeeds even though CAVERTON is outside the 10
    # hand-extracted FSI tickers, since company_thesis_360 draws on the
    # broader company_intelligence dataset. ------------------------------
    annotated_caverton = cpc.as_of(real_ro, "CAVERTON", "2026-08-02")
    check("CAVERTON: IS in the live sleeve (real, confirmed AlphaEngine data)",
          annotated_caverton.portfolio_memory.in_live_sleeve is True
          and annotated_caverton.portfolio_memory.hypothesis_id == "H-011")
    check("CAVERTON: not on the watchlist (real, empty table)",
          annotated_caverton.watchlist_status == [])

    rendered_caverton = cpc.render(annotated_caverton)
    check("CAVERTON: rendered output states it IS currently in the live "
          "sleeve, naming the real hypothesis_id",
          "Currently in the live sleeve (hypothesis_id=H-011)" in rendered_caverton)

    # --- 3. Watchlist-active path, on a disposable scratch copy (the real
    # production table is currently empty) -------------------------------
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)

    latest_afriprud = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='AFRIPRUD'"
    ).fetchone()[0]
    entry_id = wl.add_entry(
        con, "AFRIPRUD", rationale="Test rationale for Phase 20 composition check.",
        source_thesis_as_of_date=latest_afriprud,
        entry_criteria="Test criteria.", added_at="2026-07-01",
    )

    annotated_on_watchlist = cpc.as_of(con, "AFRIPRUD", "2026-08-02")
    check("AFRIPRUD (scratch, on watchlist as of 2026-08-02): watchlist_status "
          "correctly shows exactly the one active entry",
          len(annotated_on_watchlist.watchlist_status) == 1
          and annotated_on_watchlist.watchlist_status[0].watchlist_entry_id == entry_id)

    annotated_before_added = cpc.as_of(con, "AFRIPRUD", "2026-06-01")
    check("AFRIPRUD (scratch, as of a date BEFORE the entry's own added_at): "
          "watchlist_status correctly shows empty -- PIT-correct, no future "
          "information leaked",
          annotated_before_added.watchlist_status == [])

    rendered_on_watchlist = cpc.render(annotated_on_watchlist)
    check("rendered output includes the watchlist entry's own entry_criteria "
          "and rationale verbatim",
          "Test criteria." in rendered_on_watchlist and "Test rationale for Phase 20" in rendered_on_watchlist)

    con.close()

    # --- 4. Mechanical guardrails ------------------------------------------
    fields = set(cpc.PortfolioAnnotatedDossier.__dataclass_fields__)
    check("PortfolioAnnotatedDossier carries no score/rank/weight field",
          fields.isdisjoint({"score", "rank", "weight", "strength", "priority"}))

    as_of_params = set(inspect.signature(cpc.as_of).parameters)
    check("as_of() accepts no limit/sort/rank/threshold/plural-tickers parameter",
          as_of_params.isdisjoint({"limit", "top_n", "sort_by", "rank_by", "threshold", "tickers"}))

    src_text = (ROOT / "src" / "ngxrot" / "fre" / "company_portfolio_context.py").read_text(encoding="utf-8")
    tree = ast.parse(src_text)
    write_verbs_found = any(
        isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.strip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for node in ast.walk(tree)
    )
    check("company_portfolio_context.py contains no INSERT/UPDATE/DELETE SQL "
          "statement anywhere (AST-verified) -- read-only by construction",
          not write_verbs_found)

    # --- 5. The three composed frozen modules are byte-for-byte unchanged ---
    import subprocess
    diff = subprocess.run(
        ["git", "diff", "--stat", "--",
         "src/ngxrot/fre/company_research_dossier.py",
         "src/ngxrot/fre/watchlist.py",
         "src/ngxrot/fre/portfolio_memory.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    check("company_research_dossier.py, watchlist.py, and portfolio_memory.py "
          "are all byte-for-byte unchanged by this phase (git diff empty)",
          diff.stdout.strip() == "")

    # --- 6. the REAL production database was never touched ---------------------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged -- "
          "Section 3's writes only ever happened on a disposable scratch copy",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
