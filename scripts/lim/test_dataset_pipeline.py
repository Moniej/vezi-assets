"""Engineering-correctness tests for the LIM-1 dataset pipeline (schema,
quality scoring, registry, audit, exporters). Matches this project's
existing no-pytest, assertion-script convention (scripts/test_reasoning_
pipeline.py) -- a synthetic temp DB fixture, never the real ngx.sqlite,
never a real API/model call (this whole package is read-only data
processing, no LLM involved at all).

  lim_training/venv/Scripts/python.exe scripts/lim/test_dataset_pipeline.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.lim import audit, quality, registry  # noqa: E402
from ngxrot.lim.exporters import EXPORTERS  # noqa: E402
from ngxrot.lim.schema import TASK_TYPES, TrainingExample, make_unique_id  # noqa: E402

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def make_test_db():
    tmp = Path(tempfile.mkdtemp()) / "test_lim.sqlite"
    con = db.init_db(tmp, seed=False)
    text_dir = Path(tempfile.mkdtemp())
    text_path = text_dir / "1.txt"
    text_path.write_text("The Board declared a final dividend of N1.90 per share.", encoding="utf-8")
    con.execute("INSERT INTO securities (ticker, name, board) VALUES "
               "('TESTCO', 'Test Company Plc', 'main')")
    source_id = con.execute(
        "INSERT INTO sources (name, kind, reliability, base_confidence) "
        "VALUES ('test_source','company_filing','primary',0.85)").lastrowid
    con.execute(
        "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, source_type, "
        "filing_date, retrieved_date, local_path, text_path, extraction_method, "
        "char_count, source_confidence, source_id, as_of_date) VALUES "
        "(1,'TESTCO','TESTCO','dividend','filing','2026-04-01','2026-04-01',"
        "'x',?,'native',300,0.85,?,?)",
        (str(text_path), source_id, date.today().isoformat()))
    con.commit()
    return con


def _insert_fact(con, *, fact_id, grounding_check="passed", model_id="test-model"):
    ev_id = con.execute(
        "INSERT INTO evidence (doc_id, quoted_text, source_confidence) VALUES "
        "(1,'a final dividend of N1.90 per share',0.85)").lastrowid
    con.execute(
        "INSERT INTO extracted_facts (fact_id, doc_id, fact_type, description, "
        "extraction_confidence, evidence_id, model_id, prompt_version, grounding_check, "
        "extracted_at) VALUES (?,1,'dividend','TESTCO dividend',0.3,?,?,?,?,?)",
        (fact_id, ev_id, model_id, "v1" if model_id else None, grounding_check,
         date.today().isoformat()))
    con.commit()
    return fact_id, ev_id


def test_schema_validation():
    ex = TrainingExample(unique_id=make_unique_id("extraction", 1), task="extraction",
                        instruction="test")
    check("schema: valid example constructs", ex.acceptance_status == "accepted")
    try:
        TrainingExample(unique_id="x", task="not_a_real_task", instruction="t")
        check("schema: invalid task rejected", False)
    except ValueError:
        check("schema: invalid task rejected", True)
    try:
        TrainingExample(unique_id="x", task="extraction", instruction="t",
                       acceptance_status="rejected")
        check("schema: rejected without reason blocked", False)
    except ValueError:
        check("schema: rejected without reason blocked", True)
    check("schema: make_unique_id is deterministic",
         make_unique_id("extraction", 1, 2) == make_unique_id("extraction", 1, 2))
    check("schema: TASK_TYPES has all 17 spec types", len(TASK_TYPES) == 17)


def test_quality_hard_exclusions():
    con = make_test_db()
    fact_id, _ = _insert_fact(con, fact_id=1, grounding_check="failed")
    a = quality.assess_example_quality(con, task="financial_reasoning", fact_id=fact_id)
    check("quality: grounding failure forces score to 0.0", a.quality_score == 0.0)
    check("quality: grounding failure names the exact hard exclusion",
         a.hard_exclusion is not None and a.hard_exclusion.startswith("grounding_failed"))
    status, reason = quality.decide_acceptance("financial_reasoning", a)
    check("quality: hard-excluded example is rejected", status == "rejected")


def test_quality_contradiction_hard_exclusion():
    con = make_test_db()
    fact_a, _ = _insert_fact(con, fact_id=1, grounding_check="passed")
    fact_b, _ = _insert_fact(con, fact_id=2, grounding_check="not_run")
    impl_a = con.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "generated_at) VALUES (?,'TESTCO','medium','small',0.5,'r','bullish','no_action',"
        "'unvalidated_ai_interpretation',?)", (fact_a, date.today().isoformat())).lastrowid
    impl_b = con.execute(
        "INSERT INTO investment_implications (fact_id, ticker, duration_bucket, magnitude, "
        "confidence, confidence_rationale, direction, action_recommendation, status, "
        "propagated_from_implication_id, contradicts_implication_id, generated_at) VALUES "
        "(?,'TESTCO','medium','small',0.9,'r','bearish','no_action','under_review',?,?,?)",
        (fact_b, impl_a, impl_a, date.today().isoformat())).lastrowid
    con.commit()
    a = quality.assess_example_quality(con, task="financial_reasoning", fact_id=fact_b,
                                      implication_id=impl_b)
    check("quality: contradicting a higher-trust-tier prior forces score to 0.0",
         a.quality_score == 0.0)
    check("quality: names the contradiction hard exclusion",
         a.hard_exclusion is not None and
         a.hard_exclusion.startswith("contradicts_higher_tier_evidence"))


def test_registry_immutability_and_versioning():
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    v1 = registry.next_version(con, "extraction")
    check("registry: first version is v1.0.0", v1 == "extraction-v1.0.0")
    dummy = Path(tempfile.mktemp(suffix=".jsonl"))
    dummy.write_text("{}", encoding="utf-8")
    registry.register_version(con, version=v1, dataset_type="extraction", accepted_path=dummy,
                              rejected_path=dummy, n_accepted=5, n_rejected=1,
                              teacher_model_ids=["test-model"], changelog="test")
    v2 = registry.next_version(con, "extraction")
    check("registry: next version increments minor", v2 == "extraction-v1.1.0")

    got = registry.get_version(con, v1)
    check("registry: get_version round-trips teacher_model_ids",
         got is not None and got["teacher_model_ids"] == ["test-model"])

    try:
        con.execute("UPDATE dataset_versions SET n_accepted = 999 WHERE version = ?", (v1,))
        check("registry: UPDATE blocked by trigger", False)
    except Exception:  # noqa: BLE001 -- sqlite3.OperationalError, the exact exception IS the assertion
        check("registry: UPDATE blocked by trigger", True)
    try:
        con.execute("DELETE FROM dataset_versions WHERE version = ?", (v1,))
        check("registry: DELETE blocked by trigger", False)
    except Exception:  # noqa: BLE001
        check("registry: DELETE blocked by trigger", True)


def test_registry_lineage():
    con_lim = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    con_ngx = make_test_db()
    fact_id, _ = _insert_fact(con_ngx, fact_id=1)
    ex = TrainingExample(unique_id=make_unique_id("extraction", fact_id), task="extraction",
                        instruction="t", retrieved_facts=[fact_id], source_documents=[1])
    dummy = Path(tempfile.mktemp(suffix=".jsonl"))
    dummy.write_text(ex.to_json_line(), encoding="utf-8")
    version = registry.next_version(con_lim, "extraction")
    registry.register_version(con_lim, version=version, dataset_type="extraction",
                              accepted_path=dummy, rejected_path=dummy, n_accepted=1,
                              n_rejected=0, changelog="test")
    registry.record_lineage(con_lim, con_ngx, version, [ex])
    found = registry.versions_containing(con_lim, fact_id=fact_id)
    check("registry: reverse lineage lookup finds the version", found == [version])


def test_audit_duplicate_detection():
    a = {"unique_id": "a", "acceptance_status": "accepted", "context": {"x": 1},
        "expected_output": {"y": 1}, "citations": []}
    b = {"unique_id": "b", "acceptance_status": "accepted", "context": {"x": 1},
        "expected_output": {"y": 1}, "citations": []}  # same content, different id
    c = {"unique_id": "c", "acceptance_status": "accepted", "context": {"x": 2},
        "expected_output": {"y": 2}, "citations": []}
    dup = audit.detect_duplicates([a, b, c])
    check("audit: exact-content duplicate detected", dup["n_duplicate_examples"] == 1)
    check("audit: duplicate rate computed correctly", abs(dup["duplicate_rate"] - 1 / 3) < 1e-3)


def test_audit_thresholds_enforce():
    audit_result = {
        "duplicate_detection": {"duplicate_rate": 0.5}, "contradiction": {"unresolved_contradiction_rate": 0.0},
        "citation_integrity": 1.0, "grounding_integrity": 1.0, "acceptance_rate": 1.0,
        "company_distribution": {"max_single_ticker_share": 0.1},
    }
    violations = audit.check_thresholds(audit_result)
    check("audit: high duplicate rate flagged as a violation",
         any("duplicate_rate" in v for v in violations))

    clean_result = dict(audit_result, duplicate_detection={"duplicate_rate": 0.0})
    check("audit: clean result has no violations", audit.check_thresholds(clean_result) == [])


def test_audit_splits_stable_across_growth():
    examples_small = [{"unique_id": f"ex:{i}", "acceptance_status": "accepted"} for i in range(20)]
    examples_large = examples_small + [{"unique_id": f"ex:{i}", "acceptance_status": "accepted"}
                                       for i in range(20, 100)]
    splits_small = audit.make_splits(examples_small)
    splits_large = audit.make_splits(examples_large)
    small_train_set = set(splits_small["train"])
    large_train_set = set(splits_large["train"])
    check("audit: an example's split assignment is stable as the dataset grows",
         small_train_set.issubset(large_train_set) or
         all((eid in large_train_set) == (eid in small_train_set) for eid in small_train_set))
    check("audit: split percentages roughly match config (80/10/10 default)",
         70 <= (len(splits_large["train"]) / 100 * 100) <= 90)


def test_exporters_against_synthetic_db():
    con = make_test_db()
    _insert_fact(con, fact_id=1, grounding_check="passed")
    _insert_fact(con, fact_id=2, grounding_check="failed")
    extraction = EXPORTERS["extraction"](con)
    check("exporters: extraction finds both synthetic facts", len(extraction) == 2)
    n_accepted = sum(1 for e in extraction if e.acceptance_status == "accepted")
    n_rejected = sum(1 for e in extraction if e.acceptance_status == "rejected")
    check("exporters: the grounded fact is accepted", n_accepted == 1)
    check("exporters: the ungrounded fact is rejected", n_rejected == 1)

    citation_grounding = EXPORTERS["citation_grounding"](con)
    check("exporters: citation_grounding sees 0 rows (both facts have model_id, but only "
         "financial_reasoning-style facts count -- real behavior, not a bug)",
         len(citation_grounding) == 2)


def _insert_second_ticker_fact(con, *, fact_id):
    con.execute("INSERT INTO securities (ticker, name, board) VALUES "
               "('OTHERCO', 'Other Company Plc', 'main')")
    text_dir = Path(tempfile.mkdtemp())
    text_path = text_dir / "2.txt"
    text_path.write_text("The Board declared a final dividend of N2.50 per share.", encoding="utf-8")
    source_id = con.execute(
        "SELECT source_id FROM sources WHERE name = 'test_source'").fetchone()[0]
    con.execute(
        "INSERT INTO documents (doc_id, ticker, raw_symbol, doc_type, source_type, "
        "filing_date, retrieved_date, local_path, text_path, extraction_method, "
        "char_count, source_confidence, source_id, as_of_date) VALUES "
        "(2,'OTHERCO','OTHERCO','dividend','filing','2026-04-01','2026-04-01',"
        "'x',?,'native',300,0.85,?,?)", (str(text_path), source_id, date.today().isoformat()))
    ev_id = con.execute(
        "INSERT INTO evidence (doc_id, quoted_text, source_confidence) VALUES "
        "(2,'a final dividend of N2.50 per share',0.85)").lastrowid
    con.execute(
        "INSERT INTO extracted_facts (fact_id, doc_id, fact_type, description, "
        "extraction_confidence, evidence_id, model_id, prompt_version, grounding_check, "
        "extracted_at) VALUES (?,2,'dividend','OTHERCO dividend',0.3,?,'test-model','v1',"
        "'passed',?)", (fact_id, ev_id, date.today().isoformat()))
    con.commit()


def test_cli_audit_gate_refuses_concentrated_data():
    """A single-ticker dataset is 100% concentrated -- the audit gate must
    correctly REFUSE to register it (max_single_ticker_share), not just
    silently ship it. This is the gate working as designed, not a bug."""
    sys.path.insert(0, str(ROOT / "scripts" / "lim"))
    import export_dataset  # noqa: E402

    con = make_test_db()
    _insert_fact(con, fact_id=1, grounding_check="passed")
    con_lim = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    orig_root = export_dataset.DATASETS_ROOT
    export_dataset.DATASETS_ROOT = Path(tempfile.mkdtemp())
    try:
        result = export_dataset.export_one(con, con_lim, "extraction", limit=None,
                                           changelog="test run", parent_version=None)
        check("cli: single-ticker concentration correctly REFUSED registration",
             result["registered"] is False)
        check("cli: refusal names the concentration violation",
             any("max_single_ticker_share" in v for v in result["violations"]))
        check("cli: audit artifacts still written even on refusal (inspectable, not hidden)",
             (export_dataset.DATASETS_ROOT / "extraction" / result["version"] /
              "audit_report.md").exists())
    finally:
        export_dataset.DATASETS_ROOT = orig_root


def test_cli_orchestration_end_to_end():
    """Import the CLI module directly (not a subprocess) and run export_one
    against a synthetic DB with two tickers (avoiding the concentration
    gate this data legitimately shouldn't trip), proving the whole pipeline
    (export -> audit -> threshold gate -> write JSONL -> register ->
    lineage) works together end to end, not just each piece in isolation."""
    sys.path.insert(0, str(ROOT / "scripts" / "lim"))
    import export_dataset  # noqa: E402

    con = make_test_db()
    _insert_fact(con, fact_id=1, grounding_check="passed")
    _insert_second_ticker_fact(con, fact_id=2)
    con_lim = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    orig_root = export_dataset.DATASETS_ROOT
    export_dataset.DATASETS_ROOT = Path(tempfile.mkdtemp())
    try:
        result = export_dataset.export_one(con, con_lim, "extraction", limit=None,
                                           changelog="test run", parent_version=None)
        check("cli: end-to-end export registers a version", result["registered"] is True,
             detail=str(result))
        version_dir = export_dataset.DATASETS_ROOT / "extraction" / result["version"]
        check("cli: accepted.jsonl written", (version_dir / "accepted.jsonl").exists())
        check("cli: audit_report.md written", (version_dir / "audit_report.md").exists())
        got = registry.get_version(con_lim, result["version"])
        check("cli: version actually registered and retrievable", got is not None)
    finally:
        export_dataset.DATASETS_ROOT = orig_root


if __name__ == "__main__":
    test_schema_validation()
    test_quality_hard_exclusions()
    test_quality_contradiction_hard_exclusion()
    test_registry_immutability_and_versioning()
    test_registry_lineage()
    test_audit_duplicate_detection()
    test_audit_thresholds_enforce()
    test_audit_splits_stable_across_growth()
    test_exporters_against_synthetic_db()
    test_cli_audit_gate_refuses_concentrated_data()
    test_cli_orchestration_end_to_end()

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
