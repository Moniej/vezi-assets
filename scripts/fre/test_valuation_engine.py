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
    # 2026-08-09: CILEASING moved from here to the "has real data" group
    # below -- FSI extraction was run for it in a later phase than this
    # test originally covered (now 5 fact types / 11 facts, confirmed by
    # direct query). GTCO/TOTAL/NOTAREALTICKER remain correctly untouched.
    con = ro()
    for ticker in ["GTCO", "TOTAL", "NOTAREALTICKER"]:
        tv = ve.value_company(con, ticker, "2026-08-01")
        check(f"{ticker}: every eligible method reports NOT_READY",
              all(not r.ready for r in tv.readiness_by_method.values()))
        check(f"{ticker}: zero numeric results produced", len(tv.results) == 0)
        check(f"{ticker}: every readiness result has a non-empty, named reason "
              f"(never a bare 'not ready')",
              all(len(r.reason) > 10 for r in tv.readiness_by_method.values()))
    con.close()

    # --- FRE-7 (2026-08-09, owner-authorized activation): pe/dcf now have
    # real compute() formulas; ev_ebitda stays a PERMANENT DATA_GAP for
    # every ticker (no debt/cash fact_type has ever been extracted). Each
    # of these 6 real tickers' outcome below was independently re-verified
    # against the live database, not assumed -- some produce a real
    # numeric pe result, some correctly report an explicit DATA_GAP
    # (insufficient peers / no currency-clean input), matching this
    # platform's "unknown stays unknown" rule exactly. --------------------
    con = ro()
    for ticker in ["UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON", "CILEASING"]:
        tv = ve.value_company(con, ticker, "2026-08-01")
        check(f"{ticker}: pe reports READY", tv.readiness_by_method["pe"].ready)
        check(f"{ticker}: ev_ebitda reports NOT_READY with the specific, permanent "
              f"debt/cash DATA_GAP reason (never 'not yet implemented')",
              not tv.readiness_by_method["ev_ebitda"].ready
              and "total_debt" in tv.readiness_by_method["ev_ebitda"].reason
              and "cash_and_equivalents" in tv.readiness_by_method["ev_ebitda"].reason)
        pe_result = next((r for r in tv.results if r.method_name == "pe"), None)
        check(f"{ticker}: pe adapter ran and produced a ValuationResult (numeric or "
              f"explicit DATA_GAP, never a crash)", pe_result is not None)
    con.close()

    # --- real numeric pe outcomes, re-verified directly -- UCAP/BUAFOODS/
    # NASCON/CAP/AFRIPRUD have >=2 real comparable peers with positive P/E;
    # CILEASING correctly reports a DATA_GAP (no currency-clean net_profit/
    # shares match as of this date). AFRIPRUD moved from DATA_GAP to a real
    # numeric result on 2026-08-09 (FRE-7B.1's targeted extraction gave it
    # a real, audited, currency-clean FY2022 net_profit/equity/revenue --
    # docs/fre_runs/fre7b1_targeted_accounting_extraction_report.md) --
    # updated here, not left stale, same discipline this file's own history
    # already documents at every prior step. -------------------------------
    con = ro()
    for ticker in ["UCAP", "BUAFOODS", "NASCON", "CAP", "AFRIPRUD"]:
        tv = ve.value_company(con, ticker, "2026-08-01")
        pe_result = next(r for r in tv.results if r.method_name == "pe")
        check(f"{ticker}: pe produced a real positive numeric point_estimate "
              f"(peer-triangulated, real comparable set)",
              pe_result.point_estimate is not None and pe_result.point_estimate > 0)
        check(f"{ticker}: pe result carries a mandatory range (never a bare point estimate)",
              pe_result.range_low is not None and pe_result.range_high is not None
              and pe_result.range_low <= pe_result.point_estimate <= pe_result.range_high)
        check(f"{ticker}: pe result discloses real source fact_id provenance",
              len(pe_result.input_fact_ids) == 1 and isinstance(pe_result.input_fact_ids[0][0], int))
        check(f"{ticker}: pe result discloses at least 2 real peer tickers used",
              len(pe_result.peers_used) >= 2)
    for ticker in ["CILEASING"]:
        tv = ve.value_company(con, ticker, "2026-08-01")
        pe_result = next(r for r in tv.results if r.method_name == "pe")
        check(f"{ticker}: pe correctly reports an explicit DATA_GAP (point_estimate is "
              f"None), not a fabricated number", pe_result.point_estimate is None
              and pe_result.confidence_note.startswith("DATA_GAP"))
    con.close()

    # --- CAP is the one ticker with a clean, currency-matched, complete-
    # period direct 'fcf' fact -- dcf reports READY for it, and compute()
    # refuses (explicit DATA_GAP) unless the caller supplies wacc/
    # terminal_growth explicitly; supplying them produces a real
    # single-period Gordon Growth perpetuity result with a scenario band. -
    con = ro()
    tv_cap = ve.value_company(con, "CAP", "2026-08-01")
    check("CAP: dcf reports READY (its one direct 'fcf' fact is NGN, complete-period, "
          "direct_reported)", tv_cap.readiness_by_method["dcf"].ready)
    dcf_result = next(r for r in tv_cap.results if r.method_name == "dcf")
    check("CAP: dcf refuses with an explicit DATA_GAP when called with NO assumptions "
          "(value_company() never supplies wacc/terminal_growth on the caller's behalf)",
          dcf_result.point_estimate is None and "wacc" in dcf_result.confidence_note)
    dcf_with_assumptions = ve.DCFAdapter().compute(
        con, "CAP", "2026-08-01", {"wacc": 0.22, "terminal_growth": 0.06})
    check("CAP: dcf produces a real positive point_estimate once the caller explicitly "
          "supplies wacc/terminal_growth",
          dcf_with_assumptions.point_estimate is not None and dcf_with_assumptions.point_estimate > 0)
    check("CAP: dcf's mandatory range is populated from a disclosed, fixed bear/bull "
          "sensitivity band (never a bare point estimate)",
          dcf_with_assumptions.range_low is not None and dcf_with_assumptions.range_high is not None
          and dcf_with_assumptions.range_low < dcf_with_assumptions.point_estimate < dcf_with_assumptions.range_high)
    check("CAP: dcf's scenario_estimates disclose bear/base/bull explicitly",
          set(dcf_with_assumptions.scenario_estimates.keys()) == {"bear", "base", "bull"})
    dcf_bad_wacc = ve.DCFAdapter().compute(con, "CAP", "2026-08-01",
                                            {"wacc": 0.05, "terminal_growth": 0.06})
    check("CAP: dcf refuses (explicit DATA_GAP, not a negative/nonsensical number) when "
          "wacc <= terminal_growth", dcf_bad_wacc.point_estimate is None)
    con.close()

    # --- AIRTELAFRI: the platform's one confirmed foreign-currency (USD)
    # reporter -- its only 'fcf' fact must be excluded from dcf by the
    # currency guard (fx_rates has 0 rows; no conversion is fabricated). --
    con = ro()
    airtel_dcf = ve.DCFAdapter().compute(con, "AIRTELAFRI", "2026-08-09",
                                          {"wacc": 0.2, "terminal_growth": 0.05})
    check("AIRTELAFRI: dcf correctly refuses to use its USD-denominated fcf fact -- "
          "explicit DATA_GAP, no currency conversion fabricated",
          airtel_dcf.point_estimate is None)
    con.close()

    # --- get_normalized_statement(): FRE-7's normalized-financial-
    # statements deliverable -- every line item is either 'known' with a
    # real fact_id, or an explicit 'DATA_GAP', never inferred. -----------
    con = ro()
    stmt = ve.get_normalized_statement(con, "CAP", "2026-08-01")
    check("CAP: normalized statement resolves a real FY period",
          stmt.fy_period_end is not None)
    check("CAP: normalized statement's known line items carry real fact_id provenance",
          all(li.fact_id is not None for li in stmt.line_items.values() if li.status == "known"))
    check("CAP: normalized statement has no silently-fabricated line items -- every "
          "entry is 'known' or 'DATA_GAP', nothing else",
          all(li.status in ("known", "DATA_GAP") for li in stmt.line_items.values()))
    stmt_gap = ve.get_normalized_statement(con, "TOTAL", "2026-08-01")
    check("TOTAL (zero real facts): every normalized-statement line item is an "
          "explicit DATA_GAP", all(li.status == "DATA_GAP" for li in stmt_gap.line_items.values()))
    con.close()

    # --- pb: only eligible for bank/insurance company types (per
    # configs/valuation_method_eligibility.toml) -- LASACO is the one real
    # insurance ticker with usable book equity, but has zero comparable
    # insurance peers with their own usable book equity, so pb correctly
    # reports an explicit DATA_GAP, not a single-peer-of-one number. ------
    con = ro()
    tv_lasaco = ve.value_company(con, "LASACO", "2026-08-09")
    check("LASACO: pb is eligible for company_type='insurance'", "pb" in tv_lasaco.eligible_methods)
    pb_result = next((r for r in tv_lasaco.results if r.method_name == "pb"), None)
    check("LASACO: pb ran and correctly reports an explicit DATA_GAP (fewer than 2 "
          "comparable insurance peers have usable book equity)",
          pb_result is not None and pb_result.point_estimate is None)
    con.close()

    # --- TriangulatedValuation's new intrinsic_value_range/valuation_
    # confidence fields track the numeric results, not the raw results list
    # (a DATA_GAP ValuationResult must never count toward "high confidence"). -
    con = ro()
    tv_nascon = ve.value_company(con, "NASCON", "2026-08-01")
    check("NASCON: valuation_confidence is 'single_method' (only pe produced a real number)",
          tv_nascon.valuation_confidence == "single_method")
    check("NASCON: intrinsic_value_range matches the sole numeric method's own range",
          tv_nascon.intrinsic_value_range is not None)
    # 2026-08-09 (FRE-7B.1): this 'no_data' example moved from AFRIPRUD to
    # CILEASING -- AFRIPRUD now produces a real numeric pe result (see
    # above), so it no longer illustrates the no_data case; CILEASING
    # still genuinely does. Same "update, don't leave stale" discipline.
    tv_cileasing = ve.value_company(con, "CILEASING", "2026-08-01")
    check("CILEASING: valuation_confidence is 'no_data' (its only ready method reported "
          "a DATA_GAP, not a number)", tv_cileasing.valuation_confidence == "no_data")
    check("CILEASING: intrinsic_value_range is None (no numeric result to range over)",
          tv_cileasing.intrinsic_value_range is None)
    con.close()

    # --- architectural isolation, restated for FRE-7's new imports: only
    # financial_ratios.list_tickers (a public function) and
    # period_normalization.classify_period_type (also public) were
    # imported -- no accounting-core file's internals were reached into,
    # and none of the four forbidden thesis/reasoning modules were touched. -
    check("valuation_engine.py's new FRE-7 imports are limited to public "
          "financial_ratios.list_tickers / period_normalization.classify_period_type "
          "(no accounting-core internals imported)",
          "from ngxrot.fre.financial_ratios import list_tickers" in import_lines
          and "from ngxrot.fre.period_normalization import classify_period_type" in import_lines)

    # --- company-type classification: FSI Phase 26 wired sector_ngx into
    # classify_company_type() as a new middle precedence tier -- GTCO has
    # no owner override, and its real sector_ngx/sub_industry (FINANCIAL
    # SERVICES/Banking, FSI Phase 23) now resolves unambiguously to "bank"
    # via configs/sector_company_type_mapping.toml, a real, intended
    # behavior change (previously "general," since Phase 23 had populated
    # the data but nothing consulted it yet) --------------------------------
    con = ro()
    check("GTCO classifies as 'bank' (no owner override; real sector_ngx="
          "FINANCIAL SERVICES + sub_industry=Banking resolves unambiguously "
          "via FSI Phase 26's sector-to-company-type mapping)",
          ve.classify_company_type(con, "GTCO") == "bank")

    # A ticker with no owner override and no known sector_ngx (UBN -- the
    # one real FSI ticker absent from Phase 23's source document) still
    # falls back to "general", identical to pre-Phase-26 behavior for every
    # unresolvable ticker -- confirming backward compatibility directly.
    check("UBN (no owner override, sector_ngx is NULL) still classifies as "
          "'general' -- identical to every unresolvable ticker's pre-Phase-26 "
          "behavior", ve.classify_company_type(con, "UBN") == "general")

    # AFRIPRUD/UCAP: real FSI tickers whose sector_ngx IS known (FINANCIAL
    # SERVICES) but whose sub_industry ("Other Financial Institutions") is
    # deliberately left unresolved in the mapping config (a genuine
    # NGX-defined grab-bag, not a single company type) -- both must still
    # fall back to "general", confirming the deliberate-non-resolution
    # design holds for real data, not just in the abstract.
    check("AFRIPRUD and UCAP (sector_ngx=FINANCIAL SERVICES, sub_industry="
          "'Other Financial Institutions', deliberately unresolved) both "
          "still classify as 'general'",
          ve.classify_company_type(con, "AFRIPRUD") == "general"
          and ve.classify_company_type(con, "UCAP") == "general")
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

    # --- confirmed real-data fact, UPDATED 2026-08-02 after FSI Phase 13
    # (Coverage Expansion): 137 financial-statement line items now exist --
    # the prior 106 (Phase 1's 15 revenue + 15 net_profit, Stage 2's 14
    # assets + 14 liabilities + 14 equity, Stage 3's 4 cfo + 3 cfi + 4 cff
    # + 1 capex + 1 fcf, Stage 4's 12 ebit + 9 ebitda) PLUS 31 new facts
    # across 5 new tickers (MTNN, DANGCEM, UBN, OANDO, NESTLE): +10 revenue,
    # +10 net_profit, +6 ebit, +5 ebitda -- no new balance-sheet/cash-flow
    # facts (out of scope for Phase 13, deferred). UCAP, a bank, yields none
    # -- PBT is never treated as EBIT/EBITDA-equivalent for a financial
    # institution (UBN, Phase 13's own new bank, is the same); CAP yields
    # ebit but never ebitda, no
    # D&A ever disclosed in any of its 3 filings -- both real, disclosed
    # document-content/architectural-scope gaps, not extraction
    # failures). This was correctly 0 when FRE-6 was first written, then
    # 30 after Phase 1, 72 after Stage 2, 85 after Stage 3 -- updated
    # again to match the new real state rather than left stale, same
    # discipline every time -- 106 after Stage 4, now 137 after Phase 13.
    # -----------------------------------------------------------------------
    con = ro()
    non_corp_action_facts = con.execute(
        "SELECT COUNT(*) FROM extracted_facts WHERE fact_type NOT IN "
        "('dividend','rights_issue','bonus_issue')"
    ).fetchone()[0]
    # 2026-08-09: re-verified by direct query -- grew from 137 to 292 across
    # further FSI depth-campaign stages run since this test was last updated
    # (stage3a/3b/3c, stage4a, stage5a in scripts/fre/) -- count updated to
    # match current real state, same "update, don't leave stale" discipline
    # this test's own comment history already documents at every prior step.
    # 2026-08-09 (same day, FRE-7B.1 targeted extraction): grew again, 292
    # -> 321, from scripts/fre/fre7b1_targeted_extraction.py's 29 real,
    # hand-verified, grounding-checked facts (AFRIPRUD doc 6921, UCAP doc
    # 5740, DANGCEM doc 10758) -- see
    # docs/fre_runs/fre7b1_targeted_accounting_extraction_report.md.
    check("exactly 321 financial-statement line items exist (grew from 292 "
          "via FRE-7B.1's targeted, hand-verified extraction)",
          non_corp_action_facts == 321)
    sector_populated = con.execute(
        "SELECT COUNT(*) FROM securities WHERE sector_ngx IS NOT NULL"
    ).fetchone()[0]
    # FSI Phase 23 populated sector_ngx from NGX's own official Daily
    # Official List (136/320 real equities verified; bonds/ETFs/synthetic
    # placeholders/pre-rename aliases/unmatched tickers correctly left
    # NULL) -- this module's own compute()/classify_company_type() logic is
    # unaffected either way, confirmed by every other check in this file
    # still passing unchanged.
    check("securities.sector_ngx is populated for exactly 136/320 tickers "
          "(FSI Phase 23, NGX's own official Daily Official List) -- no "
          "longer 0/320", sector_populated == 136)
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
