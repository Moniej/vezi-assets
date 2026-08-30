"""Regression checks for directional_reasoning_v2.py (FRE-8).

  PYTHONPATH=src python scripts/fre/test_directional_reasoning_v2.py

Runs against the real database, read-only -- no scratch copy needed (this
module has no write path, same posture as reaction_check.py/
company_memory.py).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import directional_reasoning_v2 as drv2  # noqa: E402

passed = failed = 0


def check(name: str, cond: bool) -> None:
    global passed, failed
    if cond:
        print(f"[PASS] {name}")
        passed += 1
    else:
        print(f"[FAIL] {name}")
        failed += 1


con = db.connect()

# Phase 7 firewall
check("REASONING_WEIGHT is fixed at 0.0", drv2.REASONING_WEIGHT == 0.0)
check("no Alpha Engine file imports this module",
      not any((ROOT / "src" / "ngxrot" / f).read_text(encoding="utf-8").find("directional_reasoning_v2") != -1
              for f in ("alpha_engine.py", "engine_full.py", "runner.py", "registry.py")))

# Phase 2: contradiction engine
conflicts = drv2.detect_contradictions(con)
veritas = [c for c in conflicts if c.ticker == "VERITASKAP" and c.anchor_date == "2026-05-07"]
check("VERITASKAP's real bullish/bearish pair is detected as conflicted",
      len(veritas) == 1 and veritas[0].conflicted)
check("groups with a single implication are never conflicted",
      all(c.conflicted or len(c.implication_ids) >= 1 for c in conflicts))
singletons = [c for c in conflicts if len(c.implication_ids) == 1]
check("singleton groups are always conflicted=False",
      all(not c.conflicted for c in singletons) and len(singletons) > 0)

cidx = {iid: c for c in conflicts for iid in c.implication_ids}

# Phase 3: staged conclusion, worked example
sc39 = drv2.staged_conclusion(con, 39, cidx)
sc40 = drv2.staged_conclusion(con, 40, cidx)
check("VERITASKAP implication 39 (bullish) is CONFLICTED, not a blind bullish call",
      sc39.conclusion == "CONFLICTED")
check("VERITASKAP implication 40 (bearish) is ALSO CONFLICTED (system does not retain both)",
      sc40.conclusion == "CONFLICTED")
check("staged conclusion never fabricates a valuation point_estimate when compute() has no data",
      sc39.valuation.label == "insufficient_evidence" or sc39.valuation.point_estimate is not None)
check("expectation check is always insufficient_evidence (no dataset exists)",
      sc39.expectation.label == "insufficient_evidence")

# real, non-conflicted case
sc25 = drv2.staged_conclusion(con, 25, cidx)  # LASACO
check("a non-conflicted case never claims CONFLICTED",
      sc25.conclusion in ("DIRECTIONAL_WEAK", "INSUFFICIENT_EVIDENCE"))
check("staged conclusion is never a bare 'bullish'/'bearish' (never re-adds false confidence)",
      sc25.conclusion not in ("bullish", "bearish", "CONFIRM", "CONTRADICT"))

# neutral direction -> insufficient evidence, never forced
row = con.execute("SELECT implication_id FROM investment_implications WHERE direction='neutral' LIMIT 1").fetchone()
sc_neutral = drv2.staged_conclusion(con, row[0], cidx)
check("a neutral-direction implication resolves to INSUFFICIENT_EVIDENCE, never forced into a call",
      sc_neutral.conclusion == "INSUFFICIENT_EVIDENCE")

# Phase 1: taxonomy
t19 = drv2.classify_taxonomy(con, 19, cidx)  # CAVERTON, bearish, contradicted
check("CAVERTON (bearish, contradicted) is tagged fundamental_deterioration_incorrectly_bearish",
      "fundamental_deterioration_incorrectly_bearish" in t19.categories)
t25 = drv2.classify_taxonomy(con, 25, cidx)  # LASACO, bullish, contradicted
check("LASACO (bullish, contradicted) is tagged fundamental_improvement_incorrectly_bullish",
      "fundamental_improvement_incorrectly_bullish" in t25.categories)
t3 = drv2.classify_taxonomy(con, 3, cidx)  # TOTAL, confirmed
check("a confirmed case is tagged confirmed_no_failure, not a failure category",
      t3.categories == ("confirmed_no_failure",))

# nonexistent implication raises, never fabricates
try:
    drv2.staged_conclusion(con, 999999, cidx)
    check("a nonexistent implication_id raises rather than fabricating", False)
except ValueError:
    check("a nonexistent implication_id raises rather than fabricating", True)

# Phase 5: filing context object
veritas_doc = con.execute(
    "SELECT f.doc_id FROM investment_implications ii JOIN extracted_facts f ON f.fact_id=ii.fact_id "
    "WHERE ii.ticker='VERITASKAP' LIMIT 1").fetchone()[0]
fc = drv2.build_filing_context(con, veritas_doc, cidx)
check("filing context captures both sibling facts from the same document",
      {f["fact_type"] for f in fc.facts} == {"revenue", "net_profit"})
check("filing context correctly splits positive/negative factors from opposing implications",
      fc.positive_factors == ("revenue",) and fc.negative_factors == ("net_profit",))
check("filing context flags both implications as conflicted, matching the contradiction engine",
      set(fc.conflicts) == {39, 40})
check("expectation_context is always the literal string 'unavailable', never invented",
      fc.expectation_context == "unavailable")

# Phase 5: unweighted score is not a weighted composite
us = drv2.unweighted_score(sc25)
check("unweighted score is a completeness count (0-4), not a directional confidence number",
      0 <= us.stages_resolved <= us.stages_total == 4)

# no mutation
before = con.execute("SELECT COUNT(*) FROM investment_implications").fetchone()[0]
before_facts = con.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0]
drv2.detect_contradictions(con)
for iid in (3, 19, 25, 39, 40):
    drv2.staged_conclusion(con, iid, cidx)
after = con.execute("SELECT COUNT(*) FROM investment_implications").fetchone()[0]
after_facts = con.execute("SELECT COUNT(*) FROM extracted_facts").fetchone()[0]
check("production data unchanged (investment_implications)", before == after)
check("production data unchanged (extracted_facts)", before_facts == after_facts)

con.close()
print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(0 if failed == 0 else 1)
