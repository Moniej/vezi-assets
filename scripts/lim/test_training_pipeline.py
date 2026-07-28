"""Engineering-correctness tests for the LIM-2 training-registry/loader
pipeline. No real GPU training runs here (that's the real, separately-run
integration proof in docs/lim_runs/lim2_completion.md) -- these tests cover
everything that doesn't require loading a model: registry immutability,
traceability, dataset-readiness refusal (unregistered/tampered/gate
-violating), and quality-report field completeness. Matches this
project's no-pytest, assertion-script convention.

  lim_training/venv/Scripts/python.exe scripts/lim/test_training_pipeline.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.lim import (  # noqa: E402
    dataset_loader as dl, quality_report, registry, training, training_registry as tr)

FAILURES = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def _register_fake_version(con_lim, *, dataset_type: str, examples: list[dict],
                           violations: list[str] | None = None,
                           teacher_model_ids: list[str] | None = None,
                           splits: dict | None = None) -> str:
    """Builds a minimal, real (not mocked) registered version -- writes a
    real accepted.jsonl, a real audit_report.json, a real splits.json
    (LIM-4: load_training_set now REQUIRES one -- default here puts every
    example in "train" so existing callers that don't care about splits
    keep working unchanged), computes a real content hash, and registers
    it exactly the way export_dataset.py does."""
    version = registry.next_version(con_lim, dataset_type)
    version_dir = Path(tempfile.mkdtemp()) / dataset_type / version
    version_dir.mkdir(parents=True)
    accepted_path = version_dir / "accepted.jsonl"
    rejected_path = version_dir / "rejected.jsonl"
    accepted_path.write_text("\n".join(json.dumps(e) for e in examples), encoding="utf-8")
    rejected_path.write_text("", encoding="utf-8")
    (version_dir / "audit_report.json").write_text(
        json.dumps({"audit": {"n_total": len(examples)}, "violations": violations or []}),
        encoding="utf-8")
    default_splits = {"train": [e["unique_id"] for e in examples], "validation": [], "test": []}
    (version_dir / "splits.json").write_text(
        json.dumps(splits if splits is not None else default_splits), encoding="utf-8")
    registry.register_version(
        con_lim, version=version, dataset_type=dataset_type, accepted_path=accepted_path,
        rejected_path=rejected_path, source_as_of=date.today().isoformat(),
        n_accepted=len(examples), n_rejected=0,
        teacher_model_ids=teacher_model_ids or ["test-model"], changelog="test fixture")
    return version


def test_training_registry_immutability_and_traceability():
    con = tr.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    run_id = tr.start_run(
        con, dataset_versions=["extraction@extraction-v1.0.0"],
        dataset_content_hashes={"extraction-v1.0.0": "abc123"}, teacher_model_ids=["test-model"],
        base_model="unsloth/Qwen3-4B-unsloth-bnb-4bit", quantization_config={"load_in_4bit": True},
        lora_config={"r": 8}, hyperparameters={"lr": 2e-4}, seed=42, git_commit="deadbeef")
    check("training_registry: start_run returns a real run_id", bool(run_id))

    tr.log_event(con, run_id, event_type="checkpoint", step=10, checkpoint_path="/fake/ckpt-10")
    tr.log_event(con, run_id, event_type="completed", step=20, metrics={"final_loss": 1.1})
    run = tr.get_run(con, run_id)
    check("training_registry: 'started' event auto-logged by start_run",
         any(e["event_type"] == "started" for e in run["events"]))
    check("training_registry: all 3 events present", len(run["events"]) == 3)

    found = tr.run_for_checkpoint(con, "/fake/ckpt-10")
    check("training_registry: checkpoint traces back to the correct run",
         found is not None and found["run_id"] == run_id)
    check("training_registry: traced-back run carries seed/git_commit/dataset_versions",
         found["seed"] == 42 and found["git_commit"] == "deadbeef" and
         found["dataset_versions"] == ["extraction@extraction-v1.0.0"])

    try:
        con.execute("UPDATE training_runs SET seed = 99 WHERE run_id = ?", (run_id,))
        check("training_registry: UPDATE on training_runs blocked", False)
    except Exception:  # noqa: BLE001
        check("training_registry: UPDATE on training_runs blocked", True)
    try:
        con.execute("DELETE FROM training_run_events WHERE run_id = ?", (run_id,))
        check("training_registry: DELETE on training_run_events blocked", False)
    except Exception:  # noqa: BLE001
        check("training_registry: DELETE on training_run_events blocked", True)


def test_loader_refuses_unregistered_and_tampered():
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    version = _register_fake_version(con, dataset_type="extraction",
                                     examples=[{"unique_id": "extraction:1", "task": "extraction"}])

    resolved, examples = dl.load_examples(con, "extraction", version)
    check("loader: loads a real registered version successfully", len(examples) == 1)

    try:
        dl.load_examples(con, "extraction", "extraction-v99.0.0")
        check("loader: refuses a nonexistent version", False)
    except dl.DatasetNotReadyError:
        check("loader: refuses a nonexistent version", True)

    meta = registry.get_version(con, version)
    accepted_path = Path(meta["accepted_path"])
    original = accepted_path.read_text(encoding="utf-8")
    accepted_path.write_text(original + "\n{\"tampered\": true}", encoding="utf-8")
    try:
        dl.load_examples(con, "extraction", version)
        tampered_refused = False
    except dl.DatasetNotReadyError:
        tampered_refused = True
    finally:
        accepted_path.write_text(original, encoding="utf-8")
    check("loader: tampering (content_hash mismatch) correctly detected and refused",
         tampered_refused)


def test_loader_refuses_versions_with_recorded_violations():
    """A version that somehow has recorded threshold violations (e.g. a
    hand-constructed registry row, or a future bug in export_dataset.py)
    must still be refused at LOAD time too -- defense in depth, never
    trusting registration status alone."""
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    version = _register_fake_version(
        con, dataset_type="extraction",
        examples=[{"unique_id": "extraction:1", "task": "extraction"}],
        violations=["duplicate_rate 0.9 > max 0.05"])
    try:
        dl.load_examples(con, "extraction", version)
        check("loader: refuses a version with recorded violations", False)
    except dl.DatasetNotReadyError as e:
        check("loader: refuses a version with recorded violations", True)
        check("loader: refusal names the violation", "violation" in str(e).lower())


def test_load_training_set_multi_dataset():
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    v1 = _register_fake_version(con, dataset_type="extraction",
                                examples=[{"unique_id": "extraction:1"}],
                                teacher_model_ids=["gemini-3.6-flash"])
    v2 = _register_fake_version(con, dataset_type="self_critique",
                                examples=[{"unique_id": "self_critique:1"},
                                         {"unique_id": "self_critique:2"}],
                                teacher_model_ids=["gemini-3.6-flash"])
    manifest = dl.load_training_set(con, [("extraction", None), ("self_critique", None)])
    check("loader: multi-dataset manifest has correct total example count",
         manifest["n_examples"] == 3)
    check("loader: manifest records both resolved versions",
         set(manifest["dataset_versions"]) == {f"extraction@{v1}", f"self_critique@{v2}"})
    check("loader: manifest unions teacher_model_ids", manifest["teacher_model_ids"] == ["gemini-3.6-flash"])


def test_load_training_set_never_returns_test_split_examples():
    """LIM-4 regression test for the real contamination bug found in LIM-4's
    diagnosis: the first LIM-2 training run's ad hoc `examples[:len//10]`
    in-training eval slice actually trained on entity_recognition:21/25/33,
    the SAME unique_ids scripts/lim/run_evaluation.py later scored as
    "held out". load_training_set must now make that structurally
    impossible by consulting the real splits.json and excluding `test`
    unique_ids unconditionally."""
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    examples = [{"unique_id": f"extraction:{i}"} for i in range(1, 6)]
    splits = {"train": ["extraction:1", "extraction:2", "extraction:3"],
             "validation": ["extraction:4"], "test": ["extraction:5"]}
    _register_fake_version(con, dataset_type="extraction", examples=examples, splits=splits)
    manifest = dl.load_training_set(con, [("extraction", None)])
    returned_ids = {e["unique_id"] for e in manifest["examples"]}
    check("loader: test-split unique_id never appears in the returned manifest",
         "extraction:5" not in returned_ids)
    check("loader: train-split examples are returned",
         {"extraction:1", "extraction:2", "extraction:3"} <= returned_ids)
    check("loader: validation-split examples are returned separately",
         [e["unique_id"] for e in manifest["validation_examples"]] == ["extraction:4"])
    check("loader: train_examples excludes validation and test",
         [e["unique_id"] for e in manifest["train_examples"]] ==
         ["extraction:1", "extraction:2", "extraction:3"])
    check("loader: n_examples counts only train+validation, never test",
         manifest["n_examples"] == 4)


def test_load_training_set_refuses_without_splits_json():
    """A registered version missing splits.json must refuse to train
    rather than silently treating everything as trainable -- the same
    "refuse, never guess" posture as every other readiness check."""
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    version = _register_fake_version(con, dataset_type="extraction",
                                     examples=[{"unique_id": "extraction:1"}])
    meta = registry.get_version(con, version)
    (Path(meta["accepted_path"]).parent / "splits.json").unlink()
    try:
        dl.load_training_set(con, [("extraction", None)])
        check("loader: refuses a version with no splits.json", False)
    except dl.DatasetNotReadyError:
        check("loader: refuses a version with no splits.json", True)


def test_training_refuses_before_any_run_recorded():
    con_lim = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    con_train = tr.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    try:
        training.run_training(
            con_lim, con_train, dataset_specs=[("extraction", None)],
            base_model="unsloth/Qwen3-4B-unsloth-bnb-4bit",
            quantization_config={"load_in_4bit": True}, lora_config={"r": 8},
            hyperparameters={"max_steps": 1}, seed=1)
        check("training: refuses when no dataset is registered at all", False)
    except dl.DatasetNotReadyError:
        check("training: refuses when no dataset is registered at all", True)
    n_runs = con_train.execute("SELECT COUNT(*) FROM training_runs").fetchone()[0]
    check("training: a refused attempt leaves ZERO training_runs rows (nothing was attempted)",
         n_runs == 0)


def test_quality_report_has_every_required_field():
    con = registry.init_registry(Path(tempfile.mktemp(suffix=".sqlite")))
    version = _register_fake_version(con, dataset_type="extraction",
                                     examples=[{"unique_id": "extraction:1"}])
    report = quality_report.build_quality_report(con, version)
    required = ["example_count", "acceptance_rate", "rejection_rate", "duplicate_rate",
               "grounding_integrity", "citation_integrity", "confidence_distribution",
               "class_balance", "company_coverage", "date_coverage", "teacher_model_version",
               "git_commit", "dataset_version_hash"]
    missing = [f for f in required if f not in report]
    check("quality_report: every owner-specified field is present", not missing,
         detail=f"missing: {missing}")
    md = quality_report.render_markdown(report)
    check("quality_report: markdown renders without error", len(md) > 0)


if __name__ == "__main__":
    test_training_registry_immutability_and_traceability()
    test_loader_refuses_unregistered_and_tampered()
    test_loader_refuses_versions_with_recorded_violations()
    test_load_training_set_multi_dataset()
    test_load_training_set_never_returns_test_split_examples()
    test_load_training_set_refuses_without_splits_json()
    test_training_refuses_before_any_run_recorded()
    test_quality_report_has_every_required_field()

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
