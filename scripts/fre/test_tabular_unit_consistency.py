"""Adversarial tests for check_tabular_unit_consistency (2026-08-13, real
~1000x defect found live on ELLAHLAKES doc 11122 during the FRE scale-
validation program). Also regression-tests that the existing
check_numeric_consistency (prose scale-words) is unaffected.

  PYTHONPATH=src python scripts/fre/test_tabular_unit_consistency.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.documents.numeric_consistency import (  # noqa: E402
    check_numeric_consistency, check_tabular_unit_consistency)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


# --- 1. thousands: unscaled raw table figure -> flag ---
doc = "Statement of Comprehensive Income\n₦'000 ₦'000\nRevenue 146,658 130,000\n"
r = check_tabular_unit_consistency(146658.0, "146,658", doc)
check("thousands: unscaled raw figure flagged", r.status == "flag")

# --- 2. thousands: correctly scaled -> pass ---
r = check_tabular_unit_consistency(146658000.0, "146,658", doc)
check("thousands: correctly scaled value passes", r.status == "pass")

# --- 3. millions: unscaled -> flag ---
doc_m = "All figures in ₦ million unless stated otherwise.\nRevenue 408.0\n"
r = check_tabular_unit_consistency(408.0, "408.0", doc_m)
check("millions: unscaled raw figure flagged", r.status == "flag")

# --- 4. millions: correctly scaled -> pass ---
r = check_tabular_unit_consistency(408000000.0, "408.0", doc_m)
check("millions: correctly scaled value passes", r.status == "pass")

# --- 5. billions: unscaled -> flag (header declaration, not inline prose) ---
doc_b = "Figures below are stated in ₦ billion.\nTotal revenue 94.1\n"
r = check_tabular_unit_consistency(94.1, "94.1", doc_b)
check("billions: unscaled raw figure flagged", r.status == "flag")

# --- 6. billions: correctly scaled -> pass ---
r = check_tabular_unit_consistency(94100000000.0, "94.1", doc_b)
check("billions: correctly scaled value passes", r.status == "pass")

# --- 7. unscaled naira, no declared convention at all -> not_checked ---
doc_plain = "Revenue for the period was N5,000,000 as reported in the audited accounts.\n"
r = check_tabular_unit_consistency(5000000.0, "5,000,000", doc_plain)
check("no declared convention: not_checked, never assumed correct", r.status == "not_checked")

# --- 8. prose units (adjacent scale word, not a table header) -- the
# EXISTING check handles this; the tabular checker should stay silent
# (not double-flag, not conflict) since there is no standalone header
# declaration, only a number-adjacent scale word ---
doc_prose = "Profit after Tax improved 188% year-on-year to N94.1 billion in 2024.\n"
r_tab = check_tabular_unit_consistency(941000000000.0, "N94.1 billion", doc_prose)
check("prose-only scale word: tabular checker stays silent (not_checked), "
     "doesn't duplicate/conflict with check_numeric_consistency",
     r_tab.status == "not_checked")
r_old = check_numeric_consistency(941000000000.0, "N94.1 billion")
check("prose-only scale word: EXISTING check_numeric_consistency still "
     "catches the 10x error (regression check)", r_old.status == "flag")
r_old_correct = check_numeric_consistency(94100000000.0, "N94.1 billion")
check("prose-only scale word: EXISTING check_numeric_consistency still "
     "passes a correct value (regression check)", r_old_correct.status == "pass")

# --- 9. real table-header case (ELLAHLAKES's actual document text) ---
ellahlakes_text = (ROOT / "data" / "staging" / "document_text" / "11122.txt").read_text(encoding="utf-8")
r = check_tabular_unit_consistency(146658.0, "146,658", ellahlakes_text)
check("real ELLAHLAKES document: unscaled revenue flagged", r.status == "flag")
r = check_tabular_unit_consistency(146658000.0, "146,658", ellahlakes_text)
check("real ELLAHLAKES document: correctly-scaled revenue passes", r.status == "pass")
r = check_tabular_unit_consistency(-3839656000.0, "(3,839,656)", ellahlakes_text)
check("real ELLAHLAKES document: correctly-scaled NEGATIVE (loss) figure "
     "passes -- parenthesized negatives handled", r.status == "pass")

# --- 10. mixed-unit document: two different declared conventions -> ambiguous ---
doc_mixed = "Segment A (₦'000): Revenue 146,658\nSegment B (₦ million): Revenue 408.0\n"
r = check_tabular_unit_consistency(146658.0, "146,658", doc_mixed)
check("mixed-unit document: fails CLOSED as ambiguous, does not guess which "
     "convention applies", r.status == "ambiguous")

# --- 11. ambiguous: same as mixed, explicit second case (thousands + billions) ---
doc_mixed2 = "₦'000 figures below; see appendix for ₦ billion group summary.\nRevenue 146,658\n"
r = check_tabular_unit_consistency(146658.0, "146,658", doc_mixed2)
check("ambiguous (thousands + billions both declared): fails closed", r.status == "ambiguous")

# --- 12. missing units: no document text at all ---
r = check_tabular_unit_consistency(146658.0, "146,658", None)
check("missing document text: not_checked, never assumed correct", r.status == "not_checked")
r = check_tabular_unit_consistency(146658.0, "146,658", "")
check("empty document text: not_checked, never assumed correct", r.status == "not_checked")

# --- 13. null/zero numeric_value: not_checked, nothing to compare ---
r = check_tabular_unit_consistency(None, "146,658", doc)
check("null numeric_value: not_checked", r.status == "not_checked")
r = check_tabular_unit_consistency(0.0, "146,658", doc)
check("zero numeric_value: not_checked", r.status == "not_checked")

# --- 14. declared convention but no quote to check -> not_checked, not a guess ---
r = check_tabular_unit_consistency(146658000.0, None, doc)
check("declared convention, no quote: not_checked (can't verify, doesn't assume)",
     r.status == "not_checked")

# --- 15. declared convention, quote with multiple numbers -> not_checked ---
r = check_tabular_unit_consistency(146658000.0, "146,658 130,000", doc)
check("quote with multiple numbers: not_checked rather than guessing which one",
     r.status == "not_checked")

# --- 16. genuinely inconclusive: value matches neither raw nor scaled ---
r = check_tabular_unit_consistency(999999.0, "146,658", doc)
check("value matches neither raw nor scaled figure: not_checked, not "
     "force-flagged", r.status == "not_checked")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
