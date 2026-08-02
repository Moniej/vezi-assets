"""Dataset audit framework (DATASET_GENERATION_AND_TRAINING_SPEC.md §6).
Computes a fixed checklist of metrics before any dataset version is
considered usable for training, and enforces configurable thresholds --
training is refused (not merely warned) on a breach, mirroring the quant
engine's own coverage-gate enforcement pattern exactly, ported to a new
domain. Also builds train/validation/test split reports (this session's
LIM-1 addition, not previously specified in the design doc, requested
directly by the owner).
"""

from __future__ import annotations

import hashlib
import json
import statistics
import tomllib
from collections import Counter
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PKG_ROOT / "configs" / "dataset_quality_thresholds.toml"

# Ad hoc, disclosed, owner-adjustable thresholds -- same status as every
# other ad hoc constant in this package. configs/dataset_quality_thresholds.
# toml can override without a code change.
DEFAULT_THRESHOLDS = {
    "max_duplicate_rate": 0.05,
    "max_unresolved_contradiction_rate": 0.10,
    "min_citation_integrity": 0.95,
    "min_grounding_integrity": 0.95,
    "min_acceptance_rate": 0.30,
    "max_single_ticker_share": 0.60,   # company-distribution concentration cap
}

# Per-task-type overrides for dataset types whose entire purpose runs
# counter to a general-positive-dataset assumption embedded in the
# defaults above -- hallucination_detection's citations are, by
# construction, always ungrounded (that's the training signal, not a
# defect), so the general min_grounding_integrity/min_acceptance_rate
# floors would make this dataset type permanently un-registerable.
# Same status as quality.py's GROUNDING_EXCLUSION_EXEMPT_TASKS -- kept
# here rather than merged into one giant table so each module states its
# own exemption for its own reason, independently auditable.
PER_TASK_THRESHOLD_OVERRIDES = {
    "hallucination_detection": {"min_grounding_integrity": 0.0, "min_acceptance_rate": 0.0},
}


def _text_fingerprint(ex: dict) -> str:
    """Exact + near-duplicate signal: hash of expected_output + context
    together (not unique_id, which is derived from the source row id and
    would never collide even for a genuine content duplicate)."""
    payload = json.dumps([ex.get("context", {}), ex.get("expected_output", {})],
                        sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_duplicates(examples: list[dict]) -> dict:
    fingerprints = Counter(_text_fingerprint(ex) for ex in examples)
    n_duplicate_examples = sum(c - 1 for c in fingerprints.values() if c > 1)
    return {
        "n_examples": len(examples),
        "n_distinct_content": len(fingerprints),
        "n_duplicate_examples": n_duplicate_examples,
        "duplicate_rate": round(n_duplicate_examples / len(examples), 4) if examples else 0.0,
    }


def _distribution(values: list) -> dict:
    c = Counter(values)
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def _numeric_distribution(values: list[float]) -> dict:
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None, "stdev": None}
    return {
        "n": len(values), "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4), "min": round(min(values), 4),
        "max": round(max(values), 4),
        "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
    }


