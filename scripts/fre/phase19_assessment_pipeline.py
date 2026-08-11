"""Phase 19: Real-World Investment Intelligence Assessment -- pipeline
runner. Diagnostic/audit script (same convention as fre7b_accounting_
depth_audit.py) -- no persisted output, no DB write, prints structured
results for the report to be written from directly-inspected real data.

## Ticker selection rule (PRE-DECLARED, frozen before any output was read)

Alphabetically-first ticker, per `economic_peer_taxonomy.level1` group,
among `genuine_fact_universe.list_genuine_financial_statement_tickers()`.
Deterministic, reproducible, not chosen because any result looked
interesting -- the rule was fixed before this script was ever run.

  PYTHONPATH=src python scripts/fre/phase19_assessment_pipeline.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_economic_profile import build_economic_profile  # noqa: E402
from ngxrot.fre.company_intelligence_bundle import build_intelligence_bundle, what_is_happening  # noqa: E402
from ngxrot.fre.company_research_report import build_full_report, render_full_report  # noqa: E402
from ngxrot.fre.continuous_intelligence import process_new_information  # noqa: E402
from ngxrot.fre.economic_peer_taxonomy import classify_ticker  # noqa: E402
from ngxrot.fre.genuine_fact_universe import list_genuine_financial_statement_tickers  # noqa: E402
from ngxrot.fre.research_questions import answer_all  # noqa: E402

AS_OF = "2026-08-09"
PRIOR = "2024-01-01"


def select_tickers(con) -> dict[str, str]:
    tickers = list_genuine_financial_statement_tickers(con)
    by_l1: dict[str, list[str]] = {}
    for t in tickers:
        c = classify_ticker(con, t, AS_OF)
        l1 = c.level1 if c.classified else "UNCLASSIFIED"
        by_l1.setdefault(l1, []).append(t)
    return {l1: sorted(members)[0] for l1, members in sorted(by_l1.items())}


def main() -> int:
    con = db.init_db(db.DEFAULT_DB) if False else __import__("sqlite3").connect(
        f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    doc_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    selection = select_tickers(con)
    print("=" * 100)
    print("SELECTED TICKERS (deterministic, alphabetically-first per economic_peer_taxonomy "
          "level1 group)")
    print("=" * 100)
    for l1, t in selection.items():
        print(f"  {l1}: {t}")
    print()

    cache: dict = {}
    for l1, ticker in selection.items():
        print("=" * 100)
        print(f"{ticker} ({l1})")
        print("=" * 100)
        t0 = time.time()

        profile = build_economic_profile(con, ticker, AS_OF, intelligence_cache=cache)
        bundle = build_intelligence_bundle(con, ticker, AS_OF, PRIOR, intelligence_cache=cache,
                                            include_portfolio_note=False)
        answers = answer_all(bundle)
        report = build_full_report(con, ticker, AS_OF, PRIOR, intelligence_cache=cache,
                                    include_portfolio_note=False)
        rendered = render_full_report(report)
        continuous = process_new_information(con, ticker, AS_OF, PRIOR, intelligence_cache=cache)

        print(f"[timing: {time.time() - t0:.1f}s]")
        print(f"economic_profile.coverage: {profile.coverage:.0%}")
        print(f"company_state.data_completeness: {bundle.state.data_completeness:.0%}")
        print(f"overall confidence: {bundle.confidence.overall}")
        print(f"ranked_changes: {len(bundle.ranked_changes)} "
              f"({[a.level for a in bundle.ranked_changes]})")
        print(f"max_materiality: {continuous.max_materiality}  alert: {continuous.alert_entry is not None}")
        print()
        print("--- what_is_happening() ---")
        print(what_is_happening(bundle))
        print()
        print("--- research_questions answers ---")
        for a in answers:
            print(f"Q: {a.question}")
            print(f"A: {a.answer}")
            print(f"   evidence={a.evidence}  is_inference={a.is_inference}")
        print()
        print(f"--- rendered report length: {len(rendered)} chars ---")
        print(rendered[:400])
        print("...")
        print()

    con.close()
    con2 = __import__("sqlite3").connect(db.DEFAULT_DB)
    doc_after = con2.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert doc_after == doc_before, "production database was written to -- must never happen"
    con2.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
