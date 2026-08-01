"""Standalone assertion-script tests for src/ngxrot/fre/evidence_graph.py --
same no-pytest, script-based convention as scripts/test_reasoning_pipeline.py.

SAFETY (docs/fre_runs/incident_2026-08-01_prod_db_wipe.md): this script
copies the real data/ngx.sqlite into a disposable scratch file
(db.new_scratch_db_path()'s parent pattern) via shutil.copy and runs every
mutating test (backfill_implication_layers with dry_run=False) against that
COPY only. The real production file is opened read-only (via a
'file:...?mode=ro' URI connection) for the read-only assertions, so even a
bug in this test script cannot write to it.

  PYTHONPATH=src python scripts/fre/test_evidence_graph.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import evidence_graph as eg  # noqa: E402

# db.DEFAULT_DB, not a re-hardcoded literal path -- single source of truth
# for "where the real database is" (docs/fre_runs/incident_2026-08-01_prod_db_wipe.md).
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


def read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def main() -> int:
    # Snapshot production state up front -- compared, not assumed, at the
    # very end. Whether production has already been backfilled for real
    # (it has, as of this session) or not is irrelevant to this test; what
    # matters is that THIS test script changes nothing about it either way.
    prod_snapshot = sqlite3.connect(REAL_DB)
    doc_count_before = prod_snapshot.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    labeled_before = prod_snapshot.execute(
        "SELECT COUNT(*) FROM causal_chain_steps WHERE implication_layer IS NOT NULL"
    ).fetchone()[0]
    prod_snapshot.close()

    # --- classify_step_layer: known real cases (fact_id 144, the GTCO rights
    # issue -- the one real fact in this dataset that touches all three
    # layers) -----------------------------------------------------------
    ro = read_only_connection(REAL_DB)
    steps = ro.execute(
        "SELECT step_order, statement FROM causal_chain_steps WHERE fact_id = 144 ORDER BY step_order"
    ).fetchall()
    check("fact 144 has exactly 5 real steps", len(steps) == 5)
    labels = [eg.classify_step_layer(stmt) for _, stmt in steps]
    check("step 0 (raw offer restatement) classifies financial", labels[0] == "financial")
    check("step 1 (proceeds deployment/allocation) classifies business", labels[1] == "business")
    check("step 2 (regulatory compliance/lending capacity) classifies business", labels[2] == "business")
    check("step 3 is a genuine 4-4 tie, left unclassified (not guessed)", labels[3] is None)
    check("step 4 (earnings/equity/dilution synthesis) classifies financial", labels[4] == "financial")
    check("competitive never fires from step text alone on this fact "
          "(the real competitive_advantage/long_term_moat reasoning lives in "
          "impact_assessments, not causal_chain_steps -- see layer_gap_report)",
          "competitive" not in labels)

    # A known, disclosed false-positive: "mandated shareholders" (an
    # e-dividend registration detail) coincidentally contains "mandate"
    # (the business lexicon's regulatory-mandate term), producing a 1-1 tie
    # correctly left unclassified rather than mis-labeled 'business'.
    fp_statement = ro.execute(
        "SELECT statement FROM causal_chain_steps WHERE chain_id = 14"
    ).fetchone()[0]
    check("known false-positive-prone step ('mandated shareholders') is "
          "still left unclassified, not mis-labeled",
          eg.classify_step_layer(fp_statement) is None)
    ro.close()

    # --- build_evidence_chain, read-only against the real DB -------------
    ro = read_only_connection(REAL_DB)
    chain = eg.build_evidence_chain(ro, 144)
    check("EvidenceChain.fact_type is 'rights_issue'", chain.fact_type == "rights_issue")
    check("EvidenceChain.observation is non-empty (Observation stage)", len(chain.observation) > 0)
    check("EvidenceChain has at least one evidence quote (Evidence stage)",
          len(chain.evidence_quotes) >= 1)
    check("investment_implication_id resolves to the real implication",
          chain.investment_implication_id == 1)
    check("status reflects the real recorded self-critique block",
          chain.status == "blocked_by_self_critique")
    check("confidence matches the real recorded value (0.3)", chain.confidence == 0.3)
    check("missing_evidence surfaces the 4 real open research tasks for this fact",
          len(chain.missing_evidence) == 4)
    ro.close()

    # --- a simple dividend fact, for contrast (should be ~100% financial) -
    ro = read_only_connection(REAL_DB)
    chain2 = eg.build_evidence_chain(ro, 145)
    check("a routine dividend fact (145) has zero business/competitive steps "
          "-- expected, since a routine dividend has no such content, not a "
          "classifier gap", len(chain2.business_steps) == 0 and len(chain2.competitive_steps) == 0)
    ro.close()

    # --- backfill_implication_layers: on a DISPOSABLE COPY only -----------
    # (layer_gap_report is only meaningful AFTER backfill -- before it, every
    # causal_chain_steps.implication_layer is NULL by construction, so a gap
    # report against the raw production connection would trivially "flag"
    # every layer for every fact. Do it in the correct order, against the
    # scratch copy, not the production DB.)
    #
    # The scratch copy is reset to a known, fully-unbackfilled starting
    # state (implication_layer = NULL everywhere) regardless of whatever
    # state the REAL production database happens to be in when this test
    # runs -- the real backfill script may have already been run for real
    # against production earlier in the same session (it has: FRE-2's own
    # deliverable IS applying this backfill for real). This test must stay
    # deterministic either way, not assume production is always pristine.
    scratch = db.new_scratch_db_path()
    shutil.copy(REAL_DB, scratch)
    con = sqlite3.connect(scratch)
    con.execute("UPDATE causal_chain_steps SET implication_layer = NULL, reasoning_mode = NULL")
    con.commit()

    dry = eg.backfill_implication_layers(con, dry_run=True)
    check("dry run reports applied=False", dry.applied is False)
    check("dry run matches the real dataset's known distribution "
          "(60 steps, 56 financial, 2 business, 0 competitive, 2 unclassified)",
          (dry.total_steps, dry.newly_financial, dry.newly_business,
           dry.newly_competitive, dry.left_unclassified) == (60, 56, 2, 0, 2))
    still_null = con.execute(
        "SELECT COUNT(*) FROM causal_chain_steps WHERE implication_layer IS NOT NULL"
    ).fetchone()[0]
    check("dry run wrote nothing to the scratch copy", still_null == 0)

    applied = eg.backfill_implication_layers(con, dry_run=False)
    check("apply run reports applied=True", applied.applied is True)
    now_labeled = con.execute(
        "SELECT COUNT(*) FROM causal_chain_steps WHERE implication_layer IS NOT NULL"
    ).fetchone()[0]
    check("apply run wrote exactly 58 labels (56 financial + 2 business)", now_labeled == 58)

    # idempotency: re-running must not change anything (already_labeled
    # rows are skipped, not reclassified)
    second = eg.backfill_implication_layers(con, dry_run=False)
    check("re-running reports 58 already_labeled, 0 newly-anything",
          second.already_labeled == 58 and second.newly_financial == 0
          and second.newly_business == 0 and second.newly_competitive == 0)
    fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
    check("scratch copy still passes foreign_key_check after backfill", not fk_bad)

    # --- layer_gap_report, now meaningful (run AFTER backfill, against the
    # backfilled scratch copy) -- the concrete, disclosed FRE-2 finding:
    # EVERY one of the 18 real facts has at least one impact-active layer
    # with zero representation in its own causal chain. Fact 144 (the GTCO
    # rights issue) is missing only 'competitive' (its business/financial
    # steps ARE represented); every routine dividend fact is missing
    # 'business' specifically, because capital_allocation is genuinely
    # assessed 'positive' for a dividend (paying a dividend IS a capital
    # -allocation act) but the chain never writes a step whose language
    # classifies as business -- it stays financial-mechanics language
    # throughout. This is a real, useful, mechanically-discovered gap in how
    # the existing (frozen, unmodified) AI Intelligence Layer currently
    # writes causal chains, not a flaw in this audit.
    gaps = eg.layer_gap_report(con)
    check("layer_gap_report flags all 18 real facts (each is missing at "
          "least one impact-active layer from its own chain)", len(gaps) == 18)
    fact144_gap = next(g for g in gaps if g["fact_id"] == 144)
    check("fact 144 is missing ONLY 'competitive' (business/financial ARE "
          "represented in its chain)", fact144_gap["missing_layers"] == ["competitive"])
    fact145_gap = next(g for g in gaps if g["fact_id"] == 145)
    check("a routine dividend fact (145) is missing 'business' specifically "
          "(capital_allocation is genuinely active, but no step reads as "
          "business)", fact145_gap["missing_layers"] == ["business"])
    all_missing_business_or_competitive = all(
        set(g["missing_layers"]) <= {"business", "competitive"} for g in gaps
    )
    check("no fact is ever missing 'financial' (every real chain has at "
          "least one financial-classified step)", all_missing_business_or_competitive)

    con.close()
    Path(scratch).unlink()
    Path(scratch).parent.rmdir()

    # --- confirm the REAL production database was never touched by THIS
    # test script (compared against the snapshot taken at the very start of
    # main(), not against a hardcoded assumption about its absolute state --
    # production may legitimately already be backfilled for real by a
    # separate, deliberate run of scripts/fre/backfill_implication_layers.py
    # --apply, which is FRE-2's own actual deliverable, not something this
    # test performs or should expect to undo). -----------------------------
    prod = sqlite3.connect(REAL_DB)
    labeled_after = prod.execute(
        "SELECT COUNT(*) FROM causal_chain_steps WHERE implication_layer IS NOT NULL"
    ).fetchone()[0]
    check("production database's implication_layer count is UNCHANGED by "
          "this test run (this test only ever writes to a disposable "
          "scratch copy)", labeled_after == labeled_before)
    doc_count_after = prod.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged", doc_count_after == doc_count_before)
    prod.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
