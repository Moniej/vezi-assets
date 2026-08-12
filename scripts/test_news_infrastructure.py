"""Regression test for secondary-source (news) infrastructure
(2026-08-11, HANDOFF.md, Priority 4: OS infrastructure only).

Read-only against the real production database, plus one unit-level check
of evidence_ranking.py's news_outlets-aware tier assignment.

  PYTHONPATH=src python scripts/test_news_infrastructure.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.documents.evidence_ranking import assign_trust_tier  # noqa: E402

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

    outlets = con.execute("SELECT outlet_name, reliability_tier, base_confidence, source_id "
                          "FROM news_outlets ORDER BY outlet_name").fetchall()
    check("news_outlets holds both real outlets", {o[0] for o in outlets} ==
         {"Nairametrics", "MarketForces Africa"})
    check("every news_outlets row links to a real sources row",
         all(o[3] is not None for o in outlets))
    for name, tier, conf, _ in outlets:
        check(f"{name}: reliability_tier is a valid tier value (1-4)", tier in (1, 2, 3, 4))
        check(f"{name}: base_confidence is in [0,1]", 0.0 <= conf <= 1.0)

    n_news_docs = con.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'news'").fetchone()[0]
    check("real news documents registered (27)", n_news_docs == 27)

    n_no_ticker = con.execute(
        "SELECT COUNT(*) FROM documents WHERE doc_type = 'news' AND ticker IS NULL").fetchone()[0]
    check("every news document resolved to a real ticker (none left NULL/guessed)", n_no_ticker == 0)

    n_bad_ticker = con.execute(
        "SELECT COUNT(*) FROM documents d WHERE d.doc_type = 'news' AND NOT EXISTS "
        "(SELECT 1 FROM securities s WHERE s.ticker = d.ticker)").fetchone()[0]
    check("every news document's ticker exists in securities (no fabricated ticker)",
         n_bad_ticker == 0)

    n_no_source = con.execute(
        "SELECT COUNT(*) FROM documents d WHERE d.doc_type = 'news' AND NOT EXISTS "
        "(SELECT 1 FROM news_outlets no WHERE no.source_id = d.source_id)").fetchone()[0]
    check("every news document's source_id resolves to a registered news_outlets row",
         n_no_source == 0)

    n_extracted = con.execute(
        "SELECT COUNT(*) FROM documents WHERE doc_type = 'news' AND text_path IS NOT NULL "
        "AND doc_id IN (SELECT doc_id FROM extracted_facts)").fetchone()[0]
    check("no extraction has been run on these documents yet (no GEMINI_API_KEY this pass -- "
         "disclosed, not silently skipped)", n_extracted == 0)

    tickers = {r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM documents WHERE doc_type = 'news'").fetchall()}
    check("news coverage spans multiple real, distinct tickers", len(tickers) >= 15)

    con.close()

    # --- evidence_ranking.py: real per-outlet tier, not the provisional fallback ---
    a_registered = assign_trust_tier(source_type="news", grounding_check="passed",
                                     is_propagated=False, news_outlet_tier=3,
                                     news_outlet_name="Nairametrics")
    check("assign_trust_tier: a registered outlet gets its real tier, cites the outlet by name",
         a_registered.tier == 3 and "Nairametrics" in a_registered.rationale)

    a_unregistered = assign_trust_tier(source_type="news", grounding_check="passed",
                                       is_propagated=False, news_outlet_tier=None)
    check("assign_trust_tier: an unregistered news outlet still falls back to the provisional "
         "tier 3 (never silently promoted, never silently rejected)",
         a_unregistered.tier == 3 and "no matching news_outlets" in a_unregistered.rationale)

    a_filing = assign_trust_tier(source_type="filing", grounding_check="passed",
                                 is_propagated=False, news_outlet_tier=3)
    check("assign_trust_tier: news_outlet_tier is ignored for a non-news source_type "
         "(a filing stays tier 1 even if a stray tier value were passed)",
         a_filing.tier == 1)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
