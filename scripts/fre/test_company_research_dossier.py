"""Standalone assertion-script tests for company_research_dossier.py,
validated against real production data (read-only, zero write path
anywhere in this module).

  PYTHONPATH=src python scripts/fre/test_company_research_dossier.py
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import company_research_dossier as crd  # noqa: E402
from ngxrot.fre import company_thesis_360  # noqa: E402
from ngxrot.fre.entity_context import get_entity_context  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.financial_reasoning_report import render_report  # noqa: E402
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


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    before_counts = snapshot_all_table_counts(con)

    # FSI Phase 16: dynamic ticker discovery (was a hardcoded 5-ticker list
    # that silently stopped covering Phase 13's 5 new tickers).
    tickers = list_tickers(con)
    latest_dates = {}
    for ticker in tickers:
        latest_dates[ticker] = con.execute(
            "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=?", (ticker,),
        ).fetchone()[0]

    dossiers = {t: crd.build_dossier(con, t, latest_dates[t]) for t in tickers}
    reports = {t: crd.render_dossier(dossiers[t]) for t in tickers}

    # --- 1. Renders without exception for all real tickers ------------------
    check(f"build_dossier()/render_dossier() succeed for all {len(tickers)} "
          f"real tickers at their own latest real filing date, zero exceptions",
          all(t in reports for t in tickers))

    # --- 2. Section equivalence: the Company Memory portion of the rendered
    # dossier is BYTE-IDENTICAL to calling render_report() directly ----------
    memory_section_ok = True
    for ticker in tickers:
        direct_report = render_report(dossiers[ticker].memory)
        if not reports[ticker].startswith(direct_report):
            memory_section_ok = False
    check("the Company Memory portion of every rendered dossier is BYTE-"
          "IDENTICAL to calling render_report() directly on the same "
          "CompanyMemory360 snapshot (Phase 7 reused verbatim, never "
          "reimplemented)", memory_section_ok)

    # --- 3. Thesis/evidence equivalence: dossier.thesis/concern_evidence/
    # supplementary_evidence exactly match company_thesis_360.as_of() called
    # directly ----------------------------------------------------------------
    thesis_equivalence_ok = True
    for ticker in tickers:
        direct_bundle = company_thesis_360.as_of(con, ticker, latest_dates[ticker])
        d = dossiers[ticker]
        if d.thesis != direct_bundle.thesis or d.memory != direct_bundle.memory \
           or d.concern_evidence != direct_bundle.concern_evidence \
           or d.supplementary_evidence != direct_bundle.supplementary_evidence:
            thesis_equivalence_ok = False
    check(f"dossier.thesis/memory/concern_evidence/supplementary_evidence are "
          f"exactly equivalent to calling company_thesis_360.as_of() directly, "
          f"for all {len(tickers)} tickers", thesis_equivalence_ok)

    # --- 4. Graph equivalence: dossier.graph exactly matches get_entity_
    # context() called directly ------------------------------------------------
    graph_equivalence_ok = True
    for ticker in tickers:
        direct_graph = get_entity_context(con, ticker, latest_dates[ticker])
        if dossiers[ticker].graph != direct_graph:
            graph_equivalence_ok = False
    check(f"dossier.graph is exactly equivalent to calling get_entity_context() "
          f"directly, for all {len(tickers)} tickers", graph_equivalence_ok)

    # --- 5. Determinism: identical input -> byte-identical output ------------
    rendered_thrice = [crd.render_dossier(dossiers["NASCON"]) for _ in range(3)]
    check("render_dossier() produces byte-identical output across 3 calls on "
          "the SAME dossier object", rendered_thrice[0] == rendered_thrice[1] == rendered_thrice[2])

    fresh_dossier_1 = crd.build_dossier(con, "NASCON", "2026-03-03")
    fresh_dossier_2 = crd.build_dossier(con, "NASCON", "2026-03-03")
    check("render_dossier() produces byte-identical output for two "
          "INDEPENDENTLY built dossiers of the same (ticker, as_of_date) -- "
          "full-pipeline determinism, not just the renderer in isolation",
          crd.render_dossier(fresh_dossier_1) == crd.render_dossier(fresh_dossier_2))

    # --- 6. Both new sections appear, in the disclosed fixed order (Company
    # Memory -> Investment Thesis Evidence -> Knowledge Graph Context) -------
    order_ok = True
    for ticker in tickers:
        rpt = reports[ticker]
        thesis_idx = rpt.find("## Investment Thesis Evidence")
        graph_idx = rpt.find("## Knowledge Graph Context")
        if thesis_idx == -1 or graph_idx == -1 or thesis_idx > graph_idx:
            order_ok = False
    check("every rendered dossier contains both new sections, in the fixed, "
          "disclosed order (Investment Thesis Evidence before Knowledge "
          "Graph Context)", order_ok)

    # --- 7. NULL confidence tiers are never upgraded -- the same explicit
    # phrase used in Phase 7 appears for any FSI evidence item with a NULL
    # confidence_tier ----------------------------------------------------------
    null_tier_check_ok = True
    for ticker in tickers:
        d = dossiers[ticker]
        has_null_tier_item = any(
            item.confidence_tier is None for item in d.concern_evidence + d.supplementary_evidence
        )
        if has_null_tier_item and "confidence tier NOT RECORDED" not in reports[ticker]:
            null_tier_check_ok = False
    check("every NULL confidence_tier among the FSI evidence items is "
          "rendered with the explicit 'NOT RECORDED' phrase, never silently "
          "upgraded or omitted", null_tier_check_ok)

    # --- 8. No forbidden ranking/scoring/recommendation vocabulary anywhere
    # OUTSIDE this module's own disclaimer sentences --------------------------
    import re
    forbidden_terms = ("buy", "sell", "recommend", "target price", "expected return",
                       "undervalued", "overvalued")
    forbidden_whole_words = ("rank", "score", "rating")
    forbidden_found = []
    for ticker, rpt in reports.items():
        # exclude the module's own known disclaimer sentences (which legitimately
        # name these excluded categories to state what the report does NOT do)
        scrubbed = rpt
        for disclaimer in (
            "*This is a deterministic",
            "*This section restates FRE-5's own CompanyThesis",
            "*This section restates FSI Phase 9/10's own knowledge-graph",
        ):
            start = scrubbed.find(disclaimer)
            if start != -1:
                end = scrubbed.find("*", start + 1) + 1
                scrubbed = scrubbed[:start] + scrubbed[end:]
        # FRE-5's own frozen financial_signal_summary field always appends a
        # real, legitimate disclaimer ("...NOT a financial-statements-based
        # quality score -- that remains blocked pending...") that legitimately
        # uses the word 'score' to disclaim having one -- pre-existing real
        # data from a frozen module, not something Phase 11 introduces; found
        # as a real false positive during this test's own development (the
        # same class of finding as the "Operating Profit"/disclaimer false
        # positives caught while building Phase 7/8's own tests).
        scrubbed = scrubbed.replace(
            "NOT a financial-statements-based quality score -- that remains blocked pending a", ""
        )
        lower_scrubbed = scrubbed.lower()
        for term in forbidden_terms:
            if term in lower_scrubbed:
                forbidden_found.append((ticker, term))
        for word in forbidden_whole_words:
            if re.search(rf"\b{word}\w*\b", lower_scrubbed):
                forbidden_found.append((ticker, word))
    check(f"no forbidden ranking/scoring/recommendation vocabulary appears "
          f"anywhere in any of the {len(tickers)} real rendered dossiers "
          f"outside this module's own disclaimer sentences", forbidden_found == [])

    # --- 9. No synthesized field anywhere in the dossier dataclass ----------
    field_names = set(crd.CompanyResearchDossier.__dataclass_fields__.keys())
    check("CompanyResearchDossier's own dataclass fields are exactly "
          "{ticker, as_of_date, thesis, memory, graph, concern_evidence, "
          "supplementary_evidence} -- no combined score/rating/summary field",
          field_names == {"ticker", "as_of_date", "thesis", "memory", "graph",
                           "concern_evidence", "supplementary_evidence"})

    # --- 10. Mechanical single-ticker-scope guardrail -------------------------
    public_funcs = [f for name, f in inspect.getmembers(crd, inspect.isfunction)
                    if not name.startswith("_") and f.__module__ == crd.__name__]
    check("every public function DEFINED IN company_research_dossier.py "
          "accepts at most ONE 'ticker'-named parameter",
          all(len([p for p in inspect.signature(f).parameters if "ticker" in p.lower()]) <= 1
              for f in public_funcs))

    con.close()

    # --- database immutability + zero schema change --------------------------
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run "
          "(zero database writes)", table_diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