def compute_audit(examples: list, con=None, sector_lookup: dict | None = None) -> dict:
    """`examples` may be TrainingExample objects or plain dicts (both
    accepted and rejected partitions together -- the audit describes the
    WHOLE proposed version, not just what would ship)."""
    dicts = [e.to_dict() if hasattr(e, "to_dict") else e for e in examples]
    accepted = [d for d in dicts if d["acceptance_status"] == "accepted"]
    rejected = [d for d in dicts if d["acceptance_status"] == "rejected"]

    dup = detect_duplicates(dicts)

    n_contradictions = sum(1 for d in dicts if d.get("contradiction_analysis"))
    n_unresolved = sum(1 for d in dicts if d.get("contradiction_analysis")
                       and d["contradiction_analysis"].get("agreement") is False)

    citation_total = sum(len(d.get("citations", [])) for d in dicts)
    citation_with_doc_match = sum(
        1 for d in dicts for c in d.get("citations", []) if c.get("doc_id") is not None)
    citation_integrity = (citation_with_doc_match / citation_total) if citation_total else None

    grounded = sum(1 for d in dicts for c in d.get("citations", [])
                   if c.get("grounding_check") not in (None, "failed"))
    grounding_integrity = (grounded / citation_total) if citation_total else None

    tickers = [d.get("context", {}).get("ticker") for d in dicts if d.get("context", {}).get("ticker")]
    ticker_dist = _distribution(tickers)
    max_ticker_share = (max(ticker_dist.values()) / len(tickers)) if tickers else 0.0

    rejection_reasons = _distribution(
        [d["rejection_reason"].split(":", 1)[0] for d in rejected if d.get("rejection_reason")])

    filing_dates = [d.get("context", {}).get("filing_date") for d in dicts
                    if d.get("context", {}).get("filing_date")]
    fact_types = [d.get("context", {}).get("fact_type") for d in dicts
                 if d.get("context", {}).get("fact_type")]

    reasoning_lengths = [len(d.get("reasoning_chain", [])) for d in dicts if d.get("reasoning_chain")]

    n_sector_known = 0
    if sector_lookup is not None:
        n_sector_known = sum(1 for t in tickers if sector_lookup.get(t))

    return {
        "n_total": len(dicts), "n_accepted": len(accepted), "n_rejected": len(rejected),
        "acceptance_rate": round(len(accepted) / len(dicts), 4) if dicts else None,
        "rejection_rate": round(len(rejected) / len(dicts), 4) if dicts else None,
        "rejection_reason_distribution": rejection_reasons,
        "duplicate_detection": dup,
        "contradiction": {
            "n_contradictions_analyzed": n_contradictions,
            "n_unresolved_against_higher_tier": n_unresolved,
            "unresolved_contradiction_rate": round(n_unresolved / len(dicts), 4) if dicts else 0.0,
        },
        "citation_integrity": None if citation_integrity is None else round(citation_integrity, 4),
        "grounding_integrity": None if grounding_integrity is None else round(grounding_integrity, 4),
        "company_distribution": {
            "n_distinct_tickers": len(ticker_dist), "distribution": ticker_dist,
            "max_single_ticker_share": round(max_ticker_share, 4),
        },
        "sector_distribution": (
            {"status": "not_computable",
            "reason": "no sector_lookup was supplied to compute_audit() for this run "
                     "(securities.sector_ngx is now populated for 136/320 tickers "
                     "platform-wide as of FSI Phase 23, 2026-08-02, but no caller of "
                     "this function has been wired to build sector_lookup from it yet)"}
            if sector_lookup is None or n_sector_known == 0
            else {"status": "computed", "n_known": n_sector_known}
        ),
        "class_balance_by_fact_type": _distribution(fact_types),
        "temporal_distribution_by_year": _distribution(
            [d[:4] for d in filing_dates if d]),
        "confidence_distribution": _numeric_distribution([d.get("confidence") for d in dicts]),
        "coverage_score_distribution": _numeric_distribution([d.get("coverage_score") for d in dicts]),
        "evidence_tier_distribution": _distribution(
            [d.get("evidence_tier") for d in dicts if d.get("evidence_tier") is not None]),
        "reasoning_length_distribution": _numeric_distribution(reasoning_lengths) if reasoning_lengths else
            {"n": 0, "note": "no examples in this export carry a reasoning_chain"},
        "quality_score_distribution": _numeric_distribution([d.get("quality_score") for d in dicts]),
    }


