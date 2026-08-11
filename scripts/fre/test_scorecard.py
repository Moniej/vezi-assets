"""Decision Intelligence Phase 9: tests for scorecard.py.

  PYTHONPATH=src python scripts/fre/test_scorecard.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.scorecard import UNKNOWN_SIGNAL, build_scorecard  # noqa: E402

REAL_DB = db.DEFAULT_DB
passed = 0
failed = 0
_ALLOWED_FIELDS = {
    "ticker", "as_of_date", "fundamental_signal", "fundamental_confidence",
    "corporate_action_signal", "regulatory_signal", "insider_signal", "market_signal",
    "valuation_signal", "confidence", "data_completeness", "primary_thesis", "counter_thesis",
    "base_case", "key_risks", "catalysts", "contradiction_note", "missing_evidence",
    "material_changes", "evidence_ids",
}


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
    cache: dict = {}
    AS_OF, PRIOR = "2026-08-09", "2024-01-01"

    # --- GOVERNANCE: no recommendation/conviction/composite-score field
    # exists anywhere on the Scorecard dataclass -- the owner-mandated
    # scope restriction (skip Phase 8/10) is enforced structurally, not
    # just by convention. -----------------------------------------------------
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(build_scorecard.__globals__["Scorecard"])}
    check("Scorecard has NO 'recommendation' field", "recommendation" not in field_names)
    check("Scorecard has NO 'conviction' field", "conviction" not in field_names)
    check("Scorecard has NO 'catalyst_score'/'risk_score' composite-score field",
          "catalyst_score" not in field_names and "risk_score" not in field_names)
    check("Scorecard's real fields are exactly the disclosed, documented set (no undisclosed additions)",
          field_names == _ALLOWED_FIELDS)

    for t in ["CAP", "TOTAL", "AFRIPRUD"]:
        sc = build_scorecard(con, t, AS_OF, PRIOR, intelligence_cache=cache)
        check(f"{t}: ticker/as_of_date echo the request", sc.ticker == t and sc.as_of_date == AS_OF)
        for sig_field in ("fundamental_signal", "corporate_action_signal", "regulatory_signal",
                          "insider_signal", "market_signal", "valuation_signal"):
            val = getattr(sc, sig_field)
            check(f"{t}: {sig_field} is a real, non-empty categorical label", isinstance(val, str) and val)
        check(f"{t}: data_completeness matches company_state's own fraction (no recomputation)",
              0.0 <= sc.data_completeness <= 1.0)
        check(f"{t}: every material_change entry has category/field/level/description",
              all({"category", "field", "level", "description"} <= set(e.keys()) for e in sc.material_changes))
        check(f"{t}: material_changes is sorted CRITICAL/HIGH-first",
              [e["level"] for e in sc.material_changes] ==
              sorted([e["level"] for e in sc.material_changes],
                     key=lambda l: -{"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}[l]))

    # --- TOTAL (no FSI coverage): valuation_signal must be UNKNOWN, never
    # a fabricated UNDERVALUED/OVERVALUED call -------------------------------
    sc_total = build_scorecard(con, "TOTAL", AS_OF, PRIOR, intelligence_cache=cache)
    check("TOTAL: valuation_signal is UNKNOWN (no intrinsic_value_range available) -- "
          "never guessed", sc_total.valuation_signal == UNKNOWN_SIGNAL)

    # --- evidence_ids/primary_thesis/counter_thesis are verbatim passthroughs
    # of company_thesis.py's own real fields, never re-synthesized ----------
    from ngxrot.fre.company_thesis import build_company_thesis  # noqa: E402
    for t in ["CAP", "AFRIPRUD"]:
        sc = build_scorecard(con, t, AS_OF, PRIOR, intelligence_cache=cache)
        thesis = build_company_thesis(con, t, AS_OF)
        check(f"{t}: primary_thesis exactly matches company_thesis.bull_case verbatim",
              sc.primary_thesis == thesis.bull_case)
        check(f"{t}: counter_thesis exactly matches company_thesis.bear_case verbatim",
              sc.counter_thesis == thesis.bear_case)
        check(f"{t}: evidence_ids exactly matches company_thesis.source_implication_ids verbatim",
              sc.evidence_ids == (thesis.source_implication_ids or []))

    con.close()
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
