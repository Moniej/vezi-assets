"""Standalone assertion-script tests for terminology_mapping.py, using the
real AFRIPRUD anchor (docs/fre_runs/fsi_phase2_execution_plan.md section 5).

  PYTHONPATH=src python scripts/fre/test_terminology_mapping.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.fre.terminology_mapping import map_label_to_concept  # noqa: E402

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
    # --- the AFRIPRUD anchor: two real, differently-labeled synonyms for
    # the SAME concept, observed in two different real AFRIPRUD filings ----
    check("AFRIPRUD doc 4245's real label 'Gross earnings' maps to 'revenue'",
          map_label_to_concept("Gross earnings") == "revenue")
    check("AFRIPRUD doc 6349's real label 'Gross Revenue' ALSO maps to "
          "'revenue' -- the same underlying concept, a different literal "
          "label from the same company's own later filing",
          map_label_to_concept("Gross Revenue") == "revenue")
    check("case-insensitive: 'GROSS EARNINGS' also maps to 'revenue'",
          map_label_to_concept("GROSS EARNINGS") == "revenue")

    # --- the real 'TOTAL ASSESTS' typo, kept literal in the config ---------
    check("the real (typo'd) label 'TOTAL ASSESTS' maps to 'assets'",
          map_label_to_concept("TOTAL ASSESTS") == "assets")

    # --- net_profit synonyms confirmed across Phase 1's real filings -------
    check("'Profit for the year' maps to 'net_profit'",
          map_label_to_concept("Profit for the year") == "net_profit")
    check("'PROFIT FOR THE PERIOD' maps to 'net_profit'",
          map_label_to_concept("PROFIT FOR THE PERIOD") == "net_profit")

    # --- EBIT's disclosed-risk synonym ---------------------------------
    check("'Operating Profit' maps to 'ebit' (the disclosed-caveat synonym)",
          map_label_to_concept("Operating Profit") == "ebit")

    # --- an unmatched label returns None, never a guess --------------------
    check("an unrecognized label returns None, never a fabricated guess",
          map_label_to_concept("Some Made Up Line Item") is None)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
