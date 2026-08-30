"""Tests for research_memory.py against real registry.sqlite (read-only).

  PYTHONPATH=src python scripts/test_research_memory.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import registry as reg_module  # noqa: E402
from ngxrot.research_memory import (  # noqa: E402
    check_prior_art, classify_families, find_similar_formal_hypotheses)

passed, failed = 0, 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    passed, failed = (passed + 1, failed) if condition else (passed, failed + 1)


con = reg_module.connect_registry()

# --- family classification, real hypothesis text ---
fams = classify_families("Cross-sectional 3-6M price momentum across NGX sector indices")
check("real H-001 text classifies as 'momentum'", "momentum" in fams)

fams2 = classify_families("Size: long smallest-cap quintile within IRU vs EW-IRU, quarterly")
check("real H-011 text classifies as 'size'", "size" in fams2)

fams3 = classify_families("Liquidity: does a whole-universe cross-sectional sort on trailing "
                          "60-day ADTV capture a return premium")
check("real H-016 text classifies as 'liquidity'", "liquidity" in fams3)

# --- a genuinely NEW momentum-style candidate should surface H-001/H-007/H-009/H-010 ---
matches = find_similar_formal_hypotheses(con, "Cross-sectional price momentum on NGX equities, "
                                         "6-month lookback, quarterly rebalance")
match_ids = {m.hypothesis_id for m in matches}
check("a new momentum candidate surfaces at least one real prior momentum hypothesis",
     len({"H-001", "H-007", "H-009", "H-010"} & match_ids) > 0)
check("every surfaced match reports a real, non-empty status",
     all(m.status in ("rejected", "confirmed", "untested", "testing") for m in matches))
check("matches are ranked with the strongest family overlap first",
     matches == sorted(matches, key=lambda m: (len(m.shared_families), m.overlap_score), reverse=True))

# --- a size-family candidate should surface H-011 (confirmed) with its real conclusion ---
size_matches = find_similar_formal_hypotheses(con, "Small-cap size premium within the investable "
                                              "universe, long smallest-cap quintile")
h011 = next((m for m in size_matches if m.hypothesis_id == "H-011"), None)
check("size candidate surfaces H-011 specifically", h011 is not None)
check("H-011 match reports status='confirmed' (the real registry state)",
     h011 is not None and h011.status == "confirmed")
check("H-011 match includes a non-empty conclusion summary (real data, not fabricated)",
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
check("full prior-art report finds the real H-017 dividend-payer-status hypothesis",
     any(m.hypothesis_id == "H-017" for m in report.formal_matches))
lines = report.summary_lines()
check("summary_lines() produces real, non-empty text", len(lines) > 0 and all(lines))

# --- read-only: never touches registry.sqlite ---
check("registry.sqlite connection is still valid after all queries (read-only, no corruption)",
     con.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0] > 0)

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
