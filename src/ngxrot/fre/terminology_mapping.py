"""FSI Phase 2 shared infrastructure: accounting-terminology mapping
(docs/fre_runs/fsi_phase2_execution_plan.md section 4.3).

Reads configs/financial_statement_terminology.toml (config-driven, same
pattern as every other taxonomy on this platform) to map an observed,
literal label from a real filing to the canonical `fact_type` name. An
unmatched label returns None -- never a guessed fallback -- directly
implementing the "no silent metric substitution" constraint: every
successful match is intended to be recorded, by the caller, alongside
which literal label produced it (see fsi_extract_phase2.py), so a reader
can always see the trace from source label to canonical concept.

Seeded from FSI Phase 1's own confirmed real finding: AFRIPRUD (a share
registrar) has no line item literally called "Revenue" -- its own
headline metric is "Gross Earnings", and even that label is inconsistent
across AFRIPRUD's own filings over time ("Gross earnings" in 2020 vs.
"Gross Revenue" in 2022). Both are listed as synonyms for `revenue` in
the config; this module's job is only to look them up, not to invent the
mapping itself.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "financial_statement_terminology.toml"


def _load_terminology() -> dict[str, list[str]]:
    with open(CONFIG_PATH, "rb") as fh:
        data = tomllib.load(fh)
    return {concept: entry["synonyms"] for concept, entry in data.items()}


def map_label_to_concept(observed_label: str) -> str | None:
    """Case-insensitive match against every canonical concept's synonym
    list. Returns the canonical fact_type name, or None if the label is
    not a recognized synonym for anything -- an unmatched label is a real,
    disclosed gap (surface it as missing evidence), never a guess."""
    terminology = _load_terminology()
    normalized = observed_label.strip().lower()
    for concept, synonyms in terminology.items():
        if any(normalized == syn.strip().lower() for syn in synonyms):
            return concept
    return None
