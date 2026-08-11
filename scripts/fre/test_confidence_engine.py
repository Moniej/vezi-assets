"""Decision Intelligence Phase 7: tests for confidence_engine.py.

  PYTHONPATH=src python scripts/fre/test_confidence_engine.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_state import build_company_state  # noqa: E402
from ngxrot.fre.company_thesis import build_company_thesis  # noqa: E402
from ngxrot.fre.confidence_engine import HIGH, LOW, MEDIUM, compute_confidence  # noqa: E402

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
    cache: dict = {}
    AS_OF = "2026-08-09"

    for t in ["CAP", "TOTAL", "GTCO", "AFRIPRUD"]:
        state = build_company_state(con, t, AS_OF, intelligence_cache=cache)
        thesis = build_company_thesis(con, t, AS_OF)
        dims = compute_confidence(state, thesis)
        for dim_name in ("data_confidence", "fundamental_confidence", "thesis_confidence",
                          "valuation_confidence", "catalyst_confidence", "risk_confidence", "overall"):
            val = getattr(dims, dim_name)
            check(f"{t}: {dim_name} is LOW/MEDIUM/HIGH", val in (LOW, MEDIUM, HIGH))
            reason = getattr(dims, f"{dim_name}_reason", None) if dim_name != "overall" else dims.overall_reasons
            check(f"{t}: {dim_name} has a non-empty explaining reason", bool(reason))

    # --- overall is the FLOOR (weakest dimension), never an average --------
    state_total = build_company_state(con, "TOTAL", AS_OF, intelligence_cache=cache)
    thesis_total = build_company_thesis(con, "TOTAL", AS_OF)
    dims_total = compute_confidence(state_total, thesis_total)
    all_dims = [dims_total.data_confidence, dims_total.fundamental_confidence, dims_total.thesis_confidence,
                dims_total.valuation_confidence, dims_total.catalyst_confidence, dims_total.risk_confidence]
    _ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2}
    check("TOTAL: overall == min(all 6 dimensions) exactly -- floor rule, never averaged",
          _ORDER[dims_total.overall] == min(_ORDER[d] for d in all_dims))

    # --- valuation_confidence dimension is a direct, disclosed passthrough
    # of value_company()'s own vocabulary -- never independently recomputed -
    from ngxrot.fre.valuation_engine import value_company  # noqa: E402
    for t in ["CAP", "TOTAL"]:
        state = build_company_state(con, t, AS_OF, intelligence_cache=cache)
        thesis = build_company_thesis(con, t, AS_OF)
        dims = compute_confidence(state, thesis)
        tv = value_company(con, t, AS_OF)
        _MAP = {"no_data": LOW, "single_method": LOW, "low": LOW, "medium": MEDIUM, "high": HIGH}
        check(f"{t}: confidence_engine.valuation_confidence matches the bucketed "
              f"value_company().valuation_confidence exactly",
              dims.valuation_confidence == _MAP.get(tv.valuation_confidence, LOW))

    # --- thesis=None handled honestly (no crash, no fabricated confidence) -
    state_fake = build_company_state(con, "NOTAREALTICKER", AS_OF, intelligence_cache=cache)
    dims_none = compute_confidence(state_fake, None)
    check("compute_confidence() with thesis=None: thesis_confidence is LOW, not a crash or a guess",
          dims_none.thesis_confidence == LOW)
    check("compute_confidence() with thesis=None: catalyst_confidence and risk_confidence are LOW",
          dims_none.catalyst_confidence == LOW and dims_none.risk_confidence == LOW)

    con.close()
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module is pure/read-only)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