def load_thresholds(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return DEFAULT_THRESHOLDS
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return raw.get("thresholds", DEFAULT_THRESHOLDS)


def load_split_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return {"train_pct": 80, "val_pct": 10}
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return raw.get("splits", {"train_pct": 80, "val_pct": 10})


def check_thresholds(audit: dict, thresholds: dict | None = None,
                     dataset_type: str | None = None) -> list[str]:
    """Returns a list of violated-threshold messages; empty list = pass.
    Enforcement (refusing to train) is the CALLER's job -- this function
    only evaluates, matching the rest of this package's "mechanical check,
    caller decides what to do with it" convention."""
    t = dict(thresholds if thresholds is not None else load_thresholds())
    if dataset_type in PER_TASK_THRESHOLD_OVERRIDES:
        t.update(PER_TASK_THRESHOLD_OVERRIDES[dataset_type])
    violations = []
    dup_rate = audit["duplicate_detection"]["duplicate_rate"]
    if dup_rate > t["max_duplicate_rate"]:
        violations.append(f"duplicate_rate {dup_rate} > max {t['max_duplicate_rate']}")
    contra_rate = audit["contradiction"]["unresolved_contradiction_rate"]
    if contra_rate > t["max_unresolved_contradiction_rate"]:
        violations.append(f"unresolved_contradiction_rate {contra_rate} > "
                          f"max {t['max_unresolved_contradiction_rate']}")
    ci = audit["citation_integrity"]
    if ci is not None and ci < t["min_citation_integrity"]:
        violations.append(f"citation_integrity {ci} < min {t['min_citation_integrity']}")
    gi = audit["grounding_integrity"]
    if gi is not None and gi < t["min_grounding_integrity"]:
        violations.append(f"grounding_integrity {gi} < min {t['min_grounding_integrity']}")
    acc = audit["acceptance_rate"]
    if acc is not None and acc < t["min_acceptance_rate"]:
        violations.append(f"acceptance_rate {acc} < min {t['min_acceptance_rate']}")
    max_share = audit["company_distribution"]["max_single_ticker_share"]
    if max_share > t["max_single_ticker_share"]:
        violations.append(f"max_single_ticker_share {max_share} > "
                          f"max {t['max_single_ticker_share']}")
    return violations


# ---------------------------------------------------------------------------
# Train/validation/test splits
# ---------------------------------------------------------------------------

def _split_bucket(unique_id: str) -> int:
    """Deterministic 0-99 bucket from a stable hash of unique_id -- NOT a
    random shuffle. This is what keeps a split assignment stable as a
    dataset grows across versions (spec §9's non-contamination principle):
    the same source row always lands in the same split, regardless of how
    many other examples exist when the split is computed."""
    h = hashlib.sha256(unique_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100


def make_splits(examples: list, *, train_pct: int | None = None, val_pct: int | None = None) -> dict:
    """Returns {"train": [...], "validation": [...], "test": [...]} of
    unique_ids (only ACCEPTED examples are eligible for any split --
    rejected examples never enter training, by construction)."""
    if train_pct is None or val_pct is None:
        split_cfg = load_split_config()
        train_pct = train_pct if train_pct is not None else split_cfg["train_pct"]
        val_pct = val_pct if val_pct is not None else split_cfg["val_pct"]
    dicts = [e.to_dict() if hasattr(e, "to_dict") else e for e in examples]
    accepted = [d for d in dicts if d["acceptance_status"] == "accepted"]
    splits = {"train": [], "validation": [], "test": []}
    for d in accepted:
        bucket = _split_bucket(d["unique_id"])
        if bucket < train_pct:
            splits["train"].append(d["unique_id"])
        elif bucket < train_pct + val_pct:
            splits["validation"].append(d["unique_id"])
        else:
            splits["test"].append(d["unique_id"])
    return splits


def split_report(splits: dict) -> dict:
    total = sum(len(v) for v in splits.values())
    return {
        "total_accepted": total,
        "train": {"n": len(splits["train"]),
                  "pct": round(100 * len(splits["train"]) / total, 1) if total else 0.0},
        "validation": {"n": len(splits["validation"]),
                      "pct": round(100 * len(splits["validation"]) / total, 1) if total else 0.0},
        "test": {"n": len(splits["test"]),
                "pct": round(100 * len(splits["test"]) / total, 1) if total else 0.0},
    }


def render_markdown(dataset_type: str, audit: dict, splits_rep: dict,
                    violations: list[str]) -> str:
    lines = [
        f"# Dataset Audit — {dataset_type}",
        "",
        f"- Total examples: {audit['n_total']} "
        f"(accepted {audit['n_accepted']}, rejected {audit['n_rejected']})",
        f"- Acceptance rate: {audit['acceptance_rate']} | Rejection rate: {audit['rejection_rate']}",
        f"- Rejection reasons: {audit['rejection_reason_distribution']}",
        "",
        "## Duplicate detection",
        f"- {audit['duplicate_detection']}",
        "",
        "## Contradiction",
        f"- {audit['contradiction']}",
        "",
        "## Integrity",
        f"- Citation integrity: {audit['citation_integrity']}",
        f"- Grounding integrity: {audit['grounding_integrity']}",
        "",
        "## Company / sector distribution",
        f"- Companies: {audit['company_distribution']}",
        f"- Sector: {audit['sector_distribution']}",
        "",
        "## Class / temporal balance",
        f"- Fact type: {audit['class_balance_by_fact_type']}",
        f"- By year: {audit['temporal_distribution_by_year']}",
        "",
        "## Numeric distributions",
        f"- Confidence: {audit['confidence_distribution']}",
        f"- Coverage score: {audit['coverage_score_distribution']}",
        f"- Evidence tier: {audit['evidence_tier_distribution']}",
        f"- Reasoning length: {audit['reasoning_length_distribution']}",
        f"- Quality score: {audit['quality_score_distribution']}",
        "",
        "## Train / validation / test split",
        f"- {splits_rep}",
        "",
        "## Threshold check",
        ("- **ALL THRESHOLDS PASS**" if not violations else
        "- **VIOLATIONS (training must be refused):**\n" +
        "\n".join(f"  - {v}" for v in violations)),
    ]
    return "\n".join(lines)
