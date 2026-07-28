"""LIM-3 scoring logic (owner directive, 2026-07-28): "Do not optimize the
model yet. The objective is to establish an objective benchmark." Every
function here is a MECHANICAL, disclosed comparison against the recorded
expected_output (the teacher/ground-truth answer already captured in the
dataset at export time) -- never an LLM-as-judge call, never a live
re-query of the teacher model. That is a deliberate design choice, not an
oversight: it keeps every score reproducible byte-for-byte from data
already on disk, incurs no additional API cost, and treats "agreement with
teacher" literally -- does the local model's output match what the teacher
actually produced for this exact input.

A metric that isn't APPLICABLE to a given example (e.g. grounding_accuracy
on a dataset type whose expected_output carries no grounding verdict)
returns None for that example, never a fabricated 0 or 1 -- aggregate_
metrics() reports "not measurable" (with the reason) rather than silently
averaging over an empty or irrelevant set.
"""

from __future__ import annotations

import json
import re
import statistics


def parse_model_json(text: str) -> dict | None:
    """Best-effort extraction of a JSON object from raw model output --
    strips markdown code fences (the model was observed, in the LIM-2
    stabilization checkpoint-inference tests, to wrap its answers in
    ```json ... ``` fences) before attempting json.loads. Returns None
    (never raises) on anything that doesn't parse -- an unparseable
    output is a real, scoreable failure (agreement_with_teacher=0.0), not
    an error to crash the eval run over."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if brace_match:
        candidate = brace_match.group(0)
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _values_match(expected_val, actual_val) -> bool:
    if isinstance(expected_val, str) and isinstance(actual_val, str):
        return expected_val.strip().lower() == actual_val.strip().lower()
    if isinstance(expected_val, (list, tuple)) and isinstance(actual_val, (list, tuple)):
        try:
            return set(map(str, expected_val)) == set(map(str, actual_val))
        except TypeError:
            return list(expected_val) == list(actual_val)
    if isinstance(expected_val, dict) and isinstance(actual_val, dict):
        return field_agreement(expected_val, actual_val) == 1.0
    return expected_val == actual_val


def field_agreement(expected: dict, parsed: dict | None) -> float:
    """Fraction of expected_output's top-level keys the model's parsed JSON
    reproduces -- this IS the "agreement with teacher" metric, since
    expected_output is exactly what the teacher model produced for this
    input (captured at dataset-export time). An unparseable model output
    (parsed=None) scores 0.0 -- no partial credit for output that isn't
    even structured."""
    if not expected:
        return 1.0 if not parsed else 0.0  # nothing to match; only a truly empty answer agrees
    if parsed is None:
        return 0.0
    matches = sum(1 for k, v in expected.items() if k in parsed and _values_match(v, parsed[k]))
    return round(matches / len(expected), 4)


def self_critique_quality(example: dict, parsed: dict | None) -> float | None:
    """Applicable only to task='self_critique': categorical match of the
    model's 'finding' (pass/fail/concern) against the teacher's recorded
    finding -- the single most decision-relevant field for this task type
    (a self-critique that gets the finding wrong is wrong regardless of how
    well-written its explanation is)."""
    if example.get("task") != "self_critique":
        return None
    expected_finding = example.get("expected_output", {}).get("finding")
    if expected_finding is None:
        return None
    if parsed is None:
        return 0.0
    return 1.0 if str(parsed.get("finding", "")).strip().lower() == str(expected_finding).strip().lower() else 0.0


def grounding_accuracy(example: dict, parsed: dict | None) -> float | None:
    """Applicable only where expected_output carries an explicit grounding
    verdict (citation_grounding: 'grounded'/'not_grounded'; hallucination_
    detection: 'hallucinated'). None for every other task type -- there is
    no invented fallback."""
    expected = example.get("expected_output", {})
    if "verdict" not in expected:
        return None
    if parsed is None:
        return 0.0
    return 1.0 if str(parsed.get("verdict", "")).strip().lower() == str(expected["verdict"]).strip().lower() else 0.0


def hallucination_flag_correct(example: dict, parsed: dict | None) -> float | None:
    """Applicable only to examples whose teacher-recorded verdict IS a
    hallucination/non-grounding finding -- measures whether the model
    correctly reproduces that negative finding rather than fabricating an
    ungrounded positive answer. None for examples with no such label."""
    expected = example.get("expected_output", {})
    verdict = str(expected.get("verdict", "")).strip().lower()
    if verdict not in ("hallucinated", "not_grounded"):
        return None
    if parsed is None:
        return 0.0
    return 1.0 if str(parsed.get("verdict", "")).strip().lower() == verdict else 0.0


PER_EXAMPLE_METRICS = {
    "agreement_with_teacher": lambda ex, parsed: field_agreement(ex.get("expected_output", {}), parsed),
    "self_critique_quality": self_critique_quality,
    "grounding_accuracy": grounding_accuracy,
    "hallucination_flag_correct": hallucination_flag_correct,
}


def score_example(example: dict, parsed: dict | None) -> dict:
    return {name: fn(example, parsed) for name, fn in PER_EXAMPLE_METRICS.items()}


def aggregate_metrics(records: list[dict]) -> dict:
    """`records`: [{"dataset_type", "scores": {...}, "latency_s", "output_tokens"}, ...].
    Produces per-type and overall summaries. A metric with zero applicable
    (non-None) scores across ALL records is reported as "not measurable"
    with a count of 0, never silently omitted or defaulted to 0.0 -- the
    LIM-3 report must be able to say exactly which named metrics from the
    owner's list had no eligible data this run, and why."""
    by_type: dict[str, list[dict]] = {}
    for r in records:
        by_type.setdefault(r["dataset_type"], []).append(r)

    def _summarize(recs: list[dict]) -> dict:
        out = {}
        for metric_name in PER_EXAMPLE_METRICS:
            vals = [r["scores"][metric_name] for r in recs if r["scores"].get(metric_name) is not None]
            out[metric_name] = ({"n": len(vals), "mean": round(statistics.mean(vals), 4)}
                                if vals else {"n": 0, "mean": None, "status": "not measurable — "
                                             "no held-out example this run carried an applicable label"})
        latencies = [r["latency_s"] for r in recs]
        out["performance"] = {
            "n": len(recs),
            "mean_latency_s": round(statistics.mean(latencies), 3) if latencies else None,
            "p95_latency_s": (round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3)
                             if latencies else None),
            "mean_output_tokens": (round(statistics.mean([r["output_tokens"] for r in recs]), 1)
                                  if recs else None),
        }
        return out

    return {
        "overall": _summarize(records),
        "by_dataset_type": {t: _summarize(recs) for t, recs in by_type.items()},
        "n_examples_total": len(records),
        "dataset_types_evaluated": sorted(by_type),
    }
