"""Real-database regression test for the has_financial_statements fix
(2026-08-11, HANDOFF.md) -- CoverageAssessment.has_financial_statements
was previously a hardcoded False regardless of real data; it is now
computed per-ticker from extracted_facts against fact_taxonomy.toml's
[financial_statements] leaf set.

Read-only against the real production database.

  PYTHONPATH=src python scripts/test_coverage_assessment_financial_statements.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.context import build_reasoning_context  # noqa: E402
from ngxrot.documents.coverage_assessment import _financial_statement_fact_types  # noqa: E402

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

    fst = _financial_statement_fact_types()
    check("taxonomy: [financial_statements] leaf set is non-empty and matches fact_taxonomy.toml",
          fst == {"revenue", "net_profit", "assets", "liabilities", "equity", "cfo", "cfi", "cff",
                  "capex", "fcf", "ebitda", "ebit", "cogs", "gross_profit"})

    # NASCON and UCAP are real, verified to have extracted revenue/net_profit
    # facts as of 2026-08-11 (queried directly from data/ngx.sqlite before
    # writing this test -- not assumed from documentation).
    for ticker in ["NASCON", "UCAP"]:
        n_financial_facts = con.execute(
            "SELECT COUNT(*) FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id "
            f"WHERE (d.ticker = ? OR d.raw_symbol = ?) AND ef.fact_type IN "
            f"({','.join('?' * len(fst))})", (ticker, ticker, *fst)).fetchone()[0]
        check(f"{ticker}: real extracted_facts confirm >=1 financial-statement fact exists",
              n_financial_facts > 0)

        ctx = build_reasoning_context(con, ticker, as_of="2026-08-10")
        ca = ctx.coverage_assessment
        check(f"{ticker}: has_financial_statements is now True (was hardcoded False before the fix)",
              ca.has_financial_statements is True)
        check(f"{ticker}: 'has_financial_statements' correctly present in dimensions_present, "
              f"not dimensions_missing",
              "has_financial_statements" in ca.dimensions_present
              and "has_financial_statements" not in ca.dimensions_missing)

    # A ticker genuinely without financial-statement facts (an ETF -- no
    # income statement/balance sheet of its own) must still show False --
    # the fix must not become a new "always True" bug in the other direction.
    ctx_etf = build_reasoning_context(con, "STANBICETF30", as_of="2026-08-10")
    ca_etf = ctx_etf.coverage_assessment
    check("STANBICETF30 (an ETF, genuinely no financial-statement facts): "
          "has_financial_statements correctly stays False",
          ca_etf.has_financial_statements is False)
    check("STANBICETF30: 'has_financial_statements' correctly present in dimensions_missing",
          "has_financial_statements" in ca_etf.dimensions_missing)
    check("STANBICETF30: the honest per-ticker explanation is disclosed, not a platform-wide claim",
          any("[financial_statements]" in r for r in ca_etf.reasons_confidence_limited))

    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
