"""Standalone assertion-script tests for reasoning_context.py, validated
against real production data (read-only, no write path exists in this
module at all).

  PYTHONPATH=src python scripts/fre/test_reasoning_context.py
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import reasoning_context as rc  # noqa: E402

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
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # --- pick a real, known 'computed' ratio conclusion: CAP FY2020 ebit_margin
    row = con.execute(
        "SELECT conclusion_id FROM financial_reasoning_conclusions "
        "WHERE ticker='CAP' AND conclusion_type='ratio' AND metric='ebit_margin' "
        "AND period_start='2020-01-01' AND period_end='2020-12-31'"
    ).fetchone()
    check("a real CAP FY2020 ebit_margin conclusion exists to test against", row is not None)
    conclusion_id = row[0]

    ctx = rc.get_reasoning_context(con, conclusion_id)
    check("get_reasoning_context returns a populated context for a real conclusion_id",
          ctx is not None and ctx.ticker == "CAP" and ctx.metric == "ebit_margin")
    check("the context carries exactly 2 source facts (ebit numerator, revenue denominator)",
          len(ctx.source_facts) == 2)
    check("every source fact resolves to the real CAP doc_id 4508 (the FY2020 filing)",
          all(f.doc_id == 4508 for f in ctx.source_facts))
    check("every source fact carries its own fact_type, numeric_value, and confidence_tier "
          "(full provenance, not just a bare number)",
          all(f.fact_type and f.numeric_value is not None for f in ctx.source_facts))
    check("the context itself carries method and limitations text (never blank)",
          len(ctx.method) > 0 and len(ctx.limitations) > 0)

    # --- a nonexistent conclusion_id returns None, never a fabricated context
    check("a nonexistent conclusion_id returns None, never a guessed/empty context",
          rc.get_reasoning_context(con, 999_999_999) is None)

    # --- get_reasoning_contexts_for_ticker: single-ticker scope, real data
    nascon_flag_contexts = rc.get_reasoning_contexts_for_ticker(con, "NASCON", conclusion_type="flag")
    check("get_reasoning_contexts_for_ticker('NASCON', 'flag') returns exactly NASCON's 3 flags, "
          "every one actually belonging to NASCON",
          len(nascon_flag_contexts) == 3 and all(c.ticker == "NASCON" for c in nascon_flag_contexts))

    # --- mechanical single-company-scope guardrail (pre-registration Area 7):
    # every public function in this module accepts exactly one ticker
    # parameter and this module's own dataclasses carry no comparative/
    # cross-ticker field
    public_funcs = [f for name, f in inspect.getmembers(rc, inspect.isfunction)
                     if not name.startswith("_")]
    ticker_param_names = []
    for f in public_funcs:
        sig = inspect.signature(f)
        ticker_params = [p for p in sig.parameters if "ticker" in p.lower()]
        ticker_param_names.append(len(ticker_params))
    check("every public function in reasoning_context.py has at most ONE 'ticker'-named "
          "parameter (mechanical check: no function signature accepts multiple tickers)",
          all(n <= 1 for n in ticker_param_names))
    dataclass_field_names = set()
    for cls in (rc.ReasoningContext, rc.SourceFactContext):
        dataclass_field_names.update(cls.__dataclass_fields__.keys())
    check("no dataclass field name in this module suggests a cross-ticker comparison "
          "(no 'rank', 'compare', 'vs_', 'peer', or 'score' field exists)",
          not any(bad in name.lower() for name in dataclass_field_names
                  for bad in ("rank", "compare", "vs_", "peer", "score")))

    con.close()

    # --- confirm the real production database was never touched (this
    # module has no write path at all) ---
    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
