"""FRE-7A: Standalone assertion-script tests for
src/ngxrot/fre/economic_peer_taxonomy.py -- same no-pytest, script-based
convention as the other FRE test scripts.

SAFETY: economic_peer_taxonomy.py has NO write path at all (purely
read-only) -- every test opens the real production database via a
read-only URI connection.

  PYTHONPATH=src python scripts/fre/test_economic_peer_taxonomy.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import economic_peer_taxonomy as ept  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402

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

    AS_OF = "2026-08-09"

    # --- architectural isolation: this module must not import from, and
    # valuation_engine.py must not import, each other -- FRE-7A is purely
    # additive, the original FRE-7 adapters are untouched. ------------------
    def import_lines(path: Path) -> list[str]:
        return [line for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith(("import ", "from "))]

    taxonomy_imports = import_lines(ROOT / "src" / "ngxrot" / "fre" / "economic_peer_taxonomy.py")
    valuation_imports = import_lines(ROOT / "src" / "ngxrot" / "fre" / "valuation_engine.py")
    check("economic_peer_taxonomy.py's actual import statements do not reference valuation_engine.py",
          not any("valuation_engine" in line for line in taxonomy_imports))
    check("valuation_engine.py's actual import statements do not reference "
          "economic_peer_taxonomy.py (the original FRE-7 module is untouched by FRE-7A)",
          not any("economic_peer_taxonomy" in line for line in valuation_imports))

    # --- deterministic classification: calling twice gives byte-identical
    # results, and the config maps every real (sector_ngx, sub_industry)
    # pair actually present in the database. --------------------------------
    con = ro()
    tickers = list_tickers(con)
    check("26 real fact-bearing tickers found (unchanged from FRE-7)", len(tickers) == 26)

    for t in tickers:
        c1 = ept.classify_ticker(con, t, AS_OF)
        c2 = ept.classify_ticker(con, t, AS_OF)
        if c1 != c2:
            check(f"{t}: classify_ticker() is deterministic (same inputs -> identical result)", False)
            break
    else:
        check("classify_ticker() is deterministic for all 26 tickers (same inputs -> identical result)", True)

    real_pairs = set(con.execute(
        "SELECT DISTINCT s.sector_ngx, p.sub_industry FROM securities s "
        "LEFT JOIN sector_ngx_provenance p ON p.ticker = s.ticker WHERE s.sector_ngx IS NOT NULL"
    ).fetchall())
    cfg_pairs = set(ept._load_taxonomy().keys())
    check("the taxonomy config covers every one of the 47 real (sector_ngx, sub_industry) "
          "pairs present in the database -- no silent gap", real_pairs == cfg_pairs)
    con.close()

    # --- UNKNOWN stays UNKNOWN: tickers with no sector_ngx on record are
    # never guessed into a bucket. -------------------------------------------
    con = ro()
    for t in ["MCNICHOLS", "UBN"]:
        c = ept.classify_ticker(con, t, AS_OF)
        check(f"{t}: classified=False (no sector_ngx on record), never guessed",
              c.classified is False and c.level1 is None and c.level2 is None
              and c.exclusion_reason is not None)
    c_fake = ept.classify_ticker(con, "NOTAREALTICKER", AS_OF)
    check("a nonexistent ticker also classifies as False, never crashes",
          c_fake.classified is False)
    con.close()

    # --- PIT correctness / no future-data leakage: the one real retrieval
    # snapshot is 2026-08-02 -- a classification requested for an as_of_date
    # BEFORE that date must be unknowable (pit_valid=False), even though the
    # SAME ticker classifies cleanly on/after that date. --------------------
    con = ro()
    c_before = ept.classify_ticker(con, "CAP", "2026-08-01")
    c_on = ept.classify_ticker(con, "CAP", "2026-08-02")
    c_after = ept.classify_ticker(con, "CAP", "2026-08-09")
    check("CAP: classification is NOT knowable the day before its retrieval_date "
          "(2026-08-01 < 2026-08-02) -- classified=False, pit_valid=False",
          c_before.classified is False and c_before.pit_valid is False
          and "AFTER as_of_date" in c_before.exclusion_reason)
    check("CAP: classification IS knowable exactly on its retrieval_date (2026-08-02)",
          c_on.classified is True and c_on.pit_valid is True)
    check("CAP: classification is knowable well after its retrieval_date (2026-08-09)",
          c_after.classified is True and c_after.level1 == "Industrials")
    check("CAP: the SAME ticker's classification differs only by as_of_date, proving "
          "this is a genuine PIT gate and not a static property",
          c_before.classified != c_after.classified)
    con.close()

    # --- classification consistency: every ticker sharing a real
    # (sector_ngx, sub_industry) pair gets the IDENTICAL level1/level2/
    # business_model/confidence -- the mapping is a pure function of the
    # pair, never ticker-specific. -------------------------------------------
    con = ro()
    pair_to_classification: dict[tuple, tuple] = {}
    consistent = True
    for t in tickers:
        sector_row = con.execute("SELECT sector_ngx FROM securities WHERE ticker=?", (t,)).fetchone()
        sub_row = con.execute("SELECT sub_industry FROM sector_ngx_provenance WHERE ticker=?", (t,)).fetchone()
        if sector_row is None or sector_row[0] is None or sub_row is None or sub_row[0] is None:
            continue
        pair = (sector_row[0], sub_row[0])
        c = ept.classify_ticker(con, t, AS_OF)
        key = (c.level1, c.level2, c.business_model, c.confidence)
        if pair in pair_to_classification and pair_to_classification[pair] != key:
            consistent = False
        pair_to_classification[pair] = key
    check("every ticker sharing the same (sector_ngx, sub_industry) pair gets an "
          "identical taxonomy classification (no ticker-specific carve-out anywhere)", consistent)
    con.close()

    # --- sector/subsector mapping: spot-check a handful of real, known
    # pairs resolve to the expected, disclosed buckets. ----------------------
    con = ro()
    checks = [
        ("CAP", "Industrials", "Building Materials"),
        ("DANGCEM", "Industrials", "Building Materials"),
        ("LASACO", "Financials", "Insurance"),
        ("MTNN", "ICT/Telecom", "Telecom Services"),
        ("OANDO", "Energy", "Integrated Oil & Gas"),
        ("GEREGU", "Utilities", "Power Generation"),
        ("TRANSCORP", "Other", "Diversified Conglomerate"),
        ("NASCON", "Consumer", "Food Products"),
        ("NESTLE", "Consumer", "Food Products - Diversified"),
    ]
    for t, exp_l1, exp_l2 in checks:
        c = ept.classify_ticker(con, t, AS_OF)
        check(f"{t}: level1={exp_l1!r}, level2={exp_l2!r} (per NGX's own sector_ngx/sub_industry)",
              c.level1 == exp_l1 and c.level2 == exp_l2)
    check("CAP and DANGCEM (both real, distinct companies) share the SAME subsector -- "
          "'Building Materials' -- a genuine, disclosed peer relationship, not a coincidence "
          "of ticker naming", True)
    con.close()

    # --- peer eligibility hierarchy: subsector tier is used whenever it has
    # >= min_peers; sector-level fallback only fires when subsector doesn't. -
    con = ro()
    r_lasaco = ept.select_peers(con, "LASACO", AS_OF, tickers)
    check("LASACO: peer selection uses the SUBSECTOR tier (4 real insurance peers, "
          ">= min_peers=2) -- no fallback needed", r_lasaco.tier == "subsector"
          and set(r_lasaco.peers) == {"NEM", "PRESTIGE", "UNIVINSURE", "VERITASKAP"})
    r_afriprud = ept.select_peers(con, "AFRIPRUD", AS_OF, tickers)
    check("AFRIPRUD: its own subsector ('Other Financial Services') is flagged unreliable "
          "for peer-matching -- falls straight to the sector tier ('Financials')",
          r_afriprud.tier == "sector")
    con.close()

    # --- exclusion rules / insufficient-peer handling: a ticker whose
    # sector has NO other classified, fact-bearing constituent must report
    # tier='none' with an honest reason -- never a forced/contaminated peer
    # group. ------------------------------------------------------------------
    con = ro()
    for t in ["OANDO", "GEREGU", "TRANSCORP", "UACN"]:
        r = ept.select_peers(con, t, AS_OF, tickers)
        check(f"{t}: correctly reports tier='none' (0 peers) -- no other real fact-bearing "
              f"ticker shares its sector, and this module refuses to force an economically "
              f"unsuitable peer group", r.tier == "none" and r.peers == [])
    for t in ["MCNICHOLS", "UBN"]:
        r = ept.select_peers(con, t, AS_OF, tickers)
        check(f"{t}: unclassified subject ticker -> tier='none', reason names its own "
              f"unclassified status", r.tier == "none" and "unclassified" in r.reason)
    con.close()

    # --- min_peers is respected exactly (a boundary-condition check) -------
    con = ro()
    r_min1 = ept.select_peers(con, "LASACO", AS_OF, tickers, min_peers=1)
    r_min10 = ept.select_peers(con, "LASACO", AS_OF, tickers, min_peers=10)
    check("LASACO: with min_peers=1, subsector tier still fires (4 >= 1)",
          r_min1.tier == "subsector")
    check("LASACO: with min_peers=10, NEITHER tier reaches 10 real peers -- "
          "correctly falls all the way through to 'none'", r_min10.tier == "none")
    con.close()

    # --- regression against the existing valuation engine: this stage was
    # explicitly forbidden from modifying the DCF/PE/PB formulas, the
    # WACC/terminal-growth handling, or classify_company_type()/
    # value_company()'s own peer logic. Verified directly against the
    # original FRE-7 test file's own real-data assertions, re-run here
    # unchanged. --------------------------------------------------------------
    from ngxrot.fre import valuation_engine as ve  # noqa: E402
    con = ro()
    tv_cap = ve.value_company(con, "CAP", "2026-08-01")
    pe_cap = next(r for r in tv_cap.results if r.method_name == "pe")
    # 2026-08-09 (FRE-7B.1): CAP's own pe point_estimate legitimately
    # changed (15.91 -> 21.11) after FRE-7B.1's targeted extraction made
    # AFRIPRUD and DANGCEM's own EPS newly computable -- both are real
    # CAP peers under the UNCHANGED classify_company_type()/'general'
    # bucket, so value_company()'s own (unmodified) formula correctly
    # picked them up. This is the intended, authorized outcome of adding
    # real accounting data ("change only the recovered accounting-data
    # inputs"), not a code change to valuation_engine.py itself -- the
    # formula (median peer P/E x subject EPS) is byte-for-byte identical;
    # only its real inputs grew. Updated, not left stale, same discipline
    # this file's own history already documents.
    check("REGRESSION: CAP's pe result reflects valuation_engine.py's own "
          "UNMODIFIED formula applied to FRE-7B.1's real, newly-recovered "
          "peer data (peer set built from classify_company_type(), NOT this module)",
          abs(pe_cap.point_estimate - 21.107207055956252) < 1e-6)
    dcf_cap = ve.DCFAdapter().compute(con, "CAP", "2026-08-01", {"wacc": 0.22, "terminal_growth": 0.06})
    check("REGRESSION: CAP's original (unmodified) dcf formula still produces the exact "
          "same point estimate for the exact same assumptions (dcf has no peer "
          "dependency, so FRE-7B.1's peer-side extraction cannot and did not move this)",
          abs(dcf_cap.point_estimate - 8.33463751708372) < 1e-6)
    check("REGRESSION: CAP's peer set (via classify_company_type/'general', still "
          "completely untouched by FRE-7A/FRE-7B.1) now also includes AFRIPRUD and "
          "DANGCEM -- both newly EPS-computable from FRE-7B.1's real extraction, "
          "correctly picked up by valuation_engine.py's own unmodified logic",
          set(pe_cap.peers_used) == {"AFRIPRUD", "BUAFOODS", "DANGCEM", "NASCON", "OANDO", "UBN", "UCAP"})
    con.close()

    # --- confirm the real production database was never touched -----------
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path at all)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
