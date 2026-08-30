"""Standalone assertion-script tests for numeric_consistency.py (Financial
Extraction Quality Fix, 2026-08-12, Fix 2). Includes the exact real-world
case that motivated this fix (TRANSCORP net_profit, 2026-08-12 extraction
pilot: quote correctly said "N94.1 billion", numeric_value stored
941,000,000,000 -- a confirmed 10x structured-value error the grounding
check alone could not catch).

  PYTHONPATH=src python scripts/fre/test_numeric_consistency.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.documents.numeric_consistency import check_numeric_consistency  # noqa: E402

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


# --- the real case that motivated this fix -------------------------------
r = check_numeric_consistency(
    941_000_000_000.0,
    "Profit after Tax improved 188% year-on-year to N94.1 billion in 2024, "
    "from N32.6 billion in the same period last year.")
check("TRANSCORP real case: 941bn stored vs 94.1bn quoted -- FLAGGED",
      r.status == "flag")
check("TRANSCORP real case: reason names the actual quoted magnitude",
      "94,100,000,000" in r.reason or "94100000000" in r.reason)

# --- the task's own three example magnitudes ------------------------------
check("94.1bn vs 941bn: flagged (exact 10x)",
      check_numeric_consistency(941_000_000_000.0, "reported N94.1 billion in profit").status == "flag")
check("1.25bn vs 12.5bn: flagged (exact 10x)",
      check_numeric_consistency(12_500_000_000.0, "raised N1.25bn in the placement").status == "flag")
check("940m vs 940bn: flagged (exact 1000x, million/billion scale-word confusion)",
      check_numeric_consistency(940_000_000_000.0, "revenue of N940 million for the quarter").status == "flag")

# --- genuinely consistent values: must PASS, never be flagged ------------
check("a value that matches its quote within tolerance: PASS",
      check_numeric_consistency(94_100_000_000.0, "N94.1 billion in profit after tax").status == "pass")
check("a value matching a per-share/aggregate figure stated plainly: PASS",
      check_numeric_consistency(10_100_000_000.0,
          "declared a full-year dividend of N10.1 billion, representing N1.00 per share").status == "pass")

# --- no false positive on a quote with multiple, genuinely different figures ---
r = check_numeric_consistency(
    408_000_000_000.0,
    "FY 2024 Revenue increased by 107%, rising to N408 billion from N197 billion of 2023.")
check("multi-figure quote (this year + prior year, no round-factor relationship "
     "between them and the stored value): not flagged as a false positive",
      r.status == "pass")

# --- nothing to compare against: not_checked, never a false pass or flag ---
check("null numeric_value: not_checked, not a false pass",
      check_numeric_consistency(None, "N94.1 billion in profit").status == "not_checked")
check("qualitative quote with no number+scale-word: not_checked",
      check_numeric_consistency(500.0, "the company remains well capitalized and liquid").status == "not_checked")
check("a bare number with no scale word (e.g. a per-share kobo figure) doesn't "
     "false-positive against a large aggregate value",
      check_numeric_consistency(0.1, "declared an interim dividend of 10 kobo per share").status == "not_checked")

# --- never auto-corrects: the function's return type carries no "corrected" field ---
r = check_numeric_consistency(941_000_000_000.0, "N94.1 billion in profit after tax")
check("flagged result exposes the ORIGINAL numeric_value's magnitude, "
     "never substitutes/rewrites it (caller decides what to do, this only detects)",
      not hasattr(r, "corrected_value") and not hasattr(r, "suggested_value"))

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
