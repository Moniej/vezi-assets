"""Standalone assertion-script tests for sector_company_type_mapping.py
(FSI Phase 26), validated against real production data.

  PYTHONPATH=src python scripts/fre/test_sector_company_type_mapping.py
"""
from __future__ import annotations

import ast
import inspect
import sqlite3
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import sector_company_type_mapping as scm  # noqa: E402
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

    # --- 1. Real, unambiguous top-level-sector resolutions ------------------
    check("GTCO (FINANCIAL SERVICES/Banking) resolves to 'bank'",
          scm.derive_company_type_for_ticker(real_ro, "GTCO") == "bank")
    check("AIICO (FINANCIAL SERVICES/Insurance Carriers...) resolves to 'insurance'",
          scm.derive_company_type_for_ticker(real_ro, "AIICO") == "insurance")
    check("NASCON (CONSUMER GOODS) resolves to 'general'",
          scm.derive_company_type_for_ticker(real_ro, "NASCON") == "general")
    check("CUSTODIAN/TRANSCORP/JOHNHOLT (CONGLOMERATES) all resolve to "
          "'holding_company'",
          all(scm.derive_company_type_for_ticker(real_ro, t) == "holding_company"
              for t in ("CUSTODIAN", "TRANSCORP", "JOHNHOLT")))

    # --- 2. Deliberately unresolved cases return None, never a guess --------
    check("UCAP (FINANCIAL SERVICES/'Other Financial Institutions', "
          "deliberately unresolved) returns None",
          scm.derive_company_type_for_ticker(real_ro, "UCAP") is None)
    check("NPFMCRFBK (FINANCIAL SERVICES/'Micro-Finance Banks', deliberately "
          "unresolved) returns None",
          scm.derive_company_type_for_ticker(real_ro, "NPFMCRFBK") is None)
    check("UBN (real ticker, sector_ngx IS NULL) returns None",
          scm.derive_company_type_for_ticker(real_ro, "UBN") is None)
    check("NOTAREALTICKER (no matching securities row) returns None",
          scm.derive_company_type_for_ticker(real_ro, "NOTAREALTICKER") is None)

    # --- 3. Config sanity: growth_company/turnaround_company never appear --
    with open(ROOT / "configs" / "sector_company_type_mapping.toml", "rb") as fh:
        mapping = tomllib.load(fh)
    all_values = list(mapping.get("sector", {}).values()) + \
        list(mapping.get("financial_services_sub_industry", {}).values())
    check("growth_company/turnaround_company never appear as a value in "
          "sector_company_type_mapping.toml (lifecycle classifications, not "
          "industry classifications -- unreachable from sector_ngx by design)",
          "growth_company" not in all_values and "turnaround_company" not in all_values)

    valid_company_types = {"bank", "insurance", "holding_company", "growth_company",
                            "turnaround_company", "general"}
    check("every value in sector_company_type_mapping.toml is a real company_type "
          "from valuation_method_eligibility.toml's own taxonomy",
          all(v in valid_company_types for v in all_values))

    check("FINANCIAL SERVICES is absent from the [sector] table (resolved via "
          "sub-industry only, never guessed at the top level)",
          "FINANCIAL SERVICES" not in mapping.get("sector", {}))

    # --- 4. Real-data confirmation: none of the 10 FSI tickers resolve to
    # bank/insurance, so no readiness/valuation output changes for any of
    # them (the central backward-compatibility claim of this phase) --------
    fsi_tickers = ["MTNN", "DANGCEM", "UBN", "OANDO", "NESTLE", "NASCON",
                   "UCAP", "CAP", "BUAFOODS", "AFRIPRUD"]
    fsi_company_types = {t: scm.derive_company_type_for_ticker(real_ro, t) for t in fsi_tickers}
    check("none of the 10 real FSI tickers resolve to 'bank' or 'insurance' "
          "under the new mapping (confirms zero change to any real "
          "readiness/valuation-output test)",
          all(ct not in ("bank", "insurance") for ct in fsi_company_types.values()))

    # --- 4b. Readiness-gate change confirmed honest, not a crash: a
    # CONGLOMERATES-classified ticker's eligible_methods becomes
    # ['sum_of_the_parts'], which has NO adapter implementation at all --
    # value_company() must still report a clear, disclosed reason, never
    # crash or silently skip ---------------------------------------------------
    from ngxrot.fre.valuation_engine import value_company  # noqa: E402
    tv = value_company(real_ro, "TRANSCORP", "2026-08-02")
    check("TRANSCORP (CONGLOMERATES -> holding_company) reports "
          "eligible_methods=['sum_of_the_parts']",
          tv.company_type == "holding_company" and tv.eligible_methods == ["sum_of_the_parts"])
    check("TRANSCORP's sum_of_the_parts readiness is NOT_READY with a clear, "
          "disclosed 'no adapter implementation yet' reason -- never a crash, "
          "never a fabricated result",
          not tv.readiness_by_method["sum_of_the_parts"].ready
          and "no adapter implementation yet" in tv.readiness_by_method["sum_of_the_parts"].reason
          and len(tv.results) == 0)

    # --- 5. Mechanical guardrails --------------------------------------------
    params = set(inspect.signature(scm.derive_company_type_for_ticker).parameters)
    check("derive_company_type_for_ticker() is single-ticker only (no plural/"
          "list/limit parameter)",
          params.isdisjoint({"tickers", "limit", "top_n"}) and "ticker" in params)

    src_text = (ROOT / "src" / "ngxrot" / "fre" / "sector_company_type_mapping.py").read_text(encoding="utf-8")
    tree = ast.parse(src_text)
    write_verbs_found = any(
        isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.strip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for node in ast.walk(tree)
    )
    check("sector_company_type_mapping.py contains no INSERT/UPDATE/DELETE "
          "SQL statement anywhere (AST-verified) -- read-only by construction",
          not write_verbs_found)

    # --- 6. the REAL production database was never touched ---------------------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
