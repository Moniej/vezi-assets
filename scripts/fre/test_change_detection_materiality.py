"""Decision Intelligence Phase 2/3: tests for change_detection.py and
materiality.py.

  PYTHONPATH=src python scripts/fre/test_change_detection_materiality.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.change_detection import DetectedChange, detect_changes  # noqa: E402
from ngxrot.fre.company_state import build_company_state  # noqa: E402
from ngxrot.fre.materiality import (  # noqa: E402
    CRITICAL, HIGH, LOW, MEDIUM, assess_materiality, rank_by_materiality,
)

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

    # --- same-ticker / forward-in-time guards -------------------------------
    s_cap_early = build_company_state(con, "CAP", "2020-01-01", intelligence_cache=cache)
    s_cap_late = build_company_state(con, "CAP", "2026-08-09", intelligence_cache=cache)
    s_afriprud = build_company_state(con, "AFRIPRUD", "2026-08-09", intelligence_cache=cache)

    raised = False
    try:
        detect_changes(s_cap_early, s_afriprud)
    except ValueError:
        raised = True
    check("detect_changes() refuses two different tickers (ValueError, never a mismatched diff)", raised)

    raised = False
    try:
        detect_changes(s_cap_late, s_cap_early)
    except ValueError:
        raised = True
    check("detect_changes() refuses a backward-in-time comparison (later as prior)", raised)

    # --- real diff over 6+ years for CAP: something changed ------------------
    changes = detect_changes(s_cap_early, s_cap_late)
    check("CAP 2020->2026: at least one real change detected", len(changes) > 0)
    check("every DetectedChange has a non-empty category/field/description/source/confidence",
          all(c.category and c.field and c.description and c.source and c.confidence for c in changes))
    check("every DetectedChange's timestamp falls within [prior.as_of, current.as_of]",
          all(s_cap_early.as_of_date <= c.timestamp <= s_cap_late.as_of_date for c in changes))
    check("every DetectedChange's confidence is 'high' or 'low' only",
          all(c.confidence in ("high", "low") for c in changes))

    # --- identical snapshot -> zero changes (a real determinism check) -----
    changes_self = detect_changes(s_cap_late, s_cap_late)
    check("CAP compared against itself produces ZERO changes (deterministic, no phantom diffs)",
          len(changes_self) == 0)

    # --- UNKNOWN-vs-UNKNOWN never produces a change; UNKNOWN-vs-KNOWN
    # produces a 'new' change, never a fabricated magnitude ------------------
    s_total = build_company_state(con, "TOTAL", "2026-08-09", intelligence_cache=cache)
    changes_total = detect_changes(s_total, s_total)
    check("TOTAL (all-UNKNOWN financials) compared against itself: zero changes, no crash",
          len(changes_total) == 0)

    # --- materiality: every DetectedChange gets a real, explainable level --
    for chg in changes:
        m = assess_materiality(chg)
        check(f"materiality({chg.category}/{chg.field}): level is one of LOW/MEDIUM/HIGH/CRITICAL",
              m.level in (LOW, MEDIUM, HIGH, CRITICAL))
        check(f"materiality({chg.category}/{chg.field}): at least one explaining reason recorded",
              len(m.reasons) > 0)

    # --- financial threshold rule, checked directly with synthetic
    # DetectedChange objects (never touching real magnitude-tuning) ---------
    big_growth = DetectedChange(ticker="X", category="financial", field="revenue",
                                 direction="improved", magnitude=0.75, description="", timestamp="",
                                 source="test", confidence="high", prior_value=100, current_value=175)
    check("a +75% revenue change classifies CRITICAL (>=50% threshold)",
          assess_materiality(big_growth).level == CRITICAL)
    small_growth = DetectedChange(ticker="X", category="financial", field="revenue",
                                   direction="improved", magnitude=0.02, description="", timestamp="",
                                   source="test", confidence="high", prior_value=100, current_value=102)
    check("a +2% revenue change classifies LOW (<5% threshold)",
          assess_materiality(small_growth).level == LOW)
    low_conf_big = DetectedChange(ticker="X", category="financial", field="revenue",
                                   direction="improved", magnitude=0.75, description="", timestamp="",
                                   source="test", confidence="low", prior_value=100, current_value=175)
    check("the SAME +75% revenue change is capped to MEDIUM when confidence='low' (STALE data)",
          assess_materiality(low_conf_big).level == MEDIUM)

    new_flag = DetectedChange(ticker="X", category="financial", field="flag:leverage_increasing",
                               direction="worsened", magnitude=None, description="", timestamp="",
                               source="test", confidence="high", prior_value=False, current_value=True)
    check("a newly-fired accounting-anomaly flag classifies HIGH regardless of magnitude",
          assess_materiality(new_flag).level == HIGH)

    suspension = DetectedChange(ticker="X", category="regulatory", field="suspension",
                                 direction="new", magnitude=None, description="", timestamp="",
                                 source="test", confidence="high", prior_value=None,
                                 current_value={"severity": "medium", "structurally_impairing": False})
    check("a 'suspension' regulatory event classifies CRITICAL regardless of its own recorded "
          "severity field (event_type override rule)", assess_materiality(suspension).level == CRITICAL)

    structurally_impairing_evt = DetectedChange(
        ticker="X", category="corporate_event", field="asset_disposal", direction="new",
        magnitude=None, description="", timestamp="", source="test", confidence="high",
        prior_value=None, current_value={"severity": "low", "structurally_impairing": True})
    check("structurally_impairing=True overrides to CRITICAL even when severity='low'",
          assess_materiality(structurally_impairing_evt).level == CRITICAL)

    routine_insider = DetectedChange(ticker="X", category="insider", field="SALE", direction="new",
                                      magnitude=None, description="", timestamp="", source="test",
                                      confidence="high", prior_value=None,
                                      current_value=type("T", (), {"routine_flag": True})())
    check("a scheme/plan-flagged (routine) insider transaction classifies LOW",
          assess_materiality(routine_insider).level == LOW)

    # --- ranking is stable, CRITICAL-first ----------------------------------
    assessments = [assess_materiality(c) for c in [small_growth, big_growth, new_flag]]
    ranked = rank_by_materiality(assessments)
    check("rank_by_materiality() sorts CRITICAL/HIGH before LOW",
          [a.level for a in ranked][0] in (CRITICAL, HIGH) and ranked[-1].level == LOW)

    con.close()
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (both modules are pure/read-only)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
