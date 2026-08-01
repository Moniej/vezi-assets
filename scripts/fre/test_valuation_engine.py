"""Standalone assertion-script tests for src/ngxrot/fre/valuation_engine.py
-- same no-pytest, script-based convention as the other FRE test scripts.

SAFETY: valuation_engine.py has NO write path at all (purely read-only) --
every test opens the real production database via a read-only URI
connection.

  PYTHONPATH=src python scripts/fre/test_valuation_engine.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import valuation_engine as ve  # noqa: E402

REAL_DB = db.DEFAULT_DB

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


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{REAL_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    con.close()

    # --- module independence: this file must import nothing from the
    # thesis/evidence/memory/reaction FRE modules (checked as actual import
    # statements, not the docstring's own prose explaining the isolation --
    # the docstring names all four modules deliberately, to state the
    # boundary in words; this check verifies the boundary in code) --------
    import_lines = [
        line for line in
        (ROOT / "src" / "ngxrot" / "fre" / "valuation_engine.py").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    forbidden_modules = ("company_thesis", "evidence_graph", "company_memory", "reaction_check")
    check("valuation_engine.py's actual import statements reference none of "
          "company_thesis/evidence_graph/company_memory/reaction_check "
          "(architecturally isolated from thesis generation, per instruction)",
          not any(mod in line for line in import_lines for mod in forbidden_modules))

    # --- tickers untouched by FSI Phase 1: every eligible method still
    # reports NOT_READY, verified against real data, not assumed ------------
    con = ro()
    for ticker in ["GTCO", "TOTAL", "CILEASING", "NOTAREALTICKER"]:
        tv = ve.value_company(con, ticker, "2026-08-01")
        check(f"{ticker}: every eligible method reports NOT_READY",
              all(not r.ready for r in tv.readiness_by_method.values()))
        check(f"{ticker}: zero numeric results produced", len(tv.results) == 0)
        check(f"{ticker}: every readiness result has a non-empty, named reason "
              f"(never a bare 'not ready')",
              all(len(r.reason) > 10 for r in tv.readiness_by_method.values()))
    con.close()

    # --- tickers FSI Phase 1 added real revenue/net_profit facts for: the
    # readiness gate now correctly reports READY for dcf/ev_ebitda/pe (real
    # financial-statement-shaped data exists for the first time on this
    # platform) -- but compute() has no implemented formula, so it MUST
    # still produce ZERO numeric results. This is the exact "no valuation
    # activation" invariant this test exists to enforce: readiness may
    # change as real data grows, a computed number never appears without a
    # real formula and an explicit, separate implementation decision. -----
    con = ro()
    for ticker in ["UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON"]:
        tv = ve.value_company(con, ticker, "2026-08-01")
        check(f"{ticker}: dcf/ev_ebitda/pe now report READY (real FSI Phase 1 "
              f"revenue/net_profit data exists for this ticker)",
              all(tv.readiness_by_method[m].ready for m in ("dcf", "ev_ebitda", "pe")))
        check(f"{ticker}: STILL zero numeric results produced -- READY per "
              f"data presence is not the same as a computed valuation "
              f"(no formula is implemented; no valuation activation occurred)",
              len(tv.results) == 0)
        check(f"{ticker}: the readiness reason explicitly discloses that "
              f"compute() is not yet implemented despite being ready",
              all("not yet implemented" in tv.readiness_by_method[m].reason
                  for m in ("dcf", "ev_ebitda", "pe")))
    con.close()

    # --- company-type classification: defaults to 'general' since
    # sector_ngx is unpopulated and the override list is deliberately empty -
    con = ro()
    check("GTCO classifies as 'general' (no owner-confirmed override exists, "
          "sector_ngx is 0/320 populated -- this module does not guess)",
          ve.classify_company_type("GTCO") == "general")
    con.close()

    # --- the compute() safety gate refuses unconditionally on real data ----
    con = ro()
    for adapter in [ve.DCFAdapter(), ve.DDMAdapter(), ve.ResidualIncomeAdapter(),
                    ve.EVEBITDAAdapter(), ve.PEAdapter(), ve.PBAdapter()]:
        raised = False
        try:
            adapter.compute(con, "TOTAL", "2026-08-01", assumptions={})
        except RuntimeError:
            raised = True
        check(f"{adapter.method_name}.compute() refuses to run on real data "
              f"(RuntimeError, never a fabricated number)", raised)
    con.close()

    # --- confirmed real-data fact, UPDATED 2026-08-01 after FSI Phase 1:
    # exactly 30 financial-statement line items now exist (the 15 real
    # revenue + 15 real net_profit facts from FSI Phase 1's own pilot
    # extraction, docs/fre_runs/fsi_phase1_results.md) -- no more, no less.
    # This was correctly 0 when FRE-6 was first written and verified; the
    # test is updated to match the new real state rather than left stale,
    # exactly the reason the 5 anchor tickers above now show READY. -------
    con = ro()
    non_corp_action_facts = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE fact_type NOT IN "
        "('dividend','rights_issue','bonus_issue')"
    ).fetchone()[0]
    check("exactly 30 financial-statement line items exist (FSI Phase 1's "
          "own 15 revenue + 15 net_profit facts, and nothing else)",
          non_corp_action_facts == 30)
    sector_populated = con.execute(
        "SELECT COUNT(*) FROM securities WHERE sector_ngx IS NOT NULL"
    ).fetchone()[0]
    check("securities.sector_ngx is confirmed 0/320 populated", sector_populated == 0)
    con.close()

    # --- config files load correctly ---------------------------------------
    eligibility = ve._load_eligibility()
    check("eligibility config has all 6 company types",
          set(eligibility.keys()) == {"bank", "insurance", "holding_company",
                                       "growth_company", "turnaround_company", "general"})
    overrides = ve._load_company_type_overrides()
    check("company-type override list is deliberately empty (owner-judged, "
          "not yet populated)", overrides == {})

    # --- confirm the real production database was never touched ------------
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write "
          "path at all)", doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
