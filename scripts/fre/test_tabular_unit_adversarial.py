"""Gate 2, P4: adversarial cases specifically designed to break
check_tabular_unit_consistency / _declared_scales -- distinguishing a real
unit DECLARATION from numeric content that merely contains the digits
'000', and confirming the checker degrades safely (never guesses) under
deliberately hostile document shapes.

  PYTHONPATH=src python scripts/fre/test_tabular_unit_adversarial.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.documents.numeric_consistency import (  # noqa: E402
    _declared_scales, check_tabular_unit_consistency)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


# --- 1. "000" as part of a number/ID, NOT a scale declaration ---
for label, text in [
    ("account number", "Account No. N000123456, Registration"),
    ("phone number", "Tel: 0700-000-0000"),
    ("RC number", "RC: 000123"),
    ("real currency amount ending in zeros", "The company reported N100,000,000 in revenue this year."),
    ("real currency amount, another shape", "Total assets stood at N2,000,000,000 as at year end."),
]:
    scales = _declared_scales(text)
    check(f"'000-as-part-of-a-number' NOT misread as a scale declaration: {label}", scales == [])

# --- 2. unit declaration separated from the table (footnote, far away) ---
doc_footnote = (
    "STATEMENT OF COMPREHENSIVE INCOME\nRevenue 146,658\nProfit 12,000\n"
    + ("filler line\n" * 20) +
    "Note 14: All figures in this report are presented in thousands of Naira.")
r = check_tabular_unit_consistency(146658.0, "146,658", doc_footnote)
check("unit declaration in a distant footnote is still found and applied", r.status == "flag")

# --- 3. repeated headers (same convention many times) -- must NOT be
# treated as multiple conflicting conventions ---
doc_repeat = (
    "RC: 000123\n₦'000 ₦'000\nRevenue 100,000 90,000\n"
    "₦'000 ₦'000\nAssets 500,000 480,000\nNotes: figures in ₦'000 throughout.")
scales = _declared_scales(doc_repeat)
check("repeated identical headers dedup to ONE declared convention, not flagged ambiguous",
     len(scales) == 1 and scales[0][0] == "thousands")
r = check_tabular_unit_consistency(100000.0, "100,000", doc_repeat)
check("repeated-header document: unscaled figure still correctly flagged (not ambiguous)",
     r.status == "flag")

# --- 4. parentheses / negative values (already covered in the core suite,
# reconfirmed here as part of the formal adversarial set) ---
doc_neg = "₦'000\nLoss for the year (3,839,656)\n"
r = check_tabular_unit_consistency(-3839656000.0, "(3,839,656)", doc_neg)
check("parenthesized negative, correctly scaled: passes", r.status == "pass")
r = check_tabular_unit_consistency(-3839656.0, "(3,839,656)", doc_neg)
check("parenthesized negative, unscaled: flagged", r.status == "flag")

# --- 5. decimal values ---
doc_dec = "₦'000\nRevenue 146,658.50\n"
r = check_tabular_unit_consistency(146658.50, "146,658.50", doc_dec)
check("decimal raw figure, unscaled: flagged", r.status == "flag")
r = check_tabular_unit_consistency(146658500.0, "146,658.50", doc_dec)
check("decimal raw figure, correctly scaled: passes", r.status == "pass")

# --- 6. currency symbol separated from scale word (wordy declaration) ---
doc_wordy = ("Amounts in this statement, unless otherwise stated, are expressed "
            "in thousands of Naira (N).\nRevenue 146,658\n")
r = check_tabular_unit_consistency(146658.0, "146,658", doc_wordy)
check("wordy declaration with symbol separated from scale word: still detected and applied",
     r.status == "flag")

# --- 7. spacing/formatting variations of the same declaration ---
for variant in ["N '000", "N'000", "₦ '000", "₦'000", "N 000", "N'000s"]:
    scales = _declared_scales(f"Statement in {variant}: Revenue 100")
    check(f"declaration variant {variant!r} recognized", len(scales) == 1 and scales[0][1] == 1e3)

# --- 8. conflicting header AND prose units in the same document -> ambiguous ---
doc_conflict = ("Table 1 (₦'000): Revenue 146,658\n"
               "As discussed elsewhere, all figures are stated in ₦ million.")
r = check_tabular_unit_consistency(146658.0, "146,658", doc_conflict)
check("conflicting header vs prose declarations (thousands AND millions both present): "
     "fails CLOSED as ambiguous", r.status == "ambiguous")

# --- 9. no unit declaration anywhere -> not_checked, never guessed ---
doc_none = "Revenue for the year was N5,000,000 as reported in the audited accounts.\n"
r = check_tabular_unit_consistency(5000000.0, "5,000,000", doc_none)
check("no declaration anywhere: not_checked, never assumed correct or incorrect",
     r.status == "not_checked")

# --- 10. multiple SEPARATE tables, each with the SAME single convention
# (not actually conflicting) -- must NOT be flagged ambiguous merely for
# having more than one table ---
doc_multi_same = (
    "Segment A\n₦'000\nRevenue 50,000\n\n"
    "Segment B\n₦'000\nRevenue 96,658\n\n"
    "Group Total\n₦'000\nRevenue 146,658\n")
r = check_tabular_unit_consistency(146658000.0, "146,658", doc_multi_same)
check("multiple tables, all declaring the SAME convention: correctly scaled figure passes "
     "(not falsely flagged ambiguous just for having multiple tables)", r.status == "pass")

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
