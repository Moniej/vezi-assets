"""Standalone assertion-script tests for src/ngxrot/fre/reaction_check.py --
same no-pytest, script-based convention as the other FRE test scripts.

SAFETY: reaction_check.py has NO write path at all (purely read-only), so
every test here opens the real production database via a read-only URI
connection -- there is no scratch copy needed because there is nothing to
mutate.

  PYTHONPATH=src python scripts/fre/test_reaction_check.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.reaction_check import reaction_check  # noqa: E402

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

    # --- GTCO (implication_id 1): a real, concrete disagreement between the
    # existing LLM verdict and the deterministic price check --------------
    con = ro()
    r1 = reaction_check(con, 1)
    check("GTCO: direction is 'bullish' (the real, recorded verdict)", r1.direction == "bullish")
    check("GTCO: realized return is real and negative (~-1.3%)",
          r1.realized_return is not None and -0.02 < r1.realized_return < -0.01)
    check("GTCO: direction_check is 'direction_contradicted' -- the "
          "deterministic check disagrees with the LLM's bullish call, "
          "consistent with this fact's own real self-critique block",
          r1.direction_check == "direction_contradicted")
    check("GTCO: existing market_reaction_assessment is untouched ('fairly_priced')",
          r1.existing_market_reaction_assessment == "fairly_priced")
    check("GTCO: not flagged as ex-dividend confound (fact_type is rights_issue, not dividend)",
          r1.ex_dividend_confound_flag is False)
    con.close()

    # --- a dividend fact: the ex-dividend confound flag must fire --------
    con = ro()
    r2 = reaction_check(con, 3)  # TOTAL, fact_type='dividend'
    check("a dividend implication is flagged with the ex-dividend confound note",
          r2.ex_dividend_confound_flag is True)
    con.close()

    # --- thin-liquidity instruments: MOFIREIF (NAV-pegged fund units) -----
    con = ro()
    r_mofi = reaction_check(con, 16)
    check("MOFIREIF is flagged thin-liquidity (a NAV-pegged fund, 1-7 deals/day)",
          r_mofi.thin_liquidity_flag is True)
    check("MOFIREIF's realized return is exactly 0.0 (price pegged at NAV, "
          "not a real market reaction)", r_mofi.realized_return == 0.0)
    con.close()

    # --- neutral/unknown direction never gets a direction_check verdict --
    con = ro()
    r_neutral = reaction_check(con, 2)  # REDSTAREX, direction='neutral'
    check("a 'neutral' direction is correctly 'not_applicable', never forced "
          "into confirmed/contradicted", r_neutral.direction_check == "not_applicable")
    con.close()

    # --- every one of the 18 real implications resolves without error ----
    con = ro()
    all_ids = [r[0] for r in con.execute("SELECT implication_id FROM investment_implications").fetchall()]
    check("all 18 real implications exist", len(all_ids) == 18)
    results = [reaction_check(con, iid) for iid in all_ids]
    check("reaction_check runs cleanly on all 18 real implications, no exception",
          len(results) == 18)
    n_thin = sum(1 for r in results if r.thin_liquidity_flag)
    check("exactly 4 of 18 real implications are flagged thin-liquidity "
          "(LIVINGTRUST, STANBICETF30, MOFIREIF x2)", n_thin == 4)
    n_confirmed = sum(1 for r in results if r.direction_check == "direction_confirmed")
    n_contradicted = sum(1 for r in results if r.direction_check == "direction_contradicted")
    check("3 confirmed, 1 contradicted, matching the real, inspected result set",
          n_confirmed == 3 and n_contradicted == 1)
    con.close()

    # --- a nonexistent implication_id raises, never silently fabricates ---
    con = ro()
    raised = False
    try:
        reaction_check(con, 999999)
    except ValueError:
        raised = True
    check("a nonexistent implication_id raises ValueError, never returns a "
          "fabricated result", raised)
    con.close()

    # --- confirm the real production database was never touched ----------
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write "
          "path at all)", doc_count_after == doc_count_before)
    reaction_cols_untouched = con.execute(
        "SELECT market_reaction_assessment, market_reaction_reasoning FROM "
        "investment_implications WHERE implication_id = 1"
    ).fetchone()
    check("GTCO's existing market_reaction_assessment/reasoning are still "
          "exactly what they were -- never overwritten by this module",
          reaction_cols_untouched[0] == "fairly_priced" and
          "CBN directives" in reaction_cols_untouched[1])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
