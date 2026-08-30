"""Standalone assertion-script tests for extract.py's validate_period()
(Financial Extraction Quality Fix, 2026-08-12, Fix 1). Tests the
deterministic validation/enforcement layer directly -- no LLM call needed,
since validate_period() is what stands between whatever the model returns
and what actually reaches the database, and it is the thing this fix
actually changed.

  PYTHONPATH=src python scripts/fre/test_period_extraction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.documents.extract import validate_period  # noqa: E402
from ngxrot.documents.prompts import POINT_IN_TIME_FACT_TYPES  # noqa: E402

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


# --- annual statement -> correct start/end -----------------------------
w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-01-01", "period_end": "2024-12-31", "period_type": "FY"},
    "revenue", "2025-02-27", w)
check("annual statement: period_start/period_end/period_type pass through unchanged",
      ps == "2024-01-01" and pe == "2024-12-31" and pt == "FY")
check("annual statement: no warnings on a clean, valid input", w == [])

# --- quarterly statement -> correct start/end ---------------------------
w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-01-01", "period_end": "2024-03-31", "period_type": "Q1"},
    "net_profit", "2024-04-25", w)
check("quarterly statement: period fields pass through unchanged",
      ps == "2024-01-01" and pe == "2024-03-31" and pt == "Q1")
check("quarterly statement: no warnings on a clean, valid input", w == [])

# --- balance-sheet fact -> correct point-in-time semantics --------------
w = []
ps, pe, pt = validate_period(
    {"period_start": None, "period_end": "2024-12-31", "period_type": "FY"},
    "assets", "2025-02-27", w)
check("balance-sheet fact: point-in-time (period_start stays null, period_end kept)",
      ps is None and pe == "2024-12-31" and pt == "FY")

w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-01-01", "period_end": "2024-12-31", "period_type": "FY"},
    "equity", "2025-02-27", w)
check("balance-sheet fact: a MODEL-PROVIDED period_start is nulled, not trusted "
     "(a snapshot has no real 'start' even if the model invents one)",
      ps is None and pe == "2024-12-31")
check("balance-sheet fact: nulling a point-in-time period_start is warned, not silent",
      any("point-in-time" in msg for msg in w))
check("every declared point-in-time fact type is actually assets/liabilities/equity "
     "(the classification this test exercises matches the real one)",
      POINT_IN_TIME_FACT_TYPES == frozenset({"assets", "liabilities", "equity"}))

# --- YTD / irregular period -> correct period semantics -----------------
# A genuine 17-month transition-period disclosure (real case found in the
# 2026-08-12 pilot, ELLAH LAKES PLC): real dates ARE known and should be
# kept, but period_type must NOT be force-fit into a standard bucket.
w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-08-01", "period_end": "2025-12-31", "period_type": "17M"},
    "revenue", "2026-04-02", w)
check("irregular 17-month period: real dates are kept (not discarded just "
     "because the span is non-standard)",
      ps == "2024-08-01" and pe == "2025-12-31")
check("irregular 17-month period: period_type is nulled, never force-mapped "
     "to a standard bucket (17M is not a real enum value)",
      pt is None)
check("irregular period: nulling an invalid period_type is warned, not silent",
      any("period_type" in msg and "17M" in msg for msg in w))

# A standard 9-month YTD disclosure DOES fit the existing enum -- must not
# be incorrectly rejected just because "YTD" appears in casual description.
w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-01-01", "period_end": "2024-09-30", "period_type": "9M"},
    "net_profit", "2024-10-29", w)
check("standard 9-month YTD: 9M is a real enum value, passes through unchanged",
      ps == "2024-01-01" and pe == "2024-09-30" and pt == "9M" and w == [])

# --- ambiguous period -> no fabricated dates -----------------------------
w = []
ps, pe, pt = validate_period({"period_start": None, "period_end": None, "period_type": None},
                             "revenue", "2024-07-24", w)
check("no period stated at all: everything stays null, nothing invented",
      ps is None and pe is None and pt is None)

w = []
ps, pe, pt = validate_period({"period_start": "not-a-date", "period_end": "2024-12-31"},
                             "revenue", "2025-01-01", w)
check("malformed period_start ('not-a-date'): nulled, not silently coerced or dropped-quietly",
      ps is None and pe == "2024-12-31")
check("malformed date is warned, not silent", any("not-a-date" in msg for msg in w))

# The specific bug this fix exists to prevent: period_end silently equal to
# the document's own filing_date (the exact failure mode the brief named
# explicitly -- "must remain missing rather than being inferred from the
# document retrieval date").
w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-01-01", "period_end": "2025-02-27", "period_type": "FY"},
    "revenue", "2025-02-27", w)
check("period_end == filing_date: treated as suspicious and nulled, not trusted "
     "(a real reporting period essentially never ends on its own filing date)",
      ps is None and pe is None)
check("period_end==filing_date rejection is warned, not silent",
      any("filing_date" in msg for msg in w))

# period_start after period_end (internally inconsistent): reject both,
# don't guess which one is right.
w = []
ps, pe, pt = validate_period(
    {"period_start": "2024-12-31", "period_end": "2024-01-01", "period_type": "FY"},
    "revenue", "2025-03-01", w)
check("period_start after period_end: both nulled rather than guessing which is wrong",
      ps is None and pe is None)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
