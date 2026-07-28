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
from collections import Counter


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


def _leaf_strings(obj) -> list[str]:
    out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_leaf_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_leaf_strings(v))
    return out


def _leaf_values_as_str(obj) -> list[str]:
    """Like _leaf_strings, but also stringifies numeric leaves (int/float)
    -- needed for citation_correctness, where a model outputting a real
    JSON number (`{"doc_id": 123}`) is at least as likely as a string
    (`{"doc_id": "123"}`), and doc_ids/evidence_ids in this corpus ARE
    integers. _leaf_strings is left number-blind deliberately for the
    other callers (hallucination_risk, grounded_correctness), which are
    about matching free-text/ticker STRING content, not numeric ids."""
    out = []
    if isinstance(obj, (str, int, float)) and not isinstance(obj, bool):
        out.append(str(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_leaf_values_as_str(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_leaf_values_as_str(v))
    return out


def _fuzzy_str_match(a: str, b: str) -> float:
    """Token-set overlap ratio (Jaccard) -- cheap, deterministic, no model
    call, no new dependency. 1.0 for identical strings (case/whitespace
    -insensitive); partial credit for overlapping words (a paraphrase or
    reordered/partially-matching description scores between 0 and 1
    instead of a hard 0 the way exact-match field_agreement would)."""
    ta, tb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return round(len(ta & tb) / len(ta | tb), 4)


# LIM-5 §Priority 4: field-alias table for semantic_equivalence, populated
# from field-name variants ACTUALLY OBSERVED in real LIM-4 eval outputs
# (docs/lim_runs/lim4_completion.md) -- e.g. the model wrapping a dividend
# fact as {"amount": ...} instead of the schema's {"numeric_value": ...}.
# Same "disclosed, owner-adjustable, not silently extended" status as
# every other alias/config table in this package.
_FIELD_ALIASES = {
    "amount": "numeric_value", "dividend_amount": "numeric_value", "value": "numeric_value",
    "date": "filing_date", "payment_date": "filing_date",
    "entity": "canonical_name", "name": "canonical_name",
    "type": "entity_type", "ticker": "resolved_ticker",
}


def _unwrap_single_key(parsed: dict) -> dict:
    """Unwraps a single-key wrapper (e.g. {"dividend": {...}} or
    {"named_entities": [{...}]}) -- both observed in real LIM-4 eval
    output -- before scoring. A model producing the right content under
    an unexpected wrapper should not score identically to one producing
    unrelated content; that conflation is the exact gap LIM-4 found in
    agreement_with_teacher (§lim4_completion.md, "extraction"/
    "corporate_actions" raw outputs)."""
    if not isinstance(parsed, dict) or len(parsed) != 1:
        return parsed
    ((_key, val),) = parsed.items()
    if isinstance(val, dict):
        return val
    if isinstance(val, list) and len(val) == 1 and isinstance(val[0], dict):
        return val[0]
    return parsed


def _normalize_keys(d: dict) -> dict:
    return {_FIELD_ALIASES.get(k, k): v for k, v in d.items()}


def semantic_equivalence(example: dict, parsed: dict | None) -> float | None:
    """LIM-5 next-gen metric (designed in LIM-4, implemented here):
    distinguishes structurally-different-but-semantically-equivalent
    output from genuinely wrong output -- unwraps common single-key
    wrappers, normalizes known field-name aliases, then scores each
    expected field with FUZZY (not exact) string matching. Deliberately
    scores >= agreement_with_teacher whenever the two diverge, never <
    -- this is the metric meant to detect the exact real-output
    improvement LIM-4 found but agreement_with_teacher could not
    (checkpoint no longer hallucinating "Coca-Cola", but exact-key
    -matching scored it identically to before)."""
    expected = example.get("expected_output", {})
    if not expected:
        return None
    if parsed is None:
        return 0.0
    normalized = _normalize_keys(_unwrap_single_key(parsed) or {})
    scores = []
    for k, v in expected.items():
        key = _FIELD_ALIASES.get(k, k)
        actual = normalized.get(key, normalized.get(k))
        if actual is None and (key not in normalized and k not in normalized):
            scores.append(0.0)
        else:
            scores.append(_semantic_value_match(v, actual))
    return round(sum(scores) / len(scores), 4)


def _semantic_value_match(expected_val, actual_val) -> float:
    if isinstance(expected_val, str) and isinstance(actual_val, str):
        if expected_val.strip().lower() == actual_val.strip().lower():
            return 1.0
        return _fuzzy_str_match(expected_val, actual_val)
    return 1.0 if _values_match(expected_val, actual_val) else 0.0


def partial_credit_tier(score: float | None) -> str | None:
    """Reporting bucket for any [0,1] agreement-style score -- not a new
    computation, a readability layer over agreement_with_teacher or
    semantic_equivalence."""
    if score is None:
        return None
    if score >= 0.8:
        return "correct"
    if score >= 0.4:
        return "partial"
    return "incorrect"


def grounded_correctness(example: dict, parsed: dict | None) -> float | None:
    """LIM-5 next-gen metric: does the model's answer contain claims
    traceable to the example's own provided evidence (citations'
    quoted_text + context), independent of whether it matches
    expected_output exactly? A containment check (is this string present
    in the evidence the model was actually given), not a semantic
    -similarity model call -- separates "grounded" from "correct", which
    a single agreement score conflates (LIM-4 design). None when the
    example carries no context/citation text to check against, or the
    model's output has no string values worth checking."""
    citations = example.get("citations") or []
    evidence_text = " ".join(c.get("quoted_text", "") or "" for c in citations)
    context = example.get("context") or {}
    if not evidence_text.strip() and not context:
        return None
    haystack = (evidence_text + " " + json.dumps(context, default=str)).lower()
    if parsed is None:
        return 0.0
    leaf_values = [v for v in _leaf_strings(parsed) if len(v) >= 3]
    if not leaf_values:
        return None
    found = sum(1 for v in leaf_values if v.lower() in haystack)
    return round(found / len(leaf_values), 4)


def citation_correctness(example: dict, parsed: dict | None) -> float | None:
    """LIM-5 next-gen metric: applicable only when the example carries
    real citation/evidence ids AND the model's output actually references
    an id-bearing field. Honestly returns None for the current corpus in
    almost every case -- no dataset type's expected_output currently asks
    the model to cite a specific id (the citation-accuracy gap LIM-3
    disclosed still exists; this metric does not fabricate applicability
    that the underlying dataset schema doesn't support)."""
    citations = example.get("citations") or []
    real_ids = {str(c["doc_id"]) for c in citations if c.get("doc_id") is not None}
    real_ids |= {str(c["evidence_id"]) for c in citations if c.get("evidence_id") is not None}
    if not real_ids or parsed is None:
        return None
    referenced_any_id_field = any(
        k in parsed for k in ("doc_id", "evidence_id", "doc_ids", "evidence_ids", "citations"))
    if not referenced_any_id_field:
        return None
    cited = set(_leaf_values_as_str(parsed)) & real_ids
    return round(len(cited) / len(real_ids), 4)


_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")  # letters + trailing digits (e.g. "STANBICETF30")


def hallucination_risk(example: dict, parsed: dict | None) -> float | None:
    """LIM-5 next-gen metric: a TASK-AGNOSTIC hallucination check (LIM-4
    design), not limited to the one dataset type whose labels say
    "hallucinated". Extracts ticker-shaped string VALUES (whole value is
    2-12 uppercase letters, e.g. "GTCO", "KO") from the model's output and
    checks whether each one appears anywhere in the example's own
    context/citations/expected_output -- i.e. was actually part of what
    the model was given, rather than fabricated. This is precisely the
    check that would have caught LIM-3's "Coca-Cola"/"KO" hallucination
    directly and quantitatively (KO featured in no NGX filing in this
    corpus) instead of requiring manual raw-output inspection. Returns
    the FRACTION of ticker-shaped values that are fabricated (0.0 = none
    fabricated: fully grounded; 1.0 = all fabricated). None when the
    output contains no ticker-shaped value to check."""
    if parsed is None:
        return None
    haystack = json.dumps({
        "context": example.get("context", {}), "citations": example.get("citations", []),
        "expected_output": example.get("expected_output", {}),
    }, default=str)
    candidates = [v.strip() for v in _leaf_strings(parsed) if _TICKER_PATTERN.match(v.strip())]
    if not candidates:
        return None
    fabricated = sum(1 for t in candidates if t not in haystack)
    return round(fabricated / len(candidates), 4)


def reasoning_quality(example: dict, parsed: dict | None) -> float | None:
    """LIM-5 next-gen metric: lexical-overlap (word-set Jaccard, via
    _fuzzy_str_match) between the model's free-text explanation/rationale
    and the teacher's corresponding field -- partial credit for reasoning
    that references the right concepts without matching verbatim.
    Applicable to task types whose expected_output carries a free-text
    reasoning field (self_critique's 'explanation', contradiction_
    detection's 'rationale'); None otherwise."""
    expected = example.get("expected_output", {})
    text_field = next((f for f in ("explanation", "rationale", "reasoning") if f in expected), None)
    if text_field is None or not isinstance(expected.get(text_field), str) or not expected[text_field].strip():
        return None
    if parsed is None:
        return 0.0
    actual_text = parsed.get(text_field)
    if not isinstance(actual_text, str):
        candidates = [v for v in parsed.values() if isinstance(v, str) and len(v) > 20]
        actual_text = candidates[0] if candidates else ""
    return _fuzzy_str_match(expected[text_field], actual_text)


PER_EXAMPLE_METRICS = {
    # Original LIM-3 metrics -- UNCHANGED, so every future eval_run remains
    # directly comparable to the frozen lim3-eval-baseline on these keys.
    "agreement_with_teacher": lambda ex, parsed: field_agreement(ex.get("expected_output", {}), parsed),
    "self_critique_quality": self_critique_quality,
    "grounding_accuracy": grounding_accuracy,
    "hallucination_flag_correct": hallucination_flag_correct,
    # LIM-5 §Priority 4 additions -- new keys only, nothing above removed
    # or redefined.
    "semantic_equivalence": semantic_equivalence,
    "grounded_correctness": grounded_correctness,
    "citation_correctness": citation_correctness,
    "hallucination_risk": hallucination_risk,
    "reasoning_quality": reasoning_quality,
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
        # LIM-5 §Priority 4: partial-credit tier counts, reported alongside
        # (not instead of) the raw mean -- a readability layer, not a new
        # computation, over the two continuous [0,1] agreement-style
        # metrics (agreement_with_teacher stays exact-match; semantic_
        # equivalence is the fuzzy counterpart).
        for metric_name in ("agreement_with_teacher", "semantic_equivalence"):
            vals = [r["scores"][metric_name] for r in recs if r["scores"].get(metric_name) is not None]
            if vals:
                out[metric_name]["tiers"] = dict(Counter(partial_credit_tier(v) for v in vals))
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
