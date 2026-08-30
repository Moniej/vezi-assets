"""Tests for research_memory.py against the frozen registry fixture (read-only).

  PYTHONPATH=src python scripts/test_research_memory.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.research_memory import (  # noqa: E402
    check_prior_art, classify_families, find_similar_formal_hypotheses)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


FROZEN_REGISTRY = ROOT / "fixtures" / "stage1" / "frozen" / "registry_regression.sqlite"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-db", type=Path, default=FROZEN_REGISTRY)
    args = parser.parse_args(argv)
    if not args.fixture_db.is_file():
        raise RuntimeError(f"frozen registry fixture is required: {args.fixture_db}")
    con = sqlite3.connect(f"file:{args.fixture_db.as_posix()}?mode=ro", uri=True)

# --- family classification, real hypothesis text ---
    fams = classify_families("Cross-sectional 3-6M price momentum across NGX sector indices")
    check("fixture H-001 text classifies as 'momentum'", "momentum" in fams)

    fams2 = classify_families("Size: long smallest-cap quintile within IRU vs EW-IRU, quarterly")
    check("fixture H-011 text classifies as 'size'", "size" in fams2)

    fams3 = classify_families("Liquidity: does a whole-universe cross-sectional sort on trailing "
                          "60-day ADTV capture a return premium")
    check("fixture H-016 text classifies as 'liquidity'", "liquidity" in fams3)

# --- a genuinely NEW momentum-style candidate should surface H-001/H-007/H-009/H-010 ---
    matches = find_similar_formal_hypotheses(con, "Cross-sectional price momentum on NGX equities, "
                                         "6-month lookback, quarterly rebalance")
    match_ids = {m.hypothesis_id for m in matches}
    check("a new momentum candidate surfaces at least one fixture momentum hypothesis",
     len({"H-001", "H-007", "H-009", "H-010"} & match_ids) > 0)
    check("every surfaced match reports a valid status",
     all(m.status in ("rejected", "confirmed", "untested", "testing") for m in matches))
    check("matches are ranked with the strongest family overlap first",
     matches == sorted(matches, key=lambda m: (len(m.shared_families), m.overlap_score), reverse=True))

# --- a size-family candidate should surface H-011 (confirmed) with its real conclusion ---
    size_matches = find_similar_formal_hypotheses(con, "Small-cap size premium within the investable "
                                              "universe, long smallest-cap quintile")
    h011 = next((m for m in size_matches if m.hypothesis_id == "H-011"), None)
    check("size candidate surfaces H-011 specifically", h011 is not None)
    check("H-011 match reports status='confirmed' (the frozen registry state)",
     h011 is not None and h011.status == "confirmed")
    check("H-011 match includes a non-empty conclusion summary",
     h011 is not None and h011.conclusion_summary)

# --- a totally unrelated candidate (no real overlap) should surface little/nothing ---
    unrelated = find_similar_formal_hypotheses(con, "Astrological alignment forecasting")
    check("a genuinely unrelated candidate produces zero or near-zero matches "
     "(no forced/fabricated 'similar' result)", len(unrelated) <= 1)

# --- reproducibility: identical inputs against an unchanged DB -> identical output ---
    run1 = check_prior_art(con, "Size: long smallest-cap quintile within IRU")
    run2 = check_prior_art(con, "Size: long smallest-cap quintile within IRU")
    check("check_prior_art is deterministic/reproducible on identical inputs",
     [m.hypothesis_id for m in run1.formal_matches] == [m.hypothesis_id for m in run2.formal_matches])

# --- full report structure, summary lines are real and readable ---
    report = check_prior_art(con, "Dividend payer status and forward returns", "")
    check("full prior-art report finds the frozen H-017 dividend-payer-status hypothesis",
     any(m.hypothesis_id == "H-017" for m in report.formal_matches))
    lines = report.summary_lines()
    check("summary_lines() produces non-empty text", len(lines) > 0 and all(lines))

# --- read-only: never touches registry.sqlite ---
    check("registry fixture connection is still valid after all queries (read-only, no corruption)",
     con.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0] > 0)

    con.close()
    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
